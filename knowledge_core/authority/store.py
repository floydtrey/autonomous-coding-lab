from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CanonicalStoreAuthorityRequest:
    caller_principal_ref: str
    operation_id: UUID
    project_key: str
    content_sha256: str
    source_id: str | None = None
    source_event_time: datetime | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("caller_principal_ref", self.caller_principal_ref),
            ("project_key", self.project_key),
            ("content_sha256", self.content_sha256),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} must be non-empty")
        if self.source_id is not None and not self.source_id.strip():
            raise ValueError("source_id must be null or non-empty")
        if self.source_event_time is not None and (
            self.source_event_time.tzinfo is None
            or self.source_event_time.utcoffset() is None
        ):
            raise ValueError("source_event_time must be null or timezone-aware")


@dataclass(frozen=True)
class CanonicalStoreAuthorityDecision:
    allowed: bool
    decision_ref: str | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("decision_ref", self.decision_ref),
            ("reason_code", self.reason_code),
        ):
            if value is not None and not value.strip():
                raise ValueError(f"{field_name} must be null or non-empty")
        if self.allowed and self.decision_ref is None:
            raise ValueError("allowed canonical store requires a decision_ref")


class CanonicalStoreAuthorityEvaluator(Protocol):
    """Trusted host seam for proving an exact direct canonical write was authorized."""

    def evaluate_canonical_store(
        self,
        request: CanonicalStoreAuthorityRequest,
    ) -> CanonicalStoreAuthorityDecision: ...


class CanonicalStoreAuthorityDeniedError(RuntimeError):
    """The exact canonical store operation was explicitly denied."""


class CanonicalStoreAuthorityUnavailableError(RuntimeError):
    """No valid deterministic authority decision was available for canonical store."""


def require_canonical_store_authority(
    evaluator: CanonicalStoreAuthorityEvaluator | None,
    request: CanonicalStoreAuthorityRequest,
) -> CanonicalStoreAuthorityDecision:
    if evaluator is None:
        raise CanonicalStoreAuthorityUnavailableError(
            "canonical store authority is not configured"
        )
    try:
        decision = evaluator.evaluate_canonical_store(request)
    except CanonicalStoreAuthorityDeniedError:
        raise
    except CanonicalStoreAuthorityUnavailableError:
        raise
    except Exception as exc:
        raise CanonicalStoreAuthorityUnavailableError(
            "canonical store authority evaluation failed"
        ) from exc
    if not isinstance(decision, CanonicalStoreAuthorityDecision):
        raise CanonicalStoreAuthorityUnavailableError(
            "canonical store authority returned an invalid decision"
        )
    if not decision.allowed:
        raise CanonicalStoreAuthorityDeniedError(
            "canonical store operation is not authorized"
        )
    return decision
