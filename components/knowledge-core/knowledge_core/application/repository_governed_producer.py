from __future__ import annotations

from uuid import UUID, uuid5

from sqlalchemy.orm import Session

from knowledge_core.application.governed_source_evidence import (
    GovernedSourceEvidenceKnowledgeKernel,
    LEGACY_REPOSITORY_MAPPING_VERSION,
    LEGACY_REPOSITORY_OBSERVATION_NAMESPACE,
    _legacy_capture_evidence_digest,
    _repository_source_identity,
)
from knowledge_core.application.governed_source_selection import (
    GovernedProjectionSource,
    resolve_governed_projection_sources,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.governed_sources import (
    GovernedRetrievalSnapshot,
    GovernedSnapshotExclusion,
    GovernedSnapshotMember,
    GovernedSourceBinding,
    GovernedSourceDecision,
    GovernedSourceObservation,
    SourceEvidenceRef,
)
from knowledge_core.storage.governed_source_models import (
    GovernedSourceBindingRecord,
    LegacyRepositoryDecisionMap,
    LegacyRepositoryObservationMap,
    LegacyRepositorySnapshotMap,
)
from knowledge_core.storage.repository_import_models import (
    RepositoryDocumentBinding,
    RepositoryImportReceipt,
    RepositorySourceObservation,
)


REPOSITORY_PRODUCER_MAPPING_VERSION = "kc-repository-governed-producer-v2"
COMPLETE_CORPUS_SELECTION_POLICY_ID = "kc-complete-corpus-selection-v1"
_REPOSITORY_DECISION_NAMESPACE = UUID("c8390259-ed22-5e7e-a7ac-62f61d71cdcf")


class RepositoryGovernedProducerKnowledgeKernel:
    """Translate verified repository evidence into one complete generic corpus.

    Git commit/path/blob verification remains upstream in the repository adapter.
    This producer consumes those accepted observations, replaces only this
    repository's contribution, and carries every unrelated source from the expected
    predecessor snapshot so a repository update cannot silently erase another
    producer's current knowledge.
    """

    def __init__(self, session: Session):
        self.session = session
        self.evidence = GovernedSourceEvidenceKnowledgeKernel(session)

    def prepare_complete_snapshot(
        self,
        *,
        governing_manifest_digest: str,
        expected_predecessor_snapshot_digest: str | None,
    ) -> GovernedRetrievalSnapshot:
        receipt = self.session.get(
            RepositoryImportReceipt,
            governing_manifest_digest,
        )
        if receipt is None:
            raise KnowledgeInvariantError("unknown governing repository receipt")
        if receipt.status not in {"applying", "settled"}:
            raise KnowledgeInvariantError(
                "repository receipt is not eligible to produce governed evidence"
            )

        existing_map = self.session.get(
            LegacyRepositorySnapshotMap,
            governing_manifest_digest,
        )
        if existing_map is not None:
            if existing_map.mapping_version != REPOSITORY_PRODUCER_MAPPING_VERSION:
                raise KnowledgeInvariantError(
                    "repository receipt already has an incompatible governed snapshot mapping"
                )
            snapshot = self.evidence.load_snapshot(existing_map.snapshot_digest)
            if (
                snapshot.predecessor_snapshot_digest
                != expected_predecessor_snapshot_digest
            ):
                raise KnowledgeInvariantError(
                    "repository snapshot retry does not match the expected serving predecessor"
                )
            return snapshot

        predecessor = (
            self.evidence.load_snapshot(expected_predecessor_snapshot_digest)
            if expected_predecessor_snapshot_digest is not None
            else None
        )
        repository_key = receipt.source_repository_key

        members: list[GovernedSnapshotMember] = []
        exclusions: list[GovernedSnapshotExclusion] = []
        if predecessor is not None:
            for member in predecessor.members:
                observation = self.evidence.load_observation(member.observation_id)
                if not self._repository_controls_identity(
                    observation.binding.source_identity.source_kind,
                    observation.binding.source_identity.origin_scope,
                    repository_key,
                ):
                    members.append(member)
            for exclusion in predecessor.exclusions:
                binding = self.session.get(
                    GovernedSourceBindingRecord,
                    exclusion.source_identity_digest,
                )
                if binding is None:
                    raise KnowledgeInvariantError(
                        "predecessor exclusion lost its governed source binding"
                    )
                if not self._repository_controls_identity(
                    binding.source_kind,
                    binding.origin_scope,
                    repository_key,
                ):
                    exclusions.append(exclusion)

        sources = resolve_governed_projection_sources(
            self.session,
            governing_manifest_digest=governing_manifest_digest,
        )
        for source in sources:
            observation = self._persist_repository_observation(source)
            decision = self._persist_repository_decision(
                receipt=receipt,
                source=source,
                observation=observation,
            )
            members.append(
                GovernedSnapshotMember.from_selection(
                    observation=observation,
                    decision=decision,
                )
            )

        exclusions.extend(self._repository_exclusions(receipt))
        snapshot = GovernedRetrievalSnapshot(
            selection_policy_id=COMPLETE_CORPUS_SELECTION_POLICY_ID,
            created_at=receipt.created_at,
            members=tuple(members),
            exclusions=tuple(exclusions),
            predecessor_snapshot_digest=expected_predecessor_snapshot_digest,
        )
        self._validate_complete_snapshot(snapshot)
        self.evidence.persist_snapshot(snapshot)
        self.session.add(
            LegacyRepositorySnapshotMap(
                governing_manifest_digest=governing_manifest_digest,
                snapshot_digest=snapshot.digest,
                mapping_version=REPOSITORY_PRODUCER_MAPPING_VERSION,
            )
        )
        self.session.flush()
        return snapshot

    @staticmethod
    def _repository_controls_identity(
        source_kind: str,
        origin_scope: str,
        repository_key: str,
    ) -> bool:
        return (
            source_kind == "git.repository-document"
            and origin_scope == f"repository:{repository_key}"
        )

    def _persist_repository_observation(
        self,
        source: GovernedProjectionSource,
    ) -> GovernedSourceObservation:
        legacy = self.session.get(
            RepositorySourceObservation,
            source.observation.observation_id,
        )
        if legacy is None:
            raise KnowledgeInvariantError(
                "repository producer source references a missing verified observation"
            )
        identity = _repository_source_identity(
            source_repository_key=legacy.source_repository_key,
            source_document_key=legacy.source_document_key,
        )
        observation = GovernedSourceObservation(
            observation_id=uuid5(
                LEGACY_REPOSITORY_OBSERVATION_NAMESPACE,
                str(legacy.observation_id),
            ),
            binding=GovernedSourceBinding(
                source_identity=identity,
                resource_ref=legacy.resource_ref,
            ),
            resource_version_ref=legacy.resource_version_ref,
            producer_id="kc.repository-import",
            producer_version=REPOSITORY_PRODUCER_MAPPING_VERSION,
            evidence=(
                SourceEvidenceRef(
                    evidence_kind="legacy.repository-observation-capture-v1",
                    evidence_ref=(
                        f"repository_source_observation:{legacy.observation_id}"
                    ),
                    evidence_digest=_legacy_capture_evidence_digest(legacy),
                ),
            ),
            observed_at=self._receipt(legacy.manifest_digest).created_at,
            source_event_time=None,
            source_revision_time=None,
        )

        existing_map = self.session.get(
            LegacyRepositoryObservationMap,
            legacy.observation_id,
        )
        if existing_map is None:
            self.evidence.persist_observation(observation)
            self.session.add(
                LegacyRepositoryObservationMap(
                    legacy_observation_id=legacy.observation_id,
                    generic_observation_id=observation.observation_id,
                    source_identity_digest=identity.digest,
                    capture_evidence_digest=_legacy_capture_evidence_digest(legacy),
                    mapping_version=REPOSITORY_PRODUCER_MAPPING_VERSION,
                )
            )
            self.session.flush()
            return observation

        loaded = self.evidence.load_observation(existing_map.generic_observation_id)
        if (
            existing_map.generic_observation_id != observation.observation_id
            or existing_map.source_identity_digest != identity.digest
            or existing_map.capture_evidence_digest
            != _legacy_capture_evidence_digest(legacy)
            or loaded.binding != observation.binding
            or loaded.resource_version_ref != observation.resource_version_ref
            or loaded.evidence != observation.evidence
            or loaded.observed_at != observation.observed_at
        ):
            raise KnowledgeInvariantError(
                "repository observation mapping conflicts with exact verified evidence"
            )
        # Producer version is evidence about the mapping path, not canonical source
        # identity. Existing 2B/2C observations remain valid inputs.
        return loaded

    def _persist_repository_decision(
        self,
        *,
        receipt: RepositoryImportReceipt,
        source: GovernedProjectionSource,
        observation: GovernedSourceObservation,
    ) -> GovernedSourceDecision:
        legacy_observation_id = source.observation.observation_id
        decision = GovernedSourceDecision(
            decision_id=uuid5(
                _REPOSITORY_DECISION_NAMESPACE,
                ":".join(
                    (
                        receipt.manifest_digest,
                        str(legacy_observation_id),
                        source.role.value,
                    )
                ),
            ),
            observation_id=observation.observation_id,
            policy_id=COMPLETE_CORPUS_SELECTION_POLICY_ID,
            classification=source.observation.classification,
            retrieval_lifecycle=source.observation.document_lifecycle,
            authority_rank=source.observation.authority_rank,
            rationale=source.observation.rationale,
            decided_at=receipt.created_at,
        )
        self.evidence.persist_decision(decision)
        mapping = self.session.get(
            LegacyRepositoryDecisionMap,
            (receipt.manifest_digest, legacy_observation_id),
        )
        if mapping is None:
            self.session.add(
                LegacyRepositoryDecisionMap(
                    governing_manifest_digest=receipt.manifest_digest,
                    legacy_observation_id=legacy_observation_id,
                    decision_id=decision.decision_id,
                    selection_role=source.role.value,
                    mapping_version=REPOSITORY_PRODUCER_MAPPING_VERSION,
                )
            )
            self.session.flush()
        elif (
            mapping.decision_id != decision.decision_id
            or mapping.selection_role != source.role.value
            or mapping.mapping_version != REPOSITORY_PRODUCER_MAPPING_VERSION
        ):
            raise KnowledgeInvariantError(
                "repository decision mapping conflicts with complete-corpus selection"
            )
        return decision

    def _repository_exclusions(
        self,
        receipt: RepositoryImportReceipt,
    ) -> tuple[GovernedSnapshotExclusion, ...]:
        manifest = receipt.manifest_json
        retirements = manifest.get("retirements") if isinstance(manifest, dict) else None
        if not isinstance(retirements, list):
            raise KnowledgeInvariantError("repository receipt retirements are invalid")
        result: list[GovernedSnapshotExclusion] = []
        for retirement in retirements:
            if not isinstance(retirement, dict):
                raise KnowledgeInvariantError("repository retirement is invalid")
            if retirement.get("historical_retrieval") != "exclude":
                continue
            document_key = retirement.get("source_document_key")
            if not isinstance(document_key, str) or not document_key:
                raise KnowledgeInvariantError(
                    "repository retirement exclusion has invalid source identity"
                )
            binding = self.session.get(
                RepositoryDocumentBinding,
                (receipt.source_repository_key, document_key),
            )
            if binding is None:
                raise KnowledgeInvariantError(
                    "repository retirement exclusion has no stable document binding"
                )
            source_binding = GovernedSourceBinding(
                source_identity=_repository_source_identity(
                    source_repository_key=receipt.source_repository_key,
                    source_document_key=document_key,
                ),
                resource_ref=binding.resource_ref,
            )
            self.evidence._persist_binding(source_binding)
            result.append(
                GovernedSnapshotExclusion(
                    source_identity_digest=source_binding.source_identity.digest,
                    reason_code="repository-retirement-exclude",
                )
            )
        return tuple(result)

    def _receipt(self, manifest_digest: str) -> RepositoryImportReceipt:
        receipt = self.session.get(RepositoryImportReceipt, manifest_digest)
        if receipt is None or receipt.status not in {"applying", "settled"}:
            raise KnowledgeInvariantError(
                "repository observation is not backed by an eligible receipt"
            )
        return receipt

    @staticmethod
    def _validate_complete_snapshot(snapshot: GovernedRetrievalSnapshot) -> None:
        member_identities = {item.source_identity_digest for item in snapshot.members}
        exclusion_identities = {
            item.source_identity_digest for item in snapshot.exclusions
        }
        overlap = member_identities & exclusion_identities
        if overlap:
            raise KnowledgeInvariantError(
                "complete governed snapshot both selects and excludes a source identity"
            )
