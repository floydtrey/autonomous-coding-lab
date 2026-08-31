import json
from pathlib import Path

import pytest

from worker_lab.evidence import content_digest, evidence_identity_digest, verify_evidence
from worker_lab.errors import LabValidationError
from worker_lab.cli import main
from worker_lab.models import AttemptRecord, EvidenceRecord
from tests.test_models import attempt_mapping, evidence_mapping
from tests.test_test_catalog import catalog


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def evidence_fixture(tmp_path: Path) -> tuple[Path, str, dict]:
    lab = tmp_path / "lab"
    tests = catalog()
    attempt = attempt_mapping()
    attempt.update({
        "state": "EVALUATING",
        "candidate_digest": "sha256:" + "a" * 64,
        "evaluator_catalog_digest": tests.digest(),
    })
    write_json(lab / "state" / "attempts" / f"{attempt['attempt_id']}.json", attempt)
    write_json(lab / "curricula" / "catalogs" / "worker-lab-v1.json", tests.to_dict())
    content = b'{"exit_code":0,"summary":"passed"}\n'
    content_path = lab / "state" / "evidence-content" / "result.json"
    content_path.parent.mkdir(parents=True)
    content_path.write_bytes(content)
    evidence = evidence_mapping()
    evidence.update({
        "content_path": "evidence-content/result.json",
        "external_reference": None,
        "test_catalog_digest": tests.digest(),
        "verification_state": "unverified",
    })
    provisional = EvidenceRecord.from_mapping(evidence)
    digest = evidence_identity_digest(provisional, content_digest(content))
    evidence["evidence_digest"] = digest
    write_json(lab / "state" / "evidence" / f"{digest.removeprefix('sha256:')}.json", evidence)
    return lab, digest, evidence


def test_evidence_verification_hashes_content_and_resolves_authority(tmp_path: Path) -> None:
    lab, digest, evidence = evidence_fixture(tmp_path)
    assert verify_evidence(lab, digest) == EvidenceRecord.from_mapping(evidence)


def test_cli_reports_verified_only_after_content_verification(
    tmp_path: Path, capsys
) -> None:
    lab, digest, _ = evidence_fixture(tmp_path)
    assert main(["--root", str(lab), "verify-evidence", digest]) == 0
    assert capsys.readouterr().out.strip() == f"VERIFIED {digest}"
    (lab / "state" / "evidence-content" / "result.json").write_text(
        "changed", encoding="utf-8"
    )
    assert main(["--root", str(lab), "verify-evidence", digest]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "ERROR EVIDENCE_CONTENT_MISMATCH" in captured.err


def test_changed_retained_content_fails_closed(tmp_path: Path) -> None:
    lab, digest, _ = evidence_fixture(tmp_path)
    (lab / "state" / "evidence-content" / "result.json").write_text(
        "changed", encoding="utf-8"
    )
    with pytest.raises(LabValidationError) as raised:
        verify_evidence(lab, digest)
    assert raised.value.code == "EVIDENCE_CONTENT_MISMATCH"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_digest", "sha256:" + "b" * 64),
        ("base_commit", "c" * 40),
        ("test_catalog_version", "other-v1"),
        ("test_catalog_digest", "sha256:" + "b" * 64),
    ],
)
def test_evidence_must_match_bound_attempt(
    tmp_path: Path, field: str, value: str
) -> None:
    lab, _, evidence = evidence_fixture(tmp_path)
    evidence[field] = value
    record = EvidenceRecord.from_mapping(evidence)
    content = (lab / "state" / "evidence-content" / "result.json").read_bytes()
    digest = evidence_identity_digest(record, content_digest(content))
    evidence["evidence_digest"] = digest
    write_json(lab / "state" / "evidence" / f"{digest.removeprefix('sha256:')}.json", evidence)
    with pytest.raises(LabValidationError) as raised:
        verify_evidence(lab, digest)
    assert raised.value.code == "EVIDENCE_ATTEMPT_MISMATCH"


def test_environment_is_part_of_evidence_identity(tmp_path: Path) -> None:
    lab, _, evidence = evidence_fixture(tmp_path)
    record = EvidenceRecord.from_mapping(evidence)
    retained = content_digest(
        (lab / "state" / "evidence-content" / "result.json").read_bytes()
    )
    changed = {**evidence, "environment_digest": "sha256:" + "b" * 64}
    assert evidence_identity_digest(record, retained) != evidence_identity_digest(
        EvidenceRecord.from_mapping(changed), retained
    )


def test_unknown_test_identity_fails_closed(tmp_path: Path) -> None:
    lab, _, evidence = evidence_fixture(tmp_path)
    evidence["test_id"] = "T999"
    record = EvidenceRecord.from_mapping(evidence)
    retained = content_digest(
        (lab / "state" / "evidence-content" / "result.json").read_bytes()
    )
    digest = evidence_identity_digest(record, retained)
    evidence["evidence_digest"] = digest
    write_json(lab / "state" / "evidence" / f"{digest.removeprefix('sha256:')}.json", evidence)
    with pytest.raises(LabValidationError) as raised:
        verify_evidence(lab, digest)
    assert raised.value.code == "EVIDENCE_TEST_UNKNOWN"


def test_external_reference_cannot_claim_local_verification(tmp_path: Path) -> None:
    lab, _, evidence = evidence_fixture(tmp_path)
    evidence.update({"content_path": None, "external_reference": "https://example.invalid/result"})
    record = EvidenceRecord.from_mapping(evidence)
    digest = evidence_identity_digest(record, content_digest(b"not locally retained"))
    evidence["evidence_digest"] = digest
    write_json(lab / "state" / "evidence" / f"{digest.removeprefix('sha256:')}.json", evidence)
    with pytest.raises(LabValidationError) as raised:
        verify_evidence(lab, digest)
    assert raised.value.code == "EVIDENCE_CONTENT_UNAVAILABLE"
