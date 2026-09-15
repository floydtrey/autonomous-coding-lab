from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import func, insert, literal_column, select

from knowledge_core.application.governed_snapshot_selection import (
    GovernedSnapshotProjectionSource,
    resolve_governed_snapshot_sources,
)
from knowledge_core.application.lifecycle_projection import (
    GovernedLifecycleProjection,
    RetrievalProjectionProfile,
    SegmentLifecycleProjection,
    project_governed_lifecycle,
)
from knowledge_core.application.section_generation import (
    SR2_SEGMENT_MODEL_IDENTITY,
    SR2_SEGMENT_MODEL_VERSION,
    SectionGenerationKnowledgeKernel,
    _effective_control_payload,
    _heading_path_payload,
    _local_search_text,
    _weighted_search_vector,
)
from knowledge_core.application.segmentation import (
    DEFAULT_SECTION_SEGMENTATION_PROFILE,
    SectionSegmentationProfile,
    StructuralSegmentation,
    segment_structural_content,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind, GenerationSnapshot, GenerationStatus
from knowledge_core.domain.retrieval import RetrievalLifecycleState
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.section_retrieval_models import (
    ResourceSegmentTextSearch,
    TextGenerationProfile,
    TextGenerationSource,
)


SR2_SOURCE_NEUTRAL_SELECTION_VERSION = "governed-retrieval-snapshot-v1"
SR2_SOURCE_NEUTRAL_VALIDATION_VERSION = "sr2-source-neutral-candidate-v1"
_ENGLISH_REGCONFIG = literal_column("'english'::regconfig")


@dataclass(frozen=True)
class _LifecycleObservation:
    observation_id: UUID
    resource_version_ref: UUID
    classification: str
    document_lifecycle: RetrievalLifecycleState
    authority_rank: int | None
    rationale: str


@dataclass(frozen=True)
class _PreparedSegmentV2:
    projection: SegmentLifecycleProjection
    local_search_text: str
    heading_context_text: str


@dataclass(frozen=True)
class _PreparedSourceV2:
    source: GovernedSnapshotProjectionSource
    lifecycle_observation: _LifecycleObservation
    version: ResourceVersion
    content: bytes
    structural: StructuralSegmentation
    lifecycle: GovernedLifecycleProjection
    segments: tuple[_PreparedSegmentV2, ...]


def source_neutral_segment_generation_config_digest(
    *,
    structural_profile: SectionSegmentationProfile = DEFAULT_SECTION_SEGMENTATION_PROFILE,
    projection_profile: RetrievalProjectionProfile | None = None,
) -> str:
    effective_projection = projection_profile or RetrievalProjectionProfile(
        structural_profile_digest=structural_profile.digest
    )
    if effective_projection.structural_profile_digest != structural_profile.digest:
        raise KnowledgeInvariantError(
            "SR-2 source-neutral projection profile does not bind structural profile"
        )
    payload = {
        "candidate_validation_version": SR2_SOURCE_NEUTRAL_VALIDATION_VERSION,
        "derived_kind": DerivedKind.TEXT.value,
        "generation_config_version": 2,
        "lexical_backend": "postgresql-native-tsvector-weighted-v1",
        "model_identity": SR2_SEGMENT_MODEL_IDENTITY,
        "model_version": SR2_SEGMENT_MODEL_VERSION,
        "projection_profile_digest": effective_projection.digest,
        "projection_profile_id": effective_projection.profile_id,
        "source_selection_version": SR2_SOURCE_NEUTRAL_SELECTION_VERSION,
        "storage_projection_schema": "0017_sr2_source_neutral",
        "structural_profile_digest": structural_profile.digest,
        "structural_profile_id": structural_profile.profile_id,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


class SourceNeutralSectionGenerationKnowledgeKernel(SectionGenerationKnowledgeKernel):
    """Build SR-2 candidates from complete source-neutral governed snapshots."""

    def build_segment_generation_candidate(
        self,
        *,
        governing_snapshot_digest: str,
        structural_profile: SectionSegmentationProfile = DEFAULT_SECTION_SEGMENTATION_PROFILE,
        projection_profile: RetrievalProjectionProfile | None = None,
    ) -> GenerationSnapshot:
        self._require_postgresql_sr2()
        effective_projection = projection_profile or RetrievalProjectionProfile(
            structural_profile_digest=structural_profile.digest
        )
        config_digest = source_neutral_segment_generation_config_digest(
            structural_profile=structural_profile,
            projection_profile=effective_projection,
        )
        sources = resolve_governed_snapshot_sources(
            self.session,
            governing_snapshot_digest=governing_snapshot_digest,
        )
        prepared = tuple(
            self._prepare_source_v2(
                source,
                structural_profile=structural_profile,
                projection_profile=effective_projection,
            )
            for source in sources
        )

        source_revision_highwater = self.current_revision()
        if source_revision_highwater <= 0:
            raise KnowledgeInvariantError(
                "SR-2 source-neutral generation requires canonical source revisions"
            )
        generation_kernel = self._generation_kernel()
        generation = generation_kernel.start_generation(
            derived_kind=DerivedKind.TEXT,
            source_revision_highwater=source_revision_highwater,
            sources=tuple(
                (item.version.ref_id, int(item.version.created_revision_id))
                for item in prepared
            ),
            model_identity=SR2_SEGMENT_MODEL_IDENTITY,
            model_version=SR2_SEGMENT_MODEL_VERSION,
            config_digest=config_digest,
        )

        try:
            self.session.add(
                TextGenerationProfile(
                    generation_id=generation.generation_id,
                    structural_profile_id=structural_profile.profile_id,
                    structural_profile_digest=structural_profile.digest,
                    projection_profile_id=effective_projection.profile_id,
                    projection_profile_digest=effective_projection.digest,
                    generation_config_digest=config_digest,
                )
            )
            for item in prepared:
                compat = item.source.repository_compatibility
                self.session.add(
                    TextGenerationSource(
                        generation_id=generation.generation_id,
                        resource_version_ref=item.version.ref_id,
                        governed_observation_id=item.source.observation.observation_id,
                        governed_decision_id=item.source.decision.decision_id,
                        governing_snapshot_digest=governing_snapshot_digest,
                        governed_projection_digest=item.source.projection_digest,
                        source_observation_id=(
                            compat.legacy_observation_id if compat is not None else None
                        ),
                        governing_manifest_digest=(
                            compat.governing_manifest_digest
                            if compat is not None
                            else None
                        ),
                        projection_snapshot_digest=(
                            compat.projection_snapshot_digest
                            if compat is not None
                            else None
                        ),
                    )
                )
            self.session.flush()

            for item in prepared:
                compat = item.source.repository_compatibility
                for prepared_segment in item.segments:
                    segment = prepared_segment.projection
                    structural = segment.structural_segment
                    declaration = segment.declaration
                    observation = segment.governed_observation
                    self.session.execute(
                        insert(ResourceSegmentTextSearch).values(
                            generation_id=generation.generation_id,
                            resource_version_ref=item.version.ref_id,
                            segment_ordinal=structural.segment_ordinal,
                            segment_key=structural.segment_key,
                            structural_kind=structural.structural_kind,
                            base_block_ordinal=structural.base_block_ordinal,
                            part_index=structural.part_index,
                            part_count=structural.part_count,
                            source_byte_start=structural.source_byte_start,
                            source_byte_end=structural.source_byte_end,
                            source_line_start=structural.source_line_start,
                            source_line_end=structural.source_line_end,
                            source_slice_sha256=structural.source_slice_sha256,
                            heading_path=_heading_path_payload(structural.heading_path),
                            parent_lifecycle_state=observation.document_lifecycle.value,
                            declared_lifecycle_state=(
                                segment.declared_lifecycle.value
                                if segment.declared_lifecycle is not None
                                else None
                            ),
                            declaration_source_line=(
                                declaration.source_line
                                if declaration is not None
                                else None
                            ),
                            declaration_byte_start=(
                                declaration.source_byte_start
                                if declaration is not None
                                else None
                            ),
                            declaration_byte_end=(
                                declaration.source_byte_end
                                if declaration is not None
                                else None
                            ),
                            effective_lifecycle_state=segment.effective_lifecycle.value,
                            effective_control_provenance=_effective_control_payload(
                                segment
                            ),
                            authority_rank=observation.authority_rank,
                            repository=(
                                compat.repository_locator if compat is not None else None
                            ),
                            source_repository_key=(
                                compat.source_repository_key if compat is not None else None
                            ),
                            source_document_key=(
                                compat.source_document_key if compat is not None else None
                            ),
                            source_path=(
                                compat.source_path if compat is not None else None
                            ),
                            source_version=(
                                compat.source_version if compat is not None else None
                            ),
                            search_vector=_weighted_search_vector(
                                prepared_segment.local_search_text,
                                prepared_segment.heading_context_text,
                            ),
                        )
                    )
            self._commit()
            self.validate_segment_generation_candidate(
                generation_id=generation.generation_id,
                governing_snapshot_digest=governing_snapshot_digest,
                structural_profile=structural_profile,
                projection_profile=effective_projection,
            )
            return generation_kernel.read_generation(generation.generation_id)
        except Exception:
            self.session.rollback()
            self._stale_building_generation(generation.generation_id)
            raise

    def validate_segment_generation_candidate(
        self,
        *,
        generation_id: UUID,
        governing_snapshot_digest: str,
        structural_profile: SectionSegmentationProfile = DEFAULT_SECTION_SEGMENTATION_PROFILE,
        projection_profile: RetrievalProjectionProfile | None = None,
    ) -> GenerationSnapshot:
        self._require_postgresql_sr2()
        try:
            return self._validate_source_neutral_candidate(
                generation_id=generation_id,
                governing_snapshot_digest=governing_snapshot_digest,
                structural_profile=structural_profile,
                projection_profile=projection_profile,
            )
        except Exception:
            self.session.rollback()
            self._stale_building_generation(generation_id)
            raise

    def _validate_source_neutral_candidate(
        self,
        *,
        generation_id: UUID,
        governing_snapshot_digest: str,
        structural_profile: SectionSegmentationProfile,
        projection_profile: RetrievalProjectionProfile | None,
    ) -> GenerationSnapshot:
        generation_kernel = self._generation_kernel()
        generation = generation_kernel.read_generation(generation_id)
        if generation.derived_kind is not DerivedKind.TEXT:
            raise KnowledgeInvariantError(
                "SR-2 source-neutral candidate must be a text generation"
            )
        if generation.status is not GenerationStatus.BUILDING:
            raise KnowledgeInvariantError(
                "SR-2 source-neutral candidate validation requires building status"
            )

        effective_projection = projection_profile or RetrievalProjectionProfile(
            structural_profile_digest=structural_profile.digest
        )
        expected_config = source_neutral_segment_generation_config_digest(
            structural_profile=structural_profile,
            projection_profile=effective_projection,
        )
        if (
            generation.model_identity != SR2_SEGMENT_MODEL_IDENTITY
            or generation.model_version != SR2_SEGMENT_MODEL_VERSION
            or generation.config_digest != expected_config
        ):
            raise KnowledgeInvariantError(
                "SR-2 source-neutral generation profile/config identity mismatch"
            )
        profile_row = self.session.get(TextGenerationProfile, generation_id)
        if profile_row is None:
            raise KnowledgeInvariantError(
                "SR-2 source-neutral candidate is missing generation profile identity"
            )
        for field, value in {
            "structural_profile_id": structural_profile.profile_id,
            "structural_profile_digest": structural_profile.digest,
            "projection_profile_id": effective_projection.profile_id,
            "projection_profile_digest": effective_projection.digest,
            "generation_config_digest": expected_config,
        }.items():
            if getattr(profile_row, field) != value:
                raise KnowledgeInvariantError(
                    f"SR-2 source-neutral generation profile mismatch: {field}"
                )

        sources = resolve_governed_snapshot_sources(
            self.session,
            governing_snapshot_digest=governing_snapshot_digest,
        )
        prepared = tuple(
            self._prepare_source_v2(
                source,
                structural_profile=structural_profile,
                projection_profile=effective_projection,
            )
            for source in sources
        )
        expected_generation_sources = {
            (item.version.ref_id, int(item.version.created_revision_id))
            for item in prepared
        }
        actual_generation_sources = {
            (item.source_ref, item.source_revision_id) for item in generation.sources
        }
        if actual_generation_sources != expected_generation_sources:
            raise KnowledgeInvariantError(
                "SR-2 source-neutral canonical generation-source lineage mismatch"
            )
        if generation.source_revision_highwater < max(
            (revision for _ref, revision in expected_generation_sources),
            default=0,
        ):
            raise KnowledgeInvariantError(
                "SR-2 source-neutral generation highwater is incomplete"
            )

        lineage_rows = self.session.scalars(
            select(TextGenerationSource).where(
                TextGenerationSource.generation_id == generation_id
            )
        ).all()
        lineage_by_version = {
            item.resource_version_ref: item for item in lineage_rows
        }
        if len(lineage_by_version) != len(prepared):
            raise KnowledgeInvariantError(
                "SR-2 source-neutral governed lineage coverage mismatch"
            )

        expected_segments: dict[tuple[UUID, int], tuple[_PreparedSourceV2, _PreparedSegmentV2]] = {}
        for item in prepared:
            lineage = lineage_by_version.get(item.version.ref_id)
            if lineage is None:
                raise KnowledgeInvariantError(
                    "SR-2 source-neutral candidate is missing governed lineage"
                )
            compat = item.source.repository_compatibility
            expected_lineage = {
                "governed_observation_id": item.source.observation.observation_id,
                "governed_decision_id": item.source.decision.decision_id,
                "governing_snapshot_digest": governing_snapshot_digest,
                "governed_projection_digest": item.source.projection_digest,
                "source_observation_id": (
                    compat.legacy_observation_id if compat is not None else None
                ),
                "governing_manifest_digest": (
                    compat.governing_manifest_digest if compat is not None else None
                ),
                "projection_snapshot_digest": (
                    compat.projection_snapshot_digest if compat is not None else None
                ),
            }
            for field, value in expected_lineage.items():
                if getattr(lineage, field) != value:
                    raise KnowledgeInvariantError(
                        f"SR-2 source-neutral lineage mismatch: {field}"
                    )
            for segment in item.segments:
                key = (
                    item.version.ref_id,
                    segment.projection.structural_segment.segment_ordinal,
                )
                expected_segments[key] = (item, segment)

        rows = self.session.scalars(
            select(ResourceSegmentTextSearch).where(
                ResourceSegmentTextSearch.generation_id == generation_id
            )
        ).all()
        if len(rows) != len(expected_segments):
            raise KnowledgeInvariantError(
                "SR-2 source-neutral candidate segment coverage count mismatch"
            )
        seen: set[tuple[UUID, int]] = set()
        for row in rows:
            key = (row.resource_version_ref, int(row.segment_ordinal))
            expected = expected_segments.get(key)
            if expected is None or key in seen:
                raise KnowledgeInvariantError(
                    "SR-2 source-neutral candidate has unexpected/duplicate segment"
                )
            seen.add(key)
            item, prepared_segment = expected
            self._validate_segment_row_v2(row, item, prepared_segment)
            vector_matches = self.session.scalar(
                select(
                    ResourceSegmentTextSearch.search_vector
                    == _weighted_search_vector(
                        prepared_segment.local_search_text,
                        prepared_segment.heading_context_text,
                    )
                ).where(
                    ResourceSegmentTextSearch.generation_id == generation_id,
                    ResourceSegmentTextSearch.resource_version_ref
                    == row.resource_version_ref,
                    ResourceSegmentTextSearch.segment_ordinal == row.segment_ordinal,
                )
            )
            if vector_matches is not True:
                raise KnowledgeInvariantError(
                    "SR-2 source-neutral lexical projection mismatch"
                )
        if seen != set(expected_segments):
            raise KnowledgeInvariantError(
                "SR-2 source-neutral candidate segment coverage is incomplete"
            )
        return generation_kernel.read_generation(generation_id)

    def _prepare_source_v2(
        self,
        source: GovernedSnapshotProjectionSource,
        *,
        structural_profile: SectionSegmentationProfile,
        projection_profile: RetrievalProjectionProfile,
    ) -> _PreparedSourceV2:
        version_ref = source.observation.resource_version_ref
        version = self.session.get(ResourceVersion, version_ref)
        if version is None:
            raise KnowledgeInvariantError(
                f"SR-2 governed source references unknown ResourceVersion: {version_ref}"
            )
        if version.resource_ref_id != source.observation.binding.resource_ref:
            raise KnowledgeInvariantError(
                "SR-2 governed source Resource binding does not own its ResourceVersion"
            )
        if not self.resource_version_serving_eligible(version_ref):
            raise KnowledgeInvariantError(
                f"SR-2 governed source is not serving-eligible: {version_ref}"
            )
        if version.media_type not in {"text/plain", "text/markdown"}:
            raise KnowledgeInvariantError(
                f"SR-2 governed source media type is unsupported: {version.media_type}"
            )
        if version.content_digest_algo != "sha256":
            raise KnowledgeInvariantError(
                "SR-2 exact parent requires SHA-256 canonical digest"
            )
        content = self.artifact_store.read_bytes(version.artifact_key)
        if len(content) != int(version.byte_size):
            raise KnowledgeInvariantError(
                "SR-2 exact parent artifact byte size does not match ResourceVersion"
            )
        if sha256(content).hexdigest() != version.content_digest:
            raise KnowledgeInvariantError(
                "SR-2 exact parent artifact digest does not match ResourceVersion"
            )

        lifecycle_observation = _LifecycleObservation(
            observation_id=source.observation.observation_id,
            resource_version_ref=version_ref,
            classification=source.decision.classification,
            document_lifecycle=source.decision.retrieval_lifecycle,
            authority_rank=source.decision.authority_rank,
            rationale=source.decision.rationale,
        )
        structural = segment_structural_content(
            resource_version_ref=version_ref,
            media_type=version.media_type,
            content=content,
            profile=structural_profile,
        )
        lifecycle = project_governed_lifecycle(
            structural=structural,
            content=content,
            observation=lifecycle_observation,
            profile=projection_profile,
        )
        if lifecycle.projection_profile_digest != projection_profile.digest:
            raise KnowledgeInvariantError(
                "SR-2 source-neutral lifecycle projection profile mismatch"
            )
        segments = tuple(
            _PreparedSegmentV2(
                projection=segment,
                local_search_text=_local_search_text(segment, content),
                heading_context_text="\n".join(
                    heading.display_text
                    for heading in segment.structural_segment.heading_path
                ),
            )
            for segment in lifecycle.segments
        )
        return _PreparedSourceV2(
            source=source,
            lifecycle_observation=lifecycle_observation,
            version=version,
            content=content,
            structural=structural,
            lifecycle=lifecycle,
            segments=segments,
        )

    def _validate_segment_row_v2(
        self,
        row: ResourceSegmentTextSearch,
        item: _PreparedSourceV2,
        expected: _PreparedSegmentV2,
    ) -> None:
        projection = expected.projection
        structural = projection.structural_segment
        declaration = projection.declaration
        observation = projection.governed_observation
        compat = item.source.repository_compatibility
        expected_values = {
            "segment_key": structural.segment_key,
            "structural_kind": structural.structural_kind,
            "base_block_ordinal": structural.base_block_ordinal,
            "part_index": structural.part_index,
            "part_count": structural.part_count,
            "source_byte_start": structural.source_byte_start,
            "source_byte_end": structural.source_byte_end,
            "source_line_start": structural.source_line_start,
            "source_line_end": structural.source_line_end,
            "source_slice_sha256": structural.source_slice_sha256,
            "heading_path": _heading_path_payload(structural.heading_path),
            "parent_lifecycle_state": observation.document_lifecycle.value,
            "declared_lifecycle_state": (
                projection.declared_lifecycle.value
                if projection.declared_lifecycle is not None
                else None
            ),
            "declaration_source_line": (
                declaration.source_line if declaration is not None else None
            ),
            "declaration_byte_start": (
                declaration.source_byte_start if declaration is not None else None
            ),
            "declaration_byte_end": (
                declaration.source_byte_end if declaration is not None else None
            ),
            "effective_lifecycle_state": projection.effective_lifecycle.value,
            "effective_control_provenance": _effective_control_payload(projection),
            "authority_rank": observation.authority_rank,
            "repository": compat.repository_locator if compat is not None else None,
            "source_repository_key": (
                compat.source_repository_key if compat is not None else None
            ),
            "source_document_key": (
                compat.source_document_key if compat is not None else None
            ),
            "source_path": compat.source_path if compat is not None else None,
            "source_version": compat.source_version if compat is not None else None,
        }
        for field, value in expected_values.items():
            if getattr(row, field) != value:
                raise KnowledgeInvariantError(
                    f"SR-2 source-neutral candidate segment mismatch: {field}"
                )
