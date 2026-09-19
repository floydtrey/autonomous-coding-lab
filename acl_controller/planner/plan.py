"""Planner execution-plan intake and deterministic next-Pass resolution.

PL10 persists the accepted semantic ExecutionPlan under an ACL-owned plan ID and
version, tracks mechanical Pass completion/failure state, and identifies the
next eligible Pass without starting a Worker.

Planner owns the semantic plan. ACL owns canonical plan identity, version,
persistence, dependency resolution, and execution state.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from acl_core import CoreIdentity, FilesystemOperation
from acl_core.canonical import canonical_digest, canonical_json
from acl_core.diagnostics import emit
from acl_roles.planner import (
    ExecutionPlan,
    PassSpec,
    PlannerDisposition,
    PlannerResult,
    validate_planner_result,
)

from ..authority import FilesystemAuthorityCoordinator
from ..diagnostics import controller_span
from ..errors import ControllerError
from ..models import WorkflowStatus, utc_now
from ..state import WorkflowStateService


PLAN_STATE_SCHEMA = "acl-planner-plan-state:v1"
PLAN_VERSION = 1


class PlannerPlanStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"


class PlannerPassStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class PlannerNextPassStatus(StrEnum):
    READY = "READY"
    PLAN_COMPLETE = "PLAN_COMPLETE"
    BLOCKED = "BLOCKED"
    NO_ELIGIBLE_PASS = "NO_ELIGIBLE_PASS"


@dataclass(frozen=True)
class PlannerPassState:
    pass_id: str
    stage_id: str | None
    status: PlannerPassStatus = PlannerPassStatus.PENDING
    completed_at: str | None = None
    failed_at: str | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.pass_id, str) or not self.pass_id.strip():
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "pass_id must be nonblank text",
            )
        if self.stage_id is not None and (
            not isinstance(self.stage_id, str) or not self.stage_id.strip()
        ):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "stage_id must be nonblank text when present",
            )
        if not isinstance(self.status, PlannerPassStatus):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "pass status is invalid",
            )
        if self.status is PlannerPassStatus.PENDING:
            if any(
                value is not None
                for value in (self.completed_at, self.failed_at, self.failure_reason)
            ):
                raise ControllerError(
                    "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                    "PENDING Pass must not contain terminal state metadata",
                    {"pass_id": self.pass_id},
                )
        elif self.status is PlannerPassStatus.COMPLETE:
            if self.completed_at is None or self.failed_at is not None or self.failure_reason is not None:
                raise ControllerError(
                    "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                    "COMPLETE Pass state metadata is inconsistent",
                    {"pass_id": self.pass_id},
                )
        elif self.status is PlannerPassStatus.FAILED:
            if (
                self.failed_at is None
                or not isinstance(self.failure_reason, str)
                or not self.failure_reason.strip()
                or self.completed_at is not None
            ):
                raise ControllerError(
                    "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                    "FAILED Pass state metadata is inconsistent",
                    {"pass_id": self.pass_id},
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_id": self.pass_id,
            "stage_id": self.stage_id,
            "status": str(self.status),
            "completed_at": self.completed_at,
            "failed_at": self.failed_at,
            "failure_reason": self.failure_reason,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerPassState":
        try:
            return cls(
                pass_id=value["pass_id"],
                stage_id=value.get("stage_id"),
                status=PlannerPassStatus(value["status"]),
                completed_at=value.get("completed_at"),
                failed_at=value.get("failed_at"),
                failure_reason=value.get("failure_reason"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "Planner Pass state is malformed",
            ) from exc


@dataclass(frozen=True)
class PlannerPlanRecord:
    plan_id: str
    plan_version: int
    workflow_id: str
    semantic_plan: ExecutionPlan
    semantic_digest: str
    pass_states: tuple[PlannerPassState, ...]
    status: PlannerPlanStatus = PlannerPlanStatus.ACTIVE
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        workflow_id: str,
        semantic_plan: ExecutionPlan,
        metadata: Mapping[str, Any] | None = None,
    ) -> "PlannerPlanRecord":
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_INVALID",
                "workflow_id is required",
            )
        if not isinstance(semantic_plan, ExecutionPlan):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_INVALID",
                "semantic_plan must be ExecutionPlan",
            )
        pass_states: list[PlannerPassState] = []
        if semantic_plan.stages:
            for stage in semantic_plan.stages:
                for pass_spec in stage.passes:
                    pass_states.append(
                        PlannerPassState(
                            pass_id=pass_spec.pass_id,
                            stage_id=stage.stage_id,
                        )
                    )
        else:
            for pass_spec in semantic_plan.passes:
                pass_states.append(
                    PlannerPassState(
                        pass_id=pass_spec.pass_id,
                        stage_id=None,
                    )
                )

        return cls(
            plan_id=CoreIdentity.new("plan").value,
            plan_version=PLAN_VERSION,
            workflow_id=workflow_id,
            semantic_plan=semantic_plan,
            semantic_digest=canonical_digest(semantic_plan.to_dict()),
            pass_states=tuple(pass_states),
            metadata=dict(metadata or {}),
        )

    def __post_init__(self) -> None:
        if not isinstance(self.plan_id, str) or not self.plan_id.startswith("plan:"):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "plan_id is invalid",
            )
        if not isinstance(self.workflow_id, str) or not self.workflow_id.startswith("workflow:"):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "workflow_id is invalid",
            )
        if self.plan_version != PLAN_VERSION:
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "Planner V1 plan_version is unsupported",
                {
                    "expected": PLAN_VERSION,
                    "observed": self.plan_version,
                },
            )
        if not isinstance(self.semantic_plan, ExecutionPlan):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "semantic_plan must be ExecutionPlan",
            )
        if not isinstance(self.status, PlannerPlanStatus):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "plan status is invalid",
            )
        observed_digest = canonical_digest(self.semantic_plan.to_dict())
        if self.semantic_digest != observed_digest:
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_DIGEST_MISMATCH",
                "persisted semantic plan digest does not match plan content",
                {
                    "plan_id": self.plan_id,
                    "recorded": self.semantic_digest,
                    "observed": observed_digest,
                },
            )
        if not isinstance(self.pass_states, tuple) or not self.pass_states:
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "plan must contain Pass state",
            )
        ordered = _ordered_passes(self.semantic_plan)
        semantic_ids = tuple(pass_spec.pass_id for pass_spec, _ in ordered)
        semantic_stage_ids = tuple(stage_id for _, stage_id in ordered)
        state_ids = tuple(item.pass_id for item in self.pass_states)
        state_stage_ids = tuple(item.stage_id for item in self.pass_states)
        if semantic_ids != state_ids or semantic_stage_ids != state_stage_ids:
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "persisted Pass state order differs from semantic plan",
                {
                    "plan_id": self.plan_id,
                    "semantic_pass_ids": list(semantic_ids),
                    "state_pass_ids": list(state_ids),
                    "semantic_stage_ids": list(semantic_stage_ids),
                    "state_stage_ids": list(state_stage_ids),
                },
            )
        if not isinstance(self.metadata, Mapping):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "plan metadata must be a mapping",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PLAN_STATE_SCHEMA,
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "workflow_id": self.workflow_id,
            "semantic_plan": self.semantic_plan.to_dict(),
            "semantic_digest": self.semantic_digest,
            "pass_states": [item.to_dict() for item in self.pass_states],
            "status": str(self.status),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerPlanRecord":
        if (
            not isinstance(value, Mapping)
            or value.get("schema_version") != PLAN_STATE_SCHEMA
        ):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "Planner plan state schema is invalid",
            )
        try:
            return cls(
                plan_id=value["plan_id"],
                plan_version=int(value["plan_version"]),
                workflow_id=value["workflow_id"],
                semantic_plan=ExecutionPlan.from_mapping(value["semantic_plan"]),
                semantic_digest=value["semantic_digest"],
                pass_states=tuple(
                    PlannerPassState.from_mapping(item)
                    for item in value["pass_states"]
                ),
                status=PlannerPlanStatus(value["status"]),
                metadata=dict(value.get("metadata", {})),
                created_at=value["created_at"],
                updated_at=value["updated_at"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "Planner plan state is malformed",
            ) from exc


@dataclass(frozen=True)
class PlannerNextPass:
    plan_id: str
    plan_version: int
    workflow_id: str
    status: PlannerNextPassStatus
    pass_id: str | None = None
    stage_id: str | None = None
    pass_spec: PassSpec | None = None
    blocked_by: tuple[str, ...] = ()
    completed_passes: tuple[str, ...] = ()
    failed_passes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "workflow_id": self.workflow_id,
            "status": str(self.status),
            "pass_id": self.pass_id,
            "stage_id": self.stage_id,
            "pass": None if self.pass_spec is None else self.pass_spec.to_dict(),
            "blocked_by": list(self.blocked_by),
            "completed_passes": list(self.completed_passes),
            "failed_passes": list(self.failed_passes),
        }


@dataclass(frozen=True)
class PlannerPlanIntakeOutcome:
    plan: PlannerPlanRecord
    next_pass: PlannerNextPass

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_dict(),
            "next_pass": self.next_pass.to_dict(),
        }


class JsonPlannerPlanStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def create(self, record: PlannerPlanRecord) -> PlannerPlanRecord:
        path = self._path(record.plan_id)
        with self._lock:
            if path.exists():
                raise ControllerError(
                    "CONTROLLER_PLANNER_PLAN_EXISTS",
                    "Planner plan already exists",
                    {"plan_id": record.plan_id},
                )
            self._write(path, record)
        return record

    def read(self, plan_id: str) -> PlannerPlanRecord:
        try:
            return PlannerPlanRecord.from_mapping(
                json.loads(self._path(plan_id).read_text(encoding="utf-8"))
            )
        except FileNotFoundError as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_MISSING",
                "Planner plan does not exist",
                {"plan_id": plan_id},
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                "Planner plan state cannot be read",
                {"plan_id": plan_id},
            ) from exc

    def save(self, record: PlannerPlanRecord) -> PlannerPlanRecord:
        with self._lock:
            self._write(self._path(record.plan_id), record)
        return record

    def for_workflow(self, workflow_id: str) -> tuple[PlannerPlanRecord, ...]:
        directory = self.root / "planner-plans"
        if not directory.exists():
            return ()
        records: list[PlannerPlanRecord] = []
        for path in sorted(directory.glob("plan_*.json")):
            try:
                record = PlannerPlanRecord.from_mapping(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except (OSError, json.JSONDecodeError, ControllerError) as exc:
                raise ControllerError(
                    "CONTROLLER_PLANNER_PLAN_STATE_INVALID",
                    "one or more Planner plan records are unreadable",
                    {"path": str(path)},
                ) from exc
            if record.workflow_id == workflow_id:
                records.append(record)
        return tuple(records)

    def _path(self, plan_id: str) -> Path:
        if not isinstance(plan_id, str) or not plan_id.startswith("plan:"):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_INVALID",
                "plan_id is invalid",
            )
        return self.root / "planner-plans" / f"{plan_id.replace(':', '_')}.json"

    @staticmethod
    def _write(path: Path, record: PlannerPlanRecord) -> None:
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
                "CONTROLLER_PLANNER_PLAN_STATE_WRITE_FAILED",
                "Planner plan state could not be persisted",
                {"plan_id": record.plan_id},
            ) from exc


class PlannerPlanService:
    component = "controller.planner.plan"

    def __init__(
        self,
        *,
        state: WorkflowStateService,
        store: JsonPlannerPlanStore,
        filesystem_authority: FilesystemAuthorityCoordinator,
    ) -> None:
        self.state = state
        self.store = store
        self.filesystem_authority = filesystem_authority

    def intake(
        self,
        workflow_id: str,
        *,
        plan: ExecutionPlan,
        metadata: Mapping[str, Any] | None = None,
    ) -> PlannerPlanIntakeOutcome:
        """Persist one accepted Planner V1 plan for a workflow.

        V1 does not support semantic replanning/version increments. Re-intaking
        the identical semantic plan is idempotent; a different plan conflicts.
        """
        if not isinstance(plan, ExecutionPlan):
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_INVALID",
                "plan intake requires ExecutionPlan",
            )
        validate_planner_result(
            PlannerResult(
                disposition=PlannerDisposition.EXECUTION_PLAN,
                plan=plan,
            )
        )
        self._require_filesystem_authority(plan)
        with controller_span(
            "planner_plan.intake",
            workflow_id=workflow_id,
            plan_type=str(plan.plan_type),
        ):
            workflow = self.state.read(workflow_id)
            if workflow.status is not WorkflowStatus.READY:
                raise ControllerError(
                    "CONTROLLER_PLANNER_PLAN_INTAKE_STATE_INVALID",
                    "execution-plan intake requires a READY workflow",
                    {
                        "workflow_id": workflow_id,
                        "status": str(workflow.status),
                        "stage": workflow.stage,
                    },
                )

            digest = canonical_digest(plan.to_dict())
            existing = self.store.for_workflow(workflow_id)
            if existing:
                if len(existing) != 1:
                    raise ControllerError(
                        "CONTROLLER_PLANNER_PLAN_CONFLICT",
                        "V1 workflow has more than one persisted Planner plan",
                        {
                            "workflow_id": workflow_id,
                            "plan_ids": [item.plan_id for item in existing],
                        },
                    )
                current = existing[0]
                if current.semantic_digest != digest:
                    raise ControllerError(
                        "CONTROLLER_PLANNER_PLAN_CONFLICT",
                        "V1 does not replace an accepted semantic plan in place",
                        {
                            "workflow_id": workflow_id,
                            "existing_plan_id": current.plan_id,
                            "existing_digest": current.semantic_digest,
                            "requested_digest": digest,
                        },
                    )
                self.state.transition(
                    workflow_id,
                    WorkflowStatus.READY,
                    stage="plan-ready",
                    active_action=None,
                    active_role=None,
                    active_profile_id=None,
                    active_attempt_id=None,
                    waiting_for=None,
                    blocker=None,
                )
                return PlannerPlanIntakeOutcome(
                    plan=current,
                    next_pass=self.next_pass(current.plan_id),
                )

            record = PlannerPlanRecord.create(
                workflow_id=workflow_id,
                semantic_plan=plan,
                metadata=metadata,
            )
            self.store.create(record)
            self.state.transition(
                workflow_id,
                WorkflowStatus.READY,
                stage="plan-ready",
                active_action=None,
                active_role=None,
                active_profile_id=None,
                active_attempt_id=None,
                waiting_for=None,
                blocker=None,
            )
            next_pass = self.next_pass(record.plan_id)
            emit(
                "INFO",
                self.component,
                "intake",
                "planner_plan_accepted",
                workflow_id=workflow_id,
                plan_id=record.plan_id,
                plan_version=record.plan_version,
                semantic_digest=record.semantic_digest,
                pass_count=len(record.pass_states),
                next_pass_id=next_pass.pass_id,
                next_pass_status=str(next_pass.status),
            )
            return PlannerPlanIntakeOutcome(plan=record, next_pass=next_pass)

    def read(self, plan_id: str) -> PlannerPlanRecord:
        return self.store.read(plan_id)

    def for_workflow(self, workflow_id: str) -> PlannerPlanRecord | None:
        records = self.store.for_workflow(workflow_id)
        if not records:
            return None
        if len(records) != 1:
            raise ControllerError(
                "CONTROLLER_PLANNER_PLAN_CONFLICT",
                "V1 workflow has more than one persisted Planner plan",
                {
                    "workflow_id": workflow_id,
                    "plan_ids": [item.plan_id for item in records],
                },
            )
        return records[0]

    def next_pass(self, plan_id: str) -> PlannerNextPass:
        with controller_span("planner_plan.next_pass", plan_id=plan_id):
            record = self.store.read(plan_id)
            states = {item.pass_id: item for item in record.pass_states}
            completed = tuple(
                item.pass_id
                for item in record.pass_states
                if item.status is PlannerPassStatus.COMPLETE
            )
            failed = tuple(
                item.pass_id
                for item in record.pass_states
                if item.status is PlannerPassStatus.FAILED
            )

            if record.status is PlannerPlanStatus.COMPLETE:
                return PlannerNextPass(
                    plan_id=record.plan_id,
                    plan_version=record.plan_version,
                    workflow_id=record.workflow_id,
                    status=PlannerNextPassStatus.PLAN_COMPLETE,
                    completed_passes=completed,
                    failed_passes=failed,
                )

            if record.status is PlannerPlanStatus.BLOCKED or failed:
                return PlannerNextPass(
                    plan_id=record.plan_id,
                    plan_version=record.plan_version,
                    workflow_id=record.workflow_id,
                    status=PlannerNextPassStatus.BLOCKED,
                    blocked_by=failed,
                    completed_passes=completed,
                    failed_passes=failed,
                )

            ordered = _ordered_passes(record.semantic_plan)
            completed_set = set(completed)

            if len(completed_set) == len(ordered):
                completed_record = replace(
                    record,
                    status=PlannerPlanStatus.COMPLETE,
                    updated_at=utc_now(),
                )
                self.store.save(completed_record)
                return PlannerNextPass(
                    plan_id=record.plan_id,
                    plan_version=record.plan_version,
                    workflow_id=record.workflow_id,
                    status=PlannerNextPassStatus.PLAN_COMPLETE,
                    completed_passes=completed,
                )

            for pass_spec, stage_id in ordered:
                state = states[pass_spec.pass_id]
                if state.status is not PlannerPassStatus.PENDING:
                    continue
                blockers = self._blockers(
                    record.semantic_plan,
                    pass_spec=pass_spec,
                    stage_id=stage_id,
                    completed=completed_set,
                )
                if not blockers:
                    emit(
                        "INFO",
                        self.component,
                        "next_pass",
                        "planner_next_pass_selected",
                        plan_id=record.plan_id,
                        plan_version=record.plan_version,
                        pass_id=pass_spec.pass_id,
                        stage_id=stage_id,
                        completed_pass_count=len(completed),
                    )
                    return PlannerNextPass(
                        plan_id=record.plan_id,
                        plan_version=record.plan_version,
                        workflow_id=record.workflow_id,
                        status=PlannerNextPassStatus.READY,
                        pass_id=pass_spec.pass_id,
                        stage_id=stage_id,
                        pass_spec=pass_spec,
                        completed_passes=completed,
                        failed_passes=failed,
                    )

            pending_blockers: set[str] = set()
            for pass_spec, stage_id in ordered:
                if states[pass_spec.pass_id].status is PlannerPassStatus.PENDING:
                    pending_blockers.update(
                        self._blockers(
                            record.semantic_plan,
                            pass_spec=pass_spec,
                            stage_id=stage_id,
                            completed=completed_set,
                        )
                    )
            emit(
                "ERROR",
                self.component,
                "next_pass",
                "planner_no_eligible_pass",
                plan_id=record.plan_id,
                plan_version=record.plan_version,
                completed_passes=list(completed),
                blocked_by=sorted(pending_blockers),
            )
            return PlannerNextPass(
                plan_id=record.plan_id,
                plan_version=record.plan_version,
                workflow_id=record.workflow_id,
                status=PlannerNextPassStatus.NO_ELIGIBLE_PASS,
                blocked_by=tuple(sorted(pending_blockers)),
                completed_passes=completed,
                failed_passes=failed,
            )

    def mark_pass_complete(self, plan_id: str, pass_id: str) -> PlannerPlanRecord:
        """Mechanically record completion so dependency resolution can advance."""
        return self._set_pass_terminal(
            plan_id,
            pass_id,
            status=PlannerPassStatus.COMPLETE,
            failure_reason=None,
        )

    def mark_pass_failed(
        self,
        plan_id: str,
        pass_id: str,
        *,
        reason: str,
    ) -> PlannerPlanRecord:
        if not isinstance(reason, str) or not reason.strip():
            raise ControllerError(
                "CONTROLLER_PLANNER_PASS_STATE_INVALID",
                "failed Pass requires a reason",
            )
        return self._set_pass_terminal(
            plan_id,
            pass_id,
            status=PlannerPassStatus.FAILED,
            failure_reason=reason.strip(),
        )

    def _set_pass_terminal(
        self,
        plan_id: str,
        pass_id: str,
        *,
        status: PlannerPassStatus,
        failure_reason: str | None,
    ) -> PlannerPlanRecord:
        with controller_span(
            "planner_plan.set_pass_terminal",
            plan_id=plan_id,
            pass_id=pass_id,
            pass_status=str(status),
        ):
            record = self.store.read(plan_id)
            target = next(
                (item for item in record.pass_states if item.pass_id == pass_id),
                None,
            )
            if target is None:
                raise ControllerError(
                    "CONTROLLER_PLANNER_PASS_MISSING",
                    "Pass does not exist in Planner plan",
                    {"plan_id": plan_id, "pass_id": pass_id},
                )

            if target.status is status:
                if (
                    status is PlannerPassStatus.FAILED
                    and target.failure_reason != failure_reason
                ):
                    raise ControllerError(
                        "CONTROLLER_PLANNER_PASS_STATE_CONFLICT",
                        "failed Pass replay has a different failure reason",
                        {
                            "plan_id": plan_id,
                            "pass_id": pass_id,
                            "recorded_reason": target.failure_reason,
                            "requested_reason": failure_reason,
                        },
                    )
                return record

            if record.status is not PlannerPlanStatus.ACTIVE:
                raise ControllerError(
                    "CONTROLLER_PLANNER_PLAN_NOT_ACTIVE",
                    "Pass state can change only while the plan is ACTIVE",
                    {
                        "plan_id": plan_id,
                        "plan_status": str(record.status),
                    },
                )

            if target.status is not PlannerPassStatus.PENDING:
                raise ControllerError(
                    "CONTROLLER_PLANNER_PASS_STATE_CONFLICT",
                    "terminal Pass state cannot be replaced",
                    {
                        "plan_id": plan_id,
                        "pass_id": pass_id,
                        "existing_status": str(target.status),
                        "requested_status": str(status),
                    },
                )

            eligible = self.next_pass(plan_id)
            if (
                eligible.status is not PlannerNextPassStatus.READY
                or eligible.pass_id != pass_id
            ):
                raise ControllerError(
                    "CONTROLLER_PLANNER_PASS_NOT_ELIGIBLE",
                    "only the deterministic next eligible Pass may change execution state",
                    {
                        "plan_id": plan_id,
                        "requested_pass_id": pass_id,
                        "next_pass_status": str(eligible.status),
                        "next_pass_id": eligible.pass_id,
                        "blocked_by": list(eligible.blocked_by),
                    },
                )

            now = utc_now()
            replacement = replace(
                target,
                status=status,
                completed_at=now if status is PlannerPassStatus.COMPLETE else None,
                failed_at=now if status is PlannerPassStatus.FAILED else None,
                failure_reason=failure_reason,
            )
            updated_states = tuple(
                replacement if item.pass_id == pass_id else item
                for item in record.pass_states
            )
            plan_status = (
                PlannerPlanStatus.BLOCKED
                if status is PlannerPassStatus.FAILED
                else (
                    PlannerPlanStatus.COMPLETE
                    if all(
                        item.status is PlannerPassStatus.COMPLETE
                        for item in updated_states
                    )
                    else PlannerPlanStatus.ACTIVE
                )
            )
            updated = replace(
                record,
                pass_states=updated_states,
                status=plan_status,
                updated_at=now,
            )
            self.store.save(updated)
            emit(
                "INFO",
                self.component,
                "set_pass_terminal",
                "planner_pass_state_changed",
                plan_id=plan_id,
                plan_version=record.plan_version,
                pass_id=pass_id,
                pass_status=str(status),
                plan_status=str(plan_status),
                failure_reason=failure_reason,
            )
            return updated

    def _require_filesystem_authority(self, plan: ExecutionPlan) -> None:
        """Apply deterministic authority only; never judge semantic necessity."""
        for pass_spec, _ in _ordered_passes(plan):
            for task in pass_spec.tasks:
                filesystem = task.filesystem
                for path in filesystem.read_paths:
                    self.filesystem_authority.require_allowed(
                        FilesystemOperation.READ,
                        path,
                    )
                for path in filesystem.write_paths:
                    self.filesystem_authority.require_allowed(
                        FilesystemOperation.WRITE,
                        path,
                    )
                for path in filesystem.create_paths:
                    self.filesystem_authority.require_allowed(
                        FilesystemOperation.CREATE,
                        path,
                    )
                for path in filesystem.delete_paths:
                    self.filesystem_authority.require_allowed(
                        FilesystemOperation.DELETE,
                        path,
                    )
                for move in filesystem.move_paths:
                    self.filesystem_authority.require_allowed(
                        FilesystemOperation.MOVE,
                        move.source,
                        destination=move.destination,
                    )

    @staticmethod
    def _blockers(
        plan: ExecutionPlan,
        *,
        pass_spec: PassSpec,
        stage_id: str | None,
        completed: set[str],
    ) -> tuple[str, ...]:
        blockers: list[str] = [
            dependency
            for dependency in pass_spec.depends_on
            if dependency not in completed
        ]

        if stage_id is not None:
            stage = next(
                item for item in plan.stages if item.stage_id == stage_id
            )
            for dependency_stage_id in stage.depends_on:
                dependency_stage = next(
                    item
                    for item in plan.stages
                    if item.stage_id == dependency_stage_id
                )
                for dependency_pass in dependency_stage.passes:
                    if dependency_pass.pass_id not in completed:
                        blockers.append(dependency_pass.pass_id)

        return tuple(dict.fromkeys(blockers))


def _ordered_passes(plan: ExecutionPlan) -> tuple[tuple[PassSpec, str | None], ...]:
    if plan.stages:
        return tuple(
            (pass_spec, stage.stage_id)
            for stage in plan.stages
            for pass_spec in stage.passes
        )
    return tuple((pass_spec, None) for pass_spec in plan.passes)
