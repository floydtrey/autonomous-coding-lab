"""Accepted A bytes become exact, read-only B context without changing authority."""
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from tests.test_accepted_snapshot import ready, promote, tmp_path
from tests.test_job_plan import fixture, FIXTURE
from worker_lab.attempt_store import AttemptStore
from worker_lab.errors import LabValidationError
from worker_lab.job_admission import JobAuthorityProfile, JobTaskDefinition, load_task_authorities
from worker_lab.job_input import create_job_input, verify_job_input
from worker_lab.job_plan import JobPlan
from worker_lab.storage import AtomicRecordStore


def task_inputs(lab,outcome,*,omit_readme=False):
    attempt = AttemptStore(lab/'state').read(outcome.to_dict()['attempt_id'])
    original_context = load_task_authorities(lab,attempt)[3]
    value = json.loads((FIXTURE.parent/'record-docs-authority.json').read_text(encoding='utf-8'))
    value['context'] = original_context.to_dict()
    if omit_readme:
        value['context']['files']=[item for item in value['context']['files'] if item['path']!='README.md']
    next(test for test in value['catalog']['tests'] if test['test_id']=='T004')['path_prefixes']=['README.md']
    profile = JobAuthorityProfile.from_mapping(value)
    AtomicRecordStore(lab/'job-authorities').write('record-docs-authority/v1.json',profile)
    plan = fixture()
    plan['tasks'][1]['authority_ref']['digest'] = profile.digest()
    return profile,JobPlan.from_mapping(plan)


def downstream(lab,outcome,receipt,**options):
    profile,plan = task_inputs(lab,outcome,**options)
    controller = receipt.to_dict()['controller_identity']
    binding = create_job_input(lab,profile=profile,plan_digest=plan.digest(),task_id='B',
        controller_identity=controller,snapshot_reference=receipt.to_dict()['reference'],snapshot_digest=receipt.digest())
    definition = JobTaskDefinition.from_mapping(dict(schema_version='worker-lab-job-task:v2',
        plan=plan.to_dict(),task_id='B',profile=profile.to_dict(),approved_by=controller,
        approved_plan_digest=plan.digest(),input_binding=binding.to_dict()))
    return definition,binding


def test_b_prepares_from_a_snapshot_with_original_authority_preserved(tmp_path,monkeypatch):
    service,lab,outcome,accepted,artifacts = ready(tmp_path,monkeypatch)
    receipt = promote(lab,outcome,accepted,artifacts)
    definition,binding = downstream(lab,outcome,receipt)
    repository = Path(receipt.to_dict()['repository'])
    definition.verify_input(lab,source_repository=repository)
    with pytest.raises(LabValidationError,match='dependent admission requires'):
        service.admit_job_task(definition.plan,'B',repository,approved_by=definition.approved_by,
            approved_plan_digest=definition.plan.digest())
    admitted = service.admit_job_task(definition.plan,'B',repository,approved_by=definition.approved_by,
        approved_plan_digest=definition.plan.digest(),input_binding=binding)
    workspaces = tmp_path/'next';workspaces.mkdir()
    prepared = service.prepare_workspace(admitted.identity,repository,workspaces)
    attempt = AttemptStore(lab/'state').read(admitted.identity)
    loaded,policy,role,context,catalog = load_task_authorities(lab,attempt)
    assert loaded.profile.digest() == definition.profile.digest() == definition.plan.task('B').authority_ref.digest
    assert loaded.plan.digest() == definition.plan.digest()
    assert loaded.writable_paths == ('README.md',)
    assert 'record_ledger/models.py' not in loaded.writable_paths
    assert context.starting_commit == receipt.to_dict()['snapshot_commit'] != loaded.profile.authorities()[2].starting_commit
    assert next(item.digest for item in context.files if item.path=='record_ledger/models.py') == 'sha256:'+hashlib.sha256(b'VALUE = 2\n').hexdigest()
    assert (workspaces/admitted.identity/'record_ledger/models.py').read_bytes() == b'VALUE = 2\n'
    assert (lab/'state'/binding.reference).is_file()
    with pytest.raises(LabValidationError,match='exact accepted snapshot'):
        definition.verify_input(lab,source_repository=Path(outcome.to_dict()['workspace']))


def test_input_cannot_change_scope_or_ignore_snapshot_drift(tmp_path,monkeypatch):
    service,lab,outcome,accepted,artifacts = ready(tmp_path,monkeypatch)
    receipt = promote(lab,outcome,accepted,artifacts)
    definition,binding = downstream(lab,outcome,receipt)
    value = definition.to_dict()
    value['input_binding']['context']['files'][0]['purpose'] = 'expanded permission'
    with pytest.raises(LabValidationError,match='identity/purpose'):
        JobTaskDefinition.from_mapping(value)
    (Path(receipt.to_dict()['repository'])/'record_ledger/models.py').write_bytes(b'drift\n')
    with pytest.raises(LabValidationError):
        definition.verify_input(lab)


def test_input_requires_protected_lineage_record(tmp_path,monkeypatch):
    service,lab,outcome,accepted,artifacts = ready(tmp_path,monkeypatch)
    receipt = promote(lab,outcome,accepted,artifacts)
    definition,binding = downstream(lab,outcome,receipt)
    (lab/'state'/binding.reference).unlink()
    with pytest.raises(LabValidationError):
        definition.verify_input(lab)


def test_workspace_rejects_alternate_clean_repository_with_same_commit(tmp_path,monkeypatch):
    from worker_lab import workspace
    service,lab,outcome,accepted,artifacts=ready(tmp_path,monkeypatch)
    receipt=promote(lab,outcome,accepted,artifacts)
    definition,binding=downstream(lab,outcome,receipt)
    repository=Path(receipt.to_dict()['repository'])
    admitted=service.admit_job_task(definition.plan,'B',repository,approved_by=definition.approved_by,
        approved_plan_digest=definition.plan.digest(),input_binding=binding)
    other=tmp_path/'other'
    subprocess.run(['git','clone','--no-local',str(repository),str(other)],check=True,capture_output=True)
    workspaces=tmp_path/'next';workspaces.mkdir()
    original=workspace._git
    def no_clone(arguments,*args,**kwargs):
        assert 'clone' not in arguments,'substituted input reached clone'
        return original(arguments,*args,**kwargs)
    monkeypatch.setattr(workspace,'_git',no_clone)
    with pytest.raises(LabValidationError,match='exact accepted snapshot'):
        service.prepare_workspace(admitted.identity,other,workspaces)
    assert not list(workspaces.iterdir())


def test_b_keeps_snapshot_crlf_bytes_outside_its_context_manifest(tmp_path,monkeypatch):
    from tests import test_application_service_v3 as fixtures
    original=fixtures.write_authority_fixture
    def source_with_crlf(path):
        lab,target=original(path)
        (target/'README.md').write_bytes(b'instructions\r\n')
        (target/'.git/info/attributes').write_text('README.md text eol=crlf\n',encoding='utf-8')
        subprocess.run(['git','-C',str(target),'add','--renormalize','--','README.md'],check=True,capture_output=True)
        assert not subprocess.run(['git','-C',str(target),'status','--porcelain=v1'],check=True,capture_output=True).stdout
        context_path=lab/'curricula/contexts/record-model-context/v1.json'
        context=json.loads(context_path.read_text(encoding='utf-8'))
        for item in context['files']:
            if item['path']=='README.md':
                item['digest']='sha256:'+hashlib.sha256(b'instructions\r\n').hexdigest()
        context_path.write_text(json.dumps(context),encoding='utf-8')
        return lab,target
    monkeypatch.setattr(fixtures,'write_authority_fixture',source_with_crlf)
    service,lab,outcome,accepted,artifacts=ready(tmp_path,monkeypatch)
    receipt=promote(lab,outcome,accepted,artifacts)
    definition,binding=downstream(lab,outcome,receipt,omit_readme=True)
    assert all(item.path!='README.md' for item in binding.context().files)
    repository=Path(receipt.to_dict()['repository'])
    assert (repository/'README.md').read_bytes()==b'instructions\r\n'
    admitted=service.admit_job_task(definition.plan,'B',repository,approved_by=definition.approved_by,
        approved_plan_digest=definition.plan.digest(),input_binding=binding)
    workspaces=tmp_path/'next';workspaces.mkdir()
    service.prepare_workspace(admitted.identity,repository,workspaces)
    assert (workspaces/admitted.identity/'README.md').read_bytes()==b'instructions\r\n'
