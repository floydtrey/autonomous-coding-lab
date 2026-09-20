"""Serial runtime residency and durable role-recovery checkpoints.

ACL distinguishes the model physically resident on the inference service from
the execution target a nonterminal workflow must return to after interruption.

Fresh role invocations resolve their target from external profile/environment
configuration. Recovery uses the persisted resolved target that actually began
the interrupted attempt, so a configuration edit or cold-start bootstrap cannot
silently replace an in-flight model.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
import json
import os
from pathlib import Path
import subprocess
from threading import RLock
import time
from typing import Any, Mapping
from urllib import error as urlerror
from urllib import request as urlrequest

from acl_core.canonical import canonical_digest, canonical_json
from acl_core.diagnostics import emit

from ..configuration import RoleProfile
from ..errors import ControllerError
from ..models import utc_now


RUNTIME_RESIDENCY_CONFIG_SCHEMA = "acl-runtime-residency:v1"
RUNTIME_CHECKPOINT_SCHEMA = "acl-runtime-checkpoint:v1"


class RuntimeCheckpointState(StrEnum):
    PREPARING = "PREPARING"
    ACTIVE = "ACTIVE"
    RESPONSE_RECEIVED = "RESPONSE_RECEIVED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    PAUSED_FOR_SWITCH = "PAUSED_FOR_SWITCH"
    RETURN_REQUIRED = "RETURN_REQUIRED"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class RuntimeResidencyConfig:
    enabled: bool = True
    mode: str = "serial"
    base_url_env: str = "ACL_OPENAI_COMPAT_BASE_URL"
    models_path: str = "/models"
    api_key_file_env: str | None = "ACL_OPENAI_COMPAT_API_KEY_FILE"
    probe_timeout_seconds: float = 3.0
    switch_timeout_seconds: float = 300.0
    poll_interval_seconds: float = 0.5

    @classmethod
    def load(cls, path: str | Path) -> "RuntimeResidencyConfig":
        path = Path(path).expanduser().resolve()
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            emit(
                "DEBUG",
                "controller.runtime_residency",
                "load_config",
                "runtime_residency_config_absent",
                path=str(path),
            )
            return cls(enabled=False)
        except (OSError, json.JSONDecodeError) as exc:
            raise ControllerError(
                "CONTROLLER_RUNTIME_RESIDENCY_CONFIG_INVALID",
                "runtime residency configuration cannot be read",
                {"path": str(path)},
            ) from exc
        if (
            not isinstance(value, Mapping)
            or value.get("schema_version") != RUNTIME_RESIDENCY_CONFIG_SCHEMA
        ):
            raise ControllerError(
                "CONTROLLER_RUNTIME_RESIDENCY_CONFIG_INVALID",
                "runtime residency configuration schema is invalid",
                {"path": str(path)},
            )
        enabled = value.get("enabled", True)
        mode = value.get("mode", "serial")
        base_url_env = value.get("base_url_env", "ACL_OPENAI_COMPAT_BASE_URL")
        models_path = value.get("models_path", "/models")
        api_key_file_env = value.get(
            "api_key_file_env",
            "ACL_OPENAI_COMPAT_API_KEY_FILE",
        )
        probe = value.get("probe_timeout_seconds", 3)
        switch = value.get("switch_timeout_seconds", 300)
        poll = value.get("poll_interval_seconds", 0.5)
        if not isinstance(enabled, bool):
            raise ControllerError(
                "CONTROLLER_RUNTIME_RESIDENCY_CONFIG_INVALID",
                "enabled must be boolean",
            )
        if mode != "serial":
            raise ControllerError(
                "CONTROLLER_RUNTIME_RESIDENCY_CONFIG_INVALID",
                "Planner V1 supports only serial runtime residency",
                {"mode": mode},
            )
        if (
            not isinstance(base_url_env, str)
            or not base_url_env.strip()
            or not isinstance(models_path, str)
            or not models_path.startswith("/")
        ):
            raise ControllerError(
                "CONTROLLER_RUNTIME_RESIDENCY_CONFIG_INVALID",
                "base_url_env/models_path are invalid",
            )
        if api_key_file_env is not None and (
            not isinstance(api_key_file_env, str) or not api_key_file_env.strip()
        ):
            raise ControllerError(
                "CONTROLLER_RUNTIME_RESIDENCY_CONFIG_INVALID",
                "api_key_file_env must be text when configured",
            )
        for number, label in (
            (probe, "probe_timeout_seconds"),
            (switch, "switch_timeout_seconds"),
            (poll, "poll_interval_seconds"),
        ):
            if (
                isinstance(number, bool)
                or not isinstance(number, (int, float))
                or number <= 0
            ):
                raise ControllerError(
                    "CONTROLLER_RUNTIME_RESIDENCY_CONFIG_INVALID",
                    f"{label} must be positive",
                )
        return cls(
            enabled=enabled,
            mode=mode,
            base_url_env=base_url_env.strip(),
            models_path=models_path,
            api_key_file_env=(
                None if api_key_file_env is None else api_key_file_env.strip()
            ),
            probe_timeout_seconds=float(probe),
            switch_timeout_seconds=float(switch),
            poll_interval_seconds=float(poll),
        )


@dataclass(frozen=True)
class RuntimeTarget:
    role: str
    profile_id: str
    adapter_id: str
    model: str
    harness_id: str | None
    base_url: str
    launcher_command: tuple[str, ...] = ()
    launcher_cwd: str | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.role, "role"),
            (self.profile_id, "profile_id"),
            (self.adapter_id, "adapter_id"),
            (self.model, "model"),
            (self.base_url, "base_url"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ControllerError(
                    "CONTROLLER_RUNTIME_TARGET_INVALID",
                    f"{label} is required",
                )
        if self.harness_id is not None and (
            not isinstance(self.harness_id, str) or not self.harness_id.strip()
        ):
            raise ControllerError(
                "CONTROLLER_RUNTIME_TARGET_INVALID",
                "harness_id must be text when present",
            )
        if not isinstance(self.launcher_command, tuple) or any(
            not isinstance(item, str) or not item.strip()
            for item in self.launcher_command
        ):
            raise ControllerError(
                "CONTROLLER_RUNTIME_TARGET_INVALID",
                "launcher_command must contain nonblank text values",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "profile_id": self.profile_id,
            "adapter_id": self.adapter_id,
            "model": self.model,
            "harness_id": self.harness_id,
            "base_url": self.base_url,
            "launcher_command": list(self.launcher_command),
            "launcher_cwd": self.launcher_cwd,
            "runtime_digest": self.digest(),
        }

    def digest(self) -> str:
        return canonical_digest({
            "role": self.role,
            "profile_id": self.profile_id,
            "adapter_id": self.adapter_id,
            "model": self.model,
            "harness_id": self.harness_id,
            "base_url": self.base_url,
            "launcher_command": list(self.launcher_command),
            "launcher_cwd": self.launcher_cwd,
        })

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RuntimeTarget":
        if not isinstance(value, Mapping):
            raise ControllerError(
                "CONTROLLER_RUNTIME_TARGET_INVALID",
                "runtime target must be a mapping",
            )
        command = value.get("launcher_command", [])
        if not isinstance(command, list):
            raise ControllerError(
                "CONTROLLER_RUNTIME_TARGET_INVALID",
                "launcher_command must be a list",
            )
        return cls(
            role=value.get("role"),
            profile_id=value.get("profile_id"),
            adapter_id=value.get("adapter_id"),
            model=value.get("model"),
            harness_id=value.get("harness_id"),
            base_url=value.get("base_url"),
            launcher_command=tuple(command),
            launcher_cwd=value.get("launcher_cwd"),
        )


@dataclass(frozen=True)
class RuntimeCheckpoint:
    workflow_id: str
    attempt_id: str
    state: RuntimeCheckpointState
    target: RuntimeTarget
    return_target: RuntimeTarget | None = None
    return_attempt_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RUNTIME_CHECKPOINT_SCHEMA,
            "workflow_id": self.workflow_id,
            "attempt_id": self.attempt_id,
            "state": str(self.state),
            "target": self.target.to_dict(),
            "return_target": (
                None if self.return_target is None else self.return_target.to_dict()
            ),
            "return_attempt_id": self.return_attempt_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RuntimeCheckpoint":
        if (
            not isinstance(value, Mapping)
            or value.get("schema_version") != RUNTIME_CHECKPOINT_SCHEMA
        ):
            raise ControllerError(
                "CONTROLLER_RUNTIME_CHECKPOINT_INVALID",
                "runtime checkpoint schema is invalid",
            )
        try:
            return cls(
                workflow_id=value["workflow_id"],
                attempt_id=value["attempt_id"],
                state=RuntimeCheckpointState(value["state"]),
                target=RuntimeTarget.from_mapping(value["target"]),
                return_target=(
                    None
                    if value.get("return_target") is None
                    else RuntimeTarget.from_mapping(value["return_target"])
                ),
                return_attempt_id=value.get("return_attempt_id"),
                created_at=value["created_at"],
                updated_at=value["updated_at"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError(
                "CONTROLLER_RUNTIME_CHECKPOINT_INVALID",
                "runtime checkpoint is malformed",
            ) from exc


@dataclass(frozen=True)
class RuntimeLease:
    checkpoint: RuntimeCheckpoint
    execution_overrides: Mapping[str, Any]


class JsonRuntimeCheckpointStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def read(self, workflow_id: str) -> RuntimeCheckpoint | None:
        path = self._path(workflow_id)
        if not path.exists():
            return None
        try:
            return RuntimeCheckpoint.from_mapping(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ControllerError(
                "CONTROLLER_RUNTIME_CHECKPOINT_READ_FAILED",
                "runtime checkpoint could not be read",
                {"workflow_id": workflow_id},
            ) from exc

    def save(self, record: RuntimeCheckpoint) -> RuntimeCheckpoint:
        path = self._path(record.workflow_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        with self._lock:
            try:
                temp.write_text(
                    canonical_json(record.to_dict()) + "\n",
                    encoding="utf-8",
                )
                os.replace(temp, path)
            except OSError as exc:
                try:
                    temp.unlink(missing_ok=True)
                except OSError:
                    pass
                raise ControllerError(
                    "CONTROLLER_RUNTIME_CHECKPOINT_WRITE_FAILED",
                    "runtime checkpoint could not be persisted",
                    {"workflow_id": record.workflow_id},
                ) from exc
        return record

    def _path(self, workflow_id: str) -> Path:
        if not isinstance(workflow_id, str) or not workflow_id.startswith("workflow:"):
            raise ControllerError(
                "CONTROLLER_RUNTIME_CHECKPOINT_INVALID",
                "workflow_id is invalid",
            )
        return (
            self.root
            / "runtime-checkpoints"
            / f"{workflow_id.replace(':', '_')}.json"
        )


class SerialRuntimeResidencyService:
    component = "controller.runtime_residency"

    def __init__(
        self,
        *,
        config: RuntimeResidencyConfig,
        store: JsonRuntimeCheckpointStore,
    ) -> None:
        self.config = config
        self.store = store

    def prepare_role(
        self,
        *,
        workflow_id: str,
        attempt_id: str,
        role: str,
        profile: RoleProfile,
    ) -> RuntimeLease:
        if not self.config.enabled:
            target = self._resolve_target(role, profile)
            return RuntimeLease(
                checkpoint=RuntimeCheckpoint(
                    workflow_id=workflow_id,
                    attempt_id=attempt_id,
                    state=RuntimeCheckpointState.ACTIVE,
                    target=target,
                ),
                execution_overrides={"model": target.model},
            )

        current = self.store.read(workflow_id)
        if current is not None and current.state in {
            RuntimeCheckpointState.PREPARING,
            RuntimeCheckpointState.ACTIVE,
            RuntimeCheckpointState.RESPONSE_RECEIVED,
            RuntimeCheckpointState.RECOVERY_REQUIRED,
            RuntimeCheckpointState.RETURN_REQUIRED,
        }:
            self._require_same_recovery_target(
                current.target,
                role=role,
                profile=profile,
            )
            target = current.target
            self._ensure_target(target)
            checkpoint = RuntimeCheckpoint(
                workflow_id=workflow_id,
                attempt_id=attempt_id,
                state=RuntimeCheckpointState.ACTIVE,
                target=target,
                return_target=current.return_target,
                return_attempt_id=current.return_attempt_id,
                created_at=current.created_at,
                updated_at=utc_now(),
            )
            self.store.save(checkpoint)
            emit(
                "INFO",
                self.component,
                "prepare_role",
                "runtime_inflight_target_restored",
                workflow_id=workflow_id,
                prior_attempt_id=current.attempt_id,
                attempt_id=attempt_id,
                role=target.role,
                profile_id=target.profile_id,
                model=target.model,
            )
            return RuntimeLease(
                checkpoint=checkpoint,
                execution_overrides={"model": target.model},
            )

        target = self._resolve_target(role, profile)
        switching = (
            current is not None
            and current.state is RuntimeCheckpointState.PAUSED_FOR_SWITCH
        )
        checkpoint = RuntimeCheckpoint(
            workflow_id=workflow_id,
            attempt_id=attempt_id,
            state=RuntimeCheckpointState.PREPARING,
            target=target,
            return_target=(
                current.target
                if switching
                else (
                    None
                    if current is None or current.state is RuntimeCheckpointState.COMPLETE
                    else current.return_target
                )
            ),
            return_attempt_id=(
                current.attempt_id
                if switching
                else (
                    None
                    if current is None or current.state is RuntimeCheckpointState.COMPLETE
                    else current.return_attempt_id
                )
            ),
            created_at=(
                utc_now()
                if current is None or current.state is RuntimeCheckpointState.COMPLETE
                else current.created_at
            ),
            updated_at=utc_now(),
        )
        self.store.save(checkpoint)
        self._ensure_target(target)
        checkpoint = replace(
            checkpoint,
            state=RuntimeCheckpointState.ACTIVE,
            updated_at=utc_now(),
        )
        self.store.save(checkpoint)
        emit(
            "INFO",
            self.component,
            "prepare_role",
            "runtime_target_prepared",
            workflow_id=workflow_id,
            attempt_id=attempt_id,
            role=role,
            profile_id=profile.profile_id,
            model=target.model,
            resident_models=list(self._probe_models(target.base_url)),
        )
        return RuntimeLease(
            checkpoint=checkpoint,
            execution_overrides={"model": target.model},
        )

    def response_received(self, workflow_id: str, attempt_id: str) -> None:
        current = self.store.read(workflow_id)
        if current is None or current.attempt_id != attempt_id:
            return
        self.store.save(
            replace(
                current,
                state=RuntimeCheckpointState.RESPONSE_RECEIVED,
                updated_at=utc_now(),
            )
        )

    def complete_role(self, workflow_id: str, attempt_id: str) -> None:
        current = self.store.read(workflow_id)
        if current is None or current.attempt_id != attempt_id:
            return
        if current.return_target is not None:
            restored = RuntimeCheckpoint(
                workflow_id=workflow_id,
                attempt_id=current.return_attempt_id or current.attempt_id,
                state=RuntimeCheckpointState.RETURN_REQUIRED,
                target=current.return_target,
                return_target=None,
                return_attempt_id=None,
                created_at=current.created_at,
                updated_at=utc_now(),
            )
            self.store.save(restored)
            emit(
                "INFO",
                self.component,
                "complete_role",
                "runtime_return_target_required",
                workflow_id=workflow_id,
                model=restored.target.model,
                role=restored.target.role,
                profile_id=restored.target.profile_id,
            )
            return
        self.store.save(
            replace(
                current,
                state=RuntimeCheckpointState.COMPLETE,
                updated_at=utc_now(),
            )
        )

    def pause_for_role_switch(
        self,
        workflow_id: str,
        *,
        attempt_id: str,
    ) -> RuntimeCheckpoint:
        """Persist the exact role/model that must be restored after a temporary switch."""
        current = self.store.read(workflow_id)
        if current is None or current.attempt_id != attempt_id:
            raise ControllerError(
                "CONTROLLER_RUNTIME_SWITCH_TARGET_MISSING",
                "cannot pause runtime because the active checkpoint does not match",
                {
                    "workflow_id": workflow_id,
                    "attempt_id": attempt_id,
                    "checkpoint_attempt_id": (
                        None if current is None else current.attempt_id
                    ),
                },
            )
        if current.state not in {
            RuntimeCheckpointState.ACTIVE,
            RuntimeCheckpointState.RESPONSE_RECEIVED,
        }:
            raise ControllerError(
                "CONTROLLER_RUNTIME_SWITCH_STATE_INVALID",
                "runtime checkpoint is not in a switchable state",
                {
                    "workflow_id": workflow_id,
                    "state": str(current.state),
                },
            )
        paused = replace(
            current,
            state=RuntimeCheckpointState.PAUSED_FOR_SWITCH,
            updated_at=utc_now(),
        )
        self.store.save(paused)
        emit(
            "INFO",
            self.component,
            "pause_for_role_switch",
            "runtime_return_target_persisted",
            workflow_id=workflow_id,
            attempt_id=attempt_id,
            role=current.target.role,
            profile_id=current.target.profile_id,
            model=current.target.model,
        )
        return paused

    def mark_recovery_required(
        self,
        workflow_id: str,
        *,
        attempt_id: str | None = None,
    ) -> RuntimeCheckpoint | None:
        current = self.store.read(workflow_id)
        if current is None:
            return None
        if attempt_id is not None and current.attempt_id != attempt_id:
            raise ControllerError(
                "CONTROLLER_RUNTIME_RECOVERY_TARGET_MISMATCH",
                "workflow recovery attempt does not match runtime checkpoint",
                {
                    "workflow_id": workflow_id,
                    "workflow_attempt_id": attempt_id,
                    "checkpoint_attempt_id": current.attempt_id,
                },
            )
        updated = replace(
            current,
            state=RuntimeCheckpointState.RECOVERY_REQUIRED,
            updated_at=utc_now(),
        )
        self.store.save(updated)
        return updated

    def ensure_recovery_target(
        self,
        *,
        workflow_id: str,
        attempt_id: str,
        role: str,
        profile: RoleProfile,
    ) -> RuntimeCheckpoint | None:
        current = self.store.read(workflow_id)
        if current is None:
            return None
        if current.attempt_id != attempt_id:
            raise ControllerError(
                "CONTROLLER_RUNTIME_RECOVERY_TARGET_MISMATCH",
                "active workflow attempt differs from runtime checkpoint",
                {
                    "workflow_id": workflow_id,
                    "workflow_attempt_id": attempt_id,
                    "checkpoint_attempt_id": current.attempt_id,
                },
            )
        self._require_same_recovery_target(
            current.target,
            role=role,
            profile=profile,
        )
        self._ensure_target(current.target)
        return current

    def checkpoint(self, workflow_id: str) -> RuntimeCheckpoint | None:
        return self.store.read(workflow_id)

    def _require_same_recovery_target(
        self,
        target: RuntimeTarget,
        *,
        role: str,
        profile: RoleProfile,
    ) -> None:
        if (
            target.role != role
            or target.profile_id != profile.profile_id
            or target.adapter_id != profile.adapter_id
        ):
            raise ControllerError(
                "CONTROLLER_RUNTIME_RECOVERY_TARGET_MISMATCH",
                "current configuration does not match the persisted in-flight runtime identity",
                {
                    "persisted": target.to_dict(),
                    "requested_role": role,
                    "requested_profile_id": profile.profile_id,
                    "requested_adapter_id": profile.adapter_id,
                },
            )

    def _resolve_target(self, role: str, profile: RoleProfile) -> RuntimeTarget:
        settings = dict(profile.settings)
        model = settings.get("model")
        if not isinstance(model, str) or not model.strip():
            model_env = settings.get("model_env")
            if isinstance(model_env, str) and model_env.strip():
                model = os.getenv(model_env.strip())
        if not isinstance(model, str) or not model.strip():
            raise ControllerError(
                "CONTROLLER_RUNTIME_MODEL_UNRESOLVED",
                "profile model is not configured",
                {
                    "role": role,
                    "profile_id": profile.profile_id,
                    "model_env": settings.get("model_env"),
                },
            )

        base_url = settings.get("base_url")
        base_url_env = settings.get("base_url_env")
        if not isinstance(base_url, str) or not base_url.strip():
            if not isinstance(base_url_env, str) or not base_url_env.strip():
                base_url_env = self.config.base_url_env
            base_url = os.getenv(base_url_env.strip())
        if not isinstance(base_url, str) or not base_url.strip():
            raise ControllerError(
                "CONTROLLER_RUNTIME_BASE_URL_MISSING",
                "runtime base URL is not configured",
                {"env": base_url_env},
            )

        launcher_command = self._resolve_launcher_command(settings)
        launcher_cwd = self._resolve_launcher_cwd(settings)
        harness_id = profile.metadata.get("harness_id")
        if not isinstance(harness_id, str) or not harness_id.strip():
            harness_id = None
        return RuntimeTarget(
            role=role,
            profile_id=profile.profile_id,
            adapter_id=profile.adapter_id,
            model=model.strip(),
            harness_id=harness_id,
            base_url=base_url.strip().rstrip("/"),
            launcher_command=launcher_command,
            launcher_cwd=launcher_cwd,
        )

    def _ensure_target(self, target: RuntimeTarget) -> None:
        loaded = self._probe_models(target.base_url)
        if target.model in loaded:
            return

        if not target.launcher_command:
            raise ControllerError(
                "CONTROLLER_RUNTIME_MODEL_MISMATCH",
                "inference service is not serving the required runtime model and no profile launcher is configured",
                {
                    "required_model": target.model,
                    "observed_models": list(loaded),
                    "profile_id": target.profile_id,
                    "role": target.role,
                    "base_url": target.base_url,
                },
            )

        emit(
            "INFO",
            self.component,
            "ensure_target",
            "runtime_model_switch_requested",
            role=target.role,
            profile_id=target.profile_id,
            required_model=target.model,
            observed_models=list(loaded),
            launcher_command=self._redacted_command(target.launcher_command),
            launcher_cwd=target.launcher_cwd,
        )
        try:
            process = subprocess.Popen(
                list(target.launcher_command),
                cwd=target.launcher_cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(
                    (
                        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    )
                    if os.name == "nt"
                    else 0
                ),
                **({"start_new_session": True} if os.name != "nt" else {}),
            )
        except OSError as exc:
            raise ControllerError(
                "CONTROLLER_RUNTIME_MODEL_LAUNCH_FAILED",
                "configured model launcher could not be started",
                {
                    "profile_id": target.profile_id,
                    "required_model": target.model,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
            ) from exc

        started_waiting = time.monotonic()
        deadline = started_waiting + self.config.switch_timeout_seconds
        next_progress = started_waiting
        last_loaded = loaded
        while time.monotonic() < deadline:
            now = time.monotonic()
            last_loaded = self._probe_models(target.base_url)
            if now >= next_progress:
                emit(
                    "INFO",
                    self.component,
                    "ensure_target",
                    "runtime_model_waiting",
                    profile_id=target.profile_id,
                    required_model=target.model,
                    observed_models=list(last_loaded),
                    elapsed_seconds=round(now - started_waiting, 1),
                    timeout_seconds=self.config.switch_timeout_seconds,
                )
                next_progress = now + 10.0
            if target.model in last_loaded:
                emit(
                    "INFO",
                    self.component,
                    "ensure_target",
                    "runtime_model_ready",
                    profile_id=target.profile_id,
                    required_model=target.model,
                    launcher_pid=process.pid,
                )
                return
            time.sleep(self.config.poll_interval_seconds)

        raise ControllerError(
            "CONTROLLER_RUNTIME_MODEL_SWITCH_TIMEOUT",
            "configured launcher did not make the required model resident before timeout",
            {
                "profile_id": target.profile_id,
                "required_model": target.model,
                "observed_models": list(last_loaded),
                "launcher_pid": process.pid,
            },
        )

    def _probe_models(self, base_url: str) -> tuple[str, ...]:
        url = base_url.rstrip("/") + self.config.models_path
        headers: dict[str, str] = {}
        api_key = self._read_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urlrequest.Request(url, headers=headers, method="GET")
        try:
            with urlrequest.urlopen(
                request,
                timeout=self.config.probe_timeout_seconds,
            ) as response:
                raw = response.read()
        except (urlerror.URLError, urlerror.HTTPError, TimeoutError, OSError):
            return ()
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ()
        data = value.get("data") if isinstance(value, Mapping) else None
        if not isinstance(data, list):
            return ()
        models: list[str] = []
        for item in data:
            if isinstance(item, Mapping):
                model_id = item.get("id")
                if isinstance(model_id, str) and model_id.strip():
                    models.append(model_id.strip())
        return tuple(dict.fromkeys(models))

    def _resolve_launcher_command(
        self,
        settings: Mapping[str, Any],
    ) -> tuple[str, ...]:
        raw_command_env = settings.get("runtime_launcher_command_json_env")
        if isinstance(raw_command_env, str) and raw_command_env.strip():
            raw = os.getenv(raw_command_env.strip())
            if raw:
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ControllerError(
                        "CONTROLLER_RUNTIME_LAUNCHER_INVALID",
                        "runtime launcher command environment value must be a JSON array",
                        {"env": raw_command_env},
                    ) from exc
                if (
                    not isinstance(value, list)
                    or not value
                    or any(not isinstance(item, str) or not item.strip() for item in value)
                ):
                    raise ControllerError(
                        "CONTROLLER_RUNTIME_LAUNCHER_INVALID",
                        "runtime launcher command must be a nonempty JSON array of strings",
                        {"env": raw_command_env},
                    )
                return tuple(os.path.expandvars(item) for item in value)

        launcher_env = settings.get("runtime_launcher_env")
        if not isinstance(launcher_env, str) or not launcher_env.strip():
            return ()
        raw = os.getenv(launcher_env.strip())
        if not raw or not raw.strip():
            return ()
        launcher = Path(os.path.expandvars(raw.strip())).expanduser().resolve()
        if not launcher.exists():
            raise ControllerError(
                "CONTROLLER_RUNTIME_LAUNCHER_INVALID",
                "configured runtime launcher does not exist",
                {
                    "env": launcher_env,
                    "launcher": str(launcher),
                },
            )
        suffix = launcher.suffix.lower()
        if os.name == "nt" and suffix in {".bat", ".cmd"}:
            return ("cmd.exe", "/d", "/c", str(launcher))
        if os.name == "nt" and suffix == ".ps1":
            return (
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(launcher),
            )
        return (str(launcher),)

    @staticmethod
    def _resolve_launcher_cwd(settings: Mapping[str, Any]) -> str | None:
        cwd = settings.get("runtime_launcher_cwd")
        cwd_env = settings.get("runtime_launcher_cwd_env")
        if isinstance(cwd_env, str) and cwd_env.strip():
            env_value = os.getenv(cwd_env.strip())
            if env_value:
                cwd = env_value
        if cwd is None:
            return None
        if not isinstance(cwd, str) or not cwd.strip():
            raise ControllerError(
                "CONTROLLER_RUNTIME_LAUNCHER_INVALID",
                "runtime launcher cwd must be nonblank text",
            )
        path = Path(os.path.expandvars(cwd.strip())).expanduser().resolve()
        if not path.is_dir():
            raise ControllerError(
                "CONTROLLER_RUNTIME_LAUNCHER_INVALID",
                "runtime launcher cwd does not exist",
                {"cwd": str(path)},
            )
        return str(path)

    def _read_api_key(self) -> str | None:
        env_name = self.config.api_key_file_env
        if env_name is None:
            return None
        raw_path = os.getenv(env_name)
        if not raw_path or not raw_path.strip():
            return None
        try:
            value = Path(raw_path.strip()).expanduser().read_text(
                encoding="utf-8"
            ).strip()
        except OSError:
            return None
        return value or None

    @staticmethod
    def _redacted_command(command: tuple[str, ...]) -> list[str]:
        result: list[str] = []
        hide_next = False
        for item in command:
            if hide_next:
                result.append("<redacted>")
                hide_next = False
                continue
            result.append(item)
            if item.lower() in {"--api-key", "--token", "--password", "--secret"}:
                hide_next = True
        return result
