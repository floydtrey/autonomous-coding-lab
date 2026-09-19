"""Controller handling for Planner dispositions that do not require a Worker.

DIRECT_RESPONSE and QUERY_RESPONSE finish the workflow immediately.
ELEVATION_REQUIRED persists a clarification and pauses the workflow.
EXECUTION_PLAN is returned untouched for the later plan-intake phase.
CANNOT_PLAN blocks the workflow with an explicit Planner reason.

No Worker, Reviewer, Git, GitHub, or execution harness is started here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from acl_core.diagnostics import emit
from acl_roles.planner import (
    PlannerDisposition,
    PlannerInput,
    PlannerRuntimeResponse,
)

from ..clarification import ClarificationService
from ..diagnostics import controller_span
from ..errors import ControllerError
from ..models import WorkflowStatus
from ..state import WorkflowStateService


class PlannerOutcomeStatus(StrEnum):
    RESPONDED = "RESPONDED"
    ELEVATED = "ELEVATED"
    PLAN_READY = "PLAN_READY"
    CANNOT_PLAN = "CANNOT_PLAN"


@dataclass(frozen=True)
class PlannerDispositionOutcome:
    workflow_id: str
    status: PlannerOutcomeStatus
    disposition: PlannerDisposition
    answer: str | None = None
    sources: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    clarification_id: str | None = None
    questions: tuple[Mapping[str, Any], ...] = ()
    reason_codes: tuple[str, ...] = ()
    notes: str | None = None
    runtime_metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "status": str(self.status),
            "disposition": str(self.disposition),
            "answer": self.answer,
            "sources": list(self.sources),
            "references": list(self.references),
            "clarification_id": self.clarification_id,
            "questions": [dict(item) for item in self.questions],
            "reason_codes": list(self.reason_codes),
            "notes": self.notes,
            "runtime_metadata": dict(self.runtime_metadata),
        }


class PlannerDispositionService:
    component = "controller.planner.disposition"

    def __init__(
        self,
        *,
        state: WorkflowStateService,
        clarification: ClarificationService,
    ) -> None:
        self.state = state
        self.clarification = clarification

    def apply(
        self,
        workflow_id: str,
        *,
        planner_input: PlannerInput,
        response: PlannerRuntimeResponse,
    ) -> PlannerDispositionOutcome:
        if not isinstance(planner_input, PlannerInput):
            raise ControllerError(
                "CONTROLLER_PLANNER_INPUT_INVALID",
                "Planner disposition handling requires PlannerInput",
            )
        if not isinstance(response, PlannerRuntimeResponse):
            raise ControllerError(
                "CONTROLLER_PLANNER_RESPONSE_INVALID",
                "Planner disposition handling requires PlannerRuntimeResponse",
            )

        with controller_span(
            "planner_disposition.apply",
            workflow_id=workflow_id,
            disposition=str(response.result.disposition),
        ):
            workflow = self.state.read(workflow_id)
            if workflow.status is WorkflowStatus.NEW:
                workflow = self.state.transition(
                    workflow_id,
                    WorkflowStatus.READY,
                    stage="planner",
                    waiting_for=None,
                    blocker=None,
                )
            if workflow.status is not WorkflowStatus.READY:
                raise ControllerError(
                    "CONTROLLER_PLANNER_DISPOSITION_STATE_INVALID",
                    "Planner disposition can only be applied to a NEW or READY workflow",
                    {
                        "workflow_id": workflow_id,
                        "status": str(workflow.status),
                        "stage": workflow.stage,
                    },
                )

            result = response.result
            if result.disposition in {
                PlannerDisposition.DIRECT_RESPONSE,
                PlannerDisposition.QUERY_RESPONSE,
            }:
                answer = result.answer
                if answer is None:
                    raise ControllerError(
                        "CONTROLLER_PLANNER_RESPONSE_INVALID",
                        "response disposition is missing its answer",
                        {"disposition": str(result.disposition)},
                    )
                self.state.transition(
                    workflow_id,
                    WorkflowStatus.COMPLETE,
                    stage="planner-response",
                    active_action=None,
                    active_role=None,
                    active_profile_id=None,
                    active_attempt_id=None,
                    waiting_for=None,
                    blocker=None,
                )
                outcome = PlannerDispositionOutcome(
                    workflow_id=workflow_id,
                    status=PlannerOutcomeStatus.RESPONDED,
                    disposition=result.disposition,
                    answer=answer.answer,
                    sources=answer.sources,
                    references=answer.references,
                    reason_codes=result.reason_codes,
                    notes=result.notes,
                    runtime_metadata=dict(response.runtime_metadata),
                )
                emit(
                    "INFO",
                    self.component,
                    "apply",
                    "planner_fast_response_complete",
                    workflow_id=workflow_id,
                    disposition=str(result.disposition),
                    source_count=len(answer.sources),
                    reference_count=len(answer.references),
                )
                return outcome

            if result.disposition is PlannerDisposition.ELEVATION_REQUIRED:
                questions = tuple(item.to_dict() for item in result.questions)
                record = self.clarification.request(
                    workflow_id,
                    requested_by="planner",
                    questions=questions,
                    context={
                        "kind": "planner_elevation",
                        "planner_input": planner_input.to_objective(),
                        "planner_result": result.to_dict(),
                        "runtime_metadata": dict(response.runtime_metadata),
                    },
                )
                outcome = PlannerDispositionOutcome(
                    workflow_id=workflow_id,
                    status=PlannerOutcomeStatus.ELEVATED,
                    disposition=result.disposition,
                    clarification_id=record.clarification_id,
                    questions=questions,
                    reason_codes=result.reason_codes,
                    notes=result.notes,
                    runtime_metadata=dict(response.runtime_metadata),
                )
                emit(
                    "INFO",
                    self.component,
                    "apply",
                    "planner_elevation_waiting",
                    workflow_id=workflow_id,
                    clarification_id=record.clarification_id,
                    question_count=len(questions),
                )
                return outcome

            if result.disposition is PlannerDisposition.EXECUTION_PLAN:
                emit(
                    "INFO",
                    self.component,
                    "apply",
                    "planner_execution_plan_ready",
                    workflow_id=workflow_id,
                    plan_type=None if result.plan is None else str(result.plan.plan_type),
                )
                return PlannerDispositionOutcome(
                    workflow_id=workflow_id,
                    status=PlannerOutcomeStatus.PLAN_READY,
                    disposition=result.disposition,
                    reason_codes=result.reason_codes,
                    notes=result.notes,
                    runtime_metadata=dict(response.runtime_metadata),
                )

            if result.disposition is PlannerDisposition.CANNOT_PLAN:
                blocker = {
                    "code": "PLANNER_CANNOT_PLAN",
                    "reason_codes": list(result.reason_codes),
                    "notes": result.notes,
                }
                self.state.transition(
                    workflow_id,
                    WorkflowStatus.BLOCKED,
                    stage="planner",
                    active_action=None,
                    active_role=None,
                    active_profile_id=None,
                    active_attempt_id=None,
                    waiting_for=None,
                    blocker=blocker,
                )
                emit(
                    "INFO",
                    self.component,
                    "apply",
                    "planner_cannot_plan",
                    workflow_id=workflow_id,
                    reason_codes=list(result.reason_codes),
                )
                return PlannerDispositionOutcome(
                    workflow_id=workflow_id,
                    status=PlannerOutcomeStatus.CANNOT_PLAN,
                    disposition=result.disposition,
                    reason_codes=result.reason_codes,
                    notes=result.notes,
                    runtime_metadata=dict(response.runtime_metadata),
                )

            raise ControllerError(
                "CONTROLLER_PLANNER_DISPOSITION_INVALID",
                "Planner returned an unsupported disposition",
                {"disposition": str(result.disposition)},
            )
