from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .canonical import canonical_json
from .errors import LabValidationError


BACKUP_SCHEMA = "worker-lab-backup:v2"
MANIFEST_NAME = "manifest.json"
CONTENT_DIRECTORY = "content"
DURABLE_ROOTS = ("curricula", "state")
EXCLUDED_DIRECTORIES = frozenset({
    ".git", ".pytest_cache", "__pycache__", ".workspaces", "attempt-workspaces",
    "workspaces", "tmp", "temp",
})
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class BackupManifest:
    schema_version: str
    durable_roots: tuple[str, ...]
    files: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "durable_roots": list(self.durable_roots),
            "files": [{"path": path, "digest": digest} for path, digest in self.files],
        }

    @classmethod
    def from_mapping(cls, value: Any) -> "BackupManifest":
        if not isinstance(value, dict) or set(value) != {
            "schema_version", "durable_roots", "files",
        }:
            raise LabValidationError("BACKUP_MANIFEST_INVALID", "manifest fields are invalid")
        if (
            value["schema_version"] != BACKUP_SCHEMA
            or value["durable_roots"] != list(DURABLE_ROOTS)
            or not isinstance(value["files"], list)
        ):
            raise LabValidationError("BACKUP_MANIFEST_INVALID", "manifest schema or scope is invalid")
        files: list[tuple[str, str]] = []
        for item in value["files"]:
            if not isinstance(item, dict) or set(item) != {"path", "digest"}:
                raise LabValidationError("BACKUP_MANIFEST_INVALID", "file entry is invalid")
            path, digest = item["path"], item["digest"]
            if not isinstance(path, str) or not isinstance(digest, str):
                raise LabValidationError("BACKUP_MANIFEST_INVALID", "file entry types are invalid")
            if not _is_durable_path(path) or DIGEST_RE.fullmatch(digest) is None:
                raise LabValidationError("BACKUP_MANIFEST_INVALID", "file identity is invalid")
            files.append((path, digest))
        result = tuple(files)
        if (
            result != tuple(sorted(set(result)))
            or len(result) != len({path for path, _ in result})
        ):
            raise LabValidationError("BACKUP_MANIFEST_INVALID", "file entries must be sorted and unique")
        return cls(BACKUP_SCHEMA, DURABLE_ROOTS, result)


def create_backup(source: Path, destination: Path) -> BackupManifest:
    if source.is_symlink():
        raise LabValidationError("BACKUP_SOURCE_INVALID", "source cannot be a symlink")
    try:
        source = source.resolve(strict=True)
    except OSError as exc:
        raise LabValidationError("BACKUP_SOURCE_INVALID", "source is missing") from exc
    if not source.is_dir():
        raise LabValidationError("BACKUP_SOURCE_INVALID", "source must be a directory")
    if destination.exists() or destination.is_symlink():
        raise LabValidationError("BACKUP_DESTINATION_EXISTS", "backup destination must not exist")
    resolved_destination = destination.resolve()
    if resolved_destination.is_relative_to(source):
        raise LabValidationError(
            "BACKUP_DESTINATION_INVALID", "backup destination cannot be inside its source"
        )
    try:
        entries = _durable_entries(source)
    except LabValidationError:
        raise
    except OSError as exc:
        raise LabValidationError("BACKUP_SOURCE_INVALID", "durable content is unreadable") from exc
    manifest = BackupManifest(
        BACKUP_SCHEMA,
        DURABLE_ROOTS,
        tuple((path, digest) for path, digest, _ in entries),
    )
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
        if verify_backup(temporary) != manifest:
            raise LabValidationError("BACKUP_CREATE_FAILED", "staged backup identity differs")
        os.replace(temporary, destination)
    except LabValidationError:
        raise
    except OSError as exc:
        raise LabValidationError("BACKUP_CREATE_FAILED", str(exc)) from exc
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
    return manifest


def verify_backup(backup: Path) -> BackupManifest:
    if backup.is_symlink():
        raise LabValidationError("BACKUP_SOURCE_INVALID", "backup cannot be a symlink")
    try:
        backup = backup.resolve(strict=True)
    except OSError as exc:
        raise LabValidationError("BACKUP_SOURCE_INVALID", "backup is missing") from exc
    if not backup.is_dir():
        raise LabValidationError("BACKUP_SOURCE_INVALID", "backup must be a directory")
    try:
        raw = json.loads((backup / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabValidationError("BACKUP_MANIFEST_INVALID", "manifest is missing or corrupt") from exc
    manifest = BackupManifest.from_mapping(raw)
    try:
        actual = _tree_entries(backup / CONTENT_DIRECTORY)
    except LabValidationError as exc:
        if exc.code != "BACKUP_SOURCE_INVALID":
            raise
        raise LabValidationError("BACKUP_CONTENT_INVALID", "backup content tree is missing") from exc
    except OSError as exc:
        raise LabValidationError("BACKUP_CONTENT_INVALID", "backup content is unreadable") from exc
    actual_map = {path: digest for path, digest, _ in actual}
    expected_map = dict(manifest.files)
    missing = sorted(set(expected_map) - set(actual_map))
    extra = sorted(set(actual_map) - set(expected_map))
    changed = sorted(
        path
        for path in set(actual_map).intersection(expected_map)
        if actual_map[path] != expected_map[path]
    )
    if missing or extra or changed:
        raise LabValidationError(
            "BACKUP_CONTENT_INVALID", f"missing={missing}, extra={extra}, changed={changed}"
        )
    return manifest


def restore_backup(backup: Path, destination: Path) -> BackupManifest:
    manifest = verify_backup(backup)
    if destination.is_symlink():
        raise LabValidationError("RESTORE_DESTINATION_INVALID", "destination cannot be a symlink")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise LabValidationError("RESTORE_DESTINATION_NOT_EMPTY", "restore destination must be empty")
    resolved_backup = backup.resolve(strict=True)
    if destination.resolve().is_relative_to(resolved_backup):
        raise LabValidationError(
            "RESTORE_DESTINATION_INVALID", "restore destination cannot be inside its backup"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination_was_present = destination.exists()
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.restore.", dir=destination.parent))
    published = False
    try:
        content = resolved_backup / CONTENT_DIRECTORY
        for relative, _ in manifest.files:
            origin = content.joinpath(*relative.split("/"))
            target = staging.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, target)
        restored = {(path, digest) for path, digest, _ in _tree_entries(staging)}
        if restored != set(manifest.files):
            raise LabValidationError("RESTORE_VERIFICATION_FAILED", "restored identities differ")
        if verify_backup(resolved_backup) != manifest:
            raise LabValidationError("RESTORE_VERIFICATION_FAILED", "backup changed during restore")
        if destination_was_present:
            destination.rmdir()
        os.replace(staging, destination)
        published = True
    except LabValidationError:
        raise
    except OSError as exc:
        raise LabValidationError("RESTORE_FAILED", str(exc)) from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if destination_was_present and not published and not destination.exists():
            destination.mkdir()
    return manifest


def _durable_entries(source: Path) -> list[tuple[str, str, Path]]:
    entries: list[tuple[str, str, Path]] = []
    for root_name in DURABLE_ROOTS:
        root = source / root_name
        if not root.exists():
            continue
        if _is_link(root) or not root.is_dir():
            raise LabValidationError("BACKUP_SOURCE_INVALID", f"{root_name} is not a real directory")
        entries.extend(_tree_entries(root, prefix=root_name, apply_exclusions=True))
    entries.sort(key=lambda item: item[0])
    return entries


def _tree_entries(
    root: Path, *, prefix: str = "", apply_exclusions: bool = False
) -> list[tuple[str, str, Path]]:
    if not root.exists() or not root.is_dir() or _is_link(root):
        raise LabValidationError("BACKUP_SOURCE_INVALID", "source tree is invalid")
    entries: list[tuple[str, str, Path]] = []
    for current_text, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_text)
        directory_names.sort()
        file_names.sort()
        retained_directories: list[str] = []
        for name in directory_names:
            path = current / name
            if _is_link(path):
                raise LabValidationError(
                    "BACKUP_SYMLINK_REJECTED", "backup trees cannot contain links or junctions"
                )
            if not apply_exclusions or name not in EXCLUDED_DIRECTORIES:
                retained_directories.append(name)
        directory_names[:] = retained_directories
        for name in file_names:
            path = current / name
            if _is_link(path):
                raise LabValidationError(
                    "BACKUP_SYMLINK_REJECTED", "backup trees cannot contain links or junctions"
                )
            relative = path.relative_to(root)
            if apply_exclusions and (
                any(part in EXCLUDED_DIRECTORIES for part in relative.parts)
                or _is_temporary_file(relative)
            ):
                continue
            relative_text = relative.as_posix()
            if prefix:
                relative_text = f"{prefix}/{relative_text}"
            digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            entries.append((relative_text, digest, path))
    entries.sort(key=lambda item: item[0])
    return entries


def _is_durable_path(value: str) -> bool:
    if not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return bool(
        not path.is_absolute()
        and path.parts
        and path.parts[0] in DURABLE_ROOTS
        and ".." not in path.parts
        and ":" not in path.parts[0]
        and path.as_posix() == value
        and not any(part in EXCLUDED_DIRECTORIES for part in path.parts)
        and not _is_temporary_file(path)
    )


def _is_temporary_file(path: PurePosixPath) -> bool:
    return path.name.endswith(".tmp") or path.name.startswith(".tmp-")


def _is_link(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())
