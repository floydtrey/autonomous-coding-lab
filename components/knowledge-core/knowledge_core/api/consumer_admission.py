from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, HTTPException, Security
from fastapi.security import APIKeyHeader

from knowledge_core.api.bootstrap_admission import BOOTSTRAP_KEY_HEADER, BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapOperation
from knowledge_core.application.authorization import AuthorizationKernel
from knowledge_core.application.principal_auth import (
    PrincipalAuthenticationError,
    PrincipalAuthenticationKernel,
)
from knowledge_core.domain.authorization import KCOperation
from knowledge_core.domain.principals import PrincipalType


@dataclass(frozen=True)
class ConsumerPrincipalContext:
    principal_ref: UUID
    principal_code: str
    principal_type: PrincipalType
    scope_ref: UUID | None
    is_bootstrap_owner: bool = False

    @property
    def caller_principal_ref(self) -> str:
        return str(self.principal_ref)


_OPERATION_MAP = {
    KCOperation.STATUS: BootstrapOperation.STATUS,
    KCOperation.SEARCH: BootstrapOperation.SEARCH,
    KCOperation.GET_SOURCE: BootstrapOperation.GET_SOURCE,
    KCOperation.STORE: BootstrapOperation.STORE,
    KCOperation.MEMORY_PROPOSE: BootstrapOperation.MEMORY_PROPOSE,
}


class ConsumerAdmission:
    """Authenticate consumer requests and bind optional active KC scope.

    The owner bootstrap key is retained only as a migration/owner path. Service
    clients authenticate with durable kc1 credentials. Successful authentication
    proves identity only; authorization is evaluated separately against KC-B grants.
    """

    def __init__(
        self,
        *,
        session_factory,
        owner_bootstrap: BootstrapAdmission | None = None,
        owner_principal_code: str = "OWNER",
    ) -> None:
        self.session_factory = session_factory
        self.owner_bootstrap = owner_bootstrap
        self.owner_principal_code = owner_principal_code

    def ensure_owner_principal(self):
        if self.owner_bootstrap is None:
            return None
        with self.session_factory() as session:
            return PrincipalAuthenticationKernel(session).ensure_owner_principal(
                principal_code=self.owner_principal_code,
            )

    @staticmethod
    def _parse_scope_ref(scope_header: str | None) -> UUID | None:
        if scope_header is None or not scope_header.strip():
            return None
        try:
            return UUID(scope_header.strip())
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="X-Knowledge-Scope must be a valid KC scope UUID",
            ) from exc

    def authenticate(
        self,
        *,
        supplied_key: str | None,
        scope_header: str | None,
        operation: KCOperation,
    ) -> ConsumerPrincipalContext:
        if supplied_key is None or not supplied_key:
            raise HTTPException(status_code=401, detail="authentication failed")

        scope_ref = self._parse_scope_ref(scope_header)

        if self.owner_bootstrap is not None and not supplied_key.startswith("kc1."):
            bootstrap_operation = _OPERATION_MAP.get(operation)
            if bootstrap_operation is None:
                raise HTTPException(
                    status_code=403,
                    detail="bootstrap operation is not allowed",
                )
            self.owner_bootstrap.admit(
                supplied_key=supplied_key,
                operation=bootstrap_operation,
            )
            with self.session_factory() as session:
                owner = PrincipalAuthenticationKernel(session).read_principal_by_code(
                    self.owner_principal_code
                )
                if scope_ref is not None:
                    AuthorizationKernel(session).read_scope(scope_ref)
                return ConsumerPrincipalContext(
                    principal_ref=owner.principal_ref,
                    principal_code=owner.principal_code,
                    principal_type=owner.principal_type,
                    scope_ref=scope_ref,
                    is_bootstrap_owner=True,
                )

        with self.session_factory() as session:
            try:
                principal = PrincipalAuthenticationKernel(
                    session
                ).authenticate_service_token(supplied_key)
            except PrincipalAuthenticationError as exc:
                raise HTTPException(status_code=401, detail="authentication failed") from exc

            authz = AuthorizationKernel(session)
            if scope_ref is not None:
                try:
                    authz.read_scope(scope_ref)
                except KeyError as exc:
                    raise HTTPException(
                        status_code=404,
                        detail="knowledge scope is unavailable",
                    ) from exc

            decision = authz.evaluate(
                principal_ref=principal.principal_ref,
                operation=operation,
            )
            if not decision.allowed:
                raise HTTPException(
                    status_code=403,
                    detail="operation is not authorized",
                )

            return ConsumerPrincipalContext(
                principal_ref=principal.principal_ref,
                principal_code=principal.principal_code,
                principal_type=principal.principal_type,
                scope_ref=scope_ref,
                is_bootstrap_owner=False,
            )

    def require_scope_access(
        self,
        *,
        context: ConsumerPrincipalContext,
        operation: KCOperation,
    ):
        if context.scope_ref is None:
            raise HTTPException(
                status_code=400,
                detail="X-Knowledge-Scope is required for this operation",
            )
        with self.session_factory() as session:
            authz = AuthorizationKernel(session)
            decision = authz.evaluate(
                principal_ref=context.principal_ref,
                operation=operation,
                scope_ref=context.scope_ref,
            )
            if not decision.allowed:
                raise HTTPException(
                    status_code=403,
                    detail="scope is not authorized for this operation",
                )
            return authz.project_scope_for(context.scope_ref)


_api_key_header = APIKeyHeader(name=BOOTSTRAP_KEY_HEADER, auto_error=False)


def consumer_principal_dependency(
    admission: ConsumerAdmission,
    *,
    operation: KCOperation,
):
    async def dependency(
        supplied_key: str | None = Security(_api_key_header),
        x_knowledge_scope: str | None = Header(
            default=None,
            alias="X-Knowledge-Scope",
        ),
    ) -> ConsumerPrincipalContext:
        return admission.authenticate(
            supplied_key=supplied_key,
            scope_header=x_knowledge_scope,
            operation=operation,
        )

    return dependency
