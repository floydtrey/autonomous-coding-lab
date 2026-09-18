from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .application_service import COLLECTIONS, WorkerLabApplicationService
from .attempt_store import AttemptStore
from .evidence import verify_evidence
from .errors import LabValidationError
from .models import (
    ATTEMPT_SCHEMA, CURRICULUM_SCHEMA, EVIDENCE_SCHEMA, EXERCISE_SCHEMA, FAILURE_SCHEMA,
    AttemptRecord, AttemptState, CurriculumRecord, EvidenceRecord, ExerciseRecord, FailureRecord,
)
from .operator_control import inspect_source_identity
from .policy import (
    CONTEXT_MANIFEST_SCHEMA, POLICY_SCHEMA, ROLE_SCHEMA, ContextManifest, PolicyRecord,
    RoleRecord,
)
from .storage import AtomicRecordStore
from .test_catalog import CATALOG_SCHEMA, TestCatalog


LOADERS: dict[str, Callable[[Any], Any]] = {
    CURRICULUM_SCHEMA: CurriculumRecord.from_mapping,
    EXERCISE_SCHEMA: ExerciseRecord.from_mapping,
    ATTEMPT_SCHEMA: AttemptRecord.from_mapping,
    EVIDENCE_SCHEMA: EvidenceRecord.from_mapping,
    FAILURE_SCHEMA: FailureRecord.from_mapping,
    POLICY_SCHEMA: PolicyRecord.from_mapping,
    ROLE_SCHEMA: RoleRecord.from_mapping,
    CONTEXT_MANIFEST_SCHEMA: ContextManifest.from_mapping,
    CATALOG_SCHEMA: TestCatalog.from_mapping,
}


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = args.handler(args)
        if result is not None:
            print(result)
        return 0
    except LabValidationError as exc:
        print(f"ERROR {exc.code}: {exc.summary}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR OPERATION_FAILED: {exc}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="worker-lab")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(required=True)
    command = commands.add_parser("health")
    command.set_defaults(handler=_service_health)
    command = commands.add_parser("source-status")
    command.set_defaults(handler=_service_source_status)
    command = commands.add_parser("list-records")
    command.add_argument("collection", choices=COLLECTIONS)
    command.set_defaults(handler=_service_list_records)
    command = commands.add_parser("show-record")
    command.add_argument("collection", choices=COLLECTIONS)
    command.add_argument("identity")
    command.set_defaults(handler=_service_show_record)
    command = commands.add_parser("show-attempt-timeline")
    command.add_argument("attempt_id")
    command.set_defaults(handler=_service_show_attempt_timeline)
    command = commands.add_parser("review-candidate")
    command.add_argument("attempt_id")
    command.set_defaults(handler=_service_review_candidate)
    command = commands.add_parser("prepare-invocation")
    command.add_argument("attempt_id")
    command.add_argument("--workspace-root", required=True, type=Path)
    command.add_argument("--prompt-file", required=True, type=Path)
    command.add_argument("--logical-target-id", required=True)
    command.add_argument("--provider-binding-id", required=True)
    command.add_argument("--provider-binding-digest", required=True)
    command.set_defaults(handler=_service_prepare_invocation)
    command = commands.add_parser("authorize-invocation")
    command.add_argument("invocation_id")
    command.add_argument("--expected-identity-digest", required=True)
    command.add_argument("--controller", required=True)
    command.set_defaults(handler=_service_authorize_invocation)
    command = commands.add_parser("reject-invocation")
    command.add_argument("invocation_id")
    command.add_argument("--expected-identity-digest", required=True)
    command.set_defaults(handler=_service_reject_invocation)
    command = commands.add_parser("cancel-invocation")
    command.add_argument("invocation_id")
    command.add_argument("--expected-identity-digest", required=True)
    command.add_argument("--controller", required=True)
    command.set_defaults(handler=_service_cancel_invocation)
    command = commands.add_parser("approve-validation", help="explicitly approve named local checks as unsandboxed host code")
    command.add_argument("attempt_id")
    command.add_argument("--expected-outcome-digest", required=True)
    command.add_argument("--controller", required=True)
    command.add_argument("--protected-file", required=True, type=Path, action="append")
    command.add_argument("--acknowledge-unsandboxed-host-code-execution", action="store_true")
    command.add_argument("--timeout-seconds", type=int, default=30)
    command.add_argument("--output-limit-bytes", type=int, default=1048576)
    command.add_argument("--cleanup-timeout-seconds", type=int, default=5)
    command.set_defaults(handler=_service_approve_validation)
    command = commands.add_parser("validate-task", help="run the approved protected checks; no acceptance")
    command.add_argument("attempt_id")
    command.add_argument("--expected-outcome-digest", required=True)
    command.add_argument("--controller", required=True)
    command.add_argument("--validation-id", required=True)
    command.set_defaults(handler=_service_validate_task)
    command = commands.add_parser("approve-task-execution", help="approve this task's exact named local checks before execution")
    command.add_argument("task_file", type=Path)
    command.add_argument("--controller", required=True)
    command.add_argument("--protected-file", required=True, type=Path, action="append")
    command.add_argument("--acknowledge-unsandboxed-host-code-execution", action="store_true")
    command.add_argument("--review-required", action="store_true")
    command.add_argument("--timeout-seconds", type=int, default=30)
    command.add_argument("--output-limit-bytes", type=int, default=1048576)
    command.add_argument("--cleanup-timeout-seconds", type=int, default=5)
    command.set_defaults(handler=_service_approve_task_execution)
    command = commands.add_parser("accept-task", help="verify durable worker/check evidence and record acceptance")
    command.add_argument("attempt_id")
    command.add_argument("--expected-outcome-digest", required=True)
    command.add_argument("--controller", required=True)
    command.add_argument("--validation-id", required=True)
    command.add_argument("--expected-validation-digest", required=True)
    command.add_argument("--review-id")
    command.set_defaults(handler=_service_accept_task)
    command = commands.add_parser("record-task-review", help="record an explicit review of exact candidate and check evidence")
    command.add_argument("attempt_id")
    command.add_argument("--expected-outcome-digest", required=True)
    command.add_argument("--controller", required=True)
    command.add_argument("--validation-id", required=True)
    command.add_argument("--expected-validation-digest", required=True)
    command.add_argument("--review-id", required=True)
    command.add_argument("--reviewer", required=True)
    command.add_argument("--decision", choices=('approved','rejected'), required=True)
    command.set_defaults(handler=_service_record_task_review)
    command = commands.add_parser("run", help="run one approved job sequentially through the existing task workflow")
    command.add_argument("plan_file", type=Path)
    command.add_argument("--job-id")
    command.add_argument("--approved-plan-digest", required=True)
    command.add_argument("--controller", required=True)
    command.add_argument("--target-repository", required=True, type=Path)
    command.add_argument("--workspace-root", required=True, type=Path)
    command.add_argument("--artifact-root", required=True, type=Path)
    command.add_argument("--provider-binding-id", required=True)
    command.add_argument("--protected-file", required=True, type=Path, action="append")
    command.add_argument("--acknowledge-unsandboxed-host-code-execution", action="store_true")
    command.add_argument("--review-required", action="store_true")
    command.add_argument("--timeout-seconds", type=int, default=30)
    command.add_argument("--output-limit-bytes", type=int, default=1048576)
    command.add_argument("--cleanup-timeout-seconds", type=int, default=5)
    command.add_argument("--candidate-archive-limit-bytes", type=int,
        help="full candidate ZIP budget in uncompressed bytes (default 33554432; zero omits ZIP)")
    command.set_defaults(handler=_service_run_job)
    command = commands.add_parser("status", help="show the durable read-only status for one job")
    command.add_argument("job_id")
    command.set_defaults(handler=_service_job_status)
    command = commands.add_parser("stop", help="request stop for the exact active job reservation")
    command.add_argument("job_id")
    command.add_argument("--controller", required=True)
    command.set_defaults(handler=_service_stop_job)
    command = commands.add_parser("reconcile", help="finish only provable job bookkeeping without launching replacement work")
    command.add_argument("job_id")
    command.add_argument("--controller", required=True)
    command.add_argument("--artifact-root", type=Path)
    command.set_defaults(handler=_service_reconcile_job)
    command = commands.add_parser("run-task", help="run one explicitly approved task through worker, checks and acceptance")
    command.add_argument("task_file", type=Path)
    command.add_argument("--review-id")
    command.add_argument("--candidate-archive-limit-bytes", type=int,
        help="full candidate ZIP budget in uncompressed bytes (default 33554432; zero omits ZIP)")
    command.set_defaults(handler=_service_run_task)
    command = commands.add_parser("dispatch-invocation")
    command.add_argument("invocation_id")
    command.add_argument("--expected-identity-digest", required=True)
    command.add_argument("--controller", required=True)
    command.add_argument("--workspace-root", required=True, type=Path)
    command.set_defaults(handler=_service_dispatch_invocation)
    command = commands.add_parser("recover-invocation")
    command.add_argument("invocation_id")
    command.add_argument("--expected-identity-digest", required=True)
    command.add_argument("--controller", required=True)
    command.add_argument("--workspace-root", required=True, type=Path)
    command.set_defaults(handler=_service_recover_invocation)
    command = commands.add_parser("doctor")
    command.set_defaults(handler=_doctor)
    command = commands.add_parser("validate-definition")
    command.add_argument("path", type=Path)
    command.set_defaults(handler=_validate_definition)
    command = commands.add_parser("list-curricula")
    command.set_defaults(handler=_list_curricula)
    command = commands.add_parser("show-curriculum")
    command.add_argument("curriculum_id")
    command.set_defaults(handler=_show_curriculum)
    command = commands.add_parser("show-exercise")
    command.add_argument("exercise_id")
    command.add_argument("--version", required=True, type=int)
    command.set_defaults(handler=_show_exercise)
    command = commands.add_parser("create-attempt")
    command.add_argument("--exercise", required=True)
    command.add_argument("--version", required=True, type=int)
    command.add_argument("--target-repository", required=True, type=Path)
    command.set_defaults(handler=_create_attempt)
    command = commands.add_parser("show-attempt")
    command.add_argument("attempt_id")
    command.set_defaults(handler=_show_attempt)
    command = commands.add_parser("prepare-workspace")
    command.add_argument("attempt_id")
    command.add_argument("--template-repository", required=True, type=Path)
    command.add_argument("--workspace-root", required=True, type=Path)
    command.set_defaults(handler=_prepare_workspace)
    command = commands.add_parser("verify-workspace")
    command.add_argument("attempt_id")
    command.add_argument("--workspace-root", required=True, type=Path)
    command.set_defaults(handler=_verify_workspace)
    command = commands.add_parser("discard-workspace")
    command.add_argument("attempt_id")
    command.add_argument("--workspace-root", required=True, type=Path)
    command.add_argument("--cleanup-outcome", required=True)
    command.set_defaults(handler=_discard_workspace)
    command = commands.add_parser("transition-attempt")
    command.add_argument("attempt_id")
    command.add_argument("state", choices=[str(state) for state in AttemptState])
    command.add_argument("--candidate-digest")
    command.add_argument("--cleanup-outcome")
    command.set_defaults(handler=_transition_attempt)
    command = commands.add_parser("verify-evidence")
    command.add_argument("digest")
    command.set_defaults(handler=_verify_evidence)
    command = commands.add_parser("backup")
    command.add_argument("destination", type=Path)
    command.set_defaults(handler=_service_create_backup)
    command = commands.add_parser("verify-backup")
    command.add_argument("path", type=Path)
    command.set_defaults(handler=_service_verify_backup)
    command = commands.add_parser("restore")
    command.add_argument("backup", type=Path)
    command.add_argument("destination", type=Path)
    command.set_defaults(handler=_service_restore_backup)
    return parser


def _service(args: argparse.Namespace) -> WorkerLabApplicationService:
    return WorkerLabApplicationService(args.root.absolute(), clock=_now)


def _service_health(args: argparse.Namespace) -> str:
    return _service(args).health().to_json()


def _service_source_status(args: argparse.Namespace) -> str:
    return _service(args).source_status().to_json()


def _service_list_records(args: argparse.Namespace) -> str:
    return _service(args).list_records(args.collection).to_json()


def _service_show_record(args: argparse.Namespace) -> str:
    return _service(args).show_record(args.collection, args.identity).to_json()


def _service_show_attempt_timeline(args: argparse.Namespace) -> str:
    return _service(args).show_attempt_timeline(args.attempt_id).to_json()


def _service_review_candidate(args: argparse.Namespace) -> str:
    return _service(args).review_candidate(args.attempt_id).to_json()


def _service_prepare_invocation(args: argparse.Namespace) -> str:
    prompt = args.prompt_file.read_text(encoding="utf-8")
    return _service(args).prepare_invocation(
        args.attempt_id,
        args.workspace_root,
        prompt,
        logical_target_id=args.logical_target_id,
        provider_binding_id=args.provider_binding_id,
        provider_binding_digest=args.provider_binding_digest,
    ).to_json()


def _service_authorize_invocation(args: argparse.Namespace) -> str:
    return _service(args).authorize_invocation(
        args.invocation_id,
        args.expected_identity_digest,
        args.controller,
    ).to_json()


def _service_reject_invocation(args: argparse.Namespace) -> str:
    return _service(args).reject_invocation(
        args.invocation_id,
        args.expected_identity_digest,
    ).to_json()


def _service_cancel_invocation(args: argparse.Namespace) -> str:
    return _service(args).cancel_invocation(
        args.invocation_id,
        args.expected_identity_digest,
        args.controller,
    ).to_json()


def _service_approve_validation(args: argparse.Namespace) -> str:
    return _service(args).approve_local_validation(args.attempt_id, args.expected_outcome_digest,
        args.controller, protected_files=args.protected_file,
        acknowledge_unsandboxed=args.acknowledge_unsandboxed_host_code_execution,
        timeout_seconds=args.timeout_seconds, output_limit_bytes=args.output_limit_bytes,
        cleanup_timeout_seconds=args.cleanup_timeout_seconds).to_json()


def _service_validate_task(args: argparse.Namespace) -> str:
    return _service(args).validate_task(args.attempt_id, args.expected_outcome_digest,
        args.controller, args.validation_id).to_json()


def _service_run_job(args: argparse.Namespace) -> str:
    from .job_plan import JobPlan
    plan = JobPlan.from_mapping(json.loads(args.plan_file.resolve().read_text(encoding="utf-8")))
    return _service(args).run_job(
        args.job_id or plan.plan_id,
        plan,
        approved_plan_digest=args.approved_plan_digest,
        controller_identity=args.controller,
        target_repository=args.target_repository.resolve(),
        workspace_root=args.workspace_root.resolve(),
        artifact_root=args.artifact_root.resolve(),
        provider_binding_id=args.provider_binding_id,
        protected_files=tuple(path.resolve() for path in args.protected_file),
        acknowledge_unsandboxed=args.acknowledge_unsandboxed_host_code_execution,
        review_required=args.review_required,
        validation_timeout_seconds=args.timeout_seconds,
        validation_output_limit_bytes=args.output_limit_bytes,
        validation_cleanup_timeout_seconds=args.cleanup_timeout_seconds,
        candidate_archive_limit_bytes=args.candidate_archive_limit_bytes,
    ).to_json()


def _service_job_status(args: argparse.Namespace) -> str:
    return _service(args).job_status(args.job_id).to_json()


def _service_stop_job(args: argparse.Namespace) -> str:
    return _service(args).stop_job(
        args.job_id,
        controller_identity=args.controller,
    ).to_json()


def _service_reconcile_job(args: argparse.Namespace) -> str:
    return _service(args).reconcile_job(
        args.job_id,
        controller_identity=args.controller,
        artifact_root=None if args.artifact_root is None else args.artifact_root.resolve(),
    ).to_json()


def _service_run_task(args: argparse.Namespace) -> str:
    return _service(args).run_task(args.task_file.resolve(),
        candidate_archive_limit_bytes=args.candidate_archive_limit_bytes, review_id=args.review_id).to_json()


def _service_approve_task_execution(args):
    return _service(args).approve_task_execution(args.task_file.resolve(), args.controller,
        protected_files=args.protected_file,
        acknowledge_unsandboxed=args.acknowledge_unsandboxed_host_code_execution,
        review_required=args.review_required, timeout_seconds=args.timeout_seconds,
        output_limit_bytes=args.output_limit_bytes, cleanup_timeout_seconds=args.cleanup_timeout_seconds).to_json()


def _service_accept_task(args):
    return _service(args).accept_task(args.attempt_id, args.expected_outcome_digest, args.controller,
        args.validation_id, expected_validation_digest=args.expected_validation_digest,
        review_id=args.review_id).to_json()


def _service_record_task_review(args):
    return _service(args).record_task_review(args.attempt_id, args.expected_outcome_digest, args.controller,
        args.validation_id, args.expected_validation_digest, reviewer_identity=args.reviewer,
        review_id=args.review_id, decision=args.decision).to_json()


def _service_dispatch_invocation(args: argparse.Namespace) -> str:
    return _service(args).dispatch_invocation(
        args.invocation_id,
        args.expected_identity_digest,
        args.controller,
        args.workspace_root.absolute(),
    ).to_json()


def _service_recover_invocation(args: argparse.Namespace) -> str:
    return _service(args).recover_invocation(
        args.invocation_id,
        args.expected_identity_digest,
        args.controller,
        args.workspace_root.absolute(),
    ).to_json()


def _doctor(args: argparse.Namespace) -> str:
    del args
    _, report = inspect_source_identity()
    return report.to_json()






def _validate_definition(args: argparse.Namespace) -> str:
    value = json.loads(args.path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") not in LOADERS:
        raise LabValidationError("RECORD_SCHEMA_INVALID", "unknown definition schema")
    record = LOADERS[value["schema_version"]](value)
    return f"VALID {record.digest()}"


def _definitions(args: argparse.Namespace) -> AtomicRecordStore:
    return AtomicRecordStore(args.root / "curricula")


def _state(args: argparse.Namespace) -> AtomicRecordStore:
    return AtomicRecordStore(args.root / "state")


def _attempts(args: argparse.Namespace) -> AttemptStore:
    return AttemptStore(args.root / "state")


def _list_curricula(args: argparse.Namespace) -> str:
    store = _definitions(args)
    records = [store.read(path, CurriculumRecord.from_mapping) for path in store.list_paths("curricula")]
    return "\n".join(f"{item.curriculum_id}\t{item.status}\t{item.title}" for item in records)


def _show_curriculum(args: argparse.Namespace) -> str:
    return _definitions(args).read(
        f"curricula/{args.curriculum_id}.json", CurriculumRecord.from_mapping
    ).to_json(pretty=True)


def _show_exercise(args: argparse.Namespace) -> str:
    return _definitions(args).read(
        f"exercises/{args.exercise_id}/v{args.version}.json", ExerciseRecord.from_mapping
    ).to_json(pretty=True)


def _create_attempt(args: argparse.Namespace) -> str:
    return _service(args).create_attempt(
        args.exercise,
        args.version,
        args.target_repository,
    ).record_json()


def _show_attempt(args: argparse.Namespace) -> str:
    return _attempts(args).read(args.attempt_id).to_json(pretty=True)


def _prepare_workspace(args: argparse.Namespace) -> str:
    return _service(args).prepare_workspace(
        args.attempt_id,
        args.template_repository,
        args.workspace_root,
    ).record_json()


def _verify_workspace(args: argparse.Namespace) -> str:
    return _service(args).verify_workspace(
        args.attempt_id,
        args.workspace_root,
    ).record_json()


def _discard_workspace(args: argparse.Namespace) -> str:
    return _service(args).discard_workspace(
        args.attempt_id,
        args.workspace_root,
        args.cleanup_outcome,
    ).record_json()


def _transition_attempt(args: argparse.Namespace) -> str:
    return _service(args).transition_attempt(
        args.attempt_id,
        args.state,
        candidate_digest=args.candidate_digest,
        cleanup_outcome=args.cleanup_outcome,
    ).record_json()


def _verify_evidence(args: argparse.Namespace) -> str:
    record = verify_evidence(args.root, args.digest)
    return f"VERIFIED {record.evidence_digest}"


def _service_create_backup(args: argparse.Namespace) -> str:
    return _verified(_service(args).create_backup(args.destination.absolute()))


def _service_verify_backup(args: argparse.Namespace) -> str:
    return _verified(_service(args).verify_backup(args.path.absolute()))


def _service_restore_backup(args: argparse.Namespace) -> str:
    return _verified(
        _service(args).restore_backup(args.backup.absolute(), args.destination.absolute())
    )


def _verified(result: Any) -> str:
    return f"VERIFIED {result.to_dict()['file_count']} files"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
