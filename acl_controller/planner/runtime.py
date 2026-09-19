"""Controller bridge for the generic Planner runtime port.

This bridge selects an externally configured Planner profile and dispatches it
through the existing generic role/adapter boundary. It contains no provider,
model, server, harness, Git, GitHub, or machine-path assumptions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acl_roles.common import RoleResponse
from acl_roles.planner import (
    PlannerRuntimeBackend,
    PlannerRuntimeRequest,
    PlannerRuntimeResponse,
    parse_planner_role_response,
)

from ..authority import AuthorityCoordinator
from ..configuration import ProfileResolver, ProfileSelector
from ..diagnostics import controller_span
from ..dispatch import RoleDispatchRequest, RoleDispatcher
from ..errors import ControllerError


@dataclass
class ControllerPlannerRuntimeBackend:
    profiles: ProfileResolver
    role_dispatch: RoleDispatcher
    authority: AuthorityCoordinator
    backend_id: str = "controller.role-dispatch"

    def invoke(self, request: PlannerRuntimeRequest) -> PlannerRuntimeResponse:
        with controller_span(
            "planner_runtime.invoke",
            workflow_id=request.workflow_id,
            backend_id=self.backend_id,
            work_type_id=request.work_type_id,
            complexity=request.complexity,
        ):
            profile = self.profiles.resolve(
                ProfileSelector(
                    role="planner",
                    work_type=request.work_type_id,
                    complexity=request.complexity,
                )
            )
            grant = (
                None
                if request.authority_grant_id is None
                else self.authority.grant(request.authority_grant_id)
            )
            dispatched = self.role_dispatch.dispatch(
                RoleDispatchRequest(
                    workflow_id=request.workflow_id,
                    role="planner",
                    profile=profile,
                    payload=request.planner_input.to_objective(),
                    grant=grant,
                )
            )

            common_response = RoleResponse(
                status=dispatched.status,
                payload=dict(dispatched.payload),
                reference=dispatched.reference,
                metadata=dict(dispatched.metadata),
            )
            result = parse_planner_role_response(common_response)
            self.role_dispatch.complete_runtime(
                request.workflow_id,
                dispatched.attempt_id,
            )
            adapter_telemetry = dispatched.metadata.get("adapter_telemetry")
            adapter_telemetry = (
                dict(adapter_telemetry)
                if isinstance(adapter_telemetry, dict)
                else {}
            )
            return PlannerRuntimeResponse(
                result=result,
                runtime_metadata={
                    "backend_id": self.backend_id,
                    "attempt_id": dispatched.attempt_id,
                    "profile_id": dispatched.profile_id,
                    "adapter_id": profile.adapter_id,
                    "tool_profile": profile.tool_profile,
                    "profile_metadata": dict(profile.metadata),
                    "model": adapter_telemetry.get("model"),
                    "runtime_family": adapter_telemetry.get("runtime_family"),
                    "reference": dispatched.reference,
                    "role_metadata": dict(dispatched.metadata),
                },
            )


def require_planner_runtime_backend(value: Any) -> PlannerRuntimeBackend:
    if not isinstance(value, PlannerRuntimeBackend):
        raise ControllerError(
            "CONTROLLER_PLANNER_RUNTIME_INVALID",
            "Planner runtime backend does not implement the required runtime port",
        )
    return value
