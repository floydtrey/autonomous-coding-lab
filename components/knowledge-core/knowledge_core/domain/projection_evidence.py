from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from knowledge_core.domain.assertions import KnowledgeInvariantError


class ProjectionDisposition(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class ProjectionValidationState(StrEnum):
    UNVALIDATED = "unvalidated"
    VALIDATED = "validated"
    INCOMPLETE = "incomplete"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


class ProjectionAttemptReuseError(KnowledgeInvariantError):
    """A stable projection-attempt identity was reused for different inputs."""


class ProjectionAttemptStateError(KnowledgeInvariantError):
    """A projection-attempt transition conflicts with already durable evidence."""


@dataclass(frozen=True)
class ProjectionSourceEvidence:
    source_ref: UUID
    source_revision_id: int | None


@dataclass(frozen=True)
class ProjectionAttemptSnapshot:
    attempt_id: UUID
    request_digest: str
    projection_kind: str
    target_kind: str
    namespace_key: str
    scope_key: str
    backend_identity: str
    backend_version: str | None
    profile_id: str | None
    profile_digest: str | None
    config_digest: str | None
    disposition: ProjectionDisposition
    validation_state: ProjectionValidationState
    started_at: datetime
    settled_at: datetime | None
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    sources: tuple[ProjectionSourceEvidence, ...]
