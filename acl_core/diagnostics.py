"""Structured Core diagnostics.

Core code emits through this module directly. Nothing external has to "run the
logger"; any public Core operation can call emit()/span(). Output can be turned
off entirely or redirected by environment/configuration.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from threading import RLock
from time import perf_counter
from typing import Any, Iterator

from .identity import current_correlation


_LEVELS = {"OFF": 100, "ERROR": 40, "INFO": 20, "DEBUG": 10}


@dataclass(frozen=True)
class DiagnosticConfig:
    enabled: bool = False
    level: str = "ERROR"
    path: Path | None = None
    stderr: bool = False

    def __post_init__(self) -> None:
        if self.level not in _LEVELS:
            raise ValueError("unsupported diagnostic level")


_lock = RLock()
_config = DiagnosticConfig(
    enabled=os.getenv("ACL_CORE_LOG_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"},
    level=os.getenv("ACL_CORE_LOG_LEVEL", "ERROR").strip().upper() or "ERROR",
    path=Path(os.environ["ACL_CORE_LOG_PATH"]).expanduser()
        if os.getenv("ACL_CORE_LOG_PATH") else None,
    stderr=os.getenv("ACL_CORE_LOG_STDERR", "").strip().lower() in {"1", "true", "yes", "on"},
)


def configure(*, enabled: bool, level: str = "ERROR", path: Path | None = None, stderr: bool = False) -> None:
    global _config
    level = level.upper()
    if level not in _LEVELS:
        raise ValueError("unsupported diagnostic level")
    _config = DiagnosticConfig(enabled=bool(enabled), level=level, path=path, stderr=bool(stderr))


def config() -> DiagnosticConfig:
    return _config


def emit(level: str, component: str, operation: str, event: str, **details: Any) -> None:
    cfg = _config
    level = level.upper()
    if not cfg.enabled or _LEVELS.get(level, 999) < _LEVELS[cfg.level]:
        return
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "level": level,
        "component": component,
        "operation": operation,
        "event": event,
        "correlation": current_correlation().to_dict(),
        "details": details,
    }
    raw = json.dumps(record, ensure_ascii=False, default=str, sort_keys=True)
    # Diagnostics must never become an execution dependency. A broken log path
    # or stderr sink is intentionally swallowed so the original Core operation
    # remains authoritative.
    try:
        with _lock:
            if cfg.path is not None:
                path = cfg.path.expanduser().resolve()
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(raw + "\n")
            if cfg.stderr:
                print(raw, file=sys.stderr)
    except Exception:
        return


def error(component: str, operation: str, exc: BaseException, **details: Any) -> None:
    details = dict(details)
    details.update(
        exception_type=type(exc).__name__,
        exception_message=str(exc),
    )
    emit("ERROR", component, operation, "error", **details)


@contextmanager
def span(component: str, operation: str, **details: Any) -> Iterator[None]:
    started = perf_counter()
    emit("DEBUG", component, operation, "begin", **details)
    try:
        yield
    except Exception as exc:
        error(
            component,
            operation,
            exc,
            elapsed_ms=round((perf_counter() - started) * 1000, 3),
            **details,
        )
        raise
    else:
        emit(
            "DEBUG",
            component,
            operation,
            "success",
            elapsed_ms=round((perf_counter() - started) * 1000, 3),
            **details,
        )
