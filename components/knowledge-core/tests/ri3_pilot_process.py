from __future__ import annotations

import _ri3_pilot_process_base as phase

from knowledge_core.api.repository_import_app import (
    create_repository_import_app as _create_repository_import_app,
)
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityDecision,
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
)


_EXPECTED_CALLER = "ri3-persistent-pilot"


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
            decision_ref="ri3-pilot:retrieval-search",
            reason_code=(
                "qualification-caller-and-operation-match"
                if allowed
                else "qualification-boundary-mismatch"
            ),
        )


def _qualified_repository_import_app(*args, **kwargs):
    kwargs.setdefault(
        "retrieval_authority_evaluator",
        _QualificationRetrievalAuthority(),
    )
    return _create_repository_import_app(*args, **kwargs)


phase.create_repository_import_app = _qualified_repository_import_app


if __name__ == "__main__":
    raise SystemExit(phase.main())
