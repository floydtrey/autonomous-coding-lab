import json
import sys
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.integration_v3 import (
    FRAMEWORK_DISPATCH_CONTRACT_V1,
    GIT_RESULT_EVIDENCE_SCHEMA,
    GIT_SOURCE_STATE_SCHEMA,
    INVOCATION_SCHEMA_V3,
    RESULT_SCHEMA_V3,
    WORKER_LAB_CONTRACT_VERSION_V3,
    InvocationRecordV3,
    InvocationState,
    ResultRecordV3,
    authorize_invocation,
    transition_invocation,
    validate_result_for_invocation,
)
from worker_lab.provider_binding import ProviderBindingStore, create_provider_binding
from worker_lab.provider_qualification import (
    QUALIFICATION_SCHEMA,
    PYDANTIC_AI_OLLAMA_V1,
    HostProviderQualification,
)
from worker_lab.runtime_selection import selected_runtime_requirement_v3


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
DIGEST_D = "sha256:" + "d" * 64
SHA_A = "a" * 40


def qualification():
    from tests.provider_capability_fixture import capability_qualification

    return capability_qualification(model_name="qwen2.5-coder:7b")


def invocation(binding, *, operation="workspace-write-code-task", **updates):
    requirement = selected_runtime_requirement_v3()
    read_only = operation == "read-only-proposal"
    value = {
        "schema_version": INVOCATION_SCHEMA_V3,
        "invocation_id": "INVOCATION-001",
        "attempt_id": "ATTEMPT-001",
        "operation": operation,
        "logical_target_id": "target:acl",
        "workspace_id": "workspace:ATTEMPT-001",
        "exercise_id": "exercise",
        "exercise_version": 1,
        "exercise_digest": DIGEST_A,
        "policy_id": "policy",
        "policy_version": 1,
        "policy_digest": DIGEST_A,
        "role_id": "role",
        "role_version": 1,
        "role_digest": DIGEST_A,
        "context_manifest_id": "context",
        "context_manifest_version": 1,
        "context_digest": DIGEST_A,
        "task_digest": DIGEST_A,
        "controller_task_packet_digest": DIGEST_B,
        "prompt_digest": DIGEST_C,
        "test_catalog_version": "worker-lab-v3",
        "test_catalog_digest": DIGEST_A,
        "test_plan_digest": DIGEST_B,
        "test_ids": ["T001"],
        "worker_lab_source_digest": DIGEST_A,
        "worker_lab_contract_version": WORKER_LAB_CONTRACT_VERSION_V3,
        "framework_source_digest": DIGEST_B,
        "framework_contract_version": FRAMEWORK_DISPATCH_CONTRACT_V1,
        "runtime_requirement_profile_id": requirement.profile_id,
        "runtime_requirement_digest": requirement.digest(),
        "provider_binding_id": binding.binding_id,
        "provider_binding_digest": binding.digest(),
        "sandbox_mode": "read-only" if read_only else "workspace-write",
        "readable_paths": [{"path": "README.md", "digest": DIGEST_A}],
        "writable_paths": [] if read_only else ["README.md"],
        "source_state": {
            "schema_version": GIT_SOURCE_STATE_SCHEMA,
            "backend_id": "git-workspace:v1",
            "base_commit": SHA_A,
            "workspace_receipt_digest": DIGEST_A,
            "workspace_root_digest": DIGEST_B,
            "workspace_path_digest": DIGEST_C,
        },
        "authorized_by": None,
        "authorized_at": None,
        "state": "PREPARED",
        "result_digest": None,
    }
    value.update(updates)
    return InvocationRecordV3.from_mapping(value)


def result(invocation_record, **updates):
    source = invocation_record.source_state
    read_only = invocation_record.operation.value == "read-only-proposal"
    value = {
        "schema_version": RESULT_SCHEMA_V3,
        "invocation_digest": invocation_record.identity_digest(),
        "request_digest": invocation_record.identity_digest(),
        "invocation_id": invocation_record.invocation_id,
        "attempt_id": invocation_record.attempt_id,
        "operation": str(invocation_record.operation),
        "logical_target_id": invocation_record.logical_target_id,
        "workspace_id": invocation_record.workspace_id,
        "framework_source_digest": invocation_record.framework_source_digest,
        "framework_contract_version": invocation_record.framework_contract_version,
        "runtime_requirement_profile_id": invocation_record.runtime_requirement_profile_id,
        "runtime_requirement_digest": invocation_record.runtime_requirement_digest,
        "provider_binding_id": invocation_record.provider_binding_id,
        "provider_binding_digest": invocation_record.provider_binding_digest,
        "runtime_identity": invocation_record.provider_binding_digest,
        "controller_task_packet_digest": invocation_record.controller_task_packet_digest,
        "prompt_digest": invocation_record.prompt_digest,
        "test_catalog_version": invocation_record.test_catalog_version,
        "test_catalog_digest": invocation_record.test_catalog_digest,
        "test_plan_digest": invocation_record.test_plan_digest,
        "test_ids": list(invocation_record.test_ids),
        "process_outcome": "pass",
        "process_identity": DIGEST_A,
        "process_started_at": "2026-09-11T00:00:00Z",
        "process_ended_at": "2026-09-11T00:00:01Z",
        "source_evidence": {
            "schema_version": GIT_RESULT_EVIDENCE_SCHEMA,
            "backend_id": source.backend_id,
            "base_commit": source.base_commit,
            "observed_head": source.base_commit,
            "workspace_receipt_digest": source.workspace_receipt_digest,
            "workspace_root_digest": source.workspace_root_digest,
            "workspace_path_digest": source.workspace_path_digest,
            "workspace_content_digest": DIGEST_D,
            "workspace_state": "unchanged" if read_only else "changed",
            "changed_paths": [] if read_only else ["README.md"],
        },
        "proposal_digest": DIGEST_D if read_only else None,
        "candidate_digest": None if read_only else DIGEST_D,
        "validation_stages": [{"test_id": "T001", "outcome": "pass", "failure_code": None}],
        "first_failure_boundary": None,
        "failure_code": None,
        "expected": "bounded result",
        "observed": "bounded result",
        "containment_outcome": "absence-verified",
        "output_digest": DIGEST_D,
        "content_reference": "proposals/fixture.txt" if read_only else "candidates/fixture.json",
        "retryable": False,
    }
    value.update(updates)
    return ResultRecordV3.from_mapping(value)


def test_v3_identity_is_logical_not_repository_or_model_selector():
    binding = create_provider_binding("BINDING-0001", qualification())
    record = invocation(binding)
    value = record.to_dict()
    assert value["logical_target_id"] == "target:acl"
    assert value["framework_contract_version"] == FRAMEWORK_DISPATCH_CONTRACT_V1
    assert "repository" not in value
    assert "model" not in value
    assert "reasoning_effort" not in value
    assert value["source_state"]["backend_id"] == "git-workspace:v1"


@pytest.mark.parametrize(
    "target",
    ["acl", "repo.git", "C:/projects/acl", "https://github.com/floydtrey/autonomous-coding-lab"],
)
def test_target_rejects_repository_locator_forms(target):
    binding = create_provider_binding("BINDING-0001", qualification())
    with pytest.raises(LabValidationError) as error:
        invocation(binding, logical_target_id=target)
    assert error.value.code == "INTEGRATION_V3_TARGET_INVALID"


def test_authorization_requires_durable_exact_binding_and_no_bypass(tmp_path):
    binding = create_provider_binding("BINDING-0001", qualification())
    record = invocation(binding)
    store = ProviderBindingStore(tmp_path)
    with pytest.raises(LabValidationError) as error:
        authorize_invocation(
            record,
            binding_store=store,
            controller_identity="trusted-controller",
            authorized_at="2026-09-11T00:00:00Z",
        )
    assert error.value.code == "INTEGRATION_V3_PROVIDER_BINDING_UNKNOWN"
    with pytest.raises(LabValidationError) as error:
        transition_invocation(record, InvocationState.AUTHORIZED)
    assert error.value.code == "INTEGRATION_V3_PROVIDER_BINDING_REQUIRED"
    store.create(binding)
    authorized = authorize_invocation(
        record,
        binding_store=store,
        controller_identity="trusted-controller",
        authorized_at="2026-09-11T00:00:00Z",
    )
    assert authorized.state is InvocationState.AUTHORIZED
    assert authorized.identity_digest() == record.identity_digest()


def test_authorization_rejects_stale_durable_binding(tmp_path):
    binding = create_provider_binding("BINDING-0001", qualification())
    store = ProviderBindingStore(tmp_path)
    store.create(binding)
    path = tmp_path / "provider-bindings" / f"{binding.binding_id}.json"
    value = binding.to_dict()
    value["runtime_settings_digest"] = DIGEST_A
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(LabValidationError) as error:
        authorize_invocation(
            invocation(binding),
            binding_store=store,
            controller_identity="trusted-controller",
            authorized_at="2026-09-11T00:00:00Z",
        )
    assert error.value.code == "INTEGRATION_V3_PROVIDER_BINDING_INVALID"


def test_result_preserves_independent_acceptance_evidence_for_write():
    binding = create_provider_binding("BINDING-0001", qualification())
    invocation_record = invocation(binding)
    accepted = result(invocation_record)
    validate_result_for_invocation(accepted, invocation_record)
    assert accepted.request_digest == invocation_record.identity_digest()
    assert accepted.runtime_identity == binding.digest()
    assert accepted.candidate_digest is not None
    assert accepted.proposal_digest is None
    assert accepted.containment_outcome == "absence-verified"
    assert accepted.source_evidence.workspace_content_digest == DIGEST_D


def test_result_preserves_proposal_evidence_for_read_only():
    binding = create_provider_binding("BINDING-0001", qualification())
    invocation_record = invocation(binding, operation="read-only-proposal")
    accepted = result(invocation_record)
    validate_result_for_invocation(accepted, invocation_record)
    assert accepted.proposal_digest is not None
    assert accepted.candidate_digest is None
    assert accepted.source_evidence.changed_paths == ()


def test_result_rejects_provider_or_scope_substitution():
    binding = create_provider_binding("BINDING-0001", qualification())
    invocation_record = invocation(binding)
    substituted = result(invocation_record, provider_binding_digest=DIGEST_A)
    with pytest.raises(LabValidationError) as error:
        validate_result_for_invocation(substituted, invocation_record)
    assert error.value.code == "INTEGRATION_V3_IDENTITY_INVALID"
    value = result(invocation_record).to_dict()
    value["source_evidence"]["changed_paths"] = ["OTHER.md"]
    tampered = ResultRecordV3.from_mapping(value)
    with pytest.raises(LabValidationError) as error:
        validate_result_for_invocation(tampered, invocation_record)
    assert error.value.code == "INTEGRATION_V3_SCOPE_INVALID"


def test_successful_code_result_requires_complete_validation_and_containment():
    binding = create_provider_binding("BINDING-0001", qualification())
    invocation_record = invocation(binding)
    for patch in (
        {"validation_stages": []},
        {"containment_outcome": "unknown"},
        {"candidate_digest": None},
    ):
        with pytest.raises(LabValidationError) as error:
            result(invocation_record, **patch)
        assert error.value.code == "INTEGRATION_V3_RESULT_INVALID"
