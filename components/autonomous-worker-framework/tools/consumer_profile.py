from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:
    from tools.repository_state import (
        RepositoryStateError,
        repository_head,
        require_clean_workspace,
        require_repository_root,
    )
except ModuleNotFoundError:  # direct execution support
    from repository_state import (  # type: ignore
        RepositoryStateError,
        repository_head,
        require_clean_workspace,
        require_repository_root,
    )


PROFILE_VERSION = "consumer-profile:v1"
CONTEXT_VERSION = "worker-context:v1"


class ConsumerProfileError(ValueError):
    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


@dataclass(frozen=True)
class ValidationCommand:
    name: str
    argv: tuple[str, ...]
    timeout_seconds: int

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["argv"] = list(self.argv)
        return value

    @classmethod
    def from_mapping(cls, value: Any) -> "ValidationCommand":
        if not isinstance(value, dict) or set(value) != {"name", "argv", "timeout_seconds"}:
            raise ConsumerProfileError("CONTEXT_PROFILE_INVALID", "validation command fields are invalid")
        name = value["name"]
        argv = value["argv"]
        timeout = value["timeout_seconds"]
        if (
            not isinstance(name, str)
            or not name.strip()
            or name != name.strip()
            or not isinstance(argv, list)
            or not argv
            or any(not isinstance(item, str) or not item or "\x00" in item for item in argv)
            or isinstance(timeout, bool)
            or not isinstance(timeout, int)
            or timeout <= 0
        ):
            raise ConsumerProfileError("CONTEXT_PROFILE_INVALID", "validation command is invalid")
        return cls(name, tuple(argv), timeout)


@dataclass(frozen=True)
class ConsumerProfile:
    version: str
    consumer: str
    authority_paths: tuple[str, ...]
    protected_prefixes: tuple[str, ...]
    protected_exact: tuple[str, ...]
    product_invariants: tuple[str, ...]
    full_validation: tuple[ValidationCommand, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "consumer": self.consumer,
            "authority_paths": list(self.authority_paths),
            "protected_prefixes": list(self.protected_prefixes),
            "protected_exact": list(self.protected_exact),
            "product_invariants": list(self.product_invariants),
            "full_validation": [command.to_dict() for command in self.full_validation],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: Any) -> "ConsumerProfile":
        fields = {
            "version", "consumer", "authority_paths", "protected_prefixes",
            "protected_exact", "product_invariants", "full_validation",
        }
        if not isinstance(value, dict) or set(value) != fields:
            raise ConsumerProfileError("CONTEXT_PROFILE_INVALID", "consumer profile fields are invalid")
        version = value["version"]
        consumer = value["consumer"]
        if (
            version != PROFILE_VERSION
            or not isinstance(consumer, str)
            or not consumer.strip()
            or consumer != consumer.strip()
            or "\x00" in consumer
        ):
            raise ConsumerProfileError("CONTEXT_PROFILE_INVALID", "consumer profile identity is invalid")
        authority = _normalized_paths(
            value["authority_paths"], "authority_paths", require_nonempty=True, require_sorted=True
        )
        prefixes = _normalized_paths(
            value["protected_prefixes"], "protected_prefixes", require_nonempty=False, require_sorted=True
        )
        exact = _normalized_paths(
            value["protected_exact"], "protected_exact", require_nonempty=False, require_sorted=True
        )
        invariants = _texts(value["product_invariants"], "product_invariants")
        commands = value["full_validation"]
        if not isinstance(commands, list) or not commands:
            raise ConsumerProfileError("CONTEXT_PROFILE_INVALID", "profile validation commands are required")
        parsed_commands = tuple(ValidationCommand.from_mapping(item) for item in commands)
        if len({item.name for item in parsed_commands}) != len(parsed_commands):
            raise ConsumerProfileError("CONTEXT_PROFILE_INVALID", "profile validation command names must be unique")
        return cls(
            PROFILE_VERSION, consumer, authority, prefixes, exact, invariants, parsed_commands,
        )


@dataclass(frozen=True)
class ContextFile:
    path: str
    sha256: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class WorkerContextPacket:
    version: str
    consumer: str
    profile_digest: str
    repository_head: str
    allowed_paths: tuple[str, ...]
    authority_files: tuple[ContextFile, ...]
    task_files: tuple[ContextFile, ...]
    product_invariants: tuple[str, ...]
    full_validation: tuple[ValidationCommand, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "consumer": self.consumer,
            "profile_digest": self.profile_digest,
            "repository_head": self.repository_head,
            "allowed_paths": list(self.allowed_paths),
            "authority_files": [item.to_dict() for item in self.authority_files],
            "task_files": [item.to_dict() for item in self.task_files],
            "product_invariants": list(self.product_invariants),
            "full_validation": [command.to_dict() for command in self.full_validation],
        }

    def to_json(self, *, pretty: bool = False) -> str:
        options: dict[str, Any] = {"sort_keys": True}
        if pretty:
            options["indent"] = 2
        else:
            options["separators"] = (",", ":")
        return json.dumps(self.to_dict(), **options)

    def digest(self) -> str:
        return _digest(self.to_dict())



def build_context_packet(
    repo_root: Path,
    *,
    allowed_paths: Iterable[str],
    profile: ConsumerProfile,
    task_context_paths: Iterable[str] = (),
) -> WorkerContextPacket:
    root = _context_repository_root(repo_root)
    _require_clean_context_workspace(root)
    head = _context_repository_head(root, "CONTEXT_IDENTITY_INVALID")

    allowed = _normalized_paths(
        allowed_paths, "allowed_paths", require_nonempty=True, require_sorted=True
    )
    for path in allowed:
        _reject_protected(profile, path)
    context = _normalized_paths(
        task_context_paths, "task_context_paths", require_nonempty=False, require_sorted=True
    )
    authority = _normalized_paths(
        profile.authority_paths, "authority_paths", require_nonempty=True, require_sorted=False
    )
    overlap = set(context).intersection(allowed)
    if overlap:
        raise ConsumerProfileError(
            "CONTEXT_SCOPE_INVALID",
            f"read-only task context cannot also be writable: {sorted(overlap)}",
        )

    return WorkerContextPacket(
        version=CONTEXT_VERSION,
        consumer=profile.consumer,
        profile_digest=profile.digest(),
        repository_head=head,
        allowed_paths=allowed,
        authority_files=_fingerprints(root, authority, "authority"),
        task_files=_fingerprints(root, context, "task context"),
        product_invariants=profile.product_invariants,
        full_validation=profile.full_validation,
    )


def verify_context_packet(
    packet: WorkerContextPacket,
    repo_root: Path,
    *,
    profile: ConsumerProfile,
) -> None:
    root = _context_repository_root(repo_root)
    if packet.version != CONTEXT_VERSION or packet.consumer != profile.consumer:
        raise ConsumerProfileError("CONTEXT_PROFILE_MISMATCH", "context packet profile is unsupported")
    if packet.profile_digest != profile.digest():
        raise ConsumerProfileError("CONTEXT_PROFILE_MISMATCH", "consumer profile changed")
    if _context_repository_head(root, "CONTEXT_IDENTITY_CHANGED") != packet.repository_head:
        raise ConsumerProfileError("CONTEXT_IDENTITY_CHANGED", "repository HEAD changed")
    _require_clean_context_workspace(root)
    if _fingerprints(root, tuple(item.path for item in packet.authority_files), "authority") != packet.authority_files:
        raise ConsumerProfileError("CONTEXT_AUTHORITY_CHANGED", "authoritative context changed")
    if _fingerprints(root, tuple(item.path for item in packet.task_files), "task context") != packet.task_files:
        raise ConsumerProfileError("CONTEXT_TASK_FILES_CHANGED", "task context changed")


def build_context_prompt(packet: WorkerContextPacket, *, objective: str) -> str:
    clean_objective = " ".join(objective.split())
    if not clean_objective:
        raise ConsumerProfileError("CONTEXT_OBJECTIVE_INVALID", "objective must be non-empty")
    authority = "\n".join(f"- {item.path}" for item in packet.authority_files)
    task_files = "\n".join(f"- {item.path}" for item in packet.task_files) or "- none"
    allowed = "\n".join(f"- {path}" for path in packet.allowed_paths)
    invariants = "\n".join(f"- {item}" for item in packet.product_invariants)
    return (
        f"Consumer: {packet.consumer}\nRepository HEAD: {packet.repository_head}\n"
        f"Context digest: {packet.digest()}\nObjective: {clean_objective}\n\n"
        f"Read authoritative guidance first:\n{authority}\n\n"
        f"Read-only task context:\n{task_files}\n\n"
        f"The only paths that may be changed are:\n{allowed}\n\n"
        f"Product and authority invariants:\n{invariants}\n\n"
        "Do not modify files yet. Analyze the objective against this exact repository state and return a bounded implementation proposal, relevant tests, risks, and any required clarification."
    )


def _fingerprints(root: Path, paths: tuple[str, ...], label: str) -> tuple[ContextFile, ...]:
    items: list[ContextFile] = []
    for path in paths:
        file_path = root.joinpath(*PurePosixPath(path).parts)
        if not file_path.is_file():
            raise ConsumerProfileError("CONTEXT_FILE_MISSING", f"required {label} file is missing: {path}")
        items.append(ContextFile(path, "sha256:" + hashlib.sha256(file_path.read_bytes()).hexdigest()))
    return tuple(items)


def _normalized_paths(
    values: Iterable[str],
    field: str,
    *,
    require_nonempty: bool,
    require_sorted: bool,
) -> tuple[str, ...]:
    paths = tuple(_repo_path(value, field) for value in values)
    if require_nonempty and not paths:
        raise ConsumerProfileError("CONTEXT_SCOPE_INVALID", f"{field} must not be empty")
    if len(paths) != len(set(paths)):
        raise ConsumerProfileError("CONTEXT_SCOPE_INVALID", f"{field} must be unique")
    if require_sorted and paths != tuple(sorted(paths)):
        raise ConsumerProfileError("CONTEXT_SCOPE_INVALID", f"{field} must be sorted and unique")
    return paths


def _texts(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ConsumerProfileError("CONTEXT_PROFILE_INVALID", f"{field} must be a non-empty array")
    items = tuple(value)
    if any(not isinstance(item, str) or not item.strip() or item != item.strip() or "\x00" in item for item in items):
        raise ConsumerProfileError("CONTEXT_PROFILE_INVALID", f"{field} contains invalid text")
    if items != tuple(sorted(set(items))):
        raise ConsumerProfileError("CONTEXT_PROFILE_INVALID", f"{field} must be sorted and unique")
    return items


def _repo_path(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConsumerProfileError("CONTEXT_SCOPE_INVALID", f"{field} contains an invalid path")
    text = value.replace("\\", "/")
    candidate = PurePosixPath(text)
    if candidate.is_absolute() or ".." in candidate.parts or candidate.as_posix() != text or ":" in candidate.parts[0]:
        raise ConsumerProfileError("CONTEXT_SCOPE_INVALID", f"{field} path is not normalized: {value!r}")
    return text


def _reject_protected(profile: ConsumerProfile, path: str) -> None:
    if path in profile.protected_exact or any(path.startswith(prefix) for prefix in profile.protected_prefixes):
        raise ConsumerProfileError("CONTEXT_SCOPE_PROTECTED", f"protected path cannot be writable: {path}")


def _context_repository_root(root: Path) -> Path:
    try:
        return require_repository_root(root)
    except RepositoryStateError as exc:
        raise ConsumerProfileError(
            "CONTEXT_REPOSITORY_INVALID",
            "target must be a Git-backed coding workspace root",
        ) from exc


def _context_repository_head(root: Path, failure_code: str) -> str:
    try:
        return repository_head(root)
    except RepositoryStateError as exc:
        raise ConsumerProfileError(failure_code, "Git source-state identity is invalid") from exc


def _require_clean_context_workspace(root: Path) -> None:
    try:
        require_clean_workspace(root)
    except RepositoryStateError as exc:
        raise ConsumerProfileError(
            "CONTEXT_REPOSITORY_DIRTY",
            "Git-backed coding workspace must be clean",
        ) from exc


def _digest(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
