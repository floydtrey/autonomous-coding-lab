"""Shared pytest-only Authority fixtures for existing KC API qualification tests.

Production `create_app()` fails closed when required Authority evaluators are absent.
The pre-existing API qualification corpus predates the retrieval and Task 6G exact
canonical-store seams, so pytest injects explicit deterministic allow evaluators
unless a test passes its own evaluator (including explicit `None`). New boundary
tests exercise deny/unavailable behavior directly rather than inheriting these
compatibility defaults.
"""

from functools import wraps

import knowledge_core.api.app as app_module
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityDecision,
    RetrievalAuthorityRequest,
)
from knowledge_core.authority.store import (
    CanonicalStoreAuthorityDecision,
    CanonicalStoreAuthorityRequest,
)


class _PytestRetrievalAuthority:
    def evaluate_retrieval(
        self,
        request: RetrievalAuthorityRequest,
    ) -> RetrievalAuthorityDecision:
        return RetrievalAuthorityDecision(
            allowed=True,
            decision_ref=f"pytest:{request.caller_principal_ref}",
            reason_code="pytest-existing-api-qualification",
        )


class _PytestCanonicalStoreAuthority:
    def evaluate_canonical_store(
        self,
        request: CanonicalStoreAuthorityRequest,
    ) -> CanonicalStoreAuthorityDecision:
        return CanonicalStoreAuthorityDecision(
            allowed=True,
            decision_ref=f"pytest-store:{request.operation_id}",
            reason_code="pytest-existing-store-qualification",
        )


_TEST_RETRIEVAL_AUTHORITY = _PytestRetrievalAuthority()
_TEST_CANONICAL_STORE_AUTHORITY = _PytestCanonicalStoreAuthority()
_PRODUCTION_CREATE_APP = app_module.create_app


@wraps(_PRODUCTION_CREATE_APP)
def _create_app_with_explicit_test_authority(*args, **kwargs):
    kwargs.setdefault(
        "retrieval_authority_evaluator",
        _TEST_RETRIEVAL_AUTHORITY,
    )
    kwargs.setdefault(
        "canonical_store_authority_evaluator",
        _TEST_CANONICAL_STORE_AUTHORITY,
    )
    return _PRODUCTION_CREATE_APP(*args, **kwargs)


app_module.create_app = _create_app_with_explicit_test_authority
