import json
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.provider_qualification import (
    MINIMUM_CONTEXT_TOKENS,
    PYDANTIC_AI_OLLAMA_V1,
)
from worker_lab.runtime_selection import CODING_WORKER_V2
from tests.provider_capability_fixture import installation_observation
from worker_lab.provider_qualification import (
    CAPABILITY_PROBE_EVIDENCE_SCHEMA,
    CONTEXT_CAPABILITY_CANARY_DIGEST,
    CONTEXT_CAPABILITY_FIXTURE_ID,
    TOOL_CAPABILITY_FIXTURE_ID,
    TOOL_CAPABILITY_PATH,
    TOOL_CAPABILITY_RESULT_DIGEST,
    CapabilityProbeEvidence,
    ProviderCapabilityQualification,
    inspect_provider_installation,
    qualify_provider_capabilities,
)


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

    assert candidate.runtime_requirement_profile_id == CODING_WORKER_V2.profile_id
    assert candidate.runtime_requirement_digest == CODING_WORKER_V2.digest()
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











def _passing_probe(request, *, prompt_tokens=None):
    return CapabilityProbeEvidence(
        schema_version=CAPABILITY_PROBE_EVIDENCE_SCHEMA,
        request_digest=request.digest(),
        tool_fixture_id=TOOL_CAPABILITY_FIXTURE_ID,
        tool_call_name="read_file",
        tool_call_path=TOOL_CAPABILITY_PATH,
        tool_result_digest=TOOL_CAPABILITY_RESULT_DIGEST,
        tool_result_consumed=True,
        tool_evidence_digest=DIGEST_A,
        context_fixture_id=CONTEXT_CAPABILITY_FIXTURE_ID,
        context_target_tokens=request.requested_context_tokens,
        context_prompt_tokens=prompt_tokens or request.requested_context_tokens,
        context_canary_digest=CONTEXT_CAPABILITY_CANARY_DIGEST,
        context_canary_observed=True,
        context_evidence_digest=DIGEST_B,
    )


def test_installation_observation_records_metadata_without_claiming_capability(tmp_path):
    root = _repository(tmp_path)
    executable = _executable(tmp_path)
    calls, http_json = _metadata_reader(context=8_192, capabilities=("completion",))
    observation = inspect_provider_installation(
        model="qwen2.5-coder:7b",
        repository_root=root,
        executable_resolver=lambda _: str(executable),
        version_reader=lambda _: "ollama version 0.33.3",
        distribution_reader=lambda _: ("2.40.0", DIGEST_A),
        http_json=http_json,
    )
    assert observation.model_context_tokens == 8_192
    assert observation.model_capabilities == ("completion",)
    assert not hasattr(observation, "capability_qualified")
    assert not hasattr(observation, "provider_runtime_qualified")
    assert all(not url.endswith("/api/chat") for _, url, _, _ in calls)


def test_controlled_capability_qualification_requires_explicit_probe_runner():
    with pytest.raises(LabValidationError) as error:
        qualify_provider_capabilities(installation_observation(), probe_runner=None)
    assert error.value.code == "PROVIDER_CAPABILITY_PROBE_REQUIRED"


def test_controlled_probe_seals_tool_and_context_evidence():
    observed = installation_observation()
    requests = []

    def runner(request):
        requests.append(request)
        return _passing_probe(request)

    qualified = qualify_provider_capabilities(observed, probe_runner=runner)
    assert len(requests) == 1
    assert qualified.installation_observation_digest == observed.digest()
    assert qualified.capability_qualified is True
    assert qualified.execution_ready is False
    assert qualified.requested_context_tokens == 32_768
    assert qualified.effective_context_tokens == 32_768
    assert ProviderCapabilityQualification.from_mapping(qualified.to_dict()) == qualified


def test_metadata_labels_are_preconditions_not_capability_proof():
    called = False

    def runner(request):
        nonlocal called
        called = True
        return _passing_probe(request)

    with pytest.raises(LabValidationError) as error:
        qualify_provider_capabilities(
            installation_observation(model_capabilities=("completion",)),
            probe_runner=runner,
        )
    assert error.value.code == "PROVIDER_CAPABILITY_PRECONDITION_INVALID"
    assert called is False


def test_controlled_probe_rejects_unproven_context_or_tool_behavior():
    observed = installation_observation()

    def short_context(request):
        return _passing_probe(request, prompt_tokens=request.requested_context_tokens - 1)

    with pytest.raises(LabValidationError) as error:
        qualify_provider_capabilities(observed, probe_runner=short_context)
    assert error.value.code == "PROVIDER_CAPABILITY_EVIDENCE_INVALID"

    def wrong_tool(request):
        evidence = _passing_probe(request)
        return CapabilityProbeEvidence(**{**evidence.to_dict(), "tool_call_name": "run_shell"})

    with pytest.raises(LabValidationError) as error:
        qualify_provider_capabilities(observed, probe_runner=wrong_tool)
    assert error.value.code == "PROVIDER_CAPABILITY_EVIDENCE_INVALID"
