"""Persistence for workflow programs and exact step results."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from acl_core import CoreIdentity
from acl_core.canonical import canonical_digest, canonical_json

from ..diagnostics import controller_span
from ..errors import ControllerError
from ..models import utc_now
from .models import WorkflowProgram


@dataclass(frozen=True)
class StepResultRecord:
    result_id: str
    workflow_id: str
    program_id: str
    step_id: str
    executor: str
    execution_id: str
    status: str
    payload: Mapping[str, Any]
    reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        workflow_id: str,
        program_id: str,
        step_id: str,
        executor: str,
        execution_id: str,
        status: str,
        payload: Mapping[str, Any],
        reference: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "StepResultRecord":
        if not isinstance(payload, Mapping):
            raise ControllerError("CONTROLLER_RESULT_INVALID", "step result payload must be a mapping")
        return cls(
            result_id=CoreIdentity.new("result").value,
            workflow_id=workflow_id,
            program_id=program_id,
            step_id=step_id,
            executor=executor,
            execution_id=execution_id,
            status=status,
            payload=dict(payload),
            reference=reference,
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "acl-controller-step-result:v1",
            "result_id": self.result_id,
            "workflow_id": self.workflow_id,
            "program_id": self.program_id,
            "step_id": self.step_id,
            "executor": self.executor,
            "execution_id": self.execution_id,
            "status": self.status,
            "payload": dict(self.payload),
            "reference": self.reference,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "StepResultRecord":
        if not isinstance(value, Mapping) or value.get("schema_version") != "acl-controller-step-result:v1":
            raise ControllerError("CONTROLLER_RESULT_INVALID", "step result schema is invalid")
        try:
            return cls(
                result_id=value["result_id"],
                workflow_id=value["workflow_id"],
                program_id=value["program_id"],
                step_id=value["step_id"],
                executor=value["executor"],
                execution_id=value["execution_id"],
                status=value["status"],
                payload=dict(value["payload"]),
                reference=value.get("reference"),
                metadata=dict(value.get("metadata", {})),
                created_at=value["created_at"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError("CONTROLLER_RESULT_INVALID", "step result is malformed") from exc


class JsonProgramStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def save(self, program: WorkflowProgram) -> WorkflowProgram:
        with controller_span("program_store.save", program_id=program.program_id):
            path = self._path(program.program_id)
            with self._lock:
                if path.exists():
                    existing = self.read(program.program_id)
                    if canonical_digest(existing.to_dict()) != canonical_digest(program.to_dict()):
                        raise ControllerError("CONTROLLER_PROGRAM_CONFLICT", "program ID already exists with different content")
                    return existing
                self._write(path, program.to_dict())
            return program

    def read(self, program_id: str) -> WorkflowProgram:
        with controller_span("program_store.read", program_id=program_id):
            try:
                return WorkflowProgram.from_mapping(json.loads(self._path(program_id).read_text(encoding="utf-8")))
            except FileNotFoundError as exc:
                raise ControllerError("CONTROLLER_PROGRAM_MISSING", "workflow program does not exist", {"program_id": program_id}) from exc
            except (OSError, json.JSONDecodeError) as exc:
                raise ControllerError("CONTROLLER_PROGRAM_READ_FAILED", "workflow program could not be read", {"program_id": program_id}) from exc

    def _path(self, program_id: str) -> Path:
        if not isinstance(program_id, str) or not program_id.startswith("program:"):
            raise ControllerError("CONTROLLER_PROGRAM_INVALID", "program ID is invalid")
        return self.root / "programs" / f"{program_id.replace(':', '_')}.json"

    @staticmethod
    def _write(path: Path, value: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        try:
            temp.write_text(canonical_json(value) + "\n", encoding="utf-8")
            os.replace(temp, path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ControllerError("CONTROLLER_PROGRAM_WRITE_FAILED", "workflow program could not be persisted") from exc


class JsonResultStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def save(self, result: StepResultRecord) -> StepResultRecord:
        with controller_span(
            "result_store.save",
            workflow_id=result.workflow_id,
            result_id=result.result_id,
            step_id=result.step_id,
            execution_id=result.execution_id,
            result_status=result.status,
        ):
            path = self._path(result.result_id)
            with self._lock:
                if path.exists():
                    existing = self.read(result.result_id)
                    if existing.digest() != result.digest():
                        raise ControllerError("CONTROLLER_RESULT_CONFLICT", "result ID already exists with different content")
                    return existing
                JsonProgramStore._write(path, result.to_dict())
            return result

    def read(self, result_id: str) -> StepResultRecord:
        with controller_span("result_store.read", result_id=result_id):
            try:
                return StepResultRecord.from_mapping(json.loads(self._path(result_id).read_text(encoding="utf-8")))
            except FileNotFoundError as exc:
                raise ControllerError("CONTROLLER_RESULT_MISSING", "step result does not exist", {"result_id": result_id}) from exc
            except (OSError, json.JSONDecodeError) as exc:
                raise ControllerError("CONTROLLER_RESULT_READ_FAILED", "step result could not be read", {"result_id": result_id}) from exc

    def for_workflow(self, workflow_id: str) -> tuple[StepResultRecord, ...]:
        directory = self.root / "results"
        if not directory.exists():
            return ()
        records = []
        for path in sorted(directory.glob("result_*.json")):
            try:
                record = StepResultRecord.from_mapping(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, ControllerError) as exc:
                raise ControllerError(
                    "CONTROLLER_RESULT_READ_FAILED",
                    "one or more persisted results are unreadable",
                    {"path": str(path)},
                ) from exc
            if record.workflow_id == workflow_id:
                records.append(record)
        return tuple(records)

    def latest_for_step(self, workflow_id: str, step_id: str) -> StepResultRecord | None:
        matches = [item for item in self.for_workflow(workflow_id) if item.step_id == step_id]
        return matches[-1] if matches else None

    def _path(self, result_id: str) -> Path:
        if not isinstance(result_id, str) or not result_id.startswith("result:"):
            raise ControllerError("CONTROLLER_RESULT_INVALID", "result ID is invalid")
        return self.root / "results" / f"{result_id.replace(':', '_')}.json"
