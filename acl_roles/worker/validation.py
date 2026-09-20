"""Deterministic Worker V1 response validation."""

from __future__ import annotations

from typing import Any, Mapping

from acl_roles.common import RoleRequest, RoleResponse
from acl_roles.common.errors import RoleContractError

from .contract import (
    WORKER_INPUT_SCHEMA,
    WorkerInput,
    WorkerOutcome,
    WorkerResult,
    expected_role_status,
    parse_worker_role_response,
)


def normalize_worker_role_response(
    value: Mapping[str, Any],
    *,
    instructions: Mapping[str, Any],
    profile_metadata: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, Mapping):
        raise RoleContractError(
            "WORKER_RESULT_INVALID",
            "Worker response must be a mapping",
        )
    normalized = dict(value)
    transforms: list[str] = []

    # Common local-model mistake: instructional wrapper around the real envelope.
    if set(normalized) == {"shared_envelope"}:
        inner = normalized.get("shared_envelope")
        if not isinstance(inner, Mapping):
            raise RoleContractError(
                "WORKER_RESULT_INVALID",
                "shared_envelope must contain the role response",
            )
        normalized = dict(inner)
        transforms.append("unwrap_shared_envelope")

    # Some local models echo both the canonical shared envelope and the Worker
    # payload beside it. Accept this only when the redundant Worker payload is
    # exactly the same as shared_envelope.payload; otherwise keep rejecting the
    # response as ambiguous.
    elif (
        set(normalized) == {"schema_version", "shared_envelope", "worker_result"}
        and normalized.get("schema_version") == "acl-role-response:v1"
    ):
        inner = normalized.get("shared_envelope")
        worker_result = normalized.get("worker_result")
        if not isinstance(inner, Mapping) or not isinstance(worker_result, Mapping):
            raise RoleContractError(
                "WORKER_RESULT_INVALID",
                "redundant Worker response wrapper must contain mappings",
            )
        payload = inner.get("payload")
        if not isinstance(payload, Mapping) or dict(payload) != dict(worker_result):
            raise RoleContractError(
                "WORKER_RESULT_INVALID",
                "redundant Worker response wrapper is ambiguous",
            )
        normalized = dict(inner)
        transforms.append("unwrap_redundant_worker_envelope")

    payload = normalized.get("payload")
    if isinstance(payload, Mapping) and "schema_version" not in payload:
        outcome = payload.get("outcome")
        if isinstance(outcome, str) and outcome in {item.value for item in WorkerOutcome}:
            normalized["payload"] = {
                "schema_version": "acl-worker-result:v1",
                **dict(payload),
            }
            transforms.append("add_worker_v1_schema_marker")

    return normalized, {"worker_transforms": transforms}


def validate_worker_result(
    result: WorkerResult,
    *,
    worker_input: WorkerInput,
    execution_events: tuple[Mapping[str, Any], ...] = (),
) -> dict[str, Any]:
    if not isinstance(result, WorkerResult):
        raise RoleContractError(
            "WORKER_VALIDATION_INPUT_INVALID",
            "result must be WorkerResult",
        )
    if not isinstance(worker_input, WorkerInput):
        raise RoleContractError(
            "WORKER_VALIDATION_INPUT_INVALID",
            "worker_input must be WorkerInput",
        )

    if result.plan_id != worker_input.plan_id:
        raise RoleContractError(
            "WORKER_PLAN_MISMATCH",
            "Worker result plan_id differs from assigned plan",
            {
                "expected": worker_input.plan_id,
                "observed": result.plan_id,
                "location": "payload.plan_id",
            },
        )
    if result.plan_version != worker_input.plan_version:
        raise RoleContractError(
            "WORKER_PLAN_VERSION_MISMATCH",
            "Worker result plan_version differs from assigned plan",
            {
                "expected": worker_input.plan_version,
                "observed": result.plan_version,
                "location": "payload.plan_version",
            },
        )
    if result.pass_id != worker_input.pass_id:
        raise RoleContractError(
            "WORKER_PASS_MISMATCH",
            "Worker result pass_id differs from assigned Pass",
            {
                "expected": worker_input.pass_id,
                "observed": result.pass_id,
                "location": "payload.pass_id",
            },
        )

    task_ids = {task.task_id for task in worker_input.pass_spec.tasks}
    unknown_completed = [
        task_id for task_id in result.completed_task_ids if task_id not in task_ids
    ]
    if unknown_completed:
        raise RoleContractError(
            "WORKER_TASK_UNKNOWN",
            "Worker result marks tasks complete that are not in the assigned Pass",
            {
                "pass_id": worker_input.pass_id,
                "task_ids": unknown_completed,
                "location": "payload.completed_task_ids",
            },
        )

    if result.outcome is WorkerOutcome.READY_FOR_REVIEW:
        missing = [
            task.task_id
            for task in worker_input.pass_spec.tasks
            if task.task_id not in result.completed_task_ids
        ]
        if missing:
            raise RoleContractError(
                "WORKER_TASKS_INCOMPLETE",
                "READY_FOR_REVIEW requires every assigned Task to be reported complete",
                {
                    "pass_id": worker_input.pass_id,
                    "missing_task_ids": missing,
                    "location": "payload.completed_task_ids",
                },
            )

    if result.outcome is WorkerOutcome.NEEDS_PLANNER:
        request = result.planner_request
        if request is not None and request.task_id is not None and request.task_id not in task_ids:
            raise RoleContractError(
                "WORKER_PLANNER_TASK_UNKNOWN",
                "Planner consultation request references a Task outside the assigned Pass",
                {
                    "pass_id": worker_input.pass_id,
                    "task_id": request.task_id,
                    "location": "payload.planner_request.task_id",
                },
            )

    if result.outcome is WorkerOutcome.READY_FOR_REVIEW:
        required_mutation = any(
            task.filesystem.create_paths
            or task.filesystem.write_paths
            or task.filesystem.delete_paths
            or task.filesystem.move_paths
            for task in worker_input.pass_spec.tasks
        )
        observed_paths = _successful_mutation_paths(execution_events)
        if required_mutation and not observed_paths:
            raise RoleContractError(
                "WORKER_EXECUTION_EVIDENCE_MISSING",
                "READY_FOR_REVIEW requires ACL-observed successful mutation evidence",
                {
                    "pass_id": worker_input.pass_id,
                    "location": "payload.changed_paths",
                },
            )
        unsupported = [
            path
            for path in result.changed_paths
            if _claim_path(path) not in observed_paths
        ]
        if unsupported:
            raise RoleContractError(
                "WORKER_EXECUTION_EVIDENCE_MISMATCH",
                "Worker claims changed paths without matching successful ACL tool execution",
                {
                    "pass_id": worker_input.pass_id,
                    "changed_paths": unsupported,
                    "location": "payload.changed_paths",
                },
            )

    return {
        "contract": "acl-worker-result:v1",
        "outcome": str(result.outcome),
        "plan_id": result.plan_id,
        "plan_version": result.plan_version,
        "pass_id": result.pass_id,
        "completed_task_count": len(result.completed_task_ids),
        "changed_path_count": len(result.changed_paths),
        "evidence_count": len(result.evidence),
        "result_digest": result.digest(),
    }


def validate_worker_role_response(
    response: RoleResponse,
    *,
    instructions: Mapping[str, Any] | None = None,
    request: RoleRequest | None = None,
    profile_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(response, RoleResponse):
        raise RoleContractError(
            "WORKER_VALIDATION_INPUT_INVALID",
            "response must be RoleResponse",
        )
    result = parse_worker_role_response(response)
    expected = expected_role_status(result.outcome)
    if response.status is not expected:
        raise RoleContractError(
            "WORKER_STATUS_MISMATCH",
            "shared role status does not match Worker outcome",
            {
                "outcome": str(result.outcome),
                "expected_status": str(expected),
                "observed_status": str(response.status),
            },
        )

    worker_input = None
    if request is not None:
        objective = request.objective
        if isinstance(objective, Mapping) and objective.get("schema_version") == WORKER_INPUT_SCHEMA:
            worker_input = WorkerInput.from_mapping(objective)

    if worker_input is None:
        return {
            "contract": "acl-worker-result:v1",
            "outcome": str(result.outcome),
            "result_digest": result.digest(),
        }

    execution_events: list[Mapping[str, Any]] = []
    adapter_telemetry = response.metadata.get("adapter_telemetry")
    if isinstance(adapter_telemetry, Mapping):
        current_events = adapter_telemetry.get("tool_events", [])
        if isinstance(current_events, list):
            execution_events.extend(
                item for item in current_events if isinstance(item, Mapping)
            )
    if worker_input.correction is not None:
        prior_events = worker_input.correction.details.get("execution_evidence", [])
        if isinstance(prior_events, list):
            execution_events.extend(
                item for item in prior_events if isinstance(item, Mapping)
            )

    return validate_worker_result(
        result,
        worker_input=worker_input,
        execution_events=tuple(execution_events),
    )


def _successful_mutation_paths(
    events: tuple[Mapping[str, Any], ...],
) -> set[str]:
    observed: set[str] = set()
    for event in events:
        if event.get("ok") is not True or event.get("duplicate_suppressed") is True:
            continue
        tool_id = event.get("tool_id")
        arguments = event.get("arguments")
        if not isinstance(arguments, Mapping):
            continue
        if tool_id in {
            "filesystem.create_text",
            "filesystem.write_text",
            "filesystem.delete_path",
        }:
            path = arguments.get("path")
            if isinstance(path, str) and path.strip():
                observed.add(_claim_path(path))
        elif tool_id == "filesystem.move_path":
            for key in ("source", "destination"):
                path = arguments.get(key)
                if isinstance(path, str) and path.strip():
                    observed.add(_claim_path(path))
    return observed


def _claim_path(value: str) -> str:
    return value.strip().replace("/", "\\").rstrip("\\").casefold()
