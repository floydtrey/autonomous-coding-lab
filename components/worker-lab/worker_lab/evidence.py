from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .attempt_store import AttemptStore
from .canonical import canonical_digest
from .errors import LabValidationError
from .models import EvidenceRecord
from .storage import AtomicRecordStore
from .test_catalog import TestCatalog


DIGEST_RE = re.compile(r"^sha256:([0-9a-f]{64})$")


def content_digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def evidence_identity_digest(record: EvidenceRecord, retained_content_digest: str) -> str:
    if DIGEST_RE.fullmatch(retained_content_digest) is None:
        raise LabValidationError("EVIDENCE_CONTENT_DIGEST_INVALID", "content digest is invalid")
    identity = record.to_dict()
    identity.pop("evidence_digest")
    identity["retained_content_digest"] = retained_content_digest
    return canonical_digest(identity)


def verify_evidence(lab_root: Path, requested_digest: str) -> EvidenceRecord:
    match = DIGEST_RE.fullmatch(requested_digest)
    if match is None:
        raise LabValidationError("EVIDENCE_DIGEST_INVALID", "requested digest is invalid")
    state = AtomicRecordStore(lab_root / "state")
    record = state.read(
        f"evidence/{match.group(1)}.json",
        EvidenceRecord.from_mapping,
    )
    if record.evidence_digest != requested_digest:
        raise LabValidationError("EVIDENCE_IDENTITY_MISMATCH", "requested digest differs from record")
    attempt = AttemptStore(lab_root / "state").read(record.attempt_id)
    if attempt.candidate_digest is None:
        raise LabValidationError("EVIDENCE_ATTEMPT_INVALID", "attempt has no immutable candidate")
    if (
        record.candidate_digest != attempt.candidate_digest
        or record.base_commit != attempt.starting_commit
        or record.test_catalog_version != attempt.evaluator_catalog_version
        or record.test_catalog_digest != attempt.evaluator_catalog_digest
    ):
        raise LabValidationError(
            "EVIDENCE_ATTEMPT_MISMATCH",
            "evidence candidate, base, or catalog differs from its attempt",
        )
    catalog = AtomicRecordStore(lab_root / "curricula").read(
        f"catalogs/{attempt.evaluator_catalog_version}.json",
        TestCatalog.from_mapping,
    )
    if (
        catalog.catalog_version != attempt.evaluator_catalog_version
        or catalog.digest() != attempt.evaluator_catalog_digest
    ):
        raise LabValidationError("EVIDENCE_CATALOG_MISMATCH", "attempt catalog identity is unresolved")
    if record.test_id not in {test.test_id for test in catalog.tests}:
        raise LabValidationError("EVIDENCE_TEST_UNKNOWN", "evidence test is not in the bound catalog")
    if record.content_path is None:
        raise LabValidationError(
            "EVIDENCE_CONTENT_UNAVAILABLE",
            "external evidence cannot be independently content-verified",
        )
    content_path = _contained_file(lab_root / "state", record.content_path)
    actual_content_digest = content_digest(content_path.read_bytes())
    if evidence_identity_digest(record, actual_content_digest) != record.evidence_digest:
        raise LabValidationError(
            "EVIDENCE_CONTENT_MISMATCH",
            "retained content or evidence identity differs from its digest",
        )
    return record


def _contained_file(root: Path, relative_path: str) -> Path:
    try:
        resolved_root = root.resolve(strict=True)
        target = root.joinpath(*relative_path.split("/"))
        if target.is_symlink():
            raise LabValidationError("EVIDENCE_PATH_INVALID", "evidence content cannot be a symlink")
        resolved = target.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except LabValidationError:
        raise
    except (OSError, ValueError) as exc:
        raise LabValidationError(
            "EVIDENCE_PATH_INVALID", "evidence content is missing or outside state storage"
        ) from exc
    if not resolved.is_file():
        raise LabValidationError("EVIDENCE_PATH_INVALID", "evidence content must be a file")
    return resolved
