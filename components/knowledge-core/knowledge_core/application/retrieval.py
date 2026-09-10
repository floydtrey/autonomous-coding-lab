from __future__ import annotations

from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import and_, case, delete, func, insert, literal_column, or_, select

from knowledge_core.application.generations import GenerationKnowledgeKernel
from knowledge_core.application.resource_service import ResourceServiceKnowledgeKernel
from knowledge_core.application.section_generation import (
    SR2_SEGMENT_MODEL_IDENTITY,
    SR2_SEGMENT_MODEL_VERSION,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind, GenerationSnapshot
from knowledge_core.domain.retrieval import (
    RetrievalHit,
    RetrievalLifecycleState,
    RetrievalSearchSnapshot,
    SegmentRetrievalProvenance,
    TextIndexSource,
)
from knowledge_core.storage.repository_import_models import RepositorySourceObservation
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.retrieval_models import ResourceTextSearch
from knowledge_core.storage.section_retrieval_models import (
    ResourceSegmentTextSearch,
    TextGenerationProfile,
    TextGenerationSource,
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


class RetrievalServiceKnowledgeKernel(ResourceServiceKnowledgeKernel):
    """RF-2/SR-2 PostgreSQL lexical retrieval under one text-generation fence."""

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

    def _purge_derived_for_target(self, target_ref: UUID) -> None:
        """Extend the accepted privacy reconciliation to SR-2 segment derivatives."""

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

    def _load_indexable_source(
        self,
        source: TextIndexSource,
    ) -> tuple[ResourceVersion, str] | None:
        version = self.session.get(ResourceVersion, source.resource_version_ref)
        if version is None:
            raise KnowledgeInvariantError(
                f"unknown resource version: {source.resource_version_ref}"
            )
        if not self.resource_version_serving_eligible(source.resource_version_ref):
            raise KnowledgeInvariantError(
                f"resource version is not serving-eligible for indexing: "
                f"{source.resource_version_ref}"
            )
        if version.media_type not in _SUPPORTED_MEDIA:
            return None

        content = self.artifact_store.read_bytes(version.artifact_key)
        if version.content_digest_algo != "sha256":
            raise KnowledgeInvariantError(
                "RF-2 supports only SHA-256 exact resource versions"
            )
        if sha256(content).hexdigest() != version.content_digest:
            raise KnowledgeInvariantError(
                f"resource version digest does not match immutable artifact: "
                f"{source.resource_version_ref}"
            )
        try:
            body = content.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise KnowledgeInvariantError(
                f"supported text resource is not strict UTF-8: "
                f"{source.resource_version_ref}"
            ) from exc
        return version, body

    def build_text_generation(
        self,
        *,
        sources: tuple[TextIndexSource, ...] | list[TextIndexSource],
    ) -> GenerationSnapshot:
        self._require_postgresql_retrieval()
        normalized = tuple(sources)
        refs = [source.resource_version_ref for source in normalized]
        if len(set(refs)) != len(refs):
            raise KnowledgeInvariantError(
                "text retrieval generation sources must be unique"
            )

        indexable: list[tuple[TextIndexSource, ResourceVersion, str]] = []
        for source in normalized:
            loaded = self._load_indexable_source(source)
            if loaded is None:
                continue
            version, body = loaded
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
            raise KnowledgeInvariantError("retrieval limit must be between 1 and 50")

        current = self._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        if current is None:
            return RetrievalSearchSnapshot(
                query=normalized_query,
                generation_id=None,
                source_revision_highwater=None,
                results=(),
            )

        if (
            current.model_identity == SR2_SEGMENT_MODEL_IDENTITY
            and current.model_version == SR2_SEGMENT_MODEL_VERSION
        ):
            return self._search_segment_text(
                current=current,
                query=normalized_query,
                limit=limit,
                include_superseded=include_superseded,
            )
        if (
            current.model_identity == "postgresql-full-text"
            and current.model_version == "rf2-v1"
        ):
            return self._search_resource_version_text(
                current=current,
                query=normalized_query,
                limit=limit,
                include_superseded=include_superseded,
            )
        raise KnowledgeInvariantError(
            "current text generation has an unsupported retrieval implementation identity"
        )

    def _search_resource_version_text(
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
            retrieval_mode="resource_version",
            generation_config_digest=current.config_digest,
        )

    def _search_segment_text(
        self,
        *,
        current: GenerationSnapshot,
        query: str,
        limit: int,
        include_superseded: bool,
    ) -> RetrievalSearchSnapshot:
        profile = self.session.get(TextGenerationProfile, current.generation_id)
        if profile is None:
            raise KnowledgeInvariantError(
                "current SR-2 generation is missing recoverable profile identity"
            )
        if profile.generation_config_digest != current.config_digest:
            raise KnowledgeInvariantError(
                "current SR-2 generation config/profile identity mismatch"
            )

        tsquery = func.websearch_to_tsquery(_ENGLISH_REGCONFIG, query)
        lexical_score = func.ts_rank_cd(
            ResourceSegmentTextSearch.search_vector,
            tsquery,
        ).label("lexical_score")
        lifecycle_priority = case(
            (ResourceSegmentTextSearch.effective_lifecycle_state == "current", 0),
            (ResourceSegmentTextSearch.effective_lifecycle_state == "unknown", 1),
            else_=2,
        )

        statement = (
            select(
                ResourceSegmentTextSearch,
                ResourceVersion,
                TextGenerationSource,
                RepositorySourceObservation,
                lexical_score,
            )
            .join(
                ResourceVersion,
                ResourceVersion.ref_id
                == ResourceSegmentTextSearch.resource_version_ref,
            )
            .join(
                TextGenerationSource,
                and_(
                    TextGenerationSource.generation_id
                    == ResourceSegmentTextSearch.generation_id,
                    TextGenerationSource.resource_version_ref
                    == ResourceSegmentTextSearch.resource_version_ref,
                ),
            )
            .join(
                RepositorySourceObservation,
                RepositorySourceObservation.observation_id
                == TextGenerationSource.source_observation_id,
            )
            .where(
                ResourceSegmentTextSearch.generation_id == current.generation_id,
                ResourceSegmentTextSearch.search_vector.op("@@")(tsquery),
            )
        )
        if not include_superseded:
            statement = statement.where(
                ResourceSegmentTextSearch.effective_lifecycle_state
                != "superseded"
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
        for search_row, version, lineage, observation, score in self.session.execute(
            statement
        ):
            # The privacy/access fence is authoritative even if stale segment rows
            # survive or are maliciously reintroduced after eager reconciliation.
            if not self.resource_version_serving_eligible(version.ref_id):
                continue
            effective = RetrievalLifecycleState(
                search_row.effective_lifecycle_state
            )
            segment = SegmentRetrievalProvenance(
                governed_observation_id=lineage.source_observation_id,
                governing_manifest_digest=lineage.governing_manifest_digest,
                projection_snapshot_digest=lineage.projection_snapshot_digest,
                source_repository_key=search_row.source_repository_key,
                source_document_key=search_row.source_document_key,
                source_classification=observation.classification,
                segment_key=search_row.segment_key,
                segment_ordinal=int(search_row.segment_ordinal),
                structural_kind=search_row.structural_kind,
                base_block_ordinal=int(search_row.base_block_ordinal),
                part_index=int(search_row.part_index),
                part_count=int(search_row.part_count),
                source_byte_start=int(search_row.source_byte_start),
                source_byte_end=int(search_row.source_byte_end),
                source_line_start=int(search_row.source_line_start),
                source_line_end=int(search_row.source_line_end),
                source_slice_sha256=search_row.source_slice_sha256,
                heading_path=tuple(search_row.heading_path),
                parent_lifecycle_state=RetrievalLifecycleState(
                    search_row.parent_lifecycle_state
                ),
                declared_lifecycle_state=(
                    RetrievalLifecycleState(search_row.declared_lifecycle_state)
                    if search_row.declared_lifecycle_state is not None
                    else None
                ),
                declaration_source_line=(
                    int(search_row.declaration_source_line)
                    if search_row.declaration_source_line is not None
                    else None
                ),
                declaration_byte_start=(
                    int(search_row.declaration_byte_start)
                    if search_row.declaration_byte_start is not None
                    else None
                ),
                declaration_byte_end=(
                    int(search_row.declaration_byte_end)
                    if search_row.declaration_byte_end is not None
                    else None
                ),
                effective_lifecycle_state=effective,
                effective_control_provenance=tuple(
                    search_row.effective_control_provenance
                ),
            )
            hits.append(
                RetrievalHit(
                    resource_ref=version.resource_ref_id,
                    resource_version_ref=version.ref_id,
                    content_digest_algo=version.content_digest_algo,
                    content_digest=version.content_digest,
                    media_type=version.media_type,
                    observed_occurrence_ref=version.observed_occurrence_ref,
                    created_revision_id=int(version.created_revision_id),
                    lifecycle_state=effective,
                    authority_rank=search_row.authority_rank,
                    repository=search_row.repository,
                    source_path=search_row.source_path,
                    source_version=search_row.source_version,
                    observed_at=None,
                    lexical_score=float(score),
                    segment=segment,
                )
            )
            if len(hits) >= limit:
                break

        return RetrievalSearchSnapshot(
            query=query,
            generation_id=current.generation_id,
            source_revision_highwater=current.source_revision_highwater,
            results=tuple(hits),
            retrieval_mode="segment",
            generation_config_digest=current.config_digest,
            structural_profile_id=profile.structural_profile_id,
            structural_profile_digest=profile.structural_profile_digest,
            projection_profile_id=profile.projection_profile_id,
            projection_profile_digest=profile.projection_profile_digest,
        )
