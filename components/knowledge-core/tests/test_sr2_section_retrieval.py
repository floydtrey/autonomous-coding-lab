from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, insert, literal_column, select
from sqlalchemy.engine import Engine

from knowledge_core.api.app import create_app
from knowledge_core.application.repository_source import GitRepositorySourceReader
from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.application.segmentation import (
    DEFAULT_SECTION_SEGMENTATION_PROFILE,
    SectionSegmentationProfile,
    segment_text_resource,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.deletion import DeletionActionType
from knowledge_core.domain.generations import (
    DerivedKind,
    GenerationFenceError,
)
from knowledge_core.domain.retrieval import (
    RetrievalLifecycleState,
    TextIndexSource,
)
from knowledge_core.domain.resources import ResourceLocatorKind
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.generation_models import (
    DerivedGeneration,
    GenerationSource,
)
from knowledge_core.storage.repository_import_models import (
    RepositoryDocumentBinding,
    RepositoryImportReceipt,
    RepositorySourceObservation,
)
from knowledge_core.storage.resource_models import Resource, ResourceVersion
from knowledge_core.storage.retrieval_models import (
    ResourceSegmentTextSearch,
    ResourceTextSearch,
)


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PILOT_MANIFEST = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "knowledge-core"
    / "SR2_REAL_PILOT_MANIFEST.json"
)
_CALLER = {"X-Knowledge-Caller": "sr2-test"}
_ENGLISH_REGCONFIG = literal_column("'english'::regconfig")


def _require_postgres_engine() -> Engine:
    if not _POSTGRES_URL:
        pytest.skip("SR-2 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("SR-2 requires PostgreSQL")
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
            "TRUNCATE TABLE "
            + ", ".join(tables)
            + " RESTART IDENTITY CASCADE"
        )


@pytest.fixture()
def sr2_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _count(session, model) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _ingest(
    kernel: RetrievalServiceKnowledgeKernel,
    refs,
    *,
    content: bytes,
    path: str,
    media_type: str = "text/markdown",
):
    logical = kernel.create_resource(
        kind_revision_ref=refs.artifact_kind_revision_ref
    )
    return kernel.ingest_resource_version(
        resource_ref=logical.resource_ref,
        content=content,
        ingestion_kind_revision_ref=refs.resource_ingestion_kind_revision_ref,
        media_type=media_type,
        locator_kind=ResourceLocatorKind.PATH,
        locator_text=path,
    )


def _source(
    version,
    *,
    lifecycle: RetrievalLifecycleState = RetrievalLifecycleState.CURRENT,
    authority: int | None = 10,
    path: str,
):
    return TextIndexSource(
        resource_version_ref=version.resource_version_ref,
        lifecycle_state=lifecycle,
        authority_rank=authority,
        repository="synthetic/sr2",
        source_path=path,
        source_version="fixture-v1",
    )


def _assert_exact_partition(content: bytes, segments) -> None:
    assert segments
    assert [item.segment_ordinal for item in segments] == list(
        range(len(segments))
    )
    assert segments[0].source_byte_start == 0
    assert segments[-1].source_byte_end == len(content)
    assert all(
        left.source_byte_end == right.source_byte_start
        for left, right in zip(segments, segments[1:], strict=False)
    )
    rebuilt = b"".join(
        content[item.source_byte_start : item.source_byte_end]
        for item in segments
    )
    assert rebuilt == content
    assert sha256(rebuilt).hexdigest() == sha256(content).hexdigest()
    for item in segments:
        exact = content[item.source_byte_start : item.source_byte_end]
        assert sha256(exact).hexdigest() == item.source_slice_sha256


def test_sr2_deterministic_structure_lifecycle_identity_and_size_rules():
    version_ref = UUID("00000000-0000-0000-0000-000000000001")
    structure = (
        b"preamble\r\n"
        b"---\r\n"
        b"title: demo\r\n"
        b"---\r\n"
        b"# Top ###\r\n"
        b"top body\r\n"
        b"Setext-looking title\r\n"
        b"--------------------\r\n"
        b"- list item\r\n"
        b"| a | b |\r\n"
        b"|---|---|\r\n"
        b"> quote\r\n"
        b"```md\r\n"
        b"# fake heading\r\n"
        b"<!-- kc:retrieval-lifecycle=superseded -->\r\n"
        b"```\r\n"
        b"### Skipped\r\n"
        b"child token\r\n"
        b"## Historical\r\n"
        b"historicalheadingtoken\r\n"
    )
    segments = segment_text_resource(
        content=structure,
        media_type="text/markdown",
        resource_version_ref=version_ref,
        parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
    )
    _assert_exact_partition(structure, segments)
    assert [item.segment_kind for item in segments] == [
        "preamble",
        "section",
        "section",
        "section",
    ]
    assert [item.source_line_start for item in segments] == [1, 5, 17, 19]
    assert segments[1].heading_path[-1].text == "Top"
    assert [(x.level, x.text) for x in segments[2].heading_path] == [
        (1, "Top"),
        (3, "Skipped"),
    ]
    assert [(x.level, x.text) for x in segments[3].heading_path] == [
        (1, "Top"),
        (2, "Historical"),
    ]
    assert all(
        item.lifecycle_state is RetrievalLifecycleState.CURRENT
        for item in segments
    )

    # A heading named Historical is not lifecycle metadata.
    heading_only = segment_text_resource(
        content=b"# Root\n## Historical\nheadingonlytoken\n",
        media_type="text/markdown",
        resource_version_ref=version_ref,
        parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
    )
    assert heading_only[-1].lifecycle_state is RetrievalLifecycleState.CURRENT
    assert heading_only[-1].lifecycle_origin == "document"

    mixed = (
        b"# Atlas Runbook\n"
        b"rootcurrent\n"
        b"## Historical procedure\n"
        b"<!-- kc:retrieval-lifecycle=superseded -->\n"
        b"amberlegacy\n"
        b"### Child\n"
        b"childlegacy\n"
        b"## Current procedure\n"
        b"cedarcurrent\n"
    )
    mixed_segments = segment_text_resource(
        content=mixed,
        media_type="text/markdown",
        resource_version_ref=version_ref,
        parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
    )
    _assert_exact_partition(mixed, mixed_segments)
    assert [x.lifecycle_state.value for x in mixed_segments] == [
        "current",
        "superseded",
        "superseded",
        "current",
    ]
    assert mixed_segments[1].lifecycle_origin == "section-directive"
    assert mixed_segments[1].lifecycle_directive_line == 4
    assert mixed_segments[2].lifecycle_origin == "ancestor-directive"
    assert mixed_segments[2].lifecycle_directive_line == 4
    assert "kc:retrieval-lifecycle" not in mixed_segments[1].local_search_text
    assert (
        "kc:retrieval-lifecycle"
        in mixed[
            mixed_segments[1].source_byte_start : mixed_segments[1].source_byte_end
        ].decode("utf-8")
    )

    for invalid in (
        b"# A\n<!-- kc:retrieval-lifecycle=bad -->\n",
        b"# A\nbody\n<!-- kc:retrieval-lifecycle=superseded -->\n",
        (
            b"# A\n"
            b"<!-- kc:retrieval-lifecycle=unknown -->\n"
            b"<!-- kc:retrieval-lifecycle=superseded -->\n"
        ),
    ):
        with pytest.raises(KnowledgeInvariantError):
            segment_text_resource(
                content=invalid,
                media_type="text/markdown",
                resource_version_ref=version_ref,
                parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
            )

    with pytest.raises(KnowledgeInvariantError, match="promote"):
        segment_text_resource(
            content=(
                b"# Unknown parent\n"
                b"<!-- kc:retrieval-lifecycle=current -->\n"
                b"bad promotion\n"
            ),
            media_type="text/markdown",
            resource_version_ref=version_ref,
            parent_lifecycle_state=RetrievalLifecycleState.UNKNOWN,
        )
    with pytest.raises(KnowledgeInvariantError, match="promote"):
        segment_text_resource(
            content=(
                b"# Parent\n"
                b"<!-- kc:retrieval-lifecycle=superseded -->\n"
                b"parent historical\n"
                b"## Child\n"
                b"<!-- kc:retrieval-lifecycle=current -->\n"
                b"bad descendant promotion\n"
            ),
            media_type="text/markdown",
            resource_version_ref=version_ref,
            parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
        )

    small_profile = SectionSegmentationProfile(
        soft_target_bytes=40,
        hard_max_bytes=64,
    )
    large = b"# Large\n" + b"".join(
        (f"line-{index:02d}-abcdefghijklmnop\n\n").encode("ascii")
        for index in range(12)
    )
    large_first = segment_text_resource(
        content=large,
        media_type="text/markdown",
        resource_version_ref=version_ref,
        parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
        profile=small_profile,
    )
    large_second = segment_text_resource(
        content=large,
        media_type="text/markdown",
        resource_version_ref=version_ref,
        parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
        profile=small_profile,
    )
    _assert_exact_partition(large, large_first)
    assert len(large_first) > 1
    assert all(
        item.source_byte_end - item.source_byte_start
        <= small_profile.hard_max_bytes
        for item in large_first
    )
    assert [
        (item.source_byte_start, item.source_byte_end)
        for item in large_first
    ] == [
        (0, 34),
        (34, 86),
        (86, 138),
        (138, 190),
        (190, 242),
        (242, 294),
        (294, 320),
    ]
    assert [
        (
            item.segment_key,
            item.source_byte_start,
            item.source_byte_end,
            item.source_slice_sha256,
        )
        for item in large_first
    ] == [
        (
            item.segment_key,
            item.source_byte_start,
            item.source_byte_end,
            item.source_slice_sha256,
        )
        for item in large_second
    ]
    assert all(
        item.heading_path == large_first[0].heading_path
        for item in large_first
    )
    assert large_first[0].segment_kind == "section"
    assert all(
        item.segment_kind == "continuation"
        for item in large_first[1:]
    )

    plain = b"".join(
        (f"plain-{index:02d}-abcdefghijklmnop\n").encode("ascii")
        for index in range(8)
    )
    plain_segments = segment_text_resource(
        content=plain,
        media_type="text/plain",
        resource_version_ref=version_ref,
        parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
        profile=small_profile,
    )
    _assert_exact_partition(plain, plain_segments)
    assert plain_segments[0].segment_kind == "document"
    assert all(not item.heading_path for item in plain_segments)

    duplicate = (
        b"# Same\nrepeatmarker\n"
        b"# Same\nrepeatmarker\n"
    )
    duplicate_segments = segment_text_resource(
        content=duplicate,
        media_type="text/markdown",
        resource_version_ref=version_ref,
        parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
    )
    assert len(duplicate_segments) == 2
    assert (
        duplicate_segments[0].source_slice_sha256
        == duplicate_segments[1].source_slice_sha256
    )
    assert duplicate_segments[0].segment_key != duplicate_segments[1].segment_key

    # Path/rename is not an input to segment identity; parent version/profile are.
    rename_rebuild = segment_text_resource(
        content=duplicate,
        media_type="text/markdown",
        resource_version_ref=version_ref,
        parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
    )
    assert [x.segment_key for x in rename_rebuild] == [
        x.segment_key for x in duplicate_segments
    ]

    other_parent = segment_text_resource(
        content=duplicate,
        media_type="text/markdown",
        resource_version_ref=UUID(
            "00000000-0000-0000-0000-000000000002"
        ),
        parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
    )
    assert [x.source_slice_sha256 for x in other_parent] == [
        x.source_slice_sha256 for x in duplicate_segments
    ]
    assert [x.segment_key for x in other_parent] != [
        x.segment_key for x in duplicate_segments
    ]

    changed_profile = SectionSegmentationProfile(
        soft_target_bytes=32,
        hard_max_bytes=64,
    )
    changed = segment_text_resource(
        content=duplicate,
        media_type="text/markdown",
        resource_version_ref=version_ref,
        parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
        profile=changed_profile,
    )
    assert changed_profile.digest != DEFAULT_SECTION_SEGMENTATION_PROFILE.digest
    assert [x.segment_key for x in changed] != [
        x.segment_key for x in duplicate_segments
    ]


def test_sr2_unbreakable_oversized_fence_fails_closed_without_model_fallback():
    profile = SectionSegmentationProfile(
        soft_target_bytes=40,
        hard_max_bytes=64,
    )
    content = (
        b"# Huge\n"
        b"```text\n"
        + (b"x" * 100)
        + b"\n```\n"
    )
    with pytest.raises(KnowledgeInvariantError, match="cannot split"):
        segment_text_resource(
            content=content,
            media_type="text/markdown",
            resource_version_ref=UUID(
                "00000000-0000-0000-0000-000000000003"
            ),
            parent_lifecycle_state=RetrievalLifecycleState.CURRENT,
            profile=profile,
        )


@pytest.mark.postgresql
def test_sr2_segment_generation_retrieval_api_fences_and_profile_rebuild(
    sr2_engine,
    tmp_path,
):
    sessions = create_session_factory(sr2_engine)
    artifacts = LocalArtifactStore(tmp_path / "sr2-artifacts")
    with sessions() as session:
        kernel = RetrievalServiceKnowledgeKernel(
            session,
            artifact_store=artifacts,
        )
        refs = kernel.bootstrap_resource_test_profile()

        legacy = _ingest(
            kernel,
            refs,
            content=b"legacycutover token remains serving",
            path="legacy.txt",
            media_type="text/plain",
        )
        legacy_source = _source(
            legacy,
            path="legacy.txt",
        )
        legacy_generation = kernel.build_text_generation(
            sources=[legacy_source]
        )
        legacy_search = kernel.search_text(query="legacycutover")
        assert legacy_search.generation_id == legacy_generation.generation_id
        assert legacy_search.projection == "resource-version-v1"
        assert legacy_search.results

        oversize = _ingest(
            kernel,
            refs,
            content=(
                b"# Huge\n```text\n"
                + (b"x" * 33000)
                + b"\n```\n"
            ),
            path="oversize-fence.md",
        )
        with pytest.raises(KnowledgeInvariantError, match="cannot split"):
            kernel.build_segment_text_generation(
                sources=[_source(oversize, path="oversize-fence.md")]
            )
        current_after_failure = kernel._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        assert current_after_failure is not None
        assert (
            current_after_failure.generation_id
            == legacy_generation.generation_id
        )
        assert kernel.search_text(query="legacycutover").results

        mixed = _ingest(
            kernel,
            refs,
            content=(
                b"# Atlas Runbook\n"
                b"rootcurrent\n"
                b"## Historical procedure\n"
                b"<!-- kc:retrieval-lifecycle=superseded -->\n"
                b"amberlegacy\n"
                b"## Current procedure\n"
                b"cedarcurrent\n"
                b"### Verification\n"
                b"verifycurrent\n"
            ),
            path="mixed.md",
        )
        heading_only = _ingest(
            kernel,
            refs,
            content=(
                b"# Guide\n"
                b"## Historical\n"
                b"historicalheadingtoken\n"
            ),
            path="heading-only.md",
        )
        authority_best = _ingest(
            kernel,
            refs,
            content=b"ranktoken exact marker\n",
            path="authority-best.txt",
            media_type="text/plain",
        )
        authority_low = _ingest(
            kernel,
            refs,
            content=b"ranktoken exact marker\n",
            path="authority-low.txt",
            media_type="text/plain",
        )
        life_current = _ingest(
            kernel,
            refs,
            content=b"lifetie exact marker\n",
            path="life-current.txt",
            media_type="text/plain",
        )
        life_unknown = _ingest(
            kernel,
            refs,
            content=b"lifetie exact marker\n",
            path="life-unknown.txt",
            media_type="text/plain",
        )
        revision_old = _ingest(
            kernel,
            refs,
            content=b"revisiontie exact marker\n",
            path="revision-old.txt",
            media_type="text/plain",
        )
        revision_new = _ingest(
            kernel,
            refs,
            content=b"revisiontie exact marker\n",
            path="revision-new.txt",
            media_type="text/plain",
        )
        same_parent = _ingest(
            kernel,
            refs,
            content=(
                b"# Same\nsametie marker\n"
                b"# Same\nsametie marker\n"
            ),
            path="same-parent.md",
        )
        restricted = _ingest(
            kernel,
            refs,
            content=b"restrictsegment token\n",
            path="restricted.txt",
            media_type="text/plain",
        )
        safe_after_fence = _ingest(
            kernel,
            refs,
            content=b"restrictsegment token\n",
            path="safe.txt",
            media_type="text/plain",
        )

        sources = [
            _source(mixed, path="mixed.md", authority=10),
            _source(heading_only, path="heading-only.md", authority=10),
            _source(authority_best, path="authority-best.txt", authority=5),
            _source(authority_low, path="authority-low.txt", authority=50),
            _source(life_current, path="life-current.txt", authority=20),
            _source(
                life_unknown,
                path="life-unknown.txt",
                authority=20,
                lifecycle=RetrievalLifecycleState.UNKNOWN,
            ),
            _source(revision_old, path="revision-old.txt", authority=30),
            _source(revision_new, path="revision-new.txt", authority=30),
            _source(same_parent, path="same-parent.md", authority=40),
            _source(restricted, path="restricted.txt", authority=1),
            _source(safe_after_fence, path="safe.txt", authority=10),
        ]
        canonical_counts_before = {
            Resource: _count(session, Resource),
            ResourceVersion: _count(session, ResourceVersion),
            RepositoryDocumentBinding: _count(
                session, RepositoryDocumentBinding
            ),
            RepositorySourceObservation: _count(
                session, RepositorySourceObservation
            ),
        }
        parent_digests_before = {
            version.resource_version_ref: session.get(
                ResourceVersion, version.resource_version_ref
            ).content_digest
            for version in (
                mixed,
                heading_only,
                authority_best,
                authority_low,
                life_current,
                life_unknown,
                revision_old,
                revision_new,
                same_parent,
                restricted,
                safe_after_fence,
            )
        }

        segment_generation = kernel.build_segment_text_generation(
            sources=sources
        )
        current = kernel._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        assert current is not None
        assert current.generation_id == segment_generation.generation_id
        assert current.config_digest == DEFAULT_SECTION_SEGMENTATION_PROFILE.digest
        assert current.model_version == "sr2-segment-v1"

        assert canonical_counts_before == {
            Resource: _count(session, Resource),
            ResourceVersion: _count(session, ResourceVersion),
            RepositoryDocumentBinding: _count(
                session, RepositoryDocumentBinding
            ),
            RepositorySourceObservation: _count(
                session, RepositorySourceObservation
            ),
        }
        assert parent_digests_before == {
            ref: session.get(ResourceVersion, ref).content_digest
            for ref in parent_digests_before
        }

        generation_sources = set(
            session.scalars(
                select(GenerationSource.source_ref_id).where(
                    GenerationSource.generation_id
                    == segment_generation.generation_id
                )
            ).all()
        )
        assert generation_sources == {
            source.resource_version_ref for source in sources
        }

        for source in sources:
            version = session.get(
                ResourceVersion, source.resource_version_ref
            )
            assert version is not None
            content = artifacts.read_bytes(version.artifact_key)
            rows = session.scalars(
                select(ResourceSegmentTextSearch)
                .where(
                    ResourceSegmentTextSearch.generation_id
                    == segment_generation.generation_id,
                    ResourceSegmentTextSearch.resource_version_ref
                    == source.resource_version_ref,
                )
                .order_by(ResourceSegmentTextSearch.segment_ordinal)
            ).all()
            assert rows
            assert [row.segment_ordinal for row in rows] == list(
                range(len(rows))
            )
            assert rows[0].source_byte_start == 0
            assert rows[-1].source_byte_end == len(content)
            assert all(
                left.source_byte_end == right.source_byte_start
                for left, right in zip(rows, rows[1:], strict=False)
            )
            rebuilt = b"".join(
                content[row.source_byte_start : row.source_byte_end]
                for row in rows
            )
            assert rebuilt == content
            for row in rows:
                exact = content[
                    row.source_byte_start : row.source_byte_end
                ]
                assert sha256(exact).hexdigest() == row.source_slice_sha256

        assert kernel.search_text(query="amberlegacy").results == ()
        historical = kernel.search_text(
            query="amberlegacy",
            include_superseded=True,
        )
        assert len(historical.results) == 1
        historical_hit = historical.results[0]
        assert historical_hit.resource_version_ref == mixed.resource_version_ref
        assert historical_hit.lifecycle_state is RetrievalLifecycleState.SUPERSEDED
        assert historical_hit.parent_lifecycle_state is RetrievalLifecycleState.CURRENT
        assert historical_hit.lifecycle_origin == "section-directive"
        assert historical_hit.source_path == "mixed.md"

        current_hit = kernel.search_text(query="cedarcurrent")
        assert current_hit.projection == "resource-segment-v1"
        assert (
            current_hit.profile_digest
            == DEFAULT_SECTION_SEGMENTATION_PROFILE.digest
        )
        assert current_hit.results
        assert all(
            item.lifecycle_state is not RetrievalLifecycleState.SUPERSEDED
            for item in current_hit.results
        )

        no_heuristic = kernel.search_text(query="historicalheadingtoken")
        assert len(no_heuristic.results) == 1
        assert (
            no_heuristic.results[0].lifecycle_state
            is RetrievalLifecycleState.CURRENT
        )

        ranked_authority = kernel.search_text(query="ranktoken")
        assert [x.source_path for x in ranked_authority.results] == [
            "authority-best.txt",
            "authority-low.txt",
        ]

        ranked_lifecycle = kernel.search_text(
            query="lifetie",
            include_superseded=True,
        )
        assert [x.source_path for x in ranked_lifecycle.results] == [
            "life-current.txt",
            "life-unknown.txt",
        ]

        ranked_revision = kernel.search_text(query="revisiontie")
        assert [x.source_path for x in ranked_revision.results] == [
            "revision-new.txt",
            "revision-old.txt",
        ]

        same_expected = [
            row.segment_key
            for row in session.scalars(
                select(ResourceSegmentTextSearch)
                .where(
                    ResourceSegmentTextSearch.generation_id
                    == segment_generation.generation_id,
                    ResourceSegmentTextSearch.resource_version_ref
                    == same_parent.resource_version_ref,
                )
                .order_by(ResourceSegmentTextSearch.segment_ordinal)
            ).all()
        ]
        assert len(same_expected) == 2
        for _ in range(10):
            repeated = kernel.search_text(query="sametie")
            assert [x.segment_key for x in repeated.results] == same_expected

        # API exposes exact parent + child provenance, not copied body/storage internals.
        transport = TestClient(
            create_app(
                session_factory=sessions,
                artifact_store=artifacts,
            )
        )
        try:
            response = transport.post(
                "/v1/retrieval/search",
                headers=_CALLER,
                json={"query": "cedarcurrent", "limit": 10},
            )
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["projection"] == "resource-segment-v1"
            assert (
                payload["profile_digest"]
                == DEFAULT_SECTION_SEGMENTATION_PROFILE.digest
            )
            api_hit = payload["results"][0]
            assert api_hit["resource_version_ref"] == str(
                mixed.resource_version_ref
            )
            assert api_hit["content_digest"] == session.get(
                ResourceVersion,
                mixed.resource_version_ref,
            ).content_digest
            assert api_hit["segment_key"].startswith("sha256:")
            assert api_hit["source_byte_end"] > api_hit["source_byte_start"]
            assert api_hit["source_line_start"] >= 1
            assert api_hit["source_slice_sha256"]
            assert api_hit["heading_path"]

            blank = transport.post(
                "/v1/retrieval/search",
                headers=_CALLER,
                json={"query": "   "},
            )
            assert blank.status_code == 422
            irrelevant = transport.post(
                "/v1/retrieval/search",
                headers=_CALLER,
                json={"query": "interplanetary penguin theorem"},
            )
            assert irrelevant.status_code == 200
            assert irrelevant.json()["results"] == []

            openapi_text = transport.get("/openapi.json").text.lower()
            response_text = response.text.lower()
            for forbidden in (
                "knowledge_core_database_url",
                "database_url",
                "artifact_key",
                "artifact_backend",
                "repository_root",
                "repository_token",
            ):
                assert forbidden not in openapi_text
                assert forbidden not in response_text
            assert str(artifacts.root).lower() not in response_text
        finally:
            transport.close()

        columns = {
            column["name"]
            for column in inspect(sr2_engine).get_columns(
                "resource_segment_text_search",
                schema="kc_derived",
            )
        }
        assert "search_vector" in columns
        assert not {
            "body",
            "body_text",
            "content",
            "content_text",
            "segment_text",
        } & columns

        restricted_row = session.scalars(
            select(ResourceSegmentTextSearch).where(
                ResourceSegmentTextSearch.generation_id
                == segment_generation.generation_id,
                ResourceSegmentTextSearch.resource_version_ref
                == restricted.resource_version_ref,
            )
        ).one()
        kernel.fence_target_operation(
            operation_id=uuid4(),
            target_ref=restricted.resource_version_ref,
            action_type=DeletionActionType.RESTRICT,
            policy_scope_id="sr2-parent-fence",
            caller_principal_ref="sr2-privacy-controller",
        )
        assert _count(
            session,
            ResourceSegmentTextSearch,
        ) >= 1
        assert session.scalar(
            select(func.count())
            .select_from(ResourceSegmentTextSearch)
            .where(
                ResourceSegmentTextSearch.generation_id
                == segment_generation.generation_id,
                ResourceSegmentTextSearch.resource_version_ref
                == restricted.resource_version_ref,
            )
        ) == 0

        session.execute(
            insert(ResourceSegmentTextSearch).values(
                generation_id=segment_generation.generation_id,
                resource_version_ref=restricted.resource_version_ref,
                segment_ordinal=999,
                segment_key="sha256:" + ("f" * 64),
                segment_kind="document",
                base_block_ordinal=999,
                part_index=1,
                part_count=1,
                source_byte_start=0,
                source_byte_end=1,
                source_line_start=1,
                source_line_end=1,
                source_slice_sha256=sha256(b"x").hexdigest(),
                heading_path=[],
                lifecycle_state="current",
                parent_lifecycle_state="current",
                lifecycle_origin="document",
                lifecycle_directive_line=None,
                authority_rank=1,
                repository=restricted_row.repository,
                source_path=restricted_row.source_path,
                source_version=restricted_row.source_version,
                observed_at=restricted_row.observed_at,
                search_vector=func.to_tsvector(
                    _ENGLISH_REGCONFIG,
                    "restrictsegment token",
                ),
            )
        )
        session.commit()
        post_fence = kernel.search_text(
            query="restrictsegment",
            limit=1,
        )
        assert len(post_fence.results) == 1
        assert post_fence.results[0].resource_version_ref == (
            safe_after_fence.resource_version_ref
        )

        # A profile change creates a new generation/key space without canonical mutation.
        keys_before_profile_change = {
            row.resource_version_ref: tuple(
                item.segment_key
                for item in session.scalars(
                    select(ResourceSegmentTextSearch)
                    .where(
                        ResourceSegmentTextSearch.generation_id
                        == segment_generation.generation_id,
                        ResourceSegmentTextSearch.resource_version_ref
                        == row.resource_version_ref,
                    )
                    .order_by(ResourceSegmentTextSearch.segment_ordinal)
                ).all()
            )
            for row in sources[:2]
        }
        profile2 = SectionSegmentationProfile(
            soft_target_bytes=8192,
            hard_max_bytes=32768,
        )
        canonical_version_count = _count(session, ResourceVersion)
        generation2 = kernel.build_segment_text_generation(
            sources=sources[:2],
            profile=profile2,
        )
        assert generation2.config_digest == profile2.digest
        assert generation2.generation_id != segment_generation.generation_id
        assert _count(session, ResourceVersion) == canonical_version_count
        assert (
            kernel._generation_kernel()
            .current_generation(derived_kind=DerivedKind.TEXT)
            .generation_id
            == generation2.generation_id
        )
        for source in sources[:2]:
            after_keys = tuple(
                item.segment_key
                for item in session.scalars(
                    select(ResourceSegmentTextSearch)
                    .where(
                        ResourceSegmentTextSearch.generation_id
                        == generation2.generation_id,
                        ResourceSegmentTextSearch.resource_version_ref
                        == source.resource_version_ref,
                    )
                    .order_by(ResourceSegmentTextSearch.segment_ordinal)
                ).all()
            )
            assert after_keys
            assert after_keys != keys_before_profile_change[
                source.resource_version_ref
            ]
        assert kernel.search_text(query="ranktoken").results == ()


@pytest.mark.postgresql
def test_sr2_same_profile_rebuild_rename_and_edit_identity(
    sr2_engine,
    tmp_path,
):
    sessions = create_session_factory(sr2_engine)
    artifacts = LocalArtifactStore(tmp_path / "rebuild-artifacts")
    with sessions() as session:
        kernel = RetrievalServiceKnowledgeKernel(
            session,
            artifact_store=artifacts,
        )
        refs = kernel.bootstrap_resource_test_profile()
        original = _ingest(
            kernel,
            refs,
            content=(
                b"# Alpha\n"
                b"alpha deterministic section\n"
                b"## Detail\n"
                b"detail marker\n"
            ),
            path="docs/alpha.md",
        )
        first = kernel.build_segment_text_generation(
            sources=[_source(original, path="docs/alpha.md")]
        )
        first_rows = session.scalars(
            select(ResourceSegmentTextSearch)
            .where(
                ResourceSegmentTextSearch.generation_id
                == first.generation_id
            )
            .order_by(ResourceSegmentTextSearch.segment_ordinal)
        ).all()
        first_payload = [
            (
                row.segment_key,
                row.segment_ordinal,
                row.segment_kind,
                row.base_block_ordinal,
                row.part_index,
                row.part_count,
                row.source_byte_start,
                row.source_byte_end,
                row.source_line_start,
                row.source_line_end,
                row.source_slice_sha256,
                row.heading_path,
                row.lifecycle_state,
                row.parent_lifecycle_state,
                row.lifecycle_origin,
                row.lifecycle_directive_line,
            )
            for row in first_rows
        ]

        # Source-path rename alone is metadata: same exact parent/profile -> same keys.
        second = kernel.build_segment_text_generation(
            sources=[_source(original, path="docs/renamed-alpha.md")]
        )
        assert second.generation_id != first.generation_id
        second_rows = session.scalars(
            select(ResourceSegmentTextSearch)
            .where(
                ResourceSegmentTextSearch.generation_id
                == second.generation_id
            )
            .order_by(ResourceSegmentTextSearch.segment_ordinal)
        ).all()
        second_payload = [
            (
                row.segment_key,
                row.segment_ordinal,
                row.segment_kind,
                row.base_block_ordinal,
                row.part_index,
                row.part_count,
                row.source_byte_start,
                row.source_byte_end,
                row.source_line_start,
                row.source_line_end,
                row.source_slice_sha256,
                row.heading_path,
                row.lifecycle_state,
                row.parent_lifecycle_state,
                row.lifecycle_origin,
                row.lifecycle_directive_line,
            )
            for row in second_rows
        ]
        assert second_payload == first_payload
        assert {row.source_path for row in second_rows} == {
            "docs/renamed-alpha.md"
        }

        edited = kernel.ingest_resource_version(
            resource_ref=original.resource_ref,
            content=(
                b"# Alpha revised\n"
                b"alpha deterministic section\n"
                b"## Detail\n"
                b"detail marker moved by edit\n"
            ),
            ingestion_kind_revision_ref=refs.resource_ingestion_kind_revision_ref,
            media_type="text/markdown",
            locator_kind=ResourceLocatorKind.PATH,
            locator_text="docs/renamed-alpha.md",
        )
        assert edited.resource_ref == original.resource_ref
        assert edited.resource_version_ref != original.resource_version_ref

        third = kernel.build_segment_text_generation(
            sources=[_source(edited, path="docs/renamed-alpha.md")]
        )
        third_keys = [
            row.segment_key
            for row in session.scalars(
                select(ResourceSegmentTextSearch)
                .where(
                    ResourceSegmentTextSearch.generation_id
                    == third.generation_id
                )
                .order_by(ResourceSegmentTextSearch.segment_ordinal)
            ).all()
        ]
        assert third_keys
        assert third_keys != [row.segment_key for row in second_rows]
        assert (
            kernel._generation_kernel()
            .current_generation(derived_kind=DerivedKind.TEXT)
            .generation_id
            == third.generation_id
        )


@pytest.mark.postgresql
def test_sr2_late_finisher_cannot_replace_newer_segment_generation(
    sr2_engine,
    tmp_path,
):
    sessions = create_session_factory(sr2_engine)
    artifacts = LocalArtifactStore(tmp_path / "late-artifacts")
    with sessions() as session:
        kernel = RetrievalServiceKnowledgeKernel(
            session,
            artifact_store=artifacts,
        )
        refs = kernel.bootstrap_resource_test_profile()
        seed = _ingest(
            kernel,
            refs,
            content=b"seed token\n",
            path="seed.txt",
            media_type="text/plain",
        )
        kernel.build_segment_text_generation(
            sources=[_source(seed, path="seed.txt")]
        )

        outer = _ingest(
            kernel,
            refs,
            content=b"outerlate token\n",
            path="outer.txt",
            media_type="text/plain",
        )
        newer = _ingest(
            kernel,
            refs,
            content=b"newerwins token\n",
            path="newer.txt",
            media_type="text/plain",
        )
        captured: dict[str, object] = {}

        def publish_newer(_outer_generation):
            captured["generation"] = kernel.build_segment_text_generation(
                sources=[_source(newer, path="newer.txt")]
            )

        with pytest.raises(GenerationFenceError):
            kernel.build_segment_text_generation(
                sources=[_source(outer, path="outer.txt")],
                before_settle_hook=publish_newer,
            )

        newer_generation = captured["generation"]
        current = kernel._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        assert current is not None
        assert current.generation_id == newer_generation.generation_id
        assert kernel.search_text(query="newerwins").results
        assert kernel.search_text(query="outerlate").results == ()

        statuses = {
            row.generation_id: row.status
            for row in session.scalars(select(DerivedGeneration)).all()
        }
        assert statuses[current.generation_id] == "current"
        assert "stale" in statuses.values()


@pytest.mark.postgresql
def test_sr2_g22_tiny_pinned_real_document_pilot(
    sr2_engine,
    tmp_path,
):
    manifest = json.loads(_PILOT_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_commit"] == (
        "1d1313844aa4d224bd42c0888970a11e959d9501"
    )
    assert manifest["previous_manifest_digest"] is None
    assert manifest["retirements"] == []
    expected = {
        "docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md": (
            "c45034da0d72a8ed3d8ac1cec0101a6bc4dc9eeb",
            "current",
            10,
        ),
        "docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md": (
            "bc12a15dbac70e1ba538e313ce87dfed41b9e831",
            "superseded",
            10,
        ),
        "docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md": (
            "07f878a0e860433fd55cfe7d2fd7fb861f5cb2a2",
            "current",
            20,
        ),
    }
    assert {
        entry["path"]: (
            entry["git_blob_sha"],
            entry["retrieval_lifecycle"],
            entry["authority_rank"],
        )
        for entry in manifest["entries"]
    } == expected

    reader = GitRepositorySourceReader(
        repository_locator=manifest["repository_locator"],
        repository_root=_REPO_ROOT,
    )
    sessions = create_session_factory(sr2_engine)
    artifacts = LocalArtifactStore(tmp_path / "real-pilot-artifacts")
    with sessions() as session:
        kernel = SectionRepositoryImportKnowledgeKernel(
            session,
            artifact_store=artifacts,
            source_readers={
                manifest["source_repository_key"]: reader,
            },
        )
        plan = kernel.plan_repository_import(manifest)
        receipt = kernel.apply_repository_import(
            manifest=manifest,
            expected_plan_digest=plan.plan_digest,
        )
        assert receipt.status == "settled"
        assert receipt.resulting_text_generation_id is not None

        assert _count(session, RepositoryDocumentBinding) == 3
        assert _count(session, RepositoryImportReceipt) == 1
        assert _count(session, RepositorySourceObservation) == 3
        assert _count(session, Resource) == 3
        assert _count(session, ResourceVersion) == 3
        assert _count(session, ResourceTextSearch) == 3
        assert _count(session, ResourceSegmentTextSearch) > 3

        current = kernel._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        assert current is not None
        assert current.generation_id == receipt.resulting_text_generation_id
        assert current.model_version == "sr2-segment-v1"
        assert current.config_digest == DEFAULT_SECTION_SEGMENTATION_PROFILE.digest

        ri4_path = (
            "docs/architecture/knowledge-core/RI4_INTENDED_HOST_EVIDENCE.md"
        )
        ri2_path = (
            "docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md"
        )
        rf1_path = (
            "docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md"
        )

        ri4_rows = session.scalars(
            select(ResourceSegmentTextSearch).where(
                ResourceSegmentTextSearch.generation_id
                == current.generation_id,
                ResourceSegmentTextSearch.source_path == ri4_path,
            )
        ).all()
        assert ri4_rows
        assert {row.lifecycle_state for row in ri4_rows} == {"current"}
        assert {row.lifecycle_origin for row in ri4_rows} == {"document"}

        ri2_rows = session.scalars(
            select(ResourceSegmentTextSearch).where(
                ResourceSegmentTextSearch.generation_id
                == current.generation_id,
                ResourceSegmentTextSearch.source_path == ri2_path,
            )
        ).all()
        assert ri2_rows
        assert {row.lifecycle_state for row in ri2_rows} == {"superseded"}
        assert {row.parent_lifecycle_state for row in ri2_rows} == {
            "superseded"
        }

        default_history = kernel.search_text(query="rename heuristics")
        assert all(
            item.source_path != ri2_path
            for item in default_history.results
        )
        explicit_history = kernel.search_text(
            query="rename heuristics",
            include_superseded=True,
        )
        ri2_hits = [
            item for item in explicit_history.results
            if item.source_path == ri2_path
        ]
        assert ri2_hits
        assert all(
            item.lifecycle_state is RetrievalLifecycleState.SUPERSEDED
            for item in ri2_hits
        )

        ri4_query = kernel.search_text(query="serving separation")
        ri4_hits = [
            item for item in ri4_query.results
            if item.source_path == ri4_path
        ]
        assert ri4_hits
        retrieval_behavior = next(
            item
            for item in ri4_hits
            if item.heading_path
            and item.heading_path[-1]["text"] == "Retrieval behavior"
        )
        ri4_version = session.get(
            ResourceVersion,
            retrieval_behavior.resource_version_ref,
        )
        ri4_bytes = artifacts.read_bytes(ri4_version.artifact_key)
        assert retrieval_behavior.source_byte_start == ri4_bytes.index(
            b"## Retrieval behavior\n"
        )
        assert retrieval_behavior.source_byte_end == ri4_bytes.index(
            b"## Exact provenance and artifact integrity\n"
        )

        rf1_query = kernel.search_text(
            query="synthetic falsification corpus"
        )
        rf1_hits = [
            item for item in rf1_query.results
            if item.source_path == rf1_path
        ]
        assert rf1_hits
        synthetic_section = next(
            item
            for item in rf1_hits
            if item.heading_path
            and item.heading_path[-1]["text"]
            == "Synthetic falsification corpus"
        )
        rf1_version = session.get(
            ResourceVersion,
            synthetic_section.resource_version_ref,
        )
        rf1_bytes = artifacts.read_bytes(rf1_version.artifact_key)
        assert synthetic_section.source_byte_start == rf1_bytes.index(
            b"## Synthetic falsification corpus\n"
        )
        assert synthetic_section.source_byte_end == rf1_bytes.index(
            b"## RF-2 falsifiable acceptance gates\n"
        )

        # Exact replay creates no new canonical or derived state.
        counts_before_replay = {
            model: _count(session, model)
            for model in (
                RepositoryDocumentBinding,
                RepositoryImportReceipt,
                RepositorySourceObservation,
                Resource,
                ResourceVersion,
                ResourceTextSearch,
                ResourceSegmentTextSearch,
                DerivedGeneration,
            )
        }
        replay_plan = kernel.plan_repository_import(manifest)
        assert replay_plan.replay_receipt is not None
        replay = kernel.apply_repository_import(
            manifest=manifest,
            expected_plan_digest=replay_plan.plan_digest,
        )
        assert replay == receipt
        assert {
            model: _count(session, model)
            for model in counts_before_replay
        } == counts_before_replay
