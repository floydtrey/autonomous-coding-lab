from __future__ import annotations

from dataclasses import replace

from .errors import LabValidationError
from .models import AttemptRecord, AttemptState, _timestamp


LEGAL_TRANSITIONS: dict[AttemptState, frozenset[AttemptState]] = {
    AttemptState.DRAFT: frozenset({AttemptState.READY, AttemptState.ABORTED}),
    AttemptState.READY: frozenset({AttemptState.RUNNING, AttemptState.ABORTED}),
    AttemptState.RUNNING: frozenset({AttemptState.CANDIDATE, AttemptState.ABORTED}),
    AttemptState.CANDIDATE: frozenset({AttemptState.EVALUATING, AttemptState.ABORTED}),
    AttemptState.EVALUATING: frozenset({
        AttemptState.PASSED,
        AttemptState.FAILED,
        AttemptState.NEEDS_REVIEW,
        AttemptState.ABORTED,
    }),
    AttemptState.PASSED: frozenset({AttemptState.CLOSED}),
    AttemptState.FAILED: frozenset({AttemptState.CLOSED}),
    AttemptState.NEEDS_REVIEW: frozenset({AttemptState.CLOSED}),
    AttemptState.CLOSED: frozenset(),
    AttemptState.ABORTED: frozenset(),
}


def transition_attempt(
    attempt: AttemptRecord,
    target: AttemptState,
    *,
    occurred_at: str,
    candidate_digest: str | None = None,
    cleanup_outcome: str | None = None,
) -> AttemptRecord:
    """Return a new attempt state or fail without mutating the input record."""
    if target not in LEGAL_TRANSITIONS[attempt.state]:
        raise LabValidationError(
            "ATTEMPT_TRANSITION_INVALID",
            f"cannot transition attempt from {attempt.state} to {target}",
        )
    timestamp = _timestamp(occurred_at, "occurred_at")
    if timestamp < _timestamp(attempt.updated_at, "updated_at"):
        raise LabValidationError(
            "ATTEMPT_TRANSITION_TIME_INVALID", "transition time cannot move backward"
        )
    next_candidate = attempt.candidate_digest
    if target is AttemptState.CANDIDATE:
        if candidate_digest is None:
            raise LabValidationError(
                "ATTEMPT_CANDIDATE_REQUIRED", "candidate transition requires candidate identity"
            )
        next_candidate = candidate_digest
    elif candidate_digest is not None and candidate_digest != attempt.candidate_digest:
        raise LabValidationError(
            "ATTEMPT_IDENTITY_IMMUTABLE", "candidate identity cannot change after capture"
        )
    if target in {AttemptState.CLOSED, AttemptState.ABORTED} and not cleanup_outcome:
        raise LabValidationError(
            "ATTEMPT_CLEANUP_REQUIRED", "terminal transition requires cleanup outcome"
        )
    if cleanup_outcome is not None and target not in {AttemptState.CLOSED, AttemptState.ABORTED}:
        raise LabValidationError(
            "ATTEMPT_CLEANUP_INVALID", "cleanup outcome is only recorded at a terminal transition"
        )
    updated = replace(
        attempt,
        state=target,
        updated_at=occurred_at,
        candidate_digest=next_candidate,
        cleanup_outcome=cleanup_outcome or attempt.cleanup_outcome,
    )
    return AttemptRecord.from_mapping(updated.to_dict())
