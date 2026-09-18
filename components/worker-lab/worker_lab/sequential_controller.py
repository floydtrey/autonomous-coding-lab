"""M09B/M09C sequential run, status, stop request, and conservative reconcile.

This module assembles existing M07/M08/M09A operations.  It does not retry,
compact, switch models, resume sessions, or infer success from worker prose.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from .attempt_store import AttemptStore
from .canonical import canonical_digest, canonical_json
from .controller_task_packet import build_controller_task_packet
from .errors import LabValidationError
from .integration_v3 import InvocationState
from .invocation_store_v3 import InvocationStoreV3
from .job_plan import JobPlan, identity
from .job_runner import (
    _accepted,
    _artifact,
    _binding,
    block_active_reconciliation,
    read_job,
    record_stop_reconciliation,
)
from .operator_control import validate_controller_identity
from .pi_supervision import _exclusive_controller
from .provider_binding import ProviderBindingStore
from .protected_validation import _optional
from .storage import AtomicRecordStore

STATUS_SCHEMA = "worker-lab-job-status:v1"
RUN_TASK_SCHEMA = "worker-lab-run-task:v1"
STOP_SCHEMA = "worker-lab-job-stop-request:v1"


@dataclass(frozen=True)
class JobStatusReport:
    payload: str

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self.payload)

    def to_json(self) -> str:
        return self.payload

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def _stop_path(job_id: str, reservation_id: str) -> str:
    return f"job-stop-requests/{identity(job_id, 'job_id')}/{reservation_id[7:]}.json"


def _validate_stop_request(value, *, job_id, task_id, reservation_id, controller_identity):
    fields = {
        "schema_version", "job_id", "task_id", "reservation_id",
        "controller_identity", "requested_at",
    }
    if (
        not isinstance(value, dict)
        or set(value) != fields
        or value["schema_version"] != STOP_SCHEMA
        or value["job_id"] != job_id
        or value["task_id"] != task_id
        or value["reservation_id"] != reservation_id
        or value["controller_identity"] != controller_identity
        or not isinstance(value["requested_at"], str)
        or not value["requested_at"].endswith("Z")
    ):
        raise LabValidationError(
            "JOB_STOP_REQUEST_INVALID",
            "durable stop request differs from the active reservation",
        )
    return value


def _active_stop_request(records, job_value):
    active = job_value["active"]
    if active is None:
        return None
    path = _stop_path(job_value["job_id"], active["reservation_id"])
    value = _optional(records, path)
    if value is None:
        return None
    return _validate_stop_request(
        value,
        job_id=job_value["job_id"],
        task_id=active["task_id"],
        reservation_id=active["reservation_id"],
        controller_identity=job_value["controller_identity"],
    )


class _JobStopToken:
    """Cancellation token backed by the exact active reservation's durable request."""

    def __init__(self, records, *, job_id, task_id, reservation_id, controller_identity):
        self.records = records
        self.job_id = job_id
        self.task_id = task_id
        self.reservation_id = reservation_id
        self.controller_identity = controller_identity

    def is_set(self):
        value = _optional(self.records, _stop_path(self.job_id, self.reservation_id))
        if value is None:
            return False
        _validate_stop_request(
            value,
            job_id=self.job_id,
            task_id=self.task_id,
            reservation_id=self.reservation_id,
            controller_identity=self.controller_identity,
        )
        return True


def job_status(data_root: Path, job_id: str) -> JobStatusReport:
    """Project the durable job aggregate without changing controller state."""
    job = read_job(Path(data_root), identity(job_id, "job_id"))
    value = job.to_dict()
    plan = JobPlan.from_mapping(value["plan"])
    tasks = []
    evidence_gaps = []
    records = AtomicRecordStore(Path(data_root) / "state")
    stop_request = None
    try:
        stop_request = _active_stop_request(records, value)
    except LabValidationError as exc:
        evidence_gaps.append({
            "task_id": value["active"]["task_id"] if value["active"] is not None else None,
            "code": exc.code,
            "message": exc.summary,
        })
    for task in plan.tasks:
        item = value["tasks"][task.task_id]
        last = item["attempts"][-1] if item["attempts"] else None
        tasks.append({
            "task_id": task.task_id,
            "state": item["state"],
            "dependencies": list(item["dependencies"]),
            "attempt_count": len(item["attempts"]),
            "last_attempt": None if last is None else dict(last),
            "acceptance": None if item["acceptance"] is None else dict(item["acceptance"]),
            "artifact": None if item["artifact"] is None else dict(item["artifact"]),
            "blocker": None if item["blocker"] is None else dict(item["blocker"]),
        })
        if (
            last is not None
            and last["attempt_id"] is not None
            and value["active"] is not None
            and value["active"]["task_id"] == task.task_id
        ):
            try:
                _binding(
                    Path(data_root),
                    value,
                    task.task_id,
                    last["attempt_id"],
                    last["invocation_id"],
                )
            except LabValidationError as exc:
                evidence_gaps.append({
                    "task_id": task.task_id,
                    "code": exc.code,
                    "message": exc.summary,
                })
        if last is not None and last["run_reference"] is not None:
            try:
                retained = records.read(last["run_reference"], lambda stored: stored)
                if canonical_digest(retained) != last["run_digest"]:
                    raise LabValidationError(
                        "JOB_RESULT_CHANGED",
                        "retained task result differs from the job reference",
                    )
            except LabValidationError as exc:
                evidence_gaps.append({
                    "task_id": task.task_id,
                    "code": exc.code,
                    "message": exc.summary,
                })
        if item["state"] == "accepted":
            try:
                _accepted(records, item)
            except LabValidationError as exc:
                evidence_gaps.append({
                    "task_id": task.task_id,
                    "code": exc.code,
                    "message": exc.summary,
                })
            if item["artifact"] is None:
                evidence_gaps.append({
                    "task_id": task.task_id,
                    "code": "JOB_INPUT_PROMOTION_REQUIRED",
                    "message": "accepted task has no attached verified snapshot",
                })
            else:
                try:
                    _artifact(Path(data_root), item)
                except LabValidationError as exc:
                    evidence_gaps.append({
                        "task_id": task.task_id,
                        "code": exc.code,
                        "message": exc.summary,
                    })
    objective_complete = (
        value["status"] == "complete"
        and value["active"] is None
        and not evidence_gaps
        and all(item["state"] == "accepted" for item in value["tasks"].values())
    )
    runnable = (
        value["status"] == "ready"
        and value["active"] is None
        and not evidence_gaps
        and not objective_complete
    )
    report = {
        "schema_version": STATUS_SCHEMA,
        "job_id": value["job_id"],
        "job_digest": job.digest(),
        "plan_id": plan.plan_id,
        "plan_revision": plan.revision,
        "plan_digest": value["plan_digest"],
        "controller_identity": value["controller_identity"],
        "generation": value["generation"],
        "status": value["status"],
        "objective_complete": objective_complete,
        "runnable": runnable,
        "active": None if value["active"] is None else dict(value["active"]),
        "stop_request": None if stop_request is None else dict(stop_request),
        "blocker": None if value["blocker"] is None else dict(value["blocker"]),
        "evidence_gaps": evidence_gaps,
        "tasks": tasks,
    }
    return JobStatusReport(canonical_json(report))


def run_job(
    service,
    *,
    job_id: str,
    plan: JobPlan,
    approved_plan_digest: str,
    controller_identity: str,
    target_repository: Path,
    workspace_root: Path,
    artifact_root: Path,
    provider_binding_id: str,
    protected_files: Iterable[Path],
    acknowledge_unsandboxed: bool,
    review_required: bool = False,
    validation_timeout_seconds: int = 30,
    validation_output_limit_bytes: int = 1048576,
    validation_cleanup_timeout_seconds: int = 5,
    candidate_archive_limit_bytes: int | None = None,
    runner_factory=None,
    process_factory=None,
) -> JobStatusReport:
    """Run pending tasks in approved order until complete or durably blocked.

    Every attempt is reserved before admission.  Each accepted task is promoted
    and attached before another reservation is allowed.
    """
    plan = JobPlan.from_mapping(plan.to_dict() if isinstance(plan, JobPlan) else plan)
    if plan.digest() != approved_plan_digest:
        raise LabValidationError(
            "JOB_PLAN_APPROVAL_MISMATCH",
            "sequential run requires the exact approved plan digest",
        )
    job_id = identity(job_id, "job_id")
    protected_files = tuple(Path(path).resolve() for path in protected_files)
    if not protected_files:
        raise LabValidationError(
            "VALIDATION_INPUT_INVALID",
            "sequential run requires explicit protected validator inputs",
        )
    if acknowledge_unsandboxed is not True:
        raise LabValidationError(
            "VALIDATION_APPROVAL_REQUIRED",
            "sequential run requires explicit acknowledgement of unsandboxed local validators",
        )
    if type(review_required) is not bool:
        raise LabValidationError("TASK_EXECUTION_APPROVAL_INVALID", "review requirement must be explicit")
    for number in (
        validation_timeout_seconds,
        validation_output_limit_bytes,
        validation_cleanup_timeout_seconds,
    ):
        if type(number) is not int or number <= 0:
            raise LabValidationError("VALIDATION_APPROVAL_INVALID", "validation limits must be positive integers")
    if candidate_archive_limit_bytes is not None and (
        type(candidate_archive_limit_bytes) is not int or candidate_archive_limit_bytes < 0
    ):
        raise LabValidationError(
            "CANDIDATE_ARCHIVE_LIMIT_INVALID",
            "candidate archive limit must be a nonnegative byte count",
        )

    data_root = Path(service.data_root)
    records = AtomicRecordStore(data_root / "state")
    service.create_job(
        job_id,
        plan,
        approved_by=controller_identity,
        approved_plan_digest=approved_plan_digest,
    )

    while True:
        status = job_status(data_root, job_id)
        shown = status.to_dict()
        if shown["status"] == "blocked":
            return status
        if shown["objective_complete"]:
            return status
        if shown["evidence_gaps"]:
            raise LabValidationError(
                "JOB_RECONCILIATION_REQUIRED",
                "accepted task snapshot bookkeeping is incomplete; M09B will not infer or repeat promotion",
            )
        if shown["active"] is not None or shown["status"] == "active":
            raise LabValidationError(
                "JOB_RECONCILIATION_REQUIRED",
                "an existing reservation must be reconciled before sequential run can continue",
            )
        if shown["status"] == "complete":
            raise LabValidationError(
                "JOB_RECONCILIATION_REQUIRED",
                "job completion lacks the accepted snapshot lineage required by M09B",
            )
        if shown["status"] != "ready":
            raise LabValidationError("JOB_NOT_RUNNABLE", "job is not ready for sequential execution")

        # Validate the explicitly selected provider before consuming a reservation.
        # Complete or durably blocked jobs therefore do not depend on provider health.
        binding = ProviderBindingStore(records.root).read(provider_binding_id)
        current = service.read_job(job_id)
        reserved = service.reserve_next_job_task(
            job_id,
            controller_identity=controller_identity,
            expected_job_digest=current.digest(),
        )
        reserved_value = reserved.to_dict()
        task_id = reserved_value["active"]["task_id"]
        reservation_id = reserved_value["active"]["reservation_id"]
        cancellation = _JobStopToken(
            records,
            job_id=job_id,
            task_id=task_id,
            reservation_id=reservation_id,
            controller_identity=controller_identity,
        )
        input_binding = service.prepare_job_input(
            job_id,
            controller_identity=controller_identity,
            reservation_id=reservation_id,
        )
        source_repository = (
            Path(target_repository)
            if input_binding is None
            else Path(input_binding.to_dict()["repository"])
        )
        admitted = service.admit_job_task(
            plan,
            task_id,
            source_repository,
            approved_by=controller_identity,
            approved_plan_digest=approved_plan_digest,
            input_binding=input_binding,
        )
        attempt_id = admitted.identity
        service.prepare_workspace(attempt_id, source_repository, workspace_root)
        attempt = AttemptStore(records.root).read(attempt_id)
        packet = build_controller_task_packet(
            attempt,
            controller_identity=controller_identity,
            user_request=plan.objective.text,
            no_context=True,
        )
        prepared = service.prepare_invocation(
            attempt_id,
            workspace_root,
            packet.to_json(),
            logical_target_id=plan.objective.target_id,
            provider_binding_id=binding.binding_id,
            provider_binding_digest=binding.digest(),
        ).to_dict()
        invocation_id = prepared["identity"]
        invocation_digest = prepared["immutable_identity_digest"]
        service.bind_job_attempt(
            job_id,
            controller_identity=controller_identity,
            reservation_id=reservation_id,
            attempt_id=attempt_id,
            invocation_id=invocation_id,
            expected_invocation_digest=invocation_digest,
        )
        service.authorize_invocation(invocation_id, invocation_digest, controller_identity)

        task_value = {
            "schema_version": RUN_TASK_SCHEMA,
            "invocation_id": invocation_id,
            "expected_identity_digest": invocation_digest,
            "controller_identity": controller_identity,
            "workspace_root": str(Path(workspace_root).resolve()),
        }
        task_reference = f"controller-tasks/{attempt_id}.json"
        records.write_bytes(
            task_reference,
            (canonical_json(task_value) + "\n").encode("utf-8"),
        )
        task_file = records.root / task_reference
        service.approve_task_execution(
            task_file,
            controller_identity,
            protected_files=protected_files,
            acknowledge_unsandboxed=True,
            review_required=review_required,
            timeout_seconds=validation_timeout_seconds,
            output_limit_bytes=validation_output_limit_bytes,
            cleanup_timeout_seconds=validation_cleanup_timeout_seconds,
        )
        options = {
            "candidate_archive_limit_bytes": candidate_archive_limit_bytes,
            "cancellation": cancellation,
        }
        if runner_factory is not None:
            options["runner_factory"] = runner_factory
        if process_factory is not None:
            options["process_factory"] = process_factory
        run_report = service.run_task(task_file, **options)
        current = service.record_job_task_result(
            job_id,
            controller_identity=controller_identity,
            reservation_id=reservation_id,
            task_run_digest=run_report.digest(),
        )
        current_value = current.to_dict()
        item = current_value["tasks"][task_id]
        if item["state"] != "accepted":
            return job_status(data_root, job_id)

        acceptance = item["acceptance"]
        snapshot = service.promote_accepted_task(
            attempt_id,
            acceptance["digest"],
            controller_identity,
            artifact_root,
        )
        service.attach_job_artifact(
            job_id,
            task_id=task_id,
            controller_identity=controller_identity,
            acceptance_digest=acceptance["digest"],
            artifact_reference=snapshot.to_dict()["reference"],
            artifact_digest=snapshot.digest(),
        )


def stop_job(data_root: Path, job_id: str, *, controller_identity: str, clock) -> JobStatusReport:
    """Request cancellation of only the exact active reservation.

    The running supervisor already owns termination of its Windows Job.  This
    command only writes a durable, reservation-bound request that its existing
    cancellation token polls.
    """
    data_root = Path(data_root)
    job_id = identity(job_id, "job_id")
    controller = validate_controller_identity(controller_identity)
    records = AtomicRecordStore(data_root / "state")
    with _exclusive_controller(records.root, "job-controller.lock"):
        job = read_job(data_root, job_id)
        value = job.to_dict()
        if value["controller_identity"] != controller:
            raise LabValidationError(
                "JOB_CONTROLLER_MISMATCH",
                "stop controller differs from the approved job controller",
            )
        active = value["active"]
        if active is None:
            return job_status(data_root, job_id)
        path = _stop_path(job_id, active["reservation_id"])
        existing = _optional(records, path)
        if existing is None:
            request = {
                "schema_version": STOP_SCHEMA,
                "job_id": job_id,
                "task_id": active["task_id"],
                "reservation_id": active["reservation_id"],
                "controller_identity": controller,
                "requested_at": clock(),
            }
            records.write_bytes(path, (canonical_json(request) + "\n").encode("utf-8"))
        else:
            _validate_stop_request(
                existing,
                job_id=job_id,
                task_id=active["task_id"],
                reservation_id=active["reservation_id"],
                controller_identity=controller,
            )
    return job_status(data_root, job_id)


def _retained_task_runs(records, *, attempt_id, invocation_id):
    runs = []
    directory = f"task-runs/{attempt_id}"
    for path in records.list_paths(directory):
        value = records.read(path, lambda stored: stored)
        if (
            isinstance(value, dict)
            and value.get("schema_version") == "worker-lab-task-run:v1"
            and value.get("attempt_id") == attempt_id
            and value.get("invocation_id") == invocation_id
            and path == f"{directory}/{canonical_digest(value)[7:]}.json"
        ):
            runs.append((path, value, canonical_digest(value)))
    return runs


def _reconcile_accepted_artifacts(service, job_id, controller_identity, artifact_root):
    """Attach/recover deterministic M08 output; never start another task."""
    data_root = Path(service.data_root)
    records = AtomicRecordStore(data_root / "state")
    while True:
        value = service.read_job(job_id).to_dict()
        missing = next(
            (
                (task_id, item)
                for task_id, item in value["tasks"].items()
                if item["state"] == "accepted" and item["artifact"] is None
            ),
            None,
        )
        if missing is None:
            return
        task_id, item = missing
        acceptance = item["acceptance"]
        snapshot_id = "SNAPSHOT-" + acceptance["digest"][7:]
        reference = f"accepted-snapshots/{snapshot_id}.json"
        existing = _optional(records, reference)
        if existing is not None:
            from .accepted_snapshot import verify_accepted_snapshot
            snapshot = verify_accepted_snapshot(
                data_root,
                reference=reference,
                expected_digest=canonical_digest(existing),
            )
        else:
            root = artifact_root
            intent = _optional(records, f"snapshot-intents/{snapshot_id}.json")
            if root is None and isinstance(intent, dict):
                candidate_root = intent.get("artifact_root")
                if isinstance(candidate_root, str):
                    root = Path(candidate_root)
            if root is None:
                raise LabValidationError(
                    "JOB_RECONCILIATION_ARTIFACT_ROOT_REQUIRED",
                    "accepted task needs an artifact root before promotion can be completed",
                )
            snapshot = service.promote_accepted_task(
                item["attempts"][-1]["attempt_id"],
                acceptance["digest"],
                controller_identity,
                Path(root).resolve(),
            )
        service.attach_job_artifact(
            job_id,
            task_id=task_id,
            controller_identity=controller_identity,
            acceptance_digest=acceptance["digest"],
            artifact_reference=snapshot.to_dict()["reference"],
            artifact_digest=snapshot.digest(),
        )


def reconcile_job(service, job_id: str, *, controller_identity: str, artifact_root=None):
    """Finish only provable M09 bookkeeping; never launch replacement work."""
    data_root = Path(service.data_root)
    job_id = identity(job_id, "job_id")
    controller = validate_controller_identity(controller_identity)
    job = service.read_job(job_id)
    if job.to_dict()["controller_identity"] != controller:
        raise LabValidationError(
            "JOB_CONTROLLER_MISMATCH",
            "reconciliation controller differs from the approved job controller",
        )

    _reconcile_accepted_artifacts(service, job_id, controller, artifact_root)
    status = job_status(data_root, job_id)
    if status.to_dict()["active"] is None:
        return status

    records = AtomicRecordStore(data_root / "state")
    value = service.read_job(job_id).to_dict()
    active = value["active"]
    task_id = active["task_id"]
    reservation_id = active["reservation_id"]
    item = value["tasks"][task_id]
    slot = item["attempts"][-1]

    if item["state"] == "pending_review":
        return job_status(data_root, job_id)

    if slot["attempt_id"] is None:
        block_active_reconciliation(
            data_root,
            job_id,
            controller_identity=controller,
            reservation_id=reservation_id,
            code="JOB_RECONCILED_UNSTARTED",
            message="reserved task was never admitted; the consumed reservation is blocked without replacement",
            clock=service._clock,
        )
        return job_status(data_root, job_id)

    attempt_id = slot["attempt_id"]
    invocation_id = slot["invocation_id"]
    runs = _retained_task_runs(
        records,
        attempt_id=attempt_id,
        invocation_id=invocation_id,
    )
    if len(runs) > 1:
        raise LabValidationError(
            "JOB_RECONCILIATION_AMBIGUOUS",
            "multiple retained task results exist for the active reservation",
        )
    if len(runs) == 1 and slot["run_reference"] is None:
        _, _, digest = runs[0]
        service.record_job_task_result(
            job_id,
            controller_identity=controller,
            reservation_id=reservation_id,
            task_run_digest=digest,
        )
        _reconcile_accepted_artifacts(service, job_id, controller, artifact_root)
        refreshed = service.read_job(job_id).to_dict()
        if refreshed["active"] is None:
            return job_status(data_root, job_id)
        value = refreshed
        item = value["tasks"][task_id]
        slot = item["attempts"][-1]

    invocation = InvocationStoreV3(records.root).read(invocation_id)
    if (
        invocation.attempt_id != attempt_id
        or invocation.identity_digest() != slot["invocation_digest"]
    ):
        raise LabValidationError(
            "JOB_INVOCATION_MISMATCH",
            "active reservation no longer binds the exact invocation",
        )

    run_intent = _optional(records, f"run-task-intents/{attempt_id}.json")
    outcome = _optional(records, f"worker-outcomes/{attempt_id}.json")
    if outcome is not None:
        if outcome.get("stop_state") not in {"absence_verified", "not_started"}:
            raise LabValidationError(
                "JOB_RECONCILIATION_REQUIRED",
                "worker outcome still lacks exact stop evidence",
            )
        block_active_reconciliation(
            data_root,
            job_id,
            controller_identity=controller,
            reservation_id=reservation_id,
            code="JOB_RECONCILED_WITHOUT_ACCEPTANCE",
            message="worker stopped without a retained accepted task result; no replacement was launched",
            clock=service._clock,
        )
        return job_status(data_root, job_id)

    if run_intent is None:
        if invocation.state is InvocationState.PREPARED:
            service.reject_invocation(invocation_id, invocation.identity_digest())
        elif invocation.state is InvocationState.AUTHORIZED:
            service.cancel_invocation(
                invocation_id,
                invocation.identity_digest(),
                controller,
            )
        elif invocation.state not in {InvocationState.REJECTED, InvocationState.ABORTED}:
            raise LabValidationError(
                "JOB_RECONCILIATION_REQUIRED",
                "bound invocation has execution state but no durable run intent",
            )
        block_active_reconciliation(
            data_root,
            job_id,
            controller_identity=controller,
            reservation_id=reservation_id,
            code="JOB_RECONCILED_UNSTARTED",
            message="bound task never entered the durable run transaction; reservation is blocked without replacement",
            clock=service._clock,
        )
        return job_status(data_root, job_id)

    if invocation.state is InvocationState.AUTHORIZED:
        record_stop_reconciliation(
            data_root,
            invocation_id=invocation_id,
            controller_identity=controller,
            clock=service._clock,
        )
        service.cancel_invocation(
            invocation_id,
            invocation.identity_digest(),
            controller,
        )
    elif invocation.state in {InvocationState.DISPATCHING, InvocationState.UNCERTAIN}:
        task_record = records.read(f"controller-tasks/{attempt_id}.json", lambda stored: stored)
        workspace_root = Path(task_record["workspace_root"]).resolve()
        service.recover_invocation(
            invocation_id,
            invocation.identity_digest(),
            controller,
            workspace_root,
        )
        record_stop_reconciliation(
            data_root,
            invocation_id=invocation_id,
            controller_identity=controller,
            clock=service._clock,
        )
    elif invocation.state is InvocationState.ABORTED:
        record_stop_reconciliation(
            data_root,
            invocation_id=invocation_id,
            controller_identity=controller,
            clock=service._clock,
        )
    else:
        raise LabValidationError(
            "JOB_RECONCILIATION_REQUIRED",
            "active invocation cannot be conservatively reconciled",
        )

    block_active_reconciliation(
        data_root,
        job_id,
        controller_identity=controller,
        reservation_id=reservation_id,
        code="JOB_RECONCILED_INTERRUPTED",
        message="interrupted task has exact no-start/absence evidence and remains unaccepted",
        clock=service._clock,
    )
    return job_status(data_root, job_id)

