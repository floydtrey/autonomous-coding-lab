"""One explicitly approved task: stopped worker, protected checks, acceptance."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .attempt_store import AttemptStore
from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .integration_v3 import InvocationState
from .invocation_store_v3 import InvocationStoreV3
from .models import AttemptState, _timestamp
from .operator_control import inspect_source_identity, validate_controller_identity
from .pi_supervision import _exclusive_controller, now
from .protected_validation import (MODE, EXPOSURE, _check, _file_identity, _base,
    _approval, _optional, approve_local_validation, validate_task, require_resolved_validations)
from .run_task import _read_task, run_task as run_worker
from .service_runtime_v3 import _validate_dispatch_definitions
from .storage import AtomicRecordStore
from .test_catalog import TestRunner
from .windows_job import inspect_launch_workspace
from .workspace import canonical_path_digest

APPROVAL_SCHEMA = 'worker-lab-task-execution-approval:v1'
LIMITS = ('timeout_seconds', 'output_limit_bytes', 'cleanup_timeout_seconds')


@dataclass(frozen=True)
class TaskRunReport:
    payload: str

    def to_dict(self):
        return json.loads(self.payload)

    def to_json(self):
        return self.payload

    def digest(self):
        return canonical_digest(self.to_dict())


def _authority(data_root, invocation, workspace):
    _check(invocation.source_state is not None and workspace.is_absolute()
        and workspace.resolve() == workspace and not workspace.is_relative_to(data_root.resolve())
        and not data_root.resolve().is_relative_to(workspace)
        and canonical_path_digest(workspace) == invocation.source_state.workspace_path_digest,
        'TASK_EXECUTION_IDENTITY_INVALID', 'task workspace must match admission and be separate from authority')
    attempt = AttemptStore(data_root / 'state').read(invocation.attempt_id)
    *_, catalog = _validate_dispatch_definitions(data_root, attempt, invocation)
    selected = [next(test for test in catalog.tests if test.test_id == test_id) for test_id in invocation.test_ids]
    _check(bool(selected) and all(test.runner is TestRunner.COMMAND for test in selected),
        'VALIDATION_RUNNER_UNSUPPORTED', 'one task requires named protected command checks')
    _, source = inspect_source_identity()
    _check(invocation.worker_lab_source_digest == source.component_digests['worker-lab']
        and invocation.framework_source_digest == source.component_digests['autonomous-worker-framework'],
        'TASK_EXECUTION_SOURCE_MISMATCH', 'execution source changed since admission')
    return attempt, selected, source.manifest_digest


def _validation_template(data_root, workspace, selected, protected_files, limits):
    _check(all(type(limits.get(key)) is int and limits[key] > 0 for key in LIMITS)
        and set(limits) == set(LIMITS), 'VALIDATION_APPROVAL_INVALID', 'local check limits must be positive integers')
    inputs = [_file_identity(path, workspace) for path in protected_files]
    _check(bool(inputs) and len({item['path'] for item in inputs}) == len(inputs),
        'VALIDATION_INPUT_INVALID', 'declare distinct protected checker and judging files')
    commands = []
    for test in selected:
        argv = [str(workspace) if arg == '{candidate}' else arg for arg in test.command]
        _check(any(item['path'] in argv for item in inputs), 'VALIDATION_INPUT_INVALID',
            'each named command must reference an explicitly declared protected checker/input')
        commands.append(dict(test_id=test.test_id, definition_digest=canonical_digest(test.to_dict()),
            argv=argv, executable=_file_identity(Path(test.command[0]), workspace)))
    return dict(mode=MODE, resource_exposure=EXPOSURE, commands=commands, protected_inputs=inputs,
        cwd=str(data_root.resolve()), **limits)


def approve_task_execution(data_root, task_file, *, controller_identity, protected_files,
        acknowledge_unsandboxed=False, review_required=False, timeout_seconds=30,
        output_limit_bytes=1048576, cleanup_timeout_seconds=5):
    """Explicit advance consent for this invocation and these fixed local checks."""
    _check(acknowledge_unsandboxed is True, 'VALIDATION_APPROVAL_REQUIRED',
        'named local checks execute unsandboxed host code with this user account access')
    _check(type(review_required) is bool, 'TASK_EXECUTION_APPROVAL_INVALID', 'review requirement must be explicit boolean')
    controller = validate_controller_identity(controller_identity)
    data_root, task_file = Path(data_root).resolve(), Path(task_file).resolve()
    task = _read_task(task_file)
    records = AtomicRecordStore(data_root / 'state')
    with _exclusive_controller(records.root, 'task-workflow.lock'), _exclusive_controller(records.root, 'run-task.lock'), _exclusive_controller(records.root):
        invocation = InvocationStoreV3(records.root).read(task['invocation_id'])
        workspace = Path(task['workspace_root']) / invocation.attempt_id
        _check(task['expected_identity_digest'] == invocation.identity_digest()
            and task['controller_identity'] == controller == invocation.authorized_by
            and not task_file.is_relative_to(workspace),
            'TASK_EXECUTION_IDENTITY_INVALID', 'task must reference the exact operator-authorized invocation')
        attempt, selected, source = _authority(data_root, invocation, workspace)
        _check(invocation.state is InvocationState.AUTHORIZED and attempt.state is AttemptState.READY
            and _optional(records, f'run-task-intents/{attempt.attempt_id}.json') is None,
            'TASK_EXECUTION_APPROVAL_LATE', 'advance execution consent must precede the worker attempt')
        observed = inspect_launch_workspace(workspace)
        _check(not observed.status and observed.observed_head == invocation.source_state.base_commit,
            'TASK_EXECUTION_CANDIDATE_DRIFT', 'approval requires the unchanged admitted base')
        require_resolved_validations(records)
        template = _validation_template(data_root, workspace, selected, protected_files,
            dict(timeout_seconds=timeout_seconds, output_limit_bytes=output_limit_bytes,
                cleanup_timeout_seconds=cleanup_timeout_seconds))
        value = dict(schema_version=APPROVAL_SCHEMA, attempt_id=attempt.attempt_id,
            workspace=str(workspace),
            task_file_digest=canonical_digest(task), invocation_digest=invocation.identity_digest(),
            controller_identity=controller, source_manifest_digest=source,
            test_plan_digest=invocation.test_plan_digest, review_required=review_required,
            validation=template, approved_at=now())
        path = f'operator/task-execution/{attempt.attempt_id}.json'
        existing = _optional(records, path)
        if existing is not None:
            _check({k:v for k,v in existing.items() if k!='approved_at'} == {k:v for k,v in value.items() if k!='approved_at'},
                'TASK_EXECUTION_APPROVAL_CHANGED', 'the sealed execution approval cannot be replaced')
            return TaskRunReport(canonical_json(require_task_execution_approval(data_root, invocation, canonical_digest(task))))
        records.write_bytes(path, (canonical_json(value)+'\n').encode('utf-8'))
        return TaskRunReport(canonical_json(value))


def require_task_execution_approval(data_root, invocation, task_file_digest):
    records = AtomicRecordStore(data_root / 'state')
    value = _optional(records, f'operator/task-execution/{invocation.attempt_id}.json')
    fields = {'schema_version','attempt_id','workspace','task_file_digest','invocation_digest','controller_identity',
        'source_manifest_digest','test_plan_digest','review_required','validation','approved_at'}
    _check(isinstance(value, dict) and set(value) == fields and value['schema_version'] == APPROVAL_SCHEMA
        and value['attempt_id'] == invocation.attempt_id and value['task_file_digest'] == task_file_digest
        and value['invocation_digest'] == invocation.identity_digest()
        and value['controller_identity'] == invocation.authorized_by
        and value['test_plan_digest'] == invocation.test_plan_digest and type(value['review_required']) is bool,
        'TASK_EXECUTION_APPROVAL_REQUIRED', 'exact advance approval of the named local checks and review requirement is required')
    _timestamp(value['approved_at'], 'approved_at')
    # This operator-supplied path is rechecked against the admitted path digest.
    _check(isinstance(value['workspace'], str), 'TASK_EXECUTION_APPROVAL_INVALID', 'workspace path is required')
    workspace = Path(value['workspace'])
    _, selected, source = _authority(data_root, invocation, workspace)
    template = value['validation']
    _check(isinstance(template, dict) and set(template) == {'mode','resource_exposure','commands','protected_inputs','cwd',*LIMITS}
        and isinstance(template['protected_inputs'], list)
        and all(isinstance(item, dict) and set(item)=={'path','digest'} for item in template['protected_inputs']),
        'TASK_EXECUTION_APPROVAL_INVALID', 'invalid approved local command/input set')
    current = _validation_template(data_root, workspace, selected,
        [item['path'] for item in template['protected_inputs']], {key:template[key] for key in LIMITS})
    _check(value['source_manifest_digest'] == source and current == template,
        'TASK_EXECUTION_APPROVAL_CHANGED', 'approved source, command, executable or judging input changed')
    return value


def run_task(data_root, task_file, *, clock=now, cancellation=None, runner_factory=None,
        process_factory=None, candidate_archive_limit_bytes=None, review_id=None):
    """Compose existing operations; no model claim or missing approval can pass."""
    from .task_acceptance import accept_task
    data_root, task_file = Path(data_root).resolve(), Path(task_file).resolve()
    task = _read_task(task_file)
    records = AtomicRecordStore(data_root / 'state')
    invocation = InvocationStoreV3(records.root).read(task['invocation_id'])
    _check(invocation.identity_digest() == task['expected_identity_digest']
        and invocation.authorized_by == task['controller_identity'],
        'RUN_TASK_IDENTITY_MISMATCH', 'task differs from the durable authorization')
    worker, validation, decision, error = None, None, None, None
    status = 'blocked'
    with _exclusive_controller(records.root, 'task-workflow.lock'):
        try:
            consent = require_task_execution_approval(data_root, invocation, canonical_digest(task))
            options = {} if runner_factory is None else {'runner_factory':runner_factory}
            worker = run_worker(data_root, task_file, clock=clock, cancellation=cancellation,
                expected_task_file_digest=canonical_digest(task),
                candidate_archive_limit_bytes=candidate_archive_limit_bytes, **options)
            value = worker.to_dict()
            if value['status'] != 'completed_claim':
                status = 'blocked' if value['stop_state'] in {'uncertain','not_started'} or value['status']=='blocked' else 'failed'
                error = value['error'] or {'code':'TASK_WORKER_INCOMPLETE','message':'worker did not return a completed claim'}
            else:
                refreshed = _base(data_root, invocation.attempt_id, worker.digest(), task['controller_identity'])
                current = require_task_execution_approval(data_root, refreshed[2], canonical_digest(task))
                _check(current == consent, 'TASK_EXECUTION_APPROVAL_CHANGED', 'execution consent changed during worker execution')
                if _optional(records, f'operator/validation-approvals/{invocation.attempt_id}.json') is None:
                    approve_local_validation(data_root, attempt_id=invocation.attempt_id,
                        expected_outcome_digest=worker.digest(), controller_identity=task['controller_identity'],
                        protected_files=[item['path'] for item in consent['validation']['protected_inputs']],
                        acknowledge_unsandboxed=True, **{key:consent['validation'][key] for key in LIMITS})
                approval = _approval(*refreshed, data_root, task['controller_identity'])
                _check(all(approval.get(key)==value for key,value in consent['validation'].items()),
                    'TASK_EXECUTION_APPROVAL_CHANGED', 'candidate-specific check approval differs from advance consent')
                validation_id = 'VALIDATION-' + worker.digest()[7:47]
                options = {} if process_factory is None else {'process_factory':process_factory}
                validation = validate_task(data_root, attempt_id=invocation.attempt_id,
                    expected_outcome_digest=worker.digest(), controller_identity=task['controller_identity'],
                    validation_id=validation_id, clock=clock, cancellation=cancellation, **options)
                decision = accept_task(data_root, attempt_id=invocation.attempt_id,
                    expected_outcome_digest=worker.digest(), controller_identity=task['controller_identity'],
                    validation_id=validation_id, expected_validation_digest=validation.digest(),
                    review_id=review_id, clock=clock)
                status = decision.to_dict()['status']
        except (LabValidationError, OSError, KeyboardInterrupt) as exc:
            error = dict(code='TASK_CANCELLED' if isinstance(exc,KeyboardInterrupt) else getattr(exc,'code','TASK_WORKFLOW_FAILED'),
                message=str(exc)[:2048] or 'task interrupted')
        value = worker.to_dict() if worker else None
        result = dict(schema_version='worker-lab-task-run:v1', attempt_id=invocation.attempt_id,
            invocation_id=invocation.invocation_id, status=status, accepted=status=='accepted',
            worker_outcome=value, outcome_digest=worker.digest() if worker else None,
            workspace=value['workspace'] if value else str(Path(task['workspace_root'])/invocation.attempt_id),
            candidate=value['candidate'] if value else None, validation=validation.to_dict() if validation else None,
            acceptance=decision.to_dict() if decision else None, error=error)
        records.write_bytes(f'task-runs/{invocation.attempt_id}/{canonical_digest(result)[7:]}.json',
            (canonical_json(result)+'\n').encode('utf-8'))
        return TaskRunReport(canonical_json(result))
