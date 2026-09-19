"""Canonical response envelope returned by an ACL AI role."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from acl_core.canonical import canonical_digest


ROLE_RESPONSE_SCHEMA = "acl-role-response:v1"


class RoleStatus(StrEnum):
    COMPLETE = "COMPLETE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NEEDS_CONTINUATION = "NEEDS_CONTINUATION"
    NEEDS_RETRY = "NEEDS_RETRY"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RoleResponse:
    status: RoleStatus
    payload: Mapping[str, Any] = field(default_factory=dict)
    reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.payload, Mapping) or not isinstance(self.metadata, Mapping):
            raise ValueError("role response payload and metadata must be mappings")
        if self.reference is not None and not isinstance(self.reference, str):
            raise ValueError("role response reference must be text when present")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ROLE_RESPONSE_SCHEMA,
            "status": str(self.status),
            "payload": dict(self.payload),
            "reference": self.reference,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RoleResponse":
        if not isinstance(value, Mapping):
            raise ValueError("role response must be a mapping")
        schema = value.get("schema_version")
        if schema not in (None, ROLE_RESPONSE_SCHEMA):
            raise ValueError("role response schema is unsupported")
        return cls(
            status=RoleStatus(value["status"]),
            payload=dict(value.get("payload", {})),
            reference=value.get("reference"),
            metadata=dict(value.get("metadata", {})),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())
