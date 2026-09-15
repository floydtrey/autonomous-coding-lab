from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from hashlib import sha1, sha256
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.application.source_neutral_graph import (
    SourceNeutralGraphProjectionKnowledgeKernel,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.authority.retrieval import RetrievalAuthorityDecision
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.projection_adapter import (
    ProjectionAdapterDescriptor,
    ProjectionAdapterExecutionError,
    ProjectionAdapterReceipt,
    ProjectionLifecycleInventory,
    ProjectionProviderSourceBinding,
    ProjectionSearchHit,
)
from knowledge_core.domain.projection_evidence import ProjectionDisposition
from knowledge_core.domain.projection_validation import (
    ProjectionCheckOutcome,
    ProjectionValidationCheck,
    ProjectionValidationOutcome,
    ProjectionValidationReport,
    ProjectionValidatorDescriptor,
)
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.domain.source_neutral_projection import (
    GovernedProjectionSourceSegment,
    SOURCE_NEUTRAL_GRAPH_REFERENCE_TIME_POLICY,
)
from knowledge_core.storage.database import create_database_engine, create_session_factory


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_BOOTSTRAP_KEY = "task4-bootstrap-key"


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("Task 4 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("Task 4 requires PostgreSQL")
    return engine


def _truncate_kernel_tables(engine) -> None:
    inspector = inspect(engine)
    preparer = engine.dialect.identifier_preparer
    tables: list[str] = []
    for schema in ("kc", "kc_control", "kc_derived"):
        for table_name in inspector.get_table_names(schema=schema):
            tables.append(
                f"{preparer.quote_schema(schema)}.{preparer.quote(table_name)}"
            )
    if not tables:
        raise AssertionError("Knowledge Core schemas are not migrated")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"
        )


@pytest.fixture()
def task4_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


class FakeRepositoryReader:
    def __init__(self):
        self.repository_locator = "memory://task4-repository"
        self.objects: dict[tuple[str, str], bytes] = {}

    def put(self, commit: str, path: str, content: bytes) -> None:
        self.objects[(commit, path)] = content

    def read_exact(self, *, source_commit: str, path: str) -> RepositorySourceProof:
        content = self.objects[(source_commit, path)]
        digest = sha1()
        digest.update(f"blob {len(content)}\0".encode("ascii"))
        digest.update(content)
        return RepositorySourceProof(
            source_commit=source_commit,
            path=path,
            git_blob_sha=digest.hexdigest(),
            content=content,
            object_mode="100644",
            object_type="blob",
        )


def _repository_manifest(commit: str, content: bytes) -> dict:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return {
        "schema_version": 2,
        "manifest_id": "task4-repository-A",
        "source_repository_key": "repo-task4",
        "repository_locator": "memory://task4-repository",
        "source_commit": commit,
        "previous_manifest_digest": None,
        "history_policy": "retain_prior_versions_as_superseded",
        "entries": [
            {
                "source_document_key": "repo-alpha",
                "path": "alpha.md",
                "git_blob_sha": digest.hexdigest(),
                "media_type": "text/markdown",
                "classification": "approved",
                "retrieval_lifecycle": "current",
                "authority_rank": 5,
                "rationale": "Task 4 repository fixture",
            }
        ],
        "retirements": [],
    }


def _seed_repository(sessions, store) -> None:
    commit = "4" * 40
    content = b"# Repository Alpha\nrepository papaya graph evidence signal\n"
    reader = FakeRepositoryReader()
    reader.put(commit, "alpha.md", content)
    session = sessions()
    try:
        importer = SectionRepositoryImportKnowledgeKernel(
            session,
            artifact_store=store,
            source_readers={"repo-task4": reader},
        )
        manifest = _repository_manifest(commit, content)
        plan = importer.plan_repository_import(manifest)
        receipt = importer.apply_repository_import(
            manifest=manifest,
            expected_plan_digest=plan.plan_digest,
        )
        assert receipt.status == "settled"
    finally:
        session.close()


def _app(sessions, store):
    return create_app(
        session_factory=sessions,
        artifact_store=store,
        bootstrap_admission=BootstrapAdmission(
            contract=BootstrapContract(), api_key=_BOOTSTRAP_KEY
        ),
    )


class FakeGraphAdapter:
    def __init__(self, *, fail_projection: bool = False):
        self.fail_projection = fail_projection
        self.project_calls = 0
        self.search_calls = 0
        self.projected: dict[UUID, tuple[GovernedProjectionSourceSegment, ...]] = {}

    @property
    def descriptor(self) -> ProjectionAdapterDescriptor:
        return ProjectionAdapterDescriptor(
            backend_identity="task4-fake-graph",
            backend_version="1",
            adapter_identity="task4-source-neutral-adapter",
            adapter_version="1",
            config_digest="sha256:task4-fake-adapter-config-v1",
        )

    def partition_key(
        self,
        *,
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
        projection_attempt_id: UUID,
        adapter_config_digest: str,
    ) -> str:
        payload = "|".join(
            (
                namespace_key,
                scope_key,
                projection_profile_id,
                str(projection_attempt_id),
                adapter_config_digest,
            )
        )
        return "task4_" + sha256(payload.encode("utf-8")).hexdigest()[:24]

    async def project(self, request):
        self.project_calls += 1
        if self.fail_projection:
            raise RuntimeError("task4 simulated provider failure")
        segments = tuple(request.segments)
        assert all(
            isinstance(segment, GovernedProjectionSourceSegment)
            for segment in segments
        )
        self.projected[request.attempt.attempt_id] = segments
        partition = self.partition_key(
            namespace_key=request.attempt.namespace_key,
            scope_key=request.attempt.scope_key,
            projection_profile_id=request.attempt.profile_id or "",
            projection_attempt_id=request.attempt.attempt_id,
            adapter_config_digest=self.descriptor.config_digest,
        )
        bindings = tuple(
            ProjectionProviderSourceBinding(
                resource_version_ref=segment.resource_version_ref,
                source_revision_id=segment.source_revision_id,
                segment_key=segment.segment_key,
                source_slice_sha256=segment.source_slice_sha256,
                provider_partition_key=partition,
                provider_source_id=f"task4-source:{index}:{segment.segment_key}",
            )
            for index, segment in enumerate(segments)
        )
        return ProjectionAdapterReceipt(
            disposition=ProjectionDisposition.SUCCEEDED,
            episode_count=len(segments),
            source_bindings=bindings,
        )

    async def search(
        self,
        *,
        query: str,
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
        projection_attempt_id: UUID,
        adapter_config_digest: str,
        limit: int,
    ):
        self.search_calls += 1
        segments = self.projected[projection_attempt_id]
        note_index, note = next(
            (index, segment)
            for index, segment in enumerate(segments)
            if segment.source_kind == "local.user-note"
        )
        partition = self.partition_key(
            namespace_key=namespace_key,
            scope_key=scope_key,
            projection_profile_id=projection_profile_id,
            projection_attempt_id=projection_attempt_id,
            adapter_config_digest=adapter_config_digest,
        )
        return (
            ProjectionSearchHit(
                provider_hit_id="task4-hit-note",
                partition_key=partition,
                fact="Mason is the local MindsHub worker model.",
                source_correlation_keys=(
                    f"task4-source:{note_index}:{note.segment_key}",
                ),
            ),
        )[:limit]

    async def existing_source_keys(self, **_kwargs):
        return frozenset()

    async def lifecycle_inventory(
        self,
        *,
        namespace_key: str,
        scope_key: str,
        projection_profile_id: str,
        projection_attempt_id: UUID,
        adapter_config_digest: str,
    ):
        return ProjectionLifecycleInventory(
            partition_key=self.partition_key(
                namespace_key=namespace_key,
                scope_key=scope_key,
                projection_profile_id=projection_profile_id,
                projection_attempt_id=projection_attempt_id,
                adapter_config_digest=adapter_config_digest,
            ),
            complete=True,
            edges=(),
        )


class FakeValidator:
    @property
    def descriptor(self):
        return ProjectionValidatorDescriptor(
            validator_identity="task4-independent-validator",
            validator_version="1",
            ruleset_id="task4-source-neutral-graph-v1",
            ruleset_digest="sha256:task4-validator-rules-v1",
        )

    def validate(self, _attempt):
        return ProjectionValidationReport(
            outcome=ProjectionValidationOutcome.VALIDATED,
            checks=(
                ProjectionValidationCheck(
                    check_code="mixed-source-correlation",
                    outcome=ProjectionCheckOutcome.PASSED,
                    evidence={"mixed_source_correlation": True},
                ),
            ),
        )


class AllowGraphAuthority:
    def evaluate_retrieval(self, _request):
        return RetrievalAuthorityDecision(
            allowed=True,
            decision_ref="task4-authority",
            reason_code="task4-test-allow",
        )


@pytest.mark.postgresql
def test_task4_mixed_source_bounded_sync_validation_and_failure_isolation(
    task4_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task4_engine)
    store = LocalArtifactStore(tmp_path / "task4-artifacts")
    _seed_repository(sessions, store)

    event_time = "2026-09-10T12:34:56+00:00"
    with TestClient(_app(sessions, store)) as client:
        stored = client.post(
            "/v1/kc/store",
            json={
                "content": "Mason is my local MindsHub worker model. task4 cobalt graph signal\n",
                "project": "local-ai",
                "source_type": "user_note",
                "source_id": "mason-task4",
                "source_event_time": event_time,
            },
            headers={
                "X-Knowledge-Key": _BOOTSTRAP_KEY,
                "Idempotency-Key": "task4-mason-note-1",
            },
        )
        assert stored.status_code == 201, stored.text
        stored_data = stored.json()
        assert stored_data["text_state"] == "indexed"

    session = sessions()
    try:
        kernel = SourceNeutralGraphProjectionKnowledgeKernel(
            session,
            artifact_store=store,
        )
        current = kernel._current_sr2_generation()
        refs = tuple(item.source_ref for item in current.sources)
        plan = kernel.build_sr2_projection_plan(resource_version_refs=refs)
        assert plan.profile_id.startswith("sr2-governed-graph:")
        assert plan.profile_digest.startswith("sha256:")
        assert len(plan.segments) >= 2
        assert all(
            isinstance(segment, GovernedProjectionSourceSegment)
            for segment in plan.segments
        )
        assert {segment.source_kind for segment in plan.segments} == {
            "git.repository-document",
            "local.user-note",
        }

        note_segment = next(
            segment
            for segment in plan.segments
            if segment.source_kind == "local.user-note"
        )
        repo_segment = next(
            segment
            for segment in plan.segments
            if segment.source_kind == "git.repository-document"
        )
        assert note_segment.source_repository_key is None
        assert note_segment.source_document_key is None
        assert note_segment.source_path is None
        assert note_segment.source_version is None
        assert note_segment.item_key == "mason-task4"
        assert note_segment.project_keys == ("local-ai",)
        assert note_segment.reference_time == datetime.fromisoformat(event_time)
        assert (
            note_segment.reference_time_policy
            == SOURCE_NEUTRAL_GRAPH_REFERENCE_TIME_POLICY
        )
        assert repo_segment.source_repository_key == "repo-task4"
        assert repo_segment.source_document_key == "repo-alpha"
        assert repo_segment.source_path == "alpha.md"
        assert repo_segment.source_version == "4" * 40
        assert repo_segment.governed_source_observation_id
        assert repo_segment.governing_snapshot_digest == note_segment.governing_snapshot_digest

        bounded_adapter = FakeGraphAdapter()
        bounded_attempt = uuid4()
        with pytest.raises(KnowledgeInvariantError, match="exceeding max_segments=1"):
            asyncio.run(
                kernel.sync_current_sr2_projection(
                    attempt_id=bounded_attempt,
                    namespace_key="kc:task4-test",
                    scope_key="project:knowledge-core",
                    adapter=bounded_adapter,
                    max_segments=1,
                )
            )
        assert bounded_adapter.project_calls == 0
        with pytest.raises(KnowledgeInvariantError, match="unknown projection attempt"):
            kernel.read_projection_attempt(bounded_attempt)

        adapter = FakeGraphAdapter()
        attempt_id = uuid4()
        execution = asyncio.run(
            kernel.sync_current_sr2_projection(
                attempt_id=attempt_id,
                namespace_key="kc:task4-test",
                scope_key="project:knowledge-core",
                adapter=adapter,
                max_segments=10,
            )
        )
        assert execution.attempt.disposition is ProjectionDisposition.SUCCEEDED
        assert execution.projected_segment_count == len(plan.segments)
        assert adapter.project_calls == 1

        unvalidated = asyncio.run(
            kernel.search_validated_projection(
                adapter=adapter,
                authority_evaluator=AllowGraphAuthority(),
                caller_principal_ref="task4-test",
                namespace_key="kc:task4-test",
                scope_key="project:knowledge-core",
                query="Mason",
            )
        )
        assert unvalidated.results == ()
        assert adapter.search_calls == 0

        validation = kernel.validate_projection_attempt(
            validation_id=uuid4(),
            attempt_id=attempt_id,
            validator=FakeValidator(),
            config_digest="sha256:task4-independent-validation-config",
        )
        assert validation.outcome is ProjectionValidationOutcome.VALIDATED

        trusted = asyncio.run(
            kernel.search_validated_projection(
                adapter=adapter,
                authority_evaluator=AllowGraphAuthority(),
                caller_principal_ref="task4-test",
                namespace_key="kc:task4-test",
                scope_key="project:knowledge-core",
                query="Mason",
            )
        )
        assert len(trusted.results) == 1
        trusted_source = trusted.results[0].sources[0]
        assert isinstance(trusted_source, GovernedProjectionSourceSegment)
        assert trusted_source.source_kind == "local.user-note"
        assert trusted_source.item_key == "mason-task4"
        assert trusted_source.resource_version_ref == UUID(stored_data["version_id"])
        assert trusted_source.governed_source_observation_id
        assert trusted_source.governed_observation_digest.startswith("sha256:")
        assert trusted_source.governed_decision_digest.startswith("sha256:")
        assert trusted_source.governed_projection_digest.startswith("sha256:")
        assert trusted_source.governing_snapshot_digest

        generation_before_failure = current.generation_id
        failing_adapter = FakeGraphAdapter(fail_projection=True)
        failed_attempt = uuid4()
        with pytest.raises(ProjectionAdapterExecutionError):
            asyncio.run(
                kernel.sync_current_sr2_projection(
                    attempt_id=failed_attempt,
                    namespace_key="kc:task4-failure",
                    scope_key="project:knowledge-core",
                    adapter=failing_adapter,
                    max_segments=10,
                )
            )
        failed = kernel.read_projection_attempt(failed_attempt)
        assert failed.disposition is ProjectionDisposition.QUARANTINED
        assert (
            kernel._current_sr2_generation().generation_id
            == generation_before_failure
        )
        lexical = RetrievalServiceKnowledgeKernel(session, artifact_store=store)
        assert lexical.search_text(query="task4 cobalt graph signal").results
    finally:
        session.close()
