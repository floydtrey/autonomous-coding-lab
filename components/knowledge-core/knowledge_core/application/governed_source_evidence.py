from __future__ import annotations

from hashlib import sha256
import json
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_core.application.governed_source_selection import (
    GovernedProjectionSource,
    resolve_governed_projection_sources,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.governed_sources import (
    GOVERNED_SNAPSHOT_CONTRACT_VERSION,
    GOVERNED_SOURCE_CONTRACT_VERSION,
    GovernedRetrievalSnapshot,
    GovernedSnapshotExclusion,
    GovernedSnapshotMember,
    GovernedSourceBinding,
    GovernedSourceDecision,
    GovernedSourceIdentity,
    GovernedSourceObservation,
    SourceEvidenceRef,
)
from knowledge_core.storage.governed_source_models import (
    GovernedRetrievalSnapshotRecord,
    GovernedSnapshotExclusionRecord,
    GovernedSnapshotMemberRecord,
    GovernedSnapshotProjectRecord,
    GovernedSourceBindingRecord,
    GovernedSourceDecisionRecord,
    GovernedSourceEvidenceRecord,
    GovernedSourceObservationRecord,
    LegacyRepositoryDecisionMap,
    LegacyRepositoryObservationMap,
    LegacyRepositorySnapshotMap,
)
from knowledge_core.storage.repository_import_models import (
    RepositoryDocumentBinding,
    RepositoryImportReceipt,
    RepositorySourceObservation,
)
from knowledge_core.storage.resource_models import ResourceVersion


LEGACY_REPOSITORY_MAPPING_VERSION = "kc-legacy-repository-governed-source-v1"
LEGACY_REPOSITORY_SELECTION_POLICY_ID = "kc-legacy-ri2-selection-v1"
LEGACY_REPOSITORY_OBSERVATION_NAMESPACE = UUID(
    "13ff4aae-1785-5f0c-a317-f56f0033443b"
)
LEGACY_REPOSITORY_DECISION_NAMESPACE = UUID(
    "29a0ec35-ed50-5902-8a37-366e18b2d74a"
)


def _sha256_payload(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _repository_source_identity(
    *, source_repository_key: str, source_document_key: str
) -> GovernedSourceIdentity:
    return GovernedSourceIdentity(
        source_kind="git.repository-document",
        origin_scope=f"repository:{source_repository_key}",
        collection_key="documents",
        item_key=source_document_key,
    )


def _legacy_capture_evidence_digest(row: RepositorySourceObservation) -> str:
    return _sha256_payload(
        {
            "git_blob_sha": row.git_blob_sha,
            "legacy_observation_id": str(row.observation_id),
            "manifest_digest": row.manifest_digest,
            "mapping_version": LEGACY_REPOSITORY_MAPPING_VERSION,
            "path": row.path,
            "resource_ref": str(row.resource_ref),
            "resource_version_ref": str(row.resource_version_ref),
            "source_commit": row.source_commit,
            "source_document_key": row.source_document_key,
            "source_repository_key": row.source_repository_key,
        }
    )


class GovernedSourceEvidenceKnowledgeKernel:
    """Persist source-neutral evidence without changing any serving generation."""

    def __init__(self, session: Session):
        self.session = session

    def persist_observation(
        self,
        observation: GovernedSourceObservation,
    ) -> GovernedSourceObservation:
        version = self.session.get(ResourceVersion, observation.resource_version_ref)
        if version is None:
            raise KnowledgeInvariantError(
                f"unknown governed observation ResourceVersion: {observation.resource_version_ref}"
            )
        if version.resource_ref_id != observation.binding.resource_ref:
            raise KnowledgeInvariantError(
                "governed source binding Resource does not own the selected ResourceVersion"
            )

        self._persist_binding(observation.binding)
        existing = self.session.get(
            GovernedSourceObservationRecord,
            observation.observation_id,
        )
        if existing is None:
            self.session.add(
                GovernedSourceObservationRecord(
                    observation_id=observation.observation_id,
                    contract_version=GOVERNED_SOURCE_CONTRACT_VERSION,
                    source_identity_digest=observation.binding.source_identity.digest,
                    resource_version_ref=observation.resource_version_ref,
                    producer_id=observation.producer_id,
                    producer_version=observation.producer_version,
                    observed_at=observation.observed_at,
                    source_event_time=observation.source_event_time,
                    source_revision_time=observation.source_revision_time,
                    observation_digest=observation.digest,
                )
            )
            # There is intentionally no ORM relationship between the generic
            # observation and its evidence rows. Flush the parent explicitly so
            # PostgreSQL can enforce the child foreign key deterministically.
            self.session.flush()
            for ordinal, evidence in enumerate(observation.evidence):
                self.session.add(
                    GovernedSourceEvidenceRecord(
                        observation_id=observation.observation_id,
                        evidence_ordinal=ordinal,
                        evidence_kind=evidence.evidence_kind,
                        evidence_ref=evidence.evidence_ref,
                        evidence_digest=evidence.evidence_digest,
                    )
                )
            self.session.flush()
        else:
            if self.load_observation(observation.observation_id) != observation:
                raise KnowledgeInvariantError(
                    "governed observation identity was reused with different evidence"
                )
        return observation

    def persist_decision(
        self,
        decision: GovernedSourceDecision,
    ) -> GovernedSourceDecision:
        if self.session.get(GovernedSourceObservationRecord, decision.observation_id) is None:
            raise KnowledgeInvariantError(
                "governed decision references an unknown observation"
            )
        existing = self.session.get(GovernedSourceDecisionRecord, decision.decision_id)
        if existing is None:
            self.session.add(
                GovernedSourceDecisionRecord(
                    decision_id=decision.decision_id,
                    contract_version=GOVERNED_SOURCE_CONTRACT_VERSION,
                    observation_id=decision.observation_id,
                    policy_id=decision.policy_id,
                    classification=decision.classification,
                    retrieval_lifecycle=decision.retrieval_lifecycle.value,
                    authority_rank=decision.authority_rank,
                    rationale=decision.rationale,
                    decided_at=decision.decided_at,
                    decision_digest=decision.digest,
                )
            )
            self.session.flush()
        else:
            if self.load_decision(decision.decision_id) != decision:
                raise KnowledgeInvariantError(
                    "governed decision identity was reused with different evidence"
                )
        return decision

    def persist_snapshot(
        self,
        snapshot: GovernedRetrievalSnapshot,
    ) -> GovernedRetrievalSnapshot:
        existing = self.session.get(
            GovernedRetrievalSnapshotRecord,
            snapshot.digest,
        )
        if existing is not None:
            if self.load_snapshot(snapshot.digest) != snapshot:
                raise KnowledgeInvariantError(
                    "governed snapshot digest resolved to different persisted evidence"
                )
            return snapshot

        if snapshot.predecessor_snapshot_digest is not None and self.session.get(
            GovernedRetrievalSnapshotRecord,
            snapshot.predecessor_snapshot_digest,
        ) is None:
            raise KnowledgeInvariantError(
                "governed snapshot predecessor is not durably present"
            )

        for member in snapshot.members:
            observation = self.load_observation(member.observation_id)
            decision = self.load_decision(member.decision_id)
            expected = GovernedSnapshotMember.from_selection(
                observation=observation,
                decision=decision,
                project_keys=member.project_keys,
            )
            if expected != member:
                raise KnowledgeInvariantError(
                    "governed snapshot member does not match persisted observation/decision evidence"
                )

        for exclusion in snapshot.exclusions:
            binding = self.session.get(
                GovernedSourceBindingRecord,
                exclusion.source_identity_digest,
            )
            if binding is None:
                raise KnowledgeInvariantError(
                    "governed snapshot exclusion references an unknown source identity"
                )
            if exclusion.observation_id is not None:
                observation = self.load_observation(exclusion.observation_id)
                if (
                    observation.binding.source_identity.digest
                    != exclusion.source_identity_digest
                ):
                    raise KnowledgeInvariantError(
                        "governed snapshot exclusion observation belongs to another source identity"
                    )

        self.session.add(
            GovernedRetrievalSnapshotRecord(
                snapshot_digest=snapshot.digest,
                contract_version=GOVERNED_SNAPSHOT_CONTRACT_VERSION,
                selection_policy_id=snapshot.selection_policy_id,
                predecessor_snapshot_digest=snapshot.predecessor_snapshot_digest,
                created_at=snapshot.created_at,
            )
        )
        self.session.flush()
        for member in snapshot.members:
            self.session.add(
                GovernedSnapshotMemberRecord(
                    snapshot_digest=snapshot.digest,
                    source_identity_digest=member.source_identity_digest,
                    observation_id=member.observation_id,
                    resource_ref=member.resource_ref,
                    resource_version_ref=member.resource_version_ref,
                    observation_digest=member.observation_digest,
                    decision_id=member.decision_id,
                    decision_digest=member.decision_digest,
                )
            )
            for project_key in sorted(member.project_keys):
                self.session.add(
                    GovernedSnapshotProjectRecord(
                        snapshot_digest=snapshot.digest,
                        source_identity_digest=member.source_identity_digest,
                        observation_id=member.observation_id,
                        project_key=project_key,
                    )
                )
        for ordinal, exclusion in enumerate(
            sorted(
                snapshot.exclusions,
                key=lambda item: (
                    item.source_identity_digest,
                    str(item.observation_id),
                    item.reason_code,
                ),
            )
        ):
            self.session.add(
                GovernedSnapshotExclusionRecord(
                    snapshot_digest=snapshot.digest,
                    exclusion_ordinal=ordinal,
                    source_identity_digest=exclusion.source_identity_digest,
                    observation_id=exclusion.observation_id,
                    reason_code=exclusion.reason_code,
                )
            )
        self.session.flush()
        return snapshot

    def load_observation(self, observation_id: UUID) -> GovernedSourceObservation:
        row = self.session.get(GovernedSourceObservationRecord, observation_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown governed observation: {observation_id}")
        binding_row = self.session.get(
            GovernedSourceBindingRecord,
            row.source_identity_digest,
        )
        if binding_row is None:
            raise KnowledgeInvariantError("governed observation is missing its source binding")
        evidence_rows = self.session.scalars(
            select(GovernedSourceEvidenceRecord)
            .where(GovernedSourceEvidenceRecord.observation_id == observation_id)
            .order_by(GovernedSourceEvidenceRecord.evidence_ordinal)
        ).all()
        observation = GovernedSourceObservation(
            observation_id=row.observation_id,
            binding=GovernedSourceBinding(
                source_identity=GovernedSourceIdentity(
                    source_kind=binding_row.source_kind,
                    origin_scope=binding_row.origin_scope,
                    collection_key=binding_row.collection_key,
                    item_key=binding_row.item_key,
                ),
                resource_ref=binding_row.resource_ref,
            ),
            resource_version_ref=row.resource_version_ref,
            producer_id=row.producer_id,
            producer_version=row.producer_version,
            evidence=tuple(
                SourceEvidenceRef(
                    evidence_kind=item.evidence_kind,
                    evidence_ref=item.evidence_ref,
                    evidence_digest=item.evidence_digest,
                )
                for item in evidence_rows
            ),
            observed_at=row.observed_at,
            source_event_time=row.source_event_time,
            source_revision_time=row.source_revision_time,
        )
        if observation.digest != row.observation_digest:
            raise KnowledgeInvariantError(
                "persisted governed observation digest does not reconstruct"
            )
        return observation

    def load_decision(self, decision_id: UUID) -> GovernedSourceDecision:
        row = self.session.get(GovernedSourceDecisionRecord, decision_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown governed decision: {decision_id}")
        from knowledge_core.domain.retrieval import RetrievalLifecycleState

        decision = GovernedSourceDecision(
            decision_id=row.decision_id,
            observation_id=row.observation_id,
            policy_id=row.policy_id,
            classification=row.classification,
            retrieval_lifecycle=RetrievalLifecycleState(row.retrieval_lifecycle),
            authority_rank=row.authority_rank,
            rationale=row.rationale,
            decided_at=row.decided_at,
        )
        if decision.digest != row.decision_digest:
            raise KnowledgeInvariantError(
                "persisted governed decision digest does not reconstruct"
            )
        return decision

    def load_snapshot(self, snapshot_digest: str) -> GovernedRetrievalSnapshot:
        row = self.session.get(GovernedRetrievalSnapshotRecord, snapshot_digest)
        if row is None:
            raise KnowledgeInvariantError(f"unknown governed snapshot: {snapshot_digest}")
        member_rows = self.session.scalars(
            select(GovernedSnapshotMemberRecord)
            .where(GovernedSnapshotMemberRecord.snapshot_digest == snapshot_digest)
            .order_by(
                GovernedSnapshotMemberRecord.source_identity_digest,
                GovernedSnapshotMemberRecord.observation_id,
                GovernedSnapshotMemberRecord.decision_id,
            )
        ).all()
        project_rows = self.session.scalars(
            select(GovernedSnapshotProjectRecord).where(
                GovernedSnapshotProjectRecord.snapshot_digest == snapshot_digest
            )
        ).all()
        projects: dict[tuple[str, UUID], list[str]] = {}
        for item in project_rows:
            projects.setdefault(
                (item.source_identity_digest, item.observation_id), []
            ).append(item.project_key)
        members = tuple(
            GovernedSnapshotMember(
                source_identity_digest=item.source_identity_digest,
                resource_ref=item.resource_ref,
                resource_version_ref=item.resource_version_ref,
                observation_id=item.observation_id,
                observation_digest=item.observation_digest,
                decision_id=item.decision_id,
                decision_digest=item.decision_digest,
                project_keys=tuple(
                    sorted(
                        projects.get(
                            (item.source_identity_digest, item.observation_id),
                            [],
                        )
                    )
                ),
            )
            for item in member_rows
        )
        exclusion_rows = self.session.scalars(
            select(GovernedSnapshotExclusionRecord)
            .where(GovernedSnapshotExclusionRecord.snapshot_digest == snapshot_digest)
            .order_by(GovernedSnapshotExclusionRecord.exclusion_ordinal)
        ).all()
        snapshot = GovernedRetrievalSnapshot(
            selection_policy_id=row.selection_policy_id,
            created_at=row.created_at,
            members=members,
            exclusions=tuple(
                GovernedSnapshotExclusion(
                    source_identity_digest=item.source_identity_digest,
                    observation_id=item.observation_id,
                    reason_code=item.reason_code,
                )
                for item in exclusion_rows
            ),
            predecessor_snapshot_digest=row.predecessor_snapshot_digest,
            contract_version=row.contract_version,
        )
        if snapshot.digest != snapshot_digest:
            raise KnowledgeInvariantError(
                "persisted governed snapshot digest does not reconstruct"
            )
        return snapshot

    def map_settled_repository_receipt(
        self,
        governing_manifest_digest: str,
    ) -> GovernedRetrievalSnapshot:
        receipt = self.session.get(
            RepositoryImportReceipt,
            governing_manifest_digest,
        )
        if receipt is None:
            raise KnowledgeInvariantError("unknown legacy repository receipt")
        if receipt.status != "settled" or receipt.settled_at is None:
            raise KnowledgeInvariantError(
                "only settled legacy repository receipts can map into governed evidence"
            )

        existing_map = self.session.get(
            LegacyRepositorySnapshotMap,
            governing_manifest_digest,
        )
        if existing_map is not None:
            if existing_map.mapping_version != LEGACY_REPOSITORY_MAPPING_VERSION:
                raise KnowledgeInvariantError(
                    "legacy repository snapshot mapping uses an unexpected version"
                )
            return self.load_snapshot(existing_map.snapshot_digest)

        predecessor_snapshot_digest = None
        if receipt.previous_manifest_digest is not None:
            predecessor = self.map_settled_repository_receipt(
                receipt.previous_manifest_digest
            )
            predecessor_snapshot_digest = predecessor.digest

        sources = resolve_governed_projection_sources(
            self.session,
            governing_manifest_digest=governing_manifest_digest,
        )
        members: list[GovernedSnapshotMember] = []
        decision_maps: list[tuple[GovernedProjectionSource, GovernedSourceDecision]] = []
        for source in sources:
            legacy_row = self.session.get(
                RepositorySourceObservation,
                source.observation.observation_id,
            )
            if legacy_row is None:
                raise KnowledgeInvariantError(
                    "legacy governed source selection references a missing observation"
                )
            observation = self._map_repository_observation(legacy_row)
            decision_id = uuid5(
                LEGACY_REPOSITORY_DECISION_NAMESPACE,
                ":".join(
                    (
                        governing_manifest_digest,
                        str(legacy_row.observation_id),
                        source.role.value,
                    )
                ),
            )
            decision = GovernedSourceDecision(
                decision_id=decision_id,
                observation_id=observation.observation_id,
                policy_id=LEGACY_REPOSITORY_SELECTION_POLICY_ID,
                classification=source.observation.classification,
                retrieval_lifecycle=source.observation.document_lifecycle,
                authority_rank=source.observation.authority_rank,
                rationale=source.observation.rationale,
                decided_at=receipt.settled_at,
            )
            self.persist_decision(decision)
            members.append(
                GovernedSnapshotMember.from_selection(
                    observation=observation,
                    decision=decision,
                )
            )
            decision_maps.append((source, decision))

        exclusions = self._legacy_retirement_exclusions(receipt)
        snapshot = GovernedRetrievalSnapshot(
            selection_policy_id=LEGACY_REPOSITORY_SELECTION_POLICY_ID,
            created_at=receipt.settled_at,
            members=tuple(members),
            exclusions=exclusions,
            predecessor_snapshot_digest=predecessor_snapshot_digest,
        )
        self.persist_snapshot(snapshot)

        for source, decision in decision_maps:
            row = self.session.get(
                LegacyRepositoryDecisionMap,
                (governing_manifest_digest, source.observation.observation_id),
            )
            expected = {
                "decision_id": decision.decision_id,
                "selection_role": source.role.value,
                "mapping_version": LEGACY_REPOSITORY_MAPPING_VERSION,
            }
            if row is None:
                self.session.add(
                    LegacyRepositoryDecisionMap(
                        governing_manifest_digest=governing_manifest_digest,
                        legacy_observation_id=source.observation.observation_id,
                        **expected,
                    )
                )
            elif any(getattr(row, key) != value for key, value in expected.items()):
                raise KnowledgeInvariantError(
                    "legacy repository decision mapping is inconsistent"
                )

        self.session.add(
            LegacyRepositorySnapshotMap(
                governing_manifest_digest=governing_manifest_digest,
                snapshot_digest=snapshot.digest,
                mapping_version=LEGACY_REPOSITORY_MAPPING_VERSION,
            )
        )
        self.session.commit()
        return snapshot

    def _persist_binding(self, binding: GovernedSourceBinding) -> None:
        identity = binding.source_identity
        existing = self.session.get(
            GovernedSourceBindingRecord,
            identity.digest,
        )
        expected = {
            "contract_version": GOVERNED_SOURCE_CONTRACT_VERSION,
            "source_kind": identity.source_kind,
            "origin_scope": identity.origin_scope,
            "collection_key": identity.collection_key,
            "item_key": identity.item_key,
            "resource_ref": binding.resource_ref,
        }
        if existing is None:
            self.session.add(
                GovernedSourceBindingRecord(
                    source_identity_digest=identity.digest,
                    **expected,
                )
            )
            self.session.flush()
        elif any(getattr(existing, key) != value for key, value in expected.items()):
            raise KnowledgeInvariantError(
                "governed source identity was rebound to different canonical evidence"
            )

    def _map_repository_observation(
        self,
        row: RepositorySourceObservation,
    ) -> GovernedSourceObservation:
        receipt = self.session.get(RepositoryImportReceipt, row.manifest_digest)
        if receipt is None or receipt.status != "settled":
            raise KnowledgeInvariantError(
                "legacy repository observation is not backed by a settled receipt"
            )
        identity = _repository_source_identity(
            source_repository_key=row.source_repository_key,
            source_document_key=row.source_document_key,
        )
        capture_digest = _legacy_capture_evidence_digest(row)
        generic_observation_id = uuid5(
            LEGACY_REPOSITORY_OBSERVATION_NAMESPACE,
            str(row.observation_id),
        )
        expected_observation = GovernedSourceObservation(
            observation_id=generic_observation_id,
            binding=GovernedSourceBinding(
                source_identity=identity,
                resource_ref=row.resource_ref,
            ),
            resource_version_ref=row.resource_version_ref,
            producer_id="kc.repository-import",
            producer_version=LEGACY_REPOSITORY_MAPPING_VERSION,
            evidence=(
                SourceEvidenceRef(
                    evidence_kind="legacy.repository-observation-capture-v1",
                    evidence_ref=f"repository_source_observation:{row.observation_id}",
                    evidence_digest=capture_digest,
                ),
            ),
            observed_at=receipt.created_at,
            source_event_time=None,
            source_revision_time=None,
        )

        mapping = self.session.get(
            LegacyRepositoryObservationMap,
            row.observation_id,
        )
        if mapping is not None:
            if mapping.mapping_version != LEGACY_REPOSITORY_MAPPING_VERSION:
                raise KnowledgeInvariantError(
                    "legacy repository observation mapping uses an unexpected version"
                )
            if (
                mapping.generic_observation_id != generic_observation_id
                or mapping.source_identity_digest != identity.digest
                or mapping.capture_evidence_digest != capture_digest
            ):
                raise KnowledgeInvariantError(
                    "legacy repository observation mapping no longer matches immutable source evidence"
                )
            loaded = self.load_observation(mapping.generic_observation_id)
            if loaded != expected_observation:
                raise KnowledgeInvariantError(
                    "mapped governed observation no longer reconstructs from legacy evidence"
                )
            return loaded

        self.persist_observation(expected_observation)
        self.session.add(
            LegacyRepositoryObservationMap(
                legacy_observation_id=row.observation_id,
                generic_observation_id=expected_observation.observation_id,
                source_identity_digest=identity.digest,
                capture_evidence_digest=capture_digest,
                mapping_version=LEGACY_REPOSITORY_MAPPING_VERSION,
            )
        )
        self.session.flush()
        return expected_observation

    def _legacy_retirement_exclusions(
        self,
        receipt: RepositoryImportReceipt,
    ) -> tuple[GovernedSnapshotExclusion, ...]:
        manifest = receipt.manifest_json
        if not isinstance(manifest, dict):
            raise KnowledgeInvariantError("legacy repository manifest payload is invalid")
        retirements = manifest.get("retirements")
        if not isinstance(retirements, list):
            raise KnowledgeInvariantError("legacy repository retirements are invalid")
        exclusions: list[GovernedSnapshotExclusion] = []
        for retirement in retirements:
            if not isinstance(retirement, dict):
                raise KnowledgeInvariantError("legacy repository retirement is invalid")
            if retirement.get("historical_retrieval") != "exclude":
                continue
            document_key = retirement.get("source_document_key")
            if not isinstance(document_key, str) or not document_key:
                raise KnowledgeInvariantError(
                    "legacy repository retirement has invalid document identity"
                )
            binding = self.session.get(
                RepositoryDocumentBinding,
                (receipt.source_repository_key, document_key),
            )
            if binding is None:
                raise KnowledgeInvariantError(
                    "legacy repository exclusion has no stable document binding"
                )
            source_binding = GovernedSourceBinding(
                source_identity=_repository_source_identity(
                    source_repository_key=receipt.source_repository_key,
                    source_document_key=document_key,
                ),
                resource_ref=binding.resource_ref,
            )
            self._persist_binding(source_binding)
            exclusions.append(
                GovernedSnapshotExclusion(
                    source_identity_digest=source_binding.source_identity.digest,
                    reason_code="legacy-retirement-exclude",
                )
            )
        return tuple(exclusions)