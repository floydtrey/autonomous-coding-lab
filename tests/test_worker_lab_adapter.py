import json
import io
import subprocess
import sys

import pytest

import tools.worker_lab_adapter as adapter
from tools.worker_lab_adapter import (
    REQUEST_SCHEMA, AdapterError, AdapterExecution, MAX_PROPOSAL_BYTES, canonical_json, digest,
    execute_read_only, invocation_identity, prepare, preflight,
)


DIGEST = "sha256:" + "a" * 64
PROMPT = "Propose a bounded synthetic read-only change."


def invocation(state="PREPARED", **updates):
    authorized = state != "PREPARED"
    value = {
        "schema_version": "worker-lab-framework-invocation:v1", "invocation_id": "INVOCATION-001",
        "attempt_id": "ATTEMPT-001", "operation": "read-only-proposal", "exercise_id": "exercise",
        "exercise_version": 1, "exercise_digest": DIGEST, "policy_id": "policy", "policy_version": 1,
        "policy_digest": DIGEST, "role_id": "role", "role_version": 1, "role_digest": DIGEST,
        "context_manifest_id": "context", "context_manifest_version": 1, "context_digest": DIGEST,
        "task_digest": DIGEST, "test_catalog_version": "worker-lab-v3", "test_catalog_digest": DIGEST,
        "test_plan_digest": DIGEST, "test_ids": ["T001"], "worker_lab_commit": "1" * 40,
        "worker_lab_contract_version": "worker-lab-framework-client:v1", "framework_commit": "2" * 40,
        "framework_contract_version": "worker-lab-framework-adapter:v1", "workspace_receipt_digest": DIGEST,
        "workspace_root_digest": DIGEST, "workspace_path_digest": DIGEST, "starting_commit": "3" * 40,
        "sandbox_mode": "read-only", "runtime_profile_id": "terra-medium:v1", "model": "gpt-5.6-terra",
        "reasoning_effort": "medium", "timeout_seconds": 900,
        "readable_paths": [{"path": "README.md", "digest": DIGEST}], "writable_paths": [],
        "prompt_digest": digest(PROMPT.encode()), "authorized_by": "trusted-controller" if authorized else None,
        "authorized_at": "2026-08-28T00:00:00Z" if authorized else None, "state": state,
        "result_digest": None,
    }
    value.update(updates)
    return value


def request(state="PREPARED", **updates):
    value = {"schema_version": REQUEST_SCHEMA, "invocation": invocation(state), "prompt": PROMPT}
    value.update(updates)
    return value


def test_preparation_requires_full_strict_request_and_returns_canonical_identity():
    value = request()
    response = json.loads(prepare(canonical_json(value), runtime_identity=DIGEST))
    assert response["invocation_digest"] == invocation_identity(value["invocation"])
    changed = request()
    changed["unknown"] = True
    with pytest.raises(AdapterError) as error:
        prepare(canonical_json(changed), runtime_identity=DIGEST)
    assert error.value.code == "INTEGRATION_FIELDS_INVALID"


def test_request_requires_canonical_json_and_rejects_duplicate_keys():
    value = request()
    with pytest.raises(AdapterError) as error:
        prepare(json.dumps(value), runtime_identity=DIGEST)
    assert error.value.code == "INTEGRATION_RESULT_INVALID"
    duplicate = (
        b'{"schema_version":"worker-lab-framework-adapter-request:v1",'
        b'"schema_version":"worker-lab-framework-adapter-request:v1",'
        b'"invocation":{},"prompt":"x"}'
    )
    with pytest.raises(AdapterError) as error:
        prepare(duplicate, runtime_identity=DIGEST)
    assert error.value.code == "INTEGRATION_RESULT_INVALID"


@pytest.mark.parametrize("raw", [b"", b"\xff", b"{}", b'{"schema_version":"worker-lab-framework-adapter-request:v1","invocation":null,"prompt":"x"}', b"x\x00y"])
def test_request_transport_rejects_empty_invalid_utf8_incomplete_type_and_nul(raw):
    with pytest.raises(AdapterError):
        prepare(raw, runtime_identity=DIGEST)


@pytest.mark.parametrize("prompt", ["C:\\secret", "C:/secret", "\\\\server\\share", "//server/share", "OPENAI_API_KEY=x", "bearer secret", "x" * 32_769], ids=["windows", "windows-slash", "unc", "unc-slash", "api-key", "bearer", "limit-plus-one"])
def test_request_rejects_windows_unc_credentials_and_limit(prompt):
    value = request(prompt=prompt)
    value["invocation"]["prompt_digest"] = digest(prompt.encode())
    with pytest.raises(AdapterError):
        prepare(canonical_json(value), runtime_identity=DIGEST)

    incomplete = request()
    del incomplete["prompt"]
    with pytest.raises(AdapterError) as error:
        prepare(canonical_json(incomplete), runtime_identity=DIGEST)
    assert error.value.code == "INTEGRATION_FIELDS_INVALID"


@pytest.mark.parametrize("mutation", [
    {"operation": "workspace-write-code-task"}, {"sandbox_mode": "workspace-write"},
    {"writable_paths": ["app.py"]}, {"model": "gpt-5.6-sol"}, {"timeout_seconds": 901},
])
def test_adapter_rejects_non_read_only_or_runtime_substitution(mutation):
    value = request()
    value["invocation"].update(mutation)
    with pytest.raises(AdapterError):
        prepare(json.dumps(value), runtime_identity=DIGEST)


@pytest.mark.parametrize("field,value", [
    ("invocation_id", 1), ("attempt_id", "bad id"), ("exercise_version", True),
    ("policy_version", 0), ("context_manifest_version", "1"),
    ("test_catalog_version", " worker-lab-v3"), ("test_ids", [1]),
    ("test_ids", ["T001", "T001"]), ("test_ids", ["T01"]),
])
def test_adapter_rejects_invalid_invocation_scalar_and_list_types(field, value):
    item = request()
    item["invocation"][field] = value
    with pytest.raises(AdapterError) as error:
        prepare(canonical_json(item), runtime_identity=DIGEST)
    assert error.value.code in {"INTEGRATION_FIELDS_INVALID", "INTEGRATION_IDENTITY_INVALID"}


def test_preflight_and_execution_require_exact_authorization_and_injected_seams():
    authorized = canonical_json(request("AUTHORIZED"))
    with pytest.raises(AdapterError) as error:
        preflight(authorized, runtime_identity=DIGEST, checker=None)
    assert error.value.code == "INTEGRATION_EXECUTION_DISABLED"
    assert json.loads(preflight(authorized, runtime_identity=DIGEST, checker=lambda: None))

    dispatching = canonical_json(request("DISPATCHING"))
    with pytest.raises(AdapterError) as error:
        execute_read_only(dispatching, runtime_identity=DIGEST, executor=None)
    assert error.value.code == "INTEGRATION_EXECUTION_DISABLED"
    response = json.loads(execute_read_only(
        dispatching, runtime_identity=DIGEST, executor=lambda _: AdapterExecution(b"proposal"),
    ))
    assert response["proposal_digest"] == digest(b"proposal")
    assert response["proposal_content"] == "proposal"
    for stdout in (b"x" * (MAX_PROPOSAL_BYTES + 1), b"OPENAI_API_KEY=x"):
        with pytest.raises(AdapterError):
            execute_read_only(
                dispatching, runtime_identity=DIGEST, executor=lambda _: AdapterExecution(stdout),
            )


def test_runtime_identity_uses_injected_launcher_version_reader(monkeypatch):
    value = invocation()
    value["framework_commit"] = "2" * 40
    adapter_bytes = adapter.Path(adapter.__file__).read_bytes()

    def fake_git(_, *args):
        if args[:2] == ("rev-parse", "HEAD"):
            return b"2" * 40 + b"\n"
        if args[:2] == ("status", "--porcelain=v1"):
            return b""
        if args[0] == "show":
            return adapter_bytes
        raise AssertionError(args)

    monkeypatch.setattr(adapter, "_git", fake_git)
    monkeypatch.setattr(adapter.shutil, "which", lambda *_args, **_kwargs: adapter.__file__)
    identity, launcher = adapter.local_runtime_identity(value, version_reader=lambda _: "0.149.1")
    assert identity.startswith("sha256:")
    assert launcher == adapter.__file__
    with pytest.raises(AdapterError) as error:
        adapter.local_runtime_identity(value, version_reader=lambda _: "0.149.2")
    assert error.value.code == "CODEX_VERSION_INVALID"


@pytest.mark.parametrize("mode,state", [("preflight", "AUTHORIZED"), ("execute-read-only", "DISPATCHING")])
def test_cli_enables_only_the_sealed_production_modes(monkeypatch, mode, state):
    raw = canonical_json(request(state)).encode("utf-8")
    stdin = type("Input", (), {"buffer": io.BytesIO(raw)})()
    stdout = type("Output", (), {"buffer": io.BytesIO()})()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(adapter, "local_runtime_identity", lambda _: (DIGEST, "codex"))
    checked = []
    monkeypatch.setattr(adapter, "check_chatgpt_auth", lambda **_: checked.append(True))
    monkeypatch.setattr(adapter, "_execute_production", lambda *_: AdapterExecution(b"proposal"))
    assert adapter.main([mode, "--protocol", adapter.PROTOCOL]) == 0
    response = json.loads(stdout.buffer.getvalue())
    assert response["runtime_identity"] == DIGEST
    if mode == "preflight":
        assert checked == [True]
    else:
        assert response["proposal_content"] == "proposal"


def test_isolated_direct_script_starts_without_import_path_fallback():
    process = subprocess.run(
        [sys.executable, "-I", "-B", str(adapter.Path(adapter.__file__)), "--help"],
        cwd=adapter.Path(adapter.__file__).parents[1], check=False,
        capture_output=True, text=True, encoding="utf-8",
    )
    assert process.returncode == 0
    assert "Strict Worker Lab framework adapter" in process.stdout
