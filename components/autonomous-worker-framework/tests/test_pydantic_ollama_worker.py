from __future__ import annotations

import hashlib
import importlib.metadata
import json
import sys
from types import ModuleType, SimpleNamespace
from pathlib import Path

import pytest

from tools.pydantic_ollama_worker import (
    BoundedFileTools,
    PydanticWorkerError,
    QualifiedRuntimeBinding,
    SealedRuntimeSettings,
    execute_pydantic_ollama,
)
from tools.worker_runtime import WorkerRequest


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _settings() -> SealedRuntimeSettings:
    return SealedRuntimeSettings.from_mapping({
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
    })


def _binding() -> QualifiedRuntimeBinding:
    fixed = "sha256:" + ("a" * 64)
    settings = _settings()
    return QualifiedRuntimeBinding(
        qualification_digest=fixed,
        installation_observation_digest=fixed,
        runtime_settings_profile_id=settings.profile_id,
        runtime_settings_digest=settings.digest(),
        qualified_context_tokens=32768,
        candidate_id="pydantic-ai-ollama-files",
        tool_surface_id="acl-bounded-file-tools:v1",
        harness_distribution="pydantic-ai-slim",
        harness_version="2.40.0",
        harness_tree_digest=fixed,
        provider_kind="ollama",
        provider_endpoint="http://127.0.0.1:11434",
        provider_executable_sha256=fixed,
        provider_cli_version="ollama version 0.33.3",
        provider_api_version="0.33.3",
        model_name="qwen3-coder:test",
        model_digest=fixed,
        model_metadata_digest=fixed,
    )


def test_bounded_file_tools_read_then_atomic_write(tmp_path: Path):
    root = tmp_path.resolve()
    target = root / "target.py"
    target.write_bytes(b"VALUE = 1\r\n")

    tools = BoundedFileTools(
        root,
        readable_paths=("target.py",),
        writable_paths=("target.py",),
    )
    read = json.loads(tools.read_file("target.py"))
    assert read["content"] == "VALUE = 1\r\n"
    assert read["sha256"] == _digest("VALUE = 1\r\n")

    written = json.loads(
        tools.write_file(
            "target.py",
            "VALUE = 2\n",
            read["sha256"],
        )
    )
    assert written["sha256"] == _digest("VALUE = 2\n")
    assert target.read_bytes() == b"VALUE = 2\n"


def test_bounded_file_tools_reject_scope_escape_and_stale_write(tmp_path: Path):
    root = tmp_path.resolve()
    target = root / "target.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    other = root / "other.py"
    other.write_text("VALUE = 0\n", encoding="utf-8")

    tools = BoundedFileTools(
        root,
        readable_paths=("target.py",),
        writable_paths=("target.py",),
    )

    with pytest.raises(PydanticWorkerError) as escape:
        tools.read_file("../other.py")
    assert escape.value.code == "PYDANTIC_WORKER_SCOPE_INVALID"

    with pytest.raises(PydanticWorkerError) as out_of_scope:
        tools.read_file("other.py")
    assert out_of_scope.value.code == "PYDANTIC_WORKER_SCOPE_DENIED"

    with pytest.raises(PydanticWorkerError) as stale:
        tools.write_file("target.py", "VALUE = 3\n", _digest("stale\n"))
    assert stale.value.code == "PYDANTIC_WORKER_STALE_WRITE"
    assert target.read_text(encoding="utf-8") == "VALUE = 1\n"


def test_provider_adapter_receives_only_acl_owned_file_tools(tmp_path: Path):
    root = tmp_path.resolve()
    target = root / "target.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    observed = []

    request = WorkerRequest(
        prompt="Change VALUE from 1 to 2.",
        target_repo=root,
        framework_repo=tmp_path / "framework",
        sandbox="workspace-write",
        readable_paths=("target.py",),
        writable_paths=("target.py",),
    )

    def runner(req, binding, settings, tools):
        assert settings == _settings()
        observed.append((req, binding))
        read = json.loads(tools.read_file("target.py"))
        tools.write_file("target.py", "VALUE = 2\n", read["sha256"])
        assert not hasattr(tools, "run_shell")
        assert not hasattr(tools, "git")
        assert not hasattr(tools, "network")
        return "updated target.py"

    execution = execute_pydantic_ollama(request, _binding(), _settings(), runner=runner)

    assert len(observed) == 1
    assert execution.returncode == 0
    assert execution.stdout == "updated target.py"
    assert execution.command[:4] == ("pydantic-ai", "2.40.0", "ollama", "0.33.3")
    assert target.read_text(encoding="utf-8") == "VALUE = 2\n"


def test_provider_binding_requires_loopback_and_protected_tool_surface(tmp_path: Path):
    root = tmp_path.resolve()
    (root / "target.py").write_text("VALUE = 1\n", encoding="utf-8")
    request = WorkerRequest(
        prompt="Change the file.",
        target_repo=root,
        framework_repo=tmp_path / "framework",
        sandbox="workspace-write",
        readable_paths=("target.py",),
        writable_paths=("target.py",),
    )
    binding = _binding()

    invalid = QualifiedRuntimeBinding(
        **{
            **binding.to_dict(),
            "provider_endpoint": "http://192.0.2.10:11434",
        }
    )
    with pytest.raises(PydanticWorkerError) as remote:
        execute_pydantic_ollama(request, invalid, _settings(), runner=lambda *_: "never")
    assert remote.value.code == "PYDANTIC_WORKER_BINDING_INVALID"

    invalid_surface = QualifiedRuntimeBinding(
        **{
            **binding.to_dict(),
            "tool_surface_id": "shell:v1",
        }
    )
    with pytest.raises(PydanticWorkerError) as surface:
        execute_pydantic_ollama(request, invalid_surface, _settings(), runner=lambda *_: "never")
    assert surface.value.code == "PYDANTIC_WORKER_BINDING_INVALID"



def test_adapter_rejects_runtime_settings_or_context_not_sealed_by_qualification(tmp_path: Path):
    root = tmp_path.resolve()
    (root / "target.py").write_text("VALUE = 1\n", encoding="utf-8")
    request = WorkerRequest(
        prompt="Change the file.",
        target_repo=root,
        framework_repo=tmp_path / "framework",
        sandbox="workspace-write",
        readable_paths=("target.py",),
        writable_paths=("target.py",),
    )
    settings = _settings()
    changed = SealedRuntimeSettings(**{**settings.to_dict(), "request_limit": 13})
    with pytest.raises(PydanticWorkerError) as mismatch:
        execute_pydantic_ollama(request, _binding(), changed, runner=lambda *_: "never")
    assert mismatch.value.code == "PYDANTIC_WORKER_BINDING_INVALID"

    too_small = QualifiedRuntimeBinding(**{**_binding().to_dict(), "qualified_context_tokens": 8192})
    with pytest.raises(PydanticWorkerError) as context:
        execute_pydantic_ollama(request, too_small, settings, runner=lambda *_: "never")
    assert context.value.code == "PYDANTIC_WORKER_BINDING_INVALID"


def test_production_pydantic_path_uses_exact_sealed_limits_without_real_provider(monkeypatch, tmp_path: Path):
    root = tmp_path.resolve()
    (root / "target.py").write_text("VALUE = 1\n", encoding="utf-8")
    request = WorkerRequest(
        prompt="Inspect the file and summarize.",
        target_repo=root,
        framework_repo=tmp_path / "framework",
        sandbox="workspace-write",
        readable_paths=("target.py",),
        writable_paths=("target.py",),
    )
    observed = {}

    class FakeUsageLimits:
        def __init__(self, *, request_limit, tool_calls_limit):
            observed["usage_limits"] = (request_limit, tool_calls_limit)

    class FakeAgent:
        def __init__(self, model, *, instructions, tools, retries, tool_timeout, max_concurrency):
            observed["agent"] = (retries, tool_timeout, max_concurrency, len(tools))

        def run_sync(self, prompt, *, usage_limits):
            observed["prompt"] = prompt
            return SimpleNamespace(output="fixture output")

    class FakeOllamaModel:
        def __init__(self, name, *, provider):
            observed["model"] = name

    class FakeOllamaProvider:
        def __init__(self, *, base_url):
            observed["base_url"] = base_url

    pydantic_ai = ModuleType("pydantic_ai")
    pydantic_ai.Agent = FakeAgent
    pydantic_ai.UsageLimits = FakeUsageLimits
    models = ModuleType("pydantic_ai.models")
    models_ollama = ModuleType("pydantic_ai.models.ollama")
    models_ollama.OllamaModel = FakeOllamaModel
    providers = ModuleType("pydantic_ai.providers")
    providers_ollama = ModuleType("pydantic_ai.providers.ollama")
    providers_ollama.OllamaProvider = FakeOllamaProvider
    monkeypatch.setitem(sys.modules, "pydantic_ai", pydantic_ai)
    monkeypatch.setitem(sys.modules, "pydantic_ai.models", models)
    monkeypatch.setitem(sys.modules, "pydantic_ai.models.ollama", models_ollama)
    monkeypatch.setitem(sys.modules, "pydantic_ai.providers", providers)
    monkeypatch.setitem(sys.modules, "pydantic_ai.providers.ollama", providers_ollama)
    monkeypatch.setattr(importlib.metadata, "version", lambda _: _binding().harness_version)

    execution = execute_pydantic_ollama(request, _binding(), _settings())
    assert execution.stdout == "fixture output"
    assert observed["usage_limits"] == (12, 24)
    assert observed["agent"] == ({"tools": 2, "output": 1}, 30, 1, 2)
    assert observed["base_url"] == "http://127.0.0.1:11434/v1"
