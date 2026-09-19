"""Generic AI-role dispatch through ACL Core adapters.

Controller supplies a selected profile and opaque role input. The adapter handles
provider/harness transport. Controller interprets only the small role envelope.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from acl_core import AdapterRequest, AuthorityGrant, CoreIdentity, CoreServices
from acl_core.diagnostics import emit

from ..configuration import RoleProfile
from ..diagnostics import controller_span
from ..errors import ControllerError


class RoleStatus(StrEnum):
    COMPLETE = "COMPLETE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NEEDS_CONTINUATION = "NEEDS_CONTINUATION"
    NEEDS_RETRY = "NEEDS_RETRY"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RoleDispatchRequest:
    workflow_id: str
    role: str
    profile: RoleProfile
    payload: Mapping[str, Any]
    grant: AuthorityGrant | None = None
    operation: str = "role.invoke"
    attempt_id: str = field(default_factory=lambda: CoreIdentity.new("attempt").value)

    def to_adapter_payload(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "attempt_id": self.attempt_id,
            "role": self.role,
            "profile": self.profile.to_dict(),
            "input": dict(self.payload),
            "authority_grant": None if self.grant is None else self.grant.to_dict(),
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
            role_response = self._parse_response(request, envelope)
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
    def _parse_response(
        request: RoleDispatchRequest,
        value: Mapping[str, Any],
    ) -> RoleDispatchResponse:
        status_raw = value.get("status")
        try:
            status = RoleStatus(status_raw)
        except (TypeError, ValueError) as exc:
            raise ControllerError(
                "CONTROLLER_ROLE_RESPONSE_INVALID",
                "role response has an unsupported status",
                {
                    "workflow_id": request.workflow_id,
                    "attempt_id": request.attempt_id,
                    "observed_status": status_raw,
                },
            ) from exc
        payload = value.get("payload", {})
        if not isinstance(payload, Mapping):
            raise ControllerError(
                "CONTROLLER_ROLE_RESPONSE_INVALID",
                "role response payload must be a mapping",
                {"workflow_id": request.workflow_id, "attempt_id": request.attempt_id},
            )
        reference = value.get("reference")
        if reference is not None and not isinstance(reference, str):
            raise ControllerError(
                "CONTROLLER_ROLE_RESPONSE_INVALID",
                "role response reference must be text when present",
            )
        metadata = value.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ControllerError(
                "CONTROLLER_ROLE_RESPONSE_INVALID",
                "role response metadata must be a mapping",
            )
        return RoleDispatchResponse(
            workflow_id=request.workflow_id,
            attempt_id=request.attempt_id,
            role=request.role,
            profile_id=request.profile.profile_id,
            status=status,
            payload=dict(payload),
            reference=reference,
            metadata=dict(metadata),
        )
