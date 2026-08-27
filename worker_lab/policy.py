from __future__ import annotations

import re
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError


POLICY_SCHEMA = "worker-lab-policy:v1"
ROLE_SCHEMA = "worker-lab-role:v1"
CONTEXT_MANIFEST_SCHEMA = "worker-lab-context-manifest:v1"
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9.-]{2,95}$")
RULE_ID_RE = re.compile(r"^P[0-9]{3}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class InvariantRule:
    rule_id: str
    statement: str

    @classmethod
    def from_mapping(cls, value: Any) -> "InvariantRule":
        data = _object(value, {"rule_id", "statement"})
        rule_id = _text(data["rule_id"], "rule_id")
        if not RULE_ID_RE.fullmatch(rule_id):
            raise LabValidationError("POLICY_RULE_INVALID", "invariant rule ID is invalid")
        return cls(rule_id, _text(data["statement"], "statement"))


@dataclass(frozen=True)
class PolicyRecord:
    schema_version: str
    policy_id: str
    policy_version: int
    invariants: tuple[InvariantRule, ...]
    permanent_capabilities: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> "PolicyRecord":
        data = _object(value, {
            "schema_version", "policy_id", "policy_version", "invariants",
            "permanent_capabilities",
        })
        if data["schema_version"] != POLICY_SCHEMA:
            raise LabValidationError("POLICY_SCHEMA_INVALID", "unsupported policy schema")
        if not isinstance(data["invariants"], list):
            raise LabValidationError("POLICY_RULE_INVALID", "invariants must be an array")
        invariants = tuple(InvariantRule.from_mapping(item) for item in data["invariants"])
        if tuple(rule.rule_id for rule in invariants) != tuple(
            sorted({rule.rule_id for rule in invariants})
        ):
            raise LabValidationError("POLICY_RULE_INVALID", "invariants must use sorted unique IDs")
        return cls(
            POLICY_SCHEMA,
            _name(data["policy_id"], "policy_id"),
            _positive_int(data["policy_version"], "policy_version"),
            invariants,
            _capabilities(data["permanent_capabilities"], "permanent_capabilities", nonempty=True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "invariants": [asdict(rule) for rule in self.invariants],
            "permanent_capabilities": list(self.permanent_capabilities),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class RoleRecord:
    schema_version: str
    role_id: str
    role_version: int
    purpose: str
    allowed_capabilities: tuple[str, ...]
    denied_capabilities: tuple[str, ...]
    required_outputs: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> "RoleRecord":
        data = _object(value, {
            "schema_version", "role_id", "role_version", "purpose", "allowed_capabilities",
            "denied_capabilities", "required_outputs",
        })
        if data["schema_version"] != ROLE_SCHEMA:
            raise LabValidationError("ROLE_SCHEMA_INVALID", "unsupported role schema")
        allowed = _capabilities(data["allowed_capabilities"], "allowed_capabilities", nonempty=True)
        denied = _capabilities(data["denied_capabilities"], "denied_capabilities")
        if set(allowed).intersection(denied):
            raise LabValidationError("ROLE_CONFLICT_INVALID", "role cannot allow and deny a capability")
        return cls(
            ROLE_SCHEMA,
            _name(data["role_id"], "role_id"),
            _positive_int(data["role_version"], "role_version"),
            _text(data["purpose"], "purpose"),
            allowed,
            denied,
            _texts(data["required_outputs"], "required_outputs", nonempty=True),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for field in ("allowed_capabilities", "denied_capabilities", "required_outputs"):
            value[field] = list(value[field])
        return value

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class ContextFile:
    path: str
    digest: str
    purpose: str

    @classmethod
    def from_mapping(cls, value: Any) -> "ContextFile":
        data = _object(value, {"path", "digest", "purpose"})
        return cls(
            _path(data["path"]), _digest(data["digest"]), _text(data["purpose"], "purpose")
        )


@dataclass(frozen=True)
class ContextManifest:
    schema_version: str
    manifest_id: str
    manifest_version: int
    repository: str
    starting_commit: str
    files: tuple[ContextFile, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> "ContextManifest":
        data = _object(value, {
            "schema_version", "manifest_id", "manifest_version", "repository",
            "starting_commit", "files",
        })
        if data["schema_version"] != CONTEXT_MANIFEST_SCHEMA:
            raise LabValidationError("CONTEXT_SCHEMA_INVALID", "unsupported context schema")
        if not isinstance(data["files"], list) or not data["files"]:
            raise LabValidationError("CONTEXT_FILES_INVALID", "context files must be a non-empty array")
        files = tuple(ContextFile.from_mapping(item) for item in data["files"])
        if tuple(item.path for item in files) != tuple(sorted({item.path for item in files})):
            raise LabValidationError("CONTEXT_FILES_INVALID", "context paths must be sorted and unique")
        commit = _text(data["starting_commit"], "starting_commit")
        if not SHA_RE.fullmatch(commit):
            raise LabValidationError("CONTEXT_COMMIT_INVALID", "starting commit must be a full Git SHA")
        return cls(
            CONTEXT_MANIFEST_SCHEMA,
            _name(data["manifest_id"], "manifest_id"),
            _positive_int(data["manifest_version"], "manifest_version"),
            _text(data["repository"], "repository"),
            commit,
            files,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "manifest_version": self.manifest_version,
            "repository": self.repository,
            "starting_commit": self.starting_commit,
            "files": [asdict(item) for item in self.files],
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def validate_authority(
    policy: PolicyRecord,
    role: RoleRecord,
    *,
    required_capabilities: tuple[str, ...],
    temporary_denied_capabilities: tuple[str, ...],
) -> None:
    permanent = set(policy.permanent_capabilities)
    allowed = set(role.allowed_capabilities)
    denied = set(role.denied_capabilities).union(temporary_denied_capabilities)
    if allowed - permanent:
        raise LabValidationError(
            "ROLE_AUTHORITY_INVALID", "role grants capabilities absent from permanent policy"
        )
    unsupported = set(required_capabilities) - allowed
    blocked = set(required_capabilities).intersection(denied)
    if unsupported or blocked:
        raise LabValidationError(
            "ROLE_UNSUPPORTED",
            f"unsupported={sorted(unsupported)}, denied={sorted(blocked)}",
        )


def verify_context_files(manifest: ContextManifest, repository_root: Path) -> None:
    if repository_root.is_symlink():
        raise LabValidationError("CONTEXT_REPOSITORY_INVALID", "target repository cannot be a symlink")
    try:
        root = repository_root.resolve(strict=True)
    except OSError as exc:
        raise LabValidationError("CONTEXT_REPOSITORY_INVALID", "target repository is missing") from exc
    if not root.is_dir():
        raise LabValidationError("CONTEXT_REPOSITORY_INVALID", "target repository must be a directory")
    for entry in manifest.files:
        target = root.joinpath(*entry.path.split("/"))
        if target.is_symlink():
            raise LabValidationError("CONTEXT_PATH_ESCAPE", f"context file is a symlink: {entry.path}")
        try:
            resolved = target.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError) as exc:
            raise LabValidationError(
                "CONTEXT_FILE_MISSING", f"context file is missing or outside target: {entry.path}"
            ) from exc
        if not resolved.is_file():
            raise LabValidationError("CONTEXT_FILE_INVALID", f"context entry is not a file: {entry.path}")
        actual = "sha256:" + hashlib.sha256(resolved.read_bytes()).hexdigest()
        if actual != entry.digest:
            raise LabValidationError("CONTEXT_DIGEST_MISMATCH", f"context changed: {entry.path}")
def _object(value: Any, expected: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise LabValidationError("POLICY_FIELDS_INVALID", "fields are missing or unknown")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise LabValidationError("POLICY_TEXT_INVALID", f"{field} must be trimmed text")
    return value


def _name(value: Any, field: str) -> str:
    text = _text(value, field)
    if not NAME_RE.fullmatch(text):
        raise LabValidationError("POLICY_NAME_INVALID", f"{field} is invalid")
    return text


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LabValidationError("POLICY_VERSION_INVALID", f"{field} must be positive")
    return value


def _texts(value: Any, field: str, *, nonempty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LabValidationError("POLICY_LIST_INVALID", f"{field} must be an array")
    result = tuple(_text(item, field) for item in value)
    if nonempty and not result:
        raise LabValidationError("POLICY_LIST_INVALID", f"{field} cannot be empty")
    if result != tuple(sorted(set(result))):
        raise LabValidationError("POLICY_LIST_INVALID", f"{field} must be sorted and unique")
    return result


def _capabilities(value: Any, field: str, *, nonempty: bool = False) -> tuple[str, ...]:
    result = _texts(value, field, nonempty=nonempty)
    if not all(CAPABILITY_RE.fullmatch(item) for item in result):
        raise LabValidationError("POLICY_CAPABILITY_INVALID", f"{field} contains invalid names")
    return result


def _digest(value: Any) -> str:
    text = _text(value, "digest")
    if not DIGEST_RE.fullmatch(text):
        raise LabValidationError("CONTEXT_DIGEST_INVALID", "context digest is invalid")
    return text


def _path(value: Any) -> str:
    text = _text(value, "path")
    if "\\" in text:
        raise LabValidationError("CONTEXT_PATH_INVALID", "context paths use forward slashes")
    candidate = PurePosixPath(text)
    if (
        candidate.is_absolute()
        or ".." in candidate.parts
        or not candidate.parts
        or ":" in candidate.parts[0]
        or candidate.as_posix() != text
    ):
        raise LabValidationError("CONTEXT_PATH_INVALID", "context path must be normalized and relative")
    return text
