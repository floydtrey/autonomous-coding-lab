import json
import hashlib
import subprocess
from copy import deepcopy
from pathlib import Path

from worker_lab.cli import main
from tests.test_models import curriculum_mapping, exercise_mapping
from tests.test_policy import context_mapping, policy_mapping, role_mapping
from tests.test_test_catalog import catalog
from worker_lab.models import ExerciseRecord
from worker_lab.policy import ContextManifest, PolicyRecord, RoleRecord
from worker_lab.validation import attempt_task_digest


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_authority_fixture(tmp_path: Path, *, mismatched_context: bool = False) -> tuple[Path, Path]:
    lab = tmp_path / "lab"
    target = tmp_path / "target"
    (target / "record_ledger").mkdir(parents=True)
    (target / "README.md").write_text("instructions\n", encoding="utf-8")
    (target / "record_ledger" / "models.py").write_text("# model\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(target), "-c", "user.name=Worker Lab Tests",
         "-c", "user.email=worker-lab@example.invalid", "commit", "-q", "-m", "template"],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout.strip()
    exercise = exercise_mapping()
    exercise["template_commit"] = head
    context = context_mapping()
    context["starting_commit"] = "c" * 40 if mismatched_context else head
    for item in context["files"]:
        item["digest"] = "sha256:" + hashlib.sha256((target / item["path"]).read_bytes()).hexdigest()
    write_json(lab / "curricula" / "curricula" / "record-ledger.json", curriculum_mapping())
    write_json(lab / "curricula" / "exercises" / "record-model" / "v1.json", exercise)
    write_json(lab / "curricula" / "policies" / "core-worker-policy" / "v1.json", policy_mapping())
    write_json(lab / "curricula" / "roles" / "coding-worker" / "v1.json", role_mapping())
    write_json(lab / "curricula" / "contexts" / "record-model-context" / "v1.json", context)
    write_json(lab / "curricula" / "catalogs" / "worker-lab-v1.json", catalog().to_dict())
    return lab, target


def test_validate_definition_and_invalid_failure(tmp_path: Path, capsys) -> None:
    path = tmp_path / "curriculum.json"
    write_json(path, curriculum_mapping())
    assert main(["validate-definition", str(path)]) == 0
    assert capsys.readouterr().out.startswith("VALID sha256:")
    path.write_text("{}", encoding="utf-8")
    assert main(["validate-definition", str(path)]) == 2
    assert "ERROR RECORD_SCHEMA_INVALID" in capsys.readouterr().err


def test_list_curricula_does_not_create_missing_lab_root(tmp_path: Path, capsys) -> None:
    lab = tmp_path / "missing-lab"
    assert main(["--root", str(lab), "list-curricula"]) == 0
    assert capsys.readouterr().out == "\n"
    assert not lab.exists()


def test_definition_inspection_and_attempt_lifecycle(tmp_path: Path, capsys) -> None:
    lab, target = write_authority_fixture(tmp_path)
    assert main(["--root", str(lab), "list-curricula"]) == 0
    assert "record-ledger\tactive" in capsys.readouterr().out
    assert main(["--root", str(lab), "create-attempt", "--exercise", "record-model", "--version", "1", "--target-repository", str(target)]) == 0
    created = json.loads(capsys.readouterr().out)
    attempt_id = created["attempt_id"]
    assert created["state"] == "DRAFT"
    assert created["evaluator_catalog_version"] == "worker-lab-v1"
    assert created["evaluator_catalog_digest"] == catalog().digest()
    assert main(["--root", str(lab), "show-attempt", attempt_id]) == 0
    assert json.loads(capsys.readouterr().out)["attempt_id"] == attempt_id


def test_task_digest_changes_with_authority_inputs() -> None:
    exercise = ExerciseRecord.from_mapping(exercise_mapping())
    policy = PolicyRecord.from_mapping(policy_mapping())
    role = RoleRecord.from_mapping(role_mapping())
    context = ContextManifest.from_mapping(context_mapping())
    first = attempt_task_digest(exercise, policy, role, context, catalog())
    changed = exercise_mapping()
    changed["protected_paths"] = ["evaluator/changed.py"]
    second = attempt_task_digest(
        ExerciseRecord.from_mapping(changed), policy, role, context, catalog()
    )
    assert first != second

    changed_policy = policy_mapping()
    changed_policy["invariants"][0]["statement"] = "Changed permanent invariant."
    assert first != attempt_task_digest(
        exercise, PolicyRecord.from_mapping(changed_policy), role, context, catalog()
    )

    changed_role = role_mapping()
    changed_role["purpose"] = "Changed role purpose."
    assert first != attempt_task_digest(
        exercise, policy, RoleRecord.from_mapping(changed_role), context, catalog()
    )

    changed_context = deepcopy(context_mapping())
    changed_context["files"][0]["purpose"] = "Changed supplied context purpose."
    assert first != attempt_task_digest(
        exercise, policy, role, ContextManifest.from_mapping(changed_context), catalog()
    )

    changed_catalog = catalog().to_dict()
    changed_catalog["tests"][0]["purpose"] = "Changed evaluator purpose."
    from worker_lab.test_catalog import TestCatalog
    assert first != attempt_task_digest(
        exercise, policy, role, context, TestCatalog.from_mapping(changed_catalog)
    )


def test_create_attempt_fails_when_context_commit_differs(tmp_path: Path, capsys) -> None:
    lab, target = write_authority_fixture(tmp_path, mismatched_context=True)
    assert main(["--root", str(lab), "create-attempt", "--exercise", "record-model", "--version", "1", "--target-repository", str(target)]) == 2
    assert "ERROR ATTEMPT_CONTEXT_MISMATCH" in capsys.readouterr().err
    assert not (lab / "state").exists()


def test_create_attempt_rejects_dirty_target_before_state_write(tmp_path: Path, capsys) -> None:
    lab, target = write_authority_fixture(tmp_path)
    (target / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    assert main(["--root", str(lab), "create-attempt", "--exercise", "record-model", "--version", "1", "--target-repository", str(target)]) == 2
    assert "ERROR ATTEMPT_REPOSITORY_DIRTY" in capsys.readouterr().err
    assert not (lab / "state").exists()
