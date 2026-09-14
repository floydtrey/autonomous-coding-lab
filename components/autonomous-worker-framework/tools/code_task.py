from __future__ import annotations

import hashlib
import json
import os
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


CODE_TASK_VERSION = "code-task:v1"


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
) -> CodeTaskContract:
    paths = tuple(expected_changed_paths)
    criteria = tuple(" ".join(item.split()) for item in acceptance_criteria)
    clean_objective = " ".join(objective.split())
    if not task_id.strip() or not clean_objective or not criteria or not all(criteria):
        raise CodeTaskError("CODE_TASK_INVALID", "task identity, objective, and acceptance criteria are required")
    if not paths or paths != tuple(sorted(set(paths))):
        raise CodeTaskError("CODE_TASK_SCOPE_INVALID", "expected changed paths must be sorted and unique")
    if not set(paths).issubset(packet.allowed_paths):
        raise CodeTaskError("CODE_TASK_SCOPE_INVALID", "expected changed paths exceed context scope")
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
                *contract.expected_changed_paths,
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
            writable_paths=contract.expected_changed_paths,
        )
    )
    if repository_head(repo_root) != contract.repository_head:
        raise CodeTaskError("CODE_TASK_HEAD_CHANGED", "worker changed repository HEAD")
    observed = tuple(changed_paths(repo_root, contract.repository_head))
    if observed != contract.expected_changed_paths:
        raise CodeTaskError(
            "CODE_TASK_BOUNDARY_FAILED",
            f"expected changed paths {contract.expected_changed_paths!r}; observed {observed!r}",
        )
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
        or result.changed_paths != contract.expected_changed_paths
        or not result.ready_for_handoff
    ):
        raise CodeTaskError("CODE_TASK_RESULT_INVALID", "code-task result differs from its sealed contract")
    candidate_digest = candidate_content_digest(repo_root, result.changed_paths)
    worker_result = WorkerResult(
        contract_version="worker-result:v1",
        task_id=contract.task_id,
        consumer=contract.consumer,
        task_contract_digest=contract.digest(),
        base_sha=contract.repository_head,
        candidate_sha=None,
        candidate_content_digest=candidate_digest,
        workspace_state="dirty-candidate",
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
    if not set(contract.expected_changed_paths).issubset(packet.allowed_paths):
        raise CodeTaskError("CODE_TASK_SCOPE_INVALID", "task paths exceed context scope")


def _implementation_prompt(contract: CodeTaskContract, packet: WorkerContextPacket) -> str:
    authority = "\n".join(f"- {item.path}" for item in packet.authority_files)
    context = "\n".join(f"- {item.path}" for item in packet.task_files) or "- none"
    paths = "\n".join(f"- {item}" for item in contract.expected_changed_paths)
    criteria = "\n".join(f"- {item}" for item in contract.acceptance_criteria)
    invariants = "\n".join(f"- {item}" for item in packet.product_invariants)
    return (
        f"Implement exact code task {contract.task_id} at repository HEAD {contract.repository_head}.\n"
        f"Task digest: {contract.digest()}\nContext digest: {packet.digest()}\n"
        f"Objective: {contract.objective}\n\nRead authority first:\n{authority}\n\n"
        f"Read-only supporting files:\n{context}\n\n"
        f"Change exactly these paths and no others:\n{paths}\n\n"
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
    validation_environment = os.environ.copy()
    validation_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    for command in commands:
        try:
            process = subprocess.run(
                command.argv,
                cwd=root,
                env=validation_environment,
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
