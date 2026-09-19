"""Generic target/resource identities.

Locators are opaque to Core. A later adapter decides whether a locator means a
file path, service resource, Git object, video asset, API object, or something else.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..canonical import canonical_digest
from ..errors import CoreError


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CoreError("RESOURCE_INVALID", f"{label} must be trimmed nonblank text")
    return value


@dataclass(frozen=True)
class ResourceRef:
    resource_id: str
    adapter_id: str
    kind: str
    locator: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required_text(self.resource_id, "resource ID")
        _required_text(self.adapter_id, "adapter ID")
        _required_text(self.kind, "resource kind")
        _required_text(self.locator, "resource locator")

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "adapter_id": self.adapter_id,
            "kind": self.kind,
            "locator": self.locator,
            "metadata": dict(self.metadata),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class TargetRef:
    target_id: str
    resources: tuple[ResourceRef, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required_text(self.target_id, "target ID")
        ids = tuple(item.resource_id for item in self.resources)
        if len(ids) != len(set(ids)):
            raise CoreError("RESOURCE_INVALID", "target contains duplicate resource IDs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "resources": [item.to_dict() for item in self.resources],
            "metadata": dict(self.metadata),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())
