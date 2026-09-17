from __future__ import annotations

import base64
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

import pytest

from test_pi_dispatch import fixture, binding, AWF
from worker_lab.canonical import canonical_digest, canonical_json
from worker_lab.controller_task_packet import ControllerTaskPacket
from worker_lab.errors import LabValidationError
from worker_lab.integration_v3 import InvocationRecordV3, InvocationState, authorize_invocation, transition_invocation
from worker_lab.invocation_store_v3 import InvocationStoreV3
from worker_lab.operator_control import inspect_source_identity
from worker_lab.pi_protocol import build_request
from worker_lab.pi_dispatch import make_pi_dispatch_runner
from worker_lab.dispatch_client import dispatch_workspace_write
from worker_lab.pi_supervision import (SupervisedPiLauncher, set_pi_activation, minimal_pi_environment,
    _exclusive_controller, _Record)
from worker_lab.pi_worker import intended_pi_worker
from worker_lab.process_custody import CustodyState, ProcessCustodyStore
from worker_lab.provider_binding import ProviderBindingStore
from worker_lab.storage import AtomicRecordStore
from worker_lab.windows_job import OwnedWindowsProcess, process_creation_time_for_pid
from worker_lab.workspace import canonical_path_digest


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows lifetime backend')


def setup_attempt(tmp_path, *, process_factory=None, cancellation=None, budget_ms=10000, observed_binding=None, worker_config=None, user_request='Change only target.py to VALUE = 2.'):
    tmp_path = tmp_path.resolve()
    root, base = fixture.repo(tmp_path)
    fixture.git(root, 'config', 'core.autocrlf', 'false')
    fixture.git(root, 'add', '--renormalize', '.')
    fixture.git(root, 'commit', '--allow-empty', '-qm', 'explicit fixture line endings')
    base = fixture.git(root, 'rev-parse', 'HEAD')
    fixture.git(root, 'checkout', '--detach', '-q')
    payload = json.loads(fixture.request(root, base)[0])
    worker = worker_config or intended_pi_worker(context_tokens=131072)
    bound = observed_binding or binding(worker)
    state = tmp_path / 'state'
    bindings = ProviderBindingStore(state); bindings.create(bound)
    packet = ControllerTaskPacket.from_mapping(dict(schema_version='worker-lab-controller-task-packet:v2',
        context_mode='none', attempt_id='ATTEMPT-001', controller_identity='controller-1',
        user_request=user_request, exercise_id='exercise', exercise_version=1,
        starting_commit=base, authority_effect='informational-only', knowledge_evidence=[]))
    value = payload['invocation']
    _, source = inspect_source_identity()
    value.update(provider_binding_id=bound.binding_id, provider_binding_digest=bound.digest(),
        runtime_requirement_digest=bound.runtime_requirement_digest,
        controller_task_packet_digest=packet.digest(), prompt_digest=packet.digest(),
        worker_lab_source_digest=source.component_digests['worker-lab'],
        framework_source_digest=source.component_digests['autonomous-worker-framework'],
        state='PREPARED', authorized_by=None, authorized_at=None)
    value['source_state']['workspace_path_digest'] = canonical_path_digest(root)
    prepared = InvocationRecordV3.from_mapping(value)
    inv_store = InvocationStoreV3(state); inv_store.create(prepared)
    authorized = authorize_invocation(prepared, binding_store=bindings, controller_identity='controller-1', authorized_at='2026-09-17T12:00:00Z')
    inv_store.save_transition(authorized, expected_digest=prepared.digest(), binding_store=bindings)
    invocation = transition_invocation(authorized, InvocationState.DISPATCHING)
    inv_store.save_transition(invocation, expected_digest=authorized.digest())
    node = Path(shutil.which('node')).resolve()
    installation = Path(os.environ.get('ACL_PI_TEST_INSTALLATION', str(tmp_path / 'installation'))).resolve()
    agent = state / 'agent'
    options = dict(state_root=state, workspace_root=root, node=node, framework_root=AWF,
        python=Path(sys.executable).resolve(), pi_installation=installation, agent_dir=agent, cancellation=cancellation)
    if process_factory is not None: options['process_factory'] = process_factory
    launcher = SupervisedPiLauncher(**options)
    issued = time.time_ns() // 1_000_000
    request = build_request(invocation=invocation, prompt=packet.to_json(), task=payload['workspace_write'],
        worker=worker, worker_digest=canonical_digest(worker), workspace_root=str(root),
        issued_at_unix_ms=issued, deadline_unix_ms=issued + budget_ms)
    control = dict(request_digest=canonical_digest(json.loads(request)), worker_digest=canonical_digest(worker),
        binding=bound.to_dict(), python=str(options['python']), pi_installation=str(installation), agent_dir=str(agent))
    argv = (str(node), str(AWF / 'tools/pi_adapter_main.mjs'), base64.urlsafe_b64encode(canonical_json(control).encode()).decode().rstrip('='))
    return launcher, argv, request + b'\n', issued + budget_ms, worker, invocation


def enable(launcher, worker):
    set_pi_activation(launcher.state_root, enabled=True, controller_identity='controller-1', worker_digest=canonical_digest(worker))


class FixtureProcess:
    identity = 'windows-process:v1:200:1234'
    def __init__(self, argv, **kw):
        self.resumed = self.killed = self.closed = False
    def resume(self): self.resumed = True
    def poll(self): return 0
    def active_count(self): return 0
    def terminate(self): self.killed = True
    def close(self): self.closed = True


def test_disabled_creates_no_process_or_intent(tmp_path):
    def forbidden(*a, **kw): pytest.fail('disabled execution created a process')
    launcher, argv, raw, deadline, worker, invocation = setup_attempt(tmp_path, process_factory=forbidden)
    for configured in (False, True):
        if configured:
            set_pi_activation(launcher.state_root, enabled=False, controller_identity='controller-1', worker_digest=canonical_digest(worker))
        with pytest.raises(LabValidationError) as error: launcher(argv, raw, deadline)
        assert error.value.code == 'PI_EXECUTION_DISABLED'
        assert not (launcher.state_root / 'launch-intents').exists()


def test_intent_then_assigned_record_precede_resume_and_duplicate_rejects(tmp_path):
    seen = []
    class Process(FixtureProcess):
        def __init__(self, argv, **kw):
            super().__init__(argv, **kw)
            assert (launcher.state_root / 'launch-intents/INVOCATION-001.json').is_file()
            assert ProcessCustodyStore(launcher.state_root).read('INVOCATION-001').state is CustodyState.PREPARED
            seen.append(self)
        def resume(self):
            assert ProcessCustodyStore(launcher.state_root).read('INVOCATION-001').state is CustodyState.DISPATCHING
            super().resume()
    launcher, argv, raw, deadline, worker, inv = setup_attempt(tmp_path, process_factory=Process)
    enable(launcher, worker)
    assert launcher(argv, raw, deadline) == b''
    assert seen[0].resumed and seen[0].closed
    custody = ProcessCustodyStore(launcher.state_root).read(inv.invocation_id)
    assert custody.state is CustodyState.ABSENCE_VERIFIED and custody.active_workload_count == 0
    with pytest.raises(LabValidationError) as error: launcher(argv, raw, deadline)
    assert error.value.code == 'PI_ATTEMPT_ALREADY_LAUNCHED' and len(seen) == 1


@pytest.mark.parametrize('kind', ['creation', 'query', 'assignment_record', 'resume', 'deadline', 'cancel'])
def test_failure_custody_and_cleanup(tmp_path, monkeypatch, kind):
    cancelled = threading.Event()
    seen = []
    class Process(FixtureProcess):
        def __init__(self, argv, **kw):
            if kind == 'creation': raise OSError('fixture creation failure')
            super().__init__(argv, **kw); seen.append(self)
        def resume(self):
            if kind == 'resume': raise OSError('fixture resume failure')
            if kind == 'cancel': cancelled.set()
        def poll(self): return 1 if self.killed else None
        def active_count(self):
            if kind == 'query': raise OSError('fixture accounting failure')
            return 0 if self.killed else 1
    launcher, argv, raw, deadline, worker, inv = setup_attempt(tmp_path, process_factory=Process, cancellation=cancelled, budget_ms=2000)
    enable(launcher, worker)
    if kind == 'assignment_record':
        save = ProcessCustodyStore.save_transition
        def broken(self, updated, **kw):
            if updated.state is CustodyState.ASSIGNED: raise OSError('fixture durable assignment failure')
            return save(self, updated, **kw)
        monkeypatch.setattr(ProcessCustodyStore, 'save_transition', broken)
    with pytest.raises(LabValidationError) as failure: launcher(argv, raw, deadline)
    assert (launcher.state_root / 'process-custody' / (inv.invocation_id + '.json')).exists(), (failure.value.code, failure.value.summary)
    custody = ProcessCustodyStore(launcher.state_root).read(inv.invocation_id)
    assert custody.state is (CustodyState.UNCERTAIN if kind in ('creation', 'query') else CustodyState.ABSENCE_VERIFIED)
    if seen: assert seen[0].killed and seen[0].closed
    if kind in ('creation', 'query'):
        with pytest.raises(LabValidationError) as error: launcher(argv, raw, time.time_ns() // 1_000_000 + 1000)
        # Request deadline mismatch may reject even earlier; unresolved-launch test below covers restart.
        assert error.value.code in ('PI_PROTOCOL_INVALID', 'PI_LAUNCH_IDENTITY_INVALID', 'INTEGRATION_OUTCOME_UNCERTAIN')


def test_prior_unrecorded_launch_blocks_restart_and_no_replacement(tmp_path):
    launcher, argv, raw, deadline, worker, inv = setup_attempt(tmp_path, process_factory=lambda *a, **k: pytest.fail('replacement launched'))
    enable(launcher, worker)
    AtomicRecordStore(launcher.state_root).write('launch-intents/INVOCATION-OLD.json', _Record(dict(invocation_id='INVOCATION-OLD', invocation_digest=inv.identity_digest())))
    with pytest.raises(LabValidationError) as error: launcher(argv, raw, deadline)
    assert error.value.code == 'INTEGRATION_OUTCOME_UNCERTAIN'


def test_minimal_environment_and_controller_lock(tmp_path, monkeypatch):
    monkeypatch.setenv('NODE_OPTIONS', '--import=unapproved')
    monkeypatch.setenv('OPENAI_API_KEY', 'fixture-secret')
    monkeypatch.setenv('PYTHONPATH', 'unapproved')
    env = minimal_pi_environment(tmp_path / 'home', tmp_path / 'agent')
    assert not {'PATH', 'NODE_OPTIONS', 'OPENAI_API_KEY', 'PYTHONPATH', 'HTTP_PROXY'} & env.keys()
    with _exclusive_controller(tmp_path / 'state'):
        with pytest.raises(LabValidationError, match='another controller'):
            with _exclusive_controller(tmp_path / 'state'): pass


def test_real_windows_job_suspension_and_descendant_cleanup(tmp_path):
    root = tmp_path.resolve()
    marker = root / 'child.pid'
    child = 'import time; time.sleep(60)'
    code = f'import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,"-c",{child!r}]); pathlib.Path({str(marker)!r}).write_text(str(p.pid)); time.sleep(60)'
    unrelated = subprocess.Popen([sys.executable, '-c', child], creationflags=subprocess.CREATE_NO_WINDOW)
    process = None
    try:
        with open(os.devnull, 'rb') as stdin, (root / 'stdout').open('wb') as stdout, (root / 'stderr').open('wb') as stderr:
            process = OwnedWindowsProcess((sys.executable, '-c', code), cwd=root,
                environment=minimal_pi_environment(root / 'home', root / 'agent'), stdin=stdin, stdout=stdout, stderr=stderr)
            assert process.active_count() == 1 and not marker.exists()
            process.resume()
            until = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < until: time.sleep(.025)
            assert marker.exists(), (root / 'stderr').read_text()
            assert process.active_count() >= 2  # Windows may also create an owned console host.
            process.terminate()
            until = time.monotonic() + 5
            while process.active_count() and time.monotonic() < until: time.sleep(.025)
            assert process.active_count() == 0
            assert unrelated.poll() is None
    finally:
        if process: process.close()
        unrelated.terminate(); unrelated.wait(timeout=5)


@pytest.mark.skipif(not os.environ.get('ACL_PI_TEST_INSTALLATION'), reason='explicit pinned SDK installation required')
def test_installed_sdk_dispatch_under_real_windows_supervision(tmp_path):
    def http_fixture_process(argv, **kwargs):
        args = list(argv)
        args[1] = str(Path(__file__).parent / 'fixtures/pi_sdk_fixture.mjs')
        return OwnedWindowsProcess(args, **kwargs)
    launcher, argv, raw, deadline, worker, invocation = setup_attempt(tmp_path, process_factory=http_fixture_process)
    enable(launcher, worker)
    request = json.loads(raw)
    request['task']['consumer_profile']['full_validation'][0]['argv'][0] = sys.executable
    outcomes = []
    runner = make_pi_dispatch_runner(binding_store=ProviderBindingStore(launcher.state_root),
        workspace_root=launcher.workspace, framework_root=AWF, node=launcher.node, python=launcher.python,
        pi_installation=launcher.installation, agent_dir=launcher.agent_dir, launcher=launcher, outcome_sink=outcomes.append)
    result = json.loads(dispatch_workspace_write(invocation, prompt=request['prompt'], workspace_write=request['task'],
        binding_store=ProviderBindingStore(launcher.state_root), runner=runner))
    assert outcomes[0]['status'] == 'completed'
    assert result['changed_paths'] == ['target.py']
    assert launcher.last_custody.state is CustodyState.ABSENCE_VERIFIED
    assert launcher.last_custody.exit_code == 0 and launcher.last_custody.first_failure is None


@pytest.mark.parametrize('stop', ['cancel', 'timeout'])
def test_real_supervisor_stops_owned_descendants_and_preserves_unrelated(tmp_path, stop):
    cancelled = threading.Event()
    marker = tmp_path.resolve() / 'owned-child.pid'
    child = 'import time; time.sleep(60)'
    code = f'import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,"-c",{child!r}]); pathlib.Path({str(marker)!r}).write_text(str(p.pid)); time.sleep(60)'
    def owned_fixture(argv, **kwargs):
        return OwnedWindowsProcess((sys.executable, '-c', code), **kwargs)
    launcher, argv, raw, deadline, worker, invocation = setup_attempt(tmp_path, process_factory=owned_fixture,
        cancellation=cancelled, budget_ms=3000 if stop == 'timeout' else 10000)
    enable(launcher, worker)
    unrelated = subprocess.Popen([sys.executable, '-c', child], creationflags=subprocess.CREATE_NO_WINDOW)
    finished = threading.Event()
    def cancel_after_child():
        while not finished.wait(.025):
            if marker.exists():
                cancelled.set(); return
    thread = threading.Thread(target=cancel_after_child, daemon=True) if stop == 'cancel' else None
    if thread: thread.start()
    try:
        with pytest.raises(LabValidationError) as error: launcher(argv, raw, deadline)
        assert error.value.code == ('PI_CANCELLED' if stop == 'cancel' else 'PI_TIMED_OUT')
        assert marker.exists()
        assert launcher.last_custody.state is CustodyState.ABSENCE_VERIFIED
        assert launcher.last_custody.active_workload_count == 0
        assert unrelated.poll() is None
    finally:
        finished.set()
        if thread: thread.join(timeout=2)
        unrelated.terminate(); unrelated.wait(timeout=5)


def test_changed_activation_and_cancel_before_creation(tmp_path):
    cancelled = threading.Event()
    launcher, argv, raw, deadline, worker, inv = setup_attempt(tmp_path,
        process_factory=lambda *a, **k: pytest.fail('process created'), cancellation=cancelled)
    enable(launcher, worker)
    records = AtomicRecordStore(launcher.state_root)
    record = records.read('operator/pi-activation.json', lambda x: x)
    records.write('operator/pi-activation.json', _Record({**record, 'worker_digest': 'sha256:' + '0' * 64}))
    with pytest.raises(LabValidationError) as error: launcher(argv, raw, deadline)
    assert error.value.code == 'PI_EXECUTION_DISABLED'
    enable(launcher, worker)
    cancelled.set()
    with pytest.raises(LabValidationError) as error: launcher(argv, raw, deadline)
    assert error.value.code == 'PI_CANCELLED'
    assert launcher.last_custody.state is CustodyState.ABSENCE_VERIFIED
    assert launcher.last_custody.worker_identity is None and not launcher.last_custody.request_sent


def test_controller_exit_before_custody_assignment_kills_suspended_child(tmp_path):
    # Actual host crash window: child exists atomically in the job but never resumes.
    root = tmp_path.resolve()
    identity_file, marker = root / 'worker.json', root / 'must-not-run'
    worker_code = f'from pathlib import Path; Path({str(marker)!r}).write_text("ran")'
    code = f'''
import sys,json,time,os
from pathlib import Path
sys.path.insert(0, {str(Path(__file__).resolve().parents[1])!r})
from worker_lab.windows_job import OwnedWindowsProcess
from worker_lab.pi_supervision import minimal_pi_environment
root=Path({str(root)!r})
with open(os.devnull,'rb') as inp, (root/'out').open('wb') as out, (root/'err').open('wb') as err:
    child=OwnedWindowsProcess((sys.executable,'-c',{worker_code!r}),cwd=root,environment=minimal_pi_environment(root/'home',root/'agent'),stdin=inp,stdout=out,stderr=err)
    Path({str(identity_file)!r}).write_text(json.dumps(dict(pid=child.pid,identity=child.identity)))
    time.sleep(60)
'''
    controller = subprocess.Popen([sys.executable, '-c', code], creationflags=subprocess.CREATE_NO_WINDOW)
    handle = None
    try:
        until = time.monotonic() + 5
        while not identity_file.exists() and time.monotonic() < until: time.sleep(.025)
        assert identity_file.exists()
        value = json.loads(identity_file.read_text())
        from worker_lab.windows_job import _kernel32
        kernel = _kernel32()
        import ctypes
        from ctypes import wintypes
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        handle = kernel.OpenProcess(0x00100000, False, value['pid'])  # SYNCHRONIZE only
        assert handle and not marker.exists()
        controller.terminate(); controller.wait(timeout=5)
        assert kernel.WaitForSingleObject(handle, 5000) == 0
        assert not marker.exists()
    finally:
        if handle: kernel.CloseHandle(handle)
        if controller.poll() is None: controller.terminate(); controller.wait(timeout=5)


def _runtime_options(tmp_path, python=None, node=None):
    return dict(state_root=tmp_path / 'state', workspace_root=tmp_path / 'candidate',
        node=node or Path(shutil.which('node')).resolve(), framework_root=AWF,
        python=python or Path(sys.executable).resolve(),
        pi_installation=tmp_path / 'sdk', agent_dir=tmp_path / 'agent',
        process_factory=lambda *a, **k: pytest.fail('unsafe interpreter launched'))


def test_candidate_venv_startup_marker_rejected_without_execution(tmp_path):
    import venv
    from tools.pydantic_ollama_worker import BoundedFileTools
    root = tmp_path.resolve()
    candidate, marker = root / 'candidate', root / 'outside-marker'
    runtime = candidate / 'venv'
    venv.EnvBuilder(with_pip=False).create(runtime)
    relative = 'venv/Lib/site-packages/acl_regression.pth'
    files = BoundedFileTools(candidate, readable_paths=(relative,), writable_paths=(relative,))
    files.write_file(relative, 'import pathlib; pathlib.Path(' + repr(str(marker)) + ').write_text("ran")\n', 'absent')
    with pytest.raises(LabValidationError) as error:
        SupervisedPiLauncher(**_runtime_options(root, python=runtime / 'Scripts/python.exe'))
    assert error.value.code == 'PI_AUTHORITY_OVERLAP'
    assert not marker.exists() and not (root / 'state/launch-intents').exists()


@pytest.mark.parametrize('redirect', ['node', 'venv-home', 'restricted-path'])
def test_runtime_startup_locations_cannot_resolve_into_candidate(tmp_path, redirect):
    root = tmp_path.resolve()
    options = _runtime_options(root)
    candidate = options['workspace_root']; candidate.mkdir()
    runtime = root / 'runtime'; runtime.mkdir()
    executable = runtime / 'python.exe'; executable.write_bytes(b'never execute fixture')
    if redirect == 'node':
        options['node'] = candidate / 'node.exe'; options['node'].write_bytes(b'never execute fixture')
    else:
        options['python'] = executable
        if redirect == 'venv-home':
            (runtime / 'pyvenv.cfg').write_text('home = ' + str(candidate), encoding='utf-8')
        else:
            (runtime / 'python312._pth').write_text(str(candidate), encoding='utf-8')
    with pytest.raises(LabValidationError) as error:
        SupervisedPiLauncher(**options)
    assert error.value.code == 'PI_AUTHORITY_OVERLAP'
    assert not (root / 'state/launch-intents').exists()


def test_runtime_reparse_alias_is_rejected(tmp_path):
    root = tmp_path.resolve()
    candidate = root / 'candidate'; candidate.mkdir()
    alias = root / 'runtime-alias'
    # Windows junctions exercise canonical aliases without requiring symlink privilege.
    subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(candidate)], check=True, capture_output=True)
    (candidate / 'python.exe').write_bytes(b'never execute fixture')
    with pytest.raises(LabValidationError) as error:
        SupervisedPiLauncher(**_runtime_options(root, python=alias / 'python.exe'))
    assert error.value.code == 'PI_LAUNCH_PATH_INVALID'


def test_separated_venv_file_tools_skip_site_startup_and_preserve_grants(tmp_path):
    import venv
    root = tmp_path.resolve()
    candidate, marker, runtime = root / 'candidate', root / 'outside-marker', root / 'runtime'
    candidate.mkdir(); (candidate / 'target.py').write_text('VALUE = 1\n', encoding='utf-8')
    venv.EnvBuilder(with_pip=False).create(runtime)
    for startup in ('regression.pth', 'sitecustomize.py'):
        (runtime / 'Lib/site-packages' / startup).write_text(
            'import pathlib; pathlib.Path(' + repr(str(marker)) + ').write_text("ran")\n', encoding='utf-8')
    python = runtime / 'Scripts/python.exe'
    options = _runtime_options(root, python=python)
    SupervisedPiLauncher(**options)
    script = root / 'file-tools.mjs'
    script.write_text("import { createFileTools } from " + json.dumps((AWF / 'tools/pi_file_tools.mjs').as_uri()) + ";\n" +
        "const [read, write] = createFileTools(" + json.dumps(dict(python=str(python),
            grant=dict(root=str(candidate), readable_paths=['target.py'], writable_paths=['target.py']),
            maxCalls=3, timeoutMs=10000, deadlineUnixMs=int(time.time() * 1000) + 30000)) + ");\n" +
        "const current = (await read.execute('read', { path: 'target.py' })).details;\n" +
        "await write.execute('write', { path: 'target.py', content: 'VALUE = 2\\n', expected_sha256: current.sha256 });\n" +
        "try { await read.execute('denied', { path: '../outside-marker' }); process.exitCode = 1; } catch {}\n", encoding='utf-8')
    result = subprocess.run([str(options['node']), str(script)], cwd=candidate,
        env=minimal_pi_environment(root / 'home', root / 'agent'), capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert (candidate / 'target.py').read_text(encoding='utf-8') == 'VALUE = 2\n'
    assert not marker.exists()


def test_runtime_startup_redirection_after_construction_blocks_launch(tmp_path):
    launcher, argv, raw, deadline, worker, invocation = setup_attempt(tmp_path,
        process_factory=lambda *a, **k: pytest.fail('runtime substitution launched'))
    # A separate copied interpreter is not run; the changed startup file alone
    # must block before activation, durable intent, or any process construction.
    runtime = tmp_path.resolve() / 'runtime'; runtime.mkdir()
    executable = runtime / 'python.exe'; executable.write_bytes(b'never execute fixture')
    launcher.python = executable
    control = json.loads(base64.urlsafe_b64decode(argv[2] + '=' * (-len(argv[2]) % 4)))
    control['python'] = str(executable)
    argv = (*argv[:2], base64.urlsafe_b64encode(canonical_json(control).encode()).decode().rstrip('='))
    (runtime / 'pyvenv.cfg').write_text('home = ' + str(launcher.workspace), encoding='utf-8')
    with pytest.raises(LabValidationError) as error:
        launcher(argv, raw, deadline)
    assert error.value.code == 'PI_AUTHORITY_OVERLAP'
    assert not (launcher.state_root / 'launch-intents').exists()


@pytest.mark.parametrize('candidate_first', [True, False])
def test_ambiguous_duplicate_venv_home_rejected_before_launch(tmp_path, candidate_first):
    root = tmp_path.resolve()
    options = _runtime_options(root)
    candidate = options['workspace_root']; candidate.mkdir()
    runtime = root / 'runtime'; runtime.mkdir()
    options['python'] = runtime / 'python.exe'
    options['python'].write_bytes(b'never execute fixture')
    homes = [str(candidate), str(Path(sys.executable).resolve().parent)]
    if not candidate_first:
        homes.reverse()
    (runtime / 'pyvenv.cfg').write_text(''.join('home = ' + home + '\n' for home in homes), encoding='utf-8')
    with pytest.raises(LabValidationError) as error:
        SupervisedPiLauncher(**options)
    assert error.value.code == 'PI_RUNTIME_STARTUP_INVALID'
    assert not (root / 'state/launch-intents').exists()


def test_restricted_path_inline_comment_cannot_hide_candidate_redirect(tmp_path):
    root = tmp_path.resolve()
    options = _runtime_options(root)
    candidate = options['workspace_root']; candidate.mkdir()
    runtime = root / 'runtime'; runtime.mkdir()
    options['python'] = runtime / 'python.exe'
    options['python'].write_bytes(b'never execute fixture')
    (runtime / 'python312._pth').write_text(str(candidate) + ' # startup library directory\n', encoding='utf-8')
    with pytest.raises(LabValidationError) as error:
        SupervisedPiLauncher(**options)
    assert error.value.code == 'PI_AUTHORITY_OVERLAP'
    assert not (root / 'state/launch-intents').exists()


@pytest.mark.parametrize('prefix', ['# home = ', 'other_home = '])
def test_venv_redirector_home_must_be_unambiguous_first_line(tmp_path, prefix):
    root = tmp_path.resolve()
    options = _runtime_options(root)
    candidate = options['workspace_root']; candidate.mkdir()
    runtime = root / 'runtime'; runtime.mkdir()
    options['python'] = runtime / 'python.exe'
    options['python'].write_bytes(b'never execute fixture')
    (runtime / 'pyvenv.cfg').write_text(prefix + str(candidate) + '\nhome = '
        + str(Path(sys.executable).resolve().parent) + '\n', encoding='utf-8')
    with pytest.raises(LabValidationError) as error:
        SupervisedPiLauncher(**options)
    assert error.value.code == 'PI_RUNTIME_STARTUP_INVALID'
    assert not (root / 'state/launch-intents').exists()


def test_chained_venv_home_is_rejected_before_runtime_execution(tmp_path):
    root = tmp_path.resolve()
    options = _runtime_options(root)
    candidate = options['workspace_root']; candidate.mkdir()
    runtime = root / 'runtime'; runtime.mkdir()
    options['python'] = runtime / 'python.exe'
    options['python'].write_bytes(b'never execute fixture')
    chained = root / 'second-runtime'; (chained / 'Scripts').mkdir(parents=True)
    (chained / 'Scripts/python.exe').write_bytes(b'never execute fixture')
    (runtime / 'pyvenv.cfg').write_text('home = ' + str(chained / 'Scripts') + '\n', encoding='utf-8')
    (chained / 'pyvenv.cfg').write_text('home = ' + str(candidate) + '\n', encoding='utf-8')
    with pytest.raises(LabValidationError) as error:
        SupervisedPiLauncher(**options)
    assert error.value.code == 'PI_RUNTIME_STARTUP_INVALID'
    assert not (root / 'state/launch-intents').exists()
