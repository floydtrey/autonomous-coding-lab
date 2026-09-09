from __future__ import annotations

from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import case, func, insert, literal_column, select

from knowledge_core.application.generations import GenerationKnowledgeKernel
from knowledge_core.application.resource_service import ResourceServiceKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind, GenerationSnapshot
from knowledge_core.domain.retrieval import (
    RetrievalHit,
    RetrievalLifecycleState,
    RetrievalSearchSnapshot,
    TextIndexSource,
)
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.retrieval_models import ResourceTextSearch


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
    """RF-2 PostgreSQL lexical retrieval over exact resource versions."""

    def _require_postgresql_retrieval(self) -> None:
        if self.session.get_bind().dialect.name != "postgresql":
            raise KnowledgeInvariantError(
                "RF-2 lexical retrieval requires PostgreSQL"
            )

    def _generation_kernel(self) -> GenerationKnowledgeKernel:
        return GenerationKnowledgeKernel(
            self.session,
            artifact_store=self.artifact_store,
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

        tsquery = func.websearch_to_tsquery(_ENGLISH_REGCONFIG, normalized_query)
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
            query=normalized_query,
            generation_id=current.generation_id,
            source_revision_highwater=current.source_revision_highwater,
            results=tuple(hits),
        )
