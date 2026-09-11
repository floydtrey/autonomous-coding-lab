from dataclasses import replace

import pytest

from tests.test_integration_v3 import invocation, qualification
from worker_lab.errors import LabValidationError
from worker_lab.integration_v3 import InvocationState, authorize_invocation, transition_invocation
from worker_lab.invocation_store_v3 import InvocationStoreV3
from worker_lab.provider_binding import ProviderBindingStore, create_provider_binding


def _fixture(tmp_path):
    binding = create_provider_binding("BINDING-0001", qualification())
    binding_store = ProviderBindingStore(tmp_path / "bindings")
    binding_store.create(binding)
    record = invocation(binding)
    store = InvocationStoreV3(tmp_path / "state")
    store.create(record)
    return store, binding_store, record


def test_store_creates_and_reads_only_prepared_v3_records(tmp_path):
    store, _, record = _fixture(tmp_path)
    assert store.read(record.invocation_id) == record
    with pytest.raises(LabValidationError) as duplicate:
        store.create(record)
    assert duplicate.value.code == "INTEGRATION_V3_INVOCATION_EXISTS"
    with pytest.raises(LabValidationError) as nonprepared:
        store.create(replace(record, state=InvocationState.REJECTED))
    assert nonprepared.value.code == "INTEGRATION_V3_CREATE_INVALID"


def test_authorization_persistence_requires_exact_durable_binding(tmp_path):
    store, binding_store, record = _fixture(tmp_path)
    authorized = authorize_invocation(
        record,
        binding_store=binding_store,
        controller_identity="trusted-controller",
        authorized_at="2026-09-11T00:00:00Z",
    )
    with pytest.raises(LabValidationError) as missing:
        store.save_transition(authorized, expected_digest=record.digest())
    assert missing.value.code == "INTEGRATION_V3_PROVIDER_BINDING_REQUIRED"
    store.save_transition(
        authorized,
        expected_digest=record.digest(),
        binding_store=binding_store,
    )
    assert store.read(record.invocation_id) == authorized


def test_store_rejects_stale_writes_and_immutable_identity_changes(tmp_path):
    store, binding_store, record = _fixture(tmp_path)
    authorized = authorize_invocation(
        record,
        binding_store=binding_store,
        controller_identity="trusted-controller",
        authorized_at="2026-09-11T00:00:00Z",
    )
    with pytest.raises(LabValidationError) as stale:
        store.save_transition(
            authorized,
            expected_digest="sha256:" + "0" * 64,
            binding_store=binding_store,
        )
    assert stale.value.code == "INTEGRATION_V3_STALE_WRITE"
    tampered = replace(authorized, logical_target_id="target:other")
    with pytest.raises(LabValidationError) as immutable:
        store.save_transition(
            tampered,
            expected_digest=record.digest(),
            binding_store=binding_store,
        )
    assert immutable.value.code == "INTEGRATION_V3_IDENTITY_IMMUTABLE"


def test_terminal_invocation_cannot_reopen(tmp_path):
    store, _, record = _fixture(tmp_path)
    rejected = transition_invocation(record, InvocationState.REJECTED)
    store.save_transition(rejected, expected_digest=record.digest())
    reopened = replace(rejected, state=InvocationState.PREPARED)
    with pytest.raises(LabValidationError) as terminal:
        store.save_transition(reopened, expected_digest=rejected.digest())
    assert terminal.value.code == "INTEGRATION_V3_TERMINAL_IMMUTABLE"
