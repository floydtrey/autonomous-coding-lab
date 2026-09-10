from pathlib import Path
import subprocess
from dataclasses import replace

from tools.code_task import build_code_task, run_code_task
from tools.codex_runtime import codex_command
from tools.consumer_profile import MINE_TRACKER_PROFILE, ValidationCommand, build_context_packet
from tools.worker_runtime import WorkerExecution, WorkerRequest


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


def test_code_task_uses_provider_neutral_worker_request(tmp_path):
    root = _repo(tmp_path)
    packet = build_context_packet(root, allowed_paths=("tests/test_assets.py",))
    validation = ValidationCommand("Check candidate", ("git", "diff", "--check"), 10)
    packet = replace(packet, full_validation=(validation,))
    contract = build_code_task(
        packet,
        task_id="PROVIDER-NEUTRAL-1",
        objective="Update one bounded fixture without provider-specific task types",
        expected_changed_paths=("tests/test_assets.py",),
        acceptance_criteria=("The bounded candidate validates.",),
        quick_validation=(validation,),
    )
    observed = []

    def executor(request: WorkerRequest) -> WorkerExecution:
        observed.append(request)
        (root / "tests" / "test_assets.py").write_text("VALUE = 2\n", encoding="utf-8")
        return WorkerExecution(("fake-local-provider",), 0, "implemented", "")

    result = run_code_task(
        contract,
        packet,
        repo_root=root,
        framework_repo=tmp_path / "framework",
        executor=executor,
    )

    assert len(observed) == 1
    assert type(observed[0]) is WorkerRequest
    assert observed[0].sandbox == "workspace-write"
    assert observed[0].target_repo == root
    assert result.changed_paths == ("tests/test_assets.py",)
    assert result.worker_response == "implemented"


def test_worker_request_remains_compatible_with_legacy_codex_command(tmp_path):
    target = _repo(tmp_path)
    framework = tmp_path / "framework"
    framework.mkdir()
    request = WorkerRequest(
        prompt="Make one bounded change.",
        target_repo=target,
        framework_repo=framework,
        sandbox="workspace-write",
    )

    command = codex_command(request, executable="codex")

    assert command[0] == "codex"
    assert "--sandbox" in command
    assert "workspace-write" in command
    assert "--model" in command
    assert request.model in command
