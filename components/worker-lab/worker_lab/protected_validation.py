"""M05: named protected checks, explicit local host approval, no task acceptance."""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import time

from .attempt_store import AttemptStore
from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .integration_v3 import InvocationState
from .invocation_store_v3 import InvocationStoreV3
from .models import AttemptState
from .operator_control import inspect_source_identity, validate_controller_identity
from .pi_supervision import _exclusive_controller, _require_resolved_launches, now
from .process_custody import (PROCESS_CUSTODY_SCHEMA, CustodyState, ProcessCustodyRecord,
    ProcessCustodyStore, transition_custody)
from .service_runtime_v3 import _validate_dispatch_definitions, _run_sealed_tests
from .storage import AtomicRecordStore
from .test_catalog import TestRunner
from .windows_job import (OwnedWindowsProcess, WINDOWS_JOB_BACKEND_ID, WindowsJobCustodyBackend,
    inspect_launch_workspace, process_creation_time_for_pid, windows_process_identity,
    )
from .workspace import canonical_path_digest

MODE = 'operator-approved-local-test:v1'
EXPOSURE = 'unsandboxed-host-code-execution'


def _check(ok, code, message):
    if not ok:
        raise LabValidationError(code, message)


@dataclass(frozen=True)
class ValidationReport:
    payload: str

    def to_dict(self):
        return json.loads(self.payload)

    def to_json(self):
        return self.payload

    def digest(self):
        return canonical_digest(self.to_dict())


def _optional(records, path):
    try:
        return records.read(path, lambda value: value)
    except LabValidationError as exc:
        if exc.code != 'STORAGE_RECORD_MISSING':
            raise
        return None


def require_resolved_validations(records):
    """Shared with worker launch: a lost validator cannot coexist with new work."""
    for path in records.list_paths('validation-intents'):
        intent = records.read(path, lambda value: value)
        _check(isinstance(intent, dict) and isinstance(intent.get('validation_id'), str)
            and re.fullmatch(r'VALIDATION-[A-Za-z0-9_-]{1,80}', intent['validation_id']),
            'VALIDATION_UNCERTAIN', 'invalid earlier validation intent')
        report = _optional(records, f"validation-results/{intent['validation_id']}.json")
        _check(isinstance(report, dict) and report.get('schema_version') == 'worker-lab-validation-report:v1'
            and report.get('request_digest') == canonical_digest(intent)
            and report.get('all_validators_absent') is True and isinstance(report.get('checks'), list),
            'VALIDATION_UNCERTAIN', 'earlier validation lacks durable proof of cleanup')
        prefix = f"validation-logs/{intent['validation_id']}"
        launches = {p for p in records.list_paths(prefix) if p.endswith('/launch-intent.json')}
        reported = set()
        for check in report['checks']:
            _check(isinstance(check, dict) and isinstance(check.get('test_id'), str)
                and re.fullmatch(r'[A-Za-z0-9_-]+', check['test_id']),
                'VALIDATION_UNCERTAIN', 'invalid earlier check identity')
            directory = f"{prefix}/{check['test_id']}"
            launch_path = directory + '/launch-intent.json'
            _check(launch_path not in reported, 'VALIDATION_UNCERTAIN', 'duplicate earlier check')
            reported.add(launch_path)
            launch = records.read(launch_path, lambda value: value)
            saved = records.read(directory + '/result.json', lambda value: value)
            custody = ProcessCustodyStore(records._target(directory)).read(intent['invocation_id'])
            _check(saved == check and custody.to_dict() == check.get('custody')
                and custody.state is CustodyState.ABSENCE_VERIFIED and custody.active_workload_count == 0
                and custody.invocation_digest == intent['invocation_digest']
                and custody.workspace_content_digest == intent['candidate_digest']
                and launch.get('approval_digest') == intent['approval_digest']
                and launch.get('command') == check.get('command'),
                'VALIDATION_UNCERTAIN', 'earlier validator cleanup records disagree')
        _check(launches == reported, 'VALIDATION_UNCERTAIN', 'unreported validator launch intent')


def _base(data_root, attempt_id, expected_outcome_digest, controller):
    records = AtomicRecordStore(data_root / 'state')
    attempts = AttemptStore(records.root)
    outcome = attempts.read_outcome(attempt_id)
    value = outcome.to_dict()
    attempt = attempts.read(attempt_id)
    invocation = InvocationStoreV3(records.root).read(value['invocation_id'])
    _check(outcome.digest() == expected_outcome_digest
        and invocation.authorized_by == validate_controller_identity(controller)
        and invocation.identity_digest() == value['invocation_digest']
        and invocation.state is InvocationState.OUTCOME_RECORDED
        and invocation.result_digest == outcome.digest()
        and attempt.state is AttemptState.OUTCOME_RECORDED
        and attempt.cleanup_outcome == 'worker-outcome:' + outcome.digest(),
        'VALIDATION_IDENTITY_MISMATCH', 'validation differs from the durable task/outcome')
    workspace = Path(value['workspace'])
    _check(invocation.source_state is not None and workspace.is_absolute() and workspace.resolve() == workspace
        and not records.root.is_relative_to(workspace) and not workspace.is_relative_to(data_root.resolve())
        and canonical_path_digest(workspace) == invocation.source_state.workspace_path_digest,
        'VALIDATION_AUTHORITY_OVERLAP', 'candidate and protected controller data must be separate')
    custody = ProcessCustodyStore(records.root).read(invocation.invocation_id)
    _check(value['stop_state'] == 'absence_verified' and value['candidate'] is not None
        and custody.state is CustodyState.ABSENCE_VERIFIED and custody.active_workload_count == 0
        and custody.to_dict() == value['custody'] and custody.invocation_digest == invocation.identity_digest(),
        'VALIDATION_WORKER_ACTIVE', 'verified absence of the exact worker is required before validation')
    _require_resolved_launches(records, ProcessCustodyStore(records.root))
    observed = inspect_launch_workspace(workspace)
    candidate = value['candidate']['content_digest']
    _check(observed.content_digest == candidate and observed.observed_head == invocation.source_state.base_commit,
        'VALIDATION_CANDIDATE_DRIFT', 'candidate bytes or base changed since worker outcome')
    _, source = inspect_source_identity()
    _check(invocation.worker_lab_source_digest == source.component_digests['worker-lab']
        and invocation.framework_source_digest == source.component_digests['autonomous-worker-framework'],
        'VALIDATION_SOURCE_MISMATCH', 'controller source differs from the admitted invocation')
    *_, catalog = _validate_dispatch_definitions(data_root, attempt, invocation)
    by_id = {test.test_id: test for test in catalog.tests}
    selected = [by_id[test_id] for test_id in invocation.test_ids]
    _check(bool(selected) and all(test.runner is TestRunner.COMMAND for test in selected),
        'VALIDATION_RUNNER_UNSUPPORTED', 'this local mode supports named protected command tests only')
    return records, outcome, invocation, workspace, candidate, selected, source.manifest_digest


def _file_identity(path, workspace):
    path = Path(path)
    _check(path.is_absolute() and path.resolve() == path and path.is_file()
        and not path.is_relative_to(workspace), 'VALIDATION_INPUT_INVALID',
        'executables and authoritative inputs must be canonical files outside worker writes')
    for parent in (path, *path.parents):
        _check(not parent.is_symlink() and not getattr(os.lstat(parent), 'st_file_attributes', 0) & 0x400,
            'VALIDATION_INPUT_INVALID', 'substituted validator input path')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'digest': 'sha256:' + digest.hexdigest()}


def approve_local_validation(data_root, *, attempt_id, expected_outcome_digest, controller_identity,
        protected_files, acknowledge_unsandboxed=False, timeout_seconds=30,
        output_limit_bytes=1048576, cleanup_timeout_seconds=5):
    """Explicit operator action, also used to bind previously sealed advance consent."""
    _check(acknowledge_unsandboxed is True, 'VALIDATION_APPROVAL_REQUIRED',
        'local validators execute unsandboxed host code with this user account access')
    for number in (timeout_seconds, output_limit_bytes, cleanup_timeout_seconds):
        _check(type(number) is int and number > 0, 'VALIDATION_APPROVAL_INVALID', 'limits must be positive integers')
    with _exclusive_controller(data_root / 'state', 'run-task.lock'), _exclusive_controller(data_root / 'state'):
        records, outcome, invocation, workspace, candidate, selected, source = _base(
            data_root, attempt_id, expected_outcome_digest, controller_identity)
        require_resolved_validations(records)
        inputs = [_file_identity(path, workspace) for path in protected_files]
        _check(bool(inputs) and len({item['path'] for item in inputs}) == len(inputs),
            'VALIDATION_INPUT_INVALID', 'declare distinct protected checker/judging files')
        commands = []
        for test in selected:
            executable = _file_identity(Path(test.command[0]), workspace)
            # Catalogue arguments remain fixed. Only this whole argument denotes
            # the admitted candidate path; no worker-supplied shell interpolation.
            argv = [str(workspace) if arg == '{candidate}' else arg for arg in test.command]
            _check(any(item['path'] in argv for item in inputs), 'VALIDATION_INPUT_INVALID',
                'each named command must reference a declared protected checker/input')
            commands.append({'test_id': test.test_id, 'definition_digest': canonical_digest(test.to_dict()),
                'argv': argv, 'executable': executable})
        approval = dict(schema_version='worker-lab-local-validation-approval:v1', enabled=True,
            mode=MODE, resource_exposure=EXPOSURE, controller_identity=controller_identity,
            attempt_id=attempt_id, outcome_digest=outcome.digest(), invocation_digest=invocation.identity_digest(),
            candidate_digest=candidate, source_manifest_digest=source, test_catalog_digest=invocation.test_catalog_digest,
            cwd=str(data_root.resolve()), commands=commands, protected_inputs=inputs,
            timeout_seconds=timeout_seconds, output_limit_bytes=output_limit_bytes,
            cleanup_timeout_seconds=cleanup_timeout_seconds, approved_at=now())
        records.write_bytes(f'operator/validation-approvals/{attempt_id}.json',
            (canonical_json(approval) + '\n').encode())
        return ValidationReport(canonical_json(approval))


def _approval(records, outcome, invocation, workspace, candidate, selected, source, data_root, controller):
    value = records.read(f'operator/validation-approvals/{invocation.attempt_id}.json', lambda item: item)
    _check(isinstance(value, dict) and value.get('schema_version') == 'worker-lab-local-validation-approval:v1'
        and value.get('enabled') is True and value.get('mode') == MODE and value.get('resource_exposure') == EXPOSURE
        and value.get('controller_identity') == controller and value.get('outcome_digest') == outcome.digest()
        and value.get('attempt_id') == invocation.attempt_id
        and value.get('invocation_digest') == invocation.identity_digest() and value.get('candidate_digest') == candidate
        and value.get('source_manifest_digest') == source and value.get('test_catalog_digest') == invocation.test_catalog_digest
        and value.get('cwd') == str(data_root.resolve()), 'VALIDATION_APPROVAL_REQUIRED',
        'explicit approval of this exact local command set, candidate and source is required')
    _check(isinstance(value.get('commands'), list) and len(value['commands']) == len(selected)
        and isinstance(value.get('protected_inputs'), list) and value['protected_inputs'],
        'VALIDATION_APPROVAL_INVALID', 'approved command/input set is invalid')
    for limit in ('timeout_seconds', 'output_limit_bytes', 'cleanup_timeout_seconds'):
        _check(type(value.get(limit)) is int and value[limit] > 0,
            'VALIDATION_APPROVAL_INVALID', 'approved limits are invalid')
    for item in value['protected_inputs']:
        _check(isinstance(item, dict) and isinstance(item.get('path'), str),
            'VALIDATION_APPROVAL_INVALID', 'approved input identity is invalid')
        _check(_file_identity(item['path'], workspace) == item, 'VALIDATION_INPUT_DRIFT', 'protected judging input changed')
    for command, test in zip(value['commands'], selected):
        _check(isinstance(command, dict) and command.get('test_id') == test.test_id
            and command.get('definition_digest') == canonical_digest(test.to_dict())
            and command.get('argv') == [str(workspace) if arg == '{candidate}' else arg for arg in test.command]
            and command.get('executable') == _file_identity(Path(test.command[0]), workspace)
            and any(item['path'] in command['argv'] for item in value['protected_inputs']),
            'VALIDATION_COMMAND_DRIFT', 'command, executable or catalog definition changed')
    return value


def validator_environment(home):
    temporary = home / 'tmp'
    temporary.mkdir(parents=True, exist_ok=True)
    environment = {key: os.environ[key] for key in ('SystemRoot', 'WINDIR') if key in os.environ}
    environment.update(HOME=str(home), USERPROFILE=str(home), APPDATA=str(home/'appdata'),
        LOCALAPPDATA=str(home/'local'), TEMP=str(temporary), TMP=str(temporary),
        PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', CI='1', NO_COLOR='1')
    return environment


def _run_check(records, validation_id, command, approval, invocation, candidate, *, clock, cancellation, process_factory,
        absolute_deadline_unix_ms=None):
    prefix = f"validation-logs/{validation_id}/{command['test_id']}"
    directory = records._target(prefix)
    directory.mkdir(parents=True, exist_ok=False)
    store = ProcessCustodyStore(directory)
    controller_process = windows_process_identity(os.getpid(), process_creation_time_for_pid(os.getpid()))
    custody = ProcessCustodyRecord.from_mapping(dict(schema_version=PROCESS_CUSTODY_SCHEMA,
        invocation_id=invocation.invocation_id, invocation_digest=invocation.identity_digest(),
        backend_id=WINDOWS_JOB_BACKEND_ID, controller_identity=controller_process,
        worker_identity=None, workspace_content_digest=candidate, state='PREPARED', request_sent=False,
        exit_code=None, active_workload_count=None, absence_evidence_digest=None,
        absence_verified_at=None, first_failure=None))
    store.create(custody)
    records.write_bytes(prefix + '/launch-intent.json', (canonical_json({'command':command,
        'approval_digest':canonical_digest(approval), 'invocation_digest':invocation.identity_digest(),
        'candidate_digest':candidate, 'controller_identity':controller_process})+'\n').encode())
    process = None
    failure = None
    creation_attempted = False
    exit_code = None
    started = clock()
    def transition(state, **kwargs):
        nonlocal custody
        updated = transition_custody(custody, state, **kwargs)
        store.save_transition(updated, expected_digest=custody.digest())
        custody = updated
    try:
        with ExitStack() as stack:
            stdin = stack.enter_context(open(os.devnull, 'rb'))
            stdout = stack.enter_context((directory/'stdout.log').open('wb'))
            stderr = stack.enter_context((directory/'stderr.log').open('wb'))
            environment = validator_environment(directory/'home')
            if cancellation is not None and cancellation.is_set():
                raise LabValidationError('VALIDATION_CANCELLED', 'cancelled before validator creation')
            if absolute_deadline_unix_ms is not None and time.time_ns() // 1_000_000 >= absolute_deadline_unix_ms:
                raise LabValidationError('JOB_WALL_BUDGET_EXHAUSTED', 'job reservation expired before validator creation')
            creation_attempted = True
            process = process_factory(command['argv'], cwd=Path(approval['cwd']), environment=environment,
                stdin=stdin, stdout=stdout, stderr=stderr)
            transition(CustodyState.ASSIGNED, worker_identity=process.identity)
            transition(CustodyState.DISPATCHING)
            deadline = time.monotonic() + approval['timeout_seconds']
            if absolute_deadline_unix_ms is not None:
                deadline = min(deadline, time.monotonic()
                    + max(0, absolute_deadline_unix_ms - time.time_ns() // 1_000_000) / 1000)
            process.resume()
            while (exit_code := process.poll()) is None:
                if cancellation is not None and cancellation.is_set():
                    raise LabValidationError('VALIDATION_CANCELLED', 'validator cancelled')
                if time.monotonic() >= deadline:
                    code = 'JOB_WALL_BUDGET_EXHAUSTED' if (absolute_deadline_unix_ms is not None
                        and time.time_ns() // 1_000_000 >= absolute_deadline_unix_ms) else 'VALIDATION_TIMED_OUT'
                    raise LabValidationError(code, 'validator exceeded the strictest applicable deadline')
                if sum((directory/name).stat().st_size for name in ('stdout.log','stderr.log')) > approval['output_limit_bytes']:
                    raise LabValidationError('VALIDATION_OUTPUT_LIMIT', 'validator exceeded approved log limit')
                time.sleep(.025)
            if sum((directory/name).stat().st_size for name in ('stdout.log','stderr.log')) > approval['output_limit_bytes']:
                raise LabValidationError('VALIDATION_OUTPUT_LIMIT', 'validator exceeded approved log limit')
            if exit_code:
                raise LabValidationError('VALIDATION_CHECK_FAILED', 'protected check returned a nonzero exit code')
            # A successful console leader can exit before its owned Windows
            # helper finishes. Keep the same job and require natural absence
            # within the already approved cleanup budget; no process is exempt.
            drain_deadline = time.monotonic() + approval['cleanup_timeout_seconds']
            while process.active_count():
                if cancellation is not None and cancellation.is_set():
                    raise LabValidationError('VALIDATION_CANCELLED', 'validator cancelled during owned-process drain')
                if sum((directory/name).stat().st_size for name in ('stdout.log','stderr.log')) > approval['output_limit_bytes']:
                    raise LabValidationError('VALIDATION_OUTPUT_LIMIT', 'validator exceeded approved log limit')
                if absolute_deadline_unix_ms is not None and time.time_ns() // 1_000_000 >= absolute_deadline_unix_ms:
                    raise LabValidationError('JOB_WALL_BUDGET_EXHAUSTED', 'job reservation expired while validator children remained')
                if time.monotonic() >= drain_deadline:
                    raise LabValidationError('VALIDATION_CHILDREN_REMAINED', 'validator left owned children after cleanup deadline')
                time.sleep(.025)
            if sum((directory/name).stat().st_size for name in ('stdout.log','stderr.log')) > approval['output_limit_bytes']:
                raise LabValidationError('VALIDATION_OUTPUT_LIMIT', 'validator exceeded approved log limit')
    except (Exception, KeyboardInterrupt) as exc:
        failure = 'VALIDATION_CANCELLED' if isinstance(exc, KeyboardInterrupt) else getattr(exc, 'code', 'VALIDATION_PROCESS_FAILED')
    finally:
        try:
            if process is not None:
                if failure:
                    process.terminate()
                until = time.monotonic() + approval['cleanup_timeout_seconds']
                while (count := process.active_count()) and time.monotonic() < until:
                    time.sleep(.025)
                exit_code = process.poll()
            else:
                count = None if creation_attempted else 0
            if count != 0:
                transition(CustodyState.UNCERTAIN, exit_code=exit_code, active_workload_count=count,
                    first_failure=failure or 'VALIDATION_ABSENCE_UNPROVEN')
            else:
                transition(CustodyState.TERMINATED if failure else CustodyState.EXITED,
                    exit_code=exit_code, active_workload_count=0, first_failure=failure)
                proof = WindowsJobCustodyBackend().absence_evidence_digest(custody, basis='job-accounting-zero')
                transition(CustodyState.ABSENCE_VERIFIED, active_workload_count=0,
                    absence_evidence_digest=proof, absence_verified_at=clock())
        except (Exception, KeyboardInterrupt):
            failure = failure or 'VALIDATION_CUSTODY_FAILED'
        finally:
            if process is not None:
                process.close()
    absent = custody.state is CustodyState.ABSENCE_VERIFIED
    result = dict(test_id=command['test_id'], command=command, candidate_digest=candidate,
        started_at=started, ended_at=clock(), status='passed' if not failure and absent else 'failed' if absent else 'uncertain',
        failure=failure, exit_code=exit_code, validator_identity=custody.worker_identity,
        custody=custody.to_dict(), stdout=prefix+'/stdout.log', stderr=prefix+'/stderr.log')
    records.write_bytes(prefix+'/result.json', (canonical_json(result)+'\n').encode())
    return result


def validate_task(data_root, *, attempt_id, expected_outcome_digest, controller_identity, validation_id,
        clock=now, cancellation=None, process_factory=OwnedWindowsProcess, absolute_deadline_unix_ms=None):
    _check(isinstance(validation_id, str) and re.fullmatch(r'VALIDATION-[A-Za-z0-9_-]{1,80}', validation_id),
        'VALIDATION_ID_INVALID', 'validation identity must be VALIDATION- followed by a unique identifier')
    with _exclusive_controller(data_root/'state', 'run-task.lock'), _exclusive_controller(data_root/'state'):
        records, outcome, invocation, workspace, candidate, selected, source = _base(
            data_root, attempt_id, expected_outcome_digest, controller_identity)
        from .job_admission import ATTEMPT_PREFIX
        if invocation.attempt_id.startswith(ATTEMPT_PREFIX):
            from .job_runner import job_execution_allowance
            allowance = job_execution_allowance(data_root, invocation,
                controller_identity=controller_identity, clock=clock)
            job_deadline = allowance['deadline_unix_ms']
            absolute_deadline_unix_ms = job_deadline if absolute_deadline_unix_ms is None else min(
                absolute_deadline_unix_ms, job_deadline)
        approval = _approval(records, outcome, invocation, workspace, candidate, selected, source, data_root, controller_identity)
        request = dict(schema_version='worker-lab-validation-intent:v1', validation_id=validation_id,
            attempt_id=attempt_id, invocation_id=invocation.invocation_id, invocation_digest=invocation.identity_digest(),
            outcome_digest=outcome.digest(), candidate_digest=candidate, approval_digest=canonical_digest(approval),
            test_plan_digest=invocation.test_plan_digest, source_manifest_digest=source,
            mode=MODE, resource_exposure=EXPOSURE)
        existing = _optional(records, f'validation-results/{validation_id}.json')
        if existing is not None:
            _check(isinstance(existing, dict) and existing.get('request_digest') == canonical_digest(request),
                'VALIDATION_IDENTITY_MISMATCH', 'validation ID belongs to another request')
            require_resolved_validations(records)
            return ValidationReport(canonical_json(existing))
        require_resolved_validations(records)
        records.write_bytes(f'validation-intents/{validation_id}.json', (canonical_json(request)+'\n').encode())
        checks = []
        error = None
        all_absent = True
        validation_failure = None
        def execute(definition, candidate_path):
            nonlocal all_absent, validation_failure
            try:
                command = next(item for item in approval['commands'] if item['test_id'] == definition.test_id)
                # Reload worker/candidate, authority bytes, executable and approval
                # immediately before each creation, including subsequent checks.
                refreshed = _base(data_root, attempt_id, expected_outcome_digest, controller_identity)
                current_approval = _approval(*refreshed, data_root, controller_identity)
                _check(current_approval == approval, 'VALIDATION_APPROVAL_CHANGED', 'local approval changed')
                all_absent = False  # A failure inside creation/persistence cannot fabricate zero processes.
                result = _run_check(records, validation_id, command, approval, invocation, candidate,
                    clock=clock, cancellation=cancellation, process_factory=process_factory,
                    absolute_deadline_unix_ms=absolute_deadline_unix_ms)
                checks.append(result)
                all_absent = result['custody']['state'] == 'ABSENCE_VERIFIED'
                _check(all_absent, 'VALIDATION_UNCERTAIN', 'owned validator absence is unproven')
                _base(data_root, attempt_id, expected_outcome_digest, controller_identity)
                _approval(records, outcome, invocation, workspace, candidate, selected, source, data_root, controller_identity)
                return 0 if result['status'] == 'passed' else (result['exit_code'] or -1)
            except (Exception, KeyboardInterrupt) as exc:
                validation_failure = exc
                raise
        try:
            *_, catalog = _validate_dispatch_definitions(data_root, AttemptStore(records.root).read(attempt_id), invocation)
            _run_sealed_tests(invocation, catalog, workspace, execute)
        except (Exception, KeyboardInterrupt) as exc:
            exc = validation_failure or exc
            error = dict(code='VALIDATION_CANCELLED' if isinstance(exc, KeyboardInterrupt) else getattr(exc,'code','VALIDATION_FAILED'),
                message=str(exc)[:2048])
        passed = error is None and all_absent and len(checks) == len(selected) and all(c['status']=='passed' for c in checks)
        report = dict(schema_version='worker-lab-validation-report:v1', **{k:v for k,v in request.items() if k!='schema_version'},
            request_digest=canonical_digest(request), status='passed' if passed else 'failed' if all_absent else 'uncertain',
            accepted=False, all_validators_absent=all_absent, checks=checks, error=error, completed_at=clock())
        records.write_bytes(f'validation-results/{validation_id}.json', (canonical_json(report)+'\n').encode())
        return ValidationReport(canonical_json(report))
