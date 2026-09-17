"""Re-pinned single-worker configuration; all runtime observations are fixtures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from worker_lab.canonical import canonical_digest
from worker_lab.errors import LabValidationError
from worker_lab import pi_binding, pi_supervision
from worker_lab.pi_binding import create_pi_provider_binding, check_runtime_readiness, validate_pi_binding
from worker_lab.pi_protocol import parse_request
from worker_lab.pi_worker import intended_pi_worker, load_pi_worker, resolve_pi_worker
from worker_lab.runtime_settings import RuntimeSettingsProfile
from tests.test_pi_protocol import NOW, node, request_bytes


def changed_worker():
    return intended_pi_worker(context_tokens=65536, request_limit=12, tool_calls_limit=16,
        tool_timeout_seconds=45, max_output_tokens=4096, provider_timeout_seconds=120,
        attempt_timeout_seconds=900, endpoint='http://127.0.0.1:11435/v1',
        node_version='24.20.0', pi_version='0.86.0', provider_version='0.35.0',
        pi_lockfile_digest='sha256:' + '1' * 64, model_name='fixture-coder:next',
        model_digest='sha256:' + '2' * 64, quantization='Q8_0')


def observations(worker):
    model = dict(name=worker['model_name'], digest=worker['model_digest'][7:],
                 details=dict(quantization_level=worker['quantization']))
    return dict(version={'version': worker['provider_version']}, tags={'models': [model]},
                processes={'models': [dict(model, context_length=worker['required_effective_context_tokens'])]})


@pytest.mark.parametrize('field,value', [
    ('max_output_tokens', 4096), ('provider_timeout_seconds', 120),
    ('attempt_timeout_seconds', 900), ('endpoint', 'http://127.0.0.1:11435/v1'),
    ('node_version', '24.20.0'), ('pi_version', '0.86.0'), ('provider_version', '0.35.0'),
    ('pi_lockfile_digest', 'sha256:' + '3' * 64), ('model_name', 'fixture-coder:next'),
    ('model_digest', 'sha256:' + '4' * 64), ('quantization', 'Q8_0'),
])
def test_supported_field_reapproval_replaces_defaults_without_source_edits(field, value):
    worker = intended_pi_worker()
    old_pin = canonical_digest(worker)
    worker[field] = value
    with pytest.raises(LabValidationError):
        resolve_pi_worker(worker, expected_digest=old_pin)
    assert resolve_pi_worker(worker, expected_digest=canonical_digest(worker)) == worker


def test_repinned_configuration_passes_binding_and_python_node_protocol(tmp_path, monkeypatch):
    old_worker, worker = intended_pi_worker(), changed_worker()
    old_pin, pin = canonical_digest(old_worker), canonical_digest(worker)
    prior = create_pi_provider_binding('BINDING-PRIOR', worker=old_worker,
        expected_digest=old_pin, **observations(old_worker))
    path = tmp_path / 'protected-worker.json'
    path.write_text(json.dumps(worker), encoding='utf-8')
    monkeypatch.setattr(pi_binding, 'CONFIG_PATH', path)
    assert load_pi_worker(path, expected_digest=pin) == worker
    bound = create_pi_provider_binding('BINDING-REPINNED', worker=worker,
        expected_digest=pin, **observations(worker))
    assert validate_pi_binding(bound, RuntimeSettingsProfile(**worker['runtime_settings'])) == worker
    assert bound.host_provider_qualification_digest != prior.host_provider_qualification_digest
    with pytest.raises(LabValidationError):
        validate_pi_binding(prior)
    with pytest.raises(LabValidationError):
        validate_pi_binding(bound, RuntimeSettingsProfile(**old_worker['runtime_settings']))
    raw = request_bytes(worker=worker)
    echoed = node(raw, mode='echo')
    assert echoed.returncode == 0, echoed.stderr.decode()
    assert parse_request(echoed.stdout, expected_worker_digest=pin, now_unix_ms=NOW)['worker'] == worker
    assert node(raw, mode='echo', pin_raw=request_bytes(worker=old_worker)).returncode == 2
    with pytest.raises(LabValidationError):
        parse_request(raw, expected_worker_digest=old_pin, now_unix_ms=NOW)


def test_changed_configuration_requires_fresh_explicit_activation(tmp_path, monkeypatch):
    # Configuration approval is separate from the actual source verification gate.
    # This unit fixture supplies that gate's unchanged observed identity only.
    monkeypatch.setattr(pi_supervision, 'inspect_source_identity',
        lambda: (None, SimpleNamespace(manifest_digest='sha256:' + '5' * 64)))
    worker = intended_pi_worker()
    path = tmp_path / 'protected-worker.json'
    monkeypatch.setattr(pi_binding, 'CONFIG_PATH', path)
    path.write_text(json.dumps(worker), encoding='utf-8')
    state = tmp_path / 'state'
    pi_supervision.set_pi_activation(state, enabled=True, controller_identity='controller-1',
                                    worker_digest=canonical_digest(worker))
    changed = changed_worker()
    path.write_text(json.dumps(changed), encoding='utf-8')
    with pytest.raises(LabValidationError):
        pi_supervision.set_pi_activation(state, enabled=True, controller_identity='controller-1',
                                        worker_digest=canonical_digest(worker))
    with pytest.raises(LabValidationError, match='approved identity changed'):
        pi_supervision.require_activation(state, controller='controller-1', worker_digest=canonical_digest(changed))
    pi_supervision.set_pi_activation(state, enabled=True, controller_identity='controller-1',
                                    worker_digest=canonical_digest(changed))
    assert pi_supervision.require_activation(state, controller='controller-1',
        worker_digest=canonical_digest(changed))['enabled'] is True


@pytest.mark.parametrize('field', ['provider', 'model', 'digest', 'quantization', 'context'])
def test_repinned_worker_still_requires_matching_observations(field):
    worker = changed_worker()
    observed = observations(worker)
    if field == 'provider': observed['version']['version'] = '0.34.1'
    if field == 'model': observed['tags']['models'][0]['name'] = 'prior-model'
    if field == 'digest': observed['tags']['models'][0]['digest'] = 'f' * 64
    if field == 'quantization': observed['tags']['models'][0]['details']['quantization_level'] = 'Q4_K_M'
    if field == 'context': observed['processes']['models'][0]['context_length'] = 4096
    with pytest.raises(LabValidationError):
        check_runtime_readiness(worker, expected_digest=canonical_digest(worker), **observed)


@pytest.mark.parametrize('endpoint', ['http://localhost:11435/v1', 'http://[::1]:11436/v1'])
def test_explicit_supported_loopback_endpoints(endpoint):
    worker = intended_pi_worker(endpoint=endpoint)
    assert resolve_pi_worker(worker, expected_digest=canonical_digest(worker))['endpoint'] == endpoint


@pytest.mark.parametrize('endpoint', [
    'http://example.com:11434/v1', 'http://127.0.0.1:0/v1', 'http://127.0.0.1:65536/v1',
    'https://127.0.0.1:11434/v1', 'http://user:secret@127.0.0.1:11434/v1',
    'http://127.0.0.1:11434/v1?key=value', 'http://127.0.0.1:11434/v1#fragment',
    'http://127.0.0.1:11434/alternate/v1', 'http://127.0.0.1:11434/v1/',
    'http://127.0.0.1/v1', 'http://localhost.attacker:11434/v1', 'http://[::1/v1',
])
def test_repin_cannot_enable_unsupported_transport(endpoint):
    worker = intended_pi_worker()
    worker['endpoint'] = endpoint
    with pytest.raises(LabValidationError):
        resolve_pi_worker(worker, expected_digest=canonical_digest(worker))


@pytest.mark.parametrize('mutate', [
    lambda w: w.update(max_output_tokens=0), lambda w: w.update(max_output_tokens=True),
    lambda w: w.update(max_output_tokens=1.5), lambda w: w.update(max_output_tokens=131073),
    lambda w: w.update(provider_timeout_seconds=181), lambda w: w.update(attempt_timeout_seconds=901),
    lambda w: w.update(attempt_timeout_seconds=-1), lambda w: w.update(node_version='latest'),
    lambda w: w.update(pi_version='*'), lambda w: w.update(model_digest='unverified'),
    lambda w: w.update(provider_kind='other'), lambda w: w.update(api='responses'),
    lambda w: w.update(auth_policy='arbitrary-credentials'), lambda w: w.update(resource_discovery=True),
    lambda w: w.update(automatic_retry=True), lambda w: w.update(model_fallback=True),
    lambda w: w.update(automatic_compaction=0), lambda w: w.update(extra=True),
    lambda w: w['runtime_requirement'].update(timeout_seconds=1000),
    lambda w: w['runtime_settings'].update(tool_timeout_seconds=181),
    lambda w: w['runtime_settings'].update(tool_timeout_seconds=0),
    lambda w: w['runtime_settings'].update(request_limit=9_007_199_254_740_992),
    lambda w: w['runtime_settings'].update(tool_retries=1),
    lambda w: w['runtime_settings'].update(max_concurrency=2),
    lambda w: w['runtime_settings'].update(profile_version=True),
    lambda w: w['runtime_settings'].update(requested_context_tokens=65536),
])
def test_repin_cannot_change_schema_ranges_or_authority(mutate):
    worker = intended_pi_worker()
    mutate(worker)
    # Even internally consistent re-pinning cannot expand supported authority.
    worker['runtime_settings_digest'] = canonical_digest(worker['runtime_settings'])
    worker['runtime_requirement_digest'] = canonical_digest(worker['runtime_requirement'])
    with pytest.raises(LabValidationError):
        resolve_pi_worker(worker, expected_digest=canonical_digest(worker))


def test_tool_deadline_change_requires_matching_nested_digest():
    worker = intended_pi_worker()
    worker['runtime_settings']['tool_timeout_seconds'] = 45
    with pytest.raises(LabValidationError):
        resolve_pi_worker(worker, expected_digest=canonical_digest(worker))
    worker['runtime_settings_digest'] = canonical_digest(worker['runtime_settings'])
    assert resolve_pi_worker(worker, expected_digest=canonical_digest(worker)) == worker


def test_node_checks_repinned_sdk_and_prestarted_runtime_with_no_network(tmp_path, monkeypatch):
    node_exe = shutil.which('node')
    assert node_exe
    installed_node_version = subprocess.run([node_exe, '-p', 'process.versions.node'],
        capture_output=True, check=True, text=True).stdout.strip()
    package = tmp_path / 'node_modules/@earendil-works/pi-coding-agent'
    (package / 'dist').mkdir(parents=True)
    (package / 'package.json').write_text(json.dumps(dict(name='@earendil-works/pi-coding-agent',
        version='0.86.0', type='module')), encoding='utf-8')
    (package / 'dist/index.js').write_text('export const fixture = true;\n', encoding='utf-8')
    lock = b'explicit fixture lockfile\n'
    (tmp_path / 'pnpm-lock.yaml').write_bytes(lock)
    worker = changed_worker()
    worker.update(node_version=installed_node_version, pi_lockfile_digest='sha256:' + hashlib.sha256(lock).hexdigest())
    config_path = tmp_path / 'protected-worker.json'
    config_path.write_text(json.dumps(worker), encoding='utf-8')
    monkeypatch.setattr(pi_binding, 'CONFIG_PATH', config_path)
    observed = observations(worker)
    bound = create_pi_provider_binding('BINDING-NODE-FIXTURE', worker=worker,
        expected_digest=canonical_digest(worker), **observed)
    adapter = Path(__file__).resolve().parents[3] / 'components/autonomous-worker-framework/tools/pi_adapter.mjs'
    inputs = tmp_path / 'runtime-fixture.json'
    inputs.write_text(json.dumps(dict(installation=str(tmp_path), worker=worker,
        binding=bound.to_dict(), observed=observed, adapter=adapter.as_uri())), encoding='utf-8')
    script = """
      import assert from 'node:assert/strict';
      import { readFileSync } from 'node:fs';
      const f = JSON.parse(readFileSync(process.argv[1], 'utf8'));
      const { loadPinnedSdk, checkPrestartedRuntime } = await import(f.adapter);
      assert.equal((await loadPinnedSdk(f.installation, f.worker)).fixture, true);
      for (const change of [{node_version:'0.0.0'}, {pi_version:'0.0.0'},
          {pi_lockfile_digest:'sha256:' + '0'.repeat(64)}]) {
        await assert.rejects(loadPinnedSdk(f.installation, {...f.worker,...change}), /MISMATCH/);
      }
      const calls = [];
      const fetchFixture = async url => {
        calls.push(url);
        assert.ok(url.startsWith('http://127.0.0.1:11435/api/'));
        const key = url.endsWith('/version') ? 'version' : url.endsWith('/tags') ? 'tags' : 'processes';
        return Response.json(f.observed[key]);
      };
      await checkPrestartedRuntime(f.worker, f.binding, fetchFixture);
      assert.equal(calls.length, 3);
      await assert.rejects(checkPrestartedRuntime({...f.worker,max_output_tokens:1024},
        f.binding, fetchFixture), /PI_READINESS_CHANGED/);
      f.observed.version.version = '0.0.0';
      await assert.rejects(checkPrestartedRuntime(f.worker, f.binding, fetchFixture), /PI_PROVIDER_VERSION_MISMATCH/);
      console.log('repinned SDK, runtime and stale readiness fixture checks passed');
    """
    result = subprocess.run([node_exe, '--input-type=module', '-e', script, str(inputs)],
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert 'fixture checks passed' in result.stdout
