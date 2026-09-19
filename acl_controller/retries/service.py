"""Mechanical retry/continuation budget accounting."""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from acl_core.canonical import canonical_json
from acl_core.diagnostics import emit

from ..diagnostics import controller_span
from ..errors import ControllerError
from ..models import WorkflowStatus, utc_now
from ..state import WorkflowStateService


@dataclass(frozen=True)
class RetryBudget:
    max_retries: int = 0
    max_continuations: int = 0

    def __post_init__(self) -> None:
        for value, label in (
            (self.max_retries, "max_retries"),
            (self.max_continuations, "max_continuations"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ControllerError("CONTROLLER_RETRY_BUDGET_INVALID", f"{label} must be a nonnegative integer")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "RetryBudget":
        value = value or {}
        if not isinstance(value, Mapping):
            raise ControllerError("CONTROLLER_RETRY_BUDGET_INVALID", "retry budget must be a mapping")
        return cls(
            max_retries=value.get("max_retries", 0),
            max_continuations=value.get("max_continuations", 0),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "max_retries": self.max_retries,
            "max_continuations": self.max_continuations,
        }


@dataclass(frozen=True)
class RetryRecord:
    workflow_id: str
    budget: RetryBudget
    retries_used: int = 0
    continuations_used: int = 0
    updated_at: str = ""

    @classmethod
    def create(cls, workflow_id: str, budget: RetryBudget) -> "RetryRecord":
        return cls(workflow_id, budget, 0, 0, utc_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "budget": self.budget.to_dict(),
            "retries_used": self.retries_used,
            "continuations_used": self.continuations_used,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RetryRecord":
        try:
            retries = int(value["retries_used"])
            continuations = int(value["continuations_used"])
            if retries < 0 or continuations < 0:
                raise ValueError("negative counters")
            return cls(
                workflow_id=value["workflow_id"],
                budget=RetryBudget.from_mapping(value["budget"]),
                retries_used=retries,
                continuations_used=continuations,
                updated_at=value["updated_at"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError("CONTROLLER_RETRY_STATE_INVALID", "retry record is malformed") from exc


class JsonRetryStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def create_or_read(self, workflow_id: str, budget: RetryBudget) -> RetryRecord:
        with controller_span("retry_store.create_or_read", workflow_id=workflow_id):
            path = self._path(workflow_id)
            with self._lock:
                if path.exists():
                    current = self.read(workflow_id)
                    if current.budget != budget:
                        raise ControllerError(
                            "CONTROLLER_RETRY_BUDGET_CHANGED",
                            "retry budget cannot change after accounting begins",
                            {
                                "workflow_id": workflow_id,
                                "existing": current.budget.to_dict(),
                                "requested": budget.to_dict(),
                            },
                        )
                    return current
                record = RetryRecord.create(workflow_id, budget)
                self._write(path, record)
                return record

    def read(self, workflow_id: str) -> RetryRecord:
        with controller_span("retry_store.read", workflow_id=workflow_id):
            path = self._path(workflow_id)
            try:
                return RetryRecord.from_mapping(json.loads(path.read_text(encoding="utf-8")))
            except FileNotFoundError as exc:
                raise ControllerError("CONTROLLER_RETRY_STATE_MISSING", "retry state does not exist", {"workflow_id": workflow_id}) from exc
            except (OSError, json.JSONDecodeError) as exc:
                raise ControllerError("CONTROLLER_RETRY_STATE_READ_FAILED", "retry state could not be read", {"workflow_id": workflow_id}) from exc

    def save(self, record: RetryRecord) -> RetryRecord:
        with controller_span("retry_store.save", workflow_id=record.workflow_id):
            path = self._path(record.workflow_id)
            with self._lock:
                self._write(path, record)
            return record

    def _path(self, workflow_id: str) -> Path:
        if not isinstance(workflow_id, str) or not workflow_id.startswith("workflow:"):
            raise ControllerError("CONTROLLER_RETRY_STATE_INVALID", "workflow ID is invalid")
        return self.root / "retries" / f"{workflow_id.replace(':', '_')}.json"

    @staticmethod
    def _write(path: Path, record: RetryRecord) -> None:
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
            raise ControllerError("CONTROLLER_RETRY_STATE_WRITE_FAILED", "retry state could not be persisted") from exc


class RetryService:
    component = "controller.retries"

    def __init__(self, state: WorkflowStateService, store: JsonRetryStore) -> None:
        self.state = state
        self.store = store

    def configure(self, workflow_id: str, budget: RetryBudget) -> RetryRecord:
        with controller_span("retries.configure", workflow_id=workflow_id, **budget.to_dict()):
            self.state.read(workflow_id)
            record = self.store.create_or_read(workflow_id, budget)
            emit(
                "INFO",
                self.component,
                "configure",
                "retry_budget_bound",
                workflow_id=workflow_id,
                budget=budget.to_dict(),
                retries_used=record.retries_used,
                continuations_used=record.continuations_used,
            )
            return record

    def request_retry(
        self,
        workflow_id: str,
        *,
        budget: RetryBudget,
        requested_by: str,
        reason: str | None = None,
    ) -> RetryRecord:
        return self._consume(
            workflow_id,
            budget=budget,
            kind="retry",
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
        return self._consume(
            workflow_id,
            budget=budget,
            kind="continuation",
            requested_by=requested_by,
            reason=reason,
        )

    def _consume(
        self,
        workflow_id: str,
        *,
        budget: RetryBudget,
        kind: str,
        requested_by: str,
        reason: str | None,
    ) -> RetryRecord:
        with controller_span(
            f"retries.request_{kind}",
            workflow_id=workflow_id,
            requested_by=requested_by,
            reason=reason,
            **budget.to_dict(),
        ):
            if not isinstance(requested_by, str) or not requested_by.strip():
                raise ControllerError("CONTROLLER_RETRY_REQUEST_INVALID", "requested_by is required")
            current = self.store.create_or_read(workflow_id, budget)
            if kind == "retry":
                used = current.retries_used
                limit = current.budget.max_retries
            else:
                used = current.continuations_used
                limit = current.budget.max_continuations

            if used >= limit:
                self.state.transition(
                    workflow_id,
                    WorkflowStatus.BLOCKED,
                    blocker={
                        "code": "RETRY_BUDGET_EXHAUSTED" if kind == "retry" else "CONTINUATION_BUDGET_EXHAUSTED",
                        "kind": kind,
                        "requested_by": requested_by,
                        "reason": reason,
                        "used": used,
                        "limit": limit,
                    },
                )
                emit(
                    "INFO",
                    self.component,
                    f"request_{kind}",
                    "budget_exhausted",
                    workflow_id=workflow_id,
                    kind=kind,
                    requested_by=requested_by,
                    reason=reason,
                    used=used,
                    limit=limit,
                )
                raise ControllerError(
                    "CONTROLLER_RETRY_BUDGET_EXHAUSTED",
                    f"{kind} budget is exhausted",
                    {"workflow_id": workflow_id, "kind": kind, "used": used, "limit": limit},
                )

            if kind == "retry":
                updated = replace(current, retries_used=used + 1, updated_at=utc_now())
            else:
                updated = replace(current, continuations_used=used + 1, updated_at=utc_now())
            self.store.save(updated)
            self.state.transition(
                workflow_id,
                WorkflowStatus.READY,
                waiting_for=None,
                blocker=None,
            )
            emit(
                "INFO",
                self.component,
                f"request_{kind}",
                "budget_consumed",
                workflow_id=workflow_id,
                kind=kind,
                requested_by=requested_by,
                reason=reason,
                previous=used,
                current=used + 1,
                limit=limit,
            )
            return updated

    def read(self, workflow_id: str) -> RetryRecord:
        return self.store.read(workflow_id)
