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
    result = installer._register_skill("http://127.0.0.1:27108", "instructions")

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
    }
    assert "tools" not in payload


def test_register_skill_uses_put_for_existing_skill(monkeypatch):
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
                    }
                ]
            }
        return {"id": "knowledge-core", "label": "knowledge-core"}

    monkeypatch.setattr(installer, "_request_json", fake_request)
    installer._register_skill("http://127.0.0.1:27108", "updated")

    assert calls[1][0] == "PUT"
    assert calls[1][1] == "http://127.0.0.1:27108/api/v1/skills/knowledge-core"
    assert calls[1][2]["label"] == "knowledge-core"
    assert calls[1][2]["instructions"] == "updated"
