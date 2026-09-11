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
from worker_lab.provider_qualification import PYDANTIC_AI_OLLAMA_V1
from worker_lab.runtime_selection import selected_runtime_requirement_v3


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64


def qualification(*, model_digest: str = DIGEST_A, harness_tree_digest: str = DIGEST_C):
    from tests.provider_capability_fixture import capability_qualification

    return capability_qualification(
        model_digest=model_digest,
        installation_observation_digest=harness_tree_digest,
    )


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


def test_metadata_only_installation_observation_cannot_create_binding():
    from tests.provider_capability_fixture import installation_observation

    with pytest.raises(LabValidationError) as error:
        create_provider_binding("BINDING-0002", installation_observation())
    assert error.value.code == "PROVIDER_BINDING_QUALIFICATION_INVALID"
