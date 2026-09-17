from pathlib import Path
import json
import os
import shutil
import sys
import zipfile
import pytest

from tests import test_application_service_v3 as fixtures
from test_pi_dispatch import binding, AWF
from worker_lab.attempt_store import AttemptStore
from worker_lab.canonical import canonical_json, canonical_digest
from worker_lab.cli import main
from worker_lab.errors import LabValidationError
from worker_lab.integration_v3 import InvocationState
from worker_lab.invocation_store_v3 import InvocationStoreV3
from worker_lab.models import AttemptState
from worker_lab.pi_worker import intended_pi_worker
from worker_lab.pi_supervision import set_pi_activation, _Record
from worker_lab.provider_binding import ProviderBindingStore
from worker_lab.storage import AtomicRecordStore
from worker_lab.process_custody import ProcessCustodyStore

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows controller lock')


def run_worker(service, task_file, **options):
    """Exercise M04's internal observation primitive independently of M06 policy."""
    from worker_lab.run_task import run_task
    return run_task(service.data_root, task_file, clock=service._clock, **options)


def prepare(tmp_path, monkeypatch, *, enabled=True):
    def pi_binding(lab, binding_id):
        value = binding(intended_pi_worker(context_tokens=131072))
        ProviderBindingStore(lab / 'state').create(value)
        return value
    monkeypatch.setattr(fixtures, '_binding', pi_binding)
    from worker_lab.controller_task_packet import build_controller_task_packet
    def no_context_packet(attempt, **kwargs):
        kwargs.pop('kc_search_response', None)
        return build_controller_task_packet(attempt, no_context=True, **kwargs)
    monkeypatch.setattr(fixtures, 'build_controller_task_packet', no_context_packet)
    service, lab, workspace_root, bound, packet, prepared = fixtures._prepare(tmp_path)
    service.authorize_invocation(prepared['identity'], prepared['immutable_identity_digest'], fixtures.CONTROLLER)
    state = lab / 'state'
    settings = dict(schema_version='acl-pi-host:v1', node=str(Path(shutil.which('node')).resolve()),
        python=str(Path(sys.executable).resolve()), framework_root=str(AWF),
        pi_installation=str((tmp_path / 'installation').resolve()), agent_dir=str((state / 'agent').resolve()))
    AtomicRecordStore(state).write('operator/pi-host.json', _Record(settings))
    if enabled:
        set_pi_activation(state, enabled=True, controller_identity=fixtures.CONTROLLER,
            worker_digest=canonical_digest(intended_pi_worker(context_tokens=131072)))
    task = dict(schema_version='worker-lab-run-task:v1', invocation_id=prepared['identity'],
        expected_identity_digest=prepared['immutable_identity_digest'], controller_identity=fixtures.CONTROLLER,
        workspace_root=str(workspace_root.resolve()))
    path = tmp_path / 'task.json'; path.write_text(canonical_json(task), encoding='utf-8')
    return service, lab, workspace_root, path, prepared


def factory(scenario, calls):
    def create(**options):
        def runner(payload):
            from worker_lab.integration_v3 import InvocationRecordV3
            invocation = InvocationRecordV3.from_mapping(json.loads(payload)['invocation'])
            calls.append(invocation.invocation_id)
            workspace = options['workspace_root']
            (workspace / 'record_ledger/models.py').write_text('VALUE = 2\n')
            (workspace / 'failed-note.txt').write_bytes(b'diagnostic untracked bytes\n')
            if scenario != 'uncertain':
                fixtures._success_custody(invocation, workspace, ProcessCustodyStore(options['state_root']))
            if scenario in {'cancelled', 'timed_out', 'truncated', 'provider_error', 'uncertain'}:
                code = {'cancelled':'PI_CANCELLED', 'timed_out':'PI_TIMED_OUT', 'truncated':'PI_PROTOCOL_INVALID',
                        'provider_error':'PROVIDER_ERROR', 'uncertain':'INTEGRATION_OUTCOME_UNCERTAIN'}[scenario]
                raise LabValidationError(code, 'fixture failure after dirty edit')
            status = scenario if scenario in {'needs_continuation','blocked','protocol_error','failed'} else 'completed'
            options['outcome_sink']({'status': status, 'stop_reason':'stop', 'summary':'fixture worker outcome',
                'remaining_work': None if status == 'completed' else 'work remains',
                'usage': {'input_tokens':None, 'output_tokens':None, 'requests':1, 'tool_calls':1}})
            if status != 'completed':
                raise LabValidationError('PI_WORKER_INCOMPLETE', 'incomplete fixture claim')
            return fixtures._response(payload, invocation)
        return runner
    return create


@pytest.mark.parametrize('scenario,expected', [('success','completed_claim'), ('provider_error','provider_failed'),
    ('truncated','protocol_error'), ('timed_out','timed_out'), ('cancelled','cancelled'), ('uncertain','uncertain'),
    ('needs_continuation','needs_continuation'), ('blocked','blocked'), ('protocol_error','protocol_error'), ('failed','provider_failed')])
def test_all_outcomes_are_durable_and_never_relaunch(tmp_path, monkeypatch, scenario, expected):
    service, lab, root, task, prepared = prepare(tmp_path, monkeypatch)
    calls=[]
    outcome = run_worker(service, task, runner_factory=factory(scenario, calls))
    value = outcome.to_dict()
    assert value['status'] == expected, value
    assert value['accepted'] is False
    assert value['acceptance'] == ('pending_independent_acceptance' if expected == 'completed_claim' else 'not_accepted')
    assert len(calls) == 1
    attempt = AttemptStore(lab/'state').read(value['attempt_id'])
    invocation = InvocationStoreV3(lab/'state').read(value['invocation_id'])
    assert attempt.state is AttemptState.OUTCOME_RECORDED
    assert attempt.candidate_digest is None
    assert invocation.state is InvocationState.OUTCOME_RECORDED
    assert invocation.result_digest == outcome.digest()
    if expected == 'uncertain':
        assert value['candidate'] is None
        assert value['stop_state'] == 'uncertain'
    else:
        with zipfile.ZipFile(lab/'state'/value['candidate']['archive']) as archive:
            assert archive.read('failed-note.txt') == b'diagnostic untracked bytes\n'
        assert b'VALUE = 2' in (lab/'state'/value['candidate']['diff']).read_bytes()
        assert value['candidate']['accepted_base'] is False
    assert run_worker(service, task, runner_factory=lambda **kw: pytest.fail('terminal replay launched')).digest() == outcome.digest()
    assert not (lab/'state/results').exists()


def test_disabled_records_block_and_launches_nothing(tmp_path, monkeypatch):
    service, lab, root, task, _ = prepare(tmp_path, monkeypatch, enabled=False)
    value = run_worker(service, task, runner_factory=lambda **kw: pytest.fail('disabled launch')).to_dict()
    assert value['status'] == 'blocked'
    assert value['stop_state'] == 'not_started'
    assert value['error']['code'] == 'PI_EXECUTION_DISABLED'
    assert not (lab/'state/launch-intents').exists()


def test_restart_without_stop_proof_records_uncertainty_without_clean_workspace(tmp_path, monkeypatch):
    service, lab, root, task, prepared = prepare(tmp_path, monkeypatch)
    invocation = InvocationStoreV3(lab/'state').read(prepared['identity'])
    path = f'run-task-intents/{invocation.attempt_id}.json'
    AtomicRecordStore(lab/'state').write(path, _Record({'task_file_digest':canonical_digest(json.loads(task.read_text())),
        'invocation_id':invocation.invocation_id}))
    (root/invocation.attempt_id/'record_ledger/models.py').write_text('dirty interrupted bytes')
    value=run_worker(service, task, runner_factory=lambda **kw: pytest.fail('restart launched')).to_dict()
    assert value['status'] == 'uncertain'
    assert value['stop_state'] == 'uncertain'
    assert value['candidate'] is None
    assert AttemptStore(lab/'state').read(invocation.attempt_id).state is AttemptState.OUTCOME_RECORDED


def test_durable_outcome_repairs_only_lifecycle_after_write_interruption(tmp_path, monkeypatch):
    service, lab, root, task, _ = prepare(tmp_path, monkeypatch)
    original = AttemptStore.save_transition
    def interrupt(self, updated):
        if updated.state is AttemptState.OUTCOME_RECORDED:
            raise LabValidationError('STORAGE_WRITE_FAILED', 'fixture disk failure after outcome persisted')
        return original(self, updated)
    monkeypatch.setattr(AttemptStore, 'save_transition', interrupt)
    with pytest.raises(LabValidationError, match='fixture disk failure'):
        run_worker(service, task, runner_factory=factory('success', []))
    monkeypatch.setattr(AttemptStore, 'save_transition', original)
    value=run_worker(service, task, runner_factory=lambda **kw: pytest.fail('bookkeeping replay launched')).to_dict()
    assert AttemptStore(lab/'state').read(value['attempt_id']).state is AttemptState.OUTCOME_RECORDED
    assert value['status'] == 'completed_claim'


def test_cli_returns_record_without_acceptance_and_rejects_changed_identity(tmp_path, monkeypatch, capsys):
    service, lab, root, task, _ = prepare(tmp_path, monkeypatch, enabled=False)
    assert main(['--root',str(lab),'run-task',str(task),'--candidate-archive-limit-bytes','0']) == 0
    value=json.loads(capsys.readouterr().out)
    assert value['status']=='blocked' and value['accepted'] is False
    assert value['worker_outcome'] is None
    assert value['error']['code'] == 'TASK_EXECUTION_APPROVAL_REQUIRED'
    assert not (lab/'state/run-task-intents').exists()
    descriptor=json.loads(task.read_text()); descriptor['controller_identity']='wrong-controller'
    task.write_text(canonical_json(descriptor))
    assert main(['--root',str(lab),'run-task',str(task)]) == 2
    assert 'RUN_TASK_IDENTITY_MISMATCH' in capsys.readouterr().err



@pytest.mark.skipif(not os.environ.get('ACL_PI_TEST_INSTALLATION'), reason='explicit installed SDK required')
@pytest.mark.parametrize('scenario,expected', [('success','completed_claim'), ('truncated','protocol_error'), ('provider_error','provider_failed'), ('interrupted','interrupted')])
def test_real_supervisor_and_installed_sdk_stop_before_any_validator(tmp_path, monkeypatch, scenario, expected):
    from worker_lab.pi_supervision import SupervisedPiLauncher
    from worker_lab.pi_dispatch import make_pi_dispatch_runner
    from worker_lab.windows_job import OwnedWindowsProcess
    from tools import code_task
    service, lab, root, task, _ = prepare(tmp_path, monkeypatch)
    def no_validation(*args, **kwargs):
        pytest.fail('M04 launched deferred validation')
    monkeypatch.setattr(code_task, '_run_validation', no_validation)
    def real_factory(**options):
        sink = options.pop('outcome_sink')
        options['pi_installation'] = Path(os.environ['ACL_PI_TEST_INSTALLATION']).resolve()
        def process(argv, **kwargs):
            if scenario == 'truncated':
                return OwnedWindowsProcess([sys.executable, '-c', 'import sys; sys.stdout.write("{\\\"partial\\\":")'], **kwargs)
            args=list(argv)
            args[1]=str(Path(__file__).parent/'fixtures/pi_sdk_fixture.mjs')
            args.extend(['success' if scenario == 'interrupted' else scenario,'record_ledger/models.py'])
            return OwnedWindowsProcess(args, **kwargs)
        launcher=SupervisedPiLauncher(**options, process_factory=process)
        return make_pi_dispatch_runner(binding_store=ProviderBindingStore(options['state_root']),
            **{key:options[key] for key in ('workspace_root','node','framework_root','python','pi_installation','agent_dir')},
            launcher=launcher, outcome_sink=sink)
    if scenario == 'interrupted':
        original_record = AttemptStore.record_outcome
        def fail_record(*args):
            raise LabValidationError('STORAGE_WRITE_FAILED', 'fixture crash after raw claim')
        monkeypatch.setattr(AttemptStore, 'record_outcome', fail_record)
        with pytest.raises(LabValidationError, match='fixture crash'):
            run_worker(service, task, runner_factory=real_factory)
        monkeypatch.setattr(AttemptStore, 'record_outcome', original_record)
        value=run_worker(service, task, runner_factory=lambda **kw: pytest.fail('interrupted attempt relaunched')).to_dict()
        assert value['worker_result']['status']=='completed'
        assert value['usage']['requests']==4
    else:
        value=run_worker(service, task, runner_factory=real_factory).to_dict()
    assert value['status']==expected, json.dumps(value, indent=2)
    assert value['stop_state']=='absence_verified'
    if scenario != 'success':
        assert value['accepted'] is False
        assert value['candidate'] is not None
        return
    assert value['usage']['requests']==4
    assert value['custody']['active_workload_count']==0
    assert value['worker_result']['stop_reason']=='stop'
    assert 'framework_response' not in value['artifacts']
    assert (lab/'state'/value['artifacts']['stdout.jsonl']).read_bytes().endswith(b'\n')
    assert (root/value['attempt_id']/'record_ledger/models.py').read_bytes()==b'VALUE = 2\n'


def test_outcome_record_cannot_be_rewritten_or_fabricated_by_transition(tmp_path, monkeypatch):
    service, lab, root, task, prepared = prepare(tmp_path, monkeypatch)
    invocation=InvocationStoreV3(lab/'state').read(prepared['identity'])
    with pytest.raises(LabValidationError, match='use run-task'):
        service.transition_attempt(invocation.attempt_id, 'OUTCOME_RECORDED', cleanup_outcome='invented')
    first=run_worker(service, task, runner_factory=factory('cancelled', []))
    from worker_lab.worker_outcome import WorkerOutcome
    changed=first.to_dict(); changed['error']['message']='rewrite'
    with pytest.raises(LabValidationError):
        AttemptStore(lab/'state').record_outcome(WorkerOutcome.from_mapping(changed))
    assert AttemptStore(lab/'state').read_outcome(invocation.attempt_id).digest()==first.digest()


def test_unresolved_prior_task_blocks_new_attempt(tmp_path, monkeypatch):
    service, lab, root, task, _ = prepare(tmp_path, monkeypatch)
    prior=run_worker(service, task, runner_factory=factory('uncertain', [])).to_dict()
    original=InvocationStoreV3(lab/'state').read(prior['invocation_id'])
    next_id=service.create_attempt('record-model',1,tmp_path/'target').to_dict()['identity']
    service.prepare_workspace(next_id,tmp_path/'target',root)
    packet=fixtures.build_controller_task_packet(AttemptStore(lab/'state').read(next_id),
        controller_identity=fixtures.CONTROLLER,user_request='Fresh explicitly requested attempt',
        kc_search_response=fixtures.kc_response())
    prepared=service.prepare_invocation(next_id,root,packet.to_json(),logical_target_id='target:record-model',
        provider_binding_id=original.provider_binding_id,provider_binding_digest=original.provider_binding_digest).to_dict()
    service.authorize_invocation(prepared['identity'],prepared['immutable_identity_digest'],fixtures.CONTROLLER)
    descriptor=json.loads(task.read_text()); descriptor.update(invocation_id=prepared['identity'],
        expected_identity_digest=prepared['immutable_identity_digest'])
    next_file=tmp_path/'next.json'; next_file.write_text(canonical_json(descriptor))
    value=run_worker(service, next_file,runner_factory=lambda **kw: pytest.fail('uncertain prior launched replacement')).to_dict()
    assert value['status']=='blocked'
    assert value['error']['code']=='RUN_TASK_PRIOR_UNCERTAIN'
    assert value['stop_state']=='not_started'


@pytest.mark.parametrize('substitute', [False, True])
def test_normal_cli_process_loads_only_explicit_framework(tmp_path, substitute):
    import subprocess
    worker_lab = Path(__file__).resolve().parents[1]
    code = '''
import sys, types
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from worker_lab.pi_dispatch import make_pi_dispatch_runner
from worker_lab.provider_binding import ProviderBindingStore
from worker_lab.errors import LabValidationError
root, framework = Path(sys.argv[2]), Path(sys.argv[3])
assert str(framework) not in sys.path
if sys.argv[4] == 'True':
    module = types.ModuleType('tools'); module.__file__ = str(root/'hostile.py'); sys.modules['tools']=module
try:
    runner = make_pi_dispatch_runner(binding_store=ProviderBindingStore(root/'state'),
        workspace_root=root/'workspace', framework_root=framework, node=root/'node.exe',
        python=Path(sys.executable), pi_installation=root/'sdk', agent_dir=root/'agent',
        launcher=lambda *a: None, outcome_sink=lambda x: None)
    assert sys.argv[4] == 'False' and callable(runner)
except LabValidationError as exc:
    assert sys.argv[4] == 'True' and exc.code == 'PI_FRAMEWORK_IMPORT_MISMATCH'
'''
    result=subprocess.run([sys.executable,'-I','-c',code,str(worker_lab),str(tmp_path),str(AWF),str(substitute)],
        capture_output=True,text=True,timeout=15)
    assert result.returncode==0, result.stderr


def test_corrupt_outcome_does_not_relaunch(tmp_path, monkeypatch):
    service,lab,root,task,_=prepare(tmp_path,monkeypatch,enabled=False)
    value=run_worker(service, task).to_dict()
    path=lab/'state/worker-outcomes'/f"{value['attempt_id']}.json"
    value['status']=[]
    path.write_text(canonical_json(value))
    with pytest.raises(LabValidationError):
        run_worker(service, task,runner_factory=lambda **kw: pytest.fail('corrupt record launched'))
