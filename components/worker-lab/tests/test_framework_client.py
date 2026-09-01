import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.framework_client import (
    FrameworkIdentityEvidence, WorkerLabIdentityEvidence,
    call_adapter, fixed_command, inspect_configuration, pinned_framework_configuration,
    runtime_identity,
)
from worker_lab.installation_manifest import load_installation_manifest, require_execution_enabled
from worker_lab.integration import InvocationRecord, InvocationState, transition_invocation
from tests.test_integration import DIGEST, record


PROMPT = "Propose a bounded synthetic read-only change."
PROMPT_DIGEST = "sha256:" + hashlib.sha256(PROMPT.encode()).hexdigest()


def invocation():
    value = record().to_dict()
    value["prompt_digest"] = PROMPT_DIGEST
    return InvocationRecord.from_mapping(value)


def config():
    return pinned_framework_configuration()


def evidence(**updates):
    configured = config()
    value = {
        "framework_root": configured.framework_root,
        "framework_installation_digest": configured.framework_installation_digest,
        "framework_files": configured.framework_files,
        "adapter_path": configured.framework_root / "tools/worker_lab_adapter.py",
        "adapter_digest": configured.adapter_digest,
        "python_path": configured.python_executable,
        "python_digest": configured.python_digest,
        "python_version": configured.python_version,
        "python_implementation": configured.python_implementation,
        "python_architecture": configured.python_architecture,
        "codex_launcher_path": configured.codex_launcher,
        "codex_launcher_digest": configured.codex_launcher_digest,
        "codex_version": configured.codex_version,
    }
    value.update(updates)
    return FrameworkIdentityEvidence(**value)


def lab_evidence(**updates):
    manifest = load_installation_manifest()
    value = {
        "worker_lab_root": manifest.installation_root / manifest.components["worker-lab"].root,
        "worker_lab_installation_digest": DIGEST,
    }
    value.update(updates)
    return WorkerLabIdentityEvidence(**value)


def test_fixed_commands_share_one_runtime_identity_and_use_trusted_configuration():
    configured = config()
    command = fixed_command(configured, "prepare", evidence=evidence())
    assert command == (
        str(configured.python_executable), "-I", "-B",
        str(configured.framework_root / "tools/worker_lab_adapter.py"), "prepare",
        "--protocol", "worker-lab-framework-adapter:v2",
    )
    assert runtime_identity(configured, invocation(), evidence=evidence()).startswith("sha256:")
    with pytest.raises(LabValidationError):
        fixed_command(configured, "workspace-write", evidence=evidence())
    for mode in ("preflight", "execute-read-only"):
        with pytest.raises(LabValidationError) as error:
            fixed_command(configured, mode, evidence=evidence())
        assert error.value.code == "INTEGRATION_EXECUTION_DISABLED"


@pytest.mark.parametrize("field,value", [
    ("framework_installation_digest", "sha256:" + "c" * 64),
    ("framework_files", (("tools/worker_lab_adapter.py", DIGEST),)),
    ("adapter_digest", "sha256:" + "c" * 64), ("python_version", "3.12.11"),
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
    unreviewed = replace(config(), framework_installation_digest=DIGEST)
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
            worker_lab_evidence=lab_evidence(worker_lab_installation_digest="sha256:" + "c" * 64), runner=fake,
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


def test_client_rejects_wrong_worker_lab_installation_before_runner_dispatch():
    item = invocation()
    called = False

    def fake(*_):
        nonlocal called
        called = True
        return b"{}"

    with pytest.raises(LabValidationError) as error:
        call_adapter(
            item, config(), "prepare", prompt=PROMPT, evidence=evidence(),
            worker_lab_evidence=lab_evidence(worker_lab_installation_digest="sha256:" + "b" * 64), runner=fake,
        )
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"
    assert not called


def test_configuration_inspection_verifies_manifest_files_python_and_launcher():
    configured = config()
    inspected = inspect_configuration(configured)
    assert inspected.framework_installation_digest == configured.framework_installation_digest
    assert inspected.framework_files == configured.framework_files


def test_manifest_rejects_substitution_traversal_and_disabled_execution(tmp_path):
    source = json.loads(config().manifest_path.read_text(encoding="utf-8"))
    manifest_path = tmp_path / "config" / "installation-manifest.json"
    manifest_path.parent.mkdir()

    substituted = dict(source)
    substituted["unknown"] = True
    manifest_path.write_text(json.dumps(substituted), encoding="utf-8")
    with pytest.raises(LabValidationError) as error:
        load_installation_manifest(manifest_path, verify_files=False)
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"

    traversed = json.loads(json.dumps(source))
    traversed["components"]["worker-lab"]["root"] = "../worker-lab"
    manifest_path.write_text(json.dumps(traversed), encoding="utf-8")
    with pytest.raises(LabValidationError) as error:
        load_installation_manifest(manifest_path, verify_files=False)
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"

    manifest_path.write_text(json.dumps(source), encoding="utf-8")
    parsed = load_installation_manifest(manifest_path, verify_files=False)
    with pytest.raises(LabValidationError) as error:
        require_execution_enabled(parsed)
    assert error.value.code == "INTEGRATION_EXECUTION_DISABLED"
