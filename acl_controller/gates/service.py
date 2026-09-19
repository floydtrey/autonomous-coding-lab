"""Generic human/external approval gates."""
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

from ..diagnostics import controller_span
from ..errors import ControllerError
from ..models import WorkflowStatus, utc_now
from ..state import WorkflowStateService


class GateStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class GateRecord:
    gate_id: str
    workflow_id: str
    gate_type: str
    requested_by: str
    payload: Mapping[str, Any]
    status: GateStatus = GateStatus.PENDING
    decision_by: str | None = None
    decision_note: str | None = None
    created_at: str = field(default_factory=utc_now)
    resolved_at: str | None = None

    @classmethod
    def create(
        cls,
        workflow_id: str,
        gate_type: str,
        requested_by: str,
        payload: Mapping[str, Any],
    ) -> "GateRecord":
        for value, label in ((gate_type, "gate type"), (requested_by, "requested_by")):
            if not isinstance(value, str) or not value.strip():
                raise ControllerError("CONTROLLER_GATE_INVALID", f"{label} is required")
        if not isinstance(payload, Mapping):
            raise ControllerError("CONTROLLER_GATE_INVALID", "gate payload must be a mapping")
        return cls(
            gate_id=CoreIdentity.new("gate").value,
            workflow_id=workflow_id,
            gate_type=gate_type,
            requested_by=requested_by,
            payload=dict(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "workflow_id": self.workflow_id,
            "gate_type": self.gate_type,
            "requested_by": self.requested_by,
            "payload": dict(self.payload),
            "status": str(self.status),
            "decision_by": self.decision_by,
            "decision_note": self.decision_note,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "GateRecord":
        try:
            return cls(
                gate_id=value["gate_id"],
                workflow_id=value["workflow_id"],
                gate_type=value["gate_type"],
                requested_by=value["requested_by"],
                payload=dict(value["payload"]),
                status=GateStatus(value["status"]),
                decision_by=value.get("decision_by"),
                decision_note=value.get("decision_note"),
                created_at=value["created_at"],
                resolved_at=value.get("resolved_at"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError("CONTROLLER_GATE_INVALID", "gate record is malformed") from exc


class JsonGateStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def create(self, record: GateRecord) -> GateRecord:
        with controller_span("gate_store.create", workflow_id=record.workflow_id, gate_id=record.gate_id, gate_type=record.gate_type):
            path = self._path(record.gate_id)
            with self._lock:
                if path.exists():
                    raise ControllerError("CONTROLLER_GATE_EXISTS", "gate already exists")
                self._write(path, record)
            return record

    def read(self, gate_id: str) -> GateRecord:
        with controller_span("gate_store.read", gate_id=gate_id):
            path = self._path(gate_id)
            try:
                return GateRecord.from_mapping(json.loads(path.read_text(encoding="utf-8")))
            except FileNotFoundError as exc:
                raise ControllerError("CONTROLLER_GATE_MISSING", "gate does not exist", {"gate_id": gate_id}) from exc
            except (OSError, json.JSONDecodeError) as exc:
                raise ControllerError("CONTROLLER_GATE_READ_FAILED", "gate could not be read", {"gate_id": gate_id}) from exc

    def for_workflow(self, workflow_id: str) -> tuple[GateRecord, ...]:
        directory = self.root / "gates"
        if not directory.exists():
            return ()
        records = []
        for path in sorted(directory.glob("gate_*.json")):
            try:
                record = GateRecord.from_mapping(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, ControllerError) as exc:
                raise ControllerError(
                    "CONTROLLER_GATE_READ_FAILED",
                    "one or more gate records are unreadable",
                    {"path": str(path)},
                ) from exc
            if record.workflow_id == workflow_id:
                records.append(record)
        return tuple(records)

    def save(self, record: GateRecord) -> GateRecord:
        with controller_span("gate_store.save", workflow_id=record.workflow_id, gate_id=record.gate_id):
            path = self._path(record.gate_id)
            with self._lock:
                current = self.read(record.gate_id)
                if current.status is not GateStatus.PENDING:
                    raise ControllerError("CONTROLLER_GATE_RESOLVED", "gate is already resolved")
                self._write(path, record)
            return record

    def _path(self, gate_id: str) -> Path:
        if not isinstance(gate_id, str) or not gate_id.startswith("gate:"):
            raise ControllerError("CONTROLLER_GATE_INVALID", "gate ID is invalid")
        return self.root / "gates" / f"{gate_id.replace(':', '_')}.json"

    @staticmethod
    def _write(path: Path, record: GateRecord) -> None:
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
            raise ControllerError("CONTROLLER_GATE_WRITE_FAILED", "gate could not be persisted") from exc


class GateService:
    component = "controller.gates"

    def __init__(self, state: WorkflowStateService, store: JsonGateStore) -> None:
        self.state = state
        self.store = store

    def request(
        self,
        workflow_id: str,
        *,
        gate_type: str,
        requested_by: str,
        payload: Mapping[str, Any],
    ) -> GateRecord:
        with controller_span("gates.request", workflow_id=workflow_id, gate_type=gate_type, requested_by=requested_by):
            workflow = self.state.read(workflow_id)
            gate = GateRecord.create(workflow_id, gate_type, requested_by, payload)
            self.store.create(gate)
            self.state.transition(
                workflow_id,
                WorkflowStatus.WAITING,
                waiting_for=f"gate:{gate.gate_id}",
                blocker=None,
            )
            emit(
                "INFO",
                self.component,
                "request",
                "gate_requested",
                workflow_id=workflow_id,
                gate_id=gate.gate_id,
                gate_type=gate_type,
                requested_by=requested_by,
                prior_status=str(workflow.status),
                stage=workflow.stage,
            )
            return gate

    def decide(
        self,
        gate_id: str,
        *,
        approved: bool,
        decision_by: str,
        note: str | None = None,
    ) -> GateRecord:
        with controller_span("gates.decide", gate_id=gate_id, approved=approved, decision_by=decision_by):
            if not isinstance(decision_by, str) or not decision_by.strip():
                raise ControllerError("CONTROLLER_GATE_INVALID", "decision_by is required")
            current = self.store.read(gate_id)
            if current.status is not GateStatus.PENDING:
                raise ControllerError("CONTROLLER_GATE_RESOLVED", "gate is already resolved")
            if decision_by == current.requested_by:
                raise ControllerError(
                    "CONTROLLER_GATE_SELF_APPROVAL_DENIED",
                    "gate requester cannot decide its own gate",
                    {"gate_id": gate_id, "requested_by": current.requested_by},
                )
            status = GateStatus.APPROVED if approved else GateStatus.REJECTED
            resolved = replace(
                current,
                status=status,
                decision_by=decision_by,
                decision_note=note,
                resolved_at=utc_now(),
            )
            self.store.save(resolved)
            if approved:
                self.state.transition(
                    current.workflow_id,
                    WorkflowStatus.READY,
                    waiting_for=None,
                    blocker=None,
                )
            else:
                self.state.transition(
                    current.workflow_id,
                    WorkflowStatus.BLOCKED,
                    waiting_for=None,
                    blocker={
                        "code": "GATE_REJECTED",
                        "gate_id": gate_id,
                        "gate_type": current.gate_type,
                        "decision_by": decision_by,
                        "note": note,
                    },
                )
            emit(
                "INFO",
                self.component,
                "decide",
                "gate_decided",
                workflow_id=current.workflow_id,
                gate_id=gate_id,
                gate_type=current.gate_type,
                approved=approved,
                requested_by=current.requested_by,
                decision_by=decision_by,
                note=note,
            )
            return resolved

    def read(self, gate_id: str) -> GateRecord:
        return self.store.read(gate_id)
