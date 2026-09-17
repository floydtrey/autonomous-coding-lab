"""M06 evidence-gated acceptance of an unchanged, independently checked task."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from .attempt_store import AttemptStore
from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .git_workspace_evidence import inspect_git_workspace_result
from .operator_control import validate_controller_identity
from .pi_supervision import _exclusive_controller, now
from .process_custody import ProcessCustodyRecord, ProcessCustodyStore
from .protected_validation import _base, _approval, _optional, require_resolved_validations
from .result_acceptance_v3 import _validate_custody, _validate_independent_stages
from .integration_v3 import ValidationStage
from .models import _timestamp
from .run_task import _candidate_diff
from .storage import AtomicRecordStore


@dataclass(frozen=True)
class TaskAcceptanceReport:
    payload: str

    def to_dict(self):
        return json.loads(self.payload)

    def to_json(self):
        return self.payload

    def digest(self):
        return canonical_digest(self.to_dict())


class _Gate(LabValidationError):
    def __init__(self, code, message, status='blocked'):
        super().__init__(code, message)
        self.status = status


def _require(condition, code, message, status='blocked'):
    if not condition:
        raise _Gate(code, message, status)


def _bytes_digest(value):
    return 'sha256:' + hashlib.sha256(value).hexdigest()


def _validation_id(value):
    _require(isinstance(value, str) and re.fullmatch(r'VALIDATION-[A-Za-z0-9_-]{1,80}', value),
        'TASK_VALIDATION_INVALID', 'validation identity is invalid')


def _evidence(data_root, attempt_id, expected_outcome_digest, controller_identity,
              validation_id, expected_validation_digest):
    """Reload authoritative evidence; never accept a supplied report or verdict."""
    _validation_id(validation_id)
    records = AtomicRecordStore(data_root / 'state')
    initial = AttemptStore(records.root).read_outcome(attempt_id).to_dict()
    _require(initial['status'] == 'completed_claim', 'TASK_WORKER_NOT_COMPLETED',
        'only a valid completed worker claim can be accepted',
        'blocked' if initial['status'] in {'blocked', 'uncertain', 'interrupted'} else 'failed')
    base = _base(data_root, attempt_id, expected_outcome_digest, controller_identity)
    records, outcome, invocation, workspace, candidate_digest, selected, source = base
    value = outcome.to_dict()
    custody_store = ProcessCustodyStore(records.root)
    custody = custody_store.read(invocation.invocation_id)
    _validate_custody(invocation, custody, custody_store)
    from .task_workflow import require_task_execution_approval
    consent = require_task_execution_approval(data_root, invocation, value['task_file_digest'])
    _require(isinstance(consent, dict) and type(consent.get('review_required')) is bool,
        'TASK_APPROVAL_INVALID', 'protected workflow approval must declare its review requirement')
    approval = _approval(*base, data_root, controller_identity)
    _require(isinstance(consent.get('validation'), dict)
        and all(approval.get(key) == item for key, item in consent['validation'].items()),
        'TASK_APPROVAL_MISMATCH', 'candidate validation differs from the approved named commands')
    require_resolved_validations(records)
    intent = records.read(f'validation-intents/{validation_id}.json', lambda item: item)
    report = records.read(f'validation-results/{validation_id}.json', lambda item: item)
    validation_digest = canonical_digest(report)
    _require(expected_validation_digest is None or validation_digest == expected_validation_digest,
        'TASK_VALIDATION_MISMATCH', 'validation report differs from the expected digest')
    expected = dict(validation_id=validation_id, attempt_id=attempt_id,
        invocation_id=invocation.invocation_id, invocation_digest=invocation.identity_digest(),
        outcome_digest=outcome.digest(), candidate_digest=candidate_digest,
        approval_digest=canonical_digest(approval), test_plan_digest=invocation.test_plan_digest,
        source_manifest_digest=source, mode=approval['mode'], resource_exposure=approval['resource_exposure'])
    _require(isinstance(intent, dict) and intent.get('schema_version') == 'worker-lab-validation-intent:v1'
        and all(intent.get(key) == item for key, item in expected.items())
        and isinstance(report, dict) and report.get('schema_version') == 'worker-lab-validation-report:v1'
        and all(report.get(key) == item for key, item in expected.items())
        and report.get('request_digest') == canonical_digest(intent)
        and report.get('accepted') is False and report.get('all_validators_absent') is True,
        'TASK_VALIDATION_MISMATCH', 'validation evidence does not bind this exact stopped candidate')
    _require(report.get('status') == 'passed' and report.get('error') is None,
        'TASK_CHECKS_FAILED', 'required protected checks did not pass', 'failed')
    checks = report.get('checks')
    _require(isinstance(checks, list) and len(checks) == len(invocation.test_ids)
        and all(isinstance(check, dict) for check in checks)
        and tuple(check.get('test_id') for check in checks) == invocation.test_ids,
        'TASK_CHECKS_INCOMPLETE', 'every selected protected check is required exactly once and in order')
    stages, logs, validators = [], [], []
    for check, command in zip(checks, approval['commands']):
        test_id = check['test_id']
        prefix = f'validation-logs/{validation_id}/{test_id}'
        _require(check.get('status') == 'passed' and check.get('failure') is None
            and type(check.get('exit_code')) is int and check['exit_code'] == 0
            and check.get('candidate_digest') == candidate_digest and check.get('command') == command,
            'TASK_CHECKS_FAILED', 'protected check result is not a passing result for this candidate', 'failed')
        check_store = ProcessCustodyStore(records._target(prefix))
        check_custody = ProcessCustodyRecord.from_mapping(check['custody'])
        _validate_custody(invocation, check_custody, check_store)
        launch = records.read(f'{prefix}/launch-intent.json', lambda item: item)
        _require(check_custody.workspace_content_digest == candidate_digest
            and check.get('validator_identity') == check_custody.worker_identity
            and isinstance(launch, dict)
            and launch.get('invocation_digest') == invocation.identity_digest()
            and launch.get('candidate_digest') == candidate_digest
            and launch.get('controller_identity') == check_custody.controller_identity
            and launch.get('approval_digest') == canonical_digest(approval)
            and launch.get('command') == command,
            'TASK_VALIDATOR_MISMATCH', 'validator identity or candidate differs')
        validators.append(dict(test_id=test_id, custody_digest=check_custody.digest(),
            launch_digest=canonical_digest(launch), result_digest=canonical_digest(check)))
        for stream in ('stdout', 'stderr'):
            reference = f'{prefix}/{stream}.log'
            _require(check.get(stream) == reference, 'TASK_VALIDATION_MISMATCH', 'validator log reference differs')
            logs.append({'path': reference, 'digest': _bytes_digest(records.read_bytes(reference))})
        stages.append(ValidationStage(test_id, 'pass', None))
    _validate_independent_stages(tuple(stages), invocation)
    source_evidence = inspect_git_workspace_result(invocation, state_root=records.root, workspace_path=workspace)
    _require(source_evidence.workspace_content_digest == candidate_digest,
        'TASK_CANDIDATE_DRIFT', 'candidate changed since the worker outcome and protected checks')
    _require(invocation.output_acceptance is not None, 'TASK_OUTPUT_CONTRACT_REQUIRED',
        'task acceptance requires the explicitly admitted output contract')
    try:
        invocation.output_acceptance.validate_changes(source_evidence.changed_paths)
        invocation.output_acceptance.validate_artifacts(workspace)
    except LabValidationError as exc:
        raise _Gate(exc.code, exc.summary, 'failed') from exc
    artifacts = value['artifacts']
    worker_reference = artifacts.get('worker_result')
    _require(isinstance(worker_reference, str), 'TASK_WORKER_EVIDENCE_MISSING', 'retained worker result is required')
    worker_bytes = records.read_bytes(worker_reference)
    _require(worker_bytes == (canonical_json(value['worker_result']) + '\n').encode('utf-8'),
        'TASK_WORKER_EVIDENCE_MISMATCH', 'retained worker output differs from the durable outcome')
    diff_reference = value['candidate']['diff']
    diff = records.read_bytes(diff_reference)
    _require(diff == _candidate_diff(workspace, invocation.source_state.base_commit),
        'TASK_DIFF_MISMATCH', 'retained diff differs from the admitted candidate')
    invocation.output_acceptance.validate_evidence((
        'protected-test-results:v1', 'worker-output:v1', 'workspace-diff:v1'))
    evidence = dict(attempt_id=attempt_id, invocation_id=invocation.invocation_id,
        invocation_digest=invocation.identity_digest(), outcome_digest=outcome.digest(),
        candidate_digest=candidate_digest, source_manifest_digest=source,
        output_contract_digest=invocation.output_acceptance.digest(),
        source_evidence=source_evidence.to_dict(), worker_custody_digest=custody.digest(),
        task_approval_digest=canonical_digest(consent), validation_id=validation_id,
        validation_digest=validation_digest, validation_intent_digest=canonical_digest(intent),
        validation_approval_digest=canonical_digest(approval), test_plan_digest=invocation.test_plan_digest,
        test_ids=list(invocation.test_ids), validators=validators, validator_logs=logs,
        worker_output={'path': worker_reference, 'digest': _bytes_digest(worker_bytes)},
        diff={'path': diff_reference, 'digest': _bytes_digest(diff)}, review_required=consent['review_required'])
    return records, value, evidence


def _review(records, review_id, evidence):
    if review_id is None:
        _require(not evidence['review_required'], 'TASK_REVIEW_REQUIRED',
            'the exact candidate and check evidence require an explicit review', 'pending_review')
        return None
    _require(isinstance(review_id, str) and re.fullmatch(r'REVIEW-[A-Za-z0-9_-]{1,80}', review_id),
        'TASK_REVIEW_INVALID', 'review identity is invalid')
    review = _optional(records, f'task-reviews/{review_id}.json')
    fields = {'schema_version', 'review_id', 'reviewer_identity', 'decision', 'recorded_at',
        'evidence_digest', 'attempt_id', 'invocation_digest', 'outcome_digest', 'candidate_digest', 'validation_digest'}
    _require(isinstance(review, dict) and review.get('schema_version') == 'worker-lab-task-review:v1'
        and set(review) == fields
        and review.get('review_id') == review_id and review.get('evidence_digest') == canonical_digest(evidence)
        and review.get('attempt_id') == evidence['attempt_id']
        and review.get('invocation_digest') == evidence['invocation_digest']
        and review.get('outcome_digest') == evidence['outcome_digest']
        and review.get('candidate_digest') == evidence['candidate_digest']
        and review.get('validation_digest') == evidence['validation_digest'],
        'TASK_REVIEW_MISMATCH', 'review differs from the exact candidate or required evidence', 'pending_review')
    validate_controller_identity(review.get('reviewer_identity'))
    _timestamp(review['recorded_at'], 'recorded_at')
    _require(review.get('decision') == 'approved', 'TASK_REVIEW_REJECTED', 'review did not approve this candidate', 'failed')
    return canonical_digest(review)


def _decision(records, value):
    result = TaskAcceptanceReport(canonical_json(value))
    records.write_bytes(f'task-decisions/{result.digest()[7:]}.json', (result.to_json() + '\n').encode('utf-8'))
    return result


def accept_task(data_root, *, attempt_id, expected_outcome_digest, controller_identity,
                validation_id, expected_validation_digest=None, review_id=None, clock=now):
    """Accept exact evidence, or retain an honest non-accepting decision. Never launch."""
    data_root = Path(data_root)
    records = AtomicRecordStore(data_root / 'state')
    value = dict(schema_version='worker-lab-task-acceptance:v1', attempt_id=attempt_id,
        outcome_digest=expected_outcome_digest, validation_id=validation_id,
        validation_digest=expected_validation_digest, status='blocked', accepted=False,
        workspace=None, candidate=None, diff=None, evidence=None, evidence_digest=None,
        review_id=review_id, review_digest=None, error=None, recorded_at=clock())
    with _exclusive_controller(records.root, 'run-task.lock'), _exclusive_controller(records.root):
        try:
            outcome = AttemptStore(records.root).read_outcome(attempt_id).to_dict()
            value.update(workspace=outcome['workspace'], candidate=outcome['candidate'],
                diff=outcome['candidate']['diff'] if outcome['candidate'] is not None else None)
            _, outcome, evidence = _evidence(data_root, attempt_id, expected_outcome_digest,
                controller_identity, validation_id, expected_validation_digest)
            value.update(evidence=evidence, evidence_digest=canonical_digest(evidence),
                validation_digest=evidence['validation_digest'])
            review_digest = _review(records, review_id, evidence)
            # A second complete reload covers changes while files/logs/review were inspected.
            _, _, current = _evidence(data_root, attempt_id, expected_outcome_digest,
                controller_identity, validation_id, evidence['validation_digest'])
            _require(current == evidence and _review(records, review_id, current) == review_digest,
                'TASK_EVIDENCE_DRIFT', 'acceptance evidence changed during inspection')
            value.update(status='accepted', accepted=True, review_digest=review_digest)
            existing = _optional(records, f'task-acceptances/{attempt_id}.json')
            if existing is not None:
                _require(isinstance(existing, dict) and existing.get('schema_version') == value['schema_version']
                    and existing.get('accepted') is True and existing.get('status') == 'accepted'
                    and all(existing.get(key) == item for key, item in value.items() if key != 'recorded_at'),
                    'TASK_ACCEPTANCE_MISMATCH', 'this attempt already has a different immutable acceptance')
                return TaskAcceptanceReport(canonical_json(existing))
            result = TaskAcceptanceReport(canonical_json(value))
            records.write_bytes(f'task-acceptances/{attempt_id}.json', (result.to_json() + '\n').encode('utf-8'))
            return result
        except (LabValidationError, OSError, ValueError, TypeError, KeyError) as exc:
            value.update(status=getattr(exc, 'status', 'blocked'), accepted=False,
                error={'code': getattr(exc, 'code', 'TASK_ACCEPTANCE_INVALID'), 'message': str(exc)[:2048]})
            return _decision(records, value)


def record_task_review(data_root, *, attempt_id, expected_outcome_digest, controller_identity,
                       validation_id, expected_validation_digest, review_id, reviewer_identity,
                       decision='approved', clock=now):
    """Explicit reviewer action over the current, otherwise acceptable evidence."""
    _require(isinstance(review_id, str) and re.fullmatch(r'REVIEW-[A-Za-z0-9_-]{1,80}', review_id),
        'TASK_REVIEW_INVALID', 'review identity is invalid')
    _require(isinstance(decision, str) and decision in {'approved', 'rejected'},
        'TASK_REVIEW_INVALID', 'review decision is invalid')
    _require(isinstance(expected_validation_digest, str)
        and re.fullmatch(r'sha256:[0-9a-f]{64}', expected_validation_digest),
        'TASK_REVIEW_INVALID', 'review must name the exact validation report digest')
    reviewer_identity = validate_controller_identity(reviewer_identity)
    data_root = Path(data_root)
    with _exclusive_controller(data_root / 'state', 'run-task.lock'), _exclusive_controller(data_root / 'state'):
        records, _, evidence = _evidence(data_root, attempt_id, expected_outcome_digest,
            controller_identity, validation_id, expected_validation_digest)
        value = dict(schema_version='worker-lab-task-review:v1', review_id=review_id,
            reviewer_identity=reviewer_identity, decision=decision, recorded_at=clock(),
            evidence_digest=canonical_digest(evidence), **{key: evidence[key] for key in
                ('attempt_id', 'invocation_digest', 'outcome_digest', 'candidate_digest', 'validation_digest')})
        existing = _optional(records, f'task-reviews/{review_id}.json')
        if existing is not None:
            _require(isinstance(existing, dict) and all(existing.get(key) == item for key, item in value.items()
                if key != 'recorded_at'), 'TASK_REVIEW_MISMATCH', 'review identity already names different evidence')
            return TaskAcceptanceReport(canonical_json(existing))
        records.write_bytes(f'task-reviews/{review_id}.json', (canonical_json(value) + '\n').encode('utf-8'))
        return TaskAcceptanceReport(canonical_json(value))
