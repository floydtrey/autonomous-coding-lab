from pathlib import Path
import subprocess

import pytest

from tools.consumer_profile import (
    ConsumerProfileError,
    MINE_TRACKER_PROFILE,
    build_context_packet,
    build_context_prompt,
    verify_context_packet,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=repo, text=True, encoding="utf-8", capture_output=True, check=True
    ).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "mine-tracker"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.invalid")
    for path in MINE_TRACKER_PROFILE.authority_paths:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"authority: {path}\n", encoding="utf-8")
    (root / "app").mkdir()
    (root / "tests").mkdir()
    (root / "app" / "assets.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "tests" / "test_assets.py").write_text("def test_assets():\n    assert True\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def test_mine_tracker_profile_is_deterministic_and_uses_current_ci_commands():
    assert MINE_TRACKER_PROFILE.digest() == MINE_TRACKER_PROFILE.digest()
    assert MINE_TRACKER_PROFILE.digest().startswith("sha256:")
    assert [item.argv for item in MINE_TRACKER_PROFILE.full_validation] == [
        ("python", "-m", "compileall", "-q", "app", "tests", "tools", "run_app.py"),
        ("python", "-m", "pytest", "-q"),
        ("node", "--check", "web/app.js"),
        ("node", "--check", "web/lite_ui.js"),
    ]


def test_context_packet_binds_head_authority_task_files_and_scope(tmp_path):
    root = _repo(tmp_path)
    packet = build_context_packet(
        root,
        allowed_paths=("app/assets.py",),
        task_context_paths=("tests/test_assets.py",),
    )
    assert packet.repository_head == _git(root, "rev-parse", "HEAD")
    assert packet.allowed_paths == ("app/assets.py",)
    assert [item.path for item in packet.authority_files] == list(MINE_TRACKER_PROFILE.authority_paths)
    assert [item.path for item in packet.task_files] == ["tests/test_assets.py"]
    assert packet.digest().startswith("sha256:")
    verify_context_packet(packet, root)


def test_context_prompt_is_read_only_and_explains_exact_boundary(tmp_path):
    root = _repo(tmp_path)
    packet = build_context_packet(root, allowed_paths=("app/assets.py",))
    prompt = build_context_prompt(packet, objective="  Explain   a bounded asset change. ")
    assert "Objective: Explain a bounded asset change." in prompt
    assert "The only paths that may be changed are:\n- app/assets.py" in prompt
    assert "Do not modify files yet" in prompt
    assert packet.digest() in prompt


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/ci.yml",
        "data/mine_tracker.db",
        "docs/governance/MINE_TRACKER_CURRENT_BASELINE.md",
        "tests/test_autonomy_controller.py",
        "tools/autonomy_controller.py",
    ],
)
def test_protected_paths_cannot_be_writable(tmp_path, path):
    root = _repo(tmp_path)
    with pytest.raises(ConsumerProfileError) as error:
        build_context_packet(root, allowed_paths=(path,))
    assert error.value.code == "CONTEXT_SCOPE_PROTECTED"


def test_context_paths_are_read_only_and_cannot_overlap_writable_scope(tmp_path):
    root = _repo(tmp_path)
    with pytest.raises(ConsumerProfileError) as error:
        build_context_packet(
            root,
            allowed_paths=("app/assets.py",),
            task_context_paths=("app/assets.py",),
        )
    assert error.value.code == "CONTEXT_SCOPE_INVALID"


def test_dirty_repository_fails_before_packet_creation(tmp_path):
    root = _repo(tmp_path)
    (root / "app" / "assets.py").write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ConsumerProfileError) as error:
        build_context_packet(root, allowed_paths=("app/assets.py",))
    assert error.value.code == "CONTEXT_REPOSITORY_DIRTY"


def test_verification_fails_if_head_moves(tmp_path):
    root = _repo(tmp_path)
    packet = build_context_packet(root, allowed_paths=("app/assets.py",))
    (root / "new.txt").write_text("new\n", encoding="utf-8")
    _git(root, "add", "new.txt")
    _git(root, "commit", "-qm", "move head")
    with pytest.raises(ConsumerProfileError) as error:
        verify_context_packet(packet, root)
    assert error.value.code == "CONTEXT_IDENTITY_CHANGED"


def test_verification_fails_if_authority_bytes_change(tmp_path):
    root = _repo(tmp_path)
    packet = build_context_packet(root, allowed_paths=("app/assets.py",))
    authority = root / MINE_TRACKER_PROFILE.authority_paths[0]
    authority.write_text("changed authority\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "change authority")
    moved_packet = packet.__class__(
        **{**packet.__dict__, "repository_head": _git(root, "rev-parse", "HEAD")}
    )
    with pytest.raises(ConsumerProfileError) as error:
        verify_context_packet(moved_packet, root)
    assert error.value.code == "CONTEXT_AUTHORITY_CHANGED"


def test_missing_task_context_fails_closed(tmp_path):
    root = _repo(tmp_path)
    with pytest.raises(ConsumerProfileError) as error:
        build_context_packet(
            root,
            allowed_paths=("app/assets.py",),
            task_context_paths=("tests/missing.py",),
        )
    assert error.value.code == "CONTEXT_FILE_MISSING"
