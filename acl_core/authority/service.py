"""Mechanical authority issuance and narrowing.

This service never decides what authority a subject deserves. It only enforces
a ceiling supplied by a higher layer.
"""
from __future__ import annotations

from ..diagnostics import span
from ..errors import CoreError
from ..identity import CoreIdentity
from .models import AuthorityEnvelope, AuthorityGrant, AuthorityRequest


class AuthorityService:
    component = "core.authority"

    def issue(
        self,
        ceiling: AuthorityEnvelope,
        request: AuthorityRequest,
        *,
        issuer: str,
        subject: str,
        parent_digest: str | None = None,
    ) -> AuthorityGrant:
        with span(self.component, "issue", issuer=issuer, subject=subject):
            requested = request.envelope()
            if not ceiling.contains(requested):
                raise CoreError(
                    "AUTHORITY_EXPANSION_DENIED",
                    "requested authority exceeds the supplied ceiling",
                    {
                        "ceiling": ceiling.to_dict(),
                        "requested": requested.to_dict(),
                    },
                )
            return AuthorityGrant(
                grant_id=CoreIdentity.new("grant").value,
                issuer=issuer,
                subject=subject,
                authority=requested,
                parent_digest=parent_digest,
            )

    def narrow(
        self,
        parent: AuthorityGrant,
        request: AuthorityRequest,
        *,
        issuer: str,
        subject: str,
    ) -> AuthorityGrant:
        with span(self.component, "narrow", parent_grant_id=parent.grant_id, subject=subject):
            return self.issue(
                parent.authority,
                request,
                issuer=issuer,
                subject=subject,
                parent_digest=parent.digest(),
            )

    def require_capability(self, grant: AuthorityGrant, capability: str) -> None:
        with span(self.component, "require_capability", grant_id=grant.grant_id, capability=capability):
            if not grant.allows_capability(capability):
                raise CoreError("AUTHORITY_DENIED", "capability is not granted", {"capability": capability})

    def require_resource(self, grant: AuthorityGrant, scope: str) -> None:
        with span(self.component, "require_resource", grant_id=grant.grant_id, resource_scope=scope):
            if not grant.allows_resource(scope):
                raise CoreError("AUTHORITY_DENIED", "resource scope is not granted", {"resource_scope": scope})

    def require_tool(self, grant: AuthorityGrant, tool_id: str) -> None:
        with span(self.component, "require_tool", grant_id=grant.grant_id, tool_id=tool_id):
            if not grant.allows_tool(tool_id):
                raise CoreError("AUTHORITY_DENIED", "tool is not granted", {"tool_id": tool_id})
