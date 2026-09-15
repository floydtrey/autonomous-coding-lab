from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class KnowledgeStoreRequest(BaseModel):
    content: str
    project: str
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


class KnowledgeStoreResponse(BaseModel):
    stored: bool = True
    source_type: Literal["user_note"] = "user_note"
    source_id: str
    resource_id: UUID
    version_id: UUID
    sha256: str = Field(min_length=64, max_length=64)
    canonical_state: Literal["stored"] = "stored"
    text_state: Literal["searchable", "pending", "failed", "superseded"]
    text_generation_id: UUID | None = None
    text_snapshot_digest: str | None = None
    text_error_code: str | None = None
    graph_state: Literal["pending"] = "pending"
