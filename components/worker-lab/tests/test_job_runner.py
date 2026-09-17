"""M07 durable coordination tests; no worker/model/validator execution."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from worker_lab import job_runner as jobs
from worker_lab.canonical import canonical_digest, canonical_json
from worker_lab.errors import LabValidationError
from worker_lab.integration_v3 import InvocationState
from worker_lab.job_admission import JobAuthorityProfile
from worker_lab.job_plan import JobPlan
from worker_lab.models import AttemptState
from worker_lab.storage import AtomicRecordStore

FIXTURES = Path(__file__).parent / 'fixtures'
CONTROLLER = 'controller-1'
START = '2026-09-17T12:00:00Z'
WITHIN = '2026-09-17T12:00:30Z'
LATER = '2026-09-17T12:02:00Z'
DIGEST = 'sha256:' + 'a' * 64


def fixture(tmp_path, plan=None, job_id='JOB-001'):
    lab = tmp_path.resolve() / 'lab'
    value = plan.to_dict() if plan else json.loads((FIXTURES / 'two-task-job-plan.json').read_text(encoding='utf-8'))
    for task in value['tasks']:
        profile_id = task['authority_ref']['profile_id']
        profile_value = json.loads((FIXTURES / f'{profile_id}.json').read_text(encoding='utf-8'))
        # Earlier admission fixtures only exercised A. Give this copied B
        # authority an explicit trusted mapping for its authorized README.
        if profile_id == 'record-docs-authority':
            next(test for test in profile_value['catalog']['tests'] if test['test_id'] == 'T004')['path_prefixes'] = ['README.md']
        profile = JobAuthorityProfile.from_mapping(profile_value)
        task['authority_ref']['digest'] = profile.digest()
        AtomicRecordStore(lab / 'job-authorities').write(f'{profile_id}/v1.json', profile)
    plan = JobPlan.from_mapping(value)
    record = jobs.create_job(lab, job_id=job_id, plan=plan, approved_plan_digest=plan.digest(),
        controller_identity=CONTROLLER, clock=lambda: START)
    return lab, plan, record


def reserve(lab, record, clock=START):
    return jobs.reserve_next_task(lab, record.to_dict()['job_id'], controller_identity=CONTROLLER,
        expected_job_digest=record.digest(), clock=lambda: clock)


def test_application_service_registers_reads_and_reserves_without_execution(tmp_path):
    from worker_lab.application_service import WorkerLabApplicationService
    lab, plan, _ = fixture(tmp_path)
    service = WorkerLabApplicationService(lab, clock=lambda: START)
    # The job schema permits a one-character ID; public wrappers must preserve it.
    created = service.create_job('J', plan, approved_by=CONTROLLER, approved_plan_digest=plan.digest())
    assert service.read_job('J') == created
    selected = service.reserve_next_job_task('J', controller_identity=CONTROLLER,
        expected_job_digest=created.digest())
    assert service.read_job('J') == selected
    assert selected.to_dict()['active']['task_id'] == 'A'
    assert selected.to_dict()['tasks']['A']['attempts'][0]['attempt_id'] is None
    assert not (lab / 'state/attempts').exists()
    assert not (lab / 'state/invocations').exists()


def test_registration_pins_plan_authority_and_is_restart_idempotent(tmp_path):
    lab, plan, record = fixture(tmp_path)
    assert not (lab / 'state/attempts').exists()
    replay = jobs.create_job(lab, job_id='JOB-001', plan=plan, approved_plan_digest=plan.digest(),
        controller_identity=CONTROLLER, clock=lambda: LATER)
    assert replay == record == jobs.read_job(lab, 'JOB-001')
    changed = plan.to_dict(); changed['revision'] = 2
    changed = JobPlan.from_mapping(changed)
    with pytest.raises(LabValidationError, match='another approved plan'):
        jobs.create_job(lab, job_id='JOB-001', plan=changed, approved_plan_digest=changed.digest(),
            controller_identity=CONTROLLER)


def test_plan_or_profile_substitution_never_reserves_work(tmp_path):
    lab, plan, _ = fixture(tmp_path)
    with pytest.raises(LabValidationError):
        jobs.create_job(lab, job_id='JOB-002', plan=plan, approved_plan_digest='sha256:' + '0' * 64,
            controller_identity=CONTROLLER)
    path = lab / 'job-authorities/record-model-authority/v1.json'
    profile = json.loads(path.read_text(encoding='utf-8')); profile['writable_paths'] = ['README.md']
    path.write_text(json.dumps(profile), encoding='utf-8')
    with pytest.raises(LabValidationError):
        jobs.create_job(lab, job_id='JOB-002', plan=plan, approved_plan_digest=plan.digest(), controller_identity=CONTROLLER)
    assert not (lab / 'state/jobs/JOB-002.json').exists()


def test_one_durable_reservation_survives_restart_and_rejects_competitors(tmp_path):
    lab, plan, record = fixture(tmp_path)
    selected = reserve(lab, record)
    assert selected.to_dict()['active']['task_id'] == 'A'
    assert selected.to_dict()['tasks']['B']['state'] == 'pending'
    assert jobs.read_job(lab, 'JOB-001') == selected
    with pytest.raises(LabValidationError) as stale:
        reserve(lab, record)
    assert stale.value.code == 'JOB_STATE_CHANGED'
    with pytest.raises(LabValidationError) as replacement:
        reserve(lab, selected)
    assert replacement.value.code == 'JOB_TASK_RESERVED'
    second = jobs.create_job(lab, job_id='JOB-002', plan=plan, approved_plan_digest=plan.digest(),
        controller_identity=CONTROLLER, clock=lambda: START)
    with pytest.raises(LabValidationError) as competitor:
        reserve(lab, second)
    assert competitor.value.code == 'JOB_CONTROLLER_BUSY'
    assert jobs.read_job(lab, 'JOB-002') == second


def test_controller_and_native_lock_exclude_competing_selection(tmp_path):
    lab, _, record = fixture(tmp_path)
    with pytest.raises(LabValidationError) as wrong:
        jobs.reserve_next_task(lab, 'JOB-001', controller_identity='controller-other',
            expected_job_digest=record.digest(), clock=lambda: START)
    assert wrong.value.code == 'JOB_CONTROLLER_MISMATCH'
    with jobs._exclusive_controller(lab / 'state', 'job-controller.lock'):
        with pytest.raises(LabValidationError) as locked:
            reserve(lab, record)
    assert locked.value.code == 'PI_WORKER_ACTIVE'
    assert jobs.read_job(lab, 'JOB-001') == record


def fake_binding(monkeypatch, *, task_id='A'):
    # Only the already-admitted preparation seam is injected here. Admission's
    # actual protected-profile validation runs separately in existing tests.
    attempt = SimpleNamespace(attempt_id=f'JOBTASK-{task_id}', state=AttemptState.READY)
    invocation = SimpleNamespace(invocation_id=f'INVOCATION-{task_id}', attempt_id=attempt.attempt_id,
        state=InvocationState.PREPARED, identity_digest=lambda: DIGEST)
    monkeypatch.setattr(jobs, '_binding', lambda *args: (attempt, invocation))
    return attempt, invocation


def bind(lab, selected, invocation, clock=START):
    return jobs.bind_job_attempt(lab, selected.to_dict()['job_id'], controller_identity=CONTROLLER,
        reservation_id=selected.to_dict()['active']['reservation_id'], attempt_id=invocation.attempt_id,
        invocation_id=invocation.invocation_id, expected_invocation_digest=invocation.identity_digest(), clock=lambda: clock)


def test_attempt_binding_is_single_and_authorization_has_exact_budget(tmp_path, monkeypatch):
    lab, _, record = fixture(tmp_path)
    selected = reserve(lab, record)
    _, invocation = fake_binding(monkeypatch)
    bound = bind(lab, selected, invocation)
    assert bind(lab, bound, invocation) == bound
    with jobs.job_authorization_gate(lab, invocation, controller_identity=CONTROLLER, clock=lambda: WITHIN) as allowance:
        assert allowance['remaining_milliseconds'] == 30000
        assert allowance['deadline_unix_ms'] == jobs._millis('2026-09-17T12:01:00Z')
        with pytest.raises(LabValidationError):
            reserve(lab, bound)
    with pytest.raises(LabValidationError) as expired:
        with jobs.job_authorization_gate(lab, invocation, controller_identity=CONTROLLER, clock=lambda: LATER):
            pytest.fail('expired task authorized')
    assert expired.value.code == 'JOB_WALL_BUDGET_EXHAUSTED'


def test_late_binding_and_unreserved_invocation_cannot_authorize(tmp_path, monkeypatch):
    lab, _, record = fixture(tmp_path)
    _, invocation = fake_binding(monkeypatch)
    with pytest.raises(LabValidationError) as missing:
        with jobs.job_authorization_gate(lab, invocation, controller_identity=CONTROLLER):
            pytest.fail('unreserved task authorized')
    assert missing.value.code == 'JOB_RESERVATION_REQUIRED'
    selected = reserve(lab, record)
    with pytest.raises(LabValidationError) as expired:
        bind(lab, selected, invocation, LATER)
    assert expired.value.code == 'JOB_WALL_BUDGET_EXHAUSTED'
    assert jobs.read_job(lab, 'JOB-001') == selected


def retain_result(lab, invocation, status, monkeypatch, *, stopped='absence_verified', ended=WITHIN):
    # Deterministic M06 boundary fixture: records are protected, and the fresh
    # acceptance verifier is explicitly injected instead of launching anything.
    worker = {'recorded_at': ended, 'stop_state': stopped}
    monkeypatch.setattr(jobs.AttemptStore, 'read_outcome', lambda *args: SimpleNamespace(
        to_dict=lambda: worker, digest=lambda: canonical_digest(worker)))
    acceptance = dict(schema_version='worker-lab-task-acceptance:v1', attempt_id=invocation.attempt_id,
        status='accepted', accepted=True, recorded_at=ended, outcome_digest=canonical_digest(worker),
        validation_id='VALIDATION-FIXTURE', validation_digest=DIGEST, review_id=None,
        candidate={'content_digest': DIGEST}) if status == 'accepted' else None
    from worker_lab import task_acceptance
    monkeypatch.setattr(task_acceptance, 'accept_task', lambda *args, **kwargs: SimpleNamespace(to_dict=lambda: acceptance))
    report = dict(schema_version='worker-lab-task-run:v1', attempt_id=invocation.attempt_id,
        invocation_id=invocation.invocation_id, status=status, accepted=status == 'accepted',
        worker_outcome=worker, outcome_digest=canonical_digest(worker), acceptance=acceptance,
        validation={'completed_at': ended, 'all_validators_absent': True},
        error=None if status == 'accepted' else {'code': 'FIXTURE_FAILURE', 'message': 'fixture did not pass'})
    records = AtomicRecordStore(lab / 'state')
    if acceptance is not None:
        records.write_bytes(f'task-acceptances/{invocation.attempt_id}.json', (canonical_json(acceptance)+'\n').encode())
    digest = canonical_digest(report)
    records.write_bytes(f'task-runs/{invocation.attempt_id}/{digest[7:]}.json', (canonical_json(report)+'\n').encode())
    return digest


def finish(lab, bound, report_digest, clock=WITHIN):
    return jobs.record_task_result(lab, 'JOB-001', controller_identity=CONTROLLER,
        reservation_id=bound.to_dict()['active']['reservation_id'], task_run_digest=report_digest, clock=lambda: clock)


def test_b_selects_only_after_durable_accepted_a_and_cannot_execute_without_promotion(tmp_path, monkeypatch):
    lab, _, initial = fixture(tmp_path)
    _, invocation = fake_binding(monkeypatch)
    bound = bind(lab, reserve(lab, initial), invocation)
    digest = retain_result(lab, invocation, 'accepted', monkeypatch)
    accepted = finish(lab, bound, digest)
    assert accepted.to_dict()['tasks']['A']['state'] == 'accepted'
    assert accepted.to_dict()['status'] == 'ready'
    assert finish(lab, bound, digest, LATER) == accepted
    selected_b = reserve(lab, jobs.read_job(lab, 'JOB-001'), WITHIN)
    assert selected_b.to_dict()['active']['task_id'] == 'B'
    assert finish(lab, bound, digest, LATER) == selected_b
    _, b = fake_binding(monkeypatch, task_id='B')
    bind(lab, selected_b, b, WITHIN)
    with pytest.raises(LabValidationError) as promotion:
        with jobs.job_authorization_gate(lab, b, controller_identity=CONTROLLER, clock=lambda: WITHIN):
            pytest.fail('dependency executed without accepted source handoff')
    assert promotion.value.code == 'JOB_INPUT_PROMOTION_REQUIRED'


@pytest.mark.parametrize('status,stopped', [('failed','absence_verified'), ('blocked','not_started'), ('blocked','uncertain')])
def test_failed_or_uncertain_a_blocks_b_and_survives_restart(tmp_path, monkeypatch, status, stopped):
    lab, _, initial = fixture(tmp_path)
    _, invocation = fake_binding(monkeypatch)
    bound = bind(lab, reserve(lab, initial), invocation)
    digest = retain_result(lab, invocation, status, monkeypatch, stopped=stopped)
    failed = finish(lab, bound, digest)
    assert failed.to_dict()['status'] == 'blocked'
    assert failed.to_dict()['tasks']['B']['state'] == 'pending'
    assert (failed.to_dict()['active'] is not None) == (stopped == 'uncertain')
    assert jobs.read_job(lab, 'JOB-001') == failed
    with pytest.raises(LabValidationError):
        reserve(lab, failed)


def test_pending_review_can_be_completed_without_reselection(tmp_path, monkeypatch):
    lab, _, initial = fixture(tmp_path)
    _, invocation = fake_binding(monkeypatch)
    bound = bind(lab, reserve(lab, initial), invocation)
    pending = finish(lab, bound, retain_result(lab, invocation, 'pending_review', monkeypatch))
    assert pending.to_dict()['tasks']['A']['state'] == 'pending_review'
    assert pending.to_dict()['active'] == bound.to_dict()['active']
    pending_digest = pending.to_dict()['tasks']['A']['attempts'][0]['run_digest']
    assert finish(lab, pending, pending_digest) == pending
    accepted = finish(lab, pending, retain_result(lab, invocation, 'accepted', monkeypatch))
    assert accepted.to_dict()['status'] == 'ready'
    assert len(accepted.to_dict()['tasks']['A']['attempts']) == 1
    assert accepted.to_dict()['blocker'] is None
    assert accepted.to_dict()['tasks']['A']['blocker'] is None


@pytest.mark.parametrize('mutation', [
    lambda task: task['attempts'].append(deepcopy(task['attempts'][0])),
    lambda task: task['attempts'][0].update(attempt_id='JOBTASK-partial'),
    lambda task: task['attempts'][0].update(deadline_at=LATER),
])
def test_malformed_durable_attempt_budget_or_binding_fails_closed(tmp_path, mutation):
    lab, _, initial = fixture(tmp_path)
    selected = reserve(lab, initial)
    changed = selected.to_dict()
    mutation(changed['tasks']['A'])
    path = lab / 'state/jobs/JOB-001.json'
    path.write_text(canonical_json(changed), encoding='utf-8')
    with pytest.raises(LabValidationError):
        jobs.read_job(lab, 'JOB-001')


def test_result_cannot_accept_when_fresh_protected_evidence_rejects(tmp_path, monkeypatch):
    from worker_lab import task_acceptance
    lab, _, initial = fixture(tmp_path)
    _, invocation = fake_binding(monkeypatch)
    bound = bind(lab, reserve(lab, initial), invocation)
    digest = retain_result(lab, invocation, 'accepted', monkeypatch)
    def reject(*args, **kwargs):
        raise LabValidationError('ACCEPTANCE_EVIDENCE_CHANGED', 'protected evidence no longer matches')
    monkeypatch.setattr(task_acceptance, 'accept_task', reject)
    with pytest.raises(LabValidationError) as rejected:
        finish(lab, bound, digest)
    assert rejected.value.code == 'ACCEPTANCE_EVIDENCE_CHANGED'
    assert jobs.read_job(lab, 'JOB-001') == bound


def test_all_accepted_tasks_complete_the_job_without_an_extra_reservation(tmp_path, monkeypatch):
    lab, _, initial = fixture(tmp_path)
    _, a = fake_binding(monkeypatch)
    bound_a = bind(lab, reserve(lab, initial), a)
    accepted_a = finish(lab, bound_a, retain_result(lab, a, 'accepted', monkeypatch))
    _, b = fake_binding(monkeypatch, task_id='B')
    bound_b = bind(lab, reserve(lab, accepted_a, WITHIN), b, WITHIN)
    complete = finish(lab, bound_b, retain_result(lab, b, 'accepted', monkeypatch))
    assert complete.to_dict()['status'] == 'complete'
    assert complete.to_dict()['active'] is None
    assert all(item['state'] == 'accepted' for item in complete.to_dict()['tasks'].values())
    with pytest.raises(LabValidationError) as stopped:
        reserve(lab, complete, WITHIN)
    assert stopped.value.code == 'JOB_NOT_RUNNABLE'


def test_completed_report_after_task_deadline_never_accepts_job_task(tmp_path, monkeypatch):
    lab, _, initial = fixture(tmp_path)
    _, invocation = fake_binding(monkeypatch)
    bound = bind(lab, reserve(lab, initial), invocation)
    digest = retain_result(lab, invocation, 'accepted', monkeypatch, ended=LATER)
    with pytest.raises(LabValidationError) as expired:
        finish(lab, bound, digest, LATER)
    assert expired.value.code == 'JOB_WALL_BUDGET_EXHAUSTED'
    assert jobs.read_job(lab, 'JOB-001') == bound


def test_changed_dependency_acceptance_blocks_selection(tmp_path, monkeypatch):
    lab, _, initial = fixture(tmp_path)
    _, invocation = fake_binding(monkeypatch)
    bound = bind(lab, reserve(lab, initial), invocation)
    accepted = finish(lab, bound, retain_result(lab, invocation, 'accepted', monkeypatch))
    path = lab / 'state/task-acceptances/JOBTASK-A.json'
    changed = json.loads(path.read_text(encoding='utf-8')); changed['candidate']['content_digest'] = 'sha256:' + 'b'*64
    path.write_text(json.dumps(changed), encoding='utf-8')
    with pytest.raises(LabValidationError) as drift:
        reserve(lab, accepted, WITHIN)
    assert drift.value.code == 'JOB_DEPENDENCY_CHANGED'
    assert jobs.read_job(lab, 'JOB-001') == accepted
