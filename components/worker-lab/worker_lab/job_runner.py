"""M07: one durable job reservation; no dispatch loop, retry or promotion."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
import json
from pathlib import Path
import re

from .attempt_store import AttemptStore
from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .integration_v3 import InvocationState
from .invocation_store_v3 import InvocationStoreV3
from .job_admission import JobAuthorityProfile, JobTaskDefinition, load_task_authorities
from .job_plan import JobPlan, identity
from .models import AttemptState, _timestamp
from .operator_control import validate_controller_identity
from .pi_supervision import _exclusive_controller, _require_resolved_launches, now
from .process_custody import CustodyState, ProcessCustodyStore
from .protected_validation import _optional, require_resolved_validations
from .storage import AtomicRecordStore

SCHEMA = 'worker-lab-job:v1'
STOP_RECONCILIATION_SCHEMA = 'worker-lab-job-stop-reconciliation:v1'
TASK_STATES = {'pending', 'reserved', 'accepted', 'failed', 'blocked', 'pending_review'}


def _require(condition, code, message):
    if not condition:
        raise LabValidationError(code, message)


def _digest(value):
    _require(isinstance(value, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', value),
        'JOB_IDENTITY_INVALID', 'an exact digest is required')
    return value


def _millis(value):
    return int(_timestamp(value, 'job timestamp').timestamp() * 1000)


def _deadline(started, seconds):
    return (_timestamp(started, 'reserved_at') + timedelta(seconds=seconds)).isoformat().replace('+00:00', 'Z')


@dataclass(frozen=True)
class JobRecord:
    payload: str

    @classmethod
    def from_mapping(cls, value):
        fields = {'schema_version', 'job_id', 'plan', 'plan_digest', 'controller_identity',
            'created_at', 'updated_at', 'generation', 'status', 'active', 'tasks', 'blocker'}
        _require(isinstance(value, dict) and set(value) == fields and value['schema_version'] == SCHEMA,
            'JOB_RECORD_INVALID', 'job record has an unsupported schema')
        identity(value['job_id'], 'job_id')
        validate_controller_identity(value['controller_identity'])
        plan = JobPlan.from_mapping(value['plan'])
        _require(value['plan_digest'] == plan.digest(), 'JOB_PLAN_APPROVAL_MISMATCH', 'job plan identity changed')
        _require(type(value['generation']) is int and value['generation'] >= 0
            and value['status'] in {'ready', 'active', 'blocked', 'complete'}
            and _timestamp(value['updated_at'], 'updated_at') >= _timestamp(value['created_at'], 'created_at')
            and isinstance(value['tasks'], dict) and set(value['tasks']) == {task.task_id for task in plan.tasks},
            'JOB_RECORD_INVALID', 'invalid job status, task set or timestamps')
        reserved = []
        for task in plan.tasks:
            item = value['tasks'][task.task_id]
            _require(isinstance(item, dict) and set(item) == {'state', 'dependencies', 'attempts', 'acceptance', 'artifact', 'blocker'}
                and item['state'] in TASK_STATES and item['dependencies'] == list(task.dependencies)
                and isinstance(item['attempts'], list) and len(item['attempts']) <= task.budget.max_attempts,
                'JOB_RECORD_INVALID', 'task state or attempts differ from the plan')
            for reservation in item['attempts']:
                _require(isinstance(reservation, dict) and set(reservation) == {'reservation_id', 'reserved_at',
                    'deadline_at', 'attempt_id', 'invocation_id', 'invocation_digest', 'run_reference', 'run_digest'},
                    'JOB_RECORD_INVALID', 'invalid task reservation')
                _digest(reservation['reservation_id'])
                _require(_deadline(reservation['reserved_at'], task.budget.max_wall_seconds) == reservation['deadline_at'],
                    'JOB_BUDGET_INVALID', 'reservation deadline differs from the approved task budget')
                bound = [reservation[key] is not None for key in ('attempt_id', 'invocation_id', 'invocation_digest')]
                _require(all(bound) or not any(bound), 'JOB_RECORD_INVALID', 'partial attempt binding is uncertain')
                if all(bound):
                    identity(reservation['attempt_id'], 'attempt_id')
                    identity(reservation['invocation_id'], 'invocation_id')
                    _digest(reservation['invocation_digest'])
                _require((reservation['run_reference'] is None) == (reservation['run_digest'] is None),
                    'JOB_RECORD_INVALID', 'partial task-result reference')
                if reservation['run_digest'] is not None:
                    _digest(reservation['run_digest'])
            if item['state'] == 'pending':
                _require(not item['attempts'] and item['acceptance'] is None and item['artifact'] is None,
                    'JOB_RECORD_INVALID', 'pending task already has execution state')
            if item['state'] in {'reserved', 'pending_review'}:
                _require(len(item['attempts']) == 1, 'JOB_RECORD_INVALID', 'reserved task requires one attempt slot')
                reserved.append({'task_id': task.task_id, 'reservation_id': item['attempts'][-1]['reservation_id']})
            if item['state'] == 'accepted':
                _require(bool(item['attempts']) and isinstance(item['acceptance'], dict)
                    and set(item['acceptance']) == {'path', 'digest', 'candidate_digest'},
                    'JOB_RECORD_INVALID', 'accepted task requires exact protected evidence')
                _digest(item['acceptance']['digest']); _digest(item['acceptance']['candidate_digest'])
                if item['artifact'] is not None:
                    _require(isinstance(item['artifact'], dict) and set(item['artifact']) == {'path', 'digest'},
                        'JOB_RECORD_INVALID', 'accepted artifact must have one exact receipt reference')
                    _digest(item['artifact']['digest'])
            else:
                _require(item['acceptance'] is None and item['artifact'] is None,
                    'JOB_RECORD_INVALID', 'unaccepted task cannot name accepted output')
        _require(len(reserved) <= 1 and value['active'] == (reserved[0] if reserved else None),
            'JOB_RECORD_INVALID', 'job must have exactly one consistent active reservation')
        _require(value['status'] != 'complete' or (not reserved and all(t['state'] == 'accepted' for t in value['tasks'].values())),
            'JOB_RECORD_INVALID', 'incomplete work cannot complete a job')
        _require(value['status'] != 'active' or bool(reserved), 'JOB_RECORD_INVALID', 'active job lacks a reservation')
        return cls(canonical_json(value))

    def to_dict(self):
        return json.loads(self.payload)

    def to_json(self):
        return self.payload

    def digest(self):
        return canonical_digest(self.to_dict())


def _path(job_id):
    return f'jobs/{identity(job_id, "job_id")}.json'


def read_job(data_root, job_id):
    return AtomicRecordStore(Path(data_root) / 'state').read(_path(job_id), JobRecord.from_mapping)


def _read(records, job_id, controller):
    job = records.read(_path(job_id), JobRecord.from_mapping)
    _require(job.to_dict()['controller_identity'] == validate_controller_identity(controller),
        'JOB_CONTROLLER_MISMATCH', 'job belongs to a different approved controller')
    return job


def _save(records, value, *, occurred_at):
    _require(_timestamp(occurred_at, 'occurred_at') >= _timestamp(value['updated_at'], 'updated_at'),
        'JOB_TIME_INVALID', 'job clock moved backward')
    value.update(updated_at=occurred_at, generation=value['generation'] + 1)
    result = JobRecord.from_mapping(value)
    records.write(_path(value['job_id']), result)
    return result


def _stop_reconciliation_path(attempt_id):
    return f'job-stop-reconciliations/{identity(attempt_id, "attempt_id")}.json'


def _verified_stop_reconciliation(records, *, invocation, worker_outcome=None):
    proof = records.read(_stop_reconciliation_path(invocation.attempt_id), lambda value: value)
    fields = {'schema_version', 'attempt_id', 'invocation_id', 'invocation_digest',
        'controller_identity', 'basis', 'custody_digest', 'absence_evidence_digest',
        'worker_outcome_digest', 'recorded_at'}
    _require(isinstance(proof, dict) and set(proof) == fields
        and proof['schema_version'] == STOP_RECONCILIATION_SCHEMA
        and proof['attempt_id'] == invocation.attempt_id
        and proof['invocation_id'] == invocation.invocation_id
        and proof['invocation_digest'] == invocation.identity_digest()
        and proof['controller_identity'] == invocation.authorized_by
        and proof['basis'] in {'not-started', 'verified-absence'},
        'JOB_STOP_RECONCILIATION_INVALID', 'stop reconciliation identity differs')
    _timestamp(proof['recorded_at'], 'recorded_at')
    if worker_outcome is not None:
        _require(isinstance(worker_outcome, dict)
            and worker_outcome.get('attempt_id') == invocation.attempt_id
            and worker_outcome.get('invocation_id') == invocation.invocation_id
            and worker_outcome.get('invocation_digest') == invocation.identity_digest(),
            'JOB_STOP_RECONCILIATION_INVALID', 'worker outcome differs from stop reconciliation')
        if proof['worker_outcome_digest'] is not None:
            _require(proof['worker_outcome_digest'] == canonical_digest(worker_outcome),
                'JOB_STOP_RECONCILIATION_INVALID', 'worker outcome changed after reconciliation')
    else:
        _require(proof['worker_outcome_digest'] is None,
            'JOB_STOP_RECONCILIATION_INVALID', 'reconciliation names a missing worker outcome')
    if proof['basis'] == 'not-started':
        _require(proof['custody_digest'] is None and proof['absence_evidence_digest'] is None
            and _optional(records, f'launch-intents/{invocation.invocation_id}.json') is None
            and _optional(records, f'worker-outcomes/{invocation.attempt_id}.json') is None
            and invocation.state in {InvocationState.AUTHORIZED, InvocationState.ABORTED, InvocationState.REJECTED},
            'JOB_STOP_RECONCILIATION_INVALID', 'not-started reconciliation has execution evidence')
    else:
        custody = ProcessCustodyStore(records.root).read(invocation.invocation_id)
        _require(custody.invocation_digest == invocation.identity_digest()
            and custody.state is CustodyState.ABSENCE_VERIFIED
            and custody.active_workload_count == 0
            and custody.absence_evidence_digest is not None
            and custody.digest() == proof['custody_digest']
            and custody.absence_evidence_digest == proof['absence_evidence_digest'],
            'JOB_STOP_RECONCILIATION_INVALID', 'verified absence evidence changed')
    return proof


def record_stop_reconciliation(data_root, *, invocation_id, controller_identity, clock=now):
    """Record exact no-start/absence proof; never infer a worker result."""
    records = AtomicRecordStore(Path(data_root) / 'state')
    with _exclusive_controller(records.root, 'job-controller.lock'):
        invocation = InvocationStoreV3(records.root).read(invocation_id)
        controller = validate_controller_identity(controller_identity)
        _require(invocation.authorized_by == controller,
            'JOB_CONTROLLER_MISMATCH', 'reconciliation controller differs from invocation authorization')
        run_intent = _optional(records, f'run-task-intents/{invocation.attempt_id}.json')
        _require(isinstance(run_intent, dict)
            and run_intent.get('invocation_id') == invocation.invocation_id
            and run_intent.get('invocation_digest') == invocation.identity_digest(),
            'JOB_STOP_RECONCILIATION_INVALID', 'reconciliation requires the exact durable run intent')
        outcome = _optional(records, f'worker-outcomes/{invocation.attempt_id}.json')
        launch = _optional(records, f'launch-intents/{invocation.invocation_id}.json')
        custody = None
        try:
            custody = ProcessCustodyStore(records.root).read(invocation.invocation_id)
        except LabValidationError as exc:
            if exc.code != 'STORAGE_RECORD_MISSING':
                raise
        if launch is None and custody is None and outcome is None and invocation.state in {
                InvocationState.AUTHORIZED, InvocationState.ABORTED, InvocationState.REJECTED}:
            basis, custody_digest, absence_digest = 'not-started', None, None
        else:
            _require(custody is not None and custody.invocation_digest == invocation.identity_digest()
                and custody.state is CustodyState.ABSENCE_VERIFIED
                and custody.active_workload_count == 0
                and custody.absence_evidence_digest is not None,
                'JOB_PRIOR_UNCERTAIN', 'exact process absence is not proven')
            basis = 'verified-absence'
            custody_digest = custody.digest()
            absence_digest = custody.absence_evidence_digest
        value = dict(schema_version=STOP_RECONCILIATION_SCHEMA,
            attempt_id=invocation.attempt_id, invocation_id=invocation.invocation_id,
            invocation_digest=invocation.identity_digest(), controller_identity=controller,
            basis=basis, custody_digest=custody_digest, absence_evidence_digest=absence_digest,
            worker_outcome_digest=canonical_digest(outcome) if outcome is not None else None,
            recorded_at=clock())
        existing = _optional(records, _stop_reconciliation_path(invocation.attempt_id))
        if existing is not None:
            _verified_stop_reconciliation(records, invocation=invocation, worker_outcome=outcome)
            immutable = {key:value[key] for key in value if key != 'recorded_at'}
            _require({key:existing[key] for key in existing if key != 'recorded_at'} == immutable,
                'JOB_STOP_RECONCILIATION_INVALID', 'existing stop reconciliation differs')
            return existing
        records.write_bytes(_stop_reconciliation_path(invocation.attempt_id),
            (canonical_json(value) + '\n').encode('utf-8'))
        _verified_stop_reconciliation(records, invocation=invocation, worker_outcome=outcome)
        return value


def block_active_reconciliation(data_root, job_id, *, controller_identity, reservation_id,
                                code, message, clock=now):
    """Close one consumed reservation only when no active workload remains."""
    records = AtomicRecordStore(Path(data_root) / 'state')
    with _exclusive_controller(records.root, 'job-controller.lock'):
        job = _read(records, job_id, controller_identity)
        value = job.to_dict()
        task_id, item, slot = _reservation(value, reservation_id)
        _require(slot['run_reference'] is None,
            'JOB_RECONCILIATION_RESULT_AVAILABLE', 'record the retained task result instead of blocking it')
        safe = slot['attempt_id'] is None
        if slot['attempt_id'] is not None:
            invocation = InvocationStoreV3(records.root).read(slot['invocation_id'])
            _require(invocation.attempt_id == slot['attempt_id']
                and invocation.identity_digest() == slot['invocation_digest'],
                'JOB_INVOCATION_MISMATCH', 'reserved invocation identity changed')
            run_intent = _optional(records, f'run-task-intents/{slot["attempt_id"]}.json')
            launch = _optional(records, f'launch-intents/{slot["invocation_id"]}.json')
            outcome = _optional(records, f'worker-outcomes/{slot["attempt_id"]}.json')
            if run_intent is None and launch is None and outcome is None and invocation.state in {
                    InvocationState.PREPARED, InvocationState.AUTHORIZED,
                    InvocationState.REJECTED, InvocationState.ABORTED}:
                safe = True
            elif outcome is not None and outcome.get('stop_state') in {'absence_verified', 'not_started'}:
                safe = True
            elif run_intent is not None:
                _verified_stop_reconciliation(records, invocation=invocation, worker_outcome=outcome)
                safe = True
        _require(safe, 'JOB_PRIOR_UNCERTAIN',
            'active reservation lacks exact no-start or process-absence evidence')
        blocker = dict(code=str(code), message=str(message))
        item['state'] = 'blocked'
        item['blocker'] = blocker
        value['active'] = None
        value['status'] = 'blocked'
        value['blocker'] = dict(task_id=task_id, **blocker)
        return _save(records, value, occurred_at=clock())


def _stopped(records):
    _require_resolved_launches(records, ProcessCustodyStore(records.root))
    require_resolved_validations(records)
    for path in records.list_paths('run-task-intents'):
        intent = records.read(path, lambda x: x)
        invocation = InvocationStoreV3(records.root).read(intent['invocation_id'])
        outcome = _optional(records, f'worker-outcomes/{invocation.attempt_id}.json')
        if isinstance(outcome, dict) and outcome.get('stop_state') in {'absence_verified', 'not_started'}:
            continue
        try:
            _verified_stop_reconciliation(records, invocation=invocation, worker_outcome=outcome)
        except LabValidationError as exc:
            raise LabValidationError('JOB_PRIOR_UNCERTAIN',
                'an earlier worker transaction lacks resolved stop evidence') from exc


def create_job(data_root, *, job_id, plan, approved_plan_digest, controller_identity, clock=now):
    """Register one approved immutable plan; this operation never admits a task."""
    data_root = Path(data_root)
    controller = validate_controller_identity(controller_identity)
    plan = JobPlan.from_mapping(plan.to_dict() if isinstance(plan, JobPlan) else plan)
    _require(plan.digest() == approved_plan_digest, 'JOB_PLAN_APPROVAL_MISMATCH', 'explicit approval must pin the exact plan')
    identity(job_id, 'job_id')
    records = AtomicRecordStore(data_root / 'state')
    with _exclusive_controller(records.root, 'job-controller.lock'):
        existing = _optional(records, _path(job_id))
        if existing is not None:
            record = JobRecord.from_mapping(existing)
            _require(existing['plan_digest'] == plan.digest() and existing['controller_identity'] == controller,
                'JOB_IDENTITY_CHANGED', 'job identity already names another approved plan/controller')
            return record
        # Reuse the complete admission validator for every existing authority.
        for task in plan.tasks:
            profile = AtomicRecordStore(data_root / 'job-authorities').read(
                f'{task.authority_ref.profile_id}/v{task.authority_ref.version}.json', JobAuthorityProfile.from_mapping)
            JobTaskDefinition.from_mapping(dict(schema_version='worker-lab-job-task:v1', plan=plan.to_dict(),
                task_id=task.task_id, profile=profile.to_dict(), approved_by=controller, approved_plan_digest=plan.digest()))
        # Existing admission uses these exact bytes. Orphan plan storage after a
        # crash carries no reservation or execution permission.
        records.write_bytes(f'job-plans/{plan.plan_id}/v{plan.revision}.json', plan.to_json().encode('utf-8'))
        created = clock()
        record = JobRecord.from_mapping(dict(schema_version=SCHEMA, job_id=job_id, plan=plan.to_dict(),
            plan_digest=plan.digest(), controller_identity=controller, created_at=created, updated_at=created,
            generation=0, status='ready', active=None, blocker=None,
            tasks={task.task_id: dict(state='pending', dependencies=list(task.dependencies), attempts=[],
                acceptance=None, artifact=None, blocker=None) for task in plan.tasks}))
        records.write(_path(job_id), record)
        return record


def _accepted(records, item):
    ref = item['acceptance']
    _require(isinstance(ref, dict), 'JOB_DEPENDENCY_UNACCEPTED', 'dependency has no accepted artifact identity')
    accepted = records.read(ref['path'], lambda x: x)
    last = item['attempts'][-1]
    _require(isinstance(accepted, dict) and accepted.get('schema_version') == 'worker-lab-task-acceptance:v1'
        and accepted.get('status') == 'accepted' and accepted.get('accepted') is True
        and accepted.get('attempt_id') == last['attempt_id']
        and canonical_digest(accepted) == ref['digest']
        and isinstance(accepted.get('candidate'), dict)
        and accepted['candidate'].get('content_digest') == ref['candidate_digest'],
        'JOB_DEPENDENCY_CHANGED', 'protected predecessor acceptance is missing or changed')
    return accepted


def _artifact(data_root, item):
    ref = item['artifact']
    _require(ref is not None, 'JOB_INPUT_PROMOTION_REQUIRED', 'dependent execution requires the protected M08 snapshot lineage')
    from .accepted_snapshot import verify_accepted_snapshot
    report = verify_accepted_snapshot(data_root, reference=ref['path'], expected_digest=ref['digest'])
    value = report.to_dict()
    _require(value['attempt_id'] == item['attempts'][-1]['attempt_id']
        and value['acceptance_digest'] == item['acceptance']['digest']
        and value['candidate_digest'] == item['acceptance']['candidate_digest'],
        'JOB_ARTIFACT_MISMATCH', 'snapshot receipt belongs to different accepted task output')
    return value


def attach_accepted_artifact(data_root, job_id, *, task_id, controller_identity,
                             acceptance_digest, artifact_reference, artifact_digest, clock=now):
    """Attach only a verified M08 snapshot; never promote or fabricate lineage."""
    data_root = Path(data_root)
    records = AtomicRecordStore(data_root / 'state')
    with _exclusive_controller(records.root, 'job-controller.lock'):
        job = _read(records, job_id, controller_identity)
        value = job.to_dict()
        _require(task_id in value['tasks'], 'JOB_TASK_MISSING', 'task is not in the approved job')
        item = value['tasks'][task_id]
        _require(item['state'] == 'accepted' and item['acceptance']['digest'] == _digest(acceptance_digest),
            'JOB_ACCEPTANCE_CHANGED', 'snapshot requires the exact accepted task identity')
        _accepted(records, item)
        artifact = {'path': artifact_reference, 'digest': _digest(artifact_digest)}
        _require(item['artifact'] is None or item['artifact'] == artifact,
            'JOB_ARTIFACT_MISMATCH', 'accepted artifact lineage is immutable')
        unchanged = item['artifact'] == artifact
        item['artifact'] = artifact
        _artifact(data_root, item)
        return job if unchanged else _save(records, value, occurred_at=clock())


def reserve_next_task(data_root, job_id, *, controller_identity, expected_job_digest, clock=now):
    """Consume one task attempt slot before admission; a restart cannot reselect it."""
    records = AtomicRecordStore(Path(data_root) / 'state')
    with _exclusive_controller(records.root, 'job-controller.lock'):
        job = _read(records, job_id, controller_identity)
        _require(job.digest() == _digest(expected_job_digest), 'JOB_STATE_CHANGED', 'reload job status before selecting work')
        value = job.to_dict()
        _require(value['active'] is None, 'JOB_TASK_RESERVED', 'existing reservation must be reconciled; no replacement is allowed')
        _require(value['status'] == 'ready', 'JOB_NOT_RUNNABLE', 'job has completed or requires attention')
        for other in records.list_paths('jobs'):
            active = records.read(other, JobRecord.from_mapping).to_dict()
            _require(active['active'] is None, 'JOB_CONTROLLER_BUSY', 'another job has an unresolved reservation')
        _stopped(records)
        plan = JobPlan.from_mapping(value['plan'])
        task = next((task for task in plan.tasks if value['tasks'][task.task_id]['state'] == 'pending'
            and all(value['tasks'][dep]['state'] == 'accepted' for dep in task.dependencies)), None)
        _require(task is not None, 'JOB_DEPENDENCY_UNACCEPTED', 'no task has accepted prerequisites')
        for dep in task.dependencies:
            _accepted(records, value['tasks'][dep])
        item = value['tasks'][task.task_id]
        _require(len(item['attempts']) < task.budget.max_attempts, 'JOB_ATTEMPT_BUDGET_EXHAUSTED', 'task attempt budget exhausted')
        reserved_at = clock()
        reservation_id = canonical_digest(dict(job_id=job_id, plan_digest=plan.digest(), task_id=task.task_id,
            attempt_number=len(item['attempts']) + 1, reserved_at=reserved_at))
        item['attempts'].append(dict(reservation_id=reservation_id, reserved_at=reserved_at,
            deadline_at=_deadline(reserved_at, task.budget.max_wall_seconds), attempt_id=None,
            invocation_id=None, invocation_digest=None, run_reference=None, run_digest=None))
        item['state'] = 'reserved'
        value.update(status='active', active={'task_id': task.task_id, 'reservation_id': reservation_id})
        return _save(records, value, occurred_at=reserved_at)


def _reservation(value, reservation_id):
    _require(value['active'] is not None and value['active']['reservation_id'] == _digest(reservation_id),
        'JOB_RESERVATION_MISMATCH', 'the exact active reservation is required')
    task_id = value['active']['task_id']
    item = value['tasks'][task_id]
    return task_id, item, item['attempts'][-1]


def _input_snapshot(data_root, value, task_id):
    """Select a verified snapshot containing every already accepted job change.

    Declared dependencies govern eligibility. Input lineage additionally retains
    earlier independent work on the same target; divergent histories require
    attention and are never merged or reset implicitly.
    """
    from .accepted_snapshot import _git_runner
    from .workspace import _git
    _require(task_id in value['tasks'], 'JOB_TASK_MISSING', 'task is not in the approved job')
    records = AtomicRecordStore(Path(data_root) / 'state')
    receipts = []
    for prior_id, item in sorted(value['tasks'].items()):
        if prior_id == task_id or item['state'] != 'accepted':
            continue
        _accepted(records, item)
        receipt = _artifact(data_root, item)
        _require(receipt['controller_identity'] == value['controller_identity'],
            'JOB_INPUT_CONTROLLER_MISMATCH', 'accepted input belongs to another controller')
        receipts.append(receipt)
    if not receipts:
        return None
    required = {receipt['snapshot_commit'] for receipt in receipts}
    # Multiple accepted no-ops may identify one commit. Stable receipt identity
    # breaks this tie independently of dictionary or artifact-directory order.
    for receipt in sorted(receipts, key=lambda item: item['reference']):
        history = _git(['-C', receipt['repository'], '-c', 'core.fsmonitor=false',
            'rev-list', receipt['snapshot_commit'], '--'], 'verify complete accepted job lineage',
            _git_runner(receipt['recorded_at']), 30).stdout.splitlines()
        if required <= set(history):
            return receipt
    _require(False, 'JOB_INPUT_DIVERGED',
        'no accepted snapshot contains every prior accepted task; automatic merging is unavailable')


def _require_input_snapshot(data_root, value, task_id, definition):
    receipt = _input_snapshot(data_root, value, task_id)
    binding = definition.input_binding
    if receipt is None:
        _require(binding is None, 'JOB_INPUT_UNEXPECTED',
            'the first job task must use its original approved input')
        return
    _require(binding is not None, 'JOB_INPUT_REQUIRED',
        'later job tasks require the snapshot containing all prior accepted changes')
    observed = binding.to_dict()
    _require(observed['snapshot_reference'] == receipt['reference']
        and observed['snapshot_digest'] == canonical_digest(receipt)
        and observed['repository'] == receipt['repository'],
        'JOB_INPUT_MISMATCH', 'admitted task does not use the selected accepted job snapshot')


def _binding(data_root, value, task_id, attempt_id, invocation_id):
    records = AtomicRecordStore(data_root / 'state')
    attempt = AttemptStore(records.root).read(attempt_id)
    definition, *_ = load_task_authorities(data_root, attempt)
    _require(isinstance(definition, JobTaskDefinition) and definition.plan.digest() == value['plan_digest']
        and definition.task_id == task_id and definition.approved_by == value['controller_identity'],
        'JOB_ATTEMPT_MISMATCH', 'attempt is not the reserved task from this exact approved plan')
    _require_input_snapshot(data_root, value, task_id, definition)
    invocation = InvocationStoreV3(records.root).read(invocation_id)
    _require(invocation.attempt_id == attempt_id and invocation.exercise_digest == definition.digest()
        and invocation.task_digest == attempt.task_digest,
        'JOB_INVOCATION_MISMATCH', 'prepared invocation does not bind the reserved admitted attempt')
    return attempt, invocation


def bind_job_attempt(data_root, job_id, *, controller_identity, reservation_id,
                     attempt_id, invocation_id, expected_invocation_digest, clock=now):
    """Bind one prepared attempt. No replacement or silent admission on restart."""
    data_root = Path(data_root)
    records = AtomicRecordStore(data_root / 'state')
    with _exclusive_controller(records.root, 'job-controller.lock'):
        job = _read(records, job_id, controller_identity)
        value = job.to_dict()
        task_id, item, slot = _reservation(value, reservation_id)
        attempt, invocation = _binding(data_root, value, task_id, attempt_id, invocation_id)
        _require(invocation.identity_digest() == _digest(expected_invocation_digest),
            'JOB_INVOCATION_MISMATCH', 'invocation differs from the requested binding')
        binding = dict(attempt_id=attempt_id, invocation_id=invocation_id, invocation_digest=invocation.identity_digest())
        if slot['attempt_id'] is not None:
            _require(all(slot[key] == val for key, val in binding.items()),
                'JOB_ATTEMPT_ALREADY_BOUND', 'reservation already has a different attempt')
            return job
        _require(attempt.state is AttemptState.READY and invocation.state is InvocationState.PREPARED,
            'JOB_APPROVAL_LATE', 'job binding must precede invocation authorization')
        occurred_at = clock()
        _require(_millis(slot['reserved_at']) <= _millis(occurred_at) < _millis(slot['deadline_at']),
            'JOB_WALL_BUDGET_EXHAUSTED', 'reserved task time budget expired')
        for path in records.list_paths('jobs'):
            other = records.read(path, JobRecord.from_mapping).to_dict()
            for other_task in other['tasks'].values():
                _require(all(prior['attempt_id'] != attempt_id for prior in other_task['attempts']),
                    'JOB_ATTEMPT_ALREADY_BOUND', 'an admitted attempt may belong to only one reservation')
        slot.update(binding)
        return _save(records, value, occurred_at=occurred_at)


@contextmanager
def job_authorization_gate(data_root, invocation, *, controller_identity, clock=now):
    """Hold the job lock across the caller's existing authorization transaction.

    The caller must also enforce yielded deadline_unix_ms through the existing
    worker/validator supervision path. This gate alone never enables execution.
    """
    data_root = Path(data_root)
    records = AtomicRecordStore(data_root / 'state')
    with _exclusive_controller(records.root, 'job-controller.lock'):
        found = []
        for path in records.list_paths('jobs'):
            value = records.read(path, JobRecord.from_mapping).to_dict()
            if value['active'] is not None:
                task_id, item, slot = _reservation(value, value['active']['reservation_id'])
                if slot['attempt_id'] == invocation.attempt_id:
                    found.append((value, task_id, item, slot))
        _require(len(found) == 1, 'JOB_RESERVATION_REQUIRED', 'job task authorization requires one durable reservation')
        value, task_id, item, slot = found[0]
        _require(value['status'] == 'active' and value['controller_identity'] == validate_controller_identity(controller_identity)
            and slot['invocation_id'] == invocation.invocation_id and slot['invocation_digest'] == invocation.identity_digest(),
            'JOB_INVOCATION_MISMATCH', 'authorization differs from the reserved controller/invocation')
        _binding(data_root, value, task_id, invocation.attempt_id, invocation.invocation_id)
        for dep in item['dependencies']:
            _require(value['tasks'][dep]['state'] == 'accepted', 'JOB_DEPENDENCY_UNACCEPTED', 'predecessor did not pass')
            _accepted(records, value['tasks'][dep])
            _artifact(data_root, value['tasks'][dep])
        current = _millis(clock())
        _require(_millis(slot['reserved_at']) <= current < _millis(slot['deadline_at']),
            'JOB_WALL_BUDGET_EXHAUSTED', 'task wall-time budget expired or clock moved backward')
        yield dict(job_id=value['job_id'], task_id=task_id, reservation_id=slot['reservation_id'],
            deadline_unix_ms=_millis(slot['deadline_at']), remaining_milliseconds=_millis(slot['deadline_at']) - current)



def job_execution_allowance(data_root, invocation, *, controller_identity, clock=now):
    """Return the still-valid absolute reservation deadline for one bound job task.

    This reuses the M07 authorization gate rather than creating a second job
    authority contract. The returned absolute deadline is immutable across
    preparation, worker execution, validation and restart.
    """
    with job_authorization_gate(data_root, invocation,
            controller_identity=controller_identity, clock=clock) as allowance:
        return dict(allowance)

def record_task_result(data_root, job_id, *, controller_identity, reservation_id, task_run_digest, clock=now):
    """Attach the stored M06 result; neither caller-supplied verdicts nor retries."""
    from .task_acceptance import accept_task
    data_root = Path(data_root)
    records = AtomicRecordStore(data_root / 'state')
    with _exclusive_controller(records.root, 'job-controller.lock'):
        job = _read(records, job_id, controller_identity)
        value = job.to_dict()
        _digest(reservation_id); _digest(task_run_digest)
        matching = [(item, slot) for item in value['tasks'].values() for slot in item['attempts']
            if slot['reservation_id'] == reservation_id and slot['run_digest'] == task_run_digest]
        if matching:
            _require(len(matching) == 1, 'JOB_RECORD_INVALID', 'duplicate result reservation')
            item, slot = matching[0]
            saved = records.read(slot['run_reference'], lambda x: x)
            _require(canonical_digest(saved) == task_run_digest, 'JOB_RESULT_CHANGED', 'retained task result changed')
            if item['state'] == 'accepted':
                _accepted(records, item)
            return job
        task_id, item, slot = _reservation(value, reservation_id)
        _require(slot['attempt_id'] is not None, 'JOB_ATTEMPT_MISSING', 'reservation lacks an admitted attempt')
        attempt, invocation = _binding(data_root, value, task_id, slot['attempt_id'], slot['invocation_id'])
        _require(invocation.identity_digest() == slot['invocation_digest'],
            'JOB_INVOCATION_MISMATCH', 'reserved invocation identity changed before result recording')
        reference = f'task-runs/{attempt.attempt_id}/{_digest(task_run_digest)[7:]}.json'
        report = records.read(reference, lambda x: x)
        _require(isinstance(report, dict) and report.get('schema_version') == 'worker-lab-task-run:v1'
            and canonical_digest(report) == task_run_digest and report.get('attempt_id') == attempt.attempt_id
            and report.get('invocation_id') == invocation.invocation_id
            and report.get('status') in {'accepted', 'failed', 'blocked', 'pending_review'}
            and report.get('accepted') is (report['status'] == 'accepted'),
            'JOB_RESULT_INVALID', 'stored task result differs from the reserved attempt')
        worker = report.get('worker_outcome')
        if worker is not None:
            actual = AttemptStore(records.root).read_outcome(attempt.attempt_id)
            _require(actual.to_dict() == worker and actual.digest() == report.get('outcome_digest'),
                'JOB_RESULT_CHANGED', 'worker outcome differs from the durable result')
        if report['status'] == 'accepted':
            acceptance = records.read(f'task-acceptances/{attempt.attempt_id}.json', lambda x: x)
            _require(acceptance == report.get('acceptance'), 'JOB_ACCEPTANCE_CHANGED', 'task result lacks matching protected acceptance')
            current = accept_task(data_root, attempt_id=attempt.attempt_id,
                expected_outcome_digest=acceptance['outcome_digest'], controller_identity=controller_identity,
                validation_id=acceptance['validation_id'], expected_validation_digest=acceptance['validation_digest'],
                review_id=acceptance['review_id'], clock=clock).to_dict()
            _require(current == acceptance and current.get('accepted') is True,
                'JOB_ACCEPTANCE_CHANGED', 'acceptance no longer verifies against the exact retained evidence')
            completed = (_millis(worker['recorded_at']), _millis(report['validation']['completed_at']), _millis(acceptance['recorded_at']))
            _require(_millis(slot['reserved_at']) <= min(completed) and max(completed) <= _millis(slot['deadline_at']),
                'JOB_WALL_BUDGET_EXHAUSTED', 'task completion evidence lies outside its approved wall-time budget')
            item['acceptance'] = dict(path=f'task-acceptances/{attempt.attempt_id}.json',
                digest=canonical_digest(acceptance), candidate_digest=acceptance['candidate']['content_digest'])
            item['state'] = 'accepted'
            item['blocker'] = None
            value['active'] = None
            value['blocker'] = None
            value['status'] = 'complete' if all(t['state'] == 'accepted' for t in value['tasks'].values()) else 'ready'
        else:
            # Missing or uncertain process state preserves the active reservation.
            # No later selection can infer that an in-flight worker stopped.
            absent = worker is not None and worker.get('stop_state') in {'absence_verified', 'not_started'}
            absent = absent and (report.get('validation') is None or report['validation'].get('all_validators_absent') is True)
            if report['status'] == 'pending_review':
                item['state'] = 'pending_review'
            elif absent:
                item['state'] = report['status']
                value['active'] = None
            item['blocker'] = report.get('error') or dict(code='JOB_TASK_NOT_ACCEPTED', message='task has not been independently accepted')
            value.update(status='blocked', blocker=dict(task_id=task_id, **item['blocker']))
        slot.update(run_reference=reference, run_digest=task_run_digest)
        return _save(records, value, occurred_at=clock())
