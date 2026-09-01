from __future__ import annotations

import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .installation_manifest import InstallationManifest, load_installation_manifest
from .storage import AtomicRecordStore


DOCTOR_SCHEMA = "worker-lab-installation-doctor:v1"
ACTIVATION_EVIDENCE_SCHEMA = "worker-lab-activation-evidence:v1"
AUTHORIZATION_EVIDENCE_SCHEMA = "worker-lab-one-time-authorization:v1"
RECOVERY_EVIDENCE_SCHEMA = "worker-lab-synthetic-recovery:v1"
ONE_TIME_CONFIRMATION = "AUTHORIZE-SYNTHETIC-READ-ONLY-ONCE"
SYNTHETIC_OPERATION = "synthetic-read-only-proposal"

_CONTROLLER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{5,95}$")
_COMPONENT_NAMES = frozenset({
    "autonomous-worker-framework",
    "local-model-bench",
    "worker-lab",
})


@dataclass(frozen=True)
class DoctorReport:
    installation_id: str
    manifest_digest: str
    execution_authority: str
    participant_states: Mapping[str, str]
    component_digests: Mapping[str, str]
    python_digest: str
    python_version: str
    codex_digest: str
    codex_version: str
    execution_ready: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DOCTOR_SCHEMA,
            "installation_id": self.installation_id,
            "manifest_digest": self.manifest_digest,
            "execution_authority": self.execution_authority,
            "participant_states": dict(sorted(self.participant_states.items())),
            "component_digests": dict(sorted(self.component_digests.items())),
            "python_digest": self.python_digest,
            "python_version": self.python_version,
            "codex_digest": self.codex_digest,
            "codex_version": self.codex_version,
            "execution_ready": self.execution_ready,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class ActivationEvidence:
    installation_id: str
    manifest_digest: str
    execution_authority: str
    participant_states: Mapping[str, str]
    component_digests: Mapping[str, str]
    python_digest: str
    codex_digest: str
    observed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ACTIVATION_EVIDENCE_SCHEMA,
            "installation_id": self.installation_id,
            "manifest_digest": self.manifest_digest,
            "execution_authority": self.execution_authority,
            "participant_states": dict(sorted(self.participant_states.items())),
            "component_digests": dict(sorted(self.component_digests.items())),
            "python_digest": self.python_digest,
            "codex_digest": self.codex_digest,
            "observed_at": self.observed_at,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: Any) -> "ActivationEvidence":
        data = _object(value, {
            "schema_version", "installation_id", "manifest_digest", "execution_authority",
            "participant_states", "component_digests", "python_digest", "codex_digest",
            "observed_at",
        })
        if data["schema_version"] != ACTIVATION_EVIDENCE_SCHEMA:
            raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "activation evidence version differs")
        participants = _string_mapping(data["participant_states"], _COMPONENT_NAMES)
        components = _digest_mapping(data["component_digests"], _COMPONENT_NAMES)
        return cls(
            _text(data["installation_id"]), _digest(data["manifest_digest"]),
            _choice(data["execution_authority"], {"DISABLED", "ENABLED"}), participants,
            components, _digest(data["python_digest"]), _digest(data["codex_digest"]),
            _timestamp(data["observed_at"]),
        )


@dataclass(frozen=True)
class AuthorizationEvidence:
    authorization_id: str
    controller_identity: str
    operation: str
    run_directory_digest: str
    invocation_id: str
    invocation_digest: str
    activation_evidence_digest: str
    authorized_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": AUTHORIZATION_EVIDENCE_SCHEMA,
            "authorization_id": self.authorization_id,
            "controller_identity": self.controller_identity,
            "operation": self.operation,
            "run_directory_digest": self.run_directory_digest,
            "invocation_id": self.invocation_id,
            "invocation_digest": self.invocation_digest,
            "activation_evidence_digest": self.activation_evidence_digest,
            "authorized_at": self.authorized_at,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: Any) -> "AuthorizationEvidence":
        data = _object(value, {
            "schema_version", "authorization_id", "controller_identity", "operation",
            "run_directory_digest", "invocation_id", "invocation_digest",
            "activation_evidence_digest", "authorized_at",
        })
        if data["schema_version"] != AUTHORIZATION_EVIDENCE_SCHEMA or data["operation"] != SYNTHETIC_OPERATION:
            raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "authorization evidence contract differs")
        return cls(
            _identifier(data["authorization_id"]), validate_controller_identity(data["controller_identity"]),
            SYNTHETIC_OPERATION, _digest(data["run_directory_digest"]),
            _identifier(data["invocation_id"]), _digest(data["invocation_digest"]),
            _digest(data["activation_evidence_digest"]), _timestamp(data["authorized_at"]),
        )


@dataclass(frozen=True)
class RecoveryEvidence:
    authorization_id: str
    controller_identity: str
    attempt_id: str
    invocation_id: str
    invocation_state: str
    attempt_state: str
    workspace_outcome: str
    recovered_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RECOVERY_EVIDENCE_SCHEMA,
            "authorization_id": self.authorization_id,
            "controller_identity": self.controller_identity,
            "attempt_id": self.attempt_id,
            "invocation_id": self.invocation_id,
            "invocation_state": self.invocation_state,
            "attempt_state": self.attempt_state,
            "workspace_outcome": self.workspace_outcome,
            "recovered_at": self.recovered_at,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


def inspect_installation(path: Path | None = None) -> tuple[InstallationManifest, DoctorReport]:
    """Verify the complete installed identity without launching an adapter or model."""
    manifest = load_installation_manifest(path)
    ready = (
        manifest.execution_authority == "ENABLED"
        and manifest.participants.get("worker-lab") == "ACTIVE"
        and manifest.participants.get("autonomous-worker-framework") == "ACTIVE"
    )
    report = DoctorReport(
        manifest.installation_id,
        _bytes_digest(manifest.path.read_bytes()),
        manifest.execution_authority,
        manifest.participants,
        {name: component.installation_digest for name, component in manifest.components.items()},
        manifest.python.digest,
        manifest.python.version,
        manifest.codex.digest,
        manifest.codex.version,
        ready,
    )
    return manifest, report


def validate_controller_identity(value: Any) -> str:
    text = _text(value)
    if not _CONTROLLER_RE.fullmatch(text):
        raise LabValidationError("OPERATOR_CONTROLLER_INVALID", "controller identity is invalid")
    return text


def require_one_time_confirmation(value: Any) -> None:
    if value != ONE_TIME_CONFIRMATION:
        raise LabValidationError(
            "OPERATOR_AUTHORIZATION_REQUIRED",
            f"one-time confirmation must equal {ONE_TIME_CONFIRMATION}",
        )


def validate_new_run_directory(path: Path, installation_root: Path) -> Path:
    if not isinstance(path, Path) or not path.is_absolute() or os.path.lexists(path):
        raise LabValidationError("OPERATOR_RUN_DIRECTORY_INVALID", "run directory must be a new absolute path")
    parent = _canonical_directory(path.parent)
    candidate = parent / path.name
    _reject_protected_or_git_path(candidate, installation_root)
    return candidate


def validate_existing_run_directory(path: Path, installation_root: Path) -> Path:
    candidate = _canonical_directory(path)
    _reject_protected_or_git_path(candidate, installation_root)
    return candidate


def persist_operator_evidence(
    state_root: Path,
    *,
    manifest: InstallationManifest,
    report: DoctorReport,
    run_directory: Path,
    controller_identity: str,
    invocation_id: str,
    invocation_digest: str,
    observed_at: str,
) -> tuple[ActivationEvidence, AuthorizationEvidence]:
    controller = validate_controller_identity(controller_identity)
    component_digests = {
        name: component.installation_digest for name, component in manifest.components.items()
    }
    if (
        report.installation_id != manifest.installation_id
        or report.manifest_digest != _bytes_digest(manifest.path.read_bytes())
        or report.execution_authority != manifest.execution_authority
        or dict(report.participant_states) != dict(manifest.participants)
        or dict(report.component_digests) != component_digests
        or report.python_digest != manifest.python.digest
        or report.codex_digest != manifest.codex.digest
    ):
        raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "doctor report and manifest differ")
    activation = ActivationEvidence(
        manifest.installation_id, report.manifest_digest, manifest.execution_authority,
        manifest.participants,
        component_digests,
        manifest.python.digest, manifest.codex.digest, _timestamp(observed_at),
    )
    authorization = AuthorizationEvidence(
        "AUTHORIZATION-" + uuid.uuid4().hex.upper(), controller, SYNTHETIC_OPERATION,
        run_directory_digest(run_directory), _identifier(invocation_id), _digest(invocation_digest),
        activation.digest(), _timestamp(observed_at),
    )
    store = AtomicRecordStore(state_root)
    store.write("operator/activation.json", activation)
    store.write("operator/authorization.json", authorization)
    return activation, authorization


def read_operator_evidence(state_root: Path) -> tuple[ActivationEvidence, AuthorizationEvidence]:
    store = AtomicRecordStore(state_root)
    activation = store.read("operator/activation.json", ActivationEvidence.from_mapping)
    authorization = store.read("operator/authorization.json", AuthorizationEvidence.from_mapping)
    if authorization.activation_evidence_digest != activation.digest():
        raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "authorization and activation evidence differ")
    return activation, authorization


def run_directory_digest(path: Path) -> str:
    return canonical_digest({"canonical_path": os.path.normcase(os.path.normpath(str(path)))})


def _reject_protected_or_git_path(candidate: Path, installation_root: Path) -> None:
    installation = installation_root.resolve(strict=True)
    if candidate == installation or candidate.is_relative_to(installation) or installation.is_relative_to(candidate):
        raise LabValidationError("OPERATOR_RUN_DIRECTORY_INVALID", "run directory overlaps the installation")
    for ancestor in (candidate, *candidate.parents):
        if os.path.lexists(ancestor / ".git"):
            raise LabValidationError("OPERATOR_RUN_DIRECTORY_INVALID", "run directory is inside a Git repository")


def _canonical_directory(path: Path) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise LabValidationError("OPERATOR_RUN_DIRECTORY_INVALID", "run directory must be absolute")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise LabValidationError("OPERATOR_RUN_DIRECTORY_INVALID", "run directory parent is unavailable") from exc
    if resolved != path or not resolved.is_dir():
        raise LabValidationError("OPERATOR_RUN_DIRECTORY_INVALID", "run directory path is substituted")
    current = Path(resolved.anchor)
    for part in resolved.parts[1:]:
        current /= part
        if current.is_symlink() or getattr(os.lstat(current), "st_file_attributes", 0) & 0x400:
            raise LabValidationError("OPERATOR_RUN_DIRECTORY_INVALID", "run directory uses path indirection")
    return resolved


def _object(value: Any, fields: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "operator evidence fields are invalid")
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "operator evidence text is invalid")
    return value


def _identifier(value: Any) -> str:
    text = _text(value)
    if not _ID_RE.fullmatch(text):
        raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "operator evidence identifier is invalid")
    return text


def _digest(value: Any) -> str:
    text = _text(value)
    if not _DIGEST_RE.fullmatch(text):
        raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "operator evidence digest is invalid")
    return text


def _timestamp(value: Any) -> str:
    text = _text(value)
    if not text.endswith("Z") or "T" not in text:
        raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "operator evidence timestamp is invalid")
    return text


def _choice(value: Any, allowed: set[str]) -> str:
    text = _text(value)
    if text not in allowed:
        raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "operator evidence choice is invalid")
    return text


def _string_mapping(value: Any, expected_keys: frozenset[str]) -> Mapping[str, str]:
    if not isinstance(value, Mapping) or set(value) != expected_keys:
        raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "operator evidence mapping is invalid")
    return {key: _text(item) for key, item in value.items()}


def _digest_mapping(value: Any, expected_keys: frozenset[str]) -> Mapping[str, str]:
    if not isinstance(value, Mapping) or set(value) != expected_keys:
        raise LabValidationError("OPERATOR_EVIDENCE_INVALID", "operator digest mapping is invalid")
    return {key: _digest(item) for key, item in value.items()}


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()
