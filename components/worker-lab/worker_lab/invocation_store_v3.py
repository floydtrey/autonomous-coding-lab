from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path

from .errors import LabValidationError
from .integration_v3 import (
    InvocationRecordV3,
    InvocationState,
    authorize_invocation,
    transition_invocation,
)
from .provider_binding import ProviderBindingStore
from .storage import AtomicRecordStore


_INVOCATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,95}$")
_MUTABLE_FIELDS = frozenset({"state", "authorized_by", "authorized_at", "result_digest"})
_IMMUTABLE_FIELDS = tuple(
    field.name for field in fields(InvocationRecordV3) if field.name not in _MUTABLE_FIELDS
)
_TERMINAL_STATES = frozenset(
    {InvocationState.COMPLETED, InvocationState.REJECTED, InvocationState.ABORTED, InvocationState.OUTCOME_RECORDED}
)


class InvocationStoreV3:
    """Durable V3 invocation storage with binding-gated authorization transitions."""

    def __init__(self, state_root: Path) -> None:
        self.records = AtomicRecordStore(state_root)

    def read(self, invocation_id: str) -> InvocationRecordV3:
        return self.records.read(self._path(invocation_id), InvocationRecordV3.from_mapping)

    def create(self, record: InvocationRecordV3) -> None:
        if not isinstance(record, InvocationRecordV3):
            raise LabValidationError(
                "INTEGRATION_V3_CREATE_INVALID",
                "V3 invocation store requires a V3 invocation record",
            )
        if (
            record.state is not InvocationState.PREPARED
            or record.authorized_by is not None
            or record.authorized_at is not None
            or record.result_digest is not None
        ):
            raise LabValidationError(
                "INTEGRATION_V3_CREATE_INVALID",
                "new V3 invocation must be PREPARED without authorization or result state",
            )
        path = self._path(record.invocation_id)
        try:
            self.records.read(path, InvocationRecordV3.from_mapping)
        except LabValidationError as exc:
            if exc.code != "STORAGE_RECORD_MISSING":
                raise
        else:
            raise LabValidationError(
                "INTEGRATION_V3_INVOCATION_EXISTS",
                "V3 invocation identity already exists",
            )
        self.records.write(path, record)

    def save_transition(
        self,
        updated: InvocationRecordV3,
        *,
        expected_digest: str,
        binding_store: ProviderBindingStore | None = None,
    ) -> None:
        if not isinstance(updated, InvocationRecordV3):
            raise LabValidationError(
                "INTEGRATION_V3_TRANSITION_INVALID",
                "V3 invocation transition requires a V3 record",
            )
        current = self.read(updated.invocation_id)
        if updated.state is InvocationState.OUTCOME_RECORDED:
            from .attempt_store import AttemptStore
            outcome = AttemptStore(self.records.root).read_outcome(updated.attempt_id)
            value = outcome.to_dict()
            if (updated.result_digest != outcome.digest()
                    or value['invocation_digest'] != updated.identity_digest()
                    or value['invocation_id'] != updated.invocation_id):
                raise LabValidationError('WORKER_OUTCOME_MISMATCH', 'invocation must reference its durable worker outcome')
        if current.digest() != expected_digest:
            raise LabValidationError(
                "INTEGRATION_V3_STALE_WRITE",
                "V3 invocation state changed before transition",
            )
        if current.state in _TERMINAL_STATES:
            raise LabValidationError(
                "INTEGRATION_V3_TERMINAL_IMMUTABLE",
                "terminal V3 invocation cannot reopen",
            )
        changed = [
            name for name in _IMMUTABLE_FIELDS if getattr(current, name) != getattr(updated, name)
        ]
        if changed:
            raise LabValidationError(
                "INTEGRATION_V3_IDENTITY_IMMUTABLE",
                f"immutable V3 invocation fields changed: {changed}",
            )
        if updated.state is InvocationState.AUTHORIZED:
            if not isinstance(binding_store, ProviderBindingStore):
                raise LabValidationError(
                    "INTEGRATION_V3_PROVIDER_BINDING_REQUIRED",
                    "authorization persistence requires the durable Provider Binding store",
                )
            if updated.authorized_by is None or updated.authorized_at is None:
                raise LabValidationError(
                    "INTEGRATION_V3_AUTHORIZATION_INVALID",
                    "authorized V3 invocation lacks controller identity or time",
                )
            expected = authorize_invocation(
                current,
                binding_store=binding_store,
                controller_identity=updated.authorized_by,
                authorized_at=updated.authorized_at,
            )
        else:
            expected = transition_invocation(
                current,
                updated.state,
                result_digest=updated.result_digest,
            )
        if expected != updated:
            raise LabValidationError(
                "INTEGRATION_V3_TRANSITION_INVALID",
                "stored V3 transition differs from the protected lifecycle",
            )
        self.records.write(self._path(updated.invocation_id), updated)

    @staticmethod
    def _path(invocation_id: str) -> str:
        if not isinstance(invocation_id, str) or not _INVOCATION_ID_RE.fullmatch(invocation_id):
            raise LabValidationError(
                "INTEGRATION_V3_INVOCATION_INVALID",
                "V3 invocation identity is invalid",
            )
        return f"invocations/{invocation_id}.json"
