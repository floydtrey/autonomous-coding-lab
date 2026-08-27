from pathlib import Path

import pytest

from worker_lab.backup import create_backup, restore_backup, verify_backup
from worker_lab.errors import LabValidationError


def source_tree(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    (source / "nested").mkdir(parents=True)
    (source / "a.json").write_text('{"a":1}\n', encoding="utf-8")
    (source / "nested" / "b.txt").write_text("stable\n", encoding="utf-8")
    return source


def test_backup_verify_restore_round_trip(tmp_path: Path) -> None:
    source = source_tree(tmp_path)
    backup = tmp_path / "backup"
    created = create_backup(source, backup)
    assert verify_backup(backup) == created
    restored = tmp_path / "restored"
    assert restore_backup(backup, restored) == created
    assert (restored / "a.json").read_bytes() == (source / "a.json").read_bytes()
    assert (restored / "nested" / "b.txt").read_bytes() == (source / "nested" / "b.txt").read_bytes()


@pytest.mark.parametrize("damage", ["missing", "changed", "extra"])
def test_verification_detects_content_damage(tmp_path: Path, damage: str) -> None:
    backup = tmp_path / "backup"
    create_backup(source_tree(tmp_path), backup)
    if damage == "missing":
        (backup / "content" / "a.json").unlink()
    elif damage == "changed":
        (backup / "content" / "a.json").write_text("changed", encoding="utf-8")
    else:
        (backup / "content" / "extra.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(LabValidationError) as raised:
        verify_backup(backup)
    assert raised.value.code == "BACKUP_CONTENT_INVALID"


def test_backup_will_not_overwrite_destination(tmp_path: Path) -> None:
    destination = tmp_path / "backup"
    destination.mkdir()
    with pytest.raises(LabValidationError) as raised:
        create_backup(source_tree(tmp_path), destination)
    assert raised.value.code == "BACKUP_DESTINATION_EXISTS"


def test_backup_destination_cannot_be_inside_source(tmp_path: Path) -> None:
    source = source_tree(tmp_path)
    with pytest.raises(LabValidationError) as raised:
        create_backup(source, source / "backup")
    assert raised.value.code == "BACKUP_DESTINATION_INVALID"


def test_restore_requires_empty_destination(tmp_path: Path) -> None:
    backup = tmp_path / "backup"
    create_backup(source_tree(tmp_path), backup)
    destination = tmp_path / "restored"
    destination.mkdir()
    (destination / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(LabValidationError) as raised:
        restore_backup(backup, destination)
    assert raised.value.code == "RESTORE_DESTINATION_NOT_EMPTY"
    assert (destination / "keep.txt").read_text(encoding="utf-8") == "keep"
