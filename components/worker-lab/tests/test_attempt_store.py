from dataclasses import replace
from pathlib import Path

import pytest

from worker_lab.attempt_store import AttemptStore
from worker_lab.errors import LabValidationError
from worker_lab.lifecycle import transition_attempt
from worker_lab.models import AttemptState
from worker_lab.integration import InvocationRecord, InvocationState, transition_invocation
from worker_lab.invocation_store import InvocationStore
from tests.test_integration import record
from tests.test_lifecycle import attempt


def test_legal_transition_is_persisted(tmp_path: Path) -> None:
    store = AttemptStore(tmp_path / "state")
    original = attempt()
    store.create(original)
    updated = transition_attempt(
        original, AttemptState.READY, occurred_at="2026-08-27T12:00:01Z"
    )
    store.save_transition(updated)
    assert store.read(original.attempt_id) == updated


def test_duplicate_and_immutable_identity_changes_are_rejected(tmp_path: Path) -> None:
    store = AttemptStore(tmp_path / "state")
    original = attempt()
    store.create(original)
    with pytest.raises(LabValidationError) as duplicate:
        store.create(original)
    assert duplicate.value.code == "ATTEMPT_EXISTS"
    updated = transition_attempt(
        original, AttemptState.READY, occurred_at="2026-08-27T12:00:01Z"
    )
    with pytest.raises(LabValidationError) as changed:
        store.save_transition(replace(updated, task_digest="sha256:" + "f" * 64))
    assert changed.value.code == "ATTEMPT_IDENTITY_IMMUTABLE"
    assert store.read(original.attempt_id) == original


def test_new_attempt_must_be_clean_draft(tmp_path: Path) -> None:
    store = AttemptStore(tmp_path / "state")
    with pytest.raises(LabValidationError) as raised:
        store.create(replace(attempt(), state=AttemptState.RUNNING))
    assert raised.value.code == "ATTEMPT_CREATE_STATE_INVALID"
    assert not (tmp_path / "state").exists()


def test_terminal_attempt_cannot_be_reopened(tmp_path: Path) -> None:
    store = AttemptStore(tmp_path / "state")
    original = attempt()
    store.create(original)
    aborted = transition_attempt(
        original,
        AttemptState.ABORTED,
        occurred_at="2026-08-27T12:00:01Z",
        cleanup_outcome="workspace absent",
    )
    store.save_transition(aborted)
    with pytest.raises(LabValidationError) as raised:
        store.save_transition(replace(aborted, state=AttemptState.READY))
    assert raised.value.code == "ATTEMPT_TERMINAL_IMMUTABLE"


def test_retry_requires_distinct_identity_and_terminal_prior(tmp_path: Path) -> None:
    store = AttemptStore(tmp_path / "state")
    original = attempt()
    store.create(original)
    retry = replace(original, attempt_id="ATTEMPT-0002", prior_attempt_id=original.attempt_id)
    with pytest.raises(LabValidationError) as active:
        store.create(retry)
    assert active.value.code == "ATTEMPT_PRIOR_ACTIVE"
    self_retry = replace(original, attempt_id="ATTEMPT-0002", prior_attempt_id="ATTEMPT-0002")
    with pytest.raises(LabValidationError) as cycle:
        store.create(self_retry)
    assert cycle.value.code == "ATTEMPT_RETRY_CYCLE"


def test_terminal_attempt_can_be_linked_by_new_retry(tmp_path: Path) -> None:
    store = AttemptStore(tmp_path / "state")
    original = attempt()
    store.create(original)
    aborted = transition_attempt(
        original,
        AttemptState.ABORTED,
        occurred_at="2026-08-27T12:00:01Z",
        cleanup_outcome="workspace absent",
    )
    store.save_transition(aborted)
    retry = replace(
        original,
        attempt_id="ATTEMPT-0002",
        prior_attempt_id=original.attempt_id,
        created_at="2026-08-27T12:00:02Z",
        updated_at="2026-08-27T12:00:02Z",
    )
    store.create(retry)
    assert store.read(retry.attempt_id).prior_attempt_id == original.attempt_id


def test_running_binding_reloads_exact_authorized_invocation(tmp_path: Path) -> None:
    attempts = AttemptStore(tmp_path / "state")
    invocations = InvocationStore(tmp_path / "state")
    original = attempt()
    attempts.create(original)
    ready = transition_attempt(original, AttemptState.READY, occurred_at="2026-08-27T12:00:01Z")
    attempts.save_transition(ready)
    value = record().to_dict()
    value.update({
        "attempt_id": ready.attempt_id, "exercise_id": ready.exercise_id,
        "exercise_version": ready.exercise_version, "policy_id": ready.policy_id,
        "policy_version": ready.policy_version, "policy_digest": ready.policy_digest,
        "role_id": ready.role_id, "role_version": ready.role_version, "role_digest": ready.role_digest,
        "context_digest": ready.context_digest, "task_digest": ready.task_digest,
        "test_catalog_version": ready.evaluator_catalog_version,
        "test_catalog_digest": ready.evaluator_catalog_digest, "starting_commit": ready.starting_commit,
        "sandbox_mode": ready.sandbox_mode, "operation": "workspace-write-code-task",
        "framework_contract_version": "worker-lab-framework-adapter:v3",
        "writable_paths": ["app.py"],
    })
    prepared = InvocationRecord.from_mapping(value)
    invocations.create(prepared)
    authorized = transition_invocation(prepared, InvocationState.AUTHORIZED, authorized_by="trusted-controller", authorized_at="2026-08-27T12:00:01Z")
    invocations.save_transition(authorized, expected_digest=prepared.digest())
    with pytest.raises(LabValidationError):
        attempts.bind_authorized_invocation(invocations, invocation_id=authorized.invocation_id,
                                            expected_invocation_identity="sha256:" + "f" * 64,
                                            occurred_at="2026-08-27T12:00:02Z")
    bound = attempts.bind_authorized_invocation(invocations, invocation_id=authorized.invocation_id,
                                                expected_invocation_identity=authorized.identity_digest(),
                                                occurred_at="2026-08-27T12:00:02Z")
    assert bound.runtime_identity == authorized.identity_digest()
