"""Controller-owned workflow state and simple JSON persistence."""
from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Mapping, Protocol

from acl_core.canonical import canonical_json
from acl_core.diagnostics import emit

from .diagnostics import controller_span
from .errors import ControllerError
from .models import ResultReference, TERMINAL_STATUSES, WorkflowRecord, WorkflowStatus


_UNCHANGED = object()


_ALLOWED_TRANSITIONS: dict[WorkflowStatus, frozenset[WorkflowStatus]] = {
    WorkflowStatus.NEW: frozenset({WorkflowStatus.READY, WorkflowStatus.WAITING, WorkflowStatus.BLOCKED, WorkflowStatus.CANCELLED, WorkflowStatus.FAILED}),
    WorkflowStatus.READY: frozenset({WorkflowStatus.RUNNING, WorkflowStatus.WAITING, WorkflowStatus.BLOCKED, WorkflowStatus.CANCELLED, WorkflowStatus.FAILED}),
    WorkflowStatus.RUNNING: frozenset({WorkflowStatus.READY, WorkflowStatus.WAITING, WorkflowStatus.BLOCKED, WorkflowStatus.COMPLETE, WorkflowStatus.CANCELLED, WorkflowStatus.FAILED}),
    WorkflowStatus.WAITING: frozenset({WorkflowStatus.READY, WorkflowStatus.RUNNING, WorkflowStatus.BLOCKED, WorkflowStatus.CANCELLED, WorkflowStatus.FAILED}),
    WorkflowStatus.BLOCKED: frozenset({WorkflowStatus.READY, WorkflowStatus.CANCELLED, WorkflowStatus.FAILED}),
    WorkflowStatus.COMPLETE: frozenset(),
    WorkflowStatus.FAILED: frozenset(),
    WorkflowStatus.CANCELLED: frozenset(),
}


class WorkflowStore(Protocol):
    def create(self, workflow: WorkflowRecord) -> WorkflowRecord: ...
    def read(self, workflow_id: str) -> WorkflowRecord: ...
    def save(self, workflow: WorkflowRecord, *, expected_generation: int) -> WorkflowRecord: ...


class JsonWorkflowStore:
    """Small local Controller-state store; unrelated to target/project resources."""

    component = "controller.state_store"

    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def _path(self, workflow_id: str) -> Path:
        if not isinstance(workflow_id, str) or not workflow_id.startswith("workflow:"):
            raise ControllerError("CONTROLLER_WORKFLOW_ID_INVALID", "workflow ID is invalid")
        return self.root / "workflows" / f"{workflow_id.replace(':', '_')}.json"

    def create(self, workflow: WorkflowRecord) -> WorkflowRecord:
        with controller_span("state_store.create", workflow_id=workflow.workflow_id):
            path = self._path(workflow.workflow_id)
            with self._lock:
                if path.exists():
                    raise ControllerError("CONTROLLER_WORKFLOW_EXISTS", "workflow already exists", {"workflow_id": workflow.workflow_id})
                self._write(path, workflow)
            return workflow

    def read(self, workflow_id: str) -> WorkflowRecord:
        with controller_span("state_store.read", workflow_id=workflow_id):
            path = self._path(workflow_id)
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError as exc:
                raise ControllerError("CONTROLLER_WORKFLOW_MISSING", "workflow does not exist", {"workflow_id": workflow_id}) from exc
            except (OSError, json.JSONDecodeError) as exc:
                raise ControllerError("CONTROLLER_STATE_READ_FAILED", "workflow state could not be read", {"workflow_id": workflow_id}) from exc
            return WorkflowRecord.from_mapping(value)

    def save(self, workflow: WorkflowRecord, *, expected_generation: int) -> WorkflowRecord:
        with controller_span(
            "state_store.save",
            workflow_id=workflow.workflow_id,
            expected_generation=expected_generation,
            new_generation=workflow.generation,
        ):
            path = self._path(workflow.workflow_id)
            with self._lock:
                current = self.read(workflow.workflow_id)
                if current.generation != expected_generation:
                    raise ControllerError(
                        "CONTROLLER_STATE_STALE",
                        "workflow changed since it was read",
                        {
                            "workflow_id": workflow.workflow_id,
                            "expected_generation": expected_generation,
                            "observed_generation": current.generation,
                        },
                    )
                if workflow.generation != expected_generation + 1:
                    raise ControllerError(
                        "CONTROLLER_STATE_INVALID",
                        "workflow generation must advance exactly once",
                        {
                            "workflow_id": workflow.workflow_id,
                            "expected_generation": expected_generation + 1,
                            "observed_generation": workflow.generation,
                        },
                    )
                self._write(path, workflow)
            return workflow

    def _write(self, path: Path, workflow: WorkflowRecord) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        raw = canonical_json(workflow.to_dict()) + "\n"
        try:
            temp.write_text(raw, encoding="utf-8")
            os.replace(temp, path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ControllerError(
                "CONTROLLER_STATE_WRITE_FAILED",
                "workflow state could not be persisted",
                {"workflow_id": workflow.workflow_id, "path": str(path)},
            ) from exc


class WorkflowStateService:
    component = "controller.state"

    def __init__(self, store: WorkflowStore) -> None:
        self.store = store

    def create(self, workflow: WorkflowRecord) -> WorkflowRecord:
        with controller_span("state.create", workflow_id=workflow.workflow_id, request_id=workflow.request.request_id):
            created = self.store.create(workflow)
            emit(
                "INFO",
                self.component,
                "create",
                "workflow_created",
                workflow_id=workflow.workflow_id,
                request_kind=workflow.request.kind,
                status=str(workflow.status),
                stage=workflow.stage,
            )
            return created

    def transition(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        *,
        stage: str | None = None,
        active_action: str | None | object = _UNCHANGED,
        active_role: str | None | object = _UNCHANGED,
        active_attempt_id: str | None | object = _UNCHANGED,
        authority_grant_id: str | None | object = _UNCHANGED,
        waiting_for: str | None | object = _UNCHANGED,
        blocker: Mapping[str, Any] | None | object = _UNCHANGED,
    ) -> WorkflowRecord:
        with controller_span("state.transition", workflow_id=workflow_id, target_status=str(status), target_stage=stage):
            current = self.store.read(workflow_id)
            if current.status in TERMINAL_STATUSES:
                raise ControllerError(
                    "CONTROLLER_WORKFLOW_TERMINAL",
                    "terminal workflow cannot transition",
                    {"workflow_id": workflow_id, "status": str(current.status)},
                )
            if status != current.status and status not in _ALLOWED_TRANSITIONS[current.status]:
                raise ControllerError(
                    "CONTROLLER_TRANSITION_INVALID",
                    "workflow status transition is not allowed",
                    {"from": str(current.status), "to": str(status)},
                )
            updated = current.evolved(
                status=status,
                stage=current.stage if stage is None else stage,
                active_action=current.active_action if active_action is _UNCHANGED else active_action,
                active_role=current.active_role if active_role is _UNCHANGED else active_role,
                active_attempt_id=current.active_attempt_id if active_attempt_id is _UNCHANGED else active_attempt_id,
                authority_grant_id=current.authority_grant_id if authority_grant_id is _UNCHANGED else authority_grant_id,
                waiting_for=current.waiting_for if waiting_for is _UNCHANGED else waiting_for,
                blocker=(
                    current.blocker
                    if blocker is _UNCHANGED
                    else (dict(blocker) if blocker is not None else None)
                ),
            )
            saved = self.store.save(updated, expected_generation=current.generation)
            emit(
                "INFO",
                self.component,
                "transition",
                "state_transition",
                workflow_id=workflow_id,
                from_status=str(current.status),
                to_status=str(saved.status),
                from_stage=current.stage,
                to_stage=saved.stage,
                generation=saved.generation,
                active_action=saved.active_action,
                active_role=saved.active_role,
                active_attempt_id=saved.active_attempt_id,
                authority_grant_id=saved.authority_grant_id,
                waiting_for=saved.waiting_for,
                blocker=saved.blocker,
            )
            return saved

    def add_result(self, workflow_id: str, result: ResultReference) -> WorkflowRecord:
        with controller_span("state.add_result", workflow_id=workflow_id, result_id=result.result_id, result_type=result.result_type):
            current = self.store.read(workflow_id)
            if current.status in TERMINAL_STATUSES:
                raise ControllerError("CONTROLLER_WORKFLOW_TERMINAL", "cannot add a result to a terminal workflow")
            if any(item.result_id == result.result_id for item in current.result_references):
                return current
            updated = current.evolved(result_references=(*current.result_references, result))
            saved = self.store.save(updated, expected_generation=current.generation)
            emit(
                "INFO",
                self.component,
                "add_result",
                "result_attached",
                workflow_id=workflow_id,
                result_id=result.result_id,
                result_type=result.result_type,
                producer=result.producer,
                reference=result.reference,
                generation=saved.generation,
            )
            return saved

    def increment_retry(self, workflow_id: str) -> WorkflowRecord:
        with controller_span("state.increment_retry", workflow_id=workflow_id):
            current = self.store.read(workflow_id)
            if current.status in TERMINAL_STATUSES:
                raise ControllerError("CONTROLLER_WORKFLOW_TERMINAL", "terminal workflow cannot increment retry count")
            updated = current.evolved(retry_count=current.retry_count + 1)
            saved = self.store.save(updated, expected_generation=current.generation)
            emit(
                "INFO",
                self.component,
                "increment_retry",
                "retry_count_changed",
                workflow_id=workflow_id,
                previous=current.retry_count,
                current=saved.retry_count,
                generation=saved.generation,
            )
            return saved

    def read(self, workflow_id: str) -> WorkflowRecord:
        return self.store.read(workflow_id)
