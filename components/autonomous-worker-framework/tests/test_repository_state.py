from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from tools.repository_state import (
    RepositoryStateError,
    candidate_content_digest,
    changed_paths,
    repository_head,
    require_clean_workspace,
    require_repository_root,
)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", *arguments),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "coding-workspace"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.invalid")
    (root / "tracked.txt").write_bytes(b"before\n")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-qm", "baseline")
    return root


def test_git_workspace_state_is_exact_and_deterministic(tmp_path):
    root = _repository(tmp_path)
    base = repository_head(root)

    assert len(base) == 40
    assert require_repository_root(root) == root.resolve()
    require_clean_workspace(root)

    (root / "tracked.txt").write_bytes(b"after\n")
    (root / "untracked.txt").write_bytes(b"new\n")

    assert changed_paths(root, base) == ["tracked.txt", "untracked.txt"]
    digest = hashlib.sha256()
    for path, content in (("tracked.txt", b"after\n"), ("untracked.txt", b"new\n")):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0FILE\0")
        digest.update(content)
    assert candidate_content_digest(root, ("untracked.txt", "tracked.txt")) == (
        "sha256:" + digest.hexdigest()
    )
    with pytest.raises(RepositoryStateError):
        require_clean_workspace(root)


def test_candidate_digest_distinguishes_non_file_and_absent_paths(tmp_path):
    root = _repository(tmp_path)
    (root / "directory").mkdir()

    assert candidate_content_digest(root, ("directory",)) != candidate_content_digest(
        root, ("absent",)
    )


@pytest.mark.parametrize("path", ("../escape", "/absolute", "C:/absolute", "."))
def test_candidate_digest_rejects_non_relative_paths(tmp_path, path):
    root = _repository(tmp_path)

    with pytest.raises(RepositoryStateError):
        candidate_content_digest(root, (path,))


def test_repository_root_rejects_a_subdirectory_and_non_repository(tmp_path):
    root = _repository(tmp_path)
    child = root / "child"
    child.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(RepositoryStateError):
        require_repository_root(child)
    with pytest.raises(RepositoryStateError):
        repository_head(outside)


@pytest.mark.parametrize(
    "module_name",
    ("code_task.py", "local_git_publisher.py", "repository_handoff.py"),
)
def test_current_consumers_do_not_import_commissioning_harness_helpers(module_name):
    source = (Path(__file__).resolve().parents[1] / "tools" / module_name).read_text(
        encoding="utf-8"
    )

    assert "local_worker_harness" not in source
