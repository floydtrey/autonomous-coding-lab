from pathlib import Path
import subprocess

import pytest

from tools.codex_runtime import CodexExecution
from tools.consumer_profile import ConsumerProfileError, MINE_TRACKER_PROFILE
from tools.context_probe import run_context_probe


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=repo, text=True, encoding="utf-8", capture_output=True, check=True
    ).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "consumer"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.invalid")
    for path in MINE_TRACKER_PROFILE.authority_paths:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("authority\n", encoding="utf-8")
    (root / "app").mkdir()
    (root / "app" / "assets.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def test_probe_uses_read_only_codex_and_reverifies_repository(tmp_path):
    root = _repo(tmp_path)
    seen = []

    def executor(request):
        seen.append(request)
        return CodexExecution(("codex",), 0, "bounded proposal", "")

    packet, result = run_context_probe(
        repo_root=root,
        framework_repo=tmp_path / "framework",
        objective="Analyze an asset change",
        allowed_paths=("app/assets.py",),
        executor=executor,
    )
    assert seen[0].sandbox == "read-only"
    assert seen[0].target_repo == root
    assert "Do not modify files yet" in seen[0].prompt
    assert result.context_digest == packet.digest()
    assert result.response == "bounded proposal"
    assert _git(root, "status", "--porcelain") == ""


def test_probe_fails_if_executor_changes_repository(tmp_path):
    root = _repo(tmp_path)

    def executor(request):
        (request.target_repo / "app" / "assets.py").write_text("VALUE = 2\n", encoding="utf-8")
        return CodexExecution(("codex",), 0, "proposal", "")

    with pytest.raises(ConsumerProfileError) as error:
        run_context_probe(
            repo_root=root,
            framework_repo=tmp_path / "framework",
            objective="Analyze an asset change",
            allowed_paths=("app/assets.py",),
            executor=executor,
        )
    assert error.value.code == "CONTEXT_REPOSITORY_DIRTY"


def test_probe_rejects_empty_codex_analysis(tmp_path):
    root = _repo(tmp_path)

    def executor(request):
        return CodexExecution(("codex",), 0, "  ", "")

    with pytest.raises(ValueError, match="no analysis"):
        run_context_probe(
            repo_root=root,
            framework_repo=tmp_path / "framework",
            objective="Analyze an asset change",
            allowed_paths=("app/assets.py",),
            executor=executor,
        )
