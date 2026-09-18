"""One authorized task, durable observations, no automatic acceptance or retry."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

from .attempt_store import AttemptStore
from .canonical import canonical_digest, canonical_json
from .dispatch_client import dispatch_workspace_write
from .errors import LabValidationError
from .integration_v3 import InvocationState, transition_invocation
from .invocation_store_v3 import InvocationStoreV3
from .lifecycle import transition_attempt
from .models import AttemptState
from .pi_binding import validate_pi_binding
from .pi_protocol import grant_digest, parse_result
from .pi_supervision import (_exclusive_controller, require_activation,
    make_supervised_pi_dispatch_runner, _require_resolved_launches)
from .process_custody import ProcessCustodyStore, CustodyState
from .provider_binding import ProviderBindingStore
from .service_runtime_v3 import prepare_dispatch
from .storage import AtomicRecordStore
from .windows_job import workspace_content_digest
from .worker_outcome import WorkerOutcome
from .workspace import _git_bytes

TASK_SCHEMA = 'worker-lab-run-task:v1'
DEFAULT_CANDIDATE_ARCHIVE_LIMIT_BYTES = 32 * 1024 * 1024


class _WorkerOutcomeCaptured(Exception):
    """Stop at the existing outcome callback, before AWF validation/acceptance."""



def _read_task(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise LabValidationError('RUN_TASK_INVALID', 'task file must contain valid UTF-8 JSON') from exc
    fields = {'schema_version', 'invocation_id', 'expected_identity_digest', 'controller_identity', 'workspace_root'}
    if not isinstance(value, dict) or set(value) != fields or value['schema_version'] != TASK_SCHEMA or any(not isinstance(value[k], str) or not value[k] for k in fields):
        raise LabValidationError('RUN_TASK_INVALID', 'task must reference one authorized invocation and workspace root')
    root = Path(value['workspace_root'])
    if not root.is_absolute() or root.resolve() != root:
        raise LabValidationError('RUN_TASK_INVALID', 'workspace root must be canonical and absolute')
    return value


def _optional(records, path):
    try:
        return records.read(path, lambda value: value)
    except LabValidationError as exc:
        if exc.code != 'STORAGE_RECORD_MISSING':
            raise
        return None


def _host_settings(records):
    value = records.read('operator/pi-host.json', lambda value: value)
    fields = {'schema_version', 'node', 'python', 'framework_root', 'pi_installation', 'agent_dir'}
    if not isinstance(value, dict) or set(value) != fields or value['schema_version'] != 'acl-pi-host:v1':
        raise LabValidationError('PI_HOST_INVALID', 'explicit protected Pi host paths are required')
    paths = {}
    for key in fields - {'schema_version'}:
        if not isinstance(value[key], str):
            raise LabValidationError('PI_HOST_INVALID', 'host paths must be canonical absolute paths')
        p = Path(value[key])
        if not p.is_absolute() or p.resolve() != p:
            raise LabValidationError('PI_HOST_INVALID', 'host paths must be canonical absolute paths')
        paths[key] = p
    expected = Path(__file__).resolve().parents[2] / 'autonomous-worker-framework'
    if paths['framework_root'] != expected:
        raise LabValidationError('PI_HOST_INVALID', 'framework must be the current trusted installation')
    return paths


def _finish(records, outcome, clock):
    """Replay only durable lifecycle bookkeeping; never re-execute an attempt."""
    value = outcome.to_dict()
    attempts = AttemptStore(records.root)
    invocations = InvocationStoreV3(records.root)
    invocation = invocations.read(value['invocation_id'])
    attempt = attempts.read(value['attempt_id'])
    if invocation.identity_digest() != value['invocation_digest'] or invocation.attempt_id != attempt.attempt_id:
        raise LabValidationError('WORKER_OUTCOME_MISMATCH', 'outcome and durable identities differ')
    reference = 'worker-outcome:' + outcome.digest()
    if invocation.state is InvocationState.OUTCOME_RECORDED:
        if invocation.result_digest != outcome.digest():
            raise LabValidationError('WORKER_OUTCOME_MISMATCH', 'terminal invocation outcome differs')
    else:
        invocations.save_transition(transition_invocation(invocation, InvocationState.OUTCOME_RECORDED,
            result_digest=outcome.digest()), expected_digest=invocation.digest())
    if attempt.state is AttemptState.OUTCOME_RECORDED:
        if attempt.cleanup_outcome != reference:
            raise LabValidationError('WORKER_OUTCOME_MISMATCH', 'terminal attempt outcome differs')
    else:
        attempts.save_transition(transition_attempt(attempt, AttemptState.OUTCOME_RECORDED,
            occurred_at=clock(), cleanup_outcome=reference))
    return outcome


def _archive_limit(value):
    if value is None:
        return DEFAULT_CANDIDATE_ARCHIVE_LIMIT_BYTES
    if type(value) is not int or value < 0:
        raise LabValidationError('CANDIDATE_ARCHIVE_LIMIT_INVALID', 'archive budget must be a nonnegative byte count; zero omits the ZIP')
    return value


def _candidate_diff(workspace, base_commit):
    # Explicit repository selection plus the shared environment excludes inherited
    # Git redirection. Never refresh the index or execute external diff/textconv.
    args = ['-C', str(workspace), '-c', 'core.fsmonitor=false', '-c', 'diff.external=']
    options = ['--no-ext-diff', '--no-textconv', '--binary', '--no-renames',
        '--src-prefix=a/', '--dst-prefix=b/']
    patch = _git_bytes([*args, 'diff', *options, base_commit, '--'],
        'capture candidate diff', subprocess.run, 15)
    # No exclude-standard: ignored new files are part of the candidate identity too.
    names = _git_bytes([*args, 'ls-files', '--others', '-z'],
        'list candidate new files', subprocess.run, 15)
    for raw in sorted(name for name in names.split(b'\0') if name):
        name = os.fsdecode(raw)
        if not (workspace / name).is_file():
            raise LabValidationError('CANDIDATE_CAPTURE_FAILED', 'new candidate entry is not a regular file')
        patch += _git_bytes([*args, 'diff', '--no-index', *options, '--', os.devnull, name],
            'capture candidate new file', subprocess.run, 15, allowed_returncodes=(0, 1))
    return patch


def _snapshot(records, invocation, workspace, artifacts, archive_limit_bytes):
    """Retain dirty candidate bytes separately; never create an accepted base."""
    before = workspace_content_digest(workspace)
    prefix = f'worker-artifacts/{invocation.attempt_id}'
    files = [file for file in sorted(workspace.rglob('*'))
        if file.relative_to(workspace).parts[0] != '.git' and file.is_file()]
    total = sum(file.stat().st_size for file in files)
    capture_archive = archive_limit_bytes > 0 and total <= archive_limit_bytes
    archive = io.BytesIO() if capture_archive else None
    # workspace_content_digest has already rejected links/reparse entries.
    if archive is not None:
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
            for file in files:
                entry = zipfile.ZipInfo(file.relative_to(workspace).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                with file.open('rb') as source, bundle.open(entry, 'w') as destination:
                    shutil.copyfileobj(source, destination)
    patch = _candidate_diff(workspace, invocation.source_state.base_commit)
    after = workspace_content_digest(workspace)
    if before != after:
        raise LabValidationError('CANDIDATE_DRIFT', 'candidate changed while evidence was captured')
    retained = [('candidate.patch', patch)]
    if archive is not None:
        retained.append(('candidate.zip', archive.getvalue()))
    for name, content in retained:
        path = prefix + '/' + name
        records.write_bytes(path, content)
        artifacts[name] = path
    return {'content_digest': before, 'archive': artifacts.get('candidate.zip'),
        'diff': artifacts['candidate.patch'], 'accepted_base': False,
        'archive_capture': {'status': 'captured' if capture_archive else 'omitted_limit',
            'limit_bytes': archive_limit_bytes, 'content_bytes': total}}


def run_task(data_root, task_file, *, clock, cancellation=None,
             candidate_archive_limit_bytes=None,
             expected_task_file_digest=None,
             runner_factory=make_supervised_pi_dispatch_runner):
    task_file = Path(task_file).resolve()
    task = _read_task(task_file)
    if expected_task_file_digest is not None and canonical_digest(task) != expected_task_file_digest:
        raise LabValidationError('RUN_TASK_IDENTITY_MISMATCH', 'task file changed after workflow approval')
    records = AtomicRecordStore(data_root / 'state')
    invocations, attempts = InvocationStoreV3(records.root), AttemptStore(records.root)
    invocation = invocations.read(task['invocation_id'])
    if (invocation.identity_digest() != task['expected_identity_digest']
            or invocation.authorized_by != task['controller_identity']):
        raise LabValidationError('RUN_TASK_IDENTITY_MISMATCH', 'task does not match the durable authorization')
    workspace_root = Path(task['workspace_root'])
    workspace = workspace_root / invocation.attempt_id
    from .workspace import canonical_path_digest
    if invocation.source_state is None or canonical_path_digest(workspace) != invocation.source_state.workspace_path_digest:
        raise LabValidationError('RUN_TASK_IDENTITY_MISMATCH', 'workspace differs from admitted path')
    if (task_file.is_relative_to(workspace) or records.root.is_relative_to(workspace)
            or workspace.is_relative_to(records.root)):
        raise LabValidationError('RUN_TASK_AUTHORITY_OVERLAP', 'task and controller records must be outside worker writes')
    task_digest = canonical_digest(task)
    with _exclusive_controller(records.root, 'run-task.lock'):
        invocation = invocations.read(task['invocation_id'])
        existing = _optional(records, f'worker-outcomes/{invocation.attempt_id}.json')
        if existing is not None:
            outcome = WorkerOutcome.from_mapping(existing)
            if outcome.to_dict()['task_file_digest'] != task_digest:
                raise LabValidationError('RUN_TASK_IDENTITY_MISMATCH', 'attempt was recorded for a different task file')
            return _finish(records, outcome, clock)
        intent_path = f'run-task-intents/{invocation.attempt_id}.json'
        intent = _optional(records, intent_path)
        if intent and intent.get('task_file_digest') != task_digest:
            raise LabValidationError('RUN_TASK_IDENTITY_MISMATCH', 'prior task intent differs')
        archive_limit = _archive_limit(intent.get('candidate_archive_limit_bytes')
            if intent is not None else candidate_archive_limit_bytes)
        absolute_deadline_unix_ms = None
        from .job_admission import ATTEMPT_PREFIX
        if invocation.state not in {InvocationState.AUTHORIZED, InvocationState.DISPATCHING, InvocationState.UNCERTAIN}:
            raise LabValidationError('RUN_TASK_TERMINAL', 'invocation cannot execute again')
        binding = ProviderBindingStore(records.root).require(invocation.provider_binding_id, invocation.provider_binding_digest)
        if binding.provider_adapter_id != 'pi-local-files:v1':
            raise LabValidationError('RUN_TASK_PROVIDER_UNSUPPORTED', 'run-task requires the explicitly bound Pi adapter')
        prefix = f'worker-artifacts/{invocation.attempt_id}'
        worker_result, error, candidate = None, None, None
        artifacts, diagnostics = {}, []
        custody_store = ProcessCustodyStore(records.root)
        restarted = intent is not None or invocation.state is not InvocationState.AUTHORIZED
        # This immutable marker precedes all lifecycle mutation and dispatch.
        if intent is None:
            intent = {'schema_version': 'worker-lab-run-task-intent:v1', 'task_file_digest': task_digest,
                'invocation_id': invocation.invocation_id, 'invocation_digest': invocation.identity_digest(),
                'workspace': str(workspace), 'created_at': clock(),
                'candidate_archive_limit_bytes': archive_limit}
            records.write_bytes(intent_path, (canonical_json(intent) + '\n').encode())
        dispatched = invocation.state in {InvocationState.DISPATCHING, InvocationState.UNCERTAIN}
        try:
            if invocation.attempt_id.startswith(ATTEMPT_PREFIX):
                from .job_runner import job_execution_allowance
                allowance = job_execution_allowance(data_root, invocation,
                    controller_identity=invocation.authorized_by, clock=clock)
                absolute_deadline_unix_ms = allowance['deadline_unix_ms']
            if restarted:
                raise LabValidationError('RUN_TASK_INTERRUPTED', 'prior controller stopped before recording an outcome; no replay')
            # Unresolved earlier run-task transactions block replacements, even if
            # a crash happened before the lower-level launch intent was written.
            for path in records.list_paths('run-task-intents'):
                previous = records.read(path, lambda value: value)
                if path == intent_path:
                    continue
                previous_invocation = invocations.read(previous['invocation_id'])
                previous_outcome = _optional(records, f'worker-outcomes/{previous_invocation.attempt_id}.json')
                if previous_outcome is None or WorkerOutcome.from_mapping(previous_outcome).to_dict()['stop_state'] == 'uncertain':
                    raise LabValidationError('RUN_TASK_PRIOR_UNCERTAIN', 'prior task lacks resolved stop evidence')
            _require_resolved_launches(records, custody_store)
            from .protected_validation import require_resolved_validations
            require_resolved_validations(records)
            config = validate_pi_binding(binding)
            require_activation(records.root, worker_digest=canonical_digest(config), controller=invocation.authorized_by)
            host = _host_settings(records)
            prepared, attempt, _, prompt, task_body, admitted_workspace = prepare_dispatch(data_root,
                invocation_id=invocation.invocation_id, expected_identity_digest=invocation.identity_digest(),
                controller_identity=invocation.authorized_by, workspace_root=workspace_root)
            def sink(value):
                nonlocal worker_result
                worker_result = value
                path = prefix + '/worker-result.json'
                records.write_bytes(path, (canonical_json(value) + '\n').encode())
                artifacts['worker_result'] = path
                # M04 ends at this existing seam. M05/M06 own validators/acceptance.
                raise _WorkerOutcomeCaptured()
            runner_options = dict(state_root=records.root, workspace_root=admitted_workspace,
                **host, outcome_sink=sink, cancellation=cancellation)
            if absolute_deadline_unix_ms is not None:
                runner_options['absolute_deadline_unix_ms'] = absolute_deadline_unix_ms
            runner = runner_factory(**runner_options)
            running = transition_attempt(attempt, AttemptState.RUNNING, occurred_at=clock(),
                runtime_identity=prepared.identity_digest())
            attempts.save_transition(running)
            dispatching = transition_invocation(prepared, InvocationState.DISPATCHING)
            invocations.save_transition(dispatching, expected_digest=prepared.digest())
            invocation, dispatched = dispatching, True
            response = dispatch_workspace_write(invocation, prompt=prompt, workspace_write=task_body,
                binding_store=ProviderBindingStore(records.root), runner=runner)
            path = prefix + '/framework-response.json'
            records.write_bytes(path, response)
            artifacts['framework_response'] = path
        except _WorkerOutcomeCaptured:
            pass
        except (Exception, KeyboardInterrupt) as exc:
            error = {'code': 'PI_CANCELLED' if isinstance(exc, KeyboardInterrupt) else getattr(exc, 'code', type(exc).__name__),
                'message': str(exc)[:4096] or 'controller interrupted'}
        # The parsed result may have reached disk before a controller crash.
        # Retain its measured usage only after correlation to the sealed request.
        retained_result = prefix + '/worker-result.json'
        if worker_result is None and records._target(retained_result).is_file():
            artifacts['worker_result'] = retained_result
            try:
                worker_result = parse_result(records.read_bytes(retained_result).rstrip(b'\n'),
                    request_raw=records.read_bytes(f'process-logs/{invocation.invocation_id}/request.jsonl').rstrip(b'\n'),
                    expected_worker_digest=binding.qualification_candidate_digest)
            except (LabValidationError, OSError) as exc:
                diagnostics.append({'code': getattr(exc, 'code', 'RETAINED_RESULT_INVALID'), 'message': str(exc)[:2048]})
        # Never require a clean workspace to persist a stopped or failed outcome.
        try:
            custody = custody_store.read(invocation.invocation_id)
            if custody.invocation_digest != invocation.identity_digest():
                raise LabValidationError('WORKER_OUTCOME_MISMATCH', 'custody belongs to a different invocation')
            stop_state = 'absence_verified' if custody.state is CustodyState.ABSENCE_VERIFIED else 'uncertain'
            custody_value = custody.to_dict()
        except LabValidationError as exc:
            custody_value = None
            diagnostics.append({'code': exc.code, 'message': str(exc)[:2048]})
            launch = _optional(records, f'launch-intents/{invocation.invocation_id}.json')
            stop_state = 'uncertain' if launch is not None or restarted or dispatched else 'not_started'
        for name in ('request.jsonl', 'stdout.jsonl', 'stderr.log'):
            path = f'process-logs/{invocation.invocation_id}/{name}'
            if records._target(path).is_file():
                artifacts[name] = path
        if stop_state == 'absence_verified':
            try:
                candidate = _snapshot(records, invocation, workspace, artifacts, archive_limit)
                if candidate['archive_capture']['status'] == 'omitted_limit':
                    diagnostics.append({'code': 'CANDIDATE_ARCHIVE_OMITTED',
                        'message': f'Full ZIP omitted: {candidate["archive_capture"]["content_bytes"]} candidate bytes; '
                            f'archive budget {archive_limit}. Candidate identity, workspace and complete diff retained.'})
            except Exception as exc:
                diagnostics.append({'code': getattr(exc, 'code', 'CANDIDATE_CAPTURE_FAILED'), 'message': str(exc)[:2048]})
                error = error or diagnostics[-1]
        if stop_state == 'uncertain':
            status = 'uncertain'
        elif restarted:
            status = 'interrupted'
        elif error and error['code'] in {'PI_CANCELLED'}:
            status = 'cancelled'
        elif error and error['code'] in {'PI_TIMED_OUT', 'PI_DEADLINE_EXCEEDED'}:
            status = 'timed_out'
        elif error and error['code'] in {'PI_PROTOCOL_INVALID', 'ACL_OUTCOME_INVALID', 'PI_OUTPUT_LIMIT'}:
            status = 'protocol_error'
        elif worker_result and worker_result['status'] != 'completed':
            status = {'failed': 'provider_failed', 'timed_out': 'timed_out', 'protocol_error': 'protocol_error',
                'blocked': 'blocked', 'needs_continuation': 'needs_continuation', 'cancelled': 'cancelled'}.get(worker_result['status'], 'provider_failed')
        elif error:
            status = 'blocked' if stop_state == 'not_started' else 'provider_failed'
        elif worker_result and candidate is not None:
            status = 'completed_claim'
        else:
            status = 'protocol_error'
            error = {'code': 'PI_OUTCOME_MISSING', 'message': 'runner did not retain a worker outcome'}
        value = dict(schema_version='worker-lab-worker-outcome:v1', attempt_id=invocation.attempt_id,
            invocation_id=invocation.invocation_id, invocation_digest=invocation.identity_digest(),
            task_file_digest=task_digest, configuration_digest=binding.qualification_candidate_digest,
            grant_digest=grant_digest(invocation, str(workspace)), provider_binding_digest=invocation.provider_binding_digest,
            status=status, accepted=False,
            acceptance='pending_independent_acceptance' if status == 'completed_claim' else 'not_accepted',
            recorded_at=clock(), stop_state=stop_state, custody=custody_value,
            worker_result=worker_result, usage=worker_result.get('usage') if worker_result else None,
            error=error, candidate=candidate, diagnostics=diagnostics, artifacts=artifacts, workspace=str(workspace),
            manual_next_step='Inspect diagnostics and retained diff. Request a fresh authorized attempt from a clean trusted base; no automatic retry or session resume. Uncertain stop evidence must be resolved before another launch.')
        outcome = WorkerOutcome.from_mapping(value)
        attempts.record_outcome(outcome)
        return _finish(records, outcome, clock)
