from dataclasses import replace

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.integration import InvocationRecord, InvocationState, transition_invocation
from worker_lab.lifecycle import bind_authorized_invocation, transition_attempt
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
            runtime_identity=DIGEST_B if state is AttemptState.RUNNING else None,
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


def test_running_binding_revalidates_exact_authorized_invocation() -> None:
    ready = transition_attempt(attempt(), AttemptState.READY, occurred_at="2026-08-27T12:00:01Z")
    from tests.test_integration import record
    value = record().to_dict()
    value.update({
        "attempt_id": ready.attempt_id, "exercise_id": ready.exercise_id,
        "exercise_version": ready.exercise_version, "policy_id": ready.policy_id,
        "policy_version": ready.policy_version, "policy_digest": ready.policy_digest,
        "role_id": ready.role_id, "role_version": ready.role_version,
        "role_digest": ready.role_digest, "context_digest": ready.context_digest,
        "task_digest": ready.task_digest, "test_catalog_version": ready.evaluator_catalog_version,
        "test_catalog_digest": ready.evaluator_catalog_digest, "starting_commit": ready.starting_commit,
        "sandbox_mode": ready.sandbox_mode, "operation": "workspace-write-code-task",
        "writable_paths": ["app.py"],
    })
    prepared = InvocationRecord.from_mapping(value)
    authorized = transition_invocation(
        prepared, InvocationState.AUTHORIZED, authorized_by="trusted-controller",
        authorized_at="2026-08-27T12:00:01Z",
    )
    running = bind_authorized_invocation(ready, authorized, occurred_at="2026-08-27T12:00:02Z")
    assert running.runtime_identity == authorized.identity_digest()
    changed = authorized.to_dict()
    changed["attempt_id"] = "ATTEMPT-9999"
    with pytest.raises(LabValidationError) as error:
        bind_authorized_invocation(
            ready, InvocationRecord.from_mapping(changed), occurred_at="2026-08-27T12:00:02Z"
        )
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"
