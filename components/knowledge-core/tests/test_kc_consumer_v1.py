from __future__ import annotations

from hashlib import sha1, sha256
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from knowledge_core.api.app import create_app
from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.section_retrieval_models import ResourceSegmentTextSearch


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
CALLER = {"X-Knowledge-Caller": "kc-consumer-v1-test"}


def _blob_sha(content: bytes) -> str:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


class FakeRepositoryReader:
    def __init__(self):
        self.repository_locator = "memory://kc-consumer-v1"
        self.objects: dict[tuple[str, str], bytes] = {}

    def put(self, commit: str, path: str, content: bytes) -> None:
        self.objects[(commit, path)] = content

    def read_exact(self, *, source_commit: str, path: str) -> RepositorySourceProof:
        content = self.objects[(source_commit, path)]
        return RepositorySourceProof(
            source_commit=source_commit,
            path=path,
            git_blob_sha=_blob_sha(content),
            content=content,
            object_mode="100644",
            object_type="blob",
        )


def _manifest(*, commit: str, path: str, content: bytes) -> dict:
    return {
        "schema_version": 2,
        "manifest_id": "kc-consumer-v1",
        "source_repository_key": "repo-kc-consumer-v1",
        "repository_locator": "memory://kc-consumer-v1",
        "source_commit": commit,
        "previous_manifest_digest": None,
        "history_policy": "retain_prior_versions_as_superseded",
        "entries": [
            {
                "source_document_key": "consumer-doc",
                "path": path,
                "git_blob_sha": _blob_sha(content),
                "media_type": "text/markdown",
                "classification": "approved",
                "retrieval_lifecycle": "current",
                "authority_rank": 3,
                "rationale": "KC Consumer V1 canonical content fixture",
            }
        ],
        "retirements": [],
    }


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("KC Consumer V1 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("KC Consumer V1 requires PostgreSQL")
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
def consumer_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


@pytest.mark.postgresql
def test_kc_consumer_v1_serves_exact_canonical_segment_and_fails_closed_on_tamper(
    consumer_engine,
    tmp_path: Path,
):
    commit = "e" * 40
    path = "consumer.md"
    content = (
        b"# Consumer Contract\n"
        b"bounded evidence sentinel\n"
        b"## Other\n"
        b"unrelated material\n"
    )
    reader = FakeRepositoryReader()
    reader.put(commit, path, content)

    sessions = create_session_factory(consumer_engine)
    session = sessions()
    store = LocalArtifactStore(tmp_path / "artifacts")
    importer = SectionRepositoryImportKnowledgeKernel(
        session,
        artifact_store=store,
        source_readers={"repo-kc-consumer-v1": reader},
    )
    retrieval = RetrievalServiceKnowledgeKernel(
        session,
        artifact_store=store,
    )

    manifest = _manifest(commit=commit, path=path, content=content)
    plan = importer.plan_repository_import(manifest)
    receipt = importer.apply_repository_import(
        manifest=manifest,
        expected_plan_digest=plan.plan_digest,
    )
    assert receipt.status == "settled"
    assert receipt.resulting_text_generation_id is not None

    snapshot = retrieval.search_text(query="bounded evidence sentinel")
    assert snapshot.retrieval_mode == "segment"
    assert snapshot.generation_id == receipt.resulting_text_generation_id
    assert len(snapshot.results) == 1

    hit = snapshot.results[0]
    assert hit.segment is not None
    segment = hit.segment
    expected_bytes = content[segment.source_byte_start : segment.source_byte_end]
    assert hit.content == expected_bytes.decode("utf-8")
    assert sha256(expected_bytes).hexdigest() == segment.source_slice_sha256
    assert hit.content.startswith("# Consumer Contract\n")
    assert "## Other" not in hit.content

    transport = TestClient(create_app(session_factory=sessions, artifact_store=store))
    try:
        response = transport.post(
            "/v1/retrieval/search",
            json={"query": "bounded evidence sentinel"},
            headers=CALLER,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["retrieval_mode"] == "segment"
        public_hit = payload["results"][0]
        assert public_hit["content"] == hit.content
        assert public_hit["resource_version_ref"] == str(hit.resource_version_ref)
        assert public_hit["segment"]["segment_key"] == segment.segment_key
        assert public_hit["segment"]["source_slice_sha256"] == segment.source_slice_sha256
        assert public_hit["segment"]["governing_manifest_digest"] == receipt.manifest_digest
        forbidden = response.text.lower()
        for token in (
            "artifact_key",
            "artifact_backend",
            "database_url",
            "raw_sql",
            str(store.root).lower(),
        ):
            assert token not in forbidden
    finally:
        transport.close()

    row = session.get(
        ResourceSegmentTextSearch,
        {
            "generation_id": snapshot.generation_id,
            "resource_version_ref": hit.resource_version_ref,
            "segment_ordinal": segment.segment_ordinal,
        },
    )
    assert row is not None
    row.source_slice_sha256 = "0" * 64
    session.commit()

    with pytest.raises(
        KnowledgeInvariantError,
        match="segment slice digest does not match canonical artifact",
    ):
        retrieval.search_text(query="bounded evidence sentinel")

    session.close()
