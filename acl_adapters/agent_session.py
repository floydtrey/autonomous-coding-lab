"""Append-only agent interaction events with a replaceable model-visible surface.

The event log is the durable conceptual history for one adapter invocation. The
current model-visible message list is derived by replaying events. Future context
compaction can append a surface-replacement event without deleting earlier tool
calls/messages from the session history.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class AgentSessionEvent:
    sequence: int
    event_type: str
    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "payload": dict(self.payload),
        }


class AgentSession:
    def __init__(self) -> None:
        self._events: list[AgentSessionEvent] = []

    @classmethod
    def from_messages(
        cls,
        messages: Sequence[Mapping[str, Any]],
    ) -> "AgentSession":
        session = cls()
        for message in messages:
            session.append_message(message, event_type="initial")
        return session

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def surface_replacement_count(self) -> int:
        return sum(
            1 for event in self._events if event.event_type == "surface_replace"
        )

    def events(self) -> tuple[AgentSessionEvent, ...]:
        return tuple(self._events)

    def append_message(
        self,
        message: Mapping[str, Any],
        *,
        event_type: str = "message",
    ) -> AgentSessionEvent:
        if not isinstance(message, Mapping):
            raise TypeError("agent session message must be a mapping")
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("agent session event_type must be nonblank text")
        return self._append(
            event_type.strip(),
            {"message": dict(message)},
        )

    def replace_surface(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        reason: str,
    ) -> AgentSessionEvent:
        """Append a model-surface replacement while preserving prior events."""
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("surface replacement reason must be nonblank text")
        normalized = []
        for message in messages:
            if not isinstance(message, Mapping):
                raise TypeError("replacement surface messages must be mappings")
            normalized.append(dict(message))
        return self._append(
            "surface_replace",
            {
                "reason": reason.strip(),
                "messages": normalized,
            },
        )

    def messages(self) -> list[dict[str, Any]]:
        surface: list[dict[str, Any]] = []
        for event in self._events:
            if event.event_type == "surface_replace":
                replacement = event.payload.get("messages")
                if not isinstance(replacement, list):
                    raise ValueError("surface replacement event is malformed")
                surface = [dict(item) for item in replacement]
                continue
            message = event.payload.get("message")
            if isinstance(message, Mapping):
                surface.append(dict(message))
        return surface

    def telemetry(self) -> dict[str, int]:
        return {
            "session_event_count": self.event_count,
            "session_surface_message_count": len(self.messages()),
            "session_surface_replacements": self.surface_replacement_count,
        }

    def _append(
        self,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> AgentSessionEvent:
        event = AgentSessionEvent(
            sequence=len(self._events) + 1,
            event_type=event_type,
            payload=dict(payload),
        )
        self._events.append(event)
        return event
