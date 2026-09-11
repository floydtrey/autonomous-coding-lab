import importlib.util
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
