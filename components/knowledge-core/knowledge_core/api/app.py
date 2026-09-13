from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from knowledge_core.api._base_app import SessionFactory, create_app as _create_base_app
from knowledge_core.api.retrieval_schemas import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    retrieval_response_from_domain,
)
from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityDeniedError,
    RetrievalAuthorityEvaluator,
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
    RetrievalAuthorityUnavailableError,
    require_retrieval_authority,
)


_RETRIEVAL_PATH = "/v1/retrieval/search"


def _remove_base_retrieval_route(app) -> None:
    """Remove the pre-Authority retrieval route before publishing the guarded one."""

    retained = []
    removed = 0
    for route in app.router.routes:
        methods = getattr(route, "methods", None) or set()
        if getattr(route, "path", None) == _RETRIEVAL_PATH and "POST" in methods:
            removed += 1
            continue
        retained.append(route)
    if removed != 1:
        raise RuntimeError(
            "Knowledge Core expected exactly one base retrieval route before Authority composition"
        )
    app.router.routes[:] = retained
    app.openapi_schema = None


def create_app(
    *,
    session_factory: SessionFactory,
    artifact_store: LocalArtifactStore,
    retrieval_authority_evaluator: RetrievalAuthorityEvaluator | None = None,
):
    """Compose the KC semantic API with a fail-closed retrieval Authority seam.

    Other accepted semantic routes remain unchanged. Retrieval is replaced so the
    caller identity is deterministically evaluated before any protected search
    executes. The evaluator is intentionally injected by the trusted host and can
    later be backed by the separate Authority service accepted by KC-D004.
    """

    app = _create_base_app(
        session_factory=session_factory,
        artifact_store=artifact_store,
    )
    _remove_base_retrieval_route(app)

    def get_retrieval_kernel():
        session: Session = session_factory()
        try:
            yield RetrievalServiceKnowledgeKernel(
                session,
                artifact_store=artifact_store,
            )
        finally:
            session.close()

    def caller_context(
        x_knowledge_caller: str | None = Header(
            default=None,
            alias="X-Knowledge-Caller",
        ),
    ) -> str:
        if x_knowledge_caller is None or not x_knowledge_caller.strip():
            raise HTTPException(
                status_code=400,
                detail="X-Knowledge-Caller is required for v1 semantic operations",
            )
        return x_knowledge_caller.strip()

    @app.exception_handler(RetrievalAuthorityDeniedError)
    async def retrieval_authority_denied_handler(
        _request: Request,
        _exc: RetrievalAuthorityDeniedError,
    ):
        # Match the existing serving-fence non-disclosure behavior.
        return JSONResponse(
            status_code=404,
            content={"detail": "knowledge item is unavailable"},
        )

    @app.exception_handler(RetrievalAuthorityUnavailableError)
    async def retrieval_authority_unavailable_handler(
        _request: Request,
        _exc: RetrievalAuthorityUnavailableError,
    ):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "retrieval authority is unavailable",
                "error_code": "RETRIEVAL_AUTHORITY_UNAVAILABLE",
            },
        )

    @app.post(
        _RETRIEVAL_PATH,
        response_model=RetrievalSearchResponse,
    )
    def retrieval_search(
        body: RetrievalSearchRequest,
        kernel: RetrievalServiceKnowledgeKernel = Depends(get_retrieval_kernel),
        caller: str = Depends(caller_context),
    ) -> RetrievalSearchResponse:
        require_retrieval_authority(
            retrieval_authority_evaluator,
            RetrievalAuthorityRequest(
                caller_principal_ref=caller,
                operation=RetrievalAuthorityOperation.SEARCH_TEXT,
                limit=body.limit,
                include_superseded=body.include_superseded,
            ),
        )
        return retrieval_response_from_domain(
            kernel.search_text(
                query=body.query,
                limit=body.limit,
                include_superseded=body.include_superseded,
            )
        )

    return app
