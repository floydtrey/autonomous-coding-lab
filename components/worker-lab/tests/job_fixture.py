"""Deterministic disposable Git source for the checked-in job fixtures."""
import os
from pathlib import Path
import subprocess


def create_target(target: Path):
    (target / "record_ledger").mkdir(parents=True)
    (target / "README.md").write_bytes(b"instructions\n")
    (target / "record_ledger" / "models.py").write_bytes(b"# model\n")
    env = dict(os.environ, GIT_AUTHOR_DATE="2026-09-17T00:00:00Z",
               GIT_COMMITTER_DATE="2026-09-17T00:00:00Z",
               GIT_AUTHOR_NAME="Job Fixture", GIT_COMMITTER_NAME="Job Fixture",
               GIT_AUTHOR_EMAIL="fixture@example.invalid", GIT_COMMITTER_EMAIL="fixture@example.invalid")
    def git(*args):
        return subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false",
                               "-c", "core.hooksPath=", "-C", str(target), *args],
                              env=env, check=True, capture_output=True, text=True).stdout.strip()
    git("init", "-q", "--object-format=sha1")
    git("add", ".")
    git("commit", "-q", "-m", "Canonical job fixture")
    return git("rev-parse", "HEAD")
