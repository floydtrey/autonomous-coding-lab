from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from knowledge_core.domain.assertions import KnowledgeInvariantError


class DerivedKind(StrEnum):
    CURRENT_STATE = "current_state"
    IDENTITY = "identity"
    CLASSIFICATION = "classification"
    TEXT = "text"
    CHUNKS = "chunks"
    EMBEDDINGS = "embeddings"
    RELATION_CLOSURE = "relation_closure"
    OTHER = "other"


class GenerationStatus(StrEnum):
    BUILDING = "building"
    CURRENT = "current"
    STALE = "stale"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    RESTRICTED = "restricted"
    DELETION_PENDING = "deletion_pending"


class GenerationFenceError(KnowledgeInvariantError):
    """A derived generation lost the right to become current."""


@dataclass(frozen=True)
class GenerationSourceSnapshot:
    source_ref: UUID
    source_revision_id: int | None


@dataclass(frozen=True)
class GenerationSnapshot:
    generation_id: UUID
    generation_sequence: int
    derived_kind: DerivedKind
    source_revision_highwater: int
    profile_revision_ref: UUID | None
    model_identity: str | None
    model_version: str | None
    config_digest: str | None
    status: GenerationStatus
    created_at: datetime
    settled_at: datetime | None
    supersedes_generation: UUID | None
    sources: tuple[GenerationSourceSnapshot, ...]
