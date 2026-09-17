"""Explicit M03 host probe, not a production run-task CLI or task acceptance.

Uses a fixed trusted compatibility task and checks; no candidate code is executed.
Requires the exact model to be preloaded. Never loads or starts a model/server.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'components/worker-lab'), str(ROOT / 'components/worker-lab/tests')]
from test_pi_supervision import setup_attempt, enable
from worker_lab.canonical import canonical_digest
from worker_lab.dispatch_client import dispatch_workspace_write
from worker_lab.pi_binding import create_pi_provider_binding, CONFIG_PATH
from worker_lab.pi_dispatch import make_pi_dispatch_runner
from worker_lab.pi_supervision import set_pi_activation
from worker_lab.provider_binding import ProviderBindingStore
from worker_lab.windows_job import workspace_content_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['edit', 'cancel'], required=True)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--pi-installation', type=Path, required=True)
    args = parser.parse_args()
    root = args.evidence_root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    worker = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    base = worker['endpoint'].removesuffix('/v1')
    def observe(route):
        with urlopen(base + '/api/' + route, timeout=5) as response:
            return json.load(response)
    observations = dict(version=observe('version'), tags=observe('tags'), processes=observe('ps'))
    (root / 'readiness.json').write_text(json.dumps(observations, indent=2), encoding='utf-8')
    try:
        bound = create_pi_provider_binding('BINDING-PI-M03', worker=worker, expected_digest=canonical_digest(worker), **observations)
    except Exception as exc:
        report = dict(schema_version='acl-m03-host-probe:v1', mode=args.mode,
            evidence_kind='host-readiness-only', passed=False, accepted=False,
            worker_digest=canonical_digest(worker), launched=False,
            error=dict(code=getattr(exc, 'code', type(exc).__name__), message=str(exc)))
        (root / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
        return 1
    os.environ['ACL_PI_TEST_INSTALLATION'] = str(args.pi_installation.resolve())
    cancel, finished = threading.Event(), threading.Event()
    launcher, argv, raw, deadline, worker, invocation = setup_attempt(root, observed_binding=bound,
        cancellation=cancel, budget_ms=worker['attempt_timeout_seconds'] * 1000, worker_config=worker,
        user_request='Change only target.py to exactly 10 UTF-8 bytes: hex 56 41 4c 55 45 20 3d 20 32 0a. '
        'The content argument as JSON is "VALUE = 2\\n" (decode the escape to an actual final LF). '
        'Without the final LF the file is only 9 bytes and will fail. Verify the returned file size is 10. '
        'Write an actual newline, not literal backslash characters. The controller will independently '
        'check those exact contents and the allowed diff. After the edit, report completed with '
        'remaining_work null using acl_report_outcome, then respond DONE without more tool calls.')
    request = json.loads(raw)
    request['task']['consumer_profile']['full_validation'][0]['argv'][0] = sys.executable
    before = workspace_content_digest(launcher.workspace)
    authority = (launcher.workspace / 'authority.md').read_bytes()
    outcomes = []
    def outcome_sink(value):
        outcomes.append(value)
        (root / 'worker-outcome.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
    runner = make_pi_dispatch_runner(binding_store=ProviderBindingStore(launcher.state_root), workspace_root=launcher.workspace,
        framework_root=launcher.framework, node=launcher.node, python=launcher.python,
        pi_installation=launcher.installation, agent_dir=launcher.agent_dir, launcher=launcher, outcome_sink=outcome_sink)
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(240)'], creationflags=subprocess.CREATE_NO_WINDOW)
    cancel_evidence = {}
    def cancel_started_session():
        log = launcher.state_root / 'process-logs' / invocation.invocation_id / 'stdout.jsonl'
        while not finished.wait(.025):
            if log.exists() and b'"event":"started"' in log.read_bytes():
                if finished.wait(.25): return
                cancel_evidence['requested_after_started_event'] = True
                cancel.set(); return
    thread = threading.Thread(target=cancel_started_session, daemon=True) if args.mode == 'cancel' else None
    report = dict(schema_version='acl-m03-host-probe:v1', mode=args.mode, evidence_kind='real-model-and-windows-host',
        worker_digest=canonical_digest(worker), invocation_id=invocation.invocation_id,
        workspace=str(launcher.workspace), before_content_digest=before, accepted=False)
    enable(launcher, worker)
    try:
        if thread: thread.start()
        response = dispatch_workspace_write(invocation, prompt=request['prompt'], workspace_write=request['task'],
            binding_store=ProviderBindingStore(launcher.state_root), runner=runner)
        (root / 'framework-response.json').write_bytes(response)
        report['framework_changed_paths'] = json.loads(response)['changed_paths']
    except Exception as exc:
        report['error'] = dict(code=getattr(exc, 'code', type(exc).__name__), message=str(exc))
    finally:
        finished.set()
        if thread: thread.join(timeout=2)
        report['cancellation'] = cancel_evidence
        report['unrelated_process_untouched'] = unrelated.poll() is None
        unrelated.terminate(); unrelated.wait(timeout=5)
        set_pi_activation(launcher.state_root, enabled=False, controller_identity='controller-1', worker_digest=canonical_digest(worker))
    custody = launcher.last_custody
    report['custody'] = custody.to_dict() if custody else None
    report['authority_unchanged'] = (launcher.workspace / 'authority.md').read_bytes() == authority
    report['after_content_digest'] = workspace_content_digest(launcher.workspace)
    diff = subprocess.run(['git', 'diff', '--', 'target.py'], cwd=launcher.workspace, capture_output=True, check=True).stdout
    (root / 'candidate.patch').write_bytes(diff)
    clean_absence = custody is not None and str(custody.state) == 'ABSENCE_VERIFIED' and custody.active_workload_count == 0
    if args.mode == 'edit':
        report['passed'] = (clean_absence and not report.get('error') and report['authority_unchanged']
            and report['unrelated_process_untouched'] and report.get('framework_changed_paths') == ['target.py']
            and (launcher.workspace / 'target.py').read_text(encoding='utf-8') == 'VALUE = 2\n'
            and len(outcomes) == 1 and outcomes[0]['status'] == 'completed' and outcomes[0]['stop_reason'] == 'stop')
    else:
        report['passed'] = (clean_absence and report.get('error', {}).get('code') == 'PI_CANCELLED'
            and report['unrelated_process_untouched'] and bool(cancel_evidence))
    (root / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
