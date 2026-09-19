"""Optional persisted Planner telemetry for development and tuning.

Telemetry is observational only. Disabling it must not change Planner semantics,
routing, authority, or execution behavior. Raw prompts/responses are deliberately
not stored here; deep raw artifacts remain controlled by RoleDiagnostics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from acl_core import CoreIdentity
from acl_core.canonical import canonical_json
from acl_core.diagnostics import emit

from acl_roles.planner import PlannerRuntimeRequest, PlannerRuntimeResponse

from ..errors import ControllerError
from ..models import utc_now


PLANNER_TELEMETRY_CONFIG_SCHEMA = "acl-planner-telemetry:v1"
PLANNER_TELEMETRY_RECORD_SCHEMA = "acl-planner-telemetry-record:v1"


@dataclass(frozen=True)
class PlannerTelemetryConfig:
    enabled: bool = True

    @classmethod
    def load(cls, path: str | Path) -> "PlannerTelemetryConfig":
        path = Path(path).expanduser().resolve()
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_TELEMETRY_CONFIG_MISSING",
                "Planner telemetry configuration is missing",
                {"path": str(path)},
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_TELEMETRY_CONFIG_INVALID",
                "Planner telemetry configuration cannot be read",
                {"path": str(path)},
            ) from exc
        if (
            not isinstance(value, Mapping)
            or value.get("schema_version") != PLANNER_TELEMETRY_CONFIG_SCHEMA
            or not isinstance(value.get("enabled"), bool)
        ):
            raise ControllerError(
                "CONTROLLER_PLANNER_TELEMETRY_CONFIG_INVALID",
                "Planner telemetry configuration schema is invalid",
                {"path": str(path)},
            )
        return cls(enabled=value["enabled"])


@dataclass(frozen=True)
class PlannerTelemetryRecord:
    telemetry_id: str
    workflow_id: str
    invocation_mode: str
    success: bool
    disposition: str | None = None
    attempt_id: str | None = None
    backend_id: str | None = None
    profile_id: str | None = None
    adapter_id: str | None = None
    runtime_family: str | None = None
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    context_window: int | None = None
    context_utilization: float | None = None
    http_elapsed_ms: float | None = None
    planner_elapsed_ms: float | None = None
    model_load_ms: float | None = None
    model_unload_ms: float | None = None
    request_bytes: int | None = None
    response_bytes: int | None = None
    finish_reason: str | None = None
    correction_attempt: int | None = None
    consultation_id: str | None = None
    exchange_number: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    runtime_metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PLANNER_TELEMETRY_RECORD_SCHEMA,
            "telemetry_id": self.telemetry_id,
            "workflow_id": self.workflow_id,
            "invocation_mode": self.invocation_mode,
            "success": self.success,
            "disposition": self.disposition,
            "attempt_id": self.attempt_id,
            "backend_id": self.backend_id,
            "profile_id": self.profile_id,
            "adapter_id": self.adapter_id,
            "runtime_family": self.runtime_family,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "context_window": self.context_window,
            "context_utilization": self.context_utilization,
            "http_elapsed_ms": self.http_elapsed_ms,
            "planner_elapsed_ms": self.planner_elapsed_ms,
            "model_load_ms": self.model_load_ms,
            "model_unload_ms": self.model_unload_ms,
            "request_bytes": self.request_bytes,
            "response_bytes": self.response_bytes,
            "finish_reason": self.finish_reason,
            "correction_attempt": self.correction_attempt,
            "consultation_id": self.consultation_id,
            "exchange_number": self.exchange_number,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "runtime_metadata": dict(self.runtime_metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerTelemetryRecord":
        if (
            not isinstance(value, Mapping)
            or value.get("schema_version") != PLANNER_TELEMETRY_RECORD_SCHEMA
        ):
            raise ControllerError(
                "CONTROLLER_PLANNER_TELEMETRY_INVALID",
                "Planner telemetry record schema is invalid",
            )
        try:
            return cls(
                telemetry_id=value["telemetry_id"],
                workflow_id=value["workflow_id"],
                invocation_mode=value["invocation_mode"],
                success=bool(value["success"]),
                disposition=value.get("disposition"),
                attempt_id=value.get("attempt_id"),
                backend_id=value.get("backend_id"),
                profile_id=value.get("profile_id"),
                adapter_id=value.get("adapter_id"),
                runtime_family=value.get("runtime_family"),
                model=value.get("model"),
                prompt_tokens=_optional_int(value.get("prompt_tokens")),
                completion_tokens=_optional_int(value.get("completion_tokens")),
                total_tokens=_optional_int(value.get("total_tokens")),
                context_window=_optional_int(value.get("context_window")),
                context_utilization=_optional_float(value.get("context_utilization")),
                http_elapsed_ms=_optional_float(value.get("http_elapsed_ms")),
                planner_elapsed_ms=_optional_float(value.get("planner_elapsed_ms")),
                model_load_ms=_optional_float(value.get("model_load_ms")),
                model_unload_ms=_optional_float(value.get("model_unload_ms")),
                request_bytes=_optional_int(value.get("request_bytes")),
                response_bytes=_optional_int(value.get("response_bytes")),
                finish_reason=value.get("finish_reason"),
                correction_attempt=_optional_int(value.get("correction_attempt")),
                consultation_id=value.get("consultation_id"),
                exchange_number=_optional_int(value.get("exchange_number")),
                error_code=value.get("error_code"),
                error_message=value.get("error_message"),
                runtime_metadata=dict(value.get("runtime_metadata", {})),
                created_at=value["created_at"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_TELEMETRY_INVALID",
                "Planner telemetry record is malformed",
            ) from exc


class JsonPlannerTelemetryStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def save(self, record: PlannerTelemetryRecord) -> PlannerTelemetryRecord:
        path = self._path(record.telemetry_id)
        with self._lock:
            if path.exists():
                raise ControllerError(
                    "CONTROLLER_PLANNER_TELEMETRY_EXISTS",
                    "Planner telemetry ID already exists",
                    {"telemetry_id": record.telemetry_id},
                )
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix(path.suffix + ".tmp")
            try:
                temp.write_text(canonical_json(record.to_dict()) + "\n", encoding="utf-8")
                os.replace(temp, path)
            except OSError as exc:
                try:
                    temp.unlink(missing_ok=True)
                except OSError:
                    pass
                raise ControllerError(
                    "CONTROLLER_PLANNER_TELEMETRY_WRITE_FAILED",
                    "Planner telemetry could not be persisted",
                    {"telemetry_id": record.telemetry_id},
                ) from exc
        return record

    def for_workflow(self, workflow_id: str) -> tuple[PlannerTelemetryRecord, ...]:
        directory = self.root / "planner-telemetry"
        if not directory.exists():
            return ()
        records: list[PlannerTelemetryRecord] = []
        for path in sorted(directory.glob("plannertelemetry_*.json")):
            try:
                record = PlannerTelemetryRecord.from_mapping(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except (OSError, json.JSONDecodeError, ControllerError) as exc:
                raise ControllerError(
                    "CONTROLLER_PLANNER_TELEMETRY_READ_FAILED",
                    "one or more Planner telemetry records are unreadable",
                    {"path": str(path)},
                ) from exc
            if record.workflow_id == workflow_id:
                records.append(record)
        return tuple(records)

    def _path(self, telemetry_id: str) -> Path:
        if (
            not isinstance(telemetry_id, str)
            or not telemetry_id.startswith("plannertelemetry:")
        ):
            raise ControllerError(
                "CONTROLLER_PLANNER_TELEMETRY_INVALID",
                "Planner telemetry ID is invalid",
            )
        return self.root / "planner-telemetry" / f"{telemetry_id.replace(':', '_')}.json"


class PlannerTelemetryService:
    component = "controller.planner.telemetry"

    def __init__(
        self,
        *,
        config: PlannerTelemetryConfig,
        store: JsonPlannerTelemetryStore,
    ) -> None:
        self.config = config
        self.store = store

    def record(
        self,
        request: PlannerRuntimeRequest,
        *,
        response: PlannerRuntimeResponse | None = None,
        error: BaseException | None = None,
    ) -> PlannerTelemetryRecord | None:
        if not self.config.enabled:
            return None

        runtime_metadata = {} if response is None else dict(response.runtime_metadata)
        role_metadata = runtime_metadata.get("role_metadata")
        role_metadata = dict(role_metadata) if isinstance(role_metadata, Mapping) else {}
        adapter = role_metadata.get("adapter_telemetry")
        adapter = dict(adapter) if isinstance(adapter, Mapping) else {}

        error_code = None
        error_message = None
        if error is not None:
            error_code = getattr(error, "code", None)
            error_message = getattr(error, "message", None)
            if not isinstance(error_code, str):
                error_code = type(error).__name__
            if not isinstance(error_message, str):
                error_message = str(error)

            details = getattr(error, "details", None)
            if isinstance(details, Mapping):
                observed = details.get("adapter_telemetry")
                if isinstance(observed, Mapping):
                    adapter = dict(observed)

        record = PlannerTelemetryRecord(
            telemetry_id=CoreIdentity.new("plannertelemetry").value,
            workflow_id=request.workflow_id,
            invocation_mode=str(request.planner_input.invocation_mode),
            success=error is None and response is not None,
            disposition=(
                None if response is None else str(response.result.disposition)
            ),
            attempt_id=_text(runtime_metadata.get("attempt_id")),
            backend_id=_text(runtime_metadata.get("backend_id")),
            profile_id=_text(runtime_metadata.get("profile_id")),
            adapter_id=_text(adapter.get("adapter_id")),
            runtime_family=_text(adapter.get("runtime_family")),
            model=_text(adapter.get("model")),
            prompt_tokens=_optional_int(adapter.get("prompt_tokens")),
            completion_tokens=_optional_int(adapter.get("completion_tokens")),
            total_tokens=_optional_int(adapter.get("total_tokens")),
            context_window=_optional_int(adapter.get("context_window")),
            context_utilization=_optional_float(adapter.get("context_utilization")),
            http_elapsed_ms=_optional_float(adapter.get("http_elapsed_ms")),
            planner_elapsed_ms=_optional_float(runtime_metadata.get("planner_elapsed_ms")),
            model_load_ms=_optional_float(adapter.get("model_load_ms")),
            model_unload_ms=_optional_float(adapter.get("model_unload_ms")),
            request_bytes=_optional_int(adapter.get("request_bytes")),
            response_bytes=_optional_int(adapter.get("response_bytes")),
            finish_reason=_text(adapter.get("finish_reason")),
            correction_attempt=(
                None
                if request.planner_input.correction is None
                else request.planner_input.correction.attempt
            ),
            consultation_id=_text(request.metadata.get("consultation_id")),
            exchange_number=_optional_int(request.metadata.get("exchange_number")),
            error_code=error_code,
            error_message=error_message,
            runtime_metadata=runtime_metadata,
        )
        self.store.save(record)
        emit(
            "INFO" if record.success else "ERROR",
            self.component,
            "record",
            "planner_telemetry_recorded",
            telemetry_id=record.telemetry_id,
            workflow_id=record.workflow_id,
            invocation_mode=record.invocation_mode,
            disposition=record.disposition,
            success=record.success,
            backend_id=record.backend_id,
            profile_id=record.profile_id,
            adapter_id=record.adapter_id,
            model=record.model,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            total_tokens=record.total_tokens,
            context_utilization=record.context_utilization,
            planner_elapsed_ms=record.planner_elapsed_ms,
            http_elapsed_ms=record.http_elapsed_ms,
            correction_attempt=record.correction_attempt,
            consultation_id=record.consultation_id,
            exchange_number=record.exchange_number,
            error_code=record.error_code,
        )
        return record

    def records(self, workflow_id: str) -> tuple[PlannerTelemetryRecord, ...]:
        if not self.config.enabled:
            return ()
        return self.store.for_workflow(workflow_id)

    def summary(self, workflow_id: str) -> dict[str, Any]:
        records = self.records(workflow_id)
        successful = tuple(item for item in records if item.success)
        return {
            "telemetry_enabled": self.config.enabled,
            "workflow_id": workflow_id,
            "invocations": len(records),
            "successful_invocations": len(successful),
            "failed_invocations": len(records) - len(successful),
            "correction_invocations": sum(
                1 for item in records if item.correction_attempt is not None
            ),
            "consultation_invocations": sum(
                1 for item in records if item.consultation_id is not None
            ),
            "prompt_tokens": sum(
                item.prompt_tokens for item in records if item.prompt_tokens is not None
            ),
            "prompt_token_reports": sum(
                1 for item in records if item.prompt_tokens is not None
            ),
            "completion_tokens": sum(
                item.completion_tokens
                for item in records
                if item.completion_tokens is not None
            ),
            "completion_token_reports": sum(
                1 for item in records if item.completion_tokens is not None
            ),
            "total_tokens": sum(
                item.total_tokens for item in records if item.total_tokens is not None
            ),
            "total_token_reports": sum(
                1 for item in records if item.total_tokens is not None
            ),
            "planner_elapsed_ms": round(
                sum(
                    item.planner_elapsed_ms
                    for item in records
                    if item.planner_elapsed_ms is not None
                ),
                3,
            ),
            "http_elapsed_ms": round(
                sum(
                    item.http_elapsed_ms
                    for item in records
                    if item.http_elapsed_ms is not None
                ),
                3,
            ),
            "models": sorted(
                {item.model for item in records if item.model is not None}
            ),
            "adapters": sorted(
                {item.adapter_id for item in records if item.adapter_id is not None}
            ),
            "backends": sorted(
                {item.backend_id for item in records if item.backend_id is not None}
            ),
        }


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None
    return float(value)


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
