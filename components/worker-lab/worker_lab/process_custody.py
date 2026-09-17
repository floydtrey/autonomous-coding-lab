from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Callable, Mapping, Protocol

from .canonical import canonical_digest
from .errors import LabValidationError
from .storage import AtomicRecordStore


PROCESS_CUSTODY_SCHEMA = "worker-lab-process-custody:v2"
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{5,95}$")
_BACKEND_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}:v[1-9][0-9]*$")
_BACKEND_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,255}$")


class CustodyState(StrEnum):
    PREPARED = "PREPARED"
    ASSIGNED = "ASSIGNED"
    DISPATCHING = "DISPATCHING"
    EXITED = "EXITED"
    TERMINATED = "TERMINATED"
    UNCERTAIN = "UNCERTAIN"
    ABSENCE_VERIFIED = "ABSENCE_VERIFIED"


LEGAL_CUSTODY_TRANSITIONS = {
    CustodyState.PREPARED: frozenset({CustodyState.ASSIGNED, CustodyState.TERMINATED, CustodyState.UNCERTAIN}),
    CustodyState.ASSIGNED: frozenset({CustodyState.DISPATCHING, CustodyState.TERMINATED, CustodyState.UNCERTAIN}),
    CustodyState.DISPATCHING: frozenset({CustodyState.EXITED, CustodyState.TERMINATED, CustodyState.UNCERTAIN}),
    CustodyState.EXITED: frozenset({CustodyState.ABSENCE_VERIFIED}),
    CustodyState.TERMINATED: frozenset({CustodyState.ABSENCE_VERIFIED}),
    CustodyState.UNCERTAIN: frozenset(),
    CustodyState.ABSENCE_VERIFIED: frozenset(),
}


@dataclass(frozen=True)
class ProcessCustodyRecord:
    schema_version: str
    invocation_digest: str
    invocation_id: str
    backend_id: str
    controller_identity: str
    worker_identity: str | None
    workspace_content_digest: str
    state: CustodyState
    request_sent: bool
    exit_code: int | None
    active_workload_count: int | None
    absence_evidence_digest: str | None
    absence_verified_at: str | None
    first_failure: str | None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["state"] = str(self.state)
        return value

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: Any) -> "ProcessCustodyRecord":
        if not isinstance(value, Mapping) or set(value) != set(cls.__dataclass_fields__):
            raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "custody fields are missing or unknown")
        try:
            state = CustodyState(value["state"])
        except (TypeError, ValueError) as exc:
            raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "custody state is unsupported") from exc
        record = cls(
            _exact(value["schema_version"], PROCESS_CUSTODY_SCHEMA),
            _digest(value["invocation_digest"]), _id(value["invocation_id"]),
            _backend_id(value["backend_id"]), _backend_identity(value["controller_identity"]),
            _optional_backend_identity(value["worker_identity"]),
            _digest(value["workspace_content_digest"]), state,
            _boolean(value["request_sent"]), _optional_integer(value["exit_code"]),
            _optional_count(value["active_workload_count"]),
            _optional_digest(value["absence_evidence_digest"]),
            _optional_timestamp(value["absence_verified_at"]),
            _optional_text(value["first_failure"]),
        )
        _validate_custody(record)
        return record


def transition_custody(
    record: ProcessCustodyRecord,
    target: CustodyState,
    *,
    worker_identity: str | None = None,
    exit_code: int | None = None,
    active_workload_count: int | None = None,
    absence_evidence_digest: str | None = None,
    absence_verified_at: str | None = None,
    first_failure: str | None = None,
) -> ProcessCustodyRecord:
    if target not in LEGAL_CUSTODY_TRANSITIONS[record.state]:
        raise LabValidationError("INTEGRATION_CUSTODY_TRANSITION_INVALID", "custody transition is not legal")
    value = record.to_dict()
    value["state"] = str(target)
    if target is CustodyState.ASSIGNED:
        value["worker_identity"] = worker_identity
    elif worker_identity is not None:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "worker identity is set only at assignment")
    if target is CustodyState.DISPATCHING:
        value["request_sent"] = True
    if target in {CustodyState.EXITED, CustodyState.TERMINATED, CustodyState.UNCERTAIN}:
        value["exit_code"] = exit_code
        value["active_workload_count"] = active_workload_count
        if first_failure is not None:
            value["first_failure"] = first_failure
    elif target is not CustodyState.ABSENCE_VERIFIED and (
        exit_code is not None or active_workload_count is not None or first_failure is not None
    ):
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "workload outcome fields are premature")
    if target is CustodyState.ABSENCE_VERIFIED:
        value["active_workload_count"] = active_workload_count
        value["absence_evidence_digest"] = absence_evidence_digest
        value["absence_verified_at"] = absence_verified_at
    elif absence_evidence_digest is not None or absence_verified_at is not None:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "absence evidence is premature")
    return ProcessCustodyRecord.from_mapping(value)


class CustodyBackend(Protocol):
    """Platform backend used only to interpret opaque custody identities."""

    backend_id: str

    def absence_evidence_after_controller_exit(
        self, record: ProcessCustodyRecord,
    ) -> str | None: ...


def recover_absence_after_controller_exit(
    record: ProcessCustodyRecord,
    *,
    backend: CustodyBackend,
    now: Callable[[], str],
) -> tuple[ProcessCustodyRecord, ProcessCustodyRecord] | None:
    """Derive absence only through the backend named by the durable record."""
    try:
        backend_id = _backend_id(backend.backend_id)
        recover = backend.absence_evidence_after_controller_exit
    except (AttributeError, TypeError) as exc:
        raise LabValidationError(
            "INTEGRATION_CUSTODY_BACKEND_INVALID", "custody backend is invalid",
        ) from exc
    if backend_id != record.backend_id or not callable(recover):
        raise LabValidationError(
            "INTEGRATION_CUSTODY_BACKEND_INVALID", "custody backend identity differs",
        )
    if record.state is CustodyState.ABSENCE_VERIFIED:
        return None
    if record.state is not CustodyState.TERMINATED:
        raise LabValidationError("INTEGRATION_OUTCOME_UNCERTAIN", "custody state cannot prove restart absence")
    if (
        not record.request_sent
        or record.worker_identity is None
        or record.active_workload_count != 0
        or record.first_failure is None
    ):
        raise LabValidationError("INTEGRATION_OUTCOME_UNCERTAIN", "custody lacks complete absence evidence")
    evidence_digest = recover(record)
    if evidence_digest is None:
        return None
    verified = transition_custody(
        record,
        CustodyState.ABSENCE_VERIFIED,
        active_workload_count=0,
        absence_evidence_digest=_digest(evidence_digest),
        absence_verified_at=now(),
    )
    return record, verified


class ProcessCustodyStore:
    def __init__(self, state_root) -> None:
        self.records = AtomicRecordStore(state_root)

    def create(self, record: ProcessCustodyRecord) -> None:
        if record.state is not CustodyState.PREPARED:
            raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "new custody must be PREPARED")
        path = self._path(record.invocation_id)
        try:
            self.records.read(path, ProcessCustodyRecord.from_mapping)
        except LabValidationError as exc:
            if exc.code != "STORAGE_RECORD_MISSING":
                raise
        else:
            raise LabValidationError("INTEGRATION_CUSTODY_EXISTS", "custody identity already exists")
        self.records.write(path, record)

    def read(self, invocation_id: str) -> ProcessCustodyRecord:
        return self.records.read(self._path(_id(invocation_id)), ProcessCustodyRecord.from_mapping)

    def save_transition(self, updated: ProcessCustodyRecord, *, expected_digest: str) -> None:
        current = self.read(updated.invocation_id)
        if current.state is CustodyState.ABSENCE_VERIFIED:
            raise LabValidationError("INTEGRATION_CUSTODY_TERMINAL", "verified custody is immutable")
        if current.digest() != _digest(expected_digest):
            raise LabValidationError("INTEGRATION_CUSTODY_STALE_WRITE", "custody snapshot is stale")
        immutable = (
            "schema_version", "invocation_digest", "invocation_id", "backend_id",
            "controller_identity",
            "workspace_content_digest",
        )
        if any(getattr(current, field) != getattr(updated, field) for field in immutable):
            raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "custody identity changed")
        if current.worker_identity is not None and updated.worker_identity != current.worker_identity:
            raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "worker identity changed")
        if (
            current.worker_identity is None
            and updated.worker_identity is not None
            and updated.state is not CustodyState.ASSIGNED
        ):
            raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "worker identity bypassed assignment")
        if current.first_failure is not None and updated.first_failure != current.first_failure:
            raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "first failure changed")
        if updated.state not in LEGAL_CUSTODY_TRANSITIONS[current.state]:
            raise LabValidationError("INTEGRATION_CUSTODY_TRANSITION_INVALID", "custody transition is not legal")
        ProcessCustodyRecord.from_mapping(updated.to_dict())
        self.records.write(self._path(updated.invocation_id), updated)

    @staticmethod
    def _path(invocation_id: str) -> str:
        return f"process-custody/{_id(invocation_id)}.json"


def _validate_custody(record: ProcessCustodyRecord) -> None:
    assigned = record.worker_identity is not None
    if record.state is CustodyState.PREPARED and assigned:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "prepared custody cannot have worker identity")
    if record.state not in {
        CustodyState.PREPARED, CustodyState.TERMINATED, CustodyState.UNCERTAIN,
        CustodyState.ABSENCE_VERIFIED,
    } and not assigned:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "custody state requires worker identity")
    if record.request_sent and not assigned:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "dispatched custody requires worker identity")
    expected_sent = record.state in {
        CustodyState.DISPATCHING, CustodyState.EXITED,
    }
    if expected_sent and assigned and not record.request_sent:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "dispatched custody requires request evidence")
    if record.state in {CustodyState.PREPARED, CustodyState.ASSIGNED} and record.request_sent:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "request evidence is premature")
    if record.state in {CustodyState.TERMINATED, CustodyState.UNCERTAIN} and record.first_failure is None:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "failed custody requires first failure")
    if record.state is CustodyState.EXITED and record.exit_code is None:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "exited custody requires exit code")
    if record.state is CustodyState.ABSENCE_VERIFIED:
        if (
            record.active_workload_count != 0
            or record.absence_evidence_digest is None
            or record.absence_verified_at is None
        ):
            raise LabValidationError(
                "INTEGRATION_CUSTODY_INVALID",
                "absence proof requires zero active workloads, backend evidence, and time",
            )
    elif record.absence_evidence_digest is not None or record.absence_verified_at is not None:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "absence proof is premature")


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "text field is invalid")
    return value


def _optional_text(value: Any) -> str | None:
    return None if value is None else _text(value)


def _id(value: Any) -> str:
    text = _text(value)
    if not _ID_RE.fullmatch(text):
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "identifier is invalid")
    return text


def _digest(value: Any) -> str:
    text = _text(value)
    if not _DIGEST_RE.fullmatch(text):
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "digest is invalid")
    return text


def _optional_digest(value: Any) -> str | None:
    return None if value is None else _digest(value)


def _backend_id(value: Any) -> str:
    text = _text(value)
    if _BACKEND_ID_RE.fullmatch(text) is None:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "backend identifier is invalid")
    return text


def _backend_identity(value: Any) -> str:
    text = _text(value)
    if _BACKEND_IDENTITY_RE.fullmatch(text) is None:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "backend identity is invalid")
    return text


def _optional_backend_identity(value: Any) -> str | None:
    return None if value is None else _backend_identity(value)


def _exact(value: Any, expected: str) -> str:
    if _text(value) != expected:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "unsupported custody value")
    return expected


def _optional_integer(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "integer required")
    return value


def _optional_count(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "non-negative workload count required")
    return value


def _boolean(value: Any) -> bool:
    if not isinstance(value, bool):
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "boolean required")
    return value


def _timestamp(value: Any) -> str:
    text = _text(value)
    if not text.endswith("Z"):
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "UTC timestamp required")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "timestamp is invalid") from exc
    if parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != text:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "timestamp must use UTC second precision")
    return text


def _optional_timestamp(value: Any) -> str | None:
    return None if value is None else _timestamp(value)
