from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Protocol

from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.repository_import import RepositorySourceProof


_HEX_OBJECT = re.compile(r"^[0-9a-f]{40,64}$")


class RepositorySourceReader(Protocol):
    repository_locator: str

    def read_exact(self, *, source_commit: str, path: str) -> RepositorySourceProof:
        ...


@dataclass
class GitRepositorySourceReader:
    """Read exact Git objects from one server-configured repository.

    The repository root is host configuration. Manifest/client data never becomes
    a filesystem root or shell command.
    """

    repository_locator: str
    repository_root: Path

    def __post_init__(self) -> None:
        self.repository_root = Path(self.repository_root).resolve()
        if not (self.repository_root / ".git").exists():
            raise KnowledgeInvariantError(
                f"configured repository root is not a Git worktree: {self.repository_root}"
            )

    def _git(self, *args: str, text: bool = False):
        try:
            return subprocess.run(
                ["git", "-C", str(self.repository_root), *args],
                check=True,
                capture_output=True,
                text=text,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise KnowledgeInvariantError(
                "exact Git source object could not be resolved"
            ) from exc

    def read_exact(self, *, source_commit: str, path: str) -> RepositorySourceProof:
        if not _HEX_OBJECT.fullmatch(source_commit):
            raise KnowledgeInvariantError("source_commit must be an exact Git object id")
        tree = self._git("ls-tree", source_commit, "--", path, text=True).stdout.strip()
        if not tree:
            raise KnowledgeInvariantError(
                f"source path does not exist at exact commit: {path}"
            )
        meta, resolved_path = tree.split("\t", 1)
        mode, object_type, blob_sha = meta.split(" ", 2)
        if resolved_path != path:
            raise KnowledgeInvariantError("Git source path resolved unexpectedly")
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise KnowledgeInvariantError(
                "repository import accepts only regular Git blobs"
            )
        content = self._git("cat-file", "blob", blob_sha).stdout
        return RepositorySourceProof(
            source_commit=source_commit,
            path=path,
            git_blob_sha=blob_sha,
            content=content,
            object_mode=mode,
            object_type=object_type,
        )
