from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

try:
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


class HarnessSetupError(ValueError):
    """Raised when a local commissioning task is malformed or unsafe."""


class HarnessRuntimeError(RuntimeError):
    """Raised when the local repository cannot be inspected safely."""


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


def task_contract_digest(task: FixtureTask) -> str:
    encoded = json.dumps(
        task.to_dict(),
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


def _fixture_path_at_root(repo_root: Path, path: str) -> tuple[str, Path]:
    # Reuse the L0 validator's exact path-containment logic through its root override.
    return resolve_fixture_path(path, root=repo_root)


def _not_run_validation() -> ValidationResult:
    return ValidationResult(result="not-run", stages=(), failure_code=None)


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
    preexisting_dirty: bool = False,
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
        full_validation=_not_run_validation(),
        worker=WorkerStatus(
            result="fail",
            failure_code=code,
            failure_summary=summary,
            repair_attempts=0,
        ),
        first_failure=FailureDiagnostic(
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


def run_fixture_job(task: FixtureTask, repo_root: Path) -> WorkerResult:
    root = repo_root.resolve()
    base_sha = repository_head(root)
    digest = task_contract_digest(task)

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
        apply_fixture_mutation(root, task)
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
        return _failure_result(
            task=task,
            base_sha=base_sha,
            task_digest=digest,
            boundary="quick-validation",
            code="FIXTURE_TARGET_STATE_FAILED",
            summary=str(exc),
            expected=f"{task.fixture_path} in exact {task.target_state} state",
            observed=str(exc),
            retryable=True,
            next_action="Repair only the declared fixture path and rerun quick validation.",
            repo_root=root,
            patch_result=patch_result,
            quick_result=quick,
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
        full_validation=_not_run_validation(),
        worker=WorkerStatus(result="pass", repair_attempts=0),
        first_failure=None,
        ready_for_repository_handoff=False,
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
        description="Run one deterministic local fixture worker job without GitHub or Codex."
    )
    parser.add_argument("--task", required=True, help="fixture-task:v1 JSON file")
    parser.add_argument("--repo", required=True, help="target Git repository")
    parser.add_argument("--result", required=True, help="Worker Result JSON output path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        task = load_task(Path(args.task))
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
