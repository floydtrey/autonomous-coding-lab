from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_core.application.governed_source_evidence import (
    GovernedSourceEvidenceKnowledgeKernel,
)
from knowledge_core.application.lifecycle_projection import GovernedRetrievalObservation
from knowledge_core.application.projection_lineage import projection_snapshot_digest
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.governed_sources import (
    GovernedSnapshotMember,
    GovernedSourceDecision,
    GovernedSourceObservation,
)
from knowledge_core.storage.governed_source_models import (
    LegacyRepositoryDecisionMap,
    LegacyRepositoryObservationMap,
)
from knowledge_core.storage.repository_import_models import (
    RepositoryImportReceipt,
    RepositorySourceObservation,
)


GENERIC_SR2_PROJECTION_VERSION = "kc-sr2-governed-snapshot-projection-v1"


@dataclass(frozen=True)
class RepositorySourceCompatibility:
    """Optional legacy repository projection for repository-only consumers."""

    legacy_observation_id: UUID
    governing_manifest_digest: str
    projection_snapshot_digest: str
    repository_locator: str
    source_repository_key: str
    source_document_key: str
    source_path: str
    source_version: str
    git_blob_sha: str


@dataclass(frozen=True)
class GovernedSnapshotProjectionSource:
    """One exact source selected by a generic governed retrieval snapshot."""

    snapshot_digest: str
    member: GovernedSnapshotMember
    observation: GovernedSourceObservation
    decision: GovernedSourceDecision
    projection_digest: str
    repository_compatibility: RepositorySourceCompatibility | None = None


def _projection_digest(
    *,
    snapshot_digest: str,
    member: GovernedSnapshotMember,
    observation: GovernedSourceObservation,
    decision: GovernedSourceDecision,
) -> str:
    payload = {
        "member": member.canonical_payload,
        "observation_digest": observation.digest,
        "decision_digest": decision.digest,
        "projection_version": GENERIC_SR2_PROJECTION_VERSION,
        "snapshot_digest": snapshot_digest,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def resolve_governed_snapshot_sources(
    session: Session,
    *,
    governing_snapshot_digest: str,
) -> tuple[GovernedSnapshotProjectionSource, ...]:
    """Resolve exact SR-2 inputs from source-neutral governed evidence.

    Repository fields are reconstructed only when explicit legacy mapping evidence
    exists. A non-Git observation is therefore a first-class input and never needs
    fabricated repository, commit, path, or blob proof.
    """

    evidence = GovernedSourceEvidenceKnowledgeKernel(session)
    snapshot = evidence.load_snapshot(governing_snapshot_digest)
    selected: list[GovernedSnapshotProjectionSource] = []
    version_refs: set[UUID] = set()

    for member in snapshot.members:
        observation = evidence.load_observation(member.observation_id)
        decision = evidence.load_decision(member.decision_id)
        expected = GovernedSnapshotMember.from_selection(
            observation=observation,
            decision=decision,
            project_keys=member.project_keys,
        )
        if expected != member:
            raise KnowledgeInvariantError(
                "governed snapshot member does not reconstruct from exact evidence"
            )
        if member.resource_version_ref in version_refs:
            raise KnowledgeInvariantError(
                "SR-2 governed snapshot selects the same ResourceVersion more than once"
            )
        version_refs.add(member.resource_version_ref)
        selected.append(
            GovernedSnapshotProjectionSource(
                snapshot_digest=snapshot.digest,
                member=member,
                observation=observation,
                decision=decision,
                projection_digest=_projection_digest(
                    snapshot_digest=snapshot.digest,
                    member=member,
                    observation=observation,
                    decision=decision,
                ),
                repository_compatibility=_repository_compatibility(
                    session,
                    observation=observation,
                    decision=decision,
                ),
            )
        )
    return tuple(selected)


def _repository_compatibility(
    session: Session,
    *,
    observation: GovernedSourceObservation,
    decision: GovernedSourceDecision,
) -> RepositorySourceCompatibility | None:
    observation_map = session.scalars(
        select(LegacyRepositoryObservationMap).where(
            LegacyRepositoryObservationMap.generic_observation_id
            == observation.observation_id
        )
    ).one_or_none()
    if observation_map is None:
        return None

    decision_map = session.scalars(
        select(LegacyRepositoryDecisionMap).where(
            LegacyRepositoryDecisionMap.decision_id == decision.decision_id
        )
    ).one_or_none()
    if decision_map is None:
        raise KnowledgeInvariantError(
            "repository-backed governed source is missing governing decision mapping"
        )

    legacy = session.get(
        RepositorySourceObservation,
        observation_map.legacy_observation_id,
    )
    if legacy is None:
        raise KnowledgeInvariantError(
            "repository compatibility mapping references a missing observation"
        )
    receipt = session.get(
        RepositoryImportReceipt,
        decision_map.governing_manifest_digest,
    )
    if receipt is None:
        raise KnowledgeInvariantError(
            "repository compatibility mapping references a missing receipt"
        )
    manifest = receipt.manifest_json
    repository_locator = (
        manifest.get("repository_locator") if isinstance(manifest, dict) else None
    )
    if not isinstance(repository_locator, str) or not repository_locator:
        raise KnowledgeInvariantError(
            "repository compatibility mapping has no valid repository locator"
        )
    if (
        legacy.resource_version_ref != observation.resource_version_ref
        or legacy.resource_ref != observation.binding.resource_ref
        or legacy.source_repository_key
        != observation.binding.source_identity.origin_scope.removeprefix("repository:")
    ):
        raise KnowledgeInvariantError(
            "repository compatibility mapping no longer matches generic evidence"
        )

    old_observation = GovernedRetrievalObservation(
        observation_id=legacy.observation_id,
        manifest_digest=legacy.manifest_digest,
        source_repository_key=legacy.source_repository_key,
        repository_locator=repository_locator,
        source_document_key=legacy.source_document_key,
        source_commit=legacy.source_commit,
        source_path=legacy.path,
        git_blob_sha=legacy.git_blob_sha,
        resource_version_ref=legacy.resource_version_ref,
        classification=decision.classification,
        document_lifecycle=decision.retrieval_lifecycle,
        authority_rank=decision.authority_rank,
        rationale=decision.rationale,
    )
    return RepositorySourceCompatibility(
        legacy_observation_id=legacy.observation_id,
        governing_manifest_digest=decision_map.governing_manifest_digest,
        projection_snapshot_digest=projection_snapshot_digest(
            observation=old_observation,
            governing_manifest_digest=decision_map.governing_manifest_digest,
        ),
        repository_locator=repository_locator,
        source_repository_key=legacy.source_repository_key,
        source_document_key=legacy.source_document_key,
        source_path=legacy.path,
        source_version=legacy.source_commit,
        git_blob_sha=legacy.git_blob_sha,
    )
