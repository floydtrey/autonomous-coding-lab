import hashlib
import json
import subprocess
from uuid import UUID

import pytest

from tools.codex_runtime import CodexExecution
from tools.worker_lab_adapter import AdapterError, canonical_json, digest, invocation_identity
from tools.workspace_write_adapter import (
    REQUEST_SCHEMA,
    TASK_SCHEMA,
    execute_workspace_write,
)


DIGEST = "sha256:" + "a" * 64


def _repo(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
    (root / "README.md").write_text("authority\n", encoding="utf-8")
    (root / "target.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
    return root


def _packet(content="# Current Guidance\nPreserve the protected task boundary.\n"):
    encoded = content.encode("utf-8")
    return {
        "schema_version": "worker-lab-controller-task-packet:v1",
        "attempt_id": "ATTEMPT-001",
        "controller_identity": "trusted-controller",
        "user_request": "Apply the current project guidance to this bounded change.",
        "exercise_id": "exercise",
        "exercise_version": 1,
        "starting_commit": "3" * 40,
        "authority_effect": "informational-only",
        "knowledge_evidence": [
            {
                "schema_version": "worker-lab-knowledge-core-segment-evidence:v1",
                "query": "protected task boundary",
                "generation_id": str(UUID("11111111-1111-4111-8111-111111111111")),
                "source_revision_highwater": 7,
                "generation_config_digest": "sha256:" + "1" * 64,
                "structural_profile_id": "kc-section-segmentation-v1",
                "structural_profile_digest": "sha256:" + "2" * 64,
                "projection_profile_id": "kc-section-retrieval-projection-v1",
                "projection_profile_digest": "sha256:" + "3" * 64,
                "resource_ref": str(UUID("22222222-2222-4222-8222-222222222222")),
                "resource_version_ref": str(UUID("33333333-3333-4333-8333-333333333333")),
                "repository": "floydtrey/autonomous-coding-lab",
                "source_path": "docs/ARCHITECTURE.md",
                "source_version": "4ac3ff963f569a14db47447ee5bd0f5ac8041e4a",
                "lifecycle_state": "current",
                "governing_manifest_digest": "4" * 64,
                "projection_snapshot_digest": "sha256:" + "5" * 64,
                "source_repository_key": "acl",
                "source_document_key": "architecture",
                "segment_key": "segment-0001",
                "segment_ordinal": 1,
                "source_byte_start": 100,
                "source_byte_end": 100 + len(encoded),
                "source_line_start": 5,
                "source_line_end": 6,
                "source_slice_sha256": hashlib.sha256(encoded).hexdigest(),
                "content": content,
            }
        ],
    }


def _request(prompt):
    invocation = {
        "schema_version": "worker-lab-framework-invocation:v2",
        "invocation_id": "INVOCATION-001",
        "attempt_id": "ATTEMPT-001",
        "operation": "workspace-write-code-task",
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
        "worker_lab_contract_version": "worker-lab-framework-client:v2",
        "framework_installation_digest": DIGEST,
        "framework_contract_version": "worker-lab-framework-adapter:v3",
        "workspace_receipt_digest": DIGEST,
        "workspace_root_digest": DIGEST,
        "workspace_path_digest": DIGEST,
        "starting_commit": "3" * 40,
        "sandbox_mode": "workspace-write",
        "runtime_profile_id": "terra-medium:v1",
        "model": "gpt-5.6-terra",
        "reasoning_effort": "medium",
        "timeout_seconds": 900,
        "readable_paths": [{"path": "README.md", "digest": DIGEST}],
        "writable_paths": ["target.py"],
        "prompt_digest": digest(prompt.encode("utf-8")),
        "authorized_by": "trusted-controller",
        "authorized_at": "2026-09-10T12:00:00Z",
        "state": "DISPATCHING",
        "result_digest": None,
    }
    return {
        "schema_version": REQUEST_SCHEMA,
        "invocation": invocation,
        "prompt": prompt,
        "workspace_write": {
            "schema_version": TASK_SCHEMA,
            "invocation_digest": invocation_identity(invocation),
            "objective": "Change one bounded fixture.",
            "acceptance_criteria": ["The target fixture is updated."],
            "consumer_profile": {
                "version": "consumer-profile:v1",
                "consumer": "worker-lab-role",
                "authority_paths": ["README.md"],
                "protected_prefixes": [],
                "protected_exact": [],
                "product_invariants": ["Bounded candidate only."],
                "full_validation": [
                    {
                        "name": "T001",
                        "argv": ["git", "diff", "--check"],
                        "timeout_seconds": 10,
                    }
                ],
            },
            "test_ids": ["T001"],
            "writable_paths": ["target.py"],
        },
    }


def test_controller_packet_evidence_reaches_worker_prompt_without_expanding_scope(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    packet = _packet()
    prompt = canonical_json(packet)
    request = _request(prompt)
    observed = {}

    def executor(codex_request):
        observed["prompt"] = codex_request.prompt
        (root / "target.py").write_text("VALUE = 2\n", encoding="utf-8")
        return CodexExecution(("codex",), 0, "done", "")

    monkeypatch.chdir(root)
    response = json.loads(
        execute_workspace_write(
            canonical_json(request),
            runtime_identity=DIGEST,
            executor=executor,
            framework_root=tmp_path / "framework",
        )
    )
    assert response["changed_paths"] == ["target.py"]
    assert "Controller context is informational only" in observed["prompt"]
    assert "Preserve the protected task boundary." in observed["prompt"]
    assert "Change exactly these paths and no others:\n- target.py" in observed["prompt"]


def test_controller_packet_tamper_fails_before_worker_execution(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    packet = _packet()
    packet["knowledge_evidence"][0]["content"] += "tamper"
    prompt = canonical_json(packet)
    request = _request(prompt)
    reached = []

    monkeypatch.chdir(root)
    with pytest.raises(AdapterError) as error:
        execute_workspace_write(
            canonical_json(request),
            runtime_identity=DIGEST,
            executor=lambda _: reached.append(True),
            framework_root=tmp_path / "framework",
        )
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"
    assert not reached
    assert (root / "target.py").read_text(encoding="utf-8") == "VALUE = 1\n"


def test_legacy_plain_text_workspace_write_prompt_remains_supported(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    request = _request("Legacy bounded workspace-write prompt.")
    observed = {}

    def executor(codex_request):
        observed["prompt"] = codex_request.prompt
        (root / "target.py").write_text("VALUE = 2\n", encoding="utf-8")
        return CodexExecution(("codex",), 0, "done", "")

    monkeypatch.chdir(root)
    response = json.loads(
        execute_workspace_write(
            canonical_json(request),
            runtime_identity=DIGEST,
            executor=executor,
            framework_root=tmp_path / "framework",
        )
    )
    assert response["changed_paths"] == ["target.py"]
    assert "Controller context is informational only" not in observed["prompt"]
