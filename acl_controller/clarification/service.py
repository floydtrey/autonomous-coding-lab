"""Generic clarification pause/resume mechanism."""
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

from ..diagnostics import controller_span
from ..errors import ControllerError
from ..models import WorkflowStatus, utc_now
from ..state import WorkflowStateService


class ClarificationStatus(StrEnum):
    PENDING = "PENDING"
    ANSWERED = "ANSWERED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class ClarificationRecord:
    clarification_id: str
    workflow_id: str
    requested_by: str
    questions: tuple[Mapping[str, Any], ...]
    status: ClarificationStatus = ClarificationStatus.PENDING
    context: Mapping[str, Any] = field(default_factory=dict)
    answer: Mapping[str, Any] | None = None
    answered_by: str | None = None
    created_at: str = field(default_factory=utc_now)
    resolved_at: str | None = None

    @classmethod
    def create(
        cls,
        workflow_id: str,
        requested_by: str,
        questions: Sequence[Mapping[str, Any]],
        *,
        context: Mapping[str, Any] | None = None,
    ) -> "ClarificationRecord":
        if not isinstance(requested_by, str) or not requested_by.strip():
            raise ControllerError("CONTROLLER_CLARIFICATION_INVALID", "requested_by is required")
        if not questions or any(not isinstance(item, Mapping) for item in questions):
            raise ControllerError("CONTROLLER_CLARIFICATION_INVALID", "clarification needs one or more structured questions")
        return cls(
            clarification_id=CoreIdentity.new("clarify").value,
            workflow_id=workflow_id,
            requested_by=requested_by,
            questions=tuple(dict(item) for item in questions),
            context=dict(context or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "clarification_id": self.clarification_id,
            "workflow_id": self.workflow_id,
            "requested_by": self.requested_by,
            "questions": [dict(item) for item in self.questions],
            "status": str(self.status),
            "context": dict(self.context),
            "answer": None if self.answer is None else dict(self.answer),
            "answered_by": self.answered_by,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ClarificationRecord":
        try:
            questions = value["questions"]
            if not isinstance(questions, list) or not questions or any(not isinstance(item, Mapping) for item in questions):
                raise ValueError("invalid questions")
            answer = value.get("answer")
            if answer is not None and not isinstance(answer, Mapping):
                raise ValueError("invalid answer")
            return cls(
                clarification_id=value["clarification_id"],
                workflow_id=value["workflow_id"],
                requested_by=value["requested_by"],
                questions=tuple(dict(item) for item in questions),
                status=ClarificationStatus(value["status"]),
                context=dict(value.get("context", {})),
                answer=None if answer is None else dict(answer),
                answered_by=value.get("answered_by"),
                created_at=value["created_at"],
                resolved_at=value.get("resolved_at"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError("CONTROLLER_CLARIFICATION_INVALID", "clarification record is malformed") from exc


class JsonClarificationStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def create(self, record: ClarificationRecord) -> ClarificationRecord:
        with controller_span("clarification_store.create", workflow_id=record.workflow_id, clarification_id=record.clarification_id):
            path = self._path(record.clarification_id)
            with self._lock:
                if path.exists():
                    raise ControllerError("CONTROLLER_CLARIFICATION_EXISTS", "clarification already exists")
                self._write(path, record)
            return record

    def read(self, clarification_id: str) -> ClarificationRecord:
        with controller_span("clarification_store.read", clarification_id=clarification_id):
            path = self._path(clarification_id)
            try:
                return ClarificationRecord.from_mapping(json.loads(path.read_text(encoding="utf-8")))
            except FileNotFoundError as exc:
                raise ControllerError("CONTROLLER_CLARIFICATION_MISSING", "clarification does not exist", {"clarification_id": clarification_id}) from exc
            except (OSError, json.JSONDecodeError) as exc:
                raise ControllerError("CONTROLLER_CLARIFICATION_READ_FAILED", "clarification could not be read", {"clarification_id": clarification_id}) from exc

    def for_workflow(self, workflow_id: str) -> tuple[ClarificationRecord, ...]:
        directory = self.root / "clarifications"
        if not directory.exists():
            return ()
        records = []
        for path in sorted(directory.glob("clarify_*.json")):
            try:
                record = ClarificationRecord.from_mapping(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, ControllerError) as exc:
                raise ControllerError(
                    "CONTROLLER_CLARIFICATION_READ_FAILED",
                    "one or more clarification records are unreadable",
                    {"path": str(path)},
                ) from exc
            if record.workflow_id == workflow_id:
                records.append(record)
        return tuple(records)

    def save(self, record: ClarificationRecord) -> ClarificationRecord:
        with controller_span("clarification_store.save", workflow_id=record.workflow_id, clarification_id=record.clarification_id):
            path = self._path(record.clarification_id)
            with self._lock:
                current = self.read(record.clarification_id)
                if current.status is not ClarificationStatus.PENDING:
                    raise ControllerError("CONTROLLER_CLARIFICATION_RESOLVED", "clarification is already resolved")
                self._write(path, record)
            return record

    def _path(self, clarification_id: str) -> Path:
        if not isinstance(clarification_id, str) or not clarification_id.startswith("clarify:"):
            raise ControllerError("CONTROLLER_CLARIFICATION_INVALID", "clarification ID is invalid")
        return self.root / "clarifications" / f"{clarification_id.replace(':', '_')}.json"

    @staticmethod
    def _write(path: Path, record: ClarificationRecord) -> None:
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
            raise ControllerError("CONTROLLER_CLARIFICATION_WRITE_FAILED", "clarification could not be persisted") from exc


class ClarificationService:
    component = "controller.clarification"

    def __init__(self, state: WorkflowStateService, store: JsonClarificationStore) -> None:
        self.state = state
        self.store = store

    def request(
        self,
        workflow_id: str,
        *,
        requested_by: str,
        questions: Sequence[Mapping[str, Any]],
        context: Mapping[str, Any] | None = None,
    ) -> ClarificationRecord:
        with controller_span("clarification.request", workflow_id=workflow_id, requested_by=requested_by):
            workflow = self.state.read(workflow_id)
            record = ClarificationRecord.create(workflow_id, requested_by, questions, context=context)
            self.store.create(record)
            self.state.transition(
                workflow_id,
                WorkflowStatus.WAITING,
                waiting_for=f"clarification:{record.clarification_id}",
                blocker=None,
            )
            emit(
                "INFO",
                self.component,
                "request",
                "clarification_requested",
                workflow_id=workflow_id,
                clarification_id=record.clarification_id,
                requested_by=requested_by,
                question_count=len(record.questions),
                prior_status=str(workflow.status),
                stage=workflow.stage,
            )
            return record

    def answer(
        self,
        clarification_id: str,
        *,
        answer: Mapping[str, Any],
        answered_by: str,
    ) -> ClarificationRecord:
        with controller_span("clarification.answer", clarification_id=clarification_id, answered_by=answered_by):
            if not isinstance(answer, Mapping):
                raise ControllerError("CONTROLLER_CLARIFICATION_INVALID", "clarification answer must be a mapping")
            if not isinstance(answered_by, str) or not answered_by.strip():
                raise ControllerError("CONTROLLER_CLARIFICATION_INVALID", "answered_by is required")
            current = self.store.read(clarification_id)
            if current.status is not ClarificationStatus.PENDING:
                raise ControllerError("CONTROLLER_CLARIFICATION_RESOLVED", "clarification is already resolved")
            resolved = replace(
                current,
                status=ClarificationStatus.ANSWERED,
                answer=dict(answer),
                answered_by=answered_by,
                resolved_at=utc_now(),
            )
            self.store.save(resolved)
            self.state.transition(
                current.workflow_id,
                WorkflowStatus.READY,
                waiting_for=None,
                blocker=None,
            )
            emit(
                "INFO",
                self.component,
                "answer",
                "clarification_answered",
                workflow_id=current.workflow_id,
                clarification_id=clarification_id,
                requested_by=current.requested_by,
                answered_by=answered_by,
            )
            return resolved

    def read(self, clarification_id: str) -> ClarificationRecord:
        return self.store.read(clarification_id)
