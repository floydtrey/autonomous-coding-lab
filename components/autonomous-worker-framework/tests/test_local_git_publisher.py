import subprocess
from pathlib import Path

import pytest

from tools.local_git_publisher import (
    CONTRACT_VERSION,
    LocalPublicationError,
    publish_local_candidate,
)
from tools.local_worker_harness import FIXTURE_TASK_VERSION, FixtureTask, run_fixture_job


def _git(repo: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8"
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


def test_publishes_validated_candidate_as_identity_bound_local_commit(tmp_path, monkeypatch):
    repo, result = _candidate(tmp_path)
    branch = _git(repo, "branch", "--show-current")
    observed_commands = []
    real_run = subprocess.run

    def recording_run(*args, **kwargs):
        observed_commands.append(tuple(args[0]))
        return real_run(*args, **kwargs)

    monkeypatch.setattr("tools.local_git_publisher.subprocess.run", recording_run)

    committed, publication = publish_local_candidate(
        result, repo, commit_message="Apply fixture candidate"
    )

    assert publication.contract_version == CONTRACT_VERSION
    assert publication.base_sha == result.base_sha
    assert publication.candidate_sha == _git(repo, "rev-parse", "HEAD")
    assert publication.candidate_content_digest == result.candidate_content_digest
    assert publication.changed_paths == result.changed_paths
    assert publication.repository_handoff_digest.startswith("sha256:")
    assert committed.workspace_state == "committed-candidate"
    assert committed.candidate_sha == publication.candidate_sha
    assert committed.ready_for_repository_handoff is True
    assert _git(repo, "status", "--porcelain") == ""
    assert _git(repo, "branch", "--show-current") == branch
    assert _git(repo, "show", "-s", "--format=%an <%ae>", "HEAD") == (
        "Autonomous Worker <autonomous-worker@localhost>"
    )
    forbidden = {"push", "pull", "fetch", "checkout", "switch", "merge", "rebase", "remote"}
    assert not any(forbidden.intersection(command[1:]) for command in observed_commands)


def test_rejects_tampered_candidate_before_staging_or_commit(tmp_path):
    repo, result = _candidate(tmp_path)
    (repo / "autonomy_smoke" / "fixture_state.txt").write_bytes(b"STATE=TAMPERED\n")
    original_head = _git(repo, "rev-parse", "HEAD")

    with pytest.raises(Exception) as error:
        publish_local_candidate(result, repo, commit_message="Apply fixture candidate")

    assert getattr(error.value, "code") == "CANDIDATE_DIGEST_MISMATCH"
    assert _git(repo, "rev-parse", "HEAD") == original_head
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_rejects_multiline_commit_identity_input_without_mutation(tmp_path):
    repo, result = _candidate(tmp_path)
    original_head = _git(repo, "rev-parse", "HEAD")

    with pytest.raises(LocalPublicationError) as error:
        publish_local_candidate(result, repo, commit_message="line one\nline two")

    assert error.value.code == "INVALID_PUBLICATION_INPUT"
    assert _git(repo, "rev-parse", "HEAD") == original_head
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_rejects_head_movement_before_publication(tmp_path):
    repo, result = _candidate(tmp_path)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "move candidate head")

    with pytest.raises(Exception) as error:
        publish_local_candidate(result, repo, commit_message="Apply fixture candidate")

    assert getattr(error.value, "code") == "BASE_SHA_MISMATCH"
