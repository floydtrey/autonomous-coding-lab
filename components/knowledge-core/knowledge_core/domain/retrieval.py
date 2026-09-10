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


@dataclass(frozen=True)
class RetrievalSearchSnapshot:
    query: str
    generation_id: UUID | None
    source_revision_highwater: int | None
    results: tuple[RetrievalHit, ...]
