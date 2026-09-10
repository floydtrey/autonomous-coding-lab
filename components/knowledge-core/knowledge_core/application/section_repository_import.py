from __future__ import annotations

from knowledge_core.application.repository_import import RepositoryImportKnowledgeKernel
from knowledge_core.application.segmentation import (
    DEFAULT_SECTION_SEGMENTATION_PROFILE,
)
from knowledge_core.domain.generations import GenerationSnapshot
from knowledge_core.domain.retrieval import TextIndexSource


class SectionRepositoryImportKnowledgeKernel(RepositoryImportKnowledgeKernel):
    """SR-2 import service variant that publishes deterministic segment retrieval."""

    def build_text_generation(
        self,
        *,
        sources: tuple[TextIndexSource, ...] | list[TextIndexSource],
    ) -> GenerationSnapshot:
        return self.build_segment_text_generation(
            sources=sources,
            profile=DEFAULT_SECTION_SEGMENTATION_PROFILE,
        )
