from dataclasses import replace

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.lifecycle import transition_attempt
from worker_lab.models import ATTEMPT_SCHEMA, AttemptRecord, AttemptState


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def attempt(state: AttemptState = AttemptState.DRAFT) -> AttemptRecord:
    return AttemptRecord.from_mapping({
        "schema_version": ATTEMPT_SCHEMA,
        "attempt_id": "ATTEMPT-0001",
        "curriculum_id": "record-ledger",
        "exercise_id": "strict-records",
        "exercise_version": 1,
        "starting_commit": "1" * 40,
        "context_digest": DIGEST_A,
        "task_digest": DIGEST_B,
        "policy_id": "core-worker-policy",
        "policy_version": 1,
        "policy_digest": DIGEST_A,
        "role_id": "coding-worker",
        "role_version": 1,
        "role_digest": DIGEST_B,
        "sandbox_mode": "workspace-write",
        "state": str(state),
        "created_at": "2026-08-27T12:00:00Z",
        "updated_at": "2026-08-27T12:00:00Z",
        "evaluator_catalog_version": "catalog-v1",
        "evaluator_catalog_digest": DIGEST_A,
        "runtime_identity": None,
        "candidate_digest": None,
        "cleanup_outcome": None,
        "prior_attempt_id": None,
    })


def test_happy_path_to_closed() -> None:
    value = attempt()
    for index, state in enumerate((
        AttemptState.READY, AttemptState.RUNNING, AttemptState.CANDIDATE,
        AttemptState.EVALUATING, AttemptState.PASSED, AttemptState.CLOSED,
    ), start=1):
        value = transition_attempt(
            value,
            state,
            occurred_at=f"2026-08-27T12:00:0{index}Z",
            candidate_digest=DIGEST_A if state is AttemptState.CANDIDATE else None,
            cleanup_outcome="workspace removed" if state is AttemptState.CLOSED else None,
        )
    assert value.state is AttemptState.CLOSED
    assert value.candidate_digest == DIGEST_A
    assert value.cleanup_outcome == "workspace removed"


def test_illegal_transition_does_not_mutate_source() -> None:
    source = attempt()
    with pytest.raises(LabValidationError) as raised:
        transition_attempt(source, AttemptState.RUNNING, occurred_at="2026-08-27T12:00:01Z")
    assert raised.value.code == "ATTEMPT_TRANSITION_INVALID"
    assert source == attempt()


def test_candidate_identity_is_required_and_immutable() -> None:
    running = replace(attempt(AttemptState.RUNNING), updated_at="2026-08-27T12:00:01Z")
    with pytest.raises(LabValidationError) as raised:
        transition_attempt(running, AttemptState.CANDIDATE, occurred_at="2026-08-27T12:00:02Z")
    assert raised.value.code == "ATTEMPT_CANDIDATE_REQUIRED"


def test_terminal_transition_requires_cleanup() -> None:
    passed = replace(attempt(AttemptState.PASSED), updated_at="2026-08-27T12:00:01Z")
    with pytest.raises(LabValidationError) as raised:
        transition_attempt(passed, AttemptState.CLOSED, occurred_at="2026-08-27T12:00:02Z")
    assert raised.value.code == "ATTEMPT_CLEANUP_REQUIRED"


def test_transition_time_cannot_move_backward() -> None:
    source = replace(attempt(), updated_at="2026-08-27T12:00:02Z")
    with pytest.raises(LabValidationError) as raised:
        transition_attempt(source, AttemptState.READY, occurred_at="2026-08-27T12:00:01Z")
    assert raised.value.code == "ATTEMPT_TRANSITION_TIME_INVALID"
