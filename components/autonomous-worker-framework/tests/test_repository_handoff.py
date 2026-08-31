import subprocess
from pathlib import Path

import pytest

from tools.local_worker_harness import FIXTURE_TASK_VERSION, FixtureTask, run_fixture_job
from tools.repository_handoff import (
    CONTRACT_VERSION,
    RepositoryHandoffError,
    build_repository_handoff,
)


def _git(repo: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return process.stdout.strip()


def _candidate(tmp_path: Path):
    repo = tmp_path / "consumer"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "fixture@example.com")
    _git(repo, "config", "user.name", "Fixture")
    (repo / "autonomy_smoke").mkdir()
    (repo / "autonomy_smoke" / "fixture_state.txt").write_bytes(b"STATE=A\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture baseline")
    task = FixtureTask.from_mapping(
        {
            "contract_version": FIXTURE_TASK_VERSION,
            "task_id": "fixture-a-to-b",
            "consumer": "commissioning-fixture",
            "allowed_paths": ["autonomy_smoke/fixture_state.txt"],
            "fixture_path": "autonomy_smoke/fixture_state.txt",
            "initial_state": "A",
            "target_state": "B",
        }
    )
    return repo, run_fixture_job(task, repo)


def test_ready_candidate_builds_identity_bound_handoff(tmp_path):
    repo, result = _candidate(tmp_path)

    handoff = build_repository_handoff(result, repo)

    assert handoff.contract_version == CONTRACT_VERSION
    assert handoff.base_sha == result.base_sha
    assert handoff.candidate_content_digest == result.candidate_content_digest
    assert handoff.changed_paths == result.changed_paths
    assert handoff.worker_result_digest.startswith("sha256:")


def test_handoff_rejects_candidate_content_changed_after_validation(tmp_path):
    repo, result = _candidate(tmp_path)
    (repo / "autonomy_smoke" / "fixture_state.txt").write_bytes(b"STATE=TAMPERED\n")

    with pytest.raises(RepositoryHandoffError) as error:
        build_repository_handoff(result, repo)

    assert error.value.code == "CANDIDATE_DIGEST_MISMATCH"


def test_handoff_rejects_new_path_after_validation(tmp_path):
    repo, result = _candidate(tmp_path)
    (repo / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")

    with pytest.raises(RepositoryHandoffError) as error:
        build_repository_handoff(result, repo)

    assert error.value.code == "CHANGED_PATHS_MISMATCH"


def test_handoff_rejects_target_head_movement(tmp_path):
    repo, result = _candidate(tmp_path)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "move candidate head")

    with pytest.raises(RepositoryHandoffError) as error:
        build_repository_handoff(result, repo)

    assert error.value.code == "BASE_SHA_MISMATCH"
