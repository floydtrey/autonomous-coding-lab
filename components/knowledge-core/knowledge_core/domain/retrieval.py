from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


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
    governed_observation_id: UUID
    governing_manifest_digest: str
    projection_snapshot_digest: str
    source_repository_key: str
    source_document_key: str
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
    segment: SegmentRetrievalProvenance | None = None


@dataclass(frozen=True)
class RetrievalSearchSnapshot:
    query: str
    generation_id: UUID | None
    source_revision_highwater: int | None
    results: tuple[RetrievalHit, ...]
    retrieval_mode: str = "resource_version"
    generation_config_digest: str | None = None
    structural_profile_id: str | None = None
    structural_profile_digest: str | None = None
    projection_profile_id: str | None = None
    projection_profile_digest: str | None = None
