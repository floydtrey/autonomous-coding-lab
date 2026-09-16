from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from uuid import UUID, uuid5

from knowledge_core.application.operations import OperationKnowledgeKernel
from knowledge_core.authority.memory import (
    MemoryCandidateReviewEvaluator,
    MemoryCandidateReviewOutcome,
    MemoryCandidateReviewRequest,
    require_memory_candidate_review,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.memory_candidates import (
    MemoryCandidateSnapshot,
    MemoryCandidateState,
)
from knowledge_core.storage.memory_candidate_models import MemoryCandidateRecord


MAX_MEMORY_CANDIDATE_BYTES = 65_536
_MEMORY_CANDIDATE_OPERATION_CLASS = "kc.memory.propose"
_MEMORY_CANDIDATE_REVIEW_OPERATION_CLASS = "kc.memory.review"
_MEMORY_CANDIDATE_OPERATION_NAMESPACE = UUID("153b502d-1b28-53b8-a534-593246dfb03a")


def memory_candidate_operation_id(*, principal_ref: str, idempotency_key: str) -> UUID:
    principal = principal_ref.strip()
    key = idempotency_key.strip()
    if not principal:
        raise ValueError("principal_ref must be non-blank")
    if not key:
        raise ValueError("idempotency_key must be non-blank")
    if len(key) > 200:
        raise ValueError("idempotency_key must be at most 200 characters")
    return uuid5(_MEMORY_CANDIDATE_OPERATION_NAMESPACE, f"{principal}:{key}")


def _require_text(name: str, value: str, *, max_length: int = 255) -> str:
    normalized = value.strip()
    if not normalized:
        raise KnowledgeInvariantError(f"{name} must be non-blank")
    if len(normalized) > max_length:
        raise KnowledgeInvariantError(
            f"{name} must be at most {max_length} characters"
        )
    return normalized


def _require_event_time(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise KnowledgeInvariantError(
            "memory candidate source_event_time must include a timezone when supplied"
        )
    return value


class MemoryCandidateKnowledgeKernel(OperationKnowledgeKernel):
    """Durable autonomous-memory proposals that are not canonical KC knowledge.

    Proposal and review settle only in ``kc_control``. Even an approved candidate
    remains non-canonical and non-retrievable until a separate explicit trusted
    ``kc_store`` operation is performed by the existing direct-note admission path.
    """

    @staticmethod
    def _snapshot(row: MemoryCandidateRecord) -> MemoryCandidateSnapshot:
        return MemoryCandidateSnapshot(
            candidate_id=row.candidate_id,
            submitted_by_principal_ref=row.submitted_by_principal_ref,
            proposer_ref=row.proposer_ref,
            project_key=row.project_key,
            content=row.content,
            content_sha256=row.content_sha256,
            source_event_time=row.source_event_time,
            proposed_at=row.proposed_at,
            state=MemoryCandidateState(row.state),
            review_operation_id=row.review_operation_id,
            reviewed_at=row.reviewed_at,
            reviewer_principal_ref=row.reviewer_principal_ref,
            review_decision_ref=row.review_decision_ref,
            review_reason_code=row.review_reason_code,
        )

    def read_candidate(self, candidate_id: UUID) -> MemoryCandidateSnapshot:
        row = self.session.get(MemoryCandidateRecord, candidate_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown memory candidate: {candidate_id}")
        return self._snapshot(row)

    def propose_candidate(
        self,
        *,
        operation_id: UUID,
        caller_principal_ref: str,
        proposer_ref: str,
        project_key: str,
        content: str,
        source_event_time: datetime | None = None,
    ) -> MemoryCandidateSnapshot:
        caller = _require_text("caller_principal_ref", caller_principal_ref)
        proposer = _require_text("proposer_ref", proposer_ref)
        project = _require_text("project_key", project_key)
        event_time = _require_event_time(source_event_time)
        if not content or not content.strip():
            raise KnowledgeInvariantError("memory candidate content must be non-blank")
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > MAX_MEMORY_CANDIDATE_BYTES:
            raise KnowledgeInvariantError(
                f"memory candidate content must be at most {MAX_MEMORY_CANDIDATE_BYTES} UTF-8 bytes"
            )
        content_sha256 = sha256(content_bytes).hexdigest()
        payload = {
            "candidate_id": str(operation_id),
            "submitted_by_principal_ref": caller,
            "proposer_ref": proposer,
            "project_key": project,
            "content_sha256": content_sha256,
            "content_size": len(content_bytes),
            "content": content,
            "source_event_time": event_time,
        }

        def action() -> MemoryCandidateSnapshot:
            row = MemoryCandidateRecord(
                candidate_id=operation_id,
                submitted_by_principal_ref=caller,
                proposer_ref=proposer,
                project_key=project,
                content=content,
                content_sha256=content_sha256,
                source_event_time=event_time,
                proposed_at=self._now(),
                state=MemoryCandidateState.PENDING.value,
                review_operation_id=None,
                reviewed_at=None,
                reviewer_principal_ref=None,
                review_decision_ref=None,
                review_reason_code=None,
            )
            self.session.add(row)
            self.session.flush()
            return self._snapshot(row)

        return self._execute_operation(
            operation_id=operation_id,
            operation_class=_MEMORY_CANDIDATE_OPERATION_CLASS,
            caller_principal_ref=caller,
            payload=payload,
            expected_revision=None,
            action=action,
            encode_result=lambda result: {"candidate_id": str(result.candidate_id)},
            replay=lambda metadata: self.read_candidate(
                UUID(str(metadata["candidate_id"]))
            ),
            allow_no_canonical_revision=True,
        )

    def review_candidate(
        self,
        *,
        operation_id: UUID,
        candidate_id: UUID,
        reviewer_principal_ref: str,
        evaluator: MemoryCandidateReviewEvaluator | None,
    ) -> MemoryCandidateSnapshot:
        reviewer = _require_text("reviewer_principal_ref", reviewer_principal_ref)
        candidate = self.read_candidate(candidate_id)
        decision = require_memory_candidate_review(
            evaluator,
            MemoryCandidateReviewRequest(
                reviewer_principal_ref=reviewer,
                candidate_id=candidate.candidate_id,
                submitted_by_principal_ref=candidate.submitted_by_principal_ref,
                proposer_ref=candidate.proposer_ref,
                project_key=candidate.project_key,
                content_sha256=candidate.content_sha256,
            ),
        )
        target_state = (
            MemoryCandidateState.APPROVED
            if decision.outcome is MemoryCandidateReviewOutcome.APPROVE_FOR_STORE
            else MemoryCandidateState.REJECTED
        )
        payload = {
            "candidate_id": str(candidate_id),
            "review_outcome": decision.outcome.value,
            "decision_ref": decision.decision_ref,
            "reason_code": decision.reason_code,
        }

        def action() -> MemoryCandidateSnapshot:
            row = self.session.get(MemoryCandidateRecord, candidate_id)
            if row is None:
                raise KnowledgeInvariantError(
                    f"unknown memory candidate: {candidate_id}"
                )
            if row.state != MemoryCandidateState.PENDING.value:
                raise KnowledgeInvariantError(
                    "memory candidate was already reviewed by a different operation"
                )
            row.state = target_state.value
            row.review_operation_id = operation_id
            row.reviewed_at = self._now()
            row.reviewer_principal_ref = reviewer
            row.review_decision_ref = decision.decision_ref
            row.review_reason_code = decision.reason_code
            self.session.flush()
            return self._snapshot(row)

        return self._execute_operation(
            operation_id=operation_id,
            operation_class=_MEMORY_CANDIDATE_REVIEW_OPERATION_CLASS,
            caller_principal_ref=reviewer,
            payload=payload,
            expected_revision=None,
            action=action,
            encode_result=lambda result: {
                "candidate_id": str(result.candidate_id),
                "state": result.state.value,
            },
            replay=lambda metadata: self.read_candidate(
                UUID(str(metadata["candidate_id"]))
            ),
            allow_no_canonical_revision=True,
        )
