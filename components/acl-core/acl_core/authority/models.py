"""Provider- and role-neutral authority contracts."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from ..canonical import canonical_digest
from ..errors import CoreError


def _clean(values: Iterable[str], label: str) -> tuple[str, ...]:
    result = tuple(sorted(set(values)))
    if any(not isinstance(item, str) or not item.strip() or item != item.strip() for item in result):
        raise CoreError("AUTHORITY_INVALID", f"{label} contains invalid values")
    return result


@dataclass(frozen=True)
class AuthorityEnvelope:
    capabilities: tuple[str, ...] = ()
    resource_scopes: tuple[str, ...] = ()
    tool_scopes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "capabilities", _clean(self.capabilities, "capabilities"))
        object.__setattr__(self, "resource_scopes", _clean(self.resource_scopes, "resource scopes"))
        object.__setattr__(self, "tool_scopes", _clean(self.tool_scopes, "tool scopes"))

    def to_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def contains(self, other: "AuthorityEnvelope") -> bool:
        return (
            set(other.capabilities) <= set(self.capabilities)
            and set(other.resource_scopes) <= set(self.resource_scopes)
            and set(other.tool_scopes) <= set(self.tool_scopes)
        )


@dataclass(frozen=True)
class AuthorityRequest(AuthorityEnvelope):
    reason: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.reason, str):
            raise CoreError("AUTHORITY_INVALID", "authority reason must be text")

    def envelope(self) -> AuthorityEnvelope:
        return AuthorityEnvelope(self.capabilities, self.resource_scopes, self.tool_scopes)


@dataclass(frozen=True)
class AuthorityGrant:
    grant_id: str
    issuer: str
    subject: str
    authority: AuthorityEnvelope
    parent_digest: str | None = None

    def __post_init__(self) -> None:
        for value, label in ((self.grant_id, "grant ID"), (self.issuer, "issuer"), (self.subject, "subject")):
            if not isinstance(value, str) or not value.strip():
                raise CoreError("AUTHORITY_INVALID", f"{label} is required")

    def to_dict(self) -> dict:
        return {
            "grant_id": self.grant_id,
            "issuer": self.issuer,
            "subject": self.subject,
            "authority": self.authority.to_dict(),
            "parent_digest": self.parent_digest,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def allows_capability(self, capability: str) -> bool:
        return capability in self.authority.capabilities

    def allows_resource(self, scope: str) -> bool:
        return scope in self.authority.resource_scopes

    def allows_tool(self, tool_id: str) -> bool:
        return tool_id in self.authority.tool_scopes
