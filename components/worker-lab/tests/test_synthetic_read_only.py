import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from worker_lab.attempt_store import AttemptStore
from worker_lab.synthetic_read_only import (
    SYNTHETIC_PROFILE_ID,
    SYNTHETIC_TEST_ID,
    _create_attempt,
    _invocation,
    _make_template,
    _run_sealed_test,
    _write_authority,
)
from worker_lab.errors import LabValidationError
from worker_lab.integration import InvocationState
from worker_lab.models import AttemptState
from worker_lab.operator_control import ONE_TIME_CONFIRMATION
from worker_lab.test_catalog import ChangeFacts, TestRunner as CatalogRunner
from worker_lab.workspace import prepare_workspace
import worker_lab.synthetic_read_only as synthetic


def test_disabled_policy_rejects_before_creating_run_directory(tmp_path: Path) -> None:
    run_directory = tmp_path / "run"
    with pytest.raises(LabValidationError) as error:
        synthetic.run(
            run_directory,
            controller_identity="phase2-controller",
            authorization=ONE_TIME_CONFIRMATION,
        )
    assert error.value.code == "INTEGRATION_EXECUTION_DISABLED"
    assert not run_directory.exists()


def test_preflight_interruption_retains_authority_and_recovers_without_worker(
    tmp_path: Path, monkeypatch
) -> None:
    manifest, report = synthetic.inspect_installation()
    active_manifest = replace(
        manifest,
        execution_authority="ENABLED",
        participants={
            "autonomous-worker-framework": "ACTIVE",
            "local-model-bench": "ADVISORY",
            "worker-lab": "ACTIVE",
        },
    )
    active_report = replace(
        report,
        execution_authority="ENABLED",
        participant_states=active_manifest.participants,
        execution_ready=True,
    )
    monkeypatch.setattr(synthetic, "inspect_installation", lambda: (active_manifest, active_report))

    modes: list[str] = []

    def interrupted(*args, **kwargs):
        mode = args[2]
        modes.append(mode)
        if mode == "preflight":
            raise LabValidationError("SYNTHETIC_TEST_INTERRUPTION", "simulated preflight interruption")
        return b"unused"

    monkeypatch.setattr(synthetic, "_direct_adapter_runner", interrupted)
    run_directory = tmp_path / "run"
    with pytest.raises(LabValidationError) as error:
        synthetic.run(
            run_directory,
            controller_identity="phase2-controller",
            authorization=ONE_TIME_CONFIRMATION,
        )
    assert error.value.code == "SYNTHETIC_TEST_INTERRUPTION"
    assert modes == ["prepare", "preflight"]

    authorization = json.loads(
        (run_directory / "lab" / "state" / "operator" / "authorization.json").read_text(
            encoding="utf-8"
        )
    )
    assert authorization["controller_identity"] == "phase2-controller"
    invocation_id = authorization["invocation_id"]
    invocation = synthetic.InvocationStore(run_directory / "lab" / "state").read(invocation_id)
    assert invocation.state is InvocationState.AUTHORIZED

    recovered = json.loads(
        synthetic.recover(run_directory, controller_identity="phase2-controller")
    )
    assert recovered["invocation_state"] == "ABORTED"
    assert recovered["attempt_state"] == "ABORTED"
    attempt = synthetic.AttemptStore(run_directory / "lab" / "state").read(
        invocation.attempt_id
    )
    assert attempt.state is AttemptState.ABORTED
    assert not (run_directory / "workspaces" / attempt.attempt_id).exists()
    assert (run_directory / "lab" / "state" / "operator" / "recovery.json").is_file()


def test_synthetic_authority_seals_one_read_only_invocation() -> None:
    # The protected workspace primitive correctly rejects any child of the
    # Worker Lab repository, so this fixture deliberately uses the OS temp root.
    with TemporaryDirectory(prefix="worker-lab-synthetic-") as directory:
        root = Path(directory)
        template = root / "template"
        lab = root / "lab"
        workspace_root = root / "workspaces"
        workspace_root.mkdir()
        _make_template(template)
        records = _write_authority(lab, template)
        attempt = _create_attempt(lab, records)
        receipt = prepare_workspace(
            lab, attempt.attempt_id, template, workspace_root, occurred_at=attempt.updated_at
        )
        ready = AttemptStore(lab / "state").read(attempt.attempt_id)
        invocation, prompt = _invocation(
            lab, ready, records, receipt, workspace_root / attempt.attempt_id
        )
        assert invocation.sandbox_mode == "read-only"
        assert invocation.writable_paths == ()
        assert invocation.test_ids == (SYNTHETIC_TEST_ID,)
        assert prompt
        definition = records[-1].tests[0]
        assert definition.runner is CatalogRunner.COMMAND
        assert _run_sealed_test(definition, workspace_root / attempt.attempt_id) == 0
        assert records[-1].select(ChangeFacts(()), profile_ids=(SYNTHETIC_PROFILE_ID,)).test_ids == (
            SYNTHETIC_TEST_ID,
        )


def test_preexecution_runner_retains_only_a_stable_adapter_failure_code(monkeypatch) -> None:
    class Process:
        returncode = 1
        stdout = b'{"failure_code":"CHATGPT_AUTH_REQUIRED","retryable":false}'
        stderr = b"sensitive diagnostic content"

    monkeypatch.setattr(synthetic.subprocess, "run", lambda *args, **kwargs: Process())
    monkeypatch.setattr(
        synthetic, "call_adapter", lambda *args, runner, **kwargs: runner(("adapter",), b"request")
    )
    with pytest.raises(LabValidationError) as error:
        synthetic._direct_adapter_runner(
            None, SimpleNamespace(framework_root=Path(".")), None, None, None, None
        )
    assert error.value.code == "CHATGPT_AUTH_REQUIRED"
