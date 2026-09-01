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
from .operator_control import ONE_TIME_CONFIRMATION, inspect_installation
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
    command = commands.add_parser("installation-status")
    command.set_defaults(handler=_service_installation_status)
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
    command = commands.add_parser("recover-invocation")
    command.add_argument("invocation_id")
    command.add_argument("--expected-identity-digest", required=True)
    command.add_argument("--controller", required=True)
    command.add_argument("--workspace-root", required=True, type=Path)
    command.set_defaults(handler=_service_recover_invocation)
    command = commands.add_parser("doctor")
    command.set_defaults(handler=_doctor)
    command = commands.add_parser("synthetic-read-only")
    command.add_argument("--run-directory", required=True, type=Path)
    command.add_argument("--controller", required=True)
    command.add_argument(
        "--authorize-once",
        required=True,
        metavar=ONE_TIME_CONFIRMATION,
        help="exact one-time confirmation phrase",
    )
    command.set_defaults(handler=_synthetic_read_only)
    command = commands.add_parser("recover-synthetic-read-only")
    command.add_argument("--run-directory", required=True, type=Path)
    command.add_argument("--controller", required=True)
    command.set_defaults(handler=_recover_synthetic_read_only)
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


def _service_installation_status(args: argparse.Namespace) -> str:
    return _service(args).installation_status().to_json()


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


def _service_recover_invocation(args: argparse.Namespace) -> str:
    return _service(args).recover_invocation(
        args.invocation_id,
        args.expected_identity_digest,
        args.controller,
        args.workspace_root.absolute(),
    ).to_json()


def _doctor(args: argparse.Namespace) -> str:
    del args
    _, report = inspect_installation()
    return report.to_json()


def _synthetic_read_only(args: argparse.Namespace) -> str:
    from .synthetic_read_only import run

    return run(
        args.run_directory,
        controller_identity=args.controller,
        authorization=args.authorize_once,
    )


def _recover_synthetic_read_only(args: argparse.Namespace) -> str:
    from .synthetic_read_only import recover

    return recover(args.run_directory, controller_identity=args.controller)


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
