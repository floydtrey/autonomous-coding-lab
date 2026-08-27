import json
from pathlib import Path

import pytest

import worker_lab.backup as backup_module
from worker_lab.backup import DURABLE_ROOTS, create_backup, restore_backup, verify_backup
from worker_lab.errors import LabValidationError


def source_tree(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    (source / "curricula").mkdir(parents=True)
    (source / "state" / "nested").mkdir(parents=True)
    (source / "curricula" / "a.json").write_text('{"a":1}\n', encoding="utf-8")
    (source / "state" / "nested" / "b.txt").write_text("stable\n", encoding="utf-8")
    return source


def test_backup_verify_restore_round_trip(tmp_path: Path) -> None:
    source = source_tree(tmp_path)
    backup = tmp_path / "backup"
    created = create_backup(source, backup)
    assert created.durable_roots == DURABLE_ROOTS
    assert verify_backup(backup) == created
    restored = tmp_path / "restored"
    assert restore_backup(backup, restored) == created
    assert (restored / "curricula" / "a.json").read_bytes() == (
        source / "curricula" / "a.json"
    ).read_bytes()
    assert (restored / "state" / "nested" / "b.txt").read_bytes() == (
        source / "state" / "nested" / "b.txt"
    ).read_bytes()


def test_backup_excludes_everything_outside_explicit_durable_scope(tmp_path: Path) -> None:
    source = source_tree(tmp_path)
    for relative in (
        ".git/config", ".pytest_cache/data", "worker_lab/code.py", "docs/note.md",
        "state/workspaces/attempt/file.py", "state/__pycache__/cache.pyc", "state/pending.tmp",
        "state/attempt-workspaces/attempt/file.py",
    ):
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("excluded", encoding="utf-8")
    backup = tmp_path / "backup"
    manifest = create_backup(source, backup)
    paths = {path for path, _ in manifest.files}
    assert paths == {"curricula/a.json", "state/nested/b.txt"}


def test_git_marker_file_inside_durable_root_is_excluded(tmp_path: Path) -> None:
    source = source_tree(tmp_path)
    (source / "state" / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    manifest = create_backup(source, tmp_path / "backup")
    assert "state/.git" not in {path for path, _ in manifest.files}


@pytest.mark.parametrize("damage", ["missing", "changed", "extra"])
def test_verification_detects_content_damage(tmp_path: Path, damage: str) -> None:
    backup = tmp_path / "backup"
    create_backup(source_tree(tmp_path), backup)
    target = backup / "content" / "curricula" / "a.json"
    if damage == "missing":
        target.unlink()
    elif damage == "changed":
        target.write_text("changed", encoding="utf-8")
    else:
        (backup / "content" / "extra.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(LabValidationError) as raised:
        verify_backup(backup)
    assert raised.value.code == "BACKUP_CONTENT_INVALID"


def test_manifest_rejects_paths_outside_durable_scope(tmp_path: Path) -> None:
    backup = tmp_path / "backup"
    create_backup(source_tree(tmp_path), backup)
    manifest_path = backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../outside.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(LabValidationError) as raised:
        verify_backup(backup)
    assert raised.value.code == "BACKUP_MANIFEST_INVALID"


def test_manifest_rejects_duplicate_paths_with_different_digests(tmp_path: Path) -> None:
    backup = tmp_path / "backup"
    create_backup(source_tree(tmp_path), backup)
    manifest_path = backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    duplicate = dict(manifest["files"][0])
    duplicate["digest"] = "sha256:" + "f" * 64
    manifest["files"].append(duplicate)
    manifest["files"].sort(key=lambda item: [item["path"], item["digest"]])
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(LabValidationError) as raised:
        verify_backup(backup)
    assert raised.value.code == "BACKUP_MANIFEST_INVALID"


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


def test_failed_backup_copy_leaves_no_published_or_staged_backup(
    tmp_path: Path, monkeypatch
) -> None:
    destination = tmp_path / "backup"

    def fail_copy(*_args, **_kwargs):
        raise OSError("injected copy failure")

    monkeypatch.setattr(backup_module.shutil, "copyfile", fail_copy)
    with pytest.raises(LabValidationError) as raised:
        create_backup(source_tree(tmp_path), destination)
    assert raised.value.code == "BACKUP_CREATE_FAILED"
    assert not destination.exists()
    assert not tuple(tmp_path.glob(".backup.*"))


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


def test_failed_restore_publish_preserves_empty_destination_and_cleans_staging(
    tmp_path: Path, monkeypatch
) -> None:
    backup = tmp_path / "backup"
    create_backup(source_tree(tmp_path), backup)
    destination = tmp_path / "restored"
    destination.mkdir()

    def fail_replace(*_args, **_kwargs):
        raise OSError("injected publish failure")

    monkeypatch.setattr(backup_module.os, "replace", fail_replace)
    with pytest.raises(LabValidationError) as raised:
        restore_backup(backup, destination)
    assert raised.value.code == "RESTORE_FAILED"
    assert destination.is_dir()
    assert not any(destination.iterdir())
    assert not tuple(tmp_path.glob(".restored.restore.*"))
