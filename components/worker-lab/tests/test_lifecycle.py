from dataclasses import replace

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.attempt_store import AttemptStore
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
        "runtime_identity": DIGEST_A if state not in {AttemptState.DRAFT, AttemptState.READY, AttemptState.ABORTED} else None,
        "candidate_digest": None,
        "cleanup_outcome": None,
        "prior_attempt_id": None,
    })


@pytest.mark.parametrize('verdict', [AttemptState.FAILED, AttemptState.NEEDS_REVIEW])
def test_nonaccepting_lifecycle_to_closed(verdict) -> None:
    value = attempt()
    for index, state in enumerate((
        AttemptState.READY, AttemptState.RUNNING, AttemptState.CANDIDATE,
        AttemptState.EVALUATING, verdict, AttemptState.CLOSED,
    ), start=1):
        value = transition_attempt(
            value,
            state,
            occurred_at=f"2026-08-27T12:00:0{index}Z",
            candidate_digest=DIGEST_A if state is AttemptState.CANDIDATE else None,
            runtime_identity=DIGEST_B if state is AttemptState.RUNNING else None,
            cleanup_outcome="workspace removed" if state is AttemptState.CLOSED else None,
        )
    assert value.state is AttemptState.CLOSED
    assert value.candidate_digest == DIGEST_A
    assert value.cleanup_outcome == "workspace removed"


def test_generic_transition_cannot_claim_acceptance() -> None:
    evaluating = replace(attempt(AttemptState.EVALUATING), candidate_digest=DIGEST_A)
    with pytest.raises(LabValidationError) as raised:
        transition_attempt(evaluating, AttemptState.PASSED, occurred_at="2026-08-27T12:00:01Z")
    assert raised.value.code == "ATTEMPT_ACCEPTANCE_REQUIRED"
    assert evaluating.state is AttemptState.EVALUATING


def test_forged_passed_record_cannot_bypass_store_lifecycle(tmp_path) -> None:
    store = AttemptStore(tmp_path)
    current = attempt()
    store.create(current)
    for index, state in enumerate((AttemptState.READY, AttemptState.RUNNING,
                                    AttemptState.CANDIDATE, AttemptState.EVALUATING), start=1):
        current = transition_attempt(current, state,
            occurred_at=f"2026-08-27T12:00:0{index}Z",
            runtime_identity=DIGEST_B if state is AttemptState.RUNNING else None,
            candidate_digest=DIGEST_A if state is AttemptState.CANDIDATE else None)
        store.save_transition(current)
    path = tmp_path / 'attempts' / f'{current.attempt_id}.json'
    before = path.read_bytes()
    forged = replace(current, state=AttemptState.PASSED, updated_at="2026-08-27T12:00:05Z")
    with pytest.raises(LabValidationError) as raised:
        store.save_transition(forged)
    assert raised.value.code == "ATTEMPT_ACCEPTANCE_REQUIRED"
    assert path.read_bytes() == before
    assert store.read(current.attempt_id) == current


def test_historical_passed_record_remains_readable_and_can_close(tmp_path) -> None:
    store = AttemptStore(tmp_path)
    historical = replace(attempt(AttemptState.PASSED), candidate_digest=DIGEST_A)
    # Existing history predates evidence-gated task acceptance; loading it grants
    # no permission to create another PASSED record through the lifecycle API.
    store.records.write(f'attempts/{historical.attempt_id}.json', historical)
    assert store.read(historical.attempt_id) == historical
    closed = transition_attempt(historical, AttemptState.CLOSED,
        occurred_at="2026-08-27T12:00:01Z", cleanup_outcome="historical workspace absent")
    store.save_transition(closed)
    assert store.read(historical.attempt_id).state is AttemptState.CLOSED


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


def test_running_requires_one_exact_runtime_identity_binding() -> None:
    ready = transition_attempt(attempt(), AttemptState.READY, occurred_at="2026-08-27T12:00:01Z")
    with pytest.raises(LabValidationError) as raised:
        transition_attempt(ready, AttemptState.RUNNING, occurred_at="2026-08-27T12:00:02Z")
    assert raised.value.code == "ATTEMPT_RUNTIME_IDENTITY_REQUIRED"
    running = transition_attempt(
        ready, AttemptState.RUNNING, occurred_at="2026-08-27T12:00:02Z", runtime_identity=DIGEST_A
    )
    assert running.runtime_identity == DIGEST_A
    aborted = transition_attempt(
        running, AttemptState.ABORTED, occurred_at="2026-08-27T12:00:03Z", cleanup_outcome="contained"
    )
    assert aborted.runtime_identity == DIGEST_A

