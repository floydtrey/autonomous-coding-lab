"""Real Git ancestry; protected acceptance/receipt verification is a named fixture seam."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from worker_lab import job_runner as lineage
from worker_lab.accepted_snapshot import _git_runner
from worker_lab.canonical import canonical_digest
from worker_lab.errors import LabValidationError
from worker_lab.workspace import _git

STAMP = '2026-09-17T12:00:00Z'
CONTROLLER = 'controller-1'


def git(root, *arguments):
    return _git(['-C', str(root), '-c', 'core.autocrlf=false', *arguments],
        'build local ancestry fixture', _git_runner(STAMP), 30).stdout.strip()


def history(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    git(source, 'init')
    (source / 'model.txt').write_text('base\n', encoding='utf-8')
    git(source, 'add', 'model.txt')
    git(source, 'commit', '-m', 'base')
    base = git(source, 'rev-parse', 'HEAD')
    (source / 'model.txt').write_text('accepted A\n', encoding='utf-8')
    git(source, 'commit', '-am', 'A')
    a = git(source, 'rev-parse', 'HEAD')
    (source / 'notes.txt').write_text('accepted B\n', encoding='utf-8')
    git(source, 'add', 'notes.txt')
    git(source, 'commit', '-m', 'B')
    b = git(source, 'rev-parse', 'HEAD')
    return source, base, a, b


def receipt(tmp_path, source, commit, name):
    root = tmp_path / name
    _git(['clone', '--no-local', '--no-hardlinks', '--no-checkout', '--', str(source), str(root)],
        'build immutable receipt fixture', _git_runner(STAMP), 30)
    git(root, 'checkout', '--detach', commit)
    git(root, 'remote', 'remove', 'origin')
    return dict(reference=f'accepted-snapshots/{name}.json', snapshot_commit=commit,
        controller_identity=CONTROLLER, repository=str(root), recorded_at=STAMP)


def job(monkeypatch, receipts):
    tasks = {name: dict(state='accepted', artifact={'path': value['reference']}, fixture_receipt=value)
        for name, value in receipts.items()}
    tasks['NEXT'] = dict(state='reserved', dependencies=[])
    monkeypatch.setattr(lineage, '_accepted', lambda records, item: {'accepted': True})
    def verified_artifact(data_root, item):
        if item['artifact'] is None:
            raise LabValidationError('JOB_INPUT_PROMOTION_REQUIRED', 'accepted task is not promoted')
        return item['fixture_receipt']
    monkeypatch.setattr(lineage, '_artifact', verified_artifact)
    return dict(controller_identity=CONTROLLER, tasks=tasks)


def definition(selected):
    return SimpleNamespace(input_binding=SimpleNamespace(to_dict=lambda: dict(
        snapshot_reference=selected['reference'], snapshot_digest=canonical_digest(selected),
        repository=selected['repository'])))


def test_selects_snapshot_containing_all_accepted_tasks_without_dependency_edges(tmp_path, monkeypatch):
    source, _, a, b = history(tmp_path)
    ra, rb = receipt(tmp_path, source, a, 'SNAPSHOT-a'), receipt(tmp_path, source, b, 'SNAPSHOT-b')
    value = job(monkeypatch, {'A': ra, 'B': rb})
    assert value['tasks']['NEXT']['dependencies'] == []
    assert lineage._input_snapshot(tmp_path / 'lab', value, 'NEXT') == rb
    lineage._require_input_snapshot(tmp_path / 'lab', value, 'NEXT', definition(rb))
    with pytest.raises(LabValidationError) as old_input:
        lineage._require_input_snapshot(tmp_path / 'lab', value, 'NEXT', definition(ra))
    assert old_input.value.code == 'JOB_INPUT_MISMATCH'
    with pytest.raises(LabValidationError) as original:
        lineage._require_input_snapshot(tmp_path / 'lab', value, 'NEXT', SimpleNamespace(input_binding=None))
    assert original.value.code == 'JOB_INPUT_REQUIRED'


def test_noop_tie_is_deterministic_and_excludes_current_task(tmp_path, monkeypatch):
    source, _, a, _ = history(tmp_path)
    first = receipt(tmp_path, source, a, 'SNAPSHOT-a')
    noop = receipt(tmp_path, source, a, 'SNAPSHOT-z')
    value = job(monkeypatch, {'Z': noop, 'A': first})
    assert lineage._input_snapshot(tmp_path / 'lab', value, 'NEXT') == first
    assert lineage._input_snapshot(tmp_path / 'lab', value, 'A') == noop
    reversed_value = {**value, 'tasks': dict(reversed(list(value['tasks'].items())))}
    assert lineage._input_snapshot(tmp_path / 'lab', reversed_value, 'NEXT') == first


def test_divergent_accepted_commits_are_blocked_without_mutation(tmp_path, monkeypatch):
    source, base, a, _ = history(tmp_path)
    ra = receipt(tmp_path, source, a, 'SNAPSHOT-a')
    git(source, 'checkout', '--detach', base)
    (source / 'other.txt').write_text('independent branch\n', encoding='utf-8')
    git(source, 'add', 'other.txt')
    git(source, 'commit', '-m', 'divergent B')
    rb = receipt(tmp_path, source, git(source, 'rev-parse', 'HEAD'), 'SNAPSHOT-b')
    value = job(monkeypatch, {'A': ra, 'B': rb})
    before = deepcopy(value)
    with pytest.raises(LabValidationError) as diverged:
        lineage._input_snapshot(tmp_path / 'lab', value, 'NEXT')
    assert diverged.value.code == 'JOB_INPUT_DIVERGED'
    assert value == before
    assert git(Path(ra['repository']), 'rev-parse', 'HEAD') == a
    assert git(Path(rb['repository']), 'rev-parse', 'HEAD') == rb['snapshot_commit']


@pytest.mark.parametrize('fault', ['missing_promotion', 'other_controller'])
def test_every_prior_acceptance_requires_its_own_matching_promoted_receipt(tmp_path, monkeypatch, fault):
    source, _, a, b = history(tmp_path)
    ra, rb = receipt(tmp_path, source, a, 'SNAPSHOT-a'), receipt(tmp_path, source, b, 'SNAPSHOT-b')
    value = job(monkeypatch, {'A': ra, 'B': rb})
    if fault == 'missing_promotion':
        value['tasks']['A']['artifact'] = None
    else:
        ra['controller_identity'] = 'different-controller'
    with pytest.raises(LabValidationError) as rejected:
        lineage._input_snapshot(tmp_path / 'lab', value, 'NEXT')
    assert rejected.value.code == ('JOB_INPUT_PROMOTION_REQUIRED' if fault == 'missing_promotion'
        else 'JOB_INPUT_CONTROLLER_MISMATCH')


def test_first_task_has_no_snapshot_and_cannot_import_an_unrelated_snapshot(tmp_path, monkeypatch):
    value = job(monkeypatch, {})
    assert lineage._input_snapshot(tmp_path / 'lab', value, 'NEXT') is None
    lineage._require_input_snapshot(tmp_path / 'lab', value, 'NEXT', SimpleNamespace(input_binding=None))
    with pytest.raises(LabValidationError) as unexpected:
        lineage._require_input_snapshot(tmp_path / 'lab', value, 'NEXT', SimpleNamespace(input_binding=object()))
    assert unexpected.value.code == 'JOB_INPUT_UNEXPECTED'

