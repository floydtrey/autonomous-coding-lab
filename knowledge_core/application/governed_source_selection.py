from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_core.application.lifecycle_projection import GovernedRetrievalObservation
from knowledge_core.application.projection_lineage import projection_snapshot_digest
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.retrieval import RetrievalLifecycleState
from knowledge_core.storage.repository_import_models import (
    RepositoryImportReceipt,
    RepositorySourceObservation,
)


class GovernedProjectionSourceRole(StrEnum):
    CURRENT = "current"
    PRIOR_VERSION = "prior_version"
    RETIREMENT_RETAIN = "retirement_retain"


@dataclass(frozen=True)
class GovernedProjectionSource:
    role: GovernedProjectionSourceRole
    observation: GovernedRetrievalObservation
    governing_manifest_digest: str
    projection_snapshot_digest: str


def resolve_governed_projection_sources(
    session: Session,
    *,
    governing_manifest_digest: str,
) -> tuple[GovernedProjectionSource, ...]:
    """Reconstruct the exact governed SR-2 source set from RI-2 evidence.

    The governing receipt may be ``applying`` while an import is preparing its
    derived generation or ``settled`` during later deterministic rebuild. Prior
    receipts must already be settled. Failed receipts never govern projection.
    """

    governing_receipt = session.get(RepositoryImportReceipt, governing_manifest_digest)
    if governing_receipt is None:
        raise KnowledgeInvariantError("unknown governing repository manifest")
    if governing_receipt.status not in {"applying", "settled"}:
        raise KnowledgeInvariantError(
            "governing repository manifest is not eligible for projection"
        )

    governing_manifest = _validated_receipt_manifest(governing_receipt)
    chain = _prior_receipt_chain(session, governing_receipt)
    active_entries, retirements = _manifest_maps(governing_manifest)

    selected: list[GovernedProjectionSource] = []
    selected_versions: dict[UUID, tuple[str, GovernedProjectionSourceRole]] = {}

    for document_key, entry in active_entries.items():
        current_row = _observation_for_receipt(
            session,
            receipt=governing_receipt,
            document_key=document_key,
        )
        if current_row is None:
            raise KnowledgeInvariantError(
                f"governing manifest is missing its source observation: {document_key}"
            )
        _validate_observation_against_entry(
            current_row,
            receipt=governing_receipt,
            entry=entry,
        )
        try:
            current_lifecycle = RetrievalLifecycleState(entry["retrieval_lifecycle"])
        except (KeyError, ValueError) as exc:
            raise KnowledgeInvariantError(
                f"governing manifest has invalid retrieval lifecycle: {document_key}"
            ) from exc

        current = _source_from_observation(
            role=GovernedProjectionSourceRole.CURRENT,
            row=current_row,
            governing_manifest=governing_manifest,
            governing_manifest_digest=governing_receipt.manifest_digest,
            document_lifecycle=current_lifecycle,
        )
        _append_unique_source(selected, selected_versions, current)

        seen_document_versions = {current_row.resource_version_ref}
        for prior_receipt in chain:
            prior_row = _observation_for_receipt(
                session,
                receipt=prior_receipt,
                document_key=document_key,
            )
            if prior_row is None:
                continue
            prior_entry = _entry_for_observation(prior_receipt, prior_row)
            _validate_observation_against_entry(
                prior_row,
                receipt=prior_receipt,
                entry=prior_entry,
            )
            if prior_row.resource_version_ref in seen_document_versions:
                continue
            seen_document_versions.add(prior_row.resource_version_ref)
            historical = _source_from_observation(
                role=GovernedProjectionSourceRole.PRIOR_VERSION,
                row=prior_row,
                governing_manifest=governing_manifest,
                governing_manifest_digest=governing_receipt.manifest_digest,
                document_lifecycle=RetrievalLifecycleState.SUPERSEDED,
            )
            _append_unique_source(selected, selected_versions, historical)

    for document_key, retirement in retirements.items():
        if retirement.get("historical_retrieval") == "exclude":
            continue
        if retirement.get("historical_retrieval") != "retain":
            raise KnowledgeInvariantError(
                f"governing retirement has invalid historical retrieval: {document_key}"
            )

        retained_row: RepositorySourceObservation | None = None
        retained_receipt: RepositoryImportReceipt | None = None
        for prior_receipt in chain:
            candidate = _observation_for_receipt(
                session,
                receipt=prior_receipt,
                document_key=document_key,
            )
            if candidate is None:
                continue
            retained_row = candidate
            retained_receipt = prior_receipt
            break
        if retained_row is None or retained_receipt is None:
            raise KnowledgeInvariantError(
                f"cannot retain retirement without reconstructable source observation: {document_key}"
            )

        retained_entry = _entry_for_observation(retained_receipt, retained_row)
        _validate_observation_against_entry(
            retained_row,
            receipt=retained_receipt,
            entry=retained_entry,
        )
        retained = _source_from_observation(
            role=GovernedProjectionSourceRole.RETIREMENT_RETAIN,
            row=retained_row,
            governing_manifest=governing_manifest,
            governing_manifest_digest=governing_receipt.manifest_digest,
            document_lifecycle=RetrievalLifecycleState.SUPERSEDED,
        )
        _append_unique_source(selected, selected_versions, retained)

    return tuple(selected)


def _canonical_manifest_digest(manifest: dict) -> str:
    payload = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _validated_receipt_manifest(receipt: RepositoryImportReceipt) -> dict:
    manifest = receipt.manifest_json
    if not isinstance(manifest, dict):
        raise KnowledgeInvariantError("repository receipt manifest payload is invalid")
    if _canonical_manifest_digest(manifest) != receipt.manifest_digest:
        raise KnowledgeInvariantError(
            "repository receipt manifest payload does not match its digest"
        )
    if manifest.get("source_repository_key") != receipt.source_repository_key:
        raise KnowledgeInvariantError(
            "repository receipt source repository does not match manifest"
        )
    if manifest.get("source_commit") != receipt.source_commit:
        raise KnowledgeInvariantError(
            "repository receipt source commit does not match manifest"
        )
    if manifest.get("previous_manifest_digest") != receipt.previous_manifest_digest:
        raise KnowledgeInvariantError(
            "repository receipt predecessor does not match manifest"
        )
    if manifest.get("history_policy") != "retain_prior_versions_as_superseded":
        raise KnowledgeInvariantError("unsupported repository history policy")
    if not isinstance(manifest.get("repository_locator"), str) or not manifest.get(
        "repository_locator"
    ):
        raise KnowledgeInvariantError("governing repository locator is invalid")
    return manifest


def _prior_receipt_chain(
    session: Session,
    governing_receipt: RepositoryImportReceipt,
) -> tuple[RepositoryImportReceipt, ...]:
    result: list[RepositoryImportReceipt] = []
    seen = {governing_receipt.manifest_digest}
    cursor = governing_receipt.previous_manifest_digest
    while cursor is not None:
        if cursor in seen:
            raise KnowledgeInvariantError("repository manifest chain contains a cycle")
        seen.add(cursor)
        receipt = session.get(RepositoryImportReceipt, cursor)
        if receipt is None:
            raise KnowledgeInvariantError(
                "repository manifest chain references a missing predecessor"
            )
        if receipt.status != "settled":
            raise KnowledgeInvariantError(
                "repository manifest chain predecessor is not settled"
            )
        if receipt.source_repository_key != governing_receipt.source_repository_key:
            raise KnowledgeInvariantError(
                "repository manifest chain crosses source repository identity"
            )
        _validated_receipt_manifest(receipt)
        result.append(receipt)
        cursor = receipt.previous_manifest_digest
    return tuple(result)


def _manifest_maps(manifest: dict) -> tuple[dict[str, dict], dict[str, dict]]:
    raw_entries = manifest.get("entries")
    raw_retirements = manifest.get("retirements")
    if not isinstance(raw_entries, list) or not isinstance(raw_retirements, list):
        raise KnowledgeInvariantError(
            "governing repository manifest entries/retirements are invalid"
        )

    entries: dict[str, dict] = {}
    for entry in raw_entries:
        if not isinstance(entry, dict):
            raise KnowledgeInvariantError("governing repository entry is invalid")
        key = entry.get("source_document_key")
        if not isinstance(key, str) or not key or key in entries:
            raise KnowledgeInvariantError(
                "governing repository manifest has invalid/duplicate active key"
            )
        entries[key] = entry

    retirements: dict[str, dict] = {}
    for retirement in raw_retirements:
        if not isinstance(retirement, dict):
            raise KnowledgeInvariantError("governing repository retirement is invalid")
        key = retirement.get("source_document_key")
        if (
            not isinstance(key, str)
            or not key
            or key in entries
            or key in retirements
        ):
            raise KnowledgeInvariantError(
                "governing repository manifest has invalid/duplicate retirement key"
            )
        retirements[key] = retirement
    return entries, retirements


def _observation_for_receipt(
    session: Session,
    *,
    receipt: RepositoryImportReceipt,
    document_key: str,
) -> RepositorySourceObservation | None:
    return session.execute(
        select(RepositorySourceObservation).where(
            RepositorySourceObservation.manifest_digest == receipt.manifest_digest,
            RepositorySourceObservation.source_document_key == document_key,
        )
    ).scalar_one_or_none()


def _entry_for_observation(
    receipt: RepositoryImportReceipt,
    row: RepositorySourceObservation,
) -> dict:
    manifest = _validated_receipt_manifest(receipt)
    entries, _retirements = _manifest_maps(manifest)
    entry = entries.get(row.source_document_key)
    if entry is None:
        raise KnowledgeInvariantError(
            "source observation is not backed by an active entry in its own manifest"
        )
    return entry


def _validate_observation_against_entry(
    row: RepositorySourceObservation,
    *,
    receipt: RepositoryImportReceipt,
    entry: dict,
) -> None:
    expected = {
        "manifest_digest": receipt.manifest_digest,
        "source_repository_key": receipt.source_repository_key,
        "source_document_key": entry.get("source_document_key"),
        "source_commit": receipt.source_commit,
        "path": entry.get("path"),
        "git_blob_sha": entry.get("git_blob_sha"),
        "classification": entry.get("classification"),
        "retrieval_lifecycle": entry.get("retrieval_lifecycle"),
        "authority_rank": entry.get("authority_rank"),
        "rationale": entry.get("rationale"),
    }
    actual = {
        "manifest_digest": row.manifest_digest,
        "source_repository_key": row.source_repository_key,
        "source_document_key": row.source_document_key,
        "source_commit": row.source_commit,
        "path": row.path,
        "git_blob_sha": row.git_blob_sha,
        "classification": row.classification,
        "retrieval_lifecycle": row.retrieval_lifecycle,
        "authority_rank": row.authority_rank,
        "rationale": row.rationale,
    }
    if actual != expected:
        raise KnowledgeInvariantError(
            "source observation does not match its immutable repository manifest entry"
        )


def _source_from_observation(
    *,
    role: GovernedProjectionSourceRole,
    row: RepositorySourceObservation,
    governing_manifest: dict,
    governing_manifest_digest: str,
    document_lifecycle: RetrievalLifecycleState,
) -> GovernedProjectionSource:
    observation = GovernedRetrievalObservation(
        observation_id=row.observation_id,
        manifest_digest=row.manifest_digest,
        source_repository_key=row.source_repository_key,
        repository_locator=governing_manifest["repository_locator"],
        source_document_key=row.source_document_key,
        source_commit=row.source_commit,
        source_path=row.path,
        git_blob_sha=row.git_blob_sha,
        resource_version_ref=row.resource_version_ref,
        classification=row.classification,
        document_lifecycle=document_lifecycle,
        authority_rank=row.authority_rank,
        rationale=row.rationale,
    )
    return GovernedProjectionSource(
        role=role,
        observation=observation,
        governing_manifest_digest=governing_manifest_digest,
        projection_snapshot_digest=projection_snapshot_digest(
            observation=observation,
            governing_manifest_digest=governing_manifest_digest,
        ),
    )


def _append_unique_source(
    selected: list[GovernedProjectionSource],
    selected_versions: dict[UUID, tuple[str, GovernedProjectionSourceRole]],
    source: GovernedProjectionSource,
) -> None:
    version_ref = source.observation.resource_version_ref
    identity = (source.observation.source_document_key, source.role)
    prior = selected_versions.get(version_ref)
    if prior is not None:
        raise KnowledgeInvariantError(
            "governed source selection produced duplicate ResourceVersion identity "
            f"for {prior!r} and {identity!r}"
        )
    selected_versions[version_ref] = identity
    selected.append(source)
