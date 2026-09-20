"""Shared lifecycle tracking for direct role invocations.

WorkflowEngine already tracks active role attempts. Direct role paths such as
Planner/Worker runtimes can reuse this small service so recovery sees the same
generic workflow identity without embedding state logic in role implementations.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..errors import ControllerError
from ..models import WorkflowStatus
from ..state import WorkflowStateService


@dataclass
class RoleAttemptLifecycleService:
    state: WorkflowStateService

    def begin(
        self,
        workflow_id: str,
        *,
        role: str,
        profile_id: str,
        attempt_id: str,
        stage: str,
        action: str = "role.invoke",
    ):
        workflow = self.state.read(workflow_id)
        if workflow.status is WorkflowStatus.READY:
            return self.state.transition(
                workflow_id,
                WorkflowStatus.RUNNING,
                stage=stage,
                active_action=action,
                active_role=role,
                active_profile_id=profile_id,
                active_attempt_id=attempt_id,
                waiting_for=None,
                blocker=None,
            )
        if (
            workflow.status is WorkflowStatus.RUNNING
            and workflow.active_role == role
            and workflow.active_profile_id == profile_id
        ):
            # Same direct role may issue a correction attempt with a new attempt ID.
            return self.state.transition(
                workflow_id,
                WorkflowStatus.RUNNING,
                stage=stage,
                active_action=action,
                active_role=role,
                active_profile_id=profile_id,
                active_attempt_id=attempt_id,
                waiting_for=None,
                blocker=None,
            )
        raise ControllerError(
            "CONTROLLER_ROLE_ATTEMPT_STATE_INVALID",
            "direct role attempt cannot begin from the current workflow state",
            {
                "workflow_id": workflow_id,
                "status": str(workflow.status),
                "active_role": workflow.active_role,
                "active_profile_id": workflow.active_profile_id,
                "requested_role": role,
                "requested_profile_id": profile_id,
            },
        )

    def release(
        self,
        workflow_id: str,
        *,
        attempt_id: str,
        stage: str | None = None,
    ):
        workflow = self.state.read(workflow_id)
        if workflow.status is not WorkflowStatus.RUNNING:
            return workflow
        if workflow.active_attempt_id != attempt_id:
            raise ControllerError(
                "CONTROLLER_ROLE_ATTEMPT_MISMATCH",
                "cannot release a different active role attempt",
                {
                    "workflow_id": workflow_id,
                    "active_attempt_id": workflow.active_attempt_id,
                    "attempt_id": attempt_id,
                },
            )
        return self.state.transition(
            workflow_id,
            WorkflowStatus.READY,
            stage=workflow.stage if stage is None else stage,
            active_action=None,
            active_role=None,
            active_profile_id=None,
            active_attempt_id=None,
            waiting_for=None,
            blocker=None,
        )
