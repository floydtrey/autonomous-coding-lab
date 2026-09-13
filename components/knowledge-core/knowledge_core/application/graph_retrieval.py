from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from knowledge_core.application.projection_orchestration import ProjectionOrchestrationKnowledgeKernel
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityEvaluator,
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
    require_retrieval_authority,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.domain.projection_adapter import (
    ProjectionAdapter,
    ProjectionSourceSegment,
    TrustedProjectionHit,
    TrustedProjectionSearchSnapshot,
)
from knowledge_core.domain.projection_evidence import (
    ProjectionDisposition,
    ProjectionValidationState,
)
from knowledge_core.storage.projection_models import ProjectionAttempt


class GraphProjectionRetrievalKnowledgeKernel(ProjectionOrchestrationKnowledgeKernel):
    """Authority-first trusted retrieval from validated external graph projections."""

    async def search_validated_projection(
        self,
        *,
        adapter: ProjectionAdapter,
        authority_evaluator: RetrievalAuthorityEvaluator | None,
        caller_principal_ref: str,
        namespace_key: str,
        scope_key: str,
        query: str,
        limit: int = 10,
    ) -> TrustedProjectionSearchSnapshot:
        normalized_query = query.strip()
        if not normalized_query:
            raise KnowledgeInvariantError("graph retrieval query must not be blank")
        if limit < 1 or limit > 50:
            raise KnowledgeInvariantError("graph retrieval limit must be between 1 and 50")
        namespace_key = namespace_key.strip()
        scope_key = scope_key.strip()
        if not namespace_key or not scope_key:
            raise KnowledgeInvariantError("graph retrieval requires explicit namespace and scope")

        # Authority is deliberately evaluated before the query reaches Graphiti,
        # its embedder, reranker, or any other external projection component.
        require_retrieval_authority(
            authority_evaluator,
            RetrievalAuthorityRequest(
                caller_principal_ref=caller_principal_ref,
                operation=RetrievalAuthorityOperation.SEARCH_GRAPH,
                limit=limit,
                include_superseded=False,
                namespace_key=namespace_key,
                scope_key=scope_key,
            ),
        )

        current = self.current_generation(derived_kind=DerivedKind.TEXT)
        if current is None:
            return TrustedProjectionSearchSnapshot(
                query=normalized_query,
                namespace_key=namespace_key,
                scope_key=scope_key,
                generation_id=None,
                attempt_ids=(),
                results=(),
            )
        expected_profile_id = f"sr2-generation:{current.generation_id}"
        descriptor = adapter.descriptor
        rows = self.session.scalars(
            select(ProjectionAttempt)
            .where(
                ProjectionAttempt.namespace_key == namespace_key,
                ProjectionAttempt.scope_key == scope_key,
                ProjectionAttempt.backend_identity == descriptor.backend_identity,
                ProjectionAttempt.backend_version == descriptor.backend_version,
                ProjectionAttempt.profile_id == expected_profile_id,
                ProjectionAttempt.profile_digest == current.config_digest,
                ProjectionAttempt.config_digest == descriptor.config_digest,
                ProjectionAttempt.disposition == ProjectionDisposition.SUCCEEDED.value,
                ProjectionAttempt.validation_state == ProjectionValidationState.VALIDATED.value,
            )
            .order_by(ProjectionAttempt.started_at, ProjectionAttempt.attempt_id)
        ).all()
        if not rows:
            return TrustedProjectionSearchSnapshot(
                query=normalized_query,
                namespace_key=namespace_key,
                scope_key=scope_key,
                generation_id=current.generation_id,
                attempt_ids=(),
                results=(),
            )

        correlation: dict[str, ProjectionSourceSegment] = {}
        attempt_ids: list[UUID] = []
        for row in rows:
            plan = self.projection_plan_for_attempt(row.attempt_id)
            attempt_ids.append(row.attempt_id)
            for segment in plan.segments:
                source_key = adapter.source_correlation_key(
                    segment=segment,
                    namespace_key=namespace_key,
                    scope_key=scope_key,
                    projection_profile_id=expected_profile_id,
                )
                existing = correlation.get(source_key)
                if existing is not None and existing != segment:
                    raise KnowledgeInvariantError(
                        f"projection source correlation key collision: {source_key}"
                    )
                correlation[source_key] = segment

        expected_partition = adapter.partition_key(
            namespace_key=namespace_key,
            scope_key=scope_key,
            projection_profile_id=expected_profile_id,
        )
        hits = await adapter.search(
            query=normalized_query,
            namespace_key=namespace_key,
            scope_key=scope_key,
            projection_profile_id=expected_profile_id,
            limit=limit,
        )

        # The graph call can take seconds. Re-check the accepted generation after
        # the external boundary so a concurrent SR-2 publication cannot make stale
        # graph facts trusted under a new canonical snapshot.
        self.session.expire_all()
        after = self.current_generation(derived_kind=DerivedKind.TEXT)
        if after is None or after.generation_id != current.generation_id:
            raise KnowledgeInvariantError(
                "current SR-2 generation changed during graph retrieval; retry against the new snapshot"
            )

        trusted: list[TrustedProjectionHit] = []
        for hit in hits:
            if hit.partition_key != expected_partition:
                continue
            # A merged graph fact can carry multiple sourcing episodes. Trust the
            # fact only when *every* provider source maps to a currently validated,
            # currently serving KC source. One unknown contributor rejects the hit.
            if not hit.source_correlation_keys:
                continue
            if any(source_key not in correlation for source_key in hit.source_correlation_keys):
                continue

            matched: list[ProjectionSourceSegment] = []
            seen_segment_keys: set[str] = set()
            eligible = True
            for source_key in hit.source_correlation_keys:
                segment = correlation[source_key]
                if not self.resource_version_serving_eligible(segment.resource_version_ref):
                    eligible = False
                    break
                if segment.effective_lifecycle_state == "superseded":
                    eligible = False
                    break
                if segment.segment_key not in seen_segment_keys:
                    seen_segment_keys.add(segment.segment_key)
                    matched.append(segment)
            if not eligible or not matched:
                continue

            trusted.append(
                TrustedProjectionHit(
                    provider_hit_id=hit.provider_hit_id,
                    fact=hit.fact,
                    valid_at=hit.valid_at,
                    invalid_at=hit.invalid_at,
                    sources=tuple(matched),
                )
            )
            if len(trusted) >= limit:
                break

        return TrustedProjectionSearchSnapshot(
            query=normalized_query,
            namespace_key=namespace_key,
            scope_key=scope_key,
            generation_id=current.generation_id,
            attempt_ids=tuple(attempt_ids),
            results=tuple(trusted),
        )
