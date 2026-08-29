from __future__ import annotations

import json
import hashlib
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

from .canonical import canonical_json
from .process_custody import CustodyState, ProcessCustodyRecord, ProcessCustodyStore
from .errors import LabValidationError
from .integration import InvocationRecord, ResultRecord, ValidationStage
from .models import WorkspaceReceipt, WorkspaceReceiptState
from .storage import AtomicRecordStore


ADAPTER_COMMAND = ("worker-lab-framework-adapter", "prepare", "--protocol", "worker-lab-framework-invocation:v1")
MAX_ADAPTER_RESPONSE_BYTES = 65_536
MAX_PROPOSAL_BYTES = 32_768
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
        value = json.loads(decoded, object_pairs_hook=_unique_object)
        if canonical_json(value).encode("utf-8") != encoded:
            raise ValueError("response is not canonical")
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response is not JSON") from exc
    if not isinstance(value, dict) or set(value) != {"invocation_digest", "prompt_digest", "runtime_identity"}:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response fields are invalid")
    response = PreparationResponse(
        invocation_digest=_digest(value["invocation_digest"]),
        prompt_digest=_digest(value["prompt_digest"]),
        runtime_identity=_digest(value["runtime_identity"]),
    )
    if response.invocation_digest != record.identity_digest() or response.prompt_digest != record.prompt_digest:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter preparation identity differs")
    return response


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for name, item in pairs:
        if name in value:
            raise ValueError("duplicate JSON object key")
        value[name] = item
    return value


def parse_result(value: str | bytes, record: InvocationRecord, *, custody_digest: str | None = None) -> ResultRecord:
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
        decoded = json.loads(text, object_pairs_hook=_unique_object)
        if canonical_json(decoded).encode("utf-8") != encoded:
            raise ValueError("result is not canonical")
    except (TypeError, UnicodeEncodeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter result is not JSON") from exc
    result = ResultRecord.from_mapping(decoded)
    if custody_digest is not None and result.process_identity != _digest(custody_digest):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "result custody identity differs")
    if (
        result.invocation_digest != record.identity_digest()
        or result.request_digest != record.identity_digest()
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


class ProposalStore:
    """Retain only an accepted, bounded, content-addressed proposal under contained storage."""

    def __init__(self, state_root: Path) -> None:
        self.records = AtomicRecordStore(state_root.absolute())

    def store(self, result: ResultRecord, content: bytes | str) -> ResultRecord:
        if result.operation.value != "read-only-proposal" or result.process_outcome != "pass":
            raise LabValidationError("INTEGRATION_RESULT_INVALID", "only successful proposals may be retained")
        encoded = _proposal_bytes(content)
        digest = "sha256:" + hashlib.sha256(encoded).hexdigest()
        if result.proposal_digest != digest or result.output_digest != digest:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "proposal content digest differs")
        reference = f"proposals/{digest[7:]}.txt"
        if result.content_reference not in {None, reference}:
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "proposal reference differs")
        try:
            existing = self.records.read_bytes(reference)
        except LabValidationError as exc:
            if exc.code != "STORAGE_RECORD_MISSING":
                raise
        else:
            if existing != encoded:
                raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "content-addressed proposal differs")
            return replace(result, content_reference=reference)
        self.records.write_bytes(reference, encoded)
        return replace(result, content_reference=reference)


def _proposal_bytes(value: bytes | str) -> bytes:
    if isinstance(value, str):
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise LabValidationError("INTEGRATION_RESULT_INVALID", "proposal is not UTF-8") from exc
    elif isinstance(value, bytes):
        encoded = value
    else:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "proposal must be bytes or text")
    if not encoded or len(encoded) > MAX_PROPOSAL_BYTES or b"\x00" in encoded:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "proposal is empty, unsafe, or oversized")
    try:
        text = encoded.decode("utf-8").lower()
    except UnicodeDecodeError as exc:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "proposal is not UTF-8") from exc
    if any(marker in text for marker in ("openai_api_key", "codex_api_key", "github_token", "gh_token", "authorization:", "bearer ", "\\\\", "//", ":\\", ":/")):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "proposal contains forbidden content")
    return encoded


@dataclass(frozen=True)
class WorkspaceEvidence:
    """Independently observed repository/workspace facts; never derived from worker prose."""

    observed_head: str
    changed_paths: tuple[str, ...]
    workspace_receipt_digest: str
    workspace_root_digest: str
    workspace_path_digest: str
    workspace_content_digest: str


def inspect_acceptance_workspace(
    record: InvocationRecord,
    *,
    state_root: Path,
    workspace_path: Path,
) -> WorkspaceEvidence:
    """Reload the protected receipt and independently inspect the exact Git workspace."""
    receipt = AtomicRecordStore(state_root).read(
        f"workspaces/{record.attempt_id}.json", WorkspaceReceipt.from_mapping,
    )
    from .windows_job import inspect_launch_workspace
    from .workspace import canonical_path_digest

    observed = inspect_launch_workspace(workspace_path)
    if (
        receipt.state is not WorkspaceReceiptState.PREPARED
        or receipt.attempt_id != record.attempt_id
        or receipt.template_commit != record.starting_commit
        or receipt.digest() != record.workspace_receipt_digest
        or receipt.workspace_root_digest != record.workspace_root_digest
        or receipt.workspace_path_digest != record.workspace_path_digest
        or canonical_path_digest(observed.workspace_path.parent) != record.workspace_root_digest
        or observed.workspace_path_digest != record.workspace_path_digest
    ):
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "workspace receipt evidence differs")
    return WorkspaceEvidence(
        observed_head=observed.observed_head,
        changed_paths=tuple(observed.status.splitlines()),
        workspace_receipt_digest=receipt.digest(),
        workspace_root_digest=receipt.workspace_root_digest,
        workspace_path_digest=receipt.workspace_path_digest,
        workspace_content_digest=observed.content_digest,
    )


def accept_execute_response(
    value: bytes,
    record: InvocationRecord,
    custody: ProcessCustodyRecord,
    *,
    runtime_identity: str,
    started_at: str,
    ended_at: str,
    state_root: Path,
    custody_store: ProcessCustodyStore,
    evidence_collector: object | None,
) -> ResultRecord:
    """Turn the exact fake adapter response into Worker Lab-owned strict evidence.

    Custody is reloaded first.  Only after process absence is proven does this
    function invoke the sealed Worker Lab collector; nothing is inferred from
    adapter/worker text or caller-created success objects.
    """
    if not isinstance(custody, ProcessCustodyRecord):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "custody evidence has an invalid type")
    from .read_only_evidence import ReadOnlyEvidenceCollector

    if not isinstance(evidence_collector, ReadOnlyEvidenceCollector):
        raise LabValidationError("INTEGRATION_EXECUTION_DISABLED", "a sealed evidence collector is required")
    reloaded = custody_store.read(custody.invocation_id)
    if reloaded != custody:
        raise LabValidationError("INTEGRATION_OUTCOME_UNCERTAIN", "custody must be the exact durable final record")
    if (
        custody.invocation_id != record.invocation_id
        or custody.invocation_digest != record.identity_digest()
        or custody.adapter_pid is None
        or custody.adapter_creation_time_100ns is None
        or not custody.request_sent
        or custody.state is not CustodyState.ABSENCE_VERIFIED
        or custody.active_process_count != 0
        or custody.exit_code != 0
        or custody.first_failure is not None
    ):
        raise LabValidationError("INTEGRATION_OUTCOME_UNCERTAIN", "custody is not a complete verified success")
    if not isinstance(value, bytes) or not value or len(value) > MAX_ADAPTER_RESPONSE_BYTES:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response is invalid")
    try:
        decoded = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter response is not UTF-8 JSON") from exc
    fields = {"invocation_digest", "prompt_digest", "runtime_identity", "proposal_digest", "output_digest", "proposal_content", "stdout_bytes", "stderr_bytes"}
    try:
        canonical_response = canonical_json(decoded).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LabValidationError("INTEGRATION_FIELDS_INVALID", "adapter execution response is not canonical") from exc
    if not isinstance(decoded, dict) or set(decoded) != fields or canonical_response != value:
        raise LabValidationError("INTEGRATION_FIELDS_INVALID", "adapter execution response fields are invalid")
    if decoded["invocation_digest"] != record.identity_digest() or decoded["prompt_digest"] != record.prompt_digest or decoded["runtime_identity"] != runtime_identity:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter response identity differs")
    content = _proposal_bytes(decoded["proposal_content"])
    content_digest = "sha256:" + hashlib.sha256(content).hexdigest()
    if decoded["proposal_digest"] != content_digest or decoded["output_digest"] != content_digest:
        raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "adapter proposal digest differs")
    if not isinstance(decoded["stdout_bytes"], int) or isinstance(decoded["stdout_bytes"], bool) or decoded["stdout_bytes"] != len(content):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter stdout count differs")
    if (
        not isinstance(decoded["stderr_bytes"], int)
        or isinstance(decoded["stderr_bytes"], bool)
        or decoded["stderr_bytes"] != 0
    ):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "successful adapter response cannot retain stderr")
    evidence = evidence_collector.collect(record)
    workspace_evidence = evidence.workspace
    validation_stages = evidence.validation_stages
    if not isinstance(workspace_evidence, WorkspaceEvidence):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "workspace verifier returned an invalid type")
    if (
        not isinstance(workspace_evidence.changed_paths, tuple)
        or not all(isinstance(path, str) for path in workspace_evidence.changed_paths)
        or not isinstance(validation_stages, tuple)
        or not all(isinstance(stage, ValidationStage) for stage in validation_stages)
    ):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "acceptance verifier evidence has an invalid shape")
    if (
        workspace_evidence.observed_head != record.starting_commit
        or workspace_evidence.changed_paths
        or workspace_evidence.workspace_receipt_digest != record.workspace_receipt_digest
        or workspace_evidence.workspace_root_digest != record.workspace_root_digest
        or workspace_evidence.workspace_path_digest != record.workspace_path_digest
        or workspace_evidence.workspace_content_digest != custody.workspace_content_digest
    ):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "independent workspace evidence differs")
    if tuple(stage.test_id for stage in validation_stages) != tuple(record.test_ids) or any(
        stage.outcome != "pass" or stage.failure_code is not None for stage in validation_stages
    ):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "independent test evidence differs")
    reference = f"proposals/{content_digest[7:]}.txt"
    result = ResultRecord.from_mapping({
        "schema_version": "worker-lab-framework-result:v1", "invocation_digest": record.identity_digest(),
        "request_digest": record.identity_digest(), "invocation_id": record.invocation_id, "attempt_id": record.attempt_id,
        "operation": str(record.operation), "framework_commit": record.framework_commit,
        "framework_contract_version": record.framework_contract_version, "runtime_profile_id": record.runtime_profile_id,
        "runtime_identity": runtime_identity, "prompt_digest": record.prompt_digest,
        "test_catalog_version": record.test_catalog_version, "test_catalog_digest": record.test_catalog_digest,
        "test_plan_digest": record.test_plan_digest, "test_ids": list(record.test_ids),
        "workspace_receipt_digest": record.workspace_receipt_digest, "workspace_root_digest": record.workspace_root_digest,
        "workspace_path_digest": record.workspace_path_digest, "starting_commit": record.starting_commit,
        "observed_head": workspace_evidence.observed_head, "process_outcome": "pass", "process_identity": custody.digest(),
        "process_started_at": started_at, "process_ended_at": ended_at, "workspace_state": "unchanged",
        "changed_paths": [], "proposal_digest": content_digest, "candidate_digest": None,
        "validation_stages": [stage.to_dict() for stage in validation_stages],
        "first_failure_boundary": None, "failure_code": None, "expected": "unchanged workspace",
        "observed": "unchanged workspace", "containment_outcome": "absence-verified", "output_digest": content_digest,
        "content_reference": reference, "retryable": False,
    })
    return ProposalStore(state_root).store(result, content)


def _digest(value: object) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter identity digest is invalid")
    if any(character not in "0123456789abcdef" for character in value[7:]):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "adapter identity digest is invalid")
    return value
