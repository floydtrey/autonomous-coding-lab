"""Role instruction-set identity.

Instructions remain externally supplied/configured. This contract gives them a
stable identity and digest without making Core or Controller own prompt content.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from acl_core.canonical import canonical_digest


@dataclass(frozen=True)
class InstructionSet:
    instruction_set_id: str
    content: Mapping[str, Any]
    version: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.instruction_set_id, str) or not self.instruction_set_id.strip():
            raise ValueError("instruction_set_id is required")
        if self.version is not None and (not isinstance(self.version, str) or not self.version.strip()):
            raise ValueError("instruction version must be nonblank text when present")
        if not isinstance(self.content, Mapping) or not isinstance(self.metadata, Mapping):
            raise ValueError("instruction content and metadata must be mappings")

    @classmethod
    def from_profile(
        cls,
        *,
        profile_id: str,
        instructions: Mapping[str, Any],
    ) -> "InstructionSet":
        return cls(
            instruction_set_id=f"profile:{profile_id}",
            content=dict(instructions),
            metadata={"source": "role-profile", "profile_id": profile_id},
        )

    def to_dict(self, *, include_content: bool = True) -> dict[str, Any]:
        value = {
            "instruction_set_id": self.instruction_set_id,
            "version": self.version,
            "digest": self.digest(),
            "metadata": dict(self.metadata),
        }
        if include_content:
            value["content"] = dict(self.content)
        return value

    def digest(self) -> str:
        return canonical_digest({
            "instruction_set_id": self.instruction_set_id,
            "version": self.version,
            "content": dict(self.content),
            "metadata": dict(self.metadata),
        })
