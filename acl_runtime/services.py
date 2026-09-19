"""Generic local-service readiness and startup for ACL runtime dependencies.

The supervisor is configuration-driven. It does not know llama.cpp, Ollama,
Determiner, or any particular model. It probes required local services and starts
a configured launcher only when the endpoint is genuinely unreachable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping
from urllib import error as urlerror
from urllib import request as urlrequest

from acl_core.diagnostics import emit, span
from acl_core.errors import CoreError


SERVICE_CONFIG_SCHEMA = "acl-local-services:v1"


class ProbeState(StrEnum):
    HEALTHY = "HEALTHY"
    REACHABLE_ERROR = "REACHABLE_ERROR"
    UNREACHABLE = "UNREACHABLE"


@dataclass(frozen=True)
class ProbeResult:
    state: ProbeState
    url: str
    status_code: int | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LocalServiceConfig:
    service_id: str
    enabled: bool
    base_url_env: str
    health_path: str = "/models"
    api_key_env: str | None = None
    api_key_file_env: str | None = None
    probe_timeout_seconds: float = 3.0
    startup_timeout_seconds: float = 180.0
    command: tuple[str, ...] = ()
    command_json_env: str | None = None
    launcher_env: str | None = None
    cwd: str | None = None
    cwd_env: str | None = None
    log_path: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LocalServiceConfig":
        if not isinstance(value, Mapping):
            raise CoreError("LOCAL_SERVICE_CONFIG_INVALID", "service config must be a mapping")
        service_id = value.get("service_id")
        base_url_env = value.get("base_url_env")
        if not isinstance(service_id, str) or not service_id.strip():
            raise CoreError("LOCAL_SERVICE_CONFIG_INVALID", "service_id is required")
        if not isinstance(base_url_env, str) or not base_url_env.strip():
            raise CoreError(
                "LOCAL_SERVICE_CONFIG_INVALID",
                "base_url_env is required",
                {"service_id": service_id},
            )
        enabled = value.get("enabled", True)
        if not isinstance(enabled, bool):
            raise CoreError("LOCAL_SERVICE_CONFIG_INVALID", "enabled must be boolean")

        health_path = value.get("health_path", "/models")
        if not isinstance(health_path, str) or not health_path.startswith("/"):
            raise CoreError("LOCAL_SERVICE_CONFIG_INVALID", "health_path must begin with '/'")

        api_key_env = value.get("api_key_env")
        api_key_file_env = value.get("api_key_file_env")
        for item, label in (
            (api_key_env, "api_key_env"),
            (api_key_file_env, "api_key_file_env"),
        ):
            if item is not None and (not isinstance(item, str) or not item.strip()):
                raise CoreError("LOCAL_SERVICE_CONFIG_INVALID", f"{label} must be text")

        probe_timeout = cls._positive_number(
            value.get("probe_timeout_seconds", 3),
            "probe_timeout_seconds",
        )
        startup_timeout = cls._positive_number(
            value.get("startup_timeout_seconds", 180),
            "startup_timeout_seconds",
        )

        command_raw = value.get("command", [])
        if not isinstance(command_raw, list) or any(not isinstance(item, str) for item in command_raw):
            raise CoreError("LOCAL_SERVICE_CONFIG_INVALID", "command must be a list of strings")

        command_json_env = value.get("command_json_env")
        launcher_env = value.get("launcher_env")
        for item, label in (
            (command_json_env, "command_json_env"),
            (launcher_env, "launcher_env"),
        ):
            if item is not None and (not isinstance(item, str) or not item.strip()):
                raise CoreError("LOCAL_SERVICE_CONFIG_INVALID", f"{label} must be text")

        cwd = value.get("cwd")
        cwd_env = value.get("cwd_env")
        log_path = value.get("log_path")
        for item, label in ((cwd, "cwd"), (cwd_env, "cwd_env"), (log_path, "log_path")):
            if item is not None and (not isinstance(item, str) or not item.strip()):
                raise CoreError("LOCAL_SERVICE_CONFIG_INVALID", f"{label} must be nonblank text")

        return cls(
            service_id=service_id,
            enabled=enabled,
            base_url_env=base_url_env,
            health_path=health_path,
            api_key_env=api_key_env,
            api_key_file_env=api_key_file_env,
            probe_timeout_seconds=probe_timeout,
            startup_timeout_seconds=startup_timeout,
            command=tuple(command_raw),
            command_json_env=command_json_env,
            launcher_env=launcher_env,
            cwd=cwd,
            cwd_env=cwd_env,
            log_path=log_path,
        )

    @staticmethod
    def _positive_number(value: Any, label: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise CoreError("LOCAL_SERVICE_CONFIG_INVALID", f"{label} must be positive")
        return float(value)


class LocalServiceSupervisor:
    component = "runtime.services"

    def __init__(self, *, project_root: Path) -> None:
        self.project_root = Path(project_root).expanduser().resolve()

    def ensure_file(self, path: Path) -> tuple[dict[str, Any], ...]:
        path = Path(path).expanduser().resolve()
        with span(self.component, "ensure_file", path=str(path)):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                emit("DEBUG", self.component, "ensure_file", "service_config_absent", path=str(path))
                return ()
            except (OSError, json.JSONDecodeError) as exc:
                raise CoreError(
                    "LOCAL_SERVICE_CONFIG_READ_FAILED",
                    "local-service configuration could not be read",
                    {"path": str(path)},
                ) from exc
            if not isinstance(value, Mapping) or value.get("schema_version") != SERVICE_CONFIG_SCHEMA:
                raise CoreError("LOCAL_SERVICE_CONFIG_INVALID", "local-service schema is invalid")
            items = value.get("services", [])
            if not isinstance(items, list):
                raise CoreError("LOCAL_SERVICE_CONFIG_INVALID", "services must be a list")

            results = []
            for item in items:
                config = LocalServiceConfig.from_mapping(item)
                if not config.enabled:
                    emit(
                        "DEBUG",
                        self.component,
                        "ensure_file",
                        "service_skipped",
                        service_id=config.service_id,
                    )
                    continue
                results.append(self.ensure(config))
            return tuple(results)

    def ensure(self, config: LocalServiceConfig) -> dict[str, Any]:
        with span(
            self.component,
            "ensure",
            service_id=config.service_id,
            base_url_env=config.base_url_env,
        ):
            base_url = self._required_env(config.base_url_env)
            initial = self._probe(config, base_url)
            emit(
                "INFO",
                self.component,
                "ensure",
                "service_probe",
                service_id=config.service_id,
                state=str(initial.state),
                url=initial.url,
                status_code=initial.status_code,
                details=dict(initial.details),
            )

            if initial.state is ProbeState.HEALTHY:
                return {
                    "service_id": config.service_id,
                    "ready": True,
                    "started": False,
                    "url": initial.url,
                    "status_code": initial.status_code,
                }

            if initial.state is ProbeState.REACHABLE_ERROR:
                raise CoreError(
                    "LOCAL_SERVICE_REACHABLE_NOT_HEALTHY",
                    "service endpoint is reachable but failed its health check; refusing to start a duplicate process",
                    {
                        "service_id": config.service_id,
                        "url": initial.url,
                        "status_code": initial.status_code,
                        "details": dict(initial.details),
                    },
                )

            command = self._resolve_command(config)
            cwd = self._resolve_cwd(config)
            log_path = self._resolve_log_path(config)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            emit(
                "INFO",
                self.component,
                "ensure",
                "service_starting",
                service_id=config.service_id,
                command=self._redacted_command(command),
                cwd=None if cwd is None else str(cwd),
                log_path=str(log_path),
                startup_timeout_seconds=config.startup_timeout_seconds,
            )

            log_handle = log_path.open("ab", buffering=0)
            process = None
            try:
                creationflags = 0
                kwargs: dict[str, Any] = {}
                if os.name == "nt":
                    creationflags = (
                        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    )
                else:
                    kwargs["start_new_session"] = True

                process = subprocess.Popen(
                    command,
                    cwd=None if cwd is None else str(cwd),
                    stdin=subprocess.DEVNULL,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    creationflags=creationflags,
                    **kwargs,
                )
                emit(
                    "INFO",
                    self.component,
                    "ensure",
                    "service_process_started",
                    service_id=config.service_id,
                    pid=process.pid,
                )

                deadline = time.monotonic() + config.startup_timeout_seconds
                last_probe = initial
                launcher_exit_logged = False
                while time.monotonic() < deadline:
                    exit_code = process.poll()
                    if exit_code is not None and not launcher_exit_logged:
                        emit(
                            "INFO",
                            self.component,
                            "ensure",
                            "launcher_process_exited",
                            service_id=config.service_id,
                            pid=process.pid,
                            exit_code=exit_code,
                            note="continuing endpoint readiness checks because launchers may detach the service process",
                        )
                        launcher_exit_logged = True
                    last_probe = self._probe(config, base_url)
                    if last_probe.state is ProbeState.HEALTHY:
                        emit(
                            "INFO",
                            self.component,
                            "ensure",
                            "service_ready",
                            service_id=config.service_id,
                            pid=process.pid,
                            url=last_probe.url,
                            status_code=last_probe.status_code,
                        )
                        return {
                            "service_id": config.service_id,
                            "ready": True,
                            "started": True,
                            "launcher_pid": process.pid,
                            "launcher_exit_code": process.poll(),
                            "url": last_probe.url,
                            "status_code": last_probe.status_code,
                            "log_path": str(log_path),
                        }
                    if last_probe.state is ProbeState.REACHABLE_ERROR:
                        tail = self._log_tail(log_path)
                        raise CoreError(
                            "LOCAL_SERVICE_START_REACHABLE_ERROR",
                            "managed service became reachable but did not pass health validation",
                            {
                                "service_id": config.service_id,
                                "pid": process.pid,
                                "url": last_probe.url,
                                "status_code": last_probe.status_code,
                                "details": dict(last_probe.details),
                                "log_tail": tail,
                            },
                        )
                    time.sleep(0.5)

                tail = self._log_tail(log_path)
                raise CoreError(
                    "LOCAL_SERVICE_START_TIMEOUT",
                    "managed service did not become healthy before startup timeout",
                    {
                        "service_id": config.service_id,
                        "launcher_pid": process.pid,
                        "launcher_exit_code": process.poll(),
                        "url": last_probe.url,
                        "log_tail": tail,
                    },
                )
            except Exception:
                if process is not None and process.poll() is None:
                    self._terminate_owned(process, config.service_id)
                raise
            finally:
                log_handle.close()

    def _probe(self, config: LocalServiceConfig, base_url: str) -> ProbeResult:
        url = base_url.rstrip("/") + config.health_path
        headers: dict[str, str] = {}
        api_key = self._resolve_probe_api_key(config)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urlrequest.Request(url, headers=headers, method="GET")
        try:
            with urlrequest.urlopen(req, timeout=config.probe_timeout_seconds) as response:
                status = getattr(response, "status", 200)
                if 200 <= status < 300:
                    return ProbeResult(ProbeState.HEALTHY, url, status)
                return ProbeResult(
                    ProbeState.REACHABLE_ERROR,
                    url,
                    status,
                    {"reason": "unexpected_status"},
                )
        except urlerror.HTTPError as exc:
            body = exc.read() if hasattr(exc, "read") else b""
            return ProbeResult(
                ProbeState.REACHABLE_ERROR,
                url,
                exc.code,
                {
                    "reason": "http_error",
                    "body_excerpt": body.decode("utf-8", errors="replace")[:1000],
                },
            )
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            return ProbeResult(
                ProbeState.UNREACHABLE,
                url,
                None,
                {
                    "reason": "transport_error",
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
            )

    def _resolve_command(self, config: LocalServiceConfig) -> list[str]:
        if config.command:
            return [self._expand_env(item) for item in config.command]
        if config.command_json_env:
            raw = os.getenv(config.command_json_env)
            if not raw:
                raise CoreError(
                    "LOCAL_SERVICE_START_COMMAND_MISSING",
                    "service is down and no startup command is configured",
                    {
                        "service_id": config.service_id,
                        "required_env": config.command_json_env,
                    },
                )
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise CoreError(
                    "LOCAL_SERVICE_START_COMMAND_INVALID",
                    "startup command environment value must be a JSON array",
                    {
                        "service_id": config.service_id,
                        "env": config.command_json_env,
                    },
                ) from exc
            if not isinstance(value, list) or not value or any(not isinstance(item, str) for item in value):
                raise CoreError(
                    "LOCAL_SERVICE_START_COMMAND_INVALID",
                    "startup command must be a nonempty JSON array of strings",
                    {"service_id": config.service_id},
                )
            return [self._expand_env(item) for item in value]
        if config.launcher_env:
            raw_launcher = os.getenv(config.launcher_env)
            if not raw_launcher or not raw_launcher.strip():
                raise CoreError(
                    "LOCAL_SERVICE_START_COMMAND_MISSING",
                    "service is down and launcher path is not configured",
                    {
                        "service_id": config.service_id,
                        "required_env": config.launcher_env,
                    },
                )
            launcher = Path(self._expand_env(raw_launcher.strip())).expanduser().resolve()
            if not launcher.exists():
                raise CoreError(
                    "LOCAL_SERVICE_START_COMMAND_INVALID",
                    "configured launcher does not exist",
                    {
                        "service_id": config.service_id,
                        "launcher": str(launcher),
                    },
                )
            suffix = launcher.suffix.lower()
            if os.name == "nt" and suffix in {".bat", ".cmd"}:
                return ["cmd.exe", "/d", "/c", str(launcher)]
            if os.name == "nt" and suffix == ".ps1":
                return [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(launcher),
                ]
            return [str(launcher)]
        raise CoreError(
            "LOCAL_SERVICE_START_COMMAND_MISSING",
            "service is down and no startup command is configured",
            {"service_id": config.service_id},
        )

    def _resolve_cwd(self, config: LocalServiceConfig) -> Path | None:
        value = config.cwd
        if config.cwd_env:
            env_value = os.getenv(config.cwd_env)
            if env_value:
                value = env_value
        if value is None:
            return None
        path = Path(self._expand_env(value)).expanduser().resolve()
        if not path.is_dir():
            raise CoreError(
                "LOCAL_SERVICE_CWD_INVALID",
                "configured service working directory does not exist",
                {"service_id": config.service_id, "cwd": str(path)},
            )
        return path

    def _resolve_log_path(self, config: LocalServiceConfig) -> Path:
        value = config.log_path or f"logs/services/{config.service_id}.log"
        value = self._expand_env(value)
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    @staticmethod
    def _resolve_probe_api_key(config: LocalServiceConfig) -> str | None:
        if config.api_key_env:
            value = os.getenv(config.api_key_env)
            if value and value.strip():
                return value.strip()
        if config.api_key_file_env:
            path_value = os.getenv(config.api_key_file_env)
            if path_value and path_value.strip():
                path = Path(path_value.strip()).expanduser()
                try:
                    value = path.read_text(encoding="utf-8").strip()
                except OSError as exc:
                    raise CoreError(
                        "LOCAL_SERVICE_API_KEY_FILE_FAILED",
                        "configured API-key file could not be read",
                        {"path": str(path)},
                    ) from exc
                if value:
                    return value
        return None

    @staticmethod
    def _required_env(name: str) -> str:
        value = os.getenv(name)
        if not value or not value.strip():
            raise CoreError(
                "LOCAL_SERVICE_ENV_MISSING",
                "required local-service environment variable is not set",
                {"env": name},
            )
        return value.strip()

    @staticmethod
    def _expand_env(value: str) -> str:
        return os.path.expandvars(value)

    @staticmethod
    def _redacted_command(command: list[str]) -> list[str]:
        redacted = []
        hide_next = False
        secret_flags = {"--api-key", "--token", "--password", "--secret"}
        for item in command:
            if hide_next:
                redacted.append("<redacted>")
                hide_next = False
                continue
            redacted.append(item)
            if item.lower() in secret_flags:
                hide_next = True
        return redacted

    @staticmethod
    def _log_tail(path: Path, limit: int = 12000) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")[-limit:]
        except OSError:
            return ""

    @staticmethod
    def _terminate_owned(process: subprocess.Popen, service_id: str) -> None:
        emit(
            "INFO",
            LocalServiceSupervisor.component,
            "terminate_owned",
            "service_process_terminating",
            service_id=service_id,
            pid=process.pid,
        )
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        emit(
            "INFO",
            LocalServiceSupervisor.component,
            "terminate_owned",
            "service_process_terminated",
            service_id=service_id,
            pid=process.pid,
            exit_code=process.returncode,
        )
