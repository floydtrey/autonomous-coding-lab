import json

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.operator_control import inspect_source_identity, validate_controller_identity


def test_doctor_verifies_portable_source_without_claiming_activation_or_host_qualification():
    manifest, report = inspect_source_identity()
    value = json.loads(report.to_json())
    assert value["schema_version"] == "worker-lab-source-doctor:v3"
    assert value["source_identity_id"] == manifest["source_identity_id"]
    assert value["separation_policy"] == manifest["separation_policy"]
    assert value["component_digests"]["worker-lab"] == manifest["components"]["worker-lab"]["digest"]
    assert value["component_digests"]["autonomous-worker-framework"] == manifest["components"]["autonomous-worker-framework"]["digest"]
    encoded = json.dumps(value, sort_keys=True)
    assert "execution_authority" not in encoded
    assert "participant_states" not in encoded


def test_controller_identity_is_strict_and_provider_neutral():
    assert validate_controller_identity("trusted-controller") == "trusted-controller"
    for invalid in ("", "a", "bad controller", "../controller"):
        with pytest.raises(LabValidationError) as error:
            validate_controller_identity(invalid)
        assert error.value.code == "OPERATOR_CONTROLLER_INVALID"
