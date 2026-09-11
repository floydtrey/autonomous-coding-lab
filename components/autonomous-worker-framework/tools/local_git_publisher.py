from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Sequence

try:
    from tools.repository_state import candidate_content_digest, changed_paths, repository_head
    from tools.repository_handoff import RepositoryHandoff, build_repository_handoff
    from tools.worker_result import WorkerResult, validate_worker_result
except ModuleNotFoundError:  # direct execution support
    from repository_state import candidate_content_digest, changed_paths, repository_head  # type: ignore
    from repository_handoff import RepositoryHandoff, build_repository_handoff  # type: ignore
    from worker_result import WorkerResult, validate_worker_result  # type: ignore


CONTRACT_VERSION = "local-publication:v1"
DEFAULT_AUTHOR_NAME = "Autonomous Worker"
DEFAULT_AUTHOR_EMAIL = "autonomous-worker@localhost"


class LocalPublicationError(RuntimeError):
    """The candidate could not be converted into a verified local commit."""

    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


@dataclass(frozen=True)
class LocalPublication:
    contract_version: str
    task_id: str
    consumer: str
    repository_handoff_digest: str
    base_sha: str
    candidate_sha: str
    candidate_content_digest: str
    changed_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, pretty: bool = False) -> str:
        options: dict[str, Any] = {"sort_keys": True}
        if pretty:
            options["indent"] = 2
        else:
            options["separators"] = (",", ":")
        return json.dumps(self.to_dict(), **options)


def repository_handoff_digest(handoff: RepositoryHandoff) -> str:
    encoded = handoff.to_json().encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def publish_local_candidate(
    result: WorkerResult,
    repo_root: Path,
    *,
    commit_message: str,
    author_name: str = DEFAULT_AUTHOR_NAME,
    author_email: str = DEFAULT_AUTHOR_EMAIL,
) -> tuple[WorkerResult, LocalPublication]:
    message = _required_single_line("commit_message", commit_message)
    name = _required_single_line("author_name", author_name)
    email = _required_single_line("author_email", author_email)
    root = repo_root.resolve()

    # Rebuild immediately before staging so a stale or tampered candidate fails closed.
    handoff = build_repository_handoff(result, root)
    _git(root, "add", "-A", "--", *handoff.changed_paths, code="STAGING_FAILED")

    staged_paths = tuple(_git_paths(root, "diff", "--cached", "--name-only", "--diff-filter=ACDMRT"))
    if staged_paths != handoff.changed_paths:
        raise LocalPublicationError(
            "STAGED_PATHS_MISMATCH",
            f"expected staged paths={list(handoff.changed_paths)}; observed {list(staged_paths)}",
        )

    _git(
        root,
        "-c",
        f"user.name={name}",
        "-c",
        f"user.email={email}",
        "commit",
        "--no-gpg-sign",
        "-m",
        message,
        code="COMMIT_FAILED",
    )

    candidate_sha = repository_head(root)
    parent_sha = _git(root, "rev-parse", f"{candidate_sha}^", code="COMMIT_VERIFICATION_FAILED").strip().lower()
    if parent_sha != handoff.base_sha:
        raise LocalPublicationError(
            "COMMIT_PARENT_MISMATCH",
            f"expected candidate parent {handoff.base_sha}; observed {parent_sha}",
        )

    committed_paths = tuple(_git_paths(root, "diff-tree", "--no-commit-id", "--name-only", "-r", candidate_sha))
    if committed_paths != handoff.changed_paths:
        raise LocalPublicationError(
            "COMMITTED_PATHS_MISMATCH",
            f"expected committed paths={list(handoff.changed_paths)}; observed {list(committed_paths)}",
        )
    if changed_paths(root, candidate_sha):
        raise LocalPublicationError("POST_COMMIT_DIRTY", "target repository changed during local publication")
    observed_digest = candidate_content_digest(root, handoff.changed_paths)
    if observed_digest != handoff.candidate_content_digest:
        raise LocalPublicationError(
            "COMMITTED_DIGEST_MISMATCH",
            f"expected {handoff.candidate_content_digest}; observed {observed_digest}",
        )

    committed_result = replace(
        result,
        candidate_sha=candidate_sha,
        workspace_state="committed-candidate",
    )
    validate_worker_result(committed_result)
    publication = LocalPublication(
        contract_version=CONTRACT_VERSION,
        task_id=handoff.task_id,
        consumer=handoff.consumer,
        repository_handoff_digest=repository_handoff_digest(handoff),
        base_sha=handoff.base_sha,
        candidate_sha=candidate_sha,
        candidate_content_digest=handoff.candidate_content_digest,
        changed_paths=handoff.changed_paths,
    )
    return committed_result, publication


def _required_single_line(field: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LocalPublicationError("INVALID_PUBLICATION_INPUT", f"{field} must be non-empty")
    clean = value.strip()
    if "\n" in clean or "\r" in clean or "\x00" in clean:
        raise LocalPublicationError("INVALID_PUBLICATION_INPUT", f"{field} must be a single line")
    return clean


def _git(repo_root: Path, *args: str, code: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "git command failed").strip()
        raise LocalPublicationError(code, detail)
    return process.stdout


def _git_paths(repo_root: Path, *args: str) -> Sequence[str]:
    output = _git(repo_root, *args, code="GIT_INSPECTION_FAILED")
    return sorted(line.strip().replace("\\", "/") for line in output.splitlines() if line.strip())
