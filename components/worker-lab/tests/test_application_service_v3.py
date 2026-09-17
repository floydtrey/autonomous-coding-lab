from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_cli import write_authority_fixture
from tests.test_controller_task_packet import build_controller_task_packet, kc_response
from tests.test_provider_binding import qualification
from worker_lab.application_service import WorkerLabApplicationService
from worker_lab.attempt_store import AttemptStore
from worker_lab.canonical import canonical_json
from worker_lab.dispatch_client import DISPATCH_RESPONSE_SCHEMA
from worker_lab.errors import LabValidationError
from worker_lab.integration_v3 import InvocationState, ResultRecordV3
from worker_lab.invocation_store_v3 import InvocationStoreV3
from worker_lab.models import AttemptState
from worker_lab.process_custody import (
    PROCESS_CUSTODY_SCHEMA,
    CustodyState,
    ProcessCustodyRecord,
    ProcessCustodyStore,
    transition_custody,
)
from worker_lab.provider_binding import ProviderBindingStore, create_provider_binding
from worker_lab.storage import AtomicRecordStore
from worker_lab.windows_job import workspace_content_digest


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
ABSENCE_DIGEST = "sha256:" + "f" * 64
BACKEND_ID = "fixture-containment:v1"
CONTROLLER = "trusted-controller"


class FixtureCustodyBackend:
    backend_id = BACKEND_ID

    def absence_evidence_after_controller_exit(self, record):
        assert record.backend_id == self.backend_id
        return ABSENCE_DIGEST


def _binding(lab: Path, binding_id: str = "BINDING-0001"):
    binding = create_provider_binding(binding_id, qualification())
    ProviderBindingStore(lab / "state").create(binding)
    return binding


def _prepare(
    tmp_path: Path,
    *,
    runner=None,
    sealed_test_executor=lambda definition, workspace: 0,
    custody_backend=None,
    binding_id: str = "BINDING-0001",
):
    lab, target = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    service = WorkerLabApplicationService(
        lab,
        clock=lambda: "2026-09-11T08:00:00Z",
        workspace_dispatch_runner=runner,
        sealed_test_executor=sealed_test_executor,
        custody_backend=custody_backend,
    )
    attempt_id = service.create_attempt("record-model", 1, target).to_dict()["identity"]
    service.prepare_workspace(attempt_id, target, workspace_root)
    binding = _binding(lab, binding_id)
    attempt = AttemptStore(lab / "state").read(attempt_id)
    packet = build_controller_task_packet(
        attempt,
        controller_identity=CONTROLLER,
        user_request="Implement only the sealed workspace-write task.",
        kc_search_response=kc_response(),
    )
    prepared = service.prepare_invocation(
        attempt_id,
        workspace_root,
        packet.to_json(),
        logical_target_id="target:record-model",
        provider_binding_id=binding.binding_id,
        provider_binding_digest=binding.digest(),
    ).to_dict()
    return service, lab, workspace_root, binding, packet, prepared


def _success_custody(invocation, workspace_path: Path, store: ProcessCustodyStore) -> None:
    prepared = ProcessCustodyRecord.from_mapping({
        "schema_version": PROCESS_CUSTODY_SCHEMA,
        "invocation_digest": invocation.identity_digest(),
        "invocation_id": invocation.invocation_id,
        "backend_id": BACKEND_ID,
        "controller_identity": "fixture-controller:v1:1",
        "worker_identity": None,
        "workspace_content_digest": workspace_content_digest(workspace_path),
        "state": "PREPARED",
        "request_sent": False,
        "exit_code": None,
        "active_workload_count": None,
        "absence_evidence_digest": None,
        "absence_verified_at": None,
        "first_failure": None,
    })
    store.create(prepared)
    assigned = transition_custody(
        prepared,
        CustodyState.ASSIGNED,
        worker_identity="fixture-worker:v1:1",
    )
    store.save_transition(assigned, expected_digest=prepared.digest())
    dispatching = transition_custody(assigned, CustodyState.DISPATCHING)
    store.save_transition(dispatching, expected_digest=assigned.digest())
    exited = transition_custody(
        dispatching,
        CustodyState.EXITED,
        exit_code=0,
        active_workload_count=0,
    )
    store.save_transition(exited, expected_digest=dispatching.digest())
    absent = transition_custody(
        exited,
        CustodyState.ABSENCE_VERIFIED,
        active_workload_count=0,
        absence_evidence_digest=ABSENCE_DIGEST,
        absence_verified_at="2026-09-11T08:00:01Z",
    )
    store.save_transition(absent, expected_digest=exited.digest())


def _terminated_custody(invocation, workspace_path: Path, store: ProcessCustodyStore) -> None:
    prepared = ProcessCustodyRecord.from_mapping({
        "schema_version": PROCESS_CUSTODY_SCHEMA,
        "invocation_digest": invocation.identity_digest(),
        "invocation_id": invocation.invocation_id,
        "backend_id": BACKEND_ID,
        "controller_identity": "fixture-controller:v1:1",
        "worker_identity": None,
        "workspace_content_digest": workspace_content_digest(workspace_path),
        "state": "PREPARED",
        "request_sent": False,
        "exit_code": None,
        "active_workload_count": None,
        "absence_evidence_digest": None,
        "absence_verified_at": None,
        "first_failure": None,
    })
    store.create(prepared)
    assigned = transition_custody(
        prepared,
        CustodyState.ASSIGNED,
        worker_identity="fixture-worker:v1:1",
    )
    store.save_transition(assigned, expected_digest=prepared.digest())
    dispatching = transition_custody(assigned, CustodyState.DISPATCHING)
    store.save_transition(dispatching, expected_digest=assigned.digest())
    terminated = transition_custody(
        dispatching,
        CustodyState.TERMINATED,
        exit_code=1,
        active_workload_count=0,
        first_failure="INTEGRATION_OUTCOME_UNCERTAIN",
    )
    store.save_transition(terminated, expected_digest=dispatching.digest())


def _response(payload: bytes, invocation) -> bytes:
    request = json.loads(payload)
    return canonical_json({
        "schema_version": DISPATCH_RESPONSE_SCHEMA,
        "invocation_digest": invocation.identity_digest(),
        "provider_binding_digest": invocation.provider_binding_digest,
        "provider_adapter_id": request["provider_binding"]["provider_adapter_id"],
        "framework_task_digest": DIGEST_A,
        "context_digest": DIGEST_B,
        "candidate_digest": DIGEST_C,
        "changed_paths": list(invocation.writable_paths),
        "validation_stages": [
            {"test_id": test_id, "outcome": "pass"}
            for test_id in invocation.test_ids
        ],
        "worker_output_digest": DIGEST_A,
    }).encode("utf-8")


def _mutate_authorized_workspace(workspace_path: Path) -> None:
    (workspace_path / "record_ledger" / "models.py").write_text(
        "# changed by V3 fixture\n",
        encoding="utf-8",
    )
    (workspace_path / "tests").mkdir(exist_ok=True)
    (workspace_path / "tests" / "test_models.py").write_text(
        "VALUE = 2\n",
        encoding="utf-8",
    )


def _success_runner(payload, invocation, workspace_path, custody_store):
    _success_custody(invocation, workspace_path, custody_store)
    _mutate_authorized_workspace(workspace_path)
    return _response(payload, invocation)


def _authorize(service, prepared):
    return service.authorize_invocation(
        prepared["identity"],
        prepared["immutable_identity_digest"],
        CONTROLLER,
    ).to_dict()


def test_v3_prepare_binds_logical_target_provider_binding_and_controller_packet(tmp_path: Path) -> None:
    service, lab, workspace_root, binding, packet, prepared = _prepare(tmp_path)
    record = prepared["record"]
    assert record["schema_version"] == "worker-lab-framework-invocation:v4"
    assert record["logical_target_id"] == "target:record-model"
    assert record["provider_binding_id"] == binding.binding_id
    assert record["provider_binding_digest"] == binding.digest()
    assert record["controller_task_packet_digest"] == packet.digest()
    assert record["prompt_digest"] == packet.digest()
    assert record["source_state"]["backend_id"] == "git-workspace:v1"
    assert "model" not in record and "reasoning_effort" not in record

    with pytest.raises(LabValidationError) as error:
        service.prepare_invocation(
            prepared["record"]["attempt_id"],
            workspace_root,
            packet.to_json(),
            logical_target_id="target:record-model",
            provider_binding_id=binding.binding_id,
            provider_binding_digest=binding.digest(),
        )
    assert error.value.code == "INTEGRATION_V3_INVOCATION_EXISTS"
    assert InvocationStoreV3(lab / "state").read(prepared["identity"]).state is InvocationState.PREPARED


def test_v3_prepare_and_authorize_fail_closed_for_binding_or_controller_substitution(tmp_path: Path) -> None:
    lab, target = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    service = WorkerLabApplicationService(lab, clock=lambda: "2026-09-11T08:00:00Z")
    attempt_id = service.create_attempt("record-model", 1, target).to_dict()["identity"]
    service.prepare_workspace(attempt_id, target, workspace_root)
    binding = _binding(lab)
    attempt = AttemptStore(lab / "state").read(attempt_id)
    packet = build_controller_task_packet(
        attempt,
        controller_identity=CONTROLLER,
        user_request="Keep the task bounded.",
        kc_search_response=kc_response(),
    )
    with pytest.raises(LabValidationError) as error:
        service.prepare_invocation(
            attempt_id,
            workspace_root,
            packet.to_json(),
            logical_target_id="target:record-model",
            provider_binding_id=binding.binding_id,
            provider_binding_digest=DIGEST_A,
        )
    assert error.value.code == "PROVIDER_BINDING_MISMATCH"

    prepared = service.prepare_invocation(
        attempt_id,
        workspace_root,
        packet.to_json(),
        logical_target_id="target:record-model",
        provider_binding_id=binding.binding_id,
        provider_binding_digest=binding.digest(),
    ).to_dict()
    with pytest.raises(LabValidationError) as error:
        service.authorize_invocation(
            prepared["identity"],
            prepared["immutable_identity_digest"],
            "different-controller",
        )
    assert error.value.code == "OPERATOR_CONTROLLER_MISMATCH"
    assert InvocationStoreV3(lab / "state").read(prepared["identity"]).state is InvocationState.PREPARED


def test_v3_reject_and_cancel_preserve_terminal_lifecycle_without_dispatch(tmp_path: Path) -> None:
    service, lab, _, _, _, prepared = _prepare(tmp_path)
    rejected = service.reject_invocation(
        prepared["identity"],
        prepared["immutable_identity_digest"],
    ).to_dict()
    assert rejected["record"]["state"] == "REJECTED"
    assert not (lab / "state" / "results").exists()
    assert not (lab / "state" / "process-custody").exists()

    other = tmp_path / "cancel"
    other.mkdir()
    service, lab, _, _, _, prepared = _prepare(other)
    _authorize(service, prepared)
    with pytest.raises(LabValidationError) as error:
        service.cancel_invocation(
            prepared["identity"],
            prepared["immutable_identity_digest"],
            "different-controller",
        )
    assert error.value.code == "OPERATOR_CONTROLLER_MISMATCH"
    cancelled = service.cancel_invocation(
        prepared["identity"],
        prepared["immutable_identity_digest"],
        CONTROLLER,
    ).to_dict()
    assert cancelled["record"]["state"] == "ABORTED"
    assert not (lab / "state" / "results").exists()


def test_v3_dispatch_without_explicit_runner_fails_before_state_mutation(tmp_path: Path) -> None:
    service, lab, workspace_root, _, _, prepared = _prepare(tmp_path)
    _authorize(service, prepared)
    invocation_before = InvocationStoreV3(lab / "state").read(prepared["identity"])
    attempt_before = AttemptStore(lab / "state").read(prepared["record"]["attempt_id"])
    with pytest.raises(LabValidationError) as error:
        service.dispatch_invocation(
            prepared["identity"],
            prepared["immutable_identity_digest"],
            CONTROLLER,
            workspace_root,
        )
    assert error.value.code == "INTEGRATION_EXECUTION_DISABLED"
    assert InvocationStoreV3(lab / "state").read(prepared["identity"]) == invocation_before
    assert AttemptStore(lab / "state").read(attempt_before.attempt_id) == attempt_before
    assert not (lab / "state" / "process-custody").exists()


def test_v3_fake_workspace_dispatch_reaches_independently_reviewable_candidate(tmp_path: Path) -> None:
    service, lab, workspace_root, _, _, prepared = _prepare(
        tmp_path,
        runner=_success_runner,
    )
    _authorize(service, prepared)
    dispatched = service.dispatch_invocation(
        prepared["identity"],
        prepared["immutable_identity_digest"],
        CONTROLLER,
        workspace_root,
    ).to_dict()
    assert dispatched["record"]["state"] == "CANDIDATE"

    invocation = InvocationStoreV3(lab / "state").read(prepared["identity"])
    assert invocation.state is InvocationState.COMPLETED
    result = AtomicRecordStore(lab / "state").read(
        f"results/{prepared['identity']}.json",
        ResultRecordV3.from_mapping,
    )
    assert result.process_outcome == "pass"
    assert result.source_evidence is not None
    assert result.source_evidence.changed_paths == invocation.writable_paths
    assert result.runtime_identity == invocation.provider_binding_digest
    assert result.containment_outcome == "absence-verified"

    review = service.review_candidate(dispatched["identity"]).to_dict()
    assert review["schema_version"] == "worker-lab-service-candidate-review:v2"
    assert review["changed_paths"] == list(invocation.writable_paths)
    assert review["candidate_content_digest"] == DIGEST_C
    assert all(stage["outcome"] == "pass" for stage in review["validation_stages"])


def test_v3_independent_sealed_test_failure_rejects_worker_claimed_success(tmp_path: Path) -> None:
    service, lab, workspace_root, _, _, prepared = _prepare(
        tmp_path,
        runner=_success_runner,
        sealed_test_executor=lambda definition, workspace: 1,
    )
    _authorize(service, prepared)
    with pytest.raises(LabValidationError) as error:
        service.dispatch_invocation(
            prepared["identity"],
            prepared["immutable_identity_digest"],
            CONTROLLER,
            workspace_root,
        )
    assert error.value.code == "INTEGRATION_VALIDATION_FAILED"
    assert not (lab / "state" / "results" / f"{prepared['identity']}.json").exists()
    assert AttemptStore(lab / "state").read(prepared["record"]["attempt_id"]).state is AttemptState.RUNNING


def test_v3_framework_identity_mismatch_cannot_be_accepted(tmp_path: Path) -> None:
    def mismatched(payload, invocation, workspace_path, custody_store):
        _success_custody(invocation, workspace_path, custody_store)
        _mutate_authorized_workspace(workspace_path)
        value = json.loads(_response(payload, invocation))
        value["provider_binding_digest"] = DIGEST_A
        return canonical_json(value).encode("utf-8")

    service, lab, workspace_root, _, _, prepared = _prepare(tmp_path, runner=mismatched)
    _authorize(service, prepared)
    with pytest.raises(LabValidationError) as error:
        service.dispatch_invocation(
            prepared["identity"],
            prepared["immutable_identity_digest"],
            CONTROLLER,
            workspace_root,
        )
    assert error.value.code == "DISPATCH_IDENTITY_INVALID"
    assert not (lab / "state" / "results" / f"{prepared['identity']}.json").exists()


def test_v3_recovery_requires_exact_backend_absence_and_unchanged_workspace(tmp_path: Path) -> None:
    def failing_runner(payload, invocation, workspace_path, custody_store):
        del payload
        _terminated_custody(invocation, workspace_path, custody_store)
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "fixture transport outcome is uncertain",
        )

    backend = FixtureCustodyBackend()
    service, lab, workspace_root, _, _, prepared = _prepare(
        tmp_path,
        runner=failing_runner,
        custody_backend=backend,
    )
    _authorize(service, prepared)
    with pytest.raises(LabValidationError) as error:
        service.dispatch_invocation(
            prepared["identity"],
            prepared["immutable_identity_digest"],
            CONTROLLER,
            workspace_root,
        )
    assert error.value.code == "INTEGRATION_V3_RESULT_INVALID"
    assert InvocationStoreV3(lab / "state").read(prepared["identity"]).state is InvocationState.DISPATCHING
    assert AttemptStore(lab / "state").read(prepared["record"]["attempt_id"]).state is AttemptState.RUNNING

    recovered = service.recover_invocation(
        prepared["identity"],
        prepared["immutable_identity_digest"],
        CONTROLLER,
        workspace_root,
    ).to_dict()
    assert recovered["invocation"]["record"]["state"] == "ABORTED"
    assert recovered["attempt"]["record"]["state"] == "ABORTED"
    assert recovered["custody"]["record"]["state"] == "ABSENCE_VERIFIED"

    repeated = service.recover_invocation(
        prepared["identity"],
        prepared["immutable_identity_digest"],
        CONTROLLER,
        workspace_root,
    ).to_dict()
    assert repeated["invocation"]["record"]["state"] == "ABORTED"
    assert repeated["custody"]["record"]["absence_evidence_digest"] == ABSENCE_DIGEST
