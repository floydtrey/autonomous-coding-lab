from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .attempt_store import AttemptStore
from .canonical import canonical_digest
from .controller_task_packet import ControllerTaskPacket, parse_controller_task_packet
from .dispatch_client import WORKSPACE_WRITE_TASK_SCHEMA, dispatch_workspace_write
from .errors import LabValidationError
from .git_workspace_evidence import inspect_git_workspace_result
from .integration_v3 import (
    FRAMEWORK_DISPATCH_CONTRACT_V1,
    GIT_SOURCE_STATE_SCHEMA,
    INVOCATION_SCHEMA_V3,
    WORKER_LAB_CONTRACT_VERSION_V3,
    InvocationOperation,
    InvocationRecordV3,
    InvocationState,
    ResultRecordV3,
    ValidationStage,
    authorize_invocation as authorize_v3,
    transition_invocation,
)
from .invocation_store_v3 import InvocationStoreV3
from .lifecycle import transition_attempt
from .models import AttemptRecord, AttemptState, ExerciseRecord, WorkspaceReceipt, WorkspaceReceiptState
from .operator_control import validate_controller_identity
from .policy import ContextManifest, PolicyRecord, RoleRecord, validate_authority
from .process_custody import (
    CustodyBackend,
    CustodyState,
    ProcessCustodyRecord,
    ProcessCustodyStore,
    recover_absence_after_controller_exit,
)
from .provider_binding import ProviderBindingStore
from .result_acceptance_v3 import (
    accept_workspace_write_response_v3,
    parse_result_v3,
    verify_workspace_write_candidate_manifest_v3,
)
from .storage import AtomicRecordStore
from .test_catalog import ChangeFacts, TestCatalog, TestDefinition, TestRunner
from .validation import attempt_task_digest
from .windows_job import WorkspaceLaunchEvidence, inspect_launch_workspace, workspace_content_digest
from .workspace import canonical_path_digest, verify_workspace


RECOVERY_CLEANUP_OUTCOME = (
    "adapter absence and unchanged workspace verified; workspace retained"
)
_DIGEST_PREFIX = "sha256:"
_PORTABLE_SCHEMA = "acl-portable-installation-manifest:v1"

Clock = Callable[[], str]
WorkspaceDispatchRunner = Callable[
    [bytes, InvocationRecordV3, Path, ProcessCustodyStore],
    bytes,
]
SealedTestExecutor = Callable[[TestDefinition, Path], int]


@dataclass(frozen=True)
class RecoveryStateV3:
    controller_identity: str
    invocation: InvocationRecordV3
    attempt: AttemptRecord
    custody: ProcessCustodyRecord
    workspace: WorkspaceLaunchEvidence


@dataclass(frozen=True)
class CandidateReviewStateV3:
    invocation: InvocationRecordV3
    result: ResultRecordV3
    custody: ProcessCustodyRecord
    retained_framework_candidate_digest: str
    changed_paths: tuple[str, ...]
    validation_stages: tuple[ValidationStage, ...]
    first_failure_boundary: str | None


def prepare_invocation(
    data_root: Path,
    *,
    attempt_id: str,
    workspace_root: Path,
    prompt: str,
    logical_target_id: str,
    provider_binding_id: str,
    provider_binding_digest: str,
) -> InvocationRecordV3:
    state_root = data_root / "state"
    attempt = AttemptStore(state_root).read(attempt_id)
    if attempt.state is not AttemptState.READY:
        raise LabValidationError(
            "INTEGRATION_V3_ATTEMPT_STATE_INVALID",
            "V3 invocation preparation requires a READY attempt",
        )
    if attempt.sandbox_mode != "workspace-write":
        raise LabValidationError(
            "INTEGRATION_V3_OPERATION_INVALID",
            "the current V3 service slice supports workspace-write tasks only",
        )
    _require_no_invocation_for_attempt(state_root, attempt_id)
    exercise, policy, role, context, catalog = _definitions_for_attempt(data_root, attempt)
    receipt = verify_workspace(data_root, attempt_id, workspace_root)
    plan = catalog.select(
        ChangeFacts(exercise.writable_paths),
        profile_ids=exercise.test_profile_ids,
    )
    packet = parse_controller_task_packet(prompt)
    _validate_controller_packet(packet, attempt, exercise)
    prompt_bytes = _prompt_bytes(prompt)
    prompt_digest = _bytes_digest(prompt_bytes)
    if packet.digest() != prompt_digest:
        raise LabValidationError(
            "CONTROLLER_PACKET_IDENTITY_INVALID",
            "Controller Task Packet digest differs from its exact prompt bytes",
        )

    binding_store = ProviderBindingStore(state_root)
    binding = binding_store.require(provider_binding_id, provider_binding_digest)
    worker_source_digest, framework_source_digest = _current_source_digests()
    invocation = InvocationRecordV3.from_mapping({
        "schema_version": INVOCATION_SCHEMA_V3,
        "invocation_id": _new_invocation_id(),
        "attempt_id": attempt.attempt_id,
        "operation": str(InvocationOperation.WORKSPACE_WRITE_CODE_TASK),
        "logical_target_id": logical_target_id,
        "workspace_id": f"workspace:{attempt.attempt_id}",
        "exercise_id": exercise.exercise_id,
        "exercise_version": exercise.exercise_version,
        "exercise_digest": exercise.digest(),
        "policy_id": policy.policy_id,
        "policy_version": policy.policy_version,
        "policy_digest": policy.digest(),
        "role_id": role.role_id,
        "role_version": role.role_version,
        "role_digest": role.digest(),
        "context_manifest_id": context.manifest_id,
        "context_manifest_version": context.manifest_version,
        "context_digest": context.digest(),
        "task_digest": attempt.task_digest,
        "controller_task_packet_digest": packet.digest(),
        "prompt_digest": prompt_digest,
        "test_catalog_version": catalog.catalog_version,
        "test_catalog_digest": catalog.digest(),
        "test_plan_digest": canonical_digest(plan.to_dict()),
        "test_ids": list(plan.test_ids),
        "worker_lab_source_digest": worker_source_digest,
        "worker_lab_contract_version": WORKER_LAB_CONTRACT_VERSION_V3,
        "framework_source_digest": framework_source_digest,
        "framework_contract_version": FRAMEWORK_DISPATCH_CONTRACT_V1,
        "runtime_requirement_profile_id": binding.runtime_requirement_profile_id,
        "runtime_requirement_digest": binding.runtime_requirement_digest,
        "provider_binding_id": binding.binding_id,
        "provider_binding_digest": binding.digest(),
        "sandbox_mode": "workspace-write",
        "readable_paths": [
            {"path": item.path, "digest": item.digest}
            for item in sorted(context.files, key=lambda item: item.path)
        ],
        "writable_paths": sorted(exercise.writable_paths),
        "source_state": {
            "schema_version": GIT_SOURCE_STATE_SCHEMA,
            "backend_id": "git-workspace:v1",
            "base_commit": attempt.starting_commit,
            "workspace_receipt_digest": receipt.digest(),
            "workspace_root_digest": receipt.workspace_root_digest,
            "workspace_path_digest": receipt.workspace_path_digest,
        },
        "authorized_by": None,
        "authorized_at": None,
        "state": str(InvocationState.PREPARED),
        "result_digest": None,
    })
    _store_prompt(state_root, prompt_bytes)
    InvocationStoreV3(state_root).create(invocation)
    return invocation


def authorize_invocation(
    data_root: Path,
    *,
    invocation_id: str,
    expected_identity_digest: str,
    controller_identity: str,
    authorized_at: str,
) -> InvocationRecordV3:
    state_root = data_root / "state"
    store = InvocationStoreV3(state_root)
    current = store.read(invocation_id)
    if current.identity_digest() != _digest(expected_identity_digest, "expected invocation identity"):
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "invocation identity differs from authorization command",
        )
    controller = validate_controller_identity(controller_identity)
    packet = parse_controller_task_packet(_load_prompt(state_root, current))
    if packet.controller_identity != controller:
        raise LabValidationError(
            "OPERATOR_CONTROLLER_MISMATCH",
            "authorization controller differs from the sealed Controller Task Packet",
        )
    binding_store = ProviderBindingStore(state_root)
    authorized = authorize_v3(
        current,
        binding_store=binding_store,
        controller_identity=controller,
        authorized_at=authorized_at,
    )
    store.save_transition(
        authorized,
        expected_digest=current.digest(),
        binding_store=binding_store,
    )
    return authorized


def reject_invocation(
    data_root: Path,
    *,
    invocation_id: str,
    expected_identity_digest: str,
) -> InvocationRecordV3:
    store = InvocationStoreV3(data_root / "state")
    current = store.read(invocation_id)
    if current.identity_digest() != _digest(expected_identity_digest, "expected invocation identity"):
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "invocation identity differs from rejection command",
        )
    rejected = transition_invocation(current, InvocationState.REJECTED)
    store.save_transition(rejected, expected_digest=current.digest())
    return rejected


def cancel_invocation(
    data_root: Path,
    *,
    invocation_id: str,
    expected_identity_digest: str,
    controller_identity: str,
) -> InvocationRecordV3:
    store = InvocationStoreV3(data_root / "state")
    current = store.read(invocation_id)
    if current.identity_digest() != _digest(expected_identity_digest, "expected invocation identity"):
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "invocation identity differs from cancellation command",
        )
    controller = validate_controller_identity(controller_identity)
    if current.state is not InvocationState.AUTHORIZED:
        raise LabValidationError(
            "INTEGRATION_V3_TRANSITION_INVALID",
            "only an authorized V3 invocation may be cancelled directly",
        )
    if current.authorized_by != controller:
        raise LabValidationError(
            "OPERATOR_CONTROLLER_MISMATCH",
            "cancellation controller differs from invocation authorization",
        )
    cancelled = transition_invocation(current, InvocationState.ABORTED)
    store.save_transition(cancelled, expected_digest=current.digest())
    return cancelled


def dispatch_invocation(
    data_root: Path,
    *,
    invocation_id: str,
    expected_identity_digest: str,
    controller_identity: str,
    workspace_root: Path,
    clock: Clock,
    workspace_dispatch_runner: WorkspaceDispatchRunner | None,
    sealed_test_executor: SealedTestExecutor,
) -> AttemptRecord:
    if workspace_dispatch_runner is None or not callable(workspace_dispatch_runner):
        raise LabValidationError(
            "INTEGRATION_EXECUTION_DISABLED",
            "V3 dispatch requires an explicitly injected framework/provider runner",
        )
    state_root = data_root / "state"
    invocation_store = InvocationStoreV3(state_root)
    invocation = invocation_store.read(invocation_id)
    expected = _digest(expected_identity_digest, "expected invocation identity")
    if invocation.identity_digest() != expected:
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "invocation identity differs from dispatch command",
        )
    controller = validate_controller_identity(controller_identity)
    if invocation.state is not InvocationState.AUTHORIZED:
        raise LabValidationError(
            "INTEGRATION_V3_AUTHORIZATION_INVALID",
            "dispatch requires an authorized V3 invocation",
        )
    if invocation.authorized_by != controller:
        raise LabValidationError(
            "OPERATOR_CONTROLLER_MISMATCH",
            "dispatch controller differs from invocation authorization",
        )
    if invocation.operation is not InvocationOperation.WORKSPACE_WRITE_CODE_TASK:
        raise LabValidationError(
            "INTEGRATION_V3_OPERATION_INVALID",
            "current service dispatch supports only the V3 workspace-write task",
        )

    attempt_store = AttemptStore(state_root)
    attempt = attempt_store.read(invocation.attempt_id)
    _validate_dispatch_attempt_binding(attempt, invocation)
    exercise, policy, role, context, catalog = _validate_dispatch_definitions(
        data_root, attempt, invocation
    )
    receipt = verify_workspace(data_root, attempt.attempt_id, workspace_root)
    _validate_receipt(invocation, receipt, workspace_root)
    _require_no_dispatch_artifacts(state_root, invocation.invocation_id)
    prompt = _load_prompt(state_root, invocation)
    packet = parse_controller_task_packet(prompt)
    if packet.controller_identity != controller:
        raise LabValidationError(
            "OPERATOR_CONTROLLER_MISMATCH",
            "dispatch controller differs from the sealed Controller Task Packet",
        )
    workspace_task = _workspace_write_task(
        invocation, exercise, policy, role, context, catalog
    )
    workspace_path = workspace_root / attempt.attempt_id

    occurred_at = clock()
    running = transition_attempt(
        attempt,
        AttemptState.RUNNING,
        occurred_at=occurred_at,
        runtime_identity=invocation.identity_digest(),
    )
    attempt_store.save_transition(running)
    dispatching = transition_invocation(invocation, InvocationState.DISPATCHING)
    invocation_store.save_transition(
        dispatching,
        expected_digest=invocation.digest(),
    )

    custody_store = ProcessCustodyStore(state_root)
    started_at = clock()

    def run_framework(payload: bytes) -> bytes:
        response = workspace_dispatch_runner(
            payload,
            dispatching,
            workspace_path,
            custody_store,
        )
        if not isinstance(response, bytes):
            raise LabValidationError(
                "INTEGRATION_V3_RESULT_INVALID",
                "injected framework runner must return response bytes",
            )
        return response

    response = dispatch_workspace_write(
        dispatching,
        prompt=prompt,
        workspace_write=workspace_task,
        binding_store=ProviderBindingStore(state_root),
        runner=run_framework,
    )
    ended_at = clock()
    custody = custody_store.read(invocation.invocation_id)
    validation_stages = _run_sealed_tests(
        dispatching,
        catalog,
        workspace_path,
        sealed_test_executor,
    )
    source_evidence = inspect_git_workspace_result(
        dispatching,
        state_root=state_root,
        workspace_path=workspace_path,
    )
    result = accept_workspace_write_response_v3(
        response,
        dispatching,
        custody,
        started_at=started_at,
        ended_at=ended_at,
        state_root=state_root,
        custody_store=custody_store,
        source_evidence=source_evidence,
        validation_stages=validation_stages,
    )
    AtomicRecordStore(state_root).write(
        f"results/{invocation.invocation_id}.json",
        result,
    )
    completed = transition_invocation(
        dispatching,
        InvocationState.COMPLETED,
        result_digest=result.digest(),
    )
    invocation_store.save_transition(
        completed,
        expected_digest=dispatching.digest(),
    )
    durable_running = attempt_store.read(attempt.attempt_id)
    _validate_running_dispatch_binding(durable_running, completed)
    candidate = transition_attempt(
        durable_running,
        AttemptState.CANDIDATE,
        occurred_at=clock(),
        candidate_digest=result.digest(),
    )
    attempt_store.save_transition(candidate)
    return candidate


def recover_invocation(
    data_root: Path,
    *,
    invocation_id: str,
    expected_identity_digest: str,
    controller_identity: str,
    workspace_root: Path,
    clock: Clock,
    custody_backend: CustodyBackend,
) -> RecoveryStateV3:
    state_root = data_root / "state"
    invocation_store = InvocationStoreV3(state_root)
    invocation = invocation_store.read(invocation_id)
    expected = _digest(expected_identity_digest, "expected invocation identity")
    if invocation.identity_digest() != expected:
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "invocation identity differs from recovery command",
        )
    controller = validate_controller_identity(controller_identity)
    if invocation.authorized_by != controller:
        raise LabValidationError(
            "OPERATOR_CONTROLLER_MISMATCH",
            "recovery controller differs from invocation authorization",
        )
    if invocation.state not in {
        InvocationState.DISPATCHING,
        InvocationState.UNCERTAIN,
        InvocationState.ABORTED,
    }:
        raise LabValidationError(
            "OPERATOR_RECOVERY_INVALID",
            "V3 invocation state is not recoverable",
        )

    attempt_store = AttemptStore(state_root)
    attempt = attempt_store.read(invocation.attempt_id)
    _validate_recovery_attempt_binding(attempt, invocation)
    if attempt.state not in {AttemptState.RUNNING, AttemptState.ABORTED}:
        raise LabValidationError(
            "OPERATOR_RECOVERY_INVALID",
            "attempt state is not recoverable",
        )
    if attempt.state is AttemptState.ABORTED:
        if (
            invocation.state is not InvocationState.ABORTED
            or attempt.cleanup_outcome != RECOVERY_CLEANUP_OUTCOME
        ):
            raise LabValidationError(
                "OPERATOR_RECOVERY_INVALID",
                "terminal recovery records differ",
            )

    result_path = state_root / "results" / f"{invocation_id}.json"
    if os.path.lexists(result_path):
        raise LabValidationError(
            "OPERATOR_RECOVERY_INVALID",
            "uncertain invocation cannot retain a result record",
        )
    receipt = AtomicRecordStore(state_root).read(
        f"workspaces/{attempt.attempt_id}.json",
        WorkspaceReceipt.from_mapping,
    )
    workspace = inspect_launch_workspace(workspace_root / attempt.attempt_id)
    _validate_recovery_workspace(
        workspace_root,
        workspace,
        receipt,
        attempt,
        invocation,
    )

    custody_store = ProcessCustodyStore(state_root)
    custody = custody_store.read(invocation_id)
    if (
        custody.invocation_id != invocation_id
        or custody.invocation_digest != expected
        or custody.worker_identity is None
        or not custody.request_sent
    ):
        raise LabValidationError(
            "OPERATOR_RECOVERY_INVALID",
            "process custody is not bound to the dispatched V3 invocation",
        )
    occurred_at = clock()
    verified_custody = custody
    if custody.state is CustodyState.TERMINATED:
        recovered = recover_absence_after_controller_exit(
            custody,
            backend=custody_backend,
            now=lambda: occurred_at,
        )
        if recovered is None:
            raise LabValidationError(
                "OPERATOR_RECOVERY_ACTIVE",
                "original controller process is still active",
            )
        _, verified_custody = recovered
    elif custody.state is not CustodyState.ABSENCE_VERIFIED:
        raise LabValidationError(
            "INTEGRATION_OUTCOME_UNCERTAIN",
            "process custody cannot prove adapter absence",
        )
    if (
        verified_custody.active_workload_count != 0
        or verified_custody.absence_evidence_digest is None
        or verified_custody.absence_verified_at is None
        or verified_custody.workspace_content_digest != workspace.content_digest
    ):
        raise LabValidationError(
            "OPERATOR_RECOVERY_INVALID",
            "workspace or process-absence evidence differs",
        )

    aborted_attempt = (
        transition_attempt(
            attempt,
            AttemptState.ABORTED,
            occurred_at=occurred_at,
            cleanup_outcome=RECOVERY_CLEANUP_OUTCOME,
        )
        if attempt.state is AttemptState.RUNNING
        else attempt
    )
    if custody.state is CustodyState.TERMINATED:
        custody_store.save_transition(
            verified_custody,
            expected_digest=custody.digest(),
        )

    current_invocation = invocation
    if current_invocation.state is InvocationState.DISPATCHING:
        uncertain = transition_invocation(
            current_invocation,
            InvocationState.UNCERTAIN,
        )
        invocation_store.save_transition(
            uncertain,
            expected_digest=current_invocation.digest(),
        )
        current_invocation = uncertain
    if current_invocation.state is InvocationState.UNCERTAIN:
        aborted = transition_invocation(
            current_invocation,
            InvocationState.ABORTED,
        )
        invocation_store.save_transition(
            aborted,
            expected_digest=current_invocation.digest(),
        )
        current_invocation = aborted
    if attempt.state is AttemptState.RUNNING:
        attempt_store.save_transition(aborted_attempt)

    durable_custody = custody_store.read(invocation_id)
    durable_invocation = invocation_store.read(invocation_id)
    durable_attempt = attempt_store.read(attempt.attempt_id)
    if (
        durable_custody != verified_custody
        or durable_invocation != current_invocation
        or durable_attempt != aborted_attempt
        or durable_invocation.state is not InvocationState.ABORTED
        or durable_attempt.state is not AttemptState.ABORTED
    ):
        raise LabValidationError(
            "OPERATOR_RECOVERY_INVALID",
            "durable V3 recovery records differ",
        )
    return RecoveryStateV3(
        controller,
        durable_invocation,
        durable_attempt,
        durable_custody,
        workspace,
    )


def review_candidate(
    state_root: Path,
    *,
    attempt: AttemptRecord,
    invocation: InvocationRecordV3,
    result: ResultRecordV3,
    custody: ProcessCustodyRecord,
) -> CandidateReviewStateV3:
    if (
        invocation.state is not InvocationState.COMPLETED
        or invocation.result_digest != result.digest()
        or attempt.candidate_digest != result.digest()
        or attempt.runtime_identity != invocation.identity_digest()
        or custody.invocation_id != invocation.invocation_id
        or custody.invocation_digest != invocation.identity_digest()
        or custody.state is not CustodyState.ABSENCE_VERIFIED
        or result.process_identity != custody.digest()
    ):
        raise LabValidationError(
            "SERVICE_CANDIDATE_IDENTITY_INVALID",
            "V3 candidate records do not share an exact durable identity",
        )
    parse_result_v3(
        json.dumps(
            result.to_dict(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        invocation,
    )
    if result.content_reference is None or result.source_evidence is None:
        raise LabValidationError(
            "SERVICE_CANDIDATE_CONTENT_MISSING",
            "V3 candidate content is not retained",
        )
    content = AtomicRecordStore(state_root).read_bytes(result.content_reference)
    retained = verify_workspace_write_candidate_manifest_v3(
        content,
        invocation,
        result,
    )
    return CandidateReviewStateV3(
        invocation,
        result,
        custody,
        retained,
        result.source_evidence.changed_paths,
        result.validation_stages,
        result.first_failure_boundary,
    )


def load_invocation_record(value: Any):
    if isinstance(value, Mapping) and value.get("schema_version") == INVOCATION_SCHEMA_V3:
        return InvocationRecordV3.from_mapping(value)
    from .integration import InvocationRecord
    return InvocationRecord.from_mapping(value)


def load_result_record(value: Any):
    if isinstance(value, Mapping) and value.get("schema_version") == "worker-lab-framework-result:v3":
        return ResultRecordV3.from_mapping(value)
    from .integration import ResultRecord
    return ResultRecord.from_mapping(value)


def _require_no_invocation_for_attempt(state_root: Path, attempt_id: str) -> None:
    store = AtomicRecordStore(state_root)
    for path in store.list_paths("invocations"):
        raw = store.read_bytes(path)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LabValidationError(
                "STORAGE_RECORD_INVALID",
                f"{path}: invocation record is invalid",
            ) from exc
        if not isinstance(value, dict):
            raise LabValidationError(
                "STORAGE_RECORD_INVALID",
                f"{path}: invocation record is invalid",
            )
        if value.get("attempt_id") == attempt_id:
            raise LabValidationError(
                "INTEGRATION_V3_INVOCATION_EXISTS",
                "attempt already has a durable invocation",
            )


def _definitions_for_attempt(
    data_root: Path,
    attempt: AttemptRecord,
) -> tuple[ExerciseRecord, PolicyRecord, RoleRecord, ContextManifest, TestCatalog]:
    definitions = AtomicRecordStore(data_root / "curricula")
    exercise = definitions.read(
        f"exercises/{attempt.exercise_id}/v{attempt.exercise_version}.json",
        ExerciseRecord.from_mapping,
    )
    policy = definitions.read(
        f"policies/{attempt.policy_id}/v{attempt.policy_version}.json",
        PolicyRecord.from_mapping,
    )
    role = definitions.read(
        f"roles/{attempt.role_id}/v{attempt.role_version}.json",
        RoleRecord.from_mapping,
    )
    context = definitions.read(
        f"contexts/{exercise.context_manifest_id}/v{exercise.context_manifest_version}.json",
        ContextManifest.from_mapping,
    )
    catalog = definitions.read(
        f"catalogs/{attempt.evaluator_catalog_version}.json",
        TestCatalog.from_mapping,
    )
    _validate_attempt_definitions(attempt, exercise, policy, role, context, catalog)
    return exercise, policy, role, context, catalog


def _validate_dispatch_definitions(
    data_root: Path,
    attempt: AttemptRecord,
    invocation: InvocationRecordV3,
) -> tuple[ExerciseRecord, PolicyRecord, RoleRecord, ContextManifest, TestCatalog]:
    exercise, policy, role, context, catalog = _definitions_for_attempt(data_root, attempt)
    if (
        invocation.exercise_id != exercise.exercise_id
        or invocation.exercise_version != exercise.exercise_version
        or invocation.exercise_digest != exercise.digest()
        or invocation.policy_id != policy.policy_id
        or invocation.policy_version != policy.policy_version
        or invocation.policy_digest != policy.digest()
        or invocation.role_id != role.role_id
        or invocation.role_version != role.role_version
        or invocation.role_digest != role.digest()
        or invocation.context_manifest_id != context.manifest_id
        or invocation.context_manifest_version != context.manifest_version
        or invocation.context_digest != context.digest()
        or invocation.test_catalog_version != catalog.catalog_version
        or invocation.test_catalog_digest != catalog.digest()
    ):
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "V3 invocation differs from protected dispatch definitions",
        )
    plan = catalog.select(
        ChangeFacts(invocation.writable_paths),
        profile_ids=exercise.test_profile_ids,
    )
    if (
        plan.catalog_version != invocation.test_catalog_version
        or plan.catalog_digest != invocation.test_catalog_digest
        or plan.test_ids != invocation.test_ids
        or canonical_digest(plan.to_dict()) != invocation.test_plan_digest
    ):
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "V3 workspace-write test plan differs from protected definitions",
        )
    return exercise, policy, role, context, catalog


def _validate_attempt_definitions(
    attempt: AttemptRecord,
    exercise: ExerciseRecord,
    policy: PolicyRecord,
    role: RoleRecord,
    context: ContextManifest,
    catalog: TestCatalog,
) -> None:
    if (policy.policy_id, policy.policy_version) != (
        exercise.policy_id,
        exercise.policy_version,
    ):
        raise LabValidationError(
            "ATTEMPT_POLICY_MISMATCH",
            "exercise policy identity is unresolved",
        )
    if (role.role_id, role.role_version) != (exercise.role_id, exercise.role_version):
        raise LabValidationError(
            "ATTEMPT_ROLE_MISMATCH",
            "exercise role identity is unresolved",
        )
    if (
        context.repository != exercise.template_repository
        or context.starting_commit != exercise.template_commit
    ):
        raise LabValidationError(
            "ATTEMPT_CONTEXT_MISMATCH",
            "context repository or starting commit differs",
        )
    if catalog.catalog_version != exercise.evaluator_catalog_version:
        raise LabValidationError(
            "ATTEMPT_CATALOG_MISMATCH",
            "evaluator catalog is unresolved",
        )
    known_profiles = {profile.profile_id for profile in catalog.profiles}
    missing_profiles = set(exercise.test_profile_ids) - known_profiles
    if missing_profiles:
        raise LabValidationError(
            "ATTEMPT_PROFILE_MISSING",
            f"unknown test profiles: {sorted(missing_profiles)}",
        )
    validate_authority(
        policy,
        role,
        required_capabilities=exercise.required_capabilities,
        temporary_denied_capabilities=exercise.temporary_denied_capabilities,
    )
    expected = (
        attempt.curriculum_id == exercise.curriculum_id,
        attempt.exercise_id == exercise.exercise_id,
        attempt.exercise_version == exercise.exercise_version,
        attempt.starting_commit == exercise.template_commit,
        attempt.context_digest == context.digest(),
        attempt.task_digest == attempt_task_digest(exercise, policy, role, context, catalog),
        attempt.policy_id == policy.policy_id,
        attempt.policy_version == policy.policy_version,
        attempt.policy_digest == policy.digest(),
        attempt.role_id == role.role_id,
        attempt.role_version == role.role_version,
        attempt.role_digest == role.digest(),
        attempt.sandbox_mode == exercise.sandbox_mode,
        attempt.evaluator_catalog_version == catalog.catalog_version,
        attempt.evaluator_catalog_digest == catalog.digest(),
    )
    if not all(expected):
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "attempt identity differs from protected V3 invocation definitions",
        )


def _validate_controller_packet(
    packet: ControllerTaskPacket,
    attempt: AttemptRecord,
    exercise: ExerciseRecord,
) -> None:
    if (
        packet.attempt_id != attempt.attempt_id
        or packet.exercise_id != exercise.exercise_id
        or packet.exercise_version != exercise.exercise_version
        or packet.starting_commit != attempt.starting_commit
    ):
        raise LabValidationError(
            "CONTROLLER_PACKET_IDENTITY_INVALID",
            "Controller Task Packet differs from the READY attempt",
        )


def _validate_dispatch_attempt_binding(
    attempt: AttemptRecord,
    invocation: InvocationRecordV3,
) -> None:
    source = invocation.source_state
    if (
        attempt.state is not AttemptState.READY
        or attempt.runtime_identity is not None
        or attempt.candidate_digest is not None
        or invocation.attempt_id != attempt.attempt_id
        or invocation.exercise_id != attempt.exercise_id
        or invocation.exercise_version != attempt.exercise_version
        or invocation.policy_id != attempt.policy_id
        or invocation.policy_version != attempt.policy_version
        or invocation.policy_digest != attempt.policy_digest
        or invocation.role_id != attempt.role_id
        or invocation.role_version != attempt.role_version
        or invocation.role_digest != attempt.role_digest
        or invocation.context_digest != attempt.context_digest
        or invocation.task_digest != attempt.task_digest
        or invocation.test_catalog_version != attempt.evaluator_catalog_version
        or invocation.test_catalog_digest != attempt.evaluator_catalog_digest
        or source is None
        or source.base_commit != attempt.starting_commit
        or invocation.sandbox_mode != attempt.sandbox_mode
    ):
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "authorized V3 invocation differs from dispatch attempt",
        )


def _validate_running_dispatch_binding(
    attempt: AttemptRecord,
    invocation: InvocationRecordV3,
) -> None:
    source = invocation.source_state
    if (
        attempt.state is not AttemptState.RUNNING
        or attempt.runtime_identity != invocation.identity_digest()
        or attempt.candidate_digest is not None
        or invocation.state is not InvocationState.COMPLETED
        or invocation.result_digest is None
        or invocation.attempt_id != attempt.attempt_id
        or invocation.exercise_id != attempt.exercise_id
        or invocation.exercise_version != attempt.exercise_version
        or invocation.policy_id != attempt.policy_id
        or invocation.policy_version != attempt.policy_version
        or invocation.policy_digest != attempt.policy_digest
        or invocation.role_id != attempt.role_id
        or invocation.role_version != attempt.role_version
        or invocation.role_digest != attempt.role_digest
        or invocation.context_digest != attempt.context_digest
        or invocation.task_digest != attempt.task_digest
        or invocation.test_catalog_version != attempt.evaluator_catalog_version
        or invocation.test_catalog_digest != attempt.evaluator_catalog_digest
        or source is None
        or source.base_commit != attempt.starting_commit
        or invocation.sandbox_mode != attempt.sandbox_mode
    ):
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "completed V3 invocation differs from running attempt",
        )


def _validate_recovery_attempt_binding(
    attempt: AttemptRecord,
    invocation: InvocationRecordV3,
) -> None:
    source = invocation.source_state
    if (
        invocation.attempt_id != attempt.attempt_id
        or invocation.exercise_id != attempt.exercise_id
        or invocation.exercise_version != attempt.exercise_version
        or invocation.policy_id != attempt.policy_id
        or invocation.policy_version != attempt.policy_version
        or invocation.policy_digest != attempt.policy_digest
        or invocation.role_id != attempt.role_id
        or invocation.role_version != attempt.role_version
        or invocation.role_digest != attempt.role_digest
        or invocation.context_digest != attempt.context_digest
        or invocation.task_digest != attempt.task_digest
        or invocation.test_catalog_version != attempt.evaluator_catalog_version
        or invocation.test_catalog_digest != attempt.evaluator_catalog_digest
        or source is None
        or source.base_commit != attempt.starting_commit
        or invocation.sandbox_mode != attempt.sandbox_mode
        or attempt.runtime_identity != invocation.identity_digest()
        or attempt.candidate_digest is not None
    ):
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "recovery V3 invocation differs from its running attempt",
        )


def _validate_receipt(
    invocation: InvocationRecordV3,
    receipt: WorkspaceReceipt,
    workspace_root: Path,
) -> None:
    source = invocation.source_state
    if (
        source is None
        or receipt.state is not WorkspaceReceiptState.PREPARED
        or receipt.attempt_id != invocation.attempt_id
        or receipt.template_commit != source.base_commit
        or receipt.digest() != source.workspace_receipt_digest
        or receipt.workspace_root_digest != source.workspace_root_digest
        or receipt.workspace_path_digest != source.workspace_path_digest
        or canonical_path_digest(workspace_root) != source.workspace_root_digest
    ):
        raise LabValidationError(
            "INTEGRATION_V3_SOURCE_STATE_INVALID",
            "verified workspace receipt differs from V3 invocation",
        )


def _validate_recovery_workspace(
    workspace_root: Path,
    workspace: WorkspaceLaunchEvidence,
    receipt: WorkspaceReceipt,
    attempt: AttemptRecord,
    invocation: InvocationRecordV3,
) -> None:
    source = invocation.source_state
    if (
        source is None
        or receipt.state is not WorkspaceReceiptState.PREPARED
        or receipt.attempt_id != attempt.attempt_id
        or receipt.exercise_id != attempt.exercise_id
        or receipt.exercise_version != attempt.exercise_version
        or receipt.template_commit != attempt.starting_commit
        or receipt.digest() != source.workspace_receipt_digest
        or receipt.workspace_root_digest != source.workspace_root_digest
        or receipt.workspace_path_digest != source.workspace_path_digest
        or receipt.workspace_relative_path != attempt.attempt_id
        or canonical_path_digest(workspace_root) != source.workspace_root_digest
        or workspace.workspace_path_digest != source.workspace_path_digest
        or workspace.observed_head != source.base_commit
        or workspace.status
    ):
        raise LabValidationError(
            "OPERATOR_RECOVERY_INVALID",
            "workspace receipt or unchanged V3 identity differs",
        )


def _workspace_write_task(
    invocation: InvocationRecordV3,
    exercise: ExerciseRecord,
    policy: PolicyRecord,
    role: RoleRecord,
    context: ContextManifest,
    catalog: TestCatalog,
) -> Mapping[str, object]:
    readable_paths = tuple(item.path for item in invocation.readable_paths)
    if set(readable_paths).intersection(invocation.writable_paths):
        raise LabValidationError(
            "INTEGRATION_V3_SCOPE_INVALID",
            "workspace-write readable and writable paths must not overlap",
        )
    definitions = {definition.test_id: definition for definition in catalog.tests}
    try:
        selected = tuple(definitions[test_id] for test_id in invocation.test_ids)
    except KeyError as exc:
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "workspace-write test plan references an unavailable test",
        ) from exc
    if any(definition.runner is not TestRunner.COMMAND for definition in selected):
        raise LabValidationError(
            "INTEGRATION_EVALUATOR_INVALID",
            "workspace-write dispatch supports protected command tests only",
        )
    invariants = tuple(sorted({
        *(item.statement for item in policy.invariants),
        role.purpose,
        *exercise.prohibited_shortcuts,
    }))
    return {
        "schema_version": WORKSPACE_WRITE_TASK_SCHEMA,
        "task_digest": invocation.task_digest,
        "objective": exercise.objective,
        "acceptance_criteria": list(exercise.acceptance_criteria),
        "consumer_profile": {
            "version": "consumer-profile:v1",
            "consumer": f"worker-lab-{role.role_id}",
            "authority_paths": list(readable_paths),
            "protected_prefixes": [],
            "protected_exact": sorted(exercise.protected_paths),
            "product_invariants": list(invariants),
            "full_validation": [
                {
                    "name": definition.test_id,
                    "argv": list(definition.command),
                    "timeout_seconds": 30,
                }
                for definition in selected
            ],
        },
        "test_ids": list(invocation.test_ids),
        "writable_paths": list(invocation.writable_paths),
    }


def _run_sealed_tests(
    invocation: InvocationRecordV3,
    catalog: TestCatalog,
    workspace_path: Path,
    executor: SealedTestExecutor,
) -> tuple[ValidationStage, ...]:
    definitions = {definition.test_id: definition for definition in catalog.tests}
    try:
        selected = tuple(definitions[test_id] for test_id in invocation.test_ids)
    except KeyError as exc:
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "workspace-write validation test is unavailable",
        ) from exc
    if any(definition.runner is not TestRunner.COMMAND for definition in selected):
        raise LabValidationError(
            "INTEGRATION_EVALUATOR_INVALID",
            "workspace-write dispatch supports protected command tests only",
        )
    before = workspace_content_digest(workspace_path)
    stages: list[ValidationStage] = []
    for definition in selected:
        try:
            exit_code = executor(definition, workspace_path)
        except (LabValidationError, OSError, TimeoutError) as exc:
            raise LabValidationError(
                "INTEGRATION_VALIDATION_FAILED",
                "sealed workspace-write evaluator did not complete",
            ) from exc
        if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code != 0:
            raise LabValidationError(
                "INTEGRATION_VALIDATION_FAILED",
                "sealed workspace-write evaluator reported failure",
            )
        stages.append(ValidationStage(definition.test_id, "pass", None))
    if workspace_content_digest(workspace_path) != before:
        raise LabValidationError(
            "INTEGRATION_BOUNDARY_FAILED",
            "sealed workspace-write validation changed the candidate",
        )
    return tuple(stages)


def _require_no_dispatch_artifacts(state_root: Path, invocation_id: str) -> None:
    for path in (
        f"results/{invocation_id}.json",
        f"process-custody/{invocation_id}.json",
    ):
        if os.path.lexists(state_root / path):
            raise LabValidationError(
                "INTEGRATION_V3_AUTHORIZATION_INVALID",
                "invocation already has durable dispatch evidence",
            )


def _current_source_digests() -> tuple[str, str]:
    root = Path(__file__).resolve().parents[3]
    manifest_path = root / "config" / "portable-installation-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LabValidationError(
            "INTEGRATION_V3_SOURCE_IDENTITY_INVALID",
            "portable source manifest is unavailable or invalid",
        ) from exc
    try:
        authority = manifest["activation_policy"]["execution_authority"]
        components = manifest["components"]
        worker = components["worker-lab"]
        framework = components["autonomous-worker-framework"]
    except (KeyError, TypeError) as exc:
        raise LabValidationError(
            "INTEGRATION_V3_SOURCE_IDENTITY_INVALID",
            "portable source manifest fields are invalid",
        ) from exc
    if manifest.get("schema_version") != _PORTABLE_SCHEMA or authority != "DISABLED":
        raise LabValidationError(
            "INTEGRATION_V3_SOURCE_IDENTITY_INVALID",
            "current source identity must remain on the DISABLED portable baseline",
        )
    worker_digest = _component_digest(root, worker)
    framework_digest = _component_digest(root, framework)
    if worker_digest != worker.get("digest") or framework_digest != framework.get("digest"):
        raise LabValidationError(
            "INTEGRATION_V3_SOURCE_IDENTITY_INVALID",
            "current source bytes differ from the portable source identity",
        )
    return worker_digest, framework_digest


def _component_digest(root: Path, component: Mapping[str, object]) -> str:
    component_root = root / str(component.get("root"))
    production_root = str(component.get("production_root"))
    scope = component.get("scope")
    if scope == "runtime-dependency-closure":
        raw_files = component.get("files")
        if not isinstance(raw_files, list) or not raw_files:
            raise LabValidationError(
                "INTEGRATION_V3_SOURCE_IDENTITY_INVALID",
                "framework portable source closure is invalid",
            )
        files = tuple(str(item) for item in raw_files)
    elif scope == "python-production-tree":
        production = component_root / production_root
        files = tuple(
            sorted(
                path.relative_to(component_root).as_posix()
                for path in production.rglob("*.py")
                if "__pycache__" not in path.parts
            )
        )
    else:
        raise LabValidationError(
            "INTEGRATION_V3_SOURCE_IDENTITY_INVALID",
            "portable source scope is unsupported",
        )
    entries = []
    for relative in files:
        path = component_root / relative
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise LabValidationError(
                "INTEGRATION_V3_SOURCE_IDENTITY_INVALID",
                "portable source file is unavailable",
            ) from exc
        entries.append({"path": relative, "sha256": _bytes_digest(content)})
    return canonical_digest(entries)


def _store_prompt(state_root: Path, prompt: bytes) -> None:
    digest = _bytes_digest(prompt)
    AtomicRecordStore(state_root).write_bytes(
        f"prompts/{digest[7:]}.txt",
        prompt,
    )


def _load_prompt(state_root: Path, invocation: InvocationRecordV3) -> str:
    prompt = AtomicRecordStore(state_root).read_bytes(
        f"prompts/{invocation.prompt_digest[7:]}.txt",
    )
    if _bytes_digest(prompt) != invocation.prompt_digest:
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "retained prompt differs from V3 invocation",
        )
    try:
        decoded = prompt.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LabValidationError(
            "INTEGRATION_V3_IDENTITY_INVALID",
            "retained V3 prompt is not UTF-8",
        ) from exc
    if parse_controller_task_packet(decoded).digest() != invocation.controller_task_packet_digest:
        raise LabValidationError(
            "CONTROLLER_PACKET_IDENTITY_INVALID",
            "retained Controller Task Packet differs from V3 invocation",
        )
    return decoded


def _prompt_bytes(value: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise LabValidationError(
            "SERVICE_COMMAND_INVALID",
            "prompt must be non-empty text",
        )
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise LabValidationError(
            "SERVICE_COMMAND_INVALID",
            "prompt must be UTF-8 text",
        ) from exc
    if b"\x00" in encoded or len(encoded) > 32_768:
        raise LabValidationError(
            "SERVICE_COMMAND_INVALID",
            "prompt is invalid or oversized",
        )
    return encoded


def _digest(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 71
        or not value.startswith(_DIGEST_PREFIX)
        or any(character not in "0123456789abcdef" for character in value[7:])
    ):
        raise LabValidationError(
            "SERVICE_COMMAND_INVALID",
            f"{name} is invalid",
        )
    return value


def _bytes_digest(value: bytes) -> str:
    return _DIGEST_PREFIX + hashlib.sha256(value).hexdigest()


def _new_invocation_id() -> str:
    import uuid
    return "INVOCATION-" + uuid.uuid4().hex.upper()
