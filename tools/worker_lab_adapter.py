from __future__ import annotations

import hashlib
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from pathlib import Path
from typing import Any

try:
    from tools.codex_runtime import (
        CodexRequest, check_chatgpt_auth, execute_codex_bounded, sanitized_codex_environment,
    )
except ModuleNotFoundError:  # direct isolated-script execution support
    # ``-I`` deliberately removes the script directory from ``sys.path``.
    # Load only the adjacent, framework-owned runtime by exact file identity;
    # this neither broadens import search nor imports anything from Worker Lab.
    _runtime_spec = importlib.util.spec_from_file_location(
        "worker_lab_adapter_codex_runtime", Path(__file__).with_name("codex_runtime.py")
    )
    if _runtime_spec is None or _runtime_spec.loader is None:  # pragma: no cover - filesystem failure
        raise RuntimeError("framework Codex runtime is unavailable")
    _runtime_module = importlib.util.module_from_spec(_runtime_spec)
    sys.modules[_runtime_spec.name] = _runtime_module
    _runtime_spec.loader.exec_module(_runtime_module)
    CodexRequest = _runtime_module.CodexRequest
    check_chatgpt_auth = _runtime_module.check_chatgpt_auth
    execute_codex_bounded = _runtime_module.execute_codex_bounded
    sanitized_codex_environment = _runtime_module.sanitized_codex_environment


PROTOCOL = "worker-lab-framework-adapter:v1"
REQUEST_SCHEMA = "worker-lab-framework-adapter-request:v1"
INVOCATION_SCHEMA = "worker-lab-framework-invocation:v1"
MAX_REQUEST_BYTES = 262_144
MAX_PROMPT_BYTES = 32_768
MAX_RESPONSE_BYTES = 65_536
MAX_STDOUT_BYTES = 65_536
MAX_STDERR_BYTES = 16_384
MAX_PROPOSAL_BYTES = 32_768
RUNTIME_PROFILE = "terra-medium:v1"
_TEST_ID_RE = re.compile(r"^T[0-9]{3}$")
_INVOCATION_FIELDS = {
    "schema_version", "invocation_id", "attempt_id", "operation", "exercise_id",
    "exercise_version", "exercise_digest", "policy_id", "policy_version", "policy_digest",
    "role_id", "role_version", "role_digest", "context_manifest_id", "context_manifest_version",
    "context_digest", "task_digest", "test_catalog_version", "test_catalog_digest",
    "test_plan_digest", "test_ids", "worker_lab_commit", "worker_lab_contract_version",
    "framework_commit", "framework_contract_version", "workspace_receipt_digest",
    "workspace_root_digest", "workspace_path_digest", "starting_commit", "sandbox_mode",
    "runtime_profile_id", "model", "reasoning_effort", "timeout_seconds", "readable_paths",
    "writable_paths", "prompt_digest", "authorized_by", "authorized_at", "state", "result_digest",
}


class AdapterError(ValueError):
    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


@dataclass(frozen=True)
class AdapterExecution:
    stdout: bytes
    stderr: bytes = b""
    returncode: int = 0


Executor = Callable[[str], AdapterExecution]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    encoded = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def invocation_identity(value: Mapping[str, Any]) -> str:
    immutable = dict(value)
    for field in ("authorized_by", "authorized_at", "state", "result_digest"):
        immutable.pop(field)
    return digest({
        "schema_version": "worker-lab-framework-invocation-identity:v1",
        "invocation": immutable,
    })


def parse_request(raw: bytes | str) -> tuple[dict[str, Any], str]:
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
    if not isinstance(value, dict) or set(value) != {"schema_version", "invocation", "prompt"}:
        raise AdapterError("INTEGRATION_FIELDS_INVALID", "adapter request fields are invalid")
    if value["schema_version"] != REQUEST_SCHEMA:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "unsupported adapter request")
    invocation = value["invocation"]
    if not isinstance(invocation, dict) or set(invocation) != _INVOCATION_FIELDS:
        raise AdapterError("INTEGRATION_FIELDS_INVALID", "invocation fields are invalid")
    _validate_invocation(invocation)
    prompt = value["prompt"]
    prompt_bytes = _bounded_bytes(prompt, MAX_PROMPT_BYTES, "prompt")
    _reject_sensitive_content(prompt_bytes)
    if digest(prompt_bytes) != invocation["prompt_digest"]:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "prompt digest differs from invocation")
    return invocation, prompt


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for name, item in pairs:
        if name in value:
            raise ValueError("duplicate JSON object key")
        value[name] = item
    return value


def prepare(raw: bytes | str, *, runtime_identity: str) -> bytes:
    invocation, _ = parse_request(raw)
    if invocation["state"] != "PREPARED" or invocation["authorized_by"] is not None:
        raise AdapterError("INTEGRATION_AUTHORIZATION_INVALID", "preparation requires an unauthorized PREPARED invocation")
    return _response({
        "invocation_digest": invocation_identity(invocation),
        "prompt_digest": invocation["prompt_digest"],
        "runtime_identity": _digest(runtime_identity, "runtime identity"),
    })


def preflight(raw: bytes | str, *, runtime_identity: str, checker: Callable[[], None] | None) -> bytes:
    if checker is None:
        raise AdapterError("INTEGRATION_EXECUTION_DISABLED", "preflight requires an injected checker")
    invocation, _ = parse_request(raw)
    if invocation["state"] != "AUTHORIZED" or not invocation["authorized_by"]:
        raise AdapterError("INTEGRATION_AUTHORIZATION_INVALID", "preflight requires exact authorization")
    checker()
    return _response({
        "invocation_digest": invocation_identity(invocation),
        "prompt_digest": invocation["prompt_digest"],
        "runtime_identity": _digest(runtime_identity, "runtime identity"),
    })


def execute_read_only(raw: bytes | str, *, runtime_identity: str, executor: Executor | None) -> bytes:
    if executor is None:
        raise AdapterError("INTEGRATION_EXECUTION_DISABLED", "Batch 3C requires an injected execution seam")
    invocation, prompt = parse_request(raw)
    if invocation["state"] != "DISPATCHING" or not invocation["authorized_by"]:
        raise AdapterError("INTEGRATION_AUTHORIZATION_INVALID", "execution requires a DISPATCHING invocation")
    execution = executor(prompt)
    if not isinstance(execution, AdapterExecution):
        raise AdapterError("INTEGRATION_EXECUTION_FAILED", "injected executor returned an invalid value")
    stdout = _bounded_bytes(execution.stdout, MAX_PROPOSAL_BYTES, "proposal")
    _bounded_bytes(execution.stderr, MAX_STDERR_BYTES, "stderr", allow_empty=True)
    if execution.returncode != 0:
        raise AdapterError("INTEGRATION_EXECUTION_FAILED", "injected executor returned nonzero")
    _reject_sensitive_content(stdout)
    return _response({
        "invocation_digest": invocation_identity(invocation),
        "prompt_digest": invocation["prompt_digest"],
        "runtime_identity": _digest(runtime_identity, "runtime identity"),
        "proposal_digest": digest(stdout),
        "output_digest": digest(stdout),
        "proposal_content": stdout.decode("utf-8"),
        "stdout_bytes": len(stdout),
        "stderr_bytes": len(execution.stderr),
    })


def _validate_invocation(value: Mapping[str, Any]) -> None:
    exact = {
        "schema_version": INVOCATION_SCHEMA,
        "operation": "read-only-proposal",
        "sandbox_mode": "read-only",
        "runtime_profile_id": RUNTIME_PROFILE,
        "model": "gpt-5.6-terra",
        "reasoning_effort": "medium",
        "timeout_seconds": 900,
        "framework_contract_version": PROTOCOL,
        "worker_lab_contract_version": "worker-lab-framework-client:v1",
    }
    if any(value.get(name) != expected for name, expected in exact.items()):
        raise AdapterError("INTEGRATION_RUNTIME_FORBIDDEN", "invocation runtime or contract differs")
    for name in (
        "invocation_id", "attempt_id", "exercise_id", "policy_id", "role_id",
        "context_manifest_id",
    ):
        _identifier(value.get(name), name)
    for name in (
        "exercise_version", "policy_version", "role_version", "context_manifest_version",
    ):
        _positive_integer(value.get(name), name)
    _text(value.get("test_catalog_version"), "test catalog version")
    if value.get("writable_paths") != []:
        raise AdapterError("INTEGRATION_SCOPE_FAILED", "read-only proposal cannot contain writable paths")
    if not isinstance(value.get("readable_paths"), list) or not value["readable_paths"]:
        raise AdapterError("INTEGRATION_SCOPE_FAILED", "read-only proposal requires readable paths")
    seen_paths = []
    for item in value["readable_paths"]:
        if not isinstance(item, dict) or set(item) != {"path", "digest"}:
            raise AdapterError("INTEGRATION_SCOPE_FAILED", "readable path identity is invalid")
        seen_paths.append(_relative_path(item["path"]))
        _digest(item["digest"], "readable path digest")
    if seen_paths != sorted(set(seen_paths)):
        raise AdapterError("INTEGRATION_SCOPE_FAILED", "readable paths must be sorted and unique")
    test_ids = value.get("test_ids")
    if (
        not isinstance(test_ids, list)
        or not test_ids
        or any(not isinstance(item, str) or not _TEST_ID_RE.fullmatch(item) for item in test_ids)
        or test_ids != sorted(set(test_ids))
    ):
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "sealed test plan is missing")
    digest_fields = [name for name in _INVOCATION_FIELDS if name.endswith("_digest")]
    for name in digest_fields:
        if value[name] is not None:
            _digest(value[name], name)
    for name in ("worker_lab_commit", "framework_commit", "starting_commit"):
        item = value.get(name)
        if not isinstance(item, str) or len(item) != 40 or any(char not in "0123456789abcdef" for char in item):
            raise AdapterError("INTEGRATION_IDENTITY_INVALID", f"{name} is invalid")
    state = value.get("state")
    if state not in {"PREPARED", "AUTHORIZED", "DISPATCHING"}:
        raise AdapterError("INTEGRATION_AUTHORIZATION_INVALID", "invocation state is not executable")
    authorized = value.get("authorized_by") is not None and value.get("authorized_at") is not None
    if authorized != (state in {"AUTHORIZED", "DISPATCHING"}):
        raise AdapterError("INTEGRATION_AUTHORIZATION_INVALID", "authorization custody is inconsistent")
    if authorized:
        if not isinstance(value["authorized_by"], str) or not value["authorized_by"].strip():
            raise AdapterError("INTEGRATION_AUTHORIZATION_INVALID", "controller identity is invalid")
        _timestamp(value["authorized_at"])
    if value.get("result_digest") is not None:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "pre-completion invocation cannot have a result")


def _response(value: Mapping[str, Any]) -> bytes:
    encoded = canonical_json(value).encode("utf-8")
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise AdapterError("INTEGRATION_RESULT_INVALID", "response exceeds limit")
    return encoded


def _bounded_bytes(value: bytes | str, limit: int, name: str, *, allow_empty: bool = False) -> bytes:
    if isinstance(value, str):
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise AdapterError("INTEGRATION_RESULT_INVALID", f"{name} is not UTF-8") from exc
    elif isinstance(value, bytes):
        encoded = value
    else:
        raise AdapterError("INTEGRATION_RESULT_INVALID", f"{name} must be bytes or text")
    if (not allow_empty and not encoded) or b"\x00" in encoded or len(encoded) > limit:
        raise AdapterError("INTEGRATION_RESULT_INVALID", f"{name} is empty, unsafe, or oversized")
    try:
        encoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AdapterError("INTEGRATION_RESULT_INVALID", f"{name} is not UTF-8") from exc
    return encoded


def _digest(value: object, name: str) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise AdapterError("INTEGRATION_RESULT_INVALID", f"{name} is invalid")
    if any(character not in "0123456789abcdef" for character in value[7:]):
        raise AdapterError("INTEGRATION_RESULT_INVALID", f"{name} is invalid")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise AdapterError("INTEGRATION_FIELDS_INVALID", f"{name} is invalid")
    return value


def _identifier(value: object, name: str) -> str:
    text = _text(value, name)
    if not text.replace("-", "").replace("_", "").isalnum():
        raise AdapterError("INTEGRATION_FIELDS_INVALID", f"{name} is invalid")
    return text


def _positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AdapterError("INTEGRATION_FIELDS_INVALID", f"{name} is invalid")
    return value


def _reject_sensitive_content(value: bytes) -> None:
    text = value.decode("utf-8").lower()
    forbidden = (
        "openai_api_key", "codex_api_key", "github_token", "gh_token", "authorization:",
        "bearer ", "\\\\", "//", ":\\", ":/",
    )
    if any(marker in text for marker in forbidden):
        raise AdapterError("INTEGRATION_RESULT_INVALID", "content contains forbidden sensitive material")


def _relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\\" in value:
        raise AdapterError("INTEGRATION_SCOPE_FAILED", "path is invalid")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute() or value.startswith("/") or ".." in candidate.parts
        or candidate.as_posix() != value or value == "." or ":" in candidate.parts[0]
    ):
        raise AdapterError("INTEGRATION_SCOPE_FAILED", "path is not normalized relative")
    return value


def _timestamp(value: object) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AdapterError("INTEGRATION_AUTHORIZATION_INVALID", "authorization time is invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise AdapterError("INTEGRATION_AUTHORIZATION_INVALID", "authorization time is invalid") from exc
    if parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != value:
        raise AdapterError("INTEGRATION_AUTHORIZATION_INVALID", "authorization time is not canonical")
    return value


def local_runtime_identity(invocation: Mapping[str, Any], *, version_reader: Callable[[str], str] | None = None) -> tuple[str, str]:
    framework_root = Path(__file__).resolve().parents[1]
    adapter_path = Path(__file__).resolve()
    head = _git(framework_root, "rev-parse", "HEAD").decode("ascii").strip()
    status = _git(framework_root, "status", "--porcelain=v1", "--untracked-files=all").decode("utf-8")
    if head != invocation["framework_commit"] or status:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "framework repository identity differs")
    blob = _git(framework_root, "show", f"{head}:tools/worker_lab_adapter.py")
    adapter_digest = digest(adapter_path.read_bytes())
    if digest(blob) != adapter_digest:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "adapter bytes differ from framework commit")
    clean_env = sanitized_codex_environment(os.environ)
    launcher = shutil.which("codex", path=clean_env.get("PATH"))
    if launcher is None:
        raise AdapterError("CODEX_UNAVAILABLE", "could not resolve audited Codex launcher")
    version = (version_reader or _read_launcher_version)(launcher)
    if version != "0.149.1":
        raise AdapterError("CODEX_VERSION_INVALID", "audited Codex launcher version differs")
    launcher_digest = digest(Path(launcher).resolve().read_bytes())
    python_digest = digest(Path(sys.executable).resolve().read_bytes())
    command_base = (
        "python", "-I", "-B", "tools/worker_lab_adapter.py",
        ("prepare", "preflight", "execute-read-only"), "--protocol", PROTOCOL,
    )
    identity = digest({
        "schema_version": "worker-lab-runtime-identity:v1", "framework_commit": head,
        "adapter_digest": adapter_digest, "adapter_contract_version": PROTOCOL,
        "python_digest": python_digest, "python_version": sys.version.split()[0],
        "python_implementation": __import__("platform").python_implementation(),
        "python_architecture": __import__("platform").machine(),
        "codex_launcher_digest": launcher_digest, "codex_version": version,
        "environment_policy": "framework-sanitized-environment:v1",
        "runtime_profile": RUNTIME_PROFILE, "operation": invocation["operation"],
        "sandbox": invocation["sandbox_mode"], "windows_sandbox": "elevated",
        "model": invocation["model"], "reasoning_effort": invocation["reasoning_effort"],
        "timeout_seconds": invocation["timeout_seconds"], "command_digest": digest(command_base),
    })
    return identity, launcher


def _read_launcher_version(launcher: str) -> str:
    process = subprocess.run([launcher, "--version"], stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding="utf-8", timeout=30, check=False)
    if process.returncode != 0 or "codex-cli " not in process.stdout:
        raise AdapterError("CODEX_VERSION_INVALID", "could not verify Codex launcher version")
    return process.stdout.strip().split()[-1]


def _execute_production(prompt: str, framework_root: Path, launcher: str) -> AdapterExecution:
    execution = execute_codex_bounded(CodexRequest(
        prompt=prompt, target_repo=Path.cwd(), framework_repo=framework_root,
        sandbox="read-only", model="gpt-5.6-terra", reasoning_effort="medium", timeout_seconds=900,
    ), executable=launcher)
    return AdapterExecution(execution.stdout.encode("utf-8"), execution.stderr.encode("utf-8"), execution.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Strict Worker Lab framework adapter")
    parser.add_argument("mode", choices=("prepare", "preflight", "execute-read-only"))
    parser.add_argument("--protocol", required=True)
    args = parser.parse_args(argv)
    if args.protocol != PROTOCOL:
        return 2
    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    try:
        invocation, _ = parse_request(raw)
        runtime, launcher = local_runtime_identity(invocation)
        if args.mode == "prepare":
            response = prepare(raw, runtime_identity=runtime)
        elif args.mode == "preflight":
            response = preflight(
                raw, runtime_identity=runtime,
                checker=lambda: check_chatgpt_auth(environment=os.environ, executable=launcher),
            )
        else:
            response = execute_read_only(
                raw, runtime_identity=runtime,
                executor=lambda prompt: _execute_production(
                    prompt, Path(__file__).resolve().parents[1], launcher
                ),
            )
    except Exception as exc:
        # Framework runtime failures already expose stable categories such as
        # CHATGPT_AUTH_REQUIRED.  Preserve only that code, never stderr or an
        # exception message that could contain local/sensitive detail.
        candidate = getattr(exc, "code", None)
        code = candidate if isinstance(candidate, str) and re.fullmatch(r"[A-Z0-9_]{3,96}", candidate) else "INTEGRATION_EXECUTION_FAILED"
        sys.stdout.buffer.write(_response({"failure_code": code, "retryable": False}))
        return 1
    sys.stdout.buffer.write(response)
    return 0


def _git(root: Path, *args: str) -> bytes:
    environment = {"PATH": os.environ.get("PATH", ""), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    # The controller has already resolved and reparse-checked ``root`` before
    # invoking this helper.  Passing only that exact path to Git avoids a
    # sandbox-account ownership false positive without enabling a global or
    # user-controlled safe-directory exception.
    process = subprocess.run(
        ["git", "-c", f"safe.directory={root}", *args], cwd=root, env=environment, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
    )
    if process.returncode != 0:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "framework Git identity check failed")
    return process.stdout


if __name__ == "__main__":
    raise SystemExit(main())
