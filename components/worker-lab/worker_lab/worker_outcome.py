"""Durable worker observations, separate from accepted Result records."""
from __future__ import annotations
from dataclasses import dataclass
import json
import re
from pathlib import PurePosixPath
from .models import _attempt_id, _timestamp
from .process_custody import ProcessCustodyRecord, CustodyState
from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError

STATUSES = frozenset({'completed_claim', 'needs_continuation', 'blocked', 'protocol_error',
    'provider_failed', 'timed_out', 'cancelled', 'uncertain', 'interrupted'})

@dataclass(frozen=True)
class WorkerOutcome:
    # Canonical text prevents mutation of a validated record.
    payload: str

    @classmethod
    def from_mapping(cls, value):
        fields = {'schema_version', 'attempt_id', 'invocation_id', 'invocation_digest',
            'task_file_digest', 'configuration_digest', 'grant_digest', 'provider_binding_digest',
            'status', 'accepted', 'acceptance', 'recorded_at', 'stop_state', 'custody',
            'worker_result', 'usage', 'error', 'candidate', 'diagnostics', 'artifacts',
            'workspace', 'manual_next_step'}
        if (not isinstance(value, dict) or set(value) != fields
                or value['schema_version'] != 'worker-lab-worker-outcome:v1'
                or not isinstance(value['status'], str) or value['status'] not in STATUSES or value['accepted'] is not False
                or value['acceptance'] != ('pending_independent_acceptance'
                    if value['status'] == 'completed_claim' else 'not_accepted')
                or not isinstance(value['stop_state'], str) or value['stop_state'] not in {'not_started', 'absence_verified', 'uncertain'}
                or not isinstance(value['artifacts'], dict)
                or not isinstance(value['diagnostics'], list)):
            raise LabValidationError('WORKER_OUTCOME_INVALID', 'invalid worker outcome contract')
        for key in ('invocation_digest', 'task_file_digest', 'configuration_digest',
                    'grant_digest', 'provider_binding_digest'):
            item = value[key]
            if not isinstance(item, str) or len(item) != 71 or not item.startswith('sha256:') or any(c not in '0123456789abcdef' for c in item[7:]):
                raise LabValidationError('WORKER_OUTCOME_INVALID', 'invalid outcome identity')
        _attempt_id(value['attempt_id'], 'attempt_id')
        _timestamp(value['recorded_at'], 'recorded_at')
        if not isinstance(value['invocation_id'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{2,95}', value['invocation_id']):
            raise LabValidationError('WORKER_OUTCOME_INVALID', 'invalid invocation id')
        for key in ('workspace', 'manual_next_step'):
            if not isinstance(value[key], str) or not value[key].strip():
                raise LabValidationError('WORKER_OUTCOME_INVALID', 'missing outcome context')
        for path in value['artifacts'].values():
            if (not isinstance(path, str) or not path or '\\' in path or ':' in path
                    or PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts
                    or PurePosixPath(path).as_posix() != path):
                raise LabValidationError('WORKER_OUTCOME_INVALID', 'invalid retained artifact reference')
        for key in ('worker_result', 'error', 'candidate', 'usage', 'custody'):
            if value[key] is not None and not isinstance(value[key], dict):
                raise LabValidationError('WORKER_OUTCOME_INVALID', 'invalid optional outcome object')
        if value['usage'] is not None:
            if set(value['usage']) != {'input_tokens','output_tokens','requests','tool_calls'} or any(
                    x is not None and (type(x) is not int or x < 0) for x in value['usage'].values()):
                raise LabValidationError('WORKER_OUTCOME_INVALID', 'invalid measured usage')
        if value['custody'] is not None:
            custody = ProcessCustodyRecord.from_mapping(value['custody'])
            if custody.invocation_id != value['invocation_id'] or custody.invocation_digest != value['invocation_digest']:
                raise LabValidationError('WORKER_OUTCOME_INVALID', 'custody identity differs')
        if value['stop_state'] == 'absence_verified' and (value['custody'] is None or custody.state is not CustodyState.ABSENCE_VERIFIED):
            raise LabValidationError('WORKER_OUTCOME_INVALID', 'verified absence requires custody proof')
        if value['stop_state'] == 'uncertain' and (value['status'] != 'uncertain' or value['candidate'] is not None):
            raise LabValidationError('WORKER_OUTCOME_INVALID', 'uncertain workload cannot be a stable candidate')
        if value['candidate'] is not None and (value['candidate'].get('accepted_base') is not False
                or value['stop_state'] != 'absence_verified'):
            raise LabValidationError('WORKER_OUTCOME_INVALID', 'candidate is diagnostic only after verified absence')
        if value['candidate'] is not None:
            candidate = value['candidate']
            fields = {'content_digest', 'archive', 'diff', 'accepted_base'}
            if (set(candidate) not in (fields, fields | {'archive_capture'})
                    or not isinstance(candidate.get('content_digest'), str)
                    or not re.fullmatch(r'sha256:[0-9a-f]{64}', candidate['content_digest'])
                    or not candidate.get('diff')
                    or candidate['diff'] != value['artifacts'].get('candidate.patch')
                    or candidate['archive'] != value['artifacts'].get('candidate.zip')):
                raise LabValidationError('WORKER_OUTCOME_INVALID', 'candidate identity or artifact references differ')
            capture = candidate.get('archive_capture')
            if capture is not None:
                if (not isinstance(capture, dict) or set(capture) != {'status', 'limit_bytes', 'content_bytes'}
                        or type(capture['limit_bytes']) is not int or capture['limit_bytes'] < 0
                        or type(capture['content_bytes']) is not int or capture['content_bytes'] < 0):
                    raise LabValidationError('WORKER_OUTCOME_INVALID', 'invalid archive capture metadata')
                expected_capture = capture['limit_bytes'] > 0 and capture['content_bytes'] <= capture['limit_bytes']
                if (capture['status'] != ('captured' if expected_capture else 'omitted_limit')
                        or bool(candidate['archive']) != expected_capture):
                    raise LabValidationError('WORKER_OUTCOME_INVALID', 'archive capture status differs from budget')
            elif candidate['archive'] is None:
                raise LabValidationError('WORKER_OUTCOME_INVALID', 'omitted archive requires explicit capture metadata')
        if value['status'] == 'completed_claim' and (value['stop_state'] != 'absence_verified'
                or not value['worker_result'] or value['worker_result'].get('status') != 'completed'
                or value['worker_result'].get('stop_reason') != 'stop'
                or value['error'] is not None or value['candidate'] is None):
            raise LabValidationError('WORKER_OUTCOME_INVALID', 'completed claim lacks stopped worker evidence')
        return cls(canonical_json(value))

    def to_dict(self):
        return json.loads(self.payload)

    def to_json(self):
        return self.payload

    def digest(self):
        return canonical_digest(self.to_dict())
