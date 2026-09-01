from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from .canonical import canonical_json
from .errors import LabValidationError
from .integration import InvocationRecord, ResultRecord
from .models import (
    AttemptRecord,
    CurriculumRecord,
    EvidenceRecord,
    ExerciseRecord,
    FailureRecord,
)
from .operator_control import DoctorReport, inspect_installation
from .policy import ContextManifest, PolicyRecord, RoleRecord
from .storage import AtomicRecordStore
from .test_catalog import TestCatalog


HEALTH_SCHEMA = "worker-lab-service-health:v1"
INSTALLATION_STATUS_SCHEMA = "worker-lab-service-installation-status:v1"
RECORD_LIST_SCHEMA = "worker-lab-service-record-list:v1"
RECORD_DETAIL_SCHEMA = "worker-lab-service-record-detail:v1"

COLLECTIONS = (
    "attempts",
    "catalogs",
    "contexts",
    "curricula",
    "evidence",
    "exercises",
    "failures",
    "invocations",
    "policies",
    "results",
    "roles",
)

_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._@-]{1,127}$")


class _Record(Protocol):
    schema_version: str

    def to_dict(self) -> dict[str, Any]: ...

    def digest(self) -> str: ...


Loader = Callable[[Any], _Record]
Identity = Callable[[_Record], str]
State = Callable[[_Record], str | None]


@dataclass(frozen=True)
class _CollectionSpec:
    storage_root: str
    directory: str
    loader: Loader
    identity: Identity
    state: State


@dataclass(frozen=True)
class RecordSummaryDTO:
    collection: str
    identity: str
    schema_version: str
    record_digest: str
    state: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "collection": self.collection,
            "identity": self.identity,
            "schema_version": self.schema_version,
            "record_digest": self.record_digest,
            "state": self.state,
        }


@dataclass(frozen=True)
class RecordListDTO:
    collection: str
    items: tuple[RecordSummaryDTO, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RECORD_LIST_SCHEMA,
            "collection": self.collection,
            "count": len(self.items),
            "items": [item.to_dict() for item in self.items],
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class RecordDetailDTO:
    summary: RecordSummaryDTO
    record: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RECORD_DETAIL_SCHEMA,
            "summary": self.summary.to_dict(),
            "record": dict(self.record),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class InstallationStatusDTO:
    doctor: DoctorReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": INSTALLATION_STATUS_SCHEMA,
            "installation": self.doctor.to_dict(),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class HealthDTO:
    doctor: DoctorReport
    data_root_state: str
    collection_counts: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": HEALTH_SCHEMA,
            "status": "healthy",
            "data_root_state": self.data_root_state,
            "execution_ready": self.doctor.execution_ready,
            "collection_counts": dict(sorted(self.collection_counts.items())),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


class WorkerLabApplicationService:
    """Read-only application boundary shared by operator clients and the future GUI."""

    def __init__(self, data_root: Path) -> None:
        if not isinstance(data_root, Path) or not data_root.is_absolute():
            raise LabValidationError("SERVICE_DATA_ROOT_INVALID", "service data root must be absolute")
        self.data_root = data_root

    def installation_status(self) -> InstallationStatusDTO:
        _, report = inspect_installation()
        return InstallationStatusDTO(report)

    def health(self) -> HealthDTO:
        _, report = inspect_installation()
        state = self._data_root_state()
        counts = {collection: len(self.list_records(collection).items) for collection in COLLECTIONS}
        return HealthDTO(report, state, counts)

    def list_records(self, collection: str) -> RecordListDTO:
        self._data_root_state()
        spec = _collection(collection)
        store = self._store(spec)
        loaded: list[tuple[str, _Record]] = []
        for path in store.list_paths(spec.directory):
            loaded.append((path, store.read(path, spec.loader)))
        identities: set[str] = set()
        summaries: list[RecordSummaryDTO] = []
        for _, record in loaded:
            summary = _summary(collection, record, spec)
            if summary.identity in identities:
                raise LabValidationError("SERVICE_RECORD_DUPLICATE", "collection contains a duplicate identity")
            identities.add(summary.identity)
            summaries.append(summary)
        return RecordListDTO(collection, tuple(sorted(summaries, key=lambda item: item.identity)))

    def show_record(self, collection: str, identity: str) -> RecordDetailDTO:
        self._data_root_state()
        expected = _identity(identity)
        spec = _collection(collection)
        store = self._store(spec)
        matches: list[_Record] = []
        for path in store.list_paths(spec.directory):
            record = store.read(path, spec.loader)
            if spec.identity(record) == expected:
                matches.append(record)
        if not matches:
            raise LabValidationError("SERVICE_RECORD_MISSING", "requested service record is unavailable")
        if len(matches) != 1:
            raise LabValidationError("SERVICE_RECORD_DUPLICATE", "requested service identity is ambiguous")
        record = matches[0]
        return RecordDetailDTO(_summary(collection, record, spec), record.to_dict())

    def _store(self, spec: _CollectionSpec) -> AtomicRecordStore:
        return AtomicRecordStore(self.data_root / spec.storage_root)

    def _data_root_state(self) -> str:
        if not self.data_root.exists():
            return "absent"
        if (
            self.data_root.is_symlink()
            or getattr(os.lstat(self.data_root), "st_file_attributes", 0) & 0x400
            or not self.data_root.is_dir()
        ):
            raise LabValidationError("SERVICE_DATA_ROOT_INVALID", "service data root must be a real directory")
        try:
            resolved = self.data_root.resolve(strict=True)
        except OSError as exc:
            raise LabValidationError("SERVICE_DATA_ROOT_INVALID", "service data root is unavailable") from exc
        if _path_key(resolved) != _path_key(self.data_root):
            raise LabValidationError("SERVICE_DATA_ROOT_INVALID", "service data root is substituted")
        return "present"


def _collection(value: str) -> _CollectionSpec:
    try:
        return _COLLECTION_SPECS[value]
    except (KeyError, TypeError) as exc:
        raise LabValidationError("SERVICE_COLLECTION_INVALID", "service collection is unsupported") from exc


def _summary(collection: str, record: _Record, spec: _CollectionSpec) -> RecordSummaryDTO:
    identity = _identity(spec.identity(record))
    state = spec.state(record)
    if state is not None and (not isinstance(state, str) or not state or state != state.strip()):
        raise LabValidationError("SERVICE_RECORD_INVALID", "service record state is invalid")
    return RecordSummaryDTO(collection, identity, record.schema_version, record.digest(), state)


def _identity(value: Any) -> str:
    if not isinstance(value, str) or not _IDENTITY_RE.fullmatch(value):
        raise LabValidationError("SERVICE_IDENTITY_INVALID", "service record identity is invalid")
    return value


def _versioned(name: str, version: int) -> str:
    return f"{name}@v{version}"


def _state(name: str) -> State:
    def read(record: _Record) -> str | None:
        value = getattr(record, name)
        return str(value)

    return read


def _none(record: _Record) -> None:
    del record
    return None


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


_COLLECTION_SPECS: Mapping[str, _CollectionSpec] = {
    "attempts": _CollectionSpec("state", "attempts", AttemptRecord.from_mapping, lambda item: item.attempt_id, _state("state")),
    "catalogs": _CollectionSpec("curricula", "catalogs", TestCatalog.from_mapping, lambda item: item.catalog_version, _none),
    "contexts": _CollectionSpec("curricula", "contexts", ContextManifest.from_mapping, lambda item: _versioned(item.manifest_id, item.manifest_version), _none),
    "curricula": _CollectionSpec("curricula", "curricula", CurriculumRecord.from_mapping, lambda item: item.curriculum_id, _state("status")),
    "evidence": _CollectionSpec("state", "evidence", EvidenceRecord.from_mapping, lambda item: item.evidence_digest, _state("verification_state")),
    "exercises": _CollectionSpec("curricula", "exercises", ExerciseRecord.from_mapping, lambda item: _versioned(item.exercise_id, item.exercise_version), _none),
    "failures": _CollectionSpec("state", "failures", FailureRecord.from_mapping, lambda item: item.failure_id, _state("classification")),
    "invocations": _CollectionSpec("state", "invocations", InvocationRecord.from_mapping, lambda item: item.invocation_id, _state("state")),
    "policies": _CollectionSpec("curricula", "policies", PolicyRecord.from_mapping, lambda item: _versioned(item.policy_id, item.policy_version), _none),
    "results": _CollectionSpec("state", "results", ResultRecord.from_mapping, lambda item: item.invocation_id, _state("process_outcome")),
    "roles": _CollectionSpec("curricula", "roles", RoleRecord.from_mapping, lambda item: _versioned(item.role_id, item.role_version), _none),
}

if tuple(sorted(_COLLECTION_SPECS)) != COLLECTIONS:
    raise RuntimeError("service collection declaration differs")
