from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from tools.consumer_profile import PROFILE_VERSION
from tools.dispatch_adapter import (
    BoundProviderExecutor,
    DispatchAdapterError,
    execute_workspace_write,
)
from tools.worker_runtime import WorkerExecution


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
DIGEST_D = "sha256:" + "d" * 64


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def canonical_digest(value):
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def bytes_digest(value: bytes):
    return "sha256:" + hashlib.sha256(value).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=root, text=True, encoding="utf-8", capture_output=True, check=True
    ).stdout.strip()


def repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "workspace"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    (root / "authority.md").write_text("authority\n", encoding="utf-8")
    (root / "target.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "fixture")
    return root, git(root, "rev-parse", "HEAD")


def prompt(base_commit: str):
    packet = {
        "schema_version": "worker-lab-controller-task-packet:v1",
        "attempt_id": "ATTEMPT-001",
        "controller_identity": "controller-1",
        "user_request": "Change the target value to two.",
        "exercise_id": "exercise",
        "exercise_version": 1,
        "starting_commit": base_commit,
        "authority_effect": "informational-only",
        "knowledge_evidence": [
            {
                "repository": "knowledge-source",
                "source_path": "docs/rule.md",
                "source_version": base_commit,
                "segment_key": "segment-1",
                "generation_id": "generation-1",
                "content": "Only target.py may change.",
            }
        ],
    }
    raw = canonical_json(packet)
    return raw, canonical_digest(packet)


def binding_and_settings():
    settings = {
        "schema_version": "worker-lab-runtime-settings:v1",
        "profile_id": "bounded-code-worker-settings:v1",
        "profile_version": 1,
        "requested_context_tokens": 32768,
        "request_limit": 12,
        "tool_calls_limit": 24,
        "tool_timeout_seconds": 30,
        "tool_retries": 2,
        "output_retries": 1,
        "max_concurrency": 1,
    }
    settings_digest = canonical_digest(settings)
    binding = {
        "schema_version": "worker-lab-provider-binding:v1",
        "binding_id": "BINDING-0001",
        "binding_version": 1,
        "runtime_requirement_profile_id": "coding-worker:v2",
        "runtime_requirement_digest": DIGEST_A,
        "host_provider_qualification_digest": DIGEST_B,
        "qualification_candidate_id": "pydantic-ai-ollama-files",
        "qualification_candidate_version": 1,
        "qualification_candidate_digest": DIGEST_C,
        "provider_adapter_id": "pydantic-ai-ollama-files:v1",
        "tool_surface_id": "acl-bounded-file-tools:v1",
        "provider_kind": "ollama",
        "model_name": "fixture-model",
        "model_digest": DIGEST_B,
        "model_metadata_digest": DIGEST_C,
        "runtime_settings_profile_id": settings["profile_id"],
        "runtime_settings_digest": settings_digest,
    }
    binding_digest = canonical_digest({
        "schema_version": "worker-lab-provider-binding-identity:v1",
        "binding": binding,
    })
    return binding, settings, binding_digest


def request(root: Path, base_commit: str):
    raw_prompt, packet_digest = prompt(base_commit)
    binding, settings, binding_digest = binding_and_settings()
    authority_digest = bytes_digest((root / "authority.md").read_bytes())
    invocation = {
        "schema_version": "worker-lab-framework-invocation:v3",
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
        "task_digest": DIGEST_D,
        "controller_task_packet_digest": packet_digest,
        "prompt_digest": packet_digest,
        "test_catalog_version": "catalog-v1",
        "test_catalog_digest": DIGEST_A,
        "test_plan_digest": DIGEST_B,
        "test_ids": ["T001"],
        "worker_lab_source_digest": DIGEST_A,
        "worker_lab_contract_version": "worker-lab-runtime-contract:v3",
        "framework_source_digest": DIGEST_B,
        "framework_contract_version": "worker-lab-provider-dispatch:v1",
        "runtime_requirement_profile_id": binding["runtime_requirement_profile_id"],
        "runtime_requirement_digest": binding["runtime_requirement_digest"],
        "provider_binding_id": binding["binding_id"],
        "provider_binding_digest": binding_digest,
        "sandbox_mode": "workspace-write",
        "readable_paths": [{"path": "authority.md", "digest": authority_digest}],
        "writable_paths": ["target.py"],
        "source_state": {
            "schema_version": "worker-lab-git-workspace-source-state:v1",
            "backend_id": "git-workspace:v1",
            "base_commit": base_commit,
            "workspace_receipt_digest": DIGEST_A,
            "workspace_root_digest": DIGEST_B,
            "workspace_path_digest": DIGEST_C,
        },
        "authorized_by": "controller-1",
        "authorized_at": "2026-09-11T02:00:00Z",
        "state": "DISPATCHING",
        "result_digest": None,
    }
    profile = {
        "version": PROFILE_VERSION,
        "consumer": "worker-lab-role",
        "authority_paths": ["authority.md"],
        "protected_prefixes": [],
        "protected_exact": [],
        "product_invariants": ["Only the sealed target may change."],
        "full_validation": [
            {
                "name": "T001",
                "argv": [
                    "python",
                    "-c",
                    "from pathlib import Path; assert Path('target.py').read_text(encoding='utf-8') == 'VALUE = 2\\n'",
                ],
                "timeout_seconds": 30,
            }
        ],
    }
    task = {
        "schema_version": "worker-lab-workspace-write-task:v2",
        "task_digest": invocation["task_digest"],
        "objective": "Change target.py from VALUE = 1 to VALUE = 2.",
        "acceptance_criteria": ["target.py contains VALUE = 2."],
        "consumer_profile": profile,
        "test_ids": ["T001"],
        "writable_paths": ["target.py"],
    }
    payload = {
        "schema_version": "worker-lab-provider-dispatch-request:v1",
        "framework_contract_version": "worker-lab-provider-dispatch:v1",
        "invocation": invocation,
        "provider_binding": binding,
        "runtime_settings": settings,
        "prompt": raw_prompt,
        "workspace_write": task,
    }
    return canonical_json(payload).encode("utf-8"), invocation, binding, settings, binding_digest


def executor(binding, binding_digest, seen, root: Path):
    def execute(worker_request):
        seen.append(worker_request)
        (root / "target.py").write_text("VALUE = 2\n", encoding="utf-8")
        return WorkerExecution(("fake-provider",), 0, "changed target", "")

    return BoundProviderExecutor(
        provider_adapter_id=binding["provider_adapter_id"],
        tool_surface_id=binding["tool_surface_id"],
        provider_binding_digest=binding_digest,
        runtime_settings_digest=binding["runtime_settings_digest"],
        execute=execute,
    )


def test_workspace_write_uses_exact_injected_provider_and_returns_candidate_evidence(tmp_path):
    root, base_commit = repo(tmp_path)
    framework = tmp_path / "framework"
    framework.mkdir()
    raw, invocation, binding, _, binding_digest = request(root, base_commit)
    seen = []
    response = execute_workspace_write(
        raw,
        workspace_root=root,
        framework_root=framework,
        provider_executor=executor(binding, binding_digest, seen, root),
    )
    value = json.loads(response)
    assert len(seen) == 1
    assert seen[0].sandbox == "workspace-write"
    assert seen[0].writable_paths == ("target.py",)
    assert value["provider_adapter_id"] == binding["provider_adapter_id"]
    assert value["provider_binding_digest"] == binding_digest
    assert value["changed_paths"] == ["target.py"]
    assert value["validation_stages"] == [{"test_id": "T001", "outcome": "pass"}]
    assert git(root, "rev-parse", "HEAD") == base_commit


def test_no_executor_means_no_fallback_and_no_workspace_mutation(tmp_path):
    root, base_commit = repo(tmp_path)
    framework = tmp_path / "framework"
    framework.mkdir()
    raw, *_ = request(root, base_commit)
    with pytest.raises(DispatchAdapterError) as error:
        execute_workspace_write(
            raw,
            workspace_root=root,
            framework_root=framework,
            provider_executor=None,
        )
    assert error.value.code == "DISPATCH_EXECUTOR_REQUIRED"
    assert git(root, "status", "--porcelain") == ""


def test_executor_identity_substitution_is_rejected_before_execution(tmp_path):
    root, base_commit = repo(tmp_path)
    framework = tmp_path / "framework"
    framework.mkdir()
    raw, _, binding, _, binding_digest = request(root, base_commit)
    called = False

    def fake(_):
        nonlocal called
        called = True
        raise AssertionError("mismatched executor must not run")

    handle = BoundProviderExecutor(
        provider_adapter_id="other-adapter:v1",
        tool_surface_id=binding["tool_surface_id"],
        provider_binding_digest=binding_digest,
        runtime_settings_digest=binding["runtime_settings_digest"],
        execute=fake,
    )
    with pytest.raises(DispatchAdapterError) as error:
        execute_workspace_write(
            raw,
            workspace_root=root,
            framework_root=framework,
            provider_executor=handle,
        )
    assert error.value.code == "DISPATCH_EXECUTOR_MISMATCH"
    assert called is False
    assert git(root, "status", "--porcelain") == ""


def test_tampered_runtime_settings_fail_before_provider_execution(tmp_path):
    root, base_commit = repo(tmp_path)
    framework = tmp_path / "framework"
    framework.mkdir()
    raw, _, binding, _, binding_digest = request(root, base_commit)
    value = json.loads(raw)
    value["runtime_settings"]["request_limit"] = 13
    tampered = canonical_json(value).encode("utf-8")
    called = False

    def fake(_):
        nonlocal called
        called = True
        raise AssertionError("tampered settings must not run")

    handle = BoundProviderExecutor(
        provider_adapter_id=binding["provider_adapter_id"],
        tool_surface_id=binding["tool_surface_id"],
        provider_binding_digest=binding_digest,
        runtime_settings_digest=binding["runtime_settings_digest"],
        execute=fake,
    )
    with pytest.raises(DispatchAdapterError) as error:
        execute_workspace_write(
            tampered,
            workspace_root=root,
            framework_root=framework,
            provider_executor=handle,
        )
    assert error.value.code == "DISPATCH_SETTINGS_INVALID"
    assert called is False
