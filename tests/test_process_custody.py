import pytest

from worker_lab.errors import LabValidationError
from worker_lab.process_custody import (
    PROCESS_CUSTODY_SCHEMA, CustodyState, ProcessCustodyRecord, ProcessCustodyStore,
    transition_custody,
)
from worker_lab.windows_job import controller_is_active, recover_absence_after_controller_exit


DIGEST = "sha256:" + "a" * 64


def custody(**updates):
    value = {
        "schema_version": PROCESS_CUSTODY_SCHEMA, "invocation_digest": DIGEST,
        "invocation_id": "INVOCATION-001", "controller_pid": 10,
        "controller_creation_time_100ns": 100, "adapter_pid": None,
        "adapter_creation_time_100ns": None, "containment_mode": "windows-job-kill-on-close",
        "state": "PREPARED", "request_sent": False, "exit_code": None,
        "active_process_count": None, "absence_verified_at": None, "first_failure": None,
    }
    value.update(updates)
    return ProcessCustodyRecord.from_mapping(value)


def test_custody_guarded_happy_path_and_terminal_storage(tmp_path):
    store = ProcessCustodyStore(tmp_path / "state")
    prepared = custody()
    store.create(prepared)
    assigned = transition_custody(
        prepared, CustodyState.ASSIGNED, adapter_pid=20, adapter_creation_time_100ns=200
    )
    store.save_transition(assigned, expected_digest=prepared.digest())
    dispatching = transition_custody(assigned, CustodyState.DISPATCHING)
    store.save_transition(dispatching, expected_digest=assigned.digest())
    exited = transition_custody(dispatching, CustodyState.EXITED, exit_code=0, active_process_count=0)
    store.save_transition(exited, expected_digest=dispatching.digest())
    verified = transition_custody(
        exited, CustodyState.ABSENCE_VERIFIED, active_process_count=0,
        absence_verified_at="2026-08-28T00:00:01Z",
    )
    store.save_transition(verified, expected_digest=exited.digest())
    assert store.read(prepared.invocation_id) == verified
    with pytest.raises(LabValidationError) as error:
        store.save_transition(verified, expected_digest=verified.digest())
    assert error.value.code == "INTEGRATION_CUSTODY_TERMINAL"


def test_custody_rejects_false_absence_and_stale_write(tmp_path):
    with pytest.raises(LabValidationError):
        custody(state="ASSIGNED")
    with pytest.raises(LabValidationError):
        custody(state="ABSENCE_VERIFIED", active_process_count=1,
                absence_verified_at="2026-08-28T00:00:01Z")
    store = ProcessCustodyStore(tmp_path / "state")
    prepared = custody()
    store.create(prepared)
    assigned = transition_custody(
        prepared, CustodyState.ASSIGNED, adapter_pid=20, adapter_creation_time_100ns=200
    )
    with pytest.raises(LabValidationError) as error:
        store.save_transition(assigned, expected_digest="sha256:" + "b" * 64)
    assert error.value.code == "INTEGRATION_CUSTODY_STALE_WRITE"


def test_controller_identity_rejects_pid_reuse():
    record = custody()
    assert controller_is_active(record, probe=lambda pid: 100)
    assert not controller_is_active(record, probe=lambda pid: 101)
    assert not controller_is_active(record, probe=lambda pid: None)


def test_restart_recovery_waits_for_live_controller_and_proves_absence_after_exit():
    record = custody(
        state="TERMINATED", adapter_pid=20, adapter_creation_time_100ns=200,
        request_sent=True, active_process_count=0, first_failure="INTEGRATION_CONTAINMENT_FAILED",
    )
    assert recover_absence_after_controller_exit(record, probe=lambda pid: 100) is None
    failed, verified = recover_absence_after_controller_exit(
        record, probe=lambda pid: 101, now=lambda: "2026-08-28T00:00:01Z"
    )
    assert failed.state is CustodyState.TERMINATED
    assert verified.state is CustodyState.ABSENCE_VERIFIED
    assert verified.active_process_count == 0


def test_recovery_rejects_incomplete_or_contradictory_absence_evidence():
    for record in (
        custody(),
        custody(state="UNCERTAIN", active_process_count=None, first_failure="INTEGRATION_OUTCOME_UNCERTAIN"),
        custody(state="TERMINATED", active_process_count=1, first_failure="INTEGRATION_CONTAINMENT_FAILED"),
    ):
        with pytest.raises(LabValidationError) as error:
            recover_absence_after_controller_exit(record, probe=lambda pid: None)
        assert error.value.code == "INTEGRATION_OUTCOME_UNCERTAIN"


def test_uncertain_or_non_dispatched_custody_never_becomes_verified_absence():
    uncertain = custody(
        state="UNCERTAIN", active_process_count=0, first_failure="INTEGRATION_OUTCOME_UNCERTAIN"
    )
    with pytest.raises(LabValidationError) as error:
        transition_custody(
            uncertain, CustodyState.ABSENCE_VERIFIED, active_process_count=0,
            absence_verified_at="2026-08-28T00:00:01Z",
        )
    assert error.value.code == "INTEGRATION_CUSTODY_TRANSITION_INVALID"
    non_dispatched = custody(
        state="TERMINATED", active_process_count=0, first_failure="INTEGRATION_CONTAINMENT_FAILED"
    )
    with pytest.raises(LabValidationError) as error:
        recover_absence_after_controller_exit(non_dispatched, probe=lambda _: None)
    assert error.value.code == "INTEGRATION_OUTCOME_UNCERTAIN"
