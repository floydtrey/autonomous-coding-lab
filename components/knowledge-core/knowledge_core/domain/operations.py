from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from knowledge_core.domain.assertions import KnowledgeInvariantError


class OperationReuseError(KnowledgeInvariantError):
    """An operation ID was reused for a materially different request."""


class OperationInProgressError(KnowledgeInvariantError):
    """An identical operation is already present but is not settled yet."""


class OperationFailedError(KnowledgeInvariantError):
    """A previously settled operation cannot be replayed successfully."""


class StaleWriteError(KnowledgeInvariantError):
    """A state-dependent mutation used an obsolete canonical revision."""

    def __init__(self, *, expected_revision: int, actual_revision: int):
        self.expected_revision = expected_revision
        self.actual_revision = actual_revision
        super().__init__(
            "stale canonical revision: "
            f"expected {expected_revision}, actual {actual_revision}"
        )


@dataclass(frozen=True)
class OperationSnapshot:
    operation_id: UUID
    operation_class: str
    request_digest: str
    status: str
    result_revision_id: int | None
    error_code: str | None
