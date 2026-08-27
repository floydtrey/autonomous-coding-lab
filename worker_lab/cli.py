from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .backup import create_backup, restore_backup, verify_backup
from .canonical import canonical_digest
from .errors import LabValidationError
from .lifecycle import transition_attempt
from .models import (
    ATTEMPT_SCHEMA, CURRICULUM_SCHEMA, EVIDENCE_SCHEMA, EXERCISE_SCHEMA, FAILURE_SCHEMA,
    AttemptRecord, AttemptState, CurriculumRecord, EvidenceRecord, ExerciseRecord, FailureRecord,
)
from .storage import AtomicRecordStore


LOADERS: dict[str, Callable[[Any], Any]] = {
    CURRICULUM_SCHEMA: CurriculumRecord.from_mapping,
    EXERCISE_SCHEMA: ExerciseRecord.from_mapping,
    ATTEMPT_SCHEMA: AttemptRecord.from_mapping,
    EVIDENCE_SCHEMA: EvidenceRecord.from_mapping,
    FAILURE_SCHEMA: FailureRecord.from_mapping,
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
    command.set_defaults(handler=_create_attempt)
    command = commands.add_parser("show-attempt")
    command.add_argument("attempt_id")
    command.set_defaults(handler=_show_attempt)
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
    exercise = _definitions(args).read(
        f"exercises/{args.exercise}/v{args.version}.json", ExerciseRecord.from_mapping
    )
    now = _now()
    identity = "ATTEMPT-" + uuid.uuid4().hex.upper()
    record = AttemptRecord.from_mapping({
        "schema_version": ATTEMPT_SCHEMA, "attempt_id": identity,
        "curriculum_id": exercise.curriculum_id, "exercise_id": exercise.exercise_id,
        "exercise_version": exercise.exercise_version, "starting_commit": exercise.template_commit,
        "context_digest": canonical_digest(exercise.to_dict()),
        "task_digest": canonical_digest({"objective": exercise.objective, "acceptance_criteria": list(exercise.acceptance_criteria)}),
        "state": "DRAFT", "created_at": now, "updated_at": now,
        "evaluator_catalog_version": "unresolved", "runtime_identity": None,
        "candidate_digest": None, "cleanup_outcome": None, "prior_attempt_id": None,
    })
    _state(args).write(f"attempts/{identity}.json", record)
    return record.to_json(pretty=True)


def _show_attempt(args: argparse.Namespace) -> str:
    return _state(args).read(f"attempts/{args.attempt_id}.json", AttemptRecord.from_mapping).to_json(pretty=True)


def _transition_attempt(args: argparse.Namespace) -> str:
    store = _state(args)
    path = f"attempts/{args.attempt_id}.json"
    current = store.read(path, AttemptRecord.from_mapping)
    updated = transition_attempt(current, AttemptState(args.state), occurred_at=_now(), candidate_digest=args.candidate_digest, cleanup_outcome=args.cleanup_outcome)
    store.write(path, updated)
    return updated.to_json(pretty=True)


def _verify_evidence(args: argparse.Namespace) -> str:
    key = args.digest.removeprefix("sha256:")
    record = _state(args).read(f"evidence/{key}.json", EvidenceRecord.from_mapping)
    if record.evidence_digest != args.digest:
        raise LabValidationError("EVIDENCE_IDENTITY_MISMATCH", "requested digest differs from record")
    return f"VERIFIED {record.evidence_digest}"


def _backup(args: argparse.Namespace) -> str:
    return _verified(create_backup(args.root, args.destination))


def _verified(manifest: Any) -> str:
    return f"VERIFIED {len(manifest.files)} files"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
