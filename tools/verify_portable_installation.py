from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

SCHEMA_VERSION = "acl-portable-installation-manifest:v1"
FILE_SET_SCHEMA = "acl-installed-file-set:v1"
REPORT_SCHEMA = "acl-portable-installation-report:v1"
_COMPONENTS = (
    "autonomous-worker-framework",
    "local-model-bench",
    "worker-lab",
)
_FRAMEWORK_FILES = (
    "tools/code_task.py",
    "tools/consumer_profile.py",
    "tools/dispatch_adapter.py",
    "tools/pydantic_ollama_worker.py",
    "tools/repository_handoff.py",
    "tools/repository_state.py",
    "tools/worker_result.py",
    "tools/worker_runtime.py",
)


class PortableIdentityError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def inspect_portable_installation(
    repository_root: Path,
    *,
    python_executable: Path | None = None,
) -> dict[str, Any]:
    root = _canonical_directory(repository_root)
    manifest_path = _canonical_file(root / "config" / "portable-installation-manifest.json")
    manifest = _load_manifest(manifest_path)

    policy = _object(
        manifest["activation_policy"],
        {"policy_id", "execution_authority", "participants"},
    )
    if policy["policy_id"] != "acl-installation-activation:v1":
        raise PortableIdentityError("activation policy identity differs")
    if policy["execution_authority"] != "DISABLED":
        raise PortableIdentityError("portable baseline must keep execution disabled")
    participants = _object(policy["participants"], set(_COMPONENTS))
    if participants != {
        "autonomous-worker-framework": "AVAILABLE",
        "local-model-bench": "ADVISORY",
        "worker-lab": "DEFERRED",
    }:
        raise PortableIdentityError("portable participant states differ")

    component_results: dict[str, Any] = {}
    components = _object(manifest["components"], set(_COMPONENTS))
    for name in _COMPONENTS:
        component_results[name] = _inspect_component(root, name, components[name])

    host_requirements = _object(manifest["host_requirements"], {"platform", "python"})
    if host_requirements["platform"] != "Windows":
        raise PortableIdentityError("portable host platform contract differs")
    if platform.system() != "Windows":
        raise PortableIdentityError("this qualification is for Windows hosts")

    python_requirement = _object(
        host_requirements["python"],
        {"major_minor", "implementation", "architecture"},
    )
    executable = _canonical_file(python_executable or Path(sys.executable))
    observed_python = {
        "path": str(executable),
        "sha256": bytes_digest(executable.read_bytes()),
        "version": platform.python_version(),
        "major_minor": ".".join(platform.python_version_tuple()[:2]),
        "implementation": platform.python_implementation(),
        "architecture": platform.machine(),
    }
    for field in ("major_minor", "implementation", "architecture"):
        if observed_python[field] != python_requirement[field]:
            raise PortableIdentityError(f"Python {field} differs from portable requirement")

    runtime_policy = _object(
        manifest["runtime_policy"],
        {"provider_identity", "portable_identity_requires_provider"},
    )
    if runtime_policy != {
        "provider_identity": "host-qualified-separately:v1",
        "portable_identity_requires_provider": False,
    }:
        raise PortableIdentityError("runtime-provider separation contract differs")

    integrity = _object(
        manifest["integrity"],
        {"algorithm", "component_digest_algorithm", "path_policy"},
    )
    if integrity != {
        "algorithm": "sha256",
        "component_digest_algorithm": FILE_SET_SCHEMA,
        "path_policy": "installation-relative-no-traversal:v1",
    }:
        raise PortableIdentityError("portable integrity policy differs")

    return {
        "schema_version": REPORT_SCHEMA,
        "installation_id": manifest["installation_id"],
        "manifest_sha256": bytes_digest(manifest_path.read_bytes()),
        "repository_root": str(root),
        "components": component_results,
        "host": {
            "platform": platform.system(),
            "python": observed_python,
        },
        "provider_runtime_qualified": False,
        "execution_authority": "DISABLED",
        "execution_ready": False,
    }


def _inspect_component(
    root: Path,
    name: str,
    raw: Any,
) -> dict[str, Any]:
    if name == "autonomous-worker-framework":
        component = _object(raw, {"root", "production_root", "scope", "digest", "files"})
    else:
        component = _object(raw, {"root", "production_root", "scope", "digest"})

    component_root = _contained_directory(root, _relative_path(component["root"]))
    production_root = _relative_path(component["production_root"])
    expected_digest = _digest(component["digest"])

    if component["scope"] == "runtime-dependency-closure":
        if name != "autonomous-worker-framework":
            raise PortableIdentityError("runtime closure is assigned to the wrong component")
        raw_files = component["files"]
        if not isinstance(raw_files, list):
            raise PortableIdentityError("framework file set must be an array")
        files = tuple(_relative_path(item).as_posix() for item in raw_files)
        if files != _FRAMEWORK_FILES:
            raise PortableIdentityError("framework runtime closure differs")
    elif component["scope"] == "python-production-tree":
        if name == "autonomous-worker-framework":
            raise PortableIdentityError("framework must use its bounded runtime closure")
        production = _contained_directory(component_root, production_root)
        files = tuple(
            sorted(
                path.relative_to(component_root).as_posix()
                for path in production.rglob("*.py")
                if "__pycache__" not in path.parts
            )
        )
        if not files:
            raise PortableIdentityError(f"{name} production tree is empty")
    else:
        raise PortableIdentityError("component scope is invalid")

    entries = []
    for relative in files:
        path = _contained_file(component_root, _relative_path(relative))
        entries.append({"path": relative, "sha256": bytes_digest(path.read_bytes())})
    actual_digest = canonical_digest(entries)
    if actual_digest != expected_digest:
        raise PortableIdentityError(
            f"{name} installed bytes differ: expected {expected_digest}, observed {actual_digest}"
        )
    return {
        "scope": component["scope"],
        "file_count": len(entries),
        "digest": actual_digest,
        "status": "MATCH",
    }


def _load_manifest(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PortableIdentityError("portable installation manifest is invalid") from exc
    root = _object(
        value,
        {
            "schema_version",
            "installation_id",
            "activation_policy",
            "components",
            "host_requirements",
            "runtime_policy",
            "integrity",
        },
    )
    if root["schema_version"] != SCHEMA_VERSION or root["installation_id"] != "acl-development":
        raise PortableIdentityError("portable installation identity differs")
    return root


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _object(value: Any, fields: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise PortableIdentityError("portable manifest fields are invalid")
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise PortableIdentityError("portable manifest text is invalid")
    return value


def _digest(value: Any) -> str:
    text = _text(value)
    if len(text) != 71 or not text.startswith("sha256:"):
        raise PortableIdentityError("portable digest is invalid")
    if any(char not in "0123456789abcdef" for char in text[7:]):
        raise PortableIdentityError("portable digest is invalid")
    return text


def _relative_path(value: Any) -> Path:
    text = _text(value)
    pure = PurePosixPath(text)
    if (
        pure.is_absolute()
        or pure.as_posix() != text
        or text == "."
        or ".." in pure.parts
        or ":" in pure.parts[0]
        or "\\" in text
    ):
        raise PortableIdentityError("portable path is invalid")
    return Path(*pure.parts)


def _canonical_directory(path: Path) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise PortableIdentityError("required directory is unavailable") from exc
    if not resolved.is_dir():
        raise PortableIdentityError("required directory is unavailable")
    _reject_path_indirection(resolved)
    return resolved


def _canonical_file(path: Path) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise PortableIdentityError("required file is unavailable") from exc
    if not resolved.is_file():
        raise PortableIdentityError("required file is unavailable")
    _reject_path_indirection(resolved)
    return resolved


def _contained_directory(root: Path, relative: Path) -> Path:
    candidate = _canonical_directory(root / relative)
    if not candidate.is_relative_to(root):
        raise PortableIdentityError("component directory escapes installation")
    return candidate


def _contained_file(root: Path, relative: Path) -> Path:
    candidate = _canonical_file(root / relative)
    if not candidate.is_relative_to(root):
        raise PortableIdentityError("component file escapes installation")
    return candidate


def _reject_path_indirection(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise PortableIdentityError("configured path is unavailable") from exc
        if current.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise PortableIdentityError("configured path uses path indirection")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify portable ACL component identity without executing a worker or provider."
    )
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        report = inspect_portable_installation(args.repository_root)
    except PortableIdentityError as exc:
        print(f"ERROR PORTABLE_IDENTITY_INVALID: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
