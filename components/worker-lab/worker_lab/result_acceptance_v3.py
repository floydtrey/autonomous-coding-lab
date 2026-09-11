from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .canonical import canonical_json
from .dispatch_client import DISPATCH_RESPONSE_SCHEMA, MAX_DISPATCH_RESPONSE_BYTES
from .errors import LabValidationError
from .integration_v3 import (
    RESULT_SCHEMA_V3,
    GitWorkspaceResultEvidence,
    InvocationOperation,
    InvocationRecordV3,
    ResultRecordV3,
    ValidationStage,
    validate_result_for_invocation,
)
from .process_custody import CustodyState, ProcessCustodyRecord, ProcessCustodyStore
from .storage import AtomicRecordStore


_RESPONSE_FIELDS = {
    "schema_version",
    "invocation_digest",
    "provider_binding_digest",
    "provider_adapter_id",
    "framework_task_digest",
    "context_digest",
    "candidate_digest",
    "changed_paths",
    "validation_stages",
    "worker_output_digest",
}
_DIGEST_PREFIX = "sha256:"
_CANDIDATE_SCHEMA = "worker-lab-workspace-write-candidate:v2"


def accept_workspace_write_response_v3(
    value: bytes,
    record: InvocationRecordV3,
    custody: ProcessCustodyRecord,
    *,
    started_at: str,
    ended_at: str,
    state_root: Path,
    custody_store: ProcessCustodyStore,
    source_evidence: GitWorkspaceResultEvidence,
    validation_stages: tuple[ValidationStage, ...],
) -> ResultRecordV3:
    """Convert a framework dispatch response into independently accepted V3 evidence.

    The framework response may describe its own task/context/candidate output, but
    Worker Lab independently owns custody, Git workspace evidence, and protected test
    execution. A successful Result V3 is created only when those evidence sources
    agree exactly with the authorized invocation.
    """
    if not isinstance(record, InvocationRecordV3) or record.operation is not InvocationOperation.WORKSPACE_WRITE_CODE_TASK:
        raise LabValidationError(
            "INTEGRATION_V3_OPERATION_INVALID",
            "V3 result acceptance supports only the current workspace-write code task",
        )
    _validate_custody(record, custody, custody_store)
    if not isinstance(source_evidence, GitWorkspaceResultEvidence):
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "workspace result evidence has an invalid type",
        )
    decoded = _parse_response(value)
    if (
        decoded["invocation_digest"] != record.identity_digest()
        or decoded["provider_binding_digest"] != record.provider_binding_digest
        or not isinstance(decoded["provider_adapter_id"], str)
        or not decoded["provider_adapter_id"].strip()
    ):
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "framework dispatch response differs from the authorized invocation",
        )
    for field in (
        "framework_task_digest",
        "context_digest",
        "candidate_digest",
        "worker_output_digest",
    ):
        _digest(decoded[field], field)
    if decoded["changed_paths"] != list(record.writable_paths):
        raise LabValidationError(
            "INTEGRATION_V3_SCOPE_INVALID",
            "framework candidate paths differ from the authorized write scope",
        )
    if source_evidence.changed_paths != record.writable_paths:
        raise LabValidationError(
            "INTEGRATION_V3_SCOPE_INVALID",
            "independent workspace paths differ from the authorized write scope",
        )
    _validate_framework_stages(decoded["validation_stages"], record)
    _validate_independent_stages(validation_stages, record)

    candidate_manifest = {
        "schema_version": _CANDIDATE_SCHEMA,
        "invocation_digest": record.identity_digest(),
        "provider_binding_digest": record.provider_binding_digest,
        "framework_task_digest": decoded["framework_task_digest"],
        "context_digest": decoded["context_digest"],
        "framework_candidate_digest": decoded["candidate_digest"],
        "worker_output_digest": decoded["worker_output_digest"],
        "changed_paths": list(source_evidence.changed_paths),
        "workspace_content_digest": source_evidence.workspace_content_digest,
    }
    encoded_manifest = canonical_json(candidate_manifest).encode("utf-8")
    retained_digest = _bytes_digest(encoded_manifest)
    reference = f"candidates/{retained_digest[7:]}.json"

    result = ResultRecordV3.from_mapping({
        "schema_version": RESULT_SCHEMA_V3,
        "invocation_digest": record.identity_digest(),
        "request_digest": record.identity_digest(),
        "invocation_id": record.invocation_id,
        "attempt_id": record.attempt_id,
        "operation": str(record.operation),
        "logical_target_id": record.logical_target_id,
        "workspace_id": record.workspace_id,
        "framework_source_digest": record.framework_source_digest,
        "framework_contract_version": record.framework_contract_version,
        "runtime_requirement_profile_id": record.runtime_requirement_profile_id,
        "runtime_requirement_digest": record.runtime_requirement_digest,
        "provider_binding_id": record.provider_binding_id,
        "provider_binding_digest": record.provider_binding_digest,
        "runtime_identity": record.provider_binding_digest,
        "controller_task_packet_digest": record.controller_task_packet_digest,
        "prompt_digest": record.prompt_digest,
        "test_catalog_version": record.test_catalog_version,
        "test_catalog_digest": record.test_catalog_digest,
        "test_plan_digest": record.test_plan_digest,
        "test_ids": list(record.test_ids),
        "process_outcome": "pass",
        "process_identity": custody.digest(),
        "process_started_at": started_at,
        "process_ended_at": ended_at,
        "source_evidence": source_evidence.to_dict(),
        "proposal_digest": None,
        "candidate_digest": retained_digest,
        "validation_stages": [stage.to_dict() for stage in validation_stages],
        "first_failure_boundary": None,
        "failure_code": None,
        "expected": "authorized candidate paths, verified custody, and sealed validation",
        "observed": "authorized candidate paths, verified custody, and sealed validation",
        "containment_outcome": "absence-verified",
        "output_digest": decoded["worker_output_digest"],
        "content_reference": reference,
        "retryable": False,
    })
    validate_result_for_invocation(result, record)
    _store_candidate(state_root, reference, encoded_manifest)
    return result


def parse_result_v3(value: str | bytes, record: InvocationRecordV3) -> ResultRecordV3:
    """Strictly parse a durable V3 result and bind it to its exact invocation."""
    try:
        if isinstance(value, str):
            encoded = value.encode("utf-8")
        elif isinstance(value, bytes):
            encoded = value
        else:
            raise TypeError("result must be text or bytes")
        decoded = json.loads(encoded.decode("utf-8"), object_pairs_hook=_unique_object)
        if canonical_json(decoded).encode("utf-8") != encoded:
            raise ValueError("result is not canonical")
    except (TypeError, UnicodeDecodeError, UnicodeEncodeError, ValueError, json.JSONDecodeError) as exc:
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "durable V3 result is not canonical UTF-8 JSON",
        ) from exc
    result = ResultRecordV3.from_mapping(decoded)
    validate_result_for_invocation(result, record)
    return result


def verify_workspace_write_candidate_manifest_v3(
    content: bytes,
    invocation: InvocationRecordV3,
    result: ResultRecordV3,
) -> str:
    if result.candidate_digest is None or result.source_evidence is None:
        raise LabValidationError(
            "SERVICE_CANDIDATE_CONTENT_INVALID",
            "V3 workspace-write result has no retained candidate evidence",
        )
    try:
        decoded = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object)
        canonical = canonical_json(decoded).encode("utf-8")
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise LabValidationError(
            "SERVICE_CANDIDATE_CONTENT_INVALID",
            "V3 workspace-write candidate manifest is invalid",
        ) from exc
    fields = {
        "schema_version",
        "invocation_digest",
        "provider_binding_digest",
        "framework_task_digest",
        "context_digest",
        "framework_candidate_digest",
        "worker_output_digest",
        "changed_paths",
        "workspace_content_digest",
    }
    if (
        not isinstance(decoded, dict)
        or set(decoded) != fields
        or canonical != content
        or _bytes_digest(content) != result.candidate_digest
        or decoded["schema_version"] != _CANDIDATE_SCHEMA
        or decoded["invocation_digest"] != invocation.identity_digest()
        or decoded["provider_binding_digest"] != invocation.provider_binding_digest
        or decoded["changed_paths"] != list(result.source_evidence.changed_paths)
        or decoded["workspace_content_digest"] != result.source_evidence.workspace_content_digest
        or decoded["worker_output_digest"] != result.output_digest
    ):
        raise LabValidationError(
            "SERVICE_CANDIDATE_CONTENT_INVALID",
            "V3 workspace-write candidate manifest differs from durable result",
        )
    for field in ("framework_task_digest", "context_digest", "framework_candidate_digest"):
        _digest(decoded[field], field)
    return decoded["framework_candidate_digest"]


def _validate_custody(
    record: InvocationRecordV3,
    custody: ProcessCustodyRecord,
    store: ProcessCustodyStore,
) -> None:
    if not isinstance(custody, ProcessCustodyRecord) or store.read(custody.invocation_id) != custody:
        raise LabValidationError(
            "INTEGRATION_OUTCOME_UNCERTAIN",
            "custody must be the exact durable final record",
        )
    if (
        custody.invocation_id != record.invocation_id
        or custody.invocation_digest != record.identity_digest()
        or custody.worker_identity is None
        or not custody.request_sent
        or custody.state is not CustodyState.ABSENCE_VERIFIED
        or custody.active_workload_count != 0
        or custody.absence_evidence_digest is None
        or custody.exit_code != 0
        or custody.first_failure is not None
    ):
        raise LabValidationError(
            "INTEGRATION_OUTCOME_UNCERTAIN",
            "custody is not a complete verified success",
        )


def _parse_response(value: bytes) -> dict[str, object]:
    if not isinstance(value, bytes) or not value or len(value) > MAX_DISPATCH_RESPONSE_BYTES:
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "framework dispatch response is invalid",
        )
    try:
        decoded = json.loads(value.decode("utf-8"), object_pairs_hook=_unique_object)
        canonical = canonical_json(decoded).encode("utf-8")
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "framework dispatch response is not canonical UTF-8 JSON",
        ) from exc
    if (
        not isinstance(decoded, dict)
        or set(decoded) != _RESPONSE_FIELDS
        or canonical != value
        or decoded["schema_version"] != DISPATCH_RESPONSE_SCHEMA
    ):
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "framework dispatch response fields are invalid",
        )
    return decoded


def _validate_framework_stages(value: object, record: InvocationRecordV3) -> None:
    if not isinstance(value, list) or len(value) != len(record.test_ids):
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "framework validation stages do not cover the sealed test plan",
        )
    observed: list[str] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"test_id", "outcome"}:
            raise LabValidationError(
                "INTEGRATION_V3_RESULT_INVALID",
                "framework validation stage fields are invalid",
            )
        if item["outcome"] != "pass" or not isinstance(item["test_id"], str):
            raise LabValidationError(
                "INTEGRATION_V3_RESULT_INVALID",
                "framework validation stage is not a pass",
            )
        observed.append(item["test_id"])
    if tuple(observed) != record.test_ids:
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "framework validation stages differ from the sealed test plan",
        )


def _validate_independent_stages(
    stages: tuple[ValidationStage, ...],
    record: InvocationRecordV3,
) -> None:
    if (
        not isinstance(stages, tuple)
        or tuple(stage.test_id for stage in stages) != record.test_ids
        or any(stage.outcome != "pass" or stage.failure_code is not None for stage in stages)
    ):
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "independent sealed validation differs from the authorized test plan",
        )


def _store_candidate(state_root: Path, reference: str, encoded: bytes) -> None:
    records = AtomicRecordStore(state_root)
    try:
        existing = records.read_bytes(reference)
    except LabValidationError as exc:
        if exc.code != "STORAGE_RECORD_MISSING":
            raise
        records.write_bytes(reference, encoded)
        return
    if existing != encoded:
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "content-addressed V3 candidate differs",
        )


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for name, item in pairs:
        if name in value:
            raise ValueError("duplicate JSON object key")
        value[name] = item
    return value


def _bytes_digest(value: bytes) -> str:
    return _DIGEST_PREFIX + hashlib.sha256(value).hexdigest()


def _digest(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 71
        or not value.startswith(_DIGEST_PREFIX)
        or any(character not in "0123456789abcdef" for character in value[7:])
    ):
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            f"{name} is invalid",
        )
    return value
