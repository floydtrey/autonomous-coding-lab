from copy import deepcopy

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.models import (
    AttemptRecord, CurriculumRecord, EvidenceRecord, ExerciseRecord, FailureRecord,
)
from worker_lab.policy import ContextManifest, PolicyRecord, RoleRecord
from worker_lab.validation import attempt_task_digest, validate_relations
from tests.test_models import (
    attempt_mapping, curriculum_mapping, evidence_mapping, exercise_mapping, failure_mapping,
)
from tests.test_policy import context_mapping, policy_mapping, role_mapping
from tests.test_test_catalog import catalog


def valid_graph(*, with_candidate: bool = False) -> dict:
    curriculum = CurriculumRecord.from_mapping(curriculum_mapping())
    exercise = ExerciseRecord.from_mapping(exercise_mapping())
    policy = PolicyRecord.from_mapping(policy_mapping())
    role = RoleRecord.from_mapping(role_mapping())
    context = ContextManifest.from_mapping(context_mapping())
    tests = catalog()
    attempt_value = attempt_mapping()
    attempt_value.update({
        "context_digest": context.digest(),
        "task_digest": attempt_task_digest(exercise, policy, role, context, tests),
        "policy_digest": policy.digest(),
        "role_digest": role.digest(),
        "evaluator_catalog_digest": tests.digest(),
    })
    if with_candidate:
        attempt_value["state"] = "EVALUATING"
        attempt_value["candidate_digest"] = "sha256:" + "a" * 64
    return {
        "curricula": [curriculum], "exercises": [exercise], "policies": [policy],
        "roles": [role], "contexts": [context], "catalog": tests,
        "attempts": [AttemptRecord.from_mapping(attempt_value)],
    }


def test_valid_related_records_pass() -> None:
    validate_relations(**valid_graph())


def test_missing_exercise_fails_closed() -> None:
    graph = valid_graph()
    graph["exercises"] = []
    with pytest.raises(LabValidationError) as raised:
        validate_relations(**graph)
    assert raised.value.code == "RELATION_REFERENCE_MISSING"


def test_curriculum_cannot_claim_exercise_owned_by_another_curriculum() -> None:
    graph = valid_graph()
    other = curriculum_mapping()
    other["curriculum_id"] = "other-curriculum"
    graph["curricula"].append(CurriculumRecord.from_mapping(other))
    with pytest.raises(LabValidationError) as raised:
        validate_relations(**graph)
    assert raised.value.code == "RELATION_REFERENCE_MISSING"


def test_attempt_authority_digest_mismatch_fails_closed() -> None:
    graph = valid_graph()
    graph["attempts"][0] = AttemptRecord.from_mapping({
        **graph["attempts"][0].to_dict(), "task_digest": "sha256:" + "f" * 64,
    })
    with pytest.raises(LabValidationError) as raised:
        validate_relations(**graph)
    assert raised.value.code == "RELATION_IDENTITY_MISMATCH"


def test_prior_attempt_cycle_fails_closed() -> None:
    graph = valid_graph()
    first = graph["attempts"][0].to_dict()
    second = deepcopy(first)
    first["prior_attempt_id"] = "ATTEMPT-000002"
    second["attempt_id"] = "ATTEMPT-000002"
    second["prior_attempt_id"] = first["attempt_id"]
    graph["attempts"] = [AttemptRecord.from_mapping(first), AttemptRecord.from_mapping(second)]
    with pytest.raises(LabValidationError) as raised:
        validate_relations(**graph)
    assert raised.value.code == "RELATION_CYCLE_INVALID"


def test_retry_requires_terminal_prior_attempt() -> None:
    graph = valid_graph()
    first = graph["attempts"][0].to_dict()
    retry = {**first, "attempt_id": "ATTEMPT-000002", "prior_attempt_id": first["attempt_id"]}
    graph["attempts"].append(AttemptRecord.from_mapping(retry))
    with pytest.raises(LabValidationError) as raised:
        validate_relations(**graph)
    assert raised.value.code == "RELATION_STATE_INVALID"


def test_retry_cannot_predate_prior_completion() -> None:
    graph = valid_graph()
    first = {
        **graph["attempts"][0].to_dict(),
        "state": "ABORTED",
        "updated_at": "2026-08-27T12:01:00Z",
        "cleanup_outcome": "clean",
    }
    retry = {
        **graph["attempts"][0].to_dict(),
        "attempt_id": "ATTEMPT-000002",
        "prior_attempt_id": first["attempt_id"],
    }
    graph["attempts"] = [
        AttemptRecord.from_mapping(first), AttemptRecord.from_mapping(retry),
    ]
    with pytest.raises(LabValidationError) as raised:
        validate_relations(**graph)
    assert raised.value.code == "RELATION_TIME_INVALID"


def test_evidence_must_match_attempt_candidate_base_catalog_and_test() -> None:
    graph = valid_graph(with_candidate=True)
    evidence = evidence_mapping()
    graph["evidence"] = [EvidenceRecord.from_mapping(evidence)]
    validate_relations(**graph)
    evidence["base_commit"] = "c" * 40
    graph["evidence"] = [EvidenceRecord.from_mapping(evidence)]
    with pytest.raises(LabValidationError) as raised:
        validate_relations(**graph)
    assert raised.value.code == "RELATION_IDENTITY_MISMATCH"


def test_failure_cannot_reference_itself() -> None:
    graph = valid_graph()
    failure = failure_mapping()
    failure["related_failure_ids"] = [failure["failure_id"]]
    graph["failures"] = [FailureRecord.from_mapping(failure)]
    with pytest.raises(LabValidationError) as raised:
        validate_relations(**graph)
    assert raised.value.code == "RELATION_CYCLE_INVALID"
