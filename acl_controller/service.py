"""Pass-1 Controller façade.

This service exposes intake, state, exact profile resolution, and explicit action
routing. It is not yet the workflow engine.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from acl_core import CoreServices
from acl_core.diagnostics import emit

from .configuration import ProfileResolver, ProfileSelector, RoleProfile
from .diagnostics import controller_span
from .models import ControllerStatus, RequestRecord, WorkflowRecord, WorkflowStatus
from .routing import ActionRegistry, ActionRequest, ActionResponse
from .state import JsonWorkflowStore, WorkflowStateService


class ControllerService:
    component = "controller.service"

    def __init__(
        self,
        *,
        core: CoreServices,
        state: WorkflowStateService,
        profiles: ProfileResolver,
        routing: ActionRegistry,
    ) -> None:
        self.core = core
        self.state = state
        self.profiles = profiles
        self.routing = routing

    @classmethod
    def create(
        cls,
        *,
        state_root: Path,
        config_root: Path,
        core: CoreServices | None = None,
    ) -> "ControllerService":
        with controller_span(
            "service.create",
            state_root=str(Path(state_root).expanduser()),
            config_root=str(Path(config_root).expanduser()),
        ):
            resolved_core = core or CoreServices.create()
            service = cls(
                core=resolved_core,
                state=WorkflowStateService(JsonWorkflowStore(state_root)),
                profiles=ProfileResolver(config_root),
                routing=ActionRegistry(),
            )
            emit(
                "INFO",
                cls.component,
                "create",
                "controller_created",
                state_root=str(Path(state_root).expanduser().resolve()),
                config_root=str(Path(config_root).expanduser().resolve()),
            )
            return service

    def create_workflow(
        self,
        request_kind: str,
        payload: Mapping[str, Any],
        *,
        requester: str | None = None,
    ) -> WorkflowRecord:
        request = RequestRecord.create(request_kind, payload, requester=requester)
        workflow = WorkflowRecord.create(request)
        with controller_span(
            "service.create_workflow",
            workflow_id=workflow.workflow_id,
            request_id=request.request_id,
            request_kind=request_kind,
            requester=requester,
        ):
            return self.state.create(workflow)

    def status(self, workflow_id: str) -> ControllerStatus:
        with controller_span("service.status", workflow_id=workflow_id):
            return ControllerStatus(self.state.read(workflow_id))

    def transition(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        **changes: Any,
    ) -> WorkflowRecord:
        with controller_span("service.transition", workflow_id=workflow_id, target_status=str(status)):
            return self.state.transition(workflow_id, status, **changes)

    def resolve_profile(
        self,
        *,
        role: str,
        work_type: str,
        complexity: str | None = None,
    ) -> RoleProfile:
        with controller_span(
            "service.resolve_profile",
            role=role,
            work_type=work_type,
            complexity=complexity,
        ):
            profile = self.profiles.resolve(ProfileSelector(role, work_type, complexity))
            emit(
                "INFO",
                self.component,
                "resolve_profile",
                "profile_resolved",
                role=role,
                work_type=work_type,
                complexity=complexity,
                profile_id=profile.profile_id,
                adapter_id=profile.adapter_id,
            )
            return profile

    def register_action(self, action_type: str, handler) -> None:
        with controller_span("service.register_action", action_type=action_type):
            self.routing.register(action_type, handler)

    def route_action(self, request: ActionRequest) -> ActionResponse:
        with controller_span(
            "service.route_action",
            workflow_id=request.workflow_id,
            action_id=request.action_id,
            action_type=request.action_type,
            role=request.role,
            profile_id=request.profile_id,
        ):
            # Existence check keeps action records tied to known Controller state.
            workflow = self.state.read(request.workflow_id)
            emit(
                "DEBUG",
                self.component,
                "route_action",
                "workflow_route_context",
                workflow_id=workflow.workflow_id,
                workflow_status=str(workflow.status),
                workflow_stage=workflow.stage,
                action_id=request.action_id,
                action_type=request.action_type,
            )
            return self.routing.dispatch(request)
