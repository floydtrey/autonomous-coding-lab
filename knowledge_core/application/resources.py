from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_core.application.operations import OperationKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError, RefKind
from knowledge_core.domain.resources import (
    EvidenceTrace,
    ImpactTrace,
    ResourceFoundationRefs,
    ResourceLocatorKind,
    ResourceLocatorSnapshot,
    ResourceSnapshot,
    ResourceVersionSnapshot,
)
from knowledge_core.storage.models import (
    Assertion,
    KnowledgeRef,
    Occurrence,
    Revision,
    SemanticKind,
    SemanticKindRevision,
    SemanticPredicate,
    SemanticPredicateRevision,
    SemanticProfile,
    SemanticProfileRevision,
)
from knowledge_core.storage.resource_models import (
    ProvenanceLink,
    Resource,
    ResourceLocator,
    ResourceVersion,
)


class ResourceKnowledgeKernel(OperationKnowledgeKernel):
    """Task 4 exact resource-version storage and traversable provenance."""

    def __init__(
        self,
        session: Session,
        *,
        artifact_store: LocalArtifactStore,
        **kwargs,
    ):
        super().__init__(session, **kwargs)
        self.artifact_store = artifact_store

    def _new_revision(self) -> Revision:
        revision = Revision(
            schema_revision="task4",
            recorded_at=self._now(),
            operation_id=self._active_operation_id,
        )
        self.session.add(revision)
        self.session.flush()
        return revision

    def bootstrap_resource_test_profile(self) -> ResourceFoundationRefs:
        existing = self.session.execute(
            select(SemanticProfile).where(
                SemanticProfile.stable_name == "resource-test"
            )
        ).scalar_one_or_none()
        if existing is not None:
            return self._load_resource_foundation_refs(existing.ref_id)

        revision = self._new_revision()
        profile_ref = self._new_ref(RefKind.SEMANTIC_PROFILE, revision.revision_id)
        profile_revision_ref = self._new_ref(
            RefKind.SEMANTIC_PROFILE_REVISION, revision.revision_id
        )
        self.session.add(
            SemanticProfile(
                ref_id=profile_ref,
                stable_name="resource-test",
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()
        self.session.add(
            SemanticProfileRevision(
                ref_id=profile_revision_ref,
                profile_ref_id=profile_ref,
                version_label="1",
                status="active-capable",
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()

        kind_refs: dict[str, UUID] = {}
        for stable_name in ("artifact", "resource_ingestion"):
            kind_ref = self._new_ref(RefKind.SEMANTIC_KIND, revision.revision_id)
            kind_revision_ref = self._new_ref(
                RefKind.SEMANTIC_KIND_REVISION, revision.revision_id
            )
            self.session.add(
                SemanticKind(
                    ref_id=kind_ref,
                    profile_ref_id=profile_ref,
                    stable_name=stable_name,
                    created_revision_id=revision.revision_id,
                )
            )
            self.session.flush()
            self.session.add(
                SemanticKindRevision(
                    ref_id=kind_revision_ref,
                    kind_ref_id=kind_ref,
                    profile_revision_ref_id=profile_revision_ref,
                    created_revision_id=revision.revision_id,
                )
            )
            kind_refs[stable_name] = kind_revision_ref

        predicate_ref = self._new_ref(
            RefKind.SEMANTIC_PREDICATE, revision.revision_id
        )
        relation_revision_ref = self._new_ref(
            RefKind.SEMANTIC_PREDICATE_REVISION, revision.revision_id
        )
        self.session.add(
            SemanticPredicate(
                ref_id=predicate_ref,
                profile_ref_id=profile_ref,
                stable_name="supports_claim",
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()
        self.session.add(
            SemanticPredicateRevision(
                ref_id=relation_revision_ref,
                predicate_ref_id=predicate_ref,
                profile_revision_ref_id=profile_revision_ref,
                value_shape="reference",
                created_revision_id=revision.revision_id,
            )
        )
        self._commit()
        return ResourceFoundationRefs(
            profile_ref=profile_ref,
            profile_revision_ref=profile_revision_ref,
            artifact_kind_revision_ref=kind_refs["artifact"],
            resource_ingestion_kind_revision_ref=kind_refs["resource_ingestion"],
            supports_claim_relation_revision_ref=relation_revision_ref,
        )

    def _load_resource_foundation_refs(
        self, profile_ref: UUID
    ) -> ResourceFoundationRefs:
        profile_revision = self.session.execute(
            select(SemanticProfileRevision).where(
                SemanticProfileRevision.profile_ref_id == profile_ref,
                SemanticProfileRevision.version_label == "1",
            )
        ).scalar_one()

        kinds: dict[str, UUID] = {}
        for kind in self.session.scalars(
            select(SemanticKind).where(SemanticKind.profile_ref_id == profile_ref)
        ):
            kind_revision = self.session.execute(
                select(SemanticKindRevision).where(
                    SemanticKindRevision.kind_ref_id == kind.ref_id,
                    SemanticKindRevision.profile_revision_ref_id
                    == profile_revision.ref_id,
                )
            ).scalar_one()
            kinds[kind.stable_name] = kind_revision.ref_id

        predicate = self.session.execute(
            select(SemanticPredicate).where(
                SemanticPredicate.profile_ref_id == profile_ref,
                SemanticPredicate.stable_name == "supports_claim",
            )
        ).scalar_one()
        relation = self.session.execute(
            select(SemanticPredicateRevision).where(
                SemanticPredicateRevision.predicate_ref_id == predicate.ref_id,
                SemanticPredicateRevision.profile_revision_ref_id
                == profile_revision.ref_id,
            )
        ).scalar_one()
        return ResourceFoundationRefs(
            profile_ref=profile_ref,
            profile_revision_ref=profile_revision.ref_id,
            artifact_kind_revision_ref=kinds["artifact"],
            resource_ingestion_kind_revision_ref=kinds["resource_ingestion"],
            supports_claim_relation_revision_ref=relation.ref_id,
        )

    def create_resource(self, *, kind_revision_ref: UUID) -> ResourceSnapshot:
        self._require_kind_revision(kind_revision_ref)
        revision = self._new_revision()
        resource_ref = self._new_ref(RefKind.RESOURCE, revision.revision_id)
        self.session.add(
            Resource(
                ref_id=resource_ref,
                kind_revision_ref=kind_revision_ref,
                created_revision_id=revision.revision_id,
            )
        )
        self._commit()
        return ResourceSnapshot(
            resource_ref=resource_ref,
            kind_revision_ref=kind_revision_ref,
            created_revision_id=revision.revision_id,
        )

    def _record_locator(
        self,
        *,
        resource_ref: UUID,
        resource_version_ref: UUID,
        ingestion_kind_revision_ref: UUID,
        locator_kind: ResourceLocatorKind,
        locator_text: str,
    ) -> None:
        revision = self._new_revision()
        occurrence_ref = self._new_ref(RefKind.OCCURRENCE, revision.revision_id)
        self.session.add(
            Occurrence(
                ref_id=occurrence_ref,
                kind_revision_ref=ingestion_kind_revision_ref,
                happened_at=revision.recorded_at,
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()
        self.session.add(
            ResourceLocator(
                locator_id=uuid4(),
                resource_ref_id=resource_ref,
                resource_version_ref=resource_version_ref,
                locator_kind=locator_kind.value,
                locator_text=locator_text,
                observed_occurrence_ref=occurrence_ref,
                created_revision_id=revision.revision_id,
            )
        )
        self._commit()

    def ingest_resource_version(
        self,
        *,
        resource_ref: UUID,
        content: bytes,
        ingestion_kind_revision_ref: UUID,
        media_type: str | None = None,
        locator_kind: ResourceLocatorKind | None = None,
        locator_text: str | None = None,
    ) -> ResourceVersionSnapshot:
        if self.session.get(Resource, resource_ref) is None:
            raise KnowledgeInvariantError(f"unknown resource: {resource_ref}")
        self._require_kind_revision(ingestion_kind_revision_ref)
        if (locator_kind is None) != (locator_text is None):
            raise KnowledgeInvariantError(
                "locator_kind and locator_text must be supplied together"
            )
        if locator_text is not None and not locator_text:
            raise KnowledgeInvariantError("locator_text must not be empty")

        artifact = self.artifact_store.commit_bytes(content)
        existing = self.session.execute(
            select(ResourceVersion).where(
                ResourceVersion.resource_ref_id == resource_ref,
                ResourceVersion.content_digest_algo == artifact.digest_algo,
                ResourceVersion.content_digest == artifact.digest,
            )
        ).scalar_one_or_none()
        if existing is not None:
            if locator_kind is not None and locator_text is not None:
                locator_exists = self.session.execute(
                    select(ResourceLocator).where(
                        ResourceLocator.resource_ref_id == resource_ref,
                        ResourceLocator.resource_version_ref == existing.ref_id,
                        ResourceLocator.locator_kind == locator_kind.value,
                        ResourceLocator.locator_text == locator_text,
                    )
                ).scalar_one_or_none()
                if locator_exists is None:
                    self._record_locator(
                        resource_ref=resource_ref,
                        resource_version_ref=existing.ref_id,
                        ingestion_kind_revision_ref=ingestion_kind_revision_ref,
                        locator_kind=locator_kind,
                        locator_text=locator_text,
                    )
            return self.read_resource_version(existing.ref_id)

        revision = self._new_revision()
        occurrence_ref = self._new_ref(RefKind.OCCURRENCE, revision.revision_id)
        version_ref = self._new_ref(RefKind.RESOURCE_VERSION, revision.revision_id)
        self.session.add(
            Occurrence(
                ref_id=occurrence_ref,
                kind_revision_ref=ingestion_kind_revision_ref,
                happened_at=revision.recorded_at,
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()
        self.session.add(
            ResourceVersion(
                ref_id=version_ref,
                resource_ref_id=resource_ref,
                content_digest_algo=artifact.digest_algo,
                content_digest=artifact.digest,
                byte_size=artifact.byte_size,
                media_type=media_type,
                artifact_backend=artifact.backend,
                artifact_key=artifact.key,
                observed_occurrence_ref=occurrence_ref,
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()
        if locator_kind is not None and locator_text is not None:
            self.session.add(
                ResourceLocator(
                    locator_id=uuid4(),
                    resource_ref_id=resource_ref,
                    resource_version_ref=version_ref,
                    locator_kind=locator_kind.value,
                    locator_text=locator_text,
                    observed_occurrence_ref=occurrence_ref,
                    created_revision_id=revision.revision_id,
                )
            )
        self._commit()
        return self.read_resource_version(version_ref)

    def read_resource_version(
        self, resource_version_ref: UUID
    ) -> ResourceVersionSnapshot:
        row = self.session.get(ResourceVersion, resource_version_ref)
        if row is None:
            raise KnowledgeInvariantError(
                f"unknown resource version: {resource_version_ref}"
            )
        return ResourceVersionSnapshot(
            resource_version_ref=row.ref_id,
            resource_ref=row.resource_ref_id,
            content_digest_algo=row.content_digest_algo,
            content_digest=row.content_digest,
            byte_size=int(row.byte_size),
            media_type=row.media_type,
            artifact_backend=row.artifact_backend,
            artifact_key=row.artifact_key,
            observed_occurrence_ref=row.observed_occurrence_ref,
            created_revision_id=row.created_revision_id,
        )

    def locator_history(
        self, *, resource_ref: UUID
    ) -> list[ResourceLocatorSnapshot]:
        rows = self.session.scalars(
            select(ResourceLocator)
            .where(ResourceLocator.resource_ref_id == resource_ref)
            .order_by(
                ResourceLocator.created_revision_id,
                ResourceLocator.locator_id,
            )
        ).all()
        return [
            ResourceLocatorSnapshot(
                locator_id=row.locator_id,
                resource_ref=row.resource_ref_id,
                resource_version_ref=row.resource_version_ref,
                locator_kind=ResourceLocatorKind(row.locator_kind),
                locator_text=row.locator_text,
                observed_occurrence_ref=row.observed_occurrence_ref,
                created_revision_id=row.created_revision_id,
            )
            for row in rows
        ]

    def link_assertion_evidence(
        self,
        *,
        assertion_ref: UUID,
        resource_version_ref: UUID,
        relation_revision_ref: UUID,
    ) -> EvidenceTrace:
        if self.session.get(Assertion, assertion_ref) is None:
            raise KnowledgeInvariantError(f"unknown assertion: {assertion_ref}")
        version = self.session.get(ResourceVersion, resource_version_ref)
        if version is None:
            raise KnowledgeInvariantError(
                f"unknown resource version: {resource_version_ref}"
            )
        relation = self.session.get(
            SemanticPredicateRevision, relation_revision_ref
        )
        relation_predicate = (
            self.session.get(SemanticPredicate, relation.predicate_ref_id)
            if relation is not None
            else None
        )
        if (
            relation is None
            or relation.value_shape != "reference"
            or relation_predicate is None
            or relation_predicate.stable_name != "supports_claim"
        ):
            raise KnowledgeInvariantError(
                "provenance relation must be the governed supports_claim relation revision"
            )

        revision = self._new_revision()
        link_id = uuid4()
        self.session.add(
            ProvenanceLink(
                link_id=link_id,
                relation_revision_ref=relation_revision_ref,
                source_ref_id=assertion_ref,
                target_ref_id=resource_version_ref,
                activity_occurrence_ref=version.observed_occurrence_ref,
                created_revision_id=revision.revision_id,
            )
        )
        self._commit()
        return EvidenceTrace(
            link_id=link_id,
            assertion_ref=assertion_ref,
            relation_revision_ref=relation_revision_ref,
            resource_version=self.read_resource_version(resource_version_ref),
            activity_occurrence_ref=version.observed_occurrence_ref,
            created_revision_id=revision.revision_id,
        )

    def explain_assertion(self, *, assertion_ref: UUID) -> list[EvidenceTrace]:
        if self.session.get(Assertion, assertion_ref) is None:
            raise KnowledgeInvariantError(f"unknown assertion: {assertion_ref}")
        rows = self.session.scalars(
            select(ProvenanceLink)
            .where(ProvenanceLink.source_ref_id == assertion_ref)
            .order_by(ProvenanceLink.created_revision_id, ProvenanceLink.link_id)
        ).all()
        traces: list[EvidenceTrace] = []
        for row in rows:
            version = self.session.get(ResourceVersion, row.target_ref_id)
            if version is None:
                raise KnowledgeInvariantError(
                    f"assertion evidence does not target an exact resource version: {row.target_ref_id}"
                )
            traces.append(
                EvidenceTrace(
                    link_id=row.link_id,
                    assertion_ref=assertion_ref,
                    relation_revision_ref=row.relation_revision_ref,
                    resource_version=self.read_resource_version(version.ref_id),
                    activity_occurrence_ref=row.activity_occurrence_ref,
                    created_revision_id=row.created_revision_id,
                )
            )
        return traces

    def impact_from_resource_version(
        self, *, resource_version_ref: UUID
    ) -> list[ImpactTrace]:
        if self.session.get(ResourceVersion, resource_version_ref) is None:
            raise KnowledgeInvariantError(
                f"unknown resource version: {resource_version_ref}"
            )
        rows = self.session.scalars(
            select(ProvenanceLink)
            .where(ProvenanceLink.target_ref_id == resource_version_ref)
            .order_by(ProvenanceLink.created_revision_id, ProvenanceLink.link_id)
        ).all()
        result: list[ImpactTrace] = []
        for row in rows:
            source_ref = self.session.get(KnowledgeRef, row.source_ref_id)
            if source_ref is None:
                raise KnowledgeInvariantError(
                    f"provenance source ref is missing: {row.source_ref_id}"
                )
            result.append(
                ImpactTrace(
                    link_id=row.link_id,
                    resource_version_ref=resource_version_ref,
                    dependent_ref=row.source_ref_id,
                    dependent_ref_kind=source_ref.ref_kind,
                    relation_revision_ref=row.relation_revision_ref,
                    created_revision_id=row.created_revision_id,
                )
            )
        return result
