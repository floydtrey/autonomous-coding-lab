"""One intended local Pi worker. Configuration is not qualification or authority."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .provider_qualification import TOOL_SURFACE_ID
from .runtime_selection import selected_runtime_requirement_v3
from .runtime_settings import CODING_WORKER_SETTINGS_V1

PI_ADAPTER_ID = "pi-local-files:v1"
CONTEXT_PRESETS = (4096, 8192, 32768, 131072, 262144)
MAX_SAFE_INTEGER = 9_007_199_254_740_991


def intended_pi_worker(*, context_tokens: int = 131072, request_limit: int = 8,
                       tool_calls_limit: int = 8, tool_timeout_seconds: int = 30,
                       max_output_tokens: int = 2048, provider_timeout_seconds: int = 60,
                       attempt_timeout_seconds: int = 180,
                       endpoint: str = "http://127.0.0.1:11434/v1",
                       node_version: str = "24.19.0", pi_version: str = "0.85.1",
                       pi_lockfile_digest: str = "sha256:35727af5925cf30922c318c4a6e9a4fac89d1e1302cf1afdc755d894f30bfd64",
                       provider_version: str = "0.34.1", model_name: str = "qwen3.8:27b",
                       model_digest: str = "sha256:22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643",
                       quantization: str = "Q4_K_M") -> dict[str, Any]:
    """Build explicit configuration data; these defaults grant no authority.

    The existing settings record supplies the vocabulary, with Pi retries disabled.
    Context is an explicit operator selection. Increasing it requires matching
    runtime configuration and evidence; metadata alone never qualifies capacity.
    """
    if type(context_tokens) is not int or not 0 < context_tokens <= MAX_SAFE_INTEGER:
        raise LabValidationError("PI_CONTEXT_INVALID", "context size must be an explicit positive safe integer")
    for budget in (request_limit, tool_calls_limit):
        if type(budget) is not int or not 0 < budget <= MAX_SAFE_INTEGER:
            raise LabValidationError("PI_BUDGET_INVALID", "request and tool budgets must be positive safe integers")
    requirement = selected_runtime_requirement_v3()
    settings = replace(
        CODING_WORKER_SETTINGS_V1,
        profile_id="pi-local-worker-settings:v1",
        requested_context_tokens=context_tokens,
        request_limit=request_limit, tool_calls_limit=tool_calls_limit, tool_retries=0, output_retries=0,
        tool_timeout_seconds=tool_timeout_seconds,
    )
    value = {
        "schema_version": "worker-lab-pi-local-configuration:v1",
        "provider_adapter_id": PI_ADAPTER_ID,
        "tool_surface_id": TOOL_SURFACE_ID,
        "pi_package": "@earendil-works/pi-coding-agent",
        "pi_version": pi_version,
        "pi_lockfile_digest": pi_lockfile_digest,
        "node_version": node_version,
        "provider_kind": "ollama",
        "provider_version": provider_version,
        "model_name": model_name,
        "model_digest": model_digest,
        "quantization": quantization,
        "api": "openai-completions",
        "endpoint": endpoint,
        "auth_policy": "local-placeholder-no-auth-header",
        "runtime_requirement": requirement.to_dict(),
        "runtime_requirement_digest": requirement.digest(),
        "runtime_settings": settings.to_dict(),
        "runtime_settings_digest": settings.digest(),
        "required_effective_context_tokens": settings.requested_context_tokens,
        "max_output_tokens": max_output_tokens,
        "provider_timeout_seconds": provider_timeout_seconds,
        "attempt_timeout_seconds": attempt_timeout_seconds,
        "thinking_level": "off",
        "reasoning_effort": "none",
        "automatic_compaction": False,
        "automatic_retry": False,
        "resource_discovery": False,
        "model_fallback": False,
    }
    return resolve_pi_worker(value, expected_digest=canonical_digest(value))


def resolve_pi_worker(value: Any, *, expected_digest: str) -> dict[str, Any]:
    """Validate the supported schema against an independently approved exact pin.

    The configuration supplies values, while code fixes the transport and authority
    boundary. Re-pinning data does not qualify an installation, refresh a Provider
    Binding, activate execution, or authorize a task.
    """
    def require(ok, detail):
        if not ok:
            raise LabValidationError("PI_CONFIGURATION_MISMATCH", detail)

    def integer(item, limit=MAX_SAFE_INTEGER):
        return type(item) is int and 0 < item <= limit

    fixed = {
        "schema_version": "worker-lab-pi-local-configuration:v1",
        "provider_adapter_id": PI_ADAPTER_ID, "tool_surface_id": TOOL_SURFACE_ID,
        "pi_package": "@earendil-works/pi-coding-agent", "provider_kind": "ollama",
        "api": "openai-completions", "auth_policy": "local-placeholder-no-auth-header",
        "thinking_level": "off", "reasoning_effort": "none",
        "automatic_compaction": False, "automatic_retry": False,
        "resource_discovery": False, "model_fallback": False,
    }
    variable = set("pi_version pi_lockfile_digest node_version provider_version model_name model_digest quantization endpoint runtime_requirement runtime_requirement_digest runtime_settings runtime_settings_digest required_effective_context_tokens max_output_tokens provider_timeout_seconds attempt_timeout_seconds".split())
    require(isinstance(value, dict) and set(value) == set(fixed) | variable,
            "Pi configuration has missing or unknown fields")
    require(all(type(value[name]) is type(item) and value[name] == item for name, item in fixed.items()),
            "Pi transport or authority invariant differs")
    for name in ("node_version", "pi_version", "provider_version"):
        require(isinstance(value[name], str) and len(value[name]) <= 128
                and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", value[name]) is not None,
                "Pi runtime version must be an exact version")
    for name in ("pi_lockfile_digest", "model_digest", "runtime_requirement_digest", "runtime_settings_digest"):
        require(isinstance(value[name], str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value[name]) is not None,
                "Pi configuration contains an invalid digest")
    require(isinstance(value['model_name'], str)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}", value['model_name']) is not None,
            "Pi model name must be an exact bounded model identifier")
    require(isinstance(value['quantization'], str)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_+-]{0,63}", value['quantization']) is not None,
            "Pi quantization must be an exact bounded identifier")
    endpoint = value['endpoint']
    require(isinstance(endpoint, str) and len(endpoint) <= 128, "Pi endpoint must be a local URL")
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
        host = '[::1]' if parsed.hostname == '::1' else parsed.hostname
        local = parsed.hostname in {'127.0.0.1', 'localhost', '::1'}
        require(local and type(port) is int and 0 < port <= 65535
                and endpoint == f'http://{host}:{port}/v1',
                "Pi endpoint must be canonical loopback HTTP with an explicit port and /v1 path")
    except ValueError as exc:
        raise LabValidationError("PI_CONFIGURATION_MISMATCH", "Pi endpoint is invalid") from exc
    requirement = selected_runtime_requirement_v3()
    require(isinstance(value['runtime_requirement'], dict)
            and canonical_json(value['runtime_requirement']) == canonical_json(requirement.to_dict())
            and value['runtime_requirement_digest'] == requirement.digest(), "Pi runtime authority requirement differs")
    settings = value['runtime_settings']
    fixed_settings = dict(schema_version=CODING_WORKER_SETTINGS_V1.schema_version,
                          profile_id="pi-local-worker-settings:v1", profile_version=1,
                          tool_retries=0, output_retries=0, max_concurrency=1)
    variable_settings = {'requested_context_tokens', 'request_limit', 'tool_calls_limit', 'tool_timeout_seconds'}
    require(isinstance(settings, dict) and set(settings) == set(fixed_settings) | variable_settings,
            "Pi runtime settings have missing or unknown fields")
    require(all(type(settings[name]) is type(item) and settings[name] == item for name, item in fixed_settings.items()),
            "Pi settings authority invariant differs")
    require(all(integer(settings[name]) for name in variable_settings), "Pi budgets must be positive safe integers")
    context, attempt = value['required_effective_context_tokens'], value['attempt_timeout_seconds']
    require(integer(context) and context == settings['requested_context_tokens'], "Pi required and requested context differ")
    require(integer(value['max_output_tokens'], context), "Pi output budget must be positive and within required context")
    require(integer(attempt, requirement.timeout_seconds), "Pi attempt deadline exceeds the protected runtime requirement")
    require(integer(value['provider_timeout_seconds'], attempt) and integer(settings['tool_timeout_seconds'], attempt),
            "Pi provider/tool deadline must be positive and within the attempt deadline")
    require(value['runtime_settings_digest'] == canonical_digest(settings), "Pi runtime settings digest differs")
    require(isinstance(expected_digest, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", expected_digest) is not None
            and expected_digest == canonical_digest(value), "Pi configuration differs from the separately approved pin")
    return json.loads(canonical_json(value))


def load_pi_worker(path: Path, *, expected_digest: str) -> dict[str, Any]:
    """Read one explicitly supplied operator config against a separately held pin."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate configuration field")
            result[key] = value
        return result

    try:
        raw = path.read_bytes()
        if len(raw) > 16384:
            raise ValueError("oversized configuration")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        raise LabValidationError("PI_CONFIGURATION_INVALID", "cannot load a bounded UTF-8 Pi configuration") from exc
    return resolve_pi_worker(value, expected_digest=expected_digest)


def validate_effective_pi_worker(value: Any, *, expected_digest: str, effective_context_tokens: int) -> None:
    """Compare independently observed configuration; metadata is not context proof.

    The caller must obtain effective_context_tokens from trusted capability
    evidence, never Pi's advertised contextWindow or a worker claim.
    """
    configured = resolve_pi_worker(value, expected_digest=expected_digest)
    if (type(effective_context_tokens) is not int
            or effective_context_tokens < configured["required_effective_context_tokens"]):
        raise LabValidationError("PI_CONTEXT_UNQUALIFIED", "effective context does not satisfy the protected runtime requirement")
