from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def validate_id(value: str, label: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError(
            f"{label} must start with a letter or digit and contain only "
            "letters, digits, dot, underscore, or hyphen (max 128 chars)"
        )
    return value


def path_key(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"{cleaned[:70] or 'item'}-{digest}"


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        # On Windows, a reader can briefly prevent replacement of the existing
        # file. The progress watcher and antivirus scanners are common causes.
        # Retry the atomic rename instead of aborting a healthy unattended run.
        delay_seconds = 0.01
        for attempt in range(20):
            try:
                os.replace(temp_name, path)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(delay_seconds)
                delay_seconds = min(delay_seconds * 2, 0.25)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def redact_config(config: dict[str, Any]) -> dict[str, Any]:
    """Round-trip copy and remove values that look like credentials."""
    copied = json.loads(json.dumps(config))
    sensitive = {"api_key", "token", "password", "secret", "authorization"}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key in list(value):
                if key.lower() in sensitive and value[key] is not None:
                    value[key] = "[REDACTED]"
                else:
                    visit(value[key])
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(copied)
    return copied
