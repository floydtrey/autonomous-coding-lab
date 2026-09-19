"""Planner elevation and resume helpers.

This module bridges Planner's semantic ELEVATION_REQUIRED disposition to ACL's
shared clarification mechanism without making Controller understand Planner
semantics. Controller persists the pending clarification and answer; these
helpers validate the Planner-specific question/answer contract and reconstruct
Planner input without requiring the original request to be re-entered.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from acl_roles.common import RoleResponse, RoleStatus
from acl_roles.common.errors import RoleContractError

from .contract import (
    PlannerDisposition,
    PlannerInput,
    PlannerQuestion,
    PlannerResult,
)


def planner_result_to_role_response(result: PlannerResult) -> RoleResponse:
    """Wrap a semantic Planner result in ACL's shared role envelope.

    Elevation is represented mechanically as NEEDS_CLARIFICATION so the generic
    Controller clarification pause/resume path can persist and resume it.
    Other semantic Planner dispositions are successful role completions; ACL
    interprets their Planner payload later.
    """
    if not isinstance(result, PlannerResult):
        raise RoleContractError(
            "PLANNER_ELEVATION_INVALID",
            "result must be a PlannerResult",
        )
    status = (
        RoleStatus.NEEDS_CLARIFICATION
        if result.disposition is PlannerDisposition.ELEVATION_REQUIRED
        else RoleStatus.COMPLETE
    )
    return RoleResponse(
        status=status,
        payload=result.to_dict(),
    )


def parse_planner_role_response(response: RoleResponse) -> PlannerResult:
    """Parse a shared role envelope and enforce Planner/status alignment."""
    if not isinstance(response, RoleResponse):
        raise RoleContractError(
            "PLANNER_ELEVATION_INVALID",
            "response must be a RoleResponse",
        )
    result = PlannerResult.from_mapping(response.payload)
    expected = (
        RoleStatus.NEEDS_CLARIFICATION
        if result.disposition is PlannerDisposition.ELEVATION_REQUIRED
        else RoleStatus.COMPLETE
    )
    if response.status is not expected:
        raise RoleContractError(
            "PLANNER_STATUS_MISMATCH",
            "shared role status does not match Planner disposition",
            {
                "disposition": str(result.disposition),
                "expected_status": str(expected),
                "observed_status": str(response.status),
            },
        )
    return result


def validate_elevation_answers(
    questions: Sequence[PlannerQuestion],
    answer: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one complete operator response for a Planner elevation.

    The persisted answer is a direct mapping from Planner question_id to the
    operator's answer. Values remain opaque to ACL because Planner owns their
    semantic interpretation.
    """
    if isinstance(questions, (str, bytes)) or not isinstance(questions, Sequence):
        raise RoleContractError(
            "PLANNER_ELEVATION_INVALID",
            "questions must be a sequence",
        )
    if not questions or any(not isinstance(item, PlannerQuestion) for item in questions):
        raise RoleContractError(
            "PLANNER_ELEVATION_INVALID",
            "elevation requires one or more PlannerQuestion values",
        )
    if not isinstance(answer, Mapping):
        raise RoleContractError(
            "PLANNER_ELEVATION_ANSWER_INVALID",
            "elevation answer must be a mapping keyed by question_id",
        )

    question_ids = tuple(item.question_id for item in questions)
    if len(question_ids) != len(set(question_ids)):
        raise RoleContractError(
            "PLANNER_ELEVATION_INVALID",
            "elevation question_id values must be unique",
        )

    observed = set(answer)
    expected = set(question_ids)
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    if missing or extra:
        raise RoleContractError(
            "PLANNER_ELEVATION_ANSWER_INVALID",
            "elevation answer keys must exactly match pending Planner question IDs",
            {
                "missing_question_ids": missing,
                "unexpected_question_ids": extra,
            },
        )

    normalized: dict[str, Any] = {}
    for question_id in question_ids:
        value = answer[question_id]
        if value is None:
            raise RoleContractError(
                "PLANNER_ELEVATION_ANSWER_INVALID",
                "elevation answers must not be null",
                {"question_id": question_id},
            )
        if isinstance(value, str):
            if not value.strip():
                raise RoleContractError(
                    "PLANNER_ELEVATION_ANSWER_INVALID",
                    "text elevation answers must not be blank",
                    {"question_id": question_id},
                )
            value = value.strip()
        normalized[question_id] = value
    return normalized


def resume_planner_input(
    original: PlannerInput,
    elevation: PlannerResult,
    answer: Mapping[str, Any],
) -> PlannerInput:
    """Return the next Planner input while preserving the original invocation.

    Existing elevation answers are retained. Re-answering a question with the
    identical value is idempotent; changing a previously recorded answer is a
    conflict rather than silent mutation.
    """
    if not isinstance(original, PlannerInput):
        raise RoleContractError(
            "PLANNER_ELEVATION_INVALID",
            "original must be a PlannerInput",
        )
    if not isinstance(elevation, PlannerResult) or (
        elevation.disposition is not PlannerDisposition.ELEVATION_REQUIRED
    ):
        raise RoleContractError(
            "PLANNER_ELEVATION_INVALID",
            "resume requires an ELEVATION_REQUIRED PlannerResult",
        )

    normalized = validate_elevation_answers(elevation.questions, answer)
    merged = dict(original.elevation_answers)
    for question_id, value in normalized.items():
        if question_id in merged and merged[question_id] != value:
            raise RoleContractError(
                "PLANNER_ELEVATION_ANSWER_CONFLICT",
                "a previously recorded Planner elevation answer cannot be changed",
                {
                    "question_id": question_id,
                    "recorded_answer": merged[question_id],
                    "requested_answer": value,
                },
            )
        merged[question_id] = value

    return PlannerInput(
        invocation_mode=original.invocation_mode,
        request=dict(original.request),
        routing_context=dict(original.routing_context),
        consultation=original.consultation,
        elevation_answers=merged,
        metadata=dict(original.metadata),
    )
