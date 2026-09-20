from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha1, sha256
import os
from pathlib import Path
from uuid import UUID, uuid5

import pytest
from sqlalchemy import inspect, select

from knowledge_core.application.governed_source_evidence import (
    GovernedSourceEvidenceKnowledgeKernel,
)
from knowledge_core.application.resources import ResourceKnowledgeKernel
from knowledge_core.application.section_publication_v2 import (
    SourceNeutralSectionPublicationKnowledgeKernel,
)
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind, GenerationStatus
from knowledge_core.domain.governed_sources import (
    GovernedRetrievalSnapshot,
    GovernedSnapshotMember,
    GovernedSourceBinding,
    GovernedSourceDecision,
    GovernedSourceIdentity,
    GovernedSourceObservation,
    SourceEvidenceRef,
)
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.domain.retrieval import RetrievalLifecycleState
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.governed_source_models import LegacyRepositorySnapshotMap
from knowledge_core.storage.section_retrieval_models import (
    ResourceSegmentTextSearch,
    TextGenerationSource,
)


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_NOTE_NAMESPACE = UUID("b70f5e84-6004-5ab6-ad99-d537767a4aa9")
_DECISION_NAMESPACE = UUID("570e2e94-48fc-5003-95ca-b4c6a3918d6a")
_NOW = datetime(2026, 9, 15, 4, 30, tzinfo=timezone.utc)


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("Task 2D PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("Task 2D requires PostgreSQL")
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
def task2d_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _persist_note_member(
    *,
    session,
    store: LocalArtifactStore,
    item_key: str,
    content: bytes,
) -> GovernedSnapshotMember:
    resources = ResourceKnowledgeKernel(session, artifact_store=store)
    foundation = resources.bootstrap_resource_test_profile()
    resource = resources.create_resource(
        kind_revision_ref=foundation.artifact_kind_revision_ref
    )
    version = resources.ingest_resource_version(
        resource_ref=resource.resource_ref,
        content=content,
        ingestion_kind_revision_ref=foundation.resource_ingestion_kind_revision_ref,
        media_type="text/plain",
    )
    observation = GovernedSourceObservation(
        observation_id=uuid5(_NOTE_NAMESPACE, item_key),
        binding=GovernedSourceBinding(
            source_identity=GovernedSourceIdentity(
                source_kind="local.user-note",
                origin_scope="local_owner",
                collection_key="task2d-notes",
                item_key=item_key,
            ),
            resource_ref=resource.resource_ref,
        ),
        resource_version_ref=version.resource_version_ref,
        producer_id="kc.task2d-fixture",
        producer_version="1",
        evidence=(
            SourceEvidenceRef(
                evidence_kind="local.authenticated-submission",
                evidence_ref=f"task2d:{item_key}",
                evidence_digest="sha256:" + sha256(content).hexdigest(),
            ),
        ),
        observed_at=_NOW,
    )
    decision = GovernedSourceDecision(
        decision_id=uuid5(_DECISION_NAMESPACE, item_key),
        observation_id=observation.observation_id,
        policy_id="kc-task2d-test-governance-v1",
        classification="approved",
        retrieval_lifecycle=RetrievalLifecycleState.CURRENT,
        authority_rank=10,
        rationale="Task 2D source-neutral fixture",
        decided_at=_NOW,
    )
    evidence = GovernedSourceEvidenceKnowledgeKernel(session)
    evidence.persist_observation(observation)
    evidence.persist_decision(decision)
    return GovernedSnapshotMember.from_selection(
        observation=observation,
        decision=decision,
        project_keys=("knowledge-core",),
    )


def _persist_snapshot(
    *,
    session,
    members: tuple[GovernedSnapshotMember, ...],
    predecessor: str | None = None,
) -> GovernedRetrievalSnapshot:
    snapshot = GovernedRetrievalSnapshot(
        selection_policy_id="kc-task2d-test-complete-corpus-v1",
        created_at=_NOW,
        members=members,
        predecessor_snapshot_digest=predecessor,
    )
    GovernedSourceEvidenceKnowledgeKernel(session).persist_snapshot(snapshot)
    session.commit()
    return snapshot


def _publish_snapshot(publication, snapshot, predecessor):
    candidate = publication.build_segment_generation_candidate(
        governing_snapshot_digest=snapshot.digest
    )
    return publication.promote_segment_generation(
        generation_id=candidate.generation_id,
        governing_snapshot_digest=snapshot.digest,
        expected_predecessor_snapshot_digest=predecessor,
    )


def _current_generation_id(session):
    return session.scalar(
        select(DerivedGeneration.generation_id).where(
            DerivedGeneration.derived_kind == DerivedKind.TEXT.value,
            DerivedGeneration.status == GenerationStatus.CURRENT.value,
        )
    )


def _git_blob_sha(content: bytes) -> str:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


class FakeRepositoryReader:
    def __init__(self):
        self.repository_locator = "memory://task2d-repository"
        self.objects: dict[tuple[str, str], bytes] = {}

    def put(self, commit: str, path: str, content: bytes) -> None:
        self.objects[(commit, path)] = content

    def read_exact(self, *, source_commit: str, path: str) -> RepositorySourceProof:
        content = self.objects[(source_commit, path)]
        return RepositorySourceProof(
            source_commit=source_commit,
            path=path,
            git_blob_sha=_git_blob_sha(content),
            content=content,
            object_mode="100644",
            object_type="blob",
        )


def _manifest(commit: str, content: bytes) -> dict:
    return {
        "schema_version": 2,
        "manifest_id": "task2d-repository-A",
        "source_repository_key": "repo-task2d",
        "repository_locator": "memory://task2d-repository",
        "source_commit": commit,
        "previous_manifest_digest": None,
        "history_policy": "retain_prior_versions_as_superseded",
        "entries": [
            {
                "source_document_key": "repo-alpha",
                "path": "alpha.md",
                "git_blob_sha": _git_blob_sha(content),
                "media_type": "text/markdown",
                "classification": "approved",
                "retrieval_lifecycle": "current",
                "authority_rank": 5,
                "rationale": "Task 2D verified repository fixture",
            }
        ],
        "retirements": [],
    }


@pytest.mark.postgresql
def test_task2d_schema_keeps_repository_provenance_optional(task2d_engine):
    inspector = inspect(task2d_engine)
    lineage = {
        item["name"]: item
        for item in inspector.get_columns(
            "text_generation_source",
            schema="kc_derived",
        )
    }
    for column in (
        "governed_observation_id",
        "governed_decision_id",
        "governing_snapshot_digest",
        "governed_projection_digest",
    ):
        assert column in lineage
        assert lineage[column]["nullable"] is True
    for column in (
        "source_observation_id",
        "governing_manifest_digest",
        "projection_snapshot_digest",
    ):
        assert lineage[column]["nullable"] is True

    segments = {
        item["name"]: item
        for item in inspector.get_columns(
            "resource_segment_text_search",
            schema="kc_derived",
        )
    }
    for column in (
        "repository",
        "source_repository_key",
        "source_document_key",
        "source_path",
        "source_version",
    ):
        assert segments[column]["nullable"] is True


@pytest.mark.postgresql
def test_task2d_non_git_snapshot_builds_and_publishes_without_fake_git_proof(
    task2d_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task2d_engine)
    session = sessions()
    store = LocalArtifactStore(tmp_path / "non-git-artifacts")
    try:
        member = _persist_note_member(
            session=session,
            store=store,
            item_key="mason-note",
            content=b"Mason source-neutral kiwi signal.\n",
        )
        snapshot = _persist_snapshot(session=session, members=(member,))
        publication = SourceNeutralSectionPublicationKnowledgeKernel(
            session,
            artifact_store=store,
        )
        current = _publish_snapshot(publication, snapshot, None)
        assert current.status is GenerationStatus.CURRENT
        assert publication.current_serving_snapshot_digest() == snapshot.digest

        lineage = session.scalars(
            select(TextGenerationSource).where(
                TextGenerationSource.generation_id == current.generation_id
            )
        ).one()
        assert lineage.governed_observation_id == member.observation_id
        assert lineage.governed_decision_id == member.decision_id
        assert lineage.governing_snapshot_digest == snapshot.digest
        assert lineage.governed_projection_digest.startswith("sha256:")
        assert lineage.source_observation_id is None
        assert lineage.governing_manifest_digest is None
        assert lineage.projection_snapshot_digest is None

        segment = session.scalars(
            select(ResourceSegmentTextSearch).where(
                ResourceSegmentTextSearch.generation_id == current.generation_id
            )
        ).one()
        assert segment.repository is None
        assert segment.source_repository_key is None
        assert segment.source_document_key is None
        assert segment.source_path is None
        assert segment.source_version is None
    finally:
        session.close()


@pytest.mark.postgresql
def test_task2d_repository_update_preserves_other_producer_member(
    task2d_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task2d_engine)
    session = sessions()
    store = LocalArtifactStore(tmp_path / "mixed-artifacts")
    try:
        note_member = _persist_note_member(
            session=session,
            store=store,
            item_key="persistent-note",
            content=b"independent note mango signal\n",
        )
        note_snapshot = _persist_snapshot(session=session, members=(note_member,))
        publication = SourceNeutralSectionPublicationKnowledgeKernel(
            session,
            artifact_store=store,
        )
        _publish_snapshot(publication, note_snapshot, None)

        commit = "a" * 40
        repository_content = b"# Repository Alpha\nrepository papaya signal\n"
        reader = FakeRepositoryReader()
        reader.put(commit, "alpha.md", repository_content)
        importer = SectionRepositoryImportKnowledgeKernel(
            session,
            artifact_store=store,
            source_readers={"repo-task2d": reader},
        )
        manifest = _manifest(commit, repository_content)
        plan = importer.plan_repository_import(manifest)
        receipt = importer.apply_repository_import(
            manifest=manifest,
            expected_plan_digest=plan.plan_digest,
        )
        assert receipt.status == "settled"

        mapping = session.get(LegacyRepositorySnapshotMap, receipt.manifest_digest)
        assert mapping is not None
        mixed = GovernedSourceEvidenceKnowledgeKernel(session).load_snapshot(
            mapping.snapshot_digest
        )
        assert mixed.predecessor_snapshot_digest == note_snapshot.digest
        assert len(mixed.members) == 2
        assert note_member in mixed.members
        assert publication.current_serving_snapshot_digest() == mixed.digest

        lineages = session.scalars(
            select(TextGenerationSource).where(
                TextGenerationSource.generation_id
                == receipt.resulting_text_generation_id
            )
        ).all()
        assert len(lineages) == 2
        assert {item.governing_snapshot_digest for item in lineages} == {mixed.digest}
        assert sum(item.source_observation_id is None for item in lineages) == 1
        assert sum(item.source_observation_id is not None for item in lineages) == 1

        repository_hit = importer.search_text(query="papaya")
        assert repository_hit.results
        assert repository_hit.results[0].source_path == "alpha.md"
    finally:
        session.close()


@pytest.mark.postgresql
def test_task2d_stale_predecessor_cannot_displace_newer_complete_snapshot(
    task2d_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task2d_engine)
    session = sessions()
    store = LocalArtifactStore(tmp_path / "predecessor-artifacts")
    try:
        member_a = _persist_note_member(
            session=session,
            store=store,
            item_key="A",
            content=b"snapshot A apple\n",
        )
        snapshot_a = _persist_snapshot(session=session, members=(member_a,))
        publication = SourceNeutralSectionPublicationKnowledgeKernel(
            session,
            artifact_store=store,
        )
        _publish_snapshot(publication, snapshot_a, None)

        member_b = _persist_note_member(
            session=session,
            store=store,
            item_key="B",
            content=b"snapshot B banana\n",
        )
        snapshot_b = _persist_snapshot(
            session=session,
            members=(member_a, member_b),
            predecessor=snapshot_a.digest,
        )
        member_c = _persist_note_member(
            session=session,
            store=store,
            item_key="C",
            content=b"snapshot C cherry\n",
        )
        snapshot_c = _persist_snapshot(
            session=session,
            members=(member_a, member_c),
            predecessor=snapshot_a.digest,
        )

        candidate_b = publication.build_segment_generation_candidate(
            governing_snapshot_digest=snapshot_b.digest
        )
        candidate_c = publication.build_segment_generation_candidate(
            governing_snapshot_digest=snapshot_c.digest
        )
        published_b = publication.promote_segment_generation(
            generation_id=candidate_b.generation_id,
            governing_snapshot_digest=snapshot_b.digest,
            expected_predecessor_snapshot_digest=snapshot_a.digest,
        )
        assert publication.current_serving_snapshot_digest() == snapshot_b.digest

        with pytest.raises(
            KnowledgeInvariantError,
            match="serving governed snapshot changed before publication",
        ):
            publication.promote_segment_generation(
                generation_id=candidate_c.generation_id,
                governing_snapshot_digest=snapshot_c.digest,
                expected_predecessor_snapshot_digest=snapshot_a.digest,
            )

        assert _current_generation_id(session) == published_b.generation_id
        assert publication.current_serving_snapshot_digest() == snapshot_b.digest
        stale_c = publication._generation_kernel().read_generation(
            candidate_c.generation_id
        )
        assert stale_c.status is GenerationStatus.STALE
    finally:
        session.close()
