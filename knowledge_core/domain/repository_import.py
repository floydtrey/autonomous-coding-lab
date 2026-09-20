from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class RepositorySourceProof:
    source_commit: str
    path: str
    git_blob_sha: str
    content: bytes
    object_mode: str = "100644"
    object_type: str = "blob"


@dataclass(frozen=True)
class ImportAction:
    source_document_key: str
    action: str
    resource_ref: UUID | None = None
    resource_version_ref: UUID | None = None


@dataclass(frozen=True)
class RepositoryImportReceiptSnapshot:
    manifest_digest: str
    previous_manifest_digest: str | None
    source_repository_key: str
    source_commit: str
    status: str
    plan_digest: str
    resulting_text_generation_id: UUID | None


@dataclass(frozen=True)
class RepositoryImportPlan:
    manifest: dict[str, Any]
    manifest_digest: str
    previous_manifest_digest: str | None
    expected_current_generation_id: UUID | None
    actions: tuple[ImportAction, ...]
    source_proofs: tuple[RepositorySourceProof, ...]
    plan_digest: str
    replay_receipt: RepositoryImportReceiptSnapshot | None = None
