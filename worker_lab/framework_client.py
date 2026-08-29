from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .integration import (
    FRAMEWORK_CONTRACT_VERSION,
    InvocationOperation,
    InvocationRecord,
    InvocationState,
    RUNTIME_PROFILE,
)


ADAPTER_RELATIVE_PATH = "tools/worker_lab_adapter.py"
ADAPTER_REQUEST_SCHEMA = "worker-lab-framework-adapter-request:v1"
PINNED_FRAMEWORK_ROOT = Path(r"C:\Users\MineTrackerWorker\repos\autonomous-worker-framework")
PINNED_FRAMEWORK_COMMIT = "2d8c93312103015125f0eef9e2afdc697a45d244"
PINNED_ADAPTER_DIGEST = "sha256:4014b58bb47689ad0dbb9e13b01a61a60012793c611d371765a2a87975f8d117"
PYTHON_EXECUTABLE = Path(r"C:\Program Files\Python312\python.exe")
PYTHON_DIGEST = "sha256:4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a"
PYTHON_VERSION = "3.12.10"
PYTHON_IMPLEMENTATION = "CPython"
PYTHON_ARCHITECTURE = "AMD64"
AUDITED_CODEX_VERSION = "0.149.1"
MAX_REQUEST_BYTES = 262_144
MAX_PROMPT_BYTES = 32_768
MAX_RESPONSE_BYTES = 65_536
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
AdapterRunner = Callable[[tuple[str, ...], bytes], bytes]
_MODE_STATES = {
    "prepare": InvocationState.PREPARED,
    "preflight": InvocationState.AUTHORIZED,
    "execute-read-only": InvocationState.DISPATCHING,
}
_MODE_RESPONSE_FIELDS = {
    "prepare": frozenset({"invocation_digest", "prompt_digest", "runtime_identity"}),
    "preflight": frozenset({"invocation_digest", "prompt_digest", "runtime_identity"}),
    "execute-read-only": frozenset({
        "invocation_digest", "prompt_digest", "runtime_identity", "proposal_digest",
        "output_digest", "proposal_content", "stdout_bytes", "stderr_bytes",
    }),
}


@dataclass(frozen=True)
class FrameworkConfiguration:
    framework_root: Path
    framework_commit: str
    python_executable: Path
    adapter_digest: str
    codex_launcher: Path
    codex_launcher_digest: str


@dataclass(frozen=True)
class FrameworkIdentityEvidence:
    framework_root: Path
    framework_head: str
    framework_status: str
    adapter_path: Path
    adapter_worktree_digest: str
    adapter_blob_digest: str
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
    worker_lab_head: str
    worker_lab_status: tuple[str, ...]


def pinned_framework_configuration(
    *, codex_launcher: Path, codex_launcher_digest: str,
) -> FrameworkConfiguration:
    """Return the reviewed local framework identity plus separately audited launcher identity."""
    return FrameworkConfiguration(
        PINNED_FRAMEWORK_ROOT, PINNED_FRAMEWORK_COMMIT, PYTHON_EXECUTABLE,
        PINNED_ADAPTER_DIGEST, codex_launcher, codex_launcher_digest,
    )


def fixed_command(
    config: FrameworkConfiguration,
    mode: str,
    *,
    evidence: FrameworkIdentityEvidence,
) -> tuple[str, ...]:
    if mode not in {"prepare", "preflight", "execute-read-only"}:
        raise LabValidationError("INTEGRATION_OPERATION_INVALID", "unsupported adapter mode")
    _verify_pinned_framework(config)
    verify_configuration(config, evidence)
    return (
        str(config.python_executable), "-I", "-B", str(config.framework_root / ADAPTER_RELATIVE_PATH),
        mode, "--protocol", FRAMEWORK_CONTRACT_VERSION,
    )


def runtime_identity(
    config: FrameworkConfiguration,
    invocation: InvocationRecord,
    *,
    evidence: FrameworkIdentityEvidence,
) -> str:
    if invocation.operation is not InvocationOperation.READ_ONLY_PROPOSAL or invocation.sandbox_mode != "read-only":
        raise LabValidationError("INTEGRATION_OPERATION_INVALID", "Batch 3C supports read-only invocation only")
    verify_configuration(config, evidence)
    command_base = (
        "python", "-I", "-B", ADAPTER_RELATIVE_PATH,
        ("prepare", "preflight", "execute-read-only"), "--protocol", FRAMEWORK_CONTRACT_VERSION,
    )
    return canonical_digest({
        "schema_version": "worker-lab-runtime-identity:v1",
        "framework_commit": config.framework_commit,
        "adapter_digest": config.adapter_digest,
        "adapter_contract_version": FRAMEWORK_CONTRACT_VERSION,
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


def verify_configuration(config: FrameworkConfiguration, evidence: FrameworkIdentityEvidence) -> None:
    if not _SHA_RE.fullmatch(config.framework_commit):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "framework commit is invalid")
    for value in (config.adapter_digest, config.codex_launcher_digest):
        if not _DIGEST_RE.fullmatch(value):
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "trusted digest is invalid")
    expected_adapter = config.framework_root / ADAPTER_RELATIVE_PATH
    expected = (
        _path_equal(evidence.framework_root, config.framework_root),
        evidence.framework_head == config.framework_commit,
        evidence.framework_status == "",
        _path_equal(evidence.adapter_path, expected_adapter),
        evidence.adapter_worktree_digest == config.adapter_digest,
        evidence.adapter_blob_digest == config.adapter_digest,
        _path_equal(evidence.python_path, config.python_executable)
        and _path_equal(config.python_executable, PYTHON_EXECUTABLE),
        evidence.python_digest == PYTHON_DIGEST,
        evidence.python_version == PYTHON_VERSION,
        evidence.python_implementation == PYTHON_IMPLEMENTATION,
        evidence.python_architecture == PYTHON_ARCHITECTURE,
        _path_equal(evidence.codex_launcher_path, config.codex_launcher),
        evidence.codex_launcher_digest == config.codex_launcher_digest,
        evidence.codex_version == AUDITED_CODEX_VERSION,
    )
    if not all(expected):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "framework runtime identity differs")


def _verify_pinned_framework(config: FrameworkConfiguration) -> None:
    if (
        not _path_equal(config.framework_root, PINNED_FRAMEWORK_ROOT)
        or config.framework_commit != PINNED_FRAMEWORK_COMMIT
        or config.adapter_digest != PINNED_ADAPTER_DIGEST
        or not _path_equal(config.python_executable, PYTHON_EXECUTABLE)
    ):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "framework configuration is not the reviewed milestone")


def inspect_configuration(config: FrameworkConfiguration) -> FrameworkIdentityEvidence:
    root = _canonical_unlinked(config.framework_root)
    python_path = _canonical_unlinked(config.python_executable)
    adapter_path = _canonical_unlinked(root / ADAPTER_RELATIVE_PATH)
    codex_path = _canonical_unlinked(config.codex_launcher)
    head = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all").decode("utf-8")
    blob = _git(root, "show", f"{config.framework_commit}:{ADAPTER_RELATIVE_PATH}")
    version = _run_python_identity(python_path)
    evidence = FrameworkIdentityEvidence(
        root, head, status, adapter_path, _bytes_digest(adapter_path.read_bytes()),
        _bytes_digest(blob), python_path, _bytes_digest(python_path.read_bytes()),
        version[0], version[1], version[2], codex_path, _bytes_digest(codex_path.read_bytes()),
        _read_launcher_version(codex_path),
    )
    verify_configuration(config, evidence)
    return evidence


def inspect_worker_lab_identity(root: Path, expected_commit: str) -> WorkerLabIdentityEvidence:
    canonical_root = _canonical_unlinked(root)
    head = _git(canonical_root, "rev-parse", "HEAD").decode("ascii").strip()
    status = tuple(
        line for line in _git(
            canonical_root, "status", "--porcelain=v1", "--untracked-files=all"
        ).decode("utf-8").splitlines() if line
    )
    evidence = WorkerLabIdentityEvidence(canonical_root, head, status)
    if head != expected_commit:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "Worker Lab commit differs")
    allowed = ("?? docs/8_27_26_ChatGPT_History",)
    if any(line not in allowed for line in status) or len(status) != len(set(status)):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "Worker Lab working tree differs")
    return evidence


def verify_worker_lab_identity(record: InvocationRecord, evidence: WorkerLabIdentityEvidence) -> None:
    if evidence.worker_lab_head != record.worker_lab_commit:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "Worker Lab evidence differs")
    allowed = ("?? docs/8_27_26_ChatGPT_History",)
    if any(line not in allowed for line in evidence.worker_lab_status):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "Worker Lab working tree differs")


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


def _git(root: Path, *args: str) -> bytes:
    environment = {"PATH": os.environ.get("PATH", ""), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    process = subprocess.run(
        ["git", *args], cwd=root, env=environment, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
    )
    if process.returncode != 0:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "framework Git identity check failed")
    return process.stdout


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


def _read_launcher_version(executable: Path) -> str:
    """Verify only the pinned launcher version; authentication is never queried here."""
    process = subprocess.run(
        [str(executable), "--version"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=30, check=False, encoding="utf-8",
    )
    expected = f"codex-cli {AUDITED_CODEX_VERSION}"
    if process.returncode != 0 or expected not in process.stdout.strip():
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "Codex launcher version differs")
    return AUDITED_CODEX_VERSION


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
