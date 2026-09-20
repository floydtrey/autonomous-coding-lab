"""Planner-specific semantic input and output contracts.

Planner describes intent, decomposition, resources, and requested filesystem work.
ACL owns canonical execution identity, authority grants, runtime/model selection,
budgets, review policy, persistence, and telemetry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Sequence

from acl_core.canonical import canonical_digest

from acl_roles.common.errors import RoleContractError


PLANNER_INPUT_SCHEMA = "acl-planner-input:v1"
PLANNER_RESULT_SCHEMA = "acl-planner-result:v1"

DEFAULT_CONTINUATION_INSTRUCTIONS = (
    "Resume from the first incomplete Task using persisted Pass state and evidence."
)


class PlannerInvocationMode(StrEnum):
    INITIAL_PLANNING = "INITIAL_PLANNING"
    WORKER_CONSULTATION = "WORKER_CONSULTATION"


class PlannerDisposition(StrEnum):
    DIRECT_RESPONSE = "DIRECT_RESPONSE"
    QUERY_RESPONSE = "QUERY_RESPONSE"
    EXECUTION_PLAN = "EXECUTION_PLAN"
    ELEVATION_REQUIRED = "ELEVATION_REQUIRED"
    CANNOT_PLAN = "CANNOT_PLAN"


class PlanType(StrEnum):
    SINGLE_PASS = "SINGLE_PASS"
    MULTI_PASS = "MULTI_PASS"
    STAGED = "STAGED"


@dataclass(frozen=True)
class PlannerCorrection:
    attempt: int
    error_code: str
    message: str
    instruction: str
    previous_response: Any
    details: Mapping[str, Any] = field(default_factory=dict)
    location: str | None = None
    previous_response_digest: str | None = None
    repeated_failure: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.attempt, bool) or not isinstance(self.attempt, int) or self.attempt < 1:
            raise RoleContractError(
                "PLANNER_CORRECTION_INVALID",
                "correction attempt must be a positive integer",
            )
        _text(self.error_code, "correction error_code")
        _text(self.message, "correction message")
        _text(self.instruction, "correction instruction")
        if not isinstance(self.details, Mapping):
            raise RoleContractError(
                "PLANNER_CORRECTION_INVALID",
                "correction details must be a mapping",
            )
        if self.location is not None:
            _text(self.location, "correction location")
        if self.previous_response_digest is not None:
            _text(self.previous_response_digest, "correction previous_response_digest")
        if not isinstance(self.repeated_failure, bool):
            raise RoleContractError(
                "PLANNER_CORRECTION_INVALID",
                "correction repeated_failure must be boolean",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "error_code": self.error_code,
            "message": self.message,
            "instruction": self.instruction,
            "previous_response": self.previous_response,
            "details": dict(self.details),
            "location": self.location,
            "previous_response_digest": self.previous_response_digest,
            "repeated_failure": self.repeated_failure,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerCorrection":
        value = _mapping(value, "planner correction")
        return cls(
            attempt=value.get("attempt"),
            error_code=value.get("error_code"),
            message=value.get("message"),
            instruction=value.get("instruction"),
            previous_response=value.get("previous_response"),
            details=_mapping(value.get("details"), "correction details"),
            location=value.get("location"),
            previous_response_digest=value.get("previous_response_digest"),
            repeated_failure=value.get("repeated_failure", False),
        )


def _text(value: Any, label: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise RoleContractError(
            "PLANNER_CONTRACT_INVALID",
            f"{label} must be trimmed nonblank text",
        )
    return value


def _text_tuple(
    values: Sequence[str] | None,
    label: str,
    *,
    unique: bool = True,
) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise RoleContractError(
            "PLANNER_CONTRACT_INVALID",
            f"{label} must be a sequence of text values",
        )
    result = tuple(values)
    if any(not isinstance(item, str) or not item.strip() or item != item.strip() for item in result):
        raise RoleContractError(
            "PLANNER_CONTRACT_INVALID",
            f"{label} must contain trimmed nonblank text",
        )
    if unique and len(result) != len(set(result)):
        raise RoleContractError(
            "PLANNER_CONTRACT_INVALID",
            f"{label} must not contain duplicates",
        )
    return result


def _mapping(value: Mapping[str, Any] | None, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise RoleContractError(
            "PLANNER_CONTRACT_INVALID",
            f"{label} must be a mapping",
        )
    return dict(value)


@dataclass(frozen=True)
class ProjectReference:
    project_name: str | None = None
    version_id: str | None = None
    project_root: str | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.project_name, "project_name"),
            (self.version_id, "version_id"),
            (self.project_root, "project_root"),
        ):
            if value is not None:
                _text(value, label)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "version_id": self.version_id,
            "project_root": self.project_root,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "ProjectReference":
        value = _mapping(value, "project")
        return cls(
            project_name=value.get("project_name"),
            version_id=value.get("version_id"),
            project_root=value.get("project_root"),
        )


@dataclass(frozen=True)
class WorkspaceSpec:
    worker_working_directory: str | None = None
    output_directory: str | None = None
    artifact_directory: str | None = None
    temporary_directory: str | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.worker_working_directory, "worker_working_directory"),
            (self.output_directory, "output_directory"),
            (self.artifact_directory, "artifact_directory"),
            (self.temporary_directory, "temporary_directory"),
        ):
            if value is not None:
                _text(value, label)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_working_directory": self.worker_working_directory,
            "output_directory": self.output_directory,
            "artifact_directory": self.artifact_directory,
            "temporary_directory": self.temporary_directory,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "WorkspaceSpec":
        value = _mapping(value, "workspace")
        return cls(
            worker_working_directory=value.get("worker_working_directory"),
            output_directory=value.get("output_directory"),
            artifact_directory=value.get("artifact_directory"),
            temporary_directory=value.get("temporary_directory"),
        )


@dataclass(frozen=True)
class MoveIntent:
    source: str
    destination: str

    def __post_init__(self) -> None:
        _text(self.source, "move source")
        _text(self.destination, "move destination")

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source, "destination": self.destination}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "MoveIntent":
        value = _mapping(value, "move intent")
        return cls(source=value.get("source"), destination=value.get("destination"))


@dataclass(frozen=True)
class FilesystemIntent:
    read_paths: tuple[str, ...] = ()
    write_paths: tuple[str, ...] = ()
    create_paths: tuple[str, ...] = ()
    delete_paths: tuple[str, ...] = ()
    move_paths: tuple[MoveIntent, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "read_paths", _text_tuple(self.read_paths, "read_paths"))
        object.__setattr__(self, "write_paths", _text_tuple(self.write_paths, "write_paths"))
        object.__setattr__(self, "create_paths", _text_tuple(self.create_paths, "create_paths"))
        object.__setattr__(self, "delete_paths", _text_tuple(self.delete_paths, "delete_paths"))
        if not isinstance(self.move_paths, tuple) or any(
            not isinstance(item, MoveIntent) for item in self.move_paths
        ):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "move_paths must contain MoveIntent values",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "read_paths": list(self.read_paths),
            "write_paths": list(self.write_paths),
            "create_paths": list(self.create_paths),
            "delete_paths": list(self.delete_paths),
            "move_paths": [item.to_dict() for item in self.move_paths],
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "FilesystemIntent":
        value = _mapping(value, "filesystem")
        move_raw = value.get("move_paths", [])
        if not isinstance(move_raw, list):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "move_paths must be a list",
            )
        return cls(
            read_paths=_text_tuple(value.get("read_paths", []), "read_paths"),
            write_paths=_text_tuple(value.get("write_paths", []), "write_paths"),
            create_paths=_text_tuple(value.get("create_paths", []), "create_paths"),
            delete_paths=_text_tuple(value.get("delete_paths", []), "delete_paths"),
            move_paths=tuple(MoveIntent.from_mapping(item) for item in move_raw),
        )


@dataclass(frozen=True)
class ReferenceMaterial:
    reference_id: str
    kind: str
    reference: str
    purpose: str | None = None
    required: bool = True

    def __post_init__(self) -> None:
        _text(self.reference_id, "reference_id")
        _text(self.kind, "reference kind")
        _text(self.reference, "reference")
        if self.purpose is not None:
            _text(self.purpose, "reference purpose")
        if not isinstance(self.required, bool):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "reference required must be boolean",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "kind": self.kind,
            "reference": self.reference,
            "purpose": self.purpose,
            "required": self.required,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ReferenceMaterial":
        value = _mapping(value, "reference material")
        return cls(
            reference_id=value.get("reference_id"),
            kind=value.get("kind"),
            reference=value.get("reference"),
            purpose=value.get("purpose"),
            required=value.get("required", True),
        )


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    name: str
    instruction: str
    depends_on: tuple[str, ...] = ()
    filesystem: FilesystemIntent = field(default_factory=FilesystemIntent)
    reference_ids: tuple[str, ...] = ()
    expected_result: str | None = None
    acceptance_criteria: tuple[str, ...] = ()
    evidence_required: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.task_id, "task_id")
        _text(self.name, "task name")
        _text(self.instruction, "task instruction")
        object.__setattr__(self, "depends_on", _text_tuple(self.depends_on, "task depends_on"))
        object.__setattr__(self, "reference_ids", _text_tuple(self.reference_ids, "task reference_ids"))
        if self.expected_result is not None:
            _text(self.expected_result, "task expected_result")
        object.__setattr__(
            self,
            "acceptance_criteria",
            _text_tuple(self.acceptance_criteria, "task acceptance_criteria"),
        )
        object.__setattr__(
            self,
            "evidence_required",
            _text_tuple(self.evidence_required, "task evidence_required"),
        )
        if not isinstance(self.filesystem, FilesystemIntent):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "task filesystem must be FilesystemIntent",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "instruction": self.instruction,
            "depends_on": list(self.depends_on),
            "filesystem": self.filesystem.to_dict(),
            "reference_ids": list(self.reference_ids),
            "expected_result": self.expected_result,
            "acceptance_criteria": list(self.acceptance_criteria),
            "evidence_required": list(self.evidence_required),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TaskSpec":
        value = _mapping(value, "task")
        return cls(
            task_id=value.get("task_id"),
            name=value.get("name"),
            instruction=value.get("instruction"),
            depends_on=_text_tuple(value.get("depends_on", []), "task depends_on"),
            filesystem=FilesystemIntent.from_mapping(value.get("filesystem")),
            reference_ids=_text_tuple(value.get("reference_ids", []), "task reference_ids"),
            expected_result=value.get("expected_result"),
            acceptance_criteria=_text_tuple(
                value.get("acceptance_criteria", []),
                "task acceptance_criteria",
            ),
            evidence_required=_text_tuple(
                value.get("evidence_required", []),
                "task evidence_required",
            ),
        )


@dataclass(frozen=True)
class PassSpec:
    pass_id: str
    name: str
    objective: str
    complexity: str
    tasks: tuple[TaskSpec, ...]
    depends_on: tuple[str, ...] = ()
    working_directory: str | None = None
    output_directory: str | None = None
    reference_ids: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    evidence_required: tuple[str, ...] = ()
    tracking_requirements: tuple[str, ...] = ()
    continuation_instructions: str | None = None

    def __post_init__(self) -> None:
        _text(self.pass_id, "pass_id")
        _text(self.name, "pass name")
        _text(self.objective, "pass objective")
        _text(self.complexity, "pass complexity")
        if not isinstance(self.tasks, tuple) or not self.tasks or any(
            not isinstance(item, TaskSpec) for item in self.tasks
        ):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "pass must contain one or more TaskSpec values",
            )
        task_ids = tuple(item.task_id for item in self.tasks)
        if len(task_ids) != len(set(task_ids)):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "task_id values must be unique within a pass",
                {"pass_id": self.pass_id},
            )
        object.__setattr__(self, "depends_on", _text_tuple(self.depends_on, "pass depends_on"))
        object.__setattr__(self, "reference_ids", _text_tuple(self.reference_ids, "pass reference_ids"))
        object.__setattr__(self, "expected_outputs", _text_tuple(self.expected_outputs, "pass expected_outputs"))
        object.__setattr__(
            self,
            "acceptance_criteria",
            _text_tuple(self.acceptance_criteria, "pass acceptance_criteria"),
        )
        if not self.acceptance_criteria:
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "pass requires acceptance criteria",
                {"pass_id": self.pass_id},
            )
        object.__setattr__(
            self,
            "evidence_required",
            _text_tuple(self.evidence_required, "pass evidence_required"),
        )
        object.__setattr__(
            self,
            "tracking_requirements",
            _text_tuple(self.tracking_requirements, "pass tracking_requirements"),
        )
        for value, label in (
            (self.working_directory, "pass working_directory"),
            (self.output_directory, "pass output_directory"),
        ):
            if value is not None:
                _text(value, label)
        _text(self.continuation_instructions, "pass continuation_instructions")

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_id": self.pass_id,
            "name": self.name,
            "objective": self.objective,
            "complexity": self.complexity,
            "depends_on": list(self.depends_on),
            "working_directory": self.working_directory,
            "output_directory": self.output_directory,
            "reference_ids": list(self.reference_ids),
            "expected_outputs": list(self.expected_outputs),
            "acceptance_criteria": list(self.acceptance_criteria),
            "evidence_required": list(self.evidence_required),
            "tracking_requirements": list(self.tracking_requirements),
            "continuation_instructions": self.continuation_instructions,
            "tasks": [item.to_dict() for item in self.tasks],
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PassSpec":
        value = _mapping(value, "pass")
        tasks = value.get("tasks", [])
        if not isinstance(tasks, list):
            raise RoleContractError("PLANNER_CONTRACT_INVALID", "pass tasks must be a list")
        return cls(
            pass_id=value.get("pass_id"),
            name=value.get("name"),
            objective=value.get("objective"),
            complexity=value.get("complexity"),
            depends_on=_text_tuple(value.get("depends_on", []), "pass depends_on"),
            working_directory=value.get("working_directory"),
            output_directory=value.get("output_directory"),
            reference_ids=_text_tuple(value.get("reference_ids", []), "pass reference_ids"),
            expected_outputs=_text_tuple(value.get("expected_outputs", []), "pass expected_outputs"),
            acceptance_criteria=_text_tuple(
                value.get("acceptance_criteria", []),
                "pass acceptance_criteria",
            ),
            evidence_required=_text_tuple(
                value.get("evidence_required", []),
                "pass evidence_required",
            ),
            tracking_requirements=_text_tuple(
                value.get("tracking_requirements", []),
                "pass tracking_requirements",
            ),
            continuation_instructions=value.get(
                "continuation_instructions",
                DEFAULT_CONTINUATION_INSTRUCTIONS,
            ),
            tasks=tuple(TaskSpec.from_mapping(item) for item in tasks),
        )


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    name: str
    objective: str
    passes: tuple[PassSpec, ...]
    depends_on: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.stage_id, "stage_id")
        _text(self.name, "stage name")
        _text(self.objective, "stage objective")
        if not isinstance(self.passes, tuple) or not self.passes or any(
            not isinstance(item, PassSpec) for item in self.passes
        ):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "stage must contain one or more PassSpec values",
            )
        object.__setattr__(self, "depends_on", _text_tuple(self.depends_on, "stage depends_on"))
        object.__setattr__(
            self,
            "acceptance_criteria",
            _text_tuple(self.acceptance_criteria, "stage acceptance_criteria"),
        )
        if not self.acceptance_criteria:
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "stage requires acceptance criteria",
                {"stage_id": self.stage_id},
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "name": self.name,
            "objective": self.objective,
            "depends_on": list(self.depends_on),
            "acceptance_criteria": list(self.acceptance_criteria),
            "passes": [item.to_dict() for item in self.passes],
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "StageSpec":
        value = _mapping(value, "stage")
        passes = value.get("passes", [])
        if not isinstance(passes, list):
            raise RoleContractError("PLANNER_CONTRACT_INVALID", "stage passes must be a list")
        return cls(
            stage_id=value.get("stage_id"),
            name=value.get("name"),
            objective=value.get("objective"),
            depends_on=_text_tuple(value.get("depends_on", []), "stage depends_on"),
            acceptance_criteria=_text_tuple(
                value.get("acceptance_criteria", []),
                "stage acceptance_criteria",
            ),
            passes=tuple(PassSpec.from_mapping(item) for item in passes),
        )


@dataclass(frozen=True)
class ExecutionPlan:
    plan_type: PlanType
    task_type: str
    complexity: str
    objective: str
    acceptance_criteria: tuple[str, ...]
    project: ProjectReference = field(default_factory=ProjectReference)
    work_type_id: str | None = None
    required_capabilities: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    required_services: tuple[str, ...] = ()
    research_requirements: tuple[str, ...] = ()
    required_outputs: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    out_of_scope: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    workspace: WorkspaceSpec = field(default_factory=WorkspaceSpec)
    reference_material: tuple[ReferenceMaterial, ...] = ()
    sources: tuple[str, ...] = ()
    tracking_requirements: tuple[str, ...] = ()
    decomposition_reason: str | None = None
    stages: tuple[StageSpec, ...] = ()
    passes: tuple[PassSpec, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.plan_type, PlanType):
            raise RoleContractError("PLANNER_CONTRACT_INVALID", "plan_type is invalid")
        _text(self.task_type, "task_type")
        _text(self.complexity, "plan complexity")
        _text(self.objective, "plan objective")
        if self.work_type_id is not None:
            _text(self.work_type_id, "work_type_id")
        object.__setattr__(
            self,
            "acceptance_criteria",
            _text_tuple(self.acceptance_criteria, "plan acceptance_criteria"),
        )
        if not self.acceptance_criteria:
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "execution plan requires acceptance criteria",
            )
        for attr, label in (
            ("required_capabilities", "required_capabilities"),
            ("required_tools", "required_tools"),
            ("required_services", "required_services"),
            ("research_requirements", "research_requirements"),
            ("required_outputs", "required_outputs"),
            ("constraints", "constraints"),
            ("out_of_scope", "out_of_scope"),
            ("assumptions", "assumptions"),
            ("unresolved_questions", "unresolved_questions"),
            ("sources", "sources"),
            ("tracking_requirements", "tracking_requirements"),
        ):
            object.__setattr__(self, attr, _text_tuple(getattr(self, attr), label))
        if self.decomposition_reason is not None:
            _text(self.decomposition_reason, "decomposition_reason")
        if not isinstance(self.project, ProjectReference):
            raise RoleContractError("PLANNER_CONTRACT_INVALID", "project is invalid")
        if not isinstance(self.workspace, WorkspaceSpec):
            raise RoleContractError("PLANNER_CONTRACT_INVALID", "workspace is invalid")
        _text(
            self.workspace.worker_working_directory,
            "workspace worker_working_directory",
        )
        _text(self.workspace.output_directory, "workspace output_directory")
        if not isinstance(self.reference_material, tuple) or any(
            not isinstance(item, ReferenceMaterial) for item in self.reference_material
        ):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "reference_material must contain ReferenceMaterial values",
            )
        reference_ids = tuple(item.reference_id for item in self.reference_material)
        if len(reference_ids) != len(set(reference_ids)):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "reference_id values must be unique within a plan",
            )
        if bool(self.stages) == bool(self.passes):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "execution plan must contain either top-level passes or stages, but not both",
            )
        if self.stages and self.plan_type is not PlanType.STAGED:
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "a plan containing stages must use STAGED plan_type",
            )
        if self.passes and self.plan_type is PlanType.STAGED:
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "STAGED plan_type must contain stages",
            )
        if self.plan_type is PlanType.SINGLE_PASS and len(self.passes) != 1:
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "SINGLE_PASS plan_type requires exactly one top-level pass",
            )
        if self.plan_type is PlanType.MULTI_PASS and len(self.passes) < 2:
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "MULTI_PASS plan_type requires at least two top-level passes",
            )
        if self.plan_type in {PlanType.MULTI_PASS, PlanType.STAGED} and self.decomposition_reason is None:
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "decomposed plans require decomposition_reason",
            )
        all_passes = list(self.passes)
        for stage in self.stages:
            all_passes.extend(stage.passes)
        pass_ids = tuple(item.pass_id for item in all_passes)
        if len(pass_ids) != len(set(pass_ids)):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "pass_id values must be unique within a plan",
            )
        stage_ids = tuple(item.stage_id for item in self.stages)
        if len(stage_ids) != len(set(stage_ids)):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "stage_id values must be unique within a plan",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_type": str(self.plan_type),
            "project": self.project.to_dict(),
            "work_type_id": self.work_type_id,
            "task_type": self.task_type,
            "complexity": self.complexity,
            "required_capabilities": list(self.required_capabilities),
            "required_tools": list(self.required_tools),
            "required_services": list(self.required_services),
            "research_requirements": list(self.research_requirements),
            "objective": self.objective,
            "acceptance_criteria": list(self.acceptance_criteria),
            "required_outputs": list(self.required_outputs),
            "constraints": list(self.constraints),
            "out_of_scope": list(self.out_of_scope),
            "assumptions": list(self.assumptions),
            "unresolved_questions": list(self.unresolved_questions),
            "workspace": self.workspace.to_dict(),
            "reference_material": [item.to_dict() for item in self.reference_material],
            "sources": list(self.sources),
            "tracking_requirements": list(self.tracking_requirements),
            "decomposition_reason": self.decomposition_reason,
            "stages": [item.to_dict() for item in self.stages],
            "passes": [item.to_dict() for item in self.passes],
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ExecutionPlan":
        value = _mapping(value, "execution plan")
        refs = value.get("reference_material", [])
        stages = value.get("stages", [])
        passes = value.get("passes", [])
        if not isinstance(refs, list) or not isinstance(stages, list) or not isinstance(passes, list):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "reference_material, stages, and passes must be lists",
            )
        raw_plan_type = value.get("plan_type")
        if raw_plan_type is None:
            if stages and not passes:
                plan_type = PlanType.STAGED
            elif passes and len(passes) == 1:
                plan_type = PlanType.SINGLE_PASS
            elif passes and len(passes) >= 2:
                plan_type = PlanType.MULTI_PASS
            else:
                raise RoleContractError(
                    "PLANNER_CONTRACT_INVALID",
                    "plan structure cannot determine plan_type",
                )
        else:
            try:
                plan_type = PlanType(raw_plan_type)
            except (TypeError, ValueError) as exc:
                raise RoleContractError("PLANNER_CONTRACT_INVALID", "plan_type is invalid") from exc
        return cls(
            plan_type=plan_type,
            project=ProjectReference.from_mapping(value.get("project")),
            work_type_id=value.get("work_type_id"),
            task_type=value.get("task_type"),
            complexity=value.get("complexity"),
            required_capabilities=_text_tuple(
                value.get("required_capabilities", []),
                "required_capabilities",
            ),
            required_tools=_text_tuple(value.get("required_tools", []), "required_tools"),
            required_services=_text_tuple(
                value.get("required_services", []),
                "required_services",
            ),
            research_requirements=_text_tuple(
                value.get("research_requirements", []),
                "research_requirements",
            ),
            objective=value.get("objective"),
            acceptance_criteria=_text_tuple(
                value.get("acceptance_criteria", []),
                "plan acceptance_criteria",
            ),
            required_outputs=_text_tuple(value.get("required_outputs", []), "required_outputs"),
            constraints=_text_tuple(value.get("constraints", []), "constraints"),
            out_of_scope=_text_tuple(value.get("out_of_scope", []), "out_of_scope"),
            assumptions=_text_tuple(value.get("assumptions", []), "assumptions"),
            unresolved_questions=_text_tuple(
                value.get("unresolved_questions", []),
                "unresolved_questions",
            ),
            workspace=WorkspaceSpec.from_mapping(value.get("workspace")),
            reference_material=tuple(ReferenceMaterial.from_mapping(item) for item in refs),
            sources=_text_tuple(value.get("sources", []), "sources"),
            tracking_requirements=_text_tuple(
                value.get("tracking_requirements", []),
                "tracking_requirements",
            ),
            decomposition_reason=value.get("decomposition_reason"),
            stages=tuple(StageSpec.from_mapping(item) for item in stages),
            passes=tuple(PassSpec.from_mapping(item) for item in passes),
        )


@dataclass(frozen=True)
class PlannerQuestion:
    question_id: str
    question: str
    reason: str
    options: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.question_id, "question_id")
        _text(self.question, "question")
        _text(self.reason, "question reason")
        object.__setattr__(self, "options", _text_tuple(self.options, "question options"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "reason": self.reason,
            "options": list(self.options),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerQuestion":
        value = _mapping(value, "planner question")
        return cls(
            question_id=value.get("question_id"),
            question=value.get("question"),
            reason=value.get("reason"),
            options=_text_tuple(value.get("options", []), "question options"),
        )


@dataclass(frozen=True)
class PlannerAnswer:
    answer: str
    sources: tuple[str, ...] = ()
    references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.answer, "planner answer")
        object.__setattr__(self, "sources", _text_tuple(self.sources, "answer sources"))
        object.__setattr__(self, "references", _text_tuple(self.references, "answer references"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": list(self.sources),
            "references": list(self.references),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerAnswer":
        value = _mapping(value, "planner answer")
        return cls(
            answer=value.get("answer"),
            sources=_text_tuple(value.get("sources", []), "answer sources"),
            references=_text_tuple(value.get("references", []), "answer references"),
        )


@dataclass(frozen=True)
class WorkerConsultation:
    plan_id: str
    pass_id: str
    question: str
    reason: str
    current_state_summary: str
    task_id: str | None = None
    relevant_reference_ids: tuple[str, ...] = ()
    relevant_evidence: tuple[str, ...] = ()
    prior_exchanges: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        _text(self.plan_id, "consultation plan_id")
        _text(self.pass_id, "consultation pass_id")
        _text(self.question, "consultation question")
        _text(self.reason, "consultation reason")
        _text(self.current_state_summary, "consultation current_state_summary")
        if self.task_id is not None:
            _text(self.task_id, "consultation task_id")
        object.__setattr__(
            self,
            "relevant_reference_ids",
            _text_tuple(self.relevant_reference_ids, "consultation relevant_reference_ids"),
        )
        object.__setattr__(
            self,
            "relevant_evidence",
            _text_tuple(self.relevant_evidence, "consultation relevant_evidence"),
        )
        if not isinstance(self.prior_exchanges, tuple) or any(
            not isinstance(item, Mapping) for item in self.prior_exchanges
        ):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "consultation prior_exchanges must contain mappings",
            )
        object.__setattr__(
            self,
            "prior_exchanges",
            tuple(dict(item) for item in self.prior_exchanges),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "pass_id": self.pass_id,
            "task_id": self.task_id,
            "question": self.question,
            "reason": self.reason,
            "current_state_summary": self.current_state_summary,
            "relevant_reference_ids": list(self.relevant_reference_ids),
            "relevant_evidence": list(self.relevant_evidence),
            "prior_exchanges": [dict(item) for item in self.prior_exchanges],
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkerConsultation":
        value = _mapping(value, "worker consultation")
        prior_raw = value.get("prior_exchanges", [])
        if not isinstance(prior_raw, list) or any(
            not isinstance(item, Mapping) for item in prior_raw
        ):
            raise RoleContractError(
                "PLANNER_CONTRACT_INVALID",
                "consultation prior_exchanges must be a list of mappings",
            )
        return cls(
            plan_id=value.get("plan_id"),
            pass_id=value.get("pass_id"),
            task_id=value.get("task_id"),
            question=value.get("question"),
            reason=value.get("reason"),
            current_state_summary=value.get("current_state_summary"),
            relevant_reference_ids=_text_tuple(
                value.get("relevant_reference_ids", []),
                "consultation relevant_reference_ids",
            ),
            relevant_evidence=_text_tuple(
                value.get("relevant_evidence", []),
                "consultation relevant_evidence",
            ),
            prior_exchanges=tuple(dict(item) for item in prior_raw),
        )


@dataclass(frozen=True)
class PlannerInput:
    invocation_mode: PlannerInvocationMode
    request: Mapping[str, Any]
    routing_context: Mapping[str, Any] = field(default_factory=dict)
    consultation: WorkerConsultation | None = None
    elevation_answers: Mapping[str, Any] = field(default_factory=dict)
    correction: PlannerCorrection | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.invocation_mode, PlannerInvocationMode):
            raise RoleContractError(
                "PLANNER_INPUT_INVALID",
                "invocation_mode is invalid",
            )
        if not isinstance(self.request, Mapping):
            raise RoleContractError("PLANNER_INPUT_INVALID", "request must be a mapping")
        if not isinstance(self.routing_context, Mapping):
            raise RoleContractError("PLANNER_INPUT_INVALID", "routing_context must be a mapping")
        if not isinstance(self.elevation_answers, Mapping):
            raise RoleContractError("PLANNER_INPUT_INVALID", "elevation_answers must be a mapping")
        if not isinstance(self.metadata, Mapping):
            raise RoleContractError("PLANNER_INPUT_INVALID", "metadata must be a mapping")
        if self.correction is not None and not isinstance(self.correction, PlannerCorrection):
            raise RoleContractError(
                "PLANNER_INPUT_INVALID",
                "correction must be PlannerCorrection when present",
            )
        if self.invocation_mode is PlannerInvocationMode.WORKER_CONSULTATION:
            if not isinstance(self.consultation, WorkerConsultation):
                raise RoleContractError(
                    "PLANNER_INPUT_INVALID",
                    "WORKER_CONSULTATION requires consultation details",
                )
        elif self.consultation is not None:
            raise RoleContractError(
                "PLANNER_INPUT_INVALID",
                "consultation details are only valid for WORKER_CONSULTATION",
            )
        for key in self.elevation_answers:
            _text(key, "elevation answer question_id")

    def to_objective(self) -> dict[str, Any]:
        return {
            "schema_version": PLANNER_INPUT_SCHEMA,
            "invocation_mode": str(self.invocation_mode),
            "request": dict(self.request),
            "routing_context": dict(self.routing_context),
            "consultation": None if self.consultation is None else self.consultation.to_dict(),
            "elevation_answers": dict(self.elevation_answers),
            "correction": None if self.correction is None else self.correction.to_dict(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerInput":
        value = _mapping(value, "planner input")
        if value.get("schema_version") != PLANNER_INPUT_SCHEMA:
            raise RoleContractError("PLANNER_INPUT_INVALID", "planner input schema is invalid")
        try:
            mode = PlannerInvocationMode(value.get("invocation_mode"))
        except (TypeError, ValueError) as exc:
            raise RoleContractError("PLANNER_INPUT_INVALID", "invocation_mode is invalid") from exc
        consultation_raw = value.get("consultation")
        correction_raw = value.get("correction")
        return cls(
            invocation_mode=mode,
            request=_mapping(value.get("request"), "request"),
            routing_context=_mapping(value.get("routing_context"), "routing_context"),
            consultation=(
                None
                if consultation_raw is None
                else WorkerConsultation.from_mapping(consultation_raw)
            ),
            elevation_answers=_mapping(value.get("elevation_answers"), "elevation_answers"),
            correction=(
                None
                if correction_raw is None
                else PlannerCorrection.from_mapping(correction_raw)
            ),
            metadata=_mapping(value.get("metadata"), "metadata"),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_objective())


@dataclass(frozen=True)
class PlannerResult:
    disposition: PlannerDisposition
    answer: PlannerAnswer | None = None
    plan: ExecutionPlan | None = None
    questions: tuple[PlannerQuestion, ...] = ()
    reason_codes: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, PlannerDisposition):
            raise RoleContractError("PLANNER_RESULT_INVALID", "disposition is invalid")
        object.__setattr__(
            self,
            "reason_codes",
            _text_tuple(self.reason_codes, "planner reason_codes"),
        )
        if self.notes is not None:
            _text(self.notes, "planner notes")
        if not isinstance(self.questions, tuple) or any(
            not isinstance(item, PlannerQuestion) for item in self.questions
        ):
            raise RoleContractError(
                "PLANNER_RESULT_INVALID",
                "questions must contain PlannerQuestion values",
            )
        question_ids = tuple(item.question_id for item in self.questions)
        if len(question_ids) != len(set(question_ids)):
            raise RoleContractError(
                "PLANNER_RESULT_INVALID",
                "question_id values must be unique within a Planner result",
            )

        if self.disposition in {
            PlannerDisposition.DIRECT_RESPONSE,
            PlannerDisposition.QUERY_RESPONSE,
        }:
            if not isinstance(self.answer, PlannerAnswer) or self.plan is not None or self.questions:
                raise RoleContractError(
                    "PLANNER_RESULT_INVALID",
                    "response disposition requires answer only",
                )
        elif self.disposition is PlannerDisposition.EXECUTION_PLAN:
            if not isinstance(self.plan, ExecutionPlan) or self.answer is not None or self.questions:
                raise RoleContractError(
                    "PLANNER_RESULT_INVALID",
                    "EXECUTION_PLAN requires plan only",
                )
        elif self.disposition is PlannerDisposition.ELEVATION_REQUIRED:
            if not self.questions or self.answer is not None or self.plan is not None:
                raise RoleContractError(
                    "PLANNER_RESULT_INVALID",
                    "ELEVATION_REQUIRED requires one or more questions only",
                )
        elif self.disposition is PlannerDisposition.CANNOT_PLAN:
            if self.answer is not None or self.plan is not None or self.questions:
                raise RoleContractError(
                    "PLANNER_RESULT_INVALID",
                    "CANNOT_PLAN must not contain answer, plan, or questions",
                )
            if not self.reason_codes and self.notes is None:
                raise RoleContractError(
                    "PLANNER_RESULT_INVALID",
                    "CANNOT_PLAN requires a reason code or note",
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PLANNER_RESULT_SCHEMA,
            "disposition": str(self.disposition),
            "answer": None if self.answer is None else self.answer.to_dict(),
            "plan": None if self.plan is None else self.plan.to_dict(),
            "questions": [item.to_dict() for item in self.questions],
            "reason_codes": list(self.reason_codes),
            "notes": self.notes,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerResult":
        value = _mapping(value, "planner result")
        if value.get("schema_version") != PLANNER_RESULT_SCHEMA:
            raise RoleContractError("PLANNER_RESULT_INVALID", "planner result schema is invalid")
        try:
            disposition = PlannerDisposition(value.get("disposition"))
        except (TypeError, ValueError) as exc:
            raise RoleContractError(
                "PLANNER_RESULT_INVALID",
                "planner result disposition is invalid",
            ) from exc

        answer_raw = value.get("answer")
        plan_raw = value.get("plan")
        questions_raw = value.get("questions", [])
        if not isinstance(questions_raw, list):
            raise RoleContractError("PLANNER_RESULT_INVALID", "questions must be a list")

        return cls(
            disposition=disposition,
            answer=None if answer_raw is None else PlannerAnswer.from_mapping(answer_raw),
            plan=None if plan_raw is None else ExecutionPlan.from_mapping(plan_raw),
            questions=tuple(PlannerQuestion.from_mapping(item) for item in questions_raw),
            reason_codes=_text_tuple(value.get("reason_codes", []), "planner reason_codes"),
            notes=value.get("notes"),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())
