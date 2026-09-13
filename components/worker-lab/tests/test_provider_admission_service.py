from __future__ import annotations

import json

import pytest

import worker_lab.cli as cli_module
from tests.provider_capability_fixture import installation_observation
from worker_lab.application_service import WorkerLabApplicationService
from worker_lab.cli import main
from worker_lab.errors import LabValidationError
from worker_lab.provider_qualification import (
    CAPABILITY_PROBE_EVIDENCE_SCHEMA,
    CONTEXT_CAPABILITY_CANARY_DIGEST,
    CONTEXT_CAPABILITY_FIXTURE_ID,
    TOOL_CAPABILITY_FIXTURE_ID,
    TOOL_CAPABILITY_PATH,
    TOOL_CAPABILITY_RESULT_DIGEST,
    CapabilityProbeEvidence,
)
from worker_lab.provider_records import (
    ProviderCapabilityQualificationStore,
    ProviderInstallationObservationStore,
)


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64


def passing_probe(request):
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
        context_prompt_tokens=request.requested_context_tokens,
        context_canary_digest=CONTEXT_CAPABILITY_CANARY_DIGEST,
        context_canary_observed=True,
        context_evidence_digest=DIGEST_B,
    )


def test_service_persists_observation_qualification_and_binding(tmp_path):
    observed = installation_observation()
    calls = []

    def observer(**kwargs):
        calls.append(kwargs)
        return observed

    service = WorkerLabApplicationService(
        tmp_path,
        provider_installation_observer=observer,
        provider_capability_probe_runner=passing_probe,
    )
    observation = service.observe_provider_installation(
        model=observed.model_name,
        base_url=observed.provider_endpoint,
        executable_name="ollama",
    )
    assert calls == [{
        "model": observed.model_name,
        "base_url": observed.provider_endpoint,
        "executable_name": "ollama",
    }]
    assert observation.identity == observed.digest()
    assert service.list_records("provider-installation-observations").items[0].identity == observed.digest()

    qualified = service.qualify_provider_capabilities(observed.digest())
    assert qualified.record["installation_observation_digest"] == observed.digest()
    assert qualified.record["capability_qualified"] is True
    assert service.show_record(
        "provider-capability-qualifications",
        qualified.identity,
    ).record == qualified.record

    binding = service.create_provider_binding("BINDING-QWEN-CODE-0001", qualified.identity)
    assert binding.record["model_name"] == observed.model_name
    assert binding.record["host_provider_qualification_digest"] == qualified.identity
    assert service.show_record("provider-bindings", binding.identity).record == binding.record


def test_admission_stores_are_content_addressed_and_reject_duplicates(tmp_path):
    observation_store = ProviderInstallationObservationStore(tmp_path)
    observed = observation_store.create(installation_observation())
    assert observation_store.read(observed.digest()) == observed
    with pytest.raises(LabValidationError) as error:
        observation_store.create(observed)
    assert error.value.code == "PROVIDER_RECORD_EXISTS"

    service = WorkerLabApplicationService(
        tmp_path.parent / "other",
        provider_capability_probe_runner=passing_probe,
    )
    with pytest.raises(LabValidationError) as error:
        service.qualify_provider_capabilities(DIGEST_A)
    assert error.value.code == "STORAGE_RECORD_MISSING"


def test_capability_qualification_has_no_default_runner(tmp_path):
    observed = ProviderInstallationObservationStore(tmp_path / "state").create(
        installation_observation()
    )
    service = WorkerLabApplicationService(tmp_path)
    with pytest.raises(LabValidationError) as error:
        service.qualify_provider_capabilities(observed.digest())
    assert error.value.code == "PROVIDER_CAPABILITY_PROBE_REQUIRED"
    assert not (tmp_path / "state" / "provider-capability-qualifications").exists()


def test_observation_and_binding_cli_use_explicit_operations(tmp_path, monkeypatch, capsys):
    observed = installation_observation()
    monkeypatch.setattr(cli_module, "inspect_provider_installation", lambda **_: observed)
    assert main([
        "--root", str(tmp_path),
        "observe-provider-installation",
        "--model", observed.model_name,
    ]) == 0
    observation_result = json.loads(capsys.readouterr().out)
    assert observation_result["identity"] == observed.digest()

    service = WorkerLabApplicationService(
        tmp_path,
        provider_capability_probe_runner=passing_probe,
    )
    qualified = service.qualify_provider_capabilities(observed.digest())
    assert main([
        "--root", str(tmp_path),
        "create-provider-binding",
        "BINDING-QWEN-CODE-0002",
        "--qualification-digest", qualified.identity,
    ]) == 0
    binding_result = json.loads(capsys.readouterr().out)
    assert binding_result["record"]["model_name"] == observed.model_name
    assert binding_result["identity"] == "BINDING-QWEN-CODE-0002"


def test_qualification_store_rejects_wrong_content_identity(tmp_path):
    observed = ProviderInstallationObservationStore(tmp_path).create(
        installation_observation()
    )
    service = WorkerLabApplicationService(
        tmp_path.parent / "lab",
        provider_capability_probe_runner=passing_probe,
    )
    ProviderInstallationObservationStore(
        service.data_root / "state"
    ).create(observed)
    qualified = service.qualify_provider_capabilities(observed.digest())
    path = (
        service.data_root
        / "state"
        / "provider-capability-qualifications"
        / f"{qualified.identity[7:]}.json"
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    value["model_digest"] = DIGEST_C
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(LabValidationError) as error:
        ProviderCapabilityQualificationStore(service.data_root / "state").read(
            qualified.identity
        )
    assert error.value.code == "PROVIDER_RECORD_MISMATCH"
