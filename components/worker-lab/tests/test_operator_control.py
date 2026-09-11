import json

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.operator_control import inspect_installation, validate_controller_identity


def test_doctor_verifies_portable_identity_without_enabling_execution():
    manifest, report = inspect_installation()
    value = json.loads(report.to_json())
    assert value["schema_version"] == "worker-lab-installation-doctor:v2"
    assert value["installation_id"] == manifest["installation_id"]
    assert value["execution_authority"] == "DISABLED"
    assert value["execution_ready"] is False
    assert value["component_digests"]["worker-lab"] == manifest["components"]["worker-lab"]["digest"]
    assert value["component_digests"]["autonomous-worker-framework"] == manifest["components"]["autonomous-worker-framework"]["digest"]


def test_controller_identity_is_strict_and_provider_neutral():
    assert validate_controller_identity("trusted-controller") == "trusted-controller"
    for invalid in ("", "a", "bad controller", "../controller"):
        with pytest.raises(LabValidationError) as error:
            validate_controller_identity(invalid)
        assert error.value.code == "OPERATOR_CONTROLLER_INVALID"
