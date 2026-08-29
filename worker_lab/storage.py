from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable, TypeVar

from .canonical import canonical_json
from .errors import LabValidationError


RecordT = TypeVar("RecordT")


class AtomicRecordStore:
    """Contained, one-record-per-file JSON storage with atomic replacement."""

    def __init__(self, root: Path) -> None:
        self.root = root.absolute()
        if self.root.exists():
            self._validate_root()

    def read(self, relative_path: str, loader: Callable[[Any], RecordT]) -> RecordT:
        target = self._target(relative_path)
        try:
            raw = target.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise LabValidationError("STORAGE_RECORD_MISSING", relative_path) from exc
        except OSError as exc:
            raise LabValidationError("STORAGE_READ_FAILED", str(exc)) from exc
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise LabValidationError("STORAGE_RECORD_CORRUPT", relative_path) from exc
        try:
            return loader(value)
        except LabValidationError as exc:
            raise LabValidationError(
                "STORAGE_RECORD_INVALID", f"{relative_path}: {exc.code}: {exc.summary}"
            ) from exc

    def write(self, relative_path: str, record: Any) -> None:
        self._ensure_root_for_write()
        target = self._target(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._assert_contained_existing_parents(target)
        if target.exists() and self._is_substituted(target):
            raise LabValidationError("STORAGE_PATH_ESCAPE", "record target cannot be a symlink")
        payload = canonical_json(record.to_dict()).encode("utf-8") + b"\n"
        temp_path: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
            temp_path = Path(name)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, target)
            temp_path = None
            self._fsync_directory(target.parent)
        except OSError as exc:
            raise LabValidationError("STORAGE_WRITE_FAILED", str(exc)) from exc
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass

    def read_bytes(self, relative_path: str) -> bytes:
        target = self._target(relative_path)
        if target.exists() and self._is_substituted(target):
            raise LabValidationError("STORAGE_PATH_ESCAPE", "record target cannot be a symlink")
        try:
            return target.read_bytes()
        except FileNotFoundError as exc:
            raise LabValidationError("STORAGE_RECORD_MISSING", relative_path) from exc
        except OSError as exc:
            raise LabValidationError("STORAGE_READ_FAILED", str(exc)) from exc

    def write_bytes(self, relative_path: str, payload: bytes, *, overwrite_if_identical: bool = False) -> None:
        """Atomically write bytes with the same containment checks as JSON records."""
        self._ensure_root_for_write()
        target = self._target(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._assert_contained_existing_parents(target)
        if target.exists():
            if self._is_substituted(target):
                raise LabValidationError("STORAGE_PATH_ESCAPE", "record target cannot be a symlink")
            if target.read_bytes() == payload:
                return
            if not overwrite_if_identical:
                raise LabValidationError("STORAGE_RECORD_INVALID", "existing content-addressed content differs")
        temp_path: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
            temp_path = Path(name)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, target)
            temp_path = None
            self._fsync_directory(target.parent)
        except OSError as exc:
            raise LabValidationError("STORAGE_WRITE_FAILED", str(exc)) from exc
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass

    def list_paths(self, relative_directory: str = ".") -> tuple[str, ...]:
        if not self.root.exists():
            return ()
        directory = self._target(relative_directory, allow_dot=True)
        if not directory.exists():
            return ()
        if not directory.is_dir():
            raise LabValidationError("STORAGE_PATH_INVALID", "list target must be a directory")
        paths: list[str] = []
        for item in directory.rglob("*.json"):
            if self._is_substituted(item):
                raise LabValidationError("STORAGE_PATH_ESCAPE", "symlink found in record tree")
            resolved = item.resolve()
            self._assert_contained(resolved)
            paths.append(resolved.relative_to(self.root).as_posix())
        return tuple(sorted(paths))

    def _target(self, relative_path: str, *, allow_dot: bool = False) -> Path:
        if not isinstance(relative_path, str) or not relative_path:
            raise LabValidationError("STORAGE_PATH_INVALID", "path must be non-empty text")
        if "\\" in relative_path:
            raise LabValidationError("STORAGE_PATH_INVALID", "path must use forward slashes")
        normalized = relative_path
        candidate = PurePosixPath(normalized)
        first_part = candidate.parts[0] if candidate.parts else ""
        if (
            candidate.is_absolute()
            or normalized.startswith("/")
            or ".." in candidate.parts
            or ":" in first_part
            or (candidate.as_posix() == "." and not allow_dot)
            or candidate.as_posix() != normalized
        ):
            raise LabValidationError("STORAGE_PATH_INVALID", "path must be normalized and relative")
        if candidate.as_posix() == ".":
            return self.root
        target = self.root.joinpath(*candidate.parts)
        if self.root.exists():
            self._assert_contained_existing_parents(target)
        return target

    def _ensure_root_for_write(self) -> None:
        if not self.root.exists():
            try:
                self.root.mkdir(parents=True)
            except OSError as exc:
                raise LabValidationError("STORAGE_ROOT_INVALID", str(exc)) from exc
        self._validate_root()

    def _validate_root(self) -> None:
        if self._is_substituted(self.root) or not self.root.is_dir():
            raise LabValidationError("STORAGE_ROOT_INVALID", "storage root must be a real directory")

    def _assert_contained_existing_parents(self, target: Path) -> None:
        current = target.parent
        while current != self.root and not current.exists():
            current = current.parent
        if self._is_substituted(current):
            raise LabValidationError("STORAGE_PATH_ESCAPE", "symlink escapes storage root")
        self._assert_contained(current.resolve())

    def _assert_contained(self, resolved: Path) -> None:
        try:
            resolved.relative_to(self.root.resolve(strict=True))
        except ValueError as exc:
            raise LabValidationError("STORAGE_PATH_ESCAPE", "path escapes storage root") from exc

    @staticmethod
    def _is_substituted(path: Path) -> bool:
        if path.is_symlink():
            return True
        try:
            attributes = getattr(os.lstat(path), "st_file_attributes", 0)
        except OSError as exc:
            raise LabValidationError("STORAGE_PATH_INVALID", str(exc)) from exc
        return bool(attributes & 0x400)

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        if os.name == "nt":
            return
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
