"""Canonical UTF-8 JSON frames for a future isolated Pi adapter.

Parsing is not authorization, execution, qualification, settlement or acceptance.
The trusted caller must validate Provider Binding/qualification and custody before
launch; this module does not add a dispatch runner or bypass those gates.
"""
from __future__ import annotations

import json
import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from .canonical import canonical_digest, canonical_json
from .dispatch_client import WorkspaceWriteTask, _validate_invocation_for_dispatch, _validate_prompt
from .errors import LabValidationError
from .integration_v3 import InvocationRecordV3
from .pi_worker import resolve_pi_worker

REQUEST_SCHEMA = "acl-pi-request:v1"
RESULT_SCHEMA = "acl-pi-result:v1"
EVENT_SCHEMA = "acl-pi-event:v1"
MAX_FRAME_BYTES = 262_144
MAX_SAFE_INTEGER = 9_007_199_254_740_991


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise LabValidationError("PI_PROTOCOL_INVALID", message)


def _object(value: Any, fields: str) -> None:
    _require(isinstance(value, dict) and set(value) == set(fields.split()), "missing or unknown protocol fields")


def _text(value: Any) -> None:
    _require(isinstance(value, str) and bool(value.strip()) and "\x00" not in value and len(value.encode("utf-8")) <= 32768, "invalid protocol text")


def _digest(value: Any) -> None:
    _require(isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None, "invalid digest")


def _integer(value: Any, minimum: int = 0) -> None:
    _require(type(value) is int and minimum <= value <= MAX_SAFE_INTEGER, "invalid or unsafe protocol integer")


def _portable_json(value: Any, depth: int = 0) -> None:
    _require(depth <= 64, "protocol nesting limit exceeded")
    if isinstance(value, dict):
        for key, item in value.items():
            _require(isinstance(key, str) and key.isascii(), "protocol object keys must be ASCII")
            _portable_json(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _portable_json(item, depth + 1)
    elif isinstance(value, str):
        value.encode("utf-8", errors="strict")
    elif type(value) is int:
        _require(abs(value) <= MAX_SAFE_INTEGER, "unsafe protocol integer")
    else:
        _require(value is None or type(value) is bool, "unsupported JSON value")


def encode_frame(value: dict[str, Any]) -> bytes:
    try:
        _portable_json(value)
        raw = canonical_json(value).encode("utf-8")
        _require(len(raw) <= MAX_FRAME_BYTES, "protocol frame exceeds size limit")
        return raw
    except (UnicodeError, RecursionError) as exc:
        raise LabValidationError("PI_PROTOCOL_INVALID", "invalid UTF-8 or nesting") from exc


def decode_frame(raw: bytes) -> dict[str, Any]:
    _require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_FRAME_BYTES, "invalid protocol frame size/type")
    try:
        value = json.loads(raw.decode("utf-8"))
        _require(isinstance(value, dict) and encode_frame(value) == raw, "frame must be canonical JSON (no duplicate keys or trailing bytes)")
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise LabValidationError("PI_PROTOCOL_INVALID", "invalid canonical UTF-8 JSON frame") from exc


def grant_digest(invocation: InvocationRecordV3, workspace_root: str) -> str:
    # Include authorization custody and all sealed identities, not just file names.
    return canonical_digest({"invocation": invocation.to_dict(), "workspace_root": workspace_root})


def build_request(*, invocation: InvocationRecordV3, prompt: str,
                  task: dict[str, Any], worker: dict[str, Any], worker_digest: str,
                  workspace_root: str, issued_at_unix_ms: int,
                  deadline_unix_ms: int, execution_prompt: str | None = None) -> bytes:
    value = {
        "schema_version": REQUEST_SCHEMA,
        "invocation": invocation.to_dict(), "prompt": prompt, "task": task,
        "worker": worker, "worker_digest": worker_digest,
        "workspace_root": workspace_root,
        "grant_digest": grant_digest(invocation, workspace_root),
        "issued_at_unix_ms": issued_at_unix_ms, "deadline_unix_ms": deadline_unix_ms,
    }
    if execution_prompt is not None:
        value["schema_version"] = "acl-pi-request:v2"
        value["execution_prompt"] = execution_prompt
    raw = encode_frame(value)
    parse_request(raw, expected_worker_digest=worker_digest, now_unix_ms=issued_at_unix_ms)
    return raw


def parse_request(raw: bytes, *, expected_worker_digest: str, now_unix_ms: int) -> dict[str, Any]:
    value = decode_frame(raw)
    fields = "schema_version invocation prompt task worker worker_digest workspace_root grant_digest issued_at_unix_ms deadline_unix_ms"
    if value.get("schema_version") == "acl-pi-request:v2":
        fields += " execution_prompt"
        _text(value.get("execution_prompt"))
    _object(value, fields)
    _require(value["schema_version"] in (REQUEST_SCHEMA, "acl-pi-request:v2"), "unsupported request version")
    worker = resolve_pi_worker(value["worker"], expected_digest=expected_worker_digest)
    _require(value["worker_digest"] == expected_worker_digest, "worker digest differs from trusted configuration")
    invocation = InvocationRecordV3.from_mapping(value["invocation"])
    _validate_invocation_for_dispatch(invocation)
    _validate_prompt(invocation, value["prompt"])
    WorkspaceWriteTask.from_mapping(value["task"], invocation=invocation)
    _require(invocation.runtime_requirement_digest == worker["runtime_requirement_digest"], "runtime requirement differs")
    root = value["workspace_root"]
    _text(root)
    _require((PurePosixPath(root).is_absolute() or PureWindowsPath(root).is_absolute())
             and ".." not in root.replace("\\", "/").split("/"), "workspace root must be absolute without traversal")
    _require(value["grant_digest"] == grant_digest(invocation, root), "grant identity differs")
    for field in ("issued_at_unix_ms", "deadline_unix_ms"):
        _integer(value[field], 1)
    _integer(now_unix_ms, 1)
    issued, deadline = value["issued_at_unix_ms"], value["deadline_unix_ms"]
    _require(issued <= now_unix_ms < deadline and deadline - issued <= worker["attempt_timeout_seconds"] * 1000, "expired, future or excessive execution deadline")
    return value


def _correlate(value: dict[str, Any], request_raw: bytes, expected_worker_digest: str) -> dict[str, Any]:
    # Validate the request at issuance; terminal results can arrive after deadline.
    request = decode_frame(request_raw)
    request = parse_request(request_raw, expected_worker_digest=expected_worker_digest, now_unix_ms=request.get("issued_at_unix_ms"))
    _require(value["request_digest"] == canonical_digest(request), "response belongs to another request")
    return request


def parse_event(raw: bytes, *, request_raw: bytes, expected_worker_digest: str, expected_sequence: int) -> dict[str, Any]:
    value = decode_frame(raw)
    _object(value, "schema_version request_digest sequence event detail")
    _require(value["schema_version"] == EVENT_SCHEMA, "unsupported event version")
    _correlate(value, request_raw, expected_worker_digest)
    _integer(value["sequence"])
    _integer(expected_sequence)
    _require(value["sequence"] == expected_sequence, "event sequence is missing, repeated or out of order")
    _require(isinstance(value["event"], str) and value["event"] in {"started", "settled", "stopped", "error"}, "unsupported event")
    _text(value["detail"])
    return value


def parse_result(raw: bytes, *, request_raw: bytes, expected_worker_digest: str) -> dict[str, Any]:
    value = decode_frame(raw)
    _object(value, "schema_version request_digest status stop_reason summary remaining_work session_reference usage candidate")
    _require(value["schema_version"] in (RESULT_SCHEMA, "acl-pi-result:v2"), "unsupported result version")
    request = _correlate(value, request_raw, expected_worker_digest)
    statuses = {"completed", "needs_continuation", "blocked", "failed", "cancelled", "timed_out", "protocol_error"}
    _require(isinstance(value["status"], str) and value["status"] in statuses, "unsupported worker status")
    for field in ("stop_reason", "summary"):
        _text(value[field])
    for field in ("remaining_work", "session_reference"):
        if value[field] is not None:
            _text(value[field])
    _require(value["status"] not in {"needs_continuation", "blocked"} or value["remaining_work"] is not None, "remaining work or blocker is required")
    if value["usage"] is not None:
        _object(value["usage"], "input_tokens output_tokens requests tool_calls")
        for name, item in value["usage"].items():
            if value["schema_version"] == "acl-pi-result:v2" and name in {"input_tokens", "output_tokens"} and item is None:
                continue
            _integer(item)
        if value["status"] == "completed":
            settings = request["worker"]["runtime_settings"]
            _require(value["usage"]["requests"] <= settings["request_limit"] and value["usage"]["tool_calls"] <= settings["tool_calls_limit"], "completed claim exceeds execution budget")
    if value["candidate"] is not None:
        candidate = value["candidate"]
        _object(candidate, "digest artifacts")
        _digest(candidate["digest"])
        _require(isinstance(candidate["artifacts"], list), "invalid artifacts")
        seen = set()
        for artifact in candidate["artifacts"]:
            _object(artifact, "path digest")
            path = artifact["path"]
            _text(path)
            _require(path in request["invocation"]["writable_paths"] and path not in seen, "artifact outside grant or duplicated")
            _digest(artifact["digest"])
            seen.add(path)
    return value
