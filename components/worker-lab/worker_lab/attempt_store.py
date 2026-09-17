from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from .errors import LabValidationError
from .lifecycle import transition_attempt
from .models import AttemptRecord, AttemptState
from .storage import AtomicRecordStore


TERMINAL_STATES = frozenset({AttemptState.CLOSED, AttemptState.ABORTED, AttemptState.OUTCOME_RECORDED})
MUTABLE_FIELDS = frozenset({"state", "updated_at", "runtime_identity", "candidate_digest", "cleanup_outcome"})
IMMUTABLE_FIELDS = tuple(
    field.name for field in fields(AttemptRecord) if field.name not in MUTABLE_FIELDS
)


class AttemptStore:
    """Lifecycle-aware persistence for immutable attempt history."""

    def __init__(self, state_root: Path) -> None:
        self.records = AtomicRecordStore(state_root)

    def read(self, attempt_id: str) -> AttemptRecord:
        return self.records.read(self._path(attempt_id), AttemptRecord.from_mapping)

    def create(self, attempt: AttemptRecord) -> None:
        if (
            attempt.state is not AttemptState.DRAFT
            or attempt.candidate_digest is not None
            or attempt.cleanup_outcome is not None
        ):
            raise LabValidationError(
                "ATTEMPT_CREATE_STATE_INVALID",
                "new attempt must be a clean DRAFT without candidate or cleanup state",
            )
        path = self._path(attempt.attempt_id)
        if self._exists(path):
            raise LabValidationError("ATTEMPT_EXISTS", "attempt identity already exists")
        if attempt.prior_attempt_id is not None:
            self._validate_retry_link(attempt)
        self.records.write(path, attempt)

    def save_transition(self, updated: AttemptRecord) -> None:
        current = self.read(updated.attempt_id)
        if updated.state is AttemptState.OUTCOME_RECORDED:
            outcome = self.read_outcome(updated.attempt_id)
            if updated.cleanup_outcome != 'worker-outcome:' + outcome.digest():
                raise LabValidationError('WORKER_OUTCOME_MISMATCH', 'attempt must reference its durable worker outcome')
        if current.state in TERMINAL_STATES:
            raise LabValidationError("ATTEMPT_TERMINAL_IMMUTABLE", "terminal attempt is immutable")
        changed = [
            field for field in IMMUTABLE_FIELDS
            if getattr(current, field) != getattr(updated, field)
        ]
        if changed:
            raise LabValidationError(
                "ATTEMPT_IDENTITY_IMMUTABLE", f"immutable attempt fields changed: {changed}"
            )
        expected = transition_attempt(
            current,
            updated.state,
            occurred_at=updated.updated_at,
            candidate_digest=(
                updated.candidate_digest if updated.state is AttemptState.CANDIDATE else None
            ),
            runtime_identity=(
                updated.runtime_identity if updated.state is AttemptState.RUNNING else None
            ),
            cleanup_outcome=(
                updated.cleanup_outcome
                if updated.state in {AttemptState.CLOSED, AttemptState.ABORTED, AttemptState.OUTCOME_RECORDED}
                else None
            ),
        )
        if expected != updated:
            raise LabValidationError(
                "ATTEMPT_TRANSITION_INVALID", "stored transition differs from protected lifecycle"
            )
        self.records.write(self._path(updated.attempt_id), updated)

    def read_outcome(self, attempt_id):
        from .worker_outcome import WorkerOutcome
        self.read(attempt_id)
        return self.records.read(f'worker-outcomes/{attempt_id}.json', WorkerOutcome.from_mapping)

    def record_outcome(self, outcome):
        from .worker_outcome import WorkerOutcome
        from .invocation_store_v3 import InvocationStoreV3
        from .canonical import canonical_json
        outcome = WorkerOutcome.from_mapping(outcome.to_dict())
        value = outcome.to_dict()
        attempt = self.read(value['attempt_id'])
        invocation = InvocationStoreV3(self.records.root).read(value['invocation_id'])
        if invocation.attempt_id != attempt.attempt_id or invocation.identity_digest() != value['invocation_digest']:
            raise LabValidationError('WORKER_OUTCOME_MISMATCH', 'outcome differs from durable invocation')
        self.records.write_bytes(f'worker-outcomes/{attempt.attempt_id}.json',
            (canonical_json(value) + '\n').encode('utf-8'))

    def bind_authorized_invocation(
        self,
        invocation_store,
        *,
        invocation_id: str,
        expected_invocation_identity: str,
        occurred_at: str,
    ) -> AttemptRecord:
        """Durably reload and bind exactly one AUTHORIZED invocation to READY -> RUNNING."""
        from .integration_v3 import InvocationState
        from .lifecycle import bind_authorized_invocation

        attempt = self.read(self._path_id_from_invocation(invocation_id, invocation_store))
        invocation = invocation_store.read(invocation_id)
        if invocation.state is not InvocationState.AUTHORIZED:
            raise LabValidationError("INTEGRATION_AUTHORIZATION_INVALID", "invocation is not durably authorized")
        if invocation.identity_digest() != expected_invocation_identity:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "authorized invocation identity differs")
        updated = bind_authorized_invocation(attempt, invocation, occurred_at=occurred_at)
        self.save_transition(updated)
        return updated

    @staticmethod
    def _path_id_from_invocation(invocation_id: str, invocation_store) -> str:
        """Read the durable invocation first; no caller-supplied attempt identity is trusted."""
        return invocation_store.read(invocation_id).attempt_id

    def _validate_retry_link(self, attempt: AttemptRecord) -> None:
        if attempt.prior_attempt_id == attempt.attempt_id:
            raise LabValidationError("ATTEMPT_RETRY_CYCLE", "attempt cannot retry itself")
        seen = {attempt.attempt_id}
        current_id = attempt.prior_attempt_id
        first = True
        while current_id is not None:
            if current_id in seen:
                raise LabValidationError("ATTEMPT_RETRY_CYCLE", "prior-attempt cycle detected")
            seen.add(current_id)
            try:
                prior = self.read(current_id)
            except LabValidationError as exc:
                if exc.code == "STORAGE_RECORD_MISSING":
                    raise LabValidationError(
                        "ATTEMPT_PRIOR_MISSING", "prior attempt does not exist"
                    ) from exc
                raise
            if first and prior.state not in TERMINAL_STATES:
                raise LabValidationError(
                    "ATTEMPT_PRIOR_ACTIVE", "retry requires a closed or aborted prior attempt"
                )
            first = False
            current_id = prior.prior_attempt_id

    def _exists(self, relative_path: str) -> bool:
        try:
            self.records.read(relative_path, AttemptRecord.from_mapping)
        except LabValidationError as exc:
            if exc.code == "STORAGE_RECORD_MISSING":
                return False
            raise
        return True

    @staticmethod
    def _path(attempt_id: str) -> str:
        return f"attempts/{attempt_id}.json"
