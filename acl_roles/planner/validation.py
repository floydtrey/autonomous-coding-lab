"""Deterministic Planner V1 response validation.

This layer validates Planner semantics against the Planner input. It does not
grant authority, select a model/runtime, or decide whether a planned edit is a
good idea. Filesystem authority is evaluated separately by ACL Authority.
"""
from __future__ import annotations

import ntpath
import posixpath
import re
from typing import Any, Mapping

from acl_roles.common import RoleRequest, RoleResponse
from acl_roles.common.errors import RoleContractError

from .contract import (
    ExecutionPlan,
    FilesystemIntent,
    PlannerDisposition,
    PlannerInput,
    PlannerInvocationMode,
    PlannerResult,
)
from .elevation import parse_planner_role_response


_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


def normalize_planner_role_response(
    value: Mapping[str, Any],
    *,
    instructions: Mapping[str, Any],
    profile_metadata: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Repair only unambiguous Planner transport wrappers.

    Some local models copy the instructional label shared_envelope and place
    the actual ACL role envelope beneath it. When that is the sole top-level
    key and its value is a mapping, removing the label changes representation
    only, not semantic content.
    """
    if not isinstance(value, Mapping):
        raise RoleContractError(
            "PLANNER_RESULT_INVALID",
            "Planner role response must be a mapping",
        )
    normalized = dict(value)
    transforms: list[str] = []
    if set(normalized) == {"shared_envelope"}:
        inner = normalized.get("shared_envelope")
        if not isinstance(inner, Mapping):
            raise RoleContractError(
                "PLANNER_RESULT_INVALID",
                "shared_envelope wrapper must contain a role response object",
            )
        normalized = dict(inner)
        transforms.append("unwrap_shared_envelope")

    envelope_keys = {"schema_version", "status", "payload", "reference", "metadata"}
    instructional_echo_keys = {
        "shared_envelope",
        "planner_result_common",
        "direct_or_query",
        "execution_plan_shape",
        "execution_plan_semantic_shape",
        "stage_shape",
        "filesystem_move_shape",
        "filesystem_intent_shape",
        "reference_material_shape",
    }
    if envelope_keys.issubset(normalized):
        removed = sorted(set(normalized) & instructional_echo_keys)
        if removed:
            normalized = {
                key: value
                for key, value in normalized.items()
                if key not in instructional_echo_keys
            }
            transforms.append("remove_instructional_echo_keys:" + ",".join(removed))

    payload = normalized.get("payload")
    if isinstance(payload, Mapping):
        disposition = payload.get("disposition")
        if (
            "schema_version" not in payload
            and isinstance(disposition, str)
            and disposition in {
                "DIRECT_RESPONSE",
                "QUERY_RESPONSE",
                "EXECUTION_PLAN",
                "ELEVATION_REQUIRED",
                "CANNOT_PLAN",
            }
        ):
            normalized["payload"] = {
                "schema_version": "acl-planner-result:v1",
                **dict(payload),
            }
            transforms.append("add_planner_v1_schema_marker")

    return normalized, {"planner_transforms": transforms}


def _fail(code: str, message: str, **details: Any) -> None:
    raise RoleContractError(code, message, details or None)


def _validate_path(value: str | None, *, location: str) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        _fail(
            "PLANNER_PATH_INVALID",
            "Planner filesystem paths must be trimmed nonblank text",
            location=location,
            value=value,
        )
    if "\x00" in value:
        _fail(
            "PLANNER_PATH_INVALID",
            "Planner filesystem paths must not contain NUL characters",
            location=location,
        )
    if "://" in value:
        _fail(
            "PLANNER_PATH_INVALID",
            "Planner filesystem declarations must contain filesystem paths, not URLs",
            location=location,
            value=value,
        )


def _normalized_path_key(value: str) -> str:
    if _WINDOWS_DRIVE.match(value) or "\\" in value:
        return ntpath.normcase(ntpath.normpath(value.replace("/", "\\")))
    return posixpath.normpath(value)


def _validate_filesystem_intent(value: FilesystemIntent, *, location: str) -> None:
    for field_name in ("read_paths", "write_paths", "create_paths", "delete_paths"):
        for index, path in enumerate(getattr(value, field_name)):
            _validate_path(path, location=f"{location}.{field_name}[{index}]")
    for index, move in enumerate(value.move_paths):
        _validate_path(move.source, location=f"{location}.move_paths[{index}].source")
        _validate_path(move.destination, location=f"{location}.move_paths[{index}].destination")
        if _normalized_path_key(move.source) == _normalized_path_key(move.destination):
            _fail(
                "PLANNER_MOVE_NOOP",
                "Planner move/rename source and destination must differ",
                location=f"{location}.move_paths[{index}]",
                path=move.source,
            )


def _validate_dependencies(
    graph: Mapping[str, tuple[str, ...]],
    *,
    kind: str,
    locations: Mapping[str, str],
) -> None:
    known = set(graph)
    for node, dependencies in graph.items():
        for dependency in dependencies:
            if dependency == node:
                _fail(
                    "PLANNER_DEPENDENCY_SELF",
                    f"{kind} must not depend on itself",
                    node=node,
                    location=locations[node],
                )
            if dependency not in known:
                _fail(
                    "PLANNER_DEPENDENCY_UNKNOWN",
                    f"{kind} depends on an unknown {kind.lower()}",
                    node=node,
                    dependency=dependency,
                    location=locations[node],
                )

    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            start = stack.index(node) if node in stack else 0
            cycle = stack[start:] + [node]
            _fail(
                "PLANNER_DEPENDENCY_CYCLE",
                f"{kind} dependency graph contains a cycle",
                cycle=cycle,
                location=locations[node],
            )
        visiting.add(node)
        stack.append(node)
        for dependency in graph[node]:
            visit(dependency)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def _validate_plan_structure(plan: ExecutionPlan) -> dict[str, Any]:
    if not plan.required_outputs:
        _fail(
            "PLANNER_REQUIRED_OUTPUTS_MISSING",
            "execution plan must declare one or more required outputs",
        )
    for label, path in (
        ("project.project_root", plan.project.project_root),
        ("workspace.worker_working_directory", plan.workspace.worker_working_directory),
        ("workspace.output_directory", plan.workspace.output_directory),
        ("workspace.artifact_directory", plan.workspace.artifact_directory),
        ("workspace.temporary_directory", plan.workspace.temporary_directory),
    ):
        _validate_path(path, location=label)

    reference_ids = {item.reference_id for item in plan.reference_material}
    all_passes = []
    pass_locations: dict[str, str] = {}
    stage_graph: dict[str, tuple[str, ...]] = {}
    stage_locations: dict[str, str] = {}

    if plan.stages:
        for stage_index, stage in enumerate(plan.stages):
            stage_location = f"plan.stages[{stage_index}]"
            stage_graph[stage.stage_id] = stage.depends_on
            stage_locations[stage.stage_id] = stage_location
            for pass_index, pass_spec in enumerate(stage.passes):
                pass_location = f"{stage_location}.passes[{pass_index}]"
                all_passes.append((pass_spec, pass_location))
                pass_locations[pass_spec.pass_id] = pass_location
        _validate_dependencies(
            stage_graph,
            kind="Stage",
            locations=stage_locations,
        )
    else:
        for pass_index, pass_spec in enumerate(plan.passes):
            pass_location = f"plan.passes[{pass_index}]"
            all_passes.append((pass_spec, pass_location))
            pass_locations[pass_spec.pass_id] = pass_location

    pass_graph = {
        pass_spec.pass_id: pass_spec.depends_on
        for pass_spec, _ in all_passes
    }
    _validate_dependencies(
        pass_graph,
        kind="Pass",
        locations=pass_locations,
    )

    seen_task_ids: dict[str, str] = {}
    referenced_ids: set[str] = set()

    for pass_spec, pass_location in all_passes:
        if not pass_spec.expected_outputs:
            _fail(
                "PLANNER_PASS_OUTPUTS_MISSING",
                "each Pass must declare one or more expected outputs",
                pass_id=pass_spec.pass_id,
                location=pass_location,
            )
        _validate_path(
            pass_spec.working_directory,
            location=f"{pass_location}.working_directory",
        )
        _validate_path(
            pass_spec.output_directory,
            location=f"{pass_location}.output_directory",
        )
        referenced_ids.update(pass_spec.reference_ids)

        task_graph: dict[str, tuple[str, ...]] = {}
        task_locations: dict[str, str] = {}
        for task_index, task in enumerate(pass_spec.tasks):
            task_location = f"{pass_location}.tasks[{task_index}]"
            previous = seen_task_ids.get(task.task_id)
            if previous is not None:
                _fail(
                    "PLANNER_TASK_ID_DUPLICATE",
                    "task_id values must be unique across the entire plan",
                    task_id=task.task_id,
                    first_location=previous,
                    duplicate_location=task_location,
                )
            seen_task_ids[task.task_id] = task_location
            task_graph[task.task_id] = task.depends_on
            task_locations[task.task_id] = task_location
            referenced_ids.update(task.reference_ids)
            _validate_filesystem_intent(
                task.filesystem,
                location=f"{task_location}.filesystem",
            )

        # A Task dependency is intentionally local to its Pass. Cross-Pass
        # ordering belongs on Pass.depends_on so ACL can preserve Pass as the
        # Worker session boundary.
        _validate_dependencies(
            task_graph,
            kind="Task",
            locations=task_locations,
        )

    unknown_references = sorted(referenced_ids - reference_ids)
    if unknown_references:
        _fail(
            "PLANNER_REFERENCE_UNKNOWN",
            "plan uses reference_ids that are not declared in reference_material",
            reference_ids=unknown_references,
        )

    return {
        "stage_count": len(plan.stages),
        "pass_count": len(all_passes),
        "task_count": len(seen_task_ids),
        "reference_count": len(reference_ids),
    }


def validate_planner_result(
    result: PlannerResult,
    *,
    planner_input: PlannerInput | None = None,
) -> dict[str, Any]:
    """Validate Planner semantics and cross-check them against the input."""
    if not isinstance(result, PlannerResult):
        _fail(
            "PLANNER_VALIDATION_INVALID",
            "result must be a PlannerResult",
        )

    if planner_input is not None and not isinstance(planner_input, PlannerInput):
        _fail(
            "PLANNER_VALIDATION_INPUT_INVALID",
            "planner_input must be a PlannerInput when supplied",
        )

    if (
        planner_input is not None
        and planner_input.invocation_mode is PlannerInvocationMode.WORKER_CONSULTATION
        and result.disposition is PlannerDisposition.EXECUTION_PLAN
    ):
        _fail(
            "PLANNER_CONSULTATION_REPLAN_DENIED",
            "WORKER_CONSULTATION may answer, query, elevate, or decline but may not replace the execution plan in V1",
        )

    summary: dict[str, Any] = {
        "disposition": str(result.disposition),
        "invocation_mode": (
            None if planner_input is None else str(planner_input.invocation_mode)
        ),
    }

    if result.disposition is PlannerDisposition.EXECUTION_PLAN:
        plan = result.plan
        if plan is None:
            _fail(
                "PLANNER_EXECUTION_PLAN_MISSING",
                "EXECUTION_PLAN disposition requires a plan",
            )

        if planner_input is not None:
            accepted_work_type_id = planner_input.routing_context.get("work_type_id")
            if accepted_work_type_id is not None:
                if (
                    not isinstance(accepted_work_type_id, str)
                    or not accepted_work_type_id.strip()
                ):
                    _fail(
                        "PLANNER_ROUTING_CONTEXT_INVALID",
                        "routing_context work_type_id must be nonblank text when present",
                    )
                if plan.work_type_id != accepted_work_type_id:
                    _fail(
                        "PLANNER_ROUTE_MISMATCH",
                        "Planner execution plan must preserve the accepted Determiner work_type_id",
                        accepted_work_type_id=accepted_work_type_id,
                        planner_work_type_id=plan.work_type_id,
                    )

        summary.update(_validate_plan_structure(plan))
        summary.update(
            {
                "plan_type": str(plan.plan_type),
                "work_type_id": plan.work_type_id,
                "task_type": plan.task_type,
                "complexity": plan.complexity,
            }
        )

    return summary


def validate_planner_role_response(
    response: RoleResponse,
    *,
    instructions: Mapping[str, Any],
    profile_metadata: Mapping[str, Any],
    request: RoleRequest | None = None,
) -> dict[str, Any]:
    """Configured validator entry point for the generic role dispatcher."""
    result = parse_planner_role_response(response)

    planner_input = None
    if request is not None:
        try:
            planner_input = PlannerInput.from_mapping(request.objective)
        except RoleContractError:
            raise
        except Exception as exc:
            raise RoleContractError(
                "PLANNER_VALIDATION_INPUT_INVALID",
                "Planner role request does not contain a valid PlannerInput objective",
                {
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
            ) from exc

    validation = validate_planner_result(
        result,
        planner_input=planner_input,
    )
    return {
        "contract": "acl-planner-result:v1",
        "result_digest": result.digest(),
        **validation,
    }
