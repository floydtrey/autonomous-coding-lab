from __future__ import annotations

import json
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
    SourceDoctorReport,
    inspect_source_identity,
    validate_controller_identity,
)
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
from .process_custody import (
    CustodyBackend,
    CustodyState,
    ProcessCustodyRecord,
    ProcessCustodyStore,
    recover_absence_after_controller_exit,
)
from .windows_job import WindowsJobCustodyBackend, WorkspaceLaunchEvidence

from .integration_v3 import INVOCATION_SCHEMA_V3, InvocationRecordV3, ResultRecordV3
from .service_runtime_v3 import (
    WorkspaceDispatchRunner,
    authorize_invocation as authorize_invocation_v3,
    cancel_invocation as cancel_invocation_v3,
    dispatch_invocation as dispatch_invocation_v3,
    load_invocation_record,
    load_result_record,
    prepare_invocation as prepare_invocation_v3,
    recover_invocation as recover_invocation_v3,
    reject_invocation as reject_invocation_v3,
    review_candidate as review_candidate_v3,
)


HEALTH_SCHEMA = "worker-lab-service-health:v1"
SOURCE_STATUS_SCHEMA = "worker-lab-service-source-status:v1"
RECORD_LIST_SCHEMA = "worker-lab-service-record-list:v1"
RECORD_DETAIL_SCHEMA = "worker-lab-service-record-detail:v1"
OPERATION_RESULT_SCHEMA = "worker-lab-service-operation-result:v2"
BACKUP_RESULT_SCHEMA = "worker-lab-service-backup-result:v1"
RECOVERY_RESULT_SCHEMA = "worker-lab-service-recovery-result:v2"
ATTEMPT_TIMELINE_SCHEMA = "worker-lab-service-attempt-timeline:v1"
WORKSPACE_WRITE_CANDIDATE_REVIEW_SCHEMA = "worker-lab-service-candidate-review:v2"
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


class _Record(Protocol):
    schema_version: str

    def to_dict(self) -> dict[str, Any]: ...

    def digest(self) -> str: ...


Loader = Callable[[Any], _Record]
Identity = Callable[[_Record], str]
State = Callable[[_Record], str | None]
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
class SourceStatusDTO:
    doctor: SourceDoctorReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SOURCE_STATUS_SCHEMA,
            "source_identity": self.doctor.to_dict(),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class HealthDTO:
    doctor: SourceDoctorReport
    data_root_state: str
    collection_counts: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": HEALTH_SCHEMA,
            "status": "healthy",
            "data_root_state": self.data_root_state,
            "execution_ready": False,
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
    invocation: InvocationRecordV3
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
    schema_version: str
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
        value = {
            "schema_version": self.schema_version,
            "candidate_digest": self.candidate_digest,
            "attempt": self.attempt.to_dict(),
            "invocation": self.invocation.to_dict(),
            "result": self.result.to_dict(),
            "custody": self.custody.to_dict(),
            "changed_paths": list(self.changed_paths),
            "validation_stages": [dict(item) for item in self.validation_stages],
            "evidence": [item.to_dict() for item in self.evidence],
            "failures": [item.to_dict() for item in self.failures],
            "first_failure_boundary": self.first_failure_boundary,
        }
        value["candidate_content_digest"] = self.proposal_content_digest
        return value

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


class WorkerLabApplicationService:
    """Application boundary shared by operator clients and the future GUI."""

    def __init__(
        self,
        data_root: Path,
        *,
        clock: Callable[[], str] | None = None,
        custody_backend: CustodyBackend | None = None,
        sealed_test_executor: SealedTestExecutor | None = None,
        workspace_dispatch_runner: WorkspaceDispatchRunner | None = None,
    ) -> None:
        if not isinstance(data_root, Path) or not data_root.is_absolute():
            raise LabValidationError("SERVICE_DATA_ROOT_INVALID", "service data root must be absolute")
        if sealed_test_executor is not None and not callable(sealed_test_executor):
            raise LabValidationError("SERVICE_COMMAND_INVALID", "sealed test executor must be callable")
        if workspace_dispatch_runner is not None and not callable(workspace_dispatch_runner):
            raise LabValidationError("SERVICE_COMMAND_INVALID", "V3 workspace dispatch runner must be callable")
        if custody_backend is not None and (
            not isinstance(getattr(custody_backend, "backend_id", None), str)
            or not callable(getattr(custody_backend, "absence_evidence_after_controller_exit", None))
        ):
            raise LabValidationError("SERVICE_COMMAND_INVALID", "custody backend must satisfy Custody V2")
        self.data_root = data_root
        self._clock = clock or _utc_now
        self._custody_backend = custody_backend or WindowsJobCustodyBackend()
        self._sealed_test_executor = sealed_test_executor or _run_sealed_test
        self._workspace_dispatch_runner = workspace_dispatch_runner

    def source_status(self) -> SourceStatusDTO:
        _, report = inspect_source_identity()
        return SourceStatusDTO(report)

    def health(self) -> HealthDTO:
        _, report = inspect_source_identity()
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
        if timeline.invocations[0].record.get("schema_version") != INVOCATION_SCHEMA_V3:
            raise LabValidationError(
                "SERVICE_CANDIDATE_IDENTITY_INVALID",
                "candidate invocation is not a current V3 record",
            )
        invocation = InvocationRecordV3.from_mapping(timeline.invocations[0].record)
        result = ResultRecordV3.from_mapping(timeline.results[0].record)
        custody = ProcessCustodyRecord.from_mapping(timeline.custody[0].record)
        reviewed = review_candidate_v3(
            self.data_root / "state",
            attempt=attempt,
            invocation=invocation,
            result=result,
            custody=custody,
        )
        evidence = tuple(
            item for item in timeline.evidence
            if verify_evidence(self.data_root, item.summary.identity).attempt_id == attempt_id
        )
        return CandidateReviewDTO(
            WORKSPACE_WRITE_CANDIDATE_REVIEW_SCHEMA,
            attempt.candidate_digest,
            timeline.attempt,
            timeline.invocations[0],
            timeline.results[0],
            timeline.custody[0],
            reviewed.retained_framework_candidate_digest,
            reviewed.changed_paths,
            tuple(stage.to_dict() for stage in reviewed.validation_stages),
            evidence,
            timeline.failures,
            reviewed.first_failure_boundary,
        )

    def prepare_invocation(
        self,
        attempt_id: str,
        workspace_root: Path,
        prompt: str,
        *,
        logical_target_id: str,
        provider_binding_id: str,
        provider_binding_digest: str,
    ) -> OperationResultDTO:
        attempt_id = _identity(attempt_id)
        workspace_root = _absolute_path_argument(workspace_root, "workspace root")
        self._require_present_data_root()
        invocation = prepare_invocation_v3(
            self.data_root,
            attempt_id=attempt_id,
            workspace_root=workspace_root,
            prompt=prompt,
            logical_target_id=logical_target_id,
            provider_binding_id=provider_binding_id,
            provider_binding_digest=provider_binding_digest,
        )
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
        self._require_present_data_root()
        invocation = authorize_invocation_v3(
            self.data_root,
            invocation_id=invocation_id,
            expected_identity_digest=expected_identity_digest,
            controller_identity=controller_identity,
            authorized_at=self._clock(),
        )
        return _operation_result(
            "authorize-invocation", "invocation", invocation_id, invocation
        )

    def reject_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
    ) -> OperationResultDTO:
        invocation_id = _identity(invocation_id)
        self._require_present_data_root()
        invocation = reject_invocation_v3(
            self.data_root,
            invocation_id=invocation_id,
            expected_identity_digest=expected_identity_digest,
        )
        return _operation_result(
            "reject-invocation", "invocation", invocation_id, invocation
        )

    def cancel_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
        controller_identity: str,
    ) -> OperationResultDTO:
        invocation_id = _identity(invocation_id)
        self._require_present_data_root()
        invocation = cancel_invocation_v3(
            self.data_root,
            invocation_id=invocation_id,
            expected_identity_digest=expected_identity_digest,
            controller_identity=controller_identity,
        )
        return _operation_result(
            "cancel-invocation", "invocation", invocation_id, invocation
        )

    def dispatch_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
        controller_identity: str,
        workspace_root: Path,
    ) -> OperationResultDTO:
        invocation_id = _identity(invocation_id)
        workspace_root = _absolute_path_argument(workspace_root, "workspace root")
        self._require_present_data_root()
        attempt = dispatch_invocation_v3(
            self.data_root,
            invocation_id=invocation_id,
            expected_identity_digest=expected_identity_digest,
            controller_identity=controller_identity,
            workspace_root=workspace_root,
            clock=self._clock,
            workspace_dispatch_runner=self._workspace_dispatch_runner,
            sealed_test_executor=self._sealed_test_executor,
        )
        return _operation_result(
            "dispatch-invocation", "attempt", attempt.attempt_id, attempt
        )

    def recover_invocation(
        self,
        invocation_id: str,
        expected_identity_digest: str,
        controller_identity: str,
        workspace_root: Path,
    ) -> RecoveryResultDTO:
        invocation_id = _identity(invocation_id)
        workspace_root = _absolute_path_argument(workspace_root, "workspace root")
        self._require_present_data_root()
        recovered = recover_invocation_v3(
            self.data_root,
            invocation_id=invocation_id,
            expected_identity_digest=expected_identity_digest,
            controller_identity=controller_identity,
            workspace_root=workspace_root,
            clock=self._clock,
            custody_backend=self._custody_backend,
        )
        return RecoveryResultDTO(
            recovered.controller_identity,
            recovered.invocation,
            recovered.attempt,
            recovered.custody,
            recovered.workspace,
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
        record.identity_digest() if isinstance(record, InvocationRecordV3) else None,
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
    "invocations": _CollectionSpec("state", "invocations", load_invocation_record, lambda item: item.invocation_id, _state("state")),
    "policies": _CollectionSpec("curricula", "policies", PolicyRecord.from_mapping, lambda item: _versioned(item.policy_id, item.policy_version), _none),
    "results": _CollectionSpec("state", "results", load_result_record, lambda item: item.invocation_id, _state("process_outcome")),
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
