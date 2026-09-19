"""Shared AI-role diagnostics.

Main diagnostic records contain identity, digests, sizes, statuses, and failure
information. Raw role input/output is stored only when deep-debug artifacts are
explicitly enabled.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from acl_core.canonical import canonical_digest, canonical_json
from acl_core.diagnostics import emit

from .request import RoleRequest
from .response import RoleResponse


@dataclass(frozen=True)
class RoleDiagnosticConfig:
    raw_artifacts_enabled: bool = False
    raw_artifact_root: Path | None = None


_lock = RLock()
_config = RoleDiagnosticConfig(
    raw_artifacts_enabled=os.getenv("ACL_ROLE_DEBUG_ARTIFACTS", "").strip().lower()
    in {"1", "true", "yes", "on"},
    raw_artifact_root=(
        Path(os.environ["ACL_ROLE_DEBUG_PATH"]).expanduser()
        if os.getenv("ACL_ROLE_DEBUG_PATH")
        else None
    ),
)


class RoleDiagnostics:
    component = "roles"

    @classmethod
    def configure_raw_artifacts(
        cls,
        *,
        enabled: bool,
        root: Path | None = None,
    ) -> None:
        global _config
        _config = RoleDiagnosticConfig(
            raw_artifacts_enabled=bool(enabled),
            raw_artifact_root=None if root is None else Path(root).expanduser(),
        )

    @classmethod
    def invocation(
        cls,
        request: RoleRequest,
        *,
        adapter_id: str | None = None,
    ) -> None:
        value = request.to_dict(include_instruction_content=False)
        raw_value = request.to_dict(include_instruction_content=True)
        emit(
            "INFO",
            cls.component,
            "invoke",
            "role_invocation",
            workflow_id=request.workflow_id,
            attempt_id=request.attempt_id,
            role=request.role,
            profile_id=request.profile_id,
            adapter_id=adapter_id,
            authority_grant_id=request.authority_grant_id,
            instruction_set_id=(
                None if request.instructions is None else request.instructions.instruction_set_id
            ),
            instruction_digest=(
                None if request.instructions is None else request.instructions.digest()
            ),
            context_digest=request.context.digest(),
            context_reference_count=len(request.context.references),
            tool_ids=list(request.tool_ids),
            request_digest=canonical_digest(raw_value),
            request_bytes=len(canonical_json(raw_value).encode("utf-8")),
            objective_bytes=len(canonical_json(dict(request.objective)).encode("utf-8")),
            context_bytes=len(canonical_json(request.context.to_dict()).encode("utf-8")),
            execution=value.get("execution"),
        )
        cls._write_raw(
            request.workflow_id,
            request.attempt_id,
            "request",
            raw_value,
        )

    @classmethod
    def response(
        cls,
        request: RoleRequest,
        response: RoleResponse,
        *,
        adapter_id: str | None = None,
        normalization: Mapping[str, Any] | None = None,
    ) -> None:
        value = response.to_dict()
        adapter_telemetry = response.metadata.get("adapter_telemetry")
        adapter_telemetry = (
            dict(adapter_telemetry)
            if isinstance(adapter_telemetry, Mapping)
            else {}
        )
        emit(
            "INFO",
            cls.component,
            "response",
            "role_response",
            workflow_id=request.workflow_id,
            attempt_id=request.attempt_id,
            role=request.role,
            profile_id=request.profile_id,
            adapter_id=adapter_id,
            status=str(response.status),
            response_digest=response.digest(),
            response_bytes=len(canonical_json(value).encode("utf-8")),
            reference=response.reference,
            normalization=dict(normalization or {}),
            model=adapter_telemetry.get("model"),
            prompt_tokens=adapter_telemetry.get("prompt_tokens"),
            completion_tokens=adapter_telemetry.get("completion_tokens"),
            total_tokens=adapter_telemetry.get("total_tokens"),
            context_window=adapter_telemetry.get("context_window"),
            context_utilization=adapter_telemetry.get("context_utilization"),
            http_elapsed_ms=adapter_telemetry.get("http_elapsed_ms"),
            finish_reason=adapter_telemetry.get("finish_reason"),
        )
        cls._write_raw(
            request.workflow_id,
            request.attempt_id,
            "response",
            value,
        )

    @classmethod
    def parse_error(
        cls,
        *,
        workflow_id: str,
        attempt_id: str,
        role: str,
        profile_id: str,
        adapter_id: str | None,
        raw_response: Any,
        error: BaseException,
    ) -> None:
        raw_digest, raw_bytes = cls._safe_digest_and_size(raw_response)
        emit(
            "ERROR",
            cls.component,
            "parse_response",
            "role_response_parse_error",
            workflow_id=workflow_id,
            attempt_id=attempt_id,
            role=role,
            profile_id=profile_id,
            adapter_id=adapter_id,
            raw_response_digest=raw_digest,
            raw_response_bytes=raw_bytes,
            exception_type=type(error).__name__,
            exception_message=str(error),
        )
        cls._write_raw(
            workflow_id,
            attempt_id,
            "parse-error-response",
            raw_response,
        )

    @classmethod
    def adapter_error(
        cls,
        request: RoleRequest,
        *,
        adapter_id: str | None,
        error: Any,
    ) -> None:
        error_digest, error_bytes = cls._safe_digest_and_size(error)
        emit(
            "ERROR",
            cls.component,
            "adapter",
            "role_adapter_error",
            workflow_id=request.workflow_id,
            attempt_id=request.attempt_id,
            role=request.role,
            profile_id=request.profile_id,
            adapter_id=adapter_id,
            error_digest=error_digest,
            error_bytes=error_bytes,
        )
        cls._write_raw(
            request.workflow_id,
            request.attempt_id,
            "adapter-error",
            error,
        )

    @classmethod
    def _safe_digest_and_size(cls, value: Any) -> tuple[str | None, int | None]:
        try:
            raw = canonical_json(value)
            return canonical_digest(value), len(raw.encode("utf-8"))
        except Exception:
            try:
                raw = repr(value)
                return None, len(raw.encode("utf-8"))
            except Exception:
                return None, None

    @classmethod
    def _write_raw(
        cls,
        workflow_id: str,
        attempt_id: str,
        kind: str,
        value: Any,
    ) -> None:
        cfg = _config
        if not cfg.raw_artifacts_enabled or cfg.raw_artifact_root is None:
            return
        try:
            root = cfg.raw_artifact_root.expanduser().resolve()
            safe_workflow = workflow_id.replace(":", "_")
            safe_attempt = attempt_id.replace(":", "_")
            path = root / safe_workflow / safe_attempt / f"{kind}.json"
            with _lock:
                path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    raw = canonical_json(value) + "\n"
                except Exception:
                    raw = json.dumps({"repr": repr(value)}, ensure_ascii=False) + "\n"
                path.write_text(raw, encoding="utf-8")
        except Exception:
            # Deep diagnostics must never affect execution.
            return
