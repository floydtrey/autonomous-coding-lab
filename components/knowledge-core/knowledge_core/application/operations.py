from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Callable, TypeVar
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from knowledge_core.application.history import TemporalKnowledgeKernel, _as_utc
from knowledge_core.domain.assertions import (
    EpistemicBasis,
    KnowledgeInvariantError,
    TransitionSnapshot,
    TypedValue,
)
from knowledge_core.domain.operations import (
    OperationFailedError,
    OperationInProgressError,
    OperationReuseError,
    OperationSnapshot,
    StaleWriteError,
)
from knowledge_core.domain.temporal import WorldInterval
from knowledge_core.storage.control_models import Operation
from knowledge_core.storage.models import Revision


T = TypeVar("T")

# Serializes all Task 3 managed canonical writes on PostgreSQL. State-dependent
# operations compare their expected revision while holding this transaction lock,
# so another managed write cannot advance the global revision between check/commit.
_POSTGRES_CANONICAL_WRITE_LOCK = 1262702416


def _canonical_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return _as_utc(value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def _request_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        _canonical_value(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _typed_value_payload(value: TypedValue) -> dict[str, Any]:
    value = value.validated()
    return {"kind": value.kind.value, "value": _canonical_value(value.value)}


def _interval_payload(interval: WorldInterval | None) -> dict[str, Any] | None:
    if interval is None:
        return None
    return {
        "valid_from": _canonical_value(interval.valid_from),
        "valid_to": _canonical_value(interval.valid_to),
        "precision": interval.precision,
    }


class OperationKnowledgeKernel(TemporalKnowledgeKernel):
    """Task 3 idempotent semantic writes and optimistic stale-write protection."""

    def __init__(self, session: Session, **kwargs: Any):
        super().__init__(session, **kwargs)
        self._active_operation_id: UUID | None = None
        self._defer_semantic_commit = False

    def _new_revision(self) -> Revision:
        revision = Revision(
            schema_revision="task3",
            recorded_at=self._now(),
            operation_id=self._active_operation_id,
        )
        self.session.add(revision)
        self.session.flush()
        return revision

    def _commit(self) -> None:
        if self._defer_semantic_commit:
            self.session.flush()
            return
        super()._commit()

    def current_revision(self) -> int:
        return int(self.session.scalar(select(func.max(Revision.revision_id))) or 0)

    def read_operation(self, operation_id: UUID) -> OperationSnapshot:
        row = self.session.get(Operation, operation_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown operation: {operation_id}")
        return OperationSnapshot(
            operation_id=row.operation_id,
            operation_class=row.operation_class,
            request_digest=row.request_digest,
            status=row.status,
            result_revision_id=row.result_revision_id,
            error_code=row.error_code,
        )

    def _acquire_canonical_write_lock(self) -> None:
        bind = self.session.get_bind()
        if bind.dialect.name == "postgresql":
            self.session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": _POSTGRES_CANONICAL_WRITE_LOCK},
            )

    def _validate_existing_operation(
        self,
        *,
        operation: Operation,
        operation_class: str,
        caller_principal_ref: str,
        request_digest: str,
        replay: Callable[[dict[str, Any]], T],
    ) -> T:
        if (
            operation.operation_class != operation_class
            or operation.caller_principal_ref != caller_principal_ref
            or operation.request_digest != request_digest
        ):
            raise OperationReuseError(
                f"operation ID {operation.operation_id} was reused with a different request"
            )

        if operation.status == "committed":
            metadata = dict(operation.response_metadata or {})
            return replay(metadata)

        if operation.status == "conflict":
            metadata = dict(operation.response_metadata or {})
            raise StaleWriteError(
                expected_revision=int(metadata.get("expected_revision", -1)),
                actual_revision=int(metadata.get("actual_revision", -1)),
            )

        if operation.status in {"received", "running"}:
            raise OperationInProgressError(
                f"operation {operation.operation_id} has not settled"
            )

        raise OperationFailedError(
            f"operation {operation.operation_id} settled as {operation.status}"
        )

    def _insert_operation(
        self,
        *,
        operation_id: UUID,
        operation_class: str,
        caller_principal_ref: str,
        request_digest: str,
    ) -> Operation | None:
        operation = Operation(
            operation_id=operation_id,
            caller_principal_ref=caller_principal_ref,
            operation_class=operation_class,
            request_digest=request_digest,
            status="running",
            started_at=self._now(),
            settled_at=None,
            result_revision_id=None,
            error_code=None,
            response_metadata=None,
        )
        self.session.add(operation)
        try:
            self.session.flush()
        except IntegrityError:
            # A concurrent request may have won the operation-ID race. The primary
            # key is authoritative; after rollback, replay or reject that settled row.
            self.session.rollback()
            return None
        return operation

    def _execute_operation(
        self,
        *,
        operation_id: UUID,
        operation_class: str,
        caller_principal_ref: str,
        payload: dict[str, Any],
        expected_revision: int | None,
        action: Callable[[], T],
        encode_result: Callable[[T], dict[str, Any]],
        replay: Callable[[dict[str, Any]], T],
    ) -> T:
        digest = _request_digest(
            {
                "operation_class": operation_class,
                "expected_revision": expected_revision,
                "payload": payload,
            }
        )

        existing = self.session.get(Operation, operation_id)
        if existing is not None:
            return self._validate_existing_operation(
                operation=existing,
                operation_class=operation_class,
                caller_principal_ref=caller_principal_ref,
                request_digest=digest,
                replay=replay,
            )

        operation = self._insert_operation(
            operation_id=operation_id,
            operation_class=operation_class,
            caller_principal_ref=caller_principal_ref,
            request_digest=digest,
        )
        if operation is None:
            existing = self.session.get(Operation, operation_id)
            if existing is None:
                raise OperationInProgressError(
                    f"operation {operation_id} raced but no settled row is visible"
                )
            return self._validate_existing_operation(
                operation=existing,
                operation_class=operation_class,
                caller_principal_ref=caller_principal_ref,
                request_digest=digest,
                replay=replay,
            )

        # Every managed canonical write uses one transaction-scoped serialization
        # point on PostgreSQL. This makes a global revision precondition meaningful:
        # once checked, another managed write cannot advance the revision before this
        # operation settles.
        self._acquire_canonical_write_lock()

        if expected_revision is not None:
            actual_revision = self.current_revision()
            if actual_revision != expected_revision:
                operation.status = "conflict"
                operation.settled_at = self._now()
                operation.error_code = "STALE_REVISION"
                operation.response_metadata = {
                    "expected_revision": expected_revision,
                    "actual_revision": actual_revision,
                }
                self.session.commit()
                raise StaleWriteError(
                    expected_revision=expected_revision,
                    actual_revision=actual_revision,
                )

        self._active_operation_id = operation_id
        self._defer_semantic_commit = True
        try:
            result = action()
            result_revision_id = self.session.scalar(
                select(Revision.revision_id).where(Revision.operation_id == operation_id)
            )
            if result_revision_id is None:
                raise KnowledgeInvariantError(
                    "managed semantic operation committed no canonical revision"
                )

            operation.status = "committed"
            operation.settled_at = self._now()
            operation.result_revision_id = int(result_revision_id)
            operation.error_code = None
            operation.response_metadata = encode_result(result)

            self._defer_semantic_commit = False
            self._active_operation_id = None
            self.session.commit()
            return result
        except Exception:
            self._defer_semantic_commit = False
            self._active_operation_id = None
            self.session.rollback()
            raise

    def append_assertion_operation(
        self,
        *,
        operation_id: UUID,
        subject_ref: UUID,
        predicate_revision_ref: UUID,
        profile_revision_ref: UUID,
        value: TypedValue,
        epistemic_basis: EpistemicBasis = EpistemicBasis.STATED,
        world_interval: WorldInterval | None = None,
        expected_revision: int | None = None,
        caller_principal_ref: str = "kernel-test-client",
    ) -> UUID:
        payload = {
            "subject_ref": str(subject_ref),
            "predicate_revision_ref": str(predicate_revision_ref),
            "profile_revision_ref": str(profile_revision_ref),
            "value": _typed_value_payload(value),
            "epistemic_basis": epistemic_basis.value,
            "world_interval": _interval_payload(world_interval),
        }

        def action() -> UUID:
            return TemporalKnowledgeKernel.append_assertion(
                self,
                subject_ref=subject_ref,
                predicate_revision_ref=predicate_revision_ref,
                profile_revision_ref=profile_revision_ref,
                value=value,
                epistemic_basis=epistemic_basis,
                world_interval=world_interval,
            )

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="append_assertion",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {"assertion_ref": str(result)},
            replay=lambda metadata: UUID(str(metadata["assertion_ref"])),
        )

    def correct_assertion_operation(
        self,
        *,
        operation_id: UUID,
        expected_revision: int,
        source_assertion_ref: UUID,
        replacement_value: TypedValue,
        correction_kind_revision_ref: UUID,
        replacement_world_interval: WorldInterval | None = None,
        caller_principal_ref: str = "kernel-test-client",
    ) -> TransitionSnapshot:
        payload = {
            "source_assertion_ref": str(source_assertion_ref),
            "replacement_value": _typed_value_payload(replacement_value),
            "correction_kind_revision_ref": str(correction_kind_revision_ref),
            "replacement_world_interval": _interval_payload(
                replacement_world_interval
            ),
        }

        def action() -> TransitionSnapshot:
            return TemporalKnowledgeKernel.correct_assertion(
                self,
                source_assertion_ref=source_assertion_ref,
                replacement_value=replacement_value,
                correction_kind_revision_ref=correction_kind_revision_ref,
                replacement_world_interval=replacement_world_interval,
            )

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="correct_assertion",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {"transition_ref": str(result.transition_ref)},
            replay=lambda metadata: self.read_transition(
                UUID(str(metadata["transition_ref"]))
            ),
        )
