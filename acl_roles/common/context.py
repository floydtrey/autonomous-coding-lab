"""Provider-neutral context references passed into AI roles."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from acl_core.canonical import canonical_digest


@dataclass(frozen=True)
class ContextReference:
    reference_id: str
    kind: str
    reference: str
    digest: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.reference_id, "reference_id"),
            (self.kind, "kind"),
            (self.reference, "reference"),
        ):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"{label} must be trimmed nonblank text")
        if self.digest is not None and (not isinstance(self.digest, str) or not self.digest.strip()):
            raise ValueError("digest must be nonblank text when present")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be a mapping")

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "kind": self.kind,
            "reference": self.reference,
            "digest": self.digest,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ContextReference":
        if not isinstance(value, Mapping):
            raise ValueError("context reference must be a mapping")
        return cls(
            reference_id=value["reference_id"],
            kind=value["kind"],
            reference=value["reference"],
            digest=value.get("digest"),
            metadata=dict(value.get("metadata", {})),
        )


@dataclass(frozen=True)
class RoleContext:
    references: tuple[ContextReference, ...] = ()
    inline: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.inline, Mapping):
            raise ValueError("inline context must be a mapping")
        ids = tuple(item.reference_id for item in self.references)
        if len(ids) != len(set(ids)):
            raise ValueError("context reference IDs must be unique")

    @classmethod
    def create(
        cls,
        *,
        references: Sequence[ContextReference] = (),
        inline: Mapping[str, Any] | None = None,
    ) -> "RoleContext":
        return cls(tuple(references), dict(inline or {}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "references": [item.to_dict() for item in self.references],
            "inline": dict(self.inline),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "RoleContext":
        value = value or {}
        if not isinstance(value, Mapping):
            raise ValueError("role context must be a mapping")
        references = value.get("references", [])
        if not isinstance(references, list):
            raise ValueError("context references must be a list")
        return cls(
            references=tuple(ContextReference.from_mapping(item) for item in references),
            inline=dict(value.get("inline", {})),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())
