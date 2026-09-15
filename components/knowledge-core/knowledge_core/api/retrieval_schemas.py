from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from knowledge_core.domain.retrieval import (
    LEXICAL_EVIDENCE_CONTRACT_VERSION,
    RetrievalLifecycleState,
)


class RetrievalSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=50)
    include_superseded: bool = False

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must contain non-whitespace text")
        return value


class SegmentRetrievalProvenanceResponse(BaseModel):
    provenance_contract_version: str
    governed_observation_id: UUID
    source_classification: str
    segment_key: str
    segment_ordinal: int
    structural_kind: str
    base_block_ordinal: int
    part_index: int
    part_count: int
    source_byte_start: int
    source_byte_end: int
    source_line_start: int
    source_line_end: int
    source_slice_sha256: str
    heading_path: list[dict[str, object]]
    parent_lifecycle_state: RetrievalLifecycleState
    declared_lifecycle_state: RetrievalLifecycleState | None
    declaration_source_line: int | None
    declaration_byte_start: int | None
    declaration_byte_end: int | None
    effective_lifecycle_state: RetrievalLifecycleState
    effective_control_provenance: list[dict[str, object]]

    governed_observation_digest: str | None = None
    governed_decision_id: UUID | None = None
    governed_decision_digest: str | None = None
    governing_snapshot_digest: str | None = None
    governed_projection_digest: str | None = None
    source_identity_digest: str | None = None
    source_kind: str | None = None
    origin_scope: str | None = None
    collection_key: str | None = None
    item_key: str | None = None
    project_keys: list[str] = Field(default_factory=list)
    producer_id: str | None = None
    producer_version: str | None = None
    source_observed_at: datetime | None = None
    source_event_time: datetime | None = None
    source_revision_time: datetime | None = None
    governance_policy_id: str | None = None
    governance_rationale: str | None = None
    governance_decided_at: datetime | None = None

    legacy_repository_observation_id: UUID | None = None
    governing_manifest_digest: str | None = None
    projection_snapshot_digest: str | None = None
    source_repository_key: str | None = None
    source_document_key: str | None = None


class RetrievalHitResponse(BaseModel):
    rank: int
    resource_ref: UUID
    resource_version_ref: UUID
    content_digest_algo: str
    content_digest: str
    media_type: str | None
    observed_occurrence_ref: UUID | None
    created_revision_id: int
    lifecycle_state: RetrievalLifecycleState
    authority_rank: int | None
    repository: str | None
    source_path: str | None
    source_version: str | None
    observed_at: datetime | None
    lexical_score: float
    content: str | None = None
    segment: SegmentRetrievalProvenanceResponse | None = None


class RetrievalSearchResponse(BaseModel):
    query: str
    generation_id: UUID | None
    source_revision_highwater: int | None
    retrieval_mode: str = "resource_version"
    evidence_contract_version: str = LEXICAL_EVIDENCE_CONTRACT_VERSION
    generation_config_digest: str | None = None
    structural_profile_id: str | None = None
    structural_profile_digest: str | None = None
    projection_profile_id: str | None = None
    projection_profile_digest: str | None = None
    results: list[RetrievalHitResponse]


def retrieval_response_from_domain(item) -> RetrievalSearchResponse:
    """Map bounded retrieval content and exact governed provenance to the API."""

    results: list[RetrievalHitResponse] = []
    for rank, hit in enumerate(item.results, start=1):
        segment = hit.segment
        segment_response = (
            SegmentRetrievalProvenanceResponse(
                provenance_contract_version=segment.provenance_contract_version,
                governed_observation_id=segment.governed_observation_id,
                source_classification=segment.source_classification,
                segment_key=segment.segment_key,
                segment_ordinal=segment.segment_ordinal,
                structural_kind=segment.structural_kind,
                base_block_ordinal=segment.base_block_ordinal,
                part_index=segment.part_index,
                part_count=segment.part_count,
                source_byte_start=segment.source_byte_start,
                source_byte_end=segment.source_byte_end,
                source_line_start=segment.source_line_start,
                source_line_end=segment.source_line_end,
                source_slice_sha256=segment.source_slice_sha256,
                heading_path=list(segment.heading_path),
                parent_lifecycle_state=segment.parent_lifecycle_state,
                declared_lifecycle_state=segment.declared_lifecycle_state,
                declaration_source_line=segment.declaration_source_line,
                declaration_byte_start=segment.declaration_byte_start,
                declaration_byte_end=segment.declaration_byte_end,
                effective_lifecycle_state=segment.effective_lifecycle_state,
                effective_control_provenance=list(
                    segment.effective_control_provenance
                ),
                governed_observation_digest=segment.governed_observation_digest,
                governed_decision_id=segment.governed_decision_id,
                governed_decision_digest=segment.governed_decision_digest,
                governing_snapshot_digest=segment.governing_snapshot_digest,
                governed_projection_digest=segment.governed_projection_digest,
                source_identity_digest=segment.source_identity_digest,
                source_kind=segment.source_kind,
                origin_scope=segment.origin_scope,
                collection_key=segment.collection_key,
                item_key=segment.item_key,
                project_keys=list(segment.project_keys),
                producer_id=segment.producer_id,
                producer_version=segment.producer_version,
                source_observed_at=segment.source_observed_at,
                source_event_time=segment.source_event_time,
                source_revision_time=segment.source_revision_time,
                governance_policy_id=segment.governance_policy_id,
                governance_rationale=segment.governance_rationale,
                governance_decided_at=segment.governance_decided_at,
                legacy_repository_observation_id=(
                    segment.legacy_repository_observation_id
                ),
                governing_manifest_digest=segment.governing_manifest_digest,
                projection_snapshot_digest=segment.projection_snapshot_digest,
                source_repository_key=segment.source_repository_key,
                source_document_key=segment.source_document_key,
            )
            if segment is not None
            else None
        )
        results.append(
            RetrievalHitResponse(
                rank=rank,
                resource_ref=hit.resource_ref,
                resource_version_ref=hit.resource_version_ref,
                content_digest_algo=hit.content_digest_algo,
                content_digest=hit.content_digest,
                media_type=hit.media_type,
                observed_occurrence_ref=hit.observed_occurrence_ref,
                created_revision_id=hit.created_revision_id,
                lifecycle_state=hit.lifecycle_state,
                authority_rank=hit.authority_rank,
                repository=hit.repository,
                source_path=hit.source_path,
                source_version=hit.source_version,
                observed_at=hit.observed_at,
                lexical_score=hit.lexical_score,
                content=hit.content,
                segment=segment_response,
            )
        )

    return RetrievalSearchResponse(
        query=item.query,
        generation_id=item.generation_id,
        source_revision_highwater=item.source_revision_highwater,
        retrieval_mode=item.retrieval_mode,
        evidence_contract_version=item.evidence_contract_version,
        generation_config_digest=item.generation_config_digest,
        structural_profile_id=item.structural_profile_id,
        structural_profile_digest=item.structural_profile_digest,
        projection_profile_id=item.projection_profile_id,
        projection_profile_digest=item.projection_profile_digest,
        results=results,
    )
