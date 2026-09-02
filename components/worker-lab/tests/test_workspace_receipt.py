from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.test_cli import write_authority_fixture, write_json
from worker_lab.attempt_store import AttemptStore
from worker_lab.cli import main
from worker_lab.errors import LabValidationError
from worker_lab.lifecycle import transition_attempt
from tests.test_models import workspace_receipt_mapping
from worker_lab.models import AttemptState, WorkspaceReceipt, WorkspaceReceiptState
from worker_lab.storage import AtomicRecordStore
import worker_lab.workspace as workspace_module
from worker_lab.workspace import (
    _git,
    _git_environment,
    _quarantined_receipt,
    canonical_path_digest,
    discard_workspace,
    prepare_workspace,
    verify_workspace,
)


def _git_value(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _create_draft(lab: Path, template: Path, capsys) -> str:
    assert main([
        "--root", str(lab), "create-attempt",
        "--exercise", "record-model", "--version", "1",
        "--target-repository", str(template),
    ]) == 0
    return json.loads(capsys.readouterr().out)["attempt_id"]


def _assert_no_published_state(lab: Path, workspace_root: Path, attempt_id: str) -> None:
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.DRAFT
    assert not (workspace_root / attempt_id).exists()
    assert not (lab / "state" / "workspaces" / f"{attempt_id}.json").exists()
    if workspace_root.exists():
        assert not list(workspace_root.glob(".wl-stage-*"))


def _prepare(lab: Path, attempt_id: str, template: Path, workspace_root: Path):
    occurred_at = AttemptStore(lab / "state").read(attempt_id).updated_at
    return prepare_workspace(
        lab, attempt_id, template, workspace_root, occurred_at=occurred_at
    )


def _prepared_workspace(tmp_path: Path, capsys) -> tuple[Path, Path, Path, str, Path]:
    lab, template = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    attempt_id = _create_draft(lab, template, capsys)
    _prepare(lab, attempt_id, template, workspace_root)
    return lab, template, workspace_root, attempt_id, workspace_root / attempt_id


def _next_attempt_timestamp(lab: Path, attempt_id: str) -> str:
    current = AttemptStore(lab / "state").read(attempt_id).updated_at
    instant = datetime.fromisoformat(current.replace("Z", "+00:00")) + timedelta(seconds=1)
    return instant.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _discard(lab: Path, attempt_id: str, workspace_root: Path, outcome: str):
    return discard_workspace(
        lab,
        attempt_id,
        workspace_root,
        outcome,
        occurred_at=_next_attempt_timestamp(lab, attempt_id),
    )


def _workspace_snapshot(workspace: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(sorted(
        (path.relative_to(workspace).as_posix(), path.read_bytes())
        for path in workspace.rglob("*")
        if path.is_file()
    ))


def _verification_snapshot(
    lab: Path, workspace_root: Path, attempt_id: str
) -> tuple[bytes, bytes, tuple[tuple[str, bytes], ...]]:
    return (
        (lab / "state" / "attempts" / f"{attempt_id}.json").read_bytes(),
        (lab / "state" / "workspaces" / f"{attempt_id}.json").read_bytes(),
        _workspace_snapshot(workspace_root / attempt_id),
    )


def _assert_verification_preserved(
    lab: Path,
    workspace_root: Path,
    attempt_id: str,
    before: tuple[bytes, bytes, tuple[tuple[str, bytes], ...]],
) -> None:
    assert _verification_snapshot(lab, workspace_root, attempt_id) == before
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.READY
    receipt = AtomicRecordStore(lab / "state").read(
        f"workspaces/{attempt_id}.json", WorkspaceReceipt.from_mapping
    )
    assert receipt.state is WorkspaceReceiptState.PREPARED


def _quarantine_receipt(lab: Path, workspace_root: Path, attempt_id: str) -> Path:
    workspace = workspace_root / attempt_id
    quarantine = workspace_root / f".worker-lab-quarantine-{attempt_id}"
    shutil.move(str(workspace), str(quarantine))
    store = AtomicRecordStore(lab / "state")
    receipt = store.read(f"workspaces/{attempt_id}.json", WorkspaceReceipt.from_mapping)
    store.write(f"workspaces/{attempt_id}.json", _quarantined_receipt(receipt, quarantine))
    return quarantine


def test_discard_workspace_quarantines_deletes_and_aborts(tmp_path: Path, capsys) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    receipt_path = lab / "state" / "workspaces" / f"{attempt_id}.json"

    occurred_at = _next_attempt_timestamp(lab, attempt_id)
    discarded = discard_workspace(
        lab,
        attempt_id,
        workspace_root,
        "disposed by operator",
        occurred_at=occurred_at,
    )

    assert discarded.state is AttemptState.ABORTED
    assert discarded.cleanup_outcome == "disposed by operator"
    assert discarded.updated_at == occurred_at
    assert not workspace.exists()
    assert not (workspace_root / f".worker-lab-quarantine-{attempt_id}").exists()
    assert not receipt_path.exists()
    assert AttemptStore(lab / "state").read(attempt_id) == discarded


def test_discard_workspace_recovers_interrupted_rename(tmp_path: Path, capsys) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    quarantine = workspace_root / f".worker-lab-quarantine-{attempt_id}"
    shutil.move(str(workspace), str(quarantine))

    discarded = _discard(lab, attempt_id, workspace_root, "resumed disposal")

    assert discarded.state is AttemptState.ABORTED
    assert not quarantine.exists()
    assert not (lab / "state" / "workspaces" / f"{attempt_id}.json").exists()


def test_discard_workspace_recovers_quarantined_deletion_and_transition(
    tmp_path: Path, capsys
) -> None:
    lab, _, workspace_root, attempt_id, _ = _prepared_workspace(tmp_path / "deletion-complete", capsys)
    quarantine = _quarantine_receipt(lab, workspace_root, attempt_id)
    assert _discard(lab, attempt_id, workspace_root, "resumed deletion").state is AttemptState.ABORTED
    assert not quarantine.exists()

    lab, _, workspace_root, attempt_id, _ = _prepared_workspace(tmp_path, capsys)
    quarantine = _quarantine_receipt(lab, workspace_root, attempt_id)
    workspace_module._remove_tree(quarantine)
    assert _discard(lab, attempt_id, workspace_root, "completed before restart").state is AttemptState.ABORTED
    assert not (lab / "state" / "workspaces" / f"{attempt_id}.json").exists()


def test_discard_workspace_retains_quarantined_receipt_when_transition_fails(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    lab, _, workspace_root, attempt_id, _ = _prepared_workspace(tmp_path, capsys)

    def reject_transition(self, record):
        raise LabValidationError("TEST_TRANSITION_FAILURE", "injected failure")

    monkeypatch.setattr(AttemptStore, "save_transition", reject_transition)
    with pytest.raises(LabValidationError) as error:
        _discard(lab, attempt_id, workspace_root, "cannot persist")

    assert error.value.code == "TEST_TRANSITION_FAILURE"
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.READY
    receipt = AtomicRecordStore(lab / "state").read(
        f"workspaces/{attempt_id}.json", WorkspaceReceipt.from_mapping
    )
    assert receipt.state is WorkspaceReceiptState.QUARANTINED
    assert not (workspace_root / attempt_id).exists()
    assert not (workspace_root / f".worker-lab-quarantine-{attempt_id}").exists()


def test_discard_workspace_is_idempotent_after_complete(tmp_path: Path, capsys) -> None:
    lab, _, workspace_root, attempt_id, _ = _prepared_workspace(tmp_path, capsys)
    completed = _discard(lab, attempt_id, workspace_root, "completed once")
    attempt_path = lab / "state" / "attempts" / f"{attempt_id}.json"
    before = attempt_path.read_bytes()

    repeated = _discard(lab, attempt_id, workspace_root, "completed once")

    assert repeated == completed
    assert attempt_path.read_bytes() == before
    assert not (lab / "state" / "workspaces" / f"{attempt_id}.json").exists()
    assert not (workspace_root / attempt_id).exists()
    assert not (workspace_root / f".worker-lab-quarantine-{attempt_id}").exists()

    with pytest.raises(LabValidationError) as error:
        _discard(lab, attempt_id, workspace_root, "different outcome")
    assert error.value.code == "WORKSPACE_CLEANUP_OUTCOME_MISMATCH"
    assert attempt_path.read_bytes() == before


def test_discard_workspace_rename_failure_preserves_prepared_state(tmp_path: Path, capsys) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    receipt_path = lab / "state" / "workspaces" / f"{attempt_id}.json"
    before_attempt = (lab / "state" / "attempts" / f"{attempt_id}.json").read_bytes()
    before_receipt = receipt_path.read_bytes()

    def reject_rename(source: Path, target: Path) -> None:
        raise PermissionError("injected rename failure")

    with pytest.raises(LabValidationError) as error:
        discard_workspace(
            lab,
            attempt_id,
            workspace_root,
            "must remain prepared",
            occurred_at=_next_attempt_timestamp(lab, attempt_id),
            replace_path=reject_rename,
        )

    assert error.value.code == "WORKSPACE_DISPOSAL_FAILED"
    assert (lab / "state" / "attempts" / f"{attempt_id}.json").read_bytes() == before_attempt
    assert receipt_path.read_bytes() == before_receipt
    assert workspace.is_dir()
    assert not (workspace_root / f".worker-lab-quarantine-{attempt_id}").exists()


def test_discard_workspace_rejects_backward_timestamp_before_mutation(tmp_path: Path, capsys) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    receipt_path = lab / "state" / "workspaces" / f"{attempt_id}.json"
    attempt_path = lab / "state" / "attempts" / f"{attempt_id}.json"
    before_attempt = attempt_path.read_bytes()
    before_receipt = receipt_path.read_bytes()
    current = AttemptStore(lab / "state").read(attempt_id).updated_at
    occurred_at = (
        datetime.fromisoformat(current.replace("Z", "+00:00")) - timedelta(seconds=1)
    ).astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    with pytest.raises(LabValidationError) as error:
        discard_workspace(
            lab,
            attempt_id,
            workspace_root,
            "must remain prepared",
            occurred_at=occurred_at,
        )

    assert error.value.code == "ATTEMPT_TRANSITION_TIME_INVALID"
    assert attempt_path.read_bytes() == before_attempt
    assert receipt_path.read_bytes() == before_receipt
    assert workspace.is_dir()
    assert not (workspace_root / f".worker-lab-quarantine-{attempt_id}").exists()


def test_discard_workspace_receipt_write_failure_prevents_deletion(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    receipt_path = lab / "state" / "workspaces" / f"{attempt_id}.json"
    before_receipt = receipt_path.read_bytes()
    original_write = AtomicRecordStore.write

    def reject_quarantined_receipt(self, relative_path, record):
        if relative_path == f"workspaces/{attempt_id}.json":
            raise LabValidationError("STORAGE_WRITE_FAILED", "injected receipt failure")
        return original_write(self, relative_path, record)

    monkeypatch.setattr(AtomicRecordStore, "write", reject_quarantined_receipt)
    with pytest.raises(LabValidationError) as error:
        _discard(lab, attempt_id, workspace_root, "resume after receipt failure")

    quarantine = workspace_root / f".worker-lab-quarantine-{attempt_id}"
    assert error.value.code == "STORAGE_WRITE_FAILED"
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.READY
    assert receipt_path.read_bytes() == before_receipt
    assert not workspace.exists()
    assert quarantine.is_dir()

    monkeypatch.setattr(AtomicRecordStore, "write", original_write)
    assert _discard(
        lab, attempt_id, workspace_root, "resume after receipt failure"
    ).state is AttemptState.ABORTED
    assert not quarantine.exists()


def test_discard_workspace_recovers_partial_quarantine_deletion(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    lab, _, workspace_root, attempt_id, _ = _prepared_workspace(tmp_path, capsys)
    quarantine = _quarantine_receipt(lab, workspace_root, attempt_id)
    original_remove_tree = workspace_module._remove_tree
    interrupted = False

    def interrupt_once(path: Path) -> None:
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            (path / "README.md").unlink()
            raise OSError("injected partial deletion")
        original_remove_tree(path)

    monkeypatch.setattr(workspace_module, "_remove_tree", interrupt_once)
    with pytest.raises(LabValidationError) as error:
        _discard(lab, attempt_id, workspace_root, "resume partial deletion")

    assert error.value.code == "WORKSPACE_DISPOSAL_FAILED"
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.READY
    receipt = AtomicRecordStore(lab / "state").read(
        f"workspaces/{attempt_id}.json", WorkspaceReceipt.from_mapping
    )
    assert receipt.state is WorkspaceReceiptState.QUARANTINED
    assert quarantine.is_dir()
    assert not (quarantine / "README.md").exists()

    assert _discard(
        lab, attempt_id, workspace_root, "resume partial deletion"
    ).state is AttemptState.ABORTED
    assert not quarantine.exists()


@pytest.mark.parametrize("mutation", ["missing", "malformed", "dirty"])
def test_discard_workspace_rejects_invalid_preparation_without_mutation(
    tmp_path: Path, capsys, mutation: str
) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    receipt_path = lab / "state" / "workspaces" / f"{attempt_id}.json"
    if mutation == "missing":
        receipt_path.unlink()
        before_receipt = None
    elif mutation == "malformed":
        receipt_path.write_text("{not json", encoding="utf-8")
        before_receipt = receipt_path.read_bytes()
    else:
        (workspace / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        before_receipt = receipt_path.read_bytes()
    before_attempt = (lab / "state" / "attempts" / f"{attempt_id}.json").read_bytes()

    with pytest.raises(LabValidationError) as error:
        _discard(lab, attempt_id, workspace_root, "must not dispose")

    assert error.value.code in {"STORAGE_RECORD_MISSING", "STORAGE_RECORD_CORRUPT", "WORKSPACE_VERIFY_FAILED"}
    assert (lab / "state" / "attempts" / f"{attempt_id}.json").read_bytes() == before_attempt
    assert (receipt_path.read_bytes() if receipt_path.exists() else None) == before_receipt
    assert workspace.is_dir()
    assert not (workspace_root / f".worker-lab-quarantine-{attempt_id}").exists()


def test_discard_workspace_removes_readonly_git_file(tmp_path: Path, capsys) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    config = workspace / ".git" / "config"
    os.chmod(config, 0o444)

    discarded = _discard(lab, attempt_id, workspace_root, "removed readonly files")

    assert discarded.state is AttemptState.ABORTED
    assert not workspace.exists()
    assert not (workspace_root / f".worker-lab-quarantine-{attempt_id}").exists()


def test_discard_workspace_removes_only_stale_aborted_receipt(tmp_path: Path, capsys) -> None:
    lab, _, workspace_root, attempt_id, _ = _prepared_workspace(tmp_path, capsys)
    quarantine = _quarantine_receipt(lab, workspace_root, attempt_id)
    workspace_module._remove_tree(quarantine)
    store = AttemptStore(lab / "state")
    ready = store.read(attempt_id)
    occurred_at = _next_attempt_timestamp(lab, attempt_id)
    store.save_transition(
        transition_attempt(
            ready, AttemptState.ABORTED, occurred_at=occurred_at, cleanup_outcome="done"
        )
    )

    assert _discard(lab, attempt_id, workspace_root, "done").state is AttemptState.ABORTED
    assert not (lab / "state" / "workspaces" / f"{attempt_id}.json").exists()


def test_discard_workspace_rejects_quarantine_symlink_when_supported(
    tmp_path: Path, capsys
) -> None:
    lab, _, workspace_root, attempt_id, _ = _prepared_workspace(tmp_path, capsys)
    quarantine = _quarantine_receipt(lab, workspace_root, attempt_id)
    replacement = quarantine.with_name(f"replacement-{attempt_id}")
    shutil.move(str(quarantine), str(replacement))
    try:
        os.symlink(replacement, quarantine, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    before_attempt = (lab / "state" / "attempts" / f"{attempt_id}.json").read_bytes()
    before_receipt = (lab / "state" / "workspaces" / f"{attempt_id}.json").read_bytes()

    with pytest.raises(LabValidationError) as error:
        _discard(lab, attempt_id, workspace_root, "must not follow link")

    assert error.value.code == "WORKSPACE_PATH_INDIRECTION"
    assert (lab / "state" / "attempts" / f"{attempt_id}.json").read_bytes() == before_attempt
    assert (lab / "state" / "workspaces" / f"{attempt_id}.json").read_bytes() == before_receipt
    assert quarantine.is_symlink()
    assert replacement.is_dir()


@pytest.mark.parametrize("state", ["both", "missing", "quarantined-final"])
def test_discard_workspace_rejects_ambiguous_path_states_without_mutation(
    tmp_path: Path, capsys, state: str
) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    quarantine = workspace_root / f".worker-lab-quarantine-{attempt_id}"
    if state == "both":
        quarantine.mkdir()
    elif state == "missing":
        shutil.move(str(workspace), str(workspace.with_name(f"moved-{attempt_id}")))
    else:
        _quarantine_receipt(lab, workspace_root, attempt_id)
        workspace.mkdir()
    receipt_path = lab / "state" / "workspaces" / f"{attempt_id}.json"
    before_attempt = (lab / "state" / "attempts" / f"{attempt_id}.json").read_bytes()
    before_receipt = receipt_path.read_bytes()

    with pytest.raises(LabValidationError) as error:
        _discard(lab, attempt_id, workspace_root, "must not dispose")

    assert error.value.code == "WORKSPACE_DISPOSAL_AMBIGUOUS"
    assert (lab / "state" / "attempts" / f"{attempt_id}.json").read_bytes() == before_attempt
    assert receipt_path.read_bytes() == before_receipt
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.READY
    assert workspace.exists() is (state != "missing")
    assert quarantine.exists() is (state != "missing")


def test_verify_workspace_restarts_without_mutating_records(tmp_path: Path, capsys) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    before = _verification_snapshot(lab, workspace_root, attempt_id)

    receipt = verify_workspace(lab, attempt_id, workspace_root)

    assert receipt.workspace_path_digest == canonical_path_digest(workspace)
    _assert_verification_preserved(lab, workspace_root, attempt_id, before)
    assert workspace.is_dir()


def test_verify_workspace_rejects_attempt_reparse_indirection_when_supported(
    tmp_path: Path, capsys
) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    attempt_directory = lab / "state" / "attempts"
    replacement = lab / "replacement-attempts"
    shutil.move(str(attempt_directory), str(replacement))
    try:
        os.symlink(replacement, attempt_directory, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    before_receipt = (lab / "state" / "workspaces" / f"{attempt_id}.json").read_bytes()
    before_workspace = _workspace_snapshot(workspace)

    with pytest.raises(LabValidationError) as error:
        verify_workspace(lab, attempt_id, workspace_root)

    assert error.value.code == "WORKSPACE_PATH_INDIRECTION"
    assert attempt_directory.is_symlink()
    assert (lab / "state" / "workspaces" / f"{attempt_id}.json").read_bytes() == before_receipt
    assert _workspace_snapshot(workspace) == before_workspace


@pytest.mark.parametrize("mutation", ["missing", "malformed", "identity"])
def test_verify_workspace_rejects_invalid_receipt_without_mutation(
    tmp_path: Path, capsys, mutation: str
) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    receipt_path = lab / "state" / "workspaces" / f"{attempt_id}.json"
    if mutation == "missing":
        receipt_path.unlink()
        before_attempt = (lab / "state" / "attempts" / f"{attempt_id}.json").read_bytes()
        with pytest.raises(LabValidationError) as error:
            verify_workspace(lab, attempt_id, workspace_root)
        assert error.value.code == "STORAGE_RECORD_MISSING"
        assert not receipt_path.exists()
        assert (lab / "state" / "attempts" / f"{attempt_id}.json").read_bytes() == before_attempt
    else:
        if mutation == "malformed":
            receipt_path.write_text("{not json", encoding="utf-8")
        else:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["template_repository"] = "substituted-template"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        before = _verification_snapshot(lab, workspace_root, attempt_id)
        with pytest.raises(LabValidationError) as error:
            verify_workspace(lab, attempt_id, workspace_root)
        assert error.value.code in {"STORAGE_RECORD_CORRUPT", "WORKSPACE_RECEIPT_MISMATCH"}
        assert _verification_snapshot(lab, workspace_root, attempt_id) == before
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.READY
    assert workspace.is_dir()


def test_verify_workspace_rejects_non_ready_attempt_without_mutation(tmp_path: Path, capsys) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    store = AttemptStore(lab / "state")
    ready = store.read(attempt_id)
    store.save_transition(transition_attempt(
        ready,
        AttemptState.RUNNING,
        occurred_at=ready.updated_at,
        runtime_identity="sha256:" + "f" * 64,
    ))
    before = _verification_snapshot(lab, workspace_root, attempt_id)

    with pytest.raises(LabValidationError) as error:
        verify_workspace(lab, attempt_id, workspace_root)

    assert error.value.code == "WORKSPACE_ATTEMPT_STATE_INVALID"
    assert _verification_snapshot(lab, workspace_root, attempt_id) == before
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.RUNNING
    assert workspace.is_dir()


def test_verify_workspace_rejects_non_prepared_receipt_without_mutation(
    tmp_path: Path, capsys
) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    receipt_path = lab / "state" / "workspaces" / f"{attempt_id}.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["state"] = "QUARANTINED"
    receipt["workspace_relative_path"] = f".worker-lab-quarantine-{attempt_id}"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    before = _verification_snapshot(lab, workspace_root, attempt_id)

    with pytest.raises(LabValidationError) as error:
        verify_workspace(lab, attempt_id, workspace_root)

    assert error.value.code == "WORKSPACE_RECEIPT_MISMATCH"
    assert _verification_snapshot(lab, workspace_root, attempt_id) == before
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.READY
    stored = AtomicRecordStore(lab / "state").read(
        f"workspaces/{attempt_id}.json", WorkspaceReceipt.from_mapping
    )
    assert stored.state is WorkspaceReceiptState.QUARANTINED
    assert workspace.is_dir()


@pytest.mark.parametrize("mutation", ["wrong-root", "missing-workspace", "dirty-tracked", "dirty-untracked", "branch", "changed-head", "remote", "alternates", "context", "nested-repository"])
def test_verify_workspace_rejects_workspace_mutation_without_repair(
    tmp_path: Path, capsys, mutation: str
) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    root = workspace_root
    if mutation == "wrong-root":
        root = tmp_path / "other-workspaces"
        root.mkdir()
    elif mutation == "missing-workspace":
        shutil.move(str(workspace), str(workspace.with_name(f"moved-{attempt_id}")))
    elif mutation == "dirty-tracked":
        (workspace / "README.md").write_text("changed\n", encoding="utf-8")
    elif mutation == "dirty-untracked":
        (workspace / "untracked.txt").write_text("changed\n", encoding="utf-8")
    elif mutation == "branch":
        subprocess.run(["git", "-C", str(workspace), "switch", "-c", "verification-branch"], check=True)
    elif mutation == "changed-head":
        (workspace / "later.txt").write_text("later\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(workspace), "add", "later.txt"], check=True)
        subprocess.run(["git", "-C", str(workspace), "-c", "user.name=Worker Lab Tests", "-c", "user.email=worker-lab@example.invalid", "commit", "-q", "-m", "later"], check=True)
    elif mutation == "remote":
        subprocess.run(["git", "-C", str(workspace), "remote", "add", "other", "https://example.invalid/other.git"], check=True)
    elif mutation == "alternates":
        alternates = workspace / ".git" / "objects" / "info" / "alternates"
        alternates.parent.mkdir(parents=True, exist_ok=True)
        alternates.write_text(str(workspace / ".git" / "objects"), encoding="utf-8")
    elif mutation == "context":
        (workspace / "record_ledger" / "models.py").write_text("# changed\n", encoding="utf-8")
    else:
        (workspace / ".git" / "info" / "exclude").write_text("nested/\n", encoding="utf-8")
        nested = workspace / "nested"
        nested.mkdir()
        subprocess.run(["git", "init", "-q", str(nested)], check=True)
        assert _git_value(workspace, "status", "--porcelain=v1", "--untracked-files=all") == ""
    before = _verification_snapshot(lab, workspace_root, attempt_id)

    with pytest.raises(LabValidationError) as error:
        verify_workspace(lab, attempt_id, root)

    assert error.value.code in {"WORKSPACE_RECEIPT_MISMATCH", "WORKSPACE_VERIFY_FAILED"}
    _assert_verification_preserved(lab, workspace_root, attempt_id, before)
    assert workspace.exists() is (mutation != "missing-workspace")


def test_verify_workspace_rejects_symlink_root_when_supported(tmp_path: Path, capsys) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    linked_root = tmp_path / "linked-workspaces"
    try:
        os.symlink(workspace_root, linked_root, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    before = _verification_snapshot(lab, workspace_root, attempt_id)

    with pytest.raises(LabValidationError) as error:
        verify_workspace(lab, attempt_id, linked_root)

    assert error.value.code == "WORKSPACE_PATH_INDIRECTION"
    _assert_verification_preserved(lab, workspace_root, attempt_id, before)
    assert workspace.is_dir()


def test_verify_workspace_rejects_symlink_workspace_when_supported(tmp_path: Path, capsys) -> None:
    lab, _, workspace_root, attempt_id, workspace = _prepared_workspace(tmp_path, capsys)
    replacement = workspace.with_name(f"replacement-{attempt_id}")
    shutil.move(str(workspace), str(replacement))
    try:
        os.symlink(replacement, workspace, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    before = _verification_snapshot(lab, workspace_root, attempt_id)

    with pytest.raises(LabValidationError) as error:
        verify_workspace(lab, attempt_id, workspace_root)

    assert error.value.code == "WORKSPACE_PATH_INDIRECTION"
    _assert_verification_preserved(lab, workspace_root, attempt_id, before)
    assert workspace.is_symlink()
    assert replacement.is_dir()


def test_prepare_workspace_publishes_verified_detached_copy(tmp_path: Path, capsys) -> None:
    lab, template = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    attempt_id = _create_draft(lab, template, capsys)

    receipt = _prepare(lab, attempt_id, template, workspace_root)

    workspace = workspace_root / attempt_id
    stored = AtomicRecordStore(lab / "state").read(
        f"workspaces/{attempt_id}.json", WorkspaceReceipt.from_mapping
    )
    attempt = AttemptStore(lab / "state").read(attempt_id)
    assert stored == receipt
    assert receipt.state == "PREPARED"
    assert receipt.workspace_root_digest == canonical_path_digest(workspace_root)
    assert receipt.workspace_path_digest == canonical_path_digest(workspace)
    assert receipt.workspace_relative_path == attempt_id
    assert attempt.state is AttemptState.READY
    assert attempt.runtime_identity is None
    assert attempt.candidate_digest is None
    assert _git_value(workspace, "rev-parse", "HEAD") == _git_value(template, "rev-parse", "HEAD")
    assert _git_value(workspace, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
    assert _git_value(workspace, "status", "--porcelain=v1", "--untracked-files=all") == ""
    assert _git_value(workspace, "remote") == ""
    assert not (workspace / ".git" / "objects" / "info" / "alternates").exists()
    assert _git_value(template, "status", "--porcelain=v1", "--untracked-files=all") == ""


def test_prepare_workspace_preserves_crlf_sealed_context(tmp_path: Path, capsys) -> None:
    lab, template = write_authority_fixture(tmp_path)
    sealed = template / "README.md"
    subprocess.run(
        ["git", "-C", str(template), "config", "core.autocrlf", "true"],
        check=True,
    )
    subprocess.run(["git", "-C", str(template), "checkout", "--force"], check=True)
    head = _git_value(template, "rev-parse", "HEAD")
    exercise_path = lab / "curricula" / "exercises" / "record-model" / "v1.json"
    exercise = json.loads(exercise_path.read_text(encoding="utf-8"))
    exercise["template_commit"] = head
    write_json(exercise_path, exercise)
    context_path = lab / "curricula" / "contexts" / "record-model-context" / "v1.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))
    context["starting_commit"] = head
    context["files"][0]["digest"] = "sha256:" + hashlib.sha256(sealed.read_bytes()).hexdigest()
    write_json(context_path, context)
    assert subprocess.check_output(
        ["git", "-C", str(template), "cat-file", "blob", "HEAD:README.md"]
    ) == b"instructions\n"

    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    attempt_id = _create_draft(lab, template, capsys)
    receipt = _prepare(lab, attempt_id, template, workspace_root)

    workspace = workspace_root / attempt_id
    assert (workspace / "README.md").read_bytes() == sealed.read_bytes()
    assert verify_workspace(lab, attempt_id, workspace_root) == receipt


def test_prepare_workspace_cli_returns_receipt_and_ready_attempt(tmp_path: Path, capsys) -> None:
    lab, template = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    attempt_id = _create_draft(lab, template, capsys)

    assert main([
        "--root", str(lab), "prepare-workspace", attempt_id,
        "--template-repository", str(template),
        "--workspace-root", str(workspace_root),
    ]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "PREPARED"
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.READY


def test_prepare_workspace_rejects_dirty_template_without_publication(tmp_path: Path, capsys) -> None:
    lab, template = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    attempt_id = _create_draft(lab, template, capsys)
    (template / "untracked.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(LabValidationError, match="template repository must be clean") as error:
        _prepare(lab, attempt_id, template, workspace_root)
    assert error.value.code == "WORKSPACE_TEMPLATE_DIRTY"
    _assert_no_published_state(lab, workspace_root, attempt_id)


def test_prepare_workspace_rejects_template_object_alternates(tmp_path: Path, capsys) -> None:
    lab, template = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    attempt_id = _create_draft(lab, template, capsys)
    alternates = template / ".git" / "objects" / "info" / "alternates"
    alternates.parent.mkdir(parents=True, exist_ok=True)
    alternates.write_text(str(template / ".git" / "objects"), encoding="utf-8")

    with pytest.raises(LabValidationError) as error:
        _prepare(lab, attempt_id, template, workspace_root)
    assert error.value.code == "WORKSPACE_TEMPLATE_ALTERNATES_FORBIDDEN"
    _assert_no_published_state(lab, workspace_root, attempt_id)


def test_prepare_workspace_rejects_changed_template_head(tmp_path: Path, capsys) -> None:
    lab, template = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    attempt_id = _create_draft(lab, template, capsys)
    (template / "later.txt").write_bytes(b"later commit\n")
    subprocess.run(["git", "-C", str(template), "add", "later.txt"], check=True)
    subprocess.run([
        "git", "-C", str(template), "-c", "user.name=Worker Lab Tests",
        "-c", "user.email=worker-lab@example.invalid", "commit", "-q", "-m", "later",
    ], check=True)

    with pytest.raises(LabValidationError) as error:
        _prepare(lab, attempt_id, template, workspace_root)
    assert error.value.code == "WORKSPACE_TEMPLATE_HEAD_MISMATCH"
    _assert_no_published_state(lab, workspace_root, attempt_id)


def test_prepare_workspace_requires_clean_draft_attempt(tmp_path: Path, capsys) -> None:
    lab, template = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    attempt_id = _create_draft(lab, template, capsys)
    store = AttemptStore(lab / "state")
    draft = store.read(attempt_id)
    store.save_transition(
        transition_attempt(draft, AttemptState.READY, occurred_at=draft.updated_at)
    )

    with pytest.raises(LabValidationError) as error:
        _prepare(lab, attempt_id, template, workspace_root)
    assert error.value.code == "WORKSPACE_ATTEMPT_STATE_INVALID"
    assert not (workspace_root / attempt_id).exists()


def test_prepare_workspace_preserves_preexisting_target(tmp_path: Path, capsys) -> None:
    lab, template = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    attempt_id = _create_draft(lab, template, capsys)
    target = workspace_root / attempt_id
    target.mkdir()
    marker = target / "owner.txt"
    marker.write_text("do not remove\n", encoding="utf-8")

    with pytest.raises(LabValidationError) as error:
        _prepare(lab, attempt_id, template, workspace_root)
    assert error.value.code == "WORKSPACE_TARGET_EXISTS"
    assert marker.read_text(encoding="utf-8") == "do not remove\n"
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.DRAFT


@pytest.mark.parametrize("root_kind", ["lab", "template", "git-parent"])
def test_prepare_workspace_rejects_protected_workspace_roots(
    tmp_path: Path, capsys, root_kind: str
) -> None:
    lab, template = write_authority_fixture(tmp_path)
    attempt_id = _create_draft(lab, template, capsys)
    if root_kind == "lab":
        root = lab
    elif root_kind == "template":
        root = template
    else:
        repository = tmp_path / "other-repository"
        repository.mkdir()
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        root = repository / "workspaces"
        root.mkdir()

    with pytest.raises(LabValidationError) as error:
        _prepare(lab, attempt_id, template, root)
    assert error.value.code == "WORKSPACE_ROOT_INVALID"
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.DRAFT


def test_prepare_workspace_compensates_when_ready_transition_fails(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    lab, template = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    attempt_id = _create_draft(lab, template, capsys)

    def reject_transition(self, record):
        raise LabValidationError("TEST_TRANSITION_FAILURE", "injected failure")

    monkeypatch.setattr(AttemptStore, "save_transition", reject_transition)
    with pytest.raises(LabValidationError) as error:
        _prepare(lab, attempt_id, template, workspace_root)
    assert error.value.code == "TEST_TRANSITION_FAILURE"
    _assert_no_published_state(lab, workspace_root, attempt_id)


def test_prepare_workspace_preserves_preexisting_receipt(tmp_path: Path, capsys) -> None:
    lab, template = write_authority_fixture(tmp_path)
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    attempt_id = _create_draft(lab, template, capsys)
    receipt_path = lab / "state" / "workspaces" / f"{attempt_id}.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text('{"owned":"elsewhere"}\n', encoding="utf-8")

    with pytest.raises(LabValidationError) as error:
        _prepare(lab, attempt_id, template, workspace_root)
    assert error.value.code == "WORKSPACE_RECEIPT_EXISTS"
    assert receipt_path.read_text(encoding="utf-8") == '{"owned":"elsewhere"}\n'
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.DRAFT


@pytest.mark.parametrize("name", [
    "GITHUB_TOKEN", "GITHUB_ACTIONS", "GH_TOKEN", "GH_ENTERPRISE_TOKEN",
    "ACTIONS_ID_TOKEN_REQUEST_TOKEN", "GIT_ASKPASS", "GIT_CONFIG_COUNT",
    "GIT_OBJECT_DIRECTORY", "SSH_ASKPASS",
])
def test_git_environment_strips_credentials_and_redirection(name: str) -> None:
    environment = _git_environment({name: "secret", "SAFE_VALUE": "retained"})
    assert name not in environment
    assert environment["SAFE_VALUE"] == "retained"
    assert environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"


def test_git_timeout_is_structured() -> None:
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    with pytest.raises(LabValidationError) as error:
        _git(["version"], "test operation", timeout, 1)
    assert error.value.code == "WORKSPACE_GIT_TIMEOUT"


def test_prepare_workspace_rejects_symlink_root_when_supported(tmp_path: Path, capsys) -> None:
    lab, template = write_authority_fixture(tmp_path)
    real_root = tmp_path / "real-workspaces"
    real_root.mkdir()
    linked_root = tmp_path / "linked-workspaces"
    try:
        os.symlink(real_root, linked_root, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    attempt_id = _create_draft(lab, template, capsys)

    with pytest.raises(LabValidationError) as error:
        _prepare(lab, attempt_id, template, linked_root)
    assert error.value.code == "WORKSPACE_PATH_INDIRECTION"
    assert AttemptStore(lab / "state").read(attempt_id).state is AttemptState.DRAFT


def test_receipt_round_trips_without_mutating_input() -> None:
    value = workspace_receipt_mapping()
    before = deepcopy(value)
    receipt = WorkspaceReceipt.from_mapping(value)
    assert value == before
    assert WorkspaceReceipt.from_mapping(receipt.to_dict()) == receipt
    assert receipt.to_json() == receipt.to_json()


@pytest.mark.parametrize(
    "relative_path",
    [
        "OTHER-ATTEMPT",
        "nested/ATTEMPT-000001",
        "../ATTEMPT-000001",
        "/ATTEMPT-000001",
        "C:/ATTEMPT-000001",
        "a\\b",
    ],
)
def test_prepared_receipt_rejects_any_path_other_than_attempt_id(
    relative_path: str,
) -> None:
    value = workspace_receipt_mapping()
    value["workspace_relative_path"] = relative_path
    with pytest.raises(LabValidationError) as error:
        WorkspaceReceipt.from_mapping(value)
    assert error.value.code in {"RECORD_PATH_INVALID", "RECORD_WORKSPACE_PATH_INVALID"}


def test_quarantined_receipt_requires_deterministic_attempt_bound_name() -> None:
    value = workspace_receipt_mapping()
    value["state"] = "QUARANTINED"
    value["workspace_relative_path"] = ".worker-lab-quarantine-ATTEMPT-000001"
    receipt = WorkspaceReceipt.from_mapping(value)
    assert receipt.state is WorkspaceReceiptState.QUARANTINED

    value["workspace_relative_path"] = ".worker-lab-quarantine-OTHER-ATTEMPT"
    with pytest.raises(LabValidationError) as error:
        WorkspaceReceipt.from_mapping(value)
    assert error.value.code == "RECORD_WORKSPACE_PATH_INVALID"


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("template_commit", "A" * 40),
        ("workspace_root_digest", "sha256:" + "A" * 64),
        ("workspace_path_digest", "sha256:" + "b" * 63),
        ("created_at", "2026-08-27T12:00:00+00:00"),
        ("state", "READY"),
    ],
)
def test_receipt_rejects_malformed_identity_fields(field: str, replacement: str) -> None:
    value = workspace_receipt_mapping()
    value[field] = replacement
    with pytest.raises(LabValidationError):
        WorkspaceReceipt.from_mapping(value)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("exercise_version", 2),
        ("template_repository", "local/other-template"),
        ("template_commit", "c" * 40),
        ("workspace_root_digest", "sha256:" + "c" * 64),
        ("workspace_path_digest", "sha256:" + "d" * 64),
    ],
)
def test_every_workspace_binding_changes_canonical_identity(
    field: str, replacement: object
) -> None:
    original = WorkspaceReceipt.from_mapping(workspace_receipt_mapping())
    changed_mapping = workspace_receipt_mapping()
    changed_mapping[field] = replacement
    changed = WorkspaceReceipt.from_mapping(changed_mapping)
    assert changed.digest() != original.digest()
