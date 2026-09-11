import subprocess
from pathlib import Path

from worker_lab.windows_job import inspect_launch_workspace


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def test_launch_workspace_inspector_seals_exact_clean_git_root(tmp_path):
    workspace = (tmp_path / "workspace").resolve()
    workspace.mkdir()
    (workspace / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(workspace, "init")
    _git(workspace, "config", "core.autocrlf", "false")
    _git(workspace, "config", "user.email", "fixture@example.com")
    _git(workspace, "config", "user.name", "Fixture")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-m", "fixture")
    _git(workspace, "checkout", "--detach")
    evidence = inspect_launch_workspace(workspace)
    assert evidence.workspace_path == workspace
    assert evidence.observed_head == _git(workspace, "rev-parse", "HEAD")
    assert evidence.status == ""
    assert evidence.content_digest.startswith("sha256:")
