from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from knowledge_core.application.governed_source_evidence import (
    GovernedSourceEvidenceKnowledgeKernel,
)
from knowledge_core.application.lifecycle_projection import RetrievalProjectionProfile
from knowledge_core.application.section_generation import (
    SR2_SEGMENT_MODEL_IDENTITY,
    SR2_SEGMENT_MODEL_VERSION,
)
from knowledge_core.application.section_generation_v2 import (
    SourceNeutralSectionGenerationKnowledgeKernel,
)
from knowledge_core.application.segmentation import (
    DEFAULT_SECTION_SEGMENTATION_PROFILE,
    SectionSegmentationProfile,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind, GenerationSnapshot, GenerationStatus
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.governed_source_models import LegacyRepositorySnapshotMap
from knowledge_core.storage.section_retrieval_models import TextGenerationSource


class SourceNeutralSectionPublicationKnowledgeKernel(
    SourceNeutralSectionGenerationKnowledgeKernel
):
    """Atomically publish one complete governed snapshot under the TEXT fence."""

    def current_serving_snapshot_digest(self) -> str | None:
        current = self._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        if current is None:
            return None
        if (
            current.model_identity != SR2_SEGMENT_MODEL_IDENTITY
            or current.model_version != SR2_SEGMENT_MODEL_VERSION
        ):
            # RF-2 predates generic serving-snapshot identity. A first V2 cutover
            # therefore has no source-neutral serving predecessor.
            return None

        generic = tuple(
            self.session.scalars(
                select(TextGenerationSource.governing_snapshot_digest)
                .where(
                    TextGenerationSource.generation_id == current.generation_id,
                    TextGenerationSource.governing_snapshot_digest.is_not(None),
                )
                .distinct()
            ).all()
        )
        if len(generic) > 1:
            raise KnowledgeInvariantError(
                "current SR-2 generation references multiple governed snapshots"
            )
        if len(generic) == 1:
            return generic[0]

        # Compatibility bridge for an accepted pre-2D SR-2 generation.
        manifests = tuple(
            self.session.scalars(
                select(TextGenerationSource.governing_manifest_digest)
                .where(
                    TextGenerationSource.generation_id == current.generation_id,
                    TextGenerationSource.governing_manifest_digest.is_not(None),
                )
                .distinct()
            ).all()
        )
        if len(manifests) != 1:
            raise KnowledgeInvariantError(
                "pre-2D current SR-2 generation has ambiguous repository lineage"
            )
        mapping = self.session.get(LegacyRepositorySnapshotMap, manifests[0])
        if mapping is None:
            raise KnowledgeInvariantError(
                "pre-2D current SR-2 generation has no governed snapshot mapping"
            )
        return mapping.snapshot_digest

    def stale_unpublished_candidates_for_snapshot(
        self,
        *,
        governing_snapshot_digest: str,
    ) -> int:
        generation_ids = tuple(
            self.session.scalars(
                select(TextGenerationSource.generation_id)
                .join(
                    DerivedGeneration,
                    DerivedGeneration.generation_id == TextGenerationSource.generation_id,
                )
                .where(
                    TextGenerationSource.governing_snapshot_digest
                    == governing_snapshot_digest,
                    DerivedGeneration.derived_kind == DerivedKind.TEXT.value,
                    DerivedGeneration.status == GenerationStatus.BUILDING.value,
                )
                .distinct()
            ).all()
        )
        for generation_id in generation_ids:
            self._generation_kernel().mark_generation_stale(
                generation_id=generation_id
            )
        return len(generation_ids)

    def promote_segment_generation(
        self,
        *,
        generation_id: UUID,
        governing_snapshot_digest: str,
        expected_predecessor_snapshot_digest: str | None,
        structural_profile: SectionSegmentationProfile = DEFAULT_SECTION_SEGMENTATION_PROFILE,
        projection_profile: RetrievalProjectionProfile | None = None,
        commit_transaction: bool = True,
    ) -> GenerationSnapshot:
        """Publish only if the complete snapshot still extends current serving state."""

        self._require_postgresql_sr2()
        evidence = GovernedSourceEvidenceKnowledgeKernel(self.session)
        snapshot = evidence.load_snapshot(governing_snapshot_digest)
        if (
            snapshot.predecessor_snapshot_digest
            != expected_predecessor_snapshot_digest
        ):
            raise KnowledgeInvariantError(
                "governed snapshot predecessor does not match publication expectation"
            )

        generation_kernel = self._generation_kernel()
        generation = generation_kernel.read_generation(generation_id)
        if generation.derived_kind is not DerivedKind.TEXT:
            raise KnowledgeInvariantError(
                "source-neutral SR-2 publication requires a text generation"
            )
        if generation.status is GenerationStatus.CURRENT:
            if self.current_serving_snapshot_digest() != governing_snapshot_digest:
                raise KnowledgeInvariantError(
                    "current generation does not serve the requested governed snapshot"
                )
            return generation
        if generation.status is not GenerationStatus.BUILDING:
            raise KnowledgeInvariantError(
                "source-neutral SR-2 publication requires a building candidate"
            )

        try:
            generation_kernel.acquire_generation_publication_lock()
            actual_predecessor = self.current_serving_snapshot_digest()
            if actual_predecessor != expected_predecessor_snapshot_digest:
                raise KnowledgeInvariantError(
                    "serving governed snapshot changed before publication"
                )

            self._validate_source_neutral_candidate(
                generation_id=generation_id,
                governing_snapshot_digest=governing_snapshot_digest,
                structural_profile=structural_profile,
                projection_profile=projection_profile,
            )
            generation_kernel.settle_generation(
                generation_id=generation_id,
                commit_transaction=False,
                publication_lock_held=True,
            )
            if commit_transaction:
                self._commit()
            else:
                self.session.flush()
            return generation_kernel.read_generation(generation_id)
        except Exception:
            self.session.rollback()
            self._stale_building_generation(generation_id)
            raise
