from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path, PurePosixPath
from typing import Sequence


class RepositoryStateError(RuntimeError):
    """A Git-backed coding workspace could not be inspected safely."""


def repository_head(repository_root: Path) -> str:
    """Return the exact HEAD object name for a Git-backed coding workspace."""
    value = _run_git(repository_root, "rev-parse", "HEAD").strip().lower()
    if not _is_full_sha(value):
        raise RepositoryStateError(
            "Git-backed workspace HEAD is not a normal 40-character Git SHA"
        )
    return value


def changed_paths(repository_root: Path, base_sha: str) -> list[str]:
    """Return tracked and untracked paths changed from one exact Git base."""
    changed: set[str] = set()
    for arguments in (
        ("diff", "--name-only", "--diff-filter=ACDMRT", base_sha),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        for line in _run_git(repository_root, *arguments).splitlines():
            if line.strip():
                changed.add(_normalise_repository_path(line.strip()))
    return sorted(changed)


def require_clean_workspace(repository_root: Path) -> None:
    """Fail unless the Git-backed coding workspace has no tracked or untracked changes."""
    status = _run_git(
        repository_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if status.strip():
        raise RepositoryStateError("Git-backed coding workspace must be clean")


def require_repository_root(repository_root: Path) -> Path:
    """Resolve and validate the root of a Git-backed coding workspace."""
    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise RepositoryStateError("Git-backed coding workspace root is missing")
    top_level = Path(
        _run_git(root, "rev-parse", "--show-toplevel").strip()
    ).resolve()
    if top_level != root:
        raise RepositoryStateError(
            "Git-backed coding workspace path is not the repository root"
        )
    return root


def candidate_content_digest(repository_root: Path, paths: Sequence[str]) -> str:
    """Digest exact candidate path names, kinds, and current bytes deterministically."""
    root = Path(repository_root).resolve()
    digest = hashlib.sha256()
    for path in sorted(paths):
        normal = _normalise_repository_path(path)
        candidate = root.joinpath(*PurePosixPath(normal).parts)
        digest.update(normal.encode("utf-8"))
        digest.update(b"\0")
        if candidate.is_file():
            digest.update(b"FILE\0")
            digest.update(candidate.read_bytes())
        elif candidate.exists():
            digest.update(b"NONFILE\0")
        else:
            digest.update(b"ABSENT\0")
    return "sha256:" + digest.hexdigest()


def _normalise_repository_path(value: str) -> str:
    if not isinstance(value, str):
        raise RepositoryStateError("repository-relative path must be text")
    raw = value.strip().replace("\\", "/")
    candidate = PurePosixPath(raw)
    if (
        not raw
        or candidate.is_absolute()
        or raw.startswith("/")
        or ".." in candidate.parts
        or candidate.as_posix() != raw
        or raw == "."
        or ":" in candidate.parts[0]
    ):
        raise RepositoryStateError(f"invalid repository-relative path: {value!r}")
    return raw


def _is_full_sha(value: str) -> bool:
    return len(value) == 40 and all(character in "0123456789abcdef" for character in value)


def _run_git(repository_root: Path, *arguments: str) -> str:
    try:
        process = subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise RepositoryStateError(f"Git inspection could not start: {exc}") from exc
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "Git command failed").strip()
        raise RepositoryStateError(
            f"git {' '.join(arguments)} failed: {detail}"
        )
    return process.stdout
