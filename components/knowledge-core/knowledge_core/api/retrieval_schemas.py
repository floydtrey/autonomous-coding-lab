from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from knowledge_core.domain.retrieval import RetrievalLifecycleState


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


class RetrievalSearchResponse(BaseModel):
    query: str
    generation_id: UUID | None
    source_revision_highwater: int | None
    results: list[RetrievalHitResponse]
