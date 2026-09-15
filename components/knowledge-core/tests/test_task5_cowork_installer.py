from __future__ import annotations

import importlib.util
from pathlib import Path


_INSTALLER_PATH = (
    Path(__file__).resolve().parents[1] / "tools" / "install_mason_kc_skill.py"
)
_SPEC = importlib.util.spec_from_file_location("task5_cowork_installer", _INSTALLER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
installer = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(installer)


def test_register_skill_uses_current_cowork_create_contract(monkeypatch):
    calls = []

    def fake_request(method, url, payload=None):
        calls.append((method, url, payload))
        if method == "GET":
            return {"skills": []}
        return {"id": "knowledge-core", "label": "knowledge-core"}

    monkeypatch.setattr(installer, "_request_json", fake_request)
    result = installer._register_skill(
        "http://127.0.0.1:27108",
        "instructions",
        "mason-kc-test",
    )

    assert result["id"] == "knowledge-core"
    assert calls[0] == ("GET", "http://127.0.0.1:27108/api/v1/skills/", None)
    method, url, payload = calls[1]
    assert method == "POST"
    assert url == "http://127.0.0.1:27108/api/v1/skills/"
    assert payload == {
        "label": "knowledge-core",
        "name": "Knowledge Core",
        "description": "Retrieve and store governed durable project knowledge through local Knowledge Core.",
        "instructions": "instructions",
        "enabled": True,
        "projects": ["mason-kc-test"],
    }
    assert "tools" not in payload


def test_register_skill_uses_put_and_unions_explicit_projects(monkeypatch):
    calls = []

    def fake_request(method, url, payload=None):
        calls.append((method, url, payload))
        if method == "GET":
            return {
                "skills": [
                    {
                        "id": "knowledge-core",
                        "label": "knowledge-core",
                        "name": "Knowledge Core",
                        "projects": ["existing-project"],
                    }
                ]
            }
        return {"id": "knowledge-core", "label": "knowledge-core"}

    monkeypatch.setattr(installer, "_request_json", fake_request)
    installer._register_skill(
        "http://127.0.0.1:27108",
        "updated",
        "mason-kc-test",
    )

    assert calls[1][0] == "PUT"
    assert calls[1][1] == "http://127.0.0.1:27108/api/v1/skills/knowledge-core"
    assert calls[1][2]["label"] == "knowledge-core"
    assert calls[1][2]["instructions"] == "updated"
    assert calls[1][2]["projects"] == ["existing-project", "mason-kc-test"]


def test_register_skill_replaces_legacy_global_scope_with_configured_project(monkeypatch):
    calls = []

    def fake_request(method, url, payload=None):
        calls.append((method, url, payload))
        if method == "GET":
            return {
                "skills": [
                    {
                        "id": "knowledge-core",
                        "label": "knowledge-core",
                        "projects": [],
                    }
                ]
            }
        return {"id": "knowledge-core", "label": "knowledge-core"}

    monkeypatch.setattr(installer, "_request_json", fake_request)
    installer._register_skill(
        "http://127.0.0.1:27108",
        "updated",
        "mason-kc-test",
    )

    assert calls[1][2]["projects"] == ["mason-kc-test"]


def test_resolve_cowork_project_name_matches_exact_registered_folder(monkeypatch, tmp_path):
    project_dir = tmp_path / "mason-kc-test"
    project_dir.mkdir()

    def fake_request(method, url, payload=None):
        assert method == "GET"
        assert url == "http://127.0.0.1:27108/api/v1/projects/"
        assert payload is None
        return [
            {"name": "other", "path": str(tmp_path / "other")},
            {"name": "mason-kc-test", "path": str(project_dir)},
        ]

    monkeypatch.setattr(installer, "_request_json", fake_request)
    assert (
        installer._resolve_cowork_project_name(
            "http://127.0.0.1:27108",
            project_dir,
        )
        == "mason-kc-test"
    )


def test_install_project_bridge_keeps_executable_inside_project(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    source = tmp_path / "source.py"
    source.write_text("print('bridge')\n", encoding="utf-8")

    installed = installer._install_project_bridge(project_dir, source)

    assert installed == project_dir / "knowledge-core-tools" / "mason_kc_bridge.py"
    assert installed.read_text(encoding="utf-8") == "print('bridge')\n"
    assert installed.is_relative_to(project_dir)
