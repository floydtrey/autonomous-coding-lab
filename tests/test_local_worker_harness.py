import json
import subprocess
from pathlib import Path

import pytest

from tools.local_worker_harness import (
    FIXTURE_TASK_VERSION,
    FixtureTask,
    HarnessRuntimeError,
    candidate_content_digest,
    run_fixture_job,
    task_contract_digest,
    validate_patch_boundary,
)
from tools.worker_result import validate_worker_result


def _git(repo: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return process.stdout.strip()


def _repo(tmp_path: Path, state: str = "A") -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "fixture@example.com")
    _git(repo, "config", "user.name", "Fixture")
    (repo / "autonomy_smoke").mkdir()
    (repo / "README.md").write_text("fixture consumer\n", encoding="utf-8")
    if state != "ABSENT":
        (repo / "autonomy_smoke" / "fixture_state.txt").write_bytes(
            f"STATE={state}\n".encode("ascii")
        )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture baseline")
    return repo


def _task(initial: str = "A", target: str = "B") -> FixtureTask:
    return FixtureTask.from_mapping(
        {
            "contract_version": FIXTURE_TASK_VERSION,
            "task_id": f"fixture-{initial.lower()}-to-{target.lower()}",
            "consumer": "commissioning-fixture",
            "allowed_paths": ["autonomy_smoke/fixture_state.txt"],
            "fixture_path": "autonomy_smoke/fixture_state.txt",
            "initial_state": initial,
            "target_state": target,
        }
    )


def test_task_requires_fixture_path_inside_exact_allowed_paths():
    value = _task().to_dict()
    value["allowed_paths"] = ["autonomy_smoke/other.txt"]

    with pytest.raises(Exception, match="explicitly present"):
        FixtureTask.from_mapping(value)


def test_task_digest_is_deterministic():
    task = _task()

    assert task_contract_digest(task) == task_contract_digest(task)
    assert task_contract_digest(task).startswith("sha256:")


def test_successful_a_to_b_job_produces_dirty_candidate_result(tmp_path):
    repo = _repo(tmp_path, "A")
    task = _task("A", "B")

    result = run_fixture_job(task, repo)

    assert (repo / "autonomy_smoke" / "fixture_state.txt").read_bytes() == b"STATE=B\n"
    assert result.worker.result == "pass"
    assert result.patch_boundary.result == "pass"
    assert result.quick_validation.result == "pass"
    assert result.full_validation.result == "not-run"
    assert result.workspace_state == "dirty-candidate"
    assert result.changed_paths == ("autonomy_smoke/fixture_state.txt",)
    assert result.candidate_sha is None
    assert result.candidate_content_digest.startswith("sha256:")
    assert result.ready_for_repository_handoff is False
    validate_worker_result(result)


def test_successful_absent_to_a_job_tracks_new_file(tmp_path):
    repo = _repo(tmp_path, "ABSENT")
    task = _task("ABSENT", "A")

    result = run_fixture_job(task, repo)

    assert result.worker.result == "pass"
    assert (repo / "autonomy_smoke" / "fixture_state.txt").read_bytes() == b"STATE=A\n"
    assert result.changed_paths == ("autonomy_smoke/fixture_state.txt",)


def test_initial_state_mismatch_stops_before_mutation(tmp_path):
    repo = _repo(tmp_path, "B")
    task = _task("A", "B")

    result = run_fixture_job(task, repo)

    assert result.worker.result == "fail"
    assert result.first_failure is not None
    assert result.first_failure.boundary == "fixture-precondition"
    assert result.first_failure.code == "FIXTURE_INITIAL_STATE_FAILED"
    assert result.changed_paths == ()
    assert (repo / "autonomy_smoke" / "fixture_state.txt").read_bytes() == b"STATE=B\n"


def test_dirty_repository_fails_closed_before_mutation(tmp_path):
    repo = _repo(tmp_path, "A")
    (repo / "unrelated.txt").write_text("dirty\n", encoding="utf-8")

    result = run_fixture_job(_task("A", "B"), repo)

    assert result.worker.result == "fail"
    assert result.first_failure is not None
    assert result.first_failure.code == "WORKSPACE_NOT_CLEAN"
    assert result.workspace_state == "preexisting-dirty"
    assert result.changed_paths == ()
    assert result.candidate_content_digest is None
    assert (repo / "autonomy_smoke" / "fixture_state.txt").read_bytes() == b"STATE=A\n"


def test_patch_boundary_rejects_outside_path():
    with pytest.raises(HarnessRuntimeError, match="outside"):
        validate_patch_boundary(
            ["autonomy_smoke/fixture_state.txt", "app/unrelated.py"],
            ["autonomy_smoke/fixture_state.txt"],
        )


def test_candidate_content_digest_changes_with_bytes(tmp_path):
    repo = tmp_path / "repo"
    (repo / "autonomy_smoke").mkdir(parents=True)
    path = repo / "autonomy_smoke" / "fixture_state.txt"
    path.write_bytes(b"STATE=A\n")
    first = candidate_content_digest(repo, ["autonomy_smoke/fixture_state.txt"])
    path.write_bytes(b"STATE=B\n")
    second = candidate_content_digest(repo, ["autonomy_smoke/fixture_state.txt"])

    assert first != second


def test_worker_result_json_round_trip_for_success(tmp_path):
    repo = _repo(tmp_path, "A")

    result = run_fixture_job(_task("A", "B"), repo)
    encoded = result.to_json()
    decoded = json.loads(encoded)

    assert decoded["contract_version"] == "worker-result:v1"
    assert decoded["task_id"] == "fixture-a-to-b"
