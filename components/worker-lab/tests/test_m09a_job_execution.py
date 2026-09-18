"""M09A one-reservation integration; no sequential controller or real model.

The actual job/admission/authorization, AWF/Pi request construction, outcome,
validation, acceptance and immutable record code runs. Only the provider
response, owned-process behavior, and time are simulated. This is not a
real-model or independent Windows process-lifetime qualification.
"""
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
from tests.test_validation_deadline import Clock, Process, EPOCH_MS
from worker_lab import pi_binding, pi_dispatch, protected_validation
from worker_lab.application_service import WorkerLabApplicationService
from worker_lab.attempt_store import AttemptStore
from worker_lab.canonical import canonical_digest, canonical_json
from worker_lab.controller_task_packet import build_controller_task_packet
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

# Keep native controller locks: do not replace the actual lock implementation.
pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows controller locks')
worker_module = importlib.import_module('worker_lab.run_task')


@pytest.fixture
def make_case(tmp_path, monkeypatch):
    def prepare(*, preparation_ms=0, check_timeout=30, config=None):
        timer = Clock()
        lab, target, original_plan, service = setup_job(tmp_path, complete_plan=True)
        lab = lab.resolve()
        service._clock = timer.timestamp
        monkeypatch.setattr(pi_dispatch, 'time', timer)
        monkeypatch.setattr(protected_validation, 'time', timer)
        # Explicit fixture observation, not a real host identity measurement.
        monkeypatch.setattr(protected_validation, 'process_creation_time_for_pid', lambda pid: 1)

        checker = lab / 'checks' / 'content.py'
        checker.parent.mkdir()
        checker.write_text(
            'from pathlib import Path\nimport sys\n'
            'raise SystemExit(0 if (Path(sys.argv[1]) / "record_ledger/models.py").read_bytes()'
            ' == b"VALUE = 2\\n" else 7)\n', encoding='utf-8')
        # Complete the copied test authority BEFORE any approval/admission.
        # No production authority or already-approved task is rewritten.
        value = original_plan.to_dict()
        ref = value['tasks'][0]['authority_ref']
        profiles = AtomicRecordStore(lab / 'job-authorities')
        profile_path = f"{ref['profile_id']}/v{ref['version']}.json"
        profile_value = profiles.read(profile_path, lambda x: x)
        for test in profile_value['catalog']['tests']:
            test['command'] = [str(Path(sys.executable).resolve()), '-I', '-B',
                               str(checker), '{candidate}']
        profile = JobAuthorityProfile.from_mapping(profile_value)
        profiles.write(profile_path, profile)
        ref['digest'] = profile.digest()
        plan = JobPlan.from_mapping(value)
        assert plan.task('A').budget.max_wall_seconds == 60
        job = service.create_job('JOB-M09A', plan, approved_by=CONTROLLER,
                                 approved_plan_digest=plan.digest())
        reserved = service.reserve_next_job_task('JOB-M09A', controller_identity=CONTROLLER,
                                                expected_job_digest=job.digest())
        slot = reserved.to_dict()['tasks']['A']['attempts'][0]
        deadline_ms = EPOCH_MS + 60_000
        timer.elapsed_ms += preparation_ms

        attempt_id = service.admit_job_task(plan, 'A', target, approved_by=CONTROLLER,
                                           approved_plan_digest=plan.digest()).identity
        workspaces = tmp_path.resolve() / 'workspaces'
        workspaces.mkdir()
        service.prepare_workspace(attempt_id, target, workspaces)
        packet = build_controller_task_packet(AttemptStore(lab / 'state').read(attempt_id),
            controller_identity=CONTROLLER, user_request=plan.objective.text, no_context=True)
        config = config or intended_pi_worker()
        config_path = tmp_path.resolve() / 'protected-pi-worker.json'
        config_path.write_text(canonical_json(config), encoding='utf-8')
        monkeypatch.setattr(pi_binding, 'CONFIG_PATH', config_path)
        bound = binding(config)
        ProviderBindingStore(lab / 'state').create(bound)
        prepared = service.prepare_invocation(attempt_id, workspaces, packet.to_json(),
            logical_target_id=plan.objective.target_id, provider_binding_id=bound.binding_id,
            provider_binding_digest=bound.digest()).to_dict()
        service.bind_job_attempt('JOB-M09A', controller_identity=CONTROLLER,
            reservation_id=slot['reservation_id'], attempt_id=attempt_id,
            invocation_id=prepared['identity'],
            expected_invocation_digest=prepared['immutable_identity_digest'])
        service.authorize_invocation(prepared['identity'],
            prepared['immutable_identity_digest'], CONTROLLER)
        records = AtomicRecordStore(lab / 'state')
        node = shutil.which('node')
        assert node, 'Use the previously verified Node executable on PATH for this batch'
        records.write('operator/pi-host.json', _Record(dict(schema_version='acl-pi-host:v1',
            node=str(Path(node).resolve()), python=str(Path(sys.executable).resolve()),
            framework_root=str(AWF.resolve()),
            pi_installation=str((tmp_path / 'unused-sdk').resolve()),
            agent_dir=str((lab / 'state' / 'agent').resolve()))))
        set_pi_activation(records.root, enabled=True, controller_identity=CONTROLLER,
                          worker_digest=canonical_digest(config))
        task = dict(schema_version='worker-lab-run-task:v1', invocation_id=prepared['identity'],
            expected_identity_digest=prepared['immutable_identity_digest'],
            controller_identity=CONTROLLER, workspace_root=str(workspaces))
        task_file = tmp_path.resolve() / 'task.json'
        task_file.write_text(canonical_json(task), encoding='utf-8')
        service.approve_task_execution(task_file, CONTROLLER, protected_files=[checker],
            acknowledge_unsandboxed=True, timeout_seconds=check_timeout)
        return SimpleNamespace(timer=timer, lab=lab, service=service, records=records,
            task_file=task_file, attempt_id=attempt_id, invocation_id=prepared['identity'],
            reservation_id=slot['reservation_id'], deadline_ms=deadline_ms, config=config,
            workspaces=workspaces, launches=[], check_deadlines=[], processes=[])
    return prepare


def worker_factory(case, *, status='completed', duration_ms=4000, stop_reason='stop',
                   hard_timeout=False):
    """Use the actual AWF/Pi seam; substitute only the provider process response."""
    def factory(**options):
        assert options['absolute_deadline_unix_ms'] == case.deadline_ms
        state = options['state_root']
        workspace = options['workspace_root']
        records = AtomicRecordStore(state)

        def launch(argv, raw, deadline):
            request = json.loads(raw)
            assert request['deadline_unix_ms'] == deadline
            assert deadline <= case.deadline_ms
            invocation = InvocationRecordV3.from_mapping(request['invocation'])
            case.launches.append(deepcopy(request))
            prefix = f'process-logs/{invocation.invocation_id}'
            records.write_bytes(prefix + '/request.jsonl', raw)
            (workspace / 'record_ledger/models.py').write_bytes(b'VALUE = 2\n')
            case.timer.elapsed_ms += duration_ms
            _success_custody(invocation, workspace, ProcessCustodyStore(state))
            if hard_timeout:
                # No terminal response survived. Counts/claim must remain unknown.
                raise LabValidationError('PI_TIMED_OUT', 'simulated owned-process timeout')
            result = dict(schema_version='acl-pi-result:v2', request_digest=canonical_digest(request),
                status=status, stop_reason=stop_reason, summary='Fixture: edited the authorized model file.',
                remaining_work=None if status == 'completed' else 'Fixture: protected checks remain.',
                session_reference='fixture-session:m09a',
                usage=dict(input_tokens=101, output_tokens=37,
                    requests=(case.config['runtime_settings']['request_limit']
                              if stop_reason == 'PI_REQUEST_BUDGET' else 4), tool_calls=3), candidate=None)
            event = dict(schema_version='acl-pi-event:v1', request_digest=canonical_digest(request),
                         sequence=0, event='settled', detail='Deterministic provider fixture settled.')
            output = encode_frame(event) + b'\n' + encode_frame(result) + b'\n'
            records.write_bytes(prefix + '/stdout.jsonl', output)
            return output

        return pi_dispatch.make_pi_dispatch_runner(
            binding_store=ProviderBindingStore(state), workspace_root=workspace,
            framework_root=options['framework_root'], node=options['node'], python=options['python'],
            pi_installation=options['pi_installation'], agent_dir=options['agent_dir'],
            launcher=launch, outcome_sink=options['outcome_sink'],
            absolute_deadline_unix_ms=options['absolute_deadline_unix_ms'])
    return factory


def run_workflow(case, monkeypatch, *, worker_ms=4000, check_ms=1000, **worker_options):
    original = protected_validation._run_check
    def observe(*args, **kwargs):
        case.check_deadlines.append(kwargs['absolute_deadline_unix_ms'])
        return original(*args, **kwargs)
    monkeypatch.setattr(protected_validation, '_run_check', observe)
    def process(*args, **kwargs):
        item = Process(case.timer, poll_ms=check_ms)
        case.processes.append(item)
        return item
    return case.service.run_task(case.task_file,
        runner_factory=worker_factory(case, duration_ms=worker_ms, **worker_options),
        process_factory=process, candidate_archive_limit_bytes=0)


def read_json(case, path):
    return case.records.read(path, lambda x: x)


def test_reserved_job_uses_one_deadline_and_retains_joinable_telemetry(make_case, monkeypatch):
    case = make_case(preparation_ms=20_000)
    report = run_workflow(case, monkeypatch, worker_ms=18_000, check_ms=6000)
    value = report.to_dict()
    assert value['status'] == 'accepted', json.dumps(value, indent=2)
    assert len(case.launches) == 1
    request = case.launches[0]
    assert request['issued_at_unix_ms'] == EPOCH_MS + 20_000
    assert request['deadline_unix_ms'] == case.deadline_ms
    assert request['worker']['runtime_settings']['request_limit'] == 64
    assert request['worker']['runtime_settings']['tool_calls_limit'] == 128
    assert request['worker']['model_name'] == case.config['model_name']
    worker = value['worker_outcome']
    assert worker['accepted'] is False
    assert worker['configuration_digest'] == request['worker_digest'] == canonical_digest(case.config)
    assert worker['usage'] == dict(input_tokens=101, output_tokens=37, requests=4, tool_calls=3)
    assert worker['worker_result']['status'] == 'completed'
    assert worker['worker_result']['remaining_work'] is None
    intent = read_json(case, f'run-task-intents/{case.attempt_id}.json')
    from datetime import datetime
    elapsed = (datetime.fromisoformat(worker['recorded_at']) -
               datetime.fromisoformat(intent['created_at'])).total_seconds()
    assert elapsed == 18
    assert len(case.check_deadlines) >= 2
    assert set(case.check_deadlines) == {case.deadline_ms}
    assert value['validation']['deadline_unix_ms'] == case.deadline_ms
    assert value['acceptance']['validation_digest'] == canonical_digest(value['validation'])
    validation_id = value['validation']['validation_id']
    assert read_json(case, f'validation-intents/{validation_id}.json')['deadline_unix_ms'] == case.deadline_ms
    updated = case.service.record_job_task_result('JOB-M09A', controller_identity=CONTROLLER,
        reservation_id=case.reservation_id, task_run_digest=report.digest()).to_dict()
    assert updated['tasks']['A']['state'] == 'accepted'
    assert updated['tasks']['B']['state'] == 'pending'
    assert updated['tasks']['B']['attempts'] == []  # M09B does not run here.


def test_later_check_cannot_restart_the_reservation_clock(make_case, monkeypatch):
    case = make_case(preparation_ms=20_000)
    report = run_workflow(case, monkeypatch, worker_ms=18_000, check_ms=12_000).to_dict()
    assert report['accepted'] is False
    checks = report['validation']['checks']
    assert len(checks) == 2, json.dumps(report, indent=2)
    assert checks[0]['status'] == 'passed'
    assert checks[1]['failure'] == 'JOB_WALL_BUDGET_EXHAUSTED'
    assert len(case.processes) == 2
    assert case.processes[1].killed and case.processes[1].closed
    assert report['validation']['all_validators_absent'] is True
    assert set(case.check_deadlines) == {case.deadline_ms}
    assert not (case.lab / 'state/task-acceptances' / f'{case.attempt_id}.json').exists()


def test_stricter_check_limit_remains_in_force(make_case, monkeypatch):
    case = make_case(check_timeout=1)
    report = run_workflow(case, monkeypatch, check_ms=1000).to_dict()
    assert report['accepted'] is False
    assert report['validation']['checks'][0]['failure'] == 'VALIDATION_TIMED_OUT'
    assert case.timer.time_ns() // 1_000_000 < case.deadline_ms


def test_stricter_worker_limit_is_sealed_inside_job_deadline(make_case):
    config = intended_pi_worker(attempt_timeout_seconds=12, provider_timeout_seconds=10,
                                tool_timeout_seconds=5)
    case = make_case(preparation_ms=20_000, config=config)
    outcome = worker_module.run_task(case.lab, case.task_file, clock=case.timer.timestamp,
        runner_factory=worker_factory(case), candidate_archive_limit_bytes=0).to_dict()
    assert outcome['status'] == 'completed_claim', json.dumps(outcome, indent=2)
    request = case.launches[0]
    assert request['deadline_unix_ms'] == request['issued_at_unix_ms'] + 12_000
    assert request['deadline_unix_ms'] < case.deadline_ms


def test_expired_reservation_launches_neither_worker_nor_validator(make_case):
    case = make_case()
    case.timer.elapsed_ms = 60_000
    report = case.service.run_task(case.task_file,
        runner_factory=lambda **k: pytest.fail('expired reservation launched worker'),
        process_factory=lambda *a, **k: pytest.fail('expired reservation launched validator')).to_dict()
    assert report['accepted'] is False
    assert report['worker_outcome']['stop_state'] == 'not_started'
    assert report['worker_outcome']['error']['code'] == 'JOB_WALL_BUDGET_EXHAUSTED'
    assert report['validation'] is None
    assert len(case.service.read_job('JOB-M09A').to_dict()['tasks']['A']['attempts']) == 1


def test_preparation_after_gate_still_cannot_extend_worker_deadline(make_case, monkeypatch):
    case = make_case()
    original = worker_module.prepare_dispatch
    def consume(*args, **kwargs):
        result = original(*args, **kwargs)
        case.timer.elapsed_ms = 60_000
        return result
    monkeypatch.setattr(worker_module, 'prepare_dispatch', consume)
    outcome = worker_module.run_task(case.lab, case.task_file, clock=case.timer.timestamp,
        runner_factory=worker_factory(case), candidate_archive_limit_bytes=0).to_dict()
    assert case.launches == []
    assert outcome['accepted'] is False
    assert outcome['error']['code'] == 'JOB_WALL_BUDGET_EXHAUSTED'


def test_late_worker_claim_cannot_launch_validation_or_become_acceptance(make_case, monkeypatch):
    case = make_case(preparation_ms=20_000)
    report = run_workflow(case, monkeypatch, worker_ms=40_000).to_dict()
    assert report['accepted'] is False
    assert report['error']['code'] == 'JOB_WALL_BUDGET_EXHAUSTED'
    assert case.processes == []
    assert report['validation'] is None
    assert not (case.lab / 'state/task-acceptances' / f'{case.attempt_id}.json').exists()


@pytest.mark.parametrize('claim,reason', [
    ('failed', 'PI_REQUEST_BUDGET'),
    ('needs_continuation', 'stop'),
    ('blocked', 'stop'),
])
def test_noncompleted_attempt_keeps_usage_claim_and_remaining_work(make_case, claim, reason):
    case = make_case()
    outcome = worker_module.run_task(case.lab, case.task_file, clock=case.timer.timestamp,
        runner_factory=worker_factory(case, status=claim, stop_reason=reason),
        candidate_archive_limit_bytes=0)
    value = outcome.to_dict()
    assert value['accepted'] is False
    assert value['worker_result']['status'] == claim
    assert value['worker_result']['stop_reason'] == reason
    assert value['worker_result']['summary']
    assert value['worker_result']['remaining_work']
    expected_requests = case.config['runtime_settings']['request_limit'] if reason == 'PI_REQUEST_BUDGET' else 4
    assert value['usage']['requests'] == expected_requests and value['usage']['tool_calls'] == 3
    assert value['candidate'] is not None and value['candidate']['accepted_base'] is False
    stored = (case.lab / 'state/worker-outcomes' / f'{case.attempt_id}.json').read_bytes()
    before_job = case.service.read_job('JOB-M09A').to_dict()
    case.timer.elapsed_ms = 120_000
    restarted = WorkerLabApplicationService(case.lab, clock=case.timer.timestamp)
    replay = worker_module.run_task(restarted.data_root, case.task_file, clock=case.timer.timestamp,
        runner_factory=lambda **k: pytest.fail('restart relaunched a failed worker'))
    assert replay.digest() == outcome.digest()
    assert restarted.read_job('JOB-M09A').to_dict() == before_job
    assert (case.lab / 'state/worker-outcomes' / f'{case.attempt_id}.json').read_bytes() == stored


def test_hard_timeout_does_not_invent_a_terminal_claim_or_zero_usage(make_case):
    case = make_case()
    value = worker_module.run_task(case.lab, case.task_file, clock=case.timer.timestamp,
        runner_factory=worker_factory(case, hard_timeout=True), candidate_archive_limit_bytes=0).to_dict()
    assert value['status'] == 'timed_out', json.dumps(value, indent=2)
    assert value['error']['code'] == 'PI_TIMED_OUT'
    assert value['worker_result'] is None and value['usage'] is None
    assert value['accepted'] is False
    assert 'request.jsonl' in value['artifacts']


@pytest.mark.parametrize('field,value', [
    ('invocation_id', 'INVOCATION-OTHER'),
    ('invocation_digest', 'sha256:' + 'b' * 64),
])
def test_changed_reservation_binding_blocks_before_any_work(make_case, field, value):
    case = make_case()
    path = case.lab / 'state/jobs/JOB-M09A.json'
    job = json.loads(path.read_text(encoding='utf-8'))
    job['tasks']['A']['attempts'][0][field] = value
    path.write_text(canonical_json(job), encoding='utf-8')
    report = case.service.run_task(case.task_file,
        runner_factory=lambda **k: pytest.fail('mismatched reservation launched'),
        process_factory=lambda *a, **k: pytest.fail('mismatched reservation validated')).to_dict()
    assert report['accepted'] is False
    assert report['worker_outcome']['error']['code'] == 'JOB_INVOCATION_MISMATCH'
    assert report['worker_outcome']['stop_state'] == 'not_started'
