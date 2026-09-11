import inspect
import subprocess
from pathlib import Path

import pytest

from tools.consumer_profile import (
    ConsumerProfileError,
    build_context_packet,
    build_context_prompt,
    verify_context_packet,
)
from tools.code_task import run_code_task
from current_test_fixtures import GENERIC_PROFILE


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
    for path in GENERIC_PROFILE.authority_paths:
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


def test_generic_profile_is_deterministic_and_has_validation():
    assert GENERIC_PROFILE.digest() == GENERIC_PROFILE.digest()
    assert GENERIC_PROFILE.digest().startswith("sha256:")
    assert GENERIC_PROFILE.full_validation


def test_generic_context_and_code_task_seams_require_an_explicit_profile():
    for operation in (build_context_packet, verify_context_packet, run_code_task):
        assert (
            inspect.signature(operation).parameters["profile"].default
            is inspect.Parameter.empty
        )


def test_context_packet_binds_head_authority_task_files_and_scope(tmp_path):
    root = _repo(tmp_path)
    packet = build_context_packet(
        root,
        allowed_paths=("app/assets.py",),
        task_context_paths=("tests/test_assets.py",),
        profile=GENERIC_PROFILE,
    )
    assert packet.repository_head == _git(root, "rev-parse", "HEAD")
    assert packet.allowed_paths == ("app/assets.py",)
    assert [item.path for item in packet.authority_files] == list(GENERIC_PROFILE.authority_paths)
    assert [item.path for item in packet.task_files] == ["tests/test_assets.py"]
    assert packet.digest().startswith("sha256:")
    verify_context_packet(packet, root, profile=GENERIC_PROFILE)


def test_context_prompt_is_read_only_and_explains_exact_boundary(tmp_path):
    root = _repo(tmp_path)
    packet = build_context_packet(
        root, allowed_paths=("app/assets.py",), profile=GENERIC_PROFILE
    )
    prompt = build_context_prompt(packet, objective="  Explain   a bounded asset change. ")
    assert "Objective: Explain a bounded asset change." in prompt
    assert "The only paths that may be changed are:\n- app/assets.py" in prompt
    assert "Do not modify files yet" in prompt
    assert packet.digest() in prompt


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/ci.yml",
        "protected/state.db",
        "policy.lock",
    ],
)
def test_protected_paths_cannot_be_writable(tmp_path, path):
    root = _repo(tmp_path)
    with pytest.raises(ConsumerProfileError) as error:
        build_context_packet(root, allowed_paths=(path,), profile=GENERIC_PROFILE)
    assert error.value.code == "CONTEXT_SCOPE_PROTECTED"


def test_context_paths_are_read_only_and_cannot_overlap_writable_scope(tmp_path):
    root = _repo(tmp_path)
    with pytest.raises(ConsumerProfileError) as error:
        build_context_packet(
            root,
            allowed_paths=("app/assets.py",),
            task_context_paths=("app/assets.py",),
            profile=GENERIC_PROFILE,
        )
    assert error.value.code == "CONTEXT_SCOPE_INVALID"


def test_dirty_repository_fails_before_packet_creation(tmp_path):
    root = _repo(tmp_path)
    (root / "app" / "assets.py").write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ConsumerProfileError) as error:
        build_context_packet(
            root, allowed_paths=("app/assets.py",), profile=GENERIC_PROFILE
        )
    assert error.value.code == "CONTEXT_REPOSITORY_DIRTY"


def test_verification_fails_if_head_moves(tmp_path):
    root = _repo(tmp_path)
    packet = build_context_packet(
        root, allowed_paths=("app/assets.py",), profile=GENERIC_PROFILE
    )
    (root / "new.txt").write_text("new\n", encoding="utf-8")
    _git(root, "add", "new.txt")
    _git(root, "commit", "-qm", "move head")
    with pytest.raises(ConsumerProfileError) as error:
        verify_context_packet(packet, root, profile=GENERIC_PROFILE)
    assert error.value.code == "CONTEXT_IDENTITY_CHANGED"


def test_verification_fails_if_authority_bytes_change(tmp_path):
    root = _repo(tmp_path)
    packet = build_context_packet(
        root, allowed_paths=("app/assets.py",), profile=GENERIC_PROFILE
    )
    authority = root / GENERIC_PROFILE.authority_paths[0]
    authority.write_text("changed authority\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "change authority")
    moved_packet = packet.__class__(
        **{**packet.__dict__, "repository_head": _git(root, "rev-parse", "HEAD")}
    )
    with pytest.raises(ConsumerProfileError) as error:
        verify_context_packet(moved_packet, root, profile=GENERIC_PROFILE)
    assert error.value.code == "CONTEXT_AUTHORITY_CHANGED"


def test_missing_task_context_fails_closed(tmp_path):
    root = _repo(tmp_path)
    with pytest.raises(ConsumerProfileError) as error:
        build_context_packet(
            root,
            allowed_paths=("app/assets.py",),
            task_context_paths=("tests/missing.py",),
            profile=GENERIC_PROFILE,
        )
    assert error.value.code == "CONTEXT_FILE_MISSING"
