from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from knowledge_core.api.retrieval_schemas import (
    RetrievalSearchResponse,
    retrieval_response_from_domain,
)
from knowledge_core.domain.unified_retrieval import (
    GraphRetrievalState,
    UNIFIED_RETRIEVAL_EVIDENCE_CONTRACT_VERSION,
    UnifiedRetrievalWarningCode,
    UnifiedRetrievalSearchSnapshot,
)


class UnifiedRetrievalWarningResponse(BaseModel):
    code: UnifiedRetrievalWarningCode
    message: str


class GraphSourceCorrelationResponse(BaseModel):
    resource_version_ref: UUID
    source_revision_id: int
    segment_key: str
    segment_ordinal: int
    source_slice_sha256: str
    source_line_start: int
    source_line_end: int
    source_identity_digest: str
    source_kind: str
    origin_scope: str
    collection_key: str
    item_key: str
    project_keys: list[str] = Field(default_factory=list)
    governed_source_observation_id: UUID
    governed_observation_digest: str
    governed_decision_id: UUID
    governed_decision_digest: str
    governing_snapshot_digest: str
    governed_projection_digest: str
    reference_time: datetime
    reference_time_policy: str
    source_repository_key: str | None = None
    source_document_key: str | None = None
    source_path: str | None = None
    source_version: str | None = None


class GraphRetrievalHitResponse(BaseModel):
    provider_hit_id: str
    fact: str
    valid_at: datetime | None = None
    invalid_at: datetime | None = None
    sources: list[GraphSourceCorrelationResponse]


class GraphRetrievalEvidenceResponse(BaseModel):
    state: GraphRetrievalState
    namespace_key: str | None = None
    scope_key: str | None = None
    generation_id: UUID | None = None
    attempt_ids: list[UUID] = Field(default_factory=list)
    results: list[GraphRetrievalHitResponse] = Field(default_factory=list)
    reason_code: str | None = None


class UnifiedRetrievalSearchResponse(RetrievalSearchResponse):
    """Additive Task 6B response contract for the existing ``kc_search`` surface.

    Every inherited field preserves the accepted Task 3/5 lexical response shape.
    New consumers may additionally inspect graph evidence and degradation warnings.
    """

    unified_evidence_contract_version: Literal[
        "kc-unified-retrieval-evidence-v1"
    ] = UNIFIED_RETRIEVAL_EVIDENCE_CONTRACT_VERSION
    graph: GraphRetrievalEvidenceResponse
    warnings: list[UnifiedRetrievalWarningResponse] = Field(default_factory=list)


def unified_retrieval_response_from_domain(
    item: UnifiedRetrievalSearchSnapshot,
) -> UnifiedRetrievalSearchResponse:
    lexical = retrieval_response_from_domain(item.lexical)
    graph = item.graph

    graph_results = []
    for hit in graph.results:
        graph_results.append(
            GraphRetrievalHitResponse(
                provider_hit_id=hit.provider_hit_id,
                fact=hit.fact,
                valid_at=hit.valid_at,
                invalid_at=hit.invalid_at,
                sources=[
                    GraphSourceCorrelationResponse(
                        resource_version_ref=source.resource_version_ref,
                        source_revision_id=source.source_revision_id,
                        segment_key=source.segment_key,
                        segment_ordinal=source.segment_ordinal,
                        source_slice_sha256=source.source_slice_sha256,
                        source_line_start=source.source_line_start,
                        source_line_end=source.source_line_end,
                        source_identity_digest=source.source_identity_digest,
                        source_kind=source.source_kind,
                        origin_scope=source.origin_scope,
                        collection_key=source.collection_key,
                        item_key=source.item_key,
                        project_keys=list(source.project_keys),
                        governed_source_observation_id=(
                            source.governed_source_observation_id
                        ),
                        governed_observation_digest=source.governed_observation_digest,
                        governed_decision_id=source.governed_decision_id,
                        governed_decision_digest=source.governed_decision_digest,
                        governing_snapshot_digest=source.governing_snapshot_digest,
                        governed_projection_digest=source.governed_projection_digest,
                        reference_time=source.reference_time,
                        reference_time_policy=source.reference_time_policy,
                        source_repository_key=source.source_repository_key,
                        source_document_key=source.source_document_key,
                        source_path=source.source_path,
                        source_version=source.source_version,
                    )
                    for source in hit.sources
                ],
            )
        )

    payload = lexical.model_dump()
    payload.update(
        {
            "unified_evidence_contract_version": item.evidence_contract_version,
            "graph": GraphRetrievalEvidenceResponse(
                state=graph.state,
                namespace_key=graph.namespace_key,
                scope_key=graph.scope_key,
                generation_id=graph.generation_id,
                attempt_ids=list(graph.attempt_ids),
                results=graph_results,
                reason_code=graph.reason_code,
            ),
            "warnings": [
                UnifiedRetrievalWarningResponse(
                    code=warning.code,
                    message=warning.message,
                )
                for warning in item.warnings
            ],
        }
    )
    return UnifiedRetrievalSearchResponse(**payload)
