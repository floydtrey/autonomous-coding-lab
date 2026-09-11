import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.provider_binding import (
    CODING_WORKER_SETTINGS_V1,
    PROVIDER_ADAPTER_ID,
    ProviderBinding,
    ProviderBindingStore,
    create_provider_binding,
    validate_binding_qualification,
)
from worker_lab.provider_qualification import (
    QUALIFICATION_SCHEMA,
    PYDANTIC_AI_OLLAMA_V1,
    HostProviderQualification,
)
from worker_lab.runtime_selection import selected_runtime_requirement_v3


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64


def qualification(*, model_digest: str = DIGEST_A, harness_tree_digest: str = DIGEST_C):
    candidate = PYDANTIC_AI_OLLAMA_V1
    executable = str(Path(sys.executable).resolve())
    return HostProviderQualification.from_mapping({
        "schema_version": QUALIFICATION_SCHEMA,
        "candidate_id": candidate.candidate_id,
        "candidate_version": candidate.candidate_version,
        "candidate_digest": candidate.digest(),
        "runtime_requirement_profile_id": candidate.runtime_requirement_profile_id,
        "runtime_requirement_digest": candidate.runtime_requirement_digest,
        "tool_surface_id": candidate.tool_surface_id,
        "host_platform": "fixture-os",
        "host_architecture": "fixture-arch",
        "python_version": "3.12.0",
        "python_executable": executable,
        "python_sha256": DIGEST_B,
        "harness_distribution": candidate.harness_distribution,
        "harness_version": "1.2.3",
        "harness_tree_digest": harness_tree_digest,
        "provider_kind": candidate.provider_kind,
        "provider_endpoint": "http://127.0.0.1:11434",
        "provider_executable": executable,
        "provider_executable_sha256": DIGEST_B,
        "provider_cli_version": "fixture-provider",
        "provider_api_version": "fixture-api",
        "model_name": "qwen2.5-coder:7b",
        "model_digest": model_digest,
        "model_metadata_digest": DIGEST_C,
        "model_context_tokens": 65_536,
        "model_capabilities": ["completion", "tools"],
        "execution_authority": "DISABLED",
        "provider_runtime_qualified": True,
        "execution_ready": False,
    })


def test_binding_seals_v3_requirement_exact_qualification_and_settings():
    observed = qualification()
    binding = create_provider_binding("BINDING-0001", observed)
    requirement = selected_runtime_requirement_v3()
    assert binding.runtime_requirement_profile_id == requirement.profile_id
    assert binding.runtime_requirement_digest == requirement.digest()
    assert binding.host_provider_qualification_digest == observed.digest()
    assert binding.qualification_candidate_digest == PYDANTIC_AI_OLLAMA_V1.digest()
    assert binding.provider_adapter_id == PROVIDER_ADAPTER_ID
    assert binding.model_digest == observed.model_digest
    assert binding.runtime_settings_digest == CODING_WORKER_SETTINGS_V1.digest()
    assert CODING_WORKER_SETTINGS_V1.requested_context_tokens == 32_768


def test_unprotected_settings_rejected():
    with pytest.raises(LabValidationError) as error:
        create_provider_binding(
            "BINDING-0001",
            qualification(),
            settings=replace(CODING_WORKER_SETTINGS_V1, request_limit=13),
        )
    assert error.value.code == "PROVIDER_BINDING_SETTINGS_INVALID"


def test_store_unknown_tampered_and_stale_fail_closed(tmp_path):
    binding = create_provider_binding("BINDING-0001", qualification())
    store = ProviderBindingStore(tmp_path)
    with pytest.raises(LabValidationError) as error:
        store.require(binding.binding_id, binding.digest())
    assert error.value.code == "STORAGE_RECORD_MISSING"
    store.create(binding)
    with pytest.raises(LabValidationError) as error:
        store.require(binding.binding_id, DIGEST_A)
    assert error.value.code == "PROVIDER_BINDING_MISMATCH"
    stale = replace(binding, runtime_settings_digest=DIGEST_A)
    path = tmp_path / "provider-bindings" / f"{binding.binding_id}.json"
    path.write_text(json.dumps(stale.to_dict()), encoding="utf-8")
    with pytest.raises(LabValidationError) as error:
        store.read(binding.binding_id)
    assert error.value.code == "STORAGE_RECORD_INVALID"
    assert "PROVIDER_BINDING_STALE" in error.value.summary


def test_model_or_harness_qualification_substitution_is_rejected():
    binding = create_provider_binding("BINDING-0001", qualification())
    for substituted in (
        qualification(model_digest=DIGEST_B),
        qualification(harness_tree_digest=DIGEST_B),
    ):
        with pytest.raises(LabValidationError) as error:
            validate_binding_qualification(binding, substituted)
        assert error.value.code == "PROVIDER_BINDING_QUALIFICATION_MISMATCH"


def test_unknown_binding_fields_rejected():
    binding = create_provider_binding("BINDING-0001", qualification())
    value = binding.to_dict()
    value["unexpected"] = True
    with pytest.raises(LabValidationError) as error:
        ProviderBinding.from_mapping(value)
    assert error.value.code == "PROVIDER_BINDING_FIELDS_INVALID"
