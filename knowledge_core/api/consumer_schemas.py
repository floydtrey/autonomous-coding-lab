from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from knowledge_core.api.unified_retrieval_schemas import GraphRetrievalEvidenceResponse
from knowledge_core.domain.retrieval import (
    LEXICAL_EVIDENCE_CONTRACT_VERSION,
    TextReadinessState,
)
from knowledge_core.domain.unified_retrieval import GraphRetrievalEvidence


class KnowledgeGetSourceRequest(BaseModel):
    resource_version_ref: UUID


class KnowledgeGetSourceResponse(BaseModel):
    evidence_contract_version: str = LEXICAL_EVIDENCE_CONTRACT_VERSION
    generation_id: UUID
    source_revision_highwater: int
    retrieval_mode: str
    lineage_mode: str
    generation_config_digest: str | None
    resource_ref: UUID
    resource_version_ref: UUID
    content_digest_algo: str
    content_digest: str
    byte_size: int
    media_type: str | None
    content: str


class KnowledgeStatusResponse(BaseModel):
    evidence_contract_version: str = LEXICAL_EVIDENCE_CONTRACT_VERSION
    canonical_revision: int
    text_state: TextReadinessState
    text_generation_id: UUID | None
    text_source_revision_highwater: int | None
    text_source_count: int
    retrieval_mode: str | None
    lineage_mode: str | None
    generation_config_digest: str | None
    graph: GraphRetrievalEvidenceResponse


def source_response_from_domain(item) -> KnowledgeGetSourceResponse:
    return KnowledgeGetSourceResponse(
        evidence_contract_version=item.evidence_contract_version,
        generation_id=item.generation_id,
        source_revision_highwater=item.source_revision_highwater,
        retrieval_mode=item.retrieval_mode,
        lineage_mode=item.lineage_mode,
        generation_config_digest=item.generation_config_digest,
        resource_ref=item.resource_ref,
        resource_version_ref=item.resource_version_ref,
        content_digest_algo=item.content_digest_algo,
        content_digest=item.content_digest,
        byte_size=item.byte_size,
        media_type=item.media_type,
        content=item.content,
    )


def status_response_from_domain(
    item,
    *,
    graph: GraphRetrievalEvidence,
) -> KnowledgeStatusResponse:
    return KnowledgeStatusResponse(
        evidence_contract_version=item.evidence_contract_version,
        canonical_revision=item.canonical_revision,
        text_state=item.text_state,
        text_generation_id=item.text_generation_id,
        text_source_revision_highwater=item.text_source_revision_highwater,
        text_source_count=item.text_source_count,
        retrieval_mode=item.retrieval_mode,
        lineage_mode=item.lineage_mode,
        generation_config_digest=item.generation_config_digest,
        graph=GraphRetrievalEvidenceResponse(
            state=graph.state,
            namespace_key=graph.namespace_key,
            scope_key=graph.scope_key,
            generation_id=graph.generation_id,
            attempt_ids=list(graph.attempt_ids),
            results=[],
            reason_code=graph.reason_code,
        ),
    )
