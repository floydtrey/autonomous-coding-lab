from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.policy import (
    CONTEXT_MANIFEST_SCHEMA,
    POLICY_SCHEMA,
    ROLE_SCHEMA,
    ContextManifest,
    PolicyRecord,
    RoleRecord,
    validate_authority,
    verify_context_files,
)


DIGEST = "sha256:" + "a" * 64
SHA = "b" * 40


def policy_mapping() -> dict:
    return {
        "schema_version": POLICY_SCHEMA,
        "policy_id": "core-worker-policy",
        "policy_version": 1,
        "invariants": [
            {"rule_id": "P001", "statement": "Use managed authentication only."},
            {"rule_id": "P002", "statement": "Stop at the first failed boundary."},
        ],
        "permanent_capabilities": [
            "candidate.modify-authorized",
            "context.read-assigned",
            "evidence.write-worker-log",
            "plan.propose",
            "tests.run-authorized",
        ],
    }


def role_mapping() -> dict:
    return {
        "schema_version": ROLE_SCHEMA,
        "role_id": "coding-worker",
        "role_version": 1,
        "purpose": "Implement one bounded task.",
        "allowed_capabilities": [
            "candidate.modify-authorized",
            "context.read-assigned",
            "evidence.write-worker-log",
            "tests.run-authorized",
        ],
        "denied_capabilities": ["evaluator.modify", "git.publish"],
        "required_outputs": ["protected-test-results:v1", "worker-output:v1", "workspace-diff:v1"],
    }


def context_mapping() -> dict:
    return {
        "schema_version": CONTEXT_MANIFEST_SCHEMA,
        "manifest_id": "record-model-context",
        "manifest_version": 1,
        "repository": "local/record-ledger-template",
        "starting_commit": SHA,
        "files": [
            {"path": "README.md", "digest": DIGEST, "purpose": "Exercise instructions."},
            {"path": "record_ledger/models.py", "digest": DIGEST, "purpose": "Target module."},
        ],
    }


def test_policy_role_and_context_round_trip_deterministically() -> None:
    policy = PolicyRecord.from_mapping(policy_mapping())
    role = RoleRecord.from_mapping(role_mapping())
    context = ContextManifest.from_mapping(context_mapping())
    assert PolicyRecord.from_mapping(policy.to_dict()) == policy
    assert RoleRecord.from_mapping(role.to_dict()) == role
    assert ContextManifest.from_mapping(context.to_dict()) == context
    assert context.digest() == ContextManifest.from_mapping(context.to_dict()).digest()


def test_task_restrictions_can_narrow_role_authority() -> None:
    with pytest.raises(LabValidationError) as error:
        validate_authority(
            PolicyRecord.from_mapping(policy_mapping()),
            RoleRecord.from_mapping(role_mapping()),
            required_capabilities=("candidate.modify-authorized",),
            temporary_denied_capabilities=("candidate.modify-authorized",),
        )
    assert error.value.code == "ROLE_UNSUPPORTED"


def test_role_cannot_grant_capability_absent_from_permanent_policy() -> None:
    value = role_mapping()
    value["allowed_capabilities"].append("network.access")
    value["allowed_capabilities"].sort()
    with pytest.raises(LabValidationError) as error:
        validate_authority(
            PolicyRecord.from_mapping(policy_mapping()),
            RoleRecord.from_mapping(value),
            required_capabilities=(),
            temporary_denied_capabilities=(),
        )
    assert error.value.code == "ROLE_AUTHORITY_INVALID"


@pytest.mark.parametrize("path", ["../secret", "/absolute", "C:/secret", "a\\b"])
def test_context_manifest_rejects_unsafe_paths(path: str) -> None:
    value = deepcopy(context_mapping())
    value["files"][0]["path"] = path
    value["files"].sort(key=lambda item: item["path"])
    with pytest.raises(LabValidationError) as error:
        ContextManifest.from_mapping(value)
    assert error.value.code == "CONTEXT_PATH_INVALID"


def test_unknown_policy_fields_fail_closed() -> None:
    value = policy_mapping()
    value["surprise"] = True
    with pytest.raises(LabValidationError) as error:
        PolicyRecord.from_mapping(value)
    assert error.value.code == "POLICY_FIELDS_INVALID"


def test_context_files_are_verified_against_exact_content(tmp_path: Path) -> None:
    root = tmp_path / "target"
    (root / "record_ledger").mkdir(parents=True)
    (root / "README.md").write_text("instructions\n", encoding="utf-8")
    (root / "record_ledger" / "models.py").write_text("# model\n", encoding="utf-8")
    value = context_mapping()
    for item in value["files"]:
        content = (root / item["path"]).read_bytes()
        item["digest"] = "sha256:" + hashlib.sha256(content).hexdigest()
    manifest = ContextManifest.from_mapping(value)
    verify_context_files(manifest, root)
    (root / "README.md").write_text("changed\n", encoding="utf-8")
    with pytest.raises(LabValidationError) as error:
        verify_context_files(manifest, root)
    assert error.value.code == "CONTEXT_DIGEST_MISMATCH"
