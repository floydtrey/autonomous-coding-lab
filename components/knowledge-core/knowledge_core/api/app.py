from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from knowledge_core.api._base_app import SessionFactory, create_app as _create_base_app
from knowledge_core.api.bootstrap_admission import (
    BootstrapAdmission,
    bootstrap_principal_dependency,
)
from knowledge_core.api.bootstrap_contract import BootstrapOperation
from knowledge_core.api.consumer_schemas import (
    KnowledgeGetSourceRequest,
    KnowledgeGetSourceResponse,
    KnowledgeStatusResponse,
    source_response_from_domain,
    status_response_from_domain,
)
from knowledge_core.api.retrieval_schemas import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    retrieval_response_from_domain,
)
from knowledge_core.api.store_schemas import KnowledgeStoreRequest, KnowledgeStoreResponse
from knowledge_core.application.consumer_read import ConsumerReadKnowledgeKernel
from knowledge_core.application.direct_note_store import (
    DirectNoteStoreKnowledgeKernel,
    direct_note_operation_id,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityDeniedError,
    RetrievalAuthorityEvaluator,
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
    RetrievalAuthorityUnavailableError,
    require_retrieval_authority,
)
from knowledge_core.domain.retrieval import KnowledgeSourceUnavailableError


_RETRIEVAL_PATH = "/v1/retrieval/search"
_STORE_PATH = "/v1/kc/store"
_KC_SEARCH_PATH = "/v1/kc/search"
_KC_GET_SOURCE_PATH = "/v1/kc/get-source"
_KC_STATUS_PATH = "/v1/kc/status"


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
    bootstrap_admission: BootstrapAdmission | None = None,
):
    """Compose the KC semantic API with bounded trusted-host seams.

    Retrieval retains the fail-closed Authority seam. When a bootstrap admission
    contract is explicitly supplied by the host, the Usable V1 ``kc_store``,
    ``kc_search``, ``kc_get_source`` and ``kc_status`` front doors are exposed and
    map successful shared-key admission to ``local_owner``. Existing low-level routes
    are not placed behind the bootstrap key.
    """

    app = _create_base_app(
        session_factory=session_factory,
        artifact_store=artifact_store,
    )
    _remove_base_retrieval_route(app)

    def get_retrieval_kernel():
        session: Session = session_factory()
        try:
            yield ConsumerReadKnowledgeKernel(
                session,
                artifact_store=artifact_store,
            )
        finally:
            session.close()

    def get_store_kernel():
        session: Session = session_factory()
        try:
            yield DirectNoteStoreKnowledgeKernel(
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

    @app.exception_handler(KnowledgeSourceUnavailableError)
    async def knowledge_source_unavailable_handler(
        _request: Request,
        _exc: KnowledgeSourceUnavailableError,
    ):
        return JSONResponse(
            status_code=404,
            content={"detail": "knowledge item is unavailable"},
        )

    @app.post(
        _RETRIEVAL_PATH,
        response_model=RetrievalSearchResponse,
    )
    def retrieval_search(
        body: RetrievalSearchRequest,
        kernel: ConsumerReadKnowledgeKernel = Depends(get_retrieval_kernel),
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

    if bootstrap_admission is not None:
        store_principal = bootstrap_principal_dependency(
            bootstrap_admission,
            operation=BootstrapOperation.STORE,
        )
        search_principal = bootstrap_principal_dependency(
            bootstrap_admission,
            operation=BootstrapOperation.SEARCH,
        )
        get_source_principal = bootstrap_principal_dependency(
            bootstrap_admission,
            operation=BootstrapOperation.GET_SOURCE,
        )
        status_principal = bootstrap_principal_dependency(
            bootstrap_admission,
            operation=BootstrapOperation.STATUS,
        )

        @app.post(
            _STORE_PATH,
            response_model=KnowledgeStoreResponse,
            status_code=201,
        )
        def knowledge_store(
            body: KnowledgeStoreRequest,
            idempotency_key: str = Header(alias="Idempotency-Key"),
            kernel: DirectNoteStoreKnowledgeKernel = Depends(get_store_kernel),
            principal: str = Depends(store_principal),
        ) -> KnowledgeStoreResponse:
            try:
                operation_id = direct_note_operation_id(
                    principal_ref=principal,
                    idempotency_key=idempotency_key,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            canonical = kernel.store_note_operation(
                operation_id=operation_id,
                caller_principal_ref=principal,
                content=body.content,
                project_key=body.project,
                source_id=body.source_id,
                source_event_time=body.source_event_time,
            )
            publication = kernel.publish_note_text(canonical)
            return KnowledgeStoreResponse(
                source_id=canonical.source_id,
                resource_id=canonical.resource_ref,
                version_id=canonical.resource_version_ref,
                sha256=canonical.content_sha256,
                text_state=publication.text_state,
                text_generation_id=publication.generation_id,
                text_snapshot_digest=publication.snapshot_digest,
                text_error_code=publication.error_code,
            )

        @app.post(
            _KC_SEARCH_PATH,
            response_model=RetrievalSearchResponse,
        )
        def knowledge_search(
            body: RetrievalSearchRequest,
            kernel: ConsumerReadKnowledgeKernel = Depends(get_retrieval_kernel),
            principal: str = Depends(search_principal),
        ) -> RetrievalSearchResponse:
            # Bootstrap admission is the bounded Usable V1 local-read authority. If a
            # separate retrieval Authority evaluator is supplied by the trusted host,
            # it remains an additional fail-closed policy layer for search.
            if retrieval_authority_evaluator is not None:
                require_retrieval_authority(
                    retrieval_authority_evaluator,
                    RetrievalAuthorityRequest(
                        caller_principal_ref=principal,
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

        @app.post(
            _KC_GET_SOURCE_PATH,
            response_model=KnowledgeGetSourceResponse,
        )
        def knowledge_get_source(
            body: KnowledgeGetSourceRequest,
            kernel: ConsumerReadKnowledgeKernel = Depends(get_retrieval_kernel),
            _principal: str = Depends(get_source_principal),
        ) -> KnowledgeGetSourceResponse:
            return source_response_from_domain(
                kernel.read_current_source(
                    resource_version_ref=body.resource_version_ref,
                )
            )

        @app.get(
            _KC_STATUS_PATH,
            response_model=KnowledgeStatusResponse,
        )
        def knowledge_status(
            kernel: ConsumerReadKnowledgeKernel = Depends(get_retrieval_kernel),
            _principal: str = Depends(status_principal),
        ) -> KnowledgeStatusResponse:
            return status_response_from_domain(kernel.retrieval_status())

    return app
