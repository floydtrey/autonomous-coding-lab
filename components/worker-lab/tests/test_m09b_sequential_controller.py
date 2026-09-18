"""M09B sequential controller integration over the existing M09A task path."""
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

from tests.test_application_service_v3 import CONTROLLER, _success_custody
from tests.test_job_admission import setup_job
from tests.test_pi_dispatch import AWF, binding
from tests.test_validation_deadline import Clock, Process
from worker_lab import pi_binding, pi_dispatch, protected_validation
from worker_lab.application_service import WorkerLabApplicationService
from worker_lab.canonical import canonical_digest, canonical_json
from worker_lab.errors import LabValidationError
from worker_lab.integration_v3 import InvocationRecordV3
from worker_lab.job_admission import JobAuthorityProfile
from worker_lab.job_plan import JobPlan
from worker_lab.pi_protocol import encode_frame
from worker_lab.pi_supervision import _Record, set_pi_activation
from worker_lab.pi_worker import intended_pi_worker
from worker_lab.process_custody import ProcessCustodyStore
from worker_lab.provider_binding import ProviderBindingStore
from worker_lab.storage import AtomicRecordStore

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows controller locks")
cli_module = importlib.import_module("worker_lab.cli")


@pytest.fixture
def make_case(tmp_path, monkeypatch):
    def prepare():
        timer = Clock()
        lab, target, original_plan, _ = setup_job(tmp_path, complete_plan=True)
        lab = lab.resolve()
        target = target.resolve()
        checker = (tmp_path / "checks" / "sequential.py").resolve()
        checker.parent.mkdir()
        checker.write_text(
            "from pathlib import Path\n"
            "import sys\n"
            "root = Path(sys.argv[1])\n"
            "task = sys.argv[2]\n"
            "model_ok = (root / 'record_ledger/models.py').read_bytes() == b'VALUE = 2\\n'\n"
            "docs_ok = task == 'A' or b'Record format: VALUE = 2' in (root / 'README.md').read_bytes()\n"
            "raise SystemExit(0 if model_ok and docs_ok else 7)\n",
            encoding="utf-8",
        )

        plan_value = original_plan.to_dict()
        authorities = AtomicRecordStore(lab / "job-authorities")
        for task in plan_value["tasks"]:
            ref = task["authority_ref"]
            path = f"{ref['profile_id']}/v{ref['version']}.json"
            value = authorities.read(path, lambda item: item)
            for test in value["catalog"]["tests"]:
                test["command"] = [
                    str(Path(sys.executable).resolve()),
                    "-I",
                    "-B",
                    str(checker),
                    "{candidate}",
                    task["task_id"],
                ]
            profile = JobAuthorityProfile.from_mapping(value)
            authorities.write(path, profile)
            ref["digest"] = profile.digest()
        plan = JobPlan.from_mapping(plan_value)

        monkeypatch.setattr(pi_dispatch, "time", timer)
        monkeypatch.setattr(protected_validation, "time", timer)
        monkeypatch.setattr(
            protected_validation,
            "process_creation_time_for_pid",
            lambda pid: 1,
        )
        service = WorkerLabApplicationService(lab, clock=timer.timestamp)
        config = intended_pi_worker()
        config_path = (tmp_path / "protected-pi-worker.json").resolve()
        config_path.write_text(canonical_json(config), encoding="utf-8")
        monkeypatch.setattr(pi_binding, "CONFIG_PATH", config_path)
        bound = binding(config)
        ProviderBindingStore(lab / "state").create(bound)

        node = shutil.which("node")
        assert node, "Use the previously verified Node executable on PATH for this batch"
        records = AtomicRecordStore(lab / "state")
        records.write(
            "operator/pi-host.json",
            _Record(
                dict(
                    schema_version="acl-pi-host:v1",
                    node=str(Path(node).resolve()),
                    python=str(Path(sys.executable).resolve()),
                    framework_root=str(AWF.resolve()),
                    pi_installation=str((tmp_path / "unused-sdk").resolve()),
                    agent_dir=str((lab / "state" / "agent").resolve()),
                )
            ),
        )
        set_pi_activation(
            records.root,
            enabled=True,
            controller_identity=CONTROLLER,
            worker_digest=canonical_digest(config),
        )
        workspaces = (tmp_path / "workspaces").resolve()
        artifacts = (tmp_path / "artifacts").resolve()
        workspaces.mkdir()
        artifacts.mkdir()
        return SimpleNamespace(
            timer=timer,
            lab=lab,
            target=target,
            service=service,
            records=records,
            plan=plan,
            checker=checker,
            binding=bound,
            config=config,
            workspaces=workspaces,
            artifacts=artifacts,
            launches=[],
            b_saw_a=False,
        )

    return prepare


def worker_factory(case, *, fail_a_validation=False):
    """Use the real AWF/Pi seam while replacing only provider process output."""
    def factory(**options):
        state = options["state_root"]
        workspace = options["workspace_root"]
        records = AtomicRecordStore(state)

        def launch(argv, raw, deadline):
            request = json.loads(raw)
            invocation = InvocationRecordV3.from_mapping(request["invocation"])
            case.launches.append(deepcopy(request))
            prefix = f"process-logs/{invocation.invocation_id}"
            records.write_bytes(prefix + "/request.jsonl", raw)
            writable = tuple(invocation.writable_paths)
            if writable == ("record_ledger/models.py",):
                (workspace / "record_ledger/models.py").write_bytes(
                    b"VALUE = 3\n" if fail_a_validation else b"VALUE = 2\n"
                )
            elif writable == ("README.md",):
                case.b_saw_a = (
                    workspace / "record_ledger/models.py"
                ).read_bytes() == b"VALUE = 2\n"
                assert case.b_saw_a, "B did not receive A's accepted snapshot"
                (workspace / "README.md").write_bytes(b"Record format: VALUE = 2\n")
            else:
                raise AssertionError(f"unexpected writable paths: {writable!r}")
            case.timer.elapsed_ms += 1000
            _success_custody(invocation, workspace, ProcessCustodyStore(state))
            result = dict(
                schema_version="acl-pi-result:v2",
                request_digest=canonical_digest(request),
                status="completed",
                stop_reason="stop",
                summary="Fixture completed the exact authorized file.",
                remaining_work=None,
                session_reference=f"fixture-session:{invocation.attempt_id}",
                usage=dict(input_tokens=101, output_tokens=37, requests=4, tool_calls=3),
                candidate=None,
            )
            event = dict(
                schema_version="acl-pi-event:v1",
                request_digest=canonical_digest(request),
                sequence=0,
                event="settled",
                detail="Deterministic provider fixture settled.",
            )
            output = encode_frame(event) + b"\n" + encode_frame(result) + b"\n"
            records.write_bytes(prefix + "/stdout.jsonl", output)
            return output

        return pi_dispatch.make_pi_dispatch_runner(
            binding_store=ProviderBindingStore(state),
            workspace_root=workspace,
            framework_root=options["framework_root"],
            node=options["node"],
            python=options["python"],
            pi_installation=options["pi_installation"],
            agent_dir=options["agent_dir"],
            launcher=launch,
            outcome_sink=options["outcome_sink"],
            absolute_deadline_unix_ms=options["absolute_deadline_unix_ms"],
        )

    return factory


class CheckingProcess(Process):
    def __init__(self, timer, *, exit_code):
        super().__init__(timer, poll_ms=100)
        self.exit_code = exit_code

    def poll(self):
        if self.killed:
            return -1
        if not self.polled:
            self.polled = True
            self.timer.elapsed_ms += self.poll_ms
        return self.exit_code


def process_factory(case):
    def factory(argv, **kwargs):
        root = Path(argv[-2])
        task = argv[-1]
        model_ok = (root / "record_ledger/models.py").read_bytes() == b"VALUE = 2\n"
        docs_ok = task == "A" or b"Record format: VALUE = 2" in (root / "README.md").read_bytes()
        return CheckingProcess(case.timer, exit_code=0 if model_ok and docs_ok else 7)
    return factory


def run(case, *, fail_a_validation=False):
    return case.service.run_job(
        "JOB-M09B",
        case.plan,
        approved_plan_digest=case.plan.digest(),
        controller_identity=CONTROLLER,
        target_repository=case.target,
        workspace_root=case.workspaces,
        artifact_root=case.artifacts,
        provider_binding_id=case.binding.binding_id,
        protected_files=(case.checker,),
        acknowledge_unsandboxed=True,
        runner_factory=worker_factory(case, fail_a_validation=fail_a_validation),
        process_factory=process_factory(case),
        candidate_archive_limit_bytes=0,
    )


def test_two_tasks_run_in_order_and_status_is_read_only(make_case, capsys):
    case = make_case()
    report = run(case)
    value = report.to_dict()
    assert value["status"] == "complete"
    assert value["objective_complete"] is True
    assert value["runnable"] is False
    assert [task["state"] for task in value["tasks"]] == ["accepted", "accepted"]
    assert all(task["artifact"] is not None for task in value["tasks"])
    assert len(case.launches) == 2
    assert case.b_saw_a is True

    a_snapshot = case.records.read(value["tasks"][0]["artifact"]["path"], lambda item: item)
    assert case.launches[1]["invocation"]["source_state"]["base_commit"] == a_snapshot["snapshot_commit"]
    assert case.launches[0]["deadline_unix_ms"] != case.launches[1]["deadline_unix_ms"]

    job_path = case.lab / "state" / "jobs" / "JOB-M09B.json"
    before = job_path.read_bytes()
    service_status = case.service.job_status("JOB-M09B")
    assert service_status.to_dict() == value
    assert job_path.read_bytes() == before

    assert cli_module.main(["--root", str(case.lab), "status", "JOB-M09B"]) == 0
    cli_status = json.loads(capsys.readouterr().out)
    assert cli_status == value
    assert job_path.read_bytes() == before


def test_run_cli_uses_the_same_sequential_service_path(make_case, tmp_path, monkeypatch, capsys):
    case = make_case()
    plan_file = (tmp_path / "plan.json").resolve()
    plan_file.write_text(case.plan.to_json(), encoding="utf-8")

    class CliService:
        def run_job(self, *args, **kwargs):
            kwargs["runner_factory"] = worker_factory(case)
            kwargs["process_factory"] = process_factory(case)
            return case.service.run_job(*args, **kwargs)

    monkeypatch.setattr(cli_module, "_service", lambda args: CliService())
    result = cli_module.main([
        "run",
        str(plan_file),
        "--job-id", "JOB-M09B-CLI",
        "--approved-plan-digest", case.plan.digest(),
        "--controller", CONTROLLER,
        "--target-repository", str(case.target),
        "--workspace-root", str(case.workspaces),
        "--artifact-root", str(case.artifacts),
        "--provider-binding-id", case.binding.binding_id,
        "--protected-file", str(case.checker),
        "--acknowledge-unsandboxed-host-code-execution",
        "--candidate-archive-limit-bytes", "0",
    ])
    assert result == 0
    value = json.loads(capsys.readouterr().out)
    assert value["job_id"] == "JOB-M09B-CLI"
    assert value["status"] == "complete"
    assert value["objective_complete"] is True
    assert len(case.launches) == 2
    assert case.b_saw_a is True


def test_status_reports_drifted_evidence_without_mutating_job(make_case):
    case = make_case()
    assert run(case).to_dict()["objective_complete"] is True
    job_path = case.lab / "state" / "jobs" / "JOB-M09B.json"
    before_job = job_path.read_bytes()
    status = case.service.job_status("JOB-M09B").to_dict()
    acceptance_path = case.lab / "state" / status["tasks"][0]["acceptance"]["path"]
    changed = json.loads(acceptance_path.read_text(encoding="utf-8"))
    changed["candidate"]["content_digest"] = "sha256:" + "b" * 64
    acceptance_path.write_text(canonical_json(changed), encoding="utf-8")

    drifted = case.service.job_status("JOB-M09B").to_dict()
    assert drifted["status"] == "complete"
    assert drifted["objective_complete"] is False
    assert drifted["runnable"] is False
    assert any(item["task_id"] == "A" for item in drifted["evidence_gaps"])
    assert job_path.read_bytes() == before_job


def test_failed_a_blocks_b_without_promotion_or_second_worker(make_case):
    case = make_case()
    value = run(case, fail_a_validation=True).to_dict()
    assert value["status"] == "blocked"
    assert value["objective_complete"] is False
    assert value["tasks"][0]["state"] == "failed"
    assert value["tasks"][0]["artifact"] is None
    assert value["tasks"][1]["state"] == "pending"
    assert value["tasks"][1]["attempt_count"] == 0
    assert len(case.launches) == 1
    assert list(case.artifacts.iterdir()) == []


def test_interrupted_promotion_never_reserves_b_or_repeats_promotion(make_case, monkeypatch):
    case = make_case()
    original = case.service.promote_accepted_task
    calls = []

    def interrupted(*args, **kwargs):
        calls.append((args, kwargs))
        raise LabValidationError("SNAPSHOT_TEST_INTERRUPT", "simulated promotion interruption")

    monkeypatch.setattr(case.service, "promote_accepted_task", interrupted)
    with pytest.raises(LabValidationError) as first:
        run(case)
    assert first.value.code == "SNAPSHOT_TEST_INTERRUPT"
    assert len(calls) == 1

    status = case.service.job_status("JOB-M09B").to_dict()
    assert status["status"] == "ready"
    assert status["tasks"][0]["state"] == "accepted"
    assert status["tasks"][0]["artifact"] is None
    assert status["tasks"][1]["attempt_count"] == 0
    assert status["evidence_gaps"][0]["code"] == "JOB_INPUT_PROMOTION_REQUIRED"

    monkeypatch.setattr(case.service, "promote_accepted_task", original)
    with pytest.raises(LabValidationError) as second:
        run(case)
    assert second.value.code == "JOB_RECONCILIATION_REQUIRED"
    assert case.service.job_status("JOB-M09B").to_dict()["tasks"][1]["attempt_count"] == 0
    assert len(case.launches) == 1


def test_existing_active_reservation_is_not_replaced(make_case):
    case = make_case()
    created = case.service.create_job(
        "JOB-M09B",
        case.plan,
        approved_by=CONTROLLER,
        approved_plan_digest=case.plan.digest(),
    )
    case.service.reserve_next_job_task(
        "JOB-M09B",
        controller_identity=CONTROLLER,
        expected_job_digest=created.digest(),
    )
    before = case.service.read_job("JOB-M09B").to_json()
    with pytest.raises(LabValidationError) as error:
        run(case)
    assert error.value.code == "JOB_RECONCILIATION_REQUIRED"
    assert case.service.read_job("JOB-M09B").to_json() == before
    assert not (case.lab / "state" / "attempts").exists()
