from __future__ import annotations

from datetime import timezone
from hashlib import sha256
from uuid import UUID

from sqlalchemy import and_, select

from knowledge_core.application.projection_validation import ProjectionValidationKnowledgeKernel
from knowledge_core.application.section_generation import (
    SR2_SEGMENT_MODEL_IDENTITY,
    SR2_SEGMENT_MODEL_VERSION,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.domain.projection_adapter import (
    ProjectionAdapter,
    ProjectionAdapterExecutionError,
    ProjectionAdapterReceipt,
    ProjectionAdapterRequest,
    ProjectionAmbiguousRetryError,
    ProjectionExecutionResult,
    ProjectionPlan,
    ProjectionProviderSourceBinding,
    ProjectionSourceSegment,
)
from knowledge_core.domain.projection_evidence import ProjectionDisposition
from knowledge_core.storage.projection_models import ProjectionAttempt
from knowledge_core.storage.projection_source_models import ProjectionSourceBindingRecord
from knowledge_core.storage.repository_import_models import RepositoryImportReceipt
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.section_retrieval_models import (
    ResourceSegmentTextSearch,
    TextGenerationProfile,
    TextGenerationSource,
)


class ProjectionOrchestrationKnowledgeKernel(ProjectionValidationKnowledgeKernel):
    """Provider-neutral orchestration over the accepted projection evidence ledger."""

    def _current_sr2_generation(self):
        current = self.current_generation(derived_kind=DerivedKind.TEXT)
        if current is None:
            raise KnowledgeInvariantError("Graph projection requires a current SR-2 text generation")
        if (
            current.model_identity != SR2_SEGMENT_MODEL_IDENTITY
            or current.model_version != SR2_SEGMENT_MODEL_VERSION
        ):
            raise KnowledgeInvariantError(
                "Graph projection requires the current text generation to be SR-2"
            )
        if current.config_digest is None:
            raise KnowledgeInvariantError("current SR-2 generation is missing its config digest")
        profile = self.session.get(TextGenerationProfile, current.generation_id)
        if profile is None or profile.generation_config_digest != current.config_digest:
            raise KnowledgeInvariantError("current SR-2 generation/profile identity is not recoverable")
        return current

    def resolve_current_sr2_resource_versions(
        self,
        *,
        source_paths: tuple[str, ...],
    ) -> tuple[UUID, ...]:
        current = self._current_sr2_generation()
        normalized_paths = tuple(dict.fromkeys(path.strip() for path in source_paths if path.strip()))
        if not normalized_paths:
            raise KnowledgeInvariantError("at least one source path is required")
        rows = self.session.execute(
            select(
                ResourceSegmentTextSearch.source_path,
                ResourceSegmentTextSearch.resource_version_ref,
            )
            .where(
                ResourceSegmentTextSearch.generation_id == current.generation_id,
                ResourceSegmentTextSearch.source_path.in_(normalized_paths),
            )
            .distinct()
        ).all()
        by_path: dict[str, set[UUID]] = {}
        for path, resource_version_ref in rows:
            by_path.setdefault(path, set()).add(resource_version_ref)
        missing = [path for path in normalized_paths if path not in by_path]
        ambiguous = [path for path in normalized_paths if len(by_path.get(path, ())) != 1]
        if missing:
            raise KnowledgeInvariantError(
                "source paths are not present in the current SR-2 generation: " + ", ".join(missing)
            )
        if ambiguous:
            raise KnowledgeInvariantError(
                "source paths are ambiguous in the current SR-2 generation: " + ", ".join(ambiguous)
            )
        return tuple(by_path[path].pop() for path in normalized_paths)

    def build_sr2_projection_plan(
        self,
        *,
        resource_version_refs: tuple[UUID, ...],
    ) -> ProjectionPlan:
        current = self._current_sr2_generation()
        normalized_refs = tuple(dict.fromkeys(resource_version_refs))
        if not normalized_refs:
            raise KnowledgeInvariantError("projection requires one or more resource versions")

        lineage_rows = self.session.scalars(
            select(TextGenerationSource).where(
                TextGenerationSource.generation_id == current.generation_id,
                TextGenerationSource.resource_version_ref.in_(normalized_refs),
            )
        ).all()
        lineage_by_ref = {row.resource_version_ref: row for row in lineage_rows}
        missing_lineage = [ref for ref in normalized_refs if ref not in lineage_by_ref]
        if missing_lineage:
            raise KnowledgeInvariantError(
                "resource versions are not governed sources of the current SR-2 generation: "
                + ", ".join(str(ref) for ref in missing_lineage)
            )

        versions: dict[UUID, ResourceVersion] = {}
        sources: list[tuple[UUID, int]] = []
        for resource_version_ref in normalized_refs:
            version = self.session.get(ResourceVersion, resource_version_ref)
            if version is None:
                raise KnowledgeInvariantError(
                    f"unknown projection resource version: {resource_version_ref}"
                )
            if version.content_digest_algo != "sha256":
                raise KnowledgeInvariantError("Graph projection supports only SHA-256 resource versions")
            if not self.resource_version_serving_eligible(resource_version_ref):
                raise KnowledgeInvariantError(
                    f"resource version is not serving-eligible for projection: {resource_version_ref}"
                )
            versions[resource_version_ref] = version
            sources.append((resource_version_ref, int(version.created_revision_id)))

        rows = self.session.execute(
            select(
                ResourceSegmentTextSearch,
                TextGenerationSource,
                RepositoryImportReceipt,
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
                RepositoryImportReceipt,
                RepositoryImportReceipt.manifest_digest
                == TextGenerationSource.governing_manifest_digest,
            )
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
        for segment, _lineage, receipt in rows:
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
                    f"projection segment coordinates fall outside canonical artifact: {segment.segment_key}"
                )
            source_slice = content[start:end]
            if sha256(source_slice).hexdigest() != segment.source_slice_sha256:
                raise KnowledgeInvariantError(
                    f"projection segment digest does not match canonical artifact: {segment.segment_key}"
                )
            try:
                body = source_slice.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise KnowledgeInvariantError(
                    f"projection segment is not strict UTF-8: {segment.segment_key}"
                ) from exc

            reference_time = receipt.created_at
            if reference_time.tzinfo is None:
                reference_time = reference_time.replace(tzinfo=timezone.utc)
            else:
                reference_time = reference_time.astimezone(timezone.utc)

            segments.append(
                ProjectionSourceSegment(
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
                    source_repository_key=segment.source_repository_key,
                    source_document_key=segment.source_document_key,
                    source_path=segment.source_path,
                    source_version=segment.source_version,
                    heading_path=tuple(dict(item) for item in segment.heading_path),
                    reference_time=reference_time,
                    body=body,
                )
            )

        return ProjectionPlan(
            generation_id=current.generation_id,
            profile_id=f"sr2-generation:{current.generation_id}",
            profile_digest=current.config_digest,
            sources=tuple(sources),
            segments=tuple(segments),
        )

    def projection_plan_for_attempt(self, attempt_id: UUID) -> ProjectionPlan:
        attempt = self.read_projection_attempt(attempt_id)
        current = self._current_sr2_generation()
        expected_profile_id = f"sr2-generation:{current.generation_id}"
        if attempt.profile_id != expected_profile_id or attempt.profile_digest != current.config_digest:
            raise KnowledgeInvariantError(
                "projection attempt is not bound to the current SR-2 generation"
            )
        plan = self.build_sr2_projection_plan(
            resource_version_refs=tuple(source.source_ref for source in attempt.sources),
        )
        expected_sources = tuple(
            sorted(
                ((source.source_ref, source.source_revision_id) for source in attempt.sources),
                key=lambda item: str(item[0]),
            )
        )
        actual_sources = tuple(sorted(plan.sources, key=lambda item: str(item[0])))
        if expected_sources != actual_sources:
            raise KnowledgeInvariantError(
                "projection attempt source revisions no longer match canonical SR-2 evidence"
            )
        return plan

    def read_projection_source_bindings(
        self,
        attempt_id: UUID,
    ) -> tuple[ProjectionProviderSourceBinding, ...]:
        rows = self.session.scalars(
            select(ProjectionSourceBindingRecord)
            .where(ProjectionSourceBindingRecord.attempt_id == attempt_id)
            .order_by(
                ProjectionSourceBindingRecord.resource_version_ref,
                ProjectionSourceBindingRecord.segment_key,
            )
        ).all()
        return tuple(
            ProjectionProviderSourceBinding(
                resource_version_ref=row.resource_version_ref,
                source_revision_id=int(row.source_revision_id),
                segment_key=row.segment_key,
                source_slice_sha256=row.source_slice_sha256,
                provider_partition_key=row.provider_partition_key,
                provider_source_id=row.provider_source_id,
            )
            for row in rows
        )

    def _validate_and_stage_source_bindings(
        self,
        *,
        attempt_id: UUID,
        plan: ProjectionPlan,
        receipt: ProjectionAdapterReceipt,
        expected_partition: str,
    ) -> None:
        expected = {
            (
                segment.resource_version_ref,
                segment.segment_key,
                segment.source_slice_sha256,
            ): segment
            for segment in plan.segments
        }
        if len(expected) != len(plan.segments):
            raise KnowledgeInvariantError("projection plan contains duplicate exact segment identities")

        staged: list[ProjectionProviderSourceBinding] = []
        seen_segment_keys: set[tuple[UUID, str, str]] = set()
        seen_provider_ids: set[str] = set()
        for binding in receipt.source_bindings:
            provider_source_id = binding.provider_source_id.strip()
            provider_partition_key = binding.provider_partition_key.strip()
            if not provider_source_id or not provider_partition_key:
                raise KnowledgeInvariantError("projection provider source bindings must be non-empty")
            if provider_partition_key != expected_partition:
                raise KnowledgeInvariantError(
                    "projection provider source binding was returned for the wrong physical partition"
                )
            key = (
                binding.resource_version_ref,
                binding.segment_key,
                binding.source_slice_sha256,
            )
            segment = expected.get(key)
            if segment is None:
                raise KnowledgeInvariantError(
                    "projection provider source binding does not match a planned canonical segment"
                )
            if binding.source_revision_id != segment.source_revision_id:
                raise KnowledgeInvariantError(
                    "projection provider source binding changed the canonical source revision"
                )
            if key in seen_segment_keys:
                raise KnowledgeInvariantError(
                    "projection adapter returned duplicate provider bindings for one canonical segment"
                )
            if provider_source_id in seen_provider_ids:
                raise KnowledgeInvariantError(
                    "projection adapter reused one provider source ID for multiple canonical segments"
                )
            seen_segment_keys.add(key)
            seen_provider_ids.add(provider_source_id)
            staged.append(binding)

        if receipt.disposition is ProjectionDisposition.SUCCEEDED and seen_segment_keys != set(expected):
            missing = len(set(expected) - seen_segment_keys)
            raise KnowledgeInvariantError(
                f"successful projection receipt is missing {missing} canonical segment binding(s)"
            )

        captured_at = self._now()
        for binding in staged:
            self.session.add(
                ProjectionSourceBindingRecord(
                    attempt_id=attempt_id,
                    resource_version_ref=binding.resource_version_ref,
                    source_revision_id=binding.source_revision_id,
                    segment_key=binding.segment_key,
                    source_slice_sha256=binding.source_slice_sha256,
                    provider_partition_key=binding.provider_partition_key,
                    provider_source_id=binding.provider_source_id,
                    captured_at=captured_at,
                )
            )

    async def execute_sr2_projection(
        self,
        *,
        attempt_id: UUID,
        namespace_key: str,
        scope_key: str,
        resource_version_refs: tuple[UUID, ...],
        adapter: ProjectionAdapter,
    ) -> ProjectionExecutionResult:
        plan = self.build_sr2_projection_plan(resource_version_refs=resource_version_refs)
        descriptor = adapter.descriptor
        for name, value in (
            ("backend_identity", descriptor.backend_identity),
            ("adapter_identity", descriptor.adapter_identity),
            ("config_digest", descriptor.config_digest),
        ):
            if not value.strip():
                raise KnowledgeInvariantError(f"projection adapter {name} must not be empty")

        existing = self.session.get(ProjectionAttempt, attempt_id)
        attempt = self.start_projection_attempt(
            attempt_id=attempt_id,
            projection_kind="semantic_relationship_graph",
            target_kind="sr2_segment_relationship_graph",
            namespace_key=namespace_key,
            scope_key=scope_key,
            backend_identity=descriptor.backend_identity,
            backend_version=descriptor.backend_version,
            profile_id=plan.profile_id,
            profile_digest=plan.profile_digest,
            config_digest=descriptor.config_digest,
            sources=plan.sources,
        )

        if existing is not None:
            if attempt.disposition is ProjectionDisposition.PENDING:
                raise ProjectionAmbiguousRetryError(
                    f"projection attempt {attempt_id} is still pending; external side effects may already exist"
                )
            return ProjectionExecutionResult(
                attempt=attempt,
                receipt=None,
                projected_segment_count=len(plan.segments),
                replayed=True,
            )

        if not plan.segments:
            receipt = ProjectionAdapterReceipt(
                disposition=ProjectionDisposition.INCOMPLETE,
                warnings=("current SR-2 sources contain no serving-eligible non-superseded segments",),
            )
            settled = self.settle_projection_attempt(
                attempt_id=attempt_id,
                disposition=receipt.disposition,
                warnings=receipt.warnings,
                errors=receipt.errors,
            )
            return ProjectionExecutionResult(
                attempt=settled,
                receipt=receipt,
                projected_segment_count=0,
                replayed=False,
            )

        expected_partition = adapter.partition_key(
            namespace_key=namespace_key,
            scope_key=scope_key,
            projection_profile_id=plan.profile_id,
        )
        try:
            receipt = await adapter.project(
                ProjectionAdapterRequest(attempt=attempt, segments=plan.segments)
            )
            if receipt.disposition is ProjectionDisposition.PENDING:
                raise KnowledgeInvariantError("projection adapter cannot return a pending receipt")
            self._validate_and_stage_source_bindings(
                attempt_id=attempt_id,
                plan=plan,
                receipt=receipt,
                expected_partition=expected_partition,
            )
        except Exception as exc:
            settled = self.settle_projection_attempt(
                attempt_id=attempt_id,
                disposition=ProjectionDisposition.QUARANTINED,
                errors=(f"{type(exc).__name__}: {exc}",),
            )
            raise ProjectionAdapterExecutionError(
                f"projection adapter failed; attempt {settled.attempt_id} was quarantined"
            ) from exc

        settled = self.settle_projection_attempt(
            attempt_id=attempt_id,
            disposition=receipt.disposition,
            warnings=receipt.warnings,
            errors=receipt.errors,
        )
        return ProjectionExecutionResult(
            attempt=settled,
            receipt=receipt,
            projected_segment_count=len(plan.segments),
            replayed=False,
        )
