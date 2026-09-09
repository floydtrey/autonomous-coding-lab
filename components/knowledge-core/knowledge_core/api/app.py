from __future__ import annotations

from datetime import datetime
from typing import Callable
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from knowledge_core.api.resource_schemas import (
    EvidenceLinkRequest,
    EvidenceTraceResponse,
    ImpactTraceResponse,
    ResourceCreateRequest,
    ResourceIngestRequest,
    ResourceResponse,
    ResourceVersionResponse,
)
from knowledge_core.api.schemas import (
    AssertionCorrectRequest,
    AssertionCreateRequest,
    AssertionResponse,
    BitemporalAssertionResponse,
    EntityCreateRequest,
    EntityResponse,
    HealthResponse,
    IdentityMemberResponse,
    IdentityMergeRequest,
    IdentityReplaceRequest,
    IdentityResolutionResponse,
    IdentityReverseRequest,
    IdentityTransitionResponse,
    StatusResponse,
    TransitionResponse,
    TransitionReverseRequest,
    ValueResponse,
)
from knowledge_core.application.resource_service import ResourceServiceKnowledgeKernel
from knowledge_core.application.service import ServiceKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import AssertionSnapshot, KnowledgeInvariantError
from knowledge_core.domain.deletion import KnowledgeRestrictedError
from knowledge_core.domain.identity import (
    IdentityResolutionSnapshot,
    IdentityTransitionSnapshot,
)
from knowledge_core.domain.operations import (
    OperationFailedError,
    OperationInProgressError,
    OperationReuseError,
    StaleWriteError,
)
from knowledge_core.domain.resources import EvidenceTrace, ImpactTrace, ResourceVersionSnapshot
from knowledge_core.domain.temporal import BitemporalAssertion


SessionFactory = Callable[[], Session]


def _assertion_response(item: AssertionSnapshot) -> AssertionResponse:
    return AssertionResponse(
        assertion_ref=item.assertion_ref,
        subject_ref=item.subject_ref,
        predicate_revision_ref=item.predicate_revision_ref,
        profile_revision_ref=item.profile_revision_ref,
        value_state=item.value_state.value,
        epistemic_basis=item.epistemic_basis.value,
        value=ValueResponse(kind=item.value.kind, value=item.value.value),
        created_revision_id=item.created_revision_id,
    )


def _bitemporal_response(item: BitemporalAssertion) -> BitemporalAssertionResponse:
    return BitemporalAssertionResponse(
        assertion=_assertion_response(item.assertion),
        valid_from=item.valid_from,
        valid_to=item.valid_to,
        world_time_precision=item.world_time_precision,
        recorded_at=item.recorded_at,
    )


def _transition_response(item) -> TransitionResponse:
    return TransitionResponse(
        transition_ref=item.transition_ref,
        transition_type=item.transition_type.value,
        source_assertion_ref=item.source_assertion_ref,
        replacement_assertion_ref=item.replacement_assertion_ref,
        reverses_transition_ref=item.reverses_transition_ref,
        created_revision_id=item.created_revision_id,
    )


def _identity_transition_response(
    item: IdentityTransitionSnapshot,
) -> IdentityTransitionResponse:
    return IdentityTransitionResponse(
        transition_ref=item.transition_ref,
        transition_type=item.transition_type.value,
        reverses_transition_ref=item.reverses_transition_ref,
        members=[
            IdentityMemberResponse(
                entity_ref=member.entity_ref,
                member_role=member.member_role.value,
                ordinal=member.ordinal,
            )
            for member in item.members
        ],
        created_revision_id=item.created_revision_id,
    )


def _identity_resolution_response(
    item: IdentityResolutionSnapshot,
) -> IdentityResolutionResponse:
    return IdentityResolutionResponse(
        entity_ref=item.entity_ref,
        resolution_group_id=item.resolution_group_id,
        representative_ref=item.representative_ref,
        member_refs=list(item.member_refs),
        source_transition_ref=item.source_transition_ref,
        source_revision_id=item.source_revision_id,
    )


def _resource_version_response(item: ResourceVersionSnapshot) -> ResourceVersionResponse:
    return ResourceVersionResponse(
        resource_version_ref=item.resource_version_ref,
        resource_ref=item.resource_ref,
        content_digest_algo=item.content_digest_algo,
        content_digest=item.content_digest,
        byte_size=item.byte_size,
        media_type=item.media_type,
        created_revision_id=item.created_revision_id,
    )


def _evidence_response(item: EvidenceTrace) -> EvidenceTraceResponse:
    return EvidenceTraceResponse(
        link_id=item.link_id,
        assertion_ref=item.assertion_ref,
        relation_revision_ref=item.relation_revision_ref,
        resource_version=_resource_version_response(item.resource_version),
        created_revision_id=item.created_revision_id,
    )


def _impact_response(item: ImpactTrace) -> ImpactTraceResponse:
    return ImpactTraceResponse(
        link_id=item.link_id,
        resource_version_ref=item.resource_version_ref,
        dependent_ref=item.dependent_ref,
        dependent_ref_kind=item.dependent_ref_kind,
        relation_revision_ref=item.relation_revision_ref,
        created_revision_id=item.created_revision_id,
    )


def create_app(
    *,
    session_factory: SessionFactory,
    artifact_store: LocalArtifactStore,
) -> FastAPI:
    app = FastAPI(
        title="Knowledge Core",
        version="1",
        docs_url="/docs",
        redoc_url=None,
    )

    def get_kernel():
        session = session_factory()
        try:
            yield ResourceServiceKnowledgeKernel(session, artifact_store=artifact_store)
        finally:
            session.close()

    def caller_context(
        x_knowledge_caller: str | None = Header(
            default=None, alias="X-Knowledge-Caller"
        ),
    ) -> str:
        if x_knowledge_caller is None or not x_knowledge_caller.strip():
            raise HTTPException(
                status_code=400,
                detail="X-Knowledge-Caller is required for v1 semantic operations",
            )
        return x_knowledge_caller.strip()

    @app.exception_handler(StaleWriteError)
    async def stale_write_handler(_request: Request, exc: StaleWriteError):
        return JSONResponse(
            status_code=409,
            content={
                "detail": str(exc),
                "error_code": "STALE_REVISION",
                "expected_revision": exc.expected_revision,
                "actual_revision": exc.actual_revision,
            },
        )

    async def operation_error_handler(_request: Request, exc: Exception):
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc), "error_code": exc.__class__.__name__},
        )

    for operation_error in (
        OperationReuseError,
        OperationInProgressError,
        OperationFailedError,
    ):
        app.add_exception_handler(operation_error, operation_error_handler)

    @app.exception_handler(KnowledgeRestrictedError)
    async def restricted_handler(_request: Request, _exc: KnowledgeRestrictedError):
        return JSONResponse(
            status_code=404,
            content={"detail": "knowledge item is unavailable"},
        )

    @app.exception_handler(KnowledgeInvariantError)
    async def invariant_handler(_request: Request, exc: KnowledgeInvariantError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "error_code": "KNOWLEDGE_INVARIANT"},
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/v1/status", response_model=StatusResponse)
    def status(
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        _caller: str = Depends(caller_context),
    ) -> StatusResponse:
        return StatusResponse(canonical_revision=kernel.current_revision())

    @app.post("/v1/entities", response_model=EntityResponse, status_code=201)
    def create_entity(
        body: EntityCreateRequest,
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        caller: str = Depends(caller_context),
    ) -> EntityResponse:
        entity_ref = kernel.create_entity_operation(
            operation_id=body.operation_id,
            kind_revision_ref=body.kind_revision_ref,
            caller_principal_ref=caller,
            expected_revision=body.expected_revision,
        )
        entity = kernel.read_entity_serving(entity_ref)
        return EntityResponse(
            entity_ref=entity.entity_ref,
            kind_revision_ref=entity.kind_revision_ref,
            created_revision_id=entity.created_revision_id,
        )

    @app.get("/v1/entities/{entity_ref}", response_model=EntityResponse)
    def read_entity(
        entity_ref: UUID,
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        _caller: str = Depends(caller_context),
    ) -> EntityResponse:
        entity = kernel.read_entity_serving(entity_ref)
        return EntityResponse(
            entity_ref=entity.entity_ref,
            kind_revision_ref=entity.kind_revision_ref,
            created_revision_id=entity.created_revision_id,
        )

    @app.post("/v1/assertions", response_model=AssertionResponse, status_code=201)
    def append_assertion(
        body: AssertionCreateRequest,
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        caller: str = Depends(caller_context),
    ) -> AssertionResponse:
        assertion_ref = kernel.append_assertion_operation(
            operation_id=body.operation_id,
            subject_ref=body.subject_ref,
            predicate_revision_ref=body.predicate_revision_ref,
            profile_revision_ref=body.profile_revision_ref,
            value=body.value.to_domain(),
            epistemic_basis=body.epistemic_basis,
            world_interval=(
                body.world_interval.to_domain() if body.world_interval else None
            ),
            expected_revision=body.expected_revision,
            caller_principal_ref=caller,
        )
        return _assertion_response(kernel.read_assertion_serving(assertion_ref))

    @app.get("/v1/assertions/{assertion_ref}", response_model=AssertionResponse)
    def read_assertion(
        assertion_ref: UUID,
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        _caller: str = Depends(caller_context),
    ) -> AssertionResponse:
        return _assertion_response(kernel.read_assertion_serving(assertion_ref))

    @app.post(
        "/v1/assertions/{assertion_ref}/correct",
        response_model=TransitionResponse,
    )
    def correct_assertion(
        assertion_ref: UUID,
        body: AssertionCorrectRequest,
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        caller: str = Depends(caller_context),
    ) -> TransitionResponse:
        item = kernel.correct_assertion_operation(
            operation_id=body.operation_id,
            expected_revision=body.expected_revision,
            source_assertion_ref=assertion_ref,
            replacement_value=body.replacement_value.to_domain(),
            correction_kind_revision_ref=body.correction_kind_revision_ref,
            replacement_world_interval=(
                body.replacement_world_interval.to_domain()
                if body.replacement_world_interval
                else None
            ),
            caller_principal_ref=caller,
        )
        return _transition_response(item)

    @app.post(
        "/v1/transitions/{transition_ref}/reverse",
        response_model=TransitionResponse,
    )
    def reverse_assertion_transition(
        transition_ref: UUID,
        body: TransitionReverseRequest,
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        caller: str = Depends(caller_context),
    ) -> TransitionResponse:
        item = kernel.reverse_assertion_transition_operation(
            operation_id=body.operation_id,
            expected_revision=body.expected_revision,
            transition_ref=transition_ref,
            correction_kind_revision_ref=body.correction_kind_revision_ref,
            caller_principal_ref=caller,
        )
        return _transition_response(item)

    @app.get(
        "/v1/knowledge/current",
        response_model=list[BitemporalAssertionResponse],
    )
    def current_knowledge(
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        _caller: str = Depends(caller_context),
        subject_ref: UUID | None = Query(default=None),
        predicate_revision_ref: UUID | None = Query(default=None),
    ) -> list[BitemporalAssertionResponse]:
        return [
            _bitemporal_response(item)
            for item in kernel.serving_current(
                subject_ref=subject_ref,
                predicate_revision_ref=predicate_revision_ref,
            )
        ]

    @app.get(
        "/v1/knowledge/history",
        response_model=list[BitemporalAssertionResponse],
    )
    def knowledge_history(
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        _caller: str = Depends(caller_context),
        subject_ref: UUID = Query(),
        predicate_revision_ref: UUID = Query(),
    ) -> list[BitemporalAssertionResponse]:
        return [
            _bitemporal_response(item)
            for item in kernel.assertion_history_serving(
                subject_ref=subject_ref,
                predicate_revision_ref=predicate_revision_ref,
            )
        ]

    @app.get(
        "/v1/knowledge/belief",
        response_model=list[BitemporalAssertionResponse],
    )
    def knowledge_belief(
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        _caller: str = Depends(caller_context),
        world_at: datetime = Query(),
        knowledge_at: datetime = Query(),
        subject_ref: UUID | None = Query(default=None),
        predicate_revision_ref: UUID | None = Query(default=None),
    ) -> list[BitemporalAssertionResponse]:
        return [
            _bitemporal_response(item)
            for item in kernel.belief(
                world_at=world_at,
                knowledge_at=knowledge_at,
                subject_ref=subject_ref,
                predicate_revision_ref=predicate_revision_ref,
            )
        ]

    @app.get(
        "/v1/identity/entities/{entity_ref}",
        response_model=IdentityResolutionResponse,
    )
    def read_identity_resolution(
        entity_ref: UUID,
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        _caller: str = Depends(caller_context),
    ) -> IdentityResolutionResponse:
        return _identity_resolution_response(kernel.read_identity_serving(entity_ref))

    @app.post(
        "/v1/identity/merge",
        response_model=IdentityTransitionResponse,
    )
    def merge_identity(
        body: IdentityMergeRequest,
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        caller: str = Depends(caller_context),
    ) -> IdentityTransitionResponse:
        return _identity_transition_response(
            kernel.merge_entities_operation(
                operation_id=body.operation_id,
                expected_revision=body.expected_revision,
                entity_refs=body.entity_refs,
                representative_ref=body.representative_ref,
                identity_kind_revision_ref=body.identity_kind_revision_ref,
                caller_principal_ref=caller,
            )
        )

    @app.post(
        "/v1/identity/replace",
        response_model=IdentityTransitionResponse,
    )
    def replace_identity(
        body: IdentityReplaceRequest,
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        caller: str = Depends(caller_context),
    ) -> IdentityTransitionResponse:
        return _identity_transition_response(
            kernel.replace_entity_operation(
                operation_id=body.operation_id,
                expected_revision=body.expected_revision,
                old_entity_ref=body.old_entity_ref,
                new_entity_ref=body.new_entity_ref,
                identity_kind_revision_ref=body.identity_kind_revision_ref,
                caller_principal_ref=caller,
            )
        )

    @app.post(
        "/v1/identity/transitions/{transition_ref}/reverse",
        response_model=IdentityTransitionResponse,
    )
    def reverse_identity(
        transition_ref: UUID,
        body: IdentityReverseRequest,
        kernel: ServiceKnowledgeKernel = Depends(get_kernel),
        caller: str = Depends(caller_context),
    ) -> IdentityTransitionResponse:
        return _identity_transition_response(
            kernel.reverse_identity_transition_operation(
                operation_id=body.operation_id,
                expected_revision=body.expected_revision,
                transition_ref=transition_ref,
                identity_kind_revision_ref=body.identity_kind_revision_ref,
                caller_principal_ref=caller,
            )
        )

    @app.post("/v1/resources", response_model=ResourceResponse, status_code=201)
    def create_resource(
        body: ResourceCreateRequest,
        kernel: ResourceServiceKnowledgeKernel = Depends(get_kernel),
        caller: str = Depends(caller_context),
    ) -> ResourceResponse:
        item = kernel.create_resource_operation(
            operation_id=body.operation_id,
            kind_revision_ref=body.kind_revision_ref,
            caller_principal_ref=caller,
            expected_revision=body.expected_revision,
        )
        item = kernel.read_resource_serving(item.resource_ref)
        return ResourceResponse(
            resource_ref=item.resource_ref,
            kind_revision_ref=item.kind_revision_ref,
            created_revision_id=item.created_revision_id,
        )

    @app.post("/v1/resources/ingest", response_model=ResourceVersionResponse)
    def ingest_resource(
        body: ResourceIngestRequest,
        kernel: ResourceServiceKnowledgeKernel = Depends(get_kernel),
        caller: str = Depends(caller_context),
    ) -> ResourceVersionResponse:
        item = kernel.ingest_resource_version_operation(
            operation_id=body.operation_id,
            resource_ref=body.resource_ref,
            content=body.content_bytes(),
            ingestion_kind_revision_ref=body.ingestion_kind_revision_ref,
            caller_principal_ref=caller,
            media_type=body.media_type,
            locator_kind=body.locator_kind,
            locator_text=body.locator_text,
            expected_revision=body.expected_revision,
        )
        item = kernel.read_resource_version_serving(item.resource_version_ref)
        return _resource_version_response(item)

    @app.get(
        "/v1/resource-versions/{resource_version_ref}",
        response_model=ResourceVersionResponse,
    )
    def read_resource_version(
        resource_version_ref: UUID,
        kernel: ResourceServiceKnowledgeKernel = Depends(get_kernel),
        _caller: str = Depends(caller_context),
    ) -> ResourceVersionResponse:
        return _resource_version_response(
            kernel.read_resource_version_serving(resource_version_ref)
        )

    @app.post(
        "/v1/assertions/{assertion_ref}/evidence",
        response_model=EvidenceTraceResponse,
        status_code=201,
    )
    def link_evidence(
        assertion_ref: UUID,
        body: EvidenceLinkRequest,
        kernel: ResourceServiceKnowledgeKernel = Depends(get_kernel),
        caller: str = Depends(caller_context),
    ) -> EvidenceTraceResponse:
        item = kernel.link_assertion_evidence_operation(
            operation_id=body.operation_id,
            assertion_ref=assertion_ref,
            resource_version_ref=body.resource_version_ref,
            relation_revision_ref=body.relation_revision_ref,
            caller_principal_ref=caller,
            expected_revision=body.expected_revision,
        )
        return _evidence_response(kernel.read_evidence_serving(item.link_id))

    @app.get(
        "/v1/assertions/{assertion_ref}/explain",
        response_model=list[EvidenceTraceResponse],
    )
    def explain_assertion(
        assertion_ref: UUID,
        kernel: ResourceServiceKnowledgeKernel = Depends(get_kernel),
        _caller: str = Depends(caller_context),
    ) -> list[EvidenceTraceResponse]:
        return [
            _evidence_response(item)
            for item in kernel.explain_assertion_serving(assertion_ref=assertion_ref)
        ]

    @app.get(
        "/v1/resources/{resource_version_ref}/impact",
        response_model=list[ImpactTraceResponse],
    )
    def resource_impact(
        resource_version_ref: UUID,
        kernel: ResourceServiceKnowledgeKernel = Depends(get_kernel),
        _caller: str = Depends(caller_context),
    ) -> list[ImpactTraceResponse]:
        return [
            _impact_response(item)
            for item in kernel.impact_from_resource_version_serving(
                resource_version_ref=resource_version_ref
            )
        ]

    return app
