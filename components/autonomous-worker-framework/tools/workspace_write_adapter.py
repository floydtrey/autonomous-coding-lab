"""Versioned Worker Lab workspace-write bridge.

The v2 adapter remains read-only.  This module accepts only the separate v3
operation, reconstructs the framework's context and code-task contracts, and
returns only bounded candidate identity evidence.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

try:
    from tools.code_task import (
        CodeTaskError,
        build_code_task,
        build_code_task_handoff,
        run_code_task,
    )
    from tools.codex_runtime import CodexExecution, CodexRequest
    from tools.consumer_profile import (
        ConsumerProfile,
        ConsumerProfileError,
        ValidationCommand,
        build_context_packet,
    )
    from tools.repository_handoff import RepositoryHandoffError
    from tools.worker_lab_adapter import (
        AdapterError,
        MAX_PROMPT_BYTES,
        MAX_REQUEST_BYTES,
        _bounded_bytes,
        _reject_sensitive_content,
        _response,
        _unique_object,
        canonical_json,
        digest,
        invocation_identity,
        validate_workspace_write_invocation,
    )
except ModuleNotFoundError:  # direct execution from the installed tools directory
    from code_task import CodeTaskError, build_code_task, build_code_task_handoff, run_code_task  # type: ignore
    from codex_runtime import CodexExecution, CodexRequest  # type: ignore
    from consumer_profile import (  # type: ignore
        ConsumerProfile, ConsumerProfileError, ValidationCommand, build_context_packet,
    )
    from repository_handoff import RepositoryHandoffError  # type: ignore
    from worker_lab_adapter import (  # type: ignore
        AdapterError, MAX_PROMPT_BYTES, MAX_REQUEST_BYTES, _bounded_bytes,
        _reject_sensitive_content, _response, _unique_object, canonical_json, digest,
        invocation_identity, validate_workspace_write_invocation,
    )


REQUEST_SCHEMA = "worker-lab-framework-workspace-write-request:v1"
TASK_SCHEMA = "worker-lab-framework-workspace-write-task:v1"
_TASK_FIELDS = {
    "schema_version",
    "invocation_digest",
    "objective",
    "acceptance_criteria",
    "consumer_profile",
    "test_ids",
    "writable_paths",
}
_RESPONSE_FIELDS = {
    "invocation_digest",
    "prompt_digest",
    "runtime_identity",
    "task_digest",
    "context_digest",
    "candidate_digest",
    "changed_paths",
}

Executor = Callable[[CodexRequest], CodexExecution]


def parse_workspace_write_request(raw: bytes | str) -> tuple[dict[str, Any], str]:
    """Parse the v3 write transport without expanding the v2 read-only schema."""
    encoded = _bounded_bytes(raw, MAX_REQUEST_BYTES, "request")
    try:
        value = json.loads(encoded.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise AdapterError("INTEGRATION_RESULT_INVALID", "request must be bounded UTF-8 JSON") from exc
    try:
        canonical = canonical_json(value).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AdapterError("INTEGRATION_RESULT_INVALID", "request must use finite canonical JSON") from exc
    if canonical != encoded:
        raise AdapterError("INTEGRATION_RESULT_INVALID", "request must use canonical JSON")
    if not isinstance(value, dict) or set(value) != {"schema_version", "invocation", "prompt", "workspace_write"}:
        raise AdapterError("INTEGRATION_FIELDS_INVALID", "workspace-write request fields are invalid")
    if value["schema_version"] != REQUEST_SCHEMA:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "unsupported workspace-write request")
    invocation = value["invocation"]
    if not isinstance(invocation, dict):
        raise AdapterError("INTEGRATION_FIELDS_INVALID", "workspace-write invocation is invalid")
    validate_workspace_write_invocation(invocation)
    prompt = value["prompt"]
    prompt_bytes = _bounded_bytes(prompt, MAX_PROMPT_BYTES, "prompt")
    _reject_sensitive_content(prompt_bytes)
    if digest(prompt_bytes) != invocation["prompt_digest"]:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "prompt digest differs from invocation")
    _validate_task(value["workspace_write"], invocation)
    return invocation, prompt


def execute_workspace_write(
    raw: bytes | str,
    *,
    runtime_identity: str,
    executor: Executor | None,
    framework_root: Path,
) -> bytes:
    """Run the existing code-task and repository-handoff primitives behind v3."""
    if executor is None:
        raise AdapterError("INTEGRATION_EXECUTION_DISABLED", "workspace-write requires an injected execution seam")
    invocation, _ = parse_workspace_write_request(raw)
    if invocation["state"] != "DISPATCHING" or not invocation["authorized_by"]:
        raise AdapterError("INTEGRATION_AUTHORIZATION_INVALID", "workspace-write requires a DISPATCHING invocation")
    task = invocation_from_request(raw)["workspace_write"]
    try:
        profile = ConsumerProfile.from_mapping(task["consumer_profile"])
        packet = build_context_packet(
            Path.cwd(),
            allowed_paths=tuple(invocation["writable_paths"]),
            task_context_paths=tuple(item["path"] for item in invocation["readable_paths"]),
            profile=profile,
        )
        quick = (
            ValidationCommand("Worker Lab candidate diff integrity", ("git", "diff", "--check"), 30),
        )
        code_task = build_code_task(
            packet,
            task_id=invocation["invocation_id"],
            objective=task["objective"],
            expected_changed_paths=tuple(invocation["writable_paths"]),
            acceptance_criteria=tuple(task["acceptance_criteria"]),
            quick_validation=quick,
        )
        result = run_code_task(
            code_task,
            packet,
            repo_root=Path.cwd(),
            framework_repo=framework_root,
            executor=executor,
            profile=profile,
        )
        handoff = build_code_task_handoff(code_task, result, repo_root=Path.cwd())
    except (CodeTaskError, ConsumerProfileError, RepositoryHandoffError) as exc:
        code = getattr(exc, "code", "INTEGRATION_EXECUTION_FAILED")
        raise AdapterError(code, "workspace-write code-task validation failed") from exc
    return _response({
        "invocation_digest": invocation_identity(invocation),
        "prompt_digest": invocation["prompt_digest"],
        "runtime_identity": _digest(runtime_identity, "runtime identity"),
        "task_digest": result.task_digest,
        "context_digest": result.context_digest,
        "candidate_digest": handoff.repository_handoff.candidate_content_digest,
        "changed_paths": list(handoff.repository_handoff.changed_paths),
    })


def invocation_from_request(raw: bytes | str) -> Mapping[str, Any]:
    """Return the previously validated canonical request for execution only."""
    encoded = _bounded_bytes(raw, MAX_REQUEST_BYTES, "request")
    try:
        value = json.loads(encoded.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise AdapterError("INTEGRATION_RESULT_INVALID", "request must be bounded UTF-8 JSON") from exc
    if not isinstance(value, dict) or not isinstance(value.get("workspace_write"), Mapping):
        raise AdapterError("INTEGRATION_FIELDS_INVALID", "workspace-write request fields are invalid")
    return value


def _validate_task(value: Any, invocation: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping) or set(value) != _TASK_FIELDS:
        raise AdapterError("INTEGRATION_FIELDS_INVALID", "workspace-write task fields are invalid")
    if value["schema_version"] != TASK_SCHEMA:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "workspace-write task version differs")
    if value["invocation_digest"] != invocation_identity(invocation):
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "workspace-write task invocation differs")
    objective = value["objective"]
    criteria = value["acceptance_criteria"]
    if (
        not isinstance(objective, str)
        or not objective.strip()
        or objective != objective.strip()
        or "\x00" in objective
        or not isinstance(criteria, list)
        or not criteria
        or any(not isinstance(item, str) or not item.strip() or item != item.strip() or "\x00" in item for item in criteria)
    ):
        raise AdapterError("INTEGRATION_FIELDS_INVALID", "workspace-write task objective or criteria are invalid")
    if value["test_ids"] != invocation["test_ids"] or value["writable_paths"] != invocation["writable_paths"]:
        raise AdapterError("INTEGRATION_SCOPE_FAILED", "workspace-write task scope differs from invocation")
    try:
        profile = ConsumerProfile.from_mapping(value["consumer_profile"])
    except ConsumerProfileError as exc:
        raise AdapterError("INTEGRATION_FIELDS_INVALID", "workspace-write consumer profile is invalid") from exc
    readable = tuple(item["path"] for item in invocation["readable_paths"])
    if (
        profile.consumer != f"worker-lab-{invocation['role_id']}"
        or profile.authority_paths != readable
        or profile.protected_prefixes
        or tuple(item.name for item in profile.full_validation) != tuple(invocation["test_ids"])
    ):
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "workspace-write consumer profile differs")


def _digest(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise AdapterError("INTEGRATION_RESULT_INVALID", f"{name} is invalid")
    if any(character not in "0123456789abcdef" for character in value[7:]):
        raise AdapterError("INTEGRATION_RESULT_INVALID", f"{name} is invalid")
    return value
