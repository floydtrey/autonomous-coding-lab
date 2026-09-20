from __future__ import annotations

from hashlib import sha256

from fastapi import Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from knowledge_core.api._base_app import SessionFactory, create_app as _create_base_app
from knowledge_core.api.bootstrap_admission import (
    BootstrapAdmission,
    bootstrap_principal_dependency,
)
from knowledge_core.api.bootstrap_contract import BootstrapOperation
from knowledge_core.api.consumer_admission import (
    ConsumerAdmission,
    ConsumerPrincipalContext,
    consumer_principal_dependency,
)
from knowledge_core.api.consumer_schemas import (
    KnowledgeGetSourceRequest,
    KnowledgeGetSourceResponse,
    KnowledgeStatusResponse,
    source_response_from_domain,
    status_response_from_domain,
)
from knowledge_core.api.memory_candidate_schemas import (
    MemoryCandidateProposalRequest,
    MemoryCandidateProposalResponse,
)
from knowledge_core.api.retrieval_schemas import (
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    retrieval_response_from_domain,
)
from knowledge_core.api.store_schemas import KnowledgeStoreRequest, KnowledgeStoreResponse
from knowledge_core.api.unified_retrieval_schemas import (
    UnifiedRetrievalSearchResponse,
    unified_retrieval_response_from_domain,
)
from knowledge_core.application.authorization import (
    AuthorizationDeniedError,
    AuthorizationKernel,
)
from knowledge_core.application.consumer_read import ConsumerReadKnowledgeKernel
from knowledge_core.application.direct_note_store import (
    DirectNoteStoreKnowledgeKernel,
    direct_note_operation_id,
)
from knowledge_core.application.graph_readiness import (
    disabled_graph_readiness,
    inspect_source_neutral_graph_readiness,
    unavailable_graph_readiness,
)
from knowledge_core.application.memory_candidates import (
    MemoryCandidateKnowledgeKernel,
    memory_candidate_operation_id,
)
from knowledge_core.application.source_neutral_graph import (
    SourceNeutralGraphProjectionKnowledgeKernel,
)
from knowledge_core.application.unified_retrieval import (
    UnifiedGraphSearchBinding,
    UnifiedRetrievalCoordinator,
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
from knowledge_core.authority.store import (
    CanonicalStoreAuthorityDeniedError,
    CanonicalStoreAuthorityEvaluator,
    CanonicalStoreAuthorityRequest,
    CanonicalStoreAuthorityUnavailableError,
    require_canonical_store_authority,
)
from knowledge_core.domain.authorization import KCOperation
from knowledge_core.domain.principals import PrincipalType
from knowledge_core.domain.retrieval import KnowledgeSourceUnavailableError


_RETRIEVAL_PATH = "/v1/retrieval/search"
_STORE_PATH = "/v1/kc/store"
_MEMORY_CANDIDATE_PATH = "/v1/kc/memory-candidates"
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


def _remove_legacy_v1_routes(app) -> None:
    """Do not publish the broad kernel API on the hardened consumer service."""

    retained = []
    for route in app.router.routes:
        path = getattr(route, "path", None)
        if isinstance(path, str) and path.startswith("/v1/"):
            continue
        retained.append(route)
    app.router.routes[:] = retained
    app.openapi_schema = None


def create_app(
    *,
    session_factory: SessionFactory,
    artifact_store: LocalArtifactStore,
    retrieval_authority_evaluator: RetrievalAuthorityEvaluator | None = None,
    canonical_store_authority_evaluator: CanonicalStoreAuthorityEvaluator | None = None,
    bootstrap_admission: BootstrapAdmission | None = None,
    consumer_admission: ConsumerAdmission | None = None,
    unified_graph_search_binding: UnifiedGraphSearchBinding | None = None,
):
    """Compose the KC semantic API with bounded trusted-host seams.

    Retrieval retains the fail-closed Authority seam. When a bootstrap admission
    contract is explicitly supplied by the host, the Usable V1 ``kc_store``,
    ``kc_search``, ``kc_get_source`` and ``kc_status`` front doors are exposed and
    map successful shared-key admission to ``local_owner``. Task 6G also exposes a
    separate non-canonical memory-candidate proposal route. Existing low-level routes
    are not placed behind the bootstrap key.

    Bootstrap authentication alone is not sufficient for a canonical ``kc_store``.
    Task 6G requires a second deterministic trusted-host decision bound to the exact
    operation ID, project, source identity, source event time and content digest.
    This prevents a worker from silently treating an autonomous observation as an
    explicit trusted write.

    ``unified_graph_search_binding`` is optional and query-only. Supplying it never
    builds or synchronizes a graph. Its caller principal must exactly match the fixed
    bootstrap principal so graph Authority cannot substitute a second identity for
    the authenticated ``kc_search`` request. The same binding may be inspected by
    ``kc_status`` for durable graph readiness; status never calls the graph provider.
    """

    if unified_graph_search_binding is not None:
        if bootstrap_admission is None:
            raise ValueError(
                "unified graph search binding requires bootstrap admission"
            )
        if (
            unified_graph_search_binding.caller_principal_ref
            != bootstrap_admission.contract.principal_ref
        ):
            raise ValueError(
                "unified graph search binding principal must match bootstrap principal"
            )

    app = _create_base_app(
        session_factory=session_factory,
        artifact_store=artifact_store,
    )
    _remove_base_retrieval_route(app)
    if consumer_admission is not None:
        _remove_legacy_v1_routes(app)

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

    def get_memory_candidate_kernel():
        session: Session = session_factory()
        try:
            yield MemoryCandidateKnowledgeKernel(session)
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

    @app.exception_handler(CanonicalStoreAuthorityDeniedError)
    async def canonical_store_authority_denied_handler(
        _request: Request,
        _exc: CanonicalStoreAuthorityDeniedError,
    ):
        return JSONResponse(
            status_code=403,
            content={
                "detail": "canonical store is not authorized",
                "error_code": "CANONICAL_STORE_NOT_AUTHORIZED",
            },
        )

    @app.exception_handler(CanonicalStoreAuthorityUnavailableError)
    async def canonical_store_authority_unavailable_handler(
        _request: Request,
        _exc: CanonicalStoreAuthorityUnavailableError,
    ):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "canonical store authority is unavailable",
                "error_code": "CANONICAL_STORE_AUTHORITY_UNAVAILABLE",
            },
        )

    @app.exception_handler(AuthorizationDeniedError)
    async def authorization_denied_handler(
        _request: Request,
        _exc: AuthorizationDeniedError,
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "operation is not authorized"},
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

    if consumer_admission is None:
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

    if bootstrap_admission is not None or consumer_admission is not None:
        if consumer_admission is not None:
            store_principal = consumer_principal_dependency(
                consumer_admission,
                operation=KCOperation.STORE,
            )
            memory_propose_principal = consumer_principal_dependency(
                consumer_admission,
                operation=KCOperation.MEMORY_PROPOSE,
            )
            search_principal = consumer_principal_dependency(
                consumer_admission,
                operation=KCOperation.SEARCH,
            )
            get_source_principal = consumer_principal_dependency(
                consumer_admission,
                operation=KCOperation.GET_SOURCE,
            )
            status_principal = consumer_principal_dependency(
                consumer_admission,
                operation=KCOperation.STATUS,
            )
        else:
            store_principal = bootstrap_principal_dependency(
                bootstrap_admission,
                operation=BootstrapOperation.STORE,
            )
            memory_propose_principal = bootstrap_principal_dependency(
                bootstrap_admission,
                operation=BootstrapOperation.MEMORY_PROPOSE,
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

        def _caller_ref(principal) -> str:
            if isinstance(principal, ConsumerPrincipalContext):
                return principal.caller_principal_ref
            return str(principal)

        @app.post(
            _STORE_PATH,
            response_model=KnowledgeStoreResponse,
            status_code=201,
        )
        def knowledge_store(
            body: KnowledgeStoreRequest,
            idempotency_key: str = Header(alias="Idempotency-Key"),
            kernel: DirectNoteStoreKnowledgeKernel = Depends(get_store_kernel),
            principal=Depends(store_principal),
        ) -> KnowledgeStoreResponse:
            caller_ref = _caller_ref(principal)
            project_scope = None
            bounded_service_write = (
                isinstance(principal, ConsumerPrincipalContext)
                and principal.principal_type is not PrincipalType.OWNER
            )
            if bounded_service_write:
                project_scope = consumer_admission.require_scope_access(
                    context=principal,
                    operation=KCOperation.STORE,
                )
                if body.project != project_scope.scope_key:
                    raise HTTPException(
                        status_code=409,
                        detail="store project must match the authenticated active project scope",
                    )
            existing_resource_ref = None
            if bounded_service_write:
                existing_resource_ref = kernel.existing_note_resource_ref(
                    caller_principal_ref=caller_ref,
                    source_id=body.source_id,
                )
                if existing_resource_ref is not None:
                    AuthorizationKernel(
                        kernel.session
                    ).ensure_scoped_policy_for_authorized_store(
                        actor_principal_ref=principal.principal_ref,
                        resource_ref=existing_resource_ref,
                        scope_ref=project_scope.scope_ref,
                    )

            try:
                operation_id = direct_note_operation_id(
                    principal_ref=caller_ref,
                    idempotency_key=idempotency_key,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if not isinstance(principal, ConsumerPrincipalContext):
                require_canonical_store_authority(
                    canonical_store_authority_evaluator,
                    CanonicalStoreAuthorityRequest(
                        caller_principal_ref=caller_ref,
                        operation_id=operation_id,
                        project_key=body.project,
                        content_sha256=sha256(body.content.encode("utf-8")).hexdigest(),
                        source_id=body.source_id,
                        source_event_time=body.source_event_time,
                    ),
                )
            canonical = kernel.store_note_operation(
                operation_id=operation_id,
                caller_principal_ref=caller_ref,
                content=body.content,
                project_key=body.project,
                source_id=body.source_id,
                source_event_time=body.source_event_time,
            )
            if bounded_service_write and existing_resource_ref is None:
                AuthorizationKernel(
                    kernel.session
                ).ensure_scoped_policy_for_authorized_store(
                    actor_principal_ref=principal.principal_ref,
                    resource_ref=canonical.resource_ref,
                    scope_ref=project_scope.scope_ref,
                )
                kernel.session.commit()
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
            _MEMORY_CANDIDATE_PATH,
            response_model=MemoryCandidateProposalResponse,
            status_code=202,
        )
        def memory_candidate_propose(
            body: MemoryCandidateProposalRequest,
            idempotency_key: str = Header(alias="Idempotency-Key"),
            kernel: MemoryCandidateKnowledgeKernel = Depends(
                get_memory_candidate_kernel
            ),
            principal=Depends(memory_propose_principal),
        ) -> MemoryCandidateProposalResponse:
            caller_ref = _caller_ref(principal)
            bounded_service_proposal = (
                isinstance(principal, ConsumerPrincipalContext)
                and principal.principal_type is not PrincipalType.OWNER
            )
            if bounded_service_proposal:
                project_scope = consumer_admission.require_scope_access(
                    context=principal,
                    operation=KCOperation.MEMORY_PROPOSE,
                )
                if body.project != project_scope.scope_key:
                    raise HTTPException(
                        status_code=409,
                        detail="memory project must match the authenticated active project scope",
                    )
                if body.proposer_ref != principal.principal_code:
                    raise HTTPException(
                        status_code=409,
                        detail="proposer_ref must match the authenticated principal code",
                    )
            try:
                operation_id = memory_candidate_operation_id(
                    principal_ref=caller_ref,
                    idempotency_key=idempotency_key,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            candidate = kernel.propose_candidate(
                operation_id=operation_id,
                caller_principal_ref=caller_ref,
                proposer_ref=body.proposer_ref,
                project_key=body.project,
                content=body.content,
                source_event_time=body.source_event_time,
            )
            return MemoryCandidateProposalResponse(
                candidate_id=candidate.candidate_id,
                proposer_ref=candidate.proposer_ref,
                project=candidate.project_key,
                content_sha256=candidate.content_sha256,
                proposed_at=candidate.proposed_at,
            )

        @app.post(
            _KC_SEARCH_PATH,
            response_model=UnifiedRetrievalSearchResponse,
        )
        async def knowledge_search(
            body: RetrievalSearchRequest,
            kernel: ConsumerReadKnowledgeKernel = Depends(get_retrieval_kernel),
            principal=Depends(search_principal),
        ) -> UnifiedRetrievalSearchResponse:
            caller_ref = _caller_ref(principal)
            if retrieval_authority_evaluator is not None:
                require_retrieval_authority(
                    retrieval_authority_evaluator,
                    RetrievalAuthorityRequest(
                        caller_principal_ref=caller_ref,
                        operation=RetrievalAuthorityOperation.SEARCH_TEXT,
                        limit=body.limit,
                        include_superseded=body.include_superseded,
                    ),
                )

            authorized_resource_refs_statement = None
            graph_binding_for_request = unified_graph_search_binding
            if isinstance(principal, ConsumerPrincipalContext):
                authorized_resource_refs_statement = AuthorizationKernel(
                    kernel.session
                ).authorized_resource_refs_statement(
                    principal_ref=principal.principal_ref,
                    operation=KCOperation.SEARCH,
                    scope_ref=principal.scope_ref,
                )
                if not principal.is_bootstrap_owner:
                    # KC-D will bind graph authority per authenticated principal.
                    # Until then, do not reuse the historical owner graph binding.
                    graph_binding_for_request = None

            graph_kernel = SourceNeutralGraphProjectionKnowledgeKernel(
                kernel.session,
                artifact_store=artifact_store,
            )
            coordinator = UnifiedRetrievalCoordinator(
                lexical_kernel=kernel,
                graph_kernel=graph_kernel,
                graph_binding=graph_binding_for_request,
            )
            result = await coordinator.search(
                query=body.query,
                limit=body.limit,
                include_superseded=body.include_superseded,
                authorized_resource_refs_statement=authorized_resource_refs_statement,
            )
            return unified_retrieval_response_from_domain(result)

        @app.post(
            _KC_GET_SOURCE_PATH,
            response_model=KnowledgeGetSourceResponse,
        )
        def knowledge_get_source(
            body: KnowledgeGetSourceRequest,
            kernel: ConsumerReadKnowledgeKernel = Depends(get_retrieval_kernel),
            principal=Depends(get_source_principal),
        ) -> KnowledgeGetSourceResponse:
            if isinstance(principal, ConsumerPrincipalContext):
                resource_ref = kernel.current_source_resource_ref(
                    resource_version_ref=body.resource_version_ref,
                )
                decision = AuthorizationKernel(kernel.session).evaluate(
                    principal_ref=principal.principal_ref,
                    operation=KCOperation.GET_SOURCE,
                    scope_ref=principal.scope_ref,
                    resource_ref=resource_ref,
                )
                if not decision.allowed:
                    raise KnowledgeSourceUnavailableError(
                        "knowledge source is unavailable"
                    )
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
            _principal=Depends(status_principal),
        ) -> KnowledgeStatusResponse:
            lexical_status = kernel.retrieval_status()
            binding = unified_graph_search_binding
            if binding is None:
                graph_status = disabled_graph_readiness()
            else:
                graph_kernel = SourceNeutralGraphProjectionKnowledgeKernel(
                    kernel.session,
                    artifact_store=artifact_store,
                )
                try:
                    graph_status = inspect_source_neutral_graph_readiness(
                        kernel=graph_kernel,
                        adapter=binding.adapter,
                        namespace_key=binding.namespace_key,
                        scope_key=binding.scope_key,
                    )
                except Exception:
                    graph_status = unavailable_graph_readiness(
                        namespace_key=binding.namespace_key,
                        scope_key=binding.scope_key,
                    )
            return status_response_from_domain(
                lexical_status,
                graph=graph_status,
            )

    return app
