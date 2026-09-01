import json
import io
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

import tools.worker_lab_adapter as adapter
from tools.codex_runtime import CodexExecution
from tools.worker_lab_adapter import (
    REQUEST_SCHEMA, AdapterError, AdapterExecution, MAX_PROPOSAL_BYTES, canonical_json, digest,
    execute_read_only, invocation_identity, prepare, preflight,
)
from tools.workspace_write_adapter import (
    REQUEST_SCHEMA as WORKSPACE_WRITE_REQUEST_SCHEMA,
    TASK_SCHEMA as WORKSPACE_WRITE_TASK_SCHEMA,
    execute_workspace_write,
)


DIGEST = "sha256:" + "a" * 64
PROMPT = "Propose a bounded synthetic read-only change."


def invocation(state="PREPARED", **updates):
    authorized = state != "PREPARED"
    value = {
        "schema_version": "worker-lab-framework-invocation:v2", "invocation_id": "INVOCATION-001",
        "attempt_id": "ATTEMPT-001", "operation": "read-only-proposal", "exercise_id": "exercise",
        "exercise_version": 1, "exercise_digest": DIGEST, "policy_id": "policy", "policy_version": 1,
        "policy_digest": DIGEST, "role_id": "role", "role_version": 1, "role_digest": DIGEST,
        "context_manifest_id": "context", "context_manifest_version": 1, "context_digest": DIGEST,
        "task_digest": DIGEST, "test_catalog_version": "worker-lab-v3", "test_catalog_digest": DIGEST,
        "test_plan_digest": DIGEST, "test_ids": ["T001"], "worker_lab_installation_digest": DIGEST,
        "worker_lab_contract_version": "worker-lab-framework-client:v2", "framework_installation_digest": DIGEST,
        "framework_contract_version": "worker-lab-framework-adapter:v2", "workspace_receipt_digest": DIGEST,
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
        b'{"schema_version":"worker-lab-framework-adapter-request:v2",'
        b'"schema_version":"worker-lab-framework-adapter-request:v2",'
        b'"invocation":{},"prompt":"x"}'
    )
    with pytest.raises(AdapterError) as error:
        prepare(duplicate, runtime_identity=DIGEST)
    assert error.value.code == "INTEGRATION_RESULT_INVALID"


@pytest.mark.parametrize("raw", [b"", b"\xff", b"{}", b'{"schema_version":"worker-lab-framework-adapter-request:v2","invocation":null,"prompt":"x"}', b"x\x00y"])
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
    installed = adapter._installed_adapter_identity()
    value["framework_installation_digest"] = installed.framework_installation_digest
    monkeypatch.setattr(adapter.shutil, "which", lambda *_args, **_kwargs: str(installed.codex_path))
    identity, launcher = adapter.local_runtime_identity(value, version_reader=lambda _: "0.149.1")
    assert identity.startswith("sha256:")
    assert adapter.Path(launcher).resolve() == installed.codex_path.resolve()
    with pytest.raises(AdapterError) as error:
        adapter.local_runtime_identity(value, version_reader=lambda _: "0.149.2")
    assert error.value.code == "CODEX_VERSION_INVALID"


def _installation_fixture(tmp_path):
    source_root = adapter.Path(adapter.__file__).resolve().parents[3]
    manifest = json.loads((source_root / "config" / "installation-manifest.json").read_text(encoding="utf-8"))
    for relative in (
        "components/autonomous-worker-framework/tools",
        "components/worker-lab",
        "components/local-model-bench",
        "config",
    ):
        (tmp_path / relative).mkdir(parents=True, exist_ok=True)
    for name in (
        "code_task.py",
        "codex_runtime.py",
        "consumer_profile.py",
        "local_worker_harness.py",
        "repository_handoff.py",
        "worker_lab_adapter.py",
        "worker_result.py",
        "workspace_write_adapter.py",
    ):
        shutil.copy2(
            source_root / "components" / "autonomous-worker-framework" / "tools" / name,
            tmp_path / "components" / "autonomous-worker-framework" / "tools" / name,
        )
    manifest_path = tmp_path / "config" / "installation-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    adapter_path = tmp_path / "components" / "autonomous-worker-framework" / "tools" / "worker_lab_adapter.py"
    return manifest, manifest_path, adapter_path


def test_framework_manifest_parser_rejects_substitution_traversal_and_dependency_drift(tmp_path):
    manifest, manifest_path, adapter_path = _installation_fixture(tmp_path)
    assert adapter._installed_adapter_identity(
        manifest_path=manifest_path, adapter_path=adapter_path,
    ).framework_installation_digest.startswith("sha256:")

    unknown = json.loads(json.dumps(manifest))
    unknown["unexpected"] = True
    manifest_path.write_text(json.dumps(unknown), encoding="utf-8")
    with pytest.raises(AdapterError):
        adapter._installed_adapter_identity(manifest_path=manifest_path, adapter_path=adapter_path)

    traversal = json.loads(json.dumps(manifest))
    traversal["components"]["autonomous-worker-framework"]["root"] = "../framework"
    manifest_path.write_text(json.dumps(traversal), encoding="utf-8")
    with pytest.raises(AdapterError):
        adapter._installed_adapter_identity(manifest_path=manifest_path, adapter_path=adapter_path)

    stale = json.loads(json.dumps(manifest))
    stale["components"]["autonomous-worker-framework"]["installed_tree"]["files"][0]["sha256"] = DIGEST
    manifest_path.write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(AdapterError):
        adapter._installed_adapter_identity(manifest_path=manifest_path, adapter_path=adapter_path)

    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "components" / "autonomous-worker-framework" / "tools" / "codex_runtime.py").unlink()
    with pytest.raises(AdapterError):
        adapter._installed_adapter_identity(manifest_path=manifest_path, adapter_path=adapter_path)


@pytest.mark.parametrize("mode,state", [("preflight", "AUTHORIZED"), ("execute-read-only", "DISPATCHING")])
def test_cli_rejects_execution_while_installation_policy_is_disabled(monkeypatch, mode, state):
    raw = canonical_json(request(state)).encode("utf-8")
    stdin = type("Input", (), {"buffer": io.BytesIO(raw)})()
    stdout = type("Output", (), {"buffer": io.BytesIO()})()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    reached_runtime = []
    monkeypatch.setattr(adapter, "local_runtime_identity", lambda *args, **kwargs: reached_runtime.append(True))
    assert adapter.main([mode, "--protocol", adapter.PROTOCOL]) == 1
    assert json.loads(stdout.buffer.getvalue()) == {
        "failure_code": "INTEGRATION_EXECUTION_DISABLED", "retryable": False,
    }
    assert not reached_runtime


def test_isolated_direct_script_starts_without_import_path_fallback():
    process = subprocess.run(
        [sys.executable, "-I", "-B", str(adapter.Path(adapter.__file__)), "--help"],
        cwd=adapter.Path(adapter.__file__).parents[1], check=False,
        capture_output=True, text=True, encoding="utf-8",
    )
    assert process.returncode == 0
    assert "Strict Worker Lab framework adapter" in process.stdout


def test_cli_retains_only_a_stable_disabled_policy_code(monkeypatch):
    raw = canonical_json(request("AUTHORIZED")).encode("utf-8")
    stdin = type("Input", (), {"buffer": io.BytesIO(raw)})()
    stdout = type("Output", (), {"buffer": io.BytesIO()})()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    assert adapter.main(["preflight", "--protocol", adapter.PROTOCOL]) == 1
    assert json.loads(stdout.buffer.getvalue()) == {
        "failure_code": "INTEGRATION_EXECUTION_DISABLED", "retryable": False,
    }


def test_production_retains_only_the_final_message_not_cli_stderr(monkeypatch, tmp_path):
    observed = []
    request_type = adapter._framework_runtime(adapter._installed_adapter_identity()).CodexRequest

    def fake_execute(request, *, executable):
        observed.append(request.output_last_message)
        assert request.output_last_message is not None
        request.output_last_message.write_text("proposal", encoding="utf-8")
        return CodexExecution(("codex",), 0, "progress", "normal CLI progress")

    monkeypatch.setattr(
        adapter, "_framework_runtime",
        lambda _: SimpleNamespace(CodexRequest=request_type,
                                  execute_codex_bounded=fake_execute),
    )
    result = adapter._execute_production("prompt", tmp_path, "codex")
    assert result == AdapterExecution(b"proposal", b"", 0)
    assert observed[0] is not None and not observed[0].exists()


def _workspace_write_request(root, *, state="DISPATCHING", **updates):
    value = invocation(
        state,
        operation="workspace-write-code-task",
        sandbox_mode="workspace-write",
        framework_contract_version=adapter.WORKSPACE_WRITE_PROTOCOL,
        readable_paths=[{"path": "README.md", "digest": "sha256:" + "b" * 64}],
        writable_paths=["tests/test_assets.py"],
    )
    value.update(updates.pop("invocation", {}))
    request_value = {
        "schema_version": WORKSPACE_WRITE_REQUEST_SCHEMA,
        "invocation": value,
        "prompt": PROMPT,
        "workspace_write": {
            "schema_version": WORKSPACE_WRITE_TASK_SCHEMA,
            "invocation_digest": invocation_identity(value),
            "objective": "Change one bounded test fixture.",
            "acceptance_criteria": ["The target fixture is updated."],
            "consumer_profile": {
                "version": "consumer-profile:v1",
                "consumer": "worker-lab-role",
                "authority_paths": ["README.md"],
                "protected_prefixes": [],
                "protected_exact": [],
                "product_invariants": ["Bounded candidate only."],
                "full_validation": [{
                    "name": "T001",
                    "argv": ["git", "diff", "--check"],
                    "timeout_seconds": 10,
                }],
            },
            "test_ids": ["T001"],
            "writable_paths": ["tests/test_assets.py"],
        },
    }
    request_value.update(updates)
    return request_value


def _workspace_write_repo(tmp_path):
    root = tmp_path / "workspace-write"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
    (root / "README.md").write_text("authority\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_assets.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
    return root


def test_workspace_write_v3_reuses_context_code_task_and_handoff_primitives(tmp_path, monkeypatch):
    root = _workspace_write_repo(tmp_path)
    request_value = _workspace_write_request(root)

    def executor(_):
        (root / "tests" / "test_assets.py").write_text("VALUE = 2\n", encoding="utf-8")
        return CodexExecution(("codex",), 0, "done", "")

    monkeypatch.chdir(root)
    response = json.loads(execute_workspace_write(
        canonical_json(request_value),
        runtime_identity=DIGEST,
        executor=executor,
        framework_root=tmp_path / "framework",
    ))
    assert response["invocation_digest"] == invocation_identity(request_value["invocation"])
    assert response["changed_paths"] == ["tests/test_assets.py"]
    assert response["candidate_digest"].startswith("sha256:")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ({"invocation": {"state": "AUTHORIZED"}}, "INTEGRATION_AUTHORIZATION_INVALID"),
        ({"workspace_write": {"unexpected": True}}, "INTEGRATION_FIELDS_INVALID"),
    ],
)
def test_workspace_write_v3_rejects_bad_state_and_malformed_contract(tmp_path, mutation, code):
    root = _workspace_write_repo(tmp_path)
    request_value = _workspace_write_request(root)
    for key, value in mutation.items():
        if key == "invocation":
            request_value[key].update(value)
            request_value["workspace_write"]["invocation_digest"] = invocation_identity(request_value[key])
        else:
            request_value[key].update(value)
    with pytest.raises(AdapterError) as error:
        execute_workspace_write(
            canonical_json(request_value),
            runtime_identity=DIGEST,
            executor=lambda _: (_ for _ in ()).throw(AssertionError("must not execute")),
            framework_root=tmp_path / "framework",
        )
    assert error.value.code == code


def test_workspace_write_v3_rejects_scope_and_does_not_mutate_without_executor(tmp_path):
    root = _workspace_write_repo(tmp_path)
    request_value = _workspace_write_request(root)
    request_value["invocation"]["readable_paths"] = [{
        "path": "tests/test_assets.py",
        "digest": "sha256:" + "b" * 64,
    }]
    request_value["workspace_write"]["consumer_profile"]["authority_paths"] = ["tests/test_assets.py"]
    request_value["workspace_write"]["invocation_digest"] = invocation_identity(request_value["invocation"])
    with pytest.raises(AdapterError) as error:
        execute_workspace_write(
            canonical_json(request_value),
            runtime_identity=DIGEST,
            executor=lambda _: (_ for _ in ()).throw(AssertionError("must not execute")),
            framework_root=tmp_path / "framework",
        )
    assert error.value.code == "INTEGRATION_SCOPE_FAILED"
    before = (root / "tests" / "test_assets.py").read_bytes()
    with pytest.raises(AdapterError) as error:
        execute_workspace_write(
            canonical_json(_workspace_write_request(root)),
            runtime_identity=DIGEST,
            executor=None,
            framework_root=tmp_path / "framework",
        )
    assert error.value.code == "INTEGRATION_EXECUTION_DISABLED"
    assert (root / "tests" / "test_assets.py").read_bytes() == before


def test_workspace_write_v3_cli_keeps_runtime_unreachable_while_disabled(tmp_path, monkeypatch):
    root = _workspace_write_repo(tmp_path)
    raw = canonical_json(_workspace_write_request(root)).encode("utf-8")
    stdin = type("Input", (), {"buffer": io.BytesIO(raw)})()
    stdout = type("Output", (), {"buffer": io.BytesIO()})()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    reached_runtime = []
    monkeypatch.setattr(
        adapter,
        "local_runtime_identity",
        lambda *args, **kwargs: reached_runtime.append(True),
    )
    assert adapter.main(["execute-workspace-write", "--protocol", adapter.WORKSPACE_WRITE_PROTOCOL]) == 1
    assert json.loads(stdout.buffer.getvalue()) == {
        "failure_code": "INTEGRATION_EXECUTION_DISABLED",
        "retryable": False,
    }
    assert not reached_runtime
