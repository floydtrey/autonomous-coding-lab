from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


class _FakeCoworkClient:
    def __init__(self, _config):
        self.config = type("Config", (), {"base_url": "http://127.0.0.1:26866/api/v1"})()
        self._conversation = 0
        self._response = 0

    def create_conversation(self, *, project_id=None, title=None, goal=None):
        self._conversation += 1
        return {
            "id": f"conv-{self._conversation}",
            "project_id": project_id,
            "title": title,
            "goal": goal,
        }

    def create_response(
        self,
        *,
        conversation_id,
        input_text,
        model=None,
        skill_ids=(),
    ):
        self._response += 1
        return {
            "id": f"resp-{self._response}",
            "conversation_id": conversation_id,
            "output": [
                {
                    "type": "text",
                    "text": f"fake response {self._response}: {input_text[:40]}",
                }
            ],
            "status": "completed",
            "model": model or "project-default",
            "usage": {
                "input_tokens": 50 + self._response,
                "output_tokens": 10,
            },
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
        skill_id=["knowledge-core"],
        cowork_base_url="http://127.0.0.1:26866/api/v1",
        context_limit_tokens=131072,
        compact_trigger_tokens=100000,
        output_dir=str(tmp_path / "evidence"),
        exercise_memory_proposal=False,
    )

    result = module.run(args)

    assert result["mechanical_pass"] is True
    assert result["semantic_review_required"] is True
    assert result["initial_conversation_id"] == "conv-1"
    assert result["continuation_conversation_id"] == "conv-2"
    assert result["checkpoint_digest"].startswith("sha256:")
    assert result["memory_proposal_exercised"] is False

    evidence_path = Path(result["evidence_path"])
    assert evidence_path.exists()
    stored = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert stored["mechanical_pass"] is True
    assert stored["initial_status_turn"]["usage"]["input_tokens"] == 51
    assert stored["continuation_status_turn"]["usage"]["input_tokens"] == 52
    assert (tmp_path / "evidence" / "01-initial-status-output.txt").exists()
    assert (tmp_path / "evidence" / "02-continuation-status-output.txt").exists()
