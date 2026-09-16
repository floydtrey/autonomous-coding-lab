from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from knowledge_core.integrations import mindshub
from knowledge_core.integrations.mindshub import (
    MasonKnowledgeCoreBridge,
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


def _unified_payload():
    return {
        "query": "What is Mason?",
        "generation_id": "11111111-1111-1111-1111-111111111111",
        "evidence_contract_version": "kc-lexical-evidence-v2",
        "results": [
            {
                "resource_version_ref": "22222222-2222-2222-2222-222222222222",
                "content": "Mason is my local MindsHub worker model.",
            }
        ],
        "unified_evidence_contract_version": "kc-unified-retrieval-evidence-v1",
        "graph": {
            "state": "ready",
            "namespace_key": "kc:graphiti-source-neutral-v1",
            "scope_key": "project:knowledge-core",
            "generation_id": "11111111-1111-1111-1111-111111111111",
            "attempt_ids": ["33333333-3333-3333-3333-333333333333"],
            "results": [
                {
                    "provider_hit_id": "edge-1",
                    "fact": "Mason is the local MindsHub worker model.",
                    "sources": [
                        {
                            "resource_version_ref": "22222222-2222-2222-2222-222222222222",
                            "segment_key": "segment-0",
                        }
                    ],
                }
            ],
        },
        "warnings": [],
    }


def test_packaged_bridge_preserves_additive_unified_search_response(monkeypatch):
    returned = _unified_payload()
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "url": request.full_url,
                "body": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        return _Response(returned)

    monkeypatch.setattr(mindshub, "urlopen", fake_urlopen)
    bridge = MasonKnowledgeCoreBridge(
        MasonKnowledgeCoreConfig(
            base_url="http://127.0.0.1:8765",
            api_key="secret-key",
        )
    )

    result = bridge.execute("kc_search", {"query": "What is Mason?", "limit": 5})

    assert result == returned
    assert result["graph"]["state"] == "ready"
    assert result["graph"]["results"][0]["sources"][0]["resource_version_ref"] == (
        "22222222-2222-2222-2222-222222222222"
    )
    assert calls == [
        {
            "url": "http://127.0.0.1:8765/v1/kc/search",
            "body": {
                "query": "What is Mason?",
                "limit": 5,
                "include_superseded": False,
            },
            "timeout": 15.0,
        }
    ]


def test_project_local_bridge_preserves_additive_unified_search_response(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "tools" / "mason_kc_bridge.py"
    spec = importlib.util.spec_from_file_location("task6e_project_bridge", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    returned = _unified_payload()
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "url": request.full_url,
                "body": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        return _Response(returned)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    config = module.BridgeConfig(
        base_url="http://127.0.0.1:8765",
        api_key="secret-key",
    )

    result = module.execute(
        "kc_search",
        {"query": "What is Mason?", "limit": 5},
        config=config,
    )

    assert result == returned
    assert result["unified_evidence_contract_version"] == (
        "kc-unified-retrieval-evidence-v1"
    )
    assert calls[0]["url"].endswith("/v1/kc/search")
    assert calls[0]["body"]["include_superseded"] is False


def test_skill_teaches_separate_lexical_and_graph_evidence_without_new_tool():
    path = (
        Path(__file__).resolve().parents[1]
        / "integrations"
        / "mindshub"
        / "KNOWLEDGE_CORE_SKILL.md"
    )
    text = path.read_text(encoding="utf-8")

    assert "separate evidence lanes" in text
    assert "graph.state" in text
    assert "continue using relevant lexical results" in text
    assert "resource_version_ref" in text
    assert "kc_get_source" in text
    assert "derived retrieval evidence" in text
    assert "Do not invent or call a second graph-search operation" in text
    assert "Do not claim graph readiness from this response" in text

    for state in (
        "disabled",
        "no_build",
        "ready",
        "stale",
        "pending",
        "unvalidated",
        "failed",
        "unavailable",
    ):
        assert state in text

    for operation in ("kc_status", "kc_search", "kc_get_source", "kc_store"):
        assert operation in text

    assert "kc_graph_search" not in text
    assert "graphiti_sync" not in text
    assert "sql_query" not in text
