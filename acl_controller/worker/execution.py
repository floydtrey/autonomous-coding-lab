"""Controller-owned Worker Pass execution records and handoff.

A Worker executes one deterministic next Planner Pass. Worker output is persisted
for Reviewer; it never completes Planner Pass state by itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from acl_core import CoreIdentity
from acl_core.canonical import canonical_json
from acl_core.diagnostics import emit
from acl_roles.common.errors import RoleContractError
from acl_roles.worker import (
    WorkerContinuationHandoff,
    WorkerCorrectionPolicy,
    WorkerInput,
    WorkerOutcome,
    WorkerResult,
    WorkerRuntimeRequest,
    WorkerRuntimeResponse,
    WorkerRuntimeService,
    build_worker_correction_input,
    correction_signature,
    worker_previous_response_from_error,
)

from ..authority import PassAuthorityService
from ..diagnostics import controller_span
from ..errors import ControllerError
from ..models import WorkflowStatus, utc_now
from ..planner import PlannerNextPassStatus, PlannerPlanService
from ..state import WorkflowStateService
from ..telemetry import RoleTelemetryService


WORKER_RUN_SCHEMA = "acl-worker-run:v1"
WORKER_REVIEW_PACKET_SCHEMA = "acl-worker-review-packet:v1"


class WorkerRunStatus(StrEnum):
    PREPARED = "PREPARED"
    RUNNING = "RUNNING"
    RERUN_REQUIRED = "RERUN_REQUIRED"
    RECOVERY_RERUN_REQUIRED = "RECOVERY_RERUN_REQUIRED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    NEEDS_CONTINUATION = "NEEDS_CONTINUATION"
    NEEDS_PLANNER = "NEEDS_PLANNER"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class WorkerRunRecord:
    worker_run_id: str
    workflow_id: str
    plan_id: str
    plan_version: int
    pass_id: str
    stage_id: str | None
    worker_input: WorkerInput
    status: WorkerRunStatus = WorkerRunStatus.PREPARED
    result: WorkerResult | None = None
    runtime_metadata: Mapping[str, Any] = field(default_factory=dict)
    continuation_of: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        workflow_id: str,
        worker_input: WorkerInput,
        stage_id: str | None,
        continuation_of: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "WorkerRunRecord":
        return cls(
            worker_run_id=CoreIdentity.new("workerrun").value,
            workflow_id=workflow_id,
            plan_id=worker_input.plan_id,
            plan_version=worker_input.plan_version,
            pass_id=worker_input.pass_id,
            stage_id=stage_id,
            worker_input=worker_input,
            continuation_of=continuation_of,
            metadata=dict(metadata or {}),
        )

    def __post_init__(self) -> None:
        if not isinstance(self.worker_run_id, str) or not self.worker_run_id.startswith("workerrun:"):
            raise ControllerError("CONTROLLER_WORKER_RUN_INVALID", "worker_run_id is invalid")
        if not isinstance(self.workflow_id, str) or not self.workflow_id.startswith("workflow:"):
            raise ControllerError("CONTROLLER_WORKER_RUN_INVALID", "workflow_id is invalid")
        if not isinstance(self.worker_input, WorkerInput):
            raise ControllerError("CONTROLLER_WORKER_RUN_INVALID", "worker_input is invalid")
        if (
            self.plan_id != self.worker_input.plan_id
            or self.plan_version != self.worker_input.plan_version
            or self.pass_id != self.worker_input.pass_id
            or self.stage_id != self.worker_input.stage_id
        ):
            raise ControllerError(
                "CONTROLLER_WORKER_RUN_INVALID",
                "Worker run identity differs from its immutable Worker input",
            )
        if not isinstance(self.status, WorkerRunStatus):
            raise ControllerError("CONTROLLER_WORKER_RUN_INVALID", "Worker run status is invalid")
        if self.status in {
            WorkerRunStatus.PREPARED,
            WorkerRunStatus.RUNNING,
            WorkerRunStatus.RERUN_REQUIRED,
            WorkerRunStatus.RECOVERY_RERUN_REQUIRED,
        }:
            if self.result is not None:
                raise ControllerError(
                    "CONTROLLER_WORKER_RUN_INVALID",
                    "nonterminal Worker run must not contain a result",
                )
        elif not isinstance(self.result, WorkerResult):
            raise ControllerError(
                "CONTROLLER_WORKER_RUN_INVALID",
                "terminal Worker run requires a Worker result",
            )
        if self.continuation_of is not None and (
            not isinstance(self.continuation_of, str)
            or not self.continuation_of.startswith("workerrun:")
        ):
            raise ControllerError(
                "CONTROLLER_WORKER_RUN_INVALID",
                "continuation_of is invalid",
            )
        if not isinstance(self.runtime_metadata, Mapping) or not isinstance(self.metadata, Mapping):
            raise ControllerError(
                "CONTROLLER_WORKER_RUN_INVALID",
                "Worker run metadata must be mappings",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": WORKER_RUN_SCHEMA,
            "worker_run_id": self.worker_run_id,
            "workflow_id": self.workflow_id,
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "pass_id": self.pass_id,
            "stage_id": self.stage_id,
            "worker_input": self.worker_input.to_objective(),
            "status": str(self.status),
            "result": None if self.result is None else self.result.to_dict(),
            "runtime_metadata": dict(self.runtime_metadata),
            "continuation_of": self.continuation_of,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkerRunRecord":
        if not isinstance(value, Mapping) or value.get("schema_version") != WORKER_RUN_SCHEMA:
            raise ControllerError(
                "CONTROLLER_WORKER_RUN_INVALID",
                "Worker run schema is invalid",
            )
        result_raw = value.get("result")
        try:
            return cls(
                worker_run_id=value["worker_run_id"],
                workflow_id=value["workflow_id"],
                plan_id=value["plan_id"],
                plan_version=int(value["plan_version"]),
                pass_id=value["pass_id"],
                stage_id=value.get("stage_id"),
                worker_input=WorkerInput.from_mapping(value["worker_input"]),
                status=WorkerRunStatus(value["status"]),
                result=None if result_raw is None else WorkerResult.from_mapping(result_raw),
                runtime_metadata=dict(value.get("runtime_metadata", {})),
                continuation_of=value.get("continuation_of"),
                metadata=dict(value.get("metadata", {})),
                created_at=value["created_at"],
                updated_at=value["updated_at"],
            )
        except (KeyError, TypeError, ValueError, RoleContractError) as exc:
            raise ControllerError(
                "CONTROLLER_WORKER_RUN_INVALID",
                "Worker run record is malformed",
            ) from exc


@dataclass(frozen=True)
class WorkerReviewPacket:
    workflow_id: str
    plan_id: str
    plan_version: int
    semantic_plan_digest: str
    pass_id: str
    stage_id: str | None
    pass_spec: Mapping[str, Any]
    plan_context: Mapping[str, Any]
    worker_run_id: str
    worker_result: Mapping[str, Any]
    worker_runtime: Mapping[str, Any]
    prior_worker_results: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": WORKER_REVIEW_PACKET_SCHEMA,
            "workflow_id": self.workflow_id,
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "semantic_plan_digest": self.semantic_plan_digest,
            "pass_id": self.pass_id,
            "stage_id": self.stage_id,
            "pass": dict(self.pass_spec),
            "plan_context": dict(self.plan_context),
            "worker_run_id": self.worker_run_id,
            "worker_result": dict(self.worker_result),
            "worker_runtime": dict(self.worker_runtime),
            "prior_worker_results": [dict(item) for item in self.prior_worker_results],
        }


@dataclass(frozen=True)
class WorkerExecutionOutcome:
    run: WorkerRunRecord
    workflow_status: WorkflowStatus
    workflow_stage: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "run": self.run.to_dict(),
            "workflow_status": str(self.workflow_status),
            "workflow_stage": self.workflow_stage,
            "review_required": self.run.status is WorkerRunStatus.READY_FOR_REVIEW,
        }


class JsonWorkerRunStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def create(self, record: WorkerRunRecord) -> WorkerRunRecord:
        path = self._path(record.worker_run_id)
        with self._lock:
            if path.exists():
                raise ControllerError(
                    "CONTROLLER_WORKER_RUN_EXISTS",
                    "Worker run already exists",
                    {"worker_run_id": record.worker_run_id},
                )
            self._write(path, record)
        return record

    def read(self, worker_run_id: str) -> WorkerRunRecord:
        try:
            return WorkerRunRecord.from_mapping(
                json.loads(self._path(worker_run_id).read_text(encoding="utf-8"))
            )
        except FileNotFoundError as exc:
            raise ControllerError(
                "CONTROLLER_WORKER_RUN_MISSING",
                "Worker run does not exist",
                {"worker_run_id": worker_run_id},
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ControllerError(
                "CONTROLLER_WORKER_RUN_INVALID",
                "Worker run could not be read",
                {"worker_run_id": worker_run_id},
            ) from exc

    def save(self, record: WorkerRunRecord) -> WorkerRunRecord:
        with self._lock:
            self._write(self._path(record.worker_run_id), record)
        return record

    def for_pass(self, plan_id: str, pass_id: str) -> tuple[WorkerRunRecord, ...]:
        directory = self.root / "worker-runs"
        if not directory.exists():
            return ()
        records: list[WorkerRunRecord] = []
        for path in sorted(directory.glob("workerrun_*.json")):
            try:
                record = WorkerRunRecord.from_mapping(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except (OSError, json.JSONDecodeError, ControllerError) as exc:
                raise ControllerError(
                    "CONTROLLER_WORKER_RUN_INVALID",
                    "one or more Worker run records are unreadable",
                    {"path": str(path)},
                ) from exc
            if record.plan_id == plan_id and record.pass_id == pass_id:
                records.append(record)
        return tuple(records)

    def for_workflow(self, workflow_id: str) -> tuple[WorkerRunRecord, ...]:
        directory = self.root / "worker-runs"
        if not directory.exists():
            return ()
        records: list[WorkerRunRecord] = []
        for path in sorted(directory.glob("workerrun_*.json")):
            try:
                record = WorkerRunRecord.from_mapping(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except (OSError, json.JSONDecodeError, ControllerError) as exc:
                raise ControllerError(
                    "CONTROLLER_WORKER_RUN_INVALID",
                    "one or more Worker run records are unreadable",
                    {"path": str(path)},
                ) from exc
            if record.workflow_id == workflow_id:
                records.append(record)
        return tuple(records)

    def _path(self, worker_run_id: str) -> Path:
        if not isinstance(worker_run_id, str) or not worker_run_id.startswith("workerrun:"):
            raise ControllerError("CONTROLLER_WORKER_RUN_INVALID", "worker_run_id is invalid")
        return self.root / "worker-runs" / f"{worker_run_id.replace(':', '_')}.json"

    @staticmethod
    def _write(path: Path, record: WorkerRunRecord) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        try:
            temp.write_text(canonical_json(record.to_dict()) + "\n", encoding="utf-8")
            os.replace(temp, path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ControllerError(
                "CONTROLLER_WORKER_RUN_WRITE_FAILED",
                "Worker run state could not be persisted",
                {"worker_run_id": record.worker_run_id},
            ) from exc


class WorkerExecutionService:
    component = "controller.worker.execution"

    def __init__(
        self,
        *,
        state: WorkflowStateService,
        planner_plan: PlannerPlanService,
        runtime: WorkerRuntimeService,
        pass_authority: PassAuthorityService,
        correction_policy: WorkerCorrectionPolicy,
        telemetry: RoleTelemetryService,
        store: JsonWorkerRunStore,
    ) -> None:
        self.state = state
        self.planner_plan = planner_plan
        self.runtime = runtime
        self.pass_authority = pass_authority
        self.correction_policy = correction_policy
        self.telemetry = telemetry
        self.store = store

    def start_next_pass(
        self,
        plan_id: str,
        *,
        authority_grant_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> WorkerExecutionOutcome:
        next_pass = self.planner_plan.next_pass(plan_id)
        if next_pass.status is not PlannerNextPassStatus.READY or next_pass.pass_spec is None:
            raise ControllerError(
                "CONTROLLER_WORKER_PASS_NOT_READY",
                "Planner does not expose a Worker-ready Pass",
                {
                    "plan_id": plan_id,
                    "next_pass_status": str(next_pass.status),
                    "pass_id": next_pass.pass_id,
                    "blocked_by": list(next_pass.blocked_by),
                },
            )
        existing = self.store.for_pass(plan_id, next_pass.pass_id or "")
        if existing:
            latest = max(existing, key=lambda item: item.updated_at)
            if latest.status in {
                WorkerRunStatus.RERUN_REQUIRED,
                WorkerRunStatus.RECOVERY_RERUN_REQUIRED,
            }:
                worker_input = latest.worker_input
                authority_grant_id = self._resolve_pass_authority(
                    worker_input,
                    authority_grant_id=authority_grant_id,
                )
                emit(
                    "INFO",
                    self.component,
                    "start_next_pass",
                    "worker_recovery_rerun_started",
                    worker_run_id=latest.worker_run_id,
                    workflow_id=latest.workflow_id,
                    plan_id=latest.plan_id,
                    pass_id=latest.pass_id,
                    prior_attempt_id=latest.metadata.get("recovery_prior_attempt_id"),
                )
                return self._invoke(
                    worker_input,
                    continuation_of=latest.worker_run_id,
                    authority_grant_id=authority_grant_id,
                    metadata={
                        **dict(metadata or {}),
                        "recovery_rerun_of": latest.worker_run_id,
                        "recovery_prior_attempt_id": latest.metadata.get(
                            "recovery_prior_attempt_id"
                        ),
                    },
                )
            raise ControllerError(
                "CONTROLLER_WORKER_RUN_CONFLICT",
                "assigned Pass already has a Worker run; use explicit continuation/review flow",
                {
                    "plan_id": plan_id,
                    "pass_id": next_pass.pass_id,
                    "worker_run_ids": [item.worker_run_id for item in existing],
                },
            )
        worker_input = self._build_input(plan_id)
        authority_grant_id = self._resolve_pass_authority(
            worker_input,
            authority_grant_id=authority_grant_id,
        )
        return self._invoke(
            worker_input,
            continuation_of=None,
            authority_grant_id=authority_grant_id,
            metadata=metadata,
        )

    def continue_pass(
        self,
        worker_run_id: str,
        *,
        guidance: Mapping[str, Any] | None = None,
        authority_grant_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> WorkerExecutionOutcome:
        previous = self.store.read(worker_run_id)
        if previous.status not in {
            WorkerRunStatus.NEEDS_CONTINUATION,
            WorkerRunStatus.NEEDS_PLANNER,
        }:
            raise ControllerError(
                "CONTROLLER_WORKER_CONTINUATION_INVALID",
                "Worker run is not eligible for continuation",
                {
                    "worker_run_id": worker_run_id,
                    "status": str(previous.status),
                },
            )
        next_pass = self.planner_plan.next_pass(previous.plan_id)
        if (
            next_pass.status is not PlannerNextPassStatus.READY
            or next_pass.pass_id != previous.pass_id
        ):
            raise ControllerError(
                "CONTROLLER_WORKER_PASS_NOT_READY",
                "continued Worker Pass is no longer the deterministic next Pass",
                {
                    "plan_id": previous.plan_id,
                    "pass_id": previous.pass_id,
                    "next_pass_status": str(next_pass.status),
                    "next_pass_id": next_pass.pass_id,
                },
            )
        if previous.result is None or previous.result.continuation_handoff is None:
            raise ControllerError(
                "CONTROLLER_WORKER_HANDOFF_MISSING",
                "continued Worker run does not contain a bounded continuation handoff",
                {
                    "worker_run_id": previous.worker_run_id,
                    "status": str(previous.status),
                },
            )
        worker_input = self._build_input(
            previous.plan_id,
            continuation_handoff=previous.result.continuation_handoff,
            metadata={
                "continuation_of": previous.worker_run_id,
                "guidance": dict(guidance or {}),
            },
        )
        authority_grant_id = self._resolve_pass_authority(
            worker_input,
            authority_grant_id=authority_grant_id,
        )
        return self._invoke(
            worker_input,
            continuation_of=previous.worker_run_id,
            authority_grant_id=authority_grant_id,
            metadata=metadata,
        )

    def _resolve_pass_authority(
        self,
        worker_input: WorkerInput,
        *,
        authority_grant_id: str | None,
    ) -> str:
        if authority_grant_id is not None:
            return authority_grant_id
        plan = self.planner_plan.read(worker_input.plan_id)
        work_type_id = worker_input.plan_context.get("work_type_id")
        binding = self.pass_authority.bind_worker_pass(
            plan.workflow_id,
            work_type_id=(
                work_type_id
                if isinstance(work_type_id, str) and work_type_id.strip()
                else None
            ),
            complexity=worker_input.pass_spec.complexity,
            pass_spec=worker_input.pass_spec,
        )
        return binding.grant_id

    def recovery_released_for_rerun(
        self,
        workflow_id: str,
        *,
        prior_attempt_id: str,
    ) -> None:
        running = tuple(
            item
            for item in self.store.for_workflow(workflow_id)
            if item.status is WorkerRunStatus.RUNNING
        )
        if not running:
            return
        if len(running) != 1:
            raise ControllerError(
                "CONTROLLER_WORKER_RECOVERY_AMBIGUOUS",
                "more than one Worker run is marked RUNNING for the workflow",
                {
                    "workflow_id": workflow_id,
                    "worker_run_ids": [item.worker_run_id for item in running],
                },
            )
        current = running[0]
        updated = replace(
            current,
            status=WorkerRunStatus.RECOVERY_RERUN_REQUIRED,
            metadata={
                **dict(current.metadata),
                "recovery_prior_attempt_id": prior_attempt_id,
            },
            updated_at=utc_now(),
        )
        self.store.save(updated)
        emit(
            "INFO",
            self.component,
            "recovery_released_for_rerun",
            "worker_run_reconciled_for_recovery_rerun",
            workflow_id=workflow_id,
            worker_run_id=updated.worker_run_id,
            prior_attempt_id=prior_attempt_id,
        )

    def _mark_rerun_required(
        self,
        run: WorkerRunRecord,
        *,
        error: BaseException,
        reason: str,
    ) -> WorkerRunRecord:
        code = getattr(error, "code", None)
        message = getattr(error, "message", None)
        updated = replace(
            run,
            status=WorkerRunStatus.RERUN_REQUIRED,
            metadata={
                **dict(run.metadata),
                "rerun_reason": reason,
                "last_error_code": (
                    code if isinstance(code, str) else type(error).__name__
                ),
                "last_error_message": (
                    message if isinstance(message, str) else str(error)
                ),
            },
            updated_at=utc_now(),
        )
        self.store.save(updated)
        emit(
            "ERROR",
            self.component,
            "mark_rerun_required",
            "worker_run_marked_rerun_required",
            workflow_id=updated.workflow_id,
            worker_run_id=updated.worker_run_id,
            plan_id=updated.plan_id,
            pass_id=updated.pass_id,
            reason=reason,
            error_code=updated.metadata.get("last_error_code"),
        )
        return updated

    def read(self, worker_run_id: str) -> WorkerRunRecord:
        return self.store.read(worker_run_id)

    def review_packet(self, worker_run_id: str) -> WorkerReviewPacket:
        run = self.store.read(worker_run_id)
        if run.status is not WorkerRunStatus.READY_FOR_REVIEW or run.result is None:
            raise ControllerError(
                "CONTROLLER_WORKER_REVIEW_NOT_READY",
                "Worker run is not ready for Reviewer intake",
                {
                    "worker_run_id": worker_run_id,
                    "status": str(run.status),
                },
            )
        prior = tuple(
            item.result.to_dict()
            for item in self.store.for_pass(run.plan_id, run.pass_id)
            if item.worker_run_id != run.worker_run_id and item.result is not None
        )
        return WorkerReviewPacket(
            workflow_id=run.workflow_id,
            plan_id=run.plan_id,
            plan_version=run.plan_version,
            semantic_plan_digest=run.worker_input.semantic_plan_digest,
            pass_id=run.pass_id,
            stage_id=run.stage_id,
            pass_spec=run.worker_input.pass_spec.to_dict(),
            plan_context=dict(run.worker_input.plan_context),
            worker_run_id=run.worker_run_id,
            worker_result=run.result.to_dict(),
            worker_runtime=dict(run.runtime_metadata),
            prior_worker_results=prior,
        )

    def runs_for_pass(self, plan_id: str, pass_id: str) -> tuple[WorkerRunRecord, ...]:
        return self.store.for_pass(plan_id, pass_id)

    def _build_input(
        self,
        plan_id: str,
        *,
        prior_worker_results: tuple[Mapping[str, Any], ...] = (),
        continuation_handoff: WorkerContinuationHandoff | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> WorkerInput:
        record = self.planner_plan.read(plan_id)
        next_pass = self.planner_plan.next_pass(plan_id)
        if next_pass.status is not PlannerNextPassStatus.READY or next_pass.pass_spec is None:
            raise ControllerError(
                "CONTROLLER_WORKER_PASS_NOT_READY",
                "Planner does not expose a Worker-ready Pass",
                {"plan_id": plan_id, "status": str(next_pass.status)},
            )
        plan = record.semantic_plan
        plan_context = {
            "work_type_id": plan.work_type_id,
            "task_type": plan.task_type,
            "complexity": plan.complexity,
            "objective": plan.objective,
            "acceptance_criteria": list(plan.acceptance_criteria),
            "required_outputs": list(plan.required_outputs),
            "constraints": list(plan.constraints),
            "out_of_scope": list(plan.out_of_scope),
            "assumptions": list(plan.assumptions),
            "workspace": plan.workspace.to_dict(),
            "reference_material": [item.to_dict() for item in plan.reference_material],
            "sources": list(plan.sources),
            "required_capabilities": list(plan.required_capabilities),
            "required_tools": list(plan.required_tools),
            "required_services": list(plan.required_services),
            "research_requirements": list(plan.research_requirements),
            "tracking_requirements": list(plan.tracking_requirements),
        }
        return WorkerInput(
            plan_id=record.plan_id,
            plan_version=record.plan_version,
            semantic_plan_digest=record.semantic_digest,
            pass_id=next_pass.pass_id or "",
            stage_id=next_pass.stage_id,
            pass_spec=next_pass.pass_spec,
            plan_context=plan_context,
            completed_passes=next_pass.completed_passes,
            prior_worker_results=prior_worker_results,
            continuation_handoff=continuation_handoff,
            metadata=dict(metadata or {}),
        )

    def _invoke(
        self,
        worker_input: WorkerInput,
        *,
        continuation_of: str | None,
        authority_grant_id: str | None,
        metadata: Mapping[str, Any] | None,
    ) -> WorkerExecutionOutcome:
        plan = self.planner_plan.read(worker_input.plan_id)
        workflow = self.state.read(plan.workflow_id)
        if workflow.status is not WorkflowStatus.READY:
            raise ControllerError(
                "CONTROLLER_WORKER_RUN_STATE_INVALID",
                "Worker may start only from READY workflow state",
                {
                    "workflow_id": workflow.workflow_id,
                    "status": str(workflow.status),
                    "stage": workflow.stage,
                },
            )
        if authority_grant_id is not None and workflow.authority_grant_id != authority_grant_id:
            raise ControllerError(
                "CONTROLLER_WORKFLOW_GRANT_MISMATCH",
                "Worker authority grant differs from workflow authority",
                {
                    "workflow_id": workflow.workflow_id,
                    "workflow_grant_id": workflow.authority_grant_id,
                    "requested_grant_id": authority_grant_id,
                },
            )

        run = WorkerRunRecord.create(
            workflow_id=workflow.workflow_id,
            worker_input=worker_input,
            stage_id=worker_input.stage_id,
            continuation_of=continuation_of,
            metadata=metadata,
        )
        self.store.create(run)
        run = replace(run, status=WorkerRunStatus.RUNNING, updated_at=utc_now())
        self.store.save(run)

        current_input = worker_input
        prior_error_signatures: list[str] = []
        correction_attempts = (
            0
            if current_input.correction is None
            else current_input.correction.attempt
        )

        while True:
            runtime_request = WorkerRuntimeRequest(
                workflow_id=workflow.workflow_id,
                worker_input=current_input,
                authority_grant_id=(
                    None
                    if current_input.correction is not None
                    else authority_grant_id
                ),
                metadata={
                    **dict(metadata or {}),
                    "worker_run_id": run.worker_run_id,
                    "runtime_backend_id": self.runtime.backend.backend_id,
                    "correction_attempt": correction_attempts,
                },
            )
            try:
                response = self.runtime.invoke(runtime_request)
            except Exception as exc:
                self.telemetry.record_safely(
                    workflow_id=workflow.workflow_id,
                    role="worker",
                    mode="PASS_EXECUTION",
                    request_metadata=runtime_request.metadata,
                    runtime_metadata=None,
                    success=False,
                    correction_attempt=(
                        correction_attempts if correction_attempts > 0 else None
                    ),
                    run_id=run.worker_run_id,
                    error=exc,
                    elapsed_key="worker_elapsed_ms",
                )
                if correction_attempts >= self.correction_policy.max_correction_attempts:
                    emit(
                        "ERROR",
                        self.component,
                        "invoke",
                        "worker_correction_budget_exhausted",
                        worker_run_id=run.worker_run_id,
                        workflow_id=workflow.workflow_id,
                        pass_id=worker_input.pass_id,
                        correction_attempts=correction_attempts,
                        max_correction_attempts=self.correction_policy.max_correction_attempts,
                        exception_type=type(exc).__name__,
                        exception_message=str(exc),
                    )
                    self._mark_rerun_required(
                        run,
                        error=exc,
                        reason="correction_budget_exhausted",
                    )
                    raise

                previous_response = worker_previous_response_from_error(exc)
                if previous_response is None:
                    self._mark_rerun_required(
                        run,
                        error=exc,
                        reason="runtime_failure_without_repairable_response",
                    )
                    raise

                try:
                    corrected_input = build_worker_correction_input(
                        current_input,
                        previous_response=previous_response,
                        error=exc,
                        policy=self.correction_policy,
                        attempt=correction_attempts + 1,
                        prior_error_signatures=tuple(prior_error_signatures),
                    )
                except Exception as correction_exc:
                    if getattr(correction_exc, "code", None) == "WORKER_CORRECTION_NOT_REPAIRABLE":
                        self._mark_rerun_required(
                            run,
                            error=exc,
                            reason="runtime_failure_not_prompt_repairable",
                        )
                        raise exc
                    self._mark_rerun_required(
                        run,
                        error=correction_exc,
                        reason="correction_construction_failed",
                    )
                    raise

                signature = correction_signature(corrected_input)
                if signature is not None:
                    prior_error_signatures.append(signature)
                correction_attempts += 1
                current_input = corrected_input
                emit(
                    "INFO",
                    self.component,
                    "invoke",
                    "worker_correction_retry",
                    worker_run_id=run.worker_run_id,
                    workflow_id=workflow.workflow_id,
                    pass_id=worker_input.pass_id,
                    correction_attempt=correction_attempts,
                    error_code=corrected_input.correction.error_code,
                    repeated_failure=corrected_input.correction.repeated_failure,
                )
                continue

            self.telemetry.record_safely(
                workflow_id=workflow.workflow_id,
                role="worker",
                mode="PASS_EXECUTION",
                request_metadata=runtime_request.metadata,
                runtime_metadata=response.runtime_metadata,
                success=True,
                outcome=str(response.result.outcome),
                correction_attempt=(
                    correction_attempts if correction_attempts > 0 else None
                ),
                run_id=run.worker_run_id,
                elapsed_key="worker_elapsed_ms",
            )
            break
        final_status = {
            WorkerOutcome.READY_FOR_REVIEW: WorkerRunStatus.READY_FOR_REVIEW,
            WorkerOutcome.NEEDS_CONTINUATION: WorkerRunStatus.NEEDS_CONTINUATION,
            WorkerOutcome.NEEDS_PLANNER: WorkerRunStatus.NEEDS_PLANNER,
            WorkerOutcome.BLOCKED: WorkerRunStatus.BLOCKED,
            WorkerOutcome.FAILED: WorkerRunStatus.FAILED,
        }[response.result.outcome]
        completed = replace(
            run,
            status=final_status,
            result=response.result,
            runtime_metadata=dict(response.runtime_metadata),
            updated_at=utc_now(),
        )
        self.store.save(completed)

        if final_status is WorkerRunStatus.READY_FOR_REVIEW:
            target_status = WorkflowStatus.READY
            target_stage = "review-ready"
            blocker = None
        elif final_status is WorkerRunStatus.NEEDS_CONTINUATION:
            target_status = WorkflowStatus.READY
            target_stage = "worker-continuation-ready"
            blocker = None
        elif final_status is WorkerRunStatus.NEEDS_PLANNER:
            target_status = WorkflowStatus.READY
            target_stage = "worker-planner-needed"
            blocker = None
        else:
            target_status = WorkflowStatus.BLOCKED
            target_stage = "worker-blocked"
            blocker = {
                "code": "WORKER_BLOCKED" if final_status is WorkerRunStatus.BLOCKED else "WORKER_FAILED",
                "worker_run_id": completed.worker_run_id,
                "pass_id": completed.pass_id,
                "message": response.result.blocker,
            }

        updated_workflow = self.state.transition(
            workflow.workflow_id,
            target_status,
            stage=target_stage,
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
            "invoke",
            "worker_run_persisted",
            worker_run_id=completed.worker_run_id,
            workflow_id=completed.workflow_id,
            plan_id=completed.plan_id,
            pass_id=completed.pass_id,
            worker_status=str(completed.status),
            workflow_status=str(updated_workflow.status),
            workflow_stage=updated_workflow.stage,
            review_required=completed.status is WorkerRunStatus.READY_FOR_REVIEW,
        )
        return WorkerExecutionOutcome(
            run=completed,
            workflow_status=updated_workflow.status,
            workflow_stage=updated_workflow.stage,
        )
