from __future__ import annotations

import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Mapping

from .canonical import canonical_digest
from .errors import LabValidationError
from .output_acceptance import OutputAcceptance
from .provider_binding import ProviderBinding, ProviderBindingStore
from .runtime_selection import resolve_runtime_identity


INVOCATION_SCHEMA_V3 = "worker-lab-framework-invocation:v3"
INVOCATION_SCHEMA_V4 = "worker-lab-framework-invocation:v4"
INVOCATION_IDENTITY_SCHEMA_V3 = "worker-lab-framework-invocation-identity:v3"
RESULT_SCHEMA_V3 = "worker-lab-framework-result:v3"
RESULT_SCHEMA_V4 = "worker-lab-framework-result:v4"
GIT_SOURCE_STATE_SCHEMA = "worker-lab-git-workspace-source-state:v1"
GIT_RESULT_EVIDENCE_SCHEMA = "worker-lab-git-workspace-result-evidence:v1"
WORKER_LAB_CONTRACT_VERSION_V3 = "worker-lab-runtime-contract:v3"
FRAMEWORK_DISPATCH_CONTRACT_V1 = "worker-lab-provider-dispatch:v1"
MAX_STRUCTURED_TEXT_BYTES = 2_048
MAX_CONTENT_REFERENCE_BYTES = 256

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,95}$")
_TARGET_ID_RE = re.compile(r"^target:[a-z][a-z0-9._-]{1,63}$")
_WORKSPACE_ID_RE = re.compile(r"^workspace:[A-Za-z0-9][A-Za-z0-9._-]{1,95}$")


class InvocationOperation(StrEnum):
    READ_ONLY_PROPOSAL = "read-only-proposal"
    WORKSPACE_WRITE_CODE_TASK = "workspace-write-code-task"


class InvocationState(StrEnum):
    PREPARED = "PREPARED"
    AUTHORIZED = "AUTHORIZED"
    DISPATCHING = "DISPATCHING"
    COMPLETED = "COMPLETED"
    OUTCOME_RECORDED = "OUTCOME_RECORDED"
    UNCERTAIN = "UNCERTAIN"
    REJECTED = "REJECTED"
    ABORTED = "ABORTED"


LEGAL_INVOCATION_TRANSITIONS = {
    InvocationState.PREPARED: frozenset({InvocationState.AUTHORIZED, InvocationState.REJECTED}),
    InvocationState.AUTHORIZED: frozenset({InvocationState.DISPATCHING, InvocationState.ABORTED, InvocationState.OUTCOME_RECORDED}),
    InvocationState.DISPATCHING: frozenset({InvocationState.COMPLETED, InvocationState.UNCERTAIN, InvocationState.OUTCOME_RECORDED}),
    InvocationState.COMPLETED: frozenset(),
    InvocationState.OUTCOME_RECORDED: frozenset(),
    InvocationState.UNCERTAIN: frozenset({InvocationState.ABORTED, InvocationState.OUTCOME_RECORDED}),
    InvocationState.REJECTED: frozenset(),
    InvocationState.ABORTED: frozenset(),
}


@dataclass(frozen=True)
class PathIdentity:
    path: str
    digest: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Any) -> "PathIdentity":
        data = _object(value, {"path", "digest"})
        return cls(_path(data["path"]), _digest(data["digest"], "path digest"))


@dataclass(frozen=True)
class GitWorkspaceSourceState:
    """Git-backed coding-workspace facts; never the logical target identity."""

    schema_version: str
    backend_id: str
    base_commit: str
    workspace_receipt_digest: str
    workspace_root_digest: str
    workspace_path_digest: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: Any) -> "GitWorkspaceSourceState":
        data = _object(value, {
            "schema_version", "backend_id", "base_commit",
            "workspace_receipt_digest", "workspace_root_digest", "workspace_path_digest",
        })
        return cls(
            _exact(data["schema_version"], GIT_SOURCE_STATE_SCHEMA, "source-state schema"),
            _exact(data["backend_id"], "git-workspace:v1", "source-state backend"),
            _sha(data["base_commit"]),
            _digest(data["workspace_receipt_digest"], "workspace receipt digest"),
            _digest(data["workspace_root_digest"], "workspace root digest"),
            _digest(data["workspace_path_digest"], "workspace path digest"),
        )


@dataclass(frozen=True)
class GitWorkspaceResultEvidence:
    schema_version: str
    backend_id: str
    base_commit: str
    observed_head: str
    workspace_receipt_digest: str
    workspace_root_digest: str
    workspace_path_digest: str
    workspace_content_digest: str
    workspace_state: str
    changed_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["changed_paths"] = list(self.changed_paths)
        return value

    @classmethod
    def from_mapping(cls, value: Any) -> "GitWorkspaceResultEvidence":
        data = _object(value, {
            "schema_version", "backend_id", "base_commit", "observed_head",
            "workspace_receipt_digest", "workspace_root_digest", "workspace_path_digest",
            "workspace_content_digest", "workspace_state", "changed_paths",
        })
        return cls(
            _exact(data["schema_version"], GIT_RESULT_EVIDENCE_SCHEMA, "result-evidence schema"),
            _exact(data["backend_id"], "git-workspace:v1", "result-evidence backend"),
            _sha(data["base_commit"]),
            _sha(data["observed_head"]),
            _digest(data["workspace_receipt_digest"], "workspace receipt digest"),
            _digest(data["workspace_root_digest"], "workspace root digest"),
            _digest(data["workspace_path_digest"], "workspace path digest"),
            _digest(data["workspace_content_digest"], "workspace content digest"),
            _choice(data["workspace_state"], {"unchanged", "changed", "boundary-failed", "unknown"}, "workspace state"),
            _paths(data["changed_paths"]),
        )


@dataclass(frozen=True)
class InvocationRecordV3:
    schema_version: str
    invocation_id: str
    attempt_id: str
    operation: InvocationOperation
    logical_target_id: str
    workspace_id: str
    exercise_id: str
    exercise_version: int
    exercise_digest: str
    policy_id: str
    policy_version: int
    policy_digest: str
    role_id: str
    role_version: int
    role_digest: str
    context_manifest_id: str
    context_manifest_version: int
    context_digest: str
    task_digest: str
    controller_task_packet_digest: str
    prompt_digest: str
    test_catalog_version: str
    test_catalog_digest: str
    test_plan_digest: str
    test_ids: tuple[str, ...]
    worker_lab_source_digest: str
    worker_lab_contract_version: str
    framework_source_digest: str
    framework_contract_version: str
    runtime_requirement_profile_id: str
    runtime_requirement_digest: str
    provider_binding_id: str
    provider_binding_digest: str
    sandbox_mode: str
    readable_paths: tuple[PathIdentity, ...]
    writable_paths: tuple[str, ...]
    source_state: GitWorkspaceSourceState | None
    authorized_by: str | None
    authorized_at: str | None
    state: InvocationState
    result_digest: str | None
    output_acceptance: OutputAcceptance | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["operation"] = str(self.operation)
        value["state"] = str(self.state)
        value["test_ids"] = list(self.test_ids)
        value["readable_paths"] = [item.to_dict() for item in self.readable_paths]
        value["writable_paths"] = list(self.writable_paths)
        value["source_state"] = None if self.source_state is None else self.source_state.to_dict()
        if self.schema_version == INVOCATION_SCHEMA_V4:
            value["output_acceptance"] = self.output_acceptance.to_dict()
        else:
            value.pop("output_acceptance")
        return value

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def identity_digest(self) -> str:
        value = self.to_dict()
        for field in ("authorized_by", "authorized_at", "state", "result_digest"):
            value.pop(field)
        return canonical_digest({"schema_version": INVOCATION_IDENTITY_SCHEMA_V3, "invocation": value})

    @classmethod
    def from_mapping(cls, value: Any) -> "InvocationRecordV3":
        fields = set(cls.__dataclass_fields__)
        if isinstance(value, Mapping) and value.get("schema_version") == INVOCATION_SCHEMA_V3:
            fields.remove("output_acceptance")
        data = _object(value, fields)
        try:
            operation = InvocationOperation(data["operation"])
            state = InvocationState(data["state"])
        except (TypeError, ValueError) as exc:
            raise LabValidationError("INTEGRATION_V3_INVOCATION_INVALID", "unsupported operation or state") from exc
        record = cls(
            _choice(data["schema_version"], {INVOCATION_SCHEMA_V3, INVOCATION_SCHEMA_V4}, "invocation schema"),
            _id(data["invocation_id"], "invocation id"),
            _id(data["attempt_id"], "attempt id"),
            operation,
            _logical_target_id(data["logical_target_id"]),
            _workspace_id(data["workspace_id"]),
            _id(data["exercise_id"], "exercise id"),
            _positive(data["exercise_version"], "exercise version"),
            _digest(data["exercise_digest"], "exercise digest"),
            _id(data["policy_id"], "policy id"),
            _positive(data["policy_version"], "policy version"),
            _digest(data["policy_digest"], "policy digest"),
            _id(data["role_id"], "role id"),
            _positive(data["role_version"], "role version"),
            _digest(data["role_digest"], "role digest"),
            _id(data["context_manifest_id"], "context manifest id"),
            _positive(data["context_manifest_version"], "context manifest version"),
            _digest(data["context_digest"], "context digest"),
            _digest(data["task_digest"], "task digest"),
            _digest(data["controller_task_packet_digest"], "controller task packet digest"),
            _digest(data["prompt_digest"], "prompt digest"),
            _text(data["test_catalog_version"], "test catalog version"),
            _digest(data["test_catalog_digest"], "test catalog digest"),
            _digest(data["test_plan_digest"], "test plan digest"),
            _texts(data["test_ids"], "test ids"),
            _digest(data["worker_lab_source_digest"], "Worker Lab source digest"),
            _exact(data["worker_lab_contract_version"], WORKER_LAB_CONTRACT_VERSION_V3, "Worker Lab contract"),
            _digest(data["framework_source_digest"], "framework source digest"),
            _exact(data["framework_contract_version"], FRAMEWORK_DISPATCH_CONTRACT_V1, "framework contract"),
            _text(data["runtime_requirement_profile_id"], "runtime requirement profile"),
            _digest(data["runtime_requirement_digest"], "runtime requirement digest"),
            _text(data["provider_binding_id"], "provider binding id"),
            _digest(data["provider_binding_digest"], "provider binding digest"),
            _choice(data["sandbox_mode"], {"read-only", "workspace-write"}, "sandbox mode"),
            _path_identities(data["readable_paths"]),
            _paths(data["writable_paths"]),
            None if data["source_state"] is None else GitWorkspaceSourceState.from_mapping(data["source_state"]),
            _optional_text(data["authorized_by"], "authorized by"),
            _optional_timestamp(data["authorized_at"], "authorized at"),
            state,
            _optional_digest(data["result_digest"], "result digest"),
            OutputAcceptance.from_mapping(data["output_acceptance"]) if "output_acceptance" in data else None,
        )
        _validate_invocation(record)
        return record


@dataclass(frozen=True)
class ValidationStage:
    test_id: str
    outcome: str
    failure_code: str | None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Any) -> "ValidationStage":
        data = _object(value, {"test_id", "outcome", "failure_code"})
        outcome = _choice(data["outcome"], {"pass", "fail", "not-run"}, "validation outcome")
        failure = _optional_text(data["failure_code"], "failure code")
        if (outcome == "fail") != (failure is not None):
            raise LabValidationError(
                "INTEGRATION_V3_RESULT_INVALID",
                "failed validation requires exactly one failure code",
            )
        return cls(_test_id(data["test_id"]), outcome, failure)


@dataclass(frozen=True)
class ResultRecordV3:
    schema_version: str
    invocation_digest: str
    request_digest: str
    invocation_id: str
    attempt_id: str
    operation: InvocationOperation
    logical_target_id: str
    workspace_id: str
    framework_source_digest: str
    framework_contract_version: str
    runtime_requirement_profile_id: str
    runtime_requirement_digest: str
    provider_binding_id: str
    provider_binding_digest: str
    runtime_identity: str
    controller_task_packet_digest: str
    prompt_digest: str
    test_catalog_version: str
    test_catalog_digest: str
    test_plan_digest: str
    test_ids: tuple[str, ...]
    process_outcome: str
    process_identity: str | None
    process_started_at: str
    process_ended_at: str
    source_evidence: GitWorkspaceResultEvidence | None
    proposal_digest: str | None
    candidate_digest: str | None
    validation_stages: tuple[ValidationStage, ...]
    first_failure_boundary: str | None
    failure_code: str | None
    expected: str
    observed: str
    containment_outcome: str
    output_digest: str
    content_reference: str | None
    retryable: bool

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["operation"] = str(self.operation)
        value["test_ids"] = list(self.test_ids)
        value["source_evidence"] = None if self.source_evidence is None else self.source_evidence.to_dict()
        value["validation_stages"] = [item.to_dict() for item in self.validation_stages]
        return value

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: Any) -> "ResultRecordV3":
        data = _object(value, set(cls.__dataclass_fields__))
        try:
            operation = InvocationOperation(data["operation"])
        except (TypeError, ValueError) as exc:
            raise LabValidationError("INTEGRATION_V3_RESULT_INVALID", "unsupported operation") from exc
        result = cls(
            _choice(data["schema_version"], {RESULT_SCHEMA_V3, RESULT_SCHEMA_V4}, "result schema"),
            _digest(data["invocation_digest"], "invocation digest"),
            _digest(data["request_digest"], "request digest"),
            _id(data["invocation_id"], "invocation id"),
            _id(data["attempt_id"], "attempt id"),
            operation,
            _logical_target_id(data["logical_target_id"]),
            _workspace_id(data["workspace_id"]),
            _digest(data["framework_source_digest"], "framework source digest"),
            _exact(data["framework_contract_version"], FRAMEWORK_DISPATCH_CONTRACT_V1, "framework contract"),
            _text(data["runtime_requirement_profile_id"], "runtime requirement profile"),
            _digest(data["runtime_requirement_digest"], "runtime requirement digest"),
            _text(data["provider_binding_id"], "provider binding id"),
            _digest(data["provider_binding_digest"], "provider binding digest"),
            _digest(data["runtime_identity"], "runtime identity"),
            _digest(data["controller_task_packet_digest"], "controller task packet digest"),
            _digest(data["prompt_digest"], "prompt digest"),
            _text(data["test_catalog_version"], "test catalog version"),
            _digest(data["test_catalog_digest"], "test catalog digest"),
            _digest(data["test_plan_digest"], "test plan digest"),
            _texts(data["test_ids"], "test ids"),
            _choice(data["process_outcome"], {"pass", "fail", "not-run", "uncertain"}, "process outcome"),
            _optional_digest(data["process_identity"], "process identity"),
            _timestamp(data["process_started_at"], "process started at"),
            _timestamp(data["process_ended_at"], "process ended at"),
            None if data["source_evidence"] is None else GitWorkspaceResultEvidence.from_mapping(data["source_evidence"]),
            _optional_digest(data["proposal_digest"], "proposal digest"),
            _optional_digest(data["candidate_digest"], "candidate digest"),
            _stages(data["validation_stages"]),
            _optional_text(data["first_failure_boundary"], "first failure boundary"),
            _optional_text(data["failure_code"], "failure code"),
            _bounded_text(data["expected"], "expected"),
            _bounded_text(data["observed"], "observed"),
            _text(data["containment_outcome"], "containment outcome"),
            _digest(data["output_digest"], "output digest"),
            _optional_content_reference(data["content_reference"]),
            _false(data["retryable"], "retryable"),
        )
        _validate_result(result)
        return result


def authorize_invocation(
    record: InvocationRecordV3,
    *,
    binding_store: ProviderBindingStore,
    controller_identity: str,
    authorized_at: str,
) -> InvocationRecordV3:
    """Authorize only after the exact current Provider Binding is durable."""
    if record.state is not InvocationState.PREPARED:
        raise LabValidationError(
            "INTEGRATION_V3_TRANSITION_INVALID",
            "authorization requires a PREPARED invocation",
        )
    try:
        binding = binding_store.require(record.provider_binding_id, record.provider_binding_digest)
    except LabValidationError as exc:
        if exc.code == "STORAGE_RECORD_MISSING":
            raise LabValidationError(
                "INTEGRATION_V3_PROVIDER_BINDING_UNKNOWN",
                "authorized provider binding is not durable",
            ) from exc
        if exc.code == "STORAGE_RECORD_INVALID":
            raise LabValidationError(
                "INTEGRATION_V3_PROVIDER_BINDING_INVALID",
                "durable provider binding is stale or invalid",
            ) from exc
        raise
    _validate_binding_reference(record, binding)
    return replace(
        record,
        authorized_by=_text(controller_identity, "controller identity"),
        authorized_at=_timestamp(authorized_at, "authorized at"),
        state=InvocationState.AUTHORIZED,
    )


def transition_invocation(
    record: InvocationRecordV3,
    target: InvocationState,
    *,
    result_digest: str | None = None,
) -> InvocationRecordV3:
    """Perform non-authorization transitions; authorization cannot bypass binding."""
    if target is InvocationState.AUTHORIZED:
        raise LabValidationError(
            "INTEGRATION_V3_PROVIDER_BINDING_REQUIRED",
            "authorization requires the Provider Binding gate",
        )
    if target not in LEGAL_INVOCATION_TRANSITIONS[record.state]:
        raise LabValidationError(
            "INTEGRATION_V3_TRANSITION_INVALID",
            "invocation transition is not legal",
        )
    if target in {InvocationState.COMPLETED, InvocationState.OUTCOME_RECORDED}:
        digest = _digest(result_digest, "result digest")
    elif result_digest is not None:
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "only completion accepts a result digest",
        )
    else:
        digest = None
    return replace(record, state=target, result_digest=digest)


def validate_result_for_invocation(result: ResultRecordV3, invocation: InvocationRecordV3) -> None:
    expected_schema = RESULT_SCHEMA_V4 if invocation.output_acceptance is not None else RESULT_SCHEMA_V3
    if result.schema_version != expected_schema:
        raise LabValidationError("INTEGRATION_V3_IDENTITY_INVALID", "result schema differs from invocation output contract")
    expected_identity = invocation.identity_digest()
    if (
        result.invocation_digest != expected_identity
        or result.request_digest != expected_identity
        or result.invocation_id != invocation.invocation_id
        or result.attempt_id != invocation.attempt_id
        or result.operation != invocation.operation
        or result.logical_target_id != invocation.logical_target_id
        or result.workspace_id != invocation.workspace_id
        or result.framework_source_digest != invocation.framework_source_digest
        or result.framework_contract_version != invocation.framework_contract_version
        or result.runtime_requirement_profile_id != invocation.runtime_requirement_profile_id
        or result.runtime_requirement_digest != invocation.runtime_requirement_digest
        or result.provider_binding_id != invocation.provider_binding_id
        or result.provider_binding_digest != invocation.provider_binding_digest
        or result.runtime_identity != invocation.provider_binding_digest
        or result.controller_task_packet_digest != invocation.controller_task_packet_digest
        or result.prompt_digest != invocation.prompt_digest
        or result.test_catalog_version != invocation.test_catalog_version
        or result.test_catalog_digest != invocation.test_catalog_digest
        or result.test_plan_digest != invocation.test_plan_digest
        or result.test_ids != invocation.test_ids
    ):
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "result does not bind the exact authorized invocation identity",
        )
    if invocation.source_state is None:
        if result.source_evidence is not None:
            raise LabValidationError(
                "INTEGRATION_V3_SOURCE_STATE_INVALID",
                "result contains substrate evidence absent from the invocation",
            )
        return
    evidence = result.source_evidence
    if (
        evidence is None
        or evidence.backend_id != invocation.source_state.backend_id
        or evidence.base_commit != invocation.source_state.base_commit
        or evidence.workspace_receipt_digest != invocation.source_state.workspace_receipt_digest
        or evidence.workspace_root_digest != invocation.source_state.workspace_root_digest
        or evidence.workspace_path_digest != invocation.source_state.workspace_path_digest
    ):
        raise LabValidationError(
            "INTEGRATION_V3_SOURCE_STATE_INVALID",
            "result substrate evidence differs from the sealed invocation source state",
        )
    if result.process_outcome == "pass":
        if evidence.observed_head != invocation.source_state.base_commit:
            raise LabValidationError(
                "INTEGRATION_V3_SOURCE_STATE_INVALID",
                "successful coding result changed the sealed Git HEAD",
            )
        if invocation.operation is InvocationOperation.READ_ONLY_PROPOSAL:
            if evidence.changed_paths:
                raise LabValidationError(
                    "INTEGRATION_V3_SCOPE_INVALID",
                    "read-only result changed the Git workspace",
                )
        elif not set(evidence.changed_paths) <= set(invocation.writable_paths):
            raise LabValidationError(
                "INTEGRATION_V3_SCOPE_INVALID",
                "result paths differ from the exact authorized write scope",
            )
        elif invocation.output_acceptance is not None:
            invocation.output_acceptance.validate_changes(evidence.changed_paths)
        elif not evidence.changed_paths:
            raise LabValidationError("INTEGRATION_V3_SCOPE_INVALID", "no-op requires an explicit output contract")


def _validate_invocation(record: InvocationRecordV3) -> None:
    if record.output_acceptance is not None and (
        record.operation is not InvocationOperation.WORKSPACE_WRITE_CODE_TASK
        or record.output_acceptance.allowed_writable_paths != record.writable_paths
    ):
        raise LabValidationError("INTEGRATION_V3_SCOPE_INVALID", "output contract differs from invocation permission")
    requirement = resolve_runtime_identity(
        record.runtime_requirement_profile_id,
        record.runtime_requirement_digest,
    )
    if not requirement.provider_binding_required:
        raise LabValidationError(
            "INTEGRATION_V3_RUNTIME_INVALID",
            "current runtime requirement must require a provider binding",
        )
    expected_sandbox = (
        "read-only"
        if record.operation is InvocationOperation.READ_ONLY_PROPOSAL
        else "workspace-write"
    )
    if record.sandbox_mode != expected_sandbox:
        raise LabValidationError("INTEGRATION_V3_OPERATION_INVALID", "operation and sandbox differ")
    if record.operation is InvocationOperation.READ_ONLY_PROPOSAL and record.writable_paths:
        raise LabValidationError(
            "INTEGRATION_V3_SCOPE_INVALID",
            "read-only proposal cannot name writable paths",
        )
    if record.operation is InvocationOperation.WORKSPACE_WRITE_CODE_TASK and not record.writable_paths:
        raise LabValidationError(
            "INTEGRATION_V3_SCOPE_INVALID",
            "code task requires writable paths",
        )
    if record.source_state is None:
        raise LabValidationError(
            "INTEGRATION_V3_SOURCE_STATE_INVALID",
            "current coding operations require Git workspace source state",
        )
    if record.state in {InvocationState.PREPARED, InvocationState.REJECTED}:
        if record.authorized_by is not None or record.authorized_at is not None:
            raise LabValidationError(
                "INTEGRATION_V3_AUTHORIZATION_INVALID",
                "unapproved invocation cannot carry authorization identity",
            )
    elif record.authorized_by is None or record.authorized_at is None:
        raise LabValidationError(
            "INTEGRATION_V3_AUTHORIZATION_INVALID",
            "authorized state requires controller identity and time",
        )
    if (record.state in {InvocationState.COMPLETED, InvocationState.OUTCOME_RECORDED}) != (record.result_digest is not None):
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "only completed invocation carries a result digest",
        )


def _validate_binding_reference(record: InvocationRecordV3, binding: ProviderBinding) -> None:
    if (
        binding.binding_id != record.provider_binding_id
        or binding.digest() != record.provider_binding_digest
        or binding.runtime_requirement_profile_id != record.runtime_requirement_profile_id
        or binding.runtime_requirement_digest != record.runtime_requirement_digest
    ):
        raise LabValidationError(
            "INTEGRATION_V3_PROVIDER_BINDING_MISMATCH",
            "provider binding differs from the sealed invocation reference",
        )


def _validate_result(result: ResultRecordV3) -> None:
    resolve_runtime_identity(
        result.runtime_requirement_profile_id,
        result.runtime_requirement_digest,
    )
    if result.process_ended_at < result.process_started_at:
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "process end cannot precede start",
        )
    failed = result.process_outcome in {"fail", "uncertain"}
    if failed != (result.first_failure_boundary is not None and result.failure_code is not None):
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "failure outcome requires first boundary and code",
        )
    if result.process_outcome == "pass" and (result.first_failure_boundary or result.failure_code):
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "successful result cannot report failure",
        )
    stage_ids = tuple(stage.test_id for stage in result.validation_stages)
    if stage_ids != result.test_ids[:len(stage_ids)]:
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "validation stages must follow the sealed test plan",
        )
    if result.process_outcome != "pass":
        return
    if (
        result.process_identity is None
        or result.source_evidence is None
        or result.content_reference is None
        or result.containment_outcome != "absence-verified"
    ):
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "successful result requires custody, source, content, and containment evidence",
        )
    if result.operation is InvocationOperation.READ_ONLY_PROPOSAL:
        if (
            result.source_evidence.workspace_state != "unchanged"
            or result.source_evidence.changed_paths
            or result.proposal_digest is None
            or result.candidate_digest is not None
        ):
            raise LabValidationError(
                "INTEGRATION_V3_RESULT_INVALID",
                "accepted proposal requires unchanged workspace and proposal evidence",
            )
    else:
        if (
            result.source_evidence.workspace_state != ("changed" if result.source_evidence.changed_paths else "unchanged")
            or (not result.source_evidence.changed_paths and result.schema_version != RESULT_SCHEMA_V4)
            or result.proposal_digest is not None
            or result.candidate_digest is None
            or tuple(stage.test_id for stage in result.validation_stages) != result.test_ids
            or any(stage.outcome != "pass" or stage.failure_code is not None for stage in result.validation_stages)
        ):
            raise LabValidationError(
                "INTEGRATION_V3_RESULT_INVALID",
                "accepted code task requires candidate, custody, and complete validation evidence",
            )


def _object(value: Any, expected: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise LabValidationError("INTEGRATION_V3_FIELDS_INVALID", "fields are missing or unknown")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or "\x00" in value:
        raise LabValidationError("INTEGRATION_V3_FIELD_INVALID", f"{name} is invalid")
    return value


def _id(value: Any, name: str) -> str:
    text = _text(value, name)
    if not _ID_RE.fullmatch(text):
        raise LabValidationError("INTEGRATION_V3_FIELD_INVALID", f"{name} is invalid")
    return text


def _test_id(value: Any) -> str:
    text = _text(value, "test id")
    if len(text) != 4 or not text.startswith("T") or not text[1:].isdigit():
        raise LabValidationError("INTEGRATION_V3_RESULT_INVALID", "test ID is invalid")
    return text


def _logical_target_id(value: Any) -> str:
    text = _text(value, "logical target id")
    if not _TARGET_ID_RE.fullmatch(text) or text.endswith(".git"):
        raise LabValidationError(
            "INTEGRATION_V3_TARGET_INVALID",
            "logical target identity must use the target: namespace, not a repository locator",
        )
    return text


def _workspace_id(value: Any) -> str:
    text = _text(value, "workspace id")
    if not _WORKSPACE_ID_RE.fullmatch(text) or text.endswith(".git"):
        raise LabValidationError(
            "INTEGRATION_V3_WORKSPACE_INVALID",
            "workspace identity must use the workspace: namespace, not a repository locator",
        )
    return text


def _sha(value: Any) -> str:
    text = _text(value, "commit")
    if not _SHA_RE.fullmatch(text):
        raise LabValidationError("INTEGRATION_V3_FIELD_INVALID", "commit must be a lowercase SHA")
    return text


def _digest(value: Any, name: str) -> str:
    text = _text(value, name)
    if not _DIGEST_RE.fullmatch(text):
        raise LabValidationError("INTEGRATION_V3_FIELD_INVALID", f"{name} is invalid")
    return text


def _optional_digest(value: Any, name: str) -> str | None:
    return None if value is None else _digest(value, name)


def _positive(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LabValidationError("INTEGRATION_V3_FIELD_INVALID", f"{name} must be positive")
    return value


def _path(value: Any) -> str:
    text = _text(value, "path")
    path = PurePosixPath(text)
    if (
        "\\" in text
        or text == "."
        or not path.parts
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != text
        or ":" in path.parts[0]
    ):
        raise LabValidationError(
            "INTEGRATION_V3_PATH_INVALID",
            "path must be normalized and relative",
        )
    return text


def _paths(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LabValidationError("INTEGRATION_V3_PATH_INVALID", "paths must be an array")
    paths = tuple(_path(item) for item in value)
    if paths != tuple(sorted(set(paths))):
        raise LabValidationError(
            "INTEGRATION_V3_PATH_INVALID",
            "paths must be sorted and unique",
        )
    return paths


def _texts(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LabValidationError("INTEGRATION_V3_FIELD_INVALID", f"{name} must be an array")
    items = tuple(_text(item, name) for item in value)
    if not items or items != tuple(sorted(set(items))):
        raise LabValidationError(
            "INTEGRATION_V3_FIELD_INVALID",
            f"{name} must be non-empty, sorted, and unique",
        )
    return items


def _path_identities(value: Any) -> tuple[PathIdentity, ...]:
    if not isinstance(value, list):
        raise LabValidationError(
            "INTEGRATION_V3_PATH_INVALID",
            "readable paths must be an array",
        )
    items = tuple(PathIdentity.from_mapping(item) for item in value)
    if not items or tuple(item.path for item in items) != tuple(sorted({item.path for item in items})):
        raise LabValidationError(
            "INTEGRATION_V3_PATH_INVALID",
            "readable paths must be sorted and unique",
        )
    return items


def _stages(value: Any) -> tuple[ValidationStage, ...]:
    if not isinstance(value, list):
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "validation stages must be an array",
        )
    stages = tuple(ValidationStage.from_mapping(item) for item in value)
    identifiers = tuple(stage.test_id for stage in stages)
    if len(identifiers) != len(set(identifiers)):
        raise LabValidationError(
            "INTEGRATION_V3_RESULT_INVALID",
            "validation stages must be unique",
        )
    return stages


def _choice(value: Any, choices: set[str], name: str) -> str:
    text = _text(value, name)
    if text not in choices:
        raise LabValidationError("INTEGRATION_V3_FIELD_INVALID", f"{name} is unsupported")
    return text


def _optional_text(value: Any, name: str) -> str | None:
    return None if value is None else _text(value, name)


def _bounded_text(value: Any, name: str) -> str:
    text = _text(value, name)
    if len(text.encode("utf-8")) > MAX_STRUCTURED_TEXT_BYTES:
        raise LabValidationError(
            "INTEGRATION_V3_FIELD_INVALID",
            f"{name} exceeds its retained-text limit",
        )
    lowered = text.lower()
    if any(marker in lowered for marker in (
        "openai_api_key", "provider_api_key", "github_token", "gh_token",
        "authorization:", "bearer ", "\\\\", "//", ":\\", ":/",
    )):
        raise LabValidationError(
            "INTEGRATION_V3_FIELD_INVALID",
            f"{name} contains forbidden retained content",
        )
    return text


def _optional_content_reference(value: Any) -> str | None:
    if value is None:
        return None
    reference = _path(value)
    if len(reference.encode("utf-8")) > MAX_CONTENT_REFERENCE_BYTES:
        raise LabValidationError(
            "INTEGRATION_V3_FIELD_INVALID",
            "content reference exceeds its limit",
        )
    return reference


def _optional_timestamp(value: Any, name: str) -> str | None:
    if value is None:
        return None
    text = _text(value, name)
    if not text.endswith("Z"):
        raise LabValidationError("INTEGRATION_V3_FIELD_INVALID", f"{name} must use UTC Z format")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise LabValidationError("INTEGRATION_V3_FIELD_INVALID", f"{name} is invalid") from exc
    if parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != text:
        raise LabValidationError(
            "INTEGRATION_V3_FIELD_INVALID",
            f"{name} must use UTC second precision",
        )
    return text


def _timestamp(value: Any, name: str) -> str:
    text = _optional_timestamp(value, name)
    if text is None:
        raise LabValidationError("INTEGRATION_V3_FIELD_INVALID", f"{name} is required")
    return text


def _false(value: Any, name: str) -> bool:
    if value is not False:
        raise LabValidationError("INTEGRATION_V3_RESULT_INVALID", f"{name} must be false")
    return False


def _exact(value: Any, expected: str, name: str) -> str:
    text = _text(value, name)
    if text != expected:
        raise LabValidationError("INTEGRATION_V3_VERSION_INVALID", f"{name} is unsupported")
    return text
