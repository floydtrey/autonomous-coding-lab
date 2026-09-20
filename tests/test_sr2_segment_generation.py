from __future__ import annotations

from hashlib import sha1
import os
from pathlib import Path

import pytest
from sqlalchemy import func, inspect, literal_column, select

from knowledge_core.application.governed_source_selection import (
    resolve_governed_projection_sources,
)
from knowledge_core.application.lifecycle_projection import RetrievalProjectionProfile
from knowledge_core.application.repository_import import RepositoryImportKnowledgeKernel
from knowledge_core.application.section_generation import (
    SR2_SEGMENT_MODEL_IDENTITY,
    SR2_SEGMENT_MODEL_VERSION,
    SectionGenerationKnowledgeKernel,
    segment_generation_config_digest,
)
from knowledge_core.application.segmentation import SectionSegmentationProfile
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind, GenerationStatus
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
)
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.section_retrieval_models import (
    ResourceSegmentTextSearch,
    TextGenerationProfile,
    TextGenerationSource,
)


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_ENGLISH = literal_column("'english'::regconfig")


def _blob_sha(content: bytes) -> str:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


class FakeRepositoryReader:
    def __init__(self):
        self.repository_locator = "memory://sr2-segment-generation"
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


def _entry(
    key: str,
    path: str,
    content: bytes,
    *,
    lifecycle: str = "current",
    authority: int | None = 10,
    classification: str = "approved",
    rationale: str = "explicit SR-2 segment-generation fixture",
) -> dict:
    return {
        "source_document_key": key,
        "path": path,
        "git_blob_sha": _blob_sha(content),
        "media_type": "text/markdown",
        "classification": classification,
        "retrieval_lifecycle": lifecycle,
        "authority_rank": authority,
        "rationale": rationale,
    }


def _manifest(
    *,
    manifest_id: str,
    commit: str,
    entries: list[dict],
    previous: str | None = None,
    retirements: list[dict] | None = None,
) -> dict:
    return {
        "schema_version": 2,
        "manifest_id": manifest_id,
        "source_repository_key": "repo-sr2-generation",
        "repository_locator": "memory://sr2-segment-generation",
        "source_commit": commit,
        "previous_manifest_digest": previous,
        "history_policy": "retain_prior_versions_as_superseded",
        "entries": entries,
        "retirements": retirements or [],
    }


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("SR-2 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("SR-2 segment generation requires PostgreSQL")
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
def sr2_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _kernels(engine, tmp_path: Path, reader: FakeRepositoryReader):
    sessions = create_session_factory(engine)
    session = sessions()
    store = LocalArtifactStore(tmp_path / "artifacts")
    importer = RepositoryImportKnowledgeKernel(
        session,
        artifact_store=store,
        source_readers={"repo-sr2-generation": reader},
    )
    segment_builder = SectionGenerationKnowledgeKernel(
        session,
        artifact_store=store,
    )
    return importer, segment_builder, session


def _apply(importer, manifest):
    plan = importer.plan_repository_import(manifest)
    receipt = importer.apply_repository_import(
        manifest=manifest,
        expected_plan_digest=plan.plan_digest,
    )
    return receipt


def test_sr2_slice5_generation_config_binds_structural_and_projection_profiles():
    baseline = segment_generation_config_digest()
    changed_structural = segment_generation_config_digest(
        structural_profile=SectionSegmentationProfile(
            soft_target_bytes=8192,
            hard_max_bytes=32768,
        )
    )
    changed_projection = segment_generation_config_digest(
        projection_profile=RetrievalProjectionProfile(
            structural_profile_digest=SectionSegmentationProfile().digest,
            lexical_projection="local-minus-own-directive-A-heading-context-B-test",
        )
    )
    assert baseline.startswith("sha256:")
    assert changed_structural.startswith("sha256:")
    assert changed_projection.startswith("sha256:")
    assert changed_structural != baseline
    assert changed_projection != baseline


@pytest.mark.postgresql
def test_sr2_slice5_segment_table_has_lineage_fk_and_no_body_copy(sr2_engine):
    inspector = inspect(sr2_engine)
    columns = {
        item["name"]
        for item in inspector.get_columns(
            "resource_segment_text_search",
            schema="kc_derived",
        )
    }
    assert {
        "generation_id",
        "resource_version_ref",
        "segment_ordinal",
        "segment_key",
        "structural_kind",
        "base_block_ordinal",
        "part_index",
        "part_count",
        "source_byte_start",
        "source_byte_end",
        "source_line_start",
        "source_line_end",
        "source_slice_sha256",
        "heading_path",
        "parent_lifecycle_state",
        "declared_lifecycle_state",
        "declaration_source_line",
        "declaration_byte_start",
        "declaration_byte_end",
        "effective_lifecycle_state",
        "effective_control_provenance",
        "authority_rank",
        "repository",
        "source_repository_key",
        "source_document_key",
        "source_path",
        "source_version",
        "search_vector",
    } == columns
    assert not {"body", "body_text", "segment_text", "raw_text"} & columns

    profile_columns = {
        item["name"]
        for item in inspector.get_columns(
            "text_generation_profile",
            schema="kc_derived",
        )
    }
    assert profile_columns == {
        "generation_id",
        "structural_profile_id",
        "structural_profile_digest",
        "projection_profile_id",
        "projection_profile_digest",
        "generation_config_digest",
    }

    foreign_keys = inspector.get_foreign_keys(
        "resource_segment_text_search",
        schema="kc_derived",
    )
    lineage_fks = [
        item
        for item in foreign_keys
        if item["referred_schema"] == "kc_derived"
        and item["referred_table"] == "text_generation_source"
    ]
    assert len(lineage_fks) == 1
    assert lineage_fks[0]["constrained_columns"] == [
        "generation_id",
        "resource_version_ref",
    ]
    assert lineage_fks[0]["referred_columns"] == [
        "generation_id",
        "resource_version_ref",
    ]


@pytest.mark.postgresql
def test_sr2_slice5_builds_validated_nonserving_candidate_and_preserves_rf2(
    sr2_engine,
    tmp_path,
):
    commit = "a" * 40
    content = (
        b"# Alpha\n"
        b"<!-- kc:retrieval-lifecycle=unknown -->\n"
        b"orchard signal\n"
        b"## Child\n"
        b"banana signal\n"
    )
    reader = FakeRepositoryReader()
    reader.put(commit, "alpha.md", content)
    manifest = _manifest(
        manifest_id="A",
        commit=commit,
        entries=[_entry("alpha", "alpha.md", content, authority=4)],
    )
    importer, segment_builder, session = _kernels(sr2_engine, tmp_path, reader)
    receipt = _apply(importer, manifest)
    rf2_generation = receipt.resulting_text_generation_id
    assert rf2_generation is not None

    candidate = segment_builder.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest
    )
    assert candidate.status is GenerationStatus.BUILDING
    assert candidate.model_identity == SR2_SEGMENT_MODEL_IDENTITY
    assert candidate.model_version == SR2_SEGMENT_MODEL_VERSION
    assert candidate.config_digest == segment_generation_config_digest()

    profile_row = session.get(TextGenerationProfile, candidate.generation_id)
    assert profile_row is not None
    assert profile_row.structural_profile_id == "kc-section-segmentation-v1"
    assert profile_row.structural_profile_digest.startswith("sha256:")
    assert (
        profile_row.projection_profile_id
        == "kc-section-retrieval-projection-v1"
    )
    assert profile_row.projection_profile_digest.startswith("sha256:")
    assert profile_row.generation_config_digest == candidate.config_digest

    current = importer._generation_kernel().current_generation(
        derived_kind=DerivedKind.TEXT
    )
    assert current is not None
    assert current.generation_id == rf2_generation
    rf2_hit = importer.search_text(query="orchard")
    assert rf2_hit.generation_id == rf2_generation
    assert [item.source_path for item in rf2_hit.results] == ["alpha.md"]

    source = resolve_governed_projection_sources(
        session,
        governing_manifest_digest=receipt.manifest_digest,
    )[0]
    lineage = session.get(
        TextGenerationSource,
        {
            "generation_id": candidate.generation_id,
            "resource_version_ref": source.observation.resource_version_ref,
        },
    )
    assert lineage is not None
    assert lineage.source_observation_id == source.observation.observation_id
    assert lineage.governing_manifest_digest == receipt.manifest_digest
    assert lineage.projection_snapshot_digest == source.projection_snapshot_digest

    rows = session.scalars(
        select(ResourceSegmentTextSearch)
        .where(ResourceSegmentTextSearch.generation_id == candidate.generation_id)
        .order_by(ResourceSegmentTextSearch.segment_ordinal)
    ).all()
    assert len(rows) == 2

    alpha, child = rows
    assert alpha.structural_kind == "section"
    assert alpha.parent_lifecycle_state == "current"
    assert alpha.declared_lifecycle_state == "unknown"
    assert alpha.effective_lifecycle_state == "unknown"
    assert alpha.declaration_source_line == 2
    assert alpha.authority_rank == 4
    assert alpha.source_repository_key == "repo-sr2-generation"
    assert alpha.source_document_key == "alpha"
    assert alpha.source_path == "alpha.md"
    assert alpha.source_version == commit
    assert alpha.heading_path[-1]["display_text"] == "Alpha"
    assert alpha.effective_control_provenance == [
        {
            "declaration": {
                "heading_source_byte_start": 0,
                "source_byte_end": 48,
                "source_byte_start": 8,
                "source_line": 2,
            },
            "lifecycle_state": "unknown",
            "origin": "own",
        }
    ]

    assert child.declared_lifecycle_state is None
    assert child.effective_lifecycle_state == "unknown"
    assert child.heading_path[-1]["display_text"] == "Child"
    assert child.effective_control_provenance[0]["origin"] == "ancestor"

    lifecycle_token_matches = session.scalar(
        select(func.count())
        .select_from(ResourceSegmentTextSearch)
        .where(
            ResourceSegmentTextSearch.generation_id == candidate.generation_id,
            ResourceSegmentTextSearch.search_vector.op("@@")(
                func.websearch_to_tsquery(_ENGLISH, "unknown")
            ),
        )
    )
    assert lifecycle_token_matches == 0

    orchard_matches = session.scalar(
        select(func.count())
        .select_from(ResourceSegmentTextSearch)
        .where(
            ResourceSegmentTextSearch.generation_id == candidate.generation_id,
            ResourceSegmentTextSearch.search_vector.op("@@")(
                func.websearch_to_tsquery(_ENGLISH, "orchard")
            ),
        )
    )
    assert orchard_matches == 1

    validated = segment_builder.validate_segment_generation_candidate(
        generation_id=candidate.generation_id,
        governing_manifest_digest=receipt.manifest_digest,
    )
    assert validated.status is GenerationStatus.BUILDING
    session.close()


@pytest.mark.postgresql
def test_sr2_slice5_persists_current_prior_and_retirement_projection_rows(
    sr2_engine,
    tmp_path,
):
    a = "a" * 40
    b = "b" * 40
    alpha_a = b"# Alpha\nlegacy apricot\n"
    alpha_b = b"# Alpha\ncurrent blackberry\n"
    beta = b"# Beta\nretired canyon\n"
    reader = FakeRepositoryReader()
    reader.put(a, "alpha.md", alpha_a)
    reader.put(a, "beta.md", beta)
    reader.put(b, "alpha.md", alpha_b)

    importer, segment_builder, session = _kernels(sr2_engine, tmp_path, reader)
    manifest_a = _manifest(
        manifest_id="A",
        commit=a,
        entries=[
            _entry("alpha", "alpha.md", alpha_a),
            _entry("beta", "beta.md", beta),
        ],
    )
    receipt_a = _apply(importer, manifest_a)

    manifest_b = _manifest(
        manifest_id="B",
        commit=b,
        previous=receipt_a.manifest_digest,
        entries=[_entry("alpha", "alpha.md", alpha_b)],
        retirements=[
            {
                "source_document_key": "beta",
                "reason": "replaced by governed policy",
                "historical_retrieval": "retain",
            }
        ],
    )
    receipt_b = _apply(importer, manifest_b)

    candidate = segment_builder.build_segment_generation_candidate(
        governing_manifest_digest=receipt_b.manifest_digest
    )
    sources = resolve_governed_projection_sources(
        session,
        governing_manifest_digest=receipt_b.manifest_digest,
    )
    assert len(sources) == 3

    rows = session.scalars(
        select(ResourceSegmentTextSearch).where(
            ResourceSegmentTextSearch.generation_id == candidate.generation_id
        )
    ).all()
    assert len(rows) == 3

    by_version = {row.resource_version_ref: row for row in rows}
    for source in sources:
        row = by_version[source.observation.resource_version_ref]
        assert row.parent_lifecycle_state == source.observation.document_lifecycle.value
        assert (
            row.effective_lifecycle_state
            == source.observation.document_lifecycle.value
        )
        lineage = session.get(
            TextGenerationSource,
            {
                "generation_id": candidate.generation_id,
                "resource_version_ref": source.observation.resource_version_ref,
            },
        )
        assert lineage is not None
        assert lineage.source_observation_id == source.observation.observation_id
        assert (
            lineage.projection_snapshot_digest
            == source.projection_snapshot_digest
        )

    current_rows = [row for row in rows if row.effective_lifecycle_state == "current"]
    superseded_rows = [
        row for row in rows if row.effective_lifecycle_state == "superseded"
    ]
    assert len(current_rows) == 1
    assert len(superseded_rows) == 2

    current = importer._generation_kernel().current_generation(
        derived_kind=DerivedKind.TEXT
    )
    assert current is not None
    assert current.generation_id == receipt_b.resulting_text_generation_id
    assert current.generation_id != candidate.generation_id
    session.close()


@pytest.mark.postgresql
def test_sr2_slice5_rejects_invalid_projection_before_candidate_generation(
    sr2_engine,
    tmp_path,
):
    commit = "c" * 40
    content = (
        b"# Bad\n"
        b"<!-- kc:retrieval-lifecycle=banana -->\n"
        b"body\n"
    )
    reader = FakeRepositoryReader()
    reader.put(commit, "bad.md", content)
    manifest = _manifest(
        manifest_id="bad",
        commit=commit,
        entries=[_entry("bad", "bad.md", content)],
    )
    importer, segment_builder, session = _kernels(sr2_engine, tmp_path, reader)
    receipt = _apply(importer, manifest)
    before = session.scalar(select(func.count()).select_from(DerivedGeneration))

    with pytest.raises(KnowledgeInvariantError, match="malformed"):
        segment_builder.build_segment_generation_candidate(
            governing_manifest_digest=receipt.manifest_digest
        )

    after = session.scalar(select(func.count()).select_from(DerivedGeneration))
    assert after == before
    current = importer._generation_kernel().current_generation(
        derived_kind=DerivedKind.TEXT
    )
    assert current is not None
    assert current.generation_id == receipt.resulting_text_generation_id
    session.close()


@pytest.mark.postgresql
def test_sr2_slice5_validation_stales_tampered_candidate_without_cutover(
    sr2_engine,
    tmp_path,
):
    commit = "d" * 40
    content = b"# Stable\nintegrity signal\n"
    reader = FakeRepositoryReader()
    reader.put(commit, "stable.md", content)
    manifest = _manifest(
        manifest_id="stable",
        commit=commit,
        entries=[_entry("stable", "stable.md", content)],
    )
    importer, segment_builder, session = _kernels(sr2_engine, tmp_path, reader)
    receipt = _apply(importer, manifest)
    candidate = segment_builder.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest
    )

    row = session.scalars(
        select(ResourceSegmentTextSearch).where(
            ResourceSegmentTextSearch.generation_id == candidate.generation_id
        )
    ).one()
    row.source_slice_sha256 = "0" * 64
    session.commit()

    with pytest.raises(
        KnowledgeInvariantError,
        match="source_slice_sha256",
    ):
        segment_builder.validate_segment_generation_candidate(
            generation_id=candidate.generation_id,
            governing_manifest_digest=receipt.manifest_digest,
        )

    stale = importer._generation_kernel().read_generation(candidate.generation_id)
    assert stale.status is GenerationStatus.STALE

    current = importer._generation_kernel().current_generation(
        derived_kind=DerivedKind.TEXT
    )
    assert current is not None
    assert current.generation_id == receipt.resulting_text_generation_id
    session.close()
