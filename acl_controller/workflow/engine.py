"""Mechanical Controller workflow engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from acl_core.diagnostics import emit

from ..authority import AuthorityCoordinator
from ..clarification import ClarificationService, ClarificationStatus
from ..configuration import ProfileResolver, ProfileSelector
from ..diagnostics import controller_span
from ..dispatch import RoleDispatchRequest, RoleDispatcher, RoleStatus
from ..errors import ControllerError
from ..gates import GateService, GateStatus
from ..models import ResultReference, TERMINAL_STATUSES, WorkflowRecord, WorkflowStatus
from ..retries import RetryBudget, RetryService
from ..routing import ActionRegistry, ActionRequest, ActionResponse
from ..state import WorkflowStateService
from .models import StepExecutor, WorkflowProgram, WorkflowStep
from .store import JsonProgramStore, JsonResultStore, StepResultRecord


@dataclass(frozen=True)
class EngineReport:
    workflow_id: str
    status: str
    stage: str
    operations: int
    waiting_for: str | None
    blocker: Mapping[str, Any] | None
    latest_result_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "stage": self.stage,
            "operations": self.operations,
            "waiting_for": self.waiting_for,
            "blocker": None if self.blocker is None else dict(self.blocker),
            "latest_result_id": self.latest_result_id,
        }


class WorkflowEngine:
    component = "controller.workflow"

    def __init__(
        self,
        *,
        state: WorkflowStateService,
        profiles: ProfileResolver,
        routing: ActionRegistry,
        role_dispatch: RoleDispatcher,
        authority: AuthorityCoordinator,
        clarification: ClarificationService,
        gates: GateService,
        retries: RetryService,
        programs: JsonProgramStore,
        results: JsonResultStore,
    ) -> None:
        self.state = state
        self.profiles = profiles
        self.routing = routing
        self.role_dispatch = role_dispatch
        self.authority = authority
        self.clarification = clarification
        self.gates = gates
        self.retries = retries
        self.programs = programs
        self.results = results

    def install_program(self, program: WorkflowProgram) -> WorkflowProgram:
        with controller_span("workflow.install_program", program_id=program.program_id):
            saved = self.programs.save(program)
            emit(
                "INFO",
                self.component,
                "install_program",
                "program_installed",
                program_id=saved.program_id,
                start_step=saved.start_step,
                step_count=len(saved.steps),
            )
            return saved

    def bind_program(self, workflow_id: str, program_id: str) -> WorkflowRecord:
        with controller_span("workflow.bind_program", workflow_id=workflow_id, program_id=program_id):
            program = self.programs.read(program_id)
            current = self.state.read(workflow_id)
            if current.program_id is not None:
                if current.program_id != program_id:
                    raise ControllerError(
                        "CONTROLLER_PROGRAM_ALREADY_BOUND",
                        "workflow is already bound to a different program",
                        {
                            "workflow_id": workflow_id,
                            "existing_program_id": current.program_id,
                            "requested_program_id": program_id,
                        },
                    )
                return current
            if current.status is not WorkflowStatus.NEW:
                raise ControllerError(
                    "CONTROLLER_PROGRAM_BIND_INVALID",
                    "program can only be initially bound to a new workflow",
                    {"workflow_id": workflow_id, "status": str(current.status)},
                )
            bound = self.state.transition(
                workflow_id,
                WorkflowStatus.READY,
                stage=program.start_step,
                program_id=program.program_id,
                active_action=None,
                active_role=None,
                active_profile_id=None,
                active_attempt_id=None,
                waiting_for=None,
                blocker=None,
            )
            emit(
                "INFO",
                self.component,
                "bind_program",
                "program_bound",
                workflow_id=workflow_id,
                program_id=program.program_id,
                start_step=program.start_step,
            )
            return bound

    def run(self, workflow_id: str, *, max_operations: int = 32) -> EngineReport:
        if isinstance(max_operations, bool) or not isinstance(max_operations, int) or max_operations <= 0:
            raise ControllerError("CONTROLLER_ENGINE_LIMIT_INVALID", "max_operations must be a positive integer")
        with controller_span("workflow.run", workflow_id=workflow_id, max_operations=max_operations):
            operations = 0
            latest_result_id = None
            while operations < max_operations:
                workflow = self.state.read(workflow_id)
                if workflow.status in TERMINAL_STATUSES or workflow.status in {
                    WorkflowStatus.WAITING,
                    WorkflowStatus.BLOCKED,
                }:
                    return self._report(workflow, operations, latest_result_id)
                if workflow.status is WorkflowStatus.RUNNING:
                    raise ControllerError(
                        "CONTROLLER_RECOVERY_REQUIRED",
                        "workflow has an active execution and must be recovered before advancing",
                        {
                            "workflow_id": workflow_id,
                            "stage": workflow.stage,
                            "active_attempt_id": workflow.active_attempt_id,
                            "active_action": workflow.active_action,
                        },
                    )
                if workflow.status is not WorkflowStatus.READY:
                    raise ControllerError(
                        "CONTROLLER_WORKFLOW_NOT_RUNNABLE",
                        "workflow is not ready for engine execution",
                        {"workflow_id": workflow_id, "status": str(workflow.status)},
                    )
                if workflow.program_id is None:
                    raise ControllerError(
                        "CONTROLLER_PROGRAM_MISSING",
                        "workflow has no bound program",
                        {"workflow_id": workflow_id},
                    )
                program = self.programs.read(workflow.program_id)
                step = program.step(workflow.stage)
                operations += 1
                emit(
                    "INFO",
                    self.component,
                    "run",
                    "step_started",
                    workflow_id=workflow_id,
                    program_id=program.program_id,
                    step_id=step.step_id,
                    executor=str(step.executor),
                    operation_number=operations,
                )
                if step.executor is StepExecutor.GATE:
                    if not self._execute_gate(workflow, program, step):
                        return self._report(self.state.read(workflow_id), operations, latest_result_id)
                    continue
                if step.executor is StepExecutor.ROLE:
                    result = self._execute_role(workflow, program, step)
                elif step.executor is StepExecutor.ACTION:
                    result = self._execute_action(workflow, program, step)
                else:
                    raise ControllerError(
                        "CONTROLLER_PROGRAM_INVALID",
                        "unsupported workflow step executor",
                        {"step_id": step.step_id, "executor": str(step.executor)},
                    )
                latest_result_id = result.result_id
                if not self._apply_result(program, step, result):
                    return self._report(self.state.read(workflow_id), operations, latest_result_id)
            workflow = self.state.read(workflow_id)
            emit(
                "INFO",
                self.component,
                "run",
                "operation_limit_reached",
                workflow_id=workflow_id,
                program_id=workflow.program_id,
                stage=workflow.stage,
                status=str(workflow.status),
                max_operations=max_operations,
            )
            return self._report(workflow, operations, latest_result_id)

    def consume_recovered_role_response(
        self,
        workflow_id: str,
        *,
        response_payload: Mapping[str, Any],
    ) -> EngineReport:
        with controller_span("workflow.consume_recovered_role_response", workflow_id=workflow_id):
            workflow = self.state.read(workflow_id)
            recoverable_status = (
                workflow.status is WorkflowStatus.RUNNING
                or (
                    workflow.status is WorkflowStatus.WAITING
                    and isinstance(workflow.waiting_for, str)
                    and workflow.waiting_for.startswith("stop:")
                )
            )
            if not recoverable_status or workflow.active_attempt_id is None:
                raise ControllerError(
                    "CONTROLLER_RECOVERY_INVALID",
                    "workflow has no recoverable active role execution",
                    {
                        "workflow_id": workflow_id,
                        "status": str(workflow.status),
                        "waiting_for": workflow.waiting_for,
                    },
                )
            if workflow.program_id is None:
                raise ControllerError("CONTROLLER_PROGRAM_MISSING", "workflow has no bound program")
            program = self.programs.read(workflow.program_id)
            step = program.step(workflow.stage)
            if step.executor is not StepExecutor.ROLE:
                raise ControllerError(
                    "CONTROLLER_RECOVERY_INVALID",
                    "active workflow step is not a role step",
                    {"workflow_id": workflow_id, "step_id": step.step_id},
                )
            normalized = self.role_dispatch.core.normalization.mapping(response_payload)
            fake_request = RoleDispatchRequest(
                workflow_id=workflow_id,
                role=step.role or "",
                profile=self.profiles.profile(workflow.active_profile_id or ""),
                payload={},
                grant=(
                    None
                    if workflow.authority_grant_id is None
                    else self.authority.grant(workflow.authority_grant_id)
                ),
                attempt_id=workflow.active_attempt_id,
            )
            response = self.role_dispatch.parse_response(fake_request, normalized)
            result = self._persist_result(
                workflow=workflow,
                program=program,
                step=step,
                executor="ROLE",
                execution_id=response.attempt_id,
                status=str(response.status),
                payload=response.payload,
                reference=response.reference,
                metadata=response.metadata,
            )
            self._apply_result(program, step, result)
            return self._report(self.state.read(workflow_id), 0, result.result_id)

    def _execute_role(
        self,
        workflow: WorkflowRecord,
        program: WorkflowProgram,
        step: WorkflowStep,
    ) -> StepResultRecord:
        profile = self.profiles.resolve(
            ProfileSelector(step.role or "", step.work_type or "", step.complexity)
        )
        grant = (
            None
            if workflow.authority_grant_id is None
            else self.authority.grant(workflow.authority_grant_id)
        )
        request = RoleDispatchRequest(
            workflow_id=workflow.workflow_id,
            role=step.role or "",
            profile=profile,
            payload=self._step_input(workflow, program, step),
            grant=grant,
        )
        self.state.transition(
            workflow.workflow_id,
            WorkflowStatus.RUNNING,
            stage=step.step_id,
            active_action="role.invoke",
            active_role=step.role,
            active_profile_id=profile.profile_id,
            active_attempt_id=request.attempt_id,
            waiting_for=None,
            blocker=None,
        )
        response = self.role_dispatch.dispatch(request)
        return self._persist_result(
            workflow=workflow,
            program=program,
            step=step,
            executor="ROLE",
            execution_id=response.attempt_id,
            status=str(response.status),
            payload=response.payload,
            reference=response.reference,
            metadata=response.metadata,
        )

    def _execute_action(
        self,
        workflow: WorkflowRecord,
        program: WorkflowProgram,
        step: WorkflowStep,
    ) -> StepResultRecord:
        request = ActionRequest(
            workflow_id=workflow.workflow_id,
            action_type=step.action_type or "",
            payload=self._step_input(workflow, program, step),
        )
        self.state.transition(
            workflow.workflow_id,
            WorkflowStatus.RUNNING,
            stage=step.step_id,
            active_action=step.action_type,
            active_role=None,
            active_profile_id=None,
            active_attempt_id=request.action_id,
            waiting_for=None,
            blocker=None,
        )
        response = self.routing.dispatch(request)
        try:
            status = RoleStatus(response.status)
        except (TypeError, ValueError) as exc:
            raise ControllerError(
                "CONTROLLER_ACTION_RESPONSE_INVALID",
                "action response has an unsupported workflow status",
                {
                    "workflow_id": workflow.workflow_id,
                    "step_id": step.step_id,
                    "action_type": step.action_type,
                    "status": response.status,
                },
            ) from exc
        payload = response.payload if isinstance(response.payload, Mapping) else {"value": response.payload}
        return self._persist_result(
            workflow=workflow,
            program=program,
            step=step,
            executor="ACTION",
            execution_id=request.action_id,
            status=str(status),
            payload=payload,
            reference=response.reference,
            metadata=response.metadata,
        )

    def _execute_gate(
        self,
        workflow: WorkflowRecord,
        program: WorkflowProgram,
        step: WorkflowStep,
    ) -> bool:
        matching = []
        for gate in self.gates.store.for_workflow(workflow.workflow_id):
            marker = gate.payload.get("_controller")
            if (
                gate.gate_type == step.gate_type
                and isinstance(marker, Mapping)
                and marker.get("program_id") == program.program_id
                and marker.get("step_id") == step.step_id
            ):
                matching.append(gate)
        gate = matching[-1] if matching else None
        if gate is None:
            payload = dict(step.payload)
            payload["_controller"] = {
                "program_id": program.program_id,
                "step_id": step.step_id,
            }
            self.gates.request(
                workflow.workflow_id,
                gate_type=step.gate_type or "",
                requested_by=f"workflow:{program.program_id}:{step.step_id}",
                payload=payload,
            )
            return False
        if gate.status is GateStatus.PENDING:
            if workflow.status is not WorkflowStatus.WAITING:
                self.state.transition(
                    workflow.workflow_id,
                    WorkflowStatus.WAITING,
                    waiting_for=f"gate:{gate.gate_id}",
                )
            return False
        if gate.status is GateStatus.REJECTED:
            if workflow.status is not WorkflowStatus.BLOCKED:
                self.state.transition(
                    workflow.workflow_id,
                    WorkflowStatus.BLOCKED,
                    waiting_for=None,
                    blocker={
                        "code": "GATE_REJECTED",
                        "gate_id": gate.gate_id,
                        "gate_type": gate.gate_type,
                    },
                )
            return False
        if gate.status is GateStatus.CANCELLED:
            self.state.transition(
                workflow.workflow_id,
                WorkflowStatus.CANCELLED,
                waiting_for=None,
                blocker=None,
            )
            return False
        return self._advance_complete(workflow.workflow_id, program, step)

    def _apply_result(
        self,
        program: WorkflowProgram,
        step: WorkflowStep,
        result: StepResultRecord,
    ) -> bool:
        status = RoleStatus(result.status)
        workflow_id = result.workflow_id
        if status is RoleStatus.COMPLETE:
            return self._advance_complete(workflow_id, program, step)
        if status is RoleStatus.NEEDS_CLARIFICATION:
            questions = result.payload.get("questions")
            if not isinstance(questions, list) or not questions or any(not isinstance(item, Mapping) for item in questions):
                self.state.transition(
                    workflow_id,
                    WorkflowStatus.FAILED,
                    active_action=None,
                    active_role=None,
                    active_profile_id=None,
                    active_attempt_id=None,
                    waiting_for=None,
                    blocker={
                        "code": "CLARIFICATION_PAYLOAD_INVALID",
                        "result_id": result.result_id,
                        "step_id": step.step_id,
                    },
                )
                return False
            self.clarification.request(
                workflow_id,
                requested_by=f"{result.executor.lower()}:{step.step_id}",
                questions=questions,
                context={
                    "program_id": program.program_id,
                    "step_id": step.step_id,
                    "result_id": result.result_id,
                },
            )
            return False
        if status in {RoleStatus.NEEDS_CONTINUATION, RoleStatus.NEEDS_RETRY}:
            budget = RetryBudget.from_mapping(step.retry_budget)
            try:
                if status is RoleStatus.NEEDS_CONTINUATION:
                    self.retries.request_continuation(
                        workflow_id,
                        budget=budget,
                        requested_by=f"{result.executor.lower()}:{step.step_id}",
                        reason=result.payload.get("reason") if isinstance(result.payload.get("reason"), str) else None,
                    )
                else:
                    self.retries.request_retry(
                        workflow_id,
                        budget=budget,
                        requested_by=f"{result.executor.lower()}:{step.step_id}",
                        reason=result.payload.get("reason") if isinstance(result.payload.get("reason"), str) else None,
                    )
            except ControllerError as exc:
                if exc.code == "CONTROLLER_RETRY_BUDGET_EXHAUSTED":
                    return False
                raise
            self.state.transition(
                workflow_id,
                WorkflowStatus.READY,
                stage=step.step_id,
                active_action=None,
                active_role=None,
                active_profile_id=None,
                active_attempt_id=None,
                waiting_for=None,
                blocker=None,
            )
            return True
        if status is RoleStatus.BLOCKED:
            self.state.transition(
                workflow_id,
                WorkflowStatus.BLOCKED,
                active_action=None,
                active_role=None,
                active_profile_id=None,
                active_attempt_id=None,
                waiting_for=None,
                blocker={
                    "code": "STEP_BLOCKED",
                    "program_id": program.program_id,
                    "step_id": step.step_id,
                    "result_id": result.result_id,
                    "details": dict(result.payload),
                },
            )
            return False
        if status is RoleStatus.FAILED:
            self.state.transition(
                workflow_id,
                WorkflowStatus.FAILED,
                active_action=None,
                active_role=None,
                active_profile_id=None,
                active_attempt_id=None,
                waiting_for=None,
                blocker={
                    "code": "STEP_FAILED",
                    "program_id": program.program_id,
                    "step_id": step.step_id,
                    "result_id": result.result_id,
                    "details": dict(result.payload),
                },
            )
            return False
        raise ControllerError(
            "CONTROLLER_ENGINE_STATUS_INVALID",
            "workflow engine received an unsupported result status",
            {"result_id": result.result_id, "status": result.status},
        )

    def _advance_complete(
        self,
        workflow_id: str,
        program: WorkflowProgram,
        step: WorkflowStep,
    ) -> bool:
        if step.next_step is None:
            self.state.transition(
                workflow_id,
                WorkflowStatus.COMPLETE,
                stage=step.step_id,
                active_action=None,
                active_role=None,
                active_profile_id=None,
                active_attempt_id=None,
                waiting_for=None,
                blocker=None,
            )
            return False
        self.state.transition(
            workflow_id,
            WorkflowStatus.READY,
            stage=step.next_step,
            active_action=None,
            active_role=None,
            active_profile_id=None,
            active_attempt_id=None,
            waiting_for=None,
            blocker=None,
        )
        return True

    def _persist_result(
        self,
        *,
        workflow: WorkflowRecord,
        program: WorkflowProgram,
        step: WorkflowStep,
        executor: str,
        execution_id: str,
        status: str,
        payload: Mapping[str, Any],
        reference: str | None,
        metadata: Mapping[str, Any],
    ) -> StepResultRecord:
        result = StepResultRecord.create(
            workflow_id=workflow.workflow_id,
            program_id=program.program_id,
            step_id=step.step_id,
            executor=executor,
            execution_id=execution_id,
            status=status,
            payload=payload,
            reference=reference,
            metadata=metadata,
        )
        self.results.save(result)
        self.state.add_result(
            workflow.workflow_id,
            ResultReference(
                result_id=result.result_id,
                result_type="controller-step-result:v1",
                producer=f"{executor.lower()}:{step.step_id}",
                reference=f"controller-result:{result.result_id}",
                metadata={
                    "program_id": program.program_id,
                    "step_id": step.step_id,
                    "executor": executor,
                    "status": status,
                    "digest": result.digest(),
                },
            ),
        )
        emit(
            "INFO",
            self.component,
            "persist_result",
            "step_result_persisted",
            workflow_id=workflow.workflow_id,
            program_id=program.program_id,
            step_id=step.step_id,
            result_id=result.result_id,
            execution_id=execution_id,
            executor=executor,
            result_status=status,
            result_digest=result.digest(),
        )
        return result

    def _step_input(
        self,
        workflow: WorkflowRecord,
        program: WorkflowProgram,
        step: WorkflowStep,
    ) -> dict[str, Any]:
        clarifications = [
            item.to_dict()
            for item in self.clarification.store.for_workflow(workflow.workflow_id)
            if item.status is ClarificationStatus.ANSWERED
        ]
        prior_results = [item.to_dict() for item in self.results.for_workflow(workflow.workflow_id)]
        return {
            "workflow": {
                "workflow_id": workflow.workflow_id,
                "program_id": program.program_id,
                "step_id": step.step_id,
                "request": workflow.request.to_dict(),
            },
            "step_input": dict(step.payload),
            "prior_results": prior_results,
            "clarifications": clarifications,
        }

    def _report(
        self,
        workflow: WorkflowRecord,
        operations: int,
        latest_result_id: str | None,
    ) -> EngineReport:
        return EngineReport(
            workflow_id=workflow.workflow_id,
            status=str(workflow.status),
            stage=workflow.stage,
            operations=operations,
            waiting_for=workflow.waiting_for,
            blocker=workflow.blocker,
            latest_result_id=latest_result_id,
        )
