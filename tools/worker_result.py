from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence


CONTRACT_VERSION = "worker-result:v1"
_RESULT_VALUES = {"pass", "fail", "not-run"}
_WORKSPACE_STATES = {"clean", "preexisting-dirty", "dirty-candidate", "committed-candidate"}
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class WorkerResultValidationError(ValueError):
    """Raised when a Worker Result manifest is malformed or internally inconsistent."""


@dataclass(frozen=True)
class BoundaryResult:
    result: str
    failure_code: str | None = None


@dataclass(frozen=True)
class ValidationStage:
    name: str
    result: str
    failure_code: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    result: str
    stages: tuple[ValidationStage, ...] = field(default_factory=tuple)
    failure_code: str | None = None


@dataclass(frozen=True)
class WorkerStatus:
    result: str
    failure_code: str | None = None
    failure_summary: str | None = None
    repair_attempts: int = 0


@dataclass(frozen=True)
class FailureDiagnostic:
    boundary: str
    code: str
    summary: str
    expected: str
    observed: str
    retryable: bool
    next_action: str


@dataclass(frozen=True)
class WorkerResult:
    contract_version: str
    task_id: str
    consumer: str
    task_contract_digest: str
    base_sha: str
    candidate_sha: str | None
    candidate_content_digest: str | None
    workspace_state: str
    changed_paths: tuple[str, ...]
    patch_boundary: BoundaryResult
    quick_validation: ValidationResult
    full_validation: ValidationResult
    worker: WorkerStatus
    first_failure: FailureDiagnostic | None
    ready_for_repository_handoff: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, pretty: bool = False) -> str:
        kwargs: dict[str, Any] = {"sort_keys": True}
        if pretty:
            kwargs.update(indent=2)
        else:
            kwargs.update(separators=(",", ":"))
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "WorkerResult":
        result = _parse_worker_result(value)
        validate_worker_result(result)
        return result

    @classmethod
    def from_json(cls, value: str) -> "WorkerResult":
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise WorkerResultValidationError(f"invalid Worker Result JSON: {exc.msg}") from exc
        if not isinstance(decoded, dict):
            raise WorkerResultValidationError("Worker Result JSON must contain an object")
        return cls.from_dict(decoded)


def validate_worker_result(value: WorkerResult) -> None:
    if value.contract_version != CONTRACT_VERSION:
        raise WorkerResultValidationError(
            f"unsupported contract_version {value.contract_version!r}; expected {CONTRACT_VERSION!r}"
        )
    _require_text("task_id", value.task_id)
    _require_text("consumer", value.consumer)
    _require_digest("task_contract_digest", value.task_contract_digest)
    _require_sha("base_sha", value.base_sha)
    if value.candidate_sha is not None:
        _require_sha("candidate_sha", value.candidate_sha)
    if value.candidate_content_digest is not None:
        _require_digest("candidate_content_digest", value.candidate_content_digest)
    if value.workspace_state not in _WORKSPACE_STATES:
        raise WorkerResultValidationError(
            f"workspace_state must be one of {sorted(_WORKSPACE_STATES)}"
        )
    if value.workspace_state == "committed-candidate" and value.candidate_sha is None:
        raise WorkerResultValidationError("committed-candidate requires candidate_sha")
    if value.workspace_state in {"clean", "preexisting-dirty"} and value.changed_paths:
        raise WorkerResultValidationError(
            f"{value.workspace_state} workspace_state cannot report changed_paths"
        )
    if value.workspace_state == "preexisting-dirty" and (
        value.candidate_sha is not None or value.candidate_content_digest is not None
    ):
        raise WorkerResultValidationError(
            "preexisting-dirty workspace_state cannot report candidate identity"
        )

    _validate_changed_paths(value.changed_paths)
    _validate_boundary("patch_boundary", value.patch_boundary)
    _validate_validation("quick_validation", value.quick_validation)
    _validate_validation("full_validation", value.full_validation)
    _validate_worker(value.worker)

    failed = _has_failure(value)
    if failed and value.first_failure is None:
        raise WorkerResultValidationError("failed Worker Result requires first_failure diagnostics")
    if not failed and value.first_failure is not None:
        raise WorkerResultValidationError("passing Worker Result may not report first_failure diagnostics")
    if value.first_failure is not None:
        _validate_failure_diagnostic(value.first_failure)

    expected_ready = _compute_ready(value)
    if value.ready_for_repository_handoff != expected_ready:
        raise WorkerResultValidationError(
            "ready_for_repository_handoff does not match validated result state"
        )


def _compute_ready(value: WorkerResult) -> bool:
    return (
        value.worker.result == "pass"
        and value.patch_boundary.result == "pass"
        and value.quick_validation.result == "pass"
        and value.full_validation.result == "pass"
        and value.workspace_state in {"dirty-candidate", "committed-candidate"}
        and bool(value.changed_paths)
        and value.candidate_content_digest is not None
        and value.first_failure is None
    )


def _has_failure(value: WorkerResult) -> bool:
    return any(
        item == "fail"
        for item in (
            value.patch_boundary.result,
            value.quick_validation.result,
            value.full_validation.result,
            value.worker.result,
        )
    )


def _validate_boundary(name: str, value: BoundaryResult) -> None:
    _validate_result_and_code(name, value.result, value.failure_code)


def _validate_validation(name: str, value: ValidationResult) -> None:
    _validate_result_and_code(name, value.result, value.failure_code)
    for index, stage in enumerate(value.stages):
        _require_text(f"{name}.stages[{index}].name", stage.name)
        _validate_result_and_code(
            f"{name}.stages[{index}]", stage.result, stage.failure_code
        )
    if value.result == "not-run" and value.stages:
        raise WorkerResultValidationError(f"{name} not-run result cannot contain stages")
    stage_failed = any(stage.result == "fail" for stage in value.stages)
    if value.result == "pass" and stage_failed:
        raise WorkerResultValidationError(f"{name} pass result cannot contain failed stage")
    if value.result == "fail" and value.stages and not stage_failed:
        raise WorkerResultValidationError(f"{name} fail result requires a failed stage when stages exist")


def _validate_worker(value: WorkerStatus) -> None:
    if value.result not in {"pass", "fail"}:
        raise WorkerResultValidationError("worker.result must be pass or fail")
    if value.result == "fail":
        _require_text("worker.failure_code", value.failure_code)
        _require_text("worker.failure_summary", value.failure_summary)
    elif value.failure_code is not None or value.failure_summary is not None:
        raise WorkerResultValidationError("worker pass result may not include failure fields")
    if isinstance(value.repair_attempts, bool) or not isinstance(value.repair_attempts, int) or value.repair_attempts < 0:
        raise WorkerResultValidationError("worker.repair_attempts must be a non-negative integer")


def _validate_failure_diagnostic(value: FailureDiagnostic) -> None:
    _require_text("first_failure.boundary", value.boundary)
    _require_text("first_failure.code", value.code)
    _require_text("first_failure.summary", value.summary)
    _require_text("first_failure.expected", value.expected)
    _require_text("first_failure.observed", value.observed)
    if not isinstance(value.retryable, bool):
        raise WorkerResultValidationError("first_failure.retryable must be boolean")
    _require_text("first_failure.next_action", value.next_action)


def _validate_result_and_code(name: str, result: str, failure_code: str | None) -> None:
    if result not in _RESULT_VALUES:
        raise WorkerResultValidationError(
            f"{name}.result must be one of {sorted(_RESULT_VALUES)}"
        )
    if result == "fail":
        _require_text(f"{name}.failure_code", failure_code)
    elif failure_code is not None:
        raise WorkerResultValidationError(
            f"{name} {result} result may not include failure_code"
        )


def _validate_changed_paths(paths: Sequence[str]) -> None:
    if list(paths) != sorted(paths):
        raise WorkerResultValidationError("changed_paths must be sorted")
    if len(paths) != len(set(paths)):
        raise WorkerResultValidationError("changed_paths must not contain duplicates")
    for index, path in enumerate(paths):
        _require_text(f"changed_paths[{index}]", path)
        if "\\" in path:
            raise WorkerResultValidationError("changed_paths must use repository-relative POSIX paths")
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or path.startswith("/") or ".." in candidate.parts:
            raise WorkerResultValidationError("changed_paths must stay repository-relative")
        if candidate.as_posix() != path or path == "." or ":" in candidate.parts[0]:
            raise WorkerResultValidationError("changed_paths must be normalized repository-relative paths")


def _require_text(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise WorkerResultValidationError(f"{name} must be a non-empty string")


def _require_sha(name: str, value: str) -> None:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise WorkerResultValidationError(f"{name} must be a lowercase 40-character Git SHA")


def _require_digest(name: str, value: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise WorkerResultValidationError(f"{name} must be sha256:<64 lowercase hex characters>")


def _strict_fields(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if unknown:
            details.append(f"unknown={unknown}")
        raise WorkerResultValidationError(f"{name} fields invalid: {', '.join(details)}")


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WorkerResultValidationError(f"{name} must be an object")
    return value


def _parse_boundary(value: Any, name: str) -> BoundaryResult:
    item = _mapping(value, name)
    _strict_fields(item, {"result", "failure_code"}, name)
    return BoundaryResult(result=item["result"], failure_code=item["failure_code"])


def _parse_stage(value: Any, name: str) -> ValidationStage:
    item = _mapping(value, name)
    _strict_fields(item, {"name", "result", "failure_code"}, name)
    return ValidationStage(
        name=item["name"], result=item["result"], failure_code=item["failure_code"]
    )


def _parse_validation(value: Any, name: str) -> ValidationResult:
    item = _mapping(value, name)
    _strict_fields(item, {"result", "stages", "failure_code"}, name)
    stages_raw = item["stages"]
    if not isinstance(stages_raw, list):
        raise WorkerResultValidationError(f"{name}.stages must be an array")
    stages = tuple(
        _parse_stage(stage, f"{name}.stages[{index}]")
        for index, stage in enumerate(stages_raw)
    )
    return ValidationResult(
        result=item["result"], stages=stages, failure_code=item["failure_code"]
    )


def _parse_worker(value: Any) -> WorkerStatus:
    item = _mapping(value, "worker")
    _strict_fields(
        item,
        {"result", "failure_code", "failure_summary", "repair_attempts"},
        "worker",
    )
    return WorkerStatus(
        result=item["result"],
        failure_code=item["failure_code"],
        failure_summary=item["failure_summary"],
        repair_attempts=item["repair_attempts"],
    )


def _parse_failure(value: Any) -> FailureDiagnostic | None:
    if value is None:
        return None
    item = _mapping(value, "first_failure")
    expected = {
        "boundary",
        "code",
        "summary",
        "expected",
        "observed",
        "retryable",
        "next_action",
    }
    _strict_fields(item, expected, "first_failure")
    return FailureDiagnostic(
        boundary=item["boundary"],
        code=item["code"],
        summary=item["summary"],
        expected=item["expected"],
        observed=item["observed"],
        retryable=item["retryable"],
        next_action=item["next_action"],
    )


def _parse_worker_result(value: Mapping[str, Any]) -> WorkerResult:
    expected = {
        "contract_version",
        "task_id",
        "consumer",
        "task_contract_digest",
        "base_sha",
        "candidate_sha",
        "candidate_content_digest",
        "workspace_state",
        "changed_paths",
        "patch_boundary",
        "quick_validation",
        "full_validation",
        "worker",
        "first_failure",
        "ready_for_repository_handoff",
    }
    _strict_fields(value, expected, "Worker Result")
    paths = value["changed_paths"]
    if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
        raise WorkerResultValidationError("changed_paths must be an array of strings")
    ready = value["ready_for_repository_handoff"]
    if not isinstance(ready, bool):
        raise WorkerResultValidationError("ready_for_repository_handoff must be boolean")
    return WorkerResult(
        contract_version=value["contract_version"],
        task_id=value["task_id"],
        consumer=value["consumer"],
        task_contract_digest=value["task_contract_digest"],
        base_sha=value["base_sha"],
        candidate_sha=value["candidate_sha"],
        candidate_content_digest=value["candidate_content_digest"],
        workspace_state=value["workspace_state"],
        changed_paths=tuple(paths),
        patch_boundary=_parse_boundary(value["patch_boundary"], "patch_boundary"),
        quick_validation=_parse_validation(value["quick_validation"], "quick_validation"),
        full_validation=_parse_validation(value["full_validation"], "full_validation"),
        worker=_parse_worker(value["worker"]),
        first_failure=_parse_failure(value["first_failure"]),
        ready_for_repository_handoff=ready,
    )
