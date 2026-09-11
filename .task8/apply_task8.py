from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{label}: expected one occurrence, found {text.count(old)}")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Portable source identity V2: source bytes only. No host or activation state.
# ---------------------------------------------------------------------------
old_manifest = ROOT / "config/portable-installation-manifest.json"
if old_manifest.exists():
    old_manifest.unlink()

manifest = {
    "schema_version": "acl-portable-source-manifest:v2",
    "source_identity_id": "acl-runtime-source:v2",
    "components": {
        "autonomous-worker-framework": {
            "root": "components/autonomous-worker-framework",
            "production_root": "tools",
            "scope": "runtime-dependency-closure",
            "files": [
                "tools/code_task.py",
                "tools/consumer_profile.py",
                "tools/dispatch_adapter.py",
                "tools/local_git_publisher.py",
                "tools/local_validate.py",
                "tools/pydantic_ollama_worker.py",
                "tools/repository_handoff.py",
                "tools/repository_state.py",
            ],
            "digest": "sha256:" + "0" * 64,
        },
        "local-model-bench": {
            "root": "components/local-model-bench",
            "production_root": "src/localbench",
            "scope": "python-production-tree",
            "digest": "sha256:" + "0" * 64,
        },
        "worker-lab": {
            "root": "components/worker-lab",
            "production_root": "worker_lab",
            "scope": "python-production-tree",
            "digest": "sha256:" + "0" * 64,
        },
    },
    "separation_policy": {
        "host_qualification": "separate-evidence",
        "provider_capability_qualification": "separate-evidence",
        "local_activation": "local-operator-state",
        "task_authorization": "worker-lab-invocation-v3",
    },
    "integrity": {
        "algorithm": "sha256",
        "component_digest_algorithm": "acl-source-file-set:v2",
        "path_policy": "checkout-relative-no-traversal:v1",
    },
}
write("config/portable-source-manifest.json", json.dumps(manifest, indent=2) + "\n")

old_verifier = ROOT / "tools/verify_portable_installation.py"
if old_verifier.exists():
    old_verifier.unlink()

VERIFIER = r'''from __future__ import annotations

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
    "tools/local_git_publisher.py",
    "tools/local_validate.py",
    "tools/pydantic_ollama_worker.py",
    "tools/repository_handoff.py",
    "tools/repository_state.py",
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
        component = _object(raw, {"root", "production_root", "scope", "digest", "files"}, allow_optional={"files"})
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
'''
write("tools/verify_portable_source.py", VERIFIER)

old_root_test = ROOT / "tests/test_portable_installation.py"
if old_root_test.exists():
    old_root_test.unlink()

ROOT_TEST = r'''import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "verify_portable_source.py"
MANIFEST_PATH = ROOT / "config" / "portable-source-manifest.json"
SPEC = importlib.util.spec_from_file_location("verify_portable_source", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_portable_source_verifies_on_non_windows_ci_without_host_claims() -> None:
    report = MODULE.inspect_portable_source(ROOT)
    assert report["schema_version"] == "acl-portable-source-report:v2"
    assert all(item["status"] == "MATCH" for item in report["components"].values())
    encoded = json.dumps(report, sort_keys=True)
    for forbidden in ("execution_authority", "host_requirements", "python_executable", "provider_runtime", "execution_ready"):
        assert forbidden not in encoded


def test_manifest_is_source_only_and_strict() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert set(manifest) == {"schema_version", "source_identity_id", "components", "separation_policy", "integrity"}
    assert manifest["schema_version"] == MODULE.SCHEMA_VERSION
    assert manifest["separation_policy"] == MODULE.SEPARATION_POLICY
    assert "activation_policy" not in manifest
    assert "host_requirements" not in manifest
    assert tuple(manifest["components"]["autonomous-worker-framework"]["files"]) == MODULE._FRAMEWORK_FILES


def test_python_tree_identity_changes_when_source_bytes_change(tmp_path: Path) -> None:
    component_root = tmp_path / "component"
    production = component_root / "src"
    production.mkdir(parents=True)
    source = production / "worker.py"
    source.write_bytes(b"print('a')\n")
    relative = "src/worker.py"
    expected = MODULE.canonical_digest([{"path": relative, "sha256": MODULE.bytes_digest(source.read_bytes())}])
    raw = {"root": "component", "production_root": "src", "scope": "python-production-tree", "digest": expected}
    result = MODULE._inspect_component(tmp_path, "worker-lab", raw)
    assert result["status"] == "MATCH"
    source.write_bytes(b"print('b')\n")
    with pytest.raises(MODULE.PortableSourceError):
        MODULE._inspect_component(tmp_path, "worker-lab", raw)
'''
write("tests/test_portable_source.py", ROOT_TEST)

# ---------------------------------------------------------------------------
# Provider qualification: qualification evidence is not activation state.
# ---------------------------------------------------------------------------
pq_path = "components/worker-lab/worker_lab/provider_qualification.py"
pq = read(pq_path)
pq = pq.replace('INSTALLATION_OBSERVATION_SCHEMA = "worker-lab-provider-installation-observation:v1"', 'INSTALLATION_OBSERVATION_SCHEMA = "worker-lab-provider-installation-observation:v2"')
pq = pq.replace('INSTALLATION_OBSERVATION_IDENTITY_SCHEMA = "worker-lab-provider-installation-observation-identity:v1"', 'INSTALLATION_OBSERVATION_IDENTITY_SCHEMA = "worker-lab-provider-installation-observation-identity:v2"')
pq = pq.replace('CAPABILITY_QUALIFICATION_SCHEMA = "worker-lab-provider-capability-qualification:v1"', 'CAPABILITY_QUALIFICATION_SCHEMA = "worker-lab-provider-capability-qualification:v2"')
pq = pq.replace('CAPABILITY_QUALIFICATION_IDENTITY_SCHEMA = "worker-lab-provider-capability-qualification-identity:v1"', 'CAPABILITY_QUALIFICATION_IDENTITY_SCHEMA = "worker-lab-provider-capability-qualification-identity:v2"')
pq = pq.replace('    execution_authority: str\n\n    def to_dict(self)', '    def to_dict(self)', 1)
pq = pq.replace('            _exact(value["execution_authority"], "DISABLED", "execution_authority"),\n', '', 1)
pq = pq.replace('    execution_authority: str\n    capability_qualified: bool\n    execution_ready: bool\n', '    capability_qualified: bool\n')
pq = pq.replace('            _exact(value["execution_authority"], "DISABLED", "execution_authority"),\n            _true(value["capability_qualified"], "capability_qualified"),\n            _false(value["execution_ready"], "execution_ready"),\n', '            _true(value["capability_qualified"], "capability_qualified"),\n')
pq = pq.replace('    repository_root: Path,\n', '', 1)
old_auth = '''    repository_root = _real_directory(repository_root, "repository root")\n    if _portable_execution_authority(repository_root) != "DISABLED":\n        raise LabValidationError(\n            "PROVIDER_QUALIFICATION_AUTHORITY_INVALID",\n            "provider installation observation requires execution authority to remain disabled",\n        )\n'''
if old_auth not in pq:
    raise SystemExit("provider qualification source-authority block missing")
pq = pq.replace(old_auth, '', 1)
pq = pq.replace('        execution_authority="DISABLED",\n', '', 1)
pq = pq.replace('        qualification_version=1,\n', '        qualification_version=2,\n', 1)
pq = pq.replace('        execution_authority="DISABLED",\n        capability_qualified=True,\n        execution_ready=False,\n', '        capability_qualified=True,\n', 1)
pq = pq.replace('        record.provider_kind == candidate.provider_kind,\n        record.execution_authority == "DISABLED",\n', '        record.provider_kind == candidate.provider_kind,\n')
pq = pq.replace('        record.qualification_version != 1\n', '        record.qualification_version != 2\n')
pq = pq.replace('        or record.context_fixture_id != CONTEXT_CAPABILITY_FIXTURE_ID\n        or record.execution_authority != "DISABLED"\n        or record.capability_qualified is not True\n        or record.execution_ready is not False\n', '        or record.context_fixture_id != CONTEXT_CAPABILITY_FIXTURE_ID\n        or record.capability_qualified is not True\n')
pq = re.sub(r'\n\ndef _portable_execution_authority\(repository_root: Path\) -> str:\n.*?\n\ndef _provider_cli_version', '\n\ndef _provider_cli_version', pq, count=1, flags=re.S)
pq = pq.replace('    repository_root = Path(__file__).resolve().parents[3]\n', '', 1)
pq = pq.replace('            repository_root=repository_root,\n', '', 1)
write(pq_path, pq)

pb_path = "components/worker-lab/worker_lab/provider_binding.py"
pb = read(pb_path)
pb = pb.replace('        or qualification.effective_context_tokens < settings.requested_context_tokens\n        or qualification.execution_authority != "DISABLED"\n        or qualification.capability_qualified is not True\n        or qualification.execution_ready is not False\n', '        or qualification.effective_context_tokens < settings.requested_context_tokens\n        or qualification.capability_qualified is not True\n')
write(pb_path, pb)

fixture_path = "components/worker-lab/tests/provider_capability_fixture.py"
fixture = read(fixture_path)
fixture = fixture.replace('        "execution_authority": "DISABLED",\n', '', 1)
fixture = fixture.replace('        "qualification_version": 1,\n', '        "qualification_version": 2,\n', 1)
fixture = fixture.replace('        "execution_authority": "DISABLED",\n        "capability_qualified": True,\n        "execution_ready": False,\n', '        "capability_qualified": True,\n')
write(fixture_path, fixture)

pqt_path = "components/worker-lab/tests/test_provider_qualification.py"
pqt = read(pqt_path)
pqt = pqt.replace('import json\n', '', 1)
pqt = re.sub(r'\n\ndef _repository\(tmp_path: Path, \*, authority: str = "DISABLED"\) -> Path:\n.*?\n\ndef _executable', '\n\ndef _executable', pqt, count=1, flags=re.S)
pqt = pqt.replace('    root = _repository(tmp_path)\n', '', 1)
pqt = pqt.replace('        repository_root=root,\n', '', 1)
pqt = pqt.replace('    assert qualified.execution_ready is False\n', '')
write(pqt_path, pqt)

# ---------------------------------------------------------------------------
# Worker Lab source identity consumers.
# ---------------------------------------------------------------------------
operator_path = "components/worker-lab/worker_lab/operator_control.py"
OPERATOR = r'''from __future__ import annotations

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
'''
write(operator_path, OPERATOR)

service_path = "components/worker-lab/worker_lab/service_runtime_v3.py"
service = read(service_path)
service = service.replace('_PORTABLE_SCHEMA = "acl-portable-installation-manifest:v1"', '_SOURCE_SCHEMA = "acl-portable-source-manifest:v2"')
service = service.replace('manifest_path = root / "config" / "portable-installation-manifest.json"', 'manifest_path = root / "config" / "portable-source-manifest.json"')
old = '''    try:\n        authority = manifest["activation_policy"]["execution_authority"]\n        components = manifest["components"]\n        worker = components["worker-lab"]\n        framework = components["autonomous-worker-framework"]\n    except (KeyError, TypeError) as exc:\n        raise LabValidationError(\n            "INTEGRATION_V3_SOURCE_IDENTITY_INVALID",\n            "portable source manifest fields are invalid",\n        ) from exc\n    if manifest.get("schema_version") != _PORTABLE_SCHEMA or authority != "DISABLED":\n        raise LabValidationError(\n            "INTEGRATION_V3_SOURCE_IDENTITY_INVALID",\n            "current source identity must remain on the DISABLED portable baseline",\n        )\n'''
new = '''    try:\n        components = manifest["components"]\n        worker = components["worker-lab"]\n        framework = components["autonomous-worker-framework"]\n        separation = manifest["separation_policy"]\n    except (KeyError, TypeError) as exc:\n        raise LabValidationError(\n            "INTEGRATION_V3_SOURCE_IDENTITY_INVALID",\n            "portable source manifest fields are invalid",\n        ) from exc\n    expected_separation = {\n        "host_qualification": "separate-evidence",\n        "provider_capability_qualification": "separate-evidence",\n        "local_activation": "local-operator-state",\n        "task_authorization": "worker-lab-invocation-v3",\n    }\n    if (\n        manifest.get("schema_version") != _SOURCE_SCHEMA\n        or manifest.get("source_identity_id") != "acl-runtime-source:v2"\n        or separation != expected_separation\n    ):\n        raise LabValidationError(\n            "INTEGRATION_V3_SOURCE_IDENTITY_INVALID",\n            "current portable source identity differs",\n        )\n'''
service = replace_once(service, old, new, "service source identity block")
write(service_path, service)

app_path = "components/worker-lab/worker_lab/application_service.py"
app = read(app_path)
app = app.replace('    DoctorReport,\n    inspect_installation,\n', '    SourceDoctorReport,\n    inspect_source_identity,\n')
app = app.replace('INSTALLATION_STATUS_SCHEMA = "worker-lab-service-installation-status:v1"', 'SOURCE_STATUS_SCHEMA = "worker-lab-service-source-status:v1"')
app = app.replace('class InstallationStatusDTO:\n    doctor: DoctorReport', 'class SourceStatusDTO:\n    doctor: SourceDoctorReport')
app = app.replace('"schema_version": INSTALLATION_STATUS_SCHEMA,\n            "installation": self.doctor.to_dict(),', '"schema_version": SOURCE_STATUS_SCHEMA,\n            "source_identity": self.doctor.to_dict(),')
app = app.replace('class HealthDTO:\n    doctor: DoctorReport', 'class HealthDTO:\n    doctor: SourceDoctorReport')
app = app.replace('"execution_ready": self.doctor.execution_ready,', '"execution_ready": False,')
app = app.replace('    def installation_status(self) -> InstallationStatusDTO:\n        _, report = inspect_installation()\n        return InstallationStatusDTO(report)\n', '    def source_status(self) -> SourceStatusDTO:\n        _, report = inspect_source_identity()\n        return SourceStatusDTO(report)\n')
app = app.replace('        _, report = inspect_installation()\n', '        _, report = inspect_source_identity()\n', 1)
if 'inspect_installation' in app or 'InstallationStatusDTO' in app or 'INSTALLATION_STATUS_SCHEMA' in app:
    raise SystemExit("application service retains installation identity symbols")
write(app_path, app)

cli_path = "components/worker-lab/worker_lab/cli.py"
cli = read(cli_path)
cli = cli.replace('from .operator_control import inspect_installation', 'from .operator_control import inspect_source_identity')
cli = cli.replace('    command = commands.add_parser("installation-status")\n    command.set_defaults(handler=_service_installation_status)\n', '    command = commands.add_parser("source-status")\n    command.set_defaults(handler=_service_source_status)\n')
cli = cli.replace('def _service_installation_status(args: argparse.Namespace) -> str:\n    return _service(args).installation_status().to_json()\n', 'def _service_source_status(args: argparse.Namespace) -> str:\n    return _service(args).source_status().to_json()\n')
cli = cli.replace('    _, report = inspect_installation()\n', '    _, report = inspect_source_identity()\n')
write(cli_path, cli)

operator_test_path = "components/worker-lab/tests/test_operator_control.py"
OPERATOR_TEST = r'''import json

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.operator_control import inspect_source_identity, validate_controller_identity


def test_doctor_verifies_portable_source_without_claiming_activation_or_host_qualification():
    manifest, report = inspect_source_identity()
    value = json.loads(report.to_json())
    assert value["schema_version"] == "worker-lab-source-doctor:v3"
    assert value["source_identity_id"] == manifest["source_identity_id"]
    assert value["separation_policy"] == manifest["separation_policy"]
    assert value["component_digests"]["worker-lab"] == manifest["components"]["worker-lab"]["digest"]
    assert value["component_digests"]["autonomous-worker-framework"] == manifest["components"]["autonomous-worker-framework"]["digest"]
    encoded = json.dumps(value, sort_keys=True)
    assert "execution_authority" not in encoded
    assert "participant_states" not in encoded


def test_controller_identity_is_strict_and_provider_neutral():
    assert validate_controller_identity("trusted-controller") == "trusted-controller"
    for invalid in ("", "a", "bad controller", "../controller"):
        with pytest.raises(LabValidationError) as error:
            validate_controller_identity(invalid)
        assert error.value.code == "OPERATOR_CONTROLLER_INVALID"
'''
write(operator_test_path, OPERATOR_TEST)

cli_test_path = "components/worker-lab/tests/test_cli.py"
ct = read(cli_test_path)
old = '''def test_doctor_reports_disabled_installation_without_execution(capsys) -> None:\n    assert main(["doctor"]) == 0\n    report = json.loads(capsys.readouterr().out)\n    assert report["schema_version"] == "worker-lab-installation-doctor:v2"\n    assert report["execution_authority"] == "DISABLED"\n    assert report["execution_ready"] is False\n'''
new = '''def test_doctor_reports_source_identity_without_activation_claims(capsys) -> None:\n    assert main(["doctor"]) == 0\n    report = json.loads(capsys.readouterr().out)\n    assert report["schema_version"] == "worker-lab-source-doctor:v3"\n    assert report["source_identity_id"] == "acl-runtime-source:v2"\n    assert "execution_authority" not in report\n\n\ndef test_source_status_uses_current_source_identity_contract(capsys) -> None:\n    assert main(["source-status"]) == 0\n    report = json.loads(capsys.readouterr().out)\n    assert report["schema_version"] == "worker-lab-service-source-status:v1"\n    assert report["source_identity"]["source_identity_id"] == "acl-runtime-source:v2"\n'''
ct = replace_once(ct, old, new, "CLI doctor test")
write(cli_test_path, ct)

print("Task 8 source identity V2 candidate materialized")
