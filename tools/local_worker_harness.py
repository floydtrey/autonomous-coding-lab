from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

try:
    from tools.codex_runtime import (
        CodexExecution,
        CodexRequest,
        CodexRuntimeError,
        execute_codex,
    )
    from tools.worker_fixture_validator import (
        EXPECTED_CONTENT,
        FixtureSetupError,
        FixtureValidationError,
        resolve_fixture_path,
        validate_fixture,
    )
    from tools.worker_result import (
        CONTRACT_VERSION as WORKER_RESULT_VERSION,
        BoundaryResult,
        FailureDiagnostic,
        ValidationResult,
        ValidationStage,
        WorkerResult,
        WorkerStatus,
        validate_worker_result,
    )
except ModuleNotFoundError:  # direct execution: python tools/local_worker_harness.py
    from codex_runtime import (  # type: ignore
        CodexExecution,
        CodexRequest,
        CodexRuntimeError,
        execute_codex,
    )
    from worker_fixture_validator import (  # type: ignore
        EXPECTED_CONTENT,
        FixtureSetupError,
        FixtureValidationError,
        resolve_fixture_path,
        validate_fixture,
    )
    from worker_result import (  # type: ignore
        CONTRACT_VERSION as WORKER_RESULT_VERSION,
        BoundaryResult,
        FailureDiagnostic,
        ValidationResult,
        ValidationStage,
        WorkerResult,
        WorkerStatus,
        validate_worker_result,
    )


FIXTURE_TASK_VERSION = "fixture-task:v1"
_ALLOWED_STATES = {"A", "B", "ABSENT"}
CodexExecutor = Callable[[CodexRequest], CodexExecution]


class HarnessSetupError(ValueError):
    """Raised when a local commissioning task is malformed or unsafe."""


class HarnessRuntimeError(RuntimeError):
    """Raised when the local repository cannot be inspected safely."""


@dataclass(frozen=True)
class TrustedValidationCommand:
    name: str
    argv: tuple[str, ...]
    timeout_seconds: int = 900

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.argv or any(not item for item in self.argv):
            raise HarnessSetupError("trusted validation command requires a name and argv")
        if self.timeout_seconds <= 0:
            raise HarnessSetupError("trusted validation timeout must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "argv": list(self.argv),
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class ConsumerValidationPlan:
    quick: tuple[TrustedValidationCommand, ...] = ()
    full: tuple[TrustedValidationCommand, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "quick": [command.to_dict() for command in self.quick],
            "full": [command.to_dict() for command in self.full],
        }


@dataclass(frozen=True)
class FixtureTask:
    contract_version: str
    task_id: str
    consumer: str
    allowed_paths: tuple[str, ...]
    fixture_path: str
    initial_state: str
    target_state: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "task_id": self.task_id,
            "consumer": self.consumer,
            "allowed_paths": list(self.allowed_paths),
            "fixture_path": self.fixture_path,
            "initial_state": self.initial_state,
            "target_state": self.target_state,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FixtureTask":
        expected = {
            "contract_version",
            "task_id",
            "consumer",
            "allowed_paths",
            "fixture_path",
            "initial_state",
            "target_state",
        }
        actual = set(value)
        if actual != expected:
            missing = sorted(expected - actual)
            unknown = sorted(actual - expected)
            detail = []
            if missing:
                detail.append(f"missing={missing}")
            if unknown:
                detail.append(f"unknown={unknown}")
            raise HarnessSetupError(f"fixture task fields invalid: {', '.join(detail)}")

        version = _require_text(value["contract_version"], "contract_version")
        if version != FIXTURE_TASK_VERSION:
            raise HarnessSetupError(
                f"unsupported contract_version {version!r}; expected {FIXTURE_TASK_VERSION!r}"
            )
        task_id = _require_text(value["task_id"], "task_id")
        consumer = _require_text(value["consumer"], "consumer")
        fixture_path = _normalise_repo_path(
            _require_text(value["fixture_path"], "fixture_path")
        )

        raw_allowed = value["allowed_paths"]
        if not isinstance(raw_allowed, list) or not raw_allowed:
            raise HarnessSetupError("allowed_paths must be a non-empty array")
        allowed = tuple(
            sorted({_normalise_repo_path(_require_text(item, "allowed_paths item")) for item in raw_allowed})
        )
        if fixture_path not in allowed:
            raise HarnessSetupError("fixture_path must be explicitly present in allowed_paths")

        initial = _state(value["initial_state"], "initial_state")
        target = _state(value["target_state"], "target_state")
        if initial == target:
            raise HarnessSetupError("initial_state and target_state must differ")

        return cls(
            contract_version=version,
            task_id=task_id,
            consumer=consumer,
            allowed_paths=allowed,
            fixture_path=fixture_path,
            initial_state=initial,
            target_state=target,
        )


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HarnessSetupError(f"{field} must be a non-empty string")
    return value.strip()


def _state(value: Any, field: str) -> str:
    state = _require_text(value, field).upper()
    if state not in _ALLOWED_STATES:
        raise HarnessSetupError(f"{field} must be A, B, or ABSENT")
    return state


def _normalise_repo_path(value: str) -> str:
    raw = value.strip().replace("\\", "/")
    candidate = PurePosixPath(raw)
    if (
        not raw
        or candidate.is_absolute()
        or raw.startswith("/")
        or ".." in candidate.parts
        or candidate.as_posix() != raw
        or raw == "."
        or ":" in candidate.parts[0]
    ):
        raise HarnessSetupError(f"invalid repository-relative path: {value!r}")
    return raw


def _run_git(repo_root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "git command failed").strip()
        raise HarnessRuntimeError(f"git {' '.join(args)} failed: {detail}")
    return process.stdout


def repository_head(repo_root: Path) -> str:
    value = _run_git(repo_root, "rev-parse", "HEAD").strip().lower()
    if not re_full_sha(value):
        raise HarnessRuntimeError("target repository HEAD is not a normal 40-character Git SHA")
    return value


def re_full_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def changed_paths(repo_root: Path, base_sha: str) -> list[str]:
    changed: set[str] = set()
    for args in (
        ("diff", "--name-only", "--diff-filter=ACDMRT", base_sha),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        for line in _run_git(repo_root, *args).splitlines():
            if line.strip():
                changed.add(_normalise_repo_path(line.strip()))
    return sorted(changed)


def require_clean_workspace(repo_root: Path) -> None:
    status = _run_git(repo_root, "status", "--porcelain")
    if status.strip():
        raise HarnessRuntimeError("target repository must be clean before a worker job starts")


def task_contract_digest(
    task: FixtureTask,
    validation_plan: ConsumerValidationPlan | None = None,
) -> str:
    contract: dict[str, Any] = {"task": task.to_dict()}
    if validation_plan is not None:
        contract["trusted_validation"] = validation_plan.to_dict()
    encoded = json.dumps(
        contract,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def candidate_content_digest(repo_root: Path, paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        normal = _normalise_repo_path(path)
        candidate = repo_root / PurePosixPath(normal)
        digest.update(normal.encode("utf-8"))
        digest.update(b"\0")
        if candidate.is_file():
            digest.update(b"FILE\0")
            digest.update(candidate.read_bytes())
        elif candidate.exists():
            digest.update(b"NONFILE\0")
        else:
            digest.update(b"ABSENT\0")
    return "sha256:" + digest.hexdigest()


def validate_patch_boundary(paths: Sequence[str], allowed_paths: Sequence[str]) -> None:
    if not paths:
        raise HarnessRuntimeError("worker produced no repository changes")
    allowed = set(allowed_paths)
    violations = [path for path in paths if path not in allowed]
    if violations:
        raise HarnessRuntimeError(
            "worker changed paths outside the exact commissioning boundary: "
            + ", ".join(sorted(violations))
        )


def apply_fixture_mutation(repo_root: Path, task: FixtureTask) -> None:
    _, resolved = _fixture_path_at_root(repo_root, task.fixture_path)
    if task.target_state == "ABSENT":
        if resolved.exists():
            if not resolved.is_file():
                raise HarnessRuntimeError("fixture target path is not a file")
            resolved.unlink()
        return
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_bytes(EXPECTED_CONTENT[task.target_state])


def build_fixture_codex_prompt(task: FixtureTask) -> str:
    target_instruction = (
        f"delete {task.fixture_path}"
        if task.target_state == "ABSENT"
        else f"write exactly STATE={task.target_state} followed by one LF to {task.fixture_path}"
    )
    return "\n".join(
        (
            "Perform one deterministic commissioning fixture mutation.",
            f"Task id: {task.task_id}",
            f"Consumer label: {task.consumer}",
            f"The repository is already in declared state {task.initial_state}.",
            f"Required action: {target_instruction}.",
            "Do not modify, create, rename, or delete any other path.",
            "Do not run tests, Git commands, network commands, or package managers.",
            "Stop immediately after making the required filesystem change.",
            f"Machine-enforced allowed paths: {json.dumps(list(task.allowed_paths))}",
        )
    )


def build_fixture_codex_repair_prompt(task: FixtureTask, observed: str) -> str:
    return "\n".join(
        (
            "Repair one failed deterministic commissioning fixture candidate.",
            f"Original validation failure: {observed}",
            f"Required final state: {task.fixture_path} must be exactly {task.target_state}.",
            "Change only the declared fixture path.",
            "Do not modify, create, rename, or delete any other path.",
            "Do not run tests, Git commands, network commands, or package managers.",
            "Stop immediately after the repair.",
            f"Machine-enforced allowed paths: {json.dumps(list(task.allowed_paths))}",
        )
    )
def _fixture_path_at_root(repo_root: Path, path: str) -> tuple[str, Path]:
    # Reuse the L0 validator's exact path-containment logic through its root override.
    return resolve_fixture_path(path, root=repo_root)


def _not_run_validation() -> ValidationResult:
    return ValidationResult(result="not-run", stages=(), failure_code=None)


def _run_trusted_validation(
    repo_root: Path,
    commands: Sequence[TrustedValidationCommand],
    *,
    failure_code: str,
) -> ValidationResult:
    stages: list[ValidationStage] = []
    for command in commands:
        try:
            process = subprocess.run(
                list(command.argv),
                cwd=repo_root,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=command.timeout_seconds,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            stages.append(ValidationStage(command.name, "fail", failure_code))
            return ValidationResult("fail", tuple(stages), failure_code)
        if process.returncode != 0:
            stages.append(ValidationStage(command.name, "fail", failure_code))
            return ValidationResult("fail", tuple(stages), failure_code)
        stages.append(ValidationStage(command.name, "pass"))
    return ValidationResult("pass", tuple(stages))


def run_fixture_full_validation(
    repo_root: Path,
    task: FixtureTask,
    trusted_commands: Sequence[TrustedValidationCommand] = (),
) -> ValidationResult:
    stages: list[ValidationStage] = []
    try:
        _run_git(repo_root, "diff", "--check")
    except HarnessRuntimeError:
        return ValidationResult(
            result="fail",
            stages=(
                ValidationStage(
                    name="Git candidate diff integrity",
                    result="fail",
                    failure_code="LOCAL_DIFF_CHECK_FAILED",
                ),
            ),
            failure_code="LOCAL_DIFF_CHECK_FAILED",
        )
    stages.append(
        ValidationStage(name="Git candidate diff integrity", result="pass")
    )

    try:
        validate_fixture(task.fixture_path, task.target_state, root=repo_root)
    except (FixtureSetupError, FixtureValidationError):
        stages.append(
            ValidationStage(
                name="Full deterministic fixture validation",
                result="fail",
                failure_code="FIXTURE_FULL_VALIDATION_FAILED",
            )
        )
        return ValidationResult(
            result="fail",
            stages=tuple(stages),
            failure_code="FIXTURE_FULL_VALIDATION_FAILED",
        )
    stages.append(
        ValidationStage(name="Full deterministic fixture validation", result="pass")
    )
    trusted = _run_trusted_validation(
        repo_root,
        trusted_commands,
        failure_code="CONSUMER_FULL_VALIDATION_FAILED",
    )
    stages.extend(trusted.stages)
    if trusted.result == "fail":
        return ValidationResult(
            result="fail",
            stages=tuple(stages),
            failure_code=trusted.failure_code,
        )
    return ValidationResult(result="pass", stages=tuple(stages))


def _failure_result(
    *,
    task: FixtureTask,
    base_sha: str,
    task_digest: str,
    boundary: str,
    code: str,
    summary: str,
    expected: str,
    observed: str,
    retryable: bool,
    next_action: str,
    repo_root: Path,
    patch_result: BoundaryResult | None = None,
    quick_result: ValidationResult | None = None,
    full_result: ValidationResult | None = None,
    preexisting_dirty: bool = False,
    repair_attempts: int = 0,
    first_failure: FailureDiagnostic | None = None,
) -> WorkerResult:
    if preexisting_dirty:
        paths = ()
        workspace_state = "preexisting-dirty"
        content_digest = None
    else:
        try:
            paths = tuple(changed_paths(repo_root, base_sha))
        except HarnessRuntimeError:
            paths = ()
        workspace_state = "dirty-candidate" if paths else "clean"
        content_digest = candidate_content_digest(repo_root, paths) if paths else None
    result = WorkerResult(
        contract_version=WORKER_RESULT_VERSION,
        task_id=task.task_id,
        consumer=task.consumer,
        task_contract_digest=task_digest,
        base_sha=base_sha,
        candidate_sha=None,
        candidate_content_digest=content_digest,
        workspace_state=workspace_state,
        changed_paths=paths,
        patch_boundary=patch_result or BoundaryResult(result="not-run"),
        quick_validation=quick_result or _not_run_validation(),
        full_validation=full_result or _not_run_validation(),
        worker=WorkerStatus(
            result="fail",
            failure_code=code,
            failure_summary=summary,
            repair_attempts=repair_attempts,
        ),
        first_failure=first_failure
        or FailureDiagnostic(
                boundary=boundary,
                code=code,
                summary=summary,
                expected=expected,
                observed=observed,
                retryable=retryable,
                next_action=next_action,
            ),
        ready_for_repository_handoff=False,
    )
    validate_worker_result(result)
    return result


def run_fixture_job(
    task: FixtureTask,
    repo_root: Path,
    *,
    validation_plan: ConsumerValidationPlan | None = None,
) -> WorkerResult:
    return _run_fixture_job(
        task,
        repo_root,
        apply_fixture_mutation,
        validation_plan=validation_plan,
    )


def run_codex_fixture_job(
    task: FixtureTask,
    repo_root: Path,
    framework_repo: Path,
    *,
    executor: CodexExecutor = execute_codex,
    validation_plan: ConsumerValidationPlan | None = None,
    task_contract_digest_override: str | None = None,
) -> WorkerResult:
    def codex_mutation(root: Path, fixture_task: FixtureTask) -> None:
        executor(
            CodexRequest(
                prompt=build_fixture_codex_prompt(fixture_task),
                target_repo=root,
                framework_repo=framework_repo,
                sandbox="workspace-write",
            )
        )

    def codex_repair(root: Path, fixture_task: FixtureTask, observed: str) -> None:
        executor(
            CodexRequest(
                prompt=build_fixture_codex_repair_prompt(fixture_task, observed),
                target_repo=root,
                framework_repo=framework_repo,
                sandbox="workspace-write",
            )
        )

    return _run_fixture_job(
        task,
        repo_root,
        codex_mutation,
        repair=codex_repair,
        validation_plan=validation_plan,
        task_contract_digest_override=task_contract_digest_override,
    )


def _run_fixture_job(
    task: FixtureTask,
    repo_root: Path,
    mutation: Callable[[Path, FixtureTask], None],
    *,
    repair: Callable[[Path, FixtureTask, str], None] | None = None,
    validation_plan: ConsumerValidationPlan | None = None,
    task_contract_digest_override: str | None = None,
) -> WorkerResult:
    root = repo_root.resolve()
    base_sha = repository_head(root)
    plan = validation_plan or ConsumerValidationPlan()
    digest = task_contract_digest_override or task_contract_digest(task, plan)

    try:
        require_clean_workspace(root)
    except HarnessRuntimeError as exc:
        return _failure_result(
            task=task,
            base_sha=base_sha,
            task_digest=digest,
            boundary="precondition",
            code="WORKSPACE_NOT_CLEAN",
            summary=str(exc),
            expected="clean target repository",
            observed="pre-existing repository changes",
            retryable=False,
            next_action="Clean or checkpoint the target repository before retrying.",
            repo_root=root,
            preexisting_dirty=True,
        )

    try:
        validate_fixture(task.fixture_path, task.initial_state, root=root)
    except (FixtureSetupError, FixtureValidationError) as exc:
        return _failure_result(
            task=task,
            base_sha=base_sha,
            task_digest=digest,
            boundary="fixture-precondition",
            code="FIXTURE_INITIAL_STATE_FAILED",
            summary=str(exc),
            expected=f"{task.fixture_path} in exact {task.initial_state} state",
            observed=str(exc),
            retryable=False,
            next_action="Restore the deterministic fixture to the declared initial state.",
            repo_root=root,
        )

    try:
        mutation(root, task)
    except CodexRuntimeError as exc:
        return _failure_result(
            task=task,
            base_sha=base_sha,
            task_digest=digest,
            boundary="codex-execution",
            code=exc.code,
            summary=exc.summary,
            expected="successful bounded Codex execution in workspace-write sandbox",
            observed=exc.summary,
            retryable=exc.code in {"CODEX_TIMEOUT", "CODEX_EXECUTION_FAILED"},
            next_action="Resolve the Codex runtime boundary before inspecting later gates.",
            repo_root=root,
        )
    except (OSError, FixtureSetupError, HarnessRuntimeError) as exc:
        return _failure_result(
            task=task,
            base_sha=base_sha,
            task_digest=digest,
            boundary="mutation",
            code="FIXTURE_MUTATION_FAILED",
            summary=str(exc),
            expected=f"exact transition {task.initial_state}->{task.target_state}",
            observed=str(exc),
            retryable=False,
            next_action="Inspect the target path and filesystem permissions.",
            repo_root=root,
        )

    paths = changed_paths(root, base_sha)
    try:
        validate_patch_boundary(paths, task.allowed_paths)
    except HarnessRuntimeError as exc:
        return _failure_result(
            task=task,
            base_sha=base_sha,
            task_digest=digest,
            boundary="patch-boundary",
            code="PATCH_BOUNDARY_FAILED",
            summary=str(exc),
            expected=f"changes limited to {list(task.allowed_paths)}",
            observed=f"changed_paths={paths}",
            retryable=False,
            next_action="Discard the candidate and inspect why out-of-bound paths changed.",
            repo_root=root,
            patch_result=BoundaryResult(
                result="fail",
                failure_code="PATCH_BOUNDARY_FAILED",
            ),
        )

    patch_result = BoundaryResult(result="pass")

    repair_attempts = 0
    first_failure: FailureDiagnostic | None = None
    try:
        validate_fixture(task.fixture_path, task.target_state, root=root)
    except (FixtureSetupError, FixtureValidationError) as exc:
        quick = ValidationResult(
            result="fail",
            stages=(
                ValidationStage(
                    name="Deterministic fixture target validation",
                    result="fail",
                    failure_code="FIXTURE_TARGET_STATE_FAILED",
                ),
            ),
            failure_code="FIXTURE_TARGET_STATE_FAILED",
        )
        first_failure = FailureDiagnostic(
            boundary="quick-validation",
            code="FIXTURE_TARGET_STATE_FAILED",
            summary=str(exc),
            expected=f"{task.fixture_path} in exact {task.target_state} state",
            observed=str(exc),
            retryable=True,
            next_action="Repair only the declared fixture path and rerun quick validation.",
        )
        if repair is None:
            return _failure_result(
                task=task,
                base_sha=base_sha,
                task_digest=digest,
                boundary="quick-validation",
                code="FIXTURE_TARGET_STATE_FAILED",
                summary=str(exc),
                expected=first_failure.expected,
                observed=first_failure.observed,
                retryable=True,
                next_action=first_failure.next_action,
                repo_root=root,
                patch_result=patch_result,
                quick_result=quick,
                first_failure=first_failure,
            )

        repair_attempts = 1
        try:
            repair(root, task, str(exc))
        except CodexRuntimeError as repair_exc:
            return _failure_result(
                task=task,
                base_sha=base_sha,
                task_digest=digest,
                boundary="repair-execution",
                code=repair_exc.code,
                summary=repair_exc.summary,
                expected="one successful bounded repair execution",
                observed=repair_exc.summary,
                retryable=False,
                next_action="Inspect the original quick-validation failure and repair runtime.",
                repo_root=root,
                patch_result=patch_result,
                quick_result=quick,
                repair_attempts=repair_attempts,
                first_failure=first_failure,
            )

        paths = changed_paths(root, base_sha)
        try:
            validate_patch_boundary(paths, task.allowed_paths)
        except HarnessRuntimeError as boundary_exc:
            return _failure_result(
                task=task,
                base_sha=base_sha,
                task_digest=digest,
                boundary="repair-patch-boundary",
                code="PATCH_BOUNDARY_FAILED",
                summary=str(boundary_exc),
                expected=f"repair changes limited to {list(task.allowed_paths)}",
                observed=f"changed_paths={paths}",
                retryable=False,
                next_action="Discard the repaired candidate and inspect the out-of-bound change.",
                repo_root=root,
                patch_result=BoundaryResult("fail", "PATCH_BOUNDARY_FAILED"),
                quick_result=quick,
                repair_attempts=repair_attempts,
                first_failure=first_failure,
            )

        try:
            validate_fixture(task.fixture_path, task.target_state, root=root)
        except (FixtureSetupError, FixtureValidationError) as repair_validation_exc:
            return _failure_result(
                task=task,
                base_sha=base_sha,
                task_digest=digest,
                boundary="repair-quick-validation",
                code="FIXTURE_TARGET_STATE_FAILED",
                summary=str(repair_validation_exc),
                expected=f"{task.fixture_path} in exact {task.target_state} state",
                observed=str(repair_validation_exc),
                retryable=False,
                next_action="Stop after the single bounded repair attempt.",
                repo_root=root,
                patch_result=patch_result,
                quick_result=quick,
                repair_attempts=repair_attempts,
                first_failure=first_failure,
            )

    quick = ValidationResult(
        result="pass",
        stages=(
            ValidationStage(
                name="Deterministic fixture target validation",
                result="pass",
            ),
        ),
    )
    trusted_quick = _run_trusted_validation(
        root,
        plan.quick,
        failure_code="CONSUMER_QUICK_VALIDATION_FAILED",
    )
    if trusted_quick.result == "fail":
        quick = ValidationResult(
            "fail",
            quick.stages + trusted_quick.stages,
            trusted_quick.failure_code,
        )
        code = trusted_quick.failure_code or "CONSUMER_QUICK_VALIDATION_FAILED"
        return _failure_result(
            task=task,
            base_sha=base_sha,
            task_digest=digest,
            boundary="quick-validation",
            code=code,
            summary="trusted consumer quick validation failed",
            expected="all trusted consumer quick validation stages pass",
            observed=f"failure_code={code}",
            retryable=False,
            next_action="Inspect the failed trusted validation stage before retrying.",
            repo_root=root,
            patch_result=patch_result,
            quick_result=quick,
            repair_attempts=repair_attempts,
            first_failure=first_failure,
        )
    quick = ValidationResult("pass", quick.stages + trusted_quick.stages)
    full = run_fixture_full_validation(root, task, plan.full)
    if full.result == "fail":
        code = full.failure_code or "LOCAL_FULL_VALIDATION_FAILED"
        return _failure_result(
            task=task,
            base_sha=base_sha,
            task_digest=digest,
            boundary="full-validation",
            code=code,
            summary="full local candidate validation failed",
            expected="all full local validation stages pass",
            observed=f"failure_code={code}",
            retryable=True,
            next_action="Repair only the declared fixture path and rerun quick validation first.",
            repo_root=root,
            patch_result=patch_result,
            quick_result=quick,
            full_result=full,
            repair_attempts=repair_attempts,
            first_failure=first_failure,
        )

    paths_tuple = tuple(paths)
    result = WorkerResult(
        contract_version=WORKER_RESULT_VERSION,
        task_id=task.task_id,
        consumer=task.consumer,
        task_contract_digest=digest,
        base_sha=base_sha,
        candidate_sha=None,
        candidate_content_digest=candidate_content_digest(root, paths_tuple),
        workspace_state="dirty-candidate",
        changed_paths=paths_tuple,
        patch_boundary=patch_result,
        quick_validation=quick,
        full_validation=full,
        worker=WorkerStatus(result="pass", repair_attempts=repair_attempts),
        first_failure=first_failure,
        ready_for_repository_handoff=True,
    )
    validate_worker_result(result)
    return result


def load_task(path: Path) -> FixtureTask:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessSetupError(f"could not load fixture task: {exc}") from exc
    if not isinstance(value, dict):
        raise HarnessSetupError("fixture task JSON must contain an object")
    return FixtureTask.from_mapping(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one deterministic local fixture worker job without GitHub."
    )
    parser.add_argument("--task", required=True, help="fixture-task:v1 JSON file")
    parser.add_argument("--repo", required=True, help="target Git repository")
    parser.add_argument("--result", required=True, help="Worker Result JSON output path")
    parser.add_argument(
        "--engine",
        choices=("fixture", "codex"),
        default="fixture",
        help="deterministic direct mutation or bounded Codex execution",
    )
    parser.add_argument(
        "--framework-repo",
        help="framework repository path; required for the Codex engine",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        task = load_task(Path(args.task))
        if args.engine == "codex":
            if not args.framework_repo:
                raise HarnessSetupError("--framework-repo is required for the Codex engine")
            result = run_codex_fixture_job(
                task,
                Path(args.repo),
                Path(args.framework_repo),
            )
        else:
            result = run_fixture_job(task, Path(args.repo))
        output = Path(args.result)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.to_json(pretty=True) + "\n", encoding="utf-8")
    except (HarnessSetupError, HarnessRuntimeError, OSError) as exc:
        print(f"HARNESS_SETUP_FAILED: {exc}", file=sys.stderr)
        return 2

    print(result.to_json(pretty=True))
    return 0 if result.worker.result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
