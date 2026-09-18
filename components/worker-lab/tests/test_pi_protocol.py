from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from worker_lab.canonical import canonical_digest
from worker_lab.errors import LabValidationError
from worker_lab.pi_protocol import (
    MAX_FRAME_BYTES, build_request, decode_frame, encode_frame, parse_event,
    parse_request, parse_result,
)
from worker_lab.pi_worker import intended_pi_worker, load_pi_worker, resolve_pi_worker, validate_effective_pi_worker
from worker_lab.provider_binding import create_provider_binding
from tests.test_dispatch_client import invocation, packet, qualification, task


def protocol_worker(context_tokens=32768):
    """Keep protocol/exhaustion fixtures small, separate from operating defaults."""
    return intended_pi_worker(context_tokens=context_tokens, request_limit=8,
        tool_calls_limit=8, tool_timeout_seconds=30, max_output_tokens=2048,
        provider_timeout_seconds=60, attempt_timeout_seconds=180)


NOW = 1_789_666_800_000
WORKER_PIN = canonical_digest(protocol_worker())
FIXTURE = Path(__file__).parent / 'fixtures' / 'pi_protocol_fixture.mjs'


def test_request_and_tool_budgets_are_explicit_options_with_new_identity():
    default = intended_pi_worker(context_tokens=131072)
    configured = intended_pi_worker(context_tokens=131072, request_limit=6, tool_calls_limit=10)
    assert resolve_pi_worker(configured, expected_digest=canonical_digest(configured)) == configured
    assert configured['runtime_settings_digest'] != default['runtime_settings_digest']
    with pytest.raises(LabValidationError):
        resolve_pi_worker(configured, expected_digest=canonical_digest(default))
    for invalid in (0, -1, True, 1.5):
        with pytest.raises(LabValidationError):
            intended_pi_worker(context_tokens=131072, request_limit=invalid)


def request_bytes(context_tokens=32768, *, worker=None):
    # Binding is an opaque reference in the wire contract. This existing fake
    # qualification fixture grants no Pi authority and never reaches dispatch.
    binding = create_provider_binding('BINDING-0001', qualification())
    record = invocation(binding)
    worker = worker or protocol_worker(context_tokens)
    return build_request(
        invocation=record, prompt=packet().to_json(), task=task(record),
        worker=worker, worker_digest=canonical_digest(worker),
        workspace_root='C:/disposable/acl-fixture',
        issued_at_unix_ms=NOW, deadline_unix_ms=NOW + 180_000,
    )


def node(raw, *, mode='result', pin_raw=None):
    executable = shutil.which('node')
    assert executable, 'Node is required for the M01 cross-language acceptance gate'
    pinned = decode_frame(pin_raw or raw)
    return subprocess.run(
        [executable, str(FIXTURE), canonical_digest(pinned),
         pinned['worker_digest'], str(NOW), mode],
        input=raw, capture_output=True, timeout=15,
    )


def leaves(value, prefix=()):
    for key, item in value.items():
        path = (*prefix, key)
        if isinstance(item, dict):
            yield from leaves(item, path)
        else:
            yield path, item


@pytest.mark.parametrize('path,original', list(leaves(intended_pi_worker(context_tokens=32768))))
def test_every_execution_setting_is_pinned(path, original):
    value = intended_pi_worker(context_tokens=32768)
    pin = canonical_digest(value)
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = not original if type(original) is bool else original + 1 if type(original) is int else original + '-changed'
    with pytest.raises(LabValidationError):
        resolve_pi_worker(value, expected_digest=pin)


def test_exact_configuration_is_fresh_and_requires_explicit_pin():
    config = intended_pi_worker(context_tokens=32768)
    assert resolve_pi_worker(config, expected_digest=canonical_digest(config)) == config
    config['runtime_settings']['request_limit'] = 999
    assert intended_pi_worker(context_tokens=32768)['runtime_settings']['request_limit'] == 64
    with pytest.raises(LabValidationError):
        resolve_pi_worker(intended_pi_worker(context_tokens=32768), expected_digest='sha256:' + '0' * 64)


def test_load_one_config_and_reject_replaced_or_duplicate_bytes(tmp_path):
    config = intended_pi_worker(context_tokens=131072)
    pin = canonical_digest(config)
    path = tmp_path / 'worker.json'
    path.write_bytes(encode_frame(config))
    assert load_pi_worker(path, expected_digest=pin) == config
    path.write_bytes(encode_frame(protocol_worker(context_tokens=4096)))
    with pytest.raises(LabValidationError):
        load_pi_worker(path, expected_digest=pin)
    path.write_bytes(b'{"model_name":"first","model_name":"second"}')
    with pytest.raises(LabValidationError):
        load_pi_worker(path, expected_digest=pin)


def test_checked_in_configuration_and_lockfile_match_intended_worker():
    root = Path(__file__).resolve().parents[3]
    config = intended_pi_worker(context_tokens=131072)
    assert load_pi_worker(root / 'config/pi-local-worker.json', expected_digest=canonical_digest(config)) == config
    import hashlib
    assert config['pi_lockfile_digest'] == 'sha256:' + hashlib.sha256((root / 'tools/pi-compatibility/pnpm-lock.yaml').read_bytes()).hexdigest()


def test_s09_context_is_not_mistaken_for_production_qualification():
    with pytest.raises(LabValidationError) as error:
        validate_effective_pi_worker(protocol_worker(), expected_digest=WORKER_PIN, effective_context_tokens=4096)
    assert error.value.code == 'PI_CONTEXT_UNQUALIFIED'
    validate_effective_pi_worker(protocol_worker(), expected_digest=WORKER_PIN, effective_context_tokens=32768)


@pytest.mark.parametrize('context_tokens', [4096, 8192, 32768, 65536, 131072, 262144])
def test_explicit_context_options_round_trip_and_cannot_substitute(context_tokens):
    config = protocol_worker(context_tokens)
    pin = canonical_digest(config)
    assert resolve_pi_worker(config, expected_digest=pin) == config
    validate_effective_pi_worker(config, expected_digest=pin, effective_context_tokens=context_tokens)
    raw = request_bytes(context_tokens)
    echoed = node(raw, mode='echo')
    assert echoed.returncode == 0, echoed.stderr.decode()
    assert parse_request(echoed.stdout, expected_worker_digest=pin, now_unix_ms=NOW)['worker'] == config
    if context_tokens != 32768:
        with pytest.raises(LabValidationError):
            parse_request(raw, expected_worker_digest=WORKER_PIN, now_unix_ms=NOW)
        other = node(raw, pin_raw=request_bytes())
        assert other.returncode == 2


def test_python_node_round_trip_preserves_all_fields_and_binds_result():
    raw = request_bytes()
    result = node(raw, mode='echo')
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout == raw
    assert parse_request(result.stdout, expected_worker_digest=WORKER_PIN, now_unix_ms=NOW) == decode_frame(raw)
    result = node(raw)
    assert result.returncode == 0, result.stderr.decode()
    outcome = parse_result(result.stdout, request_raw=raw, expected_worker_digest=WORKER_PIN)
    assert outcome['summary'] == 'Fixture: café 😀'
    assert outcome['usage'] == dict(input_tokens=17, output_tokens=3, requests=1, tool_calls=0)
    assert outcome['session_reference'] == 'fixture-session:001'
    assert outcome['candidate']['artifacts'][0]['path'] == 'target.py'
    event = node(raw, mode='event')
    assert event.returncode == 0, event.stderr.decode()
    assert parse_event(event.stdout, request_raw=raw, expected_worker_digest=WORKER_PIN, expected_sequence=0)['event'] == 'started'
    with pytest.raises(LabValidationError, match='sequence'):
        parse_event(event.stdout, request_raw=raw, expected_worker_digest=WORKER_PIN, expected_sequence=1)


@pytest.mark.parametrize('mutate', [
    lambda r: r.update(schema_version='acl-pi-request:v999'),
    lambda r: r.update(extra=True),
    lambda r: r.pop('worker'),
    lambda r: r['worker'].update(model_name='wrong-model'),
    lambda r: r['worker'].update(endpoint='http://127.0.0.1:9/v1'),
    lambda r: r['invocation'].update(state='PREPARED'),
    lambda r: r['invocation'].update(attempt_id='ANOTHER-ATTEMPT'),
    lambda r: r['invocation'].update(writable_paths=['outside.py']),
    lambda r: r['task'].update(task_digest='sha256:' + '0' * 64),
    lambda r: r.update(prompt='unadmitted prompt'),
    lambda r: r.update(grant_digest='sha256:' + '0' * 64),
    lambda r: r.update(workspace_root='../outside'),
    lambda r: r.update(deadline_unix_ms=NOW),
    lambda r: r.update(deadline_unix_ms=NOW + 180001),
    lambda r: r.update(issued_at_unix_ms=NOW + 1),
    lambda r: r.update(deadline_unix_ms=True),
])
def test_python_and_node_reject_changed_or_malformed_request(mutate):
    original = request_bytes()
    value = decode_frame(original)
    mutate(value)
    bad = encode_frame(value)
    with pytest.raises(LabValidationError):
        parse_request(bad, expected_worker_digest=WORKER_PIN, now_unix_ms=NOW)
    result = node(bad, pin_raw=original)
    assert result.returncode == 2 and b'PI_PROTOCOL_INVALID' in result.stderr


@pytest.mark.parametrize('raw', [
    b'', b'null', b'[]', b'{', b'{"a":1,"a":2}', b'{"a":1.0}',
    b'{"a":NaN}', b'{"a":9007199254740992}', b'{"a":"\\ud800"}',
    b'{"a":"\xff"}', b'{}\n', b' ' * (MAX_FRAME_BYTES + 1),
    ('{"a":' * 66 + '0' + '}' * 66).encode(),
], ids=[f'frame-{n}' for n in range(13)])
def test_bad_wire_frames_fail_clearly_in_both_languages(raw):
    with pytest.raises(LabValidationError):
        decode_frame(raw)
    result = node(raw, pin_raw=request_bytes())
    assert result.returncode == 2 and b'PI_PROTOCOL_INVALID' in result.stderr


@pytest.mark.parametrize('change', [
    {'schema_version': 'acl-pi-result:v999'}, {'status': 'accepted'},
    {'status': []}, {'request_digest': 'sha256:' + 'f' * 64},
    {'usage': {'input_tokens': True, 'output_tokens': 0, 'requests': 0, 'tool_calls': 0}},
    {'usage': {'input_tokens': 0, 'output_tokens': 0, 'requests': protocol_worker()['runtime_settings']['request_limit'] + 1, 'tool_calls': 0}},
    {'usage': {'input_tokens': None, 'output_tokens': None, 'requests': 0, 'tool_calls': 0}},
    {'status': 'needs_continuation'}, {'summary': ''}, {'extra': 'unknown'},
    {'candidate': {'digest': 'sha256:' + 'a' * 64, 'artifacts': [{'path': '../outside', 'digest': 'sha256:' + 'b' * 64}]}},
])
def test_result_rejects_invalid_claims_and_cross_attempt_substitution(change):
    raw = request_bytes()
    value = decode_frame(node(raw).stdout)
    value.update(change)
    with pytest.raises(LabValidationError):
        parse_result(encode_frame(value), request_raw=raw, expected_worker_digest=WORKER_PIN)


@pytest.mark.parametrize('status', ['completed', 'needs_continuation', 'blocked', 'failed', 'cancelled', 'timed_out', 'protocol_error'])
def test_outcome_statuses_and_absent_optional_evidence(status):
    raw = request_bytes()
    value = decode_frame(node(raw).stdout)
    value.update(status=status, remaining_work='Explicit remaining work or blocker',
                 session_reference=None, usage=None, candidate=None)
    assert parse_result(encode_frame(value), request_raw=raw, expected_worker_digest=WORKER_PIN)['status'] == status


def test_expired_request_cannot_launch_but_can_receive_terminal_result():
    raw = request_bytes()
    with pytest.raises(LabValidationError, match='deadline'):
        parse_request(raw, expected_worker_digest=WORKER_PIN, now_unix_ms=NOW + 180000)
    assert parse_result(node(raw).stdout, request_raw=raw, expected_worker_digest=WORKER_PIN)['status'] == 'completed'
