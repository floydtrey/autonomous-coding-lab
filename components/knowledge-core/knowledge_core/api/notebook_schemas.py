from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from knowledge_core.application.direct_note_capture import (
    DirectNoteDetailSnapshot,
    DirectNoteSummarySnapshot,
)


class ConsoleSessionResponse(BaseModel):
    authenticated: bool = True
    csrf_token: str
    allowed_projects: list[str]
    default_project: str
    expires_at: datetime


class ConsoleNoteSaveRequest(BaseModel):
    content: str
    project: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=128)
    source_description: str | None = Field(default=None, max_length=4000)
    source_urls: list[str] = Field(default_factory=list, max_length=20)
    source_date: date | None = None
    source_event_time: datetime | None = None

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must contain non-whitespace text")
        return value

    @field_validator("project", "category")
    @classmethod
    def optional_short_text(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("field must be non-blank when supplied")
        return value

    @field_validator("title", "source_description")
    @classmethod
    def optional_preserved_text(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("field must be non-blank when supplied")
        return value

    @field_validator("source_urls")
    @classmethod
    def normalize_urls(cls, value: list[str]) -> list[str]:
        result: list[str] = []
        for item in value:
            item = item.strip()
            if not item:
                raise ValueError("source_urls cannot contain blank values")
            if len(item) > 2048:
                raise ValueError("source URL must be at most 2048 characters")
            result.append(item)
        return result

    @field_validator("source_event_time")
    @classmethod
    def event_time_must_be_timezone_aware(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("source_event_time must include a timezone when supplied")
        return value

    @model_validator(mode="after")
    def source_time_is_unambiguous(self):
        if self.source_date is not None and self.source_event_time is not None:
            raise ValueError(
                "source_date and source_event_time cannot both be supplied"
            )
        return self


class NotebookNoteSummaryResponse(BaseModel):
    observation_id: UUID
    submission_id: UUID | None
    source_id: str
    resource_id: UUID
    version_id: UUID
    sha256: str = Field(min_length=64, max_length=64)
    byte_size: int
    media_type: str | None
    captured_at: datetime
    projects: list[str]
    title: str | None
    title_supplied: bool
    display_title: str
    category: str
    category_supplied: bool
    source_description: str | None
    source_urls: list[str]
    source_event_time: datetime | None
    source_date: date | None
    source_time_precision: Literal["unsupplied", "date", "timestamp"]
    search_ready: bool


class NotebookNoteDetailResponse(NotebookNoteSummaryResponse):
    content: str


class NotebookRecentResponse(BaseModel):
    items: list[NotebookNoteSummaryResponse]
    next_cursor: str | None


class ConsoleNoteSaveResponse(BaseModel):
    stored: bool = True
    canonical_state: Literal["stored"] = "stored"
    text_state: Literal["indexed", "pending", "failed", "superseded"]
    text_generation_id: UUID | None = None
    text_snapshot_digest: str | None = None
    text_error_code: str | None = None
    note: NotebookNoteDetailResponse


def summary_response_from_domain(
    item: DirectNoteSummarySnapshot,
) -> NotebookNoteSummaryResponse:
    return NotebookNoteSummaryResponse(
        observation_id=item.observation_id,
        submission_id=item.submission_id,
        source_id=item.source_id,
        resource_id=item.resource_ref,
        version_id=item.resource_version_ref,
        sha256=item.content_sha256,
        byte_size=item.byte_size,
        media_type=item.media_type,
        captured_at=item.captured_at,
        projects=list(item.project_keys),
        title=item.title,
        title_supplied=item.title_supplied,
        display_title=item.display_title,
        category=item.category,
        category_supplied=item.category_supplied,
        source_description=item.source_description,
        source_urls=list(item.source_urls),
        source_event_time=item.source_event_time,
        source_date=item.source_date,
        source_time_precision=item.source_time_precision,
        search_ready=item.search_ready,
    )


def detail_response_from_domain(
    item: DirectNoteDetailSnapshot,
) -> NotebookNoteDetailResponse:
    base = summary_response_from_domain(item).model_dump()
    return NotebookNoteDetailResponse(
        **base,
        content=item.content,
    )
