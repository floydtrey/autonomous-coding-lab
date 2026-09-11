from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError

SOURCE_DOCTOR_SCHEMA = "worker-lab-source-doctor:v3"
SOURCE_MANIFEST_SCHEMA = "acl-portable-source-manifest:v2"
_SOURCE_ID = "acl-runtime-source:v2"
_SEPARATION = {
    "host_qualification": "separate-evidence",
    "provider_capability_qualification": "separate-evidence",
    "local_activation": "local-operator-state",
    "task_authorization": "worker-lab-invocation-v3",
}
_CONTROLLER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


@dataclass(frozen=True)
class SourceDoctorReport:
    source_identity_id: str
    manifest_digest: str
    separation_policy: Mapping[str, str]
    component_digests: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SOURCE_DOCTOR_SCHEMA,
            "source_identity_id": self.source_identity_id,
            "manifest_digest": self.manifest_digest,
            "separation_policy": dict(sorted(self.separation_policy.items())),
            "component_digests": dict(sorted(self.component_digests.items())),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


def inspect_source_identity(path: Path | None = None) -> tuple[Mapping[str, Any], SourceDoctorReport]:
    checkout_root = Path(__file__).resolve().parents[3]
    manifest_path = checkout_root / "config" / "portable-source-manifest.json" if path is None else path
    if manifest_path.is_dir():
        manifest_path = manifest_path / "config" / "portable-source-manifest.json"
    try:
        raw = manifest_path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LabValidationError("OPERATOR_SOURCE_IDENTITY_INVALID", "portable source manifest is unavailable") from exc
    if not isinstance(value, dict) or set(value) != {"schema_version", "source_identity_id", "components", "separation_policy", "integrity"}:
        raise LabValidationError("OPERATOR_SOURCE_IDENTITY_INVALID", "portable source manifest fields are invalid")
    if value.get("schema_version") != SOURCE_MANIFEST_SCHEMA or value.get("source_identity_id") != _SOURCE_ID:
        raise LabValidationError("OPERATOR_SOURCE_IDENTITY_INVALID", "portable source manifest identity differs")
    if value.get("separation_policy") != _SEPARATION:
        raise LabValidationError("OPERATOR_SOURCE_IDENTITY_INVALID", "portable source separation policy differs")
    components = value.get("components")
    if not isinstance(components, dict):
        raise LabValidationError("OPERATOR_SOURCE_IDENTITY_INVALID", "portable source components are invalid")
    observed: dict[str, str] = {}
    for name, component in components.items():
        if not isinstance(component, dict):
            raise LabValidationError("OPERATOR_SOURCE_IDENTITY_INVALID", "portable component identity is invalid")
        root = checkout_root / str(component.get("root", ""))
        production_root = root / str(component.get("production_root", ""))
        if component.get("scope") == "runtime-dependency-closure":
            files = component.get("files")
            if not isinstance(files, list) or not files:
                raise LabValidationError("OPERATOR_SOURCE_IDENTITY_INVALID", "portable source closure is invalid")
            relatives = list(files)
            paths = [root / item for item in relatives]
        elif component.get("scope") == "python-production-tree":
            if not production_root.is_dir():
                raise LabValidationError("OPERATOR_SOURCE_IDENTITY_INVALID", "portable production root is unavailable")
            paths = sorted(p for p in production_root.rglob("*.py") if "__pycache__" not in p.parts)
            relatives = [p.relative_to(root).as_posix() for p in paths]
        else:
            raise LabValidationError("OPERATOR_SOURCE_IDENTITY_INVALID", "portable source scope is invalid")
        entries = []
        for relative, file_path in zip(relatives, paths):
            if not file_path.is_file() or file_path.is_symlink():
                raise LabValidationError("OPERATOR_SOURCE_IDENTITY_INVALID", "portable source file is unavailable or indirect")
            entries.append({"path": relative, "sha256": _bytes_digest(file_path.read_bytes())})
        digest = canonical_digest(entries)
        if digest != component.get("digest"):
            raise LabValidationError("OPERATOR_SOURCE_IDENTITY_INVALID", f"{name} source bytes differ")
        observed[name] = digest
    report = SourceDoctorReport(
        source_identity_id=_SOURCE_ID,
        manifest_digest=_bytes_digest(raw),
        separation_policy=_SEPARATION,
        component_digests=observed,
    )
    return value, report


def validate_controller_identity(value: Any) -> str:
    if not isinstance(value, str) or not _CONTROLLER_RE.fullmatch(value):
        raise LabValidationError("OPERATOR_CONTROLLER_INVALID", "controller identity is invalid")
    return value


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()
