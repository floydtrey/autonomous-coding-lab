import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "verify_portable_installation.py"
MANIFEST_PATH = ROOT / "config" / "portable-installation-manifest.json"
SPEC = importlib.util.spec_from_file_location("verify_portable_installation", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _component(*, scope: str, digest: str, files=None):
    value = {
        "root": "component",
        "production_root": "src",
        "scope": scope,
        "digest": digest,
    }
    if files is not None:
        value["files"] = files
    return value


def test_canonical_digest_matches_installed_file_set_contract() -> None:
    entries = [
        {"path": "a.py", "sha256": "sha256:" + "1" * 64},
        {"path": "b.py", "sha256": "sha256:" + "2" * 64},
    ]
    assert MODULE.canonical_digest(entries) == (
        "sha256:9c3557b8c411f1a80dfaf33c6199a091eb0d686368f901e16d9c03d45aeaf7fd"
    )


def test_python_tree_identity_changes_when_installed_bytes_change(tmp_path: Path) -> None:
    component_root = tmp_path / "component"
    production = component_root / "src"
    production.mkdir(parents=True)
    source = production / "worker.py"
    source.write_bytes(b"print('a')\n")
    relative = "src/worker.py"
    expected = MODULE.canonical_digest(
        [{"path": relative, "sha256": MODULE.bytes_digest(source.read_bytes())}]
    )
    raw = _component(scope="python-production-tree", digest=expected)
    result = MODULE._inspect_component(tmp_path, "worker-lab", raw)
    assert result["status"] == "MATCH"

    source.write_bytes(b"print('b')\n")
    with pytest.raises(MODULE.PortableIdentityError):
        MODULE._inspect_component(tmp_path, "worker-lab", raw)


def test_committed_framework_closure_matches_verifier_contract() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    configured = tuple(
        manifest["components"]["autonomous-worker-framework"]["files"]
    )
    assert configured == MODULE._FRAMEWORK_FILES


def test_portable_policy_never_treats_provider_presence_as_authority() -> None:
    manifest = {
        "schema_version": MODULE.SCHEMA_VERSION,
        "installation_id": "acl-development",
        "activation_policy": {
            "policy_id": "acl-installation-activation:v1",
            "execution_authority": "DISABLED",
            "participants": {
                "autonomous-worker-framework": "AVAILABLE",
                "local-model-bench": "ADVISORY",
                "worker-lab": "DEFERRED",
            },
        },
        "runtime_policy": {
            "provider_identity": "host-qualified-separately:v1",
            "portable_identity_requires_provider": False,
        },
    }
    assert manifest["activation_policy"]["execution_authority"] == "DISABLED"
    assert manifest["runtime_policy"]["portable_identity_requires_provider"] is False
