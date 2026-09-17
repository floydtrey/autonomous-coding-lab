from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from tools.repository_state import (
        candidate_content_digest,
        changed_paths,
        repository_head,
    )
    from tools.worker_result import WorkerResult, validate_worker_result
except ModuleNotFoundError:  # direct execution support
    from repository_state import (  # type: ignore
        candidate_content_digest,
        changed_paths,
        repository_head,
    )
    from worker_result import WorkerResult, validate_worker_result  # type: ignore


CONTRACT_VERSION = "repository-handoff:v1"


class RepositoryHandoffError(RuntimeError):
    """The local candidate no longer matches its validated Worker Result."""

    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


@dataclass(frozen=True)
class RepositoryHandoff:
    contract_version: str
    task_id: str
    consumer: str
    worker_result_digest: str
    base_sha: str
    candidate_content_digest: str
    changed_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, pretty: bool = False) -> str:
        options: dict[str, Any] = {"sort_keys": True}
        options.update(indent=2 if pretty else None)
        if not pretty:
            options["separators"] = (",", ":")
        return json.dumps(self.to_dict(), **options)


def worker_result_digest(result: WorkerResult) -> str:
    return "sha256:" + hashlib.sha256(result.to_json().encode("utf-8")).hexdigest()


def build_repository_handoff(
    result: WorkerResult,
    repo_root: Path,
) -> RepositoryHandoff:
    validate_worker_result(result)
    if not result.ready_for_repository_handoff:
        raise RepositoryHandoffError(
            "WORKER_RESULT_NOT_READY",
            "Worker Result has not passed every local handoff boundary",
        )
    if result.workspace_state != "dirty-candidate" and not (
        result.contract_version == "worker-result:v2" and result.workspace_state == "clean" and not result.changed_paths
    ):
        raise RepositoryHandoffError(
            "WORKSPACE_STATE_INVALID",
            "repository handoff currently requires a dirty-candidate workspace",
        )
    if result.candidate_content_digest is None:
        raise RepositoryHandoffError(
            "CANDIDATE_IDENTITY_MISSING",
            "ready Worker Result must include candidate_content_digest",
        )

    root = repo_root.resolve()
    current_head = repository_head(root)
    if current_head != result.base_sha:
        raise RepositoryHandoffError(
            "BASE_SHA_MISMATCH",
            f"expected target HEAD {result.base_sha}; observed {current_head}",
        )

    current_paths = tuple(changed_paths(root, result.base_sha))
    if current_paths != result.changed_paths:
        raise RepositoryHandoffError(
            "CHANGED_PATHS_MISMATCH",
            f"expected changed_paths={list(result.changed_paths)}; "
            f"observed {list(current_paths)}",
        )

    current_digest = candidate_content_digest(root, current_paths)
    if current_digest != result.candidate_content_digest:
        raise RepositoryHandoffError(
            "CANDIDATE_DIGEST_MISMATCH",
            f"expected {result.candidate_content_digest}; observed {current_digest}",
        )

    return RepositoryHandoff(
        contract_version=CONTRACT_VERSION,
        task_id=result.task_id,
        consumer=result.consumer,
        worker_result_digest=worker_result_digest(result),
        base_sha=result.base_sha,
        candidate_content_digest=current_digest,
        changed_paths=current_paths,
    )
