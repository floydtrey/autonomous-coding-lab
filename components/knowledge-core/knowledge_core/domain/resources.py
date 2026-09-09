from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ResourceLocatorKind(StrEnum):
    PATH = "path"
    URL = "url"
    GIT_REF = "git_ref"
    MAILBOX_LOCATOR = "mailbox_locator"
    GOVERNED_OTHER = "governed-other"


@dataclass(frozen=True)
class ResourceFoundationRefs:
    profile_ref: UUID
    profile_revision_ref: UUID
    artifact_kind_revision_ref: UUID
    resource_ingestion_kind_revision_ref: UUID
    supports_claim_relation_revision_ref: UUID


@dataclass(frozen=True)
class ResourceSnapshot:
    resource_ref: UUID
    kind_revision_ref: UUID
    created_revision_id: int


@dataclass(frozen=True)
class ResourceVersionSnapshot:
    resource_version_ref: UUID
    resource_ref: UUID
    content_digest_algo: str
    content_digest: str
    byte_size: int
    media_type: str | None
    artifact_backend: str
    artifact_key: str
    observed_occurrence_ref: UUID | None
    created_revision_id: int


@dataclass(frozen=True)
class ResourceLocatorSnapshot:
    locator_id: UUID
    resource_ref: UUID
    resource_version_ref: UUID | None
    locator_kind: ResourceLocatorKind
    locator_text: str
    observed_occurrence_ref: UUID | None
    created_revision_id: int


@dataclass(frozen=True)
class EvidenceTrace:
    link_id: UUID
    assertion_ref: UUID
    relation_revision_ref: UUID
    resource_version: ResourceVersionSnapshot
    activity_occurrence_ref: UUID | None
    created_revision_id: int


@dataclass(frozen=True)
class ImpactTrace:
    link_id: UUID
    resource_version_ref: UUID
    dependent_ref: UUID
    dependent_ref_kind: str
    relation_revision_ref: UUID
    created_revision_id: int
