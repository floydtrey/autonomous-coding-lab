import pytest

from worker_lab.errors import LabValidationError
from worker_lab.process_custody import (
    PROCESS_CUSTODY_SCHEMA,
    CustodyState,
    ProcessCustodyRecord,
    ProcessCustodyStore,
    recover_absence_after_controller_exit,
    transition_custody,
)
from worker_lab.windows_job import (
    WINDOWS_JOB_BACKEND_ID,
    WindowsJobCustodyBackend,
    windows_process_identity,
)


DIGEST = "sha256:" + "a" * 64
ABSENCE_DIGEST = "sha256:" + "b" * 64
BACKEND_ID = "fixture-containment:v1"


def custody(**updates):
    value = {
        "schema_version": PROCESS_CUSTODY_SCHEMA,
        "invocation_digest": DIGEST,
        "invocation_id": "INVOCATION-001",
        "backend_id": BACKEND_ID,
        "controller_identity": "fixture-controller:v1:10",
        "worker_identity": None,
        "workspace_content_digest": DIGEST,
        "state": "PREPARED",
        "request_sent": False,
        "exit_code": None,
        "active_workload_count": None,
        "absence_evidence_digest": None,
        "absence_verified_at": None,
        "first_failure": None,
    }
    value.update(updates)
    return ProcessCustodyRecord.from_mapping(value)


class FixtureBackend:
    backend_id = BACKEND_ID

    def __init__(self, evidence=ABSENCE_DIGEST):
        self.evidence = evidence

    def absence_evidence_after_controller_exit(self, record):
        assert record.backend_id == self.backend_id
        return self.evidence


def assigned(record):
    return transition_custody(
        record,
        CustodyState.ASSIGNED,
        worker_identity="fixture-worker:v1:20",
    )


def test_custody_v2_is_backend_neutral_and_rejects_v1_windows_fields():
    record = custody(backend_id="linux-cgroup:v1", controller_identity="linux-session:v1:10")
    assert record.schema_version == "worker-lab-process-custody:v2"
    assert record.backend_id == "linux-cgroup:v1"
    assert not {
        "controller_pid",
        "controller_creation_time_100ns",
        "adapter_pid",
        "adapter_creation_time_100ns",
        "containment_mode",
        "active_process_count",
    }.intersection(record.to_dict())

    old = record.to_dict()
    old["schema_version"] = "worker-lab-process-custody:v1"
    with pytest.raises(LabValidationError) as error:
        ProcessCustodyRecord.from_mapping(old)
    assert error.value.code == "INTEGRATION_CUSTODY_INVALID"


def test_custody_guarded_happy_path_and_terminal_storage(tmp_path):
    store = ProcessCustodyStore(tmp_path / "state")
    prepared = custody()
    store.create(prepared)
    bound = assigned(prepared)
    store.save_transition(bound, expected_digest=prepared.digest())
    dispatching = transition_custody(bound, CustodyState.DISPATCHING)
    store.save_transition(dispatching, expected_digest=bound.digest())
    exited = transition_custody(
        dispatching,
        CustodyState.EXITED,
        exit_code=0,
        active_workload_count=0,
    )
    store.save_transition(exited, expected_digest=dispatching.digest())
    verified = transition_custody(
        exited,
        CustodyState.ABSENCE_VERIFIED,
        active_workload_count=0,
        absence_evidence_digest=ABSENCE_DIGEST,
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
        custody(
            state="ABSENCE_VERIFIED",
            active_workload_count=0,
            absence_verified_at="2026-08-28T00:00:01Z",
        )
    with pytest.raises(LabValidationError):
        custody(
            state="ABSENCE_VERIFIED",
            active_workload_count=1,
            absence_evidence_digest=ABSENCE_DIGEST,
            absence_verified_at="2026-08-28T00:00:01Z",
        )
    store = ProcessCustodyStore(tmp_path / "state")
    prepared = custody()
    store.create(prepared)
    with pytest.raises(LabValidationError) as error:
        store.save_transition(assigned(prepared), expected_digest="sha256:" + "c" * 64)
    assert error.value.code == "INTEGRATION_CUSTODY_STALE_WRITE"


@pytest.mark.parametrize("field", ["backend_id", "controller_identity", "workspace_content_digest"])
def test_custody_rejects_immutable_identity_substitution(tmp_path, field):
    store = ProcessCustodyStore(tmp_path / "state")
    prepared = custody()
    store.create(prepared)
    changes = {
        "backend_id": "other-containment:v1",
        "controller_identity": "other-controller:v1:10",
        "workspace_content_digest": "sha256:" + "c" * 64,
    }
    altered = assigned(custody(**{field: changes[field]}))
    with pytest.raises(LabValidationError) as error:
        store.save_transition(altered, expected_digest=prepared.digest())
    assert error.value.code == "INTEGRATION_CUSTODY_INVALID"


def test_restart_recovery_uses_the_bound_backend_and_proves_absence():
    record = custody(
        state="TERMINATED",
        worker_identity="fixture-worker:v1:20",
        request_sent=True,
        active_workload_count=0,
        first_failure="INTEGRATION_CONTAINMENT_FAILED",
    )
    assert recover_absence_after_controller_exit(
        record, backend=FixtureBackend(None), now=lambda: "2026-08-28T00:00:01Z",
    ) is None
    failed, verified = recover_absence_after_controller_exit(
        record, backend=FixtureBackend(), now=lambda: "2026-08-28T00:00:01Z",
    )
    assert failed.state is CustodyState.TERMINATED
    assert verified.state is CustodyState.ABSENCE_VERIFIED
    assert verified.active_workload_count == 0
    assert verified.absence_evidence_digest == ABSENCE_DIGEST

    class WrongBackend(FixtureBackend):
        backend_id = "wrong-containment:v1"

    with pytest.raises(LabValidationError) as error:
        recover_absence_after_controller_exit(
            record, backend=WrongBackend(), now=lambda: "2026-08-28T00:00:01Z",
        )
    assert error.value.code == "INTEGRATION_CUSTODY_BACKEND_INVALID"


def test_recovery_rejects_incomplete_or_contradictory_absence_evidence():
    for record in (
        custody(),
        custody(
            state="UNCERTAIN",
            active_workload_count=None,
            first_failure="INTEGRATION_OUTCOME_UNCERTAIN",
        ),
        custody(
            state="TERMINATED",
            worker_identity="fixture-worker:v1:20",
            request_sent=True,
            active_workload_count=1,
            first_failure="INTEGRATION_CONTAINMENT_FAILED",
        ),
    ):
        with pytest.raises(LabValidationError) as error:
            recover_absence_after_controller_exit(
                record, backend=FixtureBackend(), now=lambda: "2026-08-28T00:00:01Z",
            )
        assert error.value.code == "INTEGRATION_OUTCOME_UNCERTAIN"


def test_uncertain_or_non_dispatched_custody_never_becomes_verified_absence():
    uncertain = custody(
        state="UNCERTAIN",
        active_workload_count=0,
        first_failure="INTEGRATION_OUTCOME_UNCERTAIN",
    )
    with pytest.raises(LabValidationError) as error:
        transition_custody(
            uncertain,
            CustodyState.ABSENCE_VERIFIED,
            active_workload_count=0,
            absence_evidence_digest=ABSENCE_DIGEST,
            absence_verified_at="2026-08-28T00:00:01Z",
        )
    assert error.value.code == "INTEGRATION_CUSTODY_TRANSITION_INVALID"
    non_dispatched = custody(
        state="TERMINATED",
        active_workload_count=0,
        first_failure="INTEGRATION_CONTAINMENT_FAILED",
    )
    with pytest.raises(LabValidationError) as error:
        recover_absence_after_controller_exit(
            non_dispatched,
            backend=FixtureBackend(),
            now=lambda: "2026-08-28T00:00:01Z",
        )
    assert error.value.code == "INTEGRATION_OUTCOME_UNCERTAIN"


def test_windows_job_backend_owns_pid_reuse_and_absence_semantics():
    record = custody(
        backend_id=WINDOWS_JOB_BACKEND_ID,
        controller_identity=windows_process_identity(10, 100),
        worker_identity=windows_process_identity(20, 200),
        state="TERMINATED",
        request_sent=True,
        active_workload_count=0,
        first_failure="INTEGRATION_CONTAINMENT_FAILED",
    )
    assert WindowsJobCustodyBackend(lambda pid: 100).controller_is_active(record)
    assert not WindowsJobCustodyBackend(lambda pid: 101).controller_is_active(record)
    assert not WindowsJobCustodyBackend(lambda pid: None).controller_is_active(record)
    evidence = WindowsJobCustodyBackend(
        lambda pid: None,
    ).absence_evidence_after_controller_exit(record)
    assert evidence is not None and evidence.startswith("sha256:")
