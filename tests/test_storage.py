import os
from dataclasses import replace
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.models import CurriculumRecord
from worker_lab.storage import AtomicRecordStore
from tests.test_models import curriculum_mapping


def record() -> CurriculumRecord:
    return CurriculumRecord.from_mapping(curriculum_mapping())


def test_write_read_and_list_are_deterministic(tmp_path: Path) -> None:
    store = AtomicRecordStore(tmp_path / "state")
    store.write("curricula/record-ledger.json", record())
    assert store.read("curricula/record-ledger.json", CurriculumRecord.from_mapping) == record()
    assert store.list_paths() == ("curricula/record-ledger.json",)


@pytest.mark.parametrize("path", ["../escape.json", "/absolute.json", "C:/escape.json", "a\\b.json"])
def test_rejects_unsafe_paths(tmp_path: Path, path: str) -> None:
    store = AtomicRecordStore(tmp_path / "state")
    with pytest.raises(LabValidationError) as raised:
        store.write(path, record())
    assert raised.value.code == "STORAGE_PATH_INVALID"


def test_corrupt_record_is_reported_without_repair(tmp_path: Path) -> None:
    store = AtomicRecordStore(tmp_path / "state")
    target = tmp_path / "state" / "curriculum.json"
    target.parent.mkdir()
    target.write_text("{broken", encoding="utf-8")
    before = target.read_bytes()
    with pytest.raises(LabValidationError) as raised:
        store.read("curriculum.json", CurriculumRecord.from_mapping)
    assert raised.value.code == "STORAGE_RECORD_CORRUPT"
    assert target.read_bytes() == before


def test_schema_invalid_record_is_structured_and_not_repaired(tmp_path: Path) -> None:
    store = AtomicRecordStore(tmp_path / "state")
    target = tmp_path / "state" / "curriculum.json"
    target.parent.mkdir()
    target.write_text('{"schema_version":"wrong"}', encoding="utf-8")
    before = target.read_bytes()
    with pytest.raises(LabValidationError) as raised:
        store.read("curriculum.json", CurriculumRecord.from_mapping)
    assert raised.value.code == "STORAGE_RECORD_INVALID"
    assert target.read_bytes() == before


def test_read_only_operations_do_not_create_storage_root(tmp_path: Path) -> None:
    root = tmp_path / "missing-state"
    store = AtomicRecordStore(root)
    assert not root.exists()
    assert store.list_paths() == ()
    assert not root.exists()
    with pytest.raises(LabValidationError) as raised:
        store.read("missing.json", CurriculumRecord.from_mapping)
    assert raised.value.code == "STORAGE_RECORD_MISSING"
    assert not root.exists()


def test_rejected_replacement_preserves_prior_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = AtomicRecordStore(tmp_path / "state")
    store.write("curriculum.json", record())
    before = (tmp_path / "state" / "curriculum.json").read_bytes()

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("simulated interruption")

    monkeypatch.setattr(os, "replace", fail_replace)
    changed = replace(record(), title="Changed")
    with pytest.raises(LabValidationError) as raised:
        store.write("curriculum.json", changed)
    assert raised.value.code == "STORAGE_WRITE_FAILED"
    assert (tmp_path / "state" / "curriculum.json").read_bytes() == before
    assert not tuple((tmp_path / "state").glob("*.tmp"))


def test_symlink_escape_is_rejected_when_supported(tmp_path: Path) -> None:
    store = AtomicRecordStore(tmp_path / "state")
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "state" / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(LabValidationError) as raised:
        store.write("linked/record.json", record())
    assert raised.value.code == "STORAGE_PATH_ESCAPE"
