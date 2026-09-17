import json
from pathlib import Path

import pytest

from tests.job_fixture import create_target
from tests.test_job_plan import fixture, FIXTURE
from tests.test_application_service_v3 import _binding, CONTROLLER
from tests.test_controller_task_packet import build_controller_task_packet, kc_response
from worker_lab.application_service import WorkerLabApplicationService
from worker_lab.attempt_store import AttemptStore
from worker_lab.errors import LabValidationError
from worker_lab.job_admission import JobAuthorityProfile, JobTaskDefinition, load_task_authorities
from worker_lab.job_plan import JobPlan
from worker_lab.integration_v3 import InvocationRecordV3
from worker_lab.storage import AtomicRecordStore


def setup_job(tmp_path):
    lab = tmp_path / "lab"
    target = tmp_path / "target"
    create_target(target)
    plan = JobPlan.from_mapping(fixture())
    profiles = AtomicRecordStore(lab / "job-authorities")
    for task in plan.tasks:
        profile = JobAuthorityProfile.from_mapping(json.loads(
            (FIXTURE.parent / (task.authority_ref.profile_id + ".json")).read_text()))
        assert profile.digest() == task.authority_ref.digest
        profiles.write(f"{task.authority_ref.profile_id}/v1.json", profile)
    service = WorkerLabApplicationService(lab, clock=lambda: "2026-09-17T01:00:00Z")
    return lab, target, plan, service


def admit(service, plan, target):
    return service.admit_job_task(plan, "A", target, approved_by=CONTROLLER,
                                  approved_plan_digest=plan.digest()).identity


@pytest.mark.parametrize("no_context", [False, True])
def test_first_fixture_task_admits_and_prepares_without_curriculum(tmp_path, no_context):
    lab, target, plan, service = setup_job(tmp_path)
    attempt_id = admit(service, plan, target)
    attempt = AttemptStore(lab / "state").read(attempt_id)
    definition, policy, role, context, catalog = load_task_authorities(lab, attempt)
    assert isinstance(definition, JobTaskDefinition)
    assert definition.task_id == "A"
    assert definition.plan == plan
    assert definition.plan.task("A").acceptance_criteria[0].test_ids == ("T001",)
    assert not (lab / "curricula").exists()
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    service.prepare_workspace(attempt_id, target, workspace_root)
    ready = AttemptStore(lab / "state").read(attempt_id)
    packet = build_controller_task_packet(ready, controller_identity=CONTROLLER,
        user_request=plan.objective.text,
        **({"no_context": True} if no_context else {"kc_search_response": kc_response()}))
    if no_context:
        assert packet.context_mode == "none"
        assert packet.knowledge_evidence == ()
    binding = _binding(lab)
    prepared = service.prepare_invocation(attempt_id, workspace_root, packet.to_json(),
        logical_target_id=plan.objective.target_id, provider_binding_id=binding.binding_id,
        provider_binding_digest=binding.digest()).to_dict()
    record = prepared["record"]
    assert record["state"] == "PREPARED"
    assert record["exercise_id"] == attempt.exercise_id == definition.exercise_id
    assert record["exercise_digest"] == definition.digest()
    assert record["task_digest"] == attempt.task_digest
    assert record["policy_digest"] == policy.digest()
    assert record["test_catalog_digest"] == catalog.digest()
    assert record["controller_task_packet_digest"] == packet.digest()
    assert record["writable_paths"] == ["record_ledger/models.py"]
    assert "T001" in record["test_ids"]
    with pytest.raises(LabValidationError, match="admission/preparation only"):
        service.authorize_invocation(prepared["identity"], InvocationRecordV3.from_mapping(record).identity_digest(), CONTROLLER)


def test_bad_approval_and_missing_profile_do_not_create_attempts(tmp_path):
    lab, target, plan, service = setup_job(tmp_path)
    with pytest.raises(LabValidationError) as error:
        service.admit_job_task(plan, "A", target, approved_by=CONTROLLER, approved_plan_digest="sha256:" + "0" * 64)
    assert error.value.code == "JOB_PLAN_APPROVAL_MISMATCH"
    altered = plan.to_dict()
    altered["tasks"][0]["authority_ref"]["profile_id"] = "missing-profile"
    with pytest.raises(LabValidationError):
        admit(service, JobPlan.from_mapping(altered), target)
    assert not (lab / "state").exists()


@pytest.mark.parametrize("mutation", [
    lambda p: p["tasks"][0]["authority_ref"].update(digest="sha256:" + "0" * 64),
    lambda p: p["tasks"][0]["acceptance_criteria"][0].update(test_ids=["T999"]),
    lambda p: p["objective"].update(target_id="target:other"),
    lambda p: p["tasks"][0].update(required_outputs=["something-else"]),
])
def test_task_cannot_invent_authority_or_tests(tmp_path, mutation):
    lab, target, plan, service = setup_job(tmp_path)
    value = plan.to_dict()
    mutation(value)
    with pytest.raises(LabValidationError):
        admit(service, JobPlan.from_mapping(value), target)
    assert not (lab / "state").exists()


def test_same_revision_cannot_be_replaced(tmp_path):
    lab, target, plan, service = setup_job(tmp_path)
    admit(service, plan, target)
    changed = plan.to_dict()
    changed["objective"]["text"] = "Changed approved objective"
    with pytest.raises(LabValidationError):
        admit(service, JobPlan.from_mapping(changed), target)
    assert len(AtomicRecordStore(lab / "state").list_paths("attempts")) == 1


def test_tampered_admission_fails_workspace_preparation(tmp_path):
    lab, target, plan, service = setup_job(tmp_path)
    attempt_id = admit(service, plan, target)
    path = lab / "state" / "job-tasks" / f"{attempt_id}.json"
    value = json.loads(path.read_text())
    value["plan"]["tasks"][0]["budget"]["max_attempts"] = 9
    path.write_text(json.dumps(value))
    workspaces = tmp_path / "workspaces"
    workspaces.mkdir()
    with pytest.raises(LabValidationError):
        service.prepare_workspace(attempt_id, target, workspaces)


def test_missing_job_definition_never_falls_back_to_exercise(tmp_path):
    lab, target, plan, service = setup_job(tmp_path)
    attempt_id = admit(service, plan, target)
    (lab / "state" / "job-tasks" / f"{attempt_id}.json").unlink()
    with pytest.raises(LabValidationError):
        load_task_authorities(lab, AttemptStore(lab / "state").read(attempt_id))
