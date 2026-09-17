import json

import pytest

from tools.worker_result import (
    CONTRACT_VERSION,
    BoundaryResult,
    FailureDiagnostic,
    ValidationResult,
    ValidationStage,
    WorkerResult,
    WorkerResultValidationError,
    WorkerStatus,
    validate_worker_result,
)


BASE_SHA = "1" * 40
CANDIDATE_SHA = "2" * 40
TASK_DIGEST = "sha256:" + "a" * 64
CONTENT_DIGEST = "sha256:" + "b" * 64


def _passing_result(**overrides):
    values = {
        "contract_version": CONTRACT_VERSION,
        "task_id": "fixture-a-to-b",
        "consumer": "advanced-mine-tracker",
        "task_contract_digest": TASK_DIGEST,
        "base_sha": BASE_SHA,
        "candidate_sha": None,
        "candidate_content_digest": CONTENT_DIGEST,
        "workspace_state": "dirty-candidate",
        "changed_paths": ("autonomy_smoke/fixture_state.txt",),
        "patch_boundary": BoundaryResult("pass"),
        "quick_validation": ValidationResult(
            "pass", (ValidationStage("changed-python-compile", "pass"),)
        ),
        "full_validation": ValidationResult(
            "pass", (ValidationStage("pytest-full", "pass"),)
        ),
        "worker": WorkerStatus("pass"),
        "first_failure": None,
        "ready_for_repository_handoff": True,
    }
    values.update(overrides)
    return WorkerResult(**values)


def test_valid_dirty_candidate_passes():
    result = _passing_result()

    validate_worker_result(result)

    assert result.ready_for_repository_handoff is True


def test_repaired_success_preserves_first_failure_and_can_be_ready():
    result = _passing_result(
        worker=WorkerStatus("pass", repair_attempts=1),
        first_failure=FailureDiagnostic(
            boundary="quick-validation",
            code="FIXTURE_TARGET_STATE_FAILED",
            summary="initial candidate had wrong fixture bytes",
            expected="STATE=B with LF",
            observed="STATE=A with LF",
            retryable=True,
            next_action="Repair only the declared fixture path.",
        ),
    )

    validate_worker_result(result)
    assert result.ready_for_repository_handoff is True


def test_valid_committed_candidate_passes():
    result = _passing_result(
        workspace_state="committed-candidate", candidate_sha=CANDIDATE_SHA
    )

    validate_worker_result(result)


def test_json_round_trip_is_deterministic():
    original = _passing_result()

    encoded = original.to_json()
    decoded = WorkerResult.from_json(encoded)

    assert decoded == original
    assert decoded.to_json() == encoded
    assert encoded == json.dumps(original.to_dict(), sort_keys=True, separators=(",", ":"))


def test_unknown_contract_version_fails_closed():
    result = _passing_result(contract_version="worker-result:v99")

    with pytest.raises(WorkerResultValidationError, match="unsupported contract_version"):
        validate_worker_result(result)


def test_unknown_top_level_field_fails_closed():
    payload = _passing_result().to_dict()
    payload["future_field"] = "unexpected"

    with pytest.raises(WorkerResultValidationError, match="unknown=.*future_field"):
        WorkerResult.from_dict(payload)


def test_invalid_candidate_digest_is_rejected():
    result = _passing_result(candidate_content_digest="sha256:not-a-digest")

    with pytest.raises(WorkerResultValidationError, match="candidate_content_digest"):
        validate_worker_result(result)


def test_changed_paths_must_be_sorted_unique_and_normalized():
    result = _passing_result(
        changed_paths=("tools/z.py", "app/a.py"),
        ready_for_repository_handoff=False,
    )
    with pytest.raises(WorkerResultValidationError, match="sorted"):
        validate_worker_result(result)

    result = _passing_result(
        changed_paths=("app/a.py", "app/a.py"),
        ready_for_repository_handoff=False,
    )
    with pytest.raises(WorkerResultValidationError, match="duplicates"):
        validate_worker_result(result)

    result = _passing_result(
        changed_paths=("app\\a.py",),
        ready_for_repository_handoff=False,
    )
    with pytest.raises(WorkerResultValidationError, match="POSIX"):
        validate_worker_result(result)


def test_ready_flag_is_derived_from_evidence():
    result = _passing_result(full_validation=ValidationResult("not-run"))

    with pytest.raises(WorkerResultValidationError, match="ready_for_repository_handoff"):
        validate_worker_result(result)


def test_failed_result_requires_structured_first_failure():
    result = _passing_result(
        quick_validation=ValidationResult(
            "fail",
            (ValidationStage("pytest-focused", "fail", "LOCAL_FOCUSED_TESTS_FAILED"),),
            "LOCAL_FOCUSED_TESTS_FAILED",
        ),
        full_validation=ValidationResult("not-run"),
        worker=WorkerStatus(
            "fail",
            failure_code="LOCAL_FOCUSED_TESTS_FAILED",
            failure_summary="focused tests failed",
        ),
        first_failure=None,
        ready_for_repository_handoff=False,
    )

    with pytest.raises(WorkerResultValidationError, match="first_failure"):
        validate_worker_result(result)


def test_failed_result_preserves_required_diagnostics():
    diagnostic = FailureDiagnostic(
        boundary="quick-validation",
        code="LOCAL_FOCUSED_TESTS_FAILED",
        summary="focused tests failed",
        expected="focused tests pass",
        observed="pytest exit code 1",
        retryable=True,
        next_action="repair failing focused test and rerun quick validation",
    )
    result = _passing_result(
        quick_validation=ValidationResult(
            "fail",
            (ValidationStage("pytest-focused", "fail", diagnostic.code),),
            diagnostic.code,
        ),
        full_validation=ValidationResult("not-run"),
        worker=WorkerStatus("fail", diagnostic.code, diagnostic.summary, 0),
        first_failure=diagnostic,
        ready_for_repository_handoff=False,
    )

    validate_worker_result(result)


def test_not_run_validation_cannot_contain_stages():
    result = _passing_result(
        full_validation=ValidationResult(
            "not-run", (ValidationStage("pytest-full", "pass"),)
        ),
        ready_for_repository_handoff=False,
    )

    with pytest.raises(WorkerResultValidationError, match="not-run result cannot contain stages"):
        validate_worker_result(result)


def test_committed_candidate_requires_commit_sha():
    result = _passing_result(
        workspace_state="committed-candidate", candidate_sha=None
    )

    with pytest.raises(WorkerResultValidationError, match="requires candidate_sha"):
        validate_worker_result(result)


def test_accepts_preexisting_dirty_failure_without_candidate_identity():
    result = _passing_result(
        workspace_state="preexisting-dirty",
        changed_paths=(),
        candidate_sha=None,
        candidate_content_digest=None,
        patch_boundary=BoundaryResult(result="not-run"),
        quick_validation=ValidationResult(result="not-run"),
        full_validation=ValidationResult(result="not-run"),
        worker=WorkerStatus(
            result="fail",
            failure_code="WORKSPACE_NOT_CLEAN",
            failure_summary="target repository was already dirty",
        ),
        first_failure=FailureDiagnostic(
            boundary="precondition",
            code="WORKSPACE_NOT_CLEAN",
            summary="target repository was already dirty",
            expected="clean target repository",
            observed="pre-existing changes",
            retryable=False,
            next_action="Clean the repository.",
        ),
        ready_for_repository_handoff=False,
    )

    validate_worker_result(result)
