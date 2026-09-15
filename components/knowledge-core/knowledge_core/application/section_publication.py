from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from knowledge_core.application.governed_source_evidence import (
    GovernedSourceEvidenceKnowledgeKernel,
)
from knowledge_core.application.lifecycle_projection import RetrievalProjectionProfile
from knowledge_core.application.section_generation import SectionGenerationKnowledgeKernel
from knowledge_core.application.segmentation import (
    DEFAULT_SECTION_SEGMENTATION_PROFILE,
    SectionSegmentationProfile,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind, GenerationSnapshot, GenerationStatus
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.repository_import_models import RepositoryImportReceipt
from knowledge_core.storage.section_retrieval_models import TextGenerationSource


class SectionPublicationKnowledgeKernel(SectionGenerationKnowledgeKernel):
    """Atomically publish a revalidated SR-2 candidate under the text fence."""

    def stale_unpublished_candidates_for_manifest(
        self,
        *,
        governing_manifest_digest: str,
    ) -> int:
        """Fence retry residue that is identifiable as an older SR-2 candidate."""

        generation_ids = tuple(
            self.session.scalars(
                select(TextGenerationSource.generation_id)
                .join(
                    DerivedGeneration,
                    DerivedGeneration.generation_id == TextGenerationSource.generation_id,
                )
                .where(
                    TextGenerationSource.governing_manifest_digest
                    == governing_manifest_digest,
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
        governing_manifest_digest: str,
        structural_profile: SectionSegmentationProfile = DEFAULT_SECTION_SEGMENTATION_PROFILE,
        projection_profile: RetrievalProjectionProfile | None = None,
    ) -> GenerationSnapshot:
        """Revalidate and atomically make one SR-2 text generation current.

        If the governing RI-2 receipt is still ``applying``, its settlement,
        source-neutral governed-evidence mapping, and
        ``resulting_text_generation_id`` are committed in the same transaction as
        generation promotion. A previously settled receipt can govern an explicit
        RF-2 -> SR-2 cutover without rewriting that historical receipt.
        """

        self._require_postgresql_sr2()
        generation_kernel = self._generation_kernel()
        receipt = self.session.get(RepositoryImportReceipt, governing_manifest_digest)
        if receipt is None:
            raise KnowledgeInvariantError("unknown governing repository manifest")
        if receipt.status not in {"applying", "settled"}:
            raise KnowledgeInvariantError(
                "governing repository receipt is not publishable"
            )

        evidence_kernel = GovernedSourceEvidenceKnowledgeKernel(self.session)
        # Map any historical predecessor before publication mutates generation
        # state. That keeps the legacy-reconstruction bridge from committing a
        # partially promoted current generation while recursively mapping history.
        if receipt.previous_manifest_digest is not None:
            evidence_kernel.map_settled_repository_receipt(
                receipt.previous_manifest_digest
            )
            self.session.refresh(receipt)

        receipt_was_applying = receipt.status == "applying"

        generation = generation_kernel.read_generation(generation_id)
        if generation.derived_kind is not DerivedKind.TEXT:
            raise KnowledgeInvariantError("SR-2 publication requires a text generation")
        if generation.status is GenerationStatus.CURRENT:
            if receipt.status != "settled":
                raise KnowledgeInvariantError(
                    "current SR-2 generation cannot be governed by an unsettled receipt"
                )
            evidence_kernel.map_settled_repository_receipt(
                governing_manifest_digest
            )
            return generation
        if generation.status is not GenerationStatus.BUILDING:
            raise KnowledgeInvariantError(
                "SR-2 publication requires a building candidate"
            )

        try:
            # Hold the same publication fence used by the generic generation layer
            # before the final rebuild check, so no competing generation can cross
            # the one-current boundary between validation and settlement.
            generation_kernel.acquire_generation_publication_lock()
            self.session.refresh(receipt)
            if receipt.status not in {"applying", "settled"}:
                raise KnowledgeInvariantError(
                    "governing repository receipt changed before publication"
                )
            if (
                receipt_was_applying
                and receipt.status == "settled"
                and receipt.resulting_text_generation_id != generation_id
            ):
                raise KnowledgeInvariantError(
                    "governing repository receipt was settled by another publication"
                )

            self._validate_segment_generation_candidate(
                generation_id=generation_id,
                governing_manifest_digest=governing_manifest_digest,
                structural_profile=structural_profile,
                projection_profile=projection_profile,
            )
            generation_kernel.settle_generation(
                generation_id=generation_id,
                commit_transaction=False,
                publication_lock_held=True,
            )

            if receipt.status == "applying":
                receipt.status = "settled"
                receipt.resulting_text_generation_id = generation_id
                receipt.settled_at = self._now()
            # A settled historical receipt is immutable. It may point to the RF-2
            # generation that originally settled it; the SR-2 cutover is represented
            # by its own derived-generation lineage, not by rewriting that receipt.

            # The 2B mapper deliberately reconstructs the generic evidence from the
            # exact repository receipt/observation chain. At this point the current
            # receipt is settled in the same SQLAlchemy transaction, so its final
            # commit also commits the generation cutover. If mapping fails, the
            # surrounding rollback restores the previous current TEXT generation.
            evidence_kernel.map_settled_repository_receipt(
                governing_manifest_digest
            )

            self.session.flush()
            self._commit()
            return generation_kernel.read_generation(generation_id)
        except Exception:
            self.session.rollback()
            self._stale_building_generation(generation_id)
            raise
