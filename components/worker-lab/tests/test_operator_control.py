import json
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.operator_control import (
    ONE_TIME_CONFIRMATION,
    inspect_installation,
    persist_operator_evidence,
    read_operator_evidence,
    require_one_time_confirmation,
    run_directory_digest,
    validate_controller_identity,
    validate_new_run_directory,
)


DIGEST = "sha256:" + "a" * 64


def test_doctor_verifies_installed_identity_without_enabling_execution() -> None:
    manifest, report = inspect_installation()
    value = json.loads(report.to_json())
    assert value["schema_version"] == "worker-lab-installation-doctor:v1"
    assert value["installation_id"] == manifest.installation_id
    assert value["execution_authority"] == "DISABLED"
    assert value["execution_ready"] is False
    assert value["component_digests"]["worker-lab"] == manifest.components["worker-lab"].installation_digest
    assert value["component_digests"]["autonomous-worker-framework"] == manifest.components["autonomous-worker-framework"].installation_digest


def test_controller_confirmation_and_run_directory_fail_closed(tmp_path: Path) -> None:
    manifest, _ = inspect_installation()
    assert validate_controller_identity("phase2-controller") == "phase2-controller"
    require_one_time_confirmation(ONE_TIME_CONFIRMATION)
    for invalid in ("", "a", "bad controller", "../controller"):
        with pytest.raises(LabValidationError):
            validate_controller_identity(invalid)
    with pytest.raises(LabValidationError) as error:
        require_one_time_confirmation("yes")
    assert error.value.code == "OPERATOR_AUTHORIZATION_REQUIRED"
    run_directory = tmp_path / "phase2-run"
    assert validate_new_run_directory(run_directory, manifest.installation_root) == run_directory
    run_directory.mkdir()
    with pytest.raises(LabValidationError) as error:
        validate_new_run_directory(run_directory, manifest.installation_root)
    assert error.value.code == "OPERATOR_RUN_DIRECTORY_INVALID"
    with pytest.raises(LabValidationError):
        validate_new_run_directory(Path("relative-run"), manifest.installation_root)


def test_operator_evidence_round_trip_binds_controller_run_and_invocation(tmp_path: Path) -> None:
    manifest, report = inspect_installation()
    run_directory = tmp_path / "phase2-run"
    run_directory.mkdir()
    state_root = run_directory / "state"
    activation, authorization = persist_operator_evidence(
        state_root,
        manifest=manifest,
        report=report,
        run_directory=run_directory,
        controller_identity="phase2-controller",
        invocation_id="INVOCATION-000001",
        invocation_digest=DIGEST,
        observed_at="2026-08-31T12:00:00Z",
    )
    loaded_activation, loaded_authorization = read_operator_evidence(state_root)
    assert loaded_activation == activation
    assert loaded_authorization == authorization
    assert loaded_authorization.controller_identity == "phase2-controller"
    assert loaded_authorization.run_directory_digest == run_directory_digest(run_directory)
    assert loaded_authorization.invocation_digest == DIGEST
    assert loaded_authorization.activation_evidence_digest == loaded_activation.digest()
