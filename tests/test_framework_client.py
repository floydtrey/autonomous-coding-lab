import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.framework_client import (
    FrameworkConfiguration, FrameworkIdentityEvidence, WorkerLabIdentityEvidence,
    PINNED_ADAPTER_DIGEST, PINNED_FRAMEWORK_COMMIT, PINNED_FRAMEWORK_ROOT,
    call_adapter, fixed_command, inspect_configuration, pinned_framework_configuration,
    runtime_identity,
)
from worker_lab.integration import InvocationRecord, InvocationState, transition_invocation
from tests.test_integration import DIGEST, record


PROMPT = "Propose a bounded synthetic read-only change."
PROMPT_DIGEST = "sha256:" + hashlib.sha256(PROMPT.encode()).hexdigest()


def invocation():
    value = record().to_dict()
    value["prompt_digest"] = PROMPT_DIGEST
    return InvocationRecord.from_mapping(value)


def config():
    return pinned_framework_configuration(
        codex_launcher=Path(r"C:\bin\codex.cmd"),
        codex_launcher_digest="sha256:" + "b" * 64,
    )


def evidence(**updates):
    value = {
        "framework_root": PINNED_FRAMEWORK_ROOT, "framework_head": PINNED_FRAMEWORK_COMMIT,
        "framework_status": "", "adapter_path": PINNED_FRAMEWORK_ROOT / "tools/worker_lab_adapter.py",
        "adapter_worktree_digest": PINNED_ADAPTER_DIGEST, "adapter_blob_digest": PINNED_ADAPTER_DIGEST,
        "python_path": Path(r"C:\Program Files\Python312\python.exe"),
        "python_digest": "sha256:4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a",
        "python_version": "3.12.10", "python_implementation": "CPython",
        "python_architecture": "AMD64", "codex_launcher_path": Path(r"C:\bin\codex.cmd"),
        "codex_launcher_digest": "sha256:" + "b" * 64, "codex_version": "0.149.1",
    }
    value.update(updates)
    return FrameworkIdentityEvidence(**value)


def lab_evidence(**updates):
    value = {
        "worker_lab_root": Path(r"C:\worker-lab"),
        "worker_lab_head": "a" * 40,
        "worker_lab_status": ("?? docs/8_27_26_ChatGPT_History",),
    }
    value.update(updates)
    return WorkerLabIdentityEvidence(**value)


def test_fixed_commands_share_one_runtime_identity_and_use_trusted_configuration():
    identities = set()
    for mode in ("prepare", "preflight", "execute-read-only"):
        command = fixed_command(config(), mode, evidence=evidence())
        assert command == (
            r"C:\Program Files\Python312\python.exe", "-I", "-B",
            str(PINNED_FRAMEWORK_ROOT / "tools/worker_lab_adapter.py"), mode,
            "--protocol", "worker-lab-framework-adapter:v1",
        )
        identities.add(runtime_identity(config(), invocation(), evidence=evidence()))
    assert len(identities) == 1
    with pytest.raises(LabValidationError):
        fixed_command(config(), "workspace-write", evidence=evidence())
    with pytest.raises(LabValidationError):
        fixed_command(config(), "prepare", evidence=evidence(framework_status="?? injected.py\n"))
    with pytest.raises(LabValidationError):
        fixed_command(config(), "prepare", evidence=evidence(codex_version="0.149.2"))


@pytest.mark.parametrize("field,value", [
    ("framework_head", "2" * 40), ("adapter_worktree_digest", "sha256:" + "c" * 64),
    ("adapter_blob_digest", "sha256:" + "c" * 64), ("python_version", "3.12.11"),
    ("python_implementation", "PyPy"), ("python_architecture", "ARM64"),
    ("python_digest", "sha256:" + "c" * 64),
    ("python_path", Path(r"C:\other\python.exe")),
    ("adapter_path", Path(r"C:\framework\tools\other_adapter.py")),
    ("codex_launcher_path", Path(r"C:\other\codex.cmd")),
    ("codex_launcher_digest", "sha256:" + "c" * 64), ("codex_version", "0.149.2"),
])
def test_identity_evidence_rejects_each_substitution_before_dispatch(field, value):
    with pytest.raises(LabValidationError) as error:
        fixed_command(config(), "prepare", evidence=evidence(**{field: value}))
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"


def test_fixed_command_rejects_unreviewed_framework_configuration():
    unreviewed = FrameworkConfiguration(
        Path(r"C:\framework"), "1" * 40, Path(r"C:\Program Files\Python312\python.exe"),
        DIGEST, Path(r"C:\bin\codex.cmd"), "sha256:" + "b" * 64,
    )
    with pytest.raises(LabValidationError) as error:
        fixed_command(unreviewed, "prepare", evidence=evidence())
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"


def test_client_requires_runner_and_binds_prompt_invocation_and_runtime():
    item = invocation()
    with pytest.raises(LabValidationError) as error:
        call_adapter(
            item, config(), "prepare", prompt=PROMPT, evidence=evidence(),
            worker_lab_evidence=lab_evidence(),
        )
    assert error.value.code == "INTEGRATION_EXECUTION_DISABLED"
    expected_runtime = runtime_identity(config(), item, evidence=evidence())

    def fake(_, payload):
        request = json.loads(payload)
        assert request["invocation"]["prompt_digest"] == PROMPT_DIGEST
        return json.dumps({
            "invocation_digest": item.identity_digest(), "prompt_digest": PROMPT_DIGEST,
            "runtime_identity": expected_runtime,
        }, separators=(",", ":")).encode()

    assert call_adapter(
        item, config(), "prepare", prompt=PROMPT, evidence=evidence(),
        worker_lab_evidence=lab_evidence(), runner=fake,
    )
    with pytest.raises(LabValidationError):
        call_adapter(
            item, config(), "prepare", prompt=PROMPT + "x", evidence=evidence(),
            worker_lab_evidence=lab_evidence(), runner=fake,
        )
    with pytest.raises(LabValidationError):
        call_adapter(
            item, config(), "prepare", prompt=PROMPT, evidence=evidence(),
            worker_lab_evidence=lab_evidence(worker_lab_status=("?? injected.py",)), runner=fake,
        )


def test_client_rejects_wrong_mode_or_noncanonical_unknown_response_before_dispatch():
    item = invocation()
    calls = []

    def fake(command, payload):
        calls.append((command, payload))
        return b"{}"

    with pytest.raises(LabValidationError) as error:
        call_adapter(
            item, config(), "execute-read-only", prompt=PROMPT, evidence=evidence(),
            worker_lab_evidence=lab_evidence(), runner=fake,
        )
    assert error.value.code == "INTEGRATION_AUTHORIZATION_INVALID"
    assert not calls

    expected_runtime = runtime_identity(config(), item, evidence=evidence())
    response = {
        "invocation_digest": item.identity_digest(), "prompt_digest": PROMPT_DIGEST,
        "runtime_identity": expected_runtime, "unexpected": True,
    }
    with pytest.raises(LabValidationError) as error:
        call_adapter(
            item, config(), "prepare", prompt=PROMPT, evidence=evidence(),
            worker_lab_evidence=lab_evidence(), runner=lambda *_: json.dumps(response, separators=(",", ":")).encode(),
        )
    assert error.value.code == "INTEGRATION_RESULT_INVALID"

    canonical = {
        "invocation_digest": item.identity_digest(), "prompt_digest": PROMPT_DIGEST,
        "runtime_identity": expected_runtime,
    }
    with pytest.raises(LabValidationError) as error:
        call_adapter(
            item, config(), "prepare", prompt=PROMPT, evidence=evidence(),
            worker_lab_evidence=lab_evidence(), runner=lambda *_: json.dumps(canonical).encode(),
        )
    assert error.value.code == "INTEGRATION_RESULT_INVALID"

    authorized = transition_invocation(
        item, InvocationState.AUTHORIZED, authorized_by="trusted-controller", authorized_at="2026-08-28T00:00:00Z"
    )
    with pytest.raises(LabValidationError) as error:
        call_adapter(
            authorized, config(), "prepare", prompt=PROMPT, evidence=evidence(),
            worker_lab_evidence=lab_evidence(), runner=fake,
        )
    assert error.value.code == "INTEGRATION_AUTHORIZATION_INVALID"


def test_client_rejects_wrong_worker_lab_commit_before_runner_dispatch():
    item = invocation()
    called = False

    def fake(*_):
        nonlocal called
        called = True
        return b"{}"

    with pytest.raises(LabValidationError) as error:
        call_adapter(
            item, config(), "prepare", prompt=PROMPT, evidence=evidence(),
            worker_lab_evidence=lab_evidence(worker_lab_head="b" * 40), runner=fake,
        )
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"
    assert not called


def test_configuration_inspection_verifies_clean_git_blob_python_and_launcher(tmp_path, monkeypatch):
    framework = tmp_path / "framework"
    adapter = framework / "tools" / "worker_lab_adapter.py"
    launcher = framework / "codex.cmd"
    adapter.parent.mkdir(parents=True)
    adapter.write_text("# inert adapter\n", encoding="utf-8")
    launcher.write_text("@echo off\n", encoding="utf-8")
    for command in (
        ["git", "init"], ["git", "config", "core.autocrlf", "false"],
        ["git", "config", "user.email", "fixture@example.com"],
        ["git", "config", "user.name", "Fixture"], ["git", "add", "."],
        ["git", "commit", "-m", "fixture"],
    ):
        subprocess.run(command, cwd=framework, check=True, capture_output=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=framework, check=True, capture_output=True, text=True
    ).stdout.strip()
    adapter_digest = "sha256:" + hashlib.sha256(adapter.read_bytes()).hexdigest()
    launcher_digest = "sha256:" + hashlib.sha256(launcher.read_bytes()).hexdigest()
    configured = FrameworkConfiguration(
        framework, head, Path(r"C:\Program Files\Python312\python.exe"),
        adapter_digest, launcher, launcher_digest,
    )
    monkeypatch.setattr("worker_lab.framework_client._read_launcher_version", lambda _: "0.149.1")
    assert inspect_configuration(configured).framework_head == head
    (framework / "unexpected.txt").write_text("drift", encoding="utf-8")
    with pytest.raises(LabValidationError) as error:
        inspect_configuration(configured)
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"
