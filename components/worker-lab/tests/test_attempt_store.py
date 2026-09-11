from dataclasses import replace
from pathlib import Path

import pytest

from worker_lab.attempt_store import AttemptStore
from worker_lab.errors import LabValidationError
from worker_lab.lifecycle import transition_attempt
from worker_lab.models import AttemptState
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


