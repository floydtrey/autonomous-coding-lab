from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from knowledge_core.integrations.context_compaction import WorkingContextCheckpoint


_DEFAULT_BASE_URL = "http://127.0.0.1:26866/api/v1"
_ALLOWED_RESPONSE_STATES = frozenset({"in_progress", "completed", "failed"})
_CHECKPOINT_GOAL_PREFIX = (
    "Continue the existing task from this bounded working-context checkpoint. "
    "Treat exact evidence/source/output references as pointers to the retained source of truth; "
    "do not treat reduced excerpts as canonical evidence.\n\n"
)


class CoworkWrapperError(RuntimeError):
    """Fail-closed error from the bounded local Cowork wrapper."""


def _require_text(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise CoworkWrapperError(f"{name} must be non-blank")
    return normalized


def _require_local_cowork_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if parsed.scheme != "http":
        raise CoworkWrapperError("Cowork wrapper requires local http")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise CoworkWrapperError("Cowork wrapper requires a loopback endpoint")
    if parsed.path != "/api/v1" or parsed.query or parsed.fragment:
        raise CoworkWrapperError("Cowork base URL must end exactly with /api/v1")
    if parsed.username is not None or parsed.password is not None:
        raise CoworkWrapperError("Cowork base URL must not contain credentials")
    return normalized


@dataclass(frozen=True)
class CoworkClientConfig:
    base_url: str = _DEFAULT_BASE_URL
    timeout_seconds: float = 120.0
    extra_headers: Mapping[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", _require_local_cowork_url(self.base_url))
        if self.timeout_seconds <= 0 or self.timeout_seconds > 3600:
            raise CoworkWrapperError("timeout_seconds must be greater than 0 and at most 3600")
        normalized_headers: dict[str, str] = {}
        for name, value in self.extra_headers.items():
            header_name = str(name).strip()
            header_value = str(value).strip()
            if not header_name or not header_value:
                raise CoworkWrapperError("Cowork extra headers must be non-blank")
            if header_name.casefold() in {"host", "content-length", "content-type"}:
                raise CoworkWrapperError(
                    f"Cowork extra header is controlled by the wrapper: {header_name}"
                )
            normalized_headers[header_name] = header_value
        object.__setattr__(self, "extra_headers", normalized_headers)


class CoworkConversationClient(Protocol):
    def create_conversation(
        self,
        *,
        project_id: str | None = None,
        title: str | None = None,
        goal: str | None = None,
    ) -> dict[str, Any]: ...

    def create_response(
        self,
        *,
        conversation_id: str,
        input_text: str,
        model: str | None = None,
        skill_ids: tuple[str, ...] = (),
    ) -> dict[str, Any]: ...


class KnowledgeCoreBridge(Protocol):
    def execute(
        self,
        operation: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class LocalCoworkClient:
    """Minimal local Cowork REST client for conversations and non-streaming responses."""

    def __init__(self, config: CoworkClientConfig | None = None):
        self.config = config or CoworkClientConfig()

    def _request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **dict(self.config.extra_headers),
        }
        request = Request(
            f"{self.config.base_url}{path}",
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise CoworkWrapperError(
                f"Cowork returned HTTP {exc.code}: {detail}"
            ) from exc
        except URLError as exc:
            raise CoworkWrapperError(
                f"Cowork is unreachable at {self.config.base_url}: {exc.reason}"
            ) from exc
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise CoworkWrapperError("Cowork returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise CoworkWrapperError("Cowork response must be a JSON object")
        return parsed

    def create_conversation(
        self,
        *,
        project_id: str | None = None,
        title: str | None = None,
        goal: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for name, value in (
            ("project_id", project_id),
            ("title", title),
            ("goal", goal),
        ):
            if value is not None:
                payload[name] = _require_text(name, value)
        return self._request("/conversations", payload)

    def create_response(
        self,
        *,
        conversation_id: str,
        input_text: str,
        model: str | None = None,
        skill_ids: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        conversation = _require_text("conversation_id", conversation_id)
        user_input = _require_text("input_text", input_text)
        if len(skill_ids) > 64:
            raise CoworkWrapperError("skill_ids must contain at most 64 items")
        normalized_skills = tuple(_require_text("skill_id", value) for value in skill_ids)
        payload: dict[str, Any] = {
            "conversation_id": conversation,
            "input": user_input,
            "stream": False,
        }
        if model is not None:
            payload["model"] = _require_text("model", model)
        if normalized_skills:
            payload["skill_ids"] = list(normalized_skills)
        return self._request("/responses", payload)


@dataclass(frozen=True)
class CoworkUsage:
    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise CoworkWrapperError("Cowork usage token counts must be non-negative")

    @property
    def observed_context_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class CoworkTurnResult:
    response_id: str
    conversation_id: str
    status: str
    model: str | None
    output_text: str
    usage: CoworkUsage | None


@dataclass(frozen=True)
class ContextRotationPolicy:
    context_limit_tokens: int
    compact_trigger_tokens: int

    def __post_init__(self) -> None:
        if self.context_limit_tokens < 1:
            raise CoworkWrapperError("context_limit_tokens must be positive")
        if self.compact_trigger_tokens < 1:
            raise CoworkWrapperError("compact_trigger_tokens must be positive")
        if self.compact_trigger_tokens >= self.context_limit_tokens:
            raise CoworkWrapperError(
                "compact_trigger_tokens must be lower than context_limit_tokens"
            )


@dataclass(frozen=True)
class ConversationRotation:
    previous_conversation_id: str
    new_conversation_id: str
    checkpoint_digest: str


class MasonCoworkWrapper:
    """Stateful endpoint wrapper without autonomous authority expansion.

    The wrapper may rotate Cowork conversations using an already-constructed Task 6H
    checkpoint. It never creates a model-generated summary itself and never writes to
    Cowork's native memory API. Durable autonomous observations may only be routed to
    KC's non-canonical candidate path; explicit canonical storage remains a distinct
    call and remains subject to KC's exact store-authority gate.
    """

    def __init__(
        self,
        *,
        cowork_client: CoworkConversationClient,
        knowledge_bridge: KnowledgeCoreBridge | None = None,
        project_id: str | None = None,
        model: str | None = None,
        skill_ids: tuple[str, ...] = (),
        context_policy: ContextRotationPolicy | None = None,
    ):
        self.cowork_client = cowork_client
        self.knowledge_bridge = knowledge_bridge
        self.project_id = (
            _require_text("project_id", project_id) if project_id is not None else None
        )
        self.model = _require_text("model", model) if model is not None else None
        self.skill_ids = tuple(_require_text("skill_id", item) for item in skill_ids)
        self.context_policy = context_policy
        self._conversation_id: str | None = None

    @property
    def conversation_id(self) -> str | None:
        return self._conversation_id

    def start_conversation(
        self,
        *,
        goal: str,
        title: str | None = None,
    ) -> str:
        if self._conversation_id is not None:
            raise CoworkWrapperError("Cowork conversation is already active")
        payload = self.cowork_client.create_conversation(
            project_id=self.project_id,
            title=title,
            goal=_require_text("goal", goal),
        )
        self._conversation_id = self._conversation_id_from(payload)
        return self._conversation_id

    def attach_conversation(self, conversation_id: str) -> None:
        if self._conversation_id is not None:
            raise CoworkWrapperError("Cowork conversation is already active")
        self._conversation_id = _require_text("conversation_id", conversation_id)

    def send_turn(self, input_text: str) -> CoworkTurnResult:
        conversation_id = self._require_active_conversation()
        raw = self.cowork_client.create_response(
            conversation_id=conversation_id,
            input_text=_require_text("input_text", input_text),
            model=self.model,
            skill_ids=self.skill_ids,
        )
        return self._turn_result_from(raw, expected_conversation_id=conversation_id)

    def needs_context_rotation(self, result: CoworkTurnResult) -> bool:
        policy = self.context_policy
        if policy is None:
            return False
        if result.usage is None:
            raise CoworkWrapperError(
                "Cowork usage is required when a context rotation policy is configured"
            )
        return result.usage.observed_context_tokens >= policy.compact_trigger_tokens

    def rotate_for_checkpoint(
        self,
        checkpoint: WorkingContextCheckpoint,
        *,
        title: str | None = None,
    ) -> ConversationRotation:
        previous = self._require_active_conversation()
        goal = _CHECKPOINT_GOAL_PREFIX + checkpoint.render_for_model()
        raw = self.cowork_client.create_conversation(
            project_id=self.project_id,
            title=title,
            goal=goal,
        )
        new_id = self._conversation_id_from(raw)
        if new_id == previous:
            raise CoworkWrapperError(
                "context rotation must create a different Cowork conversation"
            )
        self._conversation_id = new_id
        return ConversationRotation(
            previous_conversation_id=previous,
            new_conversation_id=new_id,
            checkpoint_digest=checkpoint.checkpoint_digest,
        )

    def propose_autonomous_memory(
        self,
        *,
        content: str,
        project: str,
        source_event_time: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        bridge = self._require_knowledge_bridge()
        payload: dict[str, Any] = {
            "content": _require_text("content", content),
            "project": _require_text("project", project),
        }
        if source_event_time is not None:
            payload["source_event_time"] = _require_text(
                "source_event_time", source_event_time
            )
        if idempotency_key is not None:
            payload["idempotency_key"] = _require_text(
                "idempotency_key", idempotency_key
            )
        return bridge.execute("kc_propose_memory", payload)

    def store_explicit_memory(
        self,
        *,
        content: str,
        project: str,
        source_id: str | None = None,
        source_event_time: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        bridge = self._require_knowledge_bridge()
        payload: dict[str, Any] = {
            "content": _require_text("content", content),
            "project": _require_text("project", project),
        }
        for name, value in (
            ("source_id", source_id),
            ("source_event_time", source_event_time),
            ("idempotency_key", idempotency_key),
        ):
            if value is not None:
                payload[name] = _require_text(name, value)
        return bridge.execute("kc_store", payload)

    def _require_active_conversation(self) -> str:
        if self._conversation_id is None:
            raise CoworkWrapperError("no active Cowork conversation")
        return self._conversation_id

    def _require_knowledge_bridge(self) -> KnowledgeCoreBridge:
        if self.knowledge_bridge is None:
            raise CoworkWrapperError("Knowledge Core bridge is not configured")
        return self.knowledge_bridge

    @staticmethod
    def _conversation_id_from(payload: dict[str, Any]) -> str:
        value = payload.get("id")
        if value is None:
            value = payload.get("conversation_id")
        return _require_text("Cowork conversation id", str(value or ""))

    @staticmethod
    def _turn_result_from(
        payload: dict[str, Any],
        *,
        expected_conversation_id: str,
    ) -> CoworkTurnResult:
        response_id = _require_text("Cowork response id", str(payload.get("id") or ""))
        conversation_id = _require_text(
            "Cowork response conversation_id",
            str(payload.get("conversation_id") or ""),
        )
        if conversation_id != expected_conversation_id:
            raise CoworkWrapperError(
                "Cowork response conversation_id does not match the active conversation"
            )
        status = _require_text("Cowork response status", str(payload.get("status") or ""))
        if status not in _ALLOWED_RESPONSE_STATES:
            raise CoworkWrapperError(f"unsupported Cowork response status: {status}")
        model_value = payload.get("model")
        model = (
            _require_text("Cowork response model", str(model_value))
            if model_value is not None
            else None
        )

        output = payload.get("output")
        if not isinstance(output, list):
            raise CoworkWrapperError("Cowork response output must be a list")
        text_parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                raise CoworkWrapperError("Cowork output items must be JSON objects")
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                text_parts.append(item["text"])
        output_text = "".join(text_parts)

        usage_value = payload.get("usage")
        usage: CoworkUsage | None = None
        if usage_value is not None:
            if not isinstance(usage_value, dict):
                raise CoworkWrapperError("Cowork response usage must be a JSON object")
            try:
                input_tokens = int(usage_value["input_tokens"])
                output_tokens = int(usage_value["output_tokens"])
            except (KeyError, TypeError, ValueError) as exc:
                raise CoworkWrapperError(
                    "Cowork response usage requires integer input_tokens/output_tokens"
                ) from exc
            usage = CoworkUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        return CoworkTurnResult(
            response_id=response_id,
            conversation_id=conversation_id,
            status=status,
            model=model,
            output_text=output_text,
            usage=usage,
        )


__all__ = [
    "ContextRotationPolicy",
    "ConversationRotation",
    "CoworkClientConfig",
    "CoworkTurnResult",
    "CoworkUsage",
    "CoworkWrapperError",
    "LocalCoworkClient",
    "MasonCoworkWrapper",
]
