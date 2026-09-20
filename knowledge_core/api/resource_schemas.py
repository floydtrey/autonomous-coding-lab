from __future__ import annotations

import base64
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, model_validator

from knowledge_core.api.schemas import OperationEnvelope
from knowledge_core.domain.resources import ResourceLocatorKind


class ResourceCreateRequest(OperationEnvelope):
    kind_revision_ref: UUID


class ResourceResponse(BaseModel):
    resource_ref: UUID
    kind_revision_ref: UUID
    created_revision_id: int


class ResourceIngestRequest(OperationEnvelope):
    resource_ref: UUID
    content_base64: str
    ingestion_kind_revision_ref: UUID
    media_type: str | None = None
    locator_kind: ResourceLocatorKind | None = None
    locator_text: str | None = None

    @model_validator(mode="after")
    def validate_resource_ingest(self):
        if (self.locator_kind is None) != (self.locator_text is None):
            raise ValueError("locator_kind and locator_text must be supplied together")
        if self.locator_text is not None and not self.locator_text:
            raise ValueError("locator_text must not be empty")
        self.content_bytes()
        return self

    def content_bytes(self) -> bytes:
        try:
            return base64.b64decode(self.content_base64.encode("ascii"), validate=True)
        except Exception as exc:
            raise ValueError("content_base64 must be valid base64") from exc


class ResourceVersionResponse(BaseModel):
    resource_version_ref: UUID
    resource_ref: UUID
    content_digest_algo: Literal["sha256"] | str
    content_digest: str
    byte_size: int
    media_type: str | None = None
    created_revision_id: int


class EvidenceLinkRequest(OperationEnvelope):
    resource_version_ref: UUID
    relation_revision_ref: UUID


class EvidenceTraceResponse(BaseModel):
    link_id: UUID
    assertion_ref: UUID
    relation_revision_ref: UUID
    resource_version: ResourceVersionResponse
    created_revision_id: int


class ImpactTraceResponse(BaseModel):
    link_id: UUID
    resource_version_ref: UUID
    dependent_ref: UUID
    dependent_ref_kind: str
    relation_revision_ref: UUID
    created_revision_id: int
