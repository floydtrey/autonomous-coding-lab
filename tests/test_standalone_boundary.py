from __future__ import annotations

import ast
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]

_FORBIDDEN_CLIENT_PATHS = (
    _REPO_ROOT / "knowledge_core" / "integrations",
    _REPO_ROOT / "integrations",
)

_FORBIDDEN_TOOL_NAMES = {
    "install_mason_kc_skill.py",
    "mason_cowork_host_qualification.py",
    "mason_kc_bridge.py",
    "mason_kc_cli.py",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "worker_lab",
    "autonomous_worker",
    "minds_hub",
    "mindshub",
    "cowork",
)


def test_standalone_tree_does_not_contain_client_integration_packages():
    for path in _FORBIDDEN_CLIENT_PATHS:
        assert not path.exists(), f"client integration leaked into KC: {path}"

    tools = _REPO_ROOT / "tools"
    present = {path.name for path in tools.glob("*.py")}
    assert not (_FORBIDDEN_TOOL_NAMES & present)


def test_core_packages_do_not_import_client_systems():
    roots = (
        _REPO_ROOT / "knowledge_core",
        _REPO_ROOT / "knowledge_core_providers",
    )
    violations: list[str] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names: tuple[str, ...] = ()
                if isinstance(node, ast.Import):
                    names = tuple(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = (node.module,)
                for name in names:
                    if name.startswith(_FORBIDDEN_IMPORT_PREFIXES):
                        violations.append(f"{path.relative_to(_REPO_ROOT)} -> {name}")
    assert violations == []


def test_packaging_includes_core_and_provider_packages():
    text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"knowledge_core*"' in text
    assert '"knowledge_core_providers*"' in text
