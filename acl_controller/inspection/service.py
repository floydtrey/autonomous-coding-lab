"""Aggregated read-only Controller inspection surface."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acl_core.diagnostics import emit

from ..authority import AuthorityCoordinator
from ..clarification import ClarificationService
from ..configuration import ProfileResolver
from ..diagnostics import controller_span
from ..errors import ControllerError
from ..gates import GateService
from ..models import WorkflowRecord
from ..recovery import JsonStopStore
from ..retries import RetryService
from ..state import WorkflowStateService
from ..workflow import JsonProgramStore, JsonResultStore


@dataclass(frozen=True)
class InspectionReport:
    workflow: dict[str, Any]
    program: dict[str, Any] | None
    active_grant: dict[str, Any] | None
    active_profile: dict[str, Any] | None
    retry: dict[str, Any] | None
    clarifications: tuple[dict[str, Any], ...]
    gates: tuple[dict[str, Any], ...]
    stops: tuple[dict[str, Any], ...]
    results: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "acl-controller-inspection:v1",
            "workflow": self.workflow,
            "program": self.program,
            "active_grant": self.active_grant,
            "active_profile": self.active_profile,
            "retry": self.retry,
            "clarifications": list(self.clarifications),
            "gates": list(self.gates),
            "stops": list(self.stops),
            "results": list(self.results),
            "summary": {
                "workflow_id": self.workflow["workflow_id"],
                "status": self.workflow["status"],
                "stage": self.workflow["stage"],
                "program_id": self.workflow.get("program_id"),
                "active_action": self.workflow.get("active_action"),
                "active_role": self.workflow.get("active_role"),
                "active_profile_id": self.workflow.get("active_profile_id"),
                "active_attempt_id": self.workflow.get("active_attempt_id"),
                "authority_grant_id": self.workflow.get("authority_grant_id"),
                "waiting_for": self.workflow.get("waiting_for"),
                "blocker": self.workflow.get("blocker"),
                "retry_count": self.workflow.get("retry_count"),
                "retries_used": None if self.retry is None else self.retry.get("retries_used"),
                "continuations_used": None if self.retry is None else self.retry.get("continuations_used"),
                "retry_budget": None if self.retry is None else self.retry.get("budget"),
                "result_count": len(self.results),
                "clarification_count": len(self.clarifications),
                "gate_count": len(self.gates),
                "stop_count": len(self.stops),
            },
        }


class InspectionService:
    component = "controller.inspection"

    def __init__(
        self,
        *,
        state: WorkflowStateService,
        programs: JsonProgramStore,
        results: JsonResultStore,
        authority: AuthorityCoordinator,
        profiles: ProfileResolver,
        clarification: ClarificationService,
        gates: GateService,
        retries: RetryService,
        stops: JsonStopStore,
    ) -> None:
        self.state = state
        self.programs = programs
        self.results = results
        self.authority = authority
        self.profiles = profiles
        self.clarification = clarification
        self.gates = gates
        self.retries = retries
        self.stops = stops

    def inspect(self, workflow_id: str) -> InspectionReport:
        with controller_span("inspection.inspect", workflow_id=workflow_id):
            workflow = self.state.read(workflow_id)
            program = None
            if workflow.program_id is not None:
                program = self.programs.read(workflow.program_id).to_dict()

            active_grant = None
            if workflow.authority_grant_id is not None:
                active_grant = self.authority.grant(workflow.authority_grant_id).to_dict()

            active_profile = None
            if workflow.active_profile_id is not None:
                active_profile = self.profiles.profile(workflow.active_profile_id).to_dict()

            retry = self._optional_retry(workflow)
            clarifications = tuple(
                item.to_dict()
                for item in self.clarification.store.for_workflow(workflow_id)
            )
            gates = tuple(
                item.to_dict()
                for item in self.gates.store.for_workflow(workflow_id)
            )
            stops = tuple(
                item.to_dict()
                for item in self.stops.for_workflow(workflow_id)
            )
            results = tuple(
                item.to_dict()
                for item in self.results.for_workflow(workflow_id)
            )

            report = InspectionReport(
                workflow=workflow.to_dict(),
                program=program,
                active_grant=active_grant,
                active_profile=active_profile,
                retry=retry,
                clarifications=clarifications,
                gates=gates,
                stops=stops,
                results=results,
            )
            emit(
                "DEBUG",
                self.component,
                "inspect",
                "inspection_built",
                workflow_id=workflow_id,
                status=str(workflow.status),
                stage=workflow.stage,
                program_id=workflow.program_id,
                active_attempt_id=workflow.active_attempt_id,
                active_role=workflow.active_role,
                active_profile_id=workflow.active_profile_id,
                authority_grant_id=workflow.authority_grant_id,
                waiting_for=workflow.waiting_for,
                result_count=len(results),
                clarification_count=len(clarifications),
                gate_count=len(gates),
                stop_count=len(stops),
            )
            return report

    def _optional_retry(self, workflow: WorkflowRecord) -> dict[str, Any] | None:
        try:
            return self.retries.read(workflow.workflow_id).to_dict()
        except ControllerError as exc:
            if exc.code == "CONTROLLER_RETRY_STATE_MISSING":
                return None
            raise
