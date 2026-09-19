"""Bounded Worker-to-Planner consultation service.

PL09 establishes the advisory conversation contract without wiring a real
Worker. A caller may submit synthetic Worker questions. ACL persists the
consultation, enforces a configurable exchange ceiling, invokes Planner in
WORKER_CONSULTATION mode, and either returns Planner guidance or elevates a
material question to the operator.

One exchange means one Worker question followed by Planner's eventual answer.
If Planner elevates to the operator, resuming after the operator answer finishes
that same exchange; it does not consume a second Worker-to-Planner exchange.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Mapping, Sequence

from acl_core import CoreIdentity
from acl_core.canonical import canonical_json
from acl_core.diagnostics import emit
from acl_roles.planner import (
    PlannerDisposition,
    PlannerInput,
    PlannerInvocationMode,
    PlannerResult,
    PlannerRuntimeRequest,
    PlannerRuntimeResponse,
    PlannerRuntimeService,
    WorkerConsultation,
    resume_planner_input,
)

from ..clarification import ClarificationService, ClarificationStatus
from ..diagnostics import controller_span
from ..errors import ControllerError
from ..models import WorkflowStatus, utc_now
from ..state import WorkflowStateService


CONSULTATION_CONFIG_SCHEMA = "acl-planner-consultation:v1"


class PlannerConsultationStatus(StrEnum):
    OPEN = "OPEN"
    WAITING_USER = "WAITING_USER"
    EXHAUSTED = "EXHAUSTED"
    CLOSED = "CLOSED"


class PlannerConsultationOutcomeStatus(StrEnum):
    ANSWERED = "ANSWERED"
    ELEVATED = "ELEVATED"
    EXCHANGE_LIMIT_REACHED = "EXCHANGE_LIMIT_REACHED"
    CANNOT_ANSWER = "CANNOT_ANSWER"


@dataclass(frozen=True)
class PlannerConsultationConfig:
    max_exchanges: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_exchanges, bool)
            or not isinstance(self.max_exchanges, int)
            or self.max_exchanges < 1
        ):
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_CONFIG_INVALID",
                "max_exchanges must be a positive integer",
            )

    @classmethod
    def load(cls, path: str | Path) -> "PlannerConsultationConfig":
        path = Path(path).expanduser().resolve()
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_CONFIG_MISSING",
                "Planner consultation configuration is missing",
                {"path": str(path)},
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_CONFIG_INVALID",
                "Planner consultation configuration cannot be read",
                {"path": str(path)},
            ) from exc
        if not isinstance(value, Mapping) or value.get("schema_version") != CONSULTATION_CONFIG_SCHEMA:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_CONFIG_INVALID",
                "Planner consultation configuration schema is invalid",
                {"path": str(path)},
            )
        return cls(max_exchanges=value.get("max_exchanges"))


@dataclass(frozen=True)
class PlannerConsultationExchange:
    exchange_number: int
    question: str
    reason: str
    current_state_summary: str
    task_id: str | None = None
    relevant_reference_ids: tuple[str, ...] = ()
    relevant_evidence: tuple[str, ...] = ()
    planner_disposition: str | None = None
    answer: str | None = None
    sources: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    clarification_id: str | None = None
    reason_codes: tuple[str, ...] = ()
    notes: str | None = None
    runtime_metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    resolved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "exchange_number": self.exchange_number,
            "question": self.question,
            "reason": self.reason,
            "current_state_summary": self.current_state_summary,
            "task_id": self.task_id,
            "relevant_reference_ids": list(self.relevant_reference_ids),
            "relevant_evidence": list(self.relevant_evidence),
            "planner_disposition": self.planner_disposition,
            "answer": self.answer,
            "sources": list(self.sources),
            "references": list(self.references),
            "clarification_id": self.clarification_id,
            "reason_codes": list(self.reason_codes),
            "notes": self.notes,
            "runtime_metadata": dict(self.runtime_metadata),
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerConsultationExchange":
        try:
            return cls(
                exchange_number=int(value["exchange_number"]),
                question=value["question"],
                reason=value["reason"],
                current_state_summary=value["current_state_summary"],
                task_id=value.get("task_id"),
                relevant_reference_ids=tuple(value.get("relevant_reference_ids", [])),
                relevant_evidence=tuple(value.get("relevant_evidence", [])),
                planner_disposition=value.get("planner_disposition"),
                answer=value.get("answer"),
                sources=tuple(value.get("sources", [])),
                references=tuple(value.get("references", [])),
                clarification_id=value.get("clarification_id"),
                reason_codes=tuple(value.get("reason_codes", [])),
                notes=value.get("notes"),
                runtime_metadata=dict(value.get("runtime_metadata", {})),
                created_at=value["created_at"],
                resolved_at=value.get("resolved_at"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_STATE_INVALID",
                "Planner consultation exchange is malformed",
            ) from exc


@dataclass(frozen=True)
class PlannerConsultationRecord:
    consultation_id: str
    workflow_id: str
    plan_id: str
    pass_id: str
    original_request: Mapping[str, Any]
    routing_context: Mapping[str, Any]
    max_exchanges: int
    exchanges: tuple[PlannerConsultationExchange, ...] = ()
    status: PlannerConsultationStatus = PlannerConsultationStatus.OPEN
    authority_grant_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        workflow_id: str,
        plan_id: str,
        pass_id: str,
        original_request: Mapping[str, Any],
        routing_context: Mapping[str, Any],
        max_exchanges: int,
        authority_grant_id: str | None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "PlannerConsultationRecord":
        for value, label in (
            (workflow_id, "workflow_id"),
            (plan_id, "plan_id"),
            (pass_id, "pass_id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ControllerError(
                    "CONTROLLER_PLANNER_CONSULTATION_INVALID",
                    f"{label} is required",
                )
        if not isinstance(original_request, Mapping) or not isinstance(routing_context, Mapping):
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_INVALID",
                "original_request and routing_context must be mappings",
            )
        return cls(
            consultation_id=CoreIdentity.new("plannerconsult").value,
            workflow_id=workflow_id,
            plan_id=plan_id,
            pass_id=pass_id,
            original_request=dict(original_request),
            routing_context=dict(routing_context),
            max_exchanges=max_exchanges,
            authority_grant_id=authority_grant_id,
            metadata=dict(metadata or {}),
        )

    @property
    def exchanges_used(self) -> int:
        return len(self.exchanges)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "acl-planner-consultation-state:v1",
            "consultation_id": self.consultation_id,
            "workflow_id": self.workflow_id,
            "plan_id": self.plan_id,
            "pass_id": self.pass_id,
            "original_request": dict(self.original_request),
            "routing_context": dict(self.routing_context),
            "max_exchanges": self.max_exchanges,
            "exchanges": [item.to_dict() for item in self.exchanges],
            "status": str(self.status),
            "authority_grant_id": self.authority_grant_id,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerConsultationRecord":
        if (
            not isinstance(value, Mapping)
            or value.get("schema_version") != "acl-planner-consultation-state:v1"
        ):
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_STATE_INVALID",
                "Planner consultation state schema is invalid",
            )
        try:
            return cls(
                consultation_id=value["consultation_id"],
                workflow_id=value["workflow_id"],
                plan_id=value["plan_id"],
                pass_id=value["pass_id"],
                original_request=dict(value["original_request"]),
                routing_context=dict(value["routing_context"]),
                max_exchanges=int(value["max_exchanges"]),
                exchanges=tuple(
                    PlannerConsultationExchange.from_mapping(item)
                    for item in value.get("exchanges", [])
                ),
                status=PlannerConsultationStatus(value["status"]),
                authority_grant_id=value.get("authority_grant_id"),
                metadata=dict(value.get("metadata", {})),
                created_at=value["created_at"],
                updated_at=value["updated_at"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_STATE_INVALID",
                "Planner consultation state is malformed",
            ) from exc


class JsonPlannerConsultationStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def create(self, record: PlannerConsultationRecord) -> PlannerConsultationRecord:
        path = self._path(record.consultation_id)
        with self._lock:
            if path.exists():
                raise ControllerError(
                    "CONTROLLER_PLANNER_CONSULTATION_EXISTS",
                    "Planner consultation already exists",
                    {"consultation_id": record.consultation_id},
                )
            self._write(path, record)
        return record

    def read(self, consultation_id: str) -> PlannerConsultationRecord:
        try:
            return PlannerConsultationRecord.from_mapping(
                json.loads(self._path(consultation_id).read_text(encoding="utf-8"))
            )
        except FileNotFoundError as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_MISSING",
                "Planner consultation does not exist",
                {"consultation_id": consultation_id},
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_STATE_INVALID",
                "Planner consultation state cannot be read",
                {"consultation_id": consultation_id},
            ) from exc

    def save(self, record: PlannerConsultationRecord) -> PlannerConsultationRecord:
        with self._lock:
            self._write(self._path(record.consultation_id), record)
        return record

    def _path(self, consultation_id: str) -> Path:
        if (
            not isinstance(consultation_id, str)
            or not consultation_id.startswith("plannerconsult:")
        ):
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_INVALID",
                "Planner consultation ID is invalid",
            )
        return self.root / "planner-consultations" / f"{consultation_id.replace(':', '_')}.json"

    @staticmethod
    def _write(path: Path, record: PlannerConsultationRecord) -> None:
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
                "CONTROLLER_PLANNER_CONSULTATION_STATE_WRITE_FAILED",
                "Planner consultation state could not be persisted",
            ) from exc


@dataclass(frozen=True)
class PlannerConsultationOutcome:
    consultation_id: str
    workflow_id: str
    status: PlannerConsultationOutcomeStatus
    exchange_number: int | None
    exchanges_used: int
    max_exchanges: int
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
            "consultation_id": self.consultation_id,
            "workflow_id": self.workflow_id,
            "status": str(self.status),
            "exchange_number": self.exchange_number,
            "exchanges_used": self.exchanges_used,
            "max_exchanges": self.max_exchanges,
            "answer": self.answer,
            "sources": list(self.sources),
            "references": list(self.references),
            "clarification_id": self.clarification_id,
            "questions": [dict(item) for item in self.questions],
            "reason_codes": list(self.reason_codes),
            "notes": self.notes,
            "runtime_metadata": dict(self.runtime_metadata),
        }


class PlannerConsultationService:
    component = "controller.planner.consultation"

    def __init__(
        self,
        *,
        state: WorkflowStateService,
        runtime: PlannerRuntimeService,
        clarification: ClarificationService,
        store: JsonPlannerConsultationStore,
        config: PlannerConsultationConfig,
    ) -> None:
        self.state = state
        self.runtime = runtime
        self.clarification = clarification
        self.store = store
        self.config = config

    def start(
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
        relevant_reference_ids: Sequence[str] = (),
        relevant_evidence: Sequence[str] = (),
        authority_grant_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> PlannerConsultationOutcome:
        workflow = self.state.read(workflow_id)
        if workflow.status not in {WorkflowStatus.READY, WorkflowStatus.RUNNING}:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_STATE_INVALID",
                "Planner consultation can only start from READY or RUNNING workflow state",
                {"workflow_id": workflow_id, "status": str(workflow.status)},
            )
        if (
            authority_grant_id is not None
            and workflow.authority_grant_id != authority_grant_id
        ):
            raise ControllerError(
                "CONTROLLER_WORKFLOW_GRANT_MISMATCH",
                "Planner consultation grant differs from workflow authority",
                {
                    "workflow_id": workflow_id,
                    "workflow_grant_id": workflow.authority_grant_id,
                    "requested_grant_id": authority_grant_id,
                },
            )

        record = PlannerConsultationRecord.create(
            workflow_id=workflow_id,
            plan_id=plan_id,
            pass_id=pass_id,
            original_request=workflow.request.payload,
            routing_context=routing_context,
            max_exchanges=self.config.max_exchanges,
            authority_grant_id=authority_grant_id,
            metadata=metadata,
        )
        self.store.create(record)
        return self.ask(
            record.consultation_id,
            question=question,
            reason=reason,
            current_state_summary=current_state_summary,
            task_id=task_id,
            relevant_reference_ids=relevant_reference_ids,
            relevant_evidence=relevant_evidence,
        )

    def ask(
        self,
        consultation_id: str,
        *,
        question: str,
        reason: str,
        current_state_summary: str,
        task_id: str | None = None,
        relevant_reference_ids: Sequence[str] = (),
        relevant_evidence: Sequence[str] = (),
    ) -> PlannerConsultationOutcome:
        with controller_span(
            "planner_consultation.ask",
            consultation_id=consultation_id,
        ):
            record = self.store.read(consultation_id)
            if record.status is PlannerConsultationStatus.WAITING_USER:
                raise ControllerError(
                    "CONTROLLER_PLANNER_CONSULTATION_WAITING_USER",
                    "Planner consultation is waiting for operator input",
                    {"consultation_id": consultation_id},
                )
            if record.status in {
                PlannerConsultationStatus.EXHAUSTED,
                PlannerConsultationStatus.CLOSED,
            }:
                raise ControllerError(
                    "CONTROLLER_PLANNER_CONSULTATION_CLOSED",
                    "Planner consultation is not open for another exchange",
                    {
                        "consultation_id": consultation_id,
                        "status": str(record.status),
                    },
                )
            if record.exchanges_used >= record.max_exchanges:
                exhausted = replace(
                    record,
                    status=PlannerConsultationStatus.EXHAUSTED,
                    updated_at=utc_now(),
                )
                self.store.save(exhausted)
                emit(
                    "INFO",
                    self.component,
                    "ask",
                    "planner_consultation_exchange_limit_reached",
                    consultation_id=consultation_id,
                    workflow_id=record.workflow_id,
                    exchanges_used=record.exchanges_used,
                    max_exchanges=record.max_exchanges,
                )
                return PlannerConsultationOutcome(
                    consultation_id=consultation_id,
                    workflow_id=record.workflow_id,
                    status=PlannerConsultationOutcomeStatus.EXCHANGE_LIMIT_REACHED,
                    exchange_number=None,
                    exchanges_used=record.exchanges_used,
                    max_exchanges=record.max_exchanges,
                )

            exchange_number = record.exchanges_used + 1
            exchange = PlannerConsultationExchange(
                exchange_number=exchange_number,
                question=question,
                reason=reason,
                current_state_summary=current_state_summary,
                task_id=task_id,
                relevant_reference_ids=tuple(relevant_reference_ids),
                relevant_evidence=tuple(relevant_evidence),
            )
            record = replace(
                record,
                exchanges=(*record.exchanges, exchange),
                updated_at=utc_now(),
            )
            self.store.save(record)

            planner_input = self._planner_input(record, exchange)
            response = self.runtime.invoke(
                PlannerRuntimeRequest(
                    workflow_id=record.workflow_id,
                    planner_input=planner_input,
                    authority_grant_id=record.authority_grant_id,
                    metadata={
                        "consultation_id": record.consultation_id,
                        "exchange_number": exchange_number,
                        **dict(record.metadata),
                    },
                )
            )
            return self._apply_response(
                record,
                planner_input=planner_input,
                response=response,
            )

    def resume_elevation(
        self,
        clarification_id: str,
        *,
        answer: Mapping[str, Any],
        answered_by: str,
    ) -> PlannerConsultationOutcome:
        current = self.clarification.read(clarification_id)
        context = current.context
        if context.get("kind") != "planner_worker_consultation_elevation":
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_ELEVATION_INVALID",
                "clarification is not a Worker-to-Planner consultation elevation",
                {"clarification_id": clarification_id},
            )

        consultation_id = context.get("consultation_id")
        if not isinstance(consultation_id, str):
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_ELEVATION_INVALID",
                "consultation elevation is missing consultation_id",
                {"clarification_id": clarification_id},
            )
        record = self.store.read(consultation_id)
        if record.status is not PlannerConsultationStatus.WAITING_USER:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_STATE_INVALID",
                "consultation is not waiting for operator input",
                {
                    "consultation_id": consultation_id,
                    "status": str(record.status),
                },
            )
        try:
            original = PlannerInput.from_mapping(context["planner_input"])
            elevation = PlannerResult.from_mapping(context["planner_result"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_ELEVATION_INVALID",
                "consultation elevation context is malformed",
                {"clarification_id": clarification_id},
            ) from exc

        resumed_input = resume_planner_input(original, elevation, answer)

        if current.status is ClarificationStatus.PENDING:
            self.clarification.answer(
                clarification_id,
                answer=answer,
                answered_by=answered_by,
            )
        elif current.status is ClarificationStatus.ANSWERED:
            if dict(current.answer or {}) != dict(answer):
                raise ControllerError(
                    "CONTROLLER_CLARIFICATION_ANSWER_CONFLICT",
                    "consultation elevation already has a different operator answer",
                    {"clarification_id": clarification_id},
                )
        else:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_ELEVATION_INVALID",
                "consultation elevation cannot be resumed",
                {
                    "clarification_id": clarification_id,
                    "status": str(current.status),
                },
            )

        response = self.runtime.invoke(
            PlannerRuntimeRequest(
                workflow_id=record.workflow_id,
                planner_input=resumed_input,
                authority_grant_id=record.authority_grant_id,
                metadata={
                    "consultation_id": record.consultation_id,
                    "exchange_number": record.exchanges[-1].exchange_number,
                    "resumed_from_clarification_id": clarification_id,
                    **dict(record.metadata),
                },
            )
        )
        return self._apply_response(
            record,
            planner_input=resumed_input,
            response=response,
            resumed_clarification_id=clarification_id,
        )

    def close(self, consultation_id: str) -> PlannerConsultationRecord:
        record = self.store.read(consultation_id)
        closed = replace(
            record,
            status=PlannerConsultationStatus.CLOSED,
            updated_at=utc_now(),
        )
        return self.store.save(closed)

    def read(self, consultation_id: str) -> PlannerConsultationRecord:
        return self.store.read(consultation_id)

    def _planner_input(
        self,
        record: PlannerConsultationRecord,
        exchange: PlannerConsultationExchange,
    ) -> PlannerInput:
        return PlannerInput(
            invocation_mode=PlannerInvocationMode.WORKER_CONSULTATION,
            request=dict(record.original_request),
            routing_context=dict(record.routing_context),
            consultation=WorkerConsultation(
                plan_id=record.plan_id,
                pass_id=record.pass_id,
                task_id=exchange.task_id,
                question=exchange.question,
                reason=exchange.reason,
                current_state_summary=exchange.current_state_summary,
                relevant_reference_ids=exchange.relevant_reference_ids,
                relevant_evidence=exchange.relevant_evidence,
            ),
            metadata={
                "consultation_id": record.consultation_id,
                "exchange_number": exchange.exchange_number,
            },
        )

    def _apply_response(
        self,
        record: PlannerConsultationRecord,
        *,
        planner_input: PlannerInput,
        response: PlannerRuntimeResponse,
        resumed_clarification_id: str | None = None,
    ) -> PlannerConsultationOutcome:
        result = response.result
        if not record.exchanges:
            raise ControllerError(
                "CONTROLLER_PLANNER_CONSULTATION_STATE_INVALID",
                "consultation has no active exchange",
                {"consultation_id": record.consultation_id},
            )
        active = record.exchanges[-1]

        if result.disposition in {
            PlannerDisposition.DIRECT_RESPONSE,
            PlannerDisposition.QUERY_RESPONSE,
        }:
            if result.answer is None:
                raise ControllerError(
                    "CONTROLLER_PLANNER_CONSULTATION_RESPONSE_INVALID",
                    "Planner consultation response is missing its answer",
                )
            resolved = replace(
                active,
                planner_disposition=str(result.disposition),
                answer=result.answer.answer,
                sources=result.answer.sources,
                references=result.answer.references,
                clarification_id=resumed_clarification_id or active.clarification_id,
                reason_codes=result.reason_codes,
                notes=result.notes,
                runtime_metadata=dict(response.runtime_metadata),
                resolved_at=utc_now(),
            )
            updated = replace(
                record,
                exchanges=(*record.exchanges[:-1], resolved),
                status=PlannerConsultationStatus.OPEN,
                updated_at=utc_now(),
            )
            self.store.save(updated)
            emit(
                "INFO",
                self.component,
                "apply_response",
                "planner_consultation_answered",
                consultation_id=record.consultation_id,
                workflow_id=record.workflow_id,
                exchange_number=resolved.exchange_number,
                disposition=str(result.disposition),
                exchanges_used=updated.exchanges_used,
                max_exchanges=updated.max_exchanges,
            )
            return PlannerConsultationOutcome(
                consultation_id=record.consultation_id,
                workflow_id=record.workflow_id,
                status=PlannerConsultationOutcomeStatus.ANSWERED,
                exchange_number=resolved.exchange_number,
                exchanges_used=updated.exchanges_used,
                max_exchanges=updated.max_exchanges,
                answer=resolved.answer,
                sources=resolved.sources,
                references=resolved.references,
                reason_codes=resolved.reason_codes,
                notes=resolved.notes,
                runtime_metadata=resolved.runtime_metadata,
            )

        if result.disposition is PlannerDisposition.ELEVATION_REQUIRED:
            questions = tuple(item.to_dict() for item in result.questions)
            clarification = self.clarification.request(
                record.workflow_id,
                requested_by=f"planner-consultation:{record.consultation_id}",
                questions=questions,
                context={
                    "kind": "planner_worker_consultation_elevation",
                    "consultation_id": record.consultation_id,
                    "exchange_number": active.exchange_number,
                    "planner_input": planner_input.to_objective(),
                    "planner_result": result.to_dict(),
                    "authority_grant_id": record.authority_grant_id,
                    "runtime_metadata": dict(response.runtime_metadata),
                },
            )
            pending_exchange = replace(
                active,
                planner_disposition=str(result.disposition),
                clarification_id=clarification.clarification_id,
                reason_codes=result.reason_codes,
                notes=result.notes,
                runtime_metadata=dict(response.runtime_metadata),
            )
            waiting = replace(
                record,
                exchanges=(*record.exchanges[:-1], pending_exchange),
                status=PlannerConsultationStatus.WAITING_USER,
                updated_at=utc_now(),
            )
            self.store.save(waiting)
            emit(
                "INFO",
                self.component,
                "apply_response",
                "planner_consultation_elevated",
                consultation_id=record.consultation_id,
                workflow_id=record.workflow_id,
                exchange_number=active.exchange_number,
                clarification_id=clarification.clarification_id,
                question_count=len(questions),
            )
            return PlannerConsultationOutcome(
                consultation_id=record.consultation_id,
                workflow_id=record.workflow_id,
                status=PlannerConsultationOutcomeStatus.ELEVATED,
                exchange_number=active.exchange_number,
                exchanges_used=waiting.exchanges_used,
                max_exchanges=waiting.max_exchanges,
                clarification_id=clarification.clarification_id,
                questions=questions,
                reason_codes=result.reason_codes,
                notes=result.notes,
                runtime_metadata=dict(response.runtime_metadata),
            )

        if result.disposition is PlannerDisposition.CANNOT_PLAN:
            resolved = replace(
                active,
                planner_disposition=str(result.disposition),
                clarification_id=resumed_clarification_id or active.clarification_id,
                reason_codes=result.reason_codes,
                notes=result.notes,
                runtime_metadata=dict(response.runtime_metadata),
                resolved_at=utc_now(),
            )
            updated = replace(
                record,
                exchanges=(*record.exchanges[:-1], resolved),
                status=PlannerConsultationStatus.OPEN,
                updated_at=utc_now(),
            )
            self.store.save(updated)
            return PlannerConsultationOutcome(
                consultation_id=record.consultation_id,
                workflow_id=record.workflow_id,
                status=PlannerConsultationOutcomeStatus.CANNOT_ANSWER,
                exchange_number=resolved.exchange_number,
                exchanges_used=updated.exchanges_used,
                max_exchanges=updated.max_exchanges,
                reason_codes=result.reason_codes,
                notes=result.notes,
                runtime_metadata=dict(response.runtime_metadata),
            )

        raise ControllerError(
            "CONTROLLER_PLANNER_CONSULTATION_RESPONSE_INVALID",
            "WORKER_CONSULTATION returned a disposition that cannot be relayed to the Worker",
            {
                "consultation_id": record.consultation_id,
                "disposition": str(result.disposition),
            },
        )
