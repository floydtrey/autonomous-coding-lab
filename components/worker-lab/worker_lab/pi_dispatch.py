"""Explicit Pi runner for the existing Worker Lab -> AWF dispatch seam.

This is transport wiring, not activation, durable custody or final acceptance.
M03 supplies the supervised launcher. The normal service/CLI injects no runner.
"""
from __future__ import annotations

import base64
import json
import importlib
import sys
from pathlib import Path
import time
from typing import Callable

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .integration_v3 import InvocationRecordV3
from .pi_binding import validate_pi_binding
from .pi_protocol import build_request, decode_frame, parse_event, parse_result, MAX_FRAME_BYTES
from .provider_binding import ProviderBindingStore


class PiOutcomeError(LabValidationError):
    def __init__(self, outcome):
        super().__init__('PI_WORKER_INCOMPLETE', outcome['stop_reason'] + ': ' + outcome['summary'])
        self.outcome = outcome


def parse_adapter_output(raw: bytes, request: bytes, worker_digest: str) -> dict:
    if not isinstance(raw, bytes) or not raw.endswith(b'\n') or len(raw) > 8 * MAX_FRAME_BYTES:
        raise LabValidationError('PI_PROTOCOL_INVALID', 'unexpected EOF or oversized Pi JSONL output')
    frames = raw[:-1].split(b'\n')
    sequence = 0
    result = None
    settled = False
    for frame in frames:
        if result is not None:
            raise LabValidationError('PI_PROTOCOL_INVALID', 'output follows terminal result')
        value = decode_frame(frame)
        if value.get('schema_version') == 'acl-pi-event:v1':
            event = parse_event(frame, request_raw=request, expected_worker_digest=worker_digest, expected_sequence=sequence)
            sequence += 1
            settled |= event['event'] == 'settled'
        else:
            result = parse_result(frame, request_raw=request, expected_worker_digest=worker_digest)
    if result is None or (result['status'] == 'completed' and (not settled or result['stop_reason'] != 'stop')):
        raise LabValidationError('PI_PROTOCOL_INVALID', 'missing result or authoritative successful settlement')
    return result


def make_pi_dispatch_runner(*, binding_store: ProviderBindingStore, workspace_root: Path,
                            framework_root: Path, node: Path, python: Path,
                            pi_installation: Path, agent_dir: Path,
                            launcher: Callable, outcome_sink: Callable[[dict], None]):
    """Require an explicit launcher and sink; never silently select/run a process.

    launcher(argv, request_jsonl, deadline_unix_ms) returns stdout bytes. It owns
    environment, process lifetime and absence evidence. outcome_sink is controller
    owned and remains outside the worker's grant. Neither has an implicit default.
    """
    if not callable(launcher) or not callable(outcome_sink):
        raise LabValidationError('PI_LAUNCHER_REQUIRED', 'Pi requires an explicit supervised launcher and outcome sink')
    for path in (workspace_root, framework_root, node, python, pi_installation, agent_dir):
        if not isinstance(path, Path) or not path.is_absolute():
            raise LabValidationError('PI_LAUNCHER_INVALID', 'Pi host paths must be explicit absolute paths')
    # CLI installations need not put the sibling AWF package on PYTHONPATH.
    # Resolve it only from the explicit trusted framework, rejecting cached substitutes.
    for name, module in tuple(sys.modules.items()):
        if name == 'tools' or name.startswith('tools.'):
            origin = getattr(module, '__file__', None)
            namespace_paths = list(getattr(module, '__path__', ()))
            trusted_namespace = name == 'tools' and origin is None and namespace_paths and all(
                Path(path).resolve() == framework_root.resolve() / 'tools' for path in namespace_paths)
            if not trusted_namespace and (origin is None or not Path(origin).resolve().is_relative_to(framework_root.resolve() / 'tools')):
                raise LabValidationError('PI_FRAMEWORK_IMPORT_MISMATCH', 'loaded tools package differs from the trusted framework')
    sys.path.insert(0, str(framework_root))
    try:
        package = importlib.import_module('tools')
        package.__path__ = [str(framework_root.resolve() / 'tools')]
        adapter = importlib.import_module('tools.dispatch_adapter')
        runtime = importlib.import_module('tools.worker_runtime')
    finally:
        sys.path.remove(str(framework_root))
    BoundProviderExecutor = adapter.BoundProviderExecutor
    execute_workspace_write, parse_dispatch_request = adapter.execute_workspace_write, adapter.parse_dispatch_request
    WorkerExecution = runtime.WorkerExecution

    def runner(raw: bytes) -> bytes:
        parsed = parse_dispatch_request(raw)
        invocation = InvocationRecordV3.from_mapping(parsed.invocation)
        binding = binding_store.require(invocation.provider_binding_id, invocation.provider_binding_digest)
        config = validate_pi_binding(binding)
        config_digest = canonical_digest(config)

        def execute(worker_request, settings):
            if worker_request.target_repo.resolve() != workspace_root.resolve() or settings != config['runtime_settings']:
                raise LabValidationError('PI_DISPATCH_MISMATCH', 'workspace or settings differ from admitted Pi dispatch')
            expected_readable = sorted({p.path for p in invocation.readable_paths} | set(invocation.writable_paths))
            if sorted(worker_request.readable_paths) != expected_readable or tuple(worker_request.writable_paths) != invocation.writable_paths:
                raise LabValidationError('PI_DISPATCH_MISMATCH', 'AWF scope differs from admitted Pi grant')
            issued = time.time_ns() // 1_000_000
            deadline = issued + min(config['attempt_timeout_seconds'], worker_request.timeout_seconds) * 1000
            request = build_request(invocation=invocation, prompt=parsed.prompt, task=dict(parsed.workspace_write),
                worker=config, worker_digest=config_digest, workspace_root=str(workspace_root),
                issued_at_unix_ms=issued, deadline_unix_ms=deadline, execution_prompt=worker_request.prompt)
            control = dict(request_digest=canonical_digest(decode_frame(request)), worker_digest=config_digest,
                binding=binding.to_dict(), python=str(python), pi_installation=str(pi_installation), agent_dir=str(agent_dir))
            argument = base64.urlsafe_b64encode(canonical_json(control).encode()).decode().rstrip('=')
            argv = (str(node), str(framework_root / 'tools/pi_adapter_main.mjs'), argument)
            output = launcher(argv, request + b'\n', deadline)
            result = parse_adapter_output(output, request, config_digest)
            outcome_sink(result)
            if result['status'] != 'completed':
                raise PiOutcomeError(result)
            return WorkerExecution(argv[:2], 0, canonical_json(result), '')

        executor = BoundProviderExecutor(binding.provider_adapter_id, binding.tool_surface_id,
            binding.digest(), binding.runtime_settings_digest, execute)
        return execute_workspace_write(raw, workspace_root=workspace_root,
            framework_root=framework_root, provider_executor=executor)
    return runner
