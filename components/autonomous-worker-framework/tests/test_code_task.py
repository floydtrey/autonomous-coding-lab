from pathlib import Path
import subprocess
from dataclasses import replace

import pytest

from tools.code_task import CodeTaskError, build_code_task, run_code_task
from tools.consumer_profile import MINE_TRACKER_PROFILE, ValidationCommand, build_context_packet
from tools.worker_runtime import WorkerExecution


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
    (root / "tests").mkdir()
    (root / "tests" / "test_assets.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def _contract(root: Path):
    packet = build_context_packet(
        root,
        allowed_paths=("tests/test_assets.py",),
        profile=MINE_TRACKER_PROFILE,
    )
    command = ValidationCommand("Check candidate", ("git", "diff", "--check"), 10)
    packet = replace(packet, full_validation=(command,))
    contract = build_code_task(
        packet,
        task_id="MT-TEST-1",
        objective="Add archived asset regression coverage",
        expected_changed_paths=("tests/test_assets.py",),
        acceptance_criteria=("The focused regression passes.",),
        quick_validation=(command,),
    )
    return packet, contract


def test_general_code_task_runs_in_workspace_write_and_validates(tmp_path):
    root = _repo(tmp_path)
    packet, contract = _contract(root)
    seen = []

    def executor(request):
        seen.append(request)
        (root / "tests" / "test_assets.py").write_text("VALUE = 2\n", encoding="utf-8")
        return WorkerExecution(("fake-provider",), 0, "implemented test", "")

    result = run_code_task(
        contract,
        packet,
        repo_root=root,
        framework_repo=tmp_path / "framework",
        profile=MINE_TRACKER_PROFILE,
        executor=executor,
    )
    assert seen[0].sandbox == "workspace-write"
    assert result.changed_paths == ("tests/test_assets.py",)
    assert result.ready_for_handoff is True
    assert result.task_digest == contract.digest()


def test_out_of_scope_worker_change_stops_before_validation(tmp_path):
    root = _repo(tmp_path)
    packet, contract = _contract(root)

    def executor(request):
        (root / "unexpected.py").write_text("bad\n", encoding="utf-8")
        return WorkerExecution(("fake-provider",), 0, "done", "")

    with pytest.raises(CodeTaskError) as error:
        run_code_task(
            contract,
            packet,
            repo_root=root,
            framework_repo=tmp_path / "framework",
            profile=MINE_TRACKER_PROFILE,
            executor=executor,
        )
    assert error.value.code == "CODE_TASK_BOUNDARY_FAILED"


def test_worker_commit_is_rejected(tmp_path):
    root = _repo(tmp_path)
    packet, contract = _contract(root)

    def executor(request):
        (root / "tests" / "test_assets.py").write_text("VALUE = 2\n", encoding="utf-8")
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "forbidden")
        return WorkerExecution(("fake-provider",), 0, "done", "")

    with pytest.raises(CodeTaskError) as error:
        run_code_task(
            contract,
            packet,
            repo_root=root,
            framework_repo=tmp_path / "framework",
            profile=MINE_TRACKER_PROFILE,
            executor=executor,
        )
    assert error.value.code == "CODE_TASK_HEAD_CHANGED"


def test_task_cannot_exceed_context_scope(tmp_path):
    root = _repo(tmp_path)
    packet = build_context_packet(
        root,
        allowed_paths=("tests/test_assets.py",),
        profile=MINE_TRACKER_PROFILE,
    )
    with pytest.raises(CodeTaskError) as error:
        build_code_task(
            packet,
            task_id="MT-TEST-1",
            objective="Bad scope",
            expected_changed_paths=("app/assets.py",),
            acceptance_criteria=("No",),
            quick_validation=(ValidationCommand("Check", ("git", "status"), 10),),
        )
    assert error.value.code == "CODE_TASK_SCOPE_INVALID"


def test_validation_stops_at_first_failure(tmp_path):
    root = _repo(tmp_path)
    packet = build_context_packet(
        root,
        allowed_paths=("tests/test_assets.py",),
        profile=MINE_TRACKER_PROFILE,
    )
    contract = build_code_task(
        packet,
        task_id="MT-TEST-1",
        objective="Fail validation",
        expected_changed_paths=("tests/test_assets.py",),
        acceptance_criteria=("No",),
        quick_validation=(ValidationCommand("Fail", ("git", "rev-parse", "missing"), 10),),
    )

    def executor(request):
        (root / "tests" / "test_assets.py").write_text("VALUE = 2\n", encoding="utf-8")
        return WorkerExecution(("fake-provider",), 0, "done", "")

    with pytest.raises(CodeTaskError) as error:
        run_code_task(
            contract,
            packet,
            repo_root=root,
            framework_repo=tmp_path / "framework",
            profile=MINE_TRACKER_PROFILE,
            executor=executor,
        )
    assert error.value.code == "CODE_TASK_QUICK_FAILED"
