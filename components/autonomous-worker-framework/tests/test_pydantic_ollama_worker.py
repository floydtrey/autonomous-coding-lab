from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.pydantic_ollama_worker import (
    BoundedFileTools,
    PydanticWorkerError,
    QualifiedRuntimeBinding,
    execute_pydantic_ollama,
)
from tools.worker_runtime import WorkerRequest


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _binding() -> QualifiedRuntimeBinding:
    fixed = "sha256:" + ("a" * 64)
    return QualifiedRuntimeBinding(
        qualification_digest=fixed,
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

    def runner(req, binding, tools):
        observed.append((req, binding))
        read = json.loads(tools.read_file("target.py"))
        tools.write_file("target.py", "VALUE = 2\n", read["sha256"])
        assert not hasattr(tools, "run_shell")
        assert not hasattr(tools, "git")
        assert not hasattr(tools, "network")
        return "updated target.py"

    execution = execute_pydantic_ollama(request, _binding(), runner=runner)

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
        execute_pydantic_ollama(request, invalid, runner=lambda *_: "never")
    assert remote.value.code == "PYDANTIC_WORKER_BINDING_INVALID"

    invalid_surface = QualifiedRuntimeBinding(
        **{
            **binding.to_dict(),
            "tool_surface_id": "shell:v1",
        }
    )
    with pytest.raises(PydanticWorkerError) as surface:
        execute_pydantic_ollama(request, invalid_surface, runner=lambda *_: "never")
    assert surface.value.code == "PYDANTIC_WORKER_BINDING_INVALID"
