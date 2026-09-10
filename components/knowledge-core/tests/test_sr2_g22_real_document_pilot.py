from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import func, inspect, select

from knowledge_core.application.repository_source import GitRepositorySourceReader
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.application.segmentation import segment_structural_content
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.repository_import_models import RepositorySourceObservation
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.section_retrieval_models import (
    ResourceSegmentTextSearch,
    TextGenerationSource,
)


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_MANIFEST_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "architecture"
    / "knowledge-core"
    / "SR2_G22_REAL_DOCUMENT_PILOT_MANIFEST.json"
)


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


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("SR2-G22 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("SR2-G22 requires PostgreSQL")
    return engine


def _load_manifest() -> dict:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _observation_by_key(session, manifest_digest: str) -> dict[str, RepositorySourceObservation]:
    rows = session.scalars(
        select(RepositorySourceObservation).where(
            RepositorySourceObservation.manifest_digest == manifest_digest
        )
    ).all()
    return {row.source_document_key: row for row in rows}


def _segment_rows(session, generation_id, document_key: str):
    return session.scalars(
        select(ResourceSegmentTextSearch)
        .where(
            ResourceSegmentTextSearch.generation_id == generation_id,
            ResourceSegmentTextSearch.source_document_key == document_key,
        )
        .order_by(ResourceSegmentTextSearch.segment_ordinal)
    ).all()


def _result_identity(result) -> tuple:
    return tuple(
        (
            hit.resource_version_ref,
            hit.segment.segment_ordinal if hit.segment is not None else None,
            hit.segment.segment_key if hit.segment is not None else None,
        )
        for hit in result.results
    )


@pytest.mark.postgresql
@pytest.mark.sr2_real_pilot
def test_sr2_g22_tiny_pinned_real_document_pilot(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    manifest = _load_manifest()
    listed = {
        entry["source_document_key"]: entry for entry in manifest["entries"]
    }

    assert manifest["source_commit"] == "bb42835442c03478da2b61c3f79b1c41c26e4e92"
    assert set(listed) == {
        "sr2-g22-contract",
        "sr2-g22-current-state",
        "sr2-g22-pause-handoff",
    }
    assert manifest["retirements"] == []

    reader = GitRepositorySourceReader(
        repository_locator=manifest["repository_locator"],
        repository_root=repo_root,
    )
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    session = sessions()
    try:
        exact_sources = {}
        for key, entry in listed.items():
            proof = reader.read_exact(
                source_commit=manifest["source_commit"],
                path=entry["path"],
            )
            assert proof.git_blob_sha == entry["git_blob_sha"]
            assert proof.object_type == "blob"
            assert proof.object_mode in {"100644", "100755"}
            exact_sources[key] = proof

        assert (
            b"kc:retrieval-lifecycle"
            in exact_sources["sr2-g22-contract"].content
        )
        assert (
            b"histor"
            in exact_sources["sr2-g22-current-state"].content.lower()
        )

        kernel = SectionRepositoryImportKnowledgeKernel(
            session,
            artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
            source_readers={manifest["source_repository_key"]: reader},
        )
        plan = kernel.plan_repository_import(manifest)
        receipt = kernel.apply_repository_import(
            manifest=manifest,
            expected_plan_digest=plan.plan_digest,
        )
        assert receipt.status == "settled"
        generation_id = receipt.resulting_text_generation_id
        assert generation_id is not None

        current = kernel._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        assert current is not None
        assert current.generation_id == generation_id

        observations = _observation_by_key(session, receipt.manifest_digest)
        assert set(observations) == set(listed)
        assert session.scalar(
            select(func.count())
            .select_from(RepositorySourceObservation)
            .where(
                RepositorySourceObservation.manifest_digest
                == receipt.manifest_digest
            )
        ) == 3
        assert session.scalar(
            select(func.count())
            .select_from(TextGenerationSource)
            .where(TextGenerationSource.generation_id == generation_id)
        ) == 3

        persisted_paths = set(
            session.scalars(
                select(ResourceSegmentTextSearch.source_path)
                .where(ResourceSegmentTextSearch.generation_id == generation_id)
                .distinct()
            ).all()
        )
        assert persisted_paths == {entry["path"] for entry in listed.values()}

        for key, entry in listed.items():
            observation = observations[key]
            proof = exact_sources[key]
            assert observation.source_commit == manifest["source_commit"]
            assert observation.path == entry["path"]
            assert observation.git_blob_sha == entry["git_blob_sha"]

            version = session.get(ResourceVersion, observation.resource_version_ref)
            assert version is not None
            lineage = session.get(
                TextGenerationSource,
                {
                    "generation_id": generation_id,
                    "resource_version_ref": observation.resource_version_ref,
                },
            )
            assert lineage is not None
            assert lineage.source_observation_id == observation.observation_id
            assert lineage.governing_manifest_digest == receipt.manifest_digest
            assert lineage.projection_snapshot_digest.startswith("sha256:")

            expected = segment_structural_content(
                resource_version_ref=observation.resource_version_ref,
                media_type=entry["media_type"],
                content=proof.content,
            )
            rows = _segment_rows(session, generation_id, key)
            assert len(rows) == len(expected.segments)
            assert b"".join(
                proof.content[row.source_byte_start : row.source_byte_end]
                for row in rows
            ) == proof.content

            for row, structural in zip(rows, expected.segments, strict=True):
                assert row.segment_ordinal == structural.segment_ordinal
                assert row.segment_key == structural.segment_key
                assert row.structural_kind == structural.structural_kind
                assert row.base_block_ordinal == structural.base_block_ordinal
                assert row.part_index == structural.part_index
                assert row.part_count == structural.part_count
                assert row.source_byte_start == structural.source_byte_start
                assert row.source_byte_end == structural.source_byte_end
                assert row.source_line_start == structural.source_line_start
                assert row.source_line_end == structural.source_line_end
                assert row.source_slice_sha256 == structural.source_slice_sha256

        contract_rows = _segment_rows(
            session, generation_id, "sr2-g22-contract"
        )
        assert contract_rows
        assert all(row.parent_lifecycle_state == "current" for row in contract_rows)
        assert all(row.declared_lifecycle_state is None for row in contract_rows)
        assert all(row.effective_lifecycle_state == "current" for row in contract_rows)

        current_state_rows = _segment_rows(
            session, generation_id, "sr2-g22-current-state"
        )
        assert current_state_rows
        assert all(
            row.parent_lifecycle_state == "current" for row in current_state_rows
        )
        assert all(
            row.declared_lifecycle_state is None for row in current_state_rows
        )
        assert all(
            row.effective_lifecycle_state == "current" for row in current_state_rows
        )

        historical_rows = _segment_rows(
            session, generation_id, "sr2-g22-pause-handoff"
        )
        assert historical_rows
        assert all(
            row.parent_lifecycle_state == "superseded" for row in historical_rows
        )
        assert all(
            row.effective_lifecycle_state == "superseded" for row in historical_rows
        )

        default_historical = kernel.search_text(
            query="acceptance order invariant",
            limit=20,
        )
        assert all(
            hit.segment is None
            or hit.segment.source_document_key != "sr2-g22-pause-handoff"
            for hit in default_historical.results
        )
        explicit_historical = kernel.search_text(
            query="acceptance order invariant",
            include_superseded=True,
            limit=20,
        )
        pause_hits = [
            hit
            for hit in explicit_historical.results
            if hit.segment is not None
            and hit.segment.source_document_key == "sr2-g22-pause-handoff"
        ]
        assert pause_hits
        assert all(hit.lifecycle_state.value == "superseded" for hit in pause_hits)

        current_query = kernel.search_text(
            query="qualified runtime test workflow checkpoint",
            limit=20,
        )
        assert current_query.results
        assert current_query.results[0].segment is not None
        assert (
            current_query.results[0].segment.source_document_key
            == "sr2-g22-current-state"
        )

        contract_query = kernel.search_text(
            query="deterministic large block continuation",
            limit=20,
        )
        assert contract_query.results
        assert contract_query.results[0].segment is not None
        assert (
            contract_query.results[0].segment.source_document_key
            == "sr2-g22-contract"
        )

        contract_hit = contract_query.results[0]
        contract_observation = observations["sr2-g22-contract"]
        assert contract_hit.resource_version_ref == contract_observation.resource_version_ref
        assert contract_hit.segment.governed_observation_id == contract_observation.observation_id
        assert (
            contract_hit.segment.governing_manifest_digest
            == receipt.manifest_digest
        )
        assert contract_hit.source_version == manifest["source_commit"]
        assert contract_hit.source_path == listed["sr2-g22-contract"]["path"]

        for query, include_superseded in (
            ("qualified runtime test workflow checkpoint", False),
            ("deterministic large block continuation", False),
            ("acceptance order invariant", True),
        ):
            baseline = kernel.search_text(
                query=query,
                include_superseded=include_superseded,
                limit=20,
            )
            baseline_identity = _result_identity(baseline)
            for _ in range(2):
                repeated = kernel.search_text(
                    query=query,
                    include_superseded=include_superseded,
                    limit=20,
                )
                assert repeated.generation_id == generation_id
                assert _result_identity(repeated) == baseline_identity
    finally:
        session.close()
        _truncate_kernel_tables(engine)
        engine.dispose()
