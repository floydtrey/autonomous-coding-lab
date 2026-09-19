"""Deterministic filesystem authority policy.

This mechanism answers one question only: is the requested filesystem operation
prohibited by ACL authority policy? It does not judge whether a planned edit is
semantically correct or useful.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import ntpath
import os
from pathlib import Path
import posixpath
import re
from typing import Iterable, Sequence

from ..diagnostics import emit, span
from ..errors import CoreError


_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_WINDOWS_DRIVE_RELATIVE = re.compile(r"^[A-Za-z]:[^\\/]")


class FilesystemOperation(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    CREATE = "CREATE"
    DELETE = "DELETE"
    MOVE = "MOVE"
    RENAME = "RENAME"

    @property
    def mutates(self) -> bool:
        return self is not FilesystemOperation.READ


class ProtectionLayer(StrEnum):
    PERMANENT_SYSTEM = "PERMANENT_SYSTEM"
    PERMANENT_ACL = "PERMANENT_ACL"
    USER = "USER"


@dataclass(frozen=True)
class ProtectedPath:
    path: str
    layer: ProtectionLayer
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path.strip():
            raise CoreError("FILESYSTEM_AUTHORITY_INVALID", "protected path is required")
        if not isinstance(self.layer, ProtectionLayer):
            raise CoreError("FILESYSTEM_AUTHORITY_INVALID", "protected path layer is invalid")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise CoreError("FILESYSTEM_AUTHORITY_INVALID", "protected path reason is required")

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "layer": str(self.layer),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class FilesystemDecision:
    allowed: bool
    operation: FilesystemOperation
    path: str
    destination: str | None = None
    code: str = "FILESYSTEM_AUTHORITY_ALLOWED"
    reason: str | None = None
    matched_protection: ProtectedPath | None = None

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "operation": str(self.operation),
            "path": self.path,
            "destination": self.destination,
            "code": self.code,
            "reason": self.reason,
            "matched_protection": (
                None if self.matched_protection is None else self.matched_protection.to_dict()
            ),
        }


@dataclass(frozen=True)
class _CanonicalPath:
    style: str
    value: str


class FilesystemAuthorityService:
    """Apply permanent and operator-managed mutation-deny protections."""

    component = "core.filesystem_authority"

    def __init__(
        self,
        *,
        project_root: str | Path,
        permanent_protections: Sequence[ProtectedPath] = (),
        user_protections: Sequence[ProtectedPath] = (),
    ) -> None:
        self._project_root = self._canonicalize_root(project_root)
        self._permanent = self._normalize_protections(permanent_protections)
        self._user = self._normalize_protections(user_protections)

    @classmethod
    def for_acl(
        cls,
        *,
        project_root: str | Path,
        state_root: str | Path | None = None,
        authority_config_path: str | Path | None = None,
        user_protected_paths: Iterable[tuple[str, str]] = (),
        system_roots: Sequence[str] | None = None,
    ) -> "FilesystemAuthorityService":
        root = cls._canonicalize_root(project_root)
        permanent: list[ProtectedPath] = []

        roots = tuple(system_roots) if system_roots is not None else cls._default_system_roots()
        for item in roots:
            permanent.append(
                ProtectedPath(
                    path=item,
                    layer=ProtectionLayer.PERMANENT_SYSTEM,
                    reason="operating-system or system-managed location",
                )
            )

        permanent.extend(
            [
                ProtectedPath(
                    path=cls._join(root, "acl_core"),
                    layer=ProtectionLayer.PERMANENT_ACL,
                    reason="ACL Core is permanently protected from Worker mutation",
                ),
                ProtectedPath(
                    path=cls._join(root, "acl_controller"),
                    layer=ProtectionLayer.PERMANENT_ACL,
                    reason="ACL Controller is permanently protected from Worker mutation",
                ),
            ]
        )

        if state_root is not None:
            permanent.append(
                ProtectedPath(
                    path=str(state_root),
                    layer=ProtectionLayer.PERMANENT_ACL,
                    reason="ACL Controller state is permanently protected from Worker mutation",
                )
            )
        if authority_config_path is not None:
            permanent.append(
                ProtectedPath(
                    path=str(authority_config_path),
                    layer=ProtectionLayer.PERMANENT_ACL,
                    reason="filesystem authority policy cannot be modified by Planner or Worker",
                )
            )

        user = [
            ProtectedPath(path=path, layer=ProtectionLayer.USER, reason=reason)
            for path, reason in user_protected_paths
        ]
        return cls(
            project_root=project_root,
            permanent_protections=permanent,
            user_protections=user,
        )

    @property
    def permanent_protections(self) -> tuple[ProtectedPath, ...]:
        return tuple(item[1] for item in self._permanent)

    @property
    def user_protections(self) -> tuple[ProtectedPath, ...]:
        return tuple(item[1] for item in self._user)

    def evaluate(
        self,
        operation: FilesystemOperation | str,
        path: str | Path,
        *,
        destination: str | Path | None = None,
    ) -> FilesystemDecision:
        try:
            operation = FilesystemOperation(operation)
        except (TypeError, ValueError) as exc:
            raise CoreError(
                "FILESYSTEM_AUTHORITY_INVALID",
                "filesystem operation is unsupported",
                {"operation": str(operation)},
            ) from exc

        with span(
            self.component,
            "evaluate",
            operation=str(operation),
            requested_path=str(path),
            requested_destination=None if destination is None else str(destination),
        ):
            source = self._canonicalize(path)
            target = None if destination is None else self._canonicalize(destination)

            if operation in {FilesystemOperation.MOVE, FilesystemOperation.RENAME}:
                if target is None:
                    raise CoreError(
                        "FILESYSTEM_AUTHORITY_INVALID",
                        "move/rename operation requires destination",
                    )
            elif target is not None:
                raise CoreError(
                    "FILESYSTEM_AUTHORITY_INVALID",
                    "destination is only valid for move/rename operations",
                )

            # Read authority is intentionally distinct. PL04 provides mutation
            # protections only; broader/sensitive read policy can be layered
            # separately without turning this deny policy into a semantic judge.
            if not operation.mutates:
                decision = FilesystemDecision(
                    allowed=True,
                    operation=operation,
                    path=source.value,
                    destination=None if target is None else target.value,
                )
                self._emit_decision(decision)
                return decision

            matched = self._match_protection(source)
            denied_path = source
            if matched is None and target is not None:
                matched = self._match_protection(target)
                denied_path = target

            if matched is not None:
                decision = FilesystemDecision(
                    allowed=False,
                    operation=operation,
                    path=source.value,
                    destination=None if target is None else target.value,
                    code="FILESYSTEM_MUTATION_DENIED",
                    reason=matched.reason,
                    matched_protection=matched,
                )
                emit(
                    "ERROR",
                    self.component,
                    "evaluate",
                    "filesystem_mutation_denied",
                    operation=str(operation),
                    path=source.value,
                    destination=None if target is None else target.value,
                    denied_path=denied_path.value,
                    protection=matched.to_dict(),
                )
                return decision

            decision = FilesystemDecision(
                allowed=True,
                operation=operation,
                path=source.value,
                destination=None if target is None else target.value,
            )
            self._emit_decision(decision)
            return decision

    def require_allowed(
        self,
        operation: FilesystemOperation | str,
        path: str | Path,
        *,
        destination: str | Path | None = None,
    ) -> FilesystemDecision:
        decision = self.evaluate(operation, path, destination=destination)
        if not decision.allowed:
            raise CoreError(
                decision.code,
                "filesystem mutation is denied by authority policy",
                decision.to_dict(),
            )
        return decision

    def _match_protection(self, candidate: _CanonicalPath) -> ProtectedPath | None:
        for canonical, protection in (*self._permanent, *self._user):
            if canonical.style != candidate.style:
                continue
            if self._contains(canonical.value, candidate.value, canonical.style):
                return protection
        return None

    def _normalize_protections(
        self,
        protections: Sequence[ProtectedPath],
    ) -> tuple[tuple[_CanonicalPath, ProtectedPath], ...]:
        normalized: list[tuple[_CanonicalPath, ProtectedPath]] = []
        seen: set[tuple[str, str]] = set()
        for protection in protections:
            if not isinstance(protection, ProtectedPath):
                raise CoreError(
                    "FILESYSTEM_AUTHORITY_INVALID",
                    "protection entries must be ProtectedPath values",
                )
            canonical = self._canonicalize(protection.path)
            key = (canonical.style, canonical.value)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                (
                    canonical,
                    ProtectedPath(
                        path=canonical.value,
                        layer=protection.layer,
                        reason=protection.reason,
                    ),
                )
            )
        normalized.sort(key=lambda item: (item[0].style, item[0].value))
        return tuple(normalized)

    def _canonicalize(self, value: str | Path) -> _CanonicalPath:
        raw = str(value)
        if not raw.strip():
            raise CoreError("FILESYSTEM_AUTHORITY_INVALID", "filesystem path is required")
        raw = os.path.expandvars(raw.strip())

        if self._looks_windows(raw):
            style = "windows"
            if _WINDOWS_DRIVE_RELATIVE.match(raw):
                raise CoreError(
                    "FILESYSTEM_AUTHORITY_INVALID",
                    "drive-relative Windows paths are ambiguous and not allowed",
                    {"path": raw},
                )
            if not self._is_absolute(raw, style):
                if self._project_root.style != style:
                    raise CoreError(
                        "FILESYSTEM_AUTHORITY_INVALID",
                        "relative path style differs from project root",
                        {"path": raw, "project_root": self._project_root.value},
                    )
                raw = ntpath.join(self._project_root.value, raw)
            value_norm = ntpath.normcase(ntpath.normpath(raw.replace("/", "\\")))
            if os.name == "nt":
                try:
                    value_norm = ntpath.normcase(str(Path(value_norm).resolve(strict=False)))
                except OSError:
                    pass
            return _CanonicalPath(style, value_norm)

        style = "posix"
        raw = raw.replace("\\", "/") if os.name != "nt" else raw
        if not self._is_absolute(raw, style):
            if self._project_root.style != style:
                raise CoreError(
                    "FILESYSTEM_AUTHORITY_INVALID",
                    "relative path style differs from project root",
                    {"path": raw, "project_root": self._project_root.value},
                )
            raw = posixpath.join(self._project_root.value, raw)
        value_norm = posixpath.normpath(raw)
        if os.name != "nt":
            try:
                value_norm = str(Path(value_norm).resolve(strict=False))
            except OSError:
                pass
        return _CanonicalPath(style, value_norm)

    @classmethod
    def _canonicalize_root(cls, value: str | Path) -> _CanonicalPath:
        raw = str(value).strip()
        if not raw:
            raise CoreError("FILESYSTEM_AUTHORITY_INVALID", "project_root is required")
        raw = os.path.expandvars(raw)
        if cls._looks_windows(raw):
            if not cls._is_absolute(raw, "windows"):
                raise CoreError(
                    "FILESYSTEM_AUTHORITY_INVALID",
                    "project_root must be absolute",
                    {"project_root": raw},
                )
            normalized = ntpath.normcase(ntpath.normpath(raw.replace("/", "\\")))
            if os.name == "nt":
                try:
                    normalized = ntpath.normcase(str(Path(normalized).resolve(strict=False)))
                except OSError:
                    pass
            return _CanonicalPath("windows", normalized)

        if not cls._is_absolute(raw, "posix"):
            raw = str(Path(raw).expanduser().resolve(strict=False))
        normalized = posixpath.normpath(raw)
        if os.name != "nt":
            normalized = str(Path(normalized).resolve(strict=False))
        return _CanonicalPath("posix", normalized)

    @staticmethod
    def _looks_windows(value: str) -> bool:
        return bool(
            _WINDOWS_ABSOLUTE.match(value)
            or _WINDOWS_DRIVE_RELATIVE.match(value)
            or value.startswith("\\\\")
        )

    @staticmethod
    def _is_absolute(value: str, style: str) -> bool:
        return ntpath.isabs(value) if style == "windows" else posixpath.isabs(value)

    @staticmethod
    def _contains(parent: str, candidate: str, style: str) -> bool:
        module = ntpath if style == "windows" else posixpath
        try:
            return module.commonpath([parent, candidate]) == parent
        except ValueError:
            return False

    @staticmethod
    def _join(root: _CanonicalPath, *parts: str) -> str:
        module = ntpath if root.style == "windows" else posixpath
        return module.join(root.value, *parts)

    @staticmethod
    def _default_system_roots() -> tuple[str, ...]:
        if os.name == "nt":
            roots: list[str] = []
            for name in ("SystemRoot", "WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
                value = os.getenv(name)
                if value and value.strip():
                    roots.append(value.strip())
            system_drive = os.getenv("SystemDrive")
            if system_drive and system_drive.strip():
                drive = system_drive.strip().rstrip("\\/")
                roots.extend(
                    [
                        drive + "\\Boot",
                        drive + "\\EFI",
                        drive + "\\Recovery",
                        drive + "\\System Volume Information",
                        drive + "\\$Recycle.Bin",
                    ]
                )
            return tuple(dict.fromkeys(roots))

        return (
            "/bin",
            "/boot",
            "/dev",
            "/etc",
            "/lib",
            "/lib64",
            "/proc",
            "/root",
            "/sbin",
            "/sys",
            "/usr",
            "/var",
        )

    def _emit_decision(self, decision: FilesystemDecision) -> None:
        emit(
            "DEBUG",
            self.component,
            "evaluate",
            "filesystem_authority_allowed",
            **decision.to_dict(),
        )
