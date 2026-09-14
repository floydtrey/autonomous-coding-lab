from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Mapping, Protocol
from uuid import UUID

from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.projection_evidence import ProjectionAttemptSnapshot


class ProjectionValidationOutcome(StrEnum):
    PENDING = "pending"
    VALIDATED = "validated"
    INCOMPLETE = "incomplete"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


class ProjectionCheckOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INDETERMINATE = "indeterminate"


class ProjectionValidationReuseError(KnowledgeInvariantError):
    """A stable projection-validation identity was reused for different inputs."""


class ProjectionValidationStateError(KnowledgeInvariantError):
    """A projection validation violated the accepted state-transition contract."""


@dataclass(frozen=True)
class ProjectionValidatorDescriptor:
    validator_identity: str
    validator_version: str | None = None
    ruleset_id: str | None = None
    ruleset_digest: str | None = None


@dataclass(frozen=True)
class ProjectionValidationRequirement:
    validator_identity: str
    validator_version: str
    ruleset_id: str
    ruleset_digest: str


@dataclass(frozen=True)
class ProjectionValidationCheck:
    check_code: str
    outcome: ProjectionCheckOutcome
    evidence: Mapping[str, object]
    detail: str | None = None


@dataclass(frozen=True)
class ProjectionValidationReport:
    outcome: ProjectionValidationOutcome
    checks: tuple[ProjectionValidationCheck, ...]


@dataclass(frozen=True)
class ProjectionValidationCheckSnapshot:
    check_code: str
    outcome: ProjectionCheckOutcome
    evidence_digest: str
    evidence: Mapping[str, object]
    detail: str | None


@dataclass(frozen=True)
class ProjectionValidationSnapshot:
    validation_id: UUID
    attempt_id: UUID
    attempt_request_digest: str
    request_digest: str
    validator_identity: str
    validator_version: str | None
    ruleset_id: str | None
    ruleset_digest: str | None
    config_digest: str | None
    outcome: ProjectionValidationOutcome
    started_at: datetime
    settled_at: datetime | None
    error_code: str | None
    error_detail: str | None
    checks: tuple[ProjectionValidationCheckSnapshot, ...]


class ProjectionValidator(Protocol):
    @property
    def descriptor(self) -> ProjectionValidatorDescriptor:
        ...

    def validate(self, attempt: ProjectionAttemptSnapshot) -> ProjectionValidationReport:
        ...
