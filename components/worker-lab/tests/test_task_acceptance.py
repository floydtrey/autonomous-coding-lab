"""M06 accepts protected evidence, never a claim or a generic lifecycle verdict."""
from pathlib import Path
import json
import os
import subprocess

import pytest

from tests import test_protected_validation as m05
from tests import test_run_task as m04
from worker_lab.canonical import canonical_json
from worker_lab.errors import LabValidationError
from worker_lab.git_workspace_evidence import _changed_paths
from worker_lab.output_acceptance import OutputAcceptance
from worker_lab.process_custody import ProcessCustodyStore
from worker_lab.storage import AtomicRecordStore
from worker_lab.task_acceptance import accept_task, record_task_review

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='existing Windows controller and validators')


def prepared(tmp_path, monkeypatch, *, content=b'VALUE = 2\n', review=False, extra=False,
             contract=None, code=None):
    if contract is not None:
        import worker_lab.service_runtime_v3 as runtime
        original = runtime._output_contract
        def approved_contract(exercise, role):
            value = original(exercise, role).to_dict()
            value.update(contract)
            return OutputAcceptance.from_mapping(value)
        monkeypatch.setattr(runtime, '_output_contract', approved_contract)
    service, lab, root, outcome, checker = m05.prepare(tmp_path, monkeypatch, content=content,
        code=m05.CHECKER if code is None else code, candidate_extra=extra,
        approval_options={'review_required': review})
    m05.approve(service, outcome, checker)
    report = m05.validate(service, outcome)
    return service, lab, outcome, report, checker


def accept(lab, outcome, report, **options):
    return accept_task(lab, attempt_id=outcome.to_dict()['attempt_id'],
        expected_outcome_digest=outcome.digest(), controller_identity=m05.CONTROLLER,
        validation_id='VALIDATION-test', expected_validation_digest=report.digest(), **options)


def review(lab, outcome, report, review_id='REVIEW-one', **options):
    return record_task_review(lab, attempt_id=outcome.to_dict()['attempt_id'],
        expected_outcome_digest=outcome.digest(), controller_identity=m05.CONTROLLER,
        validation_id='VALIDATION-test', expected_validation_digest=report.digest(),
        review_id=review_id, reviewer_identity='trusted-reviewer', **options)


def test_acceptance_is_exact_immutable_and_keeps_worker_outcome_distinct(tmp_path, monkeypatch):
    service, lab, outcome, report, checker = prepared(tmp_path, monkeypatch)
    result = accept(lab, outcome, report)
    value = result.to_dict()
    assert value['status'] == 'accepted' and value['accepted'] is True, value
    assert value['candidate'] == outcome.to_dict()['candidate']
    assert value['validation_digest'] == report.digest()
    assert value['evidence']['source_evidence']['changed_paths'] == ['record_ledger/models.py']
    assert value['evidence']['test_ids'] == [check['test_id'] for check in report.to_dict()['checks']]
    assert value['evidence']['validator_logs']
    assert accept(lab, outcome, report).digest() == result.digest()
    attempt_id = outcome.to_dict()['attempt_id']
    saved = json.loads((lab/'state/task-acceptances'/f'{attempt_id}.json').read_text(encoding='utf-8'))
    assert saved == value
    assert m04.AttemptStore(lab/'state').read(attempt_id).state is m04.AttemptState.OUTCOME_RECORDED
    assert m04.AttemptStore(lab/'state').read_outcome(attempt_id).digest() == outcome.digest()
    assert outcome.to_dict()['accepted'] is False
    assert not (lab/'state/results').exists()


@pytest.mark.parametrize('change', ['candidate', 'diff', 'worker_result', 'log', 'judge', 'custody', 'validator_launch'])
def test_accepted_replay_rechecks_live_bytes_and_custody(tmp_path, monkeypatch, change):
    service, lab, outcome, report, checker = prepared(tmp_path, monkeypatch)
    accepted = accept(lab, outcome, report)
    assert accepted.to_dict()['accepted'] is True
    value = outcome.to_dict()
    if change == 'candidate':
        (Path(value['workspace'])/'record_ledger/models.py').write_bytes(b'changed after checks\n')
    elif change == 'diff':
        (lab/'state'/value['candidate']['diff']).write_bytes(b'forged review diff')
    elif change == 'worker_result':
        (lab/'state'/value['artifacts']['worker_result']).write_bytes(b'{}\n')
    elif change == 'log':
        (lab/'state'/report.to_dict()['checks'][0]['stdout']).write_bytes(b'changed log')
    elif change == 'judge':
        checker.write_text('changed authoritative checker', encoding='utf-8')
    elif change == 'validator_launch':
        path = lab/'state'/Path(report.to_dict()['checks'][0]['stdout']).parent/'launch-intent.json'
        launch = json.loads(path.read_text(encoding='utf-8'))
        launch['candidate_digest'] = 'sha256:'+'0'*64
        path.write_text(canonical_json(launch), encoding='utf-8')
    else:
        custody = ProcessCustodyStore(lab/'state').read(value['invocation_id']).to_dict()
        custody.update(state='DISPATCHING', active_workload_count=None, exit_code=None,
            absence_evidence_digest=None, absence_verified_at=None)
        AtomicRecordStore(lab/'state').write(f"process-custody/{value['invocation_id']}.json", m04._Record(custody))
    result = accept(lab, outcome, report).to_dict()
    assert result['accepted'] is False and result['status'] == 'blocked', result
    stored = json.loads((lab/'state/task-acceptances'/f"{value['attempt_id']}.json").read_text(encoding='utf-8'))
    assert stored == accepted.to_dict()


@pytest.mark.parametrize('missing', ['report', 'log', 'intent', 'check_result'])
def test_missing_protected_evidence_never_accepts(tmp_path, monkeypatch, missing):
    service, lab, outcome, report, checker = prepared(tmp_path, monkeypatch)
    check = report.to_dict()['checks'][0]
    paths = {'report': 'validation-results/VALIDATION-test.json',
        'log': check['stderr'], 'intent': 'validation-intents/VALIDATION-test.json',
        'check_result': str(Path(check['stdout']).parent/'result.json')}
    (lab/'state'/paths[missing]).unlink()
    result = accept(lab, outcome, report).to_dict()
    assert result['accepted'] is False and result['status'] == 'blocked', result
    assert not (lab/'state/task-acceptances').exists()


def test_failed_protected_check_and_out_of_scope_edit_cannot_accept(tmp_path, monkeypatch):
    service, lab, outcome, report, checker = prepared(tmp_path, monkeypatch, content=b'VALUE = 3\n')
    assert report.to_dict()['status'] == 'failed'
    decision = accept(lab, outcome, report).to_dict()
    assert decision['status'] == 'failed' and decision['error']['code'] == 'TASK_CHECKS_FAILED'
    assert not decision['accepted'] and not (lab/'state/task-acceptances').exists()


def test_passing_checks_do_not_waive_write_scope(tmp_path, monkeypatch):
    service, lab, outcome, report, checker = prepared(tmp_path, monkeypatch, extra=True)
    assert report.to_dict()['status'] == 'passed'
    decision = accept(lab, outcome, report).to_dict()
    assert decision['status'] == 'failed' and decision['error']['code'] == 'OUTPUT_ACCEPTANCE_INVALID'
    assert not decision['accepted']


@pytest.mark.parametrize('corruption', ['empty', 'duplicate', 'wrong_digest'])
def test_passing_label_is_not_complete_check_evidence(tmp_path, monkeypatch, corruption):
    service, lab, outcome, report, checker = prepared(tmp_path, monkeypatch)
    path = lab/'state/validation-results/VALIDATION-test.json'
    if corruption == 'wrong_digest':
        decision = accept_task(lab, attempt_id=outcome.to_dict()['attempt_id'],
            expected_outcome_digest=outcome.digest(), controller_identity=m05.CONTROLLER,
            validation_id='VALIDATION-test', expected_validation_digest='sha256:'+'0'*64).to_dict()
    else:
        value = report.to_dict()
        value['checks'] = [] if corruption == 'empty' else [value['checks'][0]] * len(value['checks'])
        path.write_text(canonical_json(value), encoding='utf-8')
        decision = accept(lab, outcome, report).to_dict()
    assert decision['accepted'] is False and decision['status'] == 'blocked'
    assert not (lab/'state/task-acceptances').exists()


@pytest.mark.parametrize('contract,content,expected', [
    ({'required_changed_paths': ['record_ledger/models.py'], 'required_artifact_paths': ['record_ledger/models.py']}, b'VALUE = 2\n', True),
    ({'required_changed_paths': ['tests/test_models.py']}, b'VALUE = 2\n', False),
    ({'required_artifact_paths': ['tests/test_models.py']}, b'VALUE = 2\n', False),
    ({'allow_noop': True}, b'# model\n', True),
    ({'allow_noop': False}, b'# model\n', False),
])
def test_explicit_output_obligations_and_noop(tmp_path, monkeypatch, contract, content, expected):
    checker = m05.CHECKER if content.startswith(b'VALUE') else m05.CHECKER.replace('VALUE = 2', '# model')
    service, lab, outcome, report, check = prepared(tmp_path, monkeypatch,
        content=content, contract=contract, code=checker)
    assert report.to_dict()['status'] == 'passed'
    decision = accept(lab, outcome, report).to_dict()
    assert decision['accepted'] is expected, decision
    assert decision['status'] == ('accepted' if expected else 'failed')


def test_required_review_is_pending_until_exact_review_and_replay_is_idempotent(tmp_path, monkeypatch):
    service, lab, outcome, report, checker = prepared(tmp_path, monkeypatch, review=True)
    decision = accept(lab, outcome, report).to_dict()
    assert decision['status'] == 'pending_review' and not decision['accepted']
    assert not (lab/'state/task-acceptances').exists()
    recorded = review(lab, outcome, report)
    assert review(lab, outcome, report).digest() == recorded.digest()
    result = accept(lab, outcome, report, review_id='REVIEW-one')
    assert result.to_dict()['accepted'] is True, result.to_dict()
    assert result.to_dict()['review_digest'] == recorded.digest()
    assert accept(lab, outcome, report, review_id='REVIEW-one').digest() == result.digest()


@pytest.mark.parametrize('changed', ['rejected', 'stale'])
def test_rejected_or_stale_review_is_not_approval(tmp_path, monkeypatch, changed):
    service, lab, outcome, report, checker = prepared(tmp_path, monkeypatch, review=True)
    review(lab, outcome, report, decision='rejected' if changed == 'rejected' else 'approved')
    if changed == 'stale':
        path = lab/'state/task-reviews/REVIEW-one.json'
        value = json.loads(path.read_text(encoding='utf-8'))
        value['candidate_digest'] = 'sha256:'+'0'*64
        path.write_text(canonical_json(value), encoding='utf-8')
    decision = accept(lab, outcome, report, review_id='REVIEW-one').to_dict()
    assert decision['status'] == ('failed' if changed == 'rejected' else 'pending_review')
    assert not decision['accepted'] and not (lab/'state/task-acceptances').exists()


def test_partial_acceptance_write_can_retry_without_worker_or_validator(tmp_path, monkeypatch):
    service, lab, outcome, report, checker = prepared(tmp_path, monkeypatch)
    original = AtomicRecordStore.write_bytes
    failed = []
    def interrupt(self, relative_path, payload, **options):
        if relative_path.startswith('task-acceptances/') and not failed:
            failed.append(relative_path)
            raise LabValidationError('STORAGE_WRITE_FAILED', 'fixture acceptance write interruption')
        return original(self, relative_path, payload, **options)
    monkeypatch.setattr(AtomicRecordStore, 'write_bytes', interrupt)
    first = accept(lab, outcome, report).to_dict()
    assert first['status'] == 'blocked' and not first['accepted']
    assert accept(lab, outcome, report).to_dict()['accepted'] is True


def test_git_scope_includes_ignored_names_unicode_and_both_rename_paths(tmp_path):
    root = tmp_path/'candidate'; root.mkdir()
    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], check=True,
            capture_output=True, text=True, encoding='utf-8').stdout.strip()
    git('init', '-q')
    git('config', 'core.autocrlf', 'false')
    (root/'.gitignore').write_text('ignored.txt\n', encoding='utf-8')
    (root/'old.txt').write_text('original bytes\n', encoding='utf-8')
    git('add', '.')
    git('-c', 'user.name=ACL fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'base')
    head = git('rev-parse', 'HEAD')
    (root/'old.txt').rename(root/'new.txt')
    (root/'ignored.txt').write_text('ignored but changed\n', encoding='utf-8')
    (root/'café.py').write_text('# unicode filename\n', encoding='utf-8')
    assert _changed_paths(root, head) == ('café.py', 'ignored.txt', 'new.txt', 'old.txt')
