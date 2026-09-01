from __future__ import annotations

import hashlib
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from pathlib import Path
from typing import Any

PROTOCOL = "worker-lab-framework-adapter:v2"
REQUEST_SCHEMA = "worker-lab-framework-adapter-request:v2"
INVOCATION_SCHEMA = "worker-lab-framework-invocation:v2"
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
    "test_plan_digest", "test_ids", "worker_lab_installation_digest", "worker_lab_contract_version",
    "framework_installation_digest", "framework_contract_version", "workspace_receipt_digest",
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


@dataclass(frozen=True)
class InstalledRuntime:
    manifest_path: Path
    installation_root: Path
    framework_root: Path
    framework_installation_digest: str
    framework_files: tuple[tuple[str, str], ...]
    adapter_digest: str
    python_path: Path
    python_digest: str
    python_version: str
    python_implementation: str
    python_architecture: str
    codex_path: Path
    codex_digest: str
    codex_version: str
    execution_authority: str
    participant_states: Mapping[str, str]


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
        "schema_version": "worker-lab-framework-invocation-identity:v2",
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
        "worker_lab_contract_version": "worker-lab-framework-client:v2",
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
    for name in ("starting_commit",):
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


def local_runtime_identity(
    invocation: Mapping[str, Any],
    *,
    version_reader: Callable[[str], str] | None = None,
    installed: InstalledRuntime | None = None,
) -> tuple[str, str]:
    installation = installed or _installed_adapter_identity()
    if installation.framework_installation_digest != invocation["framework_installation_digest"]:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "framework installation identity differs")
    python_path = Path(sys.executable).resolve(strict=True)
    if (
        not _path_equal(python_path, installation.python_path)
        or digest(python_path.read_bytes()) != installation.python_digest
        or sys.version.split()[0] != installation.python_version
        or __import__("platform").python_implementation() != installation.python_implementation
        or __import__("platform").machine() != installation.python_architecture
    ):
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "Python runtime identity differs")
    runtime_module = _framework_runtime(installation)
    clean_env = runtime_module.sanitized_codex_environment(os.environ)
    launcher = shutil.which("codex", path=clean_env.get("PATH"))
    if launcher is None:
        raise AdapterError("CODEX_UNAVAILABLE", "could not resolve audited Codex launcher")
    launcher_path = Path(launcher).resolve(strict=True)
    if not _path_equal(launcher_path, installation.codex_path) or digest(launcher_path.read_bytes()) != installation.codex_digest:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "Codex launcher identity differs")
    version = (version_reader or _read_launcher_version)(launcher)
    if version != installation.codex_version:
        raise AdapterError("CODEX_VERSION_INVALID", "audited Codex launcher version differs")
    command_base = (
        "python", "-I", "-B", "tools/worker_lab_adapter.py",
        ("prepare", "preflight", "execute-read-only"), "--protocol", PROTOCOL,
    )
    identity = digest({
        "schema_version": "worker-lab-runtime-identity:v2",
        "framework_installation_digest": installation.framework_installation_digest,
        "framework_runtime_files": [
            {"path": path, "sha256": file_digest}
            for path, file_digest in installation.framework_files
        ],
        "adapter_digest": installation.adapter_digest, "adapter_contract_version": PROTOCOL,
        "python_digest": installation.python_digest, "python_version": sys.version.split()[0],
        "python_implementation": __import__("platform").python_implementation(),
        "python_architecture": __import__("platform").machine(),
        "codex_launcher_digest": installation.codex_digest, "codex_version": version,
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
    runtime_module = _framework_runtime(_installed_adapter_identity())
    descriptor, output_name = tempfile.mkstemp(prefix="worker-lab-final-", suffix=".txt")
    os.close(descriptor)
    output_path = Path(output_name)
    try:
        execution = runtime_module.execute_codex_bounded(runtime_module.CodexRequest(
            prompt=prompt, target_repo=Path.cwd(), framework_repo=framework_root,
            sandbox="read-only", model="gpt-5.6-terra", reasoning_effort="medium",
            timeout_seconds=900, output_last_message=output_path,
        ), executable=launcher)
        try:
            content = output_path.read_bytes()
        except OSError as exc:
            raise AdapterError("INTEGRATION_EXECUTION_FAILED", "Codex final message is unavailable") from exc
        if not content or len(content) > MAX_PROPOSAL_BYTES:
            raise AdapterError("INTEGRATION_RESULT_INVALID", "Codex final message is empty or oversized")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AdapterError("INTEGRATION_RESULT_INVALID", "Codex final message is not UTF-8") from exc
        # stderr may contain normal CLI progress.  It is bounded by the runtime
        # but deliberately never becomes retained proposal evidence.
        return AdapterExecution(content, b"", execution.returncode)
    finally:
        try:
            output_path.unlink()
        except FileNotFoundError:
            pass


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
        installed = _installed_adapter_identity()
        _require_execution_policy(installed, args.mode)
        runtime, launcher = local_runtime_identity(invocation, installed=installed)
        if args.mode == "prepare":
            response = prepare(raw, runtime_identity=runtime)
        elif args.mode == "preflight":
            runtime_module = _framework_runtime(installed)
            response = preflight(
                raw, runtime_identity=runtime,
                checker=lambda: runtime_module.check_chatgpt_auth(
                    environment=os.environ, executable=launcher,
                ),
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


def _installed_adapter_identity(
    *,
    manifest_path: Path | None = None,
    adapter_path: Path | None = None,
) -> InstalledRuntime:
    adapter_path = (adapter_path or Path(__file__)).resolve()
    installation_root = manifest_path.parent.parent if manifest_path is not None else adapter_path.parents[3]
    manifest_path = manifest_path or installation_root / "config" / "installation-manifest.json"
    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installation manifest is invalid") from exc
    root = _manifest_object(manifest, {
        "schema_version", "installation_id", "source_provenance", "activation_policy",
        "components", "runtimes", "integrity",
    })
    if root["schema_version"] != "acl-installation-manifest:v2" or root["installation_id"] != "acl-development":
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installation manifest version or identity differs")
    component_names = {
        "autonomous-worker-framework", "worker-lab", "local-model-bench",
    }
    sources = _manifest_object(root["source_provenance"], component_names)
    for name in component_names:
        source = _manifest_object(sources[name], {"repository_id", "source_commit", "source_tree"})
        if source["repository_id"] != name:
            raise AdapterError("INTEGRATION_IDENTITY_INVALID", "source provenance identity differs")
        for field in ("source_commit", "source_tree"):
            value = source[field]
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
                raise AdapterError("INTEGRATION_IDENTITY_INVALID", "source provenance is invalid")
    policy = _manifest_object(root["activation_policy"], {"policy_id", "execution_authority", "participants"})
    if policy["policy_id"] != "acl-installation-activation:v1" or policy["execution_authority"] not in {"DISABLED", "ENABLED"}:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installation activation policy differs")
    participants = _manifest_object(policy["participants"], component_names)
    if (
        participants["autonomous-worker-framework"] not in {"ACTIVE", "AVAILABLE"}
        or participants["worker-lab"] not in {"ACTIVE", "DEFERRED"}
        or participants["local-model-bench"] != "ADVISORY"
    ):
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installation participant state differs")
    components = _manifest_object(root["components"], component_names)
    parsed_components: dict[str, tuple[Path, str, tuple[tuple[str, str], ...], Mapping[str, Any]]] = {}
    for name in component_names:
        component = _manifest_object(
            components[name], {"root", "production_root", "installed_tree", "entrypoints"},
        )
        component_root = _contained_path(installation_root, _manifest_relative_path(component["root"]), directory=True)
        production_root = _manifest_relative_path(component["production_root"])
        tree = _manifest_object(component["installed_tree"], {"schema_version", "scope", "digest", "files"})
        if tree["schema_version"] != "acl-installed-file-set:v1" or tree["scope"] not in {
            "runtime-dependency-closure", "python-production-tree",
        }:
            raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installed file-set contract differs")
        files_raw = tree["files"]
        if not isinstance(files_raw, list) or not files_raw:
            raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installed file set is empty")
        files: list[tuple[str, str]] = []
        for raw_file in files_raw:
            item = _manifest_object(raw_file, {"path", "sha256"})
            files.append((_manifest_relative_path(item["path"]).as_posix(), _digest(item["sha256"], "installed file digest")))
        file_tuple = tuple(files)
        if tuple(path for path, _ in file_tuple) != tuple(sorted({path for path, _ in file_tuple})):
            raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installed file set is not sorted and unique")
        expected_tree_digest = digest([{"path": path, "sha256": value} for path, value in file_tuple])
        if _digest(tree["digest"], "installed tree digest") != expected_tree_digest:
            raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installed file-set digest differs")
        prefix = PurePosixPath(production_root.as_posix())
        if any(PurePosixPath(path).parts[:len(prefix.parts)] != prefix.parts for path, _ in file_tuple):
            raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installed file escapes production root")
        entries = _manifest_object(
            component["entrypoints"], {"worker-lab-adapter"} if name == "autonomous-worker-framework" else set(),
        )
        parsed_components[name] = (component_root, tree["scope"], file_tuple, entries)
    framework_root, framework_scope, framework_files, framework_entrypoints = parsed_components["autonomous-worker-framework"]
    if (
        framework_scope != "runtime-dependency-closure"
        or framework_files != (
            ("tools/codex_runtime.py", dict(framework_files).get("tools/codex_runtime.py", "")),
            ("tools/worker_lab_adapter.py", dict(framework_files).get("tools/worker_lab_adapter.py", "")),
        )
        or framework_entrypoints.get("worker-lab-adapter") != "tools/worker_lab_adapter.py"
    ):
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "framework runtime closure is incomplete")
    for name in ("worker-lab", "local-model-bench"):
        if parsed_components[name][1] != "python-production-tree":
            raise AdapterError("INTEGRATION_IDENTITY_INVALID", "component production-tree scope differs")
    for relative, expected_digest in framework_files:
        installed_file = _contained_path(framework_root, Path(*PurePosixPath(relative).parts), directory=False)
        if digest(installed_file.read_bytes()) != expected_digest:
            raise AdapterError("INTEGRATION_IDENTITY_INVALID", "framework runtime dependency differs")
    declared_adapter = _contained_path(framework_root, Path("tools") / "worker_lab_adapter.py", directory=False)
    if not _path_equal(framework_root, adapter_path.parents[1]) or not _path_equal(declared_adapter, adapter_path):
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "adapter location differs from installation manifest")
    runtimes = _manifest_object(root["runtimes"], {"python", "codex"})
    python_raw = _manifest_object(runtimes["python"], {"path", "sha256", "version", "implementation", "architecture"})
    codex_raw = _manifest_object(runtimes["codex"], {"path", "sha256", "version"})
    python_path = _manifest_absolute_path(python_raw["path"])
    codex_path = _manifest_absolute_path(codex_raw["path"])
    integrity = _manifest_object(root["integrity"], {"algorithm", "file_set_algorithm", "path_policy"})
    if integrity != {
        "algorithm": "sha256",
        "file_set_algorithm": "acl-installed-file-set:v1",
        "path_policy": "installation-relative-no-traversal:v1",
    }:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installation integrity policy differs")
    return InstalledRuntime(
        manifest_path, installation_root, framework_root,
        digest([{"path": path, "sha256": value} for path, value in framework_files]),
        framework_files, dict(framework_files)["tools/worker_lab_adapter.py"],
        python_path, _digest(python_raw["sha256"], "Python digest"), _text(python_raw["version"], "Python version"),
        _text(python_raw["implementation"], "Python implementation"), _text(python_raw["architecture"], "Python architecture"),
        codex_path, _digest(codex_raw["sha256"], "Codex digest"), _text(codex_raw["version"], "Codex version"),
        policy["execution_authority"], participants,
    )


def _require_execution_policy(installed: InstalledRuntime, mode: str) -> None:
    if mode == "prepare":
        return
    if (
        installed.execution_authority != "ENABLED"
        or installed.participant_states.get("worker-lab") != "ACTIVE"
        or installed.participant_states.get("autonomous-worker-framework") != "ACTIVE"
    ):
        raise AdapterError("INTEGRATION_EXECUTION_DISABLED", "installation policy disables worker execution")


def _framework_runtime(installed: InstalledRuntime):
    runtime_path = _contained_path(installed.framework_root, Path("tools") / "codex_runtime.py", directory=False)
    if digest(runtime_path.read_bytes()) != dict(installed.framework_files)["tools/codex_runtime.py"]:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "framework runtime dependency differs")
    module_name = "worker_lab_adapter_codex_runtime"
    spec = importlib.util.spec_from_file_location(module_name, runtime_path)
    if spec is None or spec.loader is None:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "framework Codex runtime is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _manifest_object(value: Any, fields: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installation manifest fields are invalid")
    return value


def _manifest_relative_path(value: Any) -> Path:
    text = _text(value, "installation path")
    pure = PurePosixPath(text)
    if pure.is_absolute() or pure.as_posix() != text or text == "." or ".." in pure.parts or ":" in pure.parts[0] or "\\" in text:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installation path is invalid")
    return Path(*pure.parts)


def _manifest_absolute_path(value: Any) -> Path:
    path = Path(_text(value, "runtime path"))
    if not path.is_absolute() or ".." in path.parts:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "runtime path is invalid")
    return path


def _contained_path(root: Path, relative: Path, *, directory: bool) -> Path:
    try:
        root_resolved = root.resolve(strict=True)
        candidate = (root_resolved / relative).resolve(strict=True)
    except OSError as exc:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installed path is unavailable") from exc
    if not candidate.is_relative_to(root_resolved) or (candidate.is_dir() if directory else candidate.is_file()) is not True:
        raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installed path escapes its root")
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current /= part
        if getattr(os.lstat(current), "st_file_attributes", 0) & 0x400:
            raise AdapterError("INTEGRATION_IDENTITY_INVALID", "installed path uses a reparse point")
    return candidate


def _path_equal(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(os.path.normpath(str(right)))


if __name__ == "__main__":
    raise SystemExit(main())
