"""One explicitly enabled Pi workload, using existing Windows custody records.

Local activation and process evidence live outside worker grants. This module
does not accept a task, execute candidate tests, or normalize M04 task outcomes.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from .canonical import canonical_digest
from .errors import LabValidationError
from .integration_v3 import InvocationRecordV3
from .invocation_store_v3 import InvocationStoreV3
from .operator_control import inspect_source_identity, validate_controller_identity
from .pi_binding import validate_pi_binding
from .pi_dispatch import make_pi_dispatch_runner
from .pi_protocol import parse_request, MAX_FRAME_BYTES
from .process_custody import (PROCESS_CUSTODY_SCHEMA, CustodyState, ProcessCustodyRecord,
    ProcessCustodyStore, transition_custody)
from .provider_binding import ProviderBindingStore
from .storage import AtomicRecordStore
from .windows_job import (OwnedWindowsProcess, WINDOWS_JOB_BACKEND_ID, WindowsJobCustodyBackend,
    process_creation_time_for_pid, windows_process_identity,
    inspect_launch_workspace)


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


@dataclass(frozen=True)
class _Record:
    value: dict

    def to_dict(self):
        return self.value


def set_pi_activation(state_root: Path, *, enabled: bool, controller_identity: str, worker_digest: str):
    """Explicit operator action, never called as a side effect of dispatch."""
    if type(enabled) is not bool:
        raise LabValidationError('PI_ACTIVATION_INVALID', 'enabled must be a boolean')
    controller = validate_controller_identity(controller_identity)
    from .pi_worker import load_pi_worker
    from .pi_binding import CONFIG_PATH
    load_pi_worker(CONFIG_PATH, expected_digest=worker_digest)
    _, report = inspect_source_identity()
    value = dict(schema_version='acl-pi-activation:v1', enabled=enabled,
        controller_identity=controller, worker_digest=worker_digest,
        source_manifest_digest=report.manifest_digest, approved_at=now())
    AtomicRecordStore(state_root).write('operator/pi-activation.json', _Record(value))
    return value


def require_activation(state_root, *, worker_digest, controller):
    try:
        value = AtomicRecordStore(state_root).read('operator/pi-activation.json', lambda x: x)
    except LabValidationError as exc:
        raise LabValidationError('PI_EXECUTION_DISABLED', 'explicit local Pi activation is required') from exc
    _, report = inspect_source_identity()
    if not isinstance(value, dict) or set(value) != {'schema_version', 'enabled', 'controller_identity',
            'worker_digest', 'source_manifest_digest', 'approved_at'} or value != {
            **value, 'schema_version': 'acl-pi-activation:v1', 'enabled': True,
            'controller_identity': controller, 'worker_digest': worker_digest,
            'source_manifest_digest': report.manifest_digest} or value.get('enabled') is not True:
        raise LabValidationError('PI_EXECUTION_DISABLED', 'activation is disabled or its approved identity changed')
    return value


def minimal_pi_environment(home: Path, agent_dir: Path):
    """No PATH, credentials, proxy, Node injection or inherited Python settings."""
    temporary = home / 'tmp'
    temporary.mkdir(parents=True, exist_ok=True)
    environment = {key: os.environ[key] for key in ('SystemRoot', 'WINDIR') if key in os.environ}
    environment.update(HOME=str(home), USERPROFILE=str(home), APPDATA=str(home / 'appdata'),
        LOCALAPPDATA=str(home / 'local'), TEMP=str(temporary), TMP=str(temporary),
        PI_CODING_AGENT_DIR=str(agent_dir), PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1',
        CI='1', NO_COLOR='1')
    return environment


@contextmanager
def _exclusive_controller(state_root, lock_name="pi-controller.lock"):
    import msvcrt
    store = AtomicRecordStore(state_root)
    # Use the same path/reparse protections as the existing stores.
    store._ensure_root_for_write()
    path = store._target(lock_name)
    handle = path.open('a+b')
    acquired = False
    try:
        if path.stat().st_size == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            acquired = True
        except OSError as exc:
            raise LabValidationError('PI_WORKER_ACTIVE', 'another controller owns the attempt lock') from exc
        yield
    finally:
        if acquired:
            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        handle.close()


def _require_resolved_launches(records, custody_store):
    for path in records.list_paths('launch-intents'):
        intent = records.read(path, lambda value: value)
        try:
            custody = custody_store.read(intent['invocation_id'])
            resolved = custody.state is CustodyState.ABSENCE_VERIFIED and custody.invocation_digest == intent['invocation_digest']
        except (LabValidationError, KeyError, TypeError):
            resolved = False
        if not resolved:
            raise LabValidationError('INTEGRATION_OUTCOME_UNCERTAIN', 'prior launch lacks verified absence; no replacement is allowed')


def _protected_host_path(path, workspace):
    """Reject aliases before checking the actual execution dependency boundary."""
    if not isinstance(path, Path) or not path.is_absolute() or path.resolve() != path:
        raise LabValidationError('PI_LAUNCH_PATH_INVALID', 'host paths must be canonical and absolute')
    for ancestor in (path, *path.parents):
        if ancestor.exists() and (ancestor.is_symlink()
                or getattr(ancestor.lstat(), 'st_file_attributes', 0) & 0x400):
            raise LabValidationError('PI_LAUNCH_PATH_INVALID', 'host execution paths cannot contain reparse aliases')
    if path.is_relative_to(workspace) or workspace.is_relative_to(path):
        raise LabValidationError('PI_AUTHORITY_OVERLAP', 'worker workspace must be separate from authority and runtime installations')
    return path


def _require_runtime_separation(node, python, workspace):
    """Inspect supported Windows runtime startup paths without executing them.

    -I -S keeps the fixed Python bridge independent of site-packages startup code.
    A venv still has an execution-significant home and a Windows restricted-path
    file can override Python's library search. Inspect both before any launch.
    """
    for executable in (node, python):
        _protected_host_path(executable, workspace)
        if not executable.is_file():
            raise LabValidationError('PI_LAUNCH_PATH_INVALID', 'configured runtime executable must exist')
        _protected_host_path(executable.parent, workspace)
    roots, restricted_directories = {python.parent}, set()
    for directory in (python.parent, python.parent.parent):
        config = directory / 'pyvenv.cfg'
        if not config.exists():
            continue
        _protected_host_path(directory, workspace)
        _protected_host_path(config, workspace)
        # The native Windows redirector and Python getpath parse permissively
        # but differently. Support their shared canonical form, not ambiguous
        # comments/duplicate keys or truncation in the native 4 KiB buffer.
        with config.open('rb') as stream:
            raw_config = stream.read(4096)
        try:
            config_text = raw_config.decode('utf-8')
        except UnicodeError as exc:
            raise LabValidationError('PI_RUNTIME_STARTUP_INVALID', 'Python venv configuration must be UTF-8') from exc
        if (len(raw_config) >= 4096 or '\0' in config_text
                or not config_text.startswith('home = ')):
            raise LabValidationError('PI_RUNTIME_STARTUP_INVALID',
                'Python venv requires a canonical first home = line, no NUL, and fewer than 4096 bytes')
        values = {}
        for line in config_text.splitlines():
            key, separator, value = line.partition('=')
            if separator:
                key = key.strip().lower()
                if key == 'home' and key in values:
                    raise LabValidationError('PI_RUNTIME_STARTUP_INVALID', 'Python venv home must occur exactly once')
                values[key] = value.strip()
        if not values.get('home'):
            raise LabValidationError('PI_RUNTIME_STARTUP_INVALID', 'Python venv requires an explicit home')
        first_line = config_text.partition('\n')[0].removesuffix('\r')
        if first_line != 'home = ' + values['home']:
            raise LabValidationError('PI_RUNTIME_STARTUP_INVALID', 'Python venv first home line must be unambiguous')
        home = _protected_host_path(Path(values['home']), workspace)
        if any((parent / 'pyvenv.cfg').exists() for parent in (home, home.parent)):
            raise LabValidationError('PI_RUNTIME_STARTUP_INVALID',
                'Python venv home must name the base installation; chained venv homes are unsupported')
        roots.add(home)
        roots.add(directory)
    # _pth paths are relative to their containing runtime, never to the candidate.
    # Do not permit this special file to re-enable site startup bypassing -S.
    for directory in tuple(roots):
        for config in directory.glob('*._pth'):
            _protected_host_path(config, workspace)
            for line in config.read_text(encoding='utf-8-sig').splitlines():
                entry = line.partition('#')[0].strip()
                if not entry:
                    continue
                if entry.startswith('import'):
                    raise LabValidationError('PI_RUNTIME_STARTUP_INVALID', 'Python restricted-path files cannot enable startup imports')
                dependency = Path(entry)
                if not dependency.is_absolute():
                    dependency = directory / dependency
                # Normalize explicit relative path components while rejecting aliases.
                dependency = Path(os.path.abspath(dependency))
                dependency = _protected_host_path(dependency, workspace)
                if dependency.is_dir():
                    restricted_directories.add(dependency)
    for directory in roots | {node.parent}:
        _protected_host_path(directory, workspace)
        for library in directory.glob('*.dll'):
            _protected_host_path(library, workspace)
    for directory in roots:
        for dependency in (*directory.glob('python*.zip'), directory / 'Lib', directory / 'DLLs', *restricted_directories):
            _protected_host_path(dependency, workspace)
            if not dependency.is_dir():
                continue
            # Standard-library subdirectories can themselves be redirected. Site
            # packages are not imported by this bridge, so they need no discovery.
            for current, children, files in os.walk(dependency, followlinks=False):
                if Path(current) == directory / 'Lib' and 'site-packages' in children:
                    children.remove('site-packages')
                for name in (*children, *files):
                    entry = Path(current) / name
                    if entry.is_symlink() or getattr(entry.lstat(), 'st_file_attributes', 0) & 0x400:
                        raise LabValidationError('PI_LAUNCH_PATH_INVALID', 'Python standard-library paths cannot contain reparse aliases')


class SupervisedPiLauncher:
    def __init__(self, *, state_root, workspace_root, node, framework_root, python,
                 pi_installation, agent_dir, cancellation=None, process_factory=OwnedWindowsProcess):
        self.state_root, self.workspace = state_root, workspace_root
        self.node, self.framework, self.python = node, framework_root, python
        self.installation, self.agent_dir = pi_installation, agent_dir
        self.cancel = cancellation
        self.process_factory = process_factory
        self.last_custody = None
        if not isinstance(workspace_root, Path) or not workspace_root.is_absolute() or workspace_root.resolve() != workspace_root:
            raise LabValidationError('PI_LAUNCH_PATH_INVALID', 'workspace must be canonical and absolute')
        self._require_host_separation()

    def _require_host_separation(self):
        for protected in (self.state_root, self.framework, self.installation, self.agent_dir):
            _protected_host_path(protected, self.workspace)
        _require_runtime_separation(self.node, self.python, self.workspace)

    def __call__(self, argv, raw, deadline):
        if os.name != 'nt':
            raise LabValidationError('INTEGRATION_RUNTIME_FORBIDDEN', 'Windows Job Objects required')
        if not isinstance(raw, bytes) or not raw.endswith(b'\n'):
            raise LabValidationError('PI_PROTOCOL_INVALID', 'one complete request is required')
        if len(argv) != 3 or tuple(argv[:2]) != (str(self.node), str(self.framework / 'tools/pi_adapter_main.mjs')):
            raise LabValidationError('PI_LAUNCH_COMMAND_INVALID', 'only the pinned adapter entrypoint may launch')
        control = json.loads(base64.urlsafe_b64decode(argv[2] + '=' * (-len(argv[2]) % 4)))
        request = parse_request(raw[:-1], expected_worker_digest=control['worker_digest'], now_unix_ms=time.time_ns() // 1_000_000)
        invocation = InvocationRecordV3.from_mapping(request['invocation'])
        if (deadline != request['deadline_unix_ms'] or request['workspace_root'] != str(self.workspace)
                or control['request_digest'] != canonical_digest(request)
                or control['python'] != str(self.python) or control['pi_installation'] != str(self.installation)
                or control['agent_dir'] != str(self.agent_dir)):
            raise LabValidationError('PI_LAUNCH_IDENTITY_INVALID', 'launch differs from sealed request')
        self._require_host_separation()
        activation = require_activation(self.state_root, worker_digest=request['worker_digest'], controller=invocation.authorized_by)
        with _exclusive_controller(self.state_root):
            records, store = AtomicRecordStore(self.state_root), ProcessCustodyStore(self.state_root)
            _require_resolved_launches(records, store)
            from .protected_validation import require_resolved_validations
            require_resolved_validations(records)
            if InvocationStoreV3(self.state_root).read(invocation.invocation_id) != invocation:
                raise LabValidationError('PI_LAUNCH_IDENTITY_INVALID', 'invocation is not the durable dispatching record')
            binding = ProviderBindingStore(self.state_root).require(invocation.provider_binding_id, invocation.provider_binding_digest)
            if binding.to_dict() != control['binding'] or validate_pi_binding(binding) != request['worker']:
                raise LabValidationError('PI_LAUNCH_IDENTITY_INVALID', 'launch binding differs')
            if records._target(f'launch-intents/{invocation.invocation_id}.json').exists():
                raise LabValidationError('PI_ATTEMPT_ALREADY_LAUNCHED', 'an invocation may launch only once')
            launch = inspect_launch_workspace(self.workspace)
            _, source = inspect_source_identity()
            if (invocation.worker_lab_source_digest != source.component_digests['worker-lab']
                    or invocation.framework_source_digest != source.component_digests['autonomous-worker-framework']):
                raise LabValidationError('PI_LAUNCH_IDENTITY_INVALID', 'invocation source identity differs from approved installation')
            if (launch.status or launch.observed_head != invocation.source_state.base_commit
                    or launch.workspace_path_digest != invocation.source_state.workspace_path_digest):
                raise LabValidationError('PI_LAUNCH_WORKSPACE_INVALID', f'launch workspace differs: dirty={bool(launch.status)}, head_match={launch.observed_head == invocation.source_state.base_commit}, path_match={launch.workspace_path_digest == invocation.source_state.workspace_path_digest}')
            controller_process = windows_process_identity(os.getpid(), process_creation_time_for_pid(os.getpid()))
            evidence = dict(schema_version='acl-pi-launch-intent:v1', invocation_id=invocation.invocation_id,
                invocation_digest=invocation.identity_digest(), attempt_id=invocation.attempt_id,
                request_digest=canonical_digest(request), worker_digest=request['worker_digest'],
                grant_digest=request['grant_digest'], activation_digest=canonical_digest(activation),
                controller_identity=controller_process, deadline_unix_ms=deadline, created_at=now(),
                argv=list(argv), workspace_root=str(self.workspace))
            # Durable before ANY child process. A crash here is deliberately uncertain on restart.
            records.write(f'launch-intents/{invocation.invocation_id}.json', _Record(evidence))
            custody = ProcessCustodyRecord.from_mapping(dict(schema_version=PROCESS_CUSTODY_SCHEMA,
                invocation_id=invocation.invocation_id, invocation_digest=invocation.identity_digest(),
                backend_id=WINDOWS_JOB_BACKEND_ID, controller_identity=controller_process,
                worker_identity=None, workspace_content_digest=launch.content_digest, state='PREPARED',
                request_sent=False, exit_code=None, active_workload_count=None, absence_evidence_digest=None,
                absence_verified_at=None, first_failure=None))
            store.create(custody)
            return self._execute(argv, raw, deadline, records, store, custody)

    def _execute(self, argv, raw, deadline, records, store, custody):
        process, failure, exit_code, count, creation_attempted = None, None, None, None, False
        directory = records._target(f'process-logs/{custody.invocation_id}')
        directory.mkdir(parents=True, exist_ok=False)
        records.write_bytes(f'process-logs/{custody.invocation_id}/request.jsonl', raw)
        environment = minimal_pi_environment(directory / 'home', self.agent_dir)
        self.agent_dir.mkdir(parents=True, exist_ok=True)

        def transition(state, **fields):
            nonlocal custody
            updated = transition_custody(custody, state, **fields)
            store.save_transition(updated, expected_digest=custody.digest())
            custody = updated
            self.last_custody = custody

        try:
            with (directory / 'request.jsonl').open('rb') as stdin, (directory / 'stdout.jsonl').open('wb') as stdout, (directory / 'stderr.log').open('wb') as stderr:
                # Recheck activation/deadline after all preparation, before creation.
                request = json.loads(raw)
                require_activation(self.state_root, worker_digest=request['worker_digest'], controller=request['invocation']['authorized_by'])
                if self.cancel is not None and self.cancel.is_set():
                    raise LabValidationError('PI_CANCELLED', 'cancelled before creation')
                if time.time_ns() // 1_000_000 >= deadline:
                    raise LabValidationError('PI_TIMED_OUT', 'deadline expired before creation')
                self._require_host_separation()
                creation_attempted = True
                process = self.process_factory(argv, cwd=self.workspace, environment=environment, stdin=stdin, stdout=stdout, stderr=stderr)
                transition(CustodyState.ASSIGNED, worker_identity=process.identity)
                # Conservative request-sent marker before resuming the suspended child.
                transition(CustodyState.DISPATCHING)
                process.resume()
                while (exit_code := process.poll()) is None:
                    if self.cancel is not None and self.cancel.is_set():
                        raise LabValidationError('PI_CANCELLED', 'owned attempt cancelled')
                    if time.time_ns() // 1_000_000 >= deadline:
                        raise LabValidationError('PI_TIMED_OUT', 'owned attempt exceeded its deadline')
                    if sum((directory / name).stat().st_size for name in ('stdout.jsonl', 'stderr.log')) > 8 * MAX_FRAME_BYTES:
                        raise LabValidationError('PI_OUTPUT_LIMIT', 'adapter output exceeded its limit')
                    time.sleep(0.025)
                if exit_code:
                    raise LabValidationError('PI_PROCESS_FAILED', f'adapter exited with code {exit_code}')
                if sum((directory / name).stat().st_size for name in ('stdout.jsonl', 'stderr.log')) > 8 * MAX_FRAME_BYTES:
                    raise LabValidationError('PI_OUTPUT_LIMIT', 'adapter output exceeded its limit')
                if process.active_count():
                    raise LabValidationError('PI_CHILDREN_REMAINED', 'adapter exited leaving an owned child')
        except BaseException as exc:
            failure = 'PI_CANCELLED' if isinstance(exc, KeyboardInterrupt) else getattr(exc, 'code', 'PI_SUPERVISION_FAILED')
        finally:
            try:
                if process is not None:
                    if failure:
                        process.terminate()
                    until = time.monotonic() + 5
                    while (count := process.active_count()) and time.monotonic() < until:
                        time.sleep(0.025)
                    exit_code = process.poll()
                else:
                    # Creation exceptions may have occurred inside native creation.
                    # Without a retained job handle, do not manufacture absence.
                    count = None if creation_attempted else 0
                if count != 0:
                    transition(CustodyState.UNCERTAIN, exit_code=exit_code, active_workload_count=count,
                        first_failure=failure or 'PI_ABSENCE_UNPROVEN')
                else:
                    transition(CustodyState.TERMINATED if failure else CustodyState.EXITED,
                        exit_code=exit_code, active_workload_count=0, first_failure=failure)
                    proof = WindowsJobCustodyBackend().absence_evidence_digest(custody, basis='job-accounting-zero')
                    transition(CustodyState.ABSENCE_VERIFIED, active_workload_count=0,
                        absence_evidence_digest=proof, absence_verified_at=now())
            except BaseException as exc:
                failure = failure or getattr(exc, 'code', 'PI_CUSTODY_WRITE_FAILED')
                # Best effort only: an older unresolved record also blocks restart.
                if custody.state in (CustodyState.PREPARED, CustodyState.ASSIGNED, CustodyState.DISPATCHING):
                    try:
                        transition(CustodyState.UNCERTAIN, first_failure=failure)
                    except BaseException:
                        pass
            finally:
                if process is not None:
                    process.close()
        if custody.state is not CustodyState.ABSENCE_VERIFIED:
            raise LabValidationError('INTEGRATION_OUTCOME_UNCERTAIN', 'owned workload absence could not be proven')
        if failure:
            raise LabValidationError(failure, 'owned attempt stopped; inspect durable custody and process logs')
        output = (directory / 'stdout.jsonl').read_bytes()
        if len(output) > 8 * MAX_FRAME_BYTES:
            raise LabValidationError('PI_OUTPUT_LIMIT', 'adapter output exceeded its limit')
        return output


def make_supervised_pi_dispatch_runner(*, state_root, workspace_root, node, framework_root,
                                      python, pi_installation, agent_dir, outcome_sink, cancellation=None,
                                      absolute_deadline_unix_ms=None):
    launcher = SupervisedPiLauncher(state_root=state_root, workspace_root=workspace_root, node=node,
        framework_root=framework_root, python=python, pi_installation=pi_installation, agent_dir=agent_dir,
        cancellation=cancellation)
    return make_pi_dispatch_runner(binding_store=ProviderBindingStore(state_root), workspace_root=workspace_root,
        node=node, framework_root=framework_root, python=python, pi_installation=pi_installation,
        agent_dir=agent_dir, launcher=launcher, outcome_sink=outcome_sink,
        absolute_deadline_unix_ms=absolute_deadline_unix_ms)
