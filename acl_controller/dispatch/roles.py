"""Generic AI-role dispatch through ACL Core adapters.

Controller supplies a selected profile and opaque role input. The adapter handles
provider/harness transport. Controller interprets only the small role envelope.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from acl_core import AdapterRequest, AuthorityGrant, CoreIdentity, CoreServices
from acl_core.diagnostics import emit
from acl_roles.common import InstructionSet, RoleDiagnostics, RoleRequest, RoleResponse, RoleStatus, normalize_configured_response, validate_configured_response

from ..configuration import RoleProfile
from ..diagnostics import controller_span
from ..errors import ControllerError


@dataclass(frozen=True)
class RoleDispatchRequest:
    workflow_id: str
    role: str
    profile: RoleProfile
    payload: Mapping[str, Any]
    grant: AuthorityGrant | None = None
    operation: str = "role.invoke"
    attempt_id: str = field(default_factory=lambda: CoreIdentity.new("attempt").value)

    def to_role_request(self) -> RoleRequest:
        instructions = InstructionSet.from_profile(
            profile_id=self.profile.profile_id,
            instructions=self.profile.instructions,
        )
        return RoleRequest.create(
            workflow_id=self.workflow_id,
            attempt_id=self.attempt_id,
            role=self.role,
            profile_id=self.profile.profile_id,
            objective=dict(self.payload),
            instructions=instructions,
            authority_grant_id=None if self.grant is None else self.grant.grant_id,
            tool_ids=() if self.grant is None else self.grant.authority.tool_scopes,
            execution=self.profile.settings,
            metadata={
                "adapter_id": self.profile.adapter_id,
                "tool_profile": self.profile.tool_profile,
                "profile_metadata": dict(self.profile.metadata),
                "operation": self.operation,
            },
        )

    def to_adapter_payload(self) -> dict[str, Any]:
        role_request = self.to_role_request()
        return {
            "role_request": role_request.to_dict(),
            "authority": {
                "grant_id": None if self.grant is None else self.grant.grant_id,
                "grant_digest": None if self.grant is None else self.grant.digest(),
                "authority": None if self.grant is None else self.grant.authority.to_dict(),
            },
        }


@dataclass(frozen=True)
class RoleDispatchResponse:
    workflow_id: str
    attempt_id: str
    role: str
    profile_id: str
    status: RoleStatus
    payload: Mapping[str, Any]
    reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "attempt_id": self.attempt_id,
            "role": self.role,
            "profile_id": self.profile_id,
            "status": str(self.status),
            "payload": dict(self.payload),
            "reference": self.reference,
            "metadata": dict(self.metadata),
        }


class RoleDispatcher:
    component = "controller.role_dispatch"

    def __init__(self, core: CoreServices) -> None:
        self.core = core

    def dispatch(self, request: RoleDispatchRequest) -> RoleDispatchResponse:
        with controller_span(
            "role_dispatch.dispatch",
            workflow_id=request.workflow_id,
            attempt_id=request.attempt_id,
            grant_id=None if request.grant is None else request.grant.grant_id,
            role=request.role,
            profile_id=request.profile.profile_id,
            adapter_id=request.profile.adapter_id,
            operation=request.operation,
        ):
            if request.profile.role != request.role:
                raise ControllerError(
                    "CONTROLLER_ROLE_PROFILE_MISMATCH",
                    "selected profile does not belong to the requested role",
                    {
                        "role": request.role,
                        "profile_id": request.profile.profile_id,
                        "profile_role": request.profile.role,
                    },
                )
            role_request = request.to_role_request()
            RoleDiagnostics.invocation(
                role_request,
                adapter_id=request.profile.adapter_id,
            )
            adapter_request = AdapterRequest(
                operation=request.operation,
                payload=request.to_adapter_payload(),
                metadata={
                    "workflow_id": request.workflow_id,
                    "attempt_id": request.attempt_id,
                    "role": request.role,
                    "profile_id": request.profile.profile_id,
                    "grant_id": None if request.grant is None else request.grant.grant_id,
                },
            )
            emit(
                "INFO",
                self.component,
                "dispatch",
                "role_dispatch_started",
                workflow_id=request.workflow_id,
                attempt_id=request.attempt_id,
                role=request.role,
                profile_id=request.profile.profile_id,
                adapter_id=request.profile.adapter_id,
                adapter_request_id=adapter_request.request_id,
                grant_id=None if request.grant is None else request.grant.grant_id,
            )
            response = self.core.adapters.invoke(request.profile.adapter_id, adapter_request)
            if not response.ok:
                RoleDiagnostics.adapter_error(
                    role_request,
                    adapter_id=request.profile.adapter_id,
                    error=dict(response.error or {}),
                )
                raise ControllerError(
                    "CONTROLLER_ROLE_ADAPTER_FAILED",
                    "role adapter returned failure",
                    {
                        "workflow_id": request.workflow_id,
                        "attempt_id": request.attempt_id,
                        "role": request.role,
                        "profile_id": request.profile.profile_id,
                        "adapter_id": request.profile.adapter_id,
                        "adapter_error": dict(response.error or {}),
                    },
                )
            envelope = self.core.normalization.mapping(response.payload)
            normalizer = request.profile.metadata.get("response_normalizer")
            try:
                envelope, normalization = normalize_configured_response(
                    envelope,
                    implementation=normalizer,
                    instructions=request.profile.instructions,
                    profile_metadata=request.profile.metadata,
                )
            except Exception as exc:
                RoleDiagnostics.parse_error(
                    workflow_id=request.workflow_id,
                    attempt_id=request.attempt_id,
                    role=request.role,
                    profile_id=request.profile.profile_id,
                    adapter_id=request.profile.adapter_id,
                    raw_response=envelope,
                    error=exc,
                )
                cause_details = {}
                to_dict = getattr(exc, "to_dict", None)
                if callable(to_dict):
                    try:
                        cause_details = to_dict()
                    except Exception:
                        cause_details = {}
                raise ControllerError(
                    "CONTROLLER_ROLE_RESPONSE_INVALID",
                    "role response normalization failed",
                    {
                        "workflow_id": request.workflow_id,
                        "attempt_id": request.attempt_id,
                        "role": request.role,
                        "profile_id": request.profile.profile_id,
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                        "cause": cause_details,
                    },
                ) from exc
            try:
                common_response = RoleResponse.from_mapping(envelope)
            except Exception as exc:
                RoleDiagnostics.parse_error(
                    workflow_id=request.workflow_id,
                    attempt_id=request.attempt_id,
                    role=request.role,
                    profile_id=request.profile.profile_id,
                    adapter_id=request.profile.adapter_id,
                    raw_response=envelope,
                    error=exc,
                )
                cause_details = {}
                to_dict = getattr(exc, "to_dict", None)
                if callable(to_dict):
                    try:
                        cause_details = to_dict()
                    except Exception:
                        cause_details = {}
                raise ControllerError(
                    "CONTROLLER_ROLE_RESPONSE_INVALID",
                    "role response does not match the common role contract",
                    {
                        "workflow_id": request.workflow_id,
                        "attempt_id": request.attempt_id,
                        "role": request.role,
                        "profile_id": request.profile.profile_id,
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                        "cause": cause_details,
                        "normalized_keys": sorted(str(key) for key in envelope),
                    },
                ) from exc
            validator = request.profile.metadata.get("response_validator")
            try:
                validation = validate_configured_response(
                    common_response,
                    implementation=validator,
                    instructions=request.profile.instructions,
                    profile_metadata=request.profile.metadata,
                    request=role_request,
                )
            except Exception as exc:
                RoleDiagnostics.parse_error(
                    workflow_id=request.workflow_id,
                    attempt_id=request.attempt_id,
                    role=request.role,
                    profile_id=request.profile.profile_id,
                    adapter_id=request.profile.adapter_id,
                    raw_response=envelope,
                    error=exc,
                )
                cause_details = {}
                to_dict = getattr(exc, "to_dict", None)
                if callable(to_dict):
                    try:
                        cause_details = to_dict()
                    except Exception:
                        cause_details = {}
                raise ControllerError(
                    "CONTROLLER_ROLE_RESPONSE_INVALID",
                    "role-specific response validation failed",
                    {
                        "workflow_id": request.workflow_id,
                        "attempt_id": request.attempt_id,
                        "role": request.role,
                        "profile_id": request.profile.profile_id,
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                        "cause": cause_details,
                    },
                ) from exc
            if validation:
                common_response = RoleResponse(
                    status=common_response.status,
                    payload=common_response.payload,
                    reference=common_response.reference,
                    metadata={
                        **dict(common_response.metadata),
                        "role_validation": validation,
                    },
                )
            RoleDiagnostics.response(
                role_request,
                common_response,
                adapter_id=request.profile.adapter_id,
                normalization=normalization,
            )
            role_response = self.from_common_response(request, common_response)
            emit(
                "INFO",
                self.component,
                "dispatch",
                "role_dispatch_finished",
                workflow_id=request.workflow_id,
                attempt_id=request.attempt_id,
                role=request.role,
                profile_id=request.profile.profile_id,
                status=str(role_response.status),
                reference=role_response.reference,
            )
            return role_response

    @staticmethod
    def from_common_response(
        request: RoleDispatchRequest,
        response: RoleResponse,
    ) -> RoleDispatchResponse:
        return RoleDispatchResponse(
            workflow_id=request.workflow_id,
            attempt_id=request.attempt_id,
            role=request.role,
            profile_id=request.profile.profile_id,
            status=response.status,
            payload=dict(response.payload),
            reference=response.reference,
            metadata=dict(response.metadata),
        )

    @staticmethod
    def parse_response(
        request: RoleDispatchRequest,
        value: Mapping[str, Any],
    ) -> RoleDispatchResponse:
        """Compatibility parser used by recovery for already-normalized responses."""
        try:
            response = RoleResponse.from_mapping(value)
        except Exception as exc:
            RoleDiagnostics.parse_error(
                workflow_id=request.workflow_id,
                attempt_id=request.attempt_id,
                role=request.role,
                profile_id=request.profile.profile_id,
                adapter_id=request.profile.adapter_id,
                raw_response=value,
                error=exc,
            )
            raise ControllerError(
                "CONTROLLER_ROLE_RESPONSE_INVALID",
                "role response does not match the common role contract",
                {
                    "workflow_id": request.workflow_id,
                    "attempt_id": request.attempt_id,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
            ) from exc
        return RoleDispatcher.from_common_response(request, response)
