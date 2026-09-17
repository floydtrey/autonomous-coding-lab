"""Real Git snapshots of deterministic worker / protected native-check evidence."""
import json
import os
from pathlib import Path
import subprocess

import pytest

from tests import test_task_acceptance as m06
from worker_lab.accepted_snapshot import promote_accepted_task, verify_accepted_snapshot
from worker_lab.errors import LabValidationError
from worker_lab.storage import AtomicRecordStore

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='existing Windows protected-check fixtures')


@pytest.fixture
def tmp_path(tmp_path_factory):
    return tmp_path_factory.mktemp('m08')


def ready(tmp_path, monkeypatch, **options):
    service, lab, outcome, checks, checker = m06.prepared(tmp_path, monkeypatch, **options)
    accepted = m06.accept(lab, outcome, checks)
    if options.get('content') != b'VALUE = 3\n':
        assert accepted.to_dict()['accepted'], accepted.to_dict()
    artifacts = tmp_path/'artifacts'
    artifacts.mkdir()
    return service, lab, outcome, accepted, artifacts


def promote(lab, outcome, accepted, artifacts):
    return promote_accepted_task(lab, attempt_id=outcome.to_dict()['attempt_id'],
        expected_acceptance_digest=accepted.digest(), controller_identity=m06.m05.CONTROLLER,
        artifact_root=artifacts, clock=lambda:'2026-09-17T12:00:00Z')


def test_promotion_is_clean_separate_and_idempotent(tmp_path, monkeypatch):
    service, lab, outcome, accepted, artifacts = ready(tmp_path, monkeypatch)
    candidate = Path(outcome.to_dict()['workspace'])
    original = subprocess.run(['git','-C',str(candidate),'rev-parse','HEAD'],check=True,
        capture_output=True,text=True).stdout.strip()
    result = promote(lab,outcome,accepted,artifacts)
    value = result.to_dict()
    repository = Path(value['repository'])
    assert repository != candidate
    assert (repository/'record_ledger/models.py').read_bytes() == b'VALUE = 2\n'
    assert (candidate/'record_ledger/models.py').read_bytes() == b'VALUE = 2\n'
    assert value['snapshot_commit'] != value['source_base_commit'] == original
    assert value['changed_paths'] == ['record_ledger/models.py'] and not value['noop']
    assert promote(lab,outcome,accepted,artifacts).digest() == result.digest()
    assert verify_accepted_snapshot(lab,reference=value['reference'],expected_digest=result.digest()) == result


def test_rejected_candidate_cannot_be_promoted(tmp_path, monkeypatch):
    service, lab, outcome, accepted, artifacts = ready(tmp_path, monkeypatch,content=b'VALUE = 3\n')
    assert not accepted.to_dict()['accepted']
    with pytest.raises(LabValidationError):
        promote(lab,outcome,accepted,artifacts)
    assert list(artifacts.iterdir()) == []


def test_candidate_drift_prevents_publication(tmp_path, monkeypatch):
    service, lab, outcome, accepted, artifacts = ready(tmp_path, monkeypatch)
    (Path(outcome.to_dict()['workspace'])/'record_ledger/models.py').write_bytes(b'drift\n')
    with pytest.raises(LabValidationError):
        promote(lab,outcome,accepted,artifacts)
    assert list(artifacts.iterdir()) == []


def test_accepted_noop_retains_base_without_empty_commit(tmp_path, monkeypatch):
    service, lab, outcome, accepted, artifacts = ready(tmp_path, monkeypatch,
        content=b'# model\n',contract={'allow_noop':True},
        code=m06.m05.CHECKER.replace('VALUE = 2','# model'))
    result = promote(lab,outcome,accepted,artifacts).to_dict()
    assert result['noop'] is True and result['changed_paths'] == []
    assert result['snapshot_commit'] == result['source_base_commit']


def test_snapshot_drift_is_rejected_on_replay(tmp_path, monkeypatch):
    service, lab, outcome, accepted, artifacts = ready(tmp_path, monkeypatch)
    result = promote(lab,outcome,accepted,artifacts)
    (Path(result.to_dict()['repository'])/'record_ledger/models.py').write_bytes(b'changed\n')
    with pytest.raises(LabValidationError,match='snapshot'):
        promote(lab,outcome,accepted,artifacts)


def test_published_receipt_recovers_after_protected_write_interruption(tmp_path, monkeypatch):
    service, lab, outcome, accepted, artifacts = ready(tmp_path, monkeypatch)
    original = AtomicRecordStore.write_bytes
    writes = []
    def interrupted(self, relative_path, payload, **options):
        if relative_path.startswith('accepted-snapshots/') and not writes:
            writes.append(relative_path)
            raise LabValidationError('STORAGE_WRITE_FAILED','simulated receipt interruption')
        return original(self,relative_path,payload,**options)
    monkeypatch.setattr(AtomicRecordStore,'write_bytes',interrupted)
    with pytest.raises(LabValidationError,match='interruption'):
        promote(lab,outcome,accepted,artifacts)
    final = next(path for path in artifacts.iterdir() if path.name.startswith('SNAPSHOT-'))
    before = json.loads((final/'receipt.json').read_text(encoding='utf-8'))
    # Completed immutable publication does not depend on retaining mutable input.
    (Path(outcome.to_dict()['workspace'])/'record_ledger/models.py').write_bytes(b'later change\n')
    result = promote(lab,outcome,accepted,artifacts)
    assert result.to_dict() == before
    assert len(list(artifacts.iterdir())) == 1


def test_partial_stage_blocks_without_second_commit(tmp_path, monkeypatch):
    service, lab, outcome, accepted, artifacts = ready(tmp_path, monkeypatch)
    original = AtomicRecordStore.write_bytes
    def interrupted(self, relative_path, payload, **options):
        if relative_path.startswith('snapshot-prepared/'):
            raise LabValidationError('STORAGE_WRITE_FAILED','simulated prepared proof interruption')
        return original(self,relative_path,payload,**options)
    monkeypatch.setattr(AtomicRecordStore,'write_bytes',interrupted)
    with pytest.raises(LabValidationError,match='interruption'):
        promote(lab,outcome,accepted,artifacts)
    with pytest.raises(LabValidationError) as exc:
        promote(lab,outcome,accepted,artifacts)
    assert exc.value.code == 'SNAPSHOT_PROMOTION_UNCERTAIN'
    assert len(list(artifacts.iterdir())) == 1


def test_copy_inventory_must_match_accepted_bytes(tmp_path, monkeypatch):
    import worker_lab.accepted_snapshot as snapshot
    service, lab, outcome, accepted, artifacts = ready(tmp_path, monkeypatch)
    original = snapshot._current_acceptance
    candidate = Path(outcome.to_dict()['workspace'])/'record_ledger/models.py'
    calls = []
    def changed_after_check(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(None)
        if len(calls)==1:
            candidate.write_bytes(b'VALUE = 999\n')
        return result
    monkeypatch.setattr(snapshot,'_current_acceptance',changed_after_check)
    with pytest.raises(LabValidationError,match='inventory'):
        promote(lab,outcome,accepted,artifacts)
    assert list(artifacts.iterdir()) == []


def test_changed_git_configuration_rejected_before_git_execution(tmp_path, monkeypatch):
    import worker_lab.accepted_snapshot as snapshot
    service, lab, outcome, accepted, artifacts = ready(tmp_path, monkeypatch)
    result = promote(lab,outcome,accepted,artifacts)
    config = Path(result.to_dict()['repository'])/'.git/config'
    config.write_bytes(config.read_bytes()+b'\n[core]\n\tfsmonitor = untrusted-command\n')
    monkeypatch.setattr(snapshot,'inspect_launch_workspace',lambda *a,**kw:pytest.fail('unverified Git config executed'))
    with pytest.raises(LabValidationError,match='metadata changed'):
        verify_accepted_snapshot(lab,reference=result.to_dict()['reference'],expected_digest=result.digest())


def test_changed_candidate_config_rejected_before_evidence_git(tmp_path,monkeypatch):
    import worker_lab.accepted_snapshot as snapshot
    service, lab, outcome, accepted, artifacts = ready(tmp_path,monkeypatch)
    config = Path(outcome.to_dict()['workspace'])/'.git/config'
    config.write_bytes(config.read_bytes()+b'\n[core]\n\tfsmonitor = untrusted-command\n')
    monkeypatch.setattr(snapshot,'_evidence',lambda *a,**kw:pytest.fail('unverified candidate config executed'))
    with pytest.raises(LabValidationError,match='before evidence inspection'):
        promote(lab,outcome,accepted,artifacts)
    assert list(artifacts.iterdir()) == []


@pytest.mark.parametrize('rewrite',['grafts','loose-replace','packed-replace'])
def test_snapshot_ancestry_overrides_rejected_before_git(tmp_path,monkeypatch,rewrite):
    import worker_lab.accepted_snapshot as snapshot
    service,lab,outcome,accepted,artifacts=ready(tmp_path,monkeypatch)
    result=promote(lab,outcome,accepted,artifacts)
    repository=Path(result.to_dict()['repository'])
    commit=result.to_dict()['snapshot_commit']
    if rewrite=='grafts':
        (repository/'.git/info/grafts').write_text(commit+'\n',encoding='utf-8')
    elif rewrite=='loose-replace':
        replacement=repository/'.git/refs/replace';replacement.mkdir()
        (replacement/commit).write_text(commit+'\n',encoding='utf-8')
    else:
        with (repository/'.git/packed-refs').open('ab') as handle:
            handle.write((commit+' refs/replace/'+commit+'\n').encode('ascii'))
    monkeypatch.setattr(snapshot,'inspect_launch_workspace',lambda *a,**kw:pytest.fail('ancestry override reached Git'))
    with pytest.raises(LabValidationError,match='ancestry overrides'):
        verify_accepted_snapshot(lab,reference=result.to_dict()['reference'],expected_digest=result.digest())


def test_snapshot_git_discards_ambient_config_and_hooks(tmp_path, monkeypatch):
    service, lab, outcome, accepted, artifacts = ready(tmp_path, monkeypatch)
    marker = tmp_path/'hook-marker'
    hook_dir = tmp_path/'hooks'; hook_dir.mkdir()
    (hook_dir/'pre-commit').write_text('#!/bin/sh\necho ran > "'+marker.as_posix()+'"\n',encoding='utf-8')
    poison = tmp_path/'poison.gitconfig'
    poison.write_text('[core]\n\thooksPath = '+hook_dir.as_posix()+'\n[filter "poison"]\n\tclean = false\n',encoding='utf-8')
    monkeypatch.setenv('GIT_CONFIG_GLOBAL',str(poison))
    monkeypatch.setenv('GIT_CONFIG_COUNT','1')
    monkeypatch.setenv('GIT_CONFIG_KEY_0','core.hooksPath')
    monkeypatch.setenv('GIT_CONFIG_VALUE_0',str(hook_dir))
    result = promote(lab,outcome,accepted,artifacts)
    assert result.to_dict()['changed_paths'] == ['record_ledger/models.py']
    assert not marker.exists()


def test_checkout_attributes_support_literal_unicode_and_punctuation(tmp_path):
    from worker_lab.accepted_snapshot import _checkout_attributes, _git_runner
    candidate=tmp_path/'candidate';candidate.mkdir()
    repository=tmp_path/'copy'
    paths=('!first.txt','#hash.txt','café [one].txt','space name.txt')
    def git(root,*args):
        return subprocess.run(['git','-C',str(root),'-c','core.autocrlf=false',*args],
            check=True,capture_output=True,text=True,encoding='utf-8').stdout.strip()
    git(candidate,'init','-q')
    for path in paths:
        (candidate/path).write_bytes(b'line\n')
    git(candidate,'add','.')
    git(candidate,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
        '-c','commit.gpgsign=false','commit','-qm','base')
    subprocess.run(['git','clone','--no-checkout',str(candidate),str(repository)],check=True,capture_output=True)
    for path in paths:
        (candidate/path).write_bytes(b'line\r\n')
    _checkout_attributes(repository,candidate,paths,run_process=_git_runner('2026-09-17T12:00:00Z'))
    git(repository,'checkout','--force','HEAD','--','.')
    assert all((repository/path).read_bytes()==b'line\r\n' for path in paths)
    assert not git(repository,'status','--porcelain')
