import json
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.provider_qualification import (
    MINIMUM_CONTEXT_TOKENS,
    PYDANTIC_AI_OLLAMA_V1,
    HostProviderQualification,
    inspect_host_provider,
)
from worker_lab.runtime_selection import CODING_WORKER_V1


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def _repository(tmp_path: Path, *, authority: str = "DISABLED") -> Path:
    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    (root / "config" / "portable-installation-manifest.json").write_text(
        json.dumps({"activation_policy": {"execution_authority": authority}}),
        encoding="utf-8",
    )
    return root


def _executable(tmp_path: Path) -> Path:
    path = tmp_path / "ollama.exe"
    path.write_bytes(b"synthetic ollama executable")
    return path


def _metadata_reader(*, context: int = MINIMUM_CONTEXT_TOKENS, capabilities=("completion", "tools")):
    calls = []

    def read(method, url, payload, timeout):
        calls.append((method, url, payload, timeout))
        if url.endswith("/api/version"):
            return {"version": "0.33.3"}
        if url.endswith("/api/tags"):
            return {
                "models": [
                    {
                        "model": "qwen2.5-coder:7b",
                        "digest": DIGEST_B,
                    }
                ]
            }
        if url.endswith("/api/show"):
            assert payload == {"model": "qwen2.5-coder:7b"}
            return {
                "capabilities": list(capabilities),
                "model_info": {"qwen2.context_length": context},
            }
        raise AssertionError(f"unexpected metadata endpoint: {url}")

    return calls, read


def test_candidate_is_bound_to_coding_worker_and_least_privilege_file_surface():
    candidate = PYDANTIC_AI_OLLAMA_V1

    assert candidate.runtime_requirement_profile_id == CODING_WORKER_V1.profile_id
    assert candidate.runtime_requirement_digest == CODING_WORKER_V1.digest()
    assert candidate.harness_project == "pydantic/pydantic-ai"
    assert candidate.harness_distribution == "pydantic-ai-slim"
    assert candidate.provider_kind == "ollama"
    assert candidate.transport_policy == "loopback-http-only"
    assert candidate.allowed_effects == ("read-bounded-file", "write-bounded-file")
    assert candidate.forbidden_effects == (
        "approval",
        "git",
        "network",
        "process",
        "publication",
        "shell",
    )
    assert candidate.minimum_context_tokens == 32_768
    assert candidate.required_model_capabilities == ("tools",)


def test_host_qualification_uses_metadata_only_and_never_chat(tmp_path):
    root = _repository(tmp_path)
    executable = _executable(tmp_path)
    calls, http_json = _metadata_reader()

    report = inspect_host_provider(
        model="qwen2.5-coder:7b",
        repository_root=root,
        executable_resolver=lambda _: str(executable),
        version_reader=lambda _: "ollama version 0.33.3",
        distribution_reader=lambda _: ("2.40.0", DIGEST_A),
        http_json=http_json,
    )

    assert report.provider_runtime_qualified is True
    assert report.execution_authority == "DISABLED"
    assert report.execution_ready is False
    assert report.runtime_requirement_profile_id == "coding-worker:v1"
    assert report.model_digest == DIGEST_B
    assert report.model_context_tokens == MINIMUM_CONTEXT_TOKENS
    assert report.model_capabilities == ("completion", "tools")
    assert [url.rsplit("/", 2)[-2:] for _, url, _, _ in calls] == [
        ["api", "version"],
        ["api", "tags"],
        ["api", "show"],
    ]
    assert all(not url.endswith("/api/chat") for _, url, _, _ in calls)

    reparsed = HostProviderQualification.from_mapping(report.to_dict())
    assert reparsed == report
    assert reparsed.digest() == report.digest()


def test_qualification_rejects_non_loopback_or_enabled_authority(tmp_path):
    executable = _executable(tmp_path)
    calls, http_json = _metadata_reader()

    with pytest.raises(LabValidationError) as error:
        inspect_host_provider(
            model="qwen2.5-coder:7b",
            repository_root=_repository(tmp_path / "one"),
            base_url="http://192.168.1.5:11434",
            executable_resolver=lambda _: str(executable),
            version_reader=lambda _: "ollama version 0.33.3",
            distribution_reader=lambda _: ("2.40.0", DIGEST_A),
            http_json=http_json,
        )
    assert error.value.code == "PROVIDER_ENDPOINT_INVALID"

    with pytest.raises(LabValidationError) as error:
        inspect_host_provider(
            model="qwen2.5-coder:7b",
            repository_root=_repository(tmp_path / "two", authority="ENABLED"),
            executable_resolver=lambda _: str(executable),
            version_reader=lambda _: "ollama version 0.33.3",
            distribution_reader=lambda _: ("2.40.0", DIGEST_A),
            http_json=http_json,
        )
    assert error.value.code == "PROVIDER_QUALIFICATION_AUTHORITY_INVALID"
    assert calls == []


def test_qualification_rejects_missing_tools_or_insufficient_context(tmp_path):
    executable = _executable(tmp_path)

    _, no_tools = _metadata_reader(capabilities=("completion",))
    with pytest.raises(LabValidationError) as error:
        inspect_host_provider(
            model="qwen2.5-coder:7b",
            repository_root=_repository(tmp_path / "one"),
            executable_resolver=lambda _: str(executable),
            version_reader=lambda _: "ollama version 0.33.3",
            distribution_reader=lambda _: ("2.40.0", DIGEST_A),
            http_json=no_tools,
        )
    assert error.value.code == "PROVIDER_MODEL_CAPABILITY_INVALID"

    _, short_context = _metadata_reader(context=8_192)
    with pytest.raises(LabValidationError) as error:
        inspect_host_provider(
            model="qwen2.5-coder:7b",
            repository_root=_repository(tmp_path / "two"),
            executable_resolver=lambda _: str(executable),
            version_reader=lambda _: "ollama version 0.33.3",
            distribution_reader=lambda _: ("2.40.0", DIGEST_A),
            http_json=short_context,
        )
    assert error.value.code == "PROVIDER_MODEL_CONTEXT_INVALID"


def test_qualification_record_cannot_claim_execution_readiness(tmp_path):
    root = _repository(tmp_path)
    executable = _executable(tmp_path)
    _, http_json = _metadata_reader()
    report = inspect_host_provider(
        model="qwen2.5-coder:7b",
        repository_root=root,
        executable_resolver=lambda _: str(executable),
        version_reader=lambda _: "ollama version 0.33.3",
        distribution_reader=lambda _: ("2.40.0", DIGEST_A),
        http_json=http_json,
    )
    value = report.to_dict()
    value["execution_ready"] = True

    with pytest.raises(LabValidationError) as error:
        HostProviderQualification.from_mapping(value)
    assert error.value.code == "PROVIDER_FIELD_INVALID"
