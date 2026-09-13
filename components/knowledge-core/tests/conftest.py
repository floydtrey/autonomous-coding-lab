"""Shared pytest-only Authority fixture for existing KC API qualification tests.

Production `create_app()` fails closed when no retrieval evaluator is supplied. The
pre-existing API qualification corpus predates that seam, so pytest injects an
explicit deterministic allow evaluator unless a test passes its own evaluator
(including explicit `None`). New Authority-boundary tests exercise deny/unavailable
behavior directly rather than inheriting this compatibility default.
"""

from functools import wraps

import knowledge_core.api.app as app_module
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityDecision,
    RetrievalAuthorityRequest,
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


_TEST_RETRIEVAL_AUTHORITY = _PytestRetrievalAuthority()
_PRODUCTION_CREATE_APP = app_module.create_app


@wraps(_PRODUCTION_CREATE_APP)
def _create_app_with_explicit_test_authority(*args, **kwargs):
    kwargs.setdefault(
        "retrieval_authority_evaluator",
        _TEST_RETRIEVAL_AUTHORITY,
    )
    return _PRODUCTION_CREATE_APP(*args, **kwargs)


app_module.create_app = _create_app_with_explicit_test_authority
