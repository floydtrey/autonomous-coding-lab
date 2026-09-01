import json
from pathlib import Path

import pytest

from tests.test_integration import record, result_mapping
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
from worker_lab.cli import main
from worker_lab.errors import LabValidationError
from worker_lab.integration import ResultRecord
from worker_lab.models import (
    AttemptRecord,
    CurriculumRecord,
    EvidenceRecord,
    ExerciseRecord,
    FailureRecord,
)
from worker_lab.policy import ContextManifest, PolicyRecord, RoleRecord
from worker_lab.storage import AtomicRecordStore


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
