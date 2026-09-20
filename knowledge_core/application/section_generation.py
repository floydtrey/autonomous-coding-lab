from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
from uuid import UUID

from sqlalchemy import func, insert, literal_column, select

from knowledge_core.application.governed_source_selection import (
    GovernedProjectionSource,
    resolve_governed_projection_sources,
)
from knowledge_core.application.lifecycle_projection import (
    GovernedLifecycleProjection,
    RetrievalProjectionProfile,
    SegmentLifecycleProjection,
    project_governed_lifecycle,
)
from knowledge_core.application.resource_service import ResourceServiceKnowledgeKernel
from knowledge_core.application.segmentation import (
    DEFAULT_SECTION_SEGMENTATION_PROFILE,
    SectionSegmentationProfile,
    StructuralSegmentation,
    segment_structural_content,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import (
    DerivedKind,
    GenerationSnapshot,
    GenerationStatus,
)
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.section_retrieval_models import (
    ResourceSegmentTextSearch,
    TextGenerationProfile,
    TextGenerationSource,
)


SR2_SEGMENT_MODEL_IDENTITY = "deterministic-python-postgresql-full-text"
SR2_SEGMENT_MODEL_VERSION = "sr2-segment-generation-v1"
SR2_SOURCE_SELECTION_VERSION = "ri2-manifest-chain-v1"
SR2_CANDIDATE_VALIDATION_VERSION = "sr2-segment-candidate-v1"

_ENGLISH_REGCONFIG = literal_column("'english'::regconfig")
_WEIGHT_A = literal_column("'A'")
_WEIGHT_B = literal_column("'B'")


@dataclass(frozen=True)
class _PreparedSegment:
    projection: SegmentLifecycleProjection
    local_search_text: str
    heading_context_text: str


@dataclass(frozen=True)
class _PreparedSource:
    source: GovernedProjectionSource
    version: ResourceVersion
    content: bytes
    structural: StructuralSegmentation
    lifecycle: GovernedLifecycleProjection
    segments: tuple[_PreparedSegment, ...]


def segment_generation_config_digest(
    *,
    structural_profile: SectionSegmentationProfile = DEFAULT_SECTION_SEGMENTATION_PROFILE,
    projection_profile: RetrievalProjectionProfile | None = None,
) -> str:
    """Bind all behavior-bearing SR-2 generation/profile choices."""

    effective_projection = projection_profile or RetrievalProjectionProfile(
        structural_profile_digest=structural_profile.digest
    )
    if effective_projection.structural_profile_digest != structural_profile.digest:
        raise KnowledgeInvariantError(
            "SR-2 generation projection profile does not bind structural profile"
        )
    payload = {
        "candidate_validation_version": SR2_CANDIDATE_VALIDATION_VERSION,
        "derived_kind": DerivedKind.TEXT.value,
        "generation_config_version": 1,
        "lexical_backend": "postgresql-native-tsvector-weighted-v1",
        "model_identity": SR2_SEGMENT_MODEL_IDENTITY,
        "model_version": SR2_SEGMENT_MODEL_VERSION,
        "projection_profile_digest": effective_projection.digest,
        "projection_profile_id": effective_projection.profile_id,
        "source_selection_version": SR2_SOURCE_SELECTION_VERSION,
        "storage_projection_schema": "0012_sr2_segments",
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


class SectionGenerationKnowledgeKernel(ResourceServiceKnowledgeKernel):
    """Build and validate non-serving SR-2 segment-generation candidates."""

    def _require_postgresql_sr2(self) -> None:
        if self.session.get_bind().dialect.name != "postgresql":
            raise KnowledgeInvariantError(
                "SR-2 segment generation requires PostgreSQL"
            )

    def build_segment_generation_candidate(
        self,
        *,
        governing_manifest_digest: str,
        structural_profile: SectionSegmentationProfile = DEFAULT_SECTION_SEGMENTATION_PROFILE,
        projection_profile: RetrievalProjectionProfile | None = None,
    ) -> GenerationSnapshot:
        """Build a complete candidate but deliberately do not settle it current."""

        self._require_postgresql_sr2()
        effective_projection = projection_profile or RetrievalProjectionProfile(
            structural_profile_digest=structural_profile.digest
        )
        config_digest = segment_generation_config_digest(
            structural_profile=structural_profile,
            projection_profile=effective_projection,
        )

        sources = resolve_governed_projection_sources(
            self.session,
            governing_manifest_digest=governing_manifest_digest,
        )
        prepared = tuple(
            self._prepare_source(
                source,
                structural_profile=structural_profile,
                projection_profile=effective_projection,
            )
            for source in sources
        )

        source_revision_highwater = self.current_revision()
        if source_revision_highwater <= 0:
            raise KnowledgeInvariantError(
                "SR-2 generation requires canonical source revisions"
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
                self.session.add(
                    TextGenerationSource(
                        generation_id=generation.generation_id,
                        resource_version_ref=item.version.ref_id,
                        source_observation_id=item.source.observation.observation_id,
                        governing_manifest_digest=item.source.governing_manifest_digest,
                        projection_snapshot_digest=item.source.projection_snapshot_digest,
                    )
                )
            self.session.flush()

            for item in prepared:
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
                            repository=observation.repository_locator,
                            source_repository_key=observation.source_repository_key,
                            source_document_key=observation.source_document_key,
                            source_path=observation.source_path,
                            source_version=observation.source_commit,
                            search_vector=_weighted_search_vector(
                                prepared_segment.local_search_text,
                                prepared_segment.heading_context_text,
                            ),
                        )
                    )
            self._commit()

            self.validate_segment_generation_candidate(
                generation_id=generation.generation_id,
                governing_manifest_digest=governing_manifest_digest,
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
        governing_manifest_digest: str,
        structural_profile: SectionSegmentationProfile = DEFAULT_SECTION_SEGMENTATION_PROFILE,
        projection_profile: RetrievalProjectionProfile | None = None,
    ) -> GenerationSnapshot:
        """Recompute and verify a candidate; stale it if any invariant fails."""

        self._require_postgresql_sr2()
        try:
            return self._validate_segment_generation_candidate(
                generation_id=generation_id,
                governing_manifest_digest=governing_manifest_digest,
                structural_profile=structural_profile,
                projection_profile=projection_profile,
            )
        except Exception:
            self.session.rollback()
            self._stale_building_generation(generation_id)
            raise

    def _validate_segment_generation_candidate(
        self,
        *,
        generation_id: UUID,
        governing_manifest_digest: str,
        structural_profile: SectionSegmentationProfile,
        projection_profile: RetrievalProjectionProfile | None,
    ) -> GenerationSnapshot:
        generation_kernel = self._generation_kernel()
        generation = generation_kernel.read_generation(generation_id)
        if generation.derived_kind is not DerivedKind.TEXT:
            raise KnowledgeInvariantError(
                "SR-2 candidate must be a text derived generation"
            )
        if generation.status is not GenerationStatus.BUILDING:
            raise KnowledgeInvariantError(
                "SR-2 candidate validation requires building status"
            )

        effective_projection = projection_profile or RetrievalProjectionProfile(
            structural_profile_digest=structural_profile.digest
        )
        expected_config = segment_generation_config_digest(
            structural_profile=structural_profile,
            projection_profile=effective_projection,
        )
        if (
            generation.model_identity != SR2_SEGMENT_MODEL_IDENTITY
            or generation.model_version != SR2_SEGMENT_MODEL_VERSION
            or generation.config_digest != expected_config
        ):
            raise KnowledgeInvariantError(
                "SR-2 candidate generation profile/config identity mismatch"
            )

        profile_row = self.session.get(TextGenerationProfile, generation_id)
        if profile_row is None:
            raise KnowledgeInvariantError(
                "SR-2 candidate is missing recoverable generation profile identity"
            )
        expected_profile_values = {
            "structural_profile_id": structural_profile.profile_id,
            "structural_profile_digest": structural_profile.digest,
            "projection_profile_id": effective_projection.profile_id,
            "projection_profile_digest": effective_projection.digest,
            "generation_config_digest": expected_config,
        }
        for field, value in expected_profile_values.items():
            if getattr(profile_row, field) != value:
                raise KnowledgeInvariantError(
                    f"SR-2 candidate generation profile field mismatch: {field}"
                )

        sources = resolve_governed_projection_sources(
            self.session,
            governing_manifest_digest=governing_manifest_digest,
        )
        prepared = tuple(
            self._prepare_source(
                source,
                structural_profile=structural_profile,
                projection_profile=effective_projection,
            )
            for source in sources
        )

        expected_generic_sources = {
            (item.version.ref_id, int(item.version.created_revision_id))
            for item in prepared
        }
        actual_generic_sources = {
            (source.source_ref, source.source_revision_id)
            for source in generation.sources
        }
        if actual_generic_sources != expected_generic_sources:
            raise KnowledgeInvariantError(
                "SR-2 candidate canonical generation-source lineage mismatch"
            )
        if generation.source_revision_highwater < max(
            (revision for _ref, revision in expected_generic_sources),
            default=0,
        ):
            raise KnowledgeInvariantError(
                "SR-2 candidate source revision highwater is incomplete"
            )

        lineage_rows = self.session.scalars(
            select(TextGenerationSource).where(
                TextGenerationSource.generation_id == generation_id
            )
        ).all()
        lineage_by_version = {
            row.resource_version_ref: row for row in lineage_rows
        }
        if len(lineage_by_version) != len(prepared):
            raise KnowledgeInvariantError(
                "SR-2 candidate governed source-lineage coverage mismatch"
            )

        expected_segments: dict[tuple[UUID, int], _PreparedSegment] = {}
        for item in prepared:
            lineage = lineage_by_version.get(item.version.ref_id)
            if lineage is None:
                raise KnowledgeInvariantError(
                    "SR-2 candidate is missing governed source lineage"
                )
            if (
                lineage.source_observation_id
                != item.source.observation.observation_id
                or lineage.governing_manifest_digest
                != item.source.governing_manifest_digest
                or lineage.projection_snapshot_digest
                != item.source.projection_snapshot_digest
            ):
                raise KnowledgeInvariantError(
                    "SR-2 candidate governed source lineage does not match exact inputs"
                )
            for segment in item.segments:
                key = (
                    item.version.ref_id,
                    segment.projection.structural_segment.segment_ordinal,
                )
                expected_segments[key] = segment

        segment_rows = self.session.scalars(
            select(ResourceSegmentTextSearch).where(
                ResourceSegmentTextSearch.generation_id == generation_id
            )
        ).all()
        if len(segment_rows) != len(expected_segments):
            raise KnowledgeInvariantError(
                "SR-2 candidate segment coverage count mismatch"
            )

        seen: set[tuple[UUID, int]] = set()
        for row in segment_rows:
            key = (row.resource_version_ref, int(row.segment_ordinal))
            expected = expected_segments.get(key)
            if expected is None or key in seen:
                raise KnowledgeInvariantError(
                    "SR-2 candidate contains unexpected/duplicate segment identity"
                )
            seen.add(key)
            self._validate_segment_row(row, expected)
            vector_matches = self.session.scalar(
                select(
                    ResourceSegmentTextSearch.search_vector
                    == _weighted_search_vector(
                        expected.local_search_text,
                        expected.heading_context_text,
                    )
                ).where(
                    ResourceSegmentTextSearch.generation_id == generation_id,
                    ResourceSegmentTextSearch.resource_version_ref
                    == row.resource_version_ref,
                    ResourceSegmentTextSearch.segment_ordinal
                    == row.segment_ordinal,
                )
            )
            if vector_matches is not True:
                raise KnowledgeInvariantError(
                    "SR-2 candidate lexical projection mismatch"
                )

        if seen != set(expected_segments):
            raise KnowledgeInvariantError(
                "SR-2 candidate segment coverage is incomplete"
            )
        return generation_kernel.read_generation(generation_id)

    def _prepare_source(
        self,
        source: GovernedProjectionSource,
        *,
        structural_profile: SectionSegmentationProfile,
        projection_profile: RetrievalProjectionProfile,
    ) -> _PreparedSource:
        version_ref = source.observation.resource_version_ref
        version = self.session.get(ResourceVersion, version_ref)
        if version is None:
            raise KnowledgeInvariantError(
                f"SR-2 governed source references unknown ResourceVersion: {version_ref}"
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
        if _git_blob_sha(content) != source.observation.git_blob_sha:
            raise KnowledgeInvariantError(
                "SR-2 exact parent bytes do not match governed Git blob observation"
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
            observation=source.observation,
            profile=projection_profile,
        )
        if lifecycle.projection_profile_digest != projection_profile.digest:
            raise KnowledgeInvariantError(
                "SR-2 lifecycle projection profile identity mismatch"
            )

        prepared_segments = tuple(
            _PreparedSegment(
                projection=segment,
                local_search_text=_local_search_text(segment, content),
                heading_context_text="\n".join(
                    heading.display_text
                    for heading in segment.structural_segment.heading_path
                ),
            )
            for segment in lifecycle.segments
        )
        return _PreparedSource(
            source=source,
            version=version,
            content=content,
            structural=structural,
            lifecycle=lifecycle,
            segments=prepared_segments,
        )

    def _validate_segment_row(
        self,
        row: ResourceSegmentTextSearch,
        expected: _PreparedSegment,
    ) -> None:
        projection = expected.projection
        structural = projection.structural_segment
        declaration = projection.declaration
        observation = projection.governed_observation
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
            "repository": observation.repository_locator,
            "source_repository_key": observation.source_repository_key,
            "source_document_key": observation.source_document_key,
            "source_path": observation.source_path,
            "source_version": observation.source_commit,
        }
        for field, value in expected_values.items():
            if getattr(row, field) != value:
                raise KnowledgeInvariantError(
                    f"SR-2 candidate segment field mismatch: {field}"
                )

    def _stale_building_generation(self, generation_id: UUID) -> None:
        row = self.session.get(DerivedGeneration, generation_id)
        if row is None or row.status != GenerationStatus.BUILDING.value:
            return
        self._generation_kernel().mark_generation_stale(
            generation_id=generation_id
        )

    def _generation_kernel(self):
        from knowledge_core.application.generations import GenerationKnowledgeKernel

        return GenerationKnowledgeKernel(
            self.session,
            artifact_store=self.artifact_store,
        )


def _git_blob_sha(content: bytes) -> str:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


def _heading_path_payload(heading_path) -> list[dict]:
    return [
        {
            "display_text": heading.display_text,
            "level": heading.level,
            "source_byte_end": heading.source_byte_end,
            "source_byte_start": heading.source_byte_start,
            "source_line": heading.source_line,
        }
        for heading in heading_path
    ]


def _effective_control_payload(segment: SegmentLifecycleProjection) -> list[dict]:
    payload: list[dict] = []
    for control in segment.effective_controls:
        declaration = control.declaration
        payload.append(
            {
                "declaration": (
                    {
                        "heading_source_byte_start": declaration.heading_source_byte_start,
                        "source_byte_end": declaration.source_byte_end,
                        "source_byte_start": declaration.source_byte_start,
                        "source_line": declaration.source_line,
                    }
                    if declaration is not None
                    else None
                ),
                "lifecycle_state": control.lifecycle_state.value,
                "origin": control.origin.value,
            }
        )
    return payload


def _local_search_text(
    segment: SegmentLifecycleProjection,
    content: bytes,
) -> str:
    structural = segment.structural_segment
    start = structural.source_byte_start
    end = structural.source_byte_end
    declaration = segment.declaration
    if (
        declaration is not None
        and start <= declaration.source_byte_start
        and declaration.source_byte_end <= end
    ):
        raw = (
            content[start : declaration.source_byte_start]
            + content[declaration.source_byte_end : end]
        )
    else:
        raw = content[start:end]
    return raw.decode("utf-8", errors="strict")


def _weighted_search_vector(local_text: str, heading_text: str):
    local_vector = func.setweight(
        func.to_tsvector(_ENGLISH_REGCONFIG, local_text),
        _WEIGHT_A,
    )
    heading_vector = func.setweight(
        func.to_tsvector(_ENGLISH_REGCONFIG, heading_text),
        _WEIGHT_B,
    )
    return local_vector.op("||")(heading_vector)
