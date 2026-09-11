import subprocess
from pathlib import Path

import pytest

from current_test_fixtures import ready_worker_result
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
    (repo / "candidate").mkdir()
    candidate = repo / "candidate" / "fixture_state.txt"
    candidate.write_bytes(b"STATE=A\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture baseline")
    candidate.write_bytes(b"STATE=B\n")
    return repo, ready_worker_result(repo)


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
    (repo / "candidate" / "fixture_state.txt").write_bytes(b"STATE=TAMPERED\n")

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
