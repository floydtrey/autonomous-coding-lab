"""Controller handoff to ACL Core authority.

Controller persists grant references for workflow recovery but Core remains the
authority mechanism. Controller cannot enlarge a supplied ceiling or parent grant.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock

from acl_core import AuthorityEnvelope, AuthorityGrant, AuthorityRequest, AuthorityService
from acl_core.canonical import canonical_json
from acl_core.diagnostics import emit

from ..diagnostics import controller_span
from ..errors import ControllerError


class JsonGrantStore:
    component = "controller.grants"

    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def save(self, grant: AuthorityGrant) -> AuthorityGrant:
        with controller_span("grants.save", grant_id=grant.grant_id):
            path = self._path(grant.grant_id)
            with self._lock:
                if path.exists():
                    existing = self.read(grant.grant_id)
                    if existing.digest() != grant.digest():
                        raise ControllerError(
                            "CONTROLLER_GRANT_CONFLICT",
                            "grant ID already exists with different authority",
                            {"grant_id": grant.grant_id},
                        )
                    return existing
                self._write(path, grant)
            return grant

    def read(self, grant_id: str) -> AuthorityGrant:
        with controller_span("grants.read", grant_id=grant_id):
            path = self._path(grant_id)
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError as exc:
                raise ControllerError(
                    "CONTROLLER_GRANT_MISSING",
                    "authority grant is not persisted",
                    {"grant_id": grant_id},
                ) from exc
            except (OSError, json.JSONDecodeError) as exc:
                raise ControllerError(
                    "CONTROLLER_GRANT_READ_FAILED",
                    "authority grant could not be read",
                    {"grant_id": grant_id},
                ) from exc
            try:
                authority = value["authority"]
                return AuthorityGrant(
                    grant_id=value["grant_id"],
                    issuer=value["issuer"],
                    subject=value["subject"],
                    authority=AuthorityEnvelope(
                        capabilities=tuple(authority.get("capabilities", ())),
                        resource_scopes=tuple(authority.get("resource_scopes", ())),
                        tool_scopes=tuple(authority.get("tool_scopes", ())),
                    ),
                    parent_digest=value.get("parent_digest"),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ControllerError(
                    "CONTROLLER_GRANT_INVALID",
                    "persisted authority grant is malformed",
                    {"grant_id": grant_id},
                ) from exc

    def _path(self, grant_id: str) -> Path:
        if not isinstance(grant_id, str) or not grant_id.startswith("grant:"):
            raise ControllerError("CONTROLLER_GRANT_INVALID", "grant ID is invalid")
        return self.root / "grants" / f"{grant_id.replace(':', '_')}.json"

    @staticmethod
    def _write(path: Path, grant: AuthorityGrant) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        try:
            temp.write_text(canonical_json(grant.to_dict()) + "\n", encoding="utf-8")
            os.replace(temp, path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ControllerError(
                "CONTROLLER_GRANT_WRITE_FAILED",
                "authority grant could not be persisted",
                {"grant_id": grant.grant_id, "path": str(path)},
            ) from exc


class AuthorityCoordinator:
    component = "controller.authority"

    def __init__(self, authority: AuthorityService, store: JsonGrantStore) -> None:
        self.authority = authority
        self.store = store

    def issue(
        self,
        *,
        ceiling: AuthorityEnvelope,
        request: AuthorityRequest,
        issuer: str,
        subject: str,
    ) -> AuthorityGrant:
        with controller_span(
            "authority.issue",
            issuer=issuer,
            subject=subject,
            requested_capabilities=list(request.capabilities),
            requested_resources=list(request.resource_scopes),
            requested_tools=list(request.tool_scopes),
        ):
            grant = self.authority.issue(
                ceiling,
                request,
                issuer=issuer,
                subject=subject,
            )
            self.store.save(grant)
            emit(
                "INFO",
                self.component,
                "issue",
                "authority_grant_issued",
                grant_id=grant.grant_id,
                issuer=issuer,
                subject=subject,
                grant_digest=grant.digest(),
                authority=grant.authority.to_dict(),
            )
            return grant

    def narrow(
        self,
        parent_grant_id: str,
        *,
        request: AuthorityRequest,
        issuer: str,
        subject: str,
    ) -> AuthorityGrant:
        with controller_span(
            "authority.narrow",
            grant_id=parent_grant_id,
            issuer=issuer,
            subject=subject,
            requested_capabilities=list(request.capabilities),
            requested_resources=list(request.resource_scopes),
            requested_tools=list(request.tool_scopes),
        ):
            parent = self.store.read(parent_grant_id)
            child = self.authority.narrow(
                parent,
                request,
                issuer=issuer,
                subject=subject,
            )
            self.store.save(child)
            emit(
                "INFO",
                self.component,
                "narrow",
                "authority_grant_narrowed",
                parent_grant_id=parent.grant_id,
                parent_digest=parent.digest(),
                grant_id=child.grant_id,
                grant_digest=child.digest(),
                authority=child.authority.to_dict(),
            )
            return child

    def grant(self, grant_id: str) -> AuthorityGrant:
        return self.store.read(grant_id)
