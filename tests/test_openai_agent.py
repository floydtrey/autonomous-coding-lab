from acl_adapters.openai_agent import OpenAICompatibleAgentAdapter
from acl_adapters.openai_compatible import OpenAICompatibleChatAdapter
from acl_core import AdapterRequest


def test_assistant_message_preserves_reasoning_for_tool_continuation():
    message = {
        "role": "assistant",
        "content": None,
        "reasoning": "I found the relevant module and need to inspect its caller.",
        "thinking": "provider-native thinking",
        "reasoning_content": "compat reasoning",
        "tool_calls": [{"id": "call-1", "type": "function", "function": {}}],
    }

    observed = OpenAICompatibleAgentAdapter._assistant_message(message)

    assert observed["role"] == "assistant"
    assert observed["content"] is None
    assert observed["reasoning"] == message["reasoning"]
    assert observed["thinking"] == message["thinking"]
    assert observed["reasoning_content"] == message["reasoning_content"]
    assert observed["tool_calls"] == message["tool_calls"]


def test_tool_alias_resolution_is_conservative_and_unambiguous():
    allowed = (
        "filesystem.list_directory",
        "filesystem.read_text",
        "filesystem.search",
    )

    assert (
        OpenAICompatibleAgentAdapter._resolve_tool_name("read_text", allowed)
        == "filesystem.read_text"
    )
    assert (
        OpenAICompatibleAgentAdapter._resolve_tool_name(
            "filesystem=read_text",
            allowed,
        )
        == "filesystem.read_text"
    )
    assert (
        OpenAICompatibleAgentAdapter._resolve_tool_name("unknown_tool", allowed)
        == "unknown_tool"
    )


def test_truncated_final_response_gets_one_response_only_retry():
    adapter = OpenAICompatibleAgentAdapter(
        adapter_id="openai-compatible.agent",
        settings={},
    )
    observed_bodies = []
    scripted = [
        (
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Long analysis that never reached the handoff.",
                        },
                        "finish_reason": "length",
                    }
                ]
            },
            {
                "model": "test-model",
                "finish_reason": "length",
            },
        ),
        (
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Pass 1:\nTask 1: Make the bounded repair.",
                        },
                        "finish_reason": "stop",
                    }
                ]
            },
            {
                "model": "test-model",
                "finish_reason": "stop",
            },
        ),
    ]

    def fake_request_completion(*, request_id, body, runtime):
        observed_bodies.append(dict(body))
        return scripted.pop(0)

    adapter._request_completion = fake_request_completion

    response = adapter.invoke(
        AdapterRequest(
            operation="role.invoke",
            payload={
                "role_request": {
                    "execution": {
                        "base_url": "http://127.0.0.1:1/v1",
                        "model": "test-model",
                        "response_format_json": False,
                        "max_agent_turns": 4,
                    },
                    "tool_ids": [],
                }
            },
        )
    )

    assert response.ok is True
    assert response.payload == "Pass 1:\nTask 1: Make the bounded repair."
    assert response.metadata["final_response_retries"] == 1
    assert len(observed_bodies) == 2
    retry_messages = observed_bodies[1]["messages"]
    assert "Stop investigating" in retry_messages[-1]["content"]


def test_second_truncated_final_response_is_an_error():
    adapter = OpenAICompatibleAgentAdapter(
        adapter_id="openai-compatible.agent",
        settings={},
    )
    scripted = [
        (
            {
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "first"},
                        "finish_reason": "length",
                    }
                ]
            },
            {"model": "test-model", "finish_reason": "length"},
        ),
        (
            {
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "second"},
                        "finish_reason": "length",
                    }
                ]
            },
            {"model": "test-model", "finish_reason": "length"},
        ),
    ]

    def fake_request_completion(*, request_id, body, runtime):
        return scripted.pop(0)

    adapter._request_completion = fake_request_completion

    response = adapter.invoke(
        AdapterRequest(
            operation="role.invoke",
            payload={
                "role_request": {
                    "execution": {
                        "base_url": "http://127.0.0.1:1/v1",
                        "model": "test-model",
                        "response_format_json": False,
                        "max_agent_turns": 4,
                    },
                    "tool_ids": [],
                }
            },
        )
    )

    assert response.ok is False
    assert response.error["code"] == "AGENT_RESPONSE_TRUNCATED"
    assert response.metadata["final_response_retries"] == 1


def test_tool_result_limit_bounds_model_visible_content():
    original = {
        "role": "tool",
        "tool_call_id": "call-1",
        "name": "filesystem.read_text",
        "content": "{\"ok\":true,\"value\":{\"content\":\"" + ("x" * 5000) + "\"}}",
    }

    bounded, metadata = OpenAICompatibleAgentAdapter._bound_tool_message(
        original,
        max_chars=1000,
    )

    assert len(bounded["content"]) <= 1000
    assert metadata["original_characters"] == len(original["content"])
    assert metadata["visible_characters"] == len(bounded["content"])
    assert '"result_truncated":true' in bounded["content"]
    assert "narrower path/query" in bounded["content"]


def test_tool_result_limit_leaves_small_content_unchanged():
    original = {
        "role": "tool",
        "tool_call_id": "call-1",
        "name": "filesystem.read_text",
        "content": "{\"ok\":true}",
    }

    bounded, metadata = OpenAICompatibleAgentAdapter._bound_tool_message(
        original,
        max_chars=1000,
    )

    assert bounded == original
    assert metadata is None


def test_context_telemetry_distinguishes_configured_from_observed_capacity():
    telemetry = OpenAICompatibleChatAdapter._extract_telemetry(
        {
            "model": "test-model",
            "usage": {"prompt_tokens": 4096, "completion_tokens": 128},
            "choices": [
                {
                    "message": {"role": "assistant", "content": "done"},
                    "finish_reason": "stop",
                }
            ],
        },
        runtime={"model": "test-model", "context_window": 16384},
        http_elapsed_ms=1.0,
        response_bytes=100,
        request_bytes=50,
    )

    assert telemetry["context_window"] == 16384
    assert telemetry["configured_context_window"] == 16384
    assert telemetry["observed_context_window"] is None
    assert telemetry["context_capacity_source"] == "configured_route"
    assert telemetry["configured_context_utilization"] == 0.25
