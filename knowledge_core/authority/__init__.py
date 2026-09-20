"""Deterministic Authority boundary contracts for Knowledge Core."""

from knowledge_core.authority.retrieval import (
    RetrievalAuthorityDecision,
    RetrievalAuthorityDeniedError,
    RetrievalAuthorityEvaluator,
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
    RetrievalAuthorityUnavailableError,
    require_retrieval_authority,
)

__all__ = [
    "RetrievalAuthorityDecision",
    "RetrievalAuthorityDeniedError",
    "RetrievalAuthorityEvaluator",
    "RetrievalAuthorityOperation",
    "RetrievalAuthorityRequest",
    "RetrievalAuthorityUnavailableError",
    "require_retrieval_authority",
]
