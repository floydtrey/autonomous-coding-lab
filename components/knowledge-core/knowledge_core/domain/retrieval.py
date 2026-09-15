from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


LEXICAL_EVIDENCE_CONTRACT_VERSION = "kc-lexical-evidence-v2"
LEGACY_REPOSITORY_SR2_PROVENANCE_VERSION = "repository-sr2-v1"
SOURCE_NEUTRAL_SR2_PROVENANCE_VERSION = "governed-source-sr2-v2"


class RetrievalLifecycleState(StrEnum):
    CURRENT = "current"
    UNKNOWN = "unknown"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class TextIndexSource:
    resource_version_ref: UUID
    lifecycle_state: RetrievalLifecycleState
    authority_rank: int | None = None
    repository: str | None = None
    source_path: str | None = None
    source_version: str | None = None
    observed_at: datetime | None = None


@dataclass(frozen=True)
class SegmentRetrievalProvenance:
    """Exact lexical evidence for one SR-2 segment.

    ``provenance_contract_version`` makes the legacy repository-only evidence shape
    explicit. Source-neutral generations populate the governed observation/decision/
    snapshot fields and only populate repository fields when an exact compatibility
    mapping exists. Non-Git sources therefore never need fabricated Git metadata.
    """

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
    heading_path: tuple[dict[str, object], ...]
    parent_lifecycle_state: RetrievalLifecycleState
    declared_lifecycle_state: RetrievalLifecycleState | None
    declaration_source_line: int | None
    declaration_byte_start: int | None
    declaration_byte_end: int | None
    effective_lifecycle_state: RetrievalLifecycleState
    effective_control_provenance: tuple[dict[str, object], ...]

    # Source-neutral governed evidence (V2). These are intentionally nullable for
    # accepted historical pre-2D SR-2 generations.
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
    project_keys: tuple[str, ...] = ()
    producer_id: str | None = None
    producer_version: str | None = None
    source_observed_at: datetime | None = None
    source_event_time: datetime | None = None
    source_revision_time: datetime | None = None
    governance_policy_id: str | None = None
    governance_rationale: str | None = None
    governance_decided_at: datetime | None = None

    # Explicit legacy/repository compatibility projection. These fields remain
    # available for repository consumers but are null for non-Git sources.
    legacy_repository_observation_id: UUID | None = None
    governing_manifest_digest: str | None = None
    projection_snapshot_digest: str | None = None
    source_repository_key: str | None = None
    source_document_key: str | None = None


@dataclass(frozen=True)
class RetrievalHit:
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
    segment: SegmentRetrievalProvenance | None = None


@dataclass(frozen=True)
class RetrievalSearchSnapshot:
    query: str
    generation_id: UUID | None
    source_revision_highwater: int | None
    results: tuple[RetrievalHit, ...]
    retrieval_mode: str = "resource_version"
    evidence_contract_version: str = LEXICAL_EVIDENCE_CONTRACT_VERSION
    generation_config_digest: str | None = None
    structural_profile_id: str | None = None
    structural_profile_digest: str | None = None
    projection_profile_id: str | None = None
    projection_profile_digest: str | None = None
