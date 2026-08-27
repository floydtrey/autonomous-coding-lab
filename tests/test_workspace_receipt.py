from __future__ import annotations

import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from tests.test_cli import write_authority_fixture
from worker_lab.attempt_store import AttemptStore
from worker_lab.cli import main
from worker_lab.errors import LabValidationError
from worker_lab.lifecycle import transition_attempt
from tests.test_models import workspace_receipt_mapping
from worker_lab.models import AttemptState, WorkspaceReceipt, WorkspaceReceiptState
from worker_lab.storage import AtomicRecordStore
from worker_lab.workspace import (
    _git,
    _git_environment,
    canonical_path_digest,
    prepare_workspace,
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
