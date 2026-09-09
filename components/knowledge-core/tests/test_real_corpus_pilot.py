from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from knowledge_core.api.app import create_app
from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.generations import GenerationStatus
from knowledge_core.domain.retrieval import RetrievalLifecycleState, TextIndexSource
from knowledge_core.domain.resources import ResourceLocatorKind
from knowledge_core.storage.database import create_database_engine, create_session_factory


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "knowledge-core"
    / "REAL_CORPUS_PILOT_MANIFEST.json"
)
_EXPECTED_BASELINE = "adb2a48a1e248f24e43550d897eed1b5e300cc26"
_CALLER = {"X-Knowledge-Caller": "knowledge-core-real-corpus-pilot"}


def _manifest() -> dict:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _git_blob_sha(content: bytes) -> str:
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


def _document_bytes(path: str) -> bytes:
    return (_REPO_ROOT / path).read_bytes()


def test_real_corpus_manifest_is_exact_bounded_baseline():
    manifest = _manifest()
    documents = manifest["documents"]

    assert manifest["source_commit"] == _EXPECTED_BASELINE
    assert manifest["repository"] == "floydtrey/autonomous-coding-lab"
    assert manifest["source_directory"] == "docs/architecture/knowledge-core"
    assert len(documents) == 10
    assert len({document["path"] for document in documents}) == 10
    assert all(document["approved_for_pilot"] for document in documents)

    current_paths = {
        document["path"]
        for document in documents
        if document["retrieval_lifecycle"] == "current"
    }
    superseded_paths = {
        document["path"]
        for document in documents
        if document["retrieval_lifecycle"] == "superseded"
    }
    assert current_paths == {
        "docs/architecture/knowledge-core/CURRENT_STATE.md",
        "docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md",
        "docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md",
        "docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF2.md",
    }
    assert len(superseded_paths) == 6

    for document in documents:
        path = document["path"]
        assert path.startswith("docs/architecture/knowledge-core/")
        assert path.endswith(".md")
        content = _document_bytes(path)
        assert _git_blob_sha(content) == document["git_blob_sha"], path


def _require_postgres_engine() -> Engine:
    if not _POSTGRES_URL:
        pytest.skip("Knowledge Core real-corpus pilot PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("Knowledge Core real-corpus pilot requires PostgreSQL")
    return engine


def _truncate_kernel_tables(engine: Engine) -> None:
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
def pilot_postgres_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _build_pilot_corpus(postgres_engine: Engine, tmp_path):
    manifest = _manifest()
    sessions = create_session_factory(postgres_engine)
    artifacts = LocalArtifactStore(tmp_path / "pilot-artifacts")
    versions = {}

    with sessions() as session:
        kernel = RetrievalServiceKnowledgeKernel(session, artifact_store=artifacts)
        resource_refs = kernel.bootstrap_resource_test_profile()
        sources: list[TextIndexSource] = []

        for document in manifest["documents"]:
            path = document["path"]
            content = _document_bytes(path)
            assert _git_blob_sha(content) == document["git_blob_sha"], path

            logical = kernel.create_resource(
                kind_revision_ref=resource_refs.artifact_kind_revision_ref
            )
            version = kernel.ingest_resource_version(
                resource_ref=logical.resource_ref,
                content=content,
                ingestion_kind_revision_ref=(
                    resource_refs.resource_ingestion_kind_revision_ref
                ),
                media_type="text/markdown",
                locator_kind=ResourceLocatorKind.PATH,
                locator_text=path,
            )
            versions[path] = version
            sources.append(
                TextIndexSource(
                    resource_version_ref=version.resource_version_ref,
                    lifecycle_state=RetrievalLifecycleState(
                        document["retrieval_lifecycle"]
                    ),
                    authority_rank=document["authority_rank"],
                    repository=manifest["repository"],
                    source_path=path,
                    source_version=manifest["source_commit"],
                )
            )

        generation = kernel.build_text_generation(sources=sources)
        assert generation.status is GenerationStatus.CURRENT
        assert len(generation.sources) == len(manifest["documents"])

    return manifest, sessions, artifacts, versions, generation


@pytest.mark.postgresql
def test_real_corpus_known_queries_and_exact_provenance(
    pilot_postgres_engine,
    tmp_path,
):
    manifest, sessions, artifacts, versions, generation = _build_pilot_corpus(
        pilot_postgres_engine,
        tmp_path,
    )
    documents_by_path = {
        document["path"]: document for document in manifest["documents"]
    }

    with sessions() as session:
        kernel = RetrievalServiceKnowledgeKernel(session, artifact_store=artifacts)

        for case in manifest["known_queries"]:
            result = kernel.search_text(
                query=case["query"],
                limit=50,
                include_superseded=case["include_superseded"],
            )
            paths = [hit.source_path for hit in result.results]
            assert result.generation_id == generation.generation_id, case["id"]
            assert result.source_revision_highwater == generation.source_revision_highwater

            if "exact_paths" in case:
                assert set(paths) == set(case["exact_paths"]), (
                    case["id"],
                    paths,
                )
            for required_path in case.get("must_include", []):
                assert required_path in paths, (case["id"], paths)

            for hit in result.results:
                assert hit.source_path is not None
                document = documents_by_path[hit.source_path]
                version = versions[hit.source_path]
                content = _document_bytes(hit.source_path)

                assert hit.repository == manifest["repository"]
                assert hit.source_version == manifest["source_commit"]
                assert hit.lifecycle_state.value == document["retrieval_lifecycle"]
                assert hit.authority_rank == document["authority_rank"]
                assert hit.resource_ref == version.resource_ref
                assert hit.resource_version_ref == version.resource_version_ref
                assert hit.content_digest_algo == "sha256"
                assert hit.content_digest == hashlib.sha256(content).hexdigest()
                if not case["include_superseded"]:
                    assert hit.lifecycle_state is RetrievalLifecycleState.CURRENT


@pytest.mark.postgresql
def test_real_corpus_service_only_query_uses_curated_generation(
    pilot_postgres_engine,
    tmp_path,
):
    manifest, sessions, artifacts, _versions, generation = _build_pilot_corpus(
        pilot_postgres_engine,
        tmp_path,
    )
    app = create_app(session_factory=sessions, artifact_store=artifacts)

    with TestClient(app) as client:
        response = client.post(
            "/v1/retrieval/search",
            headers=_CALLER,
            json={
                "query": "\"documentation and checkpoint reserve\"",
                "limit": 10,
                "include_superseded": False,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["generation_id"] == str(generation.generation_id)
    paths = [item["source_path"] for item in body["results"]]
    assert "docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md" in paths
    assert all(
        item["source_version"] == manifest["source_commit"]
        for item in body["results"]
    )
    serialized = json.dumps(body, sort_keys=True)
    assert "artifact_key" not in serialized
    assert "artifact_backend" not in serialized
    assert "KNOWLEDGE_CORE_DATABASE_URL" not in serialized
