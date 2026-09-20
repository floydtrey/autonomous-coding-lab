"""Small model-facing Planner response contract.

The model returns semantic intent only. ACL compiles that intent into the richer
internal PlannerResult/ExecutionPlan representation later. This module deliberately
contains no authority grants, runtime/provider fields, workspace serialization,
Controller IDs, filesystem permission arrays, or execution-state bookkeeping.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from acl_roles.common import RoleRequest, RoleResponse, RoleStatus
from acl_roles.common.errors import RoleContractError

from .contract import PlannerDisposition, PlannerInput, PlannerInvocationMode


PLANNER_SEMANTIC_SCHEMA = "acl-planner-semantic:v1"


def _fail(message: str, **details: Any) -> None:
    raise RoleContractError(
        "PLANNER_SEMANTIC_INVALID",
        message,
        details or None,
    )


def _text(value: Any, label: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label} must be nonblank text")
    return value.strip()


def _text_tuple(value: Any, label: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        _fail(f"{label} must be a list of text values")
    result = tuple(_text(item, label) for item in value)
    return tuple(item for item in result if item is not None)


@dataclass(frozen=True)
class PlannerSemanticTask:
    instruction: str
    acceptance_criteria: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "instruction", _text(self.instruction, "task instruction"))
        object.__setattr__(
            self,
            "acceptance_criteria",
            _text_tuple(self.acceptance_criteria, "task acceptance_criteria"),
        )

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"instruction": self.instruction}
        if self.acceptance_criteria:
            value["acceptance_criteria"] = list(self.acceptance_criteria)
        return value

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerSemanticTask":
        if not isinstance(value, Mapping):
            _fail("task must be an object")
        forbidden = {"task_id", "depends_on", "filesystem", "reference_ids", "evidence_required"}
        observed = sorted(forbidden & set(value))
        if observed:
            _fail("task contains Controller-owned fields", fields=observed)
        return cls(
            instruction=value.get("instruction"),
            acceptance_criteria=_text_tuple(
                value.get("acceptance_criteria", ()),
                "task acceptance_criteria",
            ),
        )


@dataclass(frozen=True)
class PlannerSemanticPass:
    objective: str
    tasks: tuple[PlannerSemanticTask, ...]
    name: str | None = None
    acceptance_criteria: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "objective", _text(self.objective, "pass objective"))
        if self.name is not None:
            object.__setattr__(self, "name", _text(self.name, "pass name"))
        if (
            not isinstance(self.tasks, tuple)
            or not self.tasks
            or any(not isinstance(item, PlannerSemanticTask) for item in self.tasks)
        ):
            _fail("each pass must contain one or more semantic tasks")
        object.__setattr__(
            self,
            "acceptance_criteria",
            _text_tuple(self.acceptance_criteria, "pass acceptance_criteria"),
        )

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "objective": self.objective,
            "tasks": [task.to_dict() for task in self.tasks],
        }
        if self.name is not None:
            value["name"] = self.name
        if self.acceptance_criteria:
            value["acceptance_criteria"] = list(self.acceptance_criteria)
        return value

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerSemanticPass":
        if not isinstance(value, Mapping):
            _fail("pass must be an object")
        forbidden = {
            "pass_id",
            "depends_on",
            "working_directory",
            "output_directory",
            "reference_ids",
            "evidence_required",
            "tracking_requirements",
            "continuation_instructions",
        }
        observed = sorted(forbidden & set(value))
        if observed:
            _fail("pass contains Controller-owned fields", fields=observed)
        tasks = value.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            _fail("each pass must contain one or more tasks")
        return cls(
            objective=value.get("objective"),
            name=value.get("name"),
            acceptance_criteria=_text_tuple(
                value.get("acceptance_criteria", ()),
                "pass acceptance_criteria",
            ),
            tasks=tuple(PlannerSemanticTask.from_mapping(item) for item in tasks),
        )


@dataclass(frozen=True)
class PlannerSemanticQuestion:
    question: str
    reason: str
    options: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "question", _text(self.question, "question"))
        object.__setattr__(self, "reason", _text(self.reason, "question reason"))
        object.__setattr__(self, "options", _text_tuple(self.options, "question options"))

    def to_dict(self) -> dict[str, Any]:
        value = {
            "question": self.question,
            "reason": self.reason,
        }
        if self.options:
            value["options"] = list(self.options)
        return value

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerSemanticQuestion":
        if not isinstance(value, Mapping):
            _fail("question must be an object")
        return cls(
            question=value.get("question"),
            reason=value.get("reason"),
            options=_text_tuple(value.get("options", ()), "question options"),
        )


@dataclass(frozen=True)
class PlannerSemanticSubmission:
    disposition: PlannerDisposition
    answer: str | None = None
    sources: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    objective: str | None = None
    constraints: tuple[str, ...] = ()
    passes: tuple[PlannerSemanticPass, ...] = ()
    questions: tuple[PlannerSemanticQuestion, ...] = ()
    reason_codes: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, PlannerDisposition):
            _fail("disposition is invalid")
        if self.answer is not None:
            object.__setattr__(self, "answer", _text(self.answer, "answer"))
        if self.objective is not None:
            object.__setattr__(self, "objective", _text(self.objective, "objective"))
        if self.notes is not None:
            object.__setattr__(self, "notes", _text(self.notes, "notes"))
        object.__setattr__(self, "sources", _text_tuple(self.sources, "sources"))
        object.__setattr__(self, "references", _text_tuple(self.references, "references"))
        object.__setattr__(self, "constraints", _text_tuple(self.constraints, "constraints"))
        object.__setattr__(self, "reason_codes", _text_tuple(self.reason_codes, "reason_codes"))

        if not isinstance(self.passes, tuple) or any(
            not isinstance(item, PlannerSemanticPass) for item in self.passes
        ):
            _fail("passes must contain semantic pass objects")
        if not isinstance(self.questions, tuple) or any(
            not isinstance(item, PlannerSemanticQuestion) for item in self.questions
        ):
            _fail("questions must contain semantic question objects")

        if self.disposition in {
            PlannerDisposition.DIRECT_RESPONSE,
            PlannerDisposition.QUERY_RESPONSE,
        }:
            if self.answer is None:
                _fail("response disposition requires answer")
            if self.objective is not None or self.passes or self.questions:
                _fail("response disposition may not contain plan or questions")
        elif self.disposition is PlannerDisposition.EXECUTION_PLAN:
            if self.objective is None or not self.passes:
                _fail("EXECUTION_PLAN requires objective and one or more passes")
            if self.answer is not None or self.questions:
                _fail("EXECUTION_PLAN may not contain answer or questions")
        elif self.disposition is PlannerDisposition.ELEVATION_REQUIRED:
            if not self.questions:
                _fail("ELEVATION_REQUIRED requires one or more questions")
            if self.answer is not None or self.objective is not None or self.passes:
                _fail("ELEVATION_REQUIRED may not contain answer or plan")
        elif self.disposition is PlannerDisposition.CANNOT_PLAN:
            if self.answer is not None or self.objective is not None or self.passes or self.questions:
                _fail("CANNOT_PLAN may not contain answer, plan, or questions")
            if not self.reason_codes and self.notes is None:
                _fail("CANNOT_PLAN requires a reason code or note")

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": PLANNER_SEMANTIC_SCHEMA,
            "disposition": str(self.disposition),
        }
        if self.answer is not None:
            value["answer"] = self.answer
        if self.sources:
            value["sources"] = list(self.sources)
        if self.references:
            value["references"] = list(self.references)
        if self.objective is not None:
            value["objective"] = self.objective
        if self.constraints:
            value["constraints"] = list(self.constraints)
        if self.passes:
            value["passes"] = [item.to_dict() for item in self.passes]
        if self.questions:
            value["questions"] = [item.to_dict() for item in self.questions]
        if self.reason_codes:
            value["reason_codes"] = list(self.reason_codes)
        if self.notes is not None:
            value["notes"] = self.notes
        return value

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerSemanticSubmission":
        if not isinstance(value, Mapping):
            _fail("Planner semantic submission must be an object")
        if value.get("schema_version") != PLANNER_SEMANTIC_SCHEMA:
            _fail("Planner semantic submission schema is invalid")
        forbidden = {
            "plan_type",
            "project",
            "work_type_id",
            "task_type",
            "complexity",
            "required_capabilities",
            "required_tools",
            "required_services",
            "workspace",
            "reference_material",
            "tracking_requirements",
            "decomposition_reason",
            "stages",
        }
        observed = sorted(forbidden & set(value))
        if observed:
            _fail("Planner semantic submission contains Controller-owned fields", fields=observed)
        try:
            disposition = PlannerDisposition(value.get("disposition"))
        except (TypeError, ValueError) as exc:
            raise RoleContractError(
                "PLANNER_SEMANTIC_INVALID",
                "Planner semantic disposition is invalid",
            ) from exc

        passes = value.get("passes", [])
        questions = value.get("questions", [])
        if not isinstance(passes, list):
            _fail("passes must be a list")
        if not isinstance(questions, list):
            _fail("questions must be a list")

        return cls(
            disposition=disposition,
            answer=value.get("answer"),
            sources=_text_tuple(value.get("sources", ()), "sources"),
            references=_text_tuple(value.get("references", ()), "references"),
            objective=value.get("objective"),
            constraints=_text_tuple(value.get("constraints", ()), "constraints"),
            passes=tuple(PlannerSemanticPass.from_mapping(item) for item in passes),
            questions=tuple(
                PlannerSemanticQuestion.from_mapping(item) for item in questions
            ),
            reason_codes=_text_tuple(value.get("reason_codes", ()), "reason_codes"),
            notes=value.get("notes"),
        )


def parse_planner_semantic_role_response(
    response: RoleResponse,
) -> PlannerSemanticSubmission:
    if not isinstance(response, RoleResponse):
        _fail("response must be a RoleResponse")
    submission = PlannerSemanticSubmission.from_mapping(response.payload)
    expected = (
        RoleStatus.NEEDS_CLARIFICATION
        if submission.disposition is PlannerDisposition.ELEVATION_REQUIRED
        else RoleStatus.COMPLETE
    )
    if response.status is not expected:
        raise RoleContractError(
            "PLANNER_SEMANTIC_STATUS_MISMATCH",
            "shared role status does not match Planner semantic disposition",
            {
                "disposition": str(submission.disposition),
                "expected_status": str(expected),
                "observed_status": str(response.status),
            },
        )
    return submission


def normalize_planner_semantic_role_response(
    value: Mapping[str, Any],
    *,
    instructions: Mapping[str, Any],
    profile_metadata: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply representation-only recovery to the small Planner seam."""
    if not isinstance(value, Mapping):
        _fail("Planner role response must be an object")
    normalized = dict(value)
    transforms: list[str] = []

    if set(normalized) == {"shared_envelope"} and isinstance(
        normalized.get("shared_envelope"),
        Mapping,
    ):
        normalized = dict(normalized["shared_envelope"])
        transforms.append("unwrap_shared_envelope")

    payload = normalized.get("payload")
    if isinstance(payload, Mapping):
        disposition = payload.get("disposition")
        if (
            "schema_version" not in payload
            and isinstance(disposition, str)
            and disposition in {item.value for item in PlannerDisposition}
        ):
            normalized["payload"] = {
                "schema_version": PLANNER_SEMANTIC_SCHEMA,
                **dict(payload),
            }
            transforms.append("add_planner_semantic_schema_marker")

    return normalized, {"planner_semantic_transforms": transforms}


def validate_planner_semantic_role_response(
    response: RoleResponse,
    *,
    instructions: Mapping[str, Any],
    profile_metadata: Mapping[str, Any],
    request: RoleRequest | None = None,
) -> dict[str, Any]:
    submission = parse_planner_semantic_role_response(response)

    planner_input = None
    if request is not None:
        planner_input = PlannerInput.from_mapping(request.objective)

    if (
        planner_input is not None
        and planner_input.invocation_mode is PlannerInvocationMode.WORKER_CONSULTATION
        and submission.disposition is PlannerDisposition.EXECUTION_PLAN
    ):
        raise RoleContractError(
            "PLANNER_CONSULTATION_REPLAN_DENIED",
            "WORKER_CONSULTATION may not replace the approved plan",
        )

    return {
        "contract": PLANNER_SEMANTIC_SCHEMA,
        "disposition": str(submission.disposition),
        "pass_count": len(submission.passes),
        "task_count": sum(len(item.tasks) for item in submission.passes),
        "question_count": len(submission.questions),
    }
