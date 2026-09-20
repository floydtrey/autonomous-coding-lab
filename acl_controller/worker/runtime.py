"""Controller bridge for the generic Worker runtime port.

This bridge mirrors the Planner runtime boundary: resolve the externally
configured profile, resolve the persisted authority grant, dispatch through the
generic role/adapter path, parse the Worker result, and release generic runtime
residency. Worker Pass/workflow lifecycle remains owned by the higher execution
service rather than this transport bridge.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acl_roles.common import RoleResponse
from acl_roles.worker import (
    WorkerOutcome,
    WorkerRuntimeBackend,
    WorkerRuntimeRequest,
    WorkerRuntimeResponse,
    parse_worker_role_response,
)

from ..authority import AuthorityCoordinator
from ..configuration import ProfileResolver, ProfileSelector
from ..diagnostics import controller_span
from ..dispatch import RoleAttemptLifecycleService, RoleDispatchRequest, RoleDispatcher
from ..errors import ControllerError


@dataclass
class ControllerWorkerRuntimeBackend:
    profiles: ProfileResolver
    role_dispatch: RoleDispatcher
    authority: AuthorityCoordinator
    lifecycle: RoleAttemptLifecycleService
    backend_id: str = "controller.role-dispatch"

    def invoke(self, request: WorkerRuntimeRequest) -> WorkerRuntimeResponse:
        with controller_span(
            "worker_runtime.invoke",
            workflow_id=request.workflow_id,
            backend_id=self.backend_id,
            plan_id=request.worker_input.plan_id,
            pass_id=request.worker_input.pass_id,
            work_type_id=request.work_type_id,
            complexity=request.complexity,
        ):
            profile = self.profiles.resolve(
                ProfileSelector(
                    role="worker",
                    work_type=request.work_type_id,
                    complexity=request.complexity,
                )
            )
            # Correction retries repair only the structured Worker report.
            # They must not re-expose execution tools or repeat side effects.
            grant = (
                None
                if request.worker_input.correction is not None
                or request.authority_grant_id is None
                else self.authority.grant(request.authority_grant_id)
            )
            dispatch_request = RoleDispatchRequest(
                workflow_id=request.workflow_id,
                role="worker",
                profile=profile,
                payload=request.worker_input.to_objective(),
                grant=grant,
            )
            self.lifecycle.begin(
                request.workflow_id,
                role="worker",
                profile_id=profile.profile_id,
                attempt_id=dispatch_request.attempt_id,
                stage=f"worker:{request.worker_input.pass_id}",
            )
            dispatched = self.role_dispatch.dispatch(dispatch_request)

            common_response = RoleResponse(
                status=dispatched.status,
                payload=dict(dispatched.payload),
                reference=dispatched.reference,
                metadata=dict(dispatched.metadata),
            )
            result = parse_worker_role_response(common_response)
            if result.outcome is WorkerOutcome.NEEDS_PLANNER:
                self.role_dispatch.pause_runtime_for_switch(
                    request.workflow_id,
                    dispatched.attempt_id,
                )
            else:
                self.role_dispatch.complete_runtime(
                    request.workflow_id,
                    dispatched.attempt_id,
                )
            self.lifecycle.release(
                request.workflow_id,
                attempt_id=dispatched.attempt_id,
            )

            adapter_telemetry = dispatched.metadata.get("adapter_telemetry")
            adapter_telemetry = (
                dict(adapter_telemetry)
                if isinstance(adapter_telemetry, dict)
                else {}
            )
            return WorkerRuntimeResponse(
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


def require_worker_runtime_backend(value: Any) -> WorkerRuntimeBackend:
    if not isinstance(value, WorkerRuntimeBackend):
        raise ControllerError(
            "CONTROLLER_WORKER_RUNTIME_INVALID",
            "Worker runtime backend does not implement the required runtime port",
        )
    return value
