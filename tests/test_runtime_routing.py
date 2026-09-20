from pathlib import Path

from acl_controller.configuration import ProfileResolver, ProfileSelector
from acl_runtime.pipeline import _accepted_determiner_route


ROOT = Path(__file__).resolve().parents[1]


def test_central_runtime_catalog_selects_role_models():
    resolver = ProfileResolver(ROOT / "config")

    determiner = resolver.resolve(ProfileSelector("determiner", None, None))
    planner = resolver.resolve(ProfileSelector("planner", "1127", "SMALL"))
    worker = resolver.resolve(ProfileSelector("worker", "1127", "SMALL"))

    assert determiner.settings["model"] == "qwen3.5:9b"
    assert determiner.adapter_id == "openai-compatible.chat"
    assert determiner.metadata["runtime_id"] == "ollama-qwen35-9b-chat-16k"

    assert planner.settings["model"] == "qwen3.5:9b"
    assert planner.adapter_id == "openai-compatible.chat"
    assert planner.metadata["runtime_id"] == "ollama-qwen35-9b-chat-16k"

    assert worker.settings["model"] == "qwen3-coder:30b-16k"
    assert worker.adapter_id == "openai-compatible.agent"
    assert worker.metadata["runtime_id"] == "ollama-qwen3-coder-30b-agent-16k"


def test_pipeline_extracts_accepted_determiner_route():
    result = {
        "inspection": {
            "results": [
                {
                    "executor": "ROLE",
                    "payload": {
                        "classification": "CLASSIFIED",
                        "work_type_id": "1127",
                        "complexity": "SMALL",
                    },
                }
            ]
        }
    }

    assert _accepted_determiner_route(result) == ("1127", "SMALL")


def test_pipeline_stops_when_determiner_does_not_classify():
    result = {
        "inspection": {
            "results": [
                {
                    "executor": "ROLE",
                    "payload": {
                        "classification": "UNKNOWN",
                        "work_type_id": None,
                        "complexity": None,
                    },
                }
            ]
        }
    }

    assert _accepted_determiner_route(result) is None
