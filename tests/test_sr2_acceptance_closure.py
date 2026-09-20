from __future__ import annotations

from hashlib import sha1
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, insert, inspect, literal_column, select

from knowledge_core.api.retrieval_schemas import (
    RetrievalHitResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    SegmentRetrievalProvenanceResponse,
)
from knowledge_core.application.lifecycle_projection import RetrievalProjectionProfile
from knowledge_core.application.repository_import import RepositoryImportKnowledgeKernel
from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.application.section_generation import SectionGenerationKnowledgeKernel
from knowledge_core.application.section_publication import SectionPublicationKnowledgeKernel
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.application.segmentation import (
    DEFAULT_SECTION_SEGMENTATION_PROFILE,
    SectionSegmentationProfile,
    segment_structural_content,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.deletion import DeletionActionType
from knowledge_core.domain.generations import DerivedKind, GenerationStatus
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.repository_import_models import RepositorySourceObservation
from knowledge_core.storage.resource_models import Resource, ResourceVersion
from knowledge_core.storage.section_retrieval_models import (
    ResourceSegmentTextSearch,
    TextGenerationProfile,
    TextGenerationSource,
)


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_REPOSITORY_KEY = "repo-sr2-g1-g21-closure"
_REPOSITORY_LOCATOR = "memory://sr2-g1-g21-closure"
_ENGLISH = literal_column("'english'::regconfig")


def _blob_sha(content: bytes) -> str:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


class FakeRepositoryReader:
    def __init__(self):
        self.repository_locator = _REPOSITORY_LOCATOR
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
    rationale: str = "explicit SR-2 G1-G21 closure fixture",
    media_type: str = "text/markdown",
) -> dict:
    return {
        "source_document_key": key,
        "path": path,
        "git_blob_sha": _blob_sha(content),
        "media_type": media_type,
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
        "source_repository_key": _REPOSITORY_KEY,
        "repository_locator": _REPOSITORY_LOCATOR,
        "source_commit": commit,
        "previous_manifest_digest": previous,
        "history_policy": "retain_prior_versions_as_superseded",
        "entries": entries,
        "retirements": retirements or [],
    }


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("SR-2 G1-G21 closure PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("SR-2 G1-G21 closure requires PostgreSQL")
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
    base = RepositoryImportKnowledgeKernel(
        session,
        artifact_store=store,
        source_readers={_REPOSITORY_KEY: reader},
    )
    section_importer = SectionRepositoryImportKnowledgeKernel(
        session,
        artifact_store=store,
        source_readers={_REPOSITORY_KEY: reader},
    )
    builder = SectionGenerationKnowledgeKernel(session, artifact_store=store)
    publisher = SectionPublicationKnowledgeKernel(session, artifact_store=store)
    retrieval = RetrievalServiceKnowledgeKernel(session, artifact_store=store)
    return sessions, session, store, base, section_importer, builder, publisher, retrieval


def _apply(importer, manifest, **kwargs):
    plan = importer.plan_repository_import(manifest)
    receipt = importer.apply_repository_import(
        manifest=manifest,
        expected_plan_digest=plan.plan_digest,
        **kwargs,
    )
    return plan, receipt


def _observation(session, manifest_digest: str, key: str) -> RepositorySourceObservation:
    return session.execute(
        select(RepositorySourceObservation).where(
            RepositorySourceObservation.manifest_digest == manifest_digest,
            RepositorySourceObservation.source_document_key == key,
        )
    ).scalar_one()


def _version_snapshot(row: ResourceVersion) -> tuple:
    return (
        row.ref_id,
        row.resource_ref_id,
        row.content_digest_algo,
        row.content_digest,
        int(row.byte_size),
        row.media_type,
        row.artifact_backend,
        row.artifact_key,
        row.observed_occurrence_ref,
        int(row.created_revision_id),
    )


def _observation_snapshot(row: RepositorySourceObservation) -> tuple:
    return (
        row.observation_id,
        row.manifest_digest,
        row.source_repository_key,
        row.source_document_key,
        row.source_commit,
        row.path,
        row.git_blob_sha,
        row.resource_ref,
        row.resource_version_ref,
        row.classification,
        row.retrieval_lifecycle,
        row.authority_rank,
        row.rationale,
    )


def _segment_payloads(session, generation_id: UUID):
    rows = session.scalars(
        select(ResourceSegmentTextSearch)
        .where(ResourceSegmentTextSearch.generation_id == generation_id)
        .order_by(
            ResourceSegmentTextSearch.resource_version_ref,
            ResourceSegmentTextSearch.segment_ordinal,
        )
    ).all()
    return tuple(
        tuple(
            (column.name, getattr(row, column.name))
            for column in ResourceSegmentTextSearch.__table__.columns
            if column.name != "generation_id"
        )
        for row in rows
    )


def _lineage_payloads(session, generation_id: UUID):
    rows = session.scalars(
        select(TextGenerationSource)
        .where(TextGenerationSource.generation_id == generation_id)
        .order_by(TextGenerationSource.resource_version_ref)
    ).all()
    return tuple(
        (
            row.resource_version_ref,
            row.source_observation_id,
            row.governing_manifest_digest,
            row.projection_snapshot_digest,
        )
        for row in rows
    )


def _profile_payload(session, generation_id: UUID) -> tuple:
    row = session.get(TextGenerationProfile, generation_id)
    assert row is not None
    return (
        row.structural_profile_id,
        row.structural_profile_digest,
        row.projection_profile_id,
        row.projection_profile_digest,
        row.generation_config_digest,
    )


def _segment_rows(session, generation_id: UUID, key: str):
    return session.scalars(
        select(ResourceSegmentTextSearch)
        .where(
            ResourceSegmentTextSearch.generation_id == generation_id,
            ResourceSegmentTextSearch.source_document_key == key,
        )
        .order_by(ResourceSegmentTextSearch.segment_ordinal)
    ).all()


def _result_identities(result):
    return tuple(
        (
            hit.resource_version_ref,
            hit.segment.segment_ordinal if hit.segment is not None else None,
            hit.segment.segment_key if hit.segment is not None else None,
        )
        for hit in result.results
    )


def test_sr2_g16_profile_declares_exact_deterministic_total_order():
    profile = RetrievalProjectionProfile(
        structural_profile_digest=DEFAULT_SECTION_SEGMENTATION_PROFILE.digest
    )
    assert profile.canonical_config["ranking"] == [
        "lexical_score:desc",
        "effective_lifecycle:current-unknown-superseded",
        "authority_rank:asc:nulls-last",
        "parent_created_revision_id:desc",
        "resource_version_ref:asc",
        "segment_ordinal:asc",
        "segment_key:asc",
    ]


def test_sr2_g8_identical_slices_at_distinct_coordinates_keep_distinct_keys():
    content = b"# Same\nbody\n# Same\nbody\n"
    result = segment_structural_content(
        resource_version_ref=UUID("11111111-1111-1111-1111-111111111111"),
        media_type="text/markdown",
        content=content,
    )
    assert len(result.segments) == 2
    first, second = result.segments
    assert (
        content[first.source_byte_start : first.source_byte_end]
        == content[second.source_byte_start : second.source_byte_end]
    )
    assert first.source_slice_sha256 == second.source_slice_sha256
    assert first.source_byte_start != second.source_byte_start
    assert first.segment_ordinal != second.segment_ordinal
    assert first.segment_key != second.segment_key


def test_sr2_g1_g21_qualification_boundary_excludes_g22_marker():
    component_root = Path(__file__).resolve().parents[1]
    repo_root = component_root
    pyproject = (component_root / "pyproject.toml").read_text(encoding="utf-8")
    workflow = (repo_root / ".github" / "workflows" / "knowledge-core.yml").read_text(
        encoding="utf-8"
    )
    assert '"sr2_real_pilot:' in pyproject
    assert 'python -m pytest -q -m "not postgresql and not sr2_real_pilot"' in workflow
    assert 'python -m pytest -q -m "postgresql and not sr2_real_pilot"' in workflow


def test_sr2_g18_g19_g20_public_contract_is_bounded_and_has_no_model_dependency():
    with pytest.raises(ValidationError):
        RetrievalSearchRequest(query="   ")
    with pytest.raises(ValidationError):
        RetrievalSearchRequest(query="bounded", limit=0)
    with pytest.raises(ValidationError):
        RetrievalSearchRequest(query="bounded", limit=51)

    public_fields = (
        set(RetrievalSearchResponse.model_fields)
        | set(RetrievalHitResponse.model_fields)
        | set(SegmentRetrievalProvenanceResponse.model_fields)
    )
    for forbidden in {
        "artifact_key",
        "artifact_backend",
        "artifact_path",
        "database_url",
        "repository_credentials",
        "raw_sql",
    }:
        assert forbidden not in public_fields

    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    ).lower()
    for forbidden_dependency in (
        "openai",
        "anthropic",
        "transformers",
        "sentence-transformers",
        "tiktoken",
        "chromadb",
        "qdrant",
        "pinecone",
        "weaviate",
        "faiss",
    ):
        assert forbidden_dependency not in pyproject

    source_root = Path(__file__).resolve().parents[1] / "knowledge_core"
    source_text = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in sorted(source_root.rglob("*.py"))
    )
    for forbidden_source_dependency in (
        "import openai",
        "from openai",
        "import anthropic",
        "from anthropic",
        "import transformers",
        "from transformers",
        "import tiktoken",
        "from tiktoken",
        "import chromadb",
        "from chromadb",
        "import qdrant",
        "from qdrant",
        "import pinecone",
        "from pinecone",
        "import weaviate",
        "from weaviate",
        "import faiss",
        "from faiss",
        "openai_api_key",
        "anthropic_api_key",
    ):
        assert forbidden_source_dependency not in source_text


@pytest.mark.postgresql
def test_sr2_g1_g7_complete_rebuild_is_reproducible_without_source_mutation(
    sr2_engine,
    tmp_path,
):
    commit = "1" * 40
    content = (
        b"# Alpha\n"
        b"<!-- kc:retrieval-lifecycle=unknown -->\n"
        b"rebuild sentinel\n"
        b"## Child\n"
        b"rebuild child\n"
    )
    reader = FakeRepositoryReader()
    reader.put(commit, "alpha.md", content)
    manifest = _manifest(
        manifest_id="g1-g7",
        commit=commit,
        entries=[_entry("alpha", "alpha.md", content, authority=4)],
    )
    (
        _sessions,
        session,
        store,
        base,
        _section_importer,
        builder,
        _publisher,
        _retrieval,
    ) = _kernels(sr2_engine, tmp_path, reader)
    _plan, receipt = _apply(base, manifest)

    observation = _observation(session, receipt.manifest_digest, "alpha")
    version = session.get(ResourceVersion, observation.resource_version_ref)
    assert version is not None
    version_before = _version_snapshot(version)
    observation_before = _observation_snapshot(observation)
    artifact_before = store.read_bytes(version.artifact_key)
    resource_count_before = session.scalar(select(func.count()).select_from(Resource))
    version_count_before = session.scalar(select(func.count()).select_from(ResourceVersion))
    observation_count_before = session.scalar(
        select(func.count()).select_from(RepositorySourceObservation)
    )

    first = builder.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest
    )
    second = builder.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest
    )

    assert first.generation_id != second.generation_id
    assert _segment_payloads(session, first.generation_id) == _segment_payloads(
        session, second.generation_id
    )
    assert _lineage_payloads(session, first.generation_id) == _lineage_payloads(
        session, second.generation_id
    )
    assert _profile_payload(session, first.generation_id) == _profile_payload(
        session, second.generation_id
    )

    version_after = session.get(ResourceVersion, observation.resource_version_ref)
    observation_after = _observation(session, receipt.manifest_digest, "alpha")
    assert version_after is not None
    assert _version_snapshot(version_after) == version_before
    assert _observation_snapshot(observation_after) == observation_before
    assert store.read_bytes(version_after.artifact_key) == artifact_before == content
    assert session.scalar(select(func.count()).select_from(Resource)) == resource_count_before
    assert session.scalar(select(func.count()).select_from(ResourceVersion)) == version_count_before
    assert session.scalar(
        select(func.count()).select_from(RepositorySourceObservation)
    ) == observation_count_before
    session.close()


@pytest.mark.postgresql
def test_sr2_g6_oversized_structural_failure_keeps_rf2_current_and_serving(
    sr2_engine,
    tmp_path,
):
    commit = "2" * 40
    content = b"oversize sentinel " + (b"x " * 17000)
    assert len(content) > DEFAULT_SECTION_SEGMENTATION_PROFILE.hard_max_bytes

    reader = FakeRepositoryReader()
    reader.put(commit, "oversize.txt", content)
    manifest = _manifest(
        manifest_id="g6",
        commit=commit,
        entries=[
            _entry(
                "oversize",
                "oversize.txt",
                content,
                media_type="text/plain",
            )
        ],
    )
    (
        _sessions,
        session,
        _store,
        base,
        _section_importer,
        builder,
        _publisher,
        retrieval,
    ) = _kernels(sr2_engine, tmp_path, reader)
    _plan, receipt = _apply(base, manifest)
    rf2_generation = receipt.resulting_text_generation_id
    assert rf2_generation is not None
    before = retrieval.search_text(query="oversize sentinel")
    assert before.generation_id == rf2_generation
    assert before.results

    with pytest.raises(KnowledgeInvariantError, match="no legal boundary"):
        builder.build_segment_generation_candidate(
            governing_manifest_digest=receipt.manifest_digest
        )

    current = builder._generation_kernel().current_generation(
        derived_kind=DerivedKind.TEXT
    )
    assert current is not None
    assert current.generation_id == rf2_generation
    after = retrieval.search_text(query="oversize sentinel")
    assert after.generation_id == rf2_generation
    assert after.retrieval_mode == "resource_version"
    assert after.results
    session.close()


@pytest.mark.postgresql
def test_sr2_g8_path_only_reobservation_reuses_version_and_structural_keys(
    sr2_engine,
    tmp_path,
):
    commit_a = "3" * 40
    commit_b = "4" * 40
    content = b"# Stable\npath-only sentinel\n"
    reader = FakeRepositoryReader()
    reader.put(commit_a, "alpha.md", content)
    reader.put(commit_b, "renamed/alpha.md", content)
    (
        _sessions,
        session,
        _store,
        _base,
        section_importer,
        _builder,
        _publisher,
        _retrieval,
    ) = _kernels(sr2_engine, tmp_path, reader)

    manifest_a = _manifest(
        manifest_id="path-a",
        commit=commit_a,
        entries=[_entry("alpha", "alpha.md", content)],
    )
    _plan_a, receipt_a = _apply(section_importer, manifest_a)
    generation_a = receipt_a.resulting_text_generation_id
    assert generation_a is not None
    observation_a = _observation(session, receipt_a.manifest_digest, "alpha")
    keys_a = [row.segment_key for row in _segment_rows(session, generation_a, "alpha")]

    manifest_b = _manifest(
        manifest_id="path-b",
        commit=commit_b,
        previous=receipt_a.manifest_digest,
        entries=[_entry("alpha", "renamed/alpha.md", content)],
    )
    plan_b = section_importer.plan_repository_import(manifest_b)
    assert [action.action for action in plan_b.actions] == ["add_locator"]
    receipt_b = section_importer.apply_repository_import(
        manifest=manifest_b,
        expected_plan_digest=plan_b.plan_digest,
    )
    generation_b = receipt_b.resulting_text_generation_id
    assert generation_b is not None
    observation_b = _observation(session, receipt_b.manifest_digest, "alpha")
    keys_b = [row.segment_key for row in _segment_rows(session, generation_b, "alpha")]

    assert observation_b.observation_id != observation_a.observation_id
    assert observation_b.resource_ref == observation_a.resource_ref
    assert observation_b.resource_version_ref == observation_a.resource_version_ref
    assert observation_a.path == "alpha.md"
    assert observation_b.path == "renamed/alpha.md"
    assert keys_b == keys_a
    assert session.scalar(
        select(func.count())
        .select_from(ResourceVersion)
        .where(ResourceVersion.resource_ref_id == observation_a.resource_ref)
    ) == 1
    session.close()


@pytest.mark.postgresql
def test_sr2_g12_restrictive_cases_publish_and_parent_downgrade_reuses_keys(
    sr2_engine,
    tmp_path,
):
    commit_a = "5" * 40
    commit_b = "6" * 40
    unknown_child = (
        b"# Unknown Child\n"
        b"<!-- kc:retrieval-lifecycle=current -->\n"
        b"unknown child sentinel\n"
    )
    superseded_child = (
        b"# Superseded Child\n"
        b"<!-- kc:retrieval-lifecycle=current -->\n"
        b"superseded child sentinel\n"
    )
    ancestor_child = (
        b"# Parent\n"
        b"<!-- kc:retrieval-lifecycle=superseded -->\n"
        b"ancestor sentinel\n"
        b"## Child\n"
        b"<!-- kc:retrieval-lifecycle=current -->\n"
        b"descendant sentinel\n"
    )
    downgrade = (
        b"# Downgrade\n"
        b"<!-- kc:retrieval-lifecycle=current -->\n"
        b"downgrade sentinel\n"
    )
    documents = {
        "unknown": ("unknown.md", unknown_child),
        "superseded": ("superseded.md", superseded_child),
        "ancestor": ("ancestor.md", ancestor_child),
        "downgrade": ("downgrade.md", downgrade),
    }
    reader = FakeRepositoryReader()
    for path, content in documents.values():
        reader.put(commit_a, path, content)
        reader.put(commit_b, path, content)

    (
        _sessions,
        session,
        _store,
        _base,
        section_importer,
        _builder,
        _publisher,
        _retrieval,
    ) = _kernels(sr2_engine, tmp_path, reader)
    entries_a = [
        _entry("unknown", "unknown.md", unknown_child, lifecycle="unknown"),
        _entry("superseded", "superseded.md", superseded_child, lifecycle="superseded"),
        _entry("ancestor", "ancestor.md", ancestor_child),
        _entry("downgrade", "downgrade.md", downgrade),
    ]
    manifest_a = _manifest(manifest_id="g12-a", commit=commit_a, entries=entries_a)
    _plan_a, receipt_a = _apply(section_importer, manifest_a)
    generation_a = receipt_a.resulting_text_generation_id
    assert generation_a is not None

    unknown_rows = _segment_rows(session, generation_a, "unknown")
    assert len(unknown_rows) == 1
    assert unknown_rows[0].parent_lifecycle_state == "unknown"
    assert unknown_rows[0].declared_lifecycle_state == "current"
    assert unknown_rows[0].effective_lifecycle_state == "unknown"

    superseded_rows = _segment_rows(session, generation_a, "superseded")
    assert len(superseded_rows) == 1
    assert superseded_rows[0].parent_lifecycle_state == "superseded"
    assert superseded_rows[0].declared_lifecycle_state == "current"
    assert superseded_rows[0].effective_lifecycle_state == "superseded"

    ancestor_rows = _segment_rows(session, generation_a, "ancestor")
    assert len(ancestor_rows) == 2
    assert ancestor_rows[0].declared_lifecycle_state == "superseded"
    assert ancestor_rows[0].effective_lifecycle_state == "superseded"
    assert ancestor_rows[1].declared_lifecycle_state == "current"
    assert ancestor_rows[1].effective_lifecycle_state == "superseded"
    assert ancestor_rows[1].effective_control_provenance[0]["origin"] == "ancestor"

    downgrade_obs_a = _observation(session, receipt_a.manifest_digest, "downgrade")
    downgrade_keys_a = [
        row.segment_key for row in _segment_rows(session, generation_a, "downgrade")
    ]

    entries_b = [
        _entry("unknown", "unknown.md", unknown_child, lifecycle="unknown"),
        _entry("superseded", "superseded.md", superseded_child, lifecycle="superseded"),
        _entry("ancestor", "ancestor.md", ancestor_child),
        _entry("downgrade", "downgrade.md", downgrade, lifecycle="superseded"),
    ]
    manifest_b = _manifest(
        manifest_id="g12-b",
        commit=commit_b,
        previous=receipt_a.manifest_digest,
        entries=entries_b,
    )
    _plan_b, receipt_b = _apply(section_importer, manifest_b)
    generation_b = receipt_b.resulting_text_generation_id
    assert generation_b is not None

    downgrade_obs_b = _observation(session, receipt_b.manifest_digest, "downgrade")
    downgrade_rows_b = _segment_rows(session, generation_b, "downgrade")
    assert downgrade_obs_b.observation_id != downgrade_obs_a.observation_id
    assert downgrade_obs_b.resource_version_ref == downgrade_obs_a.resource_version_ref
    assert [row.segment_key for row in downgrade_rows_b] == downgrade_keys_a
    assert all(row.parent_lifecycle_state == "superseded" for row in downgrade_rows_b)
    assert all(row.declared_lifecycle_state == "current" for row in downgrade_rows_b)
    assert all(row.effective_lifecycle_state == "superseded" for row in downgrade_rows_b)
    current = section_importer._generation_kernel().current_generation(
        derived_kind=DerivedKind.TEXT
    )
    assert current is not None
    assert current.generation_id == generation_b
    session.close()


@pytest.mark.postgresql
def test_sr2_g13_g17_g18_retirement_is_historical_and_privacy_fence_precedes_limit(
    sr2_engine,
    tmp_path,
):
    commit_a = "7" * 40
    commit_b = "8" * 40
    private = b"# Private\neligibility sentinel\n"
    public = b"# Public\neligibility sentinel\n"
    retired = b"# Retired\nretirement sentinel\n"
    reader = FakeRepositoryReader()
    for path, content in (
        ("private.md", private),
        ("public.md", public),
        ("retired.md", retired),
    ):
        reader.put(commit_a, path, content)
    reader.put(commit_b, "private.md", private)
    reader.put(commit_b, "public.md", public)

    (
        _sessions,
        session,
        _store,
        _base,
        section_importer,
        _builder,
        _publisher,
        retrieval,
    ) = _kernels(sr2_engine, tmp_path, reader)
    manifest_a = _manifest(
        manifest_id="g17-a",
        commit=commit_a,
        entries=[
            _entry("private", "private.md", private, authority=1),
            _entry("public", "public.md", public, authority=20),
            _entry("retired", "retired.md", retired, authority=10),
        ],
    )
    _plan_a, receipt_a = _apply(section_importer, manifest_a)

    manifest_b = _manifest(
        manifest_id="g17-b",
        commit=commit_b,
        previous=receipt_a.manifest_digest,
        entries=[
            _entry("private", "private.md", private, authority=1),
            _entry("public", "public.md", public, authority=20),
        ],
        retirements=[
            {
                "source_document_key": "retired",
                "reason": "bounded historical-retention fixture",
                "historical_retrieval": "retain",
            }
        ],
    )
    _plan_b, receipt_b = _apply(section_importer, manifest_b)
    generation_b = receipt_b.resulting_text_generation_id
    assert generation_b is not None

    assert retrieval.search_text(query="retirement sentinel").results == ()
    historical = retrieval.search_text(
        query="retirement sentinel",
        include_superseded=True,
    )
    assert len(historical.results) == 1
    retired_hit = historical.results[0]
    assert retired_hit.lifecycle_state.value == "superseded"
    retired_ref = retired_hit.resource_version_ref
    assert _segment_rows(session, generation_b, "retired")

    ranked_before = retrieval.search_text(query="eligibility sentinel", limit=1)
    assert len(ranked_before.results) == 1
    assert ranked_before.results[0].authority_rank == 1
    private_hit = ranked_before.results[0]
    private_version = session.get(ResourceVersion, private_hit.resource_version_ref)
    assert private_version is not None

    saved = session.get(
        ResourceSegmentTextSearch,
        {
            "generation_id": generation_b,
            "resource_version_ref": private_hit.resource_version_ref,
            "segment_ordinal": 0,
        },
    )
    assert saved is not None
    payload = {
        column.name: getattr(saved, column.name)
        for column in ResourceSegmentTextSearch.__table__.columns
        if column.name != "search_vector"
    }

    retrieval.fence_target_operation(
        operation_id=uuid4(),
        target_ref=private_version.resource_ref_id,
        action_type=DeletionActionType.RESTRICT,
        policy_scope_id="slice7-g17-logical-resource-restriction",
        caller_principal_ref="slice7-g17-privacy-controller",
    )
    assert session.scalar(
        select(func.count())
        .select_from(ResourceSegmentTextSearch)
        .where(
            ResourceSegmentTextSearch.resource_version_ref
            == private_hit.resource_version_ref
        )
    ) == 0

    payload["search_vector"] = func.to_tsvector(_ENGLISH, "eligibility sentinel")
    session.execute(insert(ResourceSegmentTextSearch).values(**payload))
    session.commit()

    after = retrieval.search_text(query="eligibility sentinel", limit=1)
    assert len(after.results) == 1
    assert after.results[0].authority_rank == 20
    assert after.results[0].resource_version_ref != private_hit.resource_version_ref

    retrieval._purge_derived_for_target(private_version.resource_ref_id)
    session.commit()
    retrieval._purge_derived_for_target(private_version.resource_ref_id)
    session.commit()
    assert session.scalar(
        select(func.count())
        .select_from(ResourceSegmentTextSearch)
        .where(
            ResourceSegmentTextSearch.resource_version_ref
            == private_hit.resource_version_ref
        )
    ) == 0

    assert session.scalar(
        select(func.count())
        .select_from(ResourceSegmentTextSearch)
        .where(ResourceSegmentTextSearch.resource_version_ref == retired_ref)
    ) > 0
    historical_after = retrieval.search_text(
        query="retirement sentinel",
        include_superseded=True,
    )
    assert len(historical_after.results) == 1
    assert historical_after.results[0].resource_version_ref == retired_ref
    session.close()


@pytest.mark.postgresql
def test_sr2_g16_reachable_ranking_discriminators_and_repeat_order_are_stable(
    sr2_engine,
    tmp_path,
):
    commit = "9" * 40
    docs = {
        "score-high": b"# Score\nscoretest scoretest scoretest\n",
        "score-low": b"# Score\nscoretest\n",
        "life-current": b"# Life\nlifetest\n",
        "life-unknown": b"# Life\nlifetest\n",
        "life-superseded": b"# Life\nlifetest\n",
        "authority-low": b"# Authority\nauthoritytest\n",
        "authority-high": b"# Authority\nauthoritytest\n",
        "revision-one": b"# Revision\nrevisiontest\n",
        "revision-two": b"# Revision\nrevisiontest\n",
        "ordinal": b"# First\nordinaltest\n# Second\nordinaltest\n",
    }
    reader = FakeRepositoryReader()
    for key, content in docs.items():
        reader.put(commit, f"{key}.md", content)

    entries = [
        _entry("score-high", "score-high.md", docs["score-high"], authority=5),
        _entry("score-low", "score-low.md", docs["score-low"], authority=5),
        _entry("life-current", "life-current.md", docs["life-current"]),
        _entry(
            "life-unknown",
            "life-unknown.md",
            docs["life-unknown"],
            lifecycle="unknown",
        ),
        _entry(
            "life-superseded",
            "life-superseded.md",
            docs["life-superseded"],
            lifecycle="superseded",
        ),
        _entry(
            "authority-low",
            "authority-low.md",
            docs["authority-low"],
            authority=1,
        ),
        _entry(
            "authority-high",
            "authority-high.md",
            docs["authority-high"],
            authority=9,
        ),
        _entry("revision-one", "revision-one.md", docs["revision-one"], authority=5),
        _entry("revision-two", "revision-two.md", docs["revision-two"], authority=5),
        _entry("ordinal", "ordinal.md", docs["ordinal"], authority=5),
    ]
    (
        _sessions,
        session,
        _store,
        _base,
        section_importer,
        _builder,
        _publisher,
        retrieval,
    ) = _kernels(sr2_engine, tmp_path, reader)
    manifest = _manifest(manifest_id="g16", commit=commit, entries=entries)
    _plan, receipt = _apply(section_importer, manifest)
    generation = receipt.resulting_text_generation_id
    assert generation is not None

    score = retrieval.search_text(query="scoretest", limit=50)
    assert len(score.results) == 2
    assert score.results[0].lexical_score > score.results[1].lexical_score
    assert score.results[0].segment.source_document_key == "score-high"

    lifecycle = retrieval.search_text(
        query="lifetest",
        include_superseded=True,
        limit=50,
    )
    assert [hit.lifecycle_state.value for hit in lifecycle.results] == [
        "current",
        "unknown",
        "superseded",
    ]

    authority = retrieval.search_text(query="authoritytest", limit=50)
    assert [hit.authority_rank for hit in authority.results] == [1, 9]

    revision = retrieval.search_text(query="revisiontest", limit=50)
    revision_ids = [hit.created_revision_id for hit in revision.results]
    assert len(revision_ids) == 2
    assert len(set(revision_ids)) == 2
    assert revision_ids == sorted(revision_ids, reverse=True)

    ordinal = retrieval.search_text(query="ordinaltest", limit=50)
    assert [hit.segment.segment_ordinal for hit in ordinal.results] == [0, 1]

    stopwords = retrieval.search_text(query="the and", limit=50)
    assert stopwords.results == ()

    for query, include_superseded in (
        ("scoretest", False),
        ("lifetest", True),
        ("authoritytest", False),
        ("revisiontest", False),
        ("ordinaltest", False),
    ):
        baseline = retrieval.search_text(
            query=query,
            include_superseded=include_superseded,
            limit=50,
        )
        baseline_ids = _result_identities(baseline)
        assert baseline.generation_id == generation
        for _ in range(3):
            repeated = retrieval.search_text(
                query=query,
                include_superseded=include_superseded,
                limit=50,
            )
            assert repeated.generation_id == generation
            assert _result_identities(repeated) == baseline_ids
    session.close()


@pytest.mark.postgresql
def test_sr2_g21_structural_and_projection_profile_cutovers_are_distinct_and_nonmutating(
    sr2_engine,
    tmp_path,
):
    commit = "a" * 40
    content = b"# Profile\nprofile transition sentinel\n"
    reader = FakeRepositoryReader()
    reader.put(commit, "profile.md", content)
    manifest = _manifest(
        manifest_id="g21",
        commit=commit,
        entries=[_entry("profile", "profile.md", content)],
    )
    (
        _sessions,
        session,
        store,
        base,
        _section_importer,
        _builder,
        publisher,
        retrieval,
    ) = _kernels(sr2_engine, tmp_path, reader)
    _plan, receipt = _apply(base, manifest)
    observation = _observation(session, receipt.manifest_digest, "profile")
    version = session.get(ResourceVersion, observation.resource_version_ref)
    assert version is not None
    version_before = _version_snapshot(version)
    artifact_before = store.read_bytes(version.artifact_key)
    version_count_before = session.scalar(select(func.count()).select_from(ResourceVersion))
    observation_count_before = session.scalar(
        select(func.count()).select_from(RepositorySourceObservation)
    )

    baseline = publisher.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest
    )
    publisher.promote_segment_generation(
        generation_id=baseline.generation_id,
        governing_manifest_digest=receipt.manifest_digest,
    )
    baseline_profile = _profile_payload(session, baseline.generation_id)
    baseline_keys = [
        row.segment_key
        for row in _segment_rows(session, baseline.generation_id, "profile")
    ]

    structural_profile = SectionSegmentationProfile(
        soft_target_bytes=12000,
        hard_max_bytes=32768,
    )
    structural_candidate = publisher.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest,
        structural_profile=structural_profile,
    )
    structural_profile_row = _profile_payload(session, structural_candidate.generation_id)
    structural_keys = [
        row.segment_key
        for row in _segment_rows(session, structural_candidate.generation_id, "profile")
    ]
    assert structural_profile_row[1] != baseline_profile[1]
    assert structural_profile_row[3] != baseline_profile[3]
    assert structural_profile_row[4] != baseline_profile[4]
    assert structural_keys != baseline_keys
    publisher.promote_segment_generation(
        generation_id=structural_candidate.generation_id,
        governing_manifest_digest=receipt.manifest_digest,
        structural_profile=structural_profile,
    )

    projection_profile = RetrievalProjectionProfile(
        structural_profile_digest=structural_profile.digest,
        lexical_projection=(
            "local-minus-own-directive-A-heading-context-B-slice7-qualification"
        ),
    )
    projection_candidate = publisher.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest,
        structural_profile=structural_profile,
        projection_profile=projection_profile,
    )
    projection_profile_row = _profile_payload(session, projection_candidate.generation_id)
    projection_keys = [
        row.segment_key
        for row in _segment_rows(session, projection_candidate.generation_id, "profile")
    ]
    assert projection_profile_row[1] == structural_profile_row[1]
    assert projection_profile_row[3] != structural_profile_row[3]
    assert projection_profile_row[4] != structural_profile_row[4]
    assert projection_keys == structural_keys
    publisher.promote_segment_generation(
        generation_id=projection_candidate.generation_id,
        governing_manifest_digest=receipt.manifest_digest,
        structural_profile=structural_profile,
        projection_profile=projection_profile,
    )

    current = publisher._generation_kernel().current_generation(
        derived_kind=DerivedKind.TEXT
    )
    assert current is not None
    assert current.generation_id == projection_candidate.generation_id
    assert publisher._generation_kernel().read_generation(
        baseline.generation_id
    ).status is GenerationStatus.SUPERSEDED
    assert publisher._generation_kernel().read_generation(
        structural_candidate.generation_id
    ).status is GenerationStatus.SUPERSEDED

    served = retrieval.search_text(query="profile transition sentinel")
    assert served.generation_id == projection_candidate.generation_id
    assert served.retrieval_mode == "segment"
    assert served.structural_profile_digest == structural_profile.digest
    assert served.projection_profile_digest == projection_profile.digest
    assert served.results
    assert all(
        hit.segment is not None and hit.segment.segment_key in set(projection_keys)
        for hit in served.results
    )

    version_after = session.get(ResourceVersion, observation.resource_version_ref)
    assert version_after is not None
    assert _version_snapshot(version_after) == version_before
    assert store.read_bytes(version_after.artifact_key) == artifact_before == content
    assert session.scalar(select(func.count()).select_from(ResourceVersion)) == version_count_before
    assert session.scalar(
        select(func.count()).select_from(RepositorySourceObservation)
    ) == observation_count_before
    session.close()
