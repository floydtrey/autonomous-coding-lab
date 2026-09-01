from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .canonical import canonical_digest
from .errors import LabValidationError


SCHEMA_VERSION = "acl-installation-manifest:v2"
FILE_SET_SCHEMA = "acl-installed-file-set:v1"
_COMPONENTS = (
    "autonomous-worker-framework",
    "local-model-bench",
    "worker-lab",
)
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class FileIdentity:
    path: str
    digest: str


@dataclass(frozen=True)
class InstalledComponent:
    root: Path
    production_root: str
    scope: str
    installation_digest: str
    files: tuple[FileIdentity, ...]
    entrypoints: Mapping[str, str]


@dataclass(frozen=True)
class RuntimeIdentity:
    path: Path
    digest: str
    version: str
    implementation: str | None = None
    architecture: str | None = None


@dataclass(frozen=True)
class InstallationManifest:
    path: Path
    installation_root: Path
    installation_id: str
    execution_authority: str
    participants: Mapping[str, str]
    components: Mapping[str, InstalledComponent]
    python: RuntimeIdentity
    codex: RuntimeIdentity


def load_installation_manifest(
    path: Path | None = None,
    *,
    verify_files: bool = True,
) -> InstallationManifest:
    manifest_path = (path or Path(__file__).resolve().parents[3] / "config" / "installation-manifest.json")
    try:
        encoded = manifest_path.read_bytes()
        raw = json.loads(encoded.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installation manifest is invalid") from exc
    data = _object(raw, {
        "schema_version", "installation_id", "source_provenance", "activation_policy",
        "components", "runtimes", "integrity",
    })
    if data["schema_version"] != SCHEMA_VERSION or data["installation_id"] != "acl-development":
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installation manifest version or identity differs")
    installation_root = _canonical_unlinked(manifest_path.parent.parent)
    _parse_source_provenance(data["source_provenance"])
    execution_authority, participants = _parse_activation_policy(data["activation_policy"])
    components = _parse_components(data["components"], installation_root, verify_files=verify_files)
    python, codex = _parse_runtimes(data["runtimes"], verify_files=verify_files)
    integrity = _object(data["integrity"], {"algorithm", "file_set_algorithm", "path_policy"})
    if integrity != {
        "algorithm": "sha256",
        "file_set_algorithm": FILE_SET_SCHEMA,
        "path_policy": "installation-relative-no-traversal:v1",
    }:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installation integrity policy differs")
    return InstallationManifest(
        manifest_path, installation_root, data["installation_id"], execution_authority,
        participants, components, python, codex,
    )


def require_execution_enabled(manifest: InstallationManifest) -> None:
    if (
        manifest.execution_authority != "ENABLED"
        or manifest.participants.get("worker-lab") != "ACTIVE"
        or manifest.participants.get("autonomous-worker-framework") != "ACTIVE"
    ):
        raise LabValidationError("INTEGRATION_EXECUTION_DISABLED", "installation policy disables worker execution")


def verify_component_tree(component: InstalledComponent, installation_root: Path) -> None:
    component_root = _contained_directory(installation_root, component.root)
    declared_paths = tuple(item.path for item in component.files)
    if component.scope == "python-production-tree":
        production = _contained_directory(component_root, Path(component.production_root))
        actual_paths = tuple(sorted(
            path.relative_to(component_root).as_posix()
            for path in production.rglob("*.py")
            if "__pycache__" not in path.parts
        ))
        if actual_paths != declared_paths:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installed production file set differs")
    for item in component.files:
        candidate = _contained_file(component_root, Path(*PurePosixPath(item.path).parts))
        if _bytes_digest(candidate.read_bytes()) != item.digest:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installed component content differs")


def _parse_source_provenance(value: Any) -> None:
    sources = _object(value, set(_COMPONENTS))
    for name in _COMPONENTS:
        item = _object(sources[name], {"repository_id", "source_commit", "source_tree"})
        if item["repository_id"] != name or not _SHA_RE.fullmatch(str(item["source_commit"])) or not _SHA_RE.fullmatch(str(item["source_tree"])):
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "source provenance is invalid")


def _parse_activation_policy(value: Any) -> tuple[str, Mapping[str, str]]:
    policy = _object(value, {"policy_id", "execution_authority", "participants"})
    if policy["policy_id"] != "acl-installation-activation:v1":
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installation activation policy differs")
    authority = policy["execution_authority"]
    if authority not in {"DISABLED", "ENABLED"}:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "execution authority is invalid")
    participants = _object(policy["participants"], set(_COMPONENTS))
    allowed = {
        "autonomous-worker-framework": {"ACTIVE", "AVAILABLE"},
        "worker-lab": {"ACTIVE", "DEFERRED"},
        "local-model-bench": {"ADVISORY"},
    }
    if any(participants[name] not in allowed[name] for name in _COMPONENTS):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installation participant state is invalid")
    return authority, participants


def _parse_components(
    value: Any,
    installation_root: Path,
    *,
    verify_files: bool,
) -> Mapping[str, InstalledComponent]:
    raw_components = _object(value, set(_COMPONENTS))
    parsed: dict[str, InstalledComponent] = {}
    for name in _COMPONENTS:
        raw = _object(raw_components[name], {"root", "production_root", "installed_tree", "entrypoints"})
        root = Path(*PurePosixPath(_relative_path(raw["root"])).parts)
        production_root = _relative_path(raw["production_root"])
        tree = _object(raw["installed_tree"], {"schema_version", "scope", "digest", "files"})
        if tree["schema_version"] != FILE_SET_SCHEMA or tree["scope"] not in {
            "runtime-dependency-closure", "python-production-tree",
        }:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installed file-set contract differs")
        files_raw = tree["files"]
        if not isinstance(files_raw, list) or not files_raw:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installed file set is empty")
        files = tuple(_parse_file_identity(item) for item in files_raw)
        paths = tuple(item.path for item in files)
        if paths != tuple(sorted(set(paths))) or canonical_digest([{"path": item.path, "sha256": item.digest} for item in files]) != tree["digest"]:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installed file-set digest differs")
        prefix = PurePosixPath(production_root)
        if any(PurePosixPath(item.path).parts[:len(prefix.parts)] != prefix.parts for item in files):
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installed file escapes production root")
        entrypoints_raw = _object(raw["entrypoints"], {"worker-lab-adapter"} if name == "autonomous-worker-framework" else set())
        entrypoints = {key: _relative_path(item) for key, item in entrypoints_raw.items()}
        component = InstalledComponent(root, production_root, tree["scope"], tree["digest"], files, entrypoints)
        if name == "autonomous-worker-framework":
            if component.scope != "runtime-dependency-closure" or paths != (
                "tools/codex_runtime.py", "tools/worker_lab_adapter.py",
            ) or entrypoints["worker-lab-adapter"] != "tools/worker_lab_adapter.py":
                raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "framework runtime closure is incomplete")
        elif component.scope != "python-production-tree":
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "component production-tree scope differs")
        if verify_files:
            verify_component_tree(component, installation_root)
        parsed[name] = component
    return parsed


def _parse_runtimes(value: Any, *, verify_files: bool) -> tuple[RuntimeIdentity, RuntimeIdentity]:
    runtimes = _object(value, {"python", "codex"})
    python_raw = _object(runtimes["python"], {"path", "sha256", "version", "implementation", "architecture"})
    codex_raw = _object(runtimes["codex"], {"path", "sha256", "version"})
    python = RuntimeIdentity(
        _absolute_path(python_raw["path"]), _digest(python_raw["sha256"]), _text(python_raw["version"]),
        _text(python_raw["implementation"]), _text(python_raw["architecture"]),
    )
    codex = RuntimeIdentity(
        _absolute_path(codex_raw["path"]), _digest(codex_raw["sha256"]), _text(codex_raw["version"]),
    )
    if verify_files:
        for runtime in (python, codex):
            path = _canonical_unlinked(runtime.path)
            if not path.is_file() or _bytes_digest(path.read_bytes()) != runtime.digest:
                raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installed runtime identity differs")
    return python, codex


def _parse_file_identity(value: Any) -> FileIdentity:
    item = _object(value, {"path", "sha256"})
    return FileIdentity(_relative_path(item["path"]), _digest(item["sha256"]))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for name, item in pairs:
        if name in value:
            raise ValueError("duplicate JSON object key")
        value[name] = item
    return value


def _object(value: Any, fields: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installation manifest fields are invalid")
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installation manifest text is invalid")
    return value


def _digest(value: Any) -> str:
    text = _text(value)
    if not _DIGEST_RE.fullmatch(text):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installation digest is invalid")
    return text


def _relative_path(value: Any) -> str:
    text = _text(value)
    path = PurePosixPath(text)
    if path.is_absolute() or path.as_posix() != text or text == "." or ".." in path.parts or ":" in path.parts[0] or "\\" in text:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "installation path is invalid")
    return text


def _absolute_path(value: Any) -> Path:
    text = _text(value)
    path = Path(text)
    if not path.is_absolute() or ".." in path.parts:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "runtime path is invalid")
    return path


def _canonical_unlinked(path: Path) -> Path:
    if not path.is_absolute() or not path.exists():
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "configured path is unavailable")
    resolved = path.resolve(strict=True)
    if not _path_equal(resolved, path):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "configured path is substituted")
    current = Path(resolved.anchor)
    for part in resolved.parts[1:]:
        current /= part
        attributes = getattr(os.lstat(current), "st_file_attributes", 0)
        if attributes & 0x400:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "configured path uses a reparse point")
    return resolved


def _contained_directory(root: Path, relative: Path) -> Path:
    candidate = _canonical_unlinked(root / relative)
    if not candidate.is_dir() or not candidate.is_relative_to(root):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "component root escapes installation")
    return candidate


def _contained_file(root: Path, relative: Path) -> Path:
    candidate = _canonical_unlinked(root / relative)
    if not candidate.is_file() or not candidate.is_relative_to(root):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "component file escapes installation")
    return candidate


def _path_equal(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(os.path.normpath(str(right)))


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()
