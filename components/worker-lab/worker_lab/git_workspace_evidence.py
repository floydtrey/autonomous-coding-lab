from __future__ import annotations

import os
import subprocess
from pathlib import Path, PurePosixPath

from .errors import LabValidationError
from .integration_v3 import GitWorkspaceResultEvidence, InvocationRecordV3
from .models import WorkspaceReceipt, WorkspaceReceiptState
from .storage import AtomicRecordStore
from .windows_job import inspect_launch_workspace
from .workspace import canonical_path_digest


_GIT_TIMEOUT_SECONDS = 30


def inspect_git_workspace_result(
    record: InvocationRecordV3,
    *,
    state_root: Path,
    workspace_path: Path,
) -> GitWorkspaceResultEvidence:
    """Observe Git-backed workspace facts independently of framework/provider output."""
    source = record.source_state
    if source is None or source.backend_id != "git-workspace:v1":
        raise LabValidationError(
            "INTEGRATION_V3_SOURCE_STATE_INVALID",
            "current coding result requires sealed Git workspace source state",
        )
    receipt = AtomicRecordStore(state_root).read(
        f"workspaces/{record.attempt_id}.json",
        WorkspaceReceipt.from_mapping,
    )
    observed = inspect_launch_workspace(workspace_path)
    if (
        receipt.state is not WorkspaceReceiptState.PREPARED
        or receipt.attempt_id != record.attempt_id
        or receipt.template_commit != source.base_commit
        or receipt.digest() != source.workspace_receipt_digest
        or receipt.workspace_root_digest != source.workspace_root_digest
        or receipt.workspace_path_digest != source.workspace_path_digest
        or canonical_path_digest(observed.workspace_path.parent) != source.workspace_root_digest
        or observed.workspace_path_digest != source.workspace_path_digest
        or observed.observed_head != source.base_commit
    ):
        raise LabValidationError(
            "INTEGRATION_V3_SOURCE_STATE_INVALID",
            "independent Git workspace evidence differs from the sealed source state",
        )
    changed = _changed_paths(observed.workspace_path, source.base_commit)
    return GitWorkspaceResultEvidence.from_mapping({
        "schema_version": "worker-lab-git-workspace-result-evidence:v1",
        "backend_id": source.backend_id,
        "base_commit": source.base_commit,
        "observed_head": observed.observed_head,
        "workspace_receipt_digest": receipt.digest(),
        "workspace_root_digest": receipt.workspace_root_digest,
        "workspace_path_digest": receipt.workspace_path_digest,
        "workspace_content_digest": observed.content_digest,
        "workspace_state": "changed" if changed else "unchanged",
        "changed_paths": list(changed),
    })


def _changed_paths(workspace_path: Path, base_commit: str) -> tuple[str, ...]:
    found: set[str] = set()
    for arguments in (
        ("diff", "--name-only", "--diff-filter=ACDMRT", base_commit),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        for line in _git(workspace_path, *arguments).splitlines():
            if line:
                found.add(_relative_path(line))
    check = _git_process(
        workspace_path,
        "-c",
        "core.whitespace=trailing-space,space-before-tab,cr-at-eol",
        "diff",
        "--check",
    )
    if check.returncode != 0:
        raise LabValidationError(
            "INTEGRATION_BOUNDARY_FAILED",
            "candidate diff integrity failed",
        )
    return tuple(sorted(found))


def _git(root: Path, *arguments: str) -> str:
    process = _git_process(root, *arguments)
    if process.returncode != 0:
        raise LabValidationError(
            "INTEGRATION_BOUNDARY_FAILED",
            "candidate Git workspace inspection failed",
        )
    return process.stdout.strip()


def _git_process(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
    }
    try:
        return subprocess.run(
            ("git", "-c", f"core.hooksPath={os.devnull}", "-c", "credential.helper=", *arguments),
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LabValidationError(
            "INTEGRATION_BOUNDARY_FAILED",
            "candidate Git workspace inspection could not complete",
        ) from exc


def _relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\\" in value:
        raise LabValidationError("INTEGRATION_V3_SCOPE_INVALID", "candidate path is invalid")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or value.startswith("/")
        or ".." in candidate.parts
        or candidate.as_posix() != value
        or value == "."
        or ":" in candidate.parts[0]
    ):
        raise LabValidationError("INTEGRATION_V3_SCOPE_INVALID", "candidate path is invalid")
    return value
