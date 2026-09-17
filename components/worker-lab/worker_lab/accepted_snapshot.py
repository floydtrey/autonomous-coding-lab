"""Promote one independently accepted candidate into a separate local snapshot.

This is controller-only local publication. It neither runs a worker nor changes
the accepted candidate, the approved plan, or any running installation.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .operator_control import validate_controller_identity
from .pi_supervision import _exclusive_controller, now
from .storage import AtomicRecordStore
from .task_acceptance import _evidence, _review
from .windows_job import inspect_launch_workspace, _content_entry
from .workspace import (_assert_no_nested_git_repository, _assert_no_reparse_tree,
    _has_only_crlf_newlines, _has_only_lf_newlines, _git, _git_bytes, _git_environment,
    _real_directory, _verify_workspace_root, _overlaps)

SCHEMA = 'worker-lab-accepted-snapshot:v1'
INTENT_SCHEMA = 'worker-lab-snapshot-intent:v1'
DIGEST = re.compile(r'sha256:[0-9a-f]{64}')


@dataclass(frozen=True)
class SnapshotReport:
    payload: str

    def to_dict(self):
        return json.loads(self.payload)

    def to_json(self):
        return self.payload

    def digest(self):
        return canonical_digest(self.to_dict())


def _require(ok, code, message):
    if not ok:
        raise LabValidationError(code, message)


def _read_optional(records, reference):
    try:
        return records.read(reference, lambda value: value)
    except LabValidationError as exc:
        if exc.code != 'STORAGE_RECORD_MISSING':
            raise
        return None


def _tree(root):
    _assert_no_reparse_tree(root, skip_git=True)
    _assert_no_nested_git_repository(root)
    entries = []
    for path in sorted(root.rglob('*'), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if relative.parts[0] == '.git' or path.is_dir():
            continue
        _require(path.is_file(), 'SNAPSHOT_ENTRY_INVALID', 'snapshot entries must be regular files')
        entries.append(_content_entry(path, relative.as_posix()))
    return entries


def _tree_digest(entries):
    return canonical_digest({'schema_version':'worker-lab-snapshot-files:v1', 'files':entries})


def _workspace_digest(root, entries):
    return canonical_digest({'schema_version':'worker-lab-workspace-content:v1',
        'files':[*entries,_content_entry(root/'.git/config','.git/config')]})


def _accepted(records, attempt_id, expected_digest):
    _require(isinstance(expected_digest, str) and DIGEST.fullmatch(expected_digest),
        'SNAPSHOT_ACCEPTANCE_INVALID', 'an exact accepted-task digest is required')
    value = records.read(f'task-acceptances/{attempt_id}.json', lambda item:item)
    _require(isinstance(value, dict) and value.get('schema_version') == 'worker-lab-task-acceptance:v1'
        and canonical_digest(value) == expected_digest and value.get('attempt_id') == attempt_id
        and value.get('accepted') is True and value.get('status') == 'accepted'
        and value.get('error') is None and isinstance(value.get('evidence'), dict)
        and canonical_digest(value['evidence']) == value.get('evidence_digest'),
        'SNAPSHOT_ACCEPTANCE_INVALID', 'promotion requires the exact protected M06 acceptance record')
    return value


def _current_acceptance(data_root, records, attempt_id, expected_digest, controller):
    accepted = _accepted(records, attempt_id, expected_digest)
    candidate = _real_directory(Path(accepted['workspace']),'SNAPSHOT_CANDIDATE_INVALID')
    _assert_no_reparse_tree(candidate)
    _require(_workspace_digest(candidate,_tree(candidate))==accepted['evidence']['candidate_digest'],
        'SNAPSHOT_ACCEPTANCE_CHANGED','candidate bytes or Git configuration changed before evidence inspection')
    _, outcome, evidence = _evidence(data_root, attempt_id, accepted['outcome_digest'], controller,
        accepted['validation_id'], accepted['validation_digest'])
    _require(evidence == accepted['evidence'] and outcome['workspace'] == accepted['workspace']
        and outcome['candidate'] == accepted['candidate']
        and _review(records, accepted['review_id'], evidence) == accepted['review_digest'],
        'SNAPSHOT_ACCEPTANCE_CHANGED', 'accepted candidate, review or required evidence changed')
    return accepted


def _git_runner(recorded_at):
    """Keep the existing Git helper's safeguards and discard ambient Git inputs."""
    def run(command, **options):
        environment = _git_environment({key:os.environ[key]
            for key in ('PATH','SystemRoot','WINDIR') if key in os.environ})
        environment.update(GIT_AUTHOR_NAME='ACL Controller', GIT_COMMITTER_NAME='ACL Controller',
            GIT_AUTHOR_EMAIL='acl-controller@localhost', GIT_COMMITTER_EMAIL='acl-controller@localhost',
            GIT_AUTHOR_DATE=recorded_at, GIT_COMMITTER_DATE=recorded_at, GIT_NO_REPLACE_OBJECTS='1')
        options['env'] = environment
        return subprocess.run(command, **options)
    return run


def _git_paths(root, *args, run_process):
    return tuple(sorted(os.fsdecode(path) for path in _git_bytes(
        ['-C',str(root),'-c','core.fsmonitor=false',*args], 'inspect accepted snapshot',
        run_process,30).split(b'\0') if path))


def _attributes_digest(repository):
    path = repository/'.git/info/attributes'
    return canonical_digest({'bytes':path.read_bytes().hex() if path.exists() else None})


def _checkout_attributes(repository, candidate, tracked, *, run_process):
    patterns = []
    for path in tracked:
        source = candidate/path
        if source.is_file() and _has_only_crlf_newlines(source.read_bytes()) and _has_only_lf_newlines(
                _git_bytes(['-C',str(repository),'cat-file','blob','HEAD:'+path],
                    'read snapshot base blob',run_process,30)):
            # Git accepts C-quoted UTF-8 patterns; quote spaces, # and ! too.
            pattern = '/' + ''.join('\\'+char if char in '*?[]' else char for char in path)
            patterns.append(json.dumps(pattern,ensure_ascii=False)+' text eol=crlf\n')
    if patterns:
        (repository/'.git/info/attributes').write_text(''.join(patterns),encoding='utf-8')


def _verify_repository(value, repository):
    # Reject changed configuration using only bytes before invoking Git, whose
    # status/config expansion could otherwise execute a drifted fsmonitor/filter.
    _assert_no_reparse_tree(repository)
    _require(not (repository/'.git/info/grafts').exists()
        and not (repository/'.git/refs/replace').exists(),
        'SNAPSHOT_GIT_REWRITES','snapshot ancestry overrides are forbidden')
    packed = repository/'.git/packed-refs'
    if packed.exists():
        _require(not any(len(line.split())>=2 and line.split()[1].startswith(b'refs/replace/')
                         for line in packed.read_bytes().splitlines() if not line.startswith((b'#',b'^'))),
            'SNAPSHOT_GIT_REWRITES','packed snapshot ancestry overrides are forbidden')
    entries = _tree(repository)
    _require(_workspace_digest(repository,entries)==value['snapshot_workspace_digest']
        and _tree_digest(entries)==value['tree_digest']
        and _attributes_digest(repository)==value['checkout_attributes_digest'],
        'SNAPSHOT_DRIFT','published snapshot bytes or checkout metadata changed')
    observed = inspect_launch_workspace(repository)
    _require(observed.observed_head == value['snapshot_commit'] and not observed.status
        and observed.content_digest == value['snapshot_workspace_digest']
        and _tree_digest(entries) == value['tree_digest']
        and _attributes_digest(repository) == value['checkout_attributes_digest'],
        'SNAPSHOT_DRIFT', 'published snapshot commit, bytes or checkout metadata changed')
    tracked = _git_paths(repository,'ls-tree','-rz','--name-only',value['snapshot_commit'],
        run_process=_git_runner(value['recorded_at']))
    _require(tracked == tuple(item['path'] for item in entries), 'SNAPSHOT_UNCOMMITTED_FILES',
        'every retained snapshot file must be represented by the committed tree')
    run_process = _git_runner(value['recorded_at'])
    changed = _git_paths(repository, 'diff', '--no-renames', '--name-only', '-z',
        value['source_base_commit'], value['snapshot_commit'], run_process=run_process)
    _require(changed == tuple(value['changed_paths']), 'SNAPSHOT_COMMIT_MISMATCH',
        'committed paths differ from accepted changes')
    if value['noop']:
        _require(value['snapshot_commit'] == value['source_base_commit'], 'SNAPSHOT_COMMIT_MISMATCH',
            'accepted no-op must retain its base commit')
    else:
        parent = _git(['-C', str(repository), 'rev-parse', 'HEAD^'], 'verify snapshot parent',
            run_process, 30).stdout.strip()
        _require(parent == value['source_base_commit'], 'SNAPSHOT_COMMIT_MISMATCH',
            'snapshot commit must directly descend from its accepted base')
    return entries


def verify_accepted_snapshot(data_root, *, reference, expected_digest):
    """Verify a completed receipt; the original mutable candidate need not remain."""
    records = AtomicRecordStore(Path(data_root)/'state')
    value = records.read(reference, lambda item:item)
    fields = {'schema_version','snapshot_id','reference','attempt_id','acceptance_digest','outcome_digest',
        'candidate_digest','controller_identity','source_base_commit','changed_paths','repository',
        'snapshot_commit','snapshot_workspace_digest','tree_digest','checkout_attributes_digest','noop','recorded_at'}
    _require(isinstance(value,dict) and set(value)==fields and value.get('schema_version')==SCHEMA
        and canonical_digest(value)==expected_digest
        and value.get('reference')==reference
        and value.get('snapshot_id')=='SNAPSHOT-'+value.get('acceptance_digest','')[7:]
        and reference==f"accepted-snapshots/{value['snapshot_id']}.json",
        'SNAPSHOT_RECEIPT_INVALID','snapshot receipt identity differs')
    accepted = _accepted(records,value['attempt_id'],value['acceptance_digest'])
    evidence = accepted['evidence']
    _require(value['outcome_digest']==accepted['outcome_digest']
        and value['candidate_digest']==evidence['candidate_digest']
        and value['source_base_commit']==evidence['source_evidence']['base_commit']
        and value['changed_paths']==evidence['source_evidence']['changed_paths']
        and value['noop'] is (not bool(value['changed_paths'])),
        'SNAPSHOT_RECEIPT_INVALID','snapshot provenance differs from acceptance')
    validate_controller_identity(value['controller_identity'])
    repository = _real_directory(Path(value['repository']),'SNAPSHOT_PATH_INVALID')
    _require(repository.name=='repository' and repository.parent.name==value['snapshot_id']
        and not _overlaps(repository,Path(data_root).resolve()),
        'SNAPSHOT_PATH_INVALID','snapshot must be a separate controller artifact')
    embedded = AtomicRecordStore(repository.parent).read('receipt.json',lambda item:item)
    _require(embedded==value,'SNAPSHOT_RECEIPT_INVALID','published receipt differs from protected record')
    _verify_repository(value,repository)
    return SnapshotReport(canonical_json(value))


def promote_accepted_task(data_root, *, attempt_id, expected_acceptance_digest,
        controller_identity, artifact_root, clock=now):
    data_root = Path(data_root).resolve()
    controller = validate_controller_identity(controller_identity)
    records = AtomicRecordStore(data_root/'state')
    _require(isinstance(expected_acceptance_digest,str) and DIGEST.fullmatch(expected_acceptance_digest),
        'SNAPSHOT_ACCEPTANCE_INVALID','an exact acceptance digest is required')
    identity = 'SNAPSHOT-'+expected_acceptance_digest[7:]
    reference = f'accepted-snapshots/{identity}.json'
    intent_reference = f'snapshot-intents/{identity}.json'
    prepared_reference = f'snapshot-prepared/{identity}.json'
    root = _real_directory(Path(artifact_root),'SNAPSHOT_ROOT_INVALID')
    final, staging = root/identity, root/('.stage-'+identity)
    with _exclusive_controller(records.root,'snapshot-controller.lock'), \
            _exclusive_controller(records.root,'run-task.lock'), _exclusive_controller(records.root):
        existing = _read_optional(records,reference)
        if existing is not None:
            _require(existing.get('controller_identity')==controller
                and existing.get('attempt_id')==attempt_id
                and existing.get('repository')==str(final/'repository'),
                'SNAPSHOT_REPLAY_MISMATCH','existing snapshot belongs to another request')
            return verify_accepted_snapshot(data_root,reference=reference,expected_digest=canonical_digest(existing))
        accepted = _accepted(records,attempt_id,expected_acceptance_digest)
        candidate = Path(accepted['workspace'])
        _verify_workspace_root(root,data_root,candidate)
        intent = _read_optional(records,intent_reference)
        request = dict(schema_version=INTENT_SCHEMA,snapshot_id=identity,attempt_id=attempt_id,
            acceptance_digest=expected_acceptance_digest,controller_identity=controller,
            artifact_root=str(root),candidate=str(candidate),repository=str(final/'repository'))
        if intent is not None:
            _require(isinstance(intent,dict) and all(intent.get(key)==value for key,value in request.items()),
                'SNAPSHOT_REPLAY_MISMATCH','prior promotion request differs')
            # Recover only an already published, self-verifying snapshot. A partial
            # stage or missing proof does not justify rerunning a local commit.
            _require(final.is_dir() and not staging.exists(),'SNAPSHOT_PROMOTION_UNCERTAIN',
                'prior promotion has no complete published receipt; inspect without rerunning')
            recovered = AtomicRecordStore(final).read('receipt.json',lambda item:item)
            protected_prepared = records.read(prepared_reference, lambda item:item)
            _require(recovered == protected_prepared, 'SNAPSHOT_RECEIPT_INVALID',
                'published receipt differs from the durable prepared receipt')
            _require(recovered.get('acceptance_digest')==expected_acceptance_digest
                and recovered.get('attempt_id')==attempt_id and recovered.get('controller_identity')==controller
                and recovered.get('repository')==request['repository'],
                'SNAPSHOT_RECEIPT_INVALID','published snapshot differs from promotion intent')
            _verify_repository(recovered,final/'repository')
            records.write_bytes(reference,(canonical_json(recovered)+'\n').encode('utf-8'))
            return verify_accepted_snapshot(data_root,reference=reference,expected_digest=canonical_digest(recovered))
        _require(not final.exists() and not staging.exists(),'SNAPSHOT_TARGET_EXISTS',
            'unrecorded snapshot or stage already occupies the target')
        accepted = _current_acceptance(data_root,records,attempt_id,expected_acceptance_digest,controller)
        candidate = _real_directory(candidate,'SNAPSHOT_CANDIDATE_INVALID')
        recorded_at = clock()
        records.write_bytes(intent_reference,(canonical_json({**request,'recorded_at':recorded_at})+'\n').encode('utf-8'))
        entries = _tree(candidate)
        accepted_inventory = _workspace_digest(candidate,entries)
        _require(accepted_inventory==accepted['evidence']['candidate_digest'],
            'SNAPSHOT_ACCEPTANCE_CHANGED','copied inventory differs from independently accepted bytes')
        expected_tree = _tree_digest(entries)
        staging.mkdir()
        repository = staging/'repository'
        run_process = _git_runner(recorded_at)
        def git(*args):
            return _git(['-C',str(repository),'-c','core.autocrlf=false','-c','core.fsmonitor=false',*args],
                'publish accepted local snapshot',run_process,30).stdout.strip()
        _git(['-c','core.autocrlf=false','clone','--no-local','--no-hardlinks','--no-checkout','--',
            str(candidate),str(repository)],'clone accepted candidate base',run_process,30)
        git('config','core.longpaths','true')
        git('config','core.fsmonitor','false')
        base = accepted['evidence']['source_evidence']['base_commit']
        tracked = _git_paths(repository,'ls-tree','-rz','--name-only',base,run_process=run_process)
        _checkout_attributes(repository,candidate,tracked,run_process=run_process)
        git('checkout','--detach','--force',base,'--')
        git('remote','remove','origin')
        expected_paths = {entry['path'] for entry in entries}
        for entry in _tree(repository):
            if entry['path'] not in expected_paths:
                (repository/entry['path']).unlink()
        for entry in entries:
            destination = repository/entry['path']
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(candidate/entry['path'],destination)
        _require(_tree_digest(_tree(repository))==expected_tree,'SNAPSHOT_COPY_DRIFT',
            'snapshot copy differs from accepted candidate bytes')
        changed = accepted['evidence']['source_evidence']['changed_paths']
        if changed:
            git('add','-f','-A','--',*changed)
            staged = _git_paths(repository,'diff','--cached','--no-renames','--name-only','-z',run_process=run_process)
            _require(staged==tuple(changed),'SNAPSHOT_STAGED_PATHS_MISMATCH','staged changes differ from acceptance')
            git('-c','commit.gpgsign=false','commit','--no-gpg-sign','-m','ACL accepted snapshot '+identity)
            _require(git('rev-parse','HEAD^')==base,'SNAPSHOT_PARENT_MISMATCH','snapshot commit has the wrong parent')
        snapshot = inspect_launch_workspace(repository)
        _require(not snapshot.status and _tree_digest(_tree(repository))==expected_tree,
            'SNAPSHOT_COPY_DRIFT','published commit does not retain accepted working-tree bytes')
        value = dict(schema_version=SCHEMA,snapshot_id=identity,reference=reference,attempt_id=attempt_id,
            acceptance_digest=expected_acceptance_digest,outcome_digest=accepted['outcome_digest'],
            candidate_digest=accepted['evidence']['candidate_digest'],controller_identity=controller,
            source_base_commit=base,changed_paths=changed,repository=str(final/'repository'),
            snapshot_commit=snapshot.observed_head,snapshot_workspace_digest=snapshot.content_digest,
            tree_digest=expected_tree,checkout_attributes_digest=_attributes_digest(repository),
            noop=not bool(changed),recorded_at=recorded_at)
        _verify_repository(value,repository)
        _require(_current_acceptance(data_root,records,attempt_id,expected_acceptance_digest,controller)==accepted,
            'SNAPSHOT_ACCEPTANCE_CHANGED','candidate changed during local promotion')
        AtomicRecordStore(staging).write_bytes('receipt.json',(canonical_json(value)+'\n').encode('utf-8'))
        records.write_bytes(prepared_reference,(canonical_json(value)+'\n').encode('utf-8'))
        os.replace(staging,final)
        records.write_bytes(reference,(canonical_json(value)+'\n').encode('utf-8'))
        return verify_accepted_snapshot(data_root,reference=reference,expected_digest=canonical_digest(value))
