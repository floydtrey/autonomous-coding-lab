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
from .canonical import canonical_digest, canonical_json
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
)
from .operator_control import (
    DoctorReport,
    inspect_installation,
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
from .test_catalog import ChangeFacts, TestCatalog
from .validation import attempt_task_digest
from .workspace import discard_workspace, prepare_workspace, verify_workspace
from .read_only_evidence import (
    READ_ONLY_EVALUATION_PLAN_SCHEMA,
    ReadOnlyEvaluationPlan,
    ReadOnlyEvaluationPlanStore,
)


HEALTH_SCHEMA = "worker-lab-service-health:v1"
INSTALLATION_STATUS_SCHEMA = "worker-lab-service-installation-status:v1"
RECORD_LIST_SCHEMA = "worker-lab-service-record-list:v1"
RECORD_DETAIL_SCHEMA = "worker-lab-service-record-detail:v1"
OPERATION_RESULT_SCHEMA = "worker-lab-service-operation-result:v2"

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


class WorkerLabApplicationService:
    """Application boundary shared by operator clients and the future GUI."""

    def __init__(self, data_root: Path, *, clock: Callable[[], str] | None = None) -> None:
        if not isinstance(data_root, Path) or not data_root.is_absolute():
            raise LabValidationError("SERVICE_DATA_ROOT_INVALID", "service data root must be absolute")
        self.data_root = data_root
        self._clock = clock or _utc_now

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

    def _store(self, spec: _CollectionSpec) -> AtomicRecordStore:
        return AtomicRecordStore(self.data_root / spec.storage_root)

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

if tuple(sorted(_COLLECTION_SPECS)) != COLLECTIONS:
    raise RuntimeError("service collection declaration differs")
