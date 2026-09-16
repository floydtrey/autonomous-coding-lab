from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from knowledge_core.application.memory_candidates import MAX_MEMORY_CANDIDATE_BYTES


class MemoryCandidateProposalRequest(BaseModel):
    content: str = Field(max_length=MAX_MEMORY_CANDIDATE_BYTES)
    project: str = Field(max_length=255)
    proposer_ref: str = Field(max_length=255)
    source_event_time: datetime | None = None

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must contain non-whitespace text")
        if len(value.encode("utf-8")) > MAX_MEMORY_CANDIDATE_BYTES:
            raise ValueError(
                f"content must be at most {MAX_MEMORY_CANDIDATE_BYTES} UTF-8 bytes"
            )
        return value

    @field_validator("project", "proposer_ref")
    @classmethod
    def bounded_text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must be non-blank")
        return value

    @field_validator("source_event_time")
    @classmethod
    def event_time_must_be_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("source_event_time must include a timezone when supplied")
        return value


class MemoryCandidateProposalResponse(BaseModel):
    candidate_id: UUID
    state: Literal["pending"] = "pending"
    proposer_ref: str
    project: str
    content_sha256: str = Field(min_length=64, max_length=64)
    proposed_at: datetime
    canonical_state: Literal["not_stored"] = "not_stored"
