from __future__ import annotations

from collections import Counter, deque
import contextvars
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import threading
import time
from typing import Any
from uuid import uuid4

from knowledge_core.domain.projection_adapter import (
    ProjectionAdapterReceipt,
    ProjectionAdapterRequest,
    ProjectionSearchHit,
)
from knowledge_core_providers.graphiti import (
    GraphitiLocalConfig,
    GraphitiProjectionAdapter,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_size(value: object) -> int:
    try:
        return len(json.dumps(value, sort_keys=True, default=str, ensure_ascii=False))
    except Exception:
        return 0


class QualificationEventRecorder:
    """Fail-open JSONL event journal for qualification-only observability."""

    def __init__(self, path: Path, *, recent_limit: int = 4000) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._sequence = 0
        self._recent: deque[dict[str, Any]] = deque(maxlen=recent_limit)
        self._errors: list[str] = []
        try:
            self.path.write_text("", encoding="utf-8")
        except Exception as exc:
            self._errors.append(f"initialize event journal: {type(exc).__name__}: {exc}")

    def emit(self, event_type: str, **payload: object) -> dict[str, Any]:
        with self._lock:
            self._sequence += 1
            event = {
                "event_version": 1,
                "sequence": self._sequence,
                "event_type": event_type,
                "timestamp_utc": _utc_now(),
                "monotonic_ns": time.monotonic_ns(),
                **payload,
            }
            self._recent.append(event)
            try:
                with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(json.dumps(event, sort_keys=True, default=str, ensure_ascii=False))
                    handle.write("\n")
                    handle.flush()
            except Exception as exc:
                message = f"write event journal: {type(exc).__name__}: {exc}"
                if message not in self._errors:
                    self._errors.append(message)
            return dict(event)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._recent]

    @property
    def errors(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._errors)


class _JournalWarningHandler(logging.Handler):
    def __init__(self, recorder: QualificationEventRecorder) -> None:
        super().__init__(level=logging.WARNING)
        self.recorder = recorder

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.recorder.emit(
                "graphiti_warning",
                logger=record.name,
                message=record.getMessage(),
            )
        except Exception:
            pass


class ObservableGraphitiProjectionAdapter(GraphitiProjectionAdapter):
    """Read-only observer around the accepted Graphiti adapter.

    This class is intended only for host qualification. It leaves the base adapter's
    descriptor, config digest, extraction behavior, validation behavior, and provider
    writes unchanged. It wraps live calls to emit timing/progress metadata.
    """

    def __init__(
        self,
        config: GraphitiLocalConfig | None = None,
        *,
        recorder: QualificationEventRecorder,
    ) -> None:
        super().__init__(config)
        self.recorder = recorder
        self._llm_request_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            "kc_graphiti_observer_llm_request_id",
            default=None,
        )
        self._llm_usage: dict[str, dict[str, int | None]] = {}

    def _emit(self, event_type: str, **payload: object) -> None:
        try:
            self.recorder.emit(event_type, **payload)
        except Exception:
            # Observability must never change the provider outcome.
            pass

    def _instrument_graphiti(self, graphiti, *, partition_key: str) -> None:
        if getattr(graphiti, "_kc_observer_instrumented", False):
            return
        setattr(graphiti, "_kc_observer_instrumented", True)

        llm_client = graphiti.llm_client
        original_generate = llm_client._generate_response

        async def observed_generate(*args, **kwargs):
            messages = args[0] if args else kwargs.get("messages", [])
            response_model = args[1] if len(args) > 1 else kwargs.get("response_model")
            stage = getattr(response_model, "__name__", None) or "unstructured"
            prompt_characters = sum(
                len(str(getattr(message, "content", "") or ""))
                for message in (messages or ())
            )
            request_id = str(uuid4())
            token = self._llm_request_context.set(request_id)
            started = time.monotonic()
            self._emit(
                "llm_request_started",
                request_id=request_id,
                stage=stage,
                model=str(getattr(llm_client, "model", self.config.llm_model)),
                partition_key=partition_key,
                message_count=len(messages or ()),
                prompt_characters=prompt_characters,
            )
            try:
                result = await original_generate(*args, **kwargs)
            except BaseException as exc:
                self._emit(
                    "llm_request_failed",
                    request_id=request_id,
                    stage=stage,
                    duration_seconds=round(time.monotonic() - started, 3),
                    error=f"{type(exc).__name__}: {exc}",
                )
                raise
            else:
                duration = time.monotonic() - started
                usage = self._llm_usage.pop(request_id, {})
                list_counts = {}
                result_keys: list[str] = []
                if isinstance(result, dict):
                    result_keys = sorted(str(key) for key in result)
                    list_counts = {
                        str(key): len(value)
                        for key, value in result.items()
                        if isinstance(value, list)
                    }
                completion_tokens = usage.get("completion_tokens")
                self._emit(
                    "llm_request_completed",
                    request_id=request_id,
                    stage=stage,
                    duration_seconds=round(duration, 3),
                    response_characters=_json_size(result),
                    result_keys=result_keys,
                    list_counts=list_counts,
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=completion_tokens,
                    total_tokens=usage.get("total_tokens"),
                    completion_tokens_per_second=(
                        round(float(completion_tokens) / duration, 3)
                        if completion_tokens is not None and duration > 0
                        else None
                    ),
                )
                return result
            finally:
                self._llm_request_context.reset(token)

        llm_client._generate_response = observed_generate

        # Capture OpenAI-compatible token usage when the concrete client allows the
        # transport method to be wrapped. If not, stage timing still works.
        try:
            completions = llm_client.client.chat.completions
            original_create = completions.create

            async def observed_create(*args, **kwargs):
                response = await original_create(*args, **kwargs)
                request_id = self._llm_request_context.get()
                usage = getattr(response, "usage", None)
                if request_id is not None and usage is not None:
                    self._llm_usage[request_id] = {
                        "prompt_tokens": getattr(usage, "prompt_tokens", None),
                        "completion_tokens": getattr(usage, "completion_tokens", None),
                        "total_tokens": getattr(usage, "total_tokens", None),
                    }
                return response

            completions.create = observed_create
        except Exception as exc:
            self._emit(
                "observer_notice",
                notice="llm-token-usage-unavailable",
                detail=f"{type(exc).__name__}: {exc}",
            )

        original_add_episode = graphiti.add_episode

        async def observed_add_episode(*args, **kwargs):
            name = kwargs.get("name")
            body = kwargs.get("episode_body", "")
            segment_key = name[3:] if isinstance(name, str) and name.startswith("kc:") else None
            started = time.monotonic()
            self._emit(
                "segment_started",
                segment_key=segment_key,
                provider_name=name,
                partition_key=partition_key,
                body_characters=len(body) if isinstance(body, str) else None,
                body_bytes=len(body.encode("utf-8")) if isinstance(body, str) else None,
            )
            try:
                result = await original_add_episode(*args, **kwargs)
            except BaseException as exc:
                self._emit(
                    "segment_failed",
                    segment_key=segment_key,
                    duration_seconds=round(time.monotonic() - started, 3),
                    error=f"{type(exc).__name__}: {exc}",
                )
                raise
            self._emit(
                "segment_completed",
                segment_key=segment_key,
                duration_seconds=round(time.monotonic() - started, 3),
                provider_source_id=str(getattr(result.episode, "uuid", "")),
                node_count=len(getattr(result, "nodes", ()) or ()),
                edge_count=len(getattr(result, "edges", ()) or ()),
            )
            return result

        graphiti.add_episode = observed_add_episode

    def _build_graphiti(self, *, partition_key: str):
        graphiti = super()._build_graphiti(partition_key=partition_key)
        self._instrument_graphiti(graphiti, partition_key=partition_key)
        return graphiti

    async def project(self, request: ProjectionAdapterRequest) -> ProjectionAdapterReceipt:
        profile_id = request.attempt.profile_id
        partition = (
            self.partition_key(
                namespace_key=request.attempt.namespace_key,
                scope_key=request.attempt.scope_key,
                projection_profile_id=profile_id,
            )
            if profile_id is not None
            else None
        )
        self._emit(
            "projection_started",
            attempt_id=str(request.attempt.attempt_id),
            partition_key=partition,
            segment_count=len(request.segments),
        )
        handler = _JournalWarningHandler(self.recorder)
        graphiti_logger = logging.getLogger("graphiti_core")
        graphiti_logger.addHandler(handler)
        started = time.monotonic()
        try:
            receipt = await super().project(request)
        except BaseException as exc:
            self._emit(
                "projection_failed",
                attempt_id=str(request.attempt.attempt_id),
                duration_seconds=round(time.monotonic() - started, 3),
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        finally:
            graphiti_logger.removeHandler(handler)
        self._emit(
            "projection_completed",
            attempt_id=str(request.attempt.attempt_id),
            duration_seconds=round(time.monotonic() - started, 3),
            disposition=receipt.disposition.value,
            episode_count=receipt.episode_count,
            node_count=receipt.node_count,
            edge_count=receipt.edge_count,
            provider_binding_count=len(receipt.source_bindings),
            warning_count=len(receipt.warnings),
            error_count=len(receipt.errors),
        )
        return receipt

    async def search(
        self,
        *,
        query: str,
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
        limit: int,
    ) -> tuple[ProjectionSearchHit, ...]:
        started = time.monotonic()
        self._emit(
            "graph_search_started",
            query=query,
            namespace_key=namespace_key,
            scope_key=scope_key,
            limit=limit,
        )
        try:
            results = await super().search(
                query=query,
                namespace_key=namespace_key,
                scope_key=scope_key,
                projection_profile_id=projection_profile_id,
                limit=limit,
            )
        except BaseException as exc:
            self._emit(
                "graph_search_failed",
                duration_seconds=round(time.monotonic() - started, 3),
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        self._emit(
            "graph_search_completed",
            duration_seconds=round(time.monotonic() - started, 3),
            result_count=len(results),
        )
        return results

    async def existing_source_keys(
        self,
        *,
        source_keys: tuple[str, ...],
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
    ) -> frozenset[str]:
        started = time.monotonic()
        self._emit("source_lookup_started", requested_source_count=len(source_keys))
        try:
            result = await super().existing_source_keys(
                source_keys=source_keys,
                namespace_key=namespace_key,
                scope_key=scope_key,
                projection_profile_id=projection_profile_id,
            )
        except BaseException as exc:
            self._emit(
                "source_lookup_failed",
                duration_seconds=round(time.monotonic() - started, 3),
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        self._emit(
            "source_lookup_completed",
            duration_seconds=round(time.monotonic() - started, 3),
            requested_source_count=len(source_keys),
            found_source_count=len(result),
        )
        return result


def aggregate_llm_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [event for event in events if event.get("event_type") == "llm_request_completed"]
    durations = [
        float(event["duration_seconds"])
        for event in completed
        if event.get("duration_seconds") is not None
    ]
    prompt_tokens = sum(
        int(event["prompt_tokens"])
        for event in completed
        if event.get("prompt_tokens") is not None
    )
    completion_tokens = sum(
        int(event["completion_tokens"])
        for event in completed
        if event.get("completion_tokens") is not None
    )
    total_tokens = sum(
        int(event["total_tokens"])
        for event in completed
        if event.get("total_tokens") is not None
    )
    token_duration = sum(
        float(event["duration_seconds"])
        for event in completed
        if event.get("completion_tokens") is not None
        and event.get("duration_seconds") is not None
    )
    stages = Counter(str(event.get("stage") or "unknown") for event in completed)
    return {
        "request_count": len(completed),
        "failed_request_count": sum(
            1 for event in events if event.get("event_type") == "llm_request_failed"
        ),
        "total_duration_seconds": round(sum(durations), 3),
        "average_duration_seconds": round(sum(durations) / len(durations), 3) if durations else None,
        "min_duration_seconds": round(min(durations), 3) if durations else None,
        "max_duration_seconds": round(max(durations), 3) if durations else None,
        "prompt_tokens": prompt_tokens or None,
        "completion_tokens": completion_tokens or None,
        "total_tokens": total_tokens or None,
        "aggregate_completion_tokens_per_second": (
            round(completion_tokens / token_duration, 3)
            if completion_tokens and token_duration > 0
            else None
        ),
        "prompt_characters": sum(
            int(event.get("prompt_characters") or 0)
            for event in events
            if event.get("event_type") == "llm_request_started"
        ),
        "response_characters": sum(
            int(event.get("response_characters") or 0)
            for event in completed
        ),
        "stages": dict(sorted(stages.items())),
    }


def open_llm_requests(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    started: dict[str, dict[str, Any]] = {}
    terminal: set[str] = set()
    for event in events:
        request_id = str(event.get("request_id") or "")
        if not request_id:
            continue
        if event.get("event_type") == "llm_request_started":
            started[request_id] = event
        elif event.get("event_type") in {"llm_request_completed", "llm_request_failed"}:
            terminal.add(request_id)
    return [event for request_id, event in started.items() if request_id not in terminal]


def latest_event(events: list[dict[str, Any]], event_type: str) -> dict[str, Any] | None:
    for event in reversed(events):
        if event.get("event_type") == event_type:
            return event
    return None
