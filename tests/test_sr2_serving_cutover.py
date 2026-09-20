from __future__ import annotations

from hashlib import sha1
import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, inspect, literal_column, select

from knowledge_core.api.app import create_app
from knowledge_core.application.repository_import import RepositoryImportKnowledgeKernel
from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.application.section_publication import SectionPublicationKnowledgeKernel
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.deletion import DeletionActionType
from knowledge_core.domain.generations import DerivedKind, GenerationFenceError, GenerationStatus
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.repository_import_models import RepositoryImportReceipt
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.retrieval_models import ResourceTextSearch
from knowledge_core.storage.section_retrieval_models import ResourceSegmentTextSearch


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_ENGLISH = literal_column("'english'::regconfig")
CALLER = {"X-Knowledge-Caller": "sr2-slice6-test"}


def _blob_sha(content: bytes) -> str:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


class FakeRepositoryReader:
    def __init__(self):
        self.repository_locator = "memory://sr2-serving-cutover"
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
) -> dict:
    return {
        "source_document_key": key,
        "path": path,
        "git_blob_sha": _blob_sha(content),
        "media_type": "text/markdown",
        "classification": "approved",
        "retrieval_lifecycle": lifecycle,
        "authority_rank": authority,
        "rationale": "explicit SR-2 Slice-6 serving fixture",
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
        "source_repository_key": "repo-sr2-serving",
        "repository_locator": "memory://sr2-serving-cutover",
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
        pytest.skip("SR-2 serving cutover requires PostgreSQL")
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
        source_readers={"repo-sr2-serving": reader},
    )
    section_importer = SectionRepositoryImportKnowledgeKernel(
        session,
        artifact_store=store,
        source_readers={"repo-sr2-serving": reader},
    )
    publication = SectionPublicationKnowledgeKernel(
        session,
        artifact_store=store,
    )
    retrieval = RetrievalServiceKnowledgeKernel(
        session,
        artifact_store=store,
    )
    return sessions, store, session, base, section_importer, publication, retrieval


def _apply(importer, manifest, **kwargs):
    plan = importer.plan_repository_import(manifest)
    return importer.apply_repository_import(
        manifest=manifest,
        expected_plan_digest=plan.plan_digest,
        **kwargs,
    )


@pytest.mark.postgresql
def test_sr2_slice6_rf2_to_sr2_cutover_has_no_gap_no_mix_and_public_provenance(
    sr2_engine,
    tmp_path,
):
    commit = "a" * 40
    content = (
        b"# Alpha\n"
        b"<!-- kc:retrieval-lifecycle=unknown -->\n"
        b"orchard signal\n"
        b"## Child\n"
        b"orchard signal\n"
    )
    reader = FakeRepositoryReader()
    reader.put(commit, "alpha.md", content)
    manifest = _manifest(
        manifest_id="A",
        commit=commit,
        entries=[_entry("alpha", "alpha.md", content, authority=4)],
    )
    sessions, store, session, base, _section_importer, publication, retrieval = _kernels(
        sr2_engine, tmp_path, reader
    )
    receipt = _apply(base, manifest)
    rf2_generation = receipt.resulting_text_generation_id
    assert rf2_generation is not None

    before = retrieval.search_text(query="orchard")
    assert before.generation_id == rf2_generation
    assert before.retrieval_mode == "resource_version"
    assert all(item.segment is None for item in before.results)

    candidate = publication.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest
    )
    while_building = retrieval.search_text(query="orchard")
    assert while_building.generation_id == rf2_generation
    assert while_building.retrieval_mode == "resource_version"

    promoted = publication.promote_segment_generation(
        generation_id=candidate.generation_id,
        governing_manifest_digest=receipt.manifest_digest,
    )
    assert promoted.status is GenerationStatus.CURRENT
    assert publication._generation_kernel().read_generation(
        rf2_generation
    ).status is GenerationStatus.SUPERSEDED

    after = retrieval.search_text(query="orchard")
    assert after.generation_id == candidate.generation_id
    assert after.retrieval_mode == "segment"
    assert after.structural_profile_id == "kc-section-segmentation-v1"
    assert after.structural_profile_digest and after.structural_profile_digest.startswith(
        "sha256:"
    )
    assert after.projection_profile_id == "kc-section-retrieval-projection-v1"
    assert after.projection_profile_digest and after.projection_profile_digest.startswith(
        "sha256:"
    )
    assert [item.segment.segment_ordinal for item in after.results if item.segment] == [
        0,
        1,
    ]
    first = after.results[0]
    assert first.lifecycle_state.value == "unknown"
    assert first.segment is not None
    assert first.segment.governing_manifest_digest == receipt.manifest_digest
    assert first.segment.source_repository_key == "repo-sr2-serving"
    assert first.segment.source_document_key == "alpha"
    assert first.segment.source_classification == "approved"
    assert first.segment.parent_lifecycle_state.value == "current"
    assert first.segment.declared_lifecycle_state.value == "unknown"
    assert first.segment.effective_lifecycle_state.value == "unknown"
    assert first.segment.heading_path[-1]["display_text"] == "Alpha"

    # Deliberately inject a whole-document row into the *current SR-2 generation*.
    # Dispatch must follow generation implementation identity and ignore this row.
    version_ref = first.resource_version_ref
    session.execute(
        insert(ResourceTextSearch).values(
            generation_id=candidate.generation_id,
            resource_version_ref=version_ref,
            lifecycle_state="current",
            authority_rank=1,
            repository="synthetic/must-not-mix",
            source_path="must-not-mix.md",
            source_version="must-not-mix",
            search_vector=func.to_tsvector(_ENGLISH, "wholeonly sentinel"),
        )
    )
    session.commit()
    no_mix = retrieval.search_text(query="wholeonly sentinel")
    assert no_mix.generation_id == candidate.generation_id
    assert no_mix.retrieval_mode == "segment"
    assert no_mix.results == ()

    transport = TestClient(create_app(session_factory=sessions, artifact_store=store))
    try:
        response = transport.post(
            "/v1/retrieval/search",
            json={"query": "orchard"},
            headers=CALLER,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["generation_id"] == str(candidate.generation_id)
        assert payload["retrieval_mode"] == "segment"
        assert payload["generation_config_digest"].startswith("sha256:")
        assert payload["structural_profile_digest"].startswith("sha256:")
        assert payload["projection_profile_digest"].startswith("sha256:")
        segment = payload["results"][0]["segment"]
        assert segment["governed_observation_id"]
        assert segment["governing_manifest_digest"] == receipt.manifest_digest
        assert segment["segment_key"].startswith("sha256:")
        assert segment["source_byte_start"] == 0
        assert segment["source_slice_sha256"]
        assert segment["effective_lifecycle_state"] == "unknown"
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
        session.close()


@pytest.mark.postgresql
def test_sr2_slice6_section_import_atomically_settles_receipt_and_promotes_generation(
    sr2_engine,
    tmp_path,
):
    a = "a" * 40
    b = "b" * 40
    alpha_a = b"# Alpha\nlegacy amber marker\n"
    alpha_b = b"# Alpha\ncurrent berry marker\n"
    reader = FakeRepositoryReader()
    reader.put(a, "alpha.md", alpha_a)
    reader.put(b, "alpha.md", alpha_b)
    sessions, store, session, base, section_importer, _publication, retrieval = _kernels(
        sr2_engine, tmp_path, reader
    )

    manifest_a = _manifest(
        manifest_id="A",
        commit=a,
        entries=[_entry("alpha", "alpha.md", alpha_a)],
    )
    receipt_a = _apply(base, manifest_a)
    rf2_generation = receipt_a.resulting_text_generation_id
    assert rf2_generation is not None

    manifest_b = _manifest(
        manifest_id="B",
        commit=b,
        previous=receipt_a.manifest_digest,
        entries=[_entry("alpha", "alpha.md", alpha_b)],
    )
    plan_b = section_importer.plan_repository_import(manifest_b)
    hook_seen = {"called": False}

    def before_publish():
        hook_seen["called"] = True
        receipt = session.get(RepositoryImportReceipt, plan_b.manifest_digest)
        assert receipt is not None
        assert receipt.status == "applying"
        current = section_importer._generation_kernel().current_generation(
            derived_kind=DerivedKind.TEXT
        )
        assert current is not None
        assert current.generation_id == rf2_generation
        still_serving = retrieval.search_text(query="legacy amber")
        assert still_serving.generation_id == rf2_generation
        assert still_serving.results

    receipt_b = section_importer.apply_repository_import(
        manifest=manifest_b,
        expected_plan_digest=plan_b.plan_digest,
        before_publish_hook=before_publish,
    )
    assert hook_seen["called"]
    assert receipt_b.status == "settled"
    assert receipt_b.resulting_text_generation_id is not None

    current = section_importer._generation_kernel().current_generation(
        derived_kind=DerivedKind.TEXT
    )
    assert current is not None
    assert current.generation_id == receipt_b.resulting_text_generation_id
    assert current.status is GenerationStatus.CURRENT

    row = session.get(RepositoryImportReceipt, receipt_b.manifest_digest)
    assert row is not None
    assert row.status == "settled"
    assert row.resulting_text_generation_id == current.generation_id

    current_search = retrieval.search_text(query="current berry")
    assert current_search.generation_id == current.generation_id
    assert current_search.retrieval_mode == "segment"
    assert current_search.results

    assert retrieval.search_text(query="legacy amber").results == ()
    historical = retrieval.search_text(
        query="legacy amber",
        include_superseded=True,
    )
    assert historical.results
    assert all(item.lifecycle_state.value == "superseded" for item in historical.results)

    replay = _apply(section_importer, manifest_b)
    assert replay == receipt_b
    session.close()


@pytest.mark.postgresql
def test_sr2_slice6_failed_and_late_candidates_cannot_replace_current(
    sr2_engine,
    tmp_path,
):
    commit = "c" * 40
    content = b"# Alpha\ncutover fence marker\n"
    reader = FakeRepositoryReader()
    reader.put(commit, "alpha.md", content)
    manifest = _manifest(
        manifest_id="A",
        commit=commit,
        entries=[_entry("alpha", "alpha.md", content)],
    )
    _sessions, _store, session, base, _section_importer, publication, retrieval = _kernels(
        sr2_engine, tmp_path, reader
    )
    receipt = _apply(base, manifest)
    rf2_generation = receipt.resulting_text_generation_id
    assert rf2_generation is not None

    bad = publication.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest
    )
    bad_row = session.scalars(
        select(ResourceSegmentTextSearch).where(
            ResourceSegmentTextSearch.generation_id == bad.generation_id
        )
    ).first()
    assert bad_row is not None
    bad_row.source_path = "tampered.md"
    session.commit()

    with pytest.raises(KnowledgeInvariantError):
        publication.promote_segment_generation(
            generation_id=bad.generation_id,
            governing_manifest_digest=receipt.manifest_digest,
        )
    assert publication._generation_kernel().read_generation(
        bad.generation_id
    ).status is GenerationStatus.STALE
    assert retrieval.search_text(query="cutover fence").generation_id == rf2_generation

    older = publication.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest
    )
    newer = publication.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest
    )
    publication.promote_segment_generation(
        generation_id=newer.generation_id,
        governing_manifest_digest=receipt.manifest_digest,
    )
    with pytest.raises(GenerationFenceError):
        publication.promote_segment_generation(
            generation_id=older.generation_id,
            governing_manifest_digest=receipt.manifest_digest,
        )
    assert publication._generation_kernel().read_generation(
        older.generation_id
    ).status is GenerationStatus.STALE
    assert retrieval.search_text(query="cutover fence").generation_id == newer.generation_id
    session.close()


@pytest.mark.postgresql
def test_sr2_slice6_privacy_reconciliation_deletes_segments_and_serving_fence_blocks_stale_reinsert(
    sr2_engine,
    tmp_path,
):
    commit = "d" * 40
    content = b"# Private\nprivacy segment sentinel\n"
    reader = FakeRepositoryReader()
    reader.put(commit, "private.md", content)
    manifest = _manifest(
        manifest_id="A",
        commit=commit,
        entries=[_entry("private", "private.md", content)],
    )
    _sessions, _store, session, base, _section_importer, publication, retrieval = _kernels(
        sr2_engine, tmp_path, reader
    )
    receipt = _apply(base, manifest)
    candidate = publication.build_segment_generation_candidate(
        governing_manifest_digest=receipt.manifest_digest
    )
    publication.promote_segment_generation(
        generation_id=candidate.generation_id,
        governing_manifest_digest=receipt.manifest_digest,
    )
    before = retrieval.search_text(query="privacy segment sentinel")
    assert len(before.results) == 1
    version_ref = before.results[0].resource_version_ref
    version = session.get(ResourceVersion, version_ref)
    assert version is not None

    saved = session.get(
        ResourceSegmentTextSearch,
        {
            "generation_id": candidate.generation_id,
            "resource_version_ref": version_ref,
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
        target_ref=version.resource_ref_id,
        action_type=DeletionActionType.RESTRICT,
        policy_scope_id="slice6-logical-resource-restriction",
        caller_principal_ref="slice6-privacy-controller",
    )
    remaining = session.scalar(
        select(func.count())
        .select_from(ResourceSegmentTextSearch)
        .where(ResourceSegmentTextSearch.resource_version_ref == version_ref)
    )
    assert remaining == 0

    # Recreate a stale derivative after eager cleanup. Parent serving eligibility
    # must still suppress it, proving cleanup timing is not the access boundary.
    payload["search_vector"] = func.to_tsvector(
        _ENGLISH,
        "privacy segment sentinel",
    )
    session.execute(insert(ResourceSegmentTextSearch).values(**payload))
    session.commit()
    assert session.scalar(
        select(func.count())
        .select_from(ResourceSegmentTextSearch)
        .where(ResourceSegmentTextSearch.resource_version_ref == version_ref)
    ) == 1
    assert retrieval.search_text(query="privacy segment sentinel").results == ()
    session.close()
