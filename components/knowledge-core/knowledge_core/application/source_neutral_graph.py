from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import select

from knowledge_core.application.governed_snapshot_selection import (
    GovernedSnapshotProjectionSource,
    resolve_governed_snapshot_sources,
)
from knowledge_core.application.graph_retrieval import (
    GraphProjectionRetrievalKnowledgeKernel,
)
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
    ProjectionAmbiguousRetryError,
    ProjectionExecutionResult,
    ProjectionPlan,
    ProjectionSourceSegment,
    TrustedProjectionHit,
    TrustedProjectionSearchSnapshot,
)
from knowledge_core.domain.projection_evidence import (
    ProjectionDisposition,
    ProjectionValidationState,
)
from knowledge_core.domain.source_neutral_projection import (
    GovernedProjectionSourceSegment,
    SOURCE_NEUTRAL_GRAPH_PLAN_VERSION,
    SOURCE_NEUTRAL_GRAPH_REFERENCE_TIME_POLICY,
)
from knowledge_core.storage.projection_models import ProjectionAttempt
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.section_retrieval_models import (
    ResourceSegmentTextSearch,
    TextGenerationSource,
)


DEFAULT_GRAPH_SYNC_MAX_SEGMENTS = 100
MAX_GRAPH_SYNC_SEGMENTS = 10_000


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _graph_profile_digest(text_generation_config_digest: str) -> str:
    payload = {
        "graph_plan_version": SOURCE_NEUTRAL_GRAPH_PLAN_VERSION,
        "reference_time_policy": SOURCE_NEUTRAL_GRAPH_REFERENCE_TIME_POLICY,
        "text_generation_config_digest": text_generation_config_digest,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


class SourceNeutralGraphProjectionKnowledgeKernel(
    GraphProjectionRetrievalKnowledgeKernel
):
    """Task 4 source-neutral, bounded graph synchronization boundary.

    The historical repository-shaped graph path remains available for its exact
    accepted evidence. This path requires source-neutral SR-2 lineage and never
    manufactures Git metadata for non-Git sources.
    """

    @staticmethod
    def graph_projection_profile_identity(current) -> tuple[str, str]:
        if current.config_digest is None:
            raise KnowledgeInvariantError(
                "source-neutral graph projection requires an SR-2 config digest"
            )
        return (
            f"sr2-governed-graph:{current.generation_id}",
            _graph_profile_digest(current.config_digest),
        )

    def _resolve_current_governed_sources(
        self,
        current,
    ) -> dict[UUID, GovernedSnapshotProjectionSource]:
        rows = tuple(
            self.session.scalars(
                select(TextGenerationSource).where(
                    TextGenerationSource.generation_id == current.generation_id
                )
            ).all()
        )
        if not rows:
            if current.sources:
                raise KnowledgeInvariantError(
                    "current SR-2 generation has canonical sources without governed graph lineage"
                )
            return {}

        generic_fields = (
            "governed_observation_id",
            "governed_decision_id",
            "governing_snapshot_digest",
            "governed_projection_digest",
        )
        if any(
            any(getattr(row, field) is None for field in generic_fields)
            for row in rows
        ):
            raise KnowledgeInvariantError(
                "Task 4 graph synchronization requires complete source-neutral SR-2 lineage"
            )

        snapshot_digests = {row.governing_snapshot_digest for row in rows}
        if len(snapshot_digests) != 1:
            raise KnowledgeInvariantError(
                "current SR-2 graph inputs reference multiple governed snapshots"
            )
        snapshot_digest = next(iter(snapshot_digests))
        if snapshot_digest is None:
            raise KnowledgeInvariantError(
                "current SR-2 graph inputs lost their governed snapshot identity"
            )

        resolved = resolve_governed_snapshot_sources(
            self.session,
            governing_snapshot_digest=snapshot_digest,
        )
        by_version = {
            source.member.resource_version_ref: source for source in resolved
        }
        row_refs = {row.resource_version_ref for row in rows}
        generation_refs = {item.source_ref for item in current.sources}
        if (
            len(by_version) != len(resolved)
            or set(by_version) != row_refs
            or row_refs != generation_refs
        ):
            raise KnowledgeInvariantError(
                "current SR-2 graph source set does not match the complete governed snapshot"
            )

        for row in rows:
            source = by_version[row.resource_version_ref]
            compat = source.repository_compatibility
            expected = {
                "governed_observation_id": source.observation.observation_id,
                "governed_decision_id": source.decision.decision_id,
                "governing_snapshot_digest": source.snapshot_digest,
                "governed_projection_digest": source.projection_digest,
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
            for field, value in expected.items():
                if getattr(row, field) != value:
                    raise KnowledgeInvariantError(
                        f"current SR-2 graph lineage mismatch: {field}"
                    )
            version = self.session.get(ResourceVersion, row.resource_version_ref)
            if (
                version is None
                or version.resource_ref_id != source.member.resource_ref
                or source.observation.resource_version_ref != version.ref_id
            ):
                raise KnowledgeInvariantError(
                    "current SR-2 graph source no longer matches canonical ResourceVersion"
                )
        return by_version

    @staticmethod
    def _validate_segment_governance(
        *,
        segment: ResourceSegmentTextSearch,
        source: GovernedSnapshotProjectionSource,
    ) -> None:
        compat = source.repository_compatibility
        expected = {
            "authority_rank": source.decision.authority_rank,
            "parent_lifecycle_state": source.decision.retrieval_lifecycle.value,
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
        for field, value in expected.items():
            if getattr(segment, field) != value:
                raise KnowledgeInvariantError(
                    f"current SR-2 graph segment/source evidence mismatch: {field}"
                )

    @staticmethod
    def _reference_time(source: GovernedSnapshotProjectionSource) -> datetime:
        observation = source.observation
        value = (
            observation.source_event_time
            or observation.source_revision_time
            or observation.observed_at
        )
        return _utc(value)

    def build_sr2_projection_plan(
        self,
        *,
        resource_version_refs: tuple[UUID, ...],
    ) -> ProjectionPlan:
        current = self._current_sr2_generation()
        normalized_refs = tuple(dict.fromkeys(resource_version_refs))
        if not normalized_refs:
            raise KnowledgeInvariantError(
                "source-neutral graph projection requires one or more resource versions"
            )

        governed_sources = self._resolve_current_governed_sources(current)
        missing = [ref for ref in normalized_refs if ref not in governed_sources]
        if missing:
            raise KnowledgeInvariantError(
                "resource versions are not governed sources of the current source-neutral SR-2 generation: "
                + ", ".join(str(ref) for ref in missing)
            )

        versions: dict[UUID, ResourceVersion] = {}
        sources: list[tuple[UUID, int]] = []
        for resource_version_ref in normalized_refs:
            version = self.session.get(ResourceVersion, resource_version_ref)
            if version is None:
                raise KnowledgeInvariantError(
                    f"unknown graph projection resource version: {resource_version_ref}"
                )
            if version.content_digest_algo != "sha256":
                raise KnowledgeInvariantError(
                    "source-neutral graph projection supports only SHA-256 resource versions"
                )
            if not self.resource_version_serving_eligible(resource_version_ref):
                raise KnowledgeInvariantError(
                    f"resource version is not serving-eligible for graph projection: {resource_version_ref}"
                )
            versions[resource_version_ref] = version
            sources.append((resource_version_ref, int(version.created_revision_id)))

        rows = self.session.scalars(
            select(ResourceSegmentTextSearch)
            .where(
                ResourceSegmentTextSearch.generation_id == current.generation_id,
                ResourceSegmentTextSearch.resource_version_ref.in_(normalized_refs),
                ResourceSegmentTextSearch.effective_lifecycle_state != "superseded",
            )
            .order_by(
                ResourceSegmentTextSearch.resource_version_ref,
                ResourceSegmentTextSearch.segment_ordinal,
                ResourceSegmentTextSearch.segment_key,
            )
        ).all()

        artifact_cache: dict[UUID, bytes] = {}
        segments: list[ProjectionSourceSegment] = []
        for segment in rows:
            source = governed_sources[segment.resource_version_ref]
            self._validate_segment_governance(segment=segment, source=source)
            version = versions[segment.resource_version_ref]
            content = artifact_cache.get(version.ref_id)
            if content is None:
                content = self.artifact_store.read_bytes(version.artifact_key)
                if len(content) != int(version.byte_size):
                    raise KnowledgeInvariantError(
                        f"resource version byte size does not match immutable artifact: {version.ref_id}"
                    )
                if sha256(content).hexdigest() != version.content_digest:
                    raise KnowledgeInvariantError(
                        f"resource version digest does not match immutable artifact: {version.ref_id}"
                    )
                artifact_cache[version.ref_id] = content

            start = int(segment.source_byte_start)
            end = int(segment.source_byte_end)
            if start < 0 or end < start or end > len(content):
                raise KnowledgeInvariantError(
                    f"graph projection segment coordinates fall outside canonical artifact: {segment.segment_key}"
                )
            source_slice = content[start:end]
            if sha256(source_slice).hexdigest() != segment.source_slice_sha256:
                raise KnowledgeInvariantError(
                    f"graph projection segment digest does not match canonical artifact: {segment.segment_key}"
                )
            try:
                body = source_slice.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise KnowledgeInvariantError(
                    f"graph projection segment is not strict UTF-8: {segment.segment_key}"
                ) from exc

            observation = source.observation
            decision = source.decision
            identity = observation.binding.source_identity
            compat = source.repository_compatibility
            segments.append(
                GovernedProjectionSourceSegment(
                    generation_id=current.generation_id,
                    resource_version_ref=version.ref_id,
                    source_revision_id=int(version.created_revision_id),
                    segment_key=segment.segment_key,
                    segment_ordinal=int(segment.segment_ordinal),
                    source_slice_sha256=segment.source_slice_sha256,
                    source_byte_start=start,
                    source_byte_end=end,
                    source_line_start=int(segment.source_line_start),
                    source_line_end=int(segment.source_line_end),
                    effective_lifecycle_state=segment.effective_lifecycle_state,
                    source_repository_key=(
                        compat.source_repository_key if compat is not None else None
                    ),
                    source_document_key=(
                        compat.source_document_key if compat is not None else None
                    ),
                    source_path=compat.source_path if compat is not None else None,
                    source_version=(
                        compat.source_version if compat is not None else None
                    ),
                    heading_path=tuple(dict(item) for item in segment.heading_path),
                    reference_time=self._reference_time(source),
                    body=body,
                    governed_source_observation_id=observation.observation_id,
                    governed_observation_digest=observation.digest,
                    governed_decision_id=decision.decision_id,
                    governed_decision_digest=decision.digest,
                    governing_snapshot_digest=source.snapshot_digest,
                    governed_projection_digest=source.projection_digest,
                    source_identity_digest=identity.digest,
                    source_kind=identity.source_kind,
                    origin_scope=identity.origin_scope,
                    collection_key=identity.collection_key,
                    item_key=identity.item_key,
                    project_keys=source.member.project_keys,
                    producer_id=observation.producer_id,
                    producer_version=observation.producer_version,
                    source_observed_at=_utc(observation.observed_at),
                    source_event_time=(
                        _utc(observation.source_event_time)
                        if observation.source_event_time is not None
                        else None
                    ),
                    source_revision_time=(
                        _utc(observation.source_revision_time)
                        if observation.source_revision_time is not None
                        else None
                    ),
                    governance_policy_id=decision.policy_id,
                    governance_rationale=decision.rationale,
                    governance_decided_at=_utc(decision.decided_at),
                    reference_time_policy=SOURCE_NEUTRAL_GRAPH_REFERENCE_TIME_POLICY,
                )
            )

        profile_id, profile_digest = self.graph_projection_profile_identity(current)
        return ProjectionPlan(
            generation_id=current.generation_id,
            profile_id=profile_id,
            profile_digest=profile_digest,
            sources=tuple(sources),
            segments=tuple(segments),
        )

    def projection_plan_for_attempt(self, attempt_id: UUID) -> ProjectionPlan:
        attempt = self.read_projection_attempt(attempt_id)
        current = self._current_sr2_generation()
        if any(
            source.source_ref not in {item.source_ref for item in current.sources}
            for source in attempt.sources
        ):
            raise KnowledgeInvariantError(
                "graph projection attempt is not bound to the current SR-2 generation"
            )
        plan = self.build_sr2_projection_plan(
            resource_version_refs=tuple(source.source_ref for source in attempt.sources),
        )
        if (
            attempt.profile_id != plan.profile_id
            or attempt.profile_digest != plan.profile_digest
        ):
            raise KnowledgeInvariantError(
                "graph projection attempt uses a stale graph-plan/reference-time contract"
            )
        expected_sources = tuple(
            sorted(
                (
                    (source.source_ref, source.source_revision_id)
                    for source in attempt.sources
                ),
                key=lambda item: str(item[0]),
            )
        )
        actual_sources = tuple(sorted(plan.sources, key=lambda item: str(item[0])))
        if expected_sources != actual_sources:
            raise KnowledgeInvariantError(
                "graph projection attempt source revisions no longer match canonical SR-2 evidence"
            )
        return plan

    async def sync_current_sr2_projection(
        self,
        *,
        attempt_id: UUID,
        namespace_key: str,
        scope_key: str,
        adapter: ProjectionAdapter,
        resource_version_refs: tuple[UUID, ...] | None = None,
        max_segments: int = DEFAULT_GRAPH_SYNC_MAX_SEGMENTS,
    ) -> ProjectionExecutionResult:
        if max_segments < 1 or max_segments > MAX_GRAPH_SYNC_SEGMENTS:
            raise KnowledgeInvariantError(
                f"graph sync max_segments must be between 1 and {MAX_GRAPH_SYNC_SEGMENTS}"
            )
        current = self._current_sr2_generation()
        refs = (
            tuple(item.source_ref for item in current.sources)
            if resource_version_refs is None
            else resource_version_refs
        )
        plan = self.build_sr2_projection_plan(resource_version_refs=refs)
        if len(plan.segments) > max_segments:
            raise KnowledgeInvariantError(
                f"graph sync plan has {len(plan.segments)} segments, exceeding max_segments={max_segments}"
            )
        return await super().execute_sr2_projection(
            attempt_id=attempt_id,
            namespace_key=namespace_key,
            scope_key=scope_key,
            resource_version_refs=refs,
            adapter=adapter,
        )

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
        authorized_resource_refs: frozenset[UUID] | None = None,
    ) -> TrustedProjectionSearchSnapshot:
        normalized_query = query.strip()
        if not normalized_query:
            raise KnowledgeInvariantError("graph retrieval query must not be blank")
        if limit < 1 or limit > 50:
            raise KnowledgeInvariantError(
                "graph retrieval limit must be between 1 and 50"
            )
        namespace_key = namespace_key.strip()
        scope_key = scope_key.strip()
        if not namespace_key or not scope_key:
            raise KnowledgeInvariantError(
                "graph retrieval requires explicit namespace and scope"
            )

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
        expected_profile_id, expected_profile_digest = (
            self.graph_projection_profile_identity(current)
        )
        descriptor = adapter.descriptor
        rows = self.session.scalars(
            select(ProjectionAttempt)
            .where(
                ProjectionAttempt.namespace_key == namespace_key,
                ProjectionAttempt.scope_key == scope_key,
                ProjectionAttempt.backend_identity == descriptor.backend_identity,
                ProjectionAttempt.backend_version == descriptor.backend_version,
                ProjectionAttempt.profile_id == expected_profile_id,
                ProjectionAttempt.profile_digest == expected_profile_digest,
                ProjectionAttempt.config_digest == descriptor.config_digest,
                ProjectionAttempt.disposition == ProjectionDisposition.SUCCEEDED.value,
                ProjectionAttempt.validation_state
                == ProjectionValidationState.VALIDATED.value,
            )
            .order_by(ProjectionAttempt.started_at, ProjectionAttempt.attempt_id)
        ).all()
        if descriptor.validation_requirement is not None:
            rows = [
                row
                for row in rows
                if self.projection_satisfies_validation_requirement(
                    attempt_id=row.attempt_id,
                    requirement=descriptor.validation_requirement,
                )
            ]
        if not rows:
            return TrustedProjectionSearchSnapshot(
                query=normalized_query,
                namespace_key=namespace_key,
                scope_key=scope_key,
                generation_id=current.generation_id,
                attempt_ids=(),
                results=(),
            )

        build_correlations: dict[str, dict[str, ProjectionSourceSegment]] = {}
        build_rows: list[tuple[ProjectionAttempt, str]] = []
        attempt_ids: list[UUID] = []
        for row in rows:
            expected_partition = adapter.partition_key(
                namespace_key=namespace_key,
                scope_key=scope_key,
                projection_profile_id=expected_profile_id,
                projection_attempt_id=row.attempt_id,
                adapter_config_digest=descriptor.config_digest,
            )
            plan = self.projection_plan_for_attempt(row.attempt_id)
            bindings = self.read_projection_source_bindings(row.attempt_id)
            segment_by_exact_key = {
                (
                    segment.resource_version_ref,
                    segment.source_revision_id,
                    segment.segment_key,
                    segment.source_slice_sha256,
                ): segment
                for segment in plan.segments
            }
            if len(bindings) != len(segment_by_exact_key):
                raise KnowledgeInvariantError(
                    f"validated graph projection attempt {row.attempt_id} lost provider source bindings"
                )

            attempt_ids.append(row.attempt_id)
            correlation: dict[str, ProjectionSourceSegment] = {}
            matched_exact_keys: set[tuple[UUID, int, str, str]] = set()
            for binding in bindings:
                if binding.provider_partition_key != expected_partition:
                    raise KnowledgeInvariantError(
                        f"validated graph projection attempt {row.attempt_id} points at the wrong provider partition"
                    )
                exact_key = (
                    binding.resource_version_ref,
                    binding.source_revision_id,
                    binding.segment_key,
                    binding.source_slice_sha256,
                )
                segment = segment_by_exact_key.get(exact_key)
                if segment is None:
                    raise KnowledgeInvariantError(
                        f"validated graph projection attempt {row.attempt_id} has an uncorrelated provider binding"
                    )
                matched_exact_keys.add(exact_key)
                existing = correlation.get(binding.provider_source_id)
                if existing is not None and existing != segment:
                    raise KnowledgeInvariantError(
                        "provider source ID collision maps one graph source to different KC segments"
                    )
                correlation[binding.provider_source_id] = segment
            if matched_exact_keys != set(segment_by_exact_key):
                raise KnowledgeInvariantError(
                    f"validated graph projection attempt {row.attempt_id} does not cover every canonical segment"
                )
            build_correlations[expected_partition] = correlation
            build_rows.append((row, expected_partition))

        build_hits = []
        for row, expected_partition in build_rows:
            hits = await adapter.search(
                query=normalized_query,
                namespace_key=namespace_key,
                scope_key=scope_key,
                projection_profile_id=expected_profile_id,
                projection_attempt_id=row.attempt_id,
                adapter_config_digest=descriptor.config_digest,
                limit=limit,
            )
            build_hits.append((expected_partition, hits))

        self.session.expire_all()
        after = self.current_generation(derived_kind=DerivedKind.TEXT)
        if after is None or after.generation_id != current.generation_id:
            raise KnowledgeInvariantError(
                "current SR-2 generation changed during graph retrieval; retry against the new snapshot"
            )

        trusted: list[TrustedProjectionHit] = []
        for expected_partition, hits in build_hits:
            correlation = build_correlations[expected_partition]
            for hit in hits:
                if hit.partition_key != expected_partition:
                    continue
                if not hit.source_correlation_keys:
                    continue
                if any(
                    source_key not in correlation
                    for source_key in hit.source_correlation_keys
                ):
                    continue

                matched: list[ProjectionSourceSegment] = []
                seen_exact: set[tuple[UUID, str]] = set()
                eligible = True
                for source_key in hit.source_correlation_keys:
                    segment = correlation[source_key]
                    version = self.session.get(
                        ResourceVersion,
                        segment.resource_version_ref,
                    )
                    if version is None:
                        eligible = False
                        break
                    if (
                        authorized_resource_refs is not None
                        and version.resource_ref_id not in authorized_resource_refs
                    ):
                        eligible = False
                        break
                    if not self.resource_version_serving_eligible(
                        segment.resource_version_ref
                    ):
                        eligible = False
                        break
                    if segment.effective_lifecycle_state == "superseded":
                        eligible = False
                        break
                    exact = (segment.resource_version_ref, segment.segment_key)
                    if exact not in seen_exact:
                        seen_exact.add(exact)
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
