from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from .errors import LabValidationError
from .integration import InvocationRecord, InvocationState, transition_invocation, validate_invocation_id
from .storage import AtomicRecordStore


_MUTABLE_FIELDS = frozenset({"state", "authorized_by", "authorized_at", "result_digest"})
_IMMUTABLE_FIELDS = tuple(field.name for field in fields(InvocationRecord) if field.name not in _MUTABLE_FIELDS)


class InvocationStore:
    """Durable storage for one immutable invocation envelope and its guarded state."""

    def __init__(self, state_root: Path) -> None:
        self.records = AtomicRecordStore(state_root)

    def read(self, invocation_id: str) -> InvocationRecord:
        validate_invocation_id(invocation_id)
        return self.records.read(self._path(invocation_id), InvocationRecord.from_mapping)

    def create(self, record: InvocationRecord) -> None:
        if record.state is not InvocationState.PREPARED or record.result_digest is not None:
            raise LabValidationError("INTEGRATION_CREATE_INVALID", "new invocation must be prepared without a result")
        try:
            self.read(record.invocation_id)
        except LabValidationError as exc:
            if exc.code != "STORAGE_RECORD_MISSING":
                raise
        else:
            raise LabValidationError("INTEGRATION_INVOCATION_EXISTS", "invocation identity already exists")
        self.records.write(self._path(record.invocation_id), record)

    def save_transition(self, updated: InvocationRecord, *, expected_digest: str) -> None:
        current = self.read(updated.invocation_id)
        if current.digest() != expected_digest:
            raise LabValidationError("INTEGRATION_STALE_WRITE", "invocation state changed before transition")
        if current.state in {InvocationState.COMPLETED, InvocationState.REJECTED, InvocationState.ABORTED}:
            raise LabValidationError("INTEGRATION_TERMINAL_IMMUTABLE", "terminal invocation cannot reopen")
        changed = [name for name in _IMMUTABLE_FIELDS if getattr(current, name) != getattr(updated, name)]
        if changed:
            raise LabValidationError("INTEGRATION_IDENTITY_IMMUTABLE", f"immutable invocation fields changed: {changed}")
        expected = transition_invocation(
            current,
            updated.state,
            authorized_by=updated.authorized_by if updated.state is InvocationState.AUTHORIZED else None,
            authorized_at=updated.authorized_at if updated.state is InvocationState.AUTHORIZED else None,
            result_digest=updated.result_digest,
        )
        if expected != updated:
            raise LabValidationError("INTEGRATION_TRANSITION_INVALID", "stored transition differs from protected lifecycle")
        self.records.write(self._path(updated.invocation_id), updated)

    @staticmethod
    def _path(invocation_id: str) -> str:
        validate_invocation_id(invocation_id)
        return f"invocations/{invocation_id}.json"