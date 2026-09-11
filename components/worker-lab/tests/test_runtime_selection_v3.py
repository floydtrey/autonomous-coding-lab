import pytest

from worker_lab.errors import LabValidationError
from worker_lab.runtime_selection import CODING_WORKER_V2, resolve_runtime_identity, selected_runtime_requirement_v3


def test_v3_requirement_is_provider_neutral_and_current():
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


def test_v3_digest_cannot_be_substituted():
    with pytest.raises(LabValidationError) as error:
        resolve_runtime_identity(CODING_WORKER_V2.profile_id, "sha256:" + "a" * 64)
    assert error.value.code == "INTEGRATION_RUNTIME_INVALID"
