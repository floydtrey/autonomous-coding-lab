from __future__ import annotations

import argparse
import json
import sys
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .backup import create_backup, restore_backup, verify_backup
from .attempt_store import AttemptStore
from .evidence import verify_evidence
from .errors import LabValidationError
from .lifecycle import transition_attempt
from .models import (
    ATTEMPT_SCHEMA, CURRICULUM_SCHEMA, EVIDENCE_SCHEMA, EXERCISE_SCHEMA, FAILURE_SCHEMA,
    AttemptRecord, AttemptState, CurriculumRecord, EvidenceRecord, ExerciseRecord, FailureRecord,
)
from .policy import (
    CONTEXT_MANIFEST_SCHEMA, POLICY_SCHEMA, ROLE_SCHEMA, ContextManifest, PolicyRecord,
    RoleRecord, validate_authority, verify_context_files,
)
from .storage import AtomicRecordStore
from .test_catalog import CATALOG_SCHEMA, TestCatalog
from .validation import attempt_task_digest
from .workspace import prepare_workspace


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
    command.set_defaults(handler=lambda args: _backup(args))
    command = commands.add_parser("verify-backup")
    command.add_argument("path", type=Path)
    command.set_defaults(handler=lambda args: _verified(verify_backup(args.path)))
    command = commands.add_parser("restore")
    command.add_argument("backup", type=Path)
    command.add_argument("destination", type=Path)
    command.set_defaults(handler=lambda args: _verified(restore_backup(args.backup, args.destination)))
    return parser


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
    definitions = _definitions(args)
    exercise = definitions.read(
        f"exercises/{args.exercise}/v{args.version}.json", ExerciseRecord.from_mapping
    )
    policy = definitions.read(
        f"policies/{exercise.policy_id}/v{exercise.policy_version}.json",
        PolicyRecord.from_mapping,
    )
    role = definitions.read(
        f"roles/{exercise.role_id}/v{exercise.role_version}.json", RoleRecord.from_mapping
    )
    context = definitions.read(
        f"contexts/{exercise.context_manifest_id}/v{exercise.context_manifest_version}.json",
        ContextManifest.from_mapping,
    )
    catalog = definitions.read(
        f"catalogs/{exercise.evaluator_catalog_version}.json", TestCatalog.from_mapping
    )
    _validate_attempt_authority(exercise, policy, role, context, catalog)
    _validate_target_repository(args.root, args.target_repository, exercise.template_commit)
    verify_context_files(context, args.target_repository)
    now = _now()
    identity = "ATTEMPT-" + uuid.uuid4().hex.upper()
    record = AttemptRecord.from_mapping({
        "schema_version": ATTEMPT_SCHEMA, "attempt_id": identity,
        "curriculum_id": exercise.curriculum_id, "exercise_id": exercise.exercise_id,
        "exercise_version": exercise.exercise_version, "starting_commit": exercise.template_commit,
        "context_digest": context.digest(),
        "task_digest": attempt_task_digest(exercise, policy, role, context, catalog),
        "policy_id": policy.policy_id, "policy_version": policy.policy_version,
        "policy_digest": policy.digest(),
        "role_id": role.role_id, "role_version": role.role_version,
        "role_digest": role.digest(), "sandbox_mode": exercise.sandbox_mode,
        "state": "DRAFT", "created_at": now, "updated_at": now,
        "evaluator_catalog_version": catalog.catalog_version,
        "evaluator_catalog_digest": catalog.digest(), "runtime_identity": None,
        "candidate_digest": None, "cleanup_outcome": None, "prior_attempt_id": None,
    })
    _attempts(args).create(record)
    return record.to_json(pretty=True)


def _validate_attempt_authority(
    exercise: ExerciseRecord,
    policy: PolicyRecord,
    role: RoleRecord,
    context: ContextManifest,
    catalog: TestCatalog,
) -> None:
    if (policy.policy_id, policy.policy_version) != (exercise.policy_id, exercise.policy_version):
        raise LabValidationError("ATTEMPT_POLICY_MISMATCH", "exercise policy identity is unresolved")
    if (role.role_id, role.role_version) != (exercise.role_id, exercise.role_version):
        raise LabValidationError("ATTEMPT_ROLE_MISMATCH", "exercise role identity is unresolved")
    if context.repository != exercise.template_repository or context.starting_commit != exercise.template_commit:
        raise LabValidationError(
            "ATTEMPT_CONTEXT_MISMATCH", "context repository or starting commit differs"
        )
    if catalog.catalog_version != exercise.evaluator_catalog_version:
        raise LabValidationError("ATTEMPT_CATALOG_MISMATCH", "evaluator catalog is unresolved")
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


def _validate_target_repository(lab_root: Path, target_repository: Path, expected_head: str) -> None:
    if target_repository.is_symlink():
        raise LabValidationError(
            "ATTEMPT_REPOSITORY_INVALID", "target repository cannot be a symlink"
        )
    try:
        target = target_repository.resolve(strict=True)
        lab = lab_root.resolve(strict=True)
    except OSError as exc:
        raise LabValidationError("ATTEMPT_REPOSITORY_INVALID", "repository path is missing") from exc
    if target == lab or target.is_relative_to(lab) or lab.is_relative_to(target):
        raise LabValidationError(
            "ATTEMPT_REPOSITORY_INVALID", "worker target must be separate from Worker Lab"
        )
    try:
        head = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True, encoding="utf-8",
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(target), "status", "--porcelain=v1"],
            check=True, capture_output=True, text=True, encoding="utf-8",
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise LabValidationError("ATTEMPT_REPOSITORY_INVALID", "target is not a readable Git repository") from exc
    if head != expected_head:
        raise LabValidationError("ATTEMPT_HEAD_MISMATCH", "target HEAD differs from exercise identity")
    if dirty:
        raise LabValidationError("ATTEMPT_REPOSITORY_DIRTY", "target repository must be clean")


def _show_attempt(args: argparse.Namespace) -> str:
    return _attempts(args).read(args.attempt_id).to_json(pretty=True)


def _prepare_workspace(args: argparse.Namespace) -> str:
    return prepare_workspace(
        args.root,
        args.attempt_id,
        args.template_repository,
        args.workspace_root,
        occurred_at=_now(),
    ).to_json(pretty=True)


def _transition_attempt(args: argparse.Namespace) -> str:
    store = _attempts(args)
    current = store.read(args.attempt_id)
    updated = transition_attempt(current, AttemptState(args.state), occurred_at=_now(), candidate_digest=args.candidate_digest, cleanup_outcome=args.cleanup_outcome)
    store.save_transition(updated)
    return updated.to_json(pretty=True)


def _verify_evidence(args: argparse.Namespace) -> str:
    record = verify_evidence(args.root, args.digest)
    return f"VERIFIED {record.evidence_digest}"


def _backup(args: argparse.Namespace) -> str:
    return _verified(create_backup(args.root, args.destination))


def _verified(manifest: Any) -> str:
    return f"VERIFIED {len(manifest.files)} files"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
