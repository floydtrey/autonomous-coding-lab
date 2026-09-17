"""Protected accepted-snapshot input; never a replacement for approved authority."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .accepted_snapshot import verify_accepted_snapshot, _git_runner, _tree, _tree_digest
from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .job_plan import identity, obj
from .operator_control import validate_controller_identity
from .policy import ContextManifest
from .storage import AtomicRecordStore
from .workspace import _git, _real_directory

SCHEMA = 'worker-lab-job-input:v1'


def _require(ok, message):
    if not ok:
        raise LabValidationError('JOB_INPUT_INVALID', message)


@dataclass(frozen=True)
class JobInput:
    canonical: str

    @classmethod
    def from_mapping(cls, value):
        d = obj(value, {'schema_version','plan_digest','task_id','profile_digest',
            'controller_identity','snapshot_reference','snapshot_digest','repository','context'}, 'job input')
        _require(d['schema_version'] == SCHEMA, 'unsupported job input schema')
        identity(d['task_id'], 'input task_id')
        validate_controller_identity(d['controller_identity'])
        from .accepted_snapshot import DIGEST
        for key in ('plan_digest','profile_digest','snapshot_digest'):
            _require(isinstance(d[key], str) and DIGEST.fullmatch(d[key]), 'job input digest is invalid')
        _require(isinstance(d['snapshot_reference'], str) and isinstance(d['repository'], str),
            'job input locator is invalid')
        ContextManifest.from_mapping(d['context'])
        return cls(canonical_json(d))

    def to_dict(self):
        return json.loads(self.canonical)

    def digest(self):
        return canonical_digest(self.to_dict())

    @property
    def reference(self):
        return 'job-inputs/INPUT-' + self.digest()[7:] + '.json'

    def context(self):
        return ContextManifest.from_mapping(self.to_dict()['context'])

    def validate_scope(self, *, profile, plan_digest, task_id, controller_identity):
        value = self.to_dict()
        _require(value['profile_digest'] == profile.digest() and value['plan_digest'] == plan_digest
            and value['task_id'] == task_id and value['controller_identity'] == controller_identity,
            'input differs from the exact original approved task/profile/controller')
        before = profile.authorities()[2].to_dict()
        after = self.context().to_dict()
        # An input overlay changes only observed base and hashes. Logical target,
        # context membership/purpose/version and every authority stay approved.
        _require({key: val for key,val in before.items() if key not in ('starting_commit','files')} ==
                 {key: val for key,val in after.items() if key not in ('starting_commit','files')}
            and [(item['path'],item['purpose']) for item in before['files']] ==
                [(item['path'],item['purpose']) for item in after['files']],
            'input cannot add context paths or change approved context identity/purpose')


def _derive(profile, receipt):
    repository = _real_directory(Path(receipt['repository']), 'JOB_INPUT_INVALID')
    context = profile.authorities()[2].to_dict()
    # A snapshot must retain the approved base in its history. Its verified
    # receipt supplies a direct accepted edge; M07 checks the selected job edge.
    _git(['-C',str(repository),'merge-base','--is-ancestor',context['starting_commit'],
          receipt['snapshot_commit']], 'verify approved job input ancestry',
          _git_runner(receipt['recorded_at']), 30)
    context['starting_commit'] = receipt['snapshot_commit']
    entries = _tree(repository)
    _require(_tree_digest(entries)==receipt['tree_digest'], 'snapshot input inventory differs from accepted artifact')
    files = {entry['path']:entry for entry in entries}
    for item in context['files']:
        _require(item['path'] in files, 'accepted snapshot is missing an approved context file')
        item['digest'] = files[item['path']]['digest']
    return ContextManifest.from_mapping(context)


def create_job_input(data_root, *, profile, plan_digest, task_id, controller_identity,
        snapshot_reference, snapshot_digest):
    """Persist exact input lineage after the job owner selected its dependency."""
    controller = validate_controller_identity(controller_identity)
    receipt = verify_accepted_snapshot(data_root, reference=snapshot_reference,
        expected_digest=snapshot_digest).to_dict()
    _require(receipt['controller_identity'] == controller, 'snapshot belongs to another controller')
    binding = JobInput.from_mapping(dict(schema_version=SCHEMA,plan_digest=plan_digest,
        task_id=task_id,profile_digest=profile.digest(),controller_identity=controller,
        snapshot_reference=snapshot_reference,snapshot_digest=snapshot_digest,
        repository=receipt['repository'],context=_derive(profile,receipt).to_dict()))
    binding.validate_scope(profile=profile,plan_digest=plan_digest,task_id=task_id,controller_identity=controller)
    AtomicRecordStore(Path(data_root)/'state').write_bytes(binding.reference,
        (binding.canonical+'\n').encode('utf-8'))
    return binding


def verify_job_input(data_root, *, binding, profile, plan_digest, task_id, controller_identity,
        source_repository=None):
    binding = binding if isinstance(binding, JobInput) else JobInput.from_mapping(binding)
    binding.validate_scope(profile=profile,plan_digest=plan_digest,task_id=task_id,
        controller_identity=controller_identity)
    protected = AtomicRecordStore(Path(data_root)/'state').read(binding.reference,JobInput.from_mapping)
    _require(protected == binding, 'protected job input differs from the admitted definition')
    value = binding.to_dict()
    receipt = verify_accepted_snapshot(data_root,reference=value['snapshot_reference'],
        expected_digest=value['snapshot_digest']).to_dict()
    _require(receipt['controller_identity'] == controller_identity and receipt['repository'] == value['repository']
        and _derive(profile,receipt).to_dict() == value['context'],
        'snapshot bytes or input lineage differ from the admitted definition')
    if source_repository is not None:
        _require(_real_directory(Path(source_repository),'JOB_INPUT_INVALID') == Path(value['repository']),
            'downstream preparation must use the exact accepted snapshot repository')
    return binding
