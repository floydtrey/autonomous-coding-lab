"""Focused M09C stop/reconcile coverage over the M09B sequential fixture."""
import json
import os

import pytest

from tests.test_m09b_sequential_controller import CONTROLLER, make_case, run
from worker_lab.errors import LabValidationError
from worker_lab.sequential_controller import _JobStopToken, _stop_path

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows controller locks")


def _reserve_a(case):
    created = case.service.create_job(
        "JOB-M09B",
        case.plan,
        approved_by=CONTROLLER,
        approved_plan_digest=case.plan.digest(),
    )
    return case.service.reserve_next_job_task(
        "JOB-M09B",
        controller_identity=CONTROLLER,
        expected_job_digest=created.digest(),
    )


def test_stop_request_is_exact_idempotent_and_visible(make_case):
    case = make_case()
    reserved = _reserve_a(case).to_dict()
    active = reserved["active"]

    status = case.service.stop_job(
        "JOB-M09B",
        controller_identity=CONTROLLER,
    ).to_dict()
    request = status["stop_request"]
    assert status["active"] == active
    assert request["job_id"] == "JOB-M09B"
    assert request["task_id"] == "A"
    assert request["reservation_id"] == active["reservation_id"]

    exact = _JobStopToken(
        case.records,
        job_id="JOB-M09B",
        task_id="A",
        reservation_id=active["reservation_id"],
        controller_identity=CONTROLLER,
    )
    other = _JobStopToken(
        case.records,
        job_id="JOB-M09B",
        task_id="A",
        reservation_id="sha256:" + "b" * 64,
        controller_identity=CONTROLLER,
    )
    assert exact.is_set() is True
    assert other.is_set() is False

    request_path = case.lab / "state" / _stop_path("JOB-M09B", active["reservation_id"])
    before = request_path.read_bytes()
    repeated = case.service.stop_job(
        "JOB-M09B",
        controller_identity=CONTROLLER,
    ).to_dict()
    assert repeated["stop_request"] == request
    assert request_path.read_bytes() == before


def test_reconcile_unstarted_reservation_blocks_without_replacement(make_case):
    case = make_case()
    _reserve_a(case)

    status = case.service.reconcile_job(
        "JOB-M09B",
        controller_identity=CONTROLLER,
    ).to_dict()

    assert status["status"] == "blocked"
    assert status["active"] is None
    assert status["objective_complete"] is False
    assert status["tasks"][0]["state"] == "blocked"
    assert status["tasks"][0]["blocker"]["code"] == "JOB_RECONCILED_UNSTARTED"
    assert status["tasks"][1]["state"] == "pending"
    assert status["tasks"][1]["attempt_count"] == 0
    assert case.launches == []
    assert not (case.lab / "state" / "attempts").exists()


def test_reconcile_finishes_accepted_promotion_without_rerunning_a(make_case, monkeypatch):
    case = make_case()
    original = case.service.promote_accepted_task

    def interrupted(*args, **kwargs):
        raise LabValidationError("SNAPSHOT_TEST_INTERRUPT", "simulated promotion interruption")

    monkeypatch.setattr(case.service, "promote_accepted_task", interrupted)
    with pytest.raises(LabValidationError) as error:
        run(case)
    assert error.value.code == "SNAPSHOT_TEST_INTERRUPT"
    assert len(case.launches) == 1

    before = case.service.job_status("JOB-M09B").to_dict()
    assert before["tasks"][0]["state"] == "accepted"
    assert before["tasks"][0]["artifact"] is None
    assert before["tasks"][1]["attempt_count"] == 0

    monkeypatch.setattr(case.service, "promote_accepted_task", original)
    reconciled = case.service.reconcile_job(
        "JOB-M09B",
        controller_identity=CONTROLLER,
        artifact_root=case.artifacts,
    ).to_dict()
    assert reconciled["status"] == "ready"
    assert reconciled["tasks"][0]["state"] == "accepted"
    assert reconciled["tasks"][0]["artifact"] is not None
    assert reconciled["tasks"][1]["attempt_count"] == 0
    assert len(case.launches) == 1

    finished = run(case).to_dict()
    assert finished["objective_complete"] is True
    assert len(case.launches) == 2
    assert case.b_saw_a is True


def test_reconcile_records_retained_accepted_run_then_waits_for_explicit_run(make_case, monkeypatch):
    case = make_case()
    original = case.service.record_job_task_result

    def interrupted(*args, **kwargs):
        raise LabValidationError("JOB_TEST_INTERRUPT", "simulated controller interruption after task-run")

    monkeypatch.setattr(case.service, "record_job_task_result", interrupted)
    with pytest.raises(LabValidationError) as error:
        run(case)
    assert error.value.code == "JOB_TEST_INTERRUPT"
    assert len(case.launches) == 1
    assert case.service.job_status("JOB-M09B").to_dict()["active"]["task_id"] == "A"
    assert case.records.list_paths("task-runs")

    monkeypatch.setattr(case.service, "record_job_task_result", original)
    reconciled = case.service.reconcile_job(
        "JOB-M09B",
        controller_identity=CONTROLLER,
        artifact_root=case.artifacts,
    ).to_dict()
    assert reconciled["status"] == "ready"
    assert reconciled["tasks"][0]["state"] == "accepted"
    assert reconciled["tasks"][0]["artifact"] is not None
    assert reconciled["tasks"][1]["attempt_count"] == 0
    assert len(case.launches) == 1

    finished = run(case).to_dict()
    assert finished["objective_complete"] is True
    assert len(case.launches) == 2


def test_stop_and_reconcile_cli_route_through_service(make_case, monkeypatch, capsys):
    from worker_lab import cli as cli_module

    case = make_case()
    _reserve_a(case)
    # Route CLI parsing/handlers into the same deterministic service/clock used
    # to create this fixture job, matching the M09B CLI seam.
    monkeypatch.setattr(cli_module, "_service", lambda args: case.service)

    assert cli_module.main([
        "--root", str(case.lab),
        "stop", "JOB-M09B",
        "--controller", CONTROLLER,
    ]) == 0
    stopped = json.loads(capsys.readouterr().out)
    assert stopped["active"]["task_id"] == "A"
    assert stopped["stop_request"]["reservation_id"] == stopped["active"]["reservation_id"]

    assert cli_module.main([
        "--root", str(case.lab),
        "reconcile", "JOB-M09B",
        "--controller", CONTROLLER,
    ]) == 0
    reconciled = json.loads(capsys.readouterr().out)
    assert reconciled["status"] == "blocked"
    assert reconciled["active"] is None
    assert reconciled["tasks"][1]["attempt_count"] == 0
