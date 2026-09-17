"""Public single-task composition, with real protected fixture checks."""
import json
import os
from pathlib import Path
import sys

import pytest

from tests import test_run_task as m04
from tests.test_protected_validation import CHECKER
from worker_lab.canonical import canonical_json
from worker_lab.cli import main
from worker_lab.errors import LabValidationError
from worker_lab.integration_v3 import InvocationRecordV3
from worker_lab.process_custody import ProcessCustodyStore
from worker_lab.storage import AtomicRecordStore

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows worker/validator lifetime backend')
CONTROLLER = m04.fixtures.CONTROLLER


def prepare(tmp_path, monkeypatch, *, approve=True, review_required=False):
    original = m04.fixtures.write_authority_fixture
    def authority(path):
        lab, target = original(path)
        checker = lab/'checks/content.py'; checker.parent.mkdir()
        checker.write_text(CHECKER, encoding='utf-8')
        catalog_path = lab/'curricula/catalogs/worker-lab-v1.json'
        catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
        for test in catalog['tests']:
            test['command'] = [str(Path(sys.executable).resolve()), '-I', '-B', str(checker.resolve()), '{candidate}']
        catalog_path.write_text(canonical_json(catalog), encoding='utf-8')
        return lab, target
    monkeypatch.setattr(m04.fixtures, 'write_authority_fixture', authority)
    service, lab, root, task, prepared = m04.prepare(tmp_path, monkeypatch)
    checker = lab/'checks/content.py'
    if approve:
        service.approve_task_execution(task, CONTROLLER, protected_files=[checker],
            acknowledge_unsandboxed=True, review_required=review_required)
    return service, lab, task, checker, prepared


def worker(calls, *, content=b'VALUE = 2\n', extra=False):
    def factory(**options):
        def execute(payload):
            invocation = InvocationRecordV3.from_mapping(json.loads(payload)['invocation'])
            calls.append(invocation.invocation_id)
            workspace = options['workspace_root']
            (workspace/'record_ledger/models.py').write_bytes(content)
            if extra:
                (workspace/'ungranted.txt').write_bytes(b'not authorized\n')
            m04.fixtures._success_custody(invocation, workspace, ProcessCustodyStore(options['state_root']))
            options['outcome_sink']({'status':'completed','stop_reason':'stop','summary':'fixture edit',
                'remaining_work':None,'usage':None})
        return execute
    return factory


@pytest.mark.parametrize('content,expected', [(b'VALUE = 2\n','accepted'), (b'VALUE = 3\n','failed')])
def test_one_call_runs_checks_then_accepts_only_correct_code(tmp_path, monkeypatch, content, expected):
    service, lab, task, checker, _ = prepare(tmp_path, monkeypatch)
    calls = []
    first = service.run_task(task, runner_factory=worker(calls, content=content), candidate_archive_limit_bytes=0)
    value = first.to_dict()
    assert value['status'] == expected, value
    assert value['accepted'] is (expected == 'accepted')
    assert value['worker_outcome']['status'] == 'completed_claim'
    assert value['candidate']['archive'] is None
    assert value['validation']['all_validators_absent'] is True
    assert value['validation']['status'] == ('passed' if expected == 'accepted' else 'failed')
    assert len(calls) == 1
    repeat = service.run_task(task, runner_factory=lambda **kw:pytest.fail('replayed worker'),
        process_factory=lambda *a,**kw:pytest.fail('replayed validator'))
    assert repeat.digest() == first.digest()
    assert (lab/'state/task-acceptances'/f'{value["attempt_id"]}.json').exists() is value['accepted']


def test_missing_advance_consent_creates_no_worker_or_validator(tmp_path, monkeypatch):
    service, lab, task, checker, _ = prepare(tmp_path, monkeypatch, approve=False)
    report = service.run_task(task, runner_factory=lambda **kw:pytest.fail('unapproved worker'),
        process_factory=lambda *a,**kw:pytest.fail('unapproved validator')).to_dict()
    assert report['status'] == 'blocked' and report['accepted'] is False
    assert report['error']['code'] == 'TASK_EXECUTION_APPROVAL_REQUIRED'
    assert not (lab/'state/run-task-intents').exists()
    assert not (lab/'state/validation-intents').exists()


def test_task_replacement_between_approval_and_worker_read_launches_nothing(tmp_path, monkeypatch):
    service, lab, task, checker, _ = prepare(tmp_path, monkeypatch)
    from worker_lab import task_workflow
    original = task_workflow.run_worker
    def swap(data_root, task_file, **options):
        value = json.loads(task_file.read_text(encoding='utf-8'))
        value['invocation_id'] = 'INVOCATION-substituted'
        task_file.write_text(canonical_json(value), encoding='utf-8')
        return original(data_root, task_file, **options)
    monkeypatch.setattr(task_workflow, 'run_worker', swap)
    value = service.run_task(task, runner_factory=lambda **kw:pytest.fail('substituted task launched')).to_dict()
    assert value['accepted'] is False and value['error']['code'] == 'RUN_TASK_IDENTITY_MISMATCH'
    assert not (lab/'state/run-task-intents').exists()


def test_explicit_consent_cannot_be_waived_or_changed(tmp_path, monkeypatch):
    service, lab, task, checker, _ = prepare(tmp_path, monkeypatch, approve=False)
    with pytest.raises(LabValidationError, match='unsandboxed'):
        service.approve_task_execution(task, CONTROLLER, protected_files=[checker])
    first = service.approve_task_execution(task, CONTROLLER, protected_files=[checker],
        acknowledge_unsandboxed=True, review_required=True)
    repeat = service.approve_task_execution(task, CONTROLLER, protected_files=[checker],
        acknowledge_unsandboxed=True, review_required=True)
    assert repeat.digest() == first.digest()
    with pytest.raises(LabValidationError, match='cannot be replaced'):
        service.approve_task_execution(task, CONTROLLER, protected_files=[checker],
            acknowledge_unsandboxed=True, review_required=False)
    checker.write_text('raise SystemExit(0)\n', encoding='utf-8')
    value = service.run_task(task, runner_factory=lambda **kw:pytest.fail('changed checker launched worker')).to_dict()
    assert value['status'] == 'blocked' and value['error']['code'] == 'TASK_EXECUTION_APPROVAL_CHANGED'


def test_required_review_stops_then_resumes_only_acceptance(tmp_path, monkeypatch):
    service, lab, task, checker, _ = prepare(tmp_path, monkeypatch, review_required=True)
    first = service.run_task(task, runner_factory=worker([])).to_dict()
    assert first['status'] == 'pending_review' and first['accepted'] is False
    from worker_lab.canonical import canonical_digest
    report = first['validation']
    service.record_task_review(first['attempt_id'], first['outcome_digest'], CONTROLLER,
        report['validation_id'], canonical_digest(report), reviewer_identity='operator-reviewer',
        review_id='REVIEW-exact-candidate', decision='approved')
    final = service.run_task(task, review_id='REVIEW-exact-candidate',
        runner_factory=lambda **kw:pytest.fail('review replay launched worker'),
        process_factory=lambda *a,**kw:pytest.fail('review replay launched validator')).to_dict()
    assert final['status'] == 'accepted' and final['accepted'] is True
    assert final['candidate'] == first['candidate']


def test_out_of_scope_change_cannot_be_accepted(tmp_path, monkeypatch):
    service, lab, task, checker, _ = prepare(tmp_path, monkeypatch)
    value = service.run_task(task, runner_factory=worker([], extra=True)).to_dict()
    assert value['accepted'] is False and value['status'] in {'failed','blocked'}
    assert not (lab/'state/task-acceptances').exists()


def test_acceptance_write_interruption_reuses_stopped_worker_and_checks(tmp_path, monkeypatch):
    service, lab, task, checker, _ = prepare(tmp_path, monkeypatch)
    original = AtomicRecordStore.write_bytes
    def interrupt(self, path, data, **kwargs):
        if path.startswith('task-acceptances/'):
            raise LabValidationError('STORAGE_WRITE_FAILED', 'fixture interrupted acceptance write')
        return original(self, path, data, **kwargs)
    monkeypatch.setattr(AtomicRecordStore, 'write_bytes', interrupt)
    first = service.run_task(task, runner_factory=worker([])).to_dict()
    assert first['accepted'] is False and first['worker_outcome']['status'] == 'completed_claim'
    monkeypatch.setattr(AtomicRecordStore, 'write_bytes', original)
    final = service.run_task(task, runner_factory=lambda **kw:pytest.fail('interrupted acceptance relaunched worker'),
        process_factory=lambda *a,**kw:pytest.fail('interrupted acceptance reran checks')).to_dict()
    assert final['accepted'] is True


def test_cli_approval_and_execution_use_same_path(tmp_path, monkeypatch, capsys):
    service, lab, task, checker, _ = prepare(tmp_path, monkeypatch, approve=False)
    assert main(['--root',str(lab),'approve-task-execution',str(task),'--controller',CONTROLLER,
        '--protected-file',str(checker),'--acknowledge-unsandboxed-host-code-execution']) == 0
    consent = json.loads(capsys.readouterr().out)
    assert consent['review_required'] is False
    # The CLI owns no alternate execution or acceptance implementation.
    from worker_lab import cli
    original = service.run_task
    monkeypatch.setattr(service, 'run_task', lambda path,**kw:original(path,runner_factory=worker([]),**kw))
    monkeypatch.setattr(cli, '_service', lambda args:service)
    assert main(['--root',str(lab),'run-task',str(task),'--candidate-archive-limit-bytes','0']) == 0
    value = json.loads(capsys.readouterr().out)
    assert value['status'] == 'accepted' and value['accepted'] is True
    assert value['candidate']['archive'] is None
