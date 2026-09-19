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
    return validate_worker_result(result, worker_input=worker_input)
