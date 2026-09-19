"""ACL Next Controller façade.

This service composes Core, workflow state, external profile resolution, explicit
action routing, role dispatch, authority, clarification, approval gates, retry
budgets, the mechanical workflow engine, conservative recovery, and read-only
inspection. AI role reasoning remains outside Controller.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from acl_core import AuthorityEnvelope, AuthorityRequest, CoreServices, FilesystemOperation
from acl_roles.worker import WorkerRuntimeService
from acl_roles.planner import (
    ExecutionPlan,
    PlannerDisposition,
    PlannerCorrectionPolicy,
    PlannerInput,
    PlannerResult,
    PlannerRuntimeRequest,
    PlannerRuntimeResponse,
    PlannerRuntimeService,
    build_planner_correction_input,
    correction_signature,
    load_planner_correction_policy,
    planner_previous_response_from_error,
    resume_planner_input,
)
from acl_core.diagnostics import emit
from acl_adapters import AdapterLoader

from .authority import AuthorityCoordinator, FilesystemAuthorityCoordinator, JsonGrantStore
from .clarification import ClarificationRecord, ClarificationService, ClarificationStatus, JsonClarificationStore
from .configuration import ProfileResolver, ProfileSelector, RoleProfile
from .dispatch import RoleDispatchRequest, RoleDispatchResponse, RoleDispatcher
from .gates import GateRecord, GateService, JsonGateStore
from .inspection import InspectionReport, InspectionService
from .planner import (
    ControllerPlannerRuntimeBackend,
    JsonPlannerConsultationStore,
    JsonPlannerPlanStore,
    JsonPlannerTelemetryStore,
    PlannerConsultationConfig,
    PlannerConsultationOutcome,
    PlannerConsultationRecord,
    PlannerConsultationService,
    PlannerDispositionOutcome,
    PlannerDispositionService,
    PlannerOutcomeStatus,
    PlannerNextPass,
    PlannerPlanIntakeOutcome,
    PlannerPlanRecord,
    PlannerPlanService,
    PlannerTelemetryConfig,
    PlannerTelemetryService,
)
from .recovery import JsonStopStore, RecoveryService, StopRecord
from .retries import JsonRetryStore, RetryBudget, RetryRecord, RetryService
from .worker import (
    ControllerWorkerRuntimeBackend,
    JsonWorkerRunStore,
    WorkerExecutionOutcome,
    WorkerExecutionService,
    WorkerRunRecord,
)
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
from .runtime import (
    JsonRuntimeCheckpointStore,
    RuntimeResidencyConfig,
    SerialRuntimeResidencyService,
)
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
        runtime_residency: SerialRuntimeResidencyService,
        authority: AuthorityCoordinator,
        filesystem_authority: FilesystemAuthorityCoordinator,
        planner_runtime: PlannerRuntimeService,
        worker_runtime: WorkerRuntimeService,
        worker_execution: WorkerExecutionService,
        planner_correction_policy: PlannerCorrectionPolicy,
        planner_disposition: PlannerDispositionService,
        planner_consultation: PlannerConsultationService,
        planner_plan: PlannerPlanService,
        planner_telemetry: PlannerTelemetryService,
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
        self.runtime_residency = runtime_residency
        self.authority = authority
        self.filesystem_authority = filesystem_authority
        self.planner_runtime = planner_runtime
        self.worker_runtime = worker_runtime
        self.worker_execution = worker_execution
        self.planner_correction_policy = planner_correction_policy
        self.planner_disposition = planner_disposition
        self.planner_consultation = planner_consultation
        self.planner_plan = planner_plan
        self.planner_telemetry = planner_telemetry
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
        project_root: Path | None = None,
        core: CoreServices | None = None,
        planner_runtime: PlannerRuntimeService | None = None,
        worker_runtime: WorkerRuntimeService | None = None,
    ) -> "ControllerService":
        with controller_span(
            "service.create",
            state_root=str(Path(state_root).expanduser()),
            config_root=str(Path(config_root).expanduser()),
        ):
            resolved_core = core or CoreServices.create()
            state_root = Path(state_root).expanduser().resolve()
            config_root = Path(config_root).expanduser().resolve()
            project_root = (
                config_root.parent
                if project_root is None
                else Path(project_root).expanduser().resolve()
            )
            loaded_adapters = AdapterLoader.load_file(
                resolved_core,
                config_root / "adapters.json",
            )

            state_service = WorkflowStateService(JsonWorkflowStore(state_root))
            profiles = ProfileResolver(config_root)
            routing = ActionRegistry()
            runtime_residency = SerialRuntimeResidencyService(
                config=RuntimeResidencyConfig.load(
                    config_root / "runtime_residency.json"
                ),
                store=JsonRuntimeCheckpointStore(state_root),
            )
            role_dispatch = RoleDispatcher(
                resolved_core,
                residency=runtime_residency,
            )
            authority = AuthorityCoordinator(
                resolved_core.authority,
                JsonGrantStore(state_root),
            )
            filesystem_authority = FilesystemAuthorityCoordinator.create(
                project_root=project_root,
                state_root=state_root,
                config_root=config_root,
            )
            resolved_planner_runtime = planner_runtime or PlannerRuntimeService(
                ControllerPlannerRuntimeBackend(
                    profiles=profiles,
                    role_dispatch=role_dispatch,
                    authority=authority,
                )
            )
            resolved_worker_runtime = worker_runtime or WorkerRuntimeService(
                ControllerWorkerRuntimeBackend(
                    state=state_service,
                    profiles=profiles,
                    role_dispatch=role_dispatch,
                    authority=authority,
                )
            )
            planner_correction_policy = load_planner_correction_policy(config_root)
            clarification = ClarificationService(
                state_service,
                JsonClarificationStore(state_root),
            )
            planner_disposition = PlannerDispositionService(
                state=state_service,
                clarification=clarification,
            )
            planner_telemetry = PlannerTelemetryService(
                config=PlannerTelemetryConfig.load(
                    config_root / "planner_telemetry.json"
                ),
                store=JsonPlannerTelemetryStore(state_root),
            )
            planner_consultation = PlannerConsultationService(
                state=state_service,
                runtime=resolved_planner_runtime,
                clarification=clarification,
                store=JsonPlannerConsultationStore(state_root),
                config=PlannerConsultationConfig.load(
                    config_root / "planner_consultation.json"
                ),
                telemetry=planner_telemetry,
                correction_policy=planner_correction_policy,
                runtime_residency=runtime_residency,
            )
            planner_plan = PlannerPlanService(
                state=state_service,
                store=JsonPlannerPlanStore(state_root),
                filesystem_authority=filesystem_authority,
            )
            worker_execution = WorkerExecutionService(
                state=state_service,
                planner_plan=planner_plan,
                runtime=resolved_worker_runtime,
                residency=runtime_residency,
                store=JsonWorkerRunStore(state_root),
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
                runtime_residency=runtime_residency,
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
                runtime_residency=runtime_residency,
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
                runtime_residency=runtime_residency,
                authority=authority,
                filesystem_authority=filesystem_authority,
                planner_runtime=resolved_planner_runtime,
                worker_runtime=resolved_worker_runtime,
                worker_execution=worker_execution,
                planner_correction_policy=planner_correction_policy,
                planner_disposition=planner_disposition,
                planner_consultation=planner_consultation,
                planner_plan=planner_plan,
                planner_telemetry=planner_telemetry,
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
                project_root=str(project_root),
                loaded_adapters=list(loaded_adapters),
                filesystem_authority_policy=str(filesystem_authority.policy_path),
                user_protected_path_count=len(filesystem_authority.service.user_protections),
                permanent_protected_path_count=len(filesystem_authority.service.permanent_protections),
            )
            return service

    def check_filesystem_authority(
        self,
        operation: FilesystemOperation | str,
        path: str | Path,
        *,
        destination: str | Path | None = None,
    ):
        """Evaluate path authority only; this does not judge Planner semantics."""
        return self.filesystem_authority.evaluate(
            operation,
            path,
            destination=destination,
        )

    def require_filesystem_authority(
        self,
        operation: FilesystemOperation | str,
        path: str | Path,
        *,
        destination: str | Path | None = None,
    ):
        """Raise when a requested filesystem operation crosses a deny boundary."""
        return self.filesystem_authority.require_allowed(
            operation,
            path,
            destination=destination,
        )

    def invoke_planner(
        self,
        workflow_id: str,
        *,
        planner_input: PlannerInput,
        grant_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> PlannerRuntimeResponse:
        """Invoke Planner through the provider-neutral runtime port."""
        workflow = self.state.read(workflow_id)
        if grant_id is not None and workflow.authority_grant_id != grant_id:
            raise ControllerError(
                "CONTROLLER_WORKFLOW_GRANT_MISMATCH",
                "Planner runtime grant differs from the workflow's active grant",
                {
                    "workflow_id": workflow_id,
                    "workflow_grant_id": workflow.authority_grant_id,
                    "requested_grant_id": grant_id,
                },
            )
        current_input = planner_input
        prior_error_signatures: list[str] = []
        correction_attempts = (
            0
            if planner_input.correction is None
            else planner_input.correction.attempt
        )

        while True:
            runtime_request = PlannerRuntimeRequest(
                workflow_id=workflow_id,
                planner_input=current_input,
                authority_grant_id=grant_id,
                metadata={
                    **dict(metadata or {}),
                    "runtime_backend_id": self.planner_runtime.backend.backend_id,
                    "correction_attempt": correction_attempts,
                },
            )
            try:
                response = self.planner_runtime.invoke(runtime_request)
            except Exception as exc:
                self.planner_telemetry.record_safely(runtime_request, error=exc)
                if (
                    correction_attempts
                    >= self.planner_correction_policy.max_correction_attempts
                ):
                    emit(
                        "ERROR",
                        self.component,
                        "invoke_planner",
                        "planner_correction_budget_exhausted",
                        workflow_id=workflow_id,
                        correction_attempts=correction_attempts,
                        max_correction_attempts=(
                            self.planner_correction_policy.max_correction_attempts
                        ),
                        exception_type=type(exc).__name__,
                        exception_message=str(exc),
                    )
                    raise

                previous_response = planner_previous_response_from_error(exc)
                if previous_response is None:
                    raise

                try:
                    corrected_input = build_planner_correction_input(
                        current_input,
                        previous_response=previous_response,
                        error=exc,
                        policy=self.planner_correction_policy,
                        attempt=correction_attempts + 1,
                        prior_error_signatures=tuple(prior_error_signatures),
                    )
                except Exception as correction_exc:
                    code = getattr(correction_exc, "code", None)
                    if code == "PLANNER_CORRECTION_NOT_REPAIRABLE":
                        raise exc
                    raise

                signature = correction_signature(corrected_input)
                if signature is not None:
                    prior_error_signatures.append(signature)
                correction_attempts += 1
                emit(
                    "INFO",
                    self.component,
                    "invoke_planner",
                    "planner_correction_retry",
                    workflow_id=workflow_id,
                    correction_attempt=correction_attempts,
                    max_correction_attempts=(
                        self.planner_correction_policy.max_correction_attempts
                    ),
                    error_code=corrected_input.correction.error_code,
                    repeated_failure=corrected_input.correction.repeated_failure,
                )
                current_input = corrected_input
                continue

            self.planner_telemetry.record_safely(
                runtime_request,
                response=response,
            )
            return response

    def run_planner(
        self,
        workflow_id: str,
        *,
        planner_input: PlannerInput,
        grant_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> PlannerDispositionOutcome:
        """Invoke Planner and apply only the current V1 disposition behavior.

        DIRECT_RESPONSE and QUERY_RESPONSE complete without Worker startup.
        ELEVATION_REQUIRED pauses on the shared clarification path.
        EXECUTION_PLAN is returned as PLAN_READY for PL10 intake.
        """
        workflow = self.state.read(workflow_id)
        if workflow.status is WorkflowStatus.NEW:
            self.state.transition(
                workflow_id,
                WorkflowStatus.READY,
                stage="planner",
                waiting_for=None,
                blocker=None,
            )
        elif workflow.status is not WorkflowStatus.READY:
            raise ControllerError(
                "CONTROLLER_PLANNER_RUN_STATE_INVALID",
                "Planner can only start from a NEW or READY workflow",
                {
                    "workflow_id": workflow_id,
                    "status": str(workflow.status),
                    "stage": workflow.stage,
                },
            )

        response = self.invoke_planner(
            workflow_id,
            planner_input=planner_input,
            grant_id=grant_id,
            metadata=metadata,
        )
        return self.planner_disposition.apply(
            workflow_id,
            planner_input=planner_input,
            response=response,
            authority_grant_id=grant_id,
        )

    def resume_planner_elevation(
        self,
        clarification_id: str,
        *,
        answer: Mapping[str, Any],
        answered_by: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> PlannerDispositionOutcome:
        """Answer a Planner elevation and resume the same Planner invocation."""
        current = self.clarification.read(clarification_id)
        context = current.context
        if context.get("kind") != "planner_elevation":
            raise ControllerError(
                "CONTROLLER_PLANNER_ELEVATION_INVALID",
                "clarification is not a Planner elevation",
                {"clarification_id": clarification_id},
            )

        try:
            original = PlannerInput.from_mapping(context["planner_input"])
            elevation = PlannerResult.from_mapping(context["planner_result"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_ELEVATION_INVALID",
                "Planner elevation context is incomplete or malformed",
                {"clarification_id": clarification_id},
            ) from exc

        resumed_input = resume_planner_input(
            original,
            elevation,
            answer,
        )

        if current.status is ClarificationStatus.PENDING:
            self.answer_clarification(
                clarification_id,
                answer=dict(answer),
                answered_by=answered_by,
            )
        elif current.status is ClarificationStatus.ANSWERED:
            if dict(current.answer or {}) != dict(answer):
                raise ControllerError(
                    "CONTROLLER_CLARIFICATION_ANSWER_CONFLICT",
                    "Planner elevation is already answered with a different response",
                    {
                        "clarification_id": clarification_id,
                        "recorded_answer": dict(current.answer or {}),
                        "requested_answer": dict(answer),
                    },
                )
        else:
            raise ControllerError(
                "CONTROLLER_PLANNER_ELEVATION_NOT_RESUMABLE",
                "Planner elevation cannot be resumed from its current state",
                {
                    "clarification_id": clarification_id,
                    "status": str(current.status),
                },
            )

        grant_id = context.get("authority_grant_id")
        if grant_id is not None and not isinstance(grant_id, str):
            raise ControllerError(
                "CONTROLLER_PLANNER_ELEVATION_INVALID",
                "stored Planner authority grant ID is invalid",
                {"clarification_id": clarification_id},
            )

        return self.run_planner(
            current.workflow_id,
            planner_input=resumed_input,
            grant_id=grant_id,
            metadata=metadata,
        )

    def start_planner_consultation(
        self,
        workflow_id: str,
        *,
        plan_id: str,
        pass_id: str,
        routing_context: Mapping[str, Any],
        question: str,
        reason: str,
        current_state_summary: str,
        task_id: str | None = None,
        relevant_reference_ids=(),
        relevant_evidence=(),
        grant_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> PlannerConsultationOutcome:
        """Start a bounded synthetic Worker-to-Planner consultation."""
        return self.planner_consultation.start(
            workflow_id,
            plan_id=plan_id,
            pass_id=pass_id,
            routing_context=routing_context,
            question=question,
            reason=reason,
            current_state_summary=current_state_summary,
            task_id=task_id,
            relevant_reference_ids=relevant_reference_ids,
            relevant_evidence=relevant_evidence,
            authority_grant_id=grant_id,
            metadata=metadata,
        )

    def continue_planner_consultation(
        self,
        consultation_id: str,
        *,
        question: str,
        reason: str,
        current_state_summary: str,
        task_id: str | None = None,
        relevant_reference_ids=(),
        relevant_evidence=(),
    ) -> PlannerConsultationOutcome:
        """Submit another Worker question within the consultation budget."""
        return self.planner_consultation.ask(
            consultation_id,
            question=question,
            reason=reason,
            current_state_summary=current_state_summary,
            task_id=task_id,
            relevant_reference_ids=relevant_reference_ids,
            relevant_evidence=relevant_evidence,
        )

    def resume_planner_consultation_elevation(
        self,
        clarification_id: str,
        *,
        answer: Mapping[str, Any],
        answered_by: str,
    ) -> PlannerConsultationOutcome:
        """Resume an elevated Worker-to-Planner exchange after operator input."""
        return self.planner_consultation.resume_elevation(
            clarification_id,
            answer=answer,
            answered_by=answered_by,
        )

    def planner_consultation_status(
        self,
        consultation_id: str,
    ) -> PlannerConsultationRecord:
        return self.planner_consultation.read(consultation_id)

    def close_planner_consultation(
        self,
        consultation_id: str,
    ) -> PlannerConsultationRecord:
        return self.planner_consultation.close(consultation_id)

    def intake_planner_plan(
        self,
        workflow_id: str,
        *,
        plan: ExecutionPlan,
        metadata: Mapping[str, Any] | None = None,
    ) -> PlannerPlanIntakeOutcome:
        """Persist an accepted Planner execution plan without starting a Worker."""
        return self.planner_plan.intake(
            workflow_id,
            plan=plan,
            metadata=metadata,
        )

    def intake_planner_outcome(
        self,
        outcome: PlannerDispositionOutcome,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> PlannerPlanIntakeOutcome:
        """Persist a PLAN_READY outcome returned by run_planner()."""
        if (
            outcome.status is not PlannerOutcomeStatus.PLAN_READY
            or outcome.disposition is not PlannerDisposition.EXECUTION_PLAN
            or outcome.plan is None
        ):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_MISSING",
                "Planner disposition outcome is not a PLAN_READY execution plan",
                {
                    "workflow_id": outcome.workflow_id,
                    "outcome_status": str(outcome.status),
                    "disposition": str(outcome.disposition),
                },
            )
        combined_metadata = {
            **dict(metadata or {}),
            "planner_runtime": dict(outcome.runtime_metadata),
        }
        return self.planner_plan.intake(
            outcome.workflow_id,
            plan=outcome.plan,
            metadata=combined_metadata,
        )

    def planner_plan_status(
        self,
        plan_id: str,
    ) -> PlannerPlanRecord:
        return self.planner_plan.read(plan_id)

    def planner_plan_for_workflow(
        self,
        workflow_id: str,
    ) -> PlannerPlanRecord | None:
        return self.planner_plan.for_workflow(workflow_id)

    def next_planner_pass(
        self,
        plan_id: str,
    ) -> PlannerNextPass:
        return self.planner_plan.next_pass(plan_id)

    def mark_planner_pass_complete(
        self,
        plan_id: str,
        pass_id: str,
    ) -> PlannerPlanRecord:
        return self.planner_plan.mark_pass_complete(plan_id, pass_id)

    def mark_planner_pass_failed(
        self,
        plan_id: str,
        pass_id: str,
        *,
        reason: str,
    ) -> PlannerPlanRecord:
        return self.planner_plan.mark_pass_failed(
            plan_id,
            pass_id,
            reason=reason,
        )

    def run_next_worker_pass(
        self,
        plan_id: str,
        *,
        grant_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> WorkerExecutionOutcome:
        """Execute the deterministic next Planner Pass through Worker V1."""
        return self.worker_execution.start_next_pass(
            plan_id,
            authority_grant_id=grant_id,
            metadata=metadata,
        )

    def continue_worker_pass(
        self,
        worker_run_id: str,
        *,
        guidance: Mapping[str, Any] | None = None,
        grant_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> WorkerExecutionOutcome:
        """Continue a Worker Pass after explicit continuation or Planner guidance."""
        return self.worker_execution.continue_pass(
            worker_run_id,
            guidance=guidance,
            authority_grant_id=grant_id,
            metadata=metadata,
        )

    def worker_run_status(self, worker_run_id: str) -> WorkerRunRecord:
        return self.worker_execution.read(worker_run_id)

    def worker_runs_for_pass(
        self,
        plan_id: str,
        pass_id: str,
    ) -> tuple[WorkerRunRecord, ...]:
        return self.worker_execution.runs_for_pass(plan_id, pass_id)

    def runtime_checkpoint(self, workflow_id: str):
        return self.runtime_residency.checkpoint(workflow_id)

    def planner_telemetry_records(self, workflow_id: str):
        return self.planner_telemetry.records(workflow_id)

    def planner_telemetry_summary(self, workflow_id: str) -> dict[str, Any]:
        return self.planner_telemetry.summary_safely(workflow_id)

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
        work_type: str | None,
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
        work_type: str | None,
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
