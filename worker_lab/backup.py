from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_json
from .errors import LabValidationError


BACKUP_SCHEMA = "worker-lab-backup:v1"
MANIFEST_NAME = "manifest.json"
CONTENT_DIRECTORY = "content"


@dataclass(frozen=True)
class BackupManifest:
    schema_version: str
    files: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "files": [{"path": path, "digest": digest} for path, digest in self.files],
        }

    @classmethod
    def from_mapping(cls, value: Any) -> "BackupManifest":
        if not isinstance(value, dict) or set(value) != {"schema_version", "files"}:
            raise LabValidationError("BACKUP_MANIFEST_INVALID", "manifest fields are invalid")
        if value["schema_version"] != BACKUP_SCHEMA or not isinstance(value["files"], list):
            raise LabValidationError("BACKUP_MANIFEST_INVALID", "manifest schema is invalid")
        files: list[tuple[str, str]] = []
        for item in value["files"]:
            if not isinstance(item, dict) or set(item) != {"path", "digest"}:
                raise LabValidationError("BACKUP_MANIFEST_INVALID", "file entry is invalid")
            path, digest = item["path"], item["digest"]
            if not isinstance(path, str) or not isinstance(digest, str):
                raise LabValidationError("BACKUP_MANIFEST_INVALID", "file entry types are invalid")
            if not digest.startswith("sha256:") or len(digest) != 71:
                raise LabValidationError("BACKUP_MANIFEST_INVALID", "file digest is invalid")
            files.append((path, digest))
        result = tuple(files)
        if result != tuple(sorted(set(result))):
            raise LabValidationError("BACKUP_MANIFEST_INVALID", "file entries must be sorted and unique")
        return cls(BACKUP_SCHEMA, result)


def create_backup(source: Path, destination: Path) -> BackupManifest:
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise LabValidationError("BACKUP_SOURCE_INVALID", "source must be a directory")
    if destination.exists():
        raise LabValidationError("BACKUP_DESTINATION_EXISTS", "backup destination must not exist")
    resolved_destination = destination.resolve()
    if resolved_destination.is_relative_to(source):
        raise LabValidationError(
            "BACKUP_DESTINATION_INVALID", "backup destination cannot be inside its source"
        )
    entries = _source_entries(source)
    manifest = BackupManifest(BACKUP_SCHEMA, tuple((path, digest) for path, digest, _ in entries))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        content = temporary / CONTENT_DIRECTORY
        content.mkdir()
        for relative, _, origin in entries:
            target = content.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, target)
        (temporary / MANIFEST_NAME).write_text(
            canonical_json(manifest.to_dict()) + "\n", encoding="utf-8", newline="\n"
        )
        os.replace(temporary, destination)
    except OSError as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        raise LabValidationError("BACKUP_CREATE_FAILED", str(exc)) from exc
    verify_backup(destination)
    return manifest


def verify_backup(backup: Path) -> BackupManifest:
    backup = backup.resolve(strict=True)
    try:
        raw = json.loads((backup / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabValidationError("BACKUP_MANIFEST_INVALID", "manifest is missing or corrupt") from exc
    manifest = BackupManifest.from_mapping(raw)
    content = backup / CONTENT_DIRECTORY
    actual = _source_entries(content)
    actual_map = {path: digest for path, digest, _ in actual}
    expected_map = dict(manifest.files)
    missing = sorted(set(expected_map) - set(actual_map))
    extra = sorted(set(actual_map) - set(expected_map))
    changed = sorted(path for path in set(actual_map) & set(expected_map) if actual_map[path] != expected_map[path])
    if missing or extra or changed:
        raise LabValidationError(
            "BACKUP_CONTENT_INVALID", f"missing={missing}, extra={extra}, changed={changed}"
        )
    return manifest


def restore_backup(backup: Path, destination: Path) -> BackupManifest:
    manifest = verify_backup(backup)
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise LabValidationError("RESTORE_DESTINATION_NOT_EMPTY", "restore destination must be empty")
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = backup.resolve() / CONTENT_DIRECTORY
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.restore.", dir=destination.parent))
    try:
        for relative, _ in manifest.files:
            origin = content.joinpath(*relative.split("/"))
            target = staging.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, target)
        restored = {(path, digest) for path, digest, _ in _source_entries(staging)}
        if restored != set(manifest.files):
            raise LabValidationError("RESTORE_VERIFICATION_FAILED", "restored identities differ")
        if destination.exists():
            destination.rmdir()
        os.replace(staging, destination)
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise LabValidationError("RESTORE_FAILED", str(exc)) from exc
    except LabValidationError:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def _source_entries(root: Path) -> list[tuple[str, str, Path]]:
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise LabValidationError("BACKUP_SOURCE_INVALID", "source tree is invalid")
    entries: list[tuple[str, str, Path]] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise LabValidationError("BACKUP_SYMLINK_REJECTED", "backup trees cannot contain symlinks")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            entries.append((relative, digest, path))
    entries.sort(key=lambda item: item[0])
    return entries
