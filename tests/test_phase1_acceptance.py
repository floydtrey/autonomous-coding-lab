from copy import deepcopy

import pytest

from worker_lab.backup import BACKUP_SCHEMA, DURABLE_ROOTS, BackupManifest
from worker_lab.canonical import canonical_digest
from worker_lab.errors import LabValidationError
from worker_lab.models import (
    AttemptRecord,
    CurriculumRecord,
    EvidenceRecord,
    ExerciseRecord,
    FailureRecord,
)
from worker_lab.policy import ContextManifest, PolicyRecord, RoleRecord
from worker_lab.test_catalog import TestCatalog
from tests.test_models import (
    attempt_mapping,
    curriculum_mapping,
    evidence_mapping,
    exercise_mapping,
    failure_mapping,
)
from tests.test_policy import context_mapping, policy_mapping, role_mapping
from tests.test_test_catalog import catalog


def backup_mapping() -> dict:
    return {
        "schema_version": BACKUP_SCHEMA,
        "durable_roots": list(DURABLE_ROOTS),
        "files": [
            {"path": "curricula/catalog.json", "digest": "sha256:" + "a" * 64},
        ],
    }


RECORD_CASES = (
    ("curriculum", CurriculumRecord.from_mapping, curriculum_mapping),
    ("exercise", ExerciseRecord.from_mapping, exercise_mapping),
    ("attempt", AttemptRecord.from_mapping, attempt_mapping),
    ("evidence", EvidenceRecord.from_mapping, evidence_mapping),
    ("failure", FailureRecord.from_mapping, failure_mapping),
    ("policy", PolicyRecord.from_mapping, policy_mapping),
    ("role", RoleRecord.from_mapping, role_mapping),
    ("context", ContextManifest.from_mapping, context_mapping),
    ("test-catalog", TestCatalog.from_mapping, lambda: catalog().to_dict()),
    ("backup-manifest", BackupManifest.from_mapping, backup_mapping),
)


@pytest.mark.parametrize(("name", "loader", "mapping"), RECORD_CASES, ids=lambda value: value if isinstance(value, str) else None)
def test_protected_records_accept_valid_deterministic_input(name, loader, mapping) -> None:
    value = mapping()
    before = deepcopy(value)
    first = loader(value)
    second = loader(deepcopy(value))
    assert value == before, name
    assert first == second
    assert canonical_digest(first.to_dict()) == canonical_digest(second.to_dict())


@pytest.mark.parametrize(("name", "loader", "mapping"), RECORD_CASES, ids=lambda value: value if isinstance(value, str) else None)
def test_protected_records_reject_missing_fields_without_mutating_input(name, loader, mapping) -> None:
    value = mapping()
    removable = next(key for key in value if key != "schema_version")
    value.pop(removable)
    before = deepcopy(value)
    with pytest.raises(LabValidationError):
        loader(value)
    assert value == before, name


@pytest.mark.parametrize(("name", "loader", "mapping"), RECORD_CASES, ids=lambda value: value if isinstance(value, str) else None)
def test_protected_records_reject_unknown_fields_without_mutating_input(name, loader, mapping) -> None:
    value = mapping()
    value["unknown_field"] = True
    before = deepcopy(value)
    with pytest.raises(LabValidationError):
        loader(value)
    assert value == before, name


@pytest.mark.parametrize(("name", "loader", "mapping"), RECORD_CASES, ids=lambda value: value if isinstance(value, str) else None)
def test_protected_records_reject_malformed_top_level_values(name, loader, mapping) -> None:
    value: list[object] = []
    before = deepcopy(value)
    with pytest.raises(LabValidationError):
        loader(value)
    assert value == before, name


@pytest.mark.parametrize(("name", "loader", "mapping"), RECORD_CASES, ids=lambda value: value if isinstance(value, str) else None)
def test_protected_records_reject_incompatible_schema_without_mutating_input(name, loader, mapping) -> None:
    value = mapping()
    value["schema_version"] = "incompatible:v999"
    before = deepcopy(value)
    with pytest.raises(LabValidationError):
        loader(value)
    assert value == before, name
