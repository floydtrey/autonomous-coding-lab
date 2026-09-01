import hashlib
import json
from pathlib import Path

import pytest

from tests.test_integration import DIGEST, record, result_mapping
from tests.test_cli import write_authority_fixture
from tests.test_models import (
    attempt_mapping,
    curriculum_mapping,
    evidence_mapping,
    exercise_mapping,
    failure_mapping,
)
from tests.test_policy import context_mapping, policy_mapping, role_mapping
from tests.test_test_catalog import catalog
from worker_lab.application_service import COLLECTIONS, WorkerLabApplicationService
from worker_lab.attempt_store import AttemptStore
from worker_lab.backup import verify_backup
from worker_lab.cli import main
from worker_lab.errors import LabValidationError
from worker_lab.integration import (
    InvocationRecord,
    InvocationState,
    ResultRecord,
    transition_invocation,
)
from worker_lab.invocation_store import InvocationStore
from worker_lab.models import (
    AttemptRecord,
    CurriculumRecord,
    EvidenceRecord,
    ExerciseRecord,
    FailureRecord,
)
from worker_lab.evidence import content_digest, evidence_identity_digest
from worker_lab.policy import ContextManifest, PolicyRecord, RoleRecord
from worker_lab.process_custody import (
    PROCESS_CUSTODY_SCHEMA,
    CustodyState,
    ProcessCustodyRecord,
    ProcessCustodyStore,
    transition_custody,
)
from worker_lab.storage import AtomicRecordStore
from worker_lab.windows_job import workspace_content_digest


def populated_lab(root: Path) -> Path:
    lab = root / "lab"
    definitions = AtomicRecordStore(lab / "curricula")
    state = AtomicRecordStore(lab / "state")
    curriculum = CurriculumRecord.from_mapping(curriculum_mapping())
    exercise = ExerciseRecord.from_mapping(exercise_mapping())
    policy = PolicyRecord.from_mapping(policy_mapping())
    role = RoleRecord.from_mapping(role_mapping())
    context = ContextManifest.from_mapping(context_mapping())
    test_catalog = catalog()
    invocation = record()
    result = ResultRecord.from_mapping(result_mapping(invocation))
    definitions.write("curricula/record-ledger.json", curriculum)
    definitions.write("exercises/record-model/v1.json", exercise)
    definitions.write("policies/core-worker-policy/v1.json", policy)
    definitions.write("roles/coding-worker/v1.json", role)
    definitions.write("contexts/record-model-context/v1.json", context)
    definitions.write("catalogs/worker-lab-v1.json", test_catalog)
    state.write("attempts/ATTEMPT-000001.json", AttemptRecord.from_mapping(attempt_mapping()))
    state.write("invocations/INVOCATION-001.json", invocation)
    state.write("results/INVOCATION-001.json", result)
    state.write("evidence/" + "a" * 64 + ".json", EvidenceRecord.from_mapping(evidence_mapping()))
    state.write("failures/FAILURE-000001.json", FailureRecord.from_mapping(failure_mapping()))
    return lab


def snapshot(root: Path) -> tuple[tuple[str, ...], dict[str, bytes]]:
    directories = tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir()))
    files = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
    return directories, files


def recovery_fixture(
    root: Path,
    *,
    invocation_state: InvocationState = InvocationState.UNCERTAIN,
    custody_state: CustodyState = CustodyState.ABSENCE_VERIFIED,
) -> tuple[Path, Path, str, str]:
    lab, target = write_authority_fixture(root)
    workspace_root = root / "workspaces"
    workspace_root.mkdir()
    service = WorkerLabApplicationService(
        lab,
        clock=lambda: "2026-08-31T12:00:00Z",
    )
    attempt_id = service.create_attempt("record-model", 1, target).to_dict()["identity"]
    service.prepare_workspace(attempt_id, target, workspace_root)
    prepared = service.prepare_invocation(
        attempt_id,
        workspace_root,
        "Prepare one deterministic recovery fixture without dispatching a process.",
    ).to_dict()
    invocation_id = prepared["identity"]
    identity_digest = prepared["immutable_identity_digest"]
    service.authorize_invocation(
        invocation_id,
        identity_digest,
        "trusted-controller",
    )
    invocations = InvocationStore(lab / "state")
    attempts = AttemptStore(lab / "state")
    attempts.bind_authorized_invocation(
        invocations,
        invocation_id=invocation_id,
        expected_invocation_identity=identity_digest,
        occurred_at="2026-08-31T12:00:01Z",
    )
    authorized = invocations.read(invocation_id)
    dispatching = transition_invocation(authorized, InvocationState.DISPATCHING)
    invocations.save_transition(dispatching, expected_digest=authorized.digest())
    if invocation_state is InvocationState.UNCERTAIN:
        invocation = transition_invocation(dispatching, InvocationState.UNCERTAIN)
        invocations.save_transition(invocation, expected_digest=dispatching.digest())
    elif invocation_state is InvocationState.DISPATCHING:
        invocation = dispatching
    else:
        raise AssertionError("unsupported recovery fixture invocation state")

    custody_store = ProcessCustodyStore(lab / "state")
    custody = ProcessCustodyRecord.from_mapping({
        "schema_version": PROCESS_CUSTODY_SCHEMA,
        "invocation_digest": identity_digest,
        "invocation_id": invocation_id,
        "controller_pid": 424242,
        "controller_creation_time_100ns": 123456789,
        "adapter_pid": None,
        "adapter_creation_time_100ns": None,
        "containment_mode": "windows-job-kill-on-close",
        "workspace_content_digest": workspace_content_digest(workspace_root / attempt_id),
        "state": "PREPARED",
        "request_sent": False,
        "exit_code": None,
        "active_process_count": None,
        "absence_verified_at": None,
        "first_failure": None,
    })
    custody_store.create(custody)
    assigned = transition_custody(
        custody,
        CustodyState.ASSIGNED,
        adapter_pid=515151,
        adapter_creation_time_100ns=987654321,
    )
    custody_store.save_transition(assigned, expected_digest=custody.digest())
    dispatch_custody = transition_custody(assigned, CustodyState.DISPATCHING)
    custody_store.save_transition(dispatch_custody, expected_digest=assigned.digest())
    if custody_state is CustodyState.UNCERTAIN:
        final_custody = transition_custody(
            dispatch_custody,
            CustodyState.UNCERTAIN,
            active_process_count=0,
            first_failure="INTEGRATION_OUTCOME_UNCERTAIN",
        )
    else:
        terminated = transition_custody(
            dispatch_custody,
            CustodyState.TERMINATED,
            exit_code=1,
            active_process_count=0,
            first_failure="INTEGRATION_OUTCOME_UNCERTAIN",
        )
        custody_store.save_transition(terminated, expected_digest=dispatch_custody.digest())
        if custody_state is CustodyState.TERMINATED:
            return lab, workspace_root, invocation_id, identity_digest
        final_custody = transition_custody(
            terminated,
            CustodyState.ABSENCE_VERIFIED,
            active_process_count=0,
            absence_verified_at="2026-08-31T12:00:02Z",
        )
        dispatch_custody = terminated
    custody_store.save_transition(final_custody, expected_digest=dispatch_custody.digest())
    return lab, workspace_root, invocation_id, identity_digest


def candidate_fixture(root: Path, *, retain_evidence: bool = False) -> tuple[Path, str]:
    lab = populated_lab(root)
    state = AtomicRecordStore(lab / "state")
    for path in (lab / "state" / "evidence").glob("*.json"):
        path.unlink()
    content = b"retained candidate proposal\n"
    proposal_digest = content_digest(content)
    invocation = record(
        state="DISPATCHING",
        attempt_id="ATTEMPT-000001",
        authorized_by="trusted-controller",
        authorized_at="2026-08-28T00:00:00Z",
    )
    custody = ProcessCustodyRecord.from_mapping({
        "schema_version": PROCESS_CUSTODY_SCHEMA,
        "invocation_digest": invocation.identity_digest(),
        "invocation_id": invocation.invocation_id,
        "controller_pid": 1,
        "controller_creation_time_100ns": 1,
        "adapter_pid": None,
        "adapter_creation_time_100ns": None,
        "containment_mode": "windows-job-kill-on-close",
        "workspace_content_digest": DIGEST,
        "state": "ABSENCE_VERIFIED",
        "request_sent": False,
        "exit_code": None,
        "active_process_count": 0,
        "absence_verified_at": "2026-08-28T00:00:01Z",
        "first_failure": None,
    })
    result_value = result_mapping(invocation)
    result_value.update({
        "proposal_digest": proposal_digest,
        "output_digest": proposal_digest,
        "content_reference": f"proposals/{proposal_digest[7:]}.txt",
        "process_identity": custody.digest(),
    })
    result = ResultRecord.from_mapping(result_value)
    invocation = InvocationRecord.from_mapping({
        **invocation.to_dict(),
        "state": "COMPLETED",
        "result_digest": result.digest(),
    })
    attempt = AttemptRecord.from_mapping({
        **attempt_mapping(),
        "state": "CANDIDATE",
        "runtime_identity": invocation.identity_digest(),
        "candidate_digest": result.digest(),
        "evaluator_catalog_digest": catalog().digest(),
    })
    state.write("attempts/ATTEMPT-000001.json", attempt)
    state.write("invocations/INVOCATION-001.json", invocation)
    state.write("results/INVOCATION-001.json", result)
    state.write("process-custody/INVOCATION-001.json", custody)
    state.write_bytes(result.content_reference, content)
    if retain_evidence:
        evidence_content = b'{"exit_code":0}\n'
        evidence = evidence_mapping()
        evidence.update({
            "attempt_id": attempt.attempt_id,
            "test_catalog_version": attempt.evaluator_catalog_version,
            "test_catalog_digest": attempt.evaluator_catalog_digest,
            "candidate_digest": attempt.candidate_digest,
            "base_commit": attempt.starting_commit,
            "test_id": "T001",
            "content_path": "evidence-content/T001.json",
        })
        provisional = EvidenceRecord.from_mapping(evidence)
        evidence["evidence_digest"] = evidence_identity_digest(
            provisional, content_digest(evidence_content)
        )
        state.write(f"evidence/{evidence['evidence_digest'][7:]}.json", EvidenceRecord.from_mapping(evidence))
        state.write_bytes("evidence-content/T001.json", evidence_content)
    return lab, attempt.attempt_id


def test_health_and_installation_status_are_non_mutating_and_disabled(tmp_path: Path) -> None:
    lab = populated_lab(tmp_path)
    before = snapshot(lab)
    service = WorkerLabApplicationService(lab)
    health = service.health().to_dict()
    installation = service.installation_status().to_dict()
    assert health["schema_version"] == "worker-lab-service-health:v1"
    assert health["status"] == "healthy"
    assert health["data_root_state"] == "present"
    assert health["execution_ready"] is False
    assert health["collection_counts"] == {collection: 1 for collection in COLLECTIONS}
    assert installation["schema_version"] == "worker-lab-service-installation-status:v1"
    assert installation["installation"]["execution_authority"] == "DISABLED"
    assert installation["installation"]["execution_ready"] is False
    assert snapshot(lab) == before


def test_absent_data_root_is_healthy_empty_and_remains_absent(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    health = WorkerLabApplicationService(missing).health().to_dict()
    assert health["data_root_state"] == "absent"
    assert health["collection_counts"] == {collection: 0 for collection in COLLECTIONS}
    assert not missing.exists()


def test_list_and_show_use_stable_strict_dtos_without_mutation(tmp_path: Path) -> None:
    lab = populated_lab(tmp_path)
    service = WorkerLabApplicationService(lab)
    before = snapshot(lab)
    exercises = service.list_records("exercises").to_dict()
    assert exercises == {
        "schema_version": "worker-lab-service-record-list:v1",
        "collection": "exercises",
        "count": 1,
        "items": [{
            "collection": "exercises",
            "identity": "record-model@v1",
            "schema_version": "worker-lab-exercise:v2",
            "record_digest": ExerciseRecord.from_mapping(exercise_mapping()).digest(),
            "state": None,
        }],
    }
    shown = service.show_record("attempts", "ATTEMPT-000001").to_dict()
    assert shown["schema_version"] == "worker-lab-service-record-detail:v1"
    assert shown["summary"]["identity"] == "ATTEMPT-000001"
    assert shown["summary"]["state"] == "DRAFT"
    assert shown["record"] == attempt_mapping()
    for collection in COLLECTIONS:
        assert service.list_records(collection).to_dict()["count"] == 1
    assert snapshot(lab) == before


def test_list_order_is_identity_based_not_storage_path_based(tmp_path: Path) -> None:
    lab = populated_lab(tmp_path)
    second_mapping = curriculum_mapping()
    second_mapping["curriculum_id"] = "another-ledger"
    AtomicRecordStore(lab / "curricula").write(
        "curricula/zzz.json", CurriculumRecord.from_mapping(second_mapping)
    )
    listed = WorkerLabApplicationService(lab).list_records("curricula").to_dict()
    assert [item["identity"] for item in listed["items"]] == [
        "another-ledger",
        "record-ledger",
    ]


def test_queries_fail_closed_for_corruption_duplicates_and_unsafe_input(tmp_path: Path) -> None:
    lab = populated_lab(tmp_path)
    corrupt = lab / "state" / "attempts" / "ATTEMPT-CORRUPT.json"
    corrupt.write_text('{"schema_version":"worker-lab-attempt:v1"}', encoding="utf-8")
    service = WorkerLabApplicationService(lab)
    before = snapshot(lab)
    with pytest.raises(LabValidationError) as error:
        service.list_records("attempts")
    assert error.value.code == "STORAGE_RECORD_INVALID"
    assert snapshot(lab) == before
    corrupt.unlink()

    duplicate = CurriculumRecord.from_mapping(curriculum_mapping())
    AtomicRecordStore(lab / "curricula").write("curricula/duplicate.json", duplicate)
    before = snapshot(lab)
    with pytest.raises(LabValidationError) as error:
        service.list_records("curricula")
    assert error.value.code == "SERVICE_RECORD_DUPLICATE"
    assert snapshot(lab) == before
    for collection, identity, code in (
        ("unknown", "record", "SERVICE_COLLECTION_INVALID"),
        ("attempts", "../ATTEMPT-000001", "SERVICE_IDENTITY_INVALID"),
        ("attempts", "ATTEMPT-MISSING", "SERVICE_RECORD_MISSING"),
    ):
        with pytest.raises(LabValidationError) as error:
            service.show_record(collection, identity)
        assert error.value.code == code
    assert snapshot(lab) == before


def test_queries_reject_invalid_data_roots_without_mutation(tmp_path: Path) -> None:
    with pytest.raises(LabValidationError) as error:
        WorkerLabApplicationService(Path("relative"))
    assert error.value.code == "SERVICE_DATA_ROOT_INVALID"

    invalid = tmp_path / "not-a-directory"
    invalid.write_text("unchanged", encoding="utf-8")
    service = WorkerLabApplicationService(invalid)
    for query in (
        service.health,
        lambda: service.list_records("attempts"),
        lambda: service.show_record("attempts", "ATTEMPT-000001"),
    ):
        with pytest.raises(LabValidationError) as error:
            query()
        assert error.value.code == "SERVICE_DATA_ROOT_INVALID"
    assert invalid.read_text(encoding="utf-8") == "unchanged"


def test_cli_exposes_service_health_list_and_show(tmp_path: Path, capsys) -> None:
    lab = populated_lab(tmp_path)
    assert main(["--root", str(lab), "health"]) == 0
    assert json.loads(capsys.readouterr().out)["schema_version"] == "worker-lab-service-health:v1"
    assert main(["--root", str(lab), "installation-status"]) == 0
    assert json.loads(capsys.readouterr().out)["schema_version"] == "worker-lab-service-installation-status:v1"
    assert main(["--root", str(lab), "list-records", "invocations"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["items"][0]["identity"] == "INVOCATION-001"
    assert main(["--root", str(lab), "show-record", "results", "INVOCATION-001"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["summary"]["state"] == "pass"
    assert shown["record"]["invocation_id"] == "INVOCATION-001"


def test_attempt_timeline_and_candidate_review_are_complete_non_mutating_queries(
    tmp_path: Path, capsys
) -> None:
    lab, attempt_id = candidate_fixture(tmp_path, retain_evidence=True)
    service = WorkerLabApplicationService(lab)
    before = snapshot(lab)
    timeline = service.show_attempt_timeline(attempt_id).to_dict()
    assert timeline["schema_version"] == "worker-lab-service-attempt-timeline:v1"
    assert timeline["attempt"]["summary"]["identity"] == attempt_id
    assert [item["summary"]["identity"] for item in timeline["invocations"]] == ["INVOCATION-001"]
    assert [item["summary"]["identity"] for item in timeline["results"]] == ["INVOCATION-001"]
    assert [item["summary"]["identity"] for item in timeline["custody"]] == ["INVOCATION-001"]
    review = service.review_candidate(attempt_id).to_dict()
    assert review["schema_version"] == "worker-lab-service-candidate-review:v1"
    assert review["candidate_digest"] == review["result"]["summary"]["record_digest"]
    assert review["changed_paths"] == []
    assert review["validation_stages"][0]["outcome"] == "pass"
    assert len(review["evidence"]) == 1
    assert snapshot(lab) == before

    assert main(["--root", str(lab), "show-attempt-timeline", attempt_id]) == 0
    assert json.loads(capsys.readouterr().out)["attempt"]["summary"]["identity"] == attempt_id
    assert main(["--root", str(lab), "review-candidate", attempt_id]) == 0
    assert json.loads(capsys.readouterr().out)["candidate_digest"] == review["candidate_digest"]


def test_candidate_review_fails_closed_for_missing_or_conflicting_evidence(tmp_path: Path) -> None:
    lab, attempt_id = candidate_fixture(tmp_path, retain_evidence=True)
    evidence_path = next((lab / "state" / "evidence-content").glob("*.json"))
    evidence_path.unlink()
    with pytest.raises(LabValidationError) as error:
        WorkerLabApplicationService(lab).review_candidate(attempt_id)
    assert error.value.code == "EVIDENCE_PATH_INVALID"

    lab, attempt_id = candidate_fixture(tmp_path)
    result_path = lab / "state" / "results" / "INVOCATION-001.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["attempt_id"] = "ATTEMPT-CONFLICT"
    result_path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(LabValidationError) as error:
        WorkerLabApplicationService(lab).review_candidate(attempt_id)
    assert error.value.code == "SERVICE_CANDIDATE_IDENTITY_INVALID"


def test_attempt_workspace_service_returns_stable_operation_dtos(tmp_path: Path) -> None:
    lab, target = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    times = iter((
        "2026-08-31T12:00:00Z",
        "2026-08-31T12:00:01Z",
        "2026-08-31T12:00:02Z",
    ))
    service = WorkerLabApplicationService(lab, clock=lambda: next(times))

    created = service.create_attempt("record-model", 1, target).to_dict()
    assert created["schema_version"] == "worker-lab-service-operation-result:v2"
    assert created["operation"] == "create-attempt"
    assert created["resource_type"] == "attempt"
    assert created["identity"] == created["record"]["attempt_id"]
    assert created["record"]["state"] == "DRAFT"

    attempt_id = created["identity"]
    prepared = service.prepare_workspace(attempt_id, target, workspace_root).to_dict()
    assert prepared["operation"] == "prepare-workspace"
    assert prepared["resource_type"] == "workspace-receipt"
    assert prepared["record"]["state"] == "PREPARED"
    assert service.verify_workspace(attempt_id, workspace_root).to_dict()["record"] == prepared["record"]

    with pytest.raises(LabValidationError) as error:
        service.transition_attempt(
            attempt_id,
            "ABORTED",
            cleanup_outcome="must dispose receipt first",
        )
    assert error.value.code == "ATTEMPT_WORKSPACE_DISPOSAL_REQUIRED"

    discarded = service.discard_workspace(
        attempt_id,
        workspace_root,
        "operator disposal",
    ).to_dict()
    assert discarded["operation"] == "discard-workspace"
    assert discarded["record"]["state"] == "ABORTED"
    assert not (workspace_root / attempt_id).exists()
    assert not (lab / "state" / "invocations").exists()


def test_mutating_service_fails_before_state_write_on_invalid_authority(tmp_path: Path) -> None:
    lab, target = write_authority_fixture(tmp_path, mismatched_context=True)
    service = WorkerLabApplicationService(
        lab,
        clock=lambda: "2026-08-31T12:00:00Z",
    )
    with pytest.raises(LabValidationError) as error:
        service.create_attempt("record-model", 1, target)
    assert error.value.code == "ATTEMPT_CONTEXT_MISMATCH"
    assert not (lab / "state").exists()


def test_mutating_service_rejects_unsafe_command_input_before_writing(tmp_path: Path) -> None:
    lab, target = write_authority_fixture(tmp_path)
    service = WorkerLabApplicationService(
        lab,
        clock=lambda: "2026-08-31T12:00:00Z",
    )
    for exercise_id, version, repository in (
        ("../record-model", 1, target),
        ("record-model", True, target),
        ("record-model", 1, str(target)),
    ):
        with pytest.raises(LabValidationError) as error:
            service.create_attempt(exercise_id, version, repository)  # type: ignore[arg-type]
        assert error.value.code == "SERVICE_COMMAND_INVALID"
    assert not (lab / "state").exists()


def test_invocation_prepare_authorize_and_reject_are_durable_without_dispatch(
    tmp_path: Path,
) -> None:
    lab, target = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    times = iter((
        "2026-09-01T12:00:00Z",
        "2026-09-01T12:00:01Z",
        "2026-09-01T12:00:02Z",
        "2026-09-01T12:00:03Z",
        "2026-09-01T12:00:04Z",
    ))
    service = WorkerLabApplicationService(lab, clock=lambda: next(times))
    first = service.create_attempt("record-model", 1, target).to_dict()["identity"]
    service.prepare_workspace(first, target, workspace_root)
    prompt = "Implement the sealed record-model exercise without exceeding its writable paths."
    prepared = service.prepare_invocation(first, workspace_root, prompt).to_dict()
    invocation_id = prepared["identity"]
    identity_digest = prepared["immutable_identity_digest"]
    assert prepared["operation"] == "prepare-invocation"
    assert prepared["record"]["state"] == "PREPARED"
    assert prepared["record"]["operation"] == "workspace-write-code-task"
    assert prepared["record"]["writable_paths"]
    prompt_digest = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    assert prepared["record"]["prompt_digest"] == prompt_digest
    assert (
        lab / "state" / "prompts" / f"{prompt_digest.removeprefix('sha256:')}.txt"
    ).read_text(encoding="utf-8") == prompt
    with pytest.raises(LabValidationError) as error:
        service.prepare_invocation(first, workspace_root, "A competing prompt.\n")
    assert error.value.code == "INTEGRATION_INVOCATION_EXISTS"
    assert len(tuple((lab / "state" / "prompts").glob("*.txt"))) == 1

    with pytest.raises(LabValidationError) as error:
        service.authorize_invocation(invocation_id, "sha256:" + "f" * 64, "trusted-controller")
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"
    with pytest.raises(LabValidationError) as error:
        service.authorize_invocation(invocation_id, identity_digest, "bad controller")
    assert error.value.code == "OPERATOR_CONTROLLER_INVALID"
    assert service.show_record("invocations", invocation_id).to_dict()["record"]["state"] == "PREPARED"

    authorized = service.authorize_invocation(
        invocation_id,
        identity_digest,
        "trusted-controller",
    ).to_dict()
    assert authorized["record"]["state"] == "AUTHORIZED"
    assert authorized["record"]["authorized_by"] == "trusted-controller"
    assert authorized["immutable_identity_digest"] == identity_digest
    with pytest.raises(LabValidationError) as error:
        service.reject_invocation(invocation_id, identity_digest)
    assert error.value.code == "INTEGRATION_TRANSITION_INVALID"

    with pytest.raises(LabValidationError) as error:
        service.cancel_invocation(
            invocation_id,
            identity_digest,
            "different-controller",
        )
    assert error.value.code == "OPERATOR_CONTROLLER_MISMATCH"
    with pytest.raises(LabValidationError) as error:
        service.cancel_invocation(
            invocation_id,
            "sha256:" + "e" * 64,
            "trusted-controller",
        )
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"
    cancelled = service.cancel_invocation(
        invocation_id,
        identity_digest,
        "trusted-controller",
    ).to_dict()
    assert cancelled["operation"] == "cancel-invocation"
    assert cancelled["record"]["state"] == "ABORTED"
    assert cancelled["record"]["authorized_by"] == "trusted-controller"
    with pytest.raises(LabValidationError) as error:
        service.cancel_invocation(invocation_id, identity_digest, "trusted-controller")
    assert error.value.code == "INTEGRATION_TRANSITION_INVALID"

    second = service.create_attempt("record-model", 1, target).to_dict()["identity"]
    service.prepare_workspace(second, target, workspace_root)
    second_prepared = service.prepare_invocation(second, workspace_root, prompt).to_dict()
    rejected = service.reject_invocation(
        second_prepared["identity"],
        second_prepared["immutable_identity_digest"],
    ).to_dict()
    assert rejected["record"]["state"] == "REJECTED"
    assert not (lab / "state" / "results").exists()
    assert not (lab / "state" / "process-custody").exists()


def test_cli_exposes_prepare_and_reject_invocation_without_dispatch(tmp_path: Path, capsys) -> None:
    lab, target = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    service = WorkerLabApplicationService(
        lab,
        clock=lambda: "2026-09-01T12:00:00Z",
    )
    attempt_id = service.create_attempt("record-model", 1, target).to_dict()["identity"]
    service.prepare_workspace(attempt_id, target, workspace_root)
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Prepare the bounded code-task invocation only.", encoding="utf-8")

    assert main([
        "--root", str(lab), "prepare-invocation", attempt_id,
        "--workspace-root", str(workspace_root), "--prompt-file", str(prompt_file),
    ]) == 0
    prepared = json.loads(capsys.readouterr().out)
    assert prepared["schema_version"] == "worker-lab-service-operation-result:v2"
    assert prepared["record"]["state"] == "PREPARED"
    assert main([
        "--root", str(lab), "reject-invocation", prepared["identity"],
        "--expected-identity-digest", prepared["immutable_identity_digest"],
    ]) == 0
    assert json.loads(capsys.readouterr().out)["record"]["state"] == "REJECTED"


def test_cli_exposes_controller_bound_invocation_cancellation(tmp_path: Path, capsys) -> None:
    lab, target = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    service = WorkerLabApplicationService(
        lab,
        clock=lambda: "2026-09-01T12:00:00Z",
    )
    attempt_id = service.create_attempt("record-model", 1, target).to_dict()["identity"]
    service.prepare_workspace(attempt_id, target, workspace_root)
    prepared = service.prepare_invocation(
        attempt_id,
        workspace_root,
        "Prepare the bounded invocation for cancellation.",
    ).to_dict()
    service.authorize_invocation(
        prepared["identity"],
        prepared["immutable_identity_digest"],
        "trusted-controller",
    )

    assert main([
        "--root", str(lab), "cancel-invocation", prepared["identity"],
        "--expected-identity-digest", prepared["immutable_identity_digest"],
        "--controller", "trusted-controller",
    ]) == 0
    cancelled = json.loads(capsys.readouterr().out)
    assert cancelled["operation"] == "cancel-invocation"
    assert cancelled["record"]["state"] == "ABORTED"
    assert not (lab / "state" / "results").exists()
    assert not (lab / "state" / "process-custody").exists()


def test_recovery_requires_exact_absence_and_unchanged_workspace_and_is_idempotent(
    tmp_path: Path,
) -> None:
    lab, workspace_root, invocation_id, identity_digest = recovery_fixture(
        tmp_path,
        custody_state=CustodyState.TERMINATED,
    )
    service = WorkerLabApplicationService(
        lab,
        clock=lambda: "2026-09-01T12:00:03Z",
        process_probe=lambda _: None,
    )
    recovered = service.recover_invocation(
        invocation_id,
        identity_digest,
        "trusted-controller",
        workspace_root,
    ).to_dict()
    assert recovered["schema_version"] == "worker-lab-service-recovery-result:v1"
    assert recovered["operation"] == "recover-invocation"
    assert recovered["workspace_outcome"] == "unchanged-retained"
    assert recovered["workspace"]["status"] == ""
    assert recovered["custody"]["record"]["state"] == "ABSENCE_VERIFIED"
    assert recovered["invocation"]["record"]["state"] == "ABORTED"
    assert recovered["attempt"]["record"]["state"] == "ABORTED"
    assert (workspace_root / recovered["attempt"]["record"]["attempt_id"]).is_dir()
    assert not (lab / "state" / "results").exists()
    assert service.recover_invocation(
        invocation_id,
        identity_digest,
        "trusted-controller",
        workspace_root,
    ).to_dict() == recovered


def test_recovery_rejects_wrong_authority_active_controller_and_uncertain_custody(
    tmp_path: Path,
) -> None:
    lab, workspace_root, invocation_id, identity_digest = recovery_fixture(
        tmp_path,
        custody_state=CustodyState.TERMINATED,
    )
    service = WorkerLabApplicationService(
        lab,
        clock=lambda: "2026-09-01T12:00:03Z",
        process_probe=lambda _: 123456789,
    )
    for digest, controller, code in (
        ("sha256:" + "d" * 64, "trusted-controller", "INTEGRATION_IDENTITY_INVALID"),
        (identity_digest, "different-controller", "OPERATOR_CONTROLLER_MISMATCH"),
        (identity_digest, "trusted-controller", "OPERATOR_RECOVERY_ACTIVE"),
    ):
        with pytest.raises(LabValidationError) as error:
            service.recover_invocation(
                invocation_id,
                digest,
                controller,
                workspace_root,
            )
        assert error.value.code == code
    assert InvocationStore(lab / "state").read(invocation_id).state is InvocationState.UNCERTAIN
    assert ProcessCustodyStore(lab / "state").read(invocation_id).state is CustodyState.TERMINATED

    other = tmp_path / "uncertain"
    other.mkdir()
    uncertain_lab, uncertain_root, uncertain_id, uncertain_digest = recovery_fixture(
        other,
        custody_state=CustodyState.UNCERTAIN,
    )
    with pytest.raises(LabValidationError) as error:
        WorkerLabApplicationService(uncertain_lab).recover_invocation(
            uncertain_id,
            uncertain_digest,
            "trusted-controller",
            uncertain_root,
        )
    assert error.value.code == "INTEGRATION_OUTCOME_UNCERTAIN"


def test_recovery_rejects_changed_workspace_without_state_transition(tmp_path: Path) -> None:
    lab, workspace_root, invocation_id, identity_digest = recovery_fixture(tmp_path)
    invocation = InvocationStore(lab / "state").read(invocation_id)
    workspace = workspace_root / invocation.attempt_id
    (workspace / "README.md").write_text("changed during uncertain execution\n", encoding="utf-8")
    with pytest.raises(LabValidationError) as error:
        WorkerLabApplicationService(lab).recover_invocation(
            invocation_id,
            identity_digest,
            "trusted-controller",
            workspace_root,
        )
    assert error.value.code == "OPERATOR_RECOVERY_INVALID"
    assert InvocationStore(lab / "state").read(invocation_id).state is InvocationState.UNCERTAIN
    assert AttemptStore(lab / "state").read(invocation.attempt_id).state.value == "RUNNING"


def test_recovery_finishes_a_partially_persisted_invocation_abort(tmp_path: Path) -> None:
    lab, workspace_root, invocation_id, identity_digest = recovery_fixture(tmp_path)
    invocations = InvocationStore(lab / "state")
    uncertain = invocations.read(invocation_id)
    aborted = transition_invocation(uncertain, InvocationState.ABORTED)
    invocations.save_transition(aborted, expected_digest=uncertain.digest())

    recovered = WorkerLabApplicationService(
        lab,
        clock=lambda: "2026-09-01T12:00:03Z",
    ).recover_invocation(
        invocation_id,
        identity_digest,
        "trusted-controller",
        workspace_root,
    ).to_dict()
    assert recovered["invocation"]["record"]["state"] == "ABORTED"
    assert recovered["attempt"]["record"]["state"] == "ABORTED"


def test_cli_recovers_dispatching_invocation_from_verified_absence(
    tmp_path: Path,
    capsys,
) -> None:
    lab, workspace_root, invocation_id, identity_digest = recovery_fixture(
        tmp_path,
        invocation_state=InvocationState.DISPATCHING,
    )
    assert main([
        "--root", str(lab), "recover-invocation", invocation_id,
        "--expected-identity-digest", identity_digest,
        "--controller", "trusted-controller",
        "--workspace-root", str(workspace_root),
    ]) == 0
    recovered = json.loads(capsys.readouterr().out)
    assert recovered["invocation"]["record"]["state"] == "ABORTED"
    assert recovered["attempt"]["record"]["state"] == "ABORTED"


def test_backup_verify_and_restore_are_versioned_service_operations(tmp_path: Path) -> None:
    lab = populated_lab(tmp_path)
    service = WorkerLabApplicationService(lab)
    destination = tmp_path / "backup"
    created = service.create_backup(destination).to_dict()
    assert created["schema_version"] == "worker-lab-service-backup-result:v1"
    assert created["operation"] == "create-backup"
    assert created["file_count"] == len(created["manifest"]["files"])
    assert created["manifest_digest"].startswith("sha256:")
    assert verify_backup(destination).to_dict() == created["manifest"]

    verified = service.verify_backup(destination).to_dict()
    assert verified["operation"] == "verify-backup"
    assert verified["manifest_digest"] == created["manifest_digest"]

    restored = tmp_path / "restored"
    result = service.restore_backup(destination, restored).to_dict()
    assert result["operation"] == "restore-backup"
    assert result["manifest_digest"] == created["manifest_digest"]
    assert snapshot(restored) == snapshot(lab)


def test_backup_service_rejects_non_path_and_relative_arguments(tmp_path: Path) -> None:
    lab = populated_lab(tmp_path)
    service = WorkerLabApplicationService(lab)
    for operation in (
        lambda: service.create_backup(Path("relative-backup")),
        lambda: service.verify_backup("not-a-path"),  # type: ignore[arg-type]
        lambda: service.restore_backup(tmp_path / "missing", Path("relative-restore")),
    ):
        with pytest.raises(LabValidationError) as error:
            operation()
        assert error.value.code == "SERVICE_COMMAND_INVALID"
