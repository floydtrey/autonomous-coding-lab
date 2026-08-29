import pytest

from worker_lab.errors import LabValidationError
from worker_lab.integration import InvocationState, transition_invocation
from worker_lab.invocation_store import InvocationStore
from tests.test_integration import record


def test_store_creates_once_and_persists_only_legal_transitions(tmp_path):
    store = InvocationStore(tmp_path / "state")
    prepared = record()
    store.create(prepared)
    with pytest.raises(LabValidationError) as error:
        store.create(prepared)
    assert error.value.code == "INTEGRATION_INVOCATION_EXISTS"

    authorized = transition_invocation(
        prepared, InvocationState.AUTHORIZED, authorized_by="trusted-controller", authorized_at="2026-08-28T00:00:00Z"
    )
    store.save_transition(authorized, expected_digest=prepared.digest())
    assert store.read(prepared.invocation_id) == authorized


def test_terminal_invocation_cannot_reopen(tmp_path):
    store = InvocationStore(tmp_path / "state")
    prepared = record()
    store.create(prepared)
    rejected = transition_invocation(prepared, InvocationState.REJECTED)
    store.save_transition(rejected, expected_digest=prepared.digest())
    with pytest.raises(LabValidationError) as error:
        store.save_transition(rejected, expected_digest=rejected.digest())
    assert error.value.code == "INTEGRATION_TERMINAL_IMMUTABLE"


def test_store_rejects_invalid_id_and_stale_transition(tmp_path):
    store = InvocationStore(tmp_path / "state")
    with pytest.raises(LabValidationError) as error:
        store.read("../escape")
    assert error.value.code == "INTEGRATION_FIELD_INVALID"
    prepared = record()
    store.create(prepared)
    authorized = transition_invocation(
        prepared, InvocationState.AUTHORIZED, authorized_by="trusted-controller", authorized_at="2026-08-28T00:00:00Z"
    )
    with pytest.raises(LabValidationError) as error:
        store.save_transition(authorized, expected_digest="sha256:" + "b" * 64)
    assert error.value.code == "INTEGRATION_STALE_WRITE"