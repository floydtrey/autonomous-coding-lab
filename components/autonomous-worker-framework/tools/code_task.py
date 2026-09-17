from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

try:
    from tools.consumer_profile import (
        ConsumerProfile,
        ValidationCommand,
        WorkerContextPacket,
        verify_context_packet,
    )
    from tools.repository_state import candidate_content_digest, changed_paths, repository_head
    from tools.repository_handoff import RepositoryHandoff, build_repository_handoff
    from tools.worker_result import (
        BoundaryResult,
        ValidationResult,
        ValidationStage,
        WorkerResult,
        WorkerStatus,
        validate_worker_result,
    )
    from tools.worker_runtime import WorkerExecution, WorkerRequest
except ModuleNotFoundError:  # direct execution support
    from consumer_profile import (  # type: ignore
        ConsumerProfile, ValidationCommand, WorkerContextPacket,
        verify_context_packet,
    )
    from repository_state import candidate_content_digest, changed_paths, repository_head  # type: ignore
    from repository_handoff import RepositoryHandoff, build_repository_handoff  # type: ignore
    from worker_result import (  # type: ignore
        BoundaryResult, ValidationResult, ValidationStage, WorkerResult, WorkerStatus,
        validate_worker_result,
    )
    from worker_runtime import WorkerExecution, WorkerRequest  # type: ignore


CODE_TASK_VERSION = "code-task:v2"


class CodeTaskError(RuntimeError):
    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


@dataclass(frozen=True)
class CodeTaskContract:
    version: str
    task_id: str
    consumer: str
    context_digest: str
    repository_head: str
    objective: str
    expected_changed_paths: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    quick_validation: tuple[ValidationCommand, ...]
    allowed_writable_paths: tuple[str, ...]
    required_artifact_paths: tuple[str, ...]
    allow_noop: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "task_id": self.task_id,
            "consumer": self.consumer,
            "context_digest": self.context_digest,
            "repository_head": self.repository_head,
            "objective": self.objective,
            "expected_changed_paths": list(self.expected_changed_paths),
            "acceptance_criteria": list(self.acceptance_criteria),
            "quick_validation": [item.to_dict() for item in self.quick_validation],
            "allowed_writable_paths": list(self.allowed_writable_paths),
            "required_artifact_paths": list(self.required_artifact_paths),
            "allow_noop": self.allow_noop,
        }

    def digest(self) -> str:
        encoded = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CodeTaskResult:
    task_digest: str
    context_digest: str
    repository_head: str
    changed_paths: tuple[str, ...]
    worker_response: str
    quick_validation: tuple[tuple[str, str], ...]
    full_validation: tuple[tuple[str, str], ...]
    ready_for_handoff: bool

    def to_json(self, *, pretty: bool = False) -> str:
        value = asdict(self)
        options: dict[str, Any] = {"sort_keys": True}
        if pretty:
            options["indent"] = 2
        else:
            options["separators"] = (",", ":")
        return json.dumps(value, **options)


@dataclass(frozen=True)
class CodeTaskHandoff:
    """The framework-owned candidate proof produced after a successful code task."""

    worker_result: WorkerResult
    repository_handoff: RepositoryHandoff


Executor = Callable[[WorkerRequest], WorkerExecution]


def build_code_task(
    packet: WorkerContextPacket,
    *,
    task_id: str,
    objective: str,
    expected_changed_paths: Sequence[str],
    acceptance_criteria: Sequence[str],
    quick_validation: Sequence[ValidationCommand],
    allowed_writable_paths: Sequence[str] | None = None,
    required_artifact_paths: Sequence[str] = (),
    allow_noop: bool = False,
) -> CodeTaskContract:
    paths = tuple(expected_changed_paths)
    allowed = tuple(packet.allowed_paths if allowed_writable_paths is None else allowed_writable_paths)
    artifacts = tuple(required_artifact_paths)
    criteria = tuple(" ".join(item.split()) for item in acceptance_criteria)
    clean_objective = " ".join(objective.split())
    if not task_id.strip() or not clean_objective or not criteria or not all(criteria):
        raise CodeTaskError("CODE_TASK_INVALID", "task identity, objective, and acceptance criteria are required")
    if paths != tuple(sorted(set(paths))):
        raise CodeTaskError("CODE_TASK_SCOPE_INVALID", "expected changed paths must be sorted and unique")
    if not set(paths).issubset(packet.allowed_paths):
        raise CodeTaskError("CODE_TASK_SCOPE_INVALID", "expected changed paths exceed context scope")
    if (not allowed or allowed != tuple(sorted(set(allowed))) or not set(allowed) <= set(packet.allowed_paths)
            or not set(paths + artifacts) <= set(allowed) or artifacts != tuple(sorted(set(artifacts)))
            or type(allow_noop) is not bool or (allow_noop and paths)):
        raise CodeTaskError("CODE_TASK_SCOPE_INVALID", "output obligations differ from allowed scope or no-op permission")
    if not quick_validation:
        raise CodeTaskError("CODE_TASK_INVALID", "quick validation is required")
    return CodeTaskContract(
        CODE_TASK_VERSION,
        task_id.strip(),
        packet.consumer,
        packet.digest(),
        packet.repository_head,
        clean_objective,
        paths,
        criteria,
        tuple(quick_validation),
        allowed,
        artifacts,
        allow_noop,
    )


def run_code_task(
    contract: CodeTaskContract,
    packet: WorkerContextPacket,
    *,
    repo_root: Path,
    framework_repo: Path,
    profile: ConsumerProfile,
    executor: Executor | None = None,
) -> CodeTaskResult:
    _verify_contract(contract, packet)
    verify_context_packet(packet, repo_root, profile=profile)
    if executor is None:
        raise CodeTaskError(
            "CODE_TASK_EXECUTOR_REQUIRED",
            "code-task execution requires an injected provider executor",
        )
    readable_paths = tuple(
        sorted(
            {
                *(item.path for item in packet.authority_files),
                *(item.path for item in packet.task_files),
                *contract.allowed_writable_paths,
            }
        )
    )
    execution = executor(
        WorkerRequest(
            prompt=_implementation_prompt(contract, packet),
            target_repo=repo_root,
            framework_repo=framework_repo,
            sandbox="workspace-write",
            readable_paths=readable_paths,
            writable_paths=contract.allowed_writable_paths,
        )
    )
    if repository_head(repo_root) != contract.repository_head:
        raise CodeTaskError("CODE_TASK_HEAD_CHANGED", "worker changed repository HEAD")
    observed = tuple(changed_paths(repo_root, contract.repository_head))
    if (not set(observed) <= set(contract.allowed_writable_paths)
            or not set(contract.expected_changed_paths) <= set(observed)
            or (not observed and not contract.allow_noop)):
        raise CodeTaskError(
            "CODE_TASK_BOUNDARY_FAILED",
            f"candidate violates allowed paths, required changes, or no-op permission: {observed!r}",
        )
    _verify_artifacts(contract, repo_root)
    _git_diff_check(repo_root)
    quick = _run_validation(repo_root, contract.quick_validation, "CODE_TASK_QUICK_FAILED")
    full = _run_validation(repo_root, packet.full_validation, "CODE_TASK_FULL_FAILED")
    return CodeTaskResult(
        task_digest=contract.digest(),
        context_digest=packet.digest(),
        repository_head=contract.repository_head,
        changed_paths=observed,
        worker_response=execution.stdout.strip(),
        quick_validation=quick,
        full_validation=full,
        ready_for_handoff=True,
    )


def build_code_task_handoff(
    contract: CodeTaskContract,
    result: CodeTaskResult,
    *,
    repo_root: Path,
) -> CodeTaskHandoff:
    """Convert a completed code-task result into independently rechecked handoff proof."""
    if (
        result.task_digest != contract.digest()
        or result.context_digest != contract.context_digest
        or result.repository_head != contract.repository_head
        or not set(result.changed_paths) <= set(contract.allowed_writable_paths)
        or not set(contract.expected_changed_paths) <= set(result.changed_paths)
        or (not result.changed_paths and not contract.allow_noop)
        or not result.ready_for_handoff
    ):
        raise CodeTaskError("CODE_TASK_RESULT_INVALID", "code-task result differs from its sealed contract")
    _verify_artifacts(contract, repo_root)
    candidate_digest = candidate_content_digest(repo_root, result.changed_paths)
    worker_result = WorkerResult(
        contract_version="worker-result:v2" if not result.changed_paths else "worker-result:v1",
        task_id=contract.task_id,
        consumer=contract.consumer,
        task_contract_digest=contract.digest(),
        base_sha=contract.repository_head,
        candidate_sha=None,
        candidate_content_digest=candidate_digest,
        workspace_state="dirty-candidate" if result.changed_paths else "clean",
        changed_paths=result.changed_paths,
        patch_boundary=BoundaryResult("pass"),
        quick_validation=ValidationResult(
            "pass",
            tuple(ValidationStage(name, "pass") for name, _ in result.quick_validation),
        ),
        full_validation=ValidationResult(
            "pass",
            tuple(ValidationStage(name, "pass") for name, _ in result.full_validation),
        ),
        worker=WorkerStatus("pass"),
        first_failure=None,
        ready_for_repository_handoff=True,
    )
    validate_worker_result(worker_result)
    return CodeTaskHandoff(worker_result, build_repository_handoff(worker_result, repo_root))


def _verify_contract(contract: CodeTaskContract, packet: WorkerContextPacket) -> None:
    if contract.version != CODE_TASK_VERSION:
        raise CodeTaskError("CODE_TASK_INVALID", "unsupported code task version")
    if contract.consumer != packet.consumer or contract.context_digest != packet.digest():
        raise CodeTaskError("CODE_TASK_CONTEXT_MISMATCH", "task does not match context packet")
    if contract.repository_head != packet.repository_head:
        raise CodeTaskError("CODE_TASK_CONTEXT_MISMATCH", "task and context repository heads differ")
    if (not set(contract.allowed_writable_paths).issubset(packet.allowed_paths)
            or not set(contract.expected_changed_paths + contract.required_artifact_paths) <= set(contract.allowed_writable_paths)
            or type(contract.allow_noop) is not bool or (contract.allow_noop and contract.expected_changed_paths)):
        raise CodeTaskError("CODE_TASK_SCOPE_INVALID", "task paths exceed context scope")


def _verify_artifacts(contract: CodeTaskContract, root: Path) -> None:
    for relative in contract.required_artifact_paths:
        target = root
        for part in Path(relative).parts:
            target = target / part
            if target.is_symlink() or target.is_junction():
                raise CodeTaskError("CODE_TASK_OUTPUT_MISSING", "required artifact traverses a link")
        if not target.is_file():
            raise CodeTaskError("CODE_TASK_OUTPUT_MISSING", f"required artifact missing: {relative}")


def _implementation_prompt(contract: CodeTaskContract, packet: WorkerContextPacket) -> str:
    authority = "\n".join(f"- {item.path}" for item in packet.authority_files)
    context = "\n".join(f"- {item.path}" for item in packet.task_files) or "- none"
    paths = "\n".join(f"- {item}" for item in contract.allowed_writable_paths)
    criteria = "\n".join(f"- {item}" for item in contract.acceptance_criteria)
    invariants = "\n".join(f"- {item}" for item in packet.product_invariants)
    return (
        f"Implement exact code task {contract.task_id} at repository HEAD {contract.repository_head}.\n"
        f"Task digest: {contract.digest()}\nContext digest: {packet.digest()}\n"
        f"Objective: {contract.objective}\n\nRead authority first:\n{authority}\n\n"
        f"Read-only supporting files:\n{context}\n\n"
        f"You may modify only these paths (permission does not require mutation):\n{paths}\n\n"
        f"Required changes: {contract.expected_changed_paths!r}\n"
        f"Required existing files: {contract.required_artifact_paths!r}\n"
        f"Unchanged workspace permitted if all criteria pass: {contract.allow_noop}\n\n"
        f"Acceptance criteria:\n{criteria}\n\nInvariants:\n{invariants}\n\n"
        "Do not commit, push, alter Git configuration, or access GitHub. Make the smallest implementation that satisfies the criteria. Run only focused tests relevant to the change and report what you changed."
    )


def _git_diff_check(root: Path) -> None:
    process = subprocess.run(
        ("git", "diff", "--check"), cwd=root, capture_output=True, text=True, encoding="utf-8", check=False
    )
    if process.returncode:
        raise CodeTaskError("CODE_TASK_DIFF_FAILED", process.stdout.strip() or process.stderr.strip())


def _run_validation(
    root: Path, commands: Sequence[ValidationCommand], failure_code: str
) -> tuple[tuple[str, str], ...]:
    results: list[tuple[str, str]] = []
    for command in commands:
        try:
            process = subprocess.run(
                command.argv,
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=command.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CodeTaskError(failure_code, f"{command.name} could not complete: {exc}") from exc
        if process.returncode:
            detail = (process.stdout + "\n" + process.stderr).strip()
            raise CodeTaskError(failure_code, f"{command.name} failed: {detail}")
        results.append((command.name, "pass"))
    return tuple(results)
