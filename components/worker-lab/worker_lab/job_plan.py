"""Immutable job plans with explicit V1 output obligations (plan schema V2)."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .output_acceptance import OutputAcceptance

PLAN_SCHEMA = "worker-lab-job-plan:v2"
ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def invalid(message: str, code: str = "JOB_PLAN_INVALID"):
    raise LabValidationError(code, message)


def obj(value: Any, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        invalid(f"{label} requires exactly: {', '.join(sorted(fields))}")
    return value


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        invalid(f"{label} must be nonblank, trimmed text")
    return value


def identity(value: Any, label: str) -> str:
    value = text(value, label)
    if not ID.fullmatch(value):
        invalid(f"{label} must be an identifier, not a path")
    return value


def positive(value: Any, label: str) -> int:
    if type(value) is not int or value < 1:
        invalid(f"{label} must be a positive integer")
    return value


def items(value: Any, label: str, *, nonempty: bool = True) -> list:
    if not isinstance(value, list) or (nonempty and not value):
        invalid(f"{label} must be {'a nonempty' if nonempty else 'an'} array")
    return value


def unique(values: tuple, label: str) -> tuple:
    if len(values) != len(set(values)):
        invalid(f"{label} contains duplicate IDs", "JOB_PLAN_DUPLICATE_ID")
    return values


@dataclass(frozen=True)
class AuthorityRef:
    profile_id: str
    version: int
    digest: str

    @classmethod
    def from_mapping(cls, value):
        d = obj(value, {"profile_id", "version", "digest"}, "authority_ref")
        digest = text(d["digest"], "authority digest")
        if not DIGEST.fullmatch(digest):
            invalid("authority_ref.digest must be a SHA-256 digest")
        return cls(identity(d["profile_id"], "profile_id"), positive(d["version"], "profile version"), digest)


@dataclass(frozen=True)
class Criterion:
    criterion_id: str
    description: str
    test_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value):
        d = obj(value, {"criterion_id", "description", "test_ids"}, "criterion")
        tests = tuple(text(v, "test ID") for v in items(d["test_ids"], "test_ids"))
        if any(not re.fullmatch(r"T[0-9]{3}", v) for v in tests):
            invalid("criterion test_ids must name protected catalog tests (Tnnn)")
        return cls(identity(d["criterion_id"], "criterion_id"), text(d["description"], "criterion description"),
                   tuple(sorted(unique(tests, "criterion test_ids"))))


@dataclass(frozen=True)
class Budget:
    max_attempts: int
    max_wall_seconds: int

    @classmethod
    def from_mapping(cls, value):
        d = obj(value, {"max_attempts", "max_wall_seconds"}, "budget")
        return cls(positive(d["max_attempts"], "max_attempts"), positive(d["max_wall_seconds"], "max_wall_seconds"))


@dataclass(frozen=True)
class JobTask:
    task_id: str
    description: str
    dependencies: tuple[str, ...]
    acceptance_criteria: tuple[Criterion, ...]
    authority_ref: AuthorityRef
    required_outputs: OutputAcceptance
    budget: Budget

    @classmethod
    def from_mapping(cls, value):
        d = obj(value, set(cls.__dataclass_fields__), "task")
        criteria = tuple(Criterion.from_mapping(v) for v in items(d["acceptance_criteria"], "acceptance_criteria"))
        unique(tuple(c.criterion_id for c in criteria), "criterion IDs")
        dependencies = tuple(identity(v, "dependency") for v in items(d["dependencies"], "dependencies", nonempty=False))
        outputs = OutputAcceptance.from_mapping(d["required_outputs"])
        return cls(identity(d["task_id"], "task_id"), text(d["description"], "task description"),
                   tuple(sorted(unique(dependencies, "dependencies"))),
                   tuple(sorted(criteria, key=lambda c: c.criterion_id)), AuthorityRef.from_mapping(d["authority_ref"]),
                   outputs, Budget.from_mapping(d["budget"]))


@dataclass(frozen=True)
class Objective:
    objective_id: str
    text: str
    target_id: str

    @classmethod
    def from_mapping(cls, value):
        d = obj(value, set(cls.__dataclass_fields__), "objective")
        target = text(d["target_id"], "target_id")
        if not re.fullmatch(r"target:[A-Za-z0-9][A-Za-z0-9._-]{0,95}", target):
            invalid("target_id must be a logical target:<id>, not a repository locator")
        return cls(identity(d["objective_id"], "objective_id"), text(d["text"], "objective text"), target)


@dataclass(frozen=True)
class JobPlan:
    schema_version: str
    plan_id: str
    revision: int
    objective: Objective
    tasks: tuple[JobTask, ...]

    @classmethod
    def from_mapping(cls, value):
        d = obj(value, set(cls.__dataclass_fields__), "job plan")
        if d["schema_version"] != PLAN_SCHEMA:
            invalid("unsupported job plan schema")
        tasks = tuple(JobTask.from_mapping(v) for v in items(d["tasks"], "tasks"))
        ids = unique(tuple(t.task_id for t in tasks), "task IDs")
        for task in tasks:
            missing = sorted(set(task.dependencies) - set(ids))
            if missing:
                invalid(f"Task {task.task_id} references missing dependencies: {', '.join(missing)}",
                        "JOB_PLAN_DEPENDENCY_MISSING")
        validate_dependencies(tasks)
        return cls(PLAN_SCHEMA, identity(d["plan_id"], "plan_id"), positive(d["revision"], "revision"),
                   Objective.from_mapping(d["objective"]), tuple(sorted(tasks, key=lambda t: t.task_id)))

    def to_dict(self):
        return json.loads(canonical_json(asdict(self)))

    def to_json(self):
        return canonical_json(self.to_dict())

    def digest(self):
        return canonical_digest(self.to_dict())

    def task(self, task_id: str) -> JobTask:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        invalid(f"Unknown task: {task_id}", "JOB_TASK_MISSING")


def validate_dependencies(tasks: tuple[JobTask, ...]) -> None:
    """Iterative DFS, stable across input ordering; produces no execution schedule."""
    graph = {task.task_id: tuple(sorted(task.dependencies)) for task in tasks}
    done: set[str] = set()
    for root in sorted(graph):
        if root in done:
            continue
        path = [root]
        active = {root: 0}
        stack = [iter(graph[root])]
        while stack:
            dependency = next(stack[-1], None)
            if dependency is None:
                done.add(path.pop())
                active = {node: index for index, node in enumerate(path)}
                stack.pop()
            elif dependency in active:
                cycle = path[active[dependency]:] + [dependency]
                invalid("Dependency cycle (task depends on next): " + " -> ".join(cycle),
                        "JOB_PLAN_DEPENDENCY_CYCLE")
            elif dependency not in done:
                active[dependency] = len(path)
                path.append(dependency)
                stack.append(iter(graph[dependency]))
