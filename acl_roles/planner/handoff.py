"""Minimal model-facing Planner execution handoff parser.

This module intentionally does not construct ACL ExecutionPlan objects. It parses
only the ordered semantic handoff defined by docs/planner-handoff-v1.md so a later
compiler can translate it into existing Controller structures deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from acl_roles.common.errors import RoleContractError


PLANNER_HANDOFF_STATUS_READY = "READY"

_TASK_HEADING = re.compile(r"^T(?P<number>\d+):[ \t]*(?P<name>.*)$")


@dataclass(frozen=True)
class PlannerHandoffTask:
    """One ordered, self-contained Worker prompt authored by Planner."""

    task_id: str
    prompt: str

    def to_dict(self) -> dict[str, str]:
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
        }


@dataclass(frozen=True)
class PlannerExecutionHandoff:
    """Parsed READY handoff without Controller bookkeeping."""

    objective: str
    tasks: tuple[PlannerHandoffTask, ...]
    constraints: str | None = None
    status: str = PLANNER_HANDOFF_STATUS_READY

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "objective": self.objective,
            "constraints": self.constraints,
            "tasks": [task.to_dict() for task in self.tasks],
        }


def _fail(message: str, **details: Any) -> None:
    raise RoleContractError(
        "PLANNER_HANDOFF_INVALID",
        message,
        details or None,
    )


def _trim_block(lines: list[str]) -> str:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return "\n".join(lines[start:end])


def _next_nonblank(lines: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        if lines[index].strip():
            return index
    return None


def _parse_task_heading(line: str) -> tuple[str, str] | None:
    match = _TASK_HEADING.fullmatch(line)
    if match is None:
        return None

    number_text = match.group("number")
    number = int(number_text)
    canonical = f"T{number:02d}"
    if number < 1 or f"{number:02d}" != number_text:
        _fail(
            "Task headings must use canonical zero-padded numbering",
            observed=f"T{number_text}",
            expected=canonical,
        )

    inline = match.group("inline").strip()
    return canonical, inline


def parse_planner_execution_handoff(text: str) -> PlannerExecutionHandoff:
    """Parse one Planner Handoff V1 READY response.

    Meaning-bearing text is preserved except for outer blank lines around section
    bodies and task prompts. END_PLAN is preferred but EOF is a valid final Task
    terminator.
    """
    if not isinstance(text, str) or not text.strip():
        _fail("Planner handoff must be nonblank text")

    lines = text.splitlines()
    first = _next_nonblank(lines, 0)
    if first is None or lines[first].strip() != "STATUS: READY":
        _fail(
            "First nonblank line must be STATUS: READY",
            observed=None if first is None else lines[first].strip(),
        )

    objective_header = _next_nonblank(lines, first + 1)
    if (
        objective_header is None
        or lines[objective_header].strip() != "OBJECTIVE:"
    ):
        _fail("STATUS: READY must be followed by an OBJECTIVE section")

    objective_lines: list[str] = []
    constraint_lines: list[str] = []
    constraints_seen = False
    tasks: list[PlannerHandoffTask] = []
    current_task_id: str | None = None
    current_task_lines: list[str] = []

    def finish_task() -> None:
        nonlocal current_task_id, current_task_lines
        if current_task_id is None:
            return
        prompt = _trim_block(current_task_lines)
        if not prompt:
            _fail(
                "Task requires a nonblank Worker prompt",
                task_id=current_task_id,
            )
        tasks.append(
            PlannerHandoffTask(
                task_id=current_task_id,
                prompt=prompt,
            )
        )
        current_task_id = None
        current_task_lines = []

    ended = False
    for line_number, line in enumerate(
        lines[objective_header + 1 :],
        start=objective_header + 2,
    ):
        stripped = line.strip()

        if current_task_id is not None:
            if stripped == "END_PLAN":
                finish_task()
                ended = True
                break

            heading = _parse_task_heading(line)
            if heading is not None:
                finish_task()
                expected_number = len(tasks) + 1
                expected_id = f"T{expected_number:02d}"
                if heading[0] != expected_id:
                    _fail(
                        "Task headings must be sequential beginning with T01",
                        line=line_number,
                        observed=heading[0],
                        expected=expected_id,
                    )
                current_task_id = heading[0]
                current_task_lines = [heading[1]] if heading[1] else []
                continue

            current_task_lines.append(line)
            continue

        if stripped == "END_PLAN":
            _fail("END_PLAN appeared before any Task", line=line_number)

        heading = _parse_task_heading(line)
        if heading is not None:
            objective = _trim_block(objective_lines)
            if not objective:
                _fail("OBJECTIVE requires nonblank content")

            expected_id = "T01"
            if heading[0] != expected_id:
                _fail(
                    "Task headings must be sequential beginning with T01",
                    line=line_number,
                    observed=heading[0],
                    expected=expected_id,
                )
            current_task_id = heading[0]
            current_task_lines = [heading[1]] if heading[1] else []
            continue

        if stripped == "CONSTRAINTS:":
            if constraints_seen:
                _fail("CONSTRAINTS section may appear only once", line=line_number)
            if not _trim_block(objective_lines):
                _fail("OBJECTIVE requires nonblank content")
            constraints_seen = True
            continue

        if constraints_seen:
            constraint_lines.append(line)
        else:
            objective_lines.append(line)

    if not ended:
        finish_task()

    objective = _trim_block(objective_lines)
    if not objective:
        _fail("OBJECTIVE requires nonblank content")
    if not tasks:
        _fail("STATUS: READY handoff requires at least one Task")

    constraints = _trim_block(constraint_lines) if constraints_seen else None
    if constraints == "":
        constraints = None

    return PlannerExecutionHandoff(
        objective=objective,
        constraints=constraints,
        tasks=tuple(tasks),
    )
