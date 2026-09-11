from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError


DOCTOR_SCHEMA = "worker-lab-installation-doctor:v2"
_CONTROLLER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


@dataclass(frozen=True)
class DoctorReport:
    installation_id: str
    manifest_digest: str
    execution_authority: str
    participant_states: Mapping[str, str]
    component_digests: Mapping[str, str]
    execution_ready: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DOCTOR_SCHEMA,
            "installation_id": self.installation_id,
            "manifest_digest": self.manifest_digest,
            "execution_authority": self.execution_authority,
            "participant_states": dict(sorted(self.participant_states.items())),
            "component_digests": dict(sorted(self.component_digests.items())),
            "execution_ready": self.execution_ready,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


def inspect_installation(path: Path | None = None) -> tuple[Mapping[str, Any], DoctorReport]:
    repository_root = Path(__file__).resolve().parents[3]
    manifest_path = repository_root / "config" / "portable-installation-manifest.json" if path is None else path
    if manifest_path.is_dir():
        manifest_path = manifest_path / "config" / "portable-installation-manifest.json"
    try:
        raw = manifest_path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable installation manifest is unavailable") from exc
    if not isinstance(value, dict) or value.get("schema_version") != "acl-portable-installation-manifest:v1":
        raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable installation manifest identity differs")
    policy = value.get("activation_policy")
    components = value.get("components")
    if not isinstance(policy, dict) or not isinstance(components, dict):
        raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable installation manifest fields are invalid")
    authority = policy.get("execution_authority")
    participants = policy.get("participants")
    if authority != "DISABLED" or not isinstance(participants, dict):
        raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable execution authority differs")
    observed: dict[str, str] = {}
    for name, component in components.items():
        if not isinstance(component, dict):
            raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable component identity is invalid")
        root = repository_root / str(component.get("root", ""))
        production_root = root / str(component.get("production_root", ""))
        if component.get("scope") == "runtime-dependency-closure":
            files = component.get("files")
            if not isinstance(files, list):
                raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable runtime closure is invalid")
            paths = [root / item for item in files]
            relatives = list(files)
        elif component.get("scope") == "python-production-tree":
            if not production_root.is_dir():
                raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable production root is unavailable")
            paths = sorted(p for p in production_root.rglob("*.py") if "__pycache__" not in p.parts)
            relatives = [p.relative_to(root).as_posix() for p in paths]
        else:
            raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable component scope is invalid")
        entries = []
        for relative, file_path in zip(relatives, paths):
            if not file_path.is_file():
                raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable component file is unavailable")
            entries.append({"path": relative, "sha256": _bytes_digest(file_path.read_bytes())})
        digest = canonical_digest(entries)
        if digest != component.get("digest"):
            raise LabValidationError("OPERATOR_INSTALLATION_INVALID", f"{name} installed bytes differ")
        observed[name] = digest
    report = DoctorReport(
        installation_id=str(value.get("installation_id")),
        manifest_digest=_bytes_digest(raw),
        execution_authority=authority,
        participant_states={str(k): str(v) for k, v in participants.items()},
        component_digests=observed,
        execution_ready=False,
    )
    return value, report


def validate_controller_identity(value: Any) -> str:
    if not isinstance(value, str) or not _CONTROLLER_RE.fullmatch(value):
        raise LabValidationError("OPERATOR_CONTROLLER_INVALID", "controller identity is invalid")
    return value


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()
