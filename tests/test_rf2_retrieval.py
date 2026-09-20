from __future__ import annotations

import os
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, inspect, literal_column, select, text
from sqlalchemy.engine import Engine

from knowledge_core.api.app import create_app
from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.deletion import DeletionActionType
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.domain.retrieval import RetrievalLifecycleState, TextIndexSource
from knowledge_core.domain.resources import ResourceLocatorKind
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.generation_models import GenerationSource
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.retrieval_models import ResourceTextSearch


pytestmark = pytest.mark.postgresql

_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
CALLER = {"X-Knowledge-Caller": "rf2-simulated-client"}
_ENGLISH_REGCONFIG = literal_column("'english'::regconfig")


def _require_postgres_engine() -> Engine:
    if not _POSTGRES_URL:
        pytest.skip("PostgreSQL RF-2 URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("RF-2 requires PostgreSQL")
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
def postgres_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _ingest(
    kernel: RetrievalServiceKnowledgeKernel,
    resource_refs,
    *,
    content: bytes,
    media_type: str,
    path: str,
):
    logical = kernel.create_resource(
        kind_revision_ref=resource_refs.artifact_kind_revision_ref
    )
    return kernel.ingest_resource_version(
        resource_ref=logical.resource_ref,
        content=content,
        ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref,
        media_type=media_type,
        locator_kind=ResourceLocatorKind.PATH,
        locator_text=path,
    )


def _build_corpus(postgres_engine: Engine, tmp_path):
    sessions = create_session_factory(postgres_engine)
    artifacts = LocalArtifactStore(tmp_path / "artifacts")
    with sessions() as session:
        kernel = RetrievalServiceKnowledgeKernel(session, artifact_store=artifacts)
        resource_refs = kernel.bootstrap_resource_test_profile()

        atlas_logical = kernel.create_resource(
            kind_revision_ref=resource_refs.artifact_kind_revision_ref
        )
        atlas_current = kernel.ingest_resource_version(
            resource_ref=atlas_logical.resource_ref,
            content=(
                b"Atlas emergency shutdown token is cedar. "
                b"Atlas restart requires supervisor acknowledgement."
            ),
            ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref,
            media_type="text/markdown",
        )
        # Deliberately observe the older source later. If lifecycle were inferred from
        # canonical recency, this superseded version would incorrectly win.
        atlas_old = kernel.ingest_resource_version(
            resource_ref=atlas_logical.resource_ref,
            content=(
                b"Atlas emergency shutdown token is amber. "
                b"Atlas restart requires supervisor acknowledgement."
            ),
            ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref,
            media_type="text/markdown",
        )

        cpdm_standard = _ingest(
            kernel,
            resource_refs,
            content=b"CPDM calibration window begins thirty minutes before shift start.",
            media_type="text/plain",
            path="/synthetic/cpdm-standard.txt",
        )
        cpdm_notes = _ingest(
            kernel,
            resource_refs,
            content=b"CPDM calibration window begins thirty minutes before shift start.",
            media_type="text/plain",
            path="/synthetic/cpdm-notes.txt",
        )
        unrelated = _ingest(
            kernel,
            resource_refs,
            content=b"Cafeteria schedule lists soup and sandwiches for Thursday.",
            media_type="text/plain",
            path="/synthetic/unrelated.txt",
        )
        unsupported_pdf = _ingest(
            kernel,
            resource_refs,
            content=b"%PDF Atlas emergency shutdown token is maliciously obvious.",
            media_type="application/pdf",
            path="/synthetic/atlas.pdf",
        )
        restricted_atlas = _ingest(
            kernel,
            resource_refs,
            content=b"Atlas emergency shutdown token restricted source marker.",
            media_type="text/plain",
            path="/synthetic/restricted-atlas.txt",
        )
        tie_older = _ingest(
            kernel,
            resource_refs,
            content=b"Deterministic tie marker echo.",
            media_type="text/plain",
            path="/synthetic/tie-older.txt",
        )
        tie_newer = _ingest(
            kernel,
            resource_refs,
            content=b"Deterministic tie marker echo.",
            media_type="text/plain",
            path="/synthetic/tie-newer.txt",
        )

        specs = {
            "atlas-current": TextIndexSource(
                atlas_current.resource_version_ref,
                RetrievalLifecycleState.CURRENT,
                10,
                "synthetic/ops",
                "docs/atlas-runbook.md",
                "commit-new",
            ),
            "atlas-old": TextIndexSource(
                atlas_old.resource_version_ref,
                RetrievalLifecycleState.SUPERSEDED,
                10,
                "synthetic/ops",
                "docs/atlas-runbook.md",
                "commit-old",
            ),
            "cpdm-standard": TextIndexSource(
                cpdm_standard.resource_version_ref,
                RetrievalLifecycleState.CURRENT,
                5,
                "synthetic/safety",
                "docs/cpdm-standard.txt",
                "standard-1",
            ),
            "cpdm-notes": TextIndexSource(
                cpdm_notes.resource_version_ref,
                RetrievalLifecycleState.CURRENT,
                50,
                "synthetic/safety",
                "notes/cpdm.txt",
                "notes-1",
            ),
            "unrelated": TextIndexSource(
                unrelated.resource_version_ref,
                RetrievalLifecycleState.CURRENT,
                20,
                "synthetic/general",
                "docs/cafeteria.txt",
                "general-1",
            ),
            "unsupported-pdf": TextIndexSource(
                unsupported_pdf.resource_version_ref,
                RetrievalLifecycleState.CURRENT,
                1,
                "synthetic/ops",
                "docs/atlas.pdf",
                "pdf-1",
            ),
            "restricted-atlas": TextIndexSource(
                restricted_atlas.resource_version_ref,
                RetrievalLifecycleState.CURRENT,
                1,
                "synthetic/private",
                "docs/restricted-atlas.txt",
                "private-1",
            ),
            "tie-older": TextIndexSource(
                tie_older.resource_version_ref,
                RetrievalLifecycleState.CURRENT,
                25,
                "synthetic/ties",
                "docs/tie-older.txt",
                "tie-1",
            ),
            "tie-newer": TextIndexSource(
                tie_newer.resource_version_ref,
                RetrievalLifecycleState.CURRENT,
                25,
                "synthetic/ties",
                "docs/tie-newer.txt",
                "tie-2",
            ),
        }

        generation = kernel.build_text_generation(sources=list(specs.values()))

        before_fence = session.scalar(
            select(func.count())
            .select_from(ResourceTextSearch)
            .where(
                ResourceTextSearch.generation_id == generation.generation_id,
                ResourceTextSearch.resource_version_ref
                == restricted_atlas.resource_version_ref,
            )
        )
        assert before_fence == 1
        kernel.fence_target_operation(
            operation_id=uuid4(),
            target_ref=restricted_atlas.resource_version_ref,
            action_type=DeletionActionType.RESTRICT,
            policy_scope_id="rf2-test-policy",
            caller_principal_ref="rf2-privacy-controller",
        )
        after_fence = session.scalar(
            select(func.count())
            .select_from(ResourceTextSearch)
            .where(
                ResourceTextSearch.generation_id == generation.generation_id,
                ResourceTextSearch.resource_version_ref
                == restricted_atlas.resource_version_ref,
            )
        )
        assert after_fence == 0

    return sessions, artifacts, specs, generation


def test_rf2_g1_migration_and_postgres_gin_index_exist(postgres_engine):
    inspector = inspect(postgres_engine)
    assert "resource_text_search" in inspector.get_table_names(schema="kc_derived")
    with postgres_engine.connect() as connection:
        indexdef = connection.scalar(
            text(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'kc_derived'
                  AND tablename = 'resource_text_search'
                  AND indexname = 'ix_resource_text_search_vector'
                """
            )
        )
    assert indexdef is not None
    assert "USING gin" in indexdef


def test_rf2_g2_through_g9_and_g13_synthetic_semantics(
    postgres_engine,
    tmp_path,
):
    sessions, artifacts, specs, generation = _build_corpus(postgres_engine, tmp_path)
    with sessions() as session:
        kernel = RetrievalServiceKnowledgeKernel(session, artifact_store=artifacts)

        indexed_refs = set(
            session.scalars(
                select(GenerationSource.source_ref_id).where(
                    GenerationSource.generation_id == generation.generation_id
                )
            ).all()
        )
        expected_indexed_refs = {
            spec.resource_version_ref
            for name, spec in specs.items()
            if name != "unsupported-pdf"
        }
        assert indexed_refs == expected_indexed_refs

        assert kernel.search_text(query="maliciously obvious").results == ()

        atlas = kernel.search_text(query="Atlas emergency shutdown token")
        atlas_refs = [item.resource_version_ref for item in atlas.results]
        assert atlas_refs == [specs["atlas-current"].resource_version_ref]

        assert kernel.search_text(query="amber").results == ()
        historical = kernel.search_text(query="amber", include_superseded=True)
        assert [item.resource_version_ref for item in historical.results] == [
            specs["atlas-old"].resource_version_ref
        ]

        cpdm = kernel.search_text(query="CPDM calibration window")
        assert [item.resource_version_ref for item in cpdm.results] == [
            specs["cpdm-standard"].resource_version_ref,
            specs["cpdm-notes"].resource_version_ref,
        ]

        expected_ties = [
            specs["tie-newer"].resource_version_ref,
            specs["tie-older"].resource_version_ref,
        ]
        for _ in range(10):
            ties = kernel.search_text(query="Deterministic tie marker echo")
            assert [item.resource_version_ref for item in ties.results] == expected_ties

        current_hit = atlas.results[0]
        current_version = session.get(
            ResourceVersion,
            specs["atlas-current"].resource_version_ref,
        )
        assert current_version is not None
        assert current_hit.resource_ref == current_version.resource_ref_id
        assert current_hit.resource_version_ref == specs["atlas-current"].resource_version_ref
        assert current_hit.content_digest_algo == "sha256"
        assert current_hit.content_digest == sha256(
            (
                b"Atlas emergency shutdown token is cedar. "
                b"Atlas restart requires supervisor acknowledgement."
            )
        ).hexdigest()
        assert current_hit.media_type == "text/markdown"
        assert current_hit.lifecycle_state is RetrievalLifecycleState.CURRENT
        assert current_hit.authority_rank == 10
        assert current_hit.repository == "synthetic/ops"
        assert current_hit.source_path == "docs/atlas-runbook.md"
        assert current_hit.source_version == "commit-new"
        assert atlas.generation_id == generation.generation_id

        # Re-introduce a stale derived row after the normal purge to prove that
        # service-time eligibility, not purge timing, is the final serving fence.
        restricted_ref = specs["restricted-atlas"].resource_version_ref
        session.execute(
            insert(ResourceTextSearch).values(
                generation_id=generation.generation_id,
                resource_version_ref=restricted_ref,
                lifecycle_state="current",
                authority_rank=1,
                repository="synthetic/private",
                source_path="docs/restricted-atlas.txt",
                source_version="private-1",
                search_vector=func.to_tsvector(
                    _ENGLISH_REGCONFIG,
                    "Atlas emergency shutdown token restricted source marker.",
                ),
            )
        )
        session.commit()
        assert session.scalar(
            select(func.count())
            .select_from(ResourceTextSearch)
            .where(
                ResourceTextSearch.generation_id == generation.generation_id,
                ResourceTextSearch.resource_version_ref == restricted_ref,
            )
        ) == 1
        after_stale_reinsert = kernel.search_text(
            query="Atlas emergency shutdown token"
        )
        assert restricted_ref not in {
            item.resource_version_ref for item in after_stale_reinsert.results
        }

        # atlas-old was created after atlas-current but remains superseded because
        # lifecycle classification is explicit rather than "latest wins".
        assert historical.results[0].created_revision_id > current_hit.created_revision_id


class _ServiceOnlyRetrievalClient:
    def __init__(self, transport: TestClient):
        self._transport = transport

    def search(self, **payload):
        return self._transport.post(
            "/v1/retrieval/search",
            json=payload,
            headers=CALLER,
        )


def test_rf2_g10_through_g12_service_only_contract(
    postgres_engine,
    tmp_path,
):
    sessions, artifacts, specs, generation = _build_corpus(postgres_engine, tmp_path)
    transport = TestClient(
        create_app(session_factory=sessions, artifact_store=artifacts)
    )
    client = _ServiceOnlyRetrievalClient(transport)
    try:
        assert set(vars(client)) == {"_transport"}

        response = client.search(query="Atlas emergency shutdown token")
        assert response.status_code == 200
        payload = response.json()
        assert payload["generation_id"] == str(generation.generation_id)
        assert [item["resource_version_ref"] for item in payload["results"]] == [
            str(specs["atlas-current"].resource_version_ref)
        ]
        assert payload["results"][0]["rank"] == 1

        blank = client.search(query="   ")
        assert blank.status_code == 422

        irrelevant = client.search(query="interplanetary penguin theorem")
        assert irrelevant.status_code == 200
        assert irrelevant.json()["results"] == []

        missing_caller = transport.post(
            "/v1/retrieval/search",
            json={"query": "Atlas"},
        )
        assert missing_caller.status_code == 400

        openapi = transport.get("/openapi.json").text.lower()
        response_text = response.text.lower()
        for forbidden in (
            "database_url",
            "artifact_key",
            "artifact_backend",
            "knowledge_core_database_url",
        ):
            assert forbidden not in openapi
            assert forbidden not in response_text
        assert str(artifacts.root).lower() not in response_text
    finally:
        transport.close()


def test_rf2_g14_uses_only_newest_current_text_generation(
    postgres_engine,
    tmp_path,
):
    sessions, artifacts, specs, first_generation = _build_corpus(
        postgres_engine,
        tmp_path,
    )
    with sessions() as session:
        kernel = RetrievalServiceKnowledgeKernel(session, artifact_store=artifacts)
        second_generation = kernel.build_text_generation(
            sources=[specs["cpdm-standard"]]
        )
        assert second_generation.generation_id != first_generation.generation_id

        atlas = kernel.search_text(query="Atlas emergency shutdown token")
        assert atlas.generation_id == second_generation.generation_id
        assert atlas.results == ()

        cpdm = kernel.search_text(query="CPDM calibration window")
        assert cpdm.generation_id == second_generation.generation_id
        assert [item.resource_version_ref for item in cpdm.results] == [
            specs["cpdm-standard"].resource_version_ref
        ]

        old_rows = session.scalar(
            select(func.count())
            .select_from(ResourceTextSearch)
            .where(ResourceTextSearch.generation_id == first_generation.generation_id)
        )
        assert old_rows and old_rows > 0
        current = kernel._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        assert current is not None
        assert current.generation_id == second_generation.generation_id
