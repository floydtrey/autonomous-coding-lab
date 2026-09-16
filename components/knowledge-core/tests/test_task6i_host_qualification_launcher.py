from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


class _FakeCoworkClient:
    last_instance = None

    def __init__(self, config):
        self.config = config
        self._conversation = 0
        self._response = 0
        self.created = []
        self.responses = []
        _FakeCoworkClient.last_instance = self

    def create_conversation(self, *, project_id=None, title=None, model=None):
        self._conversation += 1
        conversation_id = f"conv-{self._conversation}"
        self.created.append(
            {
                "id": conversation_id,
                "project_id": project_id,
                "title": title,
                "model": model,
            }
        )
        return {
            "id": conversation_id,
            "project_id": project_id,
            "title": title,
            "model": model,
        }

    def create_response(
        self,
        *,
        conversation_id,
        input_text,
        model=None,
    ):
        self._response += 1
        self.responses.append(
            {
                "conversation_id": conversation_id,
                "input_text": input_text,
                "model": model,
            }
        )
        return {
            "id": f"resp-{self._response}",
            "object": "response",
            "status": "completed",
            "model": model or "project-default",
            "output": [
                {
                    "type": "message",
                    "id": f"msg-{self._response}",
                    "status": "completed",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": f"fake response {self._response}",
                        }
                    ],
                }
            ],
        }


def _load_launcher():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "mason_cowork_host_qualification.py"
    )
    spec = importlib.util.spec_from_file_location("task6i_host_launcher", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_host_launcher_rotates_and_writes_reviewable_evidence(tmp_path, monkeypatch):
    module = _load_launcher()
    monkeypatch.setattr(module, "LocalCoworkClient", _FakeCoworkClient)
    args = argparse.Namespace(
        project_id="proj-test",
        model="mason",
        cowork_base_url="http://127.0.0.1:26866/api/v1",
        timeout_seconds=600.0,
        context_limit_tokens=131072,
        compact_trigger_tokens=100000,
        output_dir=str(tmp_path / "evidence"),
        exercise_memory_proposal=False,
    )

    result = module.run(args)

    assert result["mechanical_pass"] is True
    assert result["semantic_review_required"] is True
    assert result["contract"] == "kc-task6i-host-qualification-v2"
    assert result["cowork_contract_version"] == "v0.26.9.14.2"
    assert result["initial_conversation_id"] == "conv-1"
    assert result["continuation_conversation_id"] == "conv-2"
    assert result["checkpoint_digest"].startswith("sha256:")
    assert result["checkpoint_injection"] == "first-input-of-fresh-conversation"
    assert result["memory_proposal_exercised"] is False
    assert result["context_policy"]["usage_state"].startswith(
        "unavailable-from-cowork-responses-"
    )
    assert result["context_policy"]["automatic_token_rotation_qualified"] is False

    fake = _FakeCoworkClient.last_instance
    assert fake is not None
    assert fake.config.timeout_seconds == 600.0
    assert len(fake.created) == 2
    assert len(fake.responses) == 2
    assert fake.responses[0]["conversation_id"] == "conv-1"
    assert module.INITIAL_CONTEXT in fake.responses[0]["input_text"]
    assert fake.responses[1]["conversation_id"] == "conv-2"
    assert result["checkpoint_digest"] in fake.responses[1]["input_text"]
    assert module.CONTINUATION_PROMPT.strip() in fake.responses[1]["input_text"]

    evidence_path = Path(result["evidence_path"])
    assert evidence_path.exists()
    stored = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert stored["mechanical_pass"] is True
    assert stored["initial_status_turn"]["usage"] is None
    assert stored["continuation_status_turn"]["usage"] is None
    assert (tmp_path / "evidence" / "01-initial-status-output.txt").exists()
    assert (tmp_path / "evidence" / "02-continuation-status-output.txt").exists()
