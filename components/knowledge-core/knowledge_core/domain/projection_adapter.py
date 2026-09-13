from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.projection_evidence import (
    ProjectionAttemptSnapshot,
    ProjectionDisposition,
)


class ProjectionAdapterExecutionError(KnowledgeInvariantError):
    """A projection adapter failed after KC durably opened the attempt."""


class ProjectionAmbiguousRetryError(KnowledgeInvariantError):
    """KC will not blindly repeat an external projection with ambiguous side effects."""


@dataclass(frozen=True)
class ProjectionAdapterDescriptor:
    backend_identity: str
    backend_version: str | None
    adapter_identity: str
    adapter_version: str | None
    config_digest: str


@dataclass(frozen=True)
class ProjectionSourceSegment:
    generation_id: UUID
    resource_version_ref: UUID
    source_revision_id: int
    segment_key: str
    segment_ordinal: int
    source_slice_sha256: str
    source_byte_start: int
    source_byte_end: int
    source_line_start: int
    source_line_end: int
    effective_lifecycle_state: str
    source_repository_key: str
    source_document_key: str
    source_path: str
    source_version: str
    heading_path: tuple[dict[str, object], ...]
    reference_time: datetime
    body: str


@dataclass(frozen=True)
class ProjectionPlan:
    generation_id: UUID
    profile_id: str
    profile_digest: str
    sources: tuple[tuple[UUID, int], ...]
    segments: tuple[ProjectionSourceSegment, ...]


@dataclass(frozen=True)
class ProjectionAdapterRequest:
    attempt: ProjectionAttemptSnapshot
    segments: tuple[ProjectionSourceSegment, ...]


@dataclass(frozen=True)
class ProjectionAdapterReceipt:
    disposition: ProjectionDisposition
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    episode_count: int = 0
    node_count: int = 0
    edge_count: int = 0


@dataclass(frozen=True)
class ProjectionExecutionResult:
    attempt: ProjectionAttemptSnapshot
    receipt: ProjectionAdapterReceipt | None
    projected_segment_count: int
    replayed: bool


@dataclass(frozen=True)
class ProjectionSearchHit:
    provider_hit_id: str
    partition_key: str
    fact: str
    source_correlation_keys: tuple[str, ...]
    valid_at: datetime | None = None
    invalid_at: datetime | None = None


@dataclass(frozen=True)
class TrustedProjectionHit:
    provider_hit_id: str
    fact: str
    valid_at: datetime | None
    invalid_at: datetime | None
    sources: tuple[ProjectionSourceSegment, ...]


@dataclass(frozen=True)
class TrustedProjectionSearchSnapshot:
    query: str
    namespace_key: str
    scope_key: str
    generation_id: UUID | None
    attempt_ids: tuple[UUID, ...]
    results: tuple[TrustedProjectionHit, ...]


class ProjectionAdapter(Protocol):
    @property
    def descriptor(self) -> ProjectionAdapterDescriptor:
        ...

    def partition_key(
        self,
        *,
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
    ) -> str:
        ...

    def source_correlation_key(
        self,
        *,
        segment: ProjectionSourceSegment,
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
    ) -> str:
        ...

    async def project(self, request: ProjectionAdapterRequest) -> ProjectionAdapterReceipt:
        ...

    async def search(
        self,
        *,
        query: str,
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
        limit: int,
    ) -> tuple[ProjectionSearchHit, ...]:
        ...

    async def existing_source_keys(
        self,
        *,
        source_keys: tuple[str, ...],
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
    ) -> frozenset[str]:
        ...
