from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from uuid import UUID, uuid5

from knowledge_core.application.governed_source_evidence import (
    GovernedSourceEvidenceKnowledgeKernel,
)
from knowledge_core.application.repository_governed_producer import (
    COMPLETE_CORPUS_SELECTION_POLICY_ID,
    RepositoryGovernedProducerKnowledgeKernel,
)
from knowledge_core.application.resource_service import ResourceServiceKnowledgeKernel
from knowledge_core.application.resources import ResourceKnowledgeKernel
from knowledge_core.application.section_publication_v2 import (
    SourceNeutralSectionPublicationKnowledgeKernel,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.domain.governed_sources import (
    GovernedRetrievalSnapshot,
    GovernedSnapshotMember,
    GovernedSourceBinding,
    GovernedSourceDecision,
    GovernedSourceIdentity,
    GovernedSourceObservation,
    SourceEvidenceRef,
)
from knowledge_core.domain.resources import ResourceLocatorKind
from knowledge_core.domain.retrieval import RetrievalLifecycleState
from knowledge_core.storage.governed_source_models import GovernedSourceBindingRecord


DIRECT_NOTE_PRODUCER_VERSION = "kc-direct-note-producer-v1"
DIRECT_NOTE_GOVERNANCE_POLICY_ID = "kc-direct-note-governance-v1"
DIRECT_NOTE_SOURCE_KIND = "local.user-note"
DIRECT_NOTE_COLLECTION_KEY = "notes"
_DIRECT_NOTE_OPERATION_NAMESPACE = UUID("936df86f-ef18-51a4-9870-1b78a2b18ac7")
_DIRECT_NOTE_OBSERVATION_NAMESPACE = UUID("d6b3d705-09ea-558b-b6d7-af92e65ca1d2")
_DIRECT_NOTE_DECISION_NAMESPACE = UUID("0ac4f289-35b1-5f64-bacb-bc9099cbf8a2")


@dataclass(frozen=True)
class DirectNoteCanonicalStoreResult:
    source_id: str
    source_identity_digest: str
    resource_ref: UUID
    resource_version_ref: UUID
    observation_id: UUID
    decision_id: UUID
    project_key: str
    content_sha256: str
    observed_at: datetime


@dataclass(frozen=True)
class DirectNotePublicationResult:
    text_state: str
    generation_id: UUID | None
    snapshot_digest: str | None
    error_code: str | None = None


def direct_note_operation_id(*, principal_ref: str, idempotency_key: str) -> UUID:
    principal = principal_ref.strip()
    key = idempotency_key.strip()
    if not principal:
        raise ValueError("principal_ref must be non-blank")
    if not key:
        raise ValueError("idempotency_key must be non-blank")
    if len(key) > 200:
        raise ValueError("idempotency_key must be at most 200 characters")
    return uuid5(_DIRECT_NOTE_OPERATION_NAMESPACE, f"{principal}:{key}")


def _submission_evidence_digest(
    *,
    source_id: str,
    project_key: str,
    content_sha256: str,
    source_event_time: datetime | None,
) -> str:
    payload = {
        "content_sha256": content_sha256,
        "producer_version": DIRECT_NOTE_PRODUCER_VERSION,
        "project_key": project_key,
        "source_event_time": (
            source_event_time.isoformat() if source_event_time is not None else None
        ),
        "source_id": source_id,
        "source_kind": DIRECT_NOTE_SOURCE_KIND,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


class DirectNoteStoreKnowledgeKernel(ResourceServiceKnowledgeKernel):
    """Task 2E canonical direct-note admission plus separate SR-2 publication."""

    def store_note_operation(
        self,
        *,
        operation_id: UUID,
        caller_principal_ref: str,
        content: str,
        project_key: str,
        source_id: str | None = None,
        source_event_time: datetime | None = None,
    ) -> DirectNoteCanonicalStoreResult:
        if not content or not content.strip():
            raise KnowledgeInvariantError("direct note content must be non-blank")
        project = project_key.strip()
        if not project:
            raise KnowledgeInvariantError("direct note project must be non-blank")
        effective_source_id = (
            source_id.strip()
            if source_id is not None and source_id.strip()
            else f"note-{operation_id}"
        )
        identity = GovernedSourceIdentity(
            source_kind=DIRECT_NOTE_SOURCE_KIND,
            origin_scope=caller_principal_ref,
            collection_key=DIRECT_NOTE_COLLECTION_KEY,
            item_key=effective_source_id,
        )
        content_bytes = content.encode("utf-8")
        content_digest = sha256(content_bytes).hexdigest()

        # The accepted resource semantic profile predates Usable V1 and is reused
        # here deliberately. Bootstrap it outside the idempotent store operation so
        # profile setup is not conflated with user evidence identity.
        foundation = ResourceKnowledgeKernel.bootstrap_resource_test_profile(self)
        observation_id = uuid5(
            _DIRECT_NOTE_OBSERVATION_NAMESPACE,
            f"{caller_principal_ref}:{operation_id}",
        )
        decision_id = uuid5(
            _DIRECT_NOTE_DECISION_NAMESPACE,
            f"{caller_principal_ref}:{operation_id}",
        )
        payload = {
            "source_kind": DIRECT_NOTE_SOURCE_KIND,
            "source_id": effective_source_id,
            "project_key": project,
            "content_sha256": content_digest,
            "content_size": len(content_bytes),
            "source_event_time": source_event_time,
        }

        def action() -> DirectNoteCanonicalStoreResult:
            binding_row = self.session.get(
                GovernedSourceBindingRecord,
                identity.digest,
            )
            if binding_row is None:
                resource = ResourceKnowledgeKernel.create_resource(
                    self,
                    kind_revision_ref=foundation.artifact_kind_revision_ref,
                )
                resource_ref = resource.resource_ref
            else:
                if (
                    binding_row.source_kind != identity.source_kind
                    or binding_row.origin_scope != identity.origin_scope
                    or binding_row.collection_key != identity.collection_key
                    or binding_row.item_key != identity.item_key
                ):
                    raise KnowledgeInvariantError(
                        "direct note source identity digest resolved to different source metadata"
                    )
                resource_ref = binding_row.resource_ref
                self._require_serving_resource(resource_ref)

            version = ResourceKnowledgeKernel.ingest_resource_version(
                self,
                resource_ref=resource_ref,
                content=content_bytes,
                ingestion_kind_revision_ref=(
                    foundation.resource_ingestion_kind_revision_ref
                ),
                media_type="text/plain",
                locator_kind=ResourceLocatorKind.GOVERNED_OTHER,
                locator_text=f"user-note:{effective_source_id}",
            )
            observed_at = self._now()
            observation = GovernedSourceObservation(
                observation_id=observation_id,
                binding=GovernedSourceBinding(
                    source_identity=identity,
                    resource_ref=resource_ref,
                ),
                resource_version_ref=version.resource_version_ref,
                producer_id="kc.direct-note",
                producer_version=DIRECT_NOTE_PRODUCER_VERSION,
                evidence=(
                    SourceEvidenceRef(
                        evidence_kind="local.authenticated-submission-v1",
                        evidence_ref=f"kc_store:{operation_id}",
                        evidence_digest=_submission_evidence_digest(
                            source_id=effective_source_id,
                            project_key=project,
                            content_sha256=content_digest,
                            source_event_time=source_event_time,
                        ),
                    ),
                ),
                observed_at=observed_at,
                source_event_time=source_event_time,
            )
            decision = GovernedSourceDecision(
                decision_id=decision_id,
                observation_id=observation.observation_id,
                policy_id=DIRECT_NOTE_GOVERNANCE_POLICY_ID,
                classification="direct-user-note",
                retrieval_lifecycle=RetrievalLifecycleState.CURRENT,
                authority_rank=10,
                rationale="Authenticated local owner direct note submission.",
                decided_at=observed_at,
            )
            evidence = GovernedSourceEvidenceKnowledgeKernel(self.session)
            evidence.persist_observation(observation)
            evidence.persist_decision(decision)
            return DirectNoteCanonicalStoreResult(
                source_id=effective_source_id,
                source_identity_digest=identity.digest,
                resource_ref=resource_ref,
                resource_version_ref=version.resource_version_ref,
                observation_id=observation.observation_id,
                decision_id=decision.decision_id,
                project_key=project,
                content_sha256=content_digest,
                observed_at=observed_at,
            )

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="kc.store.direct-note",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=None,
            action=action,
            encode_result=lambda result: {
                "source_id": result.source_id,
                "source_identity_digest": result.source_identity_digest,
                "resource_ref": str(result.resource_ref),
                "resource_version_ref": str(result.resource_version_ref),
                "observation_id": str(result.observation_id),
                "decision_id": str(result.decision_id),
                "project_key": result.project_key,
                "content_sha256": result.content_sha256,
                "observed_at": result.observed_at.isoformat(),
            },
            replay=lambda metadata: DirectNoteCanonicalStoreResult(
                source_id=str(metadata["source_id"]),
                source_identity_digest=str(metadata["source_identity_digest"]),
                resource_ref=UUID(str(metadata["resource_ref"])),
                resource_version_ref=UUID(str(metadata["resource_version_ref"])),
                observation_id=UUID(str(metadata["observation_id"])),
                decision_id=UUID(str(metadata["decision_id"])),
                project_key=str(metadata["project_key"]),
                content_sha256=str(metadata["content_sha256"]),
                observed_at=datetime.fromisoformat(str(metadata["observed_at"])),
            ),
            # A new authenticated observation of bytes already stored for the same
            # logical note is legitimate evidence even if it creates no new
            # canonical ResourceVersion revision.
            allow_no_canonical_revision=True,
        )

    def publish_note_text(
        self,
        canonical: DirectNoteCanonicalStoreResult,
    ) -> DirectNotePublicationResult:
        evidence = GovernedSourceEvidenceKnowledgeKernel(self.session)
        observation = evidence.load_observation(canonical.observation_id)
        decision = evidence.load_decision(canonical.decision_id)
        if observation.binding.source_identity.digest != canonical.source_identity_digest:
            raise KnowledgeInvariantError(
                "direct note canonical result no longer matches governed source identity"
            )
        if observation.resource_version_ref != canonical.resource_version_ref:
            raise KnowledgeInvariantError(
                "direct note canonical result no longer matches governed ResourceVersion"
            )

        publication = SourceNeutralSectionPublicationKnowledgeKernel(
            self.session,
            artifact_store=self.artifact_store,
        )
        predecessor_digest = publication.current_serving_snapshot_digest()
        predecessor = (
            evidence.load_snapshot(predecessor_digest)
            if predecessor_digest is not None
            else None
        )

        if predecessor is not None:
            current_member = next(
                (
                    member
                    for member in predecessor.members
                    if member.source_identity_digest == canonical.source_identity_digest
                ),
                None,
            )
            if current_member is not None:
                if (
                    current_member.observation_id == canonical.observation_id
                    and current_member.decision_id == canonical.decision_id
                    and canonical.project_key in current_member.project_keys
                ):
                    current = publication._generation_kernel().current_generation(
                        derived_kind=DerivedKind.TEXT
                    )
                    return DirectNotePublicationResult(
                        text_state="searchable",
                        generation_id=(
                            current.generation_id if current is not None else None
                        ),
                        snapshot_digest=predecessor.digest,
                    )
                current_observation = evidence.load_observation(
                    current_member.observation_id
                )
                if current_observation.observed_at >= canonical.observed_at:
                    current = publication._generation_kernel().current_generation(
                        derived_kind=DerivedKind.TEXT
                    )
                    return DirectNotePublicationResult(
                        text_state="superseded",
                        generation_id=(
                            current.generation_id if current is not None else None
                        ),
                        snapshot_digest=predecessor.digest,
                    )

        members = []
        exclusions = []
        if predecessor is not None:
            members.extend(
                member
                for member in predecessor.members
                if member.source_identity_digest != canonical.source_identity_digest
            )
            exclusions.extend(
                exclusion
                for exclusion in predecessor.exclusions
                if exclusion.source_identity_digest != canonical.source_identity_digest
            )
        members.append(
            GovernedSnapshotMember.from_selection(
                observation=observation,
                decision=decision,
                project_keys=(canonical.project_key,),
            )
        )
        snapshot = GovernedRetrievalSnapshot(
            selection_policy_id=COMPLETE_CORPUS_SELECTION_POLICY_ID,
            created_at=self._now(),
            members=tuple(members),
            exclusions=tuple(exclusions),
            predecessor_snapshot_digest=predecessor_digest,
        )
        RepositoryGovernedProducerKnowledgeKernel._validate_complete_snapshot(snapshot)
        evidence.persist_snapshot(snapshot)
        # Persist the complete source selection independently of the derived build.
        # A later build failure must not erase canonical or governance evidence.
        self.session.commit()

        try:
            candidate = publication.build_segment_generation_candidate(
                governing_snapshot_digest=snapshot.digest
            )
            current = publication.promote_segment_generation(
                generation_id=candidate.generation_id,
                governing_snapshot_digest=snapshot.digest,
                expected_predecessor_snapshot_digest=predecessor_digest,
            )
            return DirectNotePublicationResult(
                text_state="searchable",
                generation_id=current.generation_id,
                snapshot_digest=snapshot.digest,
            )
        except KnowledgeInvariantError as exc:
            self.session.rollback()
            return DirectNotePublicationResult(
                text_state="pending",
                generation_id=None,
                snapshot_digest=snapshot.digest,
                error_code=exc.__class__.__name__,
            )
        except Exception as exc:  # derived failure cannot invalidate canonical store
            self.session.rollback()
            return DirectNotePublicationResult(
                text_state="failed",
                generation_id=None,
                snapshot_digest=snapshot.digest,
                error_code=exc.__class__.__name__,
            )
