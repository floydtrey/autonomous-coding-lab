from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class MemoryCandidateState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class MemoryCandidateSnapshot:
    candidate_id: UUID
    submitted_by_principal_ref: str
    proposer_ref: str
    project_key: str
    content: str
    content_sha256: str
    source_event_time: datetime | None
    proposed_at: datetime
    state: MemoryCandidateState
    review_operation_id: UUID | None = None
    reviewed_at: datetime | None = None
    reviewer_principal_ref: str | None = None
    review_decision_ref: str | None = None
    review_reason_code: str | None = None
