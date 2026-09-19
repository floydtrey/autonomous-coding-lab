"""Controller bridge for Worker V1 runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acl_roles.common import RoleResponse
from acl_roles.worker import (
    WorkerRuntimeBackend,
    WorkerRuntimeRequest,
    WorkerRuntimeResponse,
    parse_worker_role_response,
)

from ..authority import AuthorityCoordinator
from ..configuration import ProfileResolver, ProfileSelector
from ..diagnostics import controller_span
from ..dispatch import RoleDispatchRequest, RoleDispatcher
from ..errors import ControllerError
from ..models import WorkflowStatus
from ..state import WorkflowStateService


@dataclass
class ControllerWorkerRuntimeBackend:
    state: WorkflowStateService
    profiles: ProfileResolver
    role_dispatch: RoleDispatcher
    authority: AuthorityCoordinator
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
            grant = (
                None
                if request.authority_grant_id is None
                else self.authority.grant(request.authority_grant_id)
            )
            dispatch_request = RoleDispatchRequest(
                workflow_id=request.workflow_id,
                role="worker",
                profile=profile,
                payload=request.worker_input.to_objective(),
                grant=grant,
            )

            workflow = self.state.read(request.workflow_id)
            if workflow.status is not WorkflowStatus.READY:
                raise ControllerError(
                    "CONTROLLER_WORKER_RUN_STATE_INVALID",
                    "Worker Pass may start only from a READY workflow",
                    {
                        "workflow_id": request.workflow_id,
                        "status": str(workflow.status),
                        "stage": workflow.stage,
                    },
                )
            self.state.transition(
                request.workflow_id,
                WorkflowStatus.RUNNING,
                stage=f"worker:{request.worker_input.pass_id}",
                active_action="role.invoke",
                active_role="worker",
                active_profile_id=profile.profile_id,
                active_attempt_id=dispatch_request.attempt_id,
                waiting_for=None,
                blocker=None,
            )

            dispatched = self.role_dispatch.dispatch(dispatch_request)
            common_response = RoleResponse(
                status=dispatched.status,
                payload=dict(dispatched.payload),
                reference=dispatched.reference,
                metadata=dict(dispatched.metadata),
            )
            result = parse_worker_role_response(common_response)
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
