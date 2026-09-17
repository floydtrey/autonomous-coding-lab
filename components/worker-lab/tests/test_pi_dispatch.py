from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from worker_lab.canonical import canonical_digest, canonical_json
from worker_lab.controller_task_packet import ControllerTaskPacket
from worker_lab.dispatch_client import dispatch_workspace_write
from worker_lab.errors import LabValidationError
from worker_lab.integration_v3 import InvocationRecordV3
from worker_lab.pi_binding import create_pi_provider_binding, check_runtime_readiness
from worker_lab.pi_dispatch import make_pi_dispatch_runner, parse_adapter_output, PiOutcomeError
from worker_lab.pi_worker import intended_pi_worker
from worker_lab.provider_binding import ProviderBindingStore

ROOT = Path(__file__).resolve().parents[3]
AWF = ROOT / 'components/autonomous-worker-framework'
sys.path.insert(0, str(AWF))
spec = importlib.util.spec_from_file_location('awf_dispatch_fixtures', AWF / 'tests/test_dispatch_adapter.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def observations(worker):
    model = dict(name=worker['model_name'], digest=worker['model_digest'][7:], details=dict(quantization_level=worker['quantization']))
    return dict(version={'version': worker['provider_version']}, tags={'models': [model]},
                processes={'models': [dict(model, context_length=worker['required_effective_context_tokens'])]})


def binding(worker):
    return create_pi_provider_binding('BINDING-PI-001', worker=worker, expected_digest=canonical_digest(worker), **observations(worker))


@pytest.mark.parametrize('field', ['version', 'model', 'digest', 'context', 'unloaded'])
def test_readiness_rejects_unready_or_substituted_runtime(field):
    worker = intended_pi_worker(context_tokens=131072)
    observed = observations(worker)
    if field == 'version': observed['version']['version'] = 'changed'
    if field == 'model': observed['tags']['models'][0]['name'] = 'wrong-model'
    if field == 'digest': observed['tags']['models'][0]['digest'] = '0' * 64
    if field == 'context': observed['processes']['models'][0]['context_length'] = 4096
    if field == 'unloaded': observed['processes']['models'] = []
    with pytest.raises(LabValidationError):
        check_runtime_readiness(worker, expected_digest=canonical_digest(worker), **observed)


def test_pi_binding_round_trip_and_stale_configuration_rejection(tmp_path, monkeypatch):
    worker = intended_pi_worker(context_tokens=131072)
    record = binding(worker)
    store = ProviderBindingStore(tmp_path)
    store.create(record)
    assert store.require(record.binding_id, record.digest()) == record
    from worker_lab import pi_binding
    config = tmp_path / 'changed.json'
    config.write_text(json.dumps(intended_pi_worker(context_tokens=4096)))
    monkeypatch.setattr(pi_binding, 'CONFIG_PATH', config)
    with pytest.raises(LabValidationError):
        store.read(record.binding_id)


@pytest.mark.parametrize('scenario', ['success', 'missing_claim', 'provider_error', 'malformed_claim', 'empty_remaining'])
def test_worker_lab_dispatch_through_real_pi_sdk_with_fixture_transport(tmp_path, scenario):
    # Explicit installed SDK path: no download, qualification campaign or model call.
    install = Path(os.environ['ACL_PI_TEST_INSTALLATION']).resolve()
    node = Path(shutil.which('node')).resolve()
    root, base = fixture.repo(tmp_path)
    # Actual unapproved files, not just assertions about resource-loader flags.
    for name, contents in {
        'AGENTS.md': 'UNAPPROVED_MARKER',
        '.pi/SYSTEM.md': 'UNAPPROVED_MARKER',
        '.pi/extensions/hostile.mjs': "throw new Error('UNAPPROVED_MARKER');",
        '.pi/skills/hostile/SKILL.md': '---\nname: hostile\ndescription: UNAPPROVED_MARKER\n---\nUNAPPROVED_MARKER',
        '.pi/prompts/hostile.md': 'UNAPPROVED_MARKER',
    }.items():
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(contents)
    fixture.git(root, 'add', '.'); fixture.git(root, 'commit', '-qm', 'unapproved resource fixture')
    base = fixture.git(root, 'rev-parse', 'HEAD')
    payload = json.loads(fixture.request(root, base)[0])
    worker = intended_pi_worker(context_tokens=131072)
    bound = binding(worker)
    store = ProviderBindingStore(tmp_path / 'state')
    store.create(bound)
    packet = ControllerTaskPacket.from_mapping(dict(schema_version='worker-lab-controller-task-packet:v2',
        context_mode='none', attempt_id='ATTEMPT-001', controller_identity='controller-1',
        user_request='Change only target.py to VALUE = 2.', exercise_id='exercise', exercise_version=1,
        starting_commit=base, authority_effect='informational-only', knowledge_evidence=[]))
    inv = payload['invocation']
    inv.update(provider_binding_id=bound.binding_id, provider_binding_digest=bound.digest(),
        runtime_requirement_digest=bound.runtime_requirement_digest,
        controller_task_packet_digest=packet.digest(), prompt_digest=packet.digest())
    invocation = InvocationRecordV3.from_mapping(inv)
    task = payload['workspace_write']
    task['consumer_profile']['full_validation'][0]['argv'][0] = sys.executable
    outcomes, wire = [], []
    agent_dir = tmp_path / 'agent'; agent_dir.mkdir()
    for name in ('SYSTEM.md', 'APPEND_SYSTEM.md'):
        (agent_dir / name).write_text('UNAPPROVED_MARKER')
    def launch(argv, raw, deadline):
        # Production factory, Node adapter and installed SDK; only HTTP is a fixture.
        argv = list(argv)
        argv[1] = str(Path(__file__).parent / 'fixtures/pi_sdk_fixture.mjs')
        argv.append(scenario)
        env = {key: os.environ[key] for key in ('PATH', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP') if key in os.environ}
        env.update(PI_CODING_AGENT_DIR=str(agent_dir), HOME=str(tmp_path), USERPROFILE=str(tmp_path), CI='1')
        process = subprocess.run(argv, input=raw, capture_output=True, timeout=30, env=env, cwd=root)
        assert process.returncode == 0, process.stderr.decode(errors='replace')
        if process.stderr:
            print(process.stderr.decode(errors='replace'))
        wire.append((raw[:-1], process.stdout))
        return process.stdout
    runner = make_pi_dispatch_runner(binding_store=store, workspace_root=root, framework_root=AWF,
        node=node, python=Path(sys.executable), pi_installation=install, agent_dir=agent_dir,
        launcher=launch, outcome_sink=outcomes.append)
    if scenario == 'success':
        result = json.loads(dispatch_workspace_write(invocation, prompt=packet.to_json(), workspace_write=task,
            binding_store=store, runner=runner))
        assert result['changed_paths'] == ['target.py']
        assert outcomes[0]['status'] == 'completed' and outcomes[0]['stop_reason'] == 'stop'
        assert outcomes[0]['session_reference']
        assert outcomes[0]['usage']['requests'] == 4
        assert outcomes[0]['usage']['tool_calls'] == 3
        assert (root / 'target.py').read_text() == 'VALUE = 2\n'
        assert (root / 'authority.md').read_text() == 'authority\n'
        request, output = wire[0]
        for invalid in (output[:-1], b'', output + output, output[:output.rfind(b'\n', 0, -1) + 1]):
            with pytest.raises(LabValidationError):
                parse_adapter_output(invalid, request, canonical_digest(worker))
    else:
        with pytest.raises(PiOutcomeError):
            dispatch_workspace_write(invocation, prompt=packet.to_json(), workspace_write=task, binding_store=store, runner=runner)
        assert outcomes[0]['status'] in ('protocol_error', 'failed')
        assert (root / 'target.py').read_text() == ('VALUE = 2\n' if scenario in ('malformed_claim', 'empty_remaining') else 'VALUE = 1\n')
        if scenario == 'provider_error':
            assert outcomes[0]['usage']['requests'] == 1


def test_no_implicit_launcher(tmp_path):
    with pytest.raises(LabValidationError, match='explicit supervised launcher'):
        make_pi_dispatch_runner(binding_store=None, workspace_root=tmp_path, framework_root=AWF,
            node=Path(sys.executable), python=Path(sys.executable), pi_installation=tmp_path,
            agent_dir=tmp_path, launcher=None, outcome_sink=lambda value: None)
