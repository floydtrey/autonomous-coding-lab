from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .installation_manifest import load_installation_manifest
from .integration import (
    FRAMEWORK_CONTRACT_VERSION,
    WORKSPACE_WRITE_FRAMEWORK_CONTRACT_VERSION,
    InvocationOperation,
    InvocationRecord,
    InvocationState,
    RUNTIME_PROFILE,
)


ADAPTER_REQUEST_SCHEMA = "worker-lab-framework-adapter-request:v2"
WORKSPACE_WRITE_ADAPTER_REQUEST_SCHEMA = "worker-lab-framework-workspace-write-request:v1"
ADAPTER_RELATIVE_PATH = "tools/worker_lab_adapter.py"
MAX_REQUEST_BYTES = 262_144
MAX_PROMPT_BYTES = 32_768
MAX_RESPONSE_BYTES = 65_536
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
AdapterRunner = Callable[[tuple[str, ...], bytes], bytes]
_MODE_STATES = {
    "prepare": InvocationState.PREPARED,
    "preflight": InvocationState.AUTHORIZED,
    "execute-read-only": InvocationState.DISPATCHING,
    "execute-workspace-write": InvocationState.DISPATCHING,
}
_MODE_RESPONSE_FIELDS = {
    "prepare": frozenset({"invocation_digest", "prompt_digest", "runtime_identity"}),
    "preflight": frozenset({"invocation_digest", "prompt_digest", "runtime_identity"}),
    "execute-read-only": frozenset({
        "invocation_digest", "prompt_digest", "runtime_identity", "proposal_digest",
        "output_digest", "proposal_content", "stdout_bytes", "stderr_bytes",
    }),
    "execute-workspace-write": frozenset({
        "invocation_digest", "prompt_digest", "runtime_identity", "task_digest",
        "context_digest", "candidate_digest", "changed_paths",
    }),
}


@dataclass(frozen=True)
class FrameworkConfiguration:
    manifest_path: Path
    framework_root: Path
    framework_installation_digest: str
    framework_files: tuple[tuple[str, str], ...]
    python_executable: Path
    python_digest: str
    python_version: str
    python_implementation: str
    python_architecture: str
    adapter_digest: str
    codex_launcher: Path
    codex_launcher_digest: str
    codex_version: str
    execution_authority: str
    participant_states: Mapping[str, str]


@dataclass(frozen=True)
class FrameworkIdentityEvidence:
    framework_root: Path
    framework_installation_digest: str
    framework_files: tuple[tuple[str, str], ...]
    adapter_path: Path
    adapter_digest: str
    python_path: Path
    python_digest: str
    python_version: str
    python_implementation: str
    python_architecture: str
    codex_launcher_path: Path
    codex_launcher_digest: str
    codex_version: str


@dataclass(frozen=True)
class WorkerLabIdentityEvidence:
    worker_lab_root: Path
    worker_lab_installation_digest: str


def pinned_framework_configuration(
    *, manifest_path: Path | None = None,
) -> FrameworkConfiguration:
    """Load the reviewed installed-content and runtime identity without Git metadata."""
    manifest = load_installation_manifest(manifest_path)
    framework = manifest.components["autonomous-worker-framework"]
    framework_files = tuple((item.path, item.digest) for item in framework.files)
    adapter_digest = dict(framework_files)[ADAPTER_RELATIVE_PATH]
    return FrameworkConfiguration(
        manifest.path, manifest.installation_root / framework.root,
        framework.installation_digest, framework_files,
        manifest.python.path, manifest.python.digest, manifest.python.version,
        manifest.python.implementation or "", manifest.python.architecture or "",
        adapter_digest, manifest.codex.path, manifest.codex.digest, manifest.codex.version,
        manifest.execution_authority, manifest.participants,
    )


def fixed_command(
    config: FrameworkConfiguration,
    mode: str,
    *,
    evidence: FrameworkIdentityEvidence,
) -> tuple[str, ...]:
    if mode not in {"prepare", "preflight", "execute-read-only", "execute-workspace-write"}:
        raise LabValidationError("INTEGRATION_OPERATION_INVALID", "unsupported adapter mode")
    _verify_pinned_framework(config)
    verify_configuration(config, evidence)
    if mode != "prepare":
        _require_execution_enabled(config)
    return (
        str(config.python_executable), "-I", "-B", str(config.framework_root / ADAPTER_RELATIVE_PATH),
        mode, "--protocol", _adapter_protocol(mode),
    )


def _adapter_protocol(mode: str) -> str:
    return (
        WORKSPACE_WRITE_FRAMEWORK_CONTRACT_VERSION
        if mode == "execute-workspace-write"
        else FRAMEWORK_CONTRACT_VERSION
    )


def runtime_identity(
    config: FrameworkConfiguration,
    invocation: InvocationRecord,
    *,
    evidence: FrameworkIdentityEvidence,
) -> str:
    if invocation.operation is InvocationOperation.READ_ONLY_PROPOSAL:
        expected_protocol = FRAMEWORK_CONTRACT_VERSION
        modes = ("prepare", "preflight", "execute-read-only")
    elif invocation.operation is InvocationOperation.WORKSPACE_WRITE_CODE_TASK:
        expected_protocol = WORKSPACE_WRITE_FRAMEWORK_CONTRACT_VERSION
        modes = ("execute-workspace-write",)
    else:
        raise LabValidationError("INTEGRATION_OPERATION_INVALID", "invocation operation is unsupported")
    if invocation.framework_contract_version != expected_protocol:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "invocation adapter contract differs")
    verify_configuration(config, evidence)
    command_base = (
        "python", "-I", "-B", ADAPTER_RELATIVE_PATH,
        modes, "--protocol", expected_protocol,
    )
    return canonical_digest({
        "schema_version": "worker-lab-runtime-identity:v2",
        "framework_installation_digest": config.framework_installation_digest,
        "framework_runtime_files": [
            {"path": path, "sha256": digest} for path, digest in config.framework_files
        ],
        "adapter_digest": config.adapter_digest,
        "adapter_contract_version": expected_protocol,
        "python_digest": evidence.python_digest,
        "python_version": evidence.python_version,
        "python_implementation": evidence.python_implementation,
        "python_architecture": evidence.python_architecture,
        "codex_launcher_digest": evidence.codex_launcher_digest,
        "codex_version": evidence.codex_version,
        "environment_policy": "framework-sanitized-environment:v1",
        "runtime_profile": RUNTIME_PROFILE,
        "operation": str(invocation.operation),
        "sandbox": invocation.sandbox_mode,
        "windows_sandbox": "elevated",
        "model": invocation.model,
        "reasoning_effort": invocation.reasoning_effort,
        "timeout_seconds": invocation.timeout_seconds,
        "command_digest": canonical_digest(command_base),
    })


def call_adapter(
    record: InvocationRecord,
    config: FrameworkConfiguration,
    mode: str,
    *,
    prompt: str,
    evidence: FrameworkIdentityEvidence,
    worker_lab_evidence: WorkerLabIdentityEvidence,
    runner: AdapterRunner | None = None,
) -> bytes:
    if runner is None:
        raise LabValidationError("INTEGRATION_EXECUTION_DISABLED", "an injected adapter runner is required")
    if mode not in _MODE_STATES or record.state is not _MODE_STATES[mode]:
        raise LabValidationError("INTEGRATION_AUTHORIZATION_INVALID", "adapter mode differs from invocation custody")
    if mode != "prepare":
        _require_execution_enabled(config)
    prompt_bytes = _bounded_utf8(prompt, MAX_PROMPT_BYTES, "prompt")
    if _bytes_digest(prompt_bytes) != record.prompt_digest:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "prompt differs from sealed invocation")
    verify_worker_lab_identity(record, worker_lab_evidence)
    command = fixed_command(config, mode, evidence=evidence)
    payload = canonical_json({
        "schema_version": ADAPTER_REQUEST_SCHEMA,
        "invocation": record.to_dict(),
        "prompt": prompt,
    }).encode("utf-8")
    if len(payload) > MAX_REQUEST_BYTES:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter request exceeds limit")
    response = runner(command, payload)
    if not isinstance(response, bytes) or not response or len(response) > MAX_RESPONSE_BYTES:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response is invalid")
    try:
        decoded = json.loads(response.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response is not UTF-8 JSON") from exc
    try:
        canonical_response = canonical_json(decoded).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response is not canonical") from exc
    if (
        not isinstance(decoded, Mapping)
        or set(decoded) != _MODE_RESPONSE_FIELDS[mode]
        or canonical_response != response
    ):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response must be an object")
    if decoded.get("invocation_digest") != record.identity_digest() or decoded.get("prompt_digest") != record.prompt_digest:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter response does not bind invocation")
    expected_runtime = runtime_identity(config, record, evidence=evidence)
    if decoded.get("runtime_identity") != expected_runtime:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter runtime identity differs")
    return response


def call_workspace_write_adapter(
    record: InvocationRecord,
    config: FrameworkConfiguration,
    *,
    prompt: str,
    workspace_write: Mapping[str, object],
    evidence: FrameworkIdentityEvidence,
    worker_lab_evidence: WorkerLabIdentityEvidence,
    runner: AdapterRunner | None = None,
) -> bytes:
    """Call only the separately versioned write bridge with a sealed contract."""
    if runner is None:
        raise LabValidationError("INTEGRATION_EXECUTION_DISABLED", "an injected adapter runner is required")
    if (
        record.operation is not InvocationOperation.WORKSPACE_WRITE_CODE_TASK
        or record.state is not InvocationState.DISPATCHING
        or record.framework_contract_version != WORKSPACE_WRITE_FRAMEWORK_CONTRACT_VERSION
    ):
        raise LabValidationError("INTEGRATION_AUTHORIZATION_INVALID", "workspace-write invocation custody differs")
    if not isinstance(workspace_write, Mapping):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "workspace-write task contract is invalid")
    _require_execution_enabled(config)
    prompt_bytes = _bounded_utf8(prompt, MAX_PROMPT_BYTES, "prompt")
    if _bytes_digest(prompt_bytes) != record.prompt_digest:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "prompt differs from sealed invocation")
    verify_worker_lab_identity(record, worker_lab_evidence)
    command = fixed_command(config, "execute-workspace-write", evidence=evidence)
    payload = canonical_json({
        "schema_version": WORKSPACE_WRITE_ADAPTER_REQUEST_SCHEMA,
        "invocation": record.to_dict(),
        "prompt": prompt,
        "workspace_write": dict(workspace_write),
    }).encode("utf-8")
    if len(payload) > MAX_REQUEST_BYTES:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "workspace-write request exceeds limit")
    response = runner(command, payload)
    if not isinstance(response, bytes) or not response or len(response) > MAX_RESPONSE_BYTES:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response is invalid")
    try:
        decoded = json.loads(response.decode("utf-8"))
        canonical_response = canonical_json(decoded).encode("utf-8")
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response is not canonical JSON") from exc
    if not isinstance(decoded, Mapping) or set(decoded) != _MODE_RESPONSE_FIELDS["execute-workspace-write"] or canonical_response != response:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "workspace-write response fields are invalid")
    if (
        decoded.get("invocation_digest") != record.identity_digest()
        or decoded.get("prompt_digest") != record.prompt_digest
        or decoded.get("runtime_identity") != runtime_identity(config, record, evidence=evidence)
        or decoded.get("changed_paths") != list(record.writable_paths)
    ):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "workspace-write response differs from invocation")
    for field in ("task_digest", "context_digest", "candidate_digest"):
        if not _DIGEST_RE.fullmatch(str(decoded.get(field))):
            raise LabValidationError("INTEGRATION_RESULT_INVALID", "workspace-write response digest is invalid")
    return response


def verify_configuration(config: FrameworkConfiguration, evidence: FrameworkIdentityEvidence) -> None:
    for value in (
        config.framework_installation_digest, config.adapter_digest, config.python_digest,
        config.codex_launcher_digest,
    ):
        if not _DIGEST_RE.fullmatch(value):
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "trusted digest is invalid")
    expected_adapter = config.framework_root / ADAPTER_RELATIVE_PATH
    expected = (
        _path_equal(evidence.framework_root, config.framework_root),
        evidence.framework_installation_digest == config.framework_installation_digest,
        evidence.framework_files == config.framework_files,
        _path_equal(evidence.adapter_path, expected_adapter),
        evidence.adapter_digest == config.adapter_digest,
        _path_equal(evidence.python_path, config.python_executable),
        evidence.python_digest == config.python_digest,
        evidence.python_version == config.python_version,
        evidence.python_implementation == config.python_implementation,
        evidence.python_architecture == config.python_architecture,
        _path_equal(evidence.codex_launcher_path, config.codex_launcher),
        evidence.codex_launcher_digest == config.codex_launcher_digest,
        evidence.codex_version == config.codex_version,
    )
    if not all(expected):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "framework runtime identity differs")


def _verify_pinned_framework(config: FrameworkConfiguration) -> None:
    if config != pinned_framework_configuration(manifest_path=config.manifest_path):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "framework configuration is not the reviewed milestone")


def inspect_configuration(config: FrameworkConfiguration) -> FrameworkIdentityEvidence:
    _verify_pinned_framework(config)
    root = _canonical_unlinked(config.framework_root)
    python_path = _canonical_unlinked(config.python_executable)
    adapter_path = _canonical_unlinked(root / ADAPTER_RELATIVE_PATH)
    codex_path = _canonical_unlinked(config.codex_launcher)
    actual_files = tuple(
        (
            relative,
            _bytes_digest(_canonical_unlinked(root / Path(*PurePosixPath(relative).parts)).read_bytes()),
        )
        for relative, _ in config.framework_files
    )
    identity = canonical_digest([
        {"path": path, "sha256": digest} for path, digest in actual_files
    ])
    version = _run_python_identity(python_path)
    evidence = FrameworkIdentityEvidence(
        root, identity, actual_files, adapter_path, _bytes_digest(adapter_path.read_bytes()),
        python_path, _bytes_digest(python_path.read_bytes()),
        version[0], version[1], version[2], codex_path, _bytes_digest(codex_path.read_bytes()),
        _read_launcher_version(codex_path, config.codex_version),
    )
    verify_configuration(config, evidence)
    return evidence


def inspect_worker_lab_identity(root: Path, expected_digest: str) -> WorkerLabIdentityEvidence:
    manifest = load_installation_manifest()
    component = manifest.components["worker-lab"]
    canonical_root = _canonical_unlinked(root)
    configured_root = _canonical_unlinked(manifest.installation_root / component.root)
    if not _path_equal(canonical_root, configured_root):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "Worker Lab installation location differs")
    evidence = WorkerLabIdentityEvidence(canonical_root, component.installation_digest)
    if component.installation_digest != expected_digest:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "Worker Lab content differs")
    return evidence


def installed_worker_lab_identity(root: Path) -> str:
    """Identify the installed Worker Lab package from the verified manifest file set."""
    manifest = load_installation_manifest()
    digest = manifest.components["worker-lab"].installation_digest
    return inspect_worker_lab_identity(root, digest).worker_lab_installation_digest


def verify_worker_lab_identity(record: InvocationRecord, evidence: WorkerLabIdentityEvidence) -> None:
    if evidence.worker_lab_installation_digest != record.worker_lab_installation_digest:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "Worker Lab evidence differs")


def _canonical_unlinked(path: Path) -> Path:
    if not path.is_absolute() or not path.exists():
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "configured path is unavailable")
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "configured path is substituted")
    current = Path(resolved.anchor)
    for part in resolved.parts[1:]:
        current /= part
        attributes = getattr(os.lstat(current), "st_file_attributes", 0)
        if attributes & 0x400:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "configured path uses a reparse point")
    return resolved


def _path_equal(left: Path, right: Path) -> bool:
    """Compare configured Windows paths without treating case spelling as identity drift.

    `inspect_configuration` separately resolves every on-disk component and rejects
    reparse substitutions before it constructs evidence.  This helper only avoids
    a false mismatch caused by Windows' case-insensitive canonical spelling.
    """
    return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(os.path.normpath(str(right)))


def _run_python_identity(executable: Path) -> tuple[str, str, str]:
    script = "import platform,sys;print(sys.version.split()[0]);print(platform.python_implementation());print(platform.machine())"
    process = subprocess.run(
        [str(executable), "-I", "-B", "-c", script], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False, encoding="utf-8",
    )
    values = process.stdout.splitlines()
    if process.returncode != 0 or len(values) != 3:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "Python identity check failed")
    return values[0], values[1], values[2]


def _read_launcher_version(executable: Path, expected_version: str) -> str:
    """Verify only the pinned launcher version; authentication is never queried here."""
    process = subprocess.run(
        [str(executable), "--version"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=30, check=False, encoding="utf-8",
    )
    expected = f"codex-cli {expected_version}"
    if process.returncode != 0 or expected not in process.stdout.strip():
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "Codex launcher version differs")
    return expected_version


def _require_execution_enabled(config: FrameworkConfiguration) -> None:
    if (
        config.execution_authority != "ENABLED"
        or config.participant_states.get("worker-lab") != "ACTIVE"
        or config.participant_states.get("autonomous-worker-framework") != "ACTIVE"
    ):
        raise LabValidationError("INTEGRATION_EXECUTION_DISABLED", "installation policy disables worker execution")


def _bounded_utf8(value: object, limit: int, name: str) -> bytes:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", f"{name} is invalid")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", f"{name} is not UTF-8") from exc
    if len(encoded) > limit:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", f"{name} exceeds limit")
    return encoded


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()
