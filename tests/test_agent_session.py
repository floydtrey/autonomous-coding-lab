"""Agent session and context-pressure foundation tests."""
from __future__ import annotations

from acl_adapters.agent_session import AgentSession
from acl_adapters.context_pressure import estimate_context_pressure


def test_agent_session_replays_append_only_events():
    session = AgentSession.from_messages(
        [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "request"},
        ]
    )
    session.append_message(
        {"role": "assistant", "content": None, "tool_calls": []},
        event_type="assistant",
    )
    session.append_message(
        {"role": "tool", "content": "{\"ok\":true}"},
        event_type="tool",
    )

    observed = session.messages()

    assert [item["role"] for item in observed] == [
        "system",
        "user",
        "assistant",
        "tool",
    ]
    assert session.event_count == 4
    assert [event.sequence for event in session.events()] == [1, 2, 3, 4]


def test_surface_replacement_preserves_prior_history_events():
    session = AgentSession.from_messages(
        [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "long original request"},
            {"role": "tool", "content": "very large result"},
        ]
    )
    original_events = session.events()

    session.replace_surface(
        [
            {"role": "system", "content": "system"},
            {
                "role": "user",
                "content": "Compacted checkpoint: request and relevant findings.",
            },
        ],
        reason="future-test-compaction",
    )
    session.append_message(
        {"role": "assistant", "content": "continue"},
        event_type="assistant",
    )

    assert len(original_events) == 3
    assert session.event_count == 5
    assert session.surface_replacement_count == 1
    assert session.messages() == [
        {"role": "system", "content": "system"},
        {
            "role": "user",
            "content": "Compacted checkpoint: request and relevant findings.",
        },
        {"role": "assistant", "content": "continue"},
    ]
    assert session.events()[0].payload["message"]["content"] == "system"
    assert session.events()[2].payload["message"]["content"] == "very large result"


def test_context_pressure_reserves_output_budget():
    estimate = estimate_context_pressure(
        {
            "model": "test",
            "messages": [{"role": "user", "content": "x" * 1600}],
        },
        configured_context_window=1000,
        reserved_output_tokens=500,
        characters_per_token=4.0,
        warning_ratio=0.8,
    )

    assert estimate.estimated_input_tokens >= 400
    assert estimate.reserved_output_tokens == 500
    assert estimate.projected_tokens == (
        estimate.estimated_input_tokens + 500
    )
    assert estimate.projected_ratio >= 0.8
    assert estimate.action == "WARN"
    assert estimate.capacity_source == "configured_route_estimate"


def test_context_pressure_never_claims_observed_provider_capacity():
    estimate = estimate_context_pressure(
        {"messages": [{"role": "user", "content": "hello"}]},
        configured_context_window=None,
        reserved_output_tokens=100,
    )

    assert estimate.configured_context_window is None
    assert estimate.projected_ratio is None
    assert estimate.capacity_source is None
    assert estimate.action == "UNKNOWN"
