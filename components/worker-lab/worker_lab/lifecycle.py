from __future__ import annotations

from dataclasses import replace

from .errors import LabValidationError
from .integration_v3 import InvocationRecordV3, InvocationState
from .models import AttemptRecord, AttemptState, _timestamp


LEGAL_TRANSITIONS: dict[AttemptState, frozenset[AttemptState]] = {
    AttemptState.DRAFT: frozenset({AttemptState.READY, AttemptState.ABORTED}),
    AttemptState.READY: frozenset({AttemptState.RUNNING, AttemptState.ABORTED, AttemptState.OUTCOME_RECORDED}),
    AttemptState.RUNNING: frozenset({AttemptState.CANDIDATE, AttemptState.ABORTED, AttemptState.OUTCOME_RECORDED}),
    AttemptState.OUTCOME_RECORDED: frozenset(),
    AttemptState.CANDIDATE: frozenset({AttemptState.EVALUATING, AttemptState.ABORTED}),
    AttemptState.EVALUATING: frozenset({
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
    runtime_identity: str | None = None,
    cleanup_outcome: str | None = None,
) -> AttemptRecord:
    """Return a new attempt state or fail without mutating the input record."""
    if target == AttemptState.PASSED:
        raise LabValidationError(
            "ATTEMPT_ACCEPTANCE_REQUIRED",
            "task acceptance requires the protected evidence-gated acceptance operation",
        )
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
    next_runtime_identity = attempt.runtime_identity
    if target is AttemptState.RUNNING:
        if attempt.state is not AttemptState.READY or attempt.runtime_identity is not None:
            raise LabValidationError(
                "ATTEMPT_RUNTIME_IDENTITY_INVALID", "running transition requires a clean READY attempt"
            )
        if runtime_identity is None:
            raise LabValidationError(
                "ATTEMPT_RUNTIME_IDENTITY_REQUIRED", "running transition requires an invocation identity"
            )
        next_runtime_identity = runtime_identity
    elif runtime_identity is not None:
        raise LabValidationError(
            "ATTEMPT_RUNTIME_IDENTITY_IMMUTABLE", "runtime identity only binds READY to RUNNING"
        )
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
    if target in {AttemptState.CLOSED, AttemptState.ABORTED, AttemptState.OUTCOME_RECORDED} and not cleanup_outcome:
        raise LabValidationError(
            "ATTEMPT_CLEANUP_REQUIRED", "terminal transition requires cleanup outcome"
        )
    if cleanup_outcome is not None and target not in {AttemptState.CLOSED, AttemptState.ABORTED, AttemptState.OUTCOME_RECORDED}:
        raise LabValidationError(
            "ATTEMPT_CLEANUP_INVALID", "cleanup outcome is only recorded at a terminal transition"
        )
    updated = replace(
        attempt,
        state=target,
        updated_at=occurred_at,
        runtime_identity=next_runtime_identity,
        candidate_digest=next_candidate,
        cleanup_outcome=cleanup_outcome or attempt.cleanup_outcome,
    )
    return AttemptRecord.from_mapping(updated.to_dict())


def bind_authorized_invocation(
    attempt: AttemptRecord,
    invocation: InvocationRecordV3,
    *,
    occurred_at: str,
) -> AttemptRecord:
    """Bind one durably reloaded AUTHORIZED invocation to READY -> RUNNING."""
    if attempt.state is not AttemptState.READY or invocation.state is not InvocationState.AUTHORIZED:
        raise LabValidationError("INTEGRATION_AUTHORIZATION_INVALID", "running requires READY and AUTHORIZED records")
    expected = (
        invocation.attempt_id == attempt.attempt_id,
        invocation.exercise_id == attempt.exercise_id,
        invocation.exercise_version == attempt.exercise_version,
        invocation.policy_id == attempt.policy_id,
        invocation.policy_version == attempt.policy_version,
        invocation.policy_digest == attempt.policy_digest,
        invocation.role_id == attempt.role_id,
        invocation.role_version == attempt.role_version,
        invocation.role_digest == attempt.role_digest,
        invocation.context_digest == attempt.context_digest,
        invocation.task_digest == attempt.task_digest,
        invocation.test_catalog_version == attempt.evaluator_catalog_version,
        invocation.test_catalog_digest == attempt.evaluator_catalog_digest,
        invocation.source_state is not None,
        invocation.source_state is not None and invocation.source_state.base_commit == attempt.starting_commit,
        invocation.sandbox_mode == attempt.sandbox_mode,
        invocation.authorized_by is not None,
        invocation.authorized_at is not None,
    )
    if not all(expected):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "authorized invocation differs from attempt")
    return transition_attempt(
        attempt,
        AttemptState.RUNNING,
        occurred_at=occurred_at,
        runtime_identity=invocation.identity_digest(),
    )
