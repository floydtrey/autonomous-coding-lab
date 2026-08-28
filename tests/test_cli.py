import json
import hashlib
import subprocess
from copy import deepcopy
from pathlib import Path

import worker_lab.cli as cli_module
from worker_lab.cli import main
from worker_lab.evidence import content_digest, evidence_identity_digest
from tests.test_models import curriculum_mapping, evidence_mapping, exercise_mapping
from tests.test_policy import context_mapping, policy_mapping, role_mapping
from tests.test_test_catalog import catalog
from worker_lab.models import EvidenceRecord, ExerciseRecord
from worker_lab.policy import ContextManifest, PolicyRecord, RoleRecord
from worker_lab.attempt_store import AttemptStore
from worker_lab.validation import attempt_task_digest
from worker_lab.workspace import prepare_workspace


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_authority_fixture(tmp_path: Path, *, mismatched_context: bool = False) -> tuple[Path, Path]:
    lab = tmp_path / "lab"
    target = tmp_path / "target"
    (target / "record_ledger").mkdir(parents=True)
    (target / "README.md").write_bytes(b"instructions\n")
    (target / "record_ledger" / "models.py").write_bytes(b"# model\n")
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


def test_verify_workspace_cli_returns_receipt_and_stable_failure(tmp_path: Path, capsys) -> None:
    lab, target = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    assert main([
        "--root", str(lab), "create-attempt", "--exercise", "record-model", "--version", "1",
        "--target-repository", str(target),
    ]) == 0
    attempt_id = json.loads(capsys.readouterr().out)["attempt_id"]
    prepare_workspace(
        lab, attempt_id, target, workspace_root,
        occurred_at=AttemptStore(lab / "state").read(attempt_id).updated_at,
    )

    assert main([
        "--root", str(lab), "verify-workspace", attempt_id,
        "--workspace-root", str(workspace_root),
    ]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "PREPARED"
    (workspace_root / attempt_id / "untracked.txt").write_text("changed\n", encoding="utf-8")
    assert main([
        "--root", str(lab), "verify-workspace", attempt_id,
        "--workspace-root", str(workspace_root),
    ]) == 2
    assert capsys.readouterr().err.startswith("ERROR WORKSPACE_VERIFY_FAILED:")


def test_discard_workspace_cli_aborts_and_removes_receipt(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    lab, target = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    assert main([
        "--root", str(lab), "create-attempt", "--exercise", "record-model", "--version", "1",
        "--target-repository", str(target),
    ]) == 0
    attempt_id = json.loads(capsys.readouterr().out)["attempt_id"]
    prepare_workspace(
        lab, attempt_id, target, workspace_root,
        occurred_at=AttemptStore(lab / "state").read(attempt_id).updated_at,
    )
    occurred_at = "2099-08-28T12:00:00Z"
    monkeypatch.setattr(cli_module, "_now", lambda: occurred_at)

    assert main([
        "--root", str(lab), "discard-workspace", attempt_id,
        "--workspace-root", str(workspace_root), "--cleanup-outcome", "operator disposal",
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["state"] == "ABORTED"
    assert result["updated_at"] == occurred_at
    assert not (workspace_root / attempt_id).exists()
    assert not (lab / "state" / "workspaces" / f"{attempt_id}.json").exists()


def test_generic_transition_cannot_bypass_receipt_bound_disposal(tmp_path: Path, capsys) -> None:
    lab, target = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    assert main([
        "--root", str(lab), "create-attempt", "--exercise", "record-model", "--version", "1",
        "--target-repository", str(target),
    ]) == 0
    attempt_id = json.loads(capsys.readouterr().out)["attempt_id"]
    prepare_workspace(
        lab,
        attempt_id,
        target,
        workspace_root,
        occurred_at=AttemptStore(lab / "state").read(attempt_id).updated_at,
    )

    assert main([
        "--root", str(lab), "transition-attempt", attempt_id, "ABORTED",
        "--cleanup-outcome", "bypass disposal",
    ]) == 2

    assert capsys.readouterr().err.startswith("ERROR ATTEMPT_WORKSPACE_DISPOSAL_REQUIRED:")
    assert AttemptStore(lab / "state").read(attempt_id).state.value == "READY"
    assert (workspace_root / attempt_id).is_dir()
    assert (lab / "state" / "workspaces" / f"{attempt_id}.json").is_file()


def test_discard_workspace_cli_uses_stable_failure_output(tmp_path: Path, capsys) -> None:
    lab, target = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    assert main([
        "--root", str(lab), "create-attempt", "--exercise", "record-model", "--version", "1",
        "--target-repository", str(target),
    ]) == 0
    attempt_id = json.loads(capsys.readouterr().out)["attempt_id"]

    assert main([
        "--root", str(lab), "discard-workspace", attempt_id,
        "--workspace-root", str(workspace_root), "--cleanup-outcome", "must fail",
    ]) == 2
    assert capsys.readouterr().err.startswith("ERROR WORKSPACE_DISPOSAL_STATE_INVALID:")


def test_complete_phase1_operator_workflow(tmp_path: Path, capsys) -> None:
    lab, target = write_authority_fixture(tmp_path)

    def succeed(arguments: list[str]) -> str:
        assert main(arguments) == 0
        captured = capsys.readouterr()
        assert captured.err == ""
        return captured.out

    curriculum_path = lab / "curricula" / "curricula" / "record-ledger.json"
    assert succeed(["validate-definition", str(curriculum_path)]).startswith("VALID sha256:")
    assert "record-ledger\tactive" in succeed(["--root", str(lab), "list-curricula"])
    assert json.loads(
        succeed(["--root", str(lab), "show-curriculum", "record-ledger"])
    )["curriculum_id"] == "record-ledger"
    assert json.loads(
        succeed([
            "--root", str(lab), "show-exercise", "record-model", "--version", "1",
        ])
    )["exercise_id"] == "record-model"

    created = json.loads(succeed([
        "--root", str(lab), "create-attempt", "--exercise", "record-model",
        "--version", "1", "--target-repository", str(target),
    ]))
    attempt_id = created["attempt_id"]
    candidate = "sha256:" + "c" * 64
    for state, extra in (
        ("READY", []),
        ("RUNNING", []),
        ("CANDIDATE", ["--candidate-digest", candidate]),
        ("EVALUATING", []),
    ):
        transitioned = json.loads(succeed([
            "--root", str(lab), "transition-attempt", attempt_id, state, *extra,
        ]))
        assert transitioned["state"] == state

    content = b'{"exit_code":0,"summary":"passed"}\n'
    retained_path = lab / "state" / "evidence-content" / "T005.json"
    retained_path.parent.mkdir(parents=True)
    retained_path.write_bytes(content)
    evidence = evidence_mapping()
    evidence.update({
        "attempt_id": attempt_id,
        "test_catalog_digest": created["evaluator_catalog_digest"],
        "candidate_digest": candidate,
        "base_commit": created["starting_commit"],
        "environment_digest": "sha256:" + "d" * 64,
        "content_path": "evidence-content/T005.json",
        "verification_state": "unverified",
    })
    provisional = EvidenceRecord.from_mapping(evidence)
    digest = evidence_identity_digest(provisional, content_digest(content))
    evidence["evidence_digest"] = digest
    write_json(
        lab / "state" / "evidence" / f"{digest.removeprefix('sha256:')}.json",
        evidence,
    )
    assert succeed(["--root", str(lab), "verify-evidence", digest]).strip() == (
        f"VERIFIED {digest}"
    )

    for state, extra in (
        ("PASSED", []),
        ("CLOSED", ["--cleanup-outcome", "workspace absent"]),
    ):
        transitioned = json.loads(succeed([
            "--root", str(lab), "transition-attempt", attempt_id, state, *extra,
        ]))
        assert transitioned["state"] == state

    backup = tmp_path / "backup"
    assert succeed(["--root", str(lab), "backup", str(backup)]).startswith("VERIFIED ")
    assert succeed(["verify-backup", str(backup)]).startswith("VERIFIED ")
    restored = tmp_path / "restored"
    assert succeed(["restore", str(backup), str(restored)]).startswith("VERIFIED ")
    restored_attempt = json.loads(
        succeed(["--root", str(restored), "show-attempt", attempt_id])
    )
    assert restored_attempt["state"] == "CLOSED"
    assert restored_attempt["candidate_digest"] == candidate
