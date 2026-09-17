import json
from dataclasses import replace

import pytest

from tests.test_job_admission import setup_job, admit
from tests.test_application_service_v3 import _binding, _success_custody, CONTROLLER
from worker_lab.attempt_store import AttemptStore
from worker_lab.canonical import canonical_json
from worker_lab.controller_task_packet import build_controller_task_packet
from worker_lab.dispatch_client import dispatch_workspace_write
from worker_lab.errors import LabValidationError
from worker_lab.git_workspace_evidence import inspect_git_workspace_result
from worker_lab.integration_v3 import InvocationRecordV3, InvocationState, ValidationStage
from worker_lab.job_admission import JobAuthorityProfile, load_task_authorities
from worker_lab.job_plan import JobPlan
from worker_lab.output_acceptance import OutputAcceptance
from worker_lab.process_custody import ProcessCustodyStore
from worker_lab.provider_binding import ProviderBindingStore
from worker_lab.result_acceptance_v3 import accept_workspace_write_response_v3, parse_result_v3
from worker_lab.service_runtime_v3 import _workspace_write_task
from worker_lab.storage import AtomicRecordStore


MODEL = "record_ledger/models.py"
OPTIONAL = "record_ledger/optional_a.py"
ALLOWED = [MODEL, OPTIONAL, "record_ledger/optional_b.py"]


def output(**updates):
    value = dict(schema_version="worker-lab-output-acceptance:v1",
        allowed_writable_paths=ALLOWED, required_changed_paths=[MODEL],
        required_artifact_paths=[MODEL], required_evidence=[
            "protected-test-results:v1", "worker-output:v1", "workspace-diff:v1"], allow_noop=False)
    value.update(updates)
    return value


@pytest.mark.parametrize("changes,requirements,criteria_pass,accepted", [
    ([MODEL], {}, True, True),
    ([MODEL], {"required_artifact_paths": [OPTIONAL]}, True, False),
    ([OPTIONAL], {}, True, False),
    ([MODEL, "outside.py"], {}, True, False),
    ([], {"required_changed_paths": [], "allow_noop": True}, True, True),
    ([], {}, True, False),
    ([], {"required_changed_paths": []}, True, False),
    ([], {"required_changed_paths": [], "allow_noop": True}, False, False),
])
def test_admission_dispatch_and_independent_output_acceptance(tmp_path, changes, requirements, criteria_pass, accepted):
    lab, target, plan, service = setup_job(tmp_path)
    value = plan.to_dict()
    profile_path = lab / "job-authorities" / "record-model-authority" / "v1.json"
    profile_value = json.loads(profile_path.read_text(encoding="utf-8"))
    profile_value["writable_paths"] = ALLOWED
    profile = JobAuthorityProfile.from_mapping(profile_value)
    AtomicRecordStore(lab / "job-authorities").write("record-model-authority/v1.json", profile)
    value["tasks"][0]["authority_ref"]["digest"] = profile.digest()
    value["tasks"][0]["required_outputs"] = output(**requirements)
    plan = JobPlan.from_mapping(value)
    attempt_id = admit(service, plan, target)
    workspaces = tmp_path / "workspaces"
    workspaces.mkdir()
    service.prepare_workspace(attempt_id, target, workspaces)
    ready = AttemptStore(lab / "state").read(attempt_id)
    packet = build_controller_task_packet(ready, controller_identity=CONTROLLER,
        user_request=plan.objective.text, no_context=True)
    binding = _binding(lab)
    prepared = service.prepare_invocation(attempt_id, workspaces, packet.to_json(),
        logical_target_id=plan.objective.target_id, provider_binding_id=binding.binding_id,
        provider_binding_digest=binding.digest()).to_dict()["record"]
    invocation = InvocationRecordV3.from_mapping(prepared)
    assert invocation.output_acceptance == plan.task("A").required_outputs
    assert invocation.schema_version == "worker-lab-framework-invocation:v4"
    assert InvocationRecordV3.from_mapping(invocation.to_dict()) == invocation
    changed_contract = replace(invocation.output_acceptance, required_evidence=())
    assert replace(invocation, output_acceptance=changed_contract).identity_digest() != invocation.identity_digest()
    # Fixture authorization only: the production job execution gate stays closed.
    invocation = replace(invocation, state=InvocationState.DISPATCHING,
        authorized_by=CONTROLLER, authorized_at="2026-09-11T08:00:00Z")
    definition, policy, role, context, catalog = load_task_authorities(lab, ready)
    task = _workspace_write_task(invocation, definition, policy, role, context, catalog)
    workspace = workspaces / attempt_id
    for path in changes:
        (workspace / path).write_text("# candidate\n", encoding="utf-8")
    evidence = inspect_git_workspace_result(invocation, state_root=lab / "state", workspace_path=workspace)
    custody_store = ProcessCustodyStore(lab / "state")
    _success_custody(invocation, workspace, custody_store)
    stages = tuple(ValidationStage(t, "pass" if criteria_pass else "fail", None if criteria_pass else "TEST_FAILED")
                   for t in invocation.test_ids)

    def runner(raw):
        sent = json.loads(raw)
        assert sent["workspace_write"]["output_acceptance"] == output(**requirements)
        assert sent["invocation"]["output_acceptance"] == sent["workspace_write"]["output_acceptance"]
        return canonical_json(dict(schema_version="worker-lab-provider-dispatch-response:v1",
            invocation_digest=invocation.identity_digest(), provider_binding_digest=binding.digest(),
            provider_adapter_id=binding.provider_adapter_id, framework_task_digest="sha256:" + "a" * 64,
            context_digest="sha256:" + "b" * 64, candidate_digest="sha256:" + "c" * 64,
            changed_paths=list(evidence.changed_paths),
            validation_stages=[dict(test_id=t, outcome="pass") for t in invocation.test_ids],
            worker_output_digest="sha256:" + "d" * 64)).encode()

    def accept():
        response = dispatch_workspace_write(invocation, prompt=packet.to_json(), workspace_write=task,
            binding_store=ProviderBindingStore(lab / "state"), runner=runner)
        return accept_workspace_write_response_v3(response, invocation, custody_store.read(invocation.invocation_id),
            started_at="2026-09-11T08:00:00Z", ended_at="2026-09-11T08:00:01Z",
            state_root=lab / "state", custody_store=custody_store, source_evidence=evidence,
            validation_stages=stages, workspace_path=workspace)

    if accepted:
        result = accept()
        assert result.process_outcome == "pass"
        assert result.source_evidence.changed_paths == tuple(sorted(changes))
        assert parse_result_v3(canonical_json(result.to_dict()), invocation) == result
    else:
        with pytest.raises(LabValidationError):
            accept()
        assert not (lab / "state" / "candidates").exists()


@pytest.mark.parametrize("value", [
    ["changed-files", "test-results"],
    output(required_evidence=["test-results"]),
    output(required_changed_paths=["outside.py"]),
    output(allow_noop=True),
    output(allow_noop="yes"),
    output(required_artifact_paths=["../outside"]),
])
def test_ambiguous_or_contradictory_contracts_reject(value):
    with pytest.raises(LabValidationError):
        OutputAcceptance.from_mapping(value)


def test_output_contract_identity_and_missing_evidence():
    contract = OutputAcceptance.from_mapping(output())
    noop = OutputAcceptance.from_mapping(output(required_changed_paths=[], allow_noop=True))
    assert contract.digest() != noop.digest()
    with pytest.raises(LabValidationError, match="evidence is missing"):
        contract.validate_evidence(["workspace-diff:v1"])


def test_exercise_role_labels_are_not_inferred():
    from types import SimpleNamespace
    from worker_lab.service_runtime_v3 import _output_contract
    with pytest.raises(LabValidationError):
        _output_contract(SimpleNamespace(writable_paths=ALLOWED),
                         SimpleNamespace(required_outputs=["changed-files", "test-results"]))


def test_deleted_required_artifact_fails_even_if_path_changed(tmp_path):
    contract = OutputAcceptance.from_mapping(output())
    contract.validate_changes([MODEL])
    with pytest.raises(LabValidationError, match="missing"):
        contract.validate_artifacts(tmp_path)
