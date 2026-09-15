from __future__ import annotations

from hashlib import sha1, sha256
import os
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.application.governed_source_evidence import (
    GovernedSourceEvidenceKnowledgeKernel,
)
from knowledge_core.application.section_publication_v2 import (
    SourceNeutralSectionPublicationKnowledgeKernel,
)
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.storage.control_models import Operation
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.governed_source_models import (
    GovernedSourceDecisionRecord,
    GovernedSourceObservationRecord,
)
from knowledge_core.storage.resource_models import Resource, ResourceVersion
from knowledge_core.storage.section_retrieval_models import (
    ResourceSegmentTextSearch,
    TextGenerationSource,
)


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_BOOTSTRAP_KEY = "task2e-bootstrap-key"


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("Task 2E PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("Task 2E requires PostgreSQL")
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
def task2e_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _admission() -> BootstrapAdmission:
    return BootstrapAdmission(
        contract=BootstrapContract(),
        api_key=_BOOTSTRAP_KEY,
    )


def _store_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Knowledge-Key": _BOOTSTRAP_KEY,
        "Idempotency-Key": idempotency_key,
    }


def _store_body(
    content: str,
    *,
    source_id: str = "mason-note",
    project: str = "local-ai",
) -> dict[str, str]:
    return {
        "content": content,
        "project": project,
        "source_type": "user_note",
        "source_id": source_id,
    }


def _make_app(sessions, store):
    return create_app(
        session_factory=sessions,
        artifact_store=store,
        bootstrap_admission=_admission(),
    )


def _current_generation_id(session) -> UUID | None:
    from knowledge_core.domain.generations import DerivedKind, GenerationStatus
    from knowledge_core.storage.generation_models import DerivedGeneration

    return session.scalar(
        select(DerivedGeneration.generation_id).where(
            DerivedGeneration.derived_kind == DerivedKind.TEXT.value,
            DerivedGeneration.status == GenerationStatus.CURRENT.value,
        )
    )


class FakeRepositoryReader:
    def __init__(self):
        self.repository_locator = "memory://task2e-repository"
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
        "manifest_id": "task2e-repository-A",
        "source_repository_key": "repo-task2e",
        "repository_locator": "memory://task2e-repository",
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
                "rationale": "Task 2E repository compatibility fixture",
            }
        ],
        "retirements": [],
    }


@pytest.mark.postgresql
def test_task2e_kc_store_auth_idempotency_and_app_reconstruction(
    task2e_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task2e_engine)
    store = LocalArtifactStore(tmp_path / "task2e-auth-artifacts")
    app = _make_app(sessions, store)
    body = _store_body("Mason direct note kiwi signal.\n")

    with TestClient(app) as client:
        missing = client.post(
            "/v1/kc/store",
            json=body,
            headers={"Idempotency-Key": "mason-1"},
        )
        assert missing.status_code == 401
        wrong = client.post(
            "/v1/kc/store",
            json=body,
            headers={
                "X-Knowledge-Key": "wrong",
                "Idempotency-Key": "mason-1",
            },
        )
        assert wrong.status_code == 401

        first = client.post(
            "/v1/kc/store",
            json=body,
            headers={
                **_store_headers("mason-1"),
                "X-Knowledge-Caller": "spoofed-caller",
            },
        )
        assert first.status_code == 201, first.text
        first_data = first.json()
        assert first_data["canonical_state"] == "stored"
        assert first_data["text_state"] == "indexed"
        assert first_data["graph_state"] == "pending"
        assert first_data["source_id"] == "mason-note"
        assert first_data["sha256"] == sha256(body["content"].encode()).hexdigest()
        assert first_data["text_generation_id"]
        assert first_data["text_snapshot_digest"].startswith("sha256:")

    # Reconstruct the application against the same PostgreSQL/artifact stores and
    # replay the exact request. The durable operation/evidence/generation must win.
    reconstructed = _make_app(sessions, store)
    with TestClient(reconstructed) as client:
        replay = client.post(
            "/v1/kc/store",
            json=body,
            headers=_store_headers("mason-1"),
        )
        assert replay.status_code == 201, replay.text
        replay_data = replay.json()
        for field in (
            "source_id",
            "resource_id",
            "version_id",
            "sha256",
            "text_generation_id",
            "text_snapshot_digest",
        ):
            assert replay_data[field] == first_data[field]
        assert replay_data["text_state"] == "indexed"

        changed = client.post(
            "/v1/kc/store",
            json=_store_body("changed bytes must not reuse the operation key\n"),
            headers=_store_headers("mason-1"),
        )
        assert changed.status_code == 409
        assert changed.json()["error_code"] == "OperationReuseError"

    session = sessions()
    try:
        version = session.get(ResourceVersion, UUID(first_data["version_id"]))
        assert version is not None
        assert store.read_bytes(version.artifact_key) == body["content"].encode()

        observations = session.scalars(select(GovernedSourceObservationRecord)).all()
        decisions = session.scalars(select(GovernedSourceDecisionRecord)).all()
        assert len(observations) == 1
        assert len(decisions) == 1
        observation = GovernedSourceEvidenceKnowledgeKernel(session).load_observation(
            observations[0].observation_id
        )
        assert observation.binding.source_identity.origin_scope == "local_owner"
        assert observation.binding.source_identity.source_kind == "local.user-note"
        assert observation.binding.source_identity.item_key == "mason-note"

        snapshot = GovernedSourceEvidenceKnowledgeKernel(session).load_snapshot(
            first_data["text_snapshot_digest"]
        )
        assert len(snapshot.members) == 1
        assert snapshot.members[0].project_keys == ("local-ai",)
        assert snapshot.members[0].resource_version_ref == version.ref_id

        # One logical kc_store request intentionally composes three deterministic
        # ledger operations: source Resource creation, ResourceVersion ingest, and
        # the no-revision governed-admission parent operation.
        assert (
            session.scalar(select(func.count()).select_from(Operation)) == 3
        )
        assert session.scalar(select(func.count()).select_from(Resource)) == 1
        assert session.scalar(select(func.count()).select_from(ResourceVersion)) == 1
        assert (
            session.scalar(
                select(func.count()).select_from(GovernedSourceObservationRecord)
            )
            == 1
        )
    finally:
        session.close()


@pytest.mark.postgresql
def test_task2e_direct_note_preserves_repository_member_in_complete_snapshot(
    task2e_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task2e_engine)
    store = LocalArtifactStore(tmp_path / "task2e-mixed-artifacts")
    session = sessions()
    try:
        commit = "e" * 40
        repository_content = b"# Repository Alpha\nrepository papaya signal\n"
        reader = FakeRepositoryReader()
        reader.put(commit, "alpha.md", repository_content)
        importer = SectionRepositoryImportKnowledgeKernel(
            session,
            artifact_store=store,
            source_readers={"repo-task2e": reader},
        )
        manifest = _repository_manifest(commit, repository_content)
        plan = importer.plan_repository_import(manifest)
        receipt = importer.apply_repository_import(
            manifest=manifest,
            expected_plan_digest=plan.plan_digest,
        )
        assert receipt.status == "settled"
        repository_generation_id = receipt.resulting_text_generation_id
    finally:
        session.close()

    with TestClient(_make_app(sessions, store)) as client:
        response = client.post(
            "/v1/kc/store",
            json=_store_body("independent note mango signal\n", source_id="mixed-note"),
            headers=_store_headers("mixed-note-1"),
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["text_state"] == "indexed"
        assert UUID(data["text_generation_id"]) != repository_generation_id

    session = sessions()
    try:
        snapshot = GovernedSourceEvidenceKnowledgeKernel(session).load_snapshot(
            data["text_snapshot_digest"]
        )
        assert len(snapshot.members) == 2
        source_kinds = {
            GovernedSourceEvidenceKnowledgeKernel(session)
            .load_observation(member.observation_id)
            .binding.source_identity.source_kind
            for member in snapshot.members
        }
        assert source_kinds == {"git.repository-document", "local.user-note"}

        lineages = session.scalars(
            select(TextGenerationSource).where(
                TextGenerationSource.generation_id == UUID(data["text_generation_id"])
            )
        ).all()
        assert len(lineages) == 2
        assert {item.governing_snapshot_digest for item in lineages} == {
            data["text_snapshot_digest"]
        }

        rows = session.scalars(
            select(ResourceSegmentTextSearch).where(
                ResourceSegmentTextSearch.generation_id
                == UUID(data["text_generation_id"])
            )
        ).all()
        assert rows
        assert any(row.source_document_key == "repo-alpha" for row in rows)
        assert any(row.source_document_key is None for row in rows)
    finally:
        session.close()


@pytest.mark.postgresql
def test_task2e_publication_failure_keeps_canonical_note_and_prior_generation(
    task2e_engine,
    tmp_path: Path,
    monkeypatch,
):
    sessions = create_session_factory(task2e_engine)
    store = LocalArtifactStore(tmp_path / "task2e-failure-artifacts")
    app = _make_app(sessions, store)

    with TestClient(app) as client:
        baseline = client.post(
            "/v1/kc/store",
            json=_store_body("baseline apricot signal\n", source_id="baseline"),
            headers=_store_headers("baseline-1"),
        )
        assert baseline.status_code == 201, baseline.text
        baseline_data = baseline.json()
        assert baseline_data["text_state"] == "indexed"

    original_build = (
        SourceNeutralSectionPublicationKnowledgeKernel.build_segment_generation_candidate
    )

    def fail_build(self, **_kwargs):
        raise RuntimeError("forced Task 2E derived failure")

    monkeypatch.setattr(
        SourceNeutralSectionPublicationKnowledgeKernel,
        "build_segment_generation_candidate",
        fail_build,
    )
    failing_body = _store_body(
        "canonical survives derived failure blueberry signal\n",
        source_id="failure-note",
    )
    with TestClient(_make_app(sessions, store)) as client:
        failed = client.post(
            "/v1/kc/store",
            json=failing_body,
            headers=_store_headers("failure-note-1"),
        )
        assert failed.status_code == 201, failed.text
        failed_data = failed.json()
        assert failed_data["canonical_state"] == "stored"
        assert failed_data["text_state"] == "failed"
        assert failed_data["text_error_code"] == "RuntimeError"

    session = sessions()
    try:
        assert _current_generation_id(session) == UUID(
            baseline_data["text_generation_id"]
        )
        failed_version = session.get(
            ResourceVersion,
            UUID(failed_data["version_id"]),
        )
        assert failed_version is not None
        assert store.read_bytes(failed_version.artifact_key) == failing_body[
            "content"
        ].encode()
        assert session.get(
            GovernedSourceObservationRecord,
            next(
                row.observation_id
                for row in session.scalars(
                    select(GovernedSourceObservationRecord).where(
                        GovernedSourceObservationRecord.resource_version_ref
                        == failed_version.ref_id
                    )
                )
            ),
        ) is not None
    finally:
        session.close()

    monkeypatch.setattr(
        SourceNeutralSectionPublicationKnowledgeKernel,
        "build_segment_generation_candidate",
        original_build,
    )
    with TestClient(_make_app(sessions, store)) as client:
        recovered = client.post(
            "/v1/kc/store",
            json=failing_body,
            headers=_store_headers("failure-note-1"),
        )
        assert recovered.status_code == 201, recovered.text
        recovered_data = recovered.json()
        assert recovered_data["text_state"] == "indexed"
        assert recovered_data["resource_id"] == failed_data["resource_id"]
        assert recovered_data["version_id"] == failed_data["version_id"]
        assert recovered_data["text_generation_id"] != baseline_data[
            "text_generation_id"
        ]

    session = sessions()
    try:
        recovered_snapshot = GovernedSourceEvidenceKnowledgeKernel(session).load_snapshot(
            recovered_data["text_snapshot_digest"]
        )
        assert len(recovered_snapshot.members) == 2
        assert _current_generation_id(session) == UUID(
            recovered_data["text_generation_id"]
        )
    finally:
        session.close()
