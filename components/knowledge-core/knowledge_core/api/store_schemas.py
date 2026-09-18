from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class KnowledgeStoreRequest(BaseModel):
    content: str
    project: str = Field(max_length=255)
    source_type: Literal["user_note"] = "user_note"
    source_id: str | None = None
    source_event_time: datetime | None = None

    # C02 notebook metadata. All fields remain optional here so legacy Task 2E
    # clients preserve their exact historical request/idempotency identity.
    title: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=128)
    source_description: str | None = Field(default=None, max_length=4000)
    source_urls: list[str] | None = Field(default=None, max_length=20)
    source_date: date | None = None

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

    @field_validator("title", "source_description")
    @classmethod
    def optional_text_must_not_be_blank(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("optional text fields must be non-blank when supplied")
        return value

    @field_validator("category")
    @classmethod
    def category_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("category must be non-blank when supplied")
        return value

    @field_validator("source_urls")
    @classmethod
    def source_urls_must_be_bounded(
        cls, value: list[str] | None
    ) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        for item in value:
            item = item.strip()
            if not item:
                raise ValueError("source_urls cannot contain blank values")
            if len(item) > 2048:
                raise ValueError("source URL must be at most 2048 characters")
            normalized.append(item)
        return normalized

    @model_validator(mode="after")
    def source_time_precision_is_unambiguous(self):
        if self.source_date is not None and self.source_event_time is not None:
            raise ValueError(
                "source_date and source_event_time cannot both be supplied"
            )
        return self


class KnowledgeStoreResponse(BaseModel):
    stored: bool = True
    source_type: Literal["user_note"] = "user_note"
    source_id: str
    resource_id: UUID
    version_id: UUID
    sha256: str = Field(min_length=64, max_length=64)
    canonical_state: Literal["stored"] = "stored"
    observation_id: UUID | None = None
    captured_at: datetime | None = None
    project: str | None = None
    capture_metadata_recorded: bool = False
    # Canonical settlement and text publication are intentionally separate.
    text_state: Literal["indexed", "pending", "failed", "superseded"]
    text_generation_id: UUID | None = None
    text_snapshot_digest: str | None = None
    text_error_code: str | None = None
    graph_state: Literal["pending"] = "pending"
