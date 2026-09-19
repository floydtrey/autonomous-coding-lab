"""Canonical request envelope delivered to an ACL AI role."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from acl_core.canonical import canonical_digest

from .context import RoleContext
from .instructions import InstructionSet


ROLE_REQUEST_SCHEMA = "acl-role-request:v1"


@dataclass(frozen=True)
class RoleRequest:
    workflow_id: str
    attempt_id: str
    role: str
    profile_id: str
    objective: Mapping[str, Any]
    context: RoleContext = field(default_factory=RoleContext)
    instructions: InstructionSet | None = None
    authority_grant_id: str | None = None
    tool_ids: tuple[str, ...] = ()
    execution: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.workflow_id, "workflow_id"),
            (self.attempt_id, "attempt_id"),
            (self.role, "role"),
            (self.profile_id, "profile_id"),
        ):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"{label} must be trimmed nonblank text")
        if not isinstance(self.objective, Mapping):
            raise ValueError("objective must be a mapping")
        if not isinstance(self.execution, Mapping) or not isinstance(self.metadata, Mapping):
            raise ValueError("execution and metadata must be mappings")
        if self.authority_grant_id is not None and (
            not isinstance(self.authority_grant_id, str) or not self.authority_grant_id.strip()
        ):
            raise ValueError("authority_grant_id must be nonblank text when present")
        if self.tool_ids != tuple(sorted(set(self.tool_ids))):
            raise ValueError("tool_ids must be sorted and unique")
        if any(not isinstance(item, str) or not item.strip() for item in self.tool_ids):
            raise ValueError("tool_ids must contain nonblank text")

    @classmethod
    def create(
        cls,
        *,
        workflow_id: str,
        attempt_id: str,
        role: str,
        profile_id: str,
        objective: Mapping[str, Any],
        context: RoleContext | None = None,
        instructions: InstructionSet | None = None,
        authority_grant_id: str | None = None,
        tool_ids: Sequence[str] = (),
        execution: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "RoleRequest":
        return cls(
            workflow_id=workflow_id,
            attempt_id=attempt_id,
            role=role,
            profile_id=profile_id,
            objective=dict(objective),
            context=context or RoleContext(),
            instructions=instructions,
            authority_grant_id=authority_grant_id,
            tool_ids=tuple(sorted(set(tool_ids))),
            execution=dict(execution or {}),
            metadata=dict(metadata or {}),
        )

    def to_dict(self, *, include_instruction_content: bool = True) -> dict[str, Any]:
        return {
            "schema_version": ROLE_REQUEST_SCHEMA,
            "workflow_id": self.workflow_id,
            "attempt_id": self.attempt_id,
            "role": self.role,
            "profile_id": self.profile_id,
            "objective": dict(self.objective),
            "context": self.context.to_dict(),
            "instructions": (
                None
                if self.instructions is None
                else self.instructions.to_dict(include_content=include_instruction_content)
            ),
            "authority_grant_id": self.authority_grant_id,
            "tool_ids": list(self.tool_ids),
            "execution": dict(self.execution),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RoleRequest":
        if not isinstance(value, Mapping) or value.get("schema_version") != ROLE_REQUEST_SCHEMA:
            raise ValueError("role request schema is invalid")
        instructions_raw = value.get("instructions")
        instructions = None
        if instructions_raw is not None:
            if not isinstance(instructions_raw, Mapping):
                raise ValueError("instructions must be a mapping")
            content = instructions_raw.get("content")
            if not isinstance(content, Mapping):
                raise ValueError("instruction content is required for role execution")
            instructions = InstructionSet(
                instruction_set_id=instructions_raw["instruction_set_id"],
                version=instructions_raw.get("version"),
                content=dict(content),
                metadata=dict(instructions_raw.get("metadata", {})),
            )
        tools = value.get("tool_ids", [])
        if not isinstance(tools, list):
            raise ValueError("tool_ids must be a list")
        return cls.create(
            workflow_id=value["workflow_id"],
            attempt_id=value["attempt_id"],
            role=value["role"],
            profile_id=value["profile_id"],
            objective=dict(value["objective"]),
            context=RoleContext.from_mapping(value.get("context")),
            instructions=instructions,
            authority_grant_id=value.get("authority_grant_id"),
            tool_ids=tools,
            execution=dict(value.get("execution", {})),
            metadata=dict(value.get("metadata", {})),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())
