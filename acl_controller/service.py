"""ACL Next Controller façade.

This service composes Core, workflow state, external profile resolution, explicit
action routing, role dispatch, authority, clarification, approval gates, retry
budgets, the mechanical workflow engine, conservative recovery, and read-only
inspection. AI role reasoning remains outside Controller.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from acl_core import AuthorityEnvelope, AuthorityRequest, CoreServices
from acl_core.diagnostics import emit

from .authority import AuthorityCoordinator, JsonGrantStore
from .clarification import ClarificationRecord, ClarificationService, JsonClarificationStore
from .configuration import ProfileResolver, ProfileSelector, RoleProfile
from .dispatch import RoleDispatchRequest, RoleDispatchResponse, RoleDispatcher
from .gates import GateRecord, GateService, JsonGateStore
from .inspection import InspectionReport, InspectionService
from .recovery import JsonStopStore, RecoveryService, StopRecord
from .retries import JsonRetryStore, RetryBudget, RetryRecord, RetryService
from .workflow import (
    EngineReport,
    JsonProgramStore,
    JsonResultStore,
    WorkflowEngine,
    WorkflowProgram,
)
from .diagnostics import controller_span
from .errors import ControllerError
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
        role_dispatch: RoleDispatcher,
        authority: AuthorityCoordinator,
        clarification: ClarificationService,
        gates: GateService,
        retries: RetryService,
        engine: WorkflowEngine,
        recovery: RecoveryService,
        inspection: InspectionService,
    ) -> None:
        self.core = core
        self.state = state
        self.profiles = profiles
        self.routing = routing
        self.role_dispatch = role_dispatch
        self.authority = authority
        self.clarification = clarification
        self.gates = gates
        self.retries = retries
        self.engine = engine
        self.recovery = recovery
        self.inspection = inspection

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
            state_root = Path(state_root).expanduser().resolve()
            config_root = Path(config_root).expanduser().resolve()

            state_service = WorkflowStateService(JsonWorkflowStore(state_root))
            profiles = ProfileResolver(config_root)
            routing = ActionRegistry()
            role_dispatch = RoleDispatcher(resolved_core)
            authority = AuthorityCoordinator(
                resolved_core.authority,
                JsonGrantStore(state_root),
            )
            clarification = ClarificationService(
                state_service,
                JsonClarificationStore(state_root),
            )
            gates = GateService(
                state_service,
                JsonGateStore(state_root),
            )
            retries = RetryService(
                state_service,
                JsonRetryStore(state_root),
            )
            programs = JsonProgramStore(state_root)
            results = JsonResultStore(state_root)
            engine = WorkflowEngine(
                state=state_service,
                profiles=profiles,
                routing=routing,
                role_dispatch=role_dispatch,
                authority=authority,
                clarification=clarification,
                gates=gates,
                retries=retries,
                programs=programs,
                results=results,
            )
            stops = JsonStopStore(state_root)
            recovery = RecoveryService(
                core=resolved_core,
                state=state_service,
                profiles=profiles,
                engine=engine,
                stops=stops,
            )
            inspection = InspectionService(
                state=state_service,
                programs=programs,
                results=results,
                authority=authority,
                profiles=profiles,
                clarification=clarification,
                gates=gates,
                retries=retries,
                stops=stops,
            )
            service = cls(
                core=resolved_core,
                state=state_service,
                profiles=profiles,
                routing=routing,
                role_dispatch=role_dispatch,
                authority=authority,
                clarification=clarification,
                gates=gates,
                retries=retries,
                engine=engine,
                recovery=recovery,
                inspection=inspection,
            )
            emit(
                "INFO",
                cls.component,
                "create",
                "controller_created",
                state_root=str(state_root),
                config_root=str(config_root),
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


    def issue_authority(
        self,
        workflow_id: str,
        *,
        ceiling: AuthorityEnvelope,
        request: AuthorityRequest,
        issuer: str,
        subject: str,
    ):
        with controller_span(
            "service.issue_authority",
            workflow_id=workflow_id,
            issuer=issuer,
            subject=subject,
        ):
            workflow = self.state.read(workflow_id)
            grant = self.authority.issue(
                ceiling=ceiling,
                request=request,
                issuer=issuer,
                subject=subject,
            )
            self.state.transition(
                workflow_id,
                workflow.status,
                authority_grant_id=grant.grant_id,
            )
            return grant

    def narrow_authority(
        self,
        workflow_id: str,
        parent_grant_id: str,
        *,
        request: AuthorityRequest,
        issuer: str,
        subject: str,
    ):
        with controller_span(
            "service.narrow_authority",
            workflow_id=workflow_id,
            grant_id=parent_grant_id,
            issuer=issuer,
            subject=subject,
        ):
            workflow = self.state.read(workflow_id)
            grant = self.authority.narrow(
                parent_grant_id,
                request=request,
                issuer=issuer,
                subject=subject,
            )
            self.state.transition(
                workflow_id,
                workflow.status,
                authority_grant_id=grant.grant_id,
            )
            return grant

    def dispatch_role(
        self,
        workflow_id: str,
        *,
        role: str,
        work_type: str,
        payload: Mapping[str, Any],
        complexity: str | None = None,
        grant_id: str | None = None,
        operation: str = "role.invoke",
    ) -> RoleDispatchResponse:
        with controller_span(
            "service.dispatch_role",
            workflow_id=workflow_id,
            grant_id=grant_id,
            role=role,
            work_type=work_type,
            complexity=complexity,
            operation=operation,
        ):
            workflow = self.state.read(workflow_id)
            if grant_id is not None and workflow.authority_grant_id != grant_id:
                raise ControllerError(
                    "CONTROLLER_WORKFLOW_GRANT_MISMATCH",
                    "role dispatch grant differs from the workflow's active grant",
                    {
                        "workflow_id": workflow_id,
                        "workflow_grant_id": workflow.authority_grant_id,
                        "requested_grant_id": grant_id,
                    },
                )
            profile = self.resolve_profile(
                role=role,
                work_type=work_type,
                complexity=complexity,
            )
            grant = None if grant_id is None else self.authority.grant(grant_id)
            request = RoleDispatchRequest(
                workflow_id=workflow_id,
                role=role,
                profile=profile,
                payload=payload,
                grant=grant,
                operation=operation,
            )
            return self.role_dispatch.dispatch(request)

    def request_clarification(
        self,
        workflow_id: str,
        *,
        requested_by: str,
        questions,
        context: Mapping[str, Any] | None = None,
    ) -> ClarificationRecord:
        return self.clarification.request(
            workflow_id,
            requested_by=requested_by,
            questions=questions,
            context=context,
        )

    def answer_clarification(
        self,
        clarification_id: str,
        *,
        answer: Mapping[str, Any],
        answered_by: str,
    ) -> ClarificationRecord:
        return self.clarification.answer(
            clarification_id,
            answer=answer,
            answered_by=answered_by,
        )

    def request_gate(
        self,
        workflow_id: str,
        *,
        gate_type: str,
        requested_by: str,
        payload: Mapping[str, Any],
    ) -> GateRecord:
        return self.gates.request(
            workflow_id,
            gate_type=gate_type,
            requested_by=requested_by,
            payload=payload,
        )

    def decide_gate(
        self,
        gate_id: str,
        *,
        approved: bool,
        decision_by: str,
        note: str | None = None,
    ) -> GateRecord:
        return self.gates.decide(
            gate_id,
            approved=approved,
            decision_by=decision_by,
            note=note,
        )

    def configure_retry_budget(
        self,
        workflow_id: str,
        budget: RetryBudget,
    ) -> RetryRecord:
        return self.retries.configure(workflow_id, budget)

    def request_retry(
        self,
        workflow_id: str,
        *,
        budget: RetryBudget,
        requested_by: str,
        reason: str | None = None,
    ) -> RetryRecord:
        return self.retries.request_retry(
            workflow_id,
            budget=budget,
            requested_by=requested_by,
            reason=reason,
        )

    def request_continuation(
        self,
        workflow_id: str,
        *,
        budget: RetryBudget,
        requested_by: str,
        reason: str | None = None,
    ) -> RetryRecord:
        return self.retries.request_continuation(
            workflow_id,
            budget=budget,
            requested_by=requested_by,
            reason=reason,
        )


    def install_program(self, program: WorkflowProgram) -> WorkflowProgram:
        with controller_span("service.install_program", program_id=program.program_id):
            return self.engine.install_program(program)

    def bind_program(self, workflow_id: str, program_id: str) -> WorkflowRecord:
        with controller_span(
            "service.bind_program",
            workflow_id=workflow_id,
            program_id=program_id,
        ):
            return self.engine.bind_program(workflow_id, program_id)

    def run_workflow(
        self,
        workflow_id: str,
        *,
        max_operations: int = 32,
    ) -> EngineReport:
        with controller_span(
            "service.run_workflow",
            workflow_id=workflow_id,
            max_operations=max_operations,
        ):
            return self.engine.run(workflow_id, max_operations=max_operations)

    def stop_workflow(
        self,
        workflow_id: str,
        *,
        requested_by: str,
    ) -> StopRecord:
        with controller_span(
            "service.stop_workflow",
            workflow_id=workflow_id,
            requested_by=requested_by,
        ):
            return self.recovery.request_stop(
                workflow_id,
                requested_by=requested_by,
            )

    def recover_workflow(self, workflow_id: str):
        with controller_span("service.recover_workflow", workflow_id=workflow_id):
            return self.recovery.recover(workflow_id)

    def inspect_workflow(self, workflow_id: str) -> InspectionReport:
        with controller_span("service.inspect_workflow", workflow_id=workflow_id):
            return self.inspection.inspect(workflow_id)
