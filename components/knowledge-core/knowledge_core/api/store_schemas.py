from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class KnowledgeStoreRequest(BaseModel):
    content: str
    project: str = Field(max_length=255)
    source_type: Literal["user_note"] = "user_note"
    source_id: str | None = None
    source_event_time: datetime | None = None

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must contain non-whitespace text")
        return value

    @field_validator("project")
    @classmethod
    def project_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("project must be non-blank")
        return value

    @field_validator("source_id")
    @classmethod
    def source_id_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("source_id must be non-blank when supplied")
        return value

    @field_validator("source_event_time")
    @classmethod
    def event_time_must_be_timezone_aware(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("source_event_time must include a timezone when supplied")
        return value


class KnowledgeStoreResponse(BaseModel):
    stored: bool = True
    source_type: Literal["user_note"] = "user_note"
    source_id: str
    resource_id: UUID
    version_id: UUID
    sha256: str = Field(min_length=64, max_length=64)
    canonical_state: Literal["stored"] = "stored"
    # Task 2E can prove that the note is present in the current SR-2 index. The
    # existing lexical reader remains repository-shaped until Task 2F, so calling
    # this state "searchable" here would overstate the accepted boundary.
    text_state: Literal["indexed", "pending", "failed", "superseded"]
    text_generation_id: UUID | None = None
    text_snapshot_digest: str | None = None
    text_error_code: str | None = None
    graph_state: Literal["pending"] = "pending"
