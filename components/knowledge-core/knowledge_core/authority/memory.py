from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class MemoryCandidateReviewOutcome(StrEnum):
    APPROVE_FOR_STORE = "approve_for_store"
    REJECT = "reject"


@dataclass(frozen=True)
class MemoryCandidateReviewRequest:
    reviewer_principal_ref: str
    candidate_id: UUID
    submitted_by_principal_ref: str
    proposer_ref: str
    project_key: str
    content_sha256: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("reviewer_principal_ref", self.reviewer_principal_ref),
            ("submitted_by_principal_ref", self.submitted_by_principal_ref),
            ("proposer_ref", self.proposer_ref),
            ("project_key", self.project_key),
            ("content_sha256", self.content_sha256),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} must be non-empty")


@dataclass(frozen=True)
class MemoryCandidateReviewDecision:
    outcome: MemoryCandidateReviewOutcome
    decision_ref: str
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if not self.decision_ref.strip():
            raise ValueError("decision_ref must be non-empty")
        if self.reason_code is not None and not self.reason_code.strip():
            raise ValueError("reason_code must be null or non-empty")


class MemoryCandidateReviewEvaluator(Protocol):
    """Replaceable deterministic seam for autonomous-memory review."""

    def evaluate_memory_candidate(
        self,
        request: MemoryCandidateReviewRequest,
    ) -> MemoryCandidateReviewDecision: ...


class MemoryCandidateReviewDeniedError(RuntimeError):
    """The review seam explicitly rejected canonical-store eligibility."""


class MemoryCandidateReviewUnavailableError(RuntimeError):
    """No valid deterministic memory-candidate review decision was available."""


def require_memory_candidate_review(
    evaluator: MemoryCandidateReviewEvaluator | None,
    request: MemoryCandidateReviewRequest,
) -> MemoryCandidateReviewDecision:
    if evaluator is None:
        raise MemoryCandidateReviewUnavailableError(
            "memory candidate review authority is not configured"
        )
    try:
        decision = evaluator.evaluate_memory_candidate(request)
    except MemoryCandidateReviewDeniedError:
        raise
    except MemoryCandidateReviewUnavailableError:
        raise
    except Exception as exc:
        raise MemoryCandidateReviewUnavailableError(
            "memory candidate review evaluation failed"
        ) from exc
    if not isinstance(decision, MemoryCandidateReviewDecision):
        raise MemoryCandidateReviewUnavailableError(
            "memory candidate review returned an invalid decision"
        )
    return decision
