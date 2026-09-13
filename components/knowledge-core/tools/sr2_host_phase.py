from __future__ import annotations

import _sr2_host_phase_base as phase

from knowledge_core.api.app import create_app as _create_app
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityDecision,
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
)


_EXPECTED_CALLER = "sr2-host-qualification"


class _QualificationRetrievalAuthority:
    def evaluate_retrieval(
        self,
        request: RetrievalAuthorityRequest,
    ) -> RetrievalAuthorityDecision:
        allowed = (
            request.caller_principal_ref == _EXPECTED_CALLER
            and request.operation is RetrievalAuthorityOperation.SEARCH_TEXT
        )
        return RetrievalAuthorityDecision(
            allowed=allowed,
            decision_ref="sr2-host:retrieval-search",
            reason_code=(
                "qualification-caller-and-operation-match"
                if allowed
                else "qualification-boundary-mismatch"
            ),
        )


def _qualified_app(*args, **kwargs):
    kwargs.setdefault(
        "retrieval_authority_evaluator",
        _QualificationRetrievalAuthority(),
    )
    return _create_app(*args, **kwargs)


phase.create_app = _qualified_app


if __name__ == "__main__":
    raise SystemExit(phase.main())
