from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_core.integrations import mindshub
from knowledge_core.integrations.mindshub import (
    MasonKnowledgeCoreBridge,
    MasonKnowledgeCoreBridgeError,
    MasonKnowledgeCoreConfig,
)


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _bridge(monkeypatch, returned=None):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "method": request.get_method(),
                "url": request.full_url,
                "headers": dict(request.header_items()),
                "body": json.loads(request.data.decode("utf-8")) if request.data else None,
                "timeout": timeout,
            }
        )
        return _Response(returned or {"ok": True})

    monkeypatch.setattr(mindshub, "urlopen", fake_urlopen)
    bridge = MasonKnowledgeCoreBridge(
        MasonKnowledgeCoreConfig(
            base_url="http://127.0.0.1:8765",
            api_key="secret-key",
        )
    )
    return bridge, calls


def test_bridge_exposes_only_four_operations(monkeypatch):
    bridge, _calls = _bridge(monkeypatch)
    with pytest.raises(MasonKnowledgeCoreBridgeError, match="unsupported Knowledge Core operation"):
        bridge.execute("sql_query", {})
    with pytest.raises(MasonKnowledgeCoreBridgeError, match="unsupported Knowledge Core operation"):
        bridge.execute("graphiti_sync", {})


def test_task5_v1_requires_loopback_url():
    with pytest.raises(MasonKnowledgeCoreBridgeError, match="loopback"):
        MasonKnowledgeCoreConfig.from_env(
            {
                "KNOWLEDGE_CORE_BASE_URL": "http://192.168.1.20:8765",
                "KNOWLEDGE_CORE_BOOTSTRAP_KEY": "secret",
            }
        )


def test_status_uses_only_bootstrap_front_door(monkeypatch):
    bridge, calls = _bridge(monkeypatch, {"text_state": "ready"})
    result = bridge.execute("kc_status", {})
    assert result == {"text_state": "ready"}
    assert calls == [
        {
            "method": "GET",
            "url": "http://127.0.0.1:8765/v1/kc/status",
            "headers": {
                "Accept": "application/json",
                "X-knowledge-key": "secret-key",
            },
            "body": None,
            "timeout": 15.0,
        }
    ]


def test_search_forces_current_non_superseded_evidence(monkeypatch):
    bridge, calls = _bridge(monkeypatch, {"results": []})
    bridge.execute("kc_search", {"query": "What is Mason?", "limit": 5})
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"].endswith("/v1/kc/search")
    assert calls[0]["body"] == {
        "query": "What is Mason?",
        "limit": 5,
        "include_superseded": False,
    }
    with pytest.raises(MasonKnowledgeCoreBridgeError, match="unsupported field"):
        bridge.execute(
            "kc_search",
            {"query": "old data", "include_superseded": True},
        )


def test_get_source_accepts_only_returned_resource_version_shape(monkeypatch):
    bridge, calls = _bridge(monkeypatch, {"content": "exact"})
    bridge.execute(
        "kc_get_source",
        {"resource_version_ref": "1c3f46e3-78db-44a2-a3a4-8e564c648867"},
    )
    assert calls[0]["url"].endswith("/v1/kc/get-source")
    assert calls[0]["body"] == {
        "resource_version_ref": "1c3f46e3-78db-44a2-a3a4-8e564c648867"
    }


def test_store_forces_user_note_and_deterministic_idempotency(monkeypatch):
    bridge, calls = _bridge(monkeypatch, {"stored": True})
    payload = {
        "content": "Mason is my local MindsHub worker model.",
        "project": "local-ai",
        "source_id": "mason-model-identity",
    }
    bridge.execute("kc_store", payload)
    bridge.execute("kc_store", payload)

    first, second = calls
    assert first["url"].endswith("/v1/kc/store")
    assert first["body"] == {
        "content": payload["content"],
        "project": "local-ai",
        "source_type": "user_note",
        "source_id": "mason-model-identity",
    }
    assert first["headers"]["Idempotency-key"].startswith("mason-kc-v1:")
    assert first["headers"]["Idempotency-key"] == second["headers"]["Idempotency-key"]


def test_skill_template_is_procedure_body_and_fail_closed():
    path = (
        Path(__file__).resolve().parents[1]
        / "integrations"
        / "mindshub"
        / "KNOWLEDGE_CORE_SKILL.md"
    )
    text = path.read_text(encoding="utf-8")
    assert "{{BRIDGE_PATH}}" in text
    assert not text.startswith("---")
    assert "not a tool named `knowledge-core`" in text
    assert "Do not fall back to filesystem searches" in text
    assert "KNOWLEDGE_CORE_BOOTSTRAP_KEY" in text
    assert "Never print" in text
    for operation in ("kc_status", "kc_search", "kc_get_source", "kc_store"):
        assert operation in text
    assert "graphiti_sync" not in text
    assert "sql_query" not in text


def test_project_bridge_is_stdlib_only_and_has_no_repo_import_dependency():
    path = Path(__file__).resolve().parents[1] / "tools" / "mason_kc_bridge.py"
    text = path.read_text(encoding="utf-8")
    assert "from knowledge_core" not in text
    assert "import knowledge_core" not in text
    assert "KNOWLEDGE_CORE_BOOTSTRAP_KEY" in text
    assert "127.0.0.1" in text
    for operation in ("kc_status", "kc_search", "kc_get_source", "kc_store"):
        assert operation in text


def test_installer_does_not_assume_legacy_fixed_cowork_port():
    path = Path(__file__).resolve().parents[1] / "tools" / "install_mason_kc_skill.py"
    text = path.read_text(encoding="utf-8")
    assert 'default="http://127.0.0.1:26866"' not in text
    assert '"--cowork-url",\n        required=True' in text
