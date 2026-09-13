from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, TypeVar

from .errors import LabValidationError
from .provider_qualification import (
    ProviderCapabilityQualification,
    ProviderInstallationObservation,
)
from .storage import AtomicRecordStore


_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
RecordT = TypeVar(
    "RecordT",
    ProviderInstallationObservation,
    ProviderCapabilityQualification,
)


class _DigestRecordStore:
    def __init__(
        self,
        state_root: Path,
        *,
        directory: str,
        loader: Callable[[object], RecordT],
    ) -> None:
        self.records = AtomicRecordStore(state_root)
        self.directory = directory
        self.loader = loader

    def create(self, record: RecordT) -> RecordT:
        validated = self.loader(record.to_dict())
        identity = validated.digest()
        path = self._path(identity)
        try:
            self.records.read(path, self.loader)
        except LabValidationError as exc:
            if exc.code != "STORAGE_RECORD_MISSING":
                raise
        else:
            raise LabValidationError(
                "PROVIDER_RECORD_EXISTS",
                "provider admission record identity already exists",
            )
        self.records.write(path, validated)
        return validated

    def read(self, expected_digest: str) -> RecordT:
        expected = _digest(expected_digest)
        record = self.records.read(self._path(expected), self.loader)
        if record.digest() != expected:
            raise LabValidationError(
                "PROVIDER_RECORD_MISMATCH",
                "provider admission record differs from its content identity",
            )
        return record

    def _path(self, digest: str) -> str:
        return f"{self.directory}/{_digest(digest)[7:]}.json"


class ProviderInstallationObservationStore(_DigestRecordStore):
    def __init__(self, state_root: Path) -> None:
        super().__init__(
            state_root,
            directory="provider-installation-observations",
            loader=ProviderInstallationObservation.from_mapping,
        )


class ProviderCapabilityQualificationStore(_DigestRecordStore):
    def __init__(self, state_root: Path) -> None:
        super().__init__(
            state_root,
            directory="provider-capability-qualifications",
            loader=ProviderCapabilityQualification.from_mapping,
        )


def _digest(value: object) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise LabValidationError(
            "PROVIDER_RECORD_IDENTITY_INVALID",
            "provider admission record digest is invalid",
        )
    return value
