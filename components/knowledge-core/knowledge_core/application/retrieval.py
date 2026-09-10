from __future__ import annotations

from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import case, delete, func, insert, literal_column, or_, select

from knowledge_core.application.generations import GenerationKnowledgeKernel
from knowledge_core.application.resource_service import ResourceServiceKnowledgeKernel
from knowledge_core.application.segmentation import (
    DEFAULT_SECTION_SEGMENTATION_PROFILE,
    SectionSegmentationProfile,
    segment_text_resource,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind, GenerationSnapshot
from knowledge_core.domain.retrieval import (
    RetrievalHit,
    RetrievalLifecycleState,
    RetrievalSearchSnapshot,
    TextIndexSource,
)
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.retrieval_models import (
    ResourceSegmentTextSearch,
    ResourceTextSearch,
)


_SUPPORTED_MEDIA = frozenset({"text/plain", "text/markdown"})
_TEXT_SEARCH_CONFIG = {
    "language": "english",
    "projection": "resource-version-v1",
    "supported_media": sorted(_SUPPORTED_MEDIA),
    "default_include_superseded": False,
    "ranking": [
        "ts_rank_cd:desc",
        "lifecycle:current-unknown-superseded",
        "authority_rank:asc:nulls-last",
        "created_revision_id:desc",
        "resource_version_ref:asc",
    ],
}
TEXT_SEARCH_CONFIG_DIGEST = "sha256:" + sha256(
    json.dumps(
        _TEXT_SEARCH_CONFIG,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
_ENGLISH_REGCONFIG = literal_column("'english'::regconfig")
_WEIGHT_A = literal_column("'A'::\"char\"")
_WEIGHT_B = literal_column("'B'::\"char\"")
_SEGMENT_MODEL_IDENTITY = "deterministic-python-postgresql-full-text"
_SEGMENT_MODEL_VERSION = "sr2-segment-v1"
_SEGMENT_PROJECTION = "resource-segment-v1"
_LEGACY_PROJECTION = "resource-version-v1"


class RetrievalServiceKnowledgeKernel(ResourceServiceKnowledgeKernel):
    """RF-2 whole-document plus SR-2 deterministic segment lexical retrieval."""

    def _require_postgresql_retrieval(self) -> None:
        if self.session.get_bind().dialect.name != "postgresql":
            raise KnowledgeInvariantError(
                "RF-2/SR-2 lexical retrieval requires PostgreSQL"
            )

    def _generation_kernel(self) -> GenerationKnowledgeKernel:
        return GenerationKnowledgeKernel(
            self.session,
            artifact_store=self.artifact_store,
        )

    def _load_indexable_source(
        self,
        source: TextIndexSource,
    ) -> tuple[ResourceVersion, bytes, str] | None:
        version = self.session.get(ResourceVersion, source.resource_version_ref)
        if version is None:
            raise KnowledgeInvariantError(
                f"unknown resource version: {source.resource_version_ref}"
            )
        if not self.resource_version_serving_eligible(source.resource_version_ref):
            raise KnowledgeInvariantError(
                "resource version is not serving-eligible for indexing: "
                f"{source.resource_version_ref}"
            )
        if version.media_type not in _SUPPORTED_MEDIA:
            return None

        content = self.artifact_store.read_bytes(version.artifact_key)
        if version.content_digest_algo != "sha256":
            raise KnowledgeInvariantError(
                "RF-2/SR-2 supports only SHA-256 exact resource versions"
            )
        if sha256(content).hexdigest() != version.content_digest:
            raise KnowledgeInvariantError(
                "resource version digest does not match immutable artifact: "
                f"{source.resource_version_ref}"
            )
        try:
            body = content.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise KnowledgeInvariantError(
                "supported text resource is not strict UTF-8: "
                f"{source.resource_version_ref}"
            ) from exc
        return version, content, body

    def _normalize_sources(
        self,
        sources: tuple[TextIndexSource, ...] | list[TextIndexSource],
    ) -> tuple[TextIndexSource, ...]:
        normalized = tuple(sources)
        refs = [source.resource_version_ref for source in normalized]
        if len(set(refs)) != len(refs):
            raise KnowledgeInvariantError(
                "text retrieval generation sources must be unique"
            )
        return normalized

    def _purge_derived_for_target(self, target_ref: UUID) -> None:
        super()._purge_derived_for_target(target_ref)
        resource_versions_for_logical = select(ResourceVersion.ref_id).where(
            ResourceVersion.resource_ref_id == target_ref
        )
        self.session.execute(
            delete(ResourceSegmentTextSearch).where(
                or_(
                    ResourceSegmentTextSearch.resource_version_ref == target_ref,
                    ResourceSegmentTextSearch.resource_version_ref.in_(
                        resource_versions_for_logical
                    ),
                )
            )
        )

    def build_text_generation(
        self,
        *,
        sources: tuple[TextIndexSource, ...] | list[TextIndexSource],
    ) -> GenerationSnapshot:
        """Build the accepted RF-2 legacy whole-ResourceVersion projection."""
        self._require_postgresql_retrieval()
        normalized = self._normalize_sources(sources)

        indexable: list[tuple[TextIndexSource, ResourceVersion, str]] = []
        for source in normalized:
            loaded = self._load_indexable_source(source)
            if loaded is None:
                continue
            version, _content, body = loaded
            indexable.append((source, version, body))

        source_revision_highwater = self.current_revision()
        if source_revision_highwater <= 0:
            raise KnowledgeInvariantError(
                "text retrieval generation requires canonical source revisions"
            )

        generation_kernel = self._generation_kernel()
        generation = generation_kernel.start_generation(
            derived_kind=DerivedKind.TEXT,
            source_revision_highwater=source_revision_highwater,
            sources=tuple(
                (version.ref_id, int(version.created_revision_id))
                for _source, version, _body in indexable
            ),
            model_identity="postgresql-full-text",
            model_version="rf2-v1",
            config_digest=TEXT_SEARCH_CONFIG_DIGEST,
        )

        try:
            for source, version, body in indexable:
                self.session.execute(
                    insert(ResourceTextSearch).values(
                        generation_id=generation.generation_id,
                        resource_version_ref=version.ref_id,
                        lifecycle_state=source.lifecycle_state.value,
                        authority_rank=source.authority_rank,
                        repository=source.repository,
                        source_path=source.source_path,
                        source_version=source.source_version,
                        observed_at=source.observed_at,
                        search_vector=func.to_tsvector(_ENGLISH_REGCONFIG, body),
                    )
                )
            self._commit()
            return generation_kernel.settle_generation(
                generation_id=generation.generation_id
            )
        except Exception:
            self.session.rollback()
            try:
                generation_kernel.mark_generation_stale(
                    generation_id=generation.generation_id
                )
            except Exception:
                self.session.rollback()
            raise

    def build_segment_text_generation(
        self,
        *,
        sources: tuple[TextIndexSource, ...] | list[TextIndexSource],
        profile: SectionSegmentationProfile = DEFAULT_SECTION_SEGMENTATION_PROFILE,
        before_settle_hook=None,
    ) -> GenerationSnapshot:
        """Build an SR-2 deterministic section projection over exact parents."""
        self._require_postgresql_retrieval()
        normalized = self._normalize_sources(sources)

        prepared: list[
            tuple[TextIndexSource, ResourceVersion, str, tuple]
        ] = []
        for source in normalized:
            loaded = self._load_indexable_source(source)
            if loaded is None:
                continue
            version, content, body = loaded
            segments = segment_text_resource(
                content=content,
                media_type=str(version.media_type),
                resource_version_ref=version.ref_id,
                parent_lifecycle_state=source.lifecycle_state,
                profile=profile,
            )
            prepared.append((source, version, body, segments))

        source_revision_highwater = self.current_revision()
        if source_revision_highwater <= 0:
            raise KnowledgeInvariantError(
                "text retrieval generation requires canonical source revisions"
            )

        generation_kernel = self._generation_kernel()
        generation = generation_kernel.start_generation(
            derived_kind=DerivedKind.TEXT,
            source_revision_highwater=source_revision_highwater,
            sources=tuple(
                (version.ref_id, int(version.created_revision_id))
                for _source, version, _body, _segments in prepared
            ),
            model_identity=_SEGMENT_MODEL_IDENTITY,
            model_version=_SEGMENT_MODEL_VERSION,
            config_digest=profile.digest,
        )

        try:
            for source, version, body, segments in prepared:
                # Transition compatibility: retain the RF-2 whole-document
                # tsvector row in the same generation, but segment-mode search
                # never reads it. This preserves older persistence evidence
                # while the current projection is selected by model_version.
                self.session.execute(
                    insert(ResourceTextSearch).values(
                        generation_id=generation.generation_id,
                        resource_version_ref=version.ref_id,
                        lifecycle_state=source.lifecycle_state.value,
                        authority_rank=source.authority_rank,
                        repository=source.repository,
                        source_path=source.source_path,
                        source_version=source.source_version,
                        observed_at=source.observed_at,
                        search_vector=func.to_tsvector(
                            _ENGLISH_REGCONFIG,
                            body,
                        ),
                    )
                )
                for segment in segments:
                    local_vector = func.setweight(
                        func.to_tsvector(
                            _ENGLISH_REGCONFIG,
                            segment.local_search_text,
                        ),
                        _WEIGHT_A,
                    )
                    heading_vector = func.setweight(
                        func.to_tsvector(
                            _ENGLISH_REGCONFIG,
                            segment.heading_context_text,
                        ),
                        _WEIGHT_B,
                    )
                    self.session.execute(
                        insert(ResourceSegmentTextSearch).values(
                            generation_id=generation.generation_id,
                            resource_version_ref=version.ref_id,
                            segment_ordinal=segment.segment_ordinal,
                            segment_key=segment.segment_key,
                            segment_kind=segment.segment_kind,
                            base_block_ordinal=segment.base_block_ordinal,
                            part_index=segment.part_index,
                            part_count=segment.part_count,
                            source_byte_start=segment.source_byte_start,
                            source_byte_end=segment.source_byte_end,
                            source_line_start=segment.source_line_start,
                            source_line_end=segment.source_line_end,
                            source_slice_sha256=segment.source_slice_sha256,
                            heading_path=[
                                item.as_dict() for item in segment.heading_path
                            ],
                            lifecycle_state=segment.lifecycle_state.value,
                            parent_lifecycle_state=(
                                segment.parent_lifecycle_state.value
                            ),
                            lifecycle_origin=segment.lifecycle_origin,
                            lifecycle_directive_line=(
                                segment.lifecycle_directive_line
                            ),
                            authority_rank=source.authority_rank,
                            repository=source.repository,
                            source_path=source.source_path,
                            source_version=source.source_version,
                            observed_at=source.observed_at,
                            search_vector=local_vector.op("||")(heading_vector),
                        )
                    )
            self._commit()
            if before_settle_hook is not None:
                before_settle_hook(generation)
            return generation_kernel.settle_generation(
                generation_id=generation.generation_id
            )
        except Exception:
            self.session.rollback()
            try:
                generation_kernel.mark_generation_stale(
                    generation_id=generation.generation_id
                )
            except Exception:
                self.session.rollback()
            raise

    def _search_legacy_generation(
        self,
        *,
        current: GenerationSnapshot,
        query: str,
        limit: int,
        include_superseded: bool,
    ) -> RetrievalSearchSnapshot:
        tsquery = func.websearch_to_tsquery(_ENGLISH_REGCONFIG, query)
        lexical_score = func.ts_rank_cd(
            ResourceTextSearch.search_vector,
            tsquery,
        ).label("lexical_score")
        lifecycle_priority = case(
            (ResourceTextSearch.lifecycle_state == "current", 0),
            (ResourceTextSearch.lifecycle_state == "unknown", 1),
            else_=2,
        )

        statement = (
            select(ResourceTextSearch, ResourceVersion, lexical_score)
            .join(
                ResourceVersion,
                ResourceVersion.ref_id == ResourceTextSearch.resource_version_ref,
            )
            .where(
                ResourceTextSearch.generation_id == current.generation_id,
                ResourceTextSearch.search_vector.op("@@")(tsquery),
            )
        )
        if not include_superseded:
            statement = statement.where(
                ResourceTextSearch.lifecycle_state != "superseded"
            )
        statement = statement.order_by(
            lexical_score.desc(),
            lifecycle_priority.asc(),
            ResourceTextSearch.authority_rank.asc().nulls_last(),
            ResourceVersion.created_revision_id.desc(),
            ResourceVersion.ref_id.asc(),
        )

        hits: list[RetrievalHit] = []
        for search_row, version, score in self.session.execute(statement):
            if not self.resource_version_serving_eligible(version.ref_id):
                continue
            hits.append(
                RetrievalHit(
                    resource_ref=version.resource_ref_id,
                    resource_version_ref=version.ref_id,
                    content_digest_algo=version.content_digest_algo,
                    content_digest=version.content_digest,
                    media_type=version.media_type,
                    observed_occurrence_ref=version.observed_occurrence_ref,
                    created_revision_id=int(version.created_revision_id),
                    lifecycle_state=RetrievalLifecycleState(
                        search_row.lifecycle_state
                    ),
                    authority_rank=search_row.authority_rank,
                    repository=search_row.repository,
                    source_path=search_row.source_path,
                    source_version=search_row.source_version,
                    observed_at=search_row.observed_at,
                    lexical_score=float(score),
                )
            )
            if len(hits) >= limit:
                break

        return RetrievalSearchSnapshot(
            query=query,
            generation_id=current.generation_id,
            source_revision_highwater=current.source_revision_highwater,
            results=tuple(hits),
            projection=_LEGACY_PROJECTION,
            profile_digest=None,
        )

    def _search_segment_generation(
        self,
        *,
        current: GenerationSnapshot,
        query: str,
        limit: int,
        include_superseded: bool,
    ) -> RetrievalSearchSnapshot:
        tsquery = func.websearch_to_tsquery(_ENGLISH_REGCONFIG, query)
        lexical_score = func.ts_rank_cd(
            ResourceSegmentTextSearch.search_vector,
            tsquery,
        ).label("lexical_score")
        lifecycle_priority = case(
            (ResourceSegmentTextSearch.lifecycle_state == "current", 0),
            (ResourceSegmentTextSearch.lifecycle_state == "unknown", 1),
            else_=2,
        )

        statement = (
            select(ResourceSegmentTextSearch, ResourceVersion, lexical_score)
            .join(
                ResourceVersion,
                ResourceVersion.ref_id
                == ResourceSegmentTextSearch.resource_version_ref,
            )
            .where(
                ResourceSegmentTextSearch.generation_id
                == current.generation_id,
                ResourceSegmentTextSearch.search_vector.op("@@")(tsquery),
            )
        )
        if not include_superseded:
            statement = statement.where(
                ResourceSegmentTextSearch.lifecycle_state != "superseded"
            )
        statement = statement.order_by(
            lexical_score.desc(),
            lifecycle_priority.asc(),
            ResourceSegmentTextSearch.authority_rank.asc().nulls_last(),
            ResourceVersion.created_revision_id.desc(),
            ResourceVersion.ref_id.asc(),
            ResourceSegmentTextSearch.segment_ordinal.asc(),
            ResourceSegmentTextSearch.segment_key.asc(),
        )

        hits: list[RetrievalHit] = []
        for search_row, version, score in self.session.execute(statement):
            if not self.resource_version_serving_eligible(version.ref_id):
                continue
            hits.append(
                RetrievalHit(
                    resource_ref=version.resource_ref_id,
                    resource_version_ref=version.ref_id,
                    content_digest_algo=version.content_digest_algo,
                    content_digest=version.content_digest,
                    media_type=version.media_type,
                    observed_occurrence_ref=version.observed_occurrence_ref,
                    created_revision_id=int(version.created_revision_id),
                    lifecycle_state=RetrievalLifecycleState(
                        search_row.lifecycle_state
                    ),
                    authority_rank=search_row.authority_rank,
                    repository=search_row.repository,
                    source_path=search_row.source_path,
                    source_version=search_row.source_version,
                    observed_at=search_row.observed_at,
                    lexical_score=float(score),
                    segment_key=search_row.segment_key,
                    segment_ordinal=int(search_row.segment_ordinal),
                    segment_kind=search_row.segment_kind,
                    base_block_ordinal=int(search_row.base_block_ordinal),
                    part_index=int(search_row.part_index),
                    part_count=int(search_row.part_count),
                    source_byte_start=int(search_row.source_byte_start),
                    source_byte_end=int(search_row.source_byte_end),
                    source_line_start=int(search_row.source_line_start),
                    source_line_end=int(search_row.source_line_end),
                    source_slice_sha256=search_row.source_slice_sha256,
                    heading_path=tuple(search_row.heading_path or ()),
                    parent_lifecycle_state=RetrievalLifecycleState(
                        search_row.parent_lifecycle_state
                    ),
                    lifecycle_origin=search_row.lifecycle_origin,
                    lifecycle_directive_line=(
                        int(search_row.lifecycle_directive_line)
                        if search_row.lifecycle_directive_line is not None
                        else None
                    ),
                )
            )
            if len(hits) >= limit:
                break

        return RetrievalSearchSnapshot(
            query=query,
            generation_id=current.generation_id,
            source_revision_highwater=current.source_revision_highwater,
            results=tuple(hits),
            projection=_SEGMENT_PROJECTION,
            profile_digest=current.config_digest,
        )

    def search_text(
        self,
        *,
        query: str,
        limit: int = 10,
        include_superseded: bool = False,
    ) -> RetrievalSearchSnapshot:
        self._require_postgresql_retrieval()
        normalized_query = query.strip()
        if not normalized_query:
            raise KnowledgeInvariantError("retrieval query must not be blank")
        if limit < 1 or limit > 50:
            raise KnowledgeInvariantError(
                "retrieval limit must be between 1 and 50"
            )

        current = self._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        if current is None:
            return RetrievalSearchSnapshot(
                query=normalized_query,
                generation_id=None,
                source_revision_highwater=None,
                results=(),
                projection=None,
                profile_digest=None,
            )

        if current.model_version == _SEGMENT_MODEL_VERSION:
            return self._search_segment_generation(
                current=current,
                query=normalized_query,
                limit=limit,
                include_superseded=include_superseded,
            )
        return self._search_legacy_generation(
            current=current,
            query=normalized_query,
            limit=limit,
            include_superseded=include_superseded,
        )
