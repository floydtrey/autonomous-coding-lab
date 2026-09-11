import pytest
from worker_lab.errors import LabValidationError
from worker_lab.runtime_selection import (
    CODING_WORKER_V1, CODING_WORKER_V2, LEGACY_TERRA_V1,
    HOST_QUALIFIED_ONLY, PROVIDER_QUALIFIED,
    resolve_runtime_requirement, resolve_runtime_identity,
    selected_runtime_requirement, selected_runtime_requirement_v3,
)


def test_v2_identity_is_unchanged_and_still_selected_by_legacy_service_seam():
    requirement = selected_runtime_requirement()
    assert requirement is CODING_WORKER_V1
    assert requirement.profile_id == "coding-worker:v1"
    assert requirement.provider_selection == HOST_QUALIFIED_ONLY
    assert requirement.model_selector == PROVIDER_QUALIFIED
    assert requirement.reasoning_selector == PROVIDER_QUALIFIED
    assert requirement.invocation_fields()["model"] == PROVIDER_QUALIFIED


def test_v3_requirement_is_provider_neutral_and_separate():
    requirement = selected_runtime_requirement_v3()
    assert requirement is CODING_WORKER_V2
    assert requirement.profile_id == "coding-worker:v2"
    assert requirement.provider_binding_required is True
    assert set(requirement.to_dict()) == {
        "schema_version", "requirement_id", "requirement_version", "capability",
        "profile_id", "timeout_seconds", "provider_binding_required",
    }
    assert "model" not in requirement.to_dict()
    assert "reasoning" not in requirement.to_dict()
    assert resolve_runtime_identity(requirement.profile_id, requirement.digest()) is requirement


def test_v2_resolver_still_rejects_arbitrary_runtime():
    assert resolve_runtime_requirement(
        CODING_WORKER_V1.profile_id, PROVIDER_QUALIFIED, PROVIDER_QUALIFIED, 900,
    ) is CODING_WORKER_V1
    assert resolve_runtime_requirement(
        LEGACY_TERRA_V1.profile_id,
        LEGACY_TERRA_V1.model_selector,
        LEGACY_TERRA_V1.reasoning_selector,
        900,
    ) is LEGACY_TERRA_V1
    with pytest.raises(LabValidationError):
        resolve_runtime_requirement(
            CODING_WORKER_V1.profile_id, "other", PROVIDER_QUALIFIED, 900,
        )


def test_v3_digest_cannot_be_substituted():
    with pytest.raises(LabValidationError) as error:
        resolve_runtime_identity(CODING_WORKER_V2.profile_id, "sha256:" + "a" * 64)
    assert error.value.code == "INTEGRATION_RUNTIME_INVALID"
