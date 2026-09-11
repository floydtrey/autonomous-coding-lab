from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from .attempt_store import AttemptStore
from .canonical import canonical_digest
from .errors import LabValidationError
from .lifecycle import transition_attempt
from .models import (
    AttemptRecord,
    AttemptState,
    ExerciseRecord,
    WorkspaceReceipt,
    WORKSPACE_RECEIPT_SCHEMA,
)
from .policy import ContextManifest, PolicyRecord, RoleRecord, verify_context_files
from .storage import AtomicRecordStore
from .test_catalog import TestCatalog
from .validation import validate_attempt_authority_binding


DEFAULT_GIT_TIMEOUT_SECONDS = 30
_GITHUB_CREDENTIAL_NAMES = frozenset({"GH_TOKEN", "GH_ENTERPRISE_TOKEN"})
_GIT_REDIRECTION_NAMES = frozenset({
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_ASKPASS",
    "GIT_COMMON_DIR",
    "GIT_DIR",
    "GIT_INDEX_FILE",
    "GIT_NAMESPACE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_SSH",
    "GIT_SSH_COMMAND",
    "GIT_WORK_TREE",
    "SSH_ASKPASS",
})

RunProcess = Callable[..., subprocess.CompletedProcess[str]]


def verify_workspace(
    lab_root: Path,
    attempt_id: str,
    workspace_root: Path,
    *,
    run_process: RunProcess = subprocess.run,
    git_timeout_seconds: int = DEFAULT_GIT_TIMEOUT_SECONDS,
) -> WorkspaceReceipt:
    """Verify one prepared workspace without changing persistent or filesystem state."""
    if isinstance(git_timeout_seconds, bool) or git_timeout_seconds <= 0:
        raise LabValidationError("WORKSPACE_TIMEOUT_INVALID", "Git timeout must be positive")
    lab = _real_directory(lab_root, "WORKSPACE_LAB_INVALID")
    root = _verify_workspace_root_for_verification(workspace_root, lab)
    state_root = lab / "state"
    _assert_no_reparse_components(state_root)
    _assert_no_reparse_components(state_root / "attempts" / f"{attempt_id}.json")
    attempt = AttemptStore(state_root).read(attempt_id)
    if (
        attempt.state is not AttemptState.READY
        or attempt.runtime_identity is not None
        or attempt.candidate_digest is not None
        or attempt.cleanup_outcome is not None
    ):
        raise LabValidationError(
            "WORKSPACE_ATTEMPT_STATE_INVALID", "workspace verification requires a clean READY"
        )
    exercise, context = _load_and_verify_authority(lab, attempt)
    receipt_relative = f"workspaces/{attempt.attempt_id}.json"
    receipt_path = state_root / "workspaces" / f"{attempt.attempt_id}.json"
    _assert_no_reparse_components(receipt_path)
    receipt = AtomicRecordStore(lab / "state").read(
        receipt_relative, WorkspaceReceipt.from_mapping
    )
    workspace = root / attempt.attempt_id
    resolved_workspace = _real_directory(workspace, "WORKSPACE_VERIFY_FAILED")
    if (
        receipt.state.value != "PREPARED"
        or receipt.attempt_id != attempt.attempt_id
        or receipt.exercise_id != exercise.exercise_id
        or receipt.exercise_version != exercise.exercise_version
        or receipt.template_repository != exercise.template_repository
        or receipt.template_commit != attempt.starting_commit
        or receipt.workspace_root_digest != canonical_path_digest(root)
        or receipt.workspace_path_digest != canonical_path_digest(resolved_workspace)
        or receipt.workspace_relative_path != attempt.attempt_id
    ):
        raise LabValidationError("WORKSPACE_RECEIPT_MISMATCH", "workspace receipt binding differs")
    _verify_prepared_repository(
        resolved_workspace, attempt, context, run_process=run_process, timeout=git_timeout_seconds
    )
    return receipt


def discard_workspace(
    lab_root: Path,
    attempt_id: str,
    workspace_root: Path,
    cleanup_outcome: str,
    *,
    occurred_at: str,
    run_process: RunProcess = subprocess.run,
    replace_path: Callable[[Path, Path], None] = os.replace,
    git_timeout_seconds: int = DEFAULT_GIT_TIMEOUT_SECONDS,
) -> AttemptRecord:
    """Quarantine and remove one receipt-bound workspace before READY -> ABORTED."""
    if isinstance(git_timeout_seconds, bool) or git_timeout_seconds <= 0:
        raise LabValidationError("WORKSPACE_TIMEOUT_INVALID", "Git timeout must be positive")
    if not isinstance(cleanup_outcome, str) or not cleanup_outcome.strip():
        raise LabValidationError("WORKSPACE_CLEANUP_OUTCOME_INVALID", "cleanup outcome must be non-empty")
    lab = _real_directory(lab_root, "WORKSPACE_LAB_INVALID")
    root = _verify_workspace_root_for_verification(workspace_root, lab)
    state_root = lab / "state"
    _assert_no_reparse_components(state_root)
    _assert_no_reparse_components(state_root / "attempts" / f"{attempt_id}.json")
    attempt_store = AttemptStore(state_root)
    attempt = attempt_store.read(attempt_id)
    receipt_path = state_root / "workspaces" / f"{attempt.attempt_id}.json"
    _assert_no_reparse_components(receipt_path)
    receipt_store = AtomicRecordStore(state_root)
    receipt_relative = f"workspaces/{attempt.attempt_id}.json"
    final_workspace = root / attempt.attempt_id
    quarantine = root / f".worker-lab-quarantine-{attempt.attempt_id}"
    exercise, context = _load_and_verify_authority(lab, attempt)

    if attempt.state is AttemptState.ABORTED:
        if attempt.runtime_identity is not None or attempt.candidate_digest is not None:
            raise LabValidationError(
                "WORKSPACE_DISPOSAL_STATE_INVALID", "workspace disposal requires a Phase 2 attempt"
            )
        if attempt.cleanup_outcome != cleanup_outcome:
            raise LabValidationError(
                "WORKSPACE_CLEANUP_OUTCOME_MISMATCH",
                "cleanup outcome differs from the completed attempt",
            )
        if os.path.lexists(final_workspace) or os.path.lexists(quarantine):
            raise LabValidationError(
                "WORKSPACE_DISPOSAL_AMBIGUOUS", "aborted attempt retains a workspace"
            )
        try:
            receipt = receipt_store.read(receipt_relative, WorkspaceReceipt.from_mapping)
        except LabValidationError as exc:
            if exc.code == "STORAGE_RECORD_MISSING":
                return attempt
            raise
        _validate_quarantined_receipt(receipt, attempt, exercise, root, quarantine)
        try:
            receipt_path.unlink()
        except OSError as exc:
            raise LabValidationError("WORKSPACE_DISPOSAL_FAILED", str(exc)) from exc
        return attempt
    if (
        attempt.state is not AttemptState.READY
        or attempt.runtime_identity is not None
        or attempt.candidate_digest is not None
        or attempt.cleanup_outcome is not None
    ):
        raise LabValidationError(
            "WORKSPACE_DISPOSAL_STATE_INVALID", "workspace disposal requires a clean READY"
        )
    aborted_attempt = transition_attempt(
        attempt,
        AttemptState.ABORTED,
        occurred_at=occurred_at,
        cleanup_outcome=cleanup_outcome,
    )
    receipt = receipt_store.read(receipt_relative, WorkspaceReceipt.from_mapping)
    if receipt.state.value == "PREPARED":
        _validate_prepared_receipt(receipt, attempt, exercise, root, final_workspace)
        final_exists = os.path.lexists(final_workspace)
        quarantine_exists = os.path.lexists(quarantine)
        if final_exists and quarantine_exists:
            raise LabValidationError("WORKSPACE_DISPOSAL_AMBIGUOUS", "both workspace paths exist")
        if not final_exists and not quarantine_exists:
            raise LabValidationError("WORKSPACE_DISPOSAL_AMBIGUOUS", "workspace is missing")
        if final_exists:
            _verify_prepared_repository(
                final_workspace,
                attempt,
                context,
                run_process=run_process,
                timeout=git_timeout_seconds,
            )
            try:
                replace_path(final_workspace, quarantine)
            except OSError as exc:
                raise LabValidationError(
                    "WORKSPACE_DISPOSAL_FAILED", "workspace quarantine rename failed"
                ) from exc
        else:
            _verify_prepared_repository(
                quarantine,
                attempt,
                context,
                run_process=run_process,
                timeout=git_timeout_seconds,
            )
        _assert_direct_child(quarantine, root, prefix=".worker-lab-quarantine-")
        if _is_reparse(quarantine) or not quarantine.is_dir():
            raise LabValidationError("WORKSPACE_PATH_INDIRECTION", "quarantine path is invalid")
        receipt = _quarantined_receipt(receipt, quarantine)
        receipt_store.write(receipt_relative, receipt)
        _assert_no_reparse_components(receipt_path)
        stored = receipt_store.read(receipt_relative, WorkspaceReceipt.from_mapping)
        if stored != receipt:
            raise LabValidationError("WORKSPACE_RECEIPT_MISMATCH", "quarantined receipt differs")
    elif receipt.state.value == "QUARANTINED":
        _validate_quarantined_receipt(receipt, attempt, exercise, root, quarantine)
        if os.path.lexists(final_workspace):
            raise LabValidationError("WORKSPACE_DISPOSAL_AMBIGUOUS", "workspace remains after quarantine")
    else:
        raise LabValidationError("WORKSPACE_RECEIPT_MISMATCH", "receipt state is unsupported")

    if os.path.lexists(quarantine):
        _assert_direct_child(quarantine, root, prefix=".worker-lab-quarantine-")
        if _is_reparse(quarantine) or not quarantine.is_dir():
            raise LabValidationError("WORKSPACE_PATH_INDIRECTION", "quarantine path is invalid")
        try:
            _remove_tree(quarantine)
        except OSError as exc:
            raise LabValidationError("WORKSPACE_DISPOSAL_FAILED", str(exc)) from exc
    if os.path.lexists(quarantine):
        raise LabValidationError("WORKSPACE_DISPOSAL_FAILED", "quarantine removal was incomplete")
    attempt_store.save_transition(aborted_attempt)
    _assert_no_reparse_components(receipt_path)
    try:
        receipt_path.unlink()
    except OSError as exc:
        raise LabValidationError("WORKSPACE_DISPOSAL_FAILED", str(exc)) from exc
    return aborted_attempt


def prepare_workspace(
    lab_root: Path,
    attempt_id: str,
    template_repository: Path,
    workspace_root: Path,
    *,
    occurred_at: str,
    run_process: RunProcess = subprocess.run,
    git_timeout_seconds: int = DEFAULT_GIT_TIMEOUT_SECONDS,
) -> WorkspaceReceipt:
    """Prepare one receipt-bound detached workspace and persist DRAFT -> READY."""
    if isinstance(git_timeout_seconds, bool) or git_timeout_seconds <= 0:
        raise LabValidationError("WORKSPACE_TIMEOUT_INVALID", "Git timeout must be positive")
    lab = _real_directory(lab_root, "WORKSPACE_LAB_INVALID")
    attempt_store = AttemptStore(lab / "state")
    attempt = attempt_store.read(attempt_id)
    if (
        attempt.state is not AttemptState.DRAFT
        or attempt.runtime_identity is not None
        or attempt.candidate_digest is not None
        or attempt.cleanup_outcome is not None
    ):
        raise LabValidationError(
            "WORKSPACE_ATTEMPT_STATE_INVALID", "workspace preparation requires a clean DRAFT"
        )
    ready_attempt = transition_attempt(
        attempt, AttemptState.READY, occurred_at=occurred_at
    )
    exercise, context = _load_and_verify_authority(lab, attempt)
    source = _verify_template_repository(
        template_repository,
        lab,
        attempt,
        context,
        run_process=run_process,
        timeout=git_timeout_seconds,
    )
    root = _verify_workspace_root(workspace_root, lab, source)
    final_workspace = root / attempt.attempt_id
    quarantine = root / f".worker-lab-quarantine-{attempt.attempt_id}"
    if os.path.lexists(final_workspace) or os.path.lexists(quarantine):
        raise LabValidationError(
            "WORKSPACE_TARGET_EXISTS", "attempt workspace or quarantine path already exists"
        )
    receipt_store = AtomicRecordStore(lab / "state")
    receipt_relative = f"workspaces/{attempt.attempt_id}.json"
    receipt_path = lab / "state" / "workspaces" / f"{attempt.attempt_id}.json"
    if os.path.lexists(receipt_path):
        raise LabValidationError("WORKSPACE_RECEIPT_EXISTS", "attempt receipt already exists")

    staging_parent: Path | None = None
    published = False
    receipt_written = False
    transition_started = False
    receipt: WorkspaceReceipt | None = None
    try:
        staging_prefix = _staging_prefix(attempt.attempt_id)
        staging_parent = Path(
            tempfile.mkdtemp(prefix=staging_prefix, dir=root)
        )
        _assert_direct_child(staging_parent, root, prefix=staging_prefix)
        _assert_no_reparse_components(staging_parent)
        staged_workspace = staging_parent / "workspace"
        _git(
            [
                "-c", "core.autocrlf=false", "clone", "--no-local", "--no-hardlinks",
                "--no-checkout", "--", str(source), str(staged_workspace),
            ],
            "clone template",
            run_process,
            git_timeout_seconds,
        )
        _configure_context_checkout_attributes(
            staged_workspace,
            source,
            context,
            run_process=run_process,
            timeout=git_timeout_seconds,
        )
        _git(
            [
                "-C", str(staged_workspace), "-c", "core.autocrlf=false", "checkout",
                "--detach", "--force", attempt.starting_commit, "--",
            ],
            "check out starting commit",
            run_process,
            git_timeout_seconds,
        )
        _git(
            ["-C", str(staged_workspace), "remote", "remove", "origin"],
            "remove template remote",
            run_process,
            git_timeout_seconds,
        )
        _verify_prepared_repository(
            staged_workspace,
            attempt,
            context,
            run_process=run_process,
            timeout=git_timeout_seconds,
        )
        _verify_template_repository(
            source,
            lab,
            attempt,
            context,
            run_process=run_process,
            timeout=git_timeout_seconds,
        )
        if os.path.lexists(final_workspace):
            raise LabValidationError("WORKSPACE_TARGET_EXISTS", "attempt workspace appeared during preparation")
        os.replace(staged_workspace, final_workspace)
        published = True
        staging_parent.rmdir()
        staging_parent = None
        _verify_prepared_repository(
            final_workspace,
            attempt,
            context,
            run_process=run_process,
            timeout=git_timeout_seconds,
        )
        _verify_template_repository(
            source,
            lab,
            attempt,
            context,
            run_process=run_process,
            timeout=git_timeout_seconds,
        )
        receipt = WorkspaceReceipt.from_mapping({
            "schema_version": WORKSPACE_RECEIPT_SCHEMA,
            "attempt_id": attempt.attempt_id,
            "exercise_id": exercise.exercise_id,
            "exercise_version": exercise.exercise_version,
            "template_repository": exercise.template_repository,
            "template_commit": attempt.starting_commit,
            "workspace_root_digest": canonical_path_digest(root),
            "workspace_path_digest": canonical_path_digest(final_workspace),
            "workspace_relative_path": attempt.attempt_id,
            "created_at": occurred_at,
            "state": "PREPARED",
        })
        try:
            receipt_store.write(receipt_relative, receipt)
        except LabValidationError:
            stored = _read_exact_receipt(receipt_store, receipt_relative, receipt)
            if stored is None:
                raise
        receipt_written = True
        _assert_no_reparse_components(receipt_path)
        if _read_exact_receipt(receipt_store, receipt_relative, receipt) is None:
            raise LabValidationError("WORKSPACE_RECEIPT_MISMATCH", "published receipt differs")
        transition_started = True
        try:
            attempt_store.save_transition(ready_attempt)
        except LabValidationError:
            persisted = _read_attempt_if_available(attempt_store, attempt.attempt_id)
            if persisted == ready_attempt:
                return receipt
            raise
        return receipt
    except (LabValidationError, OSError) as exc:
        failure = exc if isinstance(exc, LabValidationError) else LabValidationError(
            "WORKSPACE_PREPARE_FAILED", str(exc)
        )
        if transition_started and _read_attempt_if_available(attempt_store, attempt.attempt_id) == ready_attempt:
            if receipt is not None:
                return receipt
            raise LabValidationError(
                "WORKSPACE_COMMIT_UNCERTAIN", "attempt is READY but receipt identity is unavailable"
            ) from failure
        compensation_error = _compensate_preparation(
            root,
            final_workspace,
            staging_parent,
            receipt_path if receipt_written else None,
            published=published,
        )
        if compensation_error is not None:
            raise LabValidationError(
                "WORKSPACE_COMPENSATION_FAILED",
                f"{failure.code}; {compensation_error}",
            ) from failure
        raise failure


def canonical_path_digest(path: Path) -> str:
    resolved = path.resolve(strict=True)
    return canonical_digest({"canonical_path": _path_key(resolved)})


def _load_and_verify_authority(
    lab: Path, attempt: AttemptRecord
) -> tuple[ExerciseRecord, ContextManifest]:
    definitions = AtomicRecordStore(lab / "curricula")
    exercise = definitions.read(
        f"exercises/{attempt.exercise_id}/v{attempt.exercise_version}.json",
        ExerciseRecord.from_mapping,
    )
    policy = definitions.read(
        f"policies/{attempt.policy_id}/v{attempt.policy_version}.json", PolicyRecord.from_mapping
    )
    role = definitions.read(
        f"roles/{attempt.role_id}/v{attempt.role_version}.json", RoleRecord.from_mapping
    )
    context = definitions.read(
        f"contexts/{exercise.context_manifest_id}/v{exercise.context_manifest_version}.json",
        ContextManifest.from_mapping,
    )
    catalog = definitions.read(
        f"catalogs/{attempt.evaluator_catalog_version}.json", TestCatalog.from_mapping
    )
    validate_attempt_authority_binding(attempt, exercise, policy, role, context, catalog)
    return exercise, context


def _verify_template_repository(
    candidate: Path,
    lab: Path,
    attempt: AttemptRecord,
    context: ContextManifest,
    *,
    run_process: RunProcess,
    timeout: int,
) -> Path:
    raw = str(candidate)
    if "://" in raw or raw.startswith("git@") or raw.startswith("\\\\"):
        raise LabValidationError("WORKSPACE_TEMPLATE_INVALID", "template must be an explicit local path")
    source = _real_directory(candidate, "WORKSPACE_TEMPLATE_INVALID")
    if _overlaps(source, lab):
        raise LabValidationError("WORKSPACE_TEMPLATE_INVALID", "template must be separate from Worker Lab")
    git_dir = source / ".git"
    if not git_dir.is_dir() or _is_reparse(git_dir):
        raise LabValidationError(
            "WORKSPACE_TEMPLATE_INVALID", "template .git must be an independent directory"
        )
    if os.path.lexists(git_dir / "objects" / "info" / "alternates"):
        raise LabValidationError(
            "WORKSPACE_TEMPLATE_ALTERNATES_FORBIDDEN",
            "template cannot use an alternate Git object store",
        )
    top = _git_value(
        ["-C", str(source), "rev-parse", "--show-toplevel"],
        "resolve template repository",
        run_process,
        timeout,
    )
    try:
        top_path = Path(top).resolve(strict=True)
    except OSError as exc:
        raise LabValidationError("WORKSPACE_TEMPLATE_INVALID", "template Git root is invalid") from exc
    if _path_key(top_path) != _path_key(source):
        raise LabValidationError("WORKSPACE_TEMPLATE_INVALID", "path is not the template Git root")
    head = _git_value(
        ["-C", str(source), "rev-parse", "HEAD"],
        "read template HEAD",
        run_process,
        timeout,
    )
    if head != attempt.starting_commit or context.starting_commit != attempt.starting_commit:
        raise LabValidationError("WORKSPACE_TEMPLATE_HEAD_MISMATCH", "template HEAD differs")
    status_value = _git_value(
        ["-C", str(source), "status", "--porcelain=v1", "--untracked-files=all"],
        "read template status",
        run_process,
        timeout,
    )
    if status_value:
        raise LabValidationError("WORKSPACE_TEMPLATE_DIRTY", "template repository must be clean")
    tracked = _git_value(
        ["-C", str(source), "ls-files", "--stage"],
        "inspect template entries",
        run_process,
        timeout,
    )
    if any(line.startswith("160000 ") for line in tracked.splitlines()):
        raise LabValidationError("WORKSPACE_TEMPLATE_SUBMODULES_FORBIDDEN", "submodules are unsupported")
    _assert_no_reparse_tree(source, skip_git=True)
    verify_context_files(context, source)
    return source


def _verify_workspace_root(candidate: Path, lab: Path, source: Path) -> Path:
    root = _real_directory(candidate, "WORKSPACE_ROOT_INVALID")
    if _overlaps(root, lab) or _overlaps(root, source):
        raise LabValidationError(
            "WORKSPACE_ROOT_INVALID", "workspace root overlaps a protected repository"
        )
    for ancestor in (root, *root.parents):
        if os.path.lexists(ancestor / ".git"):
            raise LabValidationError(
                "WORKSPACE_ROOT_INVALID", "workspace root is inside a Git repository"
            )
    return root


def _verify_workspace_root_for_verification(candidate: Path, lab: Path) -> Path:
    root = _real_directory(candidate, "WORKSPACE_ROOT_INVALID")
    if _overlaps(root, lab):
        raise LabValidationError(
            "WORKSPACE_ROOT_INVALID", "workspace root overlaps Worker Lab"
        )
    for ancestor in (root, *root.parents):
        if os.path.lexists(ancestor / ".git"):
            raise LabValidationError(
                "WORKSPACE_ROOT_INVALID", "workspace root is inside a Git repository"
            )
    return root


def _configure_context_checkout_attributes(
    workspace: Path,
    source: Path,
    context: ContextManifest,
    *,
    run_process: RunProcess,
    timeout: int,
) -> None:
    crlf_paths = [
        entry.path
        for entry in context.files
        if _has_only_crlf_newlines((source / Path(*entry.path.split("/"))).read_bytes())
        and _has_only_lf_newlines(
            _git_bytes(
                [
                    "-C", str(workspace), "cat-file", "blob",
                    f"HEAD:{entry.path}",
                ],
                "read context blob",
                run_process,
                timeout,
            )
        )
    ]
    if not crlf_paths:
        return
    attributes = workspace / ".git" / "info" / "attributes"
    _assert_no_reparse_components(attributes.parent)
    attributes.write_text(
        "".join(f"{path} text eol=crlf\n" for path in crlf_paths),
        encoding="ascii",
    )


def _has_only_crlf_newlines(content: bytes) -> bool:
    return (
        b"\0" not in content
        and b"\r\n" in content
        and b"\n" not in content.replace(b"\r\n", b"")
    )


def _has_only_lf_newlines(content: bytes) -> bool:
    return b"\r" not in content and b"\n" in content


def _validate_prepared_receipt(
    receipt: WorkspaceReceipt,
    attempt: AttemptRecord,
    exercise: ExerciseRecord,
    root: Path,
    workspace: Path,
) -> None:
    if (
        receipt.state.value != "PREPARED"
        or receipt.attempt_id != attempt.attempt_id
        or receipt.exercise_id != exercise.exercise_id
        or receipt.exercise_version != exercise.exercise_version
        or receipt.template_repository != exercise.template_repository
        or receipt.template_commit != attempt.starting_commit
        or receipt.workspace_root_digest != canonical_path_digest(root)
        or receipt.workspace_path_digest != _direct_child_path_digest(root, workspace)
        or receipt.workspace_relative_path != attempt.attempt_id
    ):
        raise LabValidationError("WORKSPACE_RECEIPT_MISMATCH", "workspace receipt binding differs")


def _validate_quarantined_receipt(
    receipt: WorkspaceReceipt,
    attempt: AttemptRecord,
    exercise: ExerciseRecord,
    root: Path,
    quarantine: Path,
) -> None:
    if (
        receipt.state.value != "QUARANTINED"
        or receipt.attempt_id != attempt.attempt_id
        or receipt.exercise_id != exercise.exercise_id
        or receipt.exercise_version != exercise.exercise_version
        or receipt.template_repository != exercise.template_repository
        or receipt.template_commit != attempt.starting_commit
        or receipt.workspace_root_digest != canonical_path_digest(root)
        or receipt.workspace_path_digest != _direct_child_path_digest(root, quarantine)
        or receipt.workspace_relative_path != f".worker-lab-quarantine-{attempt.attempt_id}"
    ):
        raise LabValidationError("WORKSPACE_RECEIPT_MISMATCH", "quarantined receipt binding differs")


def _quarantined_receipt(receipt: WorkspaceReceipt, quarantine: Path) -> WorkspaceReceipt:
    value = receipt.to_dict()
    value.update({
        "workspace_path_digest": canonical_path_digest(quarantine),
        "workspace_relative_path": f".worker-lab-quarantine-{receipt.attempt_id}",
        "state": "QUARANTINED",
    })
    return WorkspaceReceipt.from_mapping(value)


def _direct_child_path_digest(root: Path, child: Path) -> str:
    _assert_direct_child(child, root, prefix=child.name)
    return canonical_digest({"canonical_path": _path_key(child)})


def _verify_prepared_repository(
    workspace: Path,
    attempt: AttemptRecord,
    context: ContextManifest,
    *,
    run_process: RunProcess,
    timeout: int,
) -> None:
    resolved = _real_directory(workspace, "WORKSPACE_VERIFY_FAILED")
    _assert_no_reparse_tree(resolved)
    _assert_no_nested_git_repository(resolved)
    git_dir = resolved / ".git"
    if not git_dir.is_dir() or _is_reparse(git_dir):
        raise LabValidationError("WORKSPACE_VERIFY_FAILED", "workspace .git must be a real directory")
    top = _git_value(
        ["-C", str(resolved), "rev-parse", "--show-toplevel"],
        "resolve prepared repository",
        run_process,
        timeout,
    )
    if _path_key(Path(top).resolve(strict=True)) != _path_key(resolved):
        raise LabValidationError("WORKSPACE_VERIFY_FAILED", "prepared Git root differs")
    head = _git_value(
        ["-C", str(resolved), "rev-parse", "HEAD"],
        "read prepared HEAD",
        run_process,
        timeout,
    )
    if head != attempt.starting_commit:
        raise LabValidationError("WORKSPACE_VERIFY_FAILED", "prepared HEAD differs")
    branch = _git_value(
        ["-C", str(resolved), "rev-parse", "--abbrev-ref", "HEAD"],
        "read prepared branch",
        run_process,
        timeout,
    )
    if branch != "HEAD":
        raise LabValidationError("WORKSPACE_VERIFY_FAILED", "prepared workspace is not detached")
    dirty = _git_value(
        ["-C", str(resolved), "status", "--porcelain=v1", "--untracked-files=all"],
        "read prepared status",
        run_process,
        timeout,
    )
    if dirty:
        raise LabValidationError("WORKSPACE_VERIFY_FAILED", "prepared workspace is dirty")
    remotes = _git_value(
        ["-C", str(resolved), "remote"], "read prepared remotes", run_process, timeout
    )
    if remotes:
        raise LabValidationError("WORKSPACE_VERIFY_FAILED", "prepared workspace retains a remote")
    if os.path.lexists(git_dir / "objects" / "info" / "alternates"):
        raise LabValidationError(
            "WORKSPACE_VERIFY_FAILED", "prepared workspace shares a Git object store"
        )
    verify_context_files(context, resolved)


def _git(
    arguments: Sequence[str],
    operation: str,
    run_process: RunProcess,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    command = [
        "git",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "core.longpaths=true",
        "-c",
        "credential.helper=",
        *arguments,
    ]
    try:
        result = run_process(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            env=_git_environment(os.environ),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise LabValidationError("WORKSPACE_GIT_TIMEOUT", f"Git timed out: {operation}") from exc
    except OSError as exc:
        raise LabValidationError("WORKSPACE_GIT_UNAVAILABLE", f"Git unavailable: {operation}") from exc
    if result.returncode != 0:
        raise LabValidationError("WORKSPACE_GIT_FAILED", f"Git failed: {operation}")
    return result


def _git_value(
    arguments: Sequence[str],
    operation: str,
    run_process: RunProcess,
    timeout: int,
) -> str:
    return _git(arguments, operation, run_process, timeout).stdout.strip()


def _git_bytes(
    arguments: Sequence[str],
    operation: str,
    run_process: RunProcess,
    timeout: int,
) -> bytes:
    command = [
        "git",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "core.longpaths=true",
        "-c",
        "credential.helper=",
        *arguments,
    ]
    try:
        result = run_process(
            command,
            check=False,
            capture_output=True,
            text=False,
            stdin=subprocess.DEVNULL,
            env=_git_environment(os.environ),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise LabValidationError("WORKSPACE_GIT_TIMEOUT", f"Git timed out: {operation}") from exc
    except OSError as exc:
        raise LabValidationError("WORKSPACE_GIT_UNAVAILABLE", f"Git unavailable: {operation}") from exc
    if result.returncode != 0 or not isinstance(result.stdout, bytes):
        raise LabValidationError("WORKSPACE_GIT_FAILED", f"Git failed: {operation}")
    return result.stdout


def _git_environment(source: Mapping[str, str]) -> dict[str, str]:
    clean: dict[str, str] = {}
    for name, value in source.items():
        upper = name.upper()
        if (
            upper.startswith("GITHUB_")
            or upper in _GITHUB_CREDENTIAL_NAMES
            or upper.startswith("ACTIONS_ID_TOKEN_REQUEST_")
            or upper in _GIT_REDIRECTION_NAMES
            or upper.startswith("GIT_CONFIG_")
        ):
            continue
        clean[name] = value
    clean.update({
        "GCM_INTERACTIVE": "Never",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
    })
    return clean


def _real_directory(candidate: Path, code: str) -> Path:
    absolute = candidate.absolute()
    try:
        _assert_no_reparse_components(absolute)
        resolved = absolute.resolve(strict=True)
        _assert_no_reparse_components(resolved)
    except (OSError, RuntimeError) as exc:
        raise LabValidationError(code, "directory is missing or uses path indirection") from exc
    if not resolved.is_dir():
        raise LabValidationError(code, "path must be a real directory")
    return resolved


def _assert_no_reparse_components(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if os.path.lexists(current) and _is_reparse(current):
            raise LabValidationError("WORKSPACE_PATH_INDIRECTION", f"reparse path rejected: {current}")


def _assert_no_reparse_tree(root: Path, *, skip_git: bool = False) -> None:
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        if skip_git and current_path == root:
            directories[:] = [name for name in directories if name != ".git"]
        for name in (*directories, *files):
            child = current_path / name
            if _is_reparse(child):
                raise LabValidationError(
                    "WORKSPACE_PATH_INDIRECTION", f"reparse entry rejected: {child}"
                )


def _assert_no_nested_git_repository(root: Path) -> None:
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        if current_path == root:
            directories[:] = [name for name in directories if name != ".git"]
        if ".git" in directories or ".git" in files:
            raise LabValidationError(
                "WORKSPACE_VERIFY_FAILED", "nested Git repository is forbidden"
            )


def _is_reparse(path: Path) -> bool:
    if path.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(path)):
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(marker and attributes & marker)


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path)).replace("\\", "/")


def _overlaps(first: Path, second: Path) -> bool:
    first_key = Path(_path_key(first))
    second_key = Path(_path_key(second))
    return (
        first_key == second_key
        or first_key.is_relative_to(second_key)
        or second_key.is_relative_to(first_key)
    )


def _assert_direct_child(path: Path, parent: Path, *, prefix: str) -> None:
    if path.parent != parent or not path.name.startswith(prefix):
        raise LabValidationError("WORKSPACE_STAGE_INVALID", "staging path identity differs")


def _staging_prefix(attempt_id: str) -> str:
    return f".wl-stage-{attempt_id[-12:]}-"


def _read_exact_receipt(
    store: AtomicRecordStore, relative: str, expected: WorkspaceReceipt
) -> WorkspaceReceipt | None:
    try:
        value = store.read(relative, WorkspaceReceipt.from_mapping)
    except LabValidationError as exc:
        if exc.code == "STORAGE_RECORD_MISSING":
            return None
        raise
    return value if value == expected else None


def _read_attempt_if_available(store: AttemptStore, attempt_id: str) -> AttemptRecord | None:
    try:
        return store.read(attempt_id)
    except LabValidationError:
        return None


def _compensate_preparation(
    root: Path,
    final_workspace: Path,
    staging_parent: Path | None,
    receipt_path: Path | None,
    *,
    published: bool,
) -> str | None:
    try:
        if published and os.path.lexists(final_workspace):
            _assert_direct_child(final_workspace, root, prefix=final_workspace.name)
            if _is_reparse(final_workspace) or not final_workspace.is_dir():
                raise OSError("published workspace identity changed")
            _remove_tree(final_workspace)
        if staging_parent is not None and os.path.lexists(staging_parent):
            _assert_direct_child(
                staging_parent,
                root,
                prefix=_staging_prefix(final_workspace.name),
            )
            if _is_reparse(staging_parent) or not staging_parent.is_dir():
                raise OSError("staging workspace identity changed")
            _remove_tree(staging_parent)
        if receipt_path is not None and os.path.lexists(receipt_path):
            if _is_reparse(receipt_path) or not receipt_path.is_file():
                raise OSError("receipt identity changed")
            receipt_path.unlink()
        return None
    except (OSError, LabValidationError) as exc:
        return str(exc)


def _remove_tree(path: Path) -> None:
    _assert_no_reparse_tree(path)
    shutil.rmtree(path, onexc=_remove_readonly)


def _remove_readonly(function: Callable[..., object], path: str, error: BaseException) -> None:
    if isinstance(error, FileNotFoundError):
        return
    try:
        os.chmod(path, stat.S_IWRITE)
        function(path)
    except FileNotFoundError:
        return
    except OSError:
        raise error
