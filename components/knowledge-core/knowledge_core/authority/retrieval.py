from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class RetrievalAuthorityOperation(StrEnum):
    """Bounded retrieval operations that require deterministic admission."""

    SEARCH_TEXT = "retrieval.search_text"
    SEARCH_GRAPH = "retrieval.search_graph"


@dataclass(frozen=True)
class RetrievalAuthorityRequest:
    """Provider-neutral operation request evaluated before retrieval executes."""

    caller_principal_ref: str
    operation: RetrievalAuthorityOperation
    limit: int
    include_superseded: bool
    namespace_key: str | None = None
    scope_key: str | None = None

    def __post_init__(self) -> None:
        if not self.caller_principal_ref.strip():
            raise ValueError("caller_principal_ref must be non-empty")
        if self.limit < 1 or self.limit > 50:
            raise ValueError("retrieval limit must be between 1 and 50")
        for field_name, value in (
            ("namespace_key", self.namespace_key),
            ("scope_key", self.scope_key),
        ):
            if value is not None and not value.strip():
                raise ValueError(f"{field_name} must be null or non-empty")
        if self.operation is RetrievalAuthorityOperation.SEARCH_GRAPH:
            if self.namespace_key is None or self.scope_key is None:
                raise ValueError(
                    "graph retrieval authority requires explicit namespace_key and scope_key"
                )


@dataclass(frozen=True)
class RetrievalAuthorityDecision:
    """Deterministic Authority response without embedding policy in KC."""

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


class RetrievalAuthorityEvaluator(Protocol):
    """Replaceable seam implemented later by the separate Authority service."""

    def evaluate_retrieval(
        self,
        request: RetrievalAuthorityRequest,
    ) -> RetrievalAuthorityDecision: ...


class RetrievalAuthorityDeniedError(RuntimeError):
    """Authority evaluated the exact retrieval operation and denied it."""


class RetrievalAuthorityUnavailableError(RuntimeError):
    """Authority could not produce a valid deterministic decision."""


def require_retrieval_authority(
    evaluator: RetrievalAuthorityEvaluator | None,
    request: RetrievalAuthorityRequest,
) -> RetrievalAuthorityDecision:
    """Fail closed unless an evaluator returns an explicit allow decision."""

    if evaluator is None:
        raise RetrievalAuthorityUnavailableError("retrieval authority is not configured")

    try:
        decision = evaluator.evaluate_retrieval(request)
    except RetrievalAuthorityDeniedError:
        raise
    except RetrievalAuthorityUnavailableError:
        raise
    except Exception as exc:
        raise RetrievalAuthorityUnavailableError(
            "retrieval authority evaluation failed"
        ) from exc

    if not isinstance(decision, RetrievalAuthorityDecision):
        raise RetrievalAuthorityUnavailableError(
            "retrieval authority returned an invalid decision"
        )
    if not decision.allowed:
        raise RetrievalAuthorityDeniedError("retrieval operation is not authorized")
    return decision
