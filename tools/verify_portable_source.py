from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

SCHEMA_VERSION = "acl-portable-source-manifest:v2"
REPORT_SCHEMA = "acl-portable-source-report:v2"
SOURCE_IDENTITY_ID = "acl-runtime-source:v2"
FILE_SET_SCHEMA = "acl-source-file-set:v2"
SEPARATION_POLICY = {
    "host_qualification": "separate-evidence",
    "provider_capability_qualification": "separate-evidence",
    "local_activation": "local-operator-state",
    "task_authorization": "worker-lab-invocation-v3",
}
INTEGRITY_POLICY = {
    "algorithm": "sha256",
    "component_digest_algorithm": FILE_SET_SCHEMA,
    "path_policy": "checkout-relative-no-traversal:v1",
}
_FRAMEWORK_FILES = (
    "tools/code_task.py",
    "tools/consumer_profile.py",
    "tools/dispatch_adapter.py",
    "tools/pi_adapter.mjs",
    "tools/pi_adapter_main.mjs",
    "tools/pi_file_bridge.py",
    "tools/pi_file_tools.mjs",
    "tools/pi_protocol.mjs",
    "tools/pydantic_ollama_worker.py",
    "tools/repository_handoff.py",
    "tools/repository_state.py",
    "tools/worker_result.py",
    "tools/worker_runtime.py",
)


class PortableSourceError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def canonical_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def inspect_portable_source(checkout_root: Path) -> Mapping[str, Any]:
    root = _canonical_directory(checkout_root)
    manifest_path = _canonical_file(root / "config" / "portable-source-manifest.json")
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PortableSourceError("portable source manifest is not canonical UTF-8 JSON") from exc
    _validate_manifest(manifest)
    components = {
        name: _inspect_component(root, name, raw)
        for name, raw in sorted(manifest["components"].items())
    }
    return {
        "schema_version": REPORT_SCHEMA,
        "source_identity_id": SOURCE_IDENTITY_ID,
        "manifest_sha256": bytes_digest(manifest_bytes),
        "components": components,
        "separation_policy": dict(SEPARATION_POLICY),
    }


def _validate_manifest(value: Any) -> None:
    manifest = _object(value, {"schema_version", "source_identity_id", "components", "separation_policy", "integrity"})
    if manifest["schema_version"] != SCHEMA_VERSION or manifest["source_identity_id"] != SOURCE_IDENTITY_ID:
        raise PortableSourceError("portable source manifest identity differs")
    if _object(manifest["separation_policy"], set(SEPARATION_POLICY)) != SEPARATION_POLICY:
        raise PortableSourceError("portable source separation policy differs")
    if _object(manifest["integrity"], set(INTEGRITY_POLICY)) != INTEGRITY_POLICY:
        raise PortableSourceError("portable source integrity policy differs")
    components = _object(manifest["components"], {"autonomous-worker-framework", "local-model-bench", "worker-lab"})
    for name, raw in components.items():
        component = _object(raw, {"root", "production_root", "scope", "digest"}, allow_optional={"files"})
        _relative(component["root"], f"{name} root")
        _relative(component["production_root"], f"{name} production root")
        _digest(component["digest"], f"{name} digest")
        if name == "autonomous-worker-framework":
            if component["scope"] != "runtime-dependency-closure" or tuple(component.get("files", ())) != _FRAMEWORK_FILES:
                raise PortableSourceError("framework source closure differs")
        elif component["scope"] != "python-production-tree" or "files" in component:
            raise PortableSourceError(f"{name} source scope differs")


def _inspect_component(root: Path, name: str, raw: Mapping[str, Any]) -> Mapping[str, Any]:
    component_root = _inside(root, raw["root"], f"{name} root")
    production_root = _inside(component_root, raw["production_root"], f"{name} production root")
    if raw["scope"] == "runtime-dependency-closure":
        files = tuple(raw["files"])
    elif raw["scope"] == "python-production-tree":
        if not production_root.is_dir():
            raise PortableSourceError(f"{name} production root is unavailable")
        files = tuple(sorted(p.relative_to(component_root).as_posix() for p in production_root.rglob("*.py") if "__pycache__" not in p.parts))
    else:
        raise PortableSourceError(f"{name} source scope is unsupported")
    if not files or len(set(files)) != len(files):
        raise PortableSourceError(f"{name} source file set is empty or ambiguous")
    entries = []
    for relative in files:
        path = _inside(component_root, relative, f"{name} source file")
        if not path.is_file() or path.is_symlink():
            raise PortableSourceError(f"{name} source file is unavailable or indirect")
        entries.append({"path": relative, "sha256": bytes_digest(path.read_bytes())})
    observed = canonical_digest(entries)
    expected = _digest(raw["digest"], f"{name} digest")
    if observed != expected:
        raise PortableSourceError(f"{name} source bytes differ")
    return {"scope": raw["scope"], "file_count": len(files), "digest": observed, "status": "MATCH"}


def _object(value: Any, required: set[str], *, allow_optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PortableSourceError("portable source manifest object is invalid")
    optional = allow_optional or set()
    if not required.issubset(value) or set(value) - required - optional:
        raise PortableSourceError("portable source manifest fields are missing or unknown")
    return value


def _relative(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise PortableSourceError(f"{name} is invalid")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise PortableSourceError(f"{name} is not checkout-relative")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re_full_digest(value):
        raise PortableSourceError(f"{name} is invalid")
    return value


def re_full_digest(value: str) -> bool:
    return len(value) == 71 and value.startswith("sha256:") and all(c in "0123456789abcdef" for c in value[7:])


def _canonical_directory(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_dir():
        raise PortableSourceError("checkout root is not a directory")
    return resolved


def _canonical_file(path: Path) -> Path:
    if path.is_symlink():
        raise PortableSourceError("portable source manifest must not be a symlink")
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise PortableSourceError("portable source manifest is unavailable")
    return resolved


def _inside(base: Path, relative: str, name: str) -> Path:
    _relative(relative, name)
    target = base.joinpath(*PurePosixPath(relative).parts)
    if target.is_symlink():
        raise PortableSourceError(f"{name} must not be a symlink")
    try:
        resolved = target.resolve(strict=True)
    except OSError as exc:
        raise PortableSourceError(f"{name} is unavailable") from exc
    try:
        resolved.relative_to(base.resolve(strict=True))
    except ValueError as exc:
        raise PortableSourceError(f"{name} escapes its source root") from exc
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify ACL portable source identity without host/provider/activation qualification.")
    parser.add_argument("--checkout-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        report = inspect_portable_source(args.checkout_root)
    except PortableSourceError as exc:
        print(f"ERROR PORTABLE_SOURCE_INVALID: {exc}")
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
