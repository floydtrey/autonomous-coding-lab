"""Mechanical workflow-program contracts.

A workflow program is a Controller recipe, not a work plan. It names ordered
execution steps and exact next-step links. It contains no natural-language
classification logic and no task/resource authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from acl_core import CoreIdentity

from ..errors import ControllerError


class StepExecutor(StrEnum):
    ROLE = "ROLE"
    ACTION = "ACTION"
    GATE = "GATE"


@dataclass(frozen=True)
class WorkflowStep:
    step_id: str
    executor: StepExecutor
    next_step: str | None = None
    role: str | None = None
    work_type: str | None = None
    complexity: str | None = None
    action_type: str | None = None
    gate_type: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    retry_budget: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _text(self.step_id, "step_id")
        if self.next_step is not None:
            _text(self.next_step, "next_step")
        if not isinstance(self.payload, Mapping) or not isinstance(self.retry_budget, Mapping):
            raise ControllerError("CONTROLLER_PROGRAM_INVALID", "step payload and retry budget must be mappings")
        if self.executor is StepExecutor.ROLE:
            _text(self.role, "role")
            _text(self.work_type, "work_type")
            if self.action_type is not None or self.gate_type is not None:
                raise ControllerError("CONTROLLER_PROGRAM_INVALID", "role step has incompatible fields")
        elif self.executor is StepExecutor.ACTION:
            _text(self.action_type, "action_type")
            if self.role is not None or self.work_type is not None or self.complexity is not None or self.gate_type is not None:
                raise ControllerError("CONTROLLER_PROGRAM_INVALID", "action step has incompatible fields")
        elif self.executor is StepExecutor.GATE:
            _text(self.gate_type, "gate_type")
            if self.role is not None or self.work_type is not None or self.complexity is not None or self.action_type is not None:
                raise ControllerError("CONTROLLER_PROGRAM_INVALID", "gate step has incompatible fields")
        else:
            raise ControllerError("CONTROLLER_PROGRAM_INVALID", "unsupported step executor")

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "executor": str(self.executor),
            "next_step": self.next_step,
            "role": self.role,
            "work_type": self.work_type,
            "complexity": self.complexity,
            "action_type": self.action_type,
            "gate_type": self.gate_type,
            "payload": dict(self.payload),
            "retry_budget": dict(self.retry_budget),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkflowStep":
        if not isinstance(value, Mapping):
            raise ControllerError("CONTROLLER_PROGRAM_INVALID", "workflow step must be a mapping")
        try:
            return cls(
                step_id=value["step_id"],
                executor=StepExecutor(value["executor"]),
                next_step=value.get("next_step"),
                role=value.get("role"),
                work_type=value.get("work_type"),
                complexity=value.get("complexity"),
                action_type=value.get("action_type"),
                gate_type=value.get("gate_type"),
                payload=dict(value.get("payload", {})),
                retry_budget=dict(value.get("retry_budget", {})),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError("CONTROLLER_PROGRAM_INVALID", "workflow step is malformed") from exc


@dataclass(frozen=True)
class WorkflowProgram:
    program_id: str
    start_step: str
    steps: tuple[WorkflowStep, ...]
    description: str | None = None

    @classmethod
    def create(
        cls,
        *,
        start_step: str,
        steps: tuple[WorkflowStep, ...],
        description: str | None = None,
    ) -> "WorkflowProgram":
        return cls(
            program_id=CoreIdentity.new("program").value,
            start_step=start_step,
            steps=steps,
            description=description,
        )

    def __post_init__(self) -> None:
        _text(self.program_id, "program_id")
        _text(self.start_step, "start_step")
        if not self.steps:
            raise ControllerError("CONTROLLER_PROGRAM_INVALID", "workflow program needs at least one step")
        ids = tuple(step.step_id for step in self.steps)
        if len(ids) != len(set(ids)):
            raise ControllerError("CONTROLLER_PROGRAM_INVALID", "workflow program contains duplicate step IDs")
        known = set(ids)
        if self.start_step not in known:
            raise ControllerError("CONTROLLER_PROGRAM_INVALID", "start step is missing")
        missing = sorted(
            {step.next_step for step in self.steps if step.next_step is not None} - known
        )
        if missing:
            raise ControllerError(
                "CONTROLLER_PROGRAM_INVALID",
                "workflow program references missing next steps",
                {"missing": missing},
            )
        if self.description is not None and not isinstance(self.description, str):
            raise ControllerError("CONTROLLER_PROGRAM_INVALID", "program description must be text when present")

    def step(self, step_id: str) -> WorkflowStep:
        for step in self.steps:
            if step.step_id == step_id:
                return step
        raise ControllerError(
            "CONTROLLER_PROGRAM_STEP_MISSING",
            "workflow step is not present in the bound program",
            {"program_id": self.program_id, "step_id": step_id},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "acl-controller-workflow-program:v1",
            "program_id": self.program_id,
            "start_step": self.start_step,
            "steps": [step.to_dict() for step in self.steps],
            "description": self.description,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkflowProgram":
        if not isinstance(value, Mapping) or value.get("schema_version") != "acl-controller-workflow-program:v1":
            raise ControllerError("CONTROLLER_PROGRAM_INVALID", "workflow program schema is invalid")
        try:
            steps = tuple(WorkflowStep.from_mapping(item) for item in value["steps"])
            return cls(
                program_id=value["program_id"],
                start_step=value["start_step"],
                steps=steps,
                description=value.get("description"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError("CONTROLLER_PROGRAM_INVALID", "workflow program is malformed") from exc


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ControllerError("CONTROLLER_PROGRAM_INVALID", f"{label} must be trimmed nonblank text")
    return value
