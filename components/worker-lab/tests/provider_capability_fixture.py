from __future__ import annotations

import sys
from pathlib import Path

from worker_lab.provider_qualification import (
    CAPABILITY_QUALIFICATION_SCHEMA,
    INSTALLATION_OBSERVATION_SCHEMA,
    CONTEXT_CAPABILITY_FIXTURE_ID,
    PROVIDER_ADAPTER_ID,
    TOOL_CAPABILITY_FIXTURE_ID,
    PYDANTIC_AI_OLLAMA_V1,
    ProviderCapabilityQualification,
    ProviderInstallationObservation,
)
from worker_lab.runtime_selection import selected_runtime_requirement_v3
from worker_lab.runtime_settings import CODING_WORKER_SETTINGS_V1


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
DIGEST_D = "sha256:" + "d" * 64
DIGEST_E = "sha256:" + "e" * 64


def installation_observation(
    *,
    model_name: str = "qwen2.5-coder:7b",
    model_digest: str = DIGEST_B,
    model_metadata_digest: str = DIGEST_C,
    model_context_tokens: int = 65_536,
    model_capabilities: tuple[str, ...] = ("completion", "tools"),
    harness_tree_digest: str = DIGEST_D,
) -> ProviderInstallationObservation:
    candidate = PYDANTIC_AI_OLLAMA_V1
    executable = str(Path(sys.executable).resolve())
    return ProviderInstallationObservation.from_mapping({
        "schema_version": INSTALLATION_OBSERVATION_SCHEMA,
        "candidate_id": candidate.candidate_id,
        "candidate_version": candidate.candidate_version,
        "candidate_digest": candidate.digest(),
        "tool_surface_id": candidate.tool_surface_id,
        "host_platform": "fixture-os",
        "host_architecture": "fixture-arch",
        "python_version": "3.12.0",
        "python_executable": executable,
        "python_sha256": DIGEST_A,
        "harness_distribution": candidate.harness_distribution,
        "harness_version": "1.2.3",
        "harness_tree_digest": harness_tree_digest,
        "provider_kind": candidate.provider_kind,
        "provider_endpoint": "http://127.0.0.1:11434",
        "provider_executable": executable,
        "provider_executable_sha256": DIGEST_A,
        "provider_cli_version": "fixture-provider",
        "provider_api_version": "fixture-api",
        "model_name": model_name,
        "model_digest": model_digest,
        "model_metadata_digest": model_metadata_digest,
        "model_context_tokens": model_context_tokens,
        "model_capabilities": list(model_capabilities),
    })


def capability_qualification(
    *,
    model_name: str = "qwen2.5-coder:7b",
    model_digest: str = DIGEST_B,
    model_metadata_digest: str = DIGEST_C,
    installation_observation_digest: str | None = None,
    effective_context_tokens: int = 65_536,
    tool_evidence_digest: str = DIGEST_D,
    context_evidence_digest: str = DIGEST_E,
) -> ProviderCapabilityQualification:
    candidate = PYDANTIC_AI_OLLAMA_V1
    requirement = selected_runtime_requirement_v3()
    settings = CODING_WORKER_SETTINGS_V1
    observation_digest = installation_observation_digest or installation_observation(
        model_name=model_name,
        model_digest=model_digest,
        model_metadata_digest=model_metadata_digest,
    ).digest()
    return ProviderCapabilityQualification.from_mapping({
        "schema_version": CAPABILITY_QUALIFICATION_SCHEMA,
        "qualification_version": 2,
        "installation_observation_digest": observation_digest,
        "candidate_id": candidate.candidate_id,
        "candidate_version": candidate.candidate_version,
        "candidate_digest": candidate.digest(),
        "runtime_requirement_profile_id": requirement.profile_id,
        "runtime_requirement_digest": requirement.digest(),
        "provider_adapter_id": PROVIDER_ADAPTER_ID,
        "tool_surface_id": candidate.tool_surface_id,
        "provider_kind": candidate.provider_kind,
        "model_name": model_name,
        "model_digest": model_digest,
        "model_metadata_digest": model_metadata_digest,
        "runtime_settings_profile_id": settings.profile_id,
        "runtime_settings_digest": settings.digest(),
        "requested_context_tokens": settings.requested_context_tokens,
        "effective_context_tokens": effective_context_tokens,
        "tool_fixture_id": TOOL_CAPABILITY_FIXTURE_ID,
        "tool_evidence_digest": tool_evidence_digest,
        "context_fixture_id": CONTEXT_CAPABILITY_FIXTURE_ID,
        "context_evidence_digest": context_evidence_digest,
        "capability_qualified": True,
    })
