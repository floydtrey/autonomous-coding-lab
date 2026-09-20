"""Tool registry with mechanical grant enforcement."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..authority import AuthorityGrant, AuthorityService
from ..diagnostics import span
from ..errors import CoreError
from .models import ToolCall, ToolDefinition, ToolResult


ToolHandler = Callable[[ToolCall, AuthorityGrant], Any]


class ToolRegistry:
    component = "core.tools"

    def __init__(self, authority: AuthorityService | None = None) -> None:
        self._authority = authority or AuthorityService()
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> ToolDefinition:
        with span(self.component, "register", tool_id=definition.tool_id):
            if not callable(handler):
                raise CoreError("TOOL_INVALID", "tool handler must be callable")
            existing = self._definitions.get(definition.tool_id)
            if existing is not None and existing != definition:
                raise CoreError("TOOL_CONFLICT", "tool ID is already registered differently")
            self._definitions[definition.tool_id] = definition
            self._handlers[definition.tool_id] = handler
            return definition

    def definition(self, tool_id: str) -> ToolDefinition:
        with span(self.component, "definition", tool_id=tool_id):
            try:
                return self._definitions[tool_id]
            except KeyError as exc:
                raise CoreError("TOOL_MISSING", "tool is not registered", {"tool_id": tool_id}) from exc

    def invoke(self, call: ToolCall, grant: AuthorityGrant) -> ToolResult:
        with span(
            self.component,
            "invoke",
            tool_id=call.tool_id,
            call_id=call.call_id,
            grant_id=grant.grant_id,
            resource_scope=call.resource_scope,
        ):
            definition = self.definition(call.tool_id)
            self._authority.require_tool(grant, call.tool_id)
            for capability in definition.required_capabilities:
                self._authority.require_capability(grant, capability)
            if call.resource_scope is not None:
                self._authority.require_resource(grant, call.resource_scope)
            try:
                value = self._handlers[call.tool_id](call, grant)
            except CoreError:
                raise
            except Exception as exc:
                raise CoreError(
                    "TOOL_EXECUTION_FAILED",
                    "tool handler raised an exception",
                    {"tool_id": call.tool_id, "exception_type": type(exc).__name__, "message": str(exc)},
                ) from exc
            return ToolResult(call.call_id, call.tool_id, True, value=value)

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))
