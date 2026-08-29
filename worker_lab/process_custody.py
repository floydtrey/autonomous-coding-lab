from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping

from .canonical import canonical_digest
from .errors import LabValidationError
from .storage import AtomicRecordStore


PROCESS_CUSTODY_SCHEMA = "worker-lab-process-custody:v1"
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{5,95}$")


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
    controller_pid: int
    controller_creation_time_100ns: int
    adapter_pid: int | None
    adapter_creation_time_100ns: int | None
    containment_mode: str
    state: CustodyState
    request_sent: bool
    exit_code: int | None
    active_process_count: int | None
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
            _positive(value["controller_pid"]), _positive(value["controller_creation_time_100ns"]),
            _optional_positive(value["adapter_pid"]), _optional_positive(value["adapter_creation_time_100ns"]),
            _exact(value["containment_mode"], "windows-job-kill-on-close"), state,
            _boolean(value["request_sent"]), _optional_integer(value["exit_code"]),
            _optional_count(value["active_process_count"]), _optional_timestamp(value["absence_verified_at"]),
            _optional_text(value["first_failure"]),
        )
        _validate_custody(record)
        return record


def transition_custody(
    record: ProcessCustodyRecord,
    target: CustodyState,
    *,
    adapter_pid: int | None = None,
    adapter_creation_time_100ns: int | None = None,
    exit_code: int | None = None,
    active_process_count: int | None = None,
    absence_verified_at: str | None = None,
    first_failure: str | None = None,
) -> ProcessCustodyRecord:
    if target not in LEGAL_CUSTODY_TRANSITIONS[record.state]:
        raise LabValidationError("INTEGRATION_CUSTODY_TRANSITION_INVALID", "custody transition is not legal")
    value = record.to_dict()
    value["state"] = str(target)
    if target is CustodyState.ASSIGNED:
        value["adapter_pid"] = adapter_pid
        value["adapter_creation_time_100ns"] = adapter_creation_time_100ns
    elif adapter_pid is not None or adapter_creation_time_100ns is not None:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "adapter identity is set only at assignment")
    if target is CustodyState.DISPATCHING:
        value["request_sent"] = True
    if target in {CustodyState.EXITED, CustodyState.TERMINATED, CustodyState.UNCERTAIN}:
        value["exit_code"] = exit_code
        value["active_process_count"] = active_process_count
        if first_failure is not None:
            value["first_failure"] = first_failure
    elif target is not CustodyState.ABSENCE_VERIFIED and (
        exit_code is not None or active_process_count is not None or first_failure is not None
    ):
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "process outcome fields are premature")
    if target is CustodyState.ABSENCE_VERIFIED:
        value["active_process_count"] = active_process_count
        value["absence_verified_at"] = absence_verified_at
    elif absence_verified_at is not None:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "absence time is premature")
    return ProcessCustodyRecord.from_mapping(value)


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
            "schema_version", "invocation_digest", "invocation_id", "controller_pid",
            "controller_creation_time_100ns", "containment_mode",
        )
        if any(getattr(current, field) != getattr(updated, field) for field in immutable):
            raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "custody identity changed")
        if current.adapter_pid is not None and (
            updated.adapter_pid != current.adapter_pid
            or updated.adapter_creation_time_100ns != current.adapter_creation_time_100ns
        ):
            raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "adapter identity changed")
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
    assigned = record.adapter_pid is not None and record.adapter_creation_time_100ns is not None
    if (record.adapter_pid is None) != (record.adapter_creation_time_100ns is None):
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "adapter process identity is incomplete")
    if record.state is CustodyState.PREPARED and assigned:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "prepared custody cannot have adapter identity")
    if record.state not in {
        CustodyState.PREPARED, CustodyState.TERMINATED, CustodyState.UNCERTAIN,
        CustodyState.ABSENCE_VERIFIED,
    } and not assigned:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "custody state requires adapter identity")
    expected_sent = record.state in {
        CustodyState.DISPATCHING, CustodyState.EXITED, CustodyState.ABSENCE_VERIFIED,
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
        if record.active_process_count != 0 or record.absence_verified_at is None:
            raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "absence proof requires zero active processes and time")
    elif record.absence_verified_at is not None:
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


def _exact(value: Any, expected: str) -> str:
    if _text(value) != expected:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "unsupported custody value")
    return expected


def _positive(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "positive integer required")
    return value


def _optional_positive(value: Any) -> int | None:
    return None if value is None else _positive(value)


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
        raise LabValidationError("INTEGRATION_CUSTODY_INVALID", "non-negative process count required")
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
