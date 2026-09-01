from __future__ import annotations

import hashlib
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from .attempt_store import AttemptStore
from .backup import (
    BackupManifest,
    create_backup as create_durable_backup,
    restore_backup as restore_durable_backup,
    verify_backup as verify_durable_backup,
)
from .canonical import canonical_digest, canonical_json
from .evidence import content_digest, verify_evidence
from .errors import LabValidationError
from .integration import (
    FRAMEWORK_CONTRACT_VERSION,
    INVOCATION_SCHEMA,
    RUNTIME_MODEL,
    RUNTIME_PROFILE,
    RUNTIME_REASONING_EFFORT,
    RUNTIME_TIMEOUT_SECONDS,
    WORKER_LAB_CONTRACT_VERSION,
    InvocationOperation,
    InvocationRecord,
    InvocationState,
    ResultRecord,
    transition_invocation,
)
from .framework_adapter import accept_execute_response, parse_result
from .framework_client import (
    call_adapter,
    inspect_configuration,
    inspect_worker_lab_identity,
    pinned_framework_configuration,
    runtime_identity,
)
from .invocation_store import InvocationStore
from .lifecycle import transition_attempt
from .models import (
    ATTEMPT_SCHEMA,
    AttemptRecord,
    AttemptState,
    CurriculumRecord,
    EvidenceRecord,
    ExerciseRecord,
    FailureRecord,
    WorkspaceReceipt,
    WorkspaceReceiptState,
)
from .operator_control import (
    DoctorReport,
    inspect_installation,
    validate_controller_identity,
)
from .installation_manifest import require_execution_enabled
from .policy import (
    ContextManifest,
    PolicyRecord,
    RoleRecord,
    validate_authority,
    verify_context_files,
)
from .storage import AtomicRecordStore
from .test_catalog import ChangeFacts, TestCatalog, TestDefinition, TestRunner
from .validation import attempt_task_digest
from .workspace import (
    canonical_path_digest,
    discard_workspace,
    prepare_workspace,
    verify_workspace,
)
from .process_custody import CustodyState, ProcessCustodyRecord, ProcessCustodyStore
from .read_only_evidence import (
    READ_ONLY_EVALUATION_PLAN_SCHEMA,
    ReadOnlyEvidenceCollector,
    ReadOnlyEvaluationPlan,
    ReadOnlyEvaluationPlanStore,
)
from .windows_job import (
    WindowsJobAdapterRunner,
    WorkspaceLaunchEvidence,
    inspect_launch_workspace,
    recover_absence_after_controller_exit,
)


HEALTH_SCHEMA = "worker-lab-service-health:v1"
INSTALLATION_STATUS_SCHEMA = "worker-lab-service-installation-status:v1"
RECORD_LIST_SCHEMA = "worker-lab-service-record-list:v1"
RECORD_DETAIL_SCHEMA = "worker-lab-service-record-detail:v1"
OPERATION_RESULT_SCHEMA = "worker-lab-service-operation-result:v2"
BACKUP_RESULT_SCHEMA = "worker-lab-service-backup-result:v1"
RECOVERY_RESULT_SCHEMA = "worker-lab-service-recovery-result:v1"
ATTEMPT_TIMELINE_SCHEMA = "worker-lab-service-attempt-timeline:v1"
CANDIDATE_REVIEW_SCHEMA = "worker-lab-service-candidate-review:v1"
RECOVERY_CLEANUP_OUTCOME = (
    "adapter absence and unchanged workspace verified; workspace retained"
)

COLLECTIONS = (
    "attempts",
    "catalogs",
    "contexts",
    "curricula",
    "evidence",
    "exercises",
    "failures",
    "invocations",
    "policies",
    "results",
    "roles",
)

_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._@-]{1,127}$")
_DEFINITION_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_MAX_PROMPT_BYTES = 32_768


class _Record(Protocol):
    schema_version: str

    def to_dict(self) -> dict[str, Any]: ...

    def digest(self) -> str: ...


Loader = Callable[[Any], _Record]
Identity = Callable[[_Record], str]
State = Callable[[_Record], str | None]
ReadOnlyAdapter = Callable[
    [InvocationRecord, str, Path, ProcessCustodyStore],
    tuple[bytes, str],
]
SealedTestExecutor = Callable[[TestDefinition, Path], int]


@dataclass(frozen=True)
class _CollectionSpec:
    storage_root: str
    directory: str
    loader: Loader
    identity: Identity
    state: State


@dataclass(frozen=True)
class RecordSummaryDTO:
    collection: str
    identity: str
    schema_version: str
    record_digest: str
    state: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "collection": self.collection,
            "identity": self.identity,
            "schema_version": self.schema_version,
            "record_digest": self.record_digest,
            "state": self.state,
        }


@dataclass(frozen=True)
class RecordListDTO:
    collection: str
    items: tuple[RecordSummaryDTO, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RECORD_LIST_SCHEMA,
            "collection": self.collection,
            "count": len(self.items),
            "items": [item.to_dict() for item in self.items],
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class RecordDetailDTO:
    summary: RecordSummaryDTO
    record: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RECORD_DETAIL_SCHEMA,
            "summary": self.summary.to_dict(),
            "record": dict(self.record),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class InstallationStatusDTO:
    doctor: DoctorReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": INSTALLATION_STATUS_SCHEMA,
            "installation": self.doctor.to_dict(),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class HealthDTO:
    doctor: DoctorReport
    data_root_state: str
    collection_counts: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": HEALTH_SCHEMA,
            "status": "healthy",
            "data_root_state": self.data_root_state,
            "execution_ready": self.doctor.execution_ready,
            "collection_counts": dict(sorted(self.collection_counts.items())),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class OperationResultDTO:
    operation: str
    resource_type: str
    identity: str
    record_digest: str
    immutable_identity_digest: str | None
    record: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": OPERATION_RESULT_SCHEMA,
            "operation": self.operation,
            "resource_type": self.resource_type,
            "identity": self.identity,
            "record_digest": self.record_digest,
            "immutable_identity_digest": self.immutable_identity_digest,
            "record": dict(self.record),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    def record_json(self) -> str:
        """Preserve the established CLI record shape while clients adopt the DTO."""
        return canonical_json(dict(self.record))


@dataclass(frozen=True)
class BackupResultDTO:
    operation: str
    manifest: BackupManifest

    def to_dict(self) -> dict[str, Any]:
        record = self.manifest.to_dict()
        return {
            "schema_version": BACKUP_RESULT_SCHEMA,
            "operation": self.operation,
            "manifest_digest": canonical_digest(record),
            "file_count": len(self.manifest.files),
            "manifest": record,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class RecoveryResultDTO:
    controller_identity: str
    invocation: InvocationRecord
    attempt: AttemptRecord
    custody: ProcessCustodyRecord
    workspace: WorkspaceLaunchEvidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RECOVERY_RESULT_SCHEMA,
            "operation": "recover-invocation",
            "identity": self.invocation.invocation_id,
            "immutable_identity_digest": self.invocation.identity_digest(),
            "controller_identity": self.controller_identity,
            "workspace_outcome": "unchanged-retained",
            "workspace": {
                "workspace_path_digest": self.workspace.workspace_path_digest,
                "content_digest": self.workspace.content_digest,
                "observed_head": self.workspace.observed_head,
                "status": self.workspace.status,
            },
            "custody": {
                "record_digest": self.custody.digest(),
                "record": self.custody.to_dict(),
            },
            "invocation": {
                "record_digest": self.invocation.digest(),
                "record": self.invocation.to_dict(),
            },
            "attempt": {
                "record_digest": self.attempt.digest(),
                "record": self.attempt.to_dict(),
            },
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class AttemptTimelineDTO:
    attempt: RecordDetailDTO
    workspace: RecordDetailDTO | None
    invocations: tuple[RecordDetailDTO, ...]
    results: tuple[RecordDetailDTO, ...]
    custody: tuple[RecordDetailDTO, ...]
    evidence: tuple[RecordDetailDTO, ...]
    failures: tuple[RecordDetailDTO, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ATTEMPT_TIMELINE_SCHEMA,
            "attempt": self.attempt.to_dict(),
            "workspace": None if self.workspace is None else self.workspace.to_dict(),
            "invocations": [item.to_dict() for item in self.invocations],
            "results": [item.to_dict() for item in self.results],
            "custody": [item.to_dict() for item in self.custody],
            "evidence": [item.to_dict() for item in self.evidence],
            "failures": [item.to_dict() for item in self.failures],
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class CandidateReviewDTO:
    candidate_digest: str
    attempt: RecordDetailDTO
    invocation: RecordDetailDTO
    result: RecordDetailDTO
    custody: RecordDetailDTO
    proposal_content_digest: str
    changed_paths: tuple[str, ...]
    validation_stages: tuple[Mapping[str, Any], ...]
    evidence: tuple[RecordDetailDTO, ...]
    failures: tuple[RecordDetailDTO, ...]
    first_failure_boundary: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CANDIDATE_REVIEW_SCHEMA,
            "candidate_digest": self.candidate_digest,
            "attempt": self.attempt.to_dict(),
            "invocation": self.invocation.to_dict(),
            "result": self.result.to_dict(),
            "custody": self.custody.to_dict(),
            "proposal_content_digest": self.proposal_content_digest,
            "changed_paths": list(self.changed_paths),
            "validation_stages": [dict(item) for item in self.validation_stages],
            "evidence": [item.to_dict() for item in self.evidence],
            "failures": [item.to_dict() for item in self.failures],
            "first_failure_boundary": self.first_failure_boundary,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


class WorkerLabApplicationService:
    """Application boundary shared by operator clients and the future GUI."""

    def __init__(
        self,
        data_root: Path,
        *,
        clock: Callable[[], str] | None = None,
        process_probe: Callable[[int], int | None] | None = None,
        read_only_adapter: ReadOnlyAdapter | None = None,
        sealed_test_executor: SealedTestExecutor | None = None,
    ) -> None:
        if not isinstance(data_root, Path) or not data_root.is_absolute():
            raise LabValidationError("SERVICE_DATA_ROOT_INVALID", "service data root must be absolute")
        if read_only_adapter is not None and not callable(read_only_adapter):
            raise LabValidationError("SERVICE_COMMAND_INVALID", "read-only adapter must be callable")
        if sealed_test_executor is not None and not callable(sealed_test_executor):
            raise LabValidationError("SERVICE_COMMAND_INVALID", "sealed test executor must be callable")
        self.data_root = data_root
        self._clock = clock or _utc_now
        self._process_probe = process_probe
        self._read_only_adapter = read_only_adapter or _execute_read_only_adapter
        self._sealed_test_executor = sealed_test_executor or _run_sealed_test

    def installation_status(self) -> InstallationStatusDTO:
        _, report = inspect_installation()
        return InstallationStatusDTO(report)

    def health(self) -> HealthDTO:
        _, report = inspect_installation()
        state = self._data_root_state()
        counts = {collection: len(self.list_records(collection).items) for collection in COLLECTIONS}
        return HealthDTO(report, state, counts)

    def list_records(self, collection: str) -> RecordListDTO:
        self._data_root_state()
        spec = _collection(collection)
        store = self._store(spec)
        loaded: list[tuple[str, _Record]] = []
        for path in store.list_paths(spec.directory):
            loaded.append((path, store.read(path, spec.loader)))
        identities: set[str] = set()
        summaries: list[RecordSummaryDTO] = []
        for _, record in loaded:
            summary = _summary(collection, record, spec)
            if summary.identity in identities:
                raise LabValidationError("SERVICE_RECORD_DUPLICATE", "collection contains a duplicate identity")
            identities.add(summary.identity)
            summaries.append(summary)
        return RecordListDTO(collection, tuple(sorted(summaries, key=lambda item: item.identity)))

    def show_record(self, collection: str, identity: str) -> RecordDetailDTO:
        self._data_root_state()
        expected = _identity(identity)
        spec = _collection(collection)
        store = self._store(spec)
        matches: list[_Record] = []
        for path in store.list_paths(spec.directory):
            record = store.read(path, spec.loader)
            if spec.identity(record) == expected:
                matches.append(record)
        if not matches:
            raise LabValidationError("SERVICE_RECORD_MISSING", "requested service record is unavailable")
        if len(matches) != 1:
            raise LabValidationError("SERVICE_RECORD_DUPLICATE", "requested service identity is ambiguous")
        record = matches[0]
        return RecordDetailDTO(_summary(collection, record, spec), record.to_dict())

    def show_attempt_timeline(self, attempt_id: str) -> AttemptTimelineDTO:
        attempt_id = _identity(attempt_id)
        self._require_present_data_root()
        attempt = self.show_record("attempts", attempt_id)
        records = self._attempt_records(attempt_id)
        return AttemptTimelineDTO(
            attempt,
            records["workspace"],
            records["invocations"],
            records["results"],
            records["custody"],
            records["evidence"],
            records["failures"],
        )

    def review_candidate(self, attempt_id: str) -> CandidateReviewDTO:
        attempt_id = _identity(attempt_id)
        self._require_present_data_root()
        timeline = self.show_attempt_timeline(attempt_id)
        attempt = AttemptRecord.from_mapping(timeline.attempt.record)
        if attempt.candidate_digest is None:
            raise LabValidationError(
                "SERVICE_CANDIDATE_MISSING", "attempt has no retained candidate identity"
            )
        if len(timeline.invocations) != 1 or len(timeline.results) != 1 or len(timeline.custody) != 1:
            raise LabValidationError(
                "SERVICE_CANDIDATE_IDENTITY_INVALID",
                "candidate requires exactly one invocation, result, and custody record",
            )
        invocation = InvocationRecord.from_mapping(timeline.invocations[0].record)
        result = ResultRecord.from_mapping(timeline.results[0].record)
        custody = ProcessCustodyRecord.from_mapping(timeline.custody[0].record)
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
                "candidate records do not share an exact durable identity",
            )
        try:
            parse_result(canonical_json(result.to_dict()), invocation)
        except LabValidationError as exc:
            raise LabValidationError(
                "SERVICE_CANDIDATE_IDENTITY_INVALID",
                "candidate result differs from its invocation",
            ) from exc
        if result.content_reference is None:
            raise LabValidationError(
                "SERVICE_CANDIDATE_CONTENT_MISSING", "candidate content is not retained"
            )
        content = AtomicRecordStore(self.data_root / "state").read_bytes(result.content_reference)
        retained_digest = content_digest(content)
        if retained_digest != result.output_digest or retained_digest != result.proposal_digest:
            raise LabValidationError(
                "SERVICE_CANDIDATE_CONTENT_INVALID",
                "candidate content differs from retained result digests",
            )
        evidence = tuple(
            item for item in timeline.evidence
            if verify_evidence(self.data_root, item.summary.identity).attempt_id == attempt_id
        )
        return CandidateReviewDTO(
            attempt.candidate_digest,
            timeline.attempt,
            timeline.invocations[0],
            timeline.results[0],
            timeline.custody[0],
            retained_digest,
            result.changed_paths,
            tuple(stage.to_dict() for stage in result.validation_stages),
            evidence,
            timeline.failures,
            result.first_failure_boundary,
        )

    def create_attempt(
        self,
        exercise_id: str,
        exercise_version: int,
        target_repository: Path,
    ) -> OperationResultDTO:
        exercise_id = _definition_id(exercise_id)
        exercise_version = _positive_version(exercise_version)
        target_repository = _path_argument(target_repository, "target repository")
        self._require_present_data_root()
        definitions = AtomicRecordStore(self.data_root / "curricula")
        exercise = definitions.read(
            f"exercises/{exercise_id}/v{exercise_version}.json",
            ExerciseRecord.from_mapping,
        )
        policy = definitions.read(
            f"policies/{exercise.policy_id}/v{exercise.policy_version}.json",
            PolicyRecord.from_mapping,
        )
        role = definitions.read(
            f"roles/{exercise.role_id}/v{exercise.role_version}.json",
            RoleRecord.from_mapping,
        )
        context = definitions.read(
            f"contexts/{exercise.context_manifest_id}/v{exercise.context_manifest_version}.json",
            ContextManifest.from_mapping,
        )
        catalog = definitions.read(
            f"catalogs/{exercise.evaluator_catalog_version}.json",
            TestCatalog.from_mapping,
        )
        _validate_attempt_authority(exercise, policy, role, context, catalog)
        _validate_target_repository(self.data_root, target_repository, exercise.template_commit)
        verify_context_files(context, target_repository)
        occurred_at = self._clock()
        attempt = AttemptRecord.from_mapping({
            "schema_version": ATTEMPT_SCHEMA,
            "attempt_id": "ATTEMPT-" + uuid.uuid4().hex.upper(),
            "curriculum_id": exercise.curriculum_id,
            "exercise_id": exercise.exercise_id,
            "exercise_version": exercise.exercise_version,
            "starting_commit": exercise.template_commit,
            "context_digest": context.digest(),
            "task_digest": attempt_task_digest(exercise, policy, role, context, catalog),
            "policy_id": policy.policy_id,
            "policy_version": policy.policy_version,
            "policy_digest": policy.digest(),
            "role_id": role.role_id,
            "role_version": role.role_version,
            "role_digest": role.digest(),
            "sandbox_mode": exercise.sandbox_mode,
            "state": "DRAFT",
            "created_at": occurred_at,
            "updated_at": occurred_at,
            "evaluator_catalog_version": catalog.catalog_version,
            "evaluator_catalog_digest": catalog.digest(),
            "runtime_identity": None,
            "candidate_digest": None,
            "cleanup_outcome": None,
            "prior_attempt_id": None,
        })
        AttemptStore(self.data_root / "state").create(attempt)
        return _operation_result("create-attempt", "attempt", attempt.attempt_id, attempt)

    def prepare_workspace(
        self,
        attempt_id: str,
        template_repository: Path,
        workspace_root: Path,
    ) -> OperationResultDTO:
        attempt_id = _identity(attempt_id)
        template_repository = _path_argument(template_repository, "template repository")
        workspace_root = _path_argument(workspace_root, "workspace root")
        self._require_present_data_root()
        receipt = prepare_workspace(
            self.data_root,
            attempt_id,
            template_repository,
            workspace_root,
            occurred_at=self._clock(),
        )
        return _operation_result("prepare-workspace", "workspace-receipt", attempt_id, receipt)

    def verify_workspace(self, attempt_id: str, workspace_root: Path) -> OperationResultDTO:
        attempt_id = _identity(attempt_id)
        workspace_root = _path_argument(workspace_root, "workspace root")
        self._require_present_data_root()
        receipt = verify_workspace(self.data_root, attempt_id, workspace_root)
        return _operation_result("verify-workspace", "workspace-receipt", attempt_id, receipt)

    def discard_workspace(
        self,
        attempt_id: str,
        workspace_root: Path,
        cleanup_outcome: str,
    ) -> OperationResultDTO:
        attempt_id = _identity(attempt_id)
        workspace_root = _path_argument(workspace_root, "workspace root")
        self._require_present_data_root()
        attempt = discard_workspace(
            self.data_root,
            attempt_id,
            workspace_root,
            cleanup_outcome,
            occurred_at=self._clock(),
        )
        return _operation_result("discard-workspace", "attempt", attempt_id, attempt)

    def transition_attempt(
        self,
        attempt_id: str,
        target_state: str,
        *,
        candidate_digest: str | None = None,
        cleanup_outcome: str | None = None,
    ) -> OperationResultDTO:
        attempt_id = _identity(attempt_id)
        self._require_present_data_root()
        attempts = AttemptStore(self.data_root / "state")
        current = attempts.read(attempt_id)
        try:
            target = AttemptState(target_state)
        except (TypeError, ValueError) as exc:
            raise LabValidationError(
                "SERVICE_ATTEMPT_STATE_INVALID", "attempt target state is unsupported"
            ) from exc
        receipt_path = self.data_root / "state" / "workspaces" / f"{current.attempt_id}.json"
        if (
            current.state is AttemptState.READY
            and target is AttemptState.ABORTED
            and os.path.lexists(receipt_path)
        ):
            raise LabValidationError(
                "ATTEMPT_WORKSPACE_DISPOSAL_REQUIRED",
                "receipt-bound READY attempts must use discard-workspace",
            )
        updated = transition_attempt(
            current,
            target,
            occurred_at=self._clock(),
            candidate_digest=candidate_digest,
            cleanup_outcome=cleanup_outcome,
        )
        attempts.save_transition(updated)
        return _operation_result("transition-attempt", "attempt", attempt_id, updated)

    def prepare_invocation(
        self,
        attempt_id: str,
        workspace_root: Path,
        prompt: str,
    ) -> OperationResultDTO:
        attempt_id = _identity(attempt_id)
        workspace_root = _path_argument(workspace_root, "workspace root")
        prompt_bytes = _prompt_bytes(prompt)
        self._require_present_data_root()
        attempt = AttemptStore(self.data_root / "state").read(attempt_id)
        if attempt.state is not AttemptState.READY:
            raise LabValidationError(
                "INTEGRATION_ATTEMPT_STATE_INVALID",
                "invocation preparation requires a READY attempt",
            )
        invocation_store = InvocationStore(self.data_root / "state")
        for path in invocation_store.records.list_paths("invocations"):
            existing = invocation_store.records.read(path, InvocationRecord.from_mapping)
            if existing.attempt_id == attempt_id:
                raise LabValidationError(
                    "INTEGRATION_INVOCATION_EXISTS",
                    "attempt already has a durable invocation",
                )
        definitions = AtomicRecordStore(self.data_root / "curricula")
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
        _validate_prepared_attempt(attempt, exercise, policy, role, context, catalog)
        receipt = verify_workspace(self.data_root, attempt_id, workspace_root)
        plan = catalog.select(ChangeFacts(()), profile_ids=exercise.test_profile_ids)
        manifest, _ = inspect_installation()
        operation = (
            InvocationOperation.READ_ONLY_PROPOSAL
            if attempt.sandbox_mode == "read-only"
            else InvocationOperation.WORKSPACE_WRITE_CODE_TASK
        )
        invocation = InvocationRecord.from_mapping({
            "schema_version": INVOCATION_SCHEMA,
            "invocation_id": "INVOCATION-" + uuid.uuid4().hex.upper(),
            "attempt_id": attempt.attempt_id,
            "operation": str(operation),
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
            "test_catalog_version": catalog.catalog_version,
            "test_catalog_digest": catalog.digest(),
            "test_plan_digest": canonical_digest(plan.to_dict()),
            "test_ids": list(plan.test_ids),
            "worker_lab_installation_digest": manifest.components["worker-lab"].installation_digest,
            "worker_lab_contract_version": WORKER_LAB_CONTRACT_VERSION,
            "framework_installation_digest": manifest.components[
                "autonomous-worker-framework"
            ].installation_digest,
            "framework_contract_version": FRAMEWORK_CONTRACT_VERSION,
            "workspace_receipt_digest": receipt.digest(),
            "workspace_root_digest": receipt.workspace_root_digest,
            "workspace_path_digest": receipt.workspace_path_digest,
            "starting_commit": attempt.starting_commit,
            "sandbox_mode": attempt.sandbox_mode,
            "runtime_profile_id": RUNTIME_PROFILE,
            "model": RUNTIME_MODEL,
            "reasoning_effort": RUNTIME_REASONING_EFFORT,
            "timeout_seconds": RUNTIME_TIMEOUT_SECONDS,
            "readable_paths": [
                {"path": item.path, "digest": item.digest} for item in context.files
            ],
            "writable_paths": (
                []
                if operation is InvocationOperation.READ_ONLY_PROPOSAL
                else list(exercise.writable_paths)
            ),
            "prompt_digest": _bytes_digest(prompt_bytes),
            "authorized_by": None,
            "authorized_at": None,
            "state": "PREPARED",
            "result_digest": None,
        })
        _store_prompt(self.data_root / "state", prompt_bytes)
        if operation is InvocationOperation.READ_ONLY_PROPOSAL:
            sealed = ReadOnlyEvaluationPlan.from_mapping({
                "schema_version": READ_ONLY_EVALUATION_PLAN_SCHEMA,
                "invocation_id": invocation.invocation_id,
                "invocation_digest": invocation.identity_digest(),
                "catalog_version": catalog.catalog_version,
                "catalog_digest": catalog.digest(),
                "selected_profile_ids": list(plan.selected_profile_ids),
                "test_ids": list(plan.test_ids),
                "test_plan_digest": invocation.test_plan_digest,
                "changed_paths": [],
                "capabilities": [],
                "risk_flags": [],
            })
            ReadOnlyEvaluationPlanStore(self.data_root / "state").create(sealed)
        invocation_store.create(invocation)
        return _operation_result(
            "prepare-invocation",
            "invocation",
            invocation.invocation_id,
            invocation,
        )

    def authorize_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
        controller_identity: str,
    ) -> OperationResultDTO:
        invocation_id = _identity(invocation_id)
        expected = _digest(expected_identity_digest)
        controller = validate_controller_identity(controller_identity)
        self._require_present_data_root()
        store = InvocationStore(self.data_root / "state")
        current = store.read(invocation_id)
        if current.identity_digest() != expected:
            raise LabValidationError(
                "INTEGRATION_IDENTITY_INVALID",
                "invocation identity differs from authorization command",
            )
        authorized = transition_invocation(
            current,
            InvocationState.AUTHORIZED,
            authorized_by=controller,
            authorized_at=self._clock(),
        )
        store.save_transition(authorized, expected_digest=current.digest())
        return _operation_result(
            "authorize-invocation",
            "invocation",
            invocation_id,
            authorized,
        )

    def reject_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
    ) -> OperationResultDTO:
        invocation_id = _identity(invocation_id)
        expected = _digest(expected_identity_digest)
        self._require_present_data_root()
        store = InvocationStore(self.data_root / "state")
        current = store.read(invocation_id)
        if current.identity_digest() != expected:
            raise LabValidationError(
                "INTEGRATION_IDENTITY_INVALID",
                "invocation identity differs from rejection command",
            )
        rejected = transition_invocation(current, InvocationState.REJECTED)
        store.save_transition(rejected, expected_digest=current.digest())
        return _operation_result(
            "reject-invocation",
            "invocation",
            invocation_id,
            rejected,
        )

    def cancel_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
        controller_identity: str,
    ) -> OperationResultDTO:
        invocation_id = _identity(invocation_id)
        expected = _digest(expected_identity_digest)
        controller = validate_controller_identity(controller_identity)
        self._require_present_data_root()
        store = InvocationStore(self.data_root / "state")
        current = store.read(invocation_id)
        if current.identity_digest() != expected:
            raise LabValidationError(
                "INTEGRATION_IDENTITY_INVALID",
                "invocation identity differs from cancellation command",
            )
        if current.state is InvocationState.AUTHORIZED and current.authorized_by != controller:
            raise LabValidationError(
                "OPERATOR_CONTROLLER_MISMATCH",
                "cancellation controller differs from invocation authorization",
            )
        cancelled = transition_invocation(current, InvocationState.ABORTED)
        store.save_transition(cancelled, expected_digest=current.digest())
        return _operation_result(
            "cancel-invocation",
            "invocation",
            invocation_id,
            cancelled,
        )

    def dispatch_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
        controller_identity: str,
        workspace_root: Path,
    ) -> OperationResultDTO:
        """Dispatch one exact read-only invocation through the sealed primitives."""
        invocation_id = _identity(invocation_id)
        expected = _digest(expected_identity_digest)
        controller = validate_controller_identity(controller_identity)
        workspace_root = _absolute_path_argument(workspace_root, "workspace root")
        self._require_present_data_root()
        invocation_store = InvocationStore(self.data_root / "state")
        invocation = invocation_store.read(invocation_id)
        if invocation.identity_digest() != expected:
            raise LabValidationError(
                "INTEGRATION_IDENTITY_INVALID",
                "invocation identity differs from dispatch command",
            )
        if invocation.state is not InvocationState.AUTHORIZED:
            raise LabValidationError(
                "INTEGRATION_AUTHORIZATION_INVALID",
                "dispatch requires an authorized invocation",
            )
        if invocation.authorized_by != controller:
            raise LabValidationError(
                "OPERATOR_CONTROLLER_MISMATCH",
                "dispatch controller differs from invocation authorization",
            )
        attempt = AttemptStore(self.data_root / "state").read(invocation.attempt_id)
        _validate_dispatch_attempt_binding(attempt, invocation)
        _validate_dispatch_definitions(self.data_root, attempt, invocation)
        manifest, _ = inspect_installation()
        require_execution_enabled(manifest)
        if (
            invocation.operation is not InvocationOperation.READ_ONLY_PROPOSAL
            or invocation.sandbox_mode != "read-only"
        ):
            raise LabValidationError(
                "INTEGRATION_OPERATION_INVALID",
                "service dispatch supports read-only proposals only",
            )
        receipt = verify_workspace(self.data_root, attempt.attempt_id, workspace_root)
        if (
            receipt.digest() != invocation.workspace_receipt_digest
            or receipt.workspace_root_digest != invocation.workspace_root_digest
            or receipt.workspace_path_digest != invocation.workspace_path_digest
        ):
            raise LabValidationError(
                "INTEGRATION_IDENTITY_INVALID",
                "verified workspace differs from invocation",
            )

        state_root = self.data_root / "state"
        _require_no_dispatch_artifacts(state_root, invocation_id)
        prompt = _load_prompt(state_root, invocation)
        workspace_path = workspace_root / attempt.attempt_id
        invocation_store = InvocationStore(state_root)
        attempt_store = AttemptStore(state_root)
        running = attempt_store.bind_authorized_invocation(
            invocation_store,
            invocation_id=invocation_id,
            expected_invocation_identity=expected,
            occurred_at=self._clock(),
        )
        dispatching = transition_invocation(invocation, InvocationState.DISPATCHING)
        invocation_store.save_transition(
            dispatching,
            expected_digest=invocation.digest(),
        )
        custody_store = ProcessCustodyStore(state_root)
        started_at = self._clock()
        response, observed_runtime_identity = self._read_only_adapter(
            dispatching,
            prompt,
            workspace_path,
            custody_store,
        )
        ended_at = self._clock()
        custody = custody_store.read(invocation_id)
        result = accept_execute_response(
            response,
            dispatching,
            custody,
            runtime_identity=_digest(observed_runtime_identity),
            started_at=started_at,
            ended_at=ended_at,
            state_root=state_root,
            custody_store=custody_store,
            evidence_collector=ReadOnlyEvidenceCollector(
                state_root=state_root,
                workspace_path=workspace_path,
                test_executor=self._sealed_test_executor,
            ),
        )
        AtomicRecordStore(state_root).write(f"results/{invocation_id}.json", result)
        completed = transition_invocation(
            dispatching,
            InvocationState.COMPLETED,
            result_digest=result.digest(),
        )
        invocation_store.save_transition(
            completed,
            expected_digest=dispatching.digest(),
        )
        running = attempt_store.read(attempt.attempt_id)
        _validate_running_dispatch_binding(running, completed)
        candidate = transition_attempt(
            running,
            AttemptState.CANDIDATE,
            occurred_at=self._clock(),
            candidate_digest=result.digest(),
        )
        attempt_store.save_transition(candidate)
        return _operation_result(
            "dispatch-invocation",
            "attempt",
            candidate.attempt_id,
            candidate,
        )

    def recover_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
        controller_identity: str,
        workspace_root: Path,
    ) -> RecoveryResultDTO:
        invocation_id = _identity(invocation_id)
        expected = _digest(expected_identity_digest)
        controller = validate_controller_identity(controller_identity)
        workspace_root = _absolute_path_argument(workspace_root, "workspace root")
        self._require_present_data_root()

        state_root = self.data_root / "state"
        invocation_store = InvocationStore(state_root)
        invocation = invocation_store.read(invocation_id)
        if invocation.identity_digest() != expected:
            raise LabValidationError(
                "INTEGRATION_IDENTITY_INVALID",
                "invocation identity differs from recovery command",
            )
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
                "invocation state is not recoverable",
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
            or custody.adapter_pid is None
            or custody.adapter_creation_time_100ns is None
            or not custody.request_sent
        ):
            raise LabValidationError(
                "OPERATOR_RECOVERY_INVALID",
                "process custody is not bound to a dispatched invocation",
            )
        occurred_at = self._clock()
        verified_custody = custody
        if custody.state is CustodyState.TERMINATED:
            recovery_arguments: dict[str, Any] = {"now": lambda: occurred_at}
            if self._process_probe is not None:
                recovery_arguments["probe"] = self._process_probe
            recovered = recover_absence_after_controller_exit(
                custody,
                **recovery_arguments,
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
            verified_custody.active_process_count != 0
            or verified_custody.absence_verified_at is None
            or verified_custody.workspace_content_digest != workspace.content_digest
        ):
            raise LabValidationError(
                "OPERATOR_RECOVERY_INVALID",
                "workspace or process-absence evidence differs",
            )

        if attempt.state is AttemptState.RUNNING:
            aborted_attempt = transition_attempt(
                attempt,
                AttemptState.ABORTED,
                occurred_at=occurred_at,
                cleanup_outcome=RECOVERY_CLEANUP_OUTCOME,
            )
        else:
            aborted_attempt = attempt

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
            aborted_invocation = transition_invocation(
                current_invocation,
                InvocationState.ABORTED,
            )
            invocation_store.save_transition(
                aborted_invocation,
                expected_digest=current_invocation.digest(),
            )
            current_invocation = aborted_invocation
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
                "durable recovery records differ",
            )
        return RecoveryResultDTO(
            controller,
            durable_invocation,
            durable_attempt,
            durable_custody,
            workspace,
        )

    def create_backup(self, destination: Path) -> BackupResultDTO:
        destination = _absolute_path_argument(destination, "backup destination")
        self._require_present_data_root()
        return BackupResultDTO(
            "create-backup",
            create_durable_backup(self.data_root, destination),
        )

    def verify_backup(self, backup: Path) -> BackupResultDTO:
        backup = _absolute_path_argument(backup, "backup path")
        return BackupResultDTO("verify-backup", verify_durable_backup(backup))

    def restore_backup(self, backup: Path, destination: Path) -> BackupResultDTO:
        backup = _absolute_path_argument(backup, "backup path")
        destination = _absolute_path_argument(destination, "restore destination")
        return BackupResultDTO(
            "restore-backup",
            restore_durable_backup(backup, destination),
        )

    def _store(self, spec: _CollectionSpec) -> AtomicRecordStore:
        return AtomicRecordStore(self.data_root / spec.storage_root)

    def _attempt_records(self, attempt_id: str) -> dict[str, Any]:
        state = AtomicRecordStore(self.data_root / "state")
        workspace_path = f"workspaces/{attempt_id}.json"
        try:
            workspace_record = state.read(workspace_path, WorkspaceReceipt.from_mapping)
        except LabValidationError as exc:
            if exc.code != "STORAGE_RECORD_MISSING":
                raise
            workspace = None
        else:
            if workspace_record.attempt_id != attempt_id:
                raise LabValidationError(
                    "SERVICE_TIMELINE_IDENTITY_INVALID", "workspace receipt differs from attempt"
                )
            workspace = RecordDetailDTO(
                _summary("workspace-receipts", workspace_record, _WORKSPACE_SPEC),
                workspace_record.to_dict(),
            )

        invocations = self._records_for_attempt("invocations", attempt_id)
        results = self._records_for_attempt("results", attempt_id)
        evidence = self._records_for_attempt("evidence", attempt_id)
        failures = self._records_for_attempt("failures", attempt_id)
        invocation_ids = {item.summary.identity for item in invocations}
        custody = tuple(
            item for item in self._all_details("process-custody", _CUSTODY_SPEC)
            if item.record["invocation_id"] in invocation_ids
        )
        for item in results:
            if item.summary.identity not in invocation_ids:
                raise LabValidationError(
                    "SERVICE_TIMELINE_IDENTITY_INVALID", "result differs from durable invocation"
                )
        return {
            "workspace": workspace,
            "invocations": invocations,
            "results": results,
            "custody": custody,
            "evidence": evidence,
            "failures": failures,
        }

    def _records_for_attempt(self, collection: str, attempt_id: str) -> tuple[RecordDetailDTO, ...]:
        spec = _collection(collection)
        return tuple(
            item for item in self._all_details(collection, spec)
            if item.record["attempt_id"] == attempt_id
        )

    def _all_details(self, collection: str, spec: _CollectionSpec) -> tuple[RecordDetailDTO, ...]:
        store = self._store(spec)
        details = tuple(
            RecordDetailDTO(_summary(collection, record, spec), record.to_dict())
            for path in store.list_paths(spec.directory)
            for record in (store.read(path, spec.loader),)
        )
        identities = [item.summary.identity for item in details]
        if len(identities) != len(set(identities)):
            raise LabValidationError("SERVICE_RECORD_DUPLICATE", "collection contains a duplicate identity")
        return tuple(sorted(details, key=lambda item: item.summary.identity))

    def _data_root_state(self) -> str:
        if not self.data_root.exists():
            return "absent"
        if (
            self.data_root.is_symlink()
            or getattr(os.lstat(self.data_root), "st_file_attributes", 0) & 0x400
            or not self.data_root.is_dir()
        ):
            raise LabValidationError("SERVICE_DATA_ROOT_INVALID", "service data root must be a real directory")
        try:
            resolved = self.data_root.resolve(strict=True)
        except OSError as exc:
            raise LabValidationError("SERVICE_DATA_ROOT_INVALID", "service data root is unavailable") from exc
        if _path_key(resolved) != _path_key(self.data_root):
            raise LabValidationError("SERVICE_DATA_ROOT_INVALID", "service data root is substituted")
        return "present"

    def _require_present_data_root(self) -> None:
        if self._data_root_state() != "present":
            raise LabValidationError("SERVICE_DATA_ROOT_MISSING", "service data root is unavailable")


def _collection(value: str) -> _CollectionSpec:
    try:
        return _COLLECTION_SPECS[value]
    except (KeyError, TypeError) as exc:
        raise LabValidationError("SERVICE_COLLECTION_INVALID", "service collection is unsupported") from exc


def _summary(collection: str, record: _Record, spec: _CollectionSpec) -> RecordSummaryDTO:
    identity = _identity(spec.identity(record))
    state = spec.state(record)
    if state is not None and (not isinstance(state, str) or not state or state != state.strip()):
        raise LabValidationError("SERVICE_RECORD_INVALID", "service record state is invalid")
    return RecordSummaryDTO(collection, identity, record.schema_version, record.digest(), state)


def _identity(value: Any) -> str:
    if not isinstance(value, str) or not _IDENTITY_RE.fullmatch(value):
        raise LabValidationError("SERVICE_IDENTITY_INVALID", "service record identity is invalid")
    return value


def _versioned(name: str, version: int) -> str:
    return f"{name}@v{version}"


def _definition_id(value: Any) -> str:
    if not isinstance(value, str) or not _DEFINITION_ID_RE.fullmatch(value):
        raise LabValidationError("SERVICE_COMMAND_INVALID", "definition identity is invalid")
    return value


def _positive_version(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LabValidationError("SERVICE_COMMAND_INVALID", "definition version is invalid")
    return value


def _path_argument(value: Any, name: str) -> Path:
    if not isinstance(value, Path):
        raise LabValidationError("SERVICE_COMMAND_INVALID", f"{name} must be a path")
    return value


def _absolute_path_argument(value: Any, name: str) -> Path:
    value = _path_argument(value, name)
    if not value.is_absolute():
        raise LabValidationError("SERVICE_COMMAND_INVALID", f"{name} must be absolute")
    return value


def _digest(value: Any) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise LabValidationError("SERVICE_COMMAND_INVALID", "expected identity digest is invalid")
    return value


def _prompt_bytes(value: Any) -> bytes:
    if not isinstance(value, str) or not value.strip():
        raise LabValidationError("SERVICE_COMMAND_INVALID", "prompt must be non-empty text")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise LabValidationError("SERVICE_COMMAND_INVALID", "prompt must be UTF-8 text") from exc
    if b"\x00" in encoded or len(encoded) > _MAX_PROMPT_BYTES:
        raise LabValidationError("SERVICE_COMMAND_INVALID", "prompt is invalid or oversized")
    return encoded


def _bytes_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _store_prompt(state_root: Path, prompt: bytes) -> None:
    digest = _bytes_digest(prompt)
    AtomicRecordStore(state_root).write_bytes(
        f"prompts/{digest.removeprefix('sha256:')}.txt",
        prompt,
    )


def _load_prompt(state_root: Path, invocation: InvocationRecord) -> str:
    """Reload the exact sealed prompt instead of accepting controller-provided text."""
    try:
        prompt = AtomicRecordStore(state_root).read_bytes(
            f"prompts/{invocation.prompt_digest.removeprefix('sha256:')}.txt",
        )
    except LabValidationError:
        raise
    if _bytes_digest(prompt) != invocation.prompt_digest:
        raise LabValidationError(
            "INTEGRATION_IDENTITY_INVALID",
            "retained prompt differs from invocation",
        )
    try:
        return prompt.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LabValidationError(
            "INTEGRATION_IDENTITY_INVALID",
            "retained prompt is not UTF-8",
        ) from exc


def _require_no_dispatch_artifacts(state_root: Path, invocation_id: str) -> None:
    store = AtomicRecordStore(state_root)
    artifacts: tuple[tuple[str, Loader], ...] = (
        (f"results/{invocation_id}.json", ResultRecord.from_mapping),
        (f"process-custody/{invocation_id}.json", ProcessCustodyRecord.from_mapping),
    )
    for path, loader in artifacts:
        if os.path.lexists(state_root / path):
            store.read(path, loader)
            raise LabValidationError(
                "INTEGRATION_AUTHORIZATION_INVALID",
                "invocation already has durable dispatch evidence",
            )


def _execute_read_only_adapter(
    invocation: InvocationRecord,
    prompt: str,
    workspace_path: Path,
    custody_store: ProcessCustodyStore,
) -> tuple[bytes, str]:
    """Use the framework client and Job Object runner for an enabled production dispatch."""
    configuration = pinned_framework_configuration()
    if configuration.framework_installation_digest != invocation.framework_installation_digest:
        raise LabValidationError(
            "INTEGRATION_IDENTITY_INVALID",
            "framework installation differs from invocation",
        )
    framework_evidence = inspect_configuration(configuration)
    worker_evidence = inspect_worker_lab_identity(
        Path(__file__).resolve().parents[1],
        invocation.worker_lab_installation_digest,
    )
    observed_runtime_identity = runtime_identity(
        configuration,
        invocation,
        evidence=framework_evidence,
    )
    runner = WindowsJobAdapterRunner(
        custody_store,
        invocation=invocation,
        timeout_seconds=invocation.timeout_seconds,
        workspace_path=workspace_path,
    )
    response = call_adapter(
        invocation,
        configuration,
        "execute-read-only",
        prompt=prompt,
        evidence=framework_evidence,
        worker_lab_evidence=worker_evidence,
        runner=runner,
    )
    return response, observed_runtime_identity


def _run_sealed_test(definition: TestDefinition, workspace_path: Path) -> int:
    """Run only a protected command test after the read-only adapter is absent."""
    if definition.runner is not TestRunner.COMMAND:
        raise LabValidationError(
            "INTEGRATION_EVALUATOR_INVALID",
            "read-only dispatch supports protected command tests only",
        )
    try:
        process = subprocess.run(
            list(definition.command),
            cwd=workspace_path,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LabValidationError(
            "INTEGRATION_VALIDATION_FAILED",
            "sealed evaluator did not complete",
        ) from exc
    return process.returncode


def _state(name: str) -> State:
    def read(record: _Record) -> str | None:
        value = getattr(record, name)
        return str(value)

    return read


def _none(record: _Record) -> None:
    del record
    return None


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def _operation_result(
    operation: str,
    resource_type: str,
    identity: str,
    record: _Record,
) -> OperationResultDTO:
    return OperationResultDTO(
        operation,
        resource_type,
        _identity(identity),
        record.digest(),
        record.identity_digest() if isinstance(record, InvocationRecord) else None,
        record.to_dict(),
    )


def _validate_attempt_authority(
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
            "ATTEMPT_POLICY_MISMATCH", "exercise policy identity is unresolved"
        )
    if (role.role_id, role.role_version) != (exercise.role_id, exercise.role_version):
        raise LabValidationError(
            "ATTEMPT_ROLE_MISMATCH", "exercise role identity is unresolved"
        )
    if (
        context.repository != exercise.template_repository
        or context.starting_commit != exercise.template_commit
    ):
        raise LabValidationError(
            "ATTEMPT_CONTEXT_MISMATCH", "context repository or starting commit differs"
        )
    if catalog.catalog_version != exercise.evaluator_catalog_version:
        raise LabValidationError(
            "ATTEMPT_CATALOG_MISMATCH", "evaluator catalog is unresolved"
        )
    known_profiles = {profile.profile_id for profile in catalog.profiles}
    missing_profiles = set(exercise.test_profile_ids) - known_profiles
    if missing_profiles:
        raise LabValidationError(
            "ATTEMPT_PROFILE_MISSING", f"unknown test profiles: {sorted(missing_profiles)}"
        )
    validate_authority(
        policy,
        role,
        required_capabilities=exercise.required_capabilities,
        temporary_denied_capabilities=exercise.temporary_denied_capabilities,
    )


def _validate_recovery_attempt_binding(
    attempt: AttemptRecord,
    invocation: InvocationRecord,
) -> None:
    expected = (
        invocation.attempt_id == attempt.attempt_id,
        invocation.exercise_id == attempt.exercise_id,
        invocation.exercise_version == attempt.exercise_version,
        invocation.policy_id == attempt.policy_id,
        invocation.policy_version == attempt.policy_version,
        invocation.policy_digest == attempt.policy_digest,
        invocation.role_id == attempt.role_id,
        invocation.role_version == attempt.role_version,
        invocation.role_digest == attempt.role_digest,
        invocation.context_digest == attempt.context_digest,
        invocation.task_digest == attempt.task_digest,
        invocation.test_catalog_version == attempt.evaluator_catalog_version,
        invocation.test_catalog_digest == attempt.evaluator_catalog_digest,
        invocation.starting_commit == attempt.starting_commit,
        invocation.sandbox_mode == attempt.sandbox_mode,
        attempt.runtime_identity == invocation.identity_digest(),
        attempt.candidate_digest is None,
    )
    if not all(expected):
        raise LabValidationError(
            "INTEGRATION_IDENTITY_INVALID",
            "recovery invocation differs from its running attempt",
        )


def _validate_dispatch_attempt_binding(
    attempt: AttemptRecord,
    invocation: InvocationRecord,
) -> None:
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
        or invocation.starting_commit != attempt.starting_commit
        or invocation.sandbox_mode != attempt.sandbox_mode
    ):
        raise LabValidationError(
            "INTEGRATION_IDENTITY_INVALID",
            "authorized invocation differs from dispatch attempt",
        )


def _validate_dispatch_definitions(
    data_root: Path,
    attempt: AttemptRecord,
    invocation: InvocationRecord,
) -> None:
    definitions = AtomicRecordStore(data_root / "curricula")
    exercise = definitions.read(
        f"exercises/{invocation.exercise_id}/v{invocation.exercise_version}.json",
        ExerciseRecord.from_mapping,
    )
    policy = definitions.read(
        f"policies/{invocation.policy_id}/v{invocation.policy_version}.json",
        PolicyRecord.from_mapping,
    )
    role = definitions.read(
        f"roles/{invocation.role_id}/v{invocation.role_version}.json",
        RoleRecord.from_mapping,
    )
    context = definitions.read(
        "contexts/"
        f"{invocation.context_manifest_id}/v{invocation.context_manifest_version}.json",
        ContextManifest.from_mapping,
    )
    catalog = definitions.read(
        f"catalogs/{invocation.test_catalog_version}.json",
        TestCatalog.from_mapping,
    )
    _validate_prepared_attempt(attempt, exercise, policy, role, context, catalog)
    if (
        invocation.exercise_digest != exercise.digest()
        or invocation.policy_digest != policy.digest()
        or invocation.role_digest != role.digest()
        or invocation.context_digest != context.digest()
        or invocation.test_catalog_digest != catalog.digest()
    ):
        raise LabValidationError(
            "INTEGRATION_IDENTITY_INVALID",
            "invocation differs from protected dispatch definitions",
        )
    ReadOnlyEvaluationPlanStore(data_root / "state").read(
        invocation.invocation_id,
    ).validate(invocation, catalog)


def _validate_running_dispatch_binding(
    attempt: AttemptRecord,
    invocation: InvocationRecord,
) -> None:
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
        or invocation.starting_commit != attempt.starting_commit
        or invocation.sandbox_mode != attempt.sandbox_mode
    ):
        raise LabValidationError(
            "INTEGRATION_IDENTITY_INVALID",
            "completed invocation differs from running attempt",
        )


def _validate_recovery_workspace(
    workspace_root: Path,
    workspace: WorkspaceLaunchEvidence,
    receipt: WorkspaceReceipt,
    attempt: AttemptRecord,
    invocation: InvocationRecord,
) -> None:
    if (
        receipt.state is not WorkspaceReceiptState.PREPARED
        or receipt.attempt_id != attempt.attempt_id
        or receipt.exercise_id != attempt.exercise_id
        or receipt.exercise_version != attempt.exercise_version
        or receipt.template_commit != attempt.starting_commit
        or receipt.digest() != invocation.workspace_receipt_digest
        or receipt.workspace_root_digest != invocation.workspace_root_digest
        or receipt.workspace_path_digest != invocation.workspace_path_digest
        or receipt.workspace_relative_path != attempt.attempt_id
        or canonical_path_digest(workspace_root) != invocation.workspace_root_digest
        or workspace.workspace_path_digest != invocation.workspace_path_digest
        or workspace.observed_head != invocation.starting_commit
        or workspace.status
    ):
        raise LabValidationError(
            "OPERATOR_RECOVERY_INVALID",
            "workspace receipt or unchanged identity differs",
        )


def _validate_prepared_attempt(
    attempt: AttemptRecord,
    exercise: ExerciseRecord,
    policy: PolicyRecord,
    role: RoleRecord,
    context: ContextManifest,
    catalog: TestCatalog,
) -> None:
    _validate_attempt_authority(exercise, policy, role, context, catalog)
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
            "INTEGRATION_IDENTITY_INVALID",
            "attempt identity differs from protected invocation definitions",
        )


def _validate_target_repository(
    lab_root: Path,
    target_repository: Path,
    expected_head: str,
) -> None:
    if target_repository.is_symlink():
        raise LabValidationError(
            "ATTEMPT_REPOSITORY_INVALID", "target repository cannot be a symlink"
        )
    try:
        target = target_repository.resolve(strict=True)
        lab = lab_root.resolve(strict=True)
    except OSError as exc:
        raise LabValidationError(
            "ATTEMPT_REPOSITORY_INVALID", "repository path is missing"
        ) from exc
    if target == lab or target.is_relative_to(lab) or lab.is_relative_to(target):
        raise LabValidationError(
            "ATTEMPT_REPOSITORY_INVALID", "worker target must be separate from Worker Lab"
        )
    try:
        head = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(target), "status", "--porcelain=v1"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise LabValidationError(
            "ATTEMPT_REPOSITORY_INVALID", "target is not a readable Git repository"
        ) from exc
    if head != expected_head:
        raise LabValidationError(
            "ATTEMPT_HEAD_MISMATCH", "target HEAD differs from exercise identity"
        )
    if dirty:
        raise LabValidationError(
            "ATTEMPT_REPOSITORY_DIRTY", "target repository must be clean"
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


_COLLECTION_SPECS: Mapping[str, _CollectionSpec] = {
    "attempts": _CollectionSpec("state", "attempts", AttemptRecord.from_mapping, lambda item: item.attempt_id, _state("state")),
    "catalogs": _CollectionSpec("curricula", "catalogs", TestCatalog.from_mapping, lambda item: item.catalog_version, _none),
    "contexts": _CollectionSpec("curricula", "contexts", ContextManifest.from_mapping, lambda item: _versioned(item.manifest_id, item.manifest_version), _none),
    "curricula": _CollectionSpec("curricula", "curricula", CurriculumRecord.from_mapping, lambda item: item.curriculum_id, _state("status")),
    "evidence": _CollectionSpec("state", "evidence", EvidenceRecord.from_mapping, lambda item: item.evidence_digest, _state("verification_state")),
    "exercises": _CollectionSpec("curricula", "exercises", ExerciseRecord.from_mapping, lambda item: _versioned(item.exercise_id, item.exercise_version), _none),
    "failures": _CollectionSpec("state", "failures", FailureRecord.from_mapping, lambda item: item.failure_id, _state("classification")),
    "invocations": _CollectionSpec("state", "invocations", InvocationRecord.from_mapping, lambda item: item.invocation_id, _state("state")),
    "policies": _CollectionSpec("curricula", "policies", PolicyRecord.from_mapping, lambda item: _versioned(item.policy_id, item.policy_version), _none),
    "results": _CollectionSpec("state", "results", ResultRecord.from_mapping, lambda item: item.invocation_id, _state("process_outcome")),
    "roles": _CollectionSpec("curricula", "roles", RoleRecord.from_mapping, lambda item: _versioned(item.role_id, item.role_version), _none),
}

_WORKSPACE_SPEC = _CollectionSpec(
    "state", "workspaces", WorkspaceReceipt.from_mapping, lambda item: item.attempt_id, _state("state")
)
_CUSTODY_SPEC = _CollectionSpec(
    "state", "process-custody", ProcessCustodyRecord.from_mapping,
    lambda item: item.invocation_id, _state("state"),
)

if tuple(sorted(_COLLECTION_SPECS)) != COLLECTIONS:
    raise RuntimeError("service collection declaration differs")
