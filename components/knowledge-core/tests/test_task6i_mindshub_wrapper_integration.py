from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from knowledge_core.integrations.context_compaction import WorkingContextCheckpoint
from knowledge_core.integrations.cowork_wrapper import (
    ContextRotationPolicy,
    CoworkClientConfig,
    CoworkTurnResult,
    CoworkUsage,
    CoworkWrapperError,
    LocalCoworkClient,
    MasonCoworkWrapper,
)
from knowledge_core.integrations.mindshub import (
    MASON_PROPOSER_REF,
    MasonKnowledgeCoreBridge,
    MasonKnowledgeCoreBridgeError,
    MasonKnowledgeCoreConfig,
)


class _FakeCoworkClient:
    def __init__(self):
        self.created = []
        self.responses = []
        self._next_conversation = 1
        self.next_usage = {"input_tokens": 90, "output_tokens": 15}

    def create_conversation(self, *, project_id=None, title=None, goal=None):
        conversation_id = f"conv-{self._next_conversation}"
        self._next_conversation += 1
        self.created.append(
            {
                "project_id": project_id,
                "title": title,
                "goal": goal,
                "id": conversation_id,
            }
        )
        return {"id": conversation_id}

    def create_response(
        self,
        *,
        conversation_id,
        input_text,
        model=None,
        skill_ids=(),
    ):
        self.responses.append(
            {
                "conversation_id": conversation_id,
                "input_text": input_text,
                "model": model,
                "skill_ids": tuple(skill_ids),
            }
        )
        return {
            "id": f"resp-{len(self.responses)}",
            "conversation_id": conversation_id,
            "output": [{"type": "text", "text": "done"}],
            "status": "completed",
            "model": model or "project-default",
            "usage": dict(self.next_usage),
        }


class _FakeKnowledgeBridge:
    def __init__(self):
        self.calls = []

    def execute(self, operation, payload=None):
        self.calls.append((operation, dict(payload or {})))
        return {"operation": operation, "payload": dict(payload or {})}


class _FakeHttpResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _load_standalone_bridge() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "tools" / "mason_kc_bridge.py"
    spec = importlib.util.spec_from_file_location("task6i_standalone_bridge", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _checkpoint() -> WorkingContextCheckpoint:
    return WorkingContextCheckpoint(
        objective="Continue the bounded Risk Card OCR task.",
        immutable_constraints=("Do not expand tool authority.",),
        evidence_refs=(),
        completed_work=("Retrieved the accepted project state from KC.",),
        current_state="Ready for the next bounded worker action.",
        blockers=(),
        recent_actions=(),
        source_output_refs=(),
    )


def test_packaged_bridge_routes_autonomous_memory_to_candidate_path(monkeypatch):
    bridge = MasonKnowledgeCoreBridge(
        MasonKnowledgeCoreConfig(
            base_url="http://127.0.0.1:8765",
            api_key="test-key",
        )
    )
    calls = []

    def fake_request(method, path, payload=None, *, extra_headers=None):
        calls.append((method, path, payload, dict(extra_headers or {})))
        return {"state": "pending", "canonical_state": "not_stored"}

    monkeypatch.setattr(bridge, "_request", fake_request)

    first = bridge.execute(
        "kc_propose_memory",
        {
            "content": "The worker drifted after a failed tool call.",
            "project": "local-ai",
        },
    )
    second = bridge.execute(
        "kc_propose_memory",
        {
            "content": "The worker drifted after a failed tool call.",
            "project": "local-ai",
        },
    )

    assert first["canonical_state"] == "not_stored"
    assert calls[0][0:2] == ("POST", "/v1/kc/memory-candidates")
    assert calls[0][2]["proposer_ref"] == MASON_PROPOSER_REF == "mason"
    assert calls[0][3]["Idempotency-Key"].startswith("mason-kc-memory-v1:")
    assert calls[0][3]["Idempotency-Key"] == calls[1][3]["Idempotency-Key"]

    with pytest.raises(MasonKnowledgeCoreBridgeError, match="unsupported field"):
        bridge.execute(
            "kc_propose_memory",
            {
                "content": "Do not allow identity spoofing.",
                "project": "local-ai",
                "proposer_ref": "someone-else",
            },
        )


def test_standalone_bridge_matches_memory_candidate_boundary(monkeypatch):
    module = _load_standalone_bridge()
    calls = []

    def fake_request(config, method, path, payload=None, *, extra_headers=None):
        calls.append((method, path, payload, dict(extra_headers or {})))
        return {"state": "pending", "canonical_state": "not_stored"}

    monkeypatch.setattr(module, "_request", fake_request)
    config = module.BridgeConfig(
        base_url="http://127.0.0.1:8765",
        api_key="test-key",
    )
    module.execute(
        "kc_propose_memory",
        {"content": "Candidate.", "project": "knowledge-core"},
        config=config,
    )

    assert calls[0][0:2] == ("POST", "/v1/kc/memory-candidates")
    assert calls[0][2]["proposer_ref"] == "mason"
    assert calls[0][3]["Idempotency-Key"].startswith("mason-kc-memory-v1:")


def test_cowork_config_is_loopback_and_api_v1_only():
    assert CoworkClientConfig().base_url == "http://127.0.0.1:26866/api/v1"

    with pytest.raises(CoworkWrapperError, match="loopback"):
        CoworkClientConfig(base_url="http://example.com:26866/api/v1")
    with pytest.raises(CoworkWrapperError, match="/api/v1"):
        CoworkClientConfig(base_url="http://127.0.0.1:26866/v1")
    with pytest.raises(CoworkWrapperError, match="credentials"):
        CoworkClientConfig(base_url="http://user:secret@127.0.0.1:26866/api/v1")


def test_local_cowork_client_uses_real_nonstreaming_response_shape(monkeypatch):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return _FakeHttpResponse(
            {
                "id": "resp-1",
                "conversation_id": "conv-1",
                "output": [{"type": "text", "text": "ok"}],
                "status": "completed",
                "model": "mason",
                "usage": {"input_tokens": 10, "output_tokens": 4},
            }
        )

    import knowledge_core.integrations.cowork_wrapper as module

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    client = LocalCoworkClient()
    client.create_response(
        conversation_id="conv-1",
        input_text="Continue.",
        model="mason",
        skill_ids=("knowledge-core",),
    )

    request, timeout = requests[0]
    assert request.full_url == "http://127.0.0.1:26866/api/v1/responses"
    assert timeout == 120.0
    body = json.loads(request.data.decode("utf-8"))
    assert body == {
        "conversation_id": "conv-1",
        "input": "Continue.",
        "model": "mason",
        "skill_ids": ["knowledge-core"],
        "stream": False,
    }


def test_wrapper_rotates_to_new_conversation_when_checkpoint_is_supplied():
    cowork = _FakeCoworkClient()
    wrapper = MasonCoworkWrapper(
        cowork_client=cowork,
        project_id="proj-1",
        model="mason",
        skill_ids=("knowledge-core",),
        context_policy=ContextRotationPolicy(
            context_limit_tokens=128,
            compact_trigger_tokens=100,
        ),
    )
    original = wrapper.start_conversation(goal="Finish the bounded task.")
    result = wrapper.send_turn("Do the next step.")

    assert result.conversation_id == original == "conv-1"
    assert result.output_text == "done"
    assert result.usage == CoworkUsage(input_tokens=90, output_tokens=15)
    assert wrapper.needs_context_rotation(result) is True

    checkpoint = _checkpoint()
    rotation = wrapper.rotate_for_checkpoint(checkpoint)

    assert rotation.previous_conversation_id == "conv-1"
    assert rotation.new_conversation_id == "conv-2"
    assert rotation.checkpoint_digest == checkpoint.checkpoint_digest
    assert wrapper.conversation_id == "conv-2"
    assert cowork.created[1]["project_id"] == "proj-1"
    assert checkpoint.checkpoint_digest in cowork.created[1]["goal"]
    assert checkpoint.objective in cowork.created[1]["goal"]

    wrapper.send_turn("Continue from the checkpoint.")
    assert cowork.responses[-1]["conversation_id"] == "conv-2"


def test_wrapper_does_not_claim_compaction_without_usage():
    wrapper = MasonCoworkWrapper(
        cowork_client=_FakeCoworkClient(),
        context_policy=ContextRotationPolicy(
            context_limit_tokens=128,
            compact_trigger_tokens=100,
        ),
    )
    result = CoworkTurnResult(
        response_id="resp-1",
        conversation_id="conv-1",
        status="completed",
        model="mason",
        output_text="done",
        usage=None,
    )
    with pytest.raises(CoworkWrapperError, match="usage is required"):
        wrapper.needs_context_rotation(result)


def test_wrapper_keeps_autonomous_proposal_and_explicit_store_distinct():
    bridge = _FakeKnowledgeBridge()
    wrapper = MasonCoworkWrapper(
        cowork_client=_FakeCoworkClient(),
        knowledge_bridge=bridge,
    )

    wrapper.propose_autonomous_memory(
        content="Observed failure pattern.",
        project="local-ai",
    )
    wrapper.store_explicit_memory(
        content="User explicitly asked to remember this.",
        project="local-ai",
        source_id="explicit-memory",
    )

    assert bridge.calls[0] == (
        "kc_propose_memory",
        {"content": "Observed failure pattern.", "project": "local-ai"},
    )
    assert bridge.calls[1] == (
        "kc_store",
        {
            "content": "User explicitly asked to remember this.",
            "project": "local-ai",
            "source_id": "explicit-memory",
        },
    )


def test_rotation_requires_a_new_cowork_conversation():
    class SameConversationClient(_FakeCoworkClient):
        def create_conversation(self, *, project_id=None, title=None, goal=None):
            self.created.append(
                {"project_id": project_id, "title": title, "goal": goal, "id": "conv-1"}
            )
            return {"id": "conv-1"}

    wrapper = MasonCoworkWrapper(cowork_client=SameConversationClient())
    wrapper.start_conversation(goal="Initial goal.")
    with pytest.raises(CoworkWrapperError, match="different Cowork conversation"):
        wrapper.rotate_for_checkpoint(_checkpoint())


def test_skill_documents_five_operations_current_graph_status_and_memory_boundary():
    skill_path = (
        Path(__file__).resolve().parents[1]
        / "integrations"
        / "mindshub"
        / "KNOWLEDGE_CORE_SKILL.md"
    )
    text = skill_path.read_text(encoding="utf-8")

    for operation in (
        "kc_status",
        "kc_search",
        "kc_get_source",
        "kc_store",
        "kc_propose_memory",
    ):
        assert operation in text
    assert "graph status of `ready`" in text
    assert "Autonomous/self-initiated memory proposal" in text
    assert "do **not** call `kc_store`" in text
    assert "Do not use Cowork/MindsHub native memories" in text
    assert "Do not POST to `/memories`" in text
    assert "kc-worker-context-checkpoint-v1" in text
