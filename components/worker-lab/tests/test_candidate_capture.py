"""M05A review evidence is candidate-bound and independent of optional ZIP size."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import subprocess
import zipfile

import pytest

from tests import test_run_task as m04
from tests import test_protected_validation as m05
from worker_lab.canonical import canonical_json
from worker_lab.errors import LabValidationError
from worker_lab.storage import AtomicRecordStore
from worker_lab.windows_job import workspace_content_digest
from worker_lab.worker_outcome import WorkerOutcome
import worker_lab.run_task as capture


def git(root, *args):
    return subprocess.run(['git', '-c', 'core.longpaths=true', '-C', str(root), *args],
        check=True, capture_output=True).stdout


def repository(tmp_path):
    root = tmp_path / 'candidate'; root.mkdir()
    git(root, 'init', '-q')
    (root / 'tracked.txt').write_bytes(b'before\n')
    (root / '.gitignore').write_bytes(b'ignored.txt\n')
    git(root, 'add', '.')
    git(root, '-c', 'user.name=ACL fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '-qm', 'base')
    base = git(root, 'rev-parse', 'HEAD').decode().strip()
    git(root, 'checkout', '--detach', '-q', base)
    invocation = SimpleNamespace(attempt_id='ATTEMPT-fixture', source_state=SimpleNamespace(base_commit=base))
    records = AtomicRecordStore(tmp_path / 'protected-state')
    return root, invocation, records


def test_patch_is_complete_and_applies_without_touching_index(tmp_path, monkeypatch):
    root, invocation, records = repository(tmp_path)
    other = tmp_path / 'other'
    subprocess.run(['git', 'clone', '-q', '--no-hardlinks', str(root), str(other)], check=True)
    expected = {'tracked.txt': b'after\n', 'new file.txt': b'new text\n',
        'binary.bin': b'\0\xffbinary\0', 'empty.txt': b'', 'ignored.txt': b'ignored but retained\n'}
    for name, content in expected.items():
        (root / name).write_bytes(content)
    index_before = (root / '.git/index').read_bytes()
    monkeypatch.setenv('GIT_DIR', str(other / '.git'))
    monkeypatch.setenv('GIT_WORK_TREE', str(other))
    monkeypatch.setenv('GIT_INDEX_FILE', str(other / '.git/index'))
    monkeypatch.setenv('GIT_CONFIG_COUNT', '1')
    monkeypatch.setenv('GIT_CONFIG_KEY_0', 'diff.external')
    monkeypatch.setenv('GIT_CONFIG_VALUE_0', 'untrusted-command-must-never-run')
    artifacts = {}
    candidate = capture._snapshot(records, invocation, root, artifacts, 0)
    assert candidate['archive'] is None and 'candidate.zip' not in artifacts
    assert candidate['content_digest'] == workspace_content_digest(root)
    patch = records.read_bytes(candidate['diff'])
    assert b'+after' in patch and b'GIT binary patch' in patch and b'ignored but retained' in patch
    assert (root / '.git/index').read_bytes() == index_before
    # Apply the retained patch to an independent clean base and compare every byte.
    with monkeypatch.context() as clean:
        for name in list(os.environ):
            if name.startswith('GIT_'):
                clean.delenv(name)
        subprocess.run(['git', '-C', str(other), 'apply', '--binary', '-'], input=patch,
            check=True, capture_output=True)
    for name, content in expected.items():
        assert (other / name).read_bytes() == content


@pytest.mark.parametrize('limit', [0, 1, 1024])
def test_archive_budget_does_not_change_identity_or_diff(tmp_path, limit):
    root, invocation, records = repository(tmp_path)
    (root / 'tracked.txt').write_bytes(b'changed\n')
    artifacts = {}
    candidate = capture._snapshot(records, invocation, root, artifacts, limit)
    assert candidate['content_digest'] == workspace_content_digest(root)
    assert b'+changed' in records.read_bytes(candidate['diff'])
    metadata = candidate['archive_capture']
    assert metadata['limit_bytes'] == limit
    assert metadata['content_bytes'] == sum(p.stat().st_size for p in root.iterdir() if p.is_file())
    if limit == 1024:
        assert metadata['status'] == 'captured'
        with zipfile.ZipFile(records.root / candidate['archive']) as bundle:
            assert bundle.read('tracked.txt') == b'changed\n'
    else:
        assert metadata['status'] == 'omitted_limit' and candidate['archive'] is None


@pytest.mark.parametrize('failure', ['drift', 'unreadable'])
def test_omitted_archive_does_not_mask_unstable_or_unreadable_candidate(tmp_path, monkeypatch, failure):
    root, invocation, records = repository(tmp_path)
    original = capture._candidate_diff
    def changed(*args):
        result = original(*args)
        if failure == 'unreadable':
            raise PermissionError('fixture unreadable candidate')
        (root / 'tracked.txt').write_bytes(b'concurrent edit\n')
        return result
    monkeypatch.setattr(capture, '_candidate_diff', changed)
    with pytest.raises((LabValidationError, PermissionError)) as error:
        capture._snapshot(records, invocation, root, {}, 0)
    if failure == 'drift':
        assert error.value.code == 'CANDIDATE_DRIFT'
    assert not (records.root / 'worker-artifacts').exists()


@pytest.mark.skipif(os.name != 'nt', reason='existing Windows controller and validator')
def test_untouched_large_asset_retains_completed_claim_and_reaches_approved_checks(tmp_path, monkeypatch):
    original = m04.fixtures.write_authority_fixture
    def large_authority(path):
        lab, target = original(path)
        # Existing asset is committed before admission and is never granted for editing.
        with (target / 'existing-data.bin').open('wb') as asset:
            asset.truncate(33 * 1024 * 1024)
        git(target, 'add', 'existing-data.bin')
        git(target, '-c', 'user.name=ACL fixture', '-c', 'user.email=fixture@example.invalid',
            'commit', '-qm', 'existing asset')
        head = git(target, 'rev-parse', 'HEAD').decode().strip()
        for relative, field in [('curricula/exercises/record-model/v1.json', 'template_commit'),
                ('curricula/contexts/record-model-context/v1.json', 'starting_commit')]:
            authority = lab / relative
            value = json.loads(authority.read_text(encoding='utf-8')); value[field] = head
            authority.write_text(canonical_json(value), encoding='utf-8')
        return lab, target
    monkeypatch.setattr(m04.fixtures, 'write_authority_fixture', large_authority)
    service, lab, root, outcome, checker = m05.prepare(tmp_path, monkeypatch)
    value = outcome.to_dict(); candidate = value['candidate']
    assert value['status'] == 'completed_claim' and value['error'] is None
    assert value['accepted'] is False and value['stop_state'] == 'absence_verified'
    assert candidate['archive'] is None and 'candidate.zip' not in value['artifacts']
    assert candidate['archive_capture']['limit_bytes'] == 32 * 1024 * 1024
    assert candidate['archive_capture']['content_bytes'] > 33 * 1024 * 1024
    assert any(d['code'] == 'CANDIDATE_ARCHIVE_OMITTED' for d in value['diagnostics'])
    assert candidate['content_digest'] == workspace_content_digest(Path(value['workspace']))
    asset = Path(value['workspace']) / 'existing-data.bin'
    assert hashlib.sha256(asset.read_bytes()).digest() == hashlib.sha256((tmp_path / 'target/existing-data.bin').read_bytes()).digest()
    patch = (lab / 'state' / candidate['diff']).read_bytes()
    assert b'+VALUE = 2' in patch and b'content.py' in patch and b'existing-data.bin' not in patch
    m05.approve(service, outcome, checker)
    report = m05.validate(service, outcome).to_dict()
    assert report['status'] == 'passed' and report['all_validators_absent']
    assert report['accepted'] is False


@pytest.mark.skipif(os.name != 'nt', reason='existing Windows controller')
def test_operator_budget_is_durable_and_replay_cannot_change_it(tmp_path, monkeypatch):
    service, lab, root, task, prepared = m04.prepare(tmp_path, monkeypatch)
    original = m04.AttemptStore.save_transition
    def interrupt(self, updated):
        if updated.state is m04.AttemptState.OUTCOME_RECORDED:
            raise LabValidationError('STORAGE_WRITE_FAILED', 'fixture interrupted finalization')
        return original(self, updated)
    monkeypatch.setattr(m04.AttemptStore, 'save_transition', interrupt)
    with pytest.raises(LabValidationError, match='interrupted finalization'):
        m04.run_worker(service, task, runner_factory=m04.factory('success', []), candidate_archive_limit_bytes=0)
    monkeypatch.setattr(m04.AttemptStore, 'save_transition', original)
    outcome = m04.run_worker(service, task, runner_factory=lambda **kw: pytest.fail('replay launched'),
        candidate_archive_limit_bytes=100000)
    candidate = outcome.to_dict()['candidate']
    assert candidate['archive'] is None and candidate['archive_capture']['limit_bytes'] == 0
    intent = json.loads(next((lab / 'state/run-task-intents').glob('*.json')).read_text(encoding='utf-8'))
    assert intent['candidate_archive_limit_bytes'] == 0
    invalid = outcome.to_dict(); invalid['candidate']['archive_capture']['status'] = 'captured'
    with pytest.raises(LabValidationError):
        WorkerOutcome.from_mapping(invalid)
    task_value = json.loads(task.read_text(encoding='utf-8'))
    assert task_value['invocation_id'] == outcome.to_dict()['invocation_id']


@pytest.mark.parametrize('value', [-1, True, 1.5, '100'])
def test_invalid_archive_budget_rejects(value):
    with pytest.raises(LabValidationError, match='archive budget'):
        capture._archive_limit(value)
