from pathlib import Path
import json
import os
import subprocess
import sys
import threading
import time
import pytest

from tests import test_run_task as m04
from worker_lab.canonical import canonical_json, canonical_digest
from worker_lab.cli import main
from worker_lab.errors import LabValidationError
from worker_lab.pi_supervision import _Record
from worker_lab.process_custody import ProcessCustodyStore
from worker_lab.storage import AtomicRecordStore
from worker_lab.protected_validation import validator_environment, require_resolved_validations
from worker_lab.windows_job import process_creation_time_for_pid

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='existing Windows lifetime backend')
CONTROLLER = m04.fixtures.CONTROLLER
CHECKER = '''from pathlib import Path
import sys
actual = (Path(sys.argv[1]) / 'record_ledger/models.py').read_text()
print('protected content check', flush=True)
if actual != 'VALUE = 2\\n':
    print('expected VALUE = 2', file=sys.stderr, flush=True)
    sys.exit(7)
'''


def prepare(tmp_path, monkeypatch, *, content=b'VALUE = 2\n', code=CHECKER,
            approval_options=None, candidate_extra=True):
    original = m04.fixtures.write_authority_fixture
    def authority(path):
        lab,target=original(path)
        checker=lab/'checks/content.py';checker.parent.mkdir();checker.write_text(code,encoding='utf-8')
        catalog_path=lab/'curricula/catalogs/worker-lab-v1.json'
        catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
        for test in catalog['tests']:
            test['command']=[str(Path(sys.executable).resolve()),'-I','-B',str(checker.resolve()),'{candidate}']
        catalog_path.write_text(canonical_json(catalog),encoding='utf-8')
        return lab,target
    monkeypatch.setattr(m04.fixtures,'write_authority_fixture',authority)
    service,lab,root,task,_=m04.prepare(tmp_path,monkeypatch)
    if approval_options is not None:
        service.approve_task_execution(task, CONTROLLER, protected_files=[lab/'checks/content.py'],
            acknowledge_unsandboxed=True, **approval_options)
    def factory(**options):
        def runner(payload):
            from worker_lab.integration_v3 import InvocationRecordV3
            invocation=InvocationRecordV3.from_mapping(json.loads(payload)['invocation'])
            workspace=options['workspace_root']
            (workspace/'record_ledger/models.py').write_bytes(content)
            # A candidate-authored replacement must not replace the protected checker.
            if candidate_extra:
                (workspace/'content.py').write_text('print("forged pass")')
            m04.fixtures._success_custody(invocation,workspace,ProcessCustodyStore(options['state_root']))
            options['outcome_sink']({'status':'completed','stop_reason':'stop','summary':'fixture edit',
                'remaining_work':None,'usage':None})
        return runner
    outcome=m04.run_worker(service, task,runner_factory=factory)
    return service,lab,root,outcome,lab/'checks/content.py'


def approve(service,outcome,checker,**options):
    return service.approve_local_validation(outcome.to_dict()['attempt_id'],outcome.digest(),CONTROLLER,
        protected_files=[checker],acknowledge_unsandboxed=True,**options)


def validate(service,outcome,**options):
    return service.validate_task(outcome.to_dict()['attempt_id'],outcome.digest(),CONTROLLER,
        'VALIDATION-test',**options)


@pytest.mark.parametrize('content,expected', [(b'VALUE = 2\n','passed'),(b'VALUE = 3\n','failed')])
def test_same_protected_check_judges_correct_and_broken_candidates(tmp_path,monkeypatch,content,expected):
    service,lab,root,outcome,checker=prepare(tmp_path,monkeypatch,content=content)
    approval=approve(service,outcome,checker)
    assert approval.to_dict()['resource_exposure']=='unsandboxed-host-code-execution'
    report=validate(service,outcome)
    value=report.to_dict()
    assert value['status']==expected, value
    assert value['accepted'] is False and value['all_validators_absent'] is True
    first=value['checks'][0]
    assert first['validator_identity'].startswith('windows-process:v1:')
    assert first['candidate_digest']==outcome.to_dict()['candidate']['content_digest']
    assert first['custody']['state']=='ABSENCE_VERIFIED'
    assert first['exit_code']==(0 if expected=='passed' else 7)
    assert b'protected content check' in (lab/'state'/first['stdout']).read_bytes()
    if expected=='failed':
        assert b'expected VALUE = 2' in (lab/'state'/first['stderr']).read_bytes()
    saved=json.loads((lab/'state/validation-results/VALIDATION-test.json').read_text())
    assert saved==value
    assert validate(service,outcome,process_factory=lambda *a,**kw:pytest.fail('replay launched')).digest()==report.digest()


def test_no_implicit_local_execution(tmp_path,monkeypatch):
    service,lab,root,outcome,checker=prepare(tmp_path,monkeypatch)
    with pytest.raises(LabValidationError):
        validate(service,outcome,process_factory=lambda *a,**kw:pytest.fail('unapproved launch'))
    with pytest.raises(LabValidationError,match='unsandboxed host code'):
        service.approve_local_validation(outcome.to_dict()['attempt_id'],outcome.digest(),CONTROLLER,
            protected_files=[checker])
    assert not (lab/'state/validation-intents').exists()


@pytest.mark.parametrize('changed', ['candidate','checker','catalog','worker'])
def test_changed_identity_or_active_worker_launches_zero_checks(tmp_path,monkeypatch,changed):
    service,lab,root,outcome,checker=prepare(tmp_path,monkeypatch)
    approve(service,outcome,checker)
    value=outcome.to_dict()
    if changed=='candidate':
        (Path(value['workspace'])/'record_ledger/models.py').write_bytes(b'changed')
    elif changed=='checker':
        checker.write_text('print("forged pass")')
    elif changed=='catalog':
        path=lab/'curricula/catalogs/worker-lab-v1.json'
        catalog=json.loads(path.read_text());catalog['tests'][0]['command'][-1]='changed'
        path.write_text(canonical_json(catalog))
    else:
        custody=value['custody'];custody.update(state='DISPATCHING',exit_code=None,active_workload_count=None,
            absence_evidence_digest=None,absence_verified_at=None)
        AtomicRecordStore(lab/'state').write(f"process-custody/{value['invocation_id']}.json",_Record(custody))
    with pytest.raises(LabValidationError):
        validate(service,outcome,process_factory=lambda *a,**kw:pytest.fail('invalid candidate launched'))
    assert not (lab/'state/validation-intents').exists()


@pytest.mark.parametrize('stop', ['timeout','cancel'])
def test_real_validator_child_cleanup_and_unrelated_survives(tmp_path,monkeypatch,stop):
    code='''from pathlib import Path
import subprocess,sys,time
child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
(Path(__file__).parent/'child.pid').write_text(str(child.pid))
print('validator started',flush=True)
time.sleep(60)
'''
    service,lab,root,outcome,checker=prepare(tmp_path,monkeypatch,code=code)
    approve(service,outcome,checker,timeout_seconds=1 if stop=='timeout' else 10)
    cancel,finished=threading.Event(),threading.Event()
    marker=checker.parent/'child.pid'
    def request_cancel():
        while not finished.wait(.025):
            if marker.exists():
                cancel.set(); return
    thread=threading.Thread(target=request_cancel,daemon=True) if stop=='cancel' else None
    unrelated=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        if thread:thread.start()
        value=validate(service,outcome,cancellation=cancel).to_dict()
        assert value['status']=='failed' and value['all_validators_absent'] is True,value
        assert value['checks'][0]['failure']==('VALIDATION_TIMED_OUT' if stop=='timeout' else 'VALIDATION_CANCELLED')
        assert marker.exists()
        assert process_creation_time_for_pid(int(marker.read_text())) is None
        assert unrelated.poll() is None
    finally:
        finished.set()
        if thread:thread.join(timeout=2)
        unrelated.terminate();unrelated.wait(timeout=5)



def test_absolute_deadline_blocks_validator_creation_and_preserves_absence(tmp_path, monkeypatch):
    from worker_lab.protected_validation import validate_task

    service, lab, root, outcome, checker = prepare(tmp_path, monkeypatch)
    approve(service, outcome, checker)
    # Exercise the internal deadline seam. The public service does not accept
    # caller-chosen reservation deadlines; job deadlines come from the job gate.
    value = validate_task(service.data_root, attempt_id=outcome.to_dict()['attempt_id'],
        expected_outcome_digest=outcome.digest(), controller_identity=CONTROLLER,
        validation_id='VALIDATION-test', clock=service._clock, absolute_deadline_unix_ms=1,
        process_factory=lambda *a, **kw: pytest.fail('expired deadline launched validator')).to_dict()
    assert value['status'] == 'failed'
    assert value['all_validators_absent'] is True
    assert value['checks'][0]['failure'] == 'JOB_WALL_BUDGET_EXHAUSTED'
    assert value['checks'][0]['custody']['state'] == 'ABSENCE_VERIFIED'
    assert value['checks'][0]['validator_identity'] is None


def test_validator_candidate_mutation_is_not_a_pass(tmp_path,monkeypatch):
    code="from pathlib import Path\nimport sys\n(Path(sys.argv[1])/'record_ledger/models.py').write_text('changed by validator')\n"
    service,lab,root,outcome,checker=prepare(tmp_path,monkeypatch,code=code)
    approve(service,outcome,checker)
    value=validate(service,outcome).to_dict()
    assert value['status']=='failed' and value['error']['code']=='VALIDATION_CANDIDATE_DRIFT'
    assert len(value['checks'])==1
    assert value['all_validators_absent'] is True


def test_uncertain_creation_blocks_another_validation_and_worker_launch(tmp_path,monkeypatch):
    service,lab,root,outcome,checker=prepare(tmp_path,monkeypatch)
    approve(service,outcome,checker)
    def uncertain(*args,**kwargs): raise OSError('fixture creation uncertainty')
    value=validate(service,outcome,process_factory=uncertain).to_dict()
    assert value['status']=='uncertain' and value['all_validators_absent'] is False
    with pytest.raises(LabValidationError,match='proof of cleanup'):
        require_resolved_validations(AtomicRecordStore(lab/'state'))
    with pytest.raises(LabValidationError):
        service.validate_task(outcome.to_dict()['attempt_id'],outcome.digest(),CONTROLLER,
            'VALIDATION-other',process_factory=lambda *a,**kw:pytest.fail('replacement validator launched'))


def test_minimal_environment_has_no_ambient_secrets_or_injection(tmp_path,monkeypatch):
    for key in ('PATH','PYTHONPATH','OPENAI_API_KEY','HTTP_PROXY','NODE_OPTIONS'):
        monkeypatch.setenv(key,'UNRELATED_SECRET')
    environment=validator_environment(tmp_path)
    assert not any(key in environment for key in ('PATH','PYTHONPATH','OPENAI_API_KEY','HTTP_PROXY','NODE_OPTIONS'))
    assert environment['PYTEST_DISABLE_PLUGIN_AUTOLOAD']=='1'
    assert environment['TMP'].startswith(str(tmp_path))


def test_cli_requires_explicit_acknowledgement_and_reports_no_acceptance(tmp_path,monkeypatch,capsys):
    service,lab,root,outcome,checker=prepare(tmp_path,monkeypatch)
    common=[outcome.to_dict()['attempt_id'],'--expected-outcome-digest',outcome.digest(),'--controller',CONTROLLER]
    args=['--root',str(lab),'approve-validation',*common,'--protected-file',str(checker)]
    assert main(args)==2
    assert 'VALIDATION_APPROVAL_REQUIRED' in capsys.readouterr().err
    assert main([*args,'--acknowledge-unsandboxed-host-code-execution'])==0
    approval=json.loads(capsys.readouterr().out)
    assert approval['mode']=='operator-approved-local-test:v1'
    assert main(['--root',str(lab),'validate-task',*common,'--validation-id','VALIDATION-cli'])==0
    value=json.loads(capsys.readouterr().out)
    assert value['status']=='passed' and value['accepted'] is False

@pytest.mark.parametrize('failure', ['output', 'input_drift', 'pre_cancel'])
def test_additional_stop_boundaries(tmp_path,monkeypatch,failure):
    code = "print('x'*4096,flush=True)\n" if failure == 'output' else (
        "from pathlib import Path\nPath(__file__).write_text('changed judging bytes')\n" if failure == 'input_drift' else CHECKER)
    service,lab,root,outcome,checker=prepare(tmp_path,monkeypatch,code=code)
    approve(service,outcome,checker,output_limit_bytes=1024)
    cancel=threading.Event()
    options={}
    if failure=='pre_cancel':
        cancel.set()
        options=dict(cancellation=cancel,process_factory=lambda *a,**kw:pytest.fail('cancelled launch'))
    value=validate(service,outcome,**options).to_dict()
    assert value['status']=='failed' and value['all_validators_absent'] is True,value
    expected={'output':'VALIDATION_OUTPUT_LIMIT','input_drift':'VALIDATION_INPUT_DRIFT','pre_cancel':'VALIDATION_CANCELLED'}[failure]
    assert (value['error']['code'] if failure=='input_drift' else value['checks'][0]['failure'])==expected
    require_resolved_validations(AtomicRecordStore(lab/'state'))


def test_corrupt_cleanup_proof_blocks_replay(tmp_path,monkeypatch):
    service,lab,root,outcome,checker=prepare(tmp_path,monkeypatch)
    approve(service,outcome,checker)
    value=validate(service,outcome).to_dict()
    first=value['checks'][0]
    path=lab/'state'/Path(first['stdout']).parent/'result.json'
    saved=json.loads(path.read_text(encoding='utf-8'));saved['custody']['active_workload_count']=1
    path.write_text(canonical_json(saved),encoding='utf-8')
    with pytest.raises(LabValidationError,match='cleanup records disagree'):
        validate(service,outcome,process_factory=lambda *a,**kw:pytest.fail('corrupt replay launched'))


def test_unresolved_validator_blocks_new_worker(tmp_path,monkeypatch):
    service,lab,root,outcome,checker=prepare(tmp_path,monkeypatch)
    approve(service,outcome,checker)
    def uncertain(*args,**kwargs): raise OSError('fixture creation uncertainty')
    validate(service,outcome,process_factory=uncertain)
    original=m04.InvocationStoreV3(lab/'state').read(outcome.to_dict()['invocation_id'])
    next_id=service.create_attempt('record-model',1,tmp_path/'target').to_dict()['identity']
    service.prepare_workspace(next_id,tmp_path/'target',root)
    packet=m04.fixtures.build_controller_task_packet(m04.AttemptStore(lab/'state').read(next_id),
        controller_identity=CONTROLLER,user_request='Fresh explicit attempt',kc_search_response=m04.fixtures.kc_response())
    prepared=service.prepare_invocation(next_id,root,packet.to_json(),logical_target_id='target:record-model',
        provider_binding_id=original.provider_binding_id,provider_binding_digest=original.provider_binding_digest).to_dict()
    service.authorize_invocation(prepared['identity'],prepared['immutable_identity_digest'],CONTROLLER)
    descriptor=json.loads((tmp_path/'task.json').read_text(encoding='utf-8'))
    descriptor.update(invocation_id=prepared['identity'],expected_identity_digest=prepared['immutable_identity_digest'])
    next_file=tmp_path/'next.json';next_file.write_text(canonical_json(descriptor),encoding='utf-8')
    value=m04.run_worker(service, next_file,runner_factory=lambda **kw:pytest.fail('replacement worker launched')).to_dict()
    assert value['status']=='blocked' and value['error']['code']=='VALIDATION_UNCERTAIN'
    assert value['stop_state']=='not_started'
