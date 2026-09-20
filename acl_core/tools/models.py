"""Generic tool contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..errors import CoreError
from ..identity import CoreIdentity


_DEFAULT_PARAMETERS = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ToolDefinition:
    tool_id: str
    description: str
    required_capabilities: tuple[str, ...] = ()
    parameters: Mapping[str, Any] = field(default_factory=lambda: dict(_DEFAULT_PARAMETERS))

    def __post_init__(self) -> None:
        if not isinstance(self.tool_id, str) or not self.tool_id.strip():
            raise CoreError("TOOL_INVALID", "tool ID is required")
        if not isinstance(self.description, str) or not self.description.strip():
            raise CoreError("TOOL_INVALID", "tool description is required")
        if self.required_capabilities != tuple(sorted(set(self.required_capabilities))):
            raise CoreError("TOOL_INVALID", "required capabilities must be sorted and unique")
        if not isinstance(self.parameters, Mapping):
            raise CoreError("TOOL_INVALID", "tool parameters must be a JSON-schema mapping")
        object.__setattr__(self, "parameters", dict(self.parameters))

    def to_function_schema(self) -> dict[str, Any]:
        """Return the provider-neutral function description used by tool-capable harnesses."""
        return {
            "name": self.tool_id,
            "description": self.description,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class ToolCall:
    tool_id: str
    arguments: Mapping[str, Any]
    call_id: str = field(default_factory=lambda: CoreIdentity.new("toolcall").value)
    resource_scope: str | None = None


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    tool_id: str
    ok: bool
    value: Any = None
    error: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool_id": self.tool_id,
            "ok": self.ok,
            "value": self.value,
            "error": dict(self.error or {}) if self.error is not None else None,
        }
