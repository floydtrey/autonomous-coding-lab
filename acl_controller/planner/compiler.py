"""Compile small Planner semantic submissions into ACL's internal plan IR.

The model-facing contract stays intentionally small. This compiler adds only
mechanical Controller-owned structure: IDs, ordering, known workspace/routing
context, deterministic defaults, and the legacy internal ExecutionPlan shape
consumed by persistence and Worker orchestration.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from acl_roles.planner import (
    ExecutionPlan,
    FilesystemIntent,
    PassSpec,
    PlanType,
    PlannerAnswer,
    PlannerDisposition,
    PlannerInput,
    PlannerQuestion,
    PlannerResult,
    PlannerSemanticSubmission,
    ProjectReference,
    TaskSpec,
    WorkspaceSpec,
    validate_planner_result,
)
from acl_roles.planner.contract import DEFAULT_CONTINUATION_INSTRUCTIONS

from ..authority.pass_authority import WORKER_AUTHORITY_MODE_WORKSPACE
from ..errors import ControllerError


@dataclass(frozen=True)
class PlannerCompilation:
    result: PlannerResult
    worker_authority_mode: str | None = None


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ControllerError(
            "CONTROLLER_PLANNER_SEMANTIC_COMPILE_INVALID",
            f"{label} is required to compile Planner semantic output",
        )
    return value.strip()


def _project_context(planner_input: PlannerInput) -> Mapping[str, Any]:
    value = planner_input.metadata.get("project_context")
    if not isinstance(value, Mapping):
        raise ControllerError(
            "CONTROLLER_PLANNER_SEMANTIC_COMPILE_INVALID",
            "Planner project_context is required to compile an execution plan",
        )
    return value


def compile_planner_semantic_submission(
    submission: PlannerSemanticSubmission,
    planner_input: PlannerInput,
) -> PlannerCompilation:
    if not isinstance(submission, PlannerSemanticSubmission):
        raise ControllerError(
            "CONTROLLER_PLANNER_SEMANTIC_COMPILE_INVALID",
            "submission must be PlannerSemanticSubmission",
        )
    if not isinstance(planner_input, PlannerInput):
        raise ControllerError(
            "CONTROLLER_PLANNER_SEMANTIC_COMPILE_INVALID",
            "planner_input must be PlannerInput",
        )

    if submission.disposition in {
        PlannerDisposition.DIRECT_RESPONSE,
        PlannerDisposition.QUERY_RESPONSE,
    }:
        return PlannerCompilation(
            PlannerResult(
                disposition=submission.disposition,
                answer=PlannerAnswer(
                    answer=_required_text(submission.answer, "Planner answer"),
                    sources=submission.sources,
                    references=submission.references,
                ),
                reason_codes=submission.reason_codes,
                notes=submission.notes,
            )
        )

    if submission.disposition is PlannerDisposition.ELEVATION_REQUIRED:
        questions = tuple(
            PlannerQuestion(
                question_id=f"Q{index:02d}",
                question=item.question,
                reason=item.reason,
                options=item.options,
            )
            for index, item in enumerate(submission.questions, start=1)
        )
        return PlannerCompilation(
            PlannerResult(
                disposition=submission.disposition,
                questions=questions,
                reason_codes=submission.reason_codes,
                notes=submission.notes,
            )
        )

    if submission.disposition is PlannerDisposition.CANNOT_PLAN:
        return PlannerCompilation(
            PlannerResult(
                disposition=submission.disposition,
                reason_codes=submission.reason_codes,
                notes=submission.notes,
            )
        )

    if submission.disposition is not PlannerDisposition.EXECUTION_PLAN:
        raise ControllerError(
            "CONTROLLER_PLANNER_SEMANTIC_COMPILE_INVALID",
            "unsupported Planner semantic disposition",
            {"disposition": str(submission.disposition)},
        )

    context = _project_context(planner_input)
    project_root = _required_text(context.get("project_root"), "project_root")
    working_directory = _required_text(
        context.get("worker_working_directory"),
        "worker_working_directory",
    )
    output_directory = _required_text(
        context.get("output_directory"),
        "output_directory",
    )
    artifact_directory = context.get("artifact_directory")
    if artifact_directory is not None:
        artifact_directory = _required_text(
            artifact_directory,
            "artifact_directory",
        )

    work_type_id = planner_input.routing_context.get("work_type_id")
    if work_type_id is not None:
        work_type_id = _required_text(work_type_id, "routing work_type_id")
    complexity = planner_input.routing_context.get("complexity")
    complexity = (
        "MEDIUM"
        if complexity is None
        else _required_text(complexity, "routing complexity")
    )
    task_type = planner_input.routing_context.get("work_type_label")
    task_type = (
        "ROUTED_WORK"
        if task_type is None
        else _required_text(task_type, "routing work_type_label")
    )

    compiled_passes: list[PassSpec] = []
    task_number = 0
    prior_pass_id: str | None = None
    plan_criteria: list[str] = []

    for pass_number, semantic_pass in enumerate(submission.passes, start=1):
        pass_id = f"P{pass_number:02d}"
        tasks: list[TaskSpec] = []
        prior_task_id: str | None = None

        for semantic_task in semantic_pass.tasks:
            task_number += 1
            task_id = f"T{task_number:02d}"
            tasks.append(
                TaskSpec(
                    task_id=task_id,
                    name=f"Task {task_number}",
                    instruction=semantic_task.instruction,
                    depends_on=(() if prior_task_id is None else (prior_task_id,)),
                    filesystem=FilesystemIntent(),
                    acceptance_criteria=semantic_task.acceptance_criteria,
                    expected_result="The submitted task instruction is completed.",
                )
            )
            prior_task_id = task_id
            plan_criteria.extend(semantic_task.acceptance_criteria)

        pass_criteria = semantic_pass.acceptance_criteria or (
            "The submitted Pass objective is satisfied.",
        )
        plan_criteria.extend(semantic_pass.acceptance_criteria)
        compiled_passes.append(
            PassSpec(
                pass_id=pass_id,
                name=semantic_pass.name or f"Pass {pass_number}",
                objective=semantic_pass.objective,
                complexity=complexity,
                tasks=tuple(tasks),
                depends_on=(() if prior_pass_id is None else (prior_pass_id,)),
                working_directory=working_directory,
                output_directory=output_directory,
                expected_outputs=("The submitted Pass objective is completed.",),
                acceptance_criteria=tuple(pass_criteria),
                continuation_instructions=DEFAULT_CONTINUATION_INSTRUCTIONS,
            )
        )
        prior_pass_id = pass_id

    if not plan_criteria:
        plan_criteria.append("All submitted Planner Pass objectives are satisfied.")

    plan_type = (
        PlanType.SINGLE_PASS
        if len(compiled_passes) == 1
        else PlanType.MULTI_PASS
    )
    plan = ExecutionPlan(
        plan_type=plan_type,
        project=ProjectReference(
            project_name=(
                context.get("project_name")
                if isinstance(context.get("project_name"), str)
                and context.get("project_name").strip()
                else None
            ),
            version_id=(
                context.get("version_id")
                if isinstance(context.get("version_id"), str)
                and context.get("version_id").strip()
                else None
            ),
            project_root=project_root,
        ),
        work_type_id=work_type_id,
        task_type=task_type,
        complexity=complexity,
        objective=_required_text(submission.objective, "Planner objective"),
        acceptance_criteria=tuple(dict.fromkeys(plan_criteria)),
        required_outputs=("The requested work is completed in the configured workspace/output.",),
        constraints=submission.constraints,
        workspace=WorkspaceSpec(
            worker_working_directory=working_directory,
            output_directory=output_directory,
            artifact_directory=artifact_directory,
        ),
        decomposition_reason=(
            None
            if plan_type is PlanType.SINGLE_PASS
            else "Planner submitted multiple sequential Worker Passes."
        ),
        passes=tuple(compiled_passes),
    )

    result = PlannerResult(
        disposition=PlannerDisposition.EXECUTION_PLAN,
        plan=plan,
        reason_codes=submission.reason_codes,
        notes=submission.notes,
    )
    try:
        validate_planner_result(result, planner_input=planner_input)
    except Exception as exc:
        raise ControllerError(
            "CONTROLLER_PLANNER_SEMANTIC_COMPILE_INVALID",
            "Controller failed to compile semantic Planner output into valid internal IR",
            {
                "exception_type": type(exc).__name__,
                "message": str(exc),
            },
        ) from exc

    return PlannerCompilation(
        result,
        worker_authority_mode=WORKER_AUTHORITY_MODE_WORKSPACE,
    )
