from __future__ import annotations

from hashlib import sha1
import os
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from knowledge_core.api.repository_import_app import create_repository_import_app
from knowledge_core.application.governed_source_evidence import (
    GovernedSourceEvidenceKnowledgeKernel,
)
from knowledge_core.application.repository_governed_producer import (
    RepositoryGovernedProducerKnowledgeKernel,
)
from knowledge_core.application.repository_import import RepositoryImportKnowledgeKernel
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind, GenerationFenceError
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.governed_source_models import LegacyRepositorySnapshotMap
from knowledge_core.storage.repository_import_models import RepositoryImportReceipt
from knowledge_core.storage.section_retrieval_models import TextGenerationProfile


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_CALLER = {"X-Knowledge-Caller": "task2c-test"}


def _blob_sha(content: bytes) -> str:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


class FakeRepositoryReader:
    def __init__(self):
        self.repository_locator = "memory://task2c-repository"
        self.objects: dict[tuple[str, str], bytes] = {}

    def put(self, commit: str, path: str, content: bytes) -> None:
        self.objects[(commit, path)] = content

    def read_exact(self, *, source_commit: str, path: str) -> RepositorySourceProof:
        try:
            content = self.objects[(source_commit, path)]
        except KeyError as exc:
            raise KnowledgeInvariantError(
                f"source path does not exist at exact commit: {path}"
            ) from exc
        return RepositorySourceProof(
            source_commit=source_commit,
            path=path,
            git_blob_sha=_blob_sha(content),
            content=content,
            object_mode="100644",
            object_type="blob",
        )


def _manifest(
    *, manifest_id: str, commit: str, content: bytes, previous: str | None = None
) -> dict:
    return {
        "schema_version": 2,
        "manifest_id": manifest_id,
        "source_repository_key": "repo-task2c",
        "repository_locator": "memory://task2c-repository",
        "source_commit": commit,
        "previous_manifest_digest": previous,
        "history_policy": "retain_prior_versions_as_superseded",
        "entries": [
            {
                "source_document_key": "alpha",
                "path": "alpha.md",
                "git_blob_sha": _blob_sha(content),
                "media_type": "text/markdown",
                "classification": "approved",
                "retrieval_lifecycle": "current",
                "authority_rank": 10,
                "rationale": "Task 2C repository producer qualification",
            }
        ],
        "retirements": [],
    }


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("Task 2C PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("Task 2C requires PostgreSQL")
    return engine


def _truncate_kernel_tables(engine) -> None:
    inspector = inspect(engine)
    preparer = engine.dialect.identifier_preparer
    tables = [
        f"{preparer.quote_schema(schema)}.{preparer.quote(table_name)}"
        for schema in ("kc", "kc_control", "kc_derived")
        for table_name in inspector.get_table_names(schema=schema)
    ]
    if not tables:
        raise AssertionError("Knowledge Core schemas are not migrated")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"
        )


@pytest.fixture()
def task2c_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _importer(engine, tmp_path: Path, reader: FakeRepositoryReader):
    sessions = create_session_factory(engine)
    session = sessions()
    importer = SectionRepositoryImportKnowledgeKernel(
        session,
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
        source_readers={"repo-task2c": reader},
    )
    return importer, session, sessions


def _apply(importer, manifest: dict):
    plan = importer.plan_repository_import(manifest)
    return importer.apply_repository_import(
        manifest=manifest,
        expected_plan_digest=plan.plan_digest,
    )


def _current_text_generation_id(session):
    return session.scalar(
        select(DerivedGeneration.generation_id).where(
            DerivedGeneration.derived_kind == DerivedKind.TEXT.value,
            DerivedGeneration.status == "current",
        )
    )


@pytest.mark.postgresql
def test_section_repository_import_settles_generic_snapshot_with_sr2_generation(
    task2c_engine, tmp_path: Path
):
    reader = FakeRepositoryReader()
    commit = "a" * 40
    content = b"# Alpha\nproducer boundary apricot\n"
    reader.put(commit, "alpha.md", content)
    importer, session, _sessions = _importer(task2c_engine, tmp_path, reader)
    try:
        receipt = _apply(
            importer,
            _manifest(manifest_id="A", commit=commit, content=content),
        )
        assert receipt.status == "settled"
        assert receipt.resulting_text_generation_id is not None
        assert _current_text_generation_id(session) == receipt.resulting_text_generation_id
        assert session.get(TextGenerationProfile, receipt.resulting_text_generation_id)

        mapping = session.get(LegacyRepositorySnapshotMap, receipt.manifest_digest)
        assert mapping is not None
        snapshot = GovernedSourceEvidenceKnowledgeKernel(session).load_snapshot(
            mapping.snapshot_digest
        )
        assert len(snapshot.members) == 1
        assert len(snapshot.exclusions) == 0

        replay = _apply(
            importer,
            _manifest(manifest_id="A", commit=commit, content=content),
        )
        assert replay.manifest_digest == receipt.manifest_digest
        assert replay.resulting_text_generation_id == receipt.resulting_text_generation_id
        replay_mapping = session.get(LegacyRepositorySnapshotMap, receipt.manifest_digest)
        assert replay_mapping is not None
        assert replay_mapping.snapshot_digest == mapping.snapshot_digest
    finally:
        session.close()


@pytest.mark.postgresql
def test_generic_mapping_failure_rolls_back_sr2_publication(
    task2c_engine, tmp_path: Path, monkeypatch
):
    reader = FakeRepositoryReader()
    commit_a, commit_b = "a" * 40, "b" * 40
    content_a = b"# Alpha\nfirst current apple\n"
    content_b = b"# Alpha\nsecond candidate berry\n"
    reader.put(commit_a, "alpha.md", content_a)
    reader.put(commit_b, "alpha.md", content_b)
    importer, session, _sessions = _importer(task2c_engine, tmp_path, reader)
    try:
        receipt_a = _apply(
            importer,
            _manifest(manifest_id="A", commit=commit_a, content=content_a),
        )
        current_a = _current_text_generation_id(session)
        assert current_a == receipt_a.resulting_text_generation_id

        manifest_b = _manifest(
            manifest_id="B",
            commit=commit_b,
            content=content_b,
            previous=receipt_a.manifest_digest,
        )
        plan_b = importer.plan_repository_import(manifest_b)
        original = RepositoryGovernedProducerKnowledgeKernel.prepare_complete_snapshot

        def fail_current_mapping(
            self,
            *,
            governing_manifest_digest: str,
            expected_predecessor_snapshot_digest: str | None,
        ):
            if governing_manifest_digest == plan_b.manifest_digest:
                raise RuntimeError("injected generic evidence failure")
            return original(
                self,
                governing_manifest_digest=governing_manifest_digest,
                expected_predecessor_snapshot_digest=expected_predecessor_snapshot_digest,
            )

        monkeypatch.setattr(
            RepositoryGovernedProducerKnowledgeKernel,
            "prepare_complete_snapshot",
            fail_current_mapping,
        )
        with pytest.raises(RuntimeError, match="generic evidence failure"):
            importer.apply_repository_import(
                manifest=manifest_b,
                expected_plan_digest=plan_b.plan_digest,
            )

        assert _current_text_generation_id(session) == current_a
        failed = session.get(RepositoryImportReceipt, plan_b.manifest_digest)
        assert failed is not None
        assert failed.status == "failed"
        assert session.get(LegacyRepositorySnapshotMap, plan_b.manifest_digest) is None
    finally:
        session.close()


@pytest.mark.postgresql
def test_repository_import_http_service_uses_sr2_producer_and_generic_evidence(
    task2c_engine, tmp_path: Path
):
    reader = FakeRepositoryReader()
    commit = "c" * 40
    content = b"# Alpha\npublic producer citrus\n"
    reader.put(commit, "alpha.md", content)
    manifest = _manifest(manifest_id="HTTP-A", commit=commit, content=content)

    sessions = create_session_factory(task2c_engine)
    app = create_repository_import_app(
        session_factory=sessions,
        artifact_store=LocalArtifactStore(tmp_path / "http-artifacts"),
        source_readers={"repo-task2c": reader},
    )
    with TestClient(app) as client:
        planned = client.post(
            "/v1/repository-import/plan", headers=_CALLER, json={"manifest": manifest}
        )
        assert planned.status_code == 200, planned.text
        applied = client.post(
            "/v1/repository-import/apply",
            headers=_CALLER,
            json={"manifest": manifest, "plan_digest": planned.json()["plan_digest"]},
        )
        assert applied.status_code == 200, applied.text
        body = applied.json()

    session = sessions()
    try:
        generation_ref = UUID(body["resulting_text_generation_id"])
        assert session.get(TextGenerationProfile, generation_ref) is not None
        assert session.get(LegacyRepositorySnapshotMap, body["manifest_digest"])
        assert _current_text_generation_id(session) == generation_ref
    finally:
        session.close()


@pytest.mark.postgresql
def test_legacy_rf2_importer_cannot_replace_established_sr2_current_generation(
    task2c_engine, tmp_path: Path
):
    reader = FakeRepositoryReader()
    commit_a, commit_b = "d" * 40, "e" * 40
    content_a = b"# Alpha\nestablish sr2 dragonfruit\n"
    content_b = b"# Alpha\nlegacy rf2 elderberry\n"
    reader.put(commit_a, "alpha.md", content_a)
    reader.put(commit_b, "alpha.md", content_b)

    sessions = create_session_factory(task2c_engine)
    session = sessions()
    artifact_store = LocalArtifactStore(tmp_path / "guard-artifacts")
    try:
        sr2 = SectionRepositoryImportKnowledgeKernel(
            session,
            artifact_store=artifact_store,
            source_readers={"repo-task2c": reader},
        )
        receipt_a = _apply(
            sr2,
            _manifest(manifest_id="SR2-A", commit=commit_a, content=content_a),
        )
        current_a = _current_text_generation_id(session)
        assert current_a == receipt_a.resulting_text_generation_id
        assert session.get(TextGenerationProfile, current_a) is not None

        legacy = RepositoryImportKnowledgeKernel(
            session,
            artifact_store=artifact_store,
            source_readers={"repo-task2c": reader},
        )
        manifest_b = _manifest(
            manifest_id="RF2-B",
            commit=commit_b,
            content=content_b,
            previous=receipt_a.manifest_digest,
        )
        plan_b = legacy.plan_repository_import(manifest_b)
        with pytest.raises(
            GenerationFenceError,
            match="RF-2 text publication cannot replace an established SR-2",
        ):
            legacy.apply_repository_import(
                manifest=manifest_b,
                expected_plan_digest=plan_b.plan_digest,
            )
        assert _current_text_generation_id(session) == current_a
        failed = session.get(RepositoryImportReceipt, plan_b.manifest_digest)
        assert failed is not None
        assert failed.status == "failed"
    finally:
        session.close()
