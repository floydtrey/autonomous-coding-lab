from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RepositoryImportPlanRequest(BaseModel):
    manifest: dict[str, Any]


class RepositoryImportApplyRequest(BaseModel):
    manifest: dict[str, Any]
    plan_digest: str = Field(min_length=64, max_length=64)


class RepositoryImportActionResponse(BaseModel):
    source_document_key: str
    action: str
    resource_ref: UUID | None = None
    resource_version_ref: UUID | None = None


class RepositoryImportPlanResponse(BaseModel):
    manifest_digest: str
    previous_manifest_digest: str | None
    expected_current_generation_id: UUID | None
    plan_digest: str
    replay: bool
    actions: list[RepositoryImportActionResponse]


class RepositoryImportReceiptResponse(BaseModel):
    manifest_digest: str
    previous_manifest_digest: str | None
    source_repository_key: str
    source_commit: str
    status: str
    plan_digest: str
    resulting_text_generation_id: UUID | None
