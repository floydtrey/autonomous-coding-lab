from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from .canonical import canonical_json
from .errors import LabValidationError
from .integration import InvocationRecord, ResultRecord


ADAPTER_COMMAND = ("worker-lab-framework-adapter", "prepare", "--protocol", "worker-lab-framework-invocation:v1")
MAX_ADAPTER_RESPONSE_BYTES = 65_536
AdapterRunner = Callable[[tuple[str, ...], str], str | bytes]


@dataclass(frozen=True)
class PreparationResponse:
    invocation_digest: str
    prompt_digest: str
    runtime_identity: str


def prepare_invocation(record: InvocationRecord, *, runner: AdapterRunner | None = None) -> PreparationResponse:
    """Validate one fake adapter response; this seam never supplies a process runner."""
    if runner is None:
        raise LabValidationError("INTEGRATION_EXECUTION_DISABLED", "an injected adapter runner is required")
    payload = canonical_json(record.to_dict())
    raw = runner(ADAPTER_COMMAND, payload)
    if isinstance(raw, str):
        encoded = raw.encode("utf-8")
    elif isinstance(raw, bytes):
        encoded = raw
    else:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response must be UTF-8 text")
    if not encoded or len(encoded) > MAX_ADAPTER_RESPONSE_BYTES:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response is empty or oversized")
    try:
        decoded = encoded.decode("utf-8")
        value = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response is not JSON") from exc
    if not isinstance(value, dict) or set(value) != {"invocation_digest", "prompt_digest", "runtime_identity"}:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response fields are invalid")
    response = PreparationResponse(
        invocation_digest=_digest(value["invocation_digest"]),
        prompt_digest=_digest(value["prompt_digest"]),
        runtime_identity=_digest(value["runtime_identity"]),
    )
    if response.invocation_digest != record.digest() or response.prompt_digest != record.prompt_digest:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter preparation identity differs")
    return response


def parse_result(value: str | bytes, record: InvocationRecord) -> ResultRecord:
    """Parse a single strict result object without accepting it as authorization evidence."""
    try:
        if isinstance(value, str):
            encoded = value.encode("utf-8")
        elif isinstance(value, bytes):
            encoded = value
        else:
            raise TypeError("result must be text or bytes")
        if not encoded or len(encoded) > MAX_ADAPTER_RESPONSE_BYTES:
            raise ValueError("result is empty or oversized")
        text = encoded.decode("utf-8")
        decoded = json.loads(text)
    except (TypeError, UnicodeEncodeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter result is not JSON") from exc
    result = ResultRecord.from_mapping(decoded)
    if (
        result.invocation_digest != record.digest()
        or result.request_digest != record.digest()
        or result.invocation_id != record.invocation_id
        or result.attempt_id != record.attempt_id
        or result.operation != record.operation
        or result.framework_commit != record.framework_commit
        or result.framework_contract_version != record.framework_contract_version
        or result.runtime_profile_id != record.runtime_profile_id
        or result.prompt_digest != record.prompt_digest
        or result.test_catalog_version != record.test_catalog_version
        or result.test_catalog_digest != record.test_catalog_digest
        or result.test_plan_digest != record.test_plan_digest
        or result.test_ids != record.test_ids
        or result.workspace_receipt_digest != record.workspace_receipt_digest
        or result.workspace_root_digest != record.workspace_root_digest
        or result.workspace_path_digest != record.workspace_path_digest
        or result.starting_commit != record.starting_commit
    ):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "result does not bind its invocation")
    return result


def _digest(value: object) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter identity digest is invalid")
    if any(character not in "0123456789abcdef" for character in value[7:]):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter identity digest is invalid")
    return value