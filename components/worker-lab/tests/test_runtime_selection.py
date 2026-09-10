import pytest

from worker_lab.errors import LabValidationError
from worker_lab.integration import (
    FRAMEWORK_CONTRACT_VERSION,
    INVOCATION_SCHEMA,
    RUNTIME_MODEL,
    RUNTIME_PROFILE,
    RUNTIME_REASONING_EFFORT,
    RUNTIME_TIMEOUT_SECONDS,
    WORKER_LAB_CONTRACT_VERSION,
    InvocationRecord,
)
from worker_lab.runtime_selection import (
    CODING_WORKER_V1,
    LEGACY_TERRA_V1,
    HOST_QUALIFIED_ONLY,
    PROVIDER_QUALIFIED,
    resolve_runtime_requirement,
    selected_runtime_requirement,
)


DIGEST = "sha256:" + "a" * 64
SHA = "a" * 40


def _invocation(**updates):
    value = {
        "schema_version": INVOCATION_SCHEMA,
        "invocation_id": "INVOCATION-001",
        "attempt_id": "ATTEMPT-001",
        "operation": "read-only-proposal",
        "exercise_id": "exercise",
        "exercise_version": 1,
        "exercise_digest": DIGEST,
        "policy_id": "policy",
        "policy_version": 1,
        "policy_digest": DIGEST,
        "role_id": "role",
        "role_version": 1,
        "role_digest": DIGEST,
        "context_manifest_id": "context",
        "context_manifest_version": 1,
        "context_digest": DIGEST,
        "task_digest": DIGEST,
        "test_catalog_version": "worker-lab-v3",
        "test_catalog_digest": DIGEST,
        "test_plan_digest": DIGEST,
        "test_ids": ["T001"],
        "worker_lab_installation_digest": DIGEST,
        "worker_lab_contract_version": WORKER_LAB_CONTRACT_VERSION,
        "framework_installation_digest": DIGEST,
        "framework_contract_version": FRAMEWORK_CONTRACT_VERSION,
        "workspace_receipt_digest": DIGEST,
        "workspace_root_digest": DIGEST,
        "workspace_path_digest": DIGEST,
        "starting_commit": SHA,
        "sandbox_mode": "read-only",
        "runtime_profile_id": RUNTIME_PROFILE,
        "model": RUNTIME_MODEL,
        "reasoning_effort": RUNTIME_REASONING_EFFORT,
        "timeout_seconds": RUNTIME_TIMEOUT_SECONDS,
        "readable_paths": [{"path": "README.md", "digest": DIGEST}],
        "writable_paths": [],
        "prompt_digest": DIGEST,
        "authorized_by": None,
        "authorized_at": None,
        "state": "PREPARED",
        "result_digest": None,
    }
    value.update(updates)
    return value


def test_selected_requirement_is_provider_neutral_and_host_qualified_only():
    requirement = selected_runtime_requirement()
    assert requirement is CODING_WORKER_V1
    assert requirement.profile_id == "coding-worker:v1"
    assert requirement.capability == "bounded-code-task"
    assert requirement.provider_selection == HOST_QUALIFIED_ONLY
    assert requirement.model_selector == PROVIDER_QUALIFIED
    assert requirement.reasoning_selector == PROVIDER_QUALIFIED
    assert requirement.invocation_fields() == {
        "runtime_profile_id": "coding-worker:v1",
        "model": PROVIDER_QUALIFIED,
        "reasoning_effort": PROVIDER_QUALIFIED,
        "timeout_seconds": 900,
    }
    assert requirement.digest().startswith("sha256:")


def test_new_invocation_fields_resolve_to_selected_protected_requirement():
    record = InvocationRecord.from_mapping(_invocation())
    resolved = resolve_runtime_requirement(
        record.runtime_profile_id,
        record.model,
        record.reasoning_effort,
        record.timeout_seconds,
    )
    assert resolved is CODING_WORKER_V1


def test_legacy_terra_record_remains_parseable_but_is_not_selected():
    record = InvocationRecord.from_mapping(
        _invocation(
            runtime_profile_id=LEGACY_TERRA_V1.profile_id,
            model=LEGACY_TERRA_V1.model_selector,
            reasoning_effort=LEGACY_TERRA_V1.reasoning_selector,
            timeout_seconds=LEGACY_TERRA_V1.timeout_seconds,
        )
    )
    assert record.runtime_profile_id == "terra-medium:v1"
    assert selected_runtime_requirement() is not LEGACY_TERRA_V1


def test_arbitrary_runtime_substitution_fails_closed():
    with pytest.raises(LabValidationError) as error:
        InvocationRecord.from_mapping(_invocation(model="unreviewed-model"))
    assert error.value.code == "INTEGRATION_RUNTIME_INVALID"
