from copy import deepcopy

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.models import (
    ATTEMPT_SCHEMA,
    CURRICULUM_SCHEMA,
    EVIDENCE_SCHEMA,
    EXERCISE_SCHEMA,
    FAILURE_SCHEMA,
    AttemptRecord,
    AttemptState,
    CurriculumRecord,
    EvidenceRecord,
    ExerciseRecord,
    FailureRecord,
)


DIGEST = "sha256:" + "a" * 64
SHA = "b" * 40
NOW = "2026-08-27T12:00:00Z"


def curriculum_mapping():
    return {
        "schema_version": CURRICULUM_SCHEMA,
        "curriculum_id": "record-ledger",
        "title": "Local Record Ledger",
        "purpose": "Exercise deterministic local records.",
        "capabilities": ["canonical-data", "validation"],
        "prerequisite_curriculum_ids": [],
        "exercise_ids": ["record-model"],
        "status": "active",
    }


def exercise_mapping():
    return {
        "schema_version": EXERCISE_SCHEMA,
        "exercise_id": "record-model",
        "exercise_version": 1,
        "curriculum_id": "record-ledger",
        "objective": "Implement a strict record model.",
        "template_repository": "local/record-ledger-template",
        "template_commit": SHA,
        "writable_paths": ["record_ledger/models.py", "tests/test_models.py"],
        "protected_paths": ["evaluator/record_model.py"],
        "acceptance_criteria": ["Malformed records fail closed.", "Valid records round trip."],
        "test_profile_ids": ["JSON_RECORD_CHANGE:v1"],
        "prohibited_shortcuts": ["Do not modify evaluator files."],
        "expected_failure_behavior": ["Return structured validation errors."],
    }


def attempt_mapping():
    return {
        "schema_version": ATTEMPT_SCHEMA,
        "attempt_id": "ATTEMPT-000001",
        "curriculum_id": "record-ledger",
        "exercise_id": "record-model",
        "exercise_version": 1,
        "starting_commit": SHA,
        "context_digest": DIGEST,
        "task_digest": DIGEST,
        "state": "DRAFT",
        "created_at": NOW,
        "updated_at": NOW,
        "evaluator_catalog_version": "worker-lab-tests:v1",
        "runtime_identity": None,
        "candidate_digest": None,
        "cleanup_outcome": None,
        "prior_attempt_id": None,
    }


def evidence_mapping():
    return {
        "schema_version": EVIDENCE_SCHEMA,
        "evidence_digest": DIGEST,
        "evidence_type": "test-result",
        "attempt_id": "ATTEMPT-000001",
        "test_id": "T005",
        "test_catalog_version": "worker-lab-tests:v1",
        "candidate_digest": DIGEST,
        "base_commit": SHA,
        "environment_digest": DIGEST,
        "content_path": "evidence/aa/result.json",
        "external_reference": None,
        "created_at": NOW,
        "verification_state": "verified",
    }


def failure_mapping():
    return {
        "schema_version": FAILURE_SCHEMA,
        "failure_id": "FAILURE-000001",
        "attempt_id": "ATTEMPT-000001",
        "first_failed_boundary": "T005",
        "expected": "Unknown fields fail.",
        "observed": "Unknown field was accepted.",
        "classification": "worker-reasoning",
        "containment_outcome": "Candidate discarded.",
        "proposed_control": "Add strict field regression.",
        "accepted_limitation": None,
        "related_failure_ids": [],
    }


@pytest.mark.parametrize(
    ("builder", "mapping"),
    [
        (CurriculumRecord.from_mapping, curriculum_mapping),
        (ExerciseRecord.from_mapping, exercise_mapping),
        (AttemptRecord.from_mapping, attempt_mapping),
        (EvidenceRecord.from_mapping, evidence_mapping),
        (FailureRecord.from_mapping, failure_mapping),
    ],
)
def test_records_round_trip_canonically(builder, mapping):
    record = builder(mapping())
    assert builder(__import__("json").loads(record.to_json())) == record
    assert record.digest().startswith("sha256:")
    assert record.to_json() == record.to_json()


@pytest.mark.parametrize(
    ("builder", "mapping"),
    [
        (CurriculumRecord.from_mapping, curriculum_mapping),
        (ExerciseRecord.from_mapping, exercise_mapping),
        (AttemptRecord.from_mapping, attempt_mapping),
        (EvidenceRecord.from_mapping, evidence_mapping),
        (FailureRecord.from_mapping, failure_mapping),
    ],
)
def test_unknown_fields_fail_closed(builder, mapping):
    value = mapping()
    value["surprise"] = True
    with pytest.raises(LabValidationError) as error:
        builder(value)
    assert error.value.code == "RECORD_FIELDS_INVALID"


def test_curriculum_cannot_require_itself():
    value = curriculum_mapping()
    value["prerequisite_curriculum_ids"] = ["record-ledger"]
    with pytest.raises(LabValidationError, match="cannot require itself"):
        CurriculumRecord.from_mapping(value)


def test_exercise_rejects_writable_protected_overlap():
    value = exercise_mapping()
    value["protected_paths"] = ["record_ledger/models.py"]
    with pytest.raises(LabValidationError) as error:
        ExerciseRecord.from_mapping(value)
    assert error.value.code == "RECORD_SCOPE_INVALID"


@pytest.mark.parametrize("path", ["../escape.py", "/absolute.py", "C:/escape.py", "a/../b.py"])
def test_exercise_rejects_unsafe_paths(path):
    value = exercise_mapping()
    value["writable_paths"] = [path]
    with pytest.raises(LabValidationError) as error:
        ExerciseRecord.from_mapping(value)
    assert error.value.code == "RECORD_PATH_INVALID"


def test_attempt_parses_state_and_rejects_time_reversal():
    record = AttemptRecord.from_mapping(attempt_mapping())
    assert record.state is AttemptState.DRAFT
    value = attempt_mapping()
    value["updated_at"] = "2026-08-27T11:59:59Z"
    with pytest.raises(LabValidationError) as error:
        AttemptRecord.from_mapping(value)
    assert error.value.code == "RECORD_TIME_INVALID"


def test_evidence_requires_exactly_one_location():
    for content, external in ((None, None), ("evidence/a.json", "https://example.invalid/evidence")):
        value = evidence_mapping()
        value["content_path"] = content
        value["external_reference"] = external
        with pytest.raises(LabValidationError) as error:
            EvidenceRecord.from_mapping(value)
        assert error.value.code == "RECORD_EVIDENCE_LOCATION_INVALID"


def test_failure_requires_control_or_accepted_limitation():
    value = failure_mapping()
    value["proposed_control"] = None
    value["accepted_limitation"] = None
    with pytest.raises(LabValidationError) as error:
        FailureRecord.from_mapping(value)
    assert error.value.code == "RECORD_FAILURE_RESPONSE_INVALID"


def test_sorted_unique_lists_are_required():
    value = deepcopy(curriculum_mapping())
    value["capabilities"] = ["validation", "canonical-data"]
    with pytest.raises(LabValidationError) as error:
        CurriculumRecord.from_mapping(value)
    assert error.value.code == "RECORD_LIST_INVALID"
