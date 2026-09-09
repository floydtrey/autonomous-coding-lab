from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class DeletionActionType(StrEnum):
    RESTRICT = "restrict"
    ERASE = "erase"
    RETENTION_EXCEPTION = "retention_exception"


class DeletionCaseStatus(StrEnum):
    REQUESTED = "requested"
    FENCED = "fenced"
    CANONICAL_PENDING = "canonical_pending"
    DERIVATIVES_PENDING = "derivatives_pending"
    BACKUP_FENCED = "backup_fenced"
    SETTLED = "settled"
    BLOCKED = "blocked"
    FAILED = "failed"


class DeletionReconciliationState(StrEnum):
    FENCED = "fenced"
    RESTRICTED_SETTLED = "restricted_settled"
    ERASED_TOMBSTONE = "erased_tombstone"
    BLOCKED = "blocked"


class KnowledgeRestrictedError(LookupError):
    """Raised when a serving read is fenced by deletion/restriction control."""


class DeletionBlockedError(RuntimeError):
    """Raised when physical erasure cannot safely proceed."""


@dataclass(frozen=True)
class DeletionTargetSnapshot:
    target_ref: UUID
    reconciliation_state: DeletionReconciliationState
    last_checked_at: datetime


@dataclass(frozen=True)
class DeletionCaseSnapshot:
    case_id: UUID
    operation_id: UUID
    action_type: DeletionActionType
    policy_scope_id: str
    status: DeletionCaseStatus
    requested_at: datetime
    settled_at: datetime | None
    targets: tuple[DeletionTargetSnapshot, ...]
