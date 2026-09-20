"""Shared runtime telemetry extraction for ACL roles."""
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

from .errors import ControllerError
from .models import utc_now


ROLE_TELEMETRY_CONFIG_SCHEMA = "acl-role-telemetry:v1"
ROLE_TELEMETRY_RECORD_SCHEMA = "acl-role-telemetry-record:v1"


@dataclass(frozen=True)
class RoleTelemetryConfig:
    enabled: bool = True

    @classmethod
    def load(cls, path: str | Path) -> "RoleTelemetryConfig":
        path = Path(path).expanduser().resolve()
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            emit(
                "ERROR",
                "controller.role.telemetry",
                "load_config",
                "role_telemetry_config_missing",
                path=str(path),
            )
            return cls(enabled=False)
        except (OSError, json.JSONDecodeError) as exc:
            emit(
                "ERROR",
                "controller.role.telemetry",
                "load_config",
                "role_telemetry_config_invalid",
                path=str(path),
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )
            return cls(enabled=False)
        if (
            not isinstance(value, Mapping)
            or value.get("schema_version") != ROLE_TELEMETRY_CONFIG_SCHEMA
            or not isinstance(value.get("enabled"), bool)
        ):
            emit(
                "ERROR",
                "controller.role.telemetry",
                "load_config",
                "role_telemetry_config_invalid",
                path=str(path),
                reason="schema",
            )
            return cls(enabled=False)
        return cls(enabled=value["enabled"])


@dataclass(frozen=True)
class RoleTelemetryRecord:
    telemetry_id: str
    workflow_id: str
    role: str
    mode: str
    success: bool
    outcome: str | None = None
    attempt_id: str | None = None
    backend_id: str | None = None
    profile_id: str | None = None
    adapter_id: str | None = None
    runtime_family: str | None = None
    model: str | None = None
    harness_id: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    context_window: int | None = None
    context_utilization: float | None = None
    http_elapsed_ms: float | None = None
    role_elapsed_ms: float | None = None
    model_load_ms: float | None = None
    model_unload_ms: float | None = None
    tool_calls: int | None = None
    turns: int | None = None
    request_bytes: int | None = None
    response_bytes: int | None = None
    finish_reason: str | None = None
    correction_attempt: int | None = None
    run_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    runtime_metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ROLE_TELEMETRY_RECORD_SCHEMA,
            **self.__dict__,
            "runtime_metadata": dict(self.runtime_metadata),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RoleTelemetryRecord":
        if not isinstance(value, Mapping) or value.get("schema_version") != ROLE_TELEMETRY_RECORD_SCHEMA:
            raise ControllerError("CONTROLLER_ROLE_TELEMETRY_INVALID", "role telemetry schema is invalid")
        raw = dict(value)
        raw.pop("schema_version", None)
        try:
            return cls(**raw)
        except (TypeError, ValueError) as exc:
            raise ControllerError("CONTROLLER_ROLE_TELEMETRY_INVALID", "role telemetry record is malformed") from exc


class JsonRoleTelemetryStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def save(self, record: RoleTelemetryRecord) -> RoleTelemetryRecord:
        path = self.root / "role-telemetry" / f"{record.telemetry_id.replace(':', '_')}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        with self._lock:
            try:
                temp.write_text(canonical_json(record.to_dict()) + "\n", encoding="utf-8")
                os.replace(temp, path)
            except OSError as exc:
                try:
                    temp.unlink(missing_ok=True)
                except OSError:
                    pass
                raise ControllerError(
                    "CONTROLLER_ROLE_TELEMETRY_WRITE_FAILED",
                    "role telemetry could not be persisted",
                    {"telemetry_id": record.telemetry_id},
                ) from exc
        return record

    def for_workflow(self, workflow_id: str, *, role: str | None = None) -> tuple[RoleTelemetryRecord, ...]:
        directory = self.root / "role-telemetry"
        if not directory.exists():
            return ()
        records: list[RoleTelemetryRecord] = []
        for path in sorted(directory.glob("roletelemetry_*.json")):
            try:
                record = RoleTelemetryRecord.from_mapping(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, ControllerError) as exc:
                raise ControllerError(
                    "CONTROLLER_ROLE_TELEMETRY_READ_FAILED",
                    "one or more role telemetry records are unreadable",
                    {"path": str(path)},
                ) from exc
            if record.workflow_id == workflow_id and (role is None or record.role == role):
                records.append(record)
        return tuple(records)


def extract_runtime_telemetry(
    *,
    runtime_metadata: Mapping[str, Any] | None,
    request_metadata: Mapping[str, Any] | None = None,
    error: BaseException | None = None,
    elapsed_key: str | None = None,
) -> dict[str, Any]:
    runtime = dict(runtime_metadata or {})
    request_meta = dict(request_metadata or {})
    role_meta = runtime.get("role_metadata")
    role_meta = dict(role_meta) if isinstance(role_meta, Mapping) else {}
    adapter = role_meta.get("adapter_telemetry")
    adapter = dict(adapter) if isinstance(adapter, Mapping) else {}
    profile_meta = runtime.get("profile_metadata")
    profile_meta = dict(profile_meta) if isinstance(profile_meta, Mapping) else {}
    error_details: dict[str, Any] = {}

    error_code = error_message = None
    if error is not None:
        error_code = getattr(error, "code", None)
        error_message = getattr(error, "message", None)
        if not isinstance(error_code, str):
            error_code = type(error).__name__
        if not isinstance(error_message, str):
            error_message = str(error)
        details = getattr(error, "details", None)
        if isinstance(details, Mapping):
            error_details = dict(details)
            observed_runtime = details.get("runtime_metadata")
            if isinstance(observed_runtime, Mapping):
                runtime = dict(observed_runtime)
                role_meta = runtime.get("role_metadata")
                role_meta = dict(role_meta) if isinstance(role_meta, Mapping) else {}
                profile_meta = runtime.get("profile_metadata")
                profile_meta = dict(profile_meta) if isinstance(profile_meta, Mapping) else {}
                observed_adapter = role_meta.get("adapter_telemetry")
                if isinstance(observed_adapter, Mapping):
                    adapter = dict(observed_adapter)
            observed_adapter = details.get("adapter_telemetry")
            if isinstance(observed_adapter, Mapping):
                adapter = dict(observed_adapter)

    return {
        "attempt_id": _text(runtime.get("attempt_id")) or _text(error_details.get("attempt_id")),
        "backend_id": _text(runtime.get("backend_id")) or _text(request_meta.get("runtime_backend_id")),
        "profile_id": _text(runtime.get("profile_id")) or _text(error_details.get("profile_id")),
        "adapter_id": _text(adapter.get("adapter_id")) or _text(runtime.get("adapter_id")) or _text(error_details.get("adapter_id")),
        "runtime_family": _text(adapter.get("runtime_family")) or _text(runtime.get("runtime_family")),
        "model": _text(adapter.get("model")) or _text(runtime.get("model")),
        "harness_id": _text(profile_meta.get("harness_id")) or _text(runtime.get("harness_id")),
        "prompt_tokens": _optional_int(adapter.get("prompt_tokens")),
        "completion_tokens": _optional_int(adapter.get("completion_tokens")),
        "total_tokens": _optional_int(adapter.get("total_tokens")),
        "context_window": _optional_int(adapter.get("context_window")),
        "context_utilization": _optional_float(adapter.get("context_utilization")),
        "http_elapsed_ms": _optional_float(adapter.get("http_elapsed_ms")),
        "role_elapsed_ms": _optional_float(runtime.get(elapsed_key)) if elapsed_key else None,
        "model_load_ms": _optional_float(adapter.get("model_load_ms")),
        "model_unload_ms": _optional_float(adapter.get("model_unload_ms")),
        "tool_calls": _optional_int(adapter.get("tool_calls")),
        "turns": _optional_int(adapter.get("turns")),
        "request_bytes": _optional_int(adapter.get("request_bytes")),
        "response_bytes": _optional_int(adapter.get("response_bytes")),
        "finish_reason": _text(adapter.get("finish_reason")),
        "error_code": error_code,
        "error_message": error_message,
        "runtime_metadata": runtime,
    }


class RoleTelemetryService:
    component = "controller.role.telemetry"

    def __init__(self, *, config: RoleTelemetryConfig, store: JsonRoleTelemetryStore) -> None:
        self.config = config
        self.store = store

    def record_safely(
        self,
        *,
        workflow_id: str,
        role: str,
        mode: str,
        request_metadata: Mapping[str, Any] | None = None,
        runtime_metadata: Mapping[str, Any] | None = None,
        success: bool,
        outcome: str | None = None,
        correction_attempt: int | None = None,
        run_id: str | None = None,
        error: BaseException | None = None,
        elapsed_key: str | None = None,
    ) -> RoleTelemetryRecord | None:
        if not self.config.enabled:
            return None
        try:
            extracted = extract_runtime_telemetry(
                runtime_metadata=runtime_metadata,
                request_metadata=request_metadata,
                error=error,
                elapsed_key=elapsed_key,
            )
            record = RoleTelemetryRecord(
                telemetry_id=CoreIdentity.new("roletelemetry").value,
                workflow_id=workflow_id,
                role=role,
                mode=mode,
                success=success,
                outcome=outcome,
                correction_attempt=correction_attempt,
                run_id=run_id,
                **extracted,
            )
            self.store.save(record)
            emit(
                "INFO" if success else "ERROR",
                self.component,
                "record",
                "role_telemetry_recorded",
                telemetry_id=record.telemetry_id,
                workflow_id=workflow_id,
                role=role,
                mode=mode,
                success=success,
                outcome=outcome,
                model=record.model,
                harness_id=record.harness_id,
                tool_calls=record.tool_calls,
                turns=record.turns,
                total_tokens=record.total_tokens,
                error_code=record.error_code,
            )
            return record
        except Exception as exc:
            emit(
                "ERROR",
                self.component,
                "record_safely",
                "role_telemetry_internal_error",
                workflow_id=workflow_id,
                role=role,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )
            return None

    def records(self, workflow_id: str, *, role: str | None = None) -> tuple[RoleTelemetryRecord, ...]:
        if not self.config.enabled:
            return ()
        return self.store.for_workflow(workflow_id, role=role)

    def summary_safely(self, workflow_id: str, *, role: str | None = None) -> dict[str, Any]:
        try:
            records = self.records(workflow_id, role=role)
            return {
                "telemetry_enabled": self.config.enabled,
                "workflow_id": workflow_id,
                "role": role,
                "invocations": len(records),
                "successful_invocations": sum(1 for item in records if item.success),
                "failed_invocations": sum(1 for item in records if not item.success),
                "correction_invocations": sum(1 for item in records if item.correction_attempt),
                "prompt_tokens": _sum_optional(item.prompt_tokens for item in records),
                "completion_tokens": _sum_optional(item.completion_tokens for item in records),
                "total_tokens": _sum_optional(item.total_tokens for item in records),
                "tool_calls": _sum_optional(item.tool_calls for item in records),
                "turns": _sum_optional(item.turns for item in records),
                "role_elapsed_ms": _sum_optional_float(item.role_elapsed_ms for item in records),
                "http_elapsed_ms": _sum_optional_float(item.http_elapsed_ms for item in records),
                "models": sorted({item.model for item in records if item.model}),
                "harnesses": sorted({item.harness_id for item in records if item.harness_id}),
                "adapters": sorted({item.adapter_id for item in records if item.adapter_id}),
            }
        except Exception as exc:
            return {
                "telemetry_enabled": self.config.enabled,
                "workflow_id": workflow_id,
                "role": role,
                "summary_available": False,
                "error": {"exception_type": type(exc).__name__, "message": str(exc)},
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


def _sum_optional(values) -> int | None:
    observed = [value for value in values if value is not None]
    return None if not observed else sum(observed)


def _sum_optional_float(values) -> float | None:
    observed = [value for value in values if value is not None]
    return None if not observed else round(sum(observed), 3)
