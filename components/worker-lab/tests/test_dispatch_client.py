from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from worker_lab.canonical import canonical_json
from worker_lab.controller_task_packet import ControllerTaskPacket
from worker_lab.dispatch_client import (
    DISPATCH_REQUEST_SCHEMA,
    DISPATCH_RESPONSE_SCHEMA,
    WORKSPACE_WRITE_TASK_SCHEMA,
    dispatch_workspace_write,
)
from worker_lab.errors import LabValidationError
from worker_lab.integration_v3 import (
    FRAMEWORK_DISPATCH_CONTRACT_V1,
    GIT_SOURCE_STATE_SCHEMA,
    INVOCATION_SCHEMA_V3,
    WORKER_LAB_CONTRACT_VERSION_V3,
    InvocationRecordV3,
)
from worker_lab.provider_binding import ProviderBindingStore, create_provider_binding
from worker_lab.runtime_selection import selected_runtime_requirement_v3


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
SHA_A = "a" * 40


def bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def qualification():
    from tests.provider_capability_fixture import capability_qualification

    return capability_qualification(model_name="fixture-model")


def packet() -> ControllerTaskPacket:
    content = "Only the sealed writable path may change."
    encoded = content.encode("utf-8")
    return ControllerTaskPacket.from_mapping({
        "schema_version": "worker-lab-controller-task-packet:v1",
        "attempt_id": "ATTEMPT-001",
        "controller_identity": "controller-1",
        "user_request": "Change the target value to two.",
        "exercise_id": "exercise",
        "exercise_version": 1,
        "starting_commit": SHA_A,
        "authority_effect": "informational-only",
        "knowledge_evidence": [
            {
                "schema_version": "worker-lab-knowledge-core-segment-evidence:v1",
                "query": "current target rule",
                "generation_id": "00000000-0000-4000-8000-000000000001",
                "source_revision_highwater": 1,
                "generation_config_digest": DIGEST_A,
                "structural_profile_id": "markdown-v1",
                "structural_profile_digest": DIGEST_A,
                "projection_profile_id": "current-v1",
                "projection_profile_digest": DIGEST_B,
                "resource_ref": "00000000-0000-4000-8000-000000000002",
                "resource_version_ref": "00000000-0000-4000-8000-000000000003",
                "repository": "knowledge-source",
                "source_path": "docs/rule.md",
                "source_version": SHA_A,
                "lifecycle_state": "current",
                "governing_manifest_digest": DIGEST_A,
                "projection_snapshot_digest": DIGEST_B,
                "source_repository_key": "source-repo",
                "source_document_key": "rule-doc",
                "segment_key": "segment-1",
                "segment_ordinal": 0,
                "source_byte_start": 0,
                "source_byte_end": len(encoded),
                "source_line_start": 1,
                "source_line_end": 1,
                "source_slice_sha256": hashlib.sha256(encoded).hexdigest(),
                "content": content,
            }
        ],
    })


def invocation(binding, *, prompt_packet=None, **updates):
    requirement = selected_runtime_requirement_v3()
    prompt_packet = prompt_packet or packet()
    value = {
        "schema_version": INVOCATION_SCHEMA_V3,
        "invocation_id": "INVOCATION-001",
        "attempt_id": "ATTEMPT-001",
        "operation": "workspace-write-code-task",
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
        "task_digest": DIGEST_B,
        "controller_task_packet_digest": prompt_packet.digest(),
        "prompt_digest": prompt_packet.digest(),
        "test_catalog_version": "catalog-v1",
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
        "sandbox_mode": "workspace-write",
        "readable_paths": [{"path": "authority.md", "digest": DIGEST_A}],
        "writable_paths": ["target.py"],
        "source_state": {
            "schema_version": GIT_SOURCE_STATE_SCHEMA,
            "backend_id": "git-workspace:v1",
            "base_commit": SHA_A,
            "workspace_receipt_digest": DIGEST_A,
            "workspace_root_digest": DIGEST_B,
            "workspace_path_digest": DIGEST_C,
        },
        "authorized_by": "controller-1",
        "authorized_at": "2026-09-11T02:00:00Z",
        "state": "DISPATCHING",
        "result_digest": None,
    }
    value.update(updates)
    return InvocationRecordV3.from_mapping(value)


def task(record):
    return {
        "schema_version": WORKSPACE_WRITE_TASK_SCHEMA,
        "task_digest": record.task_digest,
        "objective": "Change target.py from VALUE = 1 to VALUE = 2.",
        "acceptance_criteria": ["target.py contains VALUE = 2."],
        "consumer_profile": {
            "version": "consumer-profile:v1",
            "consumer": "worker-lab-role",
        },
        "test_ids": list(record.test_ids),
        "writable_paths": list(record.writable_paths),
    }


def response(record, binding):
    return canonical_json({
        "schema_version": DISPATCH_RESPONSE_SCHEMA,
        "invocation_digest": record.identity_digest(),
        "provider_binding_digest": binding.digest(),
        "provider_adapter_id": binding.provider_adapter_id,
        "framework_task_digest": DIGEST_A,
        "context_digest": DIGEST_B,
        "candidate_digest": DIGEST_C,
        "changed_paths": list(record.writable_paths),
        "validation_stages": [{"test_id": "T001", "outcome": "pass"}],
        "worker_output_digest": DIGEST_A,
    }).encode("utf-8")


def test_dispatch_client_seals_exact_binding_settings_and_no_backend_locator(tmp_path):
    binding = create_provider_binding("BINDING-0001", qualification())
    store = ProviderBindingStore(tmp_path)
    store.create(binding)
    prompt_packet = packet()
    record = invocation(binding, prompt_packet=prompt_packet)
    seen = []

    def runner(raw):
        value = json.loads(raw)
        seen.append(value)
        assert value["schema_version"] == DISPATCH_REQUEST_SCHEMA
        assert value["invocation"]["logical_target_id"] == "target:acl"
        assert "model" not in value["invocation"]
        assert "reasoning_effort" not in value["invocation"]
        assert "target_repo" not in value
        assert "framework_repo" not in value
        assert "workspace_root" not in value
        assert value["provider_binding"]["model_name"] == "fixture-model"
        assert value["runtime_settings"]["requested_context_tokens"] == 32768
        return response(record, binding)

    raw = dispatch_workspace_write(
        record,
        prompt=prompt_packet.to_json(),
        workspace_write=task(record),
        binding_store=store,
        runner=runner,
    )
    assert raw == response(record, binding)
    assert len(seen) == 1


def test_dispatch_requires_explicit_runner_and_never_falls_back(tmp_path):
    binding = create_provider_binding("BINDING-0001", qualification())
    store = ProviderBindingStore(tmp_path)
    store.create(binding)
    prompt_packet = packet()
    record = invocation(binding, prompt_packet=prompt_packet)
    with pytest.raises(LabValidationError) as error:
        dispatch_workspace_write(
            record,
            prompt=prompt_packet.to_json(),
            workspace_write=task(record),
            binding_store=store,
            runner=None,
        )
    assert error.value.code == "DISPATCH_RUNNER_REQUIRED"


def test_binding_substitution_fails_before_runner(tmp_path):
    binding = create_provider_binding("BINDING-0001", qualification())
    store = ProviderBindingStore(tmp_path)
    store.create(binding)
    prompt_packet = packet()
    record = invocation(binding, prompt_packet=prompt_packet, provider_binding_digest=DIGEST_C)
    called = False

    def runner(_):
        nonlocal called
        called = True
        raise AssertionError("binding substitution must not dispatch")

    with pytest.raises(LabValidationError) as error:
        dispatch_workspace_write(
            record,
            prompt=prompt_packet.to_json(),
            workspace_write=task(record),
            binding_store=store,
            runner=runner,
        )
    assert error.value.code == "PROVIDER_BINDING_MISMATCH"
    assert called is False


def test_prompt_and_task_scope_mismatch_fail_before_runner(tmp_path):
    binding = create_provider_binding("BINDING-0001", qualification())
    store = ProviderBindingStore(tmp_path)
    store.create(binding)
    prompt_packet = packet()
    record = invocation(binding, prompt_packet=prompt_packet)
    called = False

    def runner(_):
        nonlocal called
        called = True
        raise AssertionError("mismatched input must not dispatch")

    with pytest.raises(LabValidationError) as error:
        dispatch_workspace_write(
            record,
            prompt=prompt_packet.to_json() + " ",
            workspace_write=task(record),
            binding_store=store,
            runner=runner,
        )
    assert error.value.code == "DISPATCH_IDENTITY_INVALID"

    bad_task = task(record)
    bad_task["writable_paths"] = ["other.py"]
    with pytest.raises(LabValidationError) as error:
        dispatch_workspace_write(
            record,
            prompt=prompt_packet.to_json(),
            workspace_write=bad_task,
            binding_store=store,
            runner=runner,
        )
    assert error.value.code == "DISPATCH_TASK_SCOPE_INVALID"
    assert called is False
