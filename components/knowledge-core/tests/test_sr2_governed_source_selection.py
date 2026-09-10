from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import os
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from knowledge_core.application.governed_source_selection import (
    GovernedProjectionSourceRole,
    resolve_governed_projection_sources,
)
from knowledge_core.application.repository_import import RepositoryImportKnowledgeKernel
from knowledge_core.application.segmentation import segment_structural_content
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.domain.retrieval import RetrievalLifecycleState
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.repository_import_models import (
    RepositoryImportReceipt,
    RepositorySourceObservation,
)


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)


def _blob_sha(content: bytes) -> str:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


class FakeRepositoryReader:
    def __init__(self):
        self.repository_locator = "memory://sr2-source-selection"
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
    rationale: str = "explicit SR-2 governed source fixture",
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
        "source_repository_key": "repo-sr2",
        "repository_locator": "memory://sr2-source-selection",
        "source_commit": commit,
        "previous_manifest_digest": previous,
        "history_policy": "retain_prior_versions_as_superseded",
        "entries": entries,
        "retirements": retirements or [],
    }


def _require_postgres_engine() -> Engine:
    if not _POSTGRES_URL:
        pytest.skip("SR-2 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("SR-2 governed source selection requires PostgreSQL")
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
def sr2_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _kernel(engine: Engine, tmp_path: Path, reader: FakeRepositoryReader):
    sessions = create_session_factory(engine)
    session = sessions()
    kernel = RepositoryImportKnowledgeKernel(
        session,
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
        source_readers={"repo-sr2": reader},
    )
    return kernel, session


def _apply(kernel, manifest):
    plan = kernel.plan_repository_import(manifest)
    receipt = kernel.apply_repository_import(
        manifest=manifest,
        expected_plan_digest=plan.plan_digest,
    )
    return plan, receipt


def _source(sources, *, key: str, role: GovernedProjectionSourceRole):
    matches = [
        item
        for item in sources
        if item.observation.source_document_key == key and item.role == role
    ]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.postgresql
def test_sr2_slice4_resolves_current_prior_and_retirement_from_manifest_chain(
    sr2_engine,
    tmp_path,
):
    a, b = "a" * 40, "b" * 40
    alpha1 = b"# Alpha\nold apricot\n"
    alpha2 = b"# Alpha\nnew blackberry\n"
    beta = b"# Beta\nretained canyon\n"
    reader = FakeRepositoryReader()
    reader.put(a, "alpha.md", alpha1)
    reader.put(a, "beta.md", beta)
    reader.put(b, "alpha.md", alpha2)
    kernel, session = _kernel(sr2_engine, tmp_path, reader)

    manifest_a = _manifest(
        manifest_id="A",
        commit=a,
        entries=[
            _entry("alpha", "alpha.md", alpha1, authority=7),
            _entry("beta", "beta.md", beta, authority=15),
        ],
    )
    _plan_a, receipt_a = _apply(kernel, manifest_a)
    alpha_obs_a = kernel._observation_for_manifest(receipt_a.manifest_digest, "alpha")
    beta_obs_a = kernel._observation_for_manifest(receipt_a.manifest_digest, "beta")
    assert alpha_obs_a is not None
    assert beta_obs_a is not None

    manifest_b = _manifest(
        manifest_id="B",
        commit=b,
        previous=receipt_a.manifest_digest,
        entries=[
            _entry(
                "alpha",
                "alpha.md",
                alpha2,
                lifecycle="unknown",
                authority=3,
                classification="reviewed",
                rationale="new exact alpha revision under review",
            )
        ],
        retirements=[
            {
                "source_document_key": "beta",
                "reason": "replaced outside this bounded corpus",
                "historical_retrieval": "retain",
            }
        ],
    )
    _plan_b, receipt_b = _apply(kernel, manifest_b)
    alpha_obs_b = kernel._observation_for_manifest(receipt_b.manifest_digest, "alpha")
    assert alpha_obs_b is not None

    sources = resolve_governed_projection_sources(
        session,
        governing_manifest_digest=receipt_b.manifest_digest,
    )
    assert len(sources) == 3

    current = _source(
        sources,
        key="alpha",
        role=GovernedProjectionSourceRole.CURRENT,
    )
    prior = _source(
        sources,
        key="alpha",
        role=GovernedProjectionSourceRole.PRIOR_VERSION,
    )
    retired = _source(
        sources,
        key="beta",
        role=GovernedProjectionSourceRole.RETIREMENT_RETAIN,
    )

    assert current.observation.observation_id == alpha_obs_b.observation_id
    assert current.observation.manifest_digest == receipt_b.manifest_digest
    assert current.observation.document_lifecycle == RetrievalLifecycleState.UNKNOWN
    assert current.observation.classification == "reviewed"
    assert current.observation.authority_rank == 3

    assert prior.observation.observation_id == alpha_obs_a.observation_id
    assert prior.observation.manifest_digest == receipt_a.manifest_digest
    assert prior.observation.document_lifecycle == RetrievalLifecycleState.SUPERSEDED
    assert prior.governing_manifest_digest == receipt_b.manifest_digest

    assert retired.observation.observation_id == beta_obs_a.observation_id
    assert retired.observation.manifest_digest == receipt_a.manifest_digest
    assert retired.observation.document_lifecycle == RetrievalLifecycleState.SUPERSEDED
    assert retired.governing_manifest_digest == receipt_b.manifest_digest

    repeat = resolve_governed_projection_sources(
        session,
        governing_manifest_digest=receipt_b.manifest_digest,
    )
    assert [item.projection_snapshot_digest for item in repeat] == [
        item.projection_snapshot_digest for item in sources
    ]
    session.close()


@pytest.mark.postgresql
def test_sr2_slice4_a_b_a_reuses_canonical_and_structural_identity_with_new_lineage(
    sr2_engine,
    tmp_path,
):
    a, b, c = "a" * 40, "b" * 40, "c" * 40
    content_a = b"# Alpha\norchard original\n"
    content_b = b"# Alpha\nberry revision\n"
    reader = FakeRepositoryReader()
    reader.put(a, "alpha.md", content_a)
    reader.put(b, "alpha.md", content_b)
    reader.put(c, "alpha.md", content_a)
    kernel, session = _kernel(sr2_engine, tmp_path, reader)

    manifest_a = _manifest(
        manifest_id="A",
        commit=a,
        entries=[_entry("alpha", "alpha.md", content_a)],
    )
    _plan_a, receipt_a = _apply(kernel, manifest_a)
    source_a = _source(
        resolve_governed_projection_sources(
            session,
            governing_manifest_digest=receipt_a.manifest_digest,
        ),
        key="alpha",
        role=GovernedProjectionSourceRole.CURRENT,
    )
    version_a = source_a.observation.resource_version_ref
    structural_a = segment_structural_content(
        resource_version_ref=version_a,
        media_type="text/markdown",
        content=content_a,
    )

    manifest_b = _manifest(
        manifest_id="B",
        commit=b,
        previous=receipt_a.manifest_digest,
        entries=[_entry("alpha", "alpha.md", content_b)],
    )
    _plan_b, receipt_b = _apply(kernel, manifest_b)

    manifest_c = _manifest(
        manifest_id="C",
        commit=c,
        previous=receipt_b.manifest_digest,
        entries=[_entry("alpha", "alpha.md", content_a)],
    )
    plan_c = kernel.plan_repository_import(manifest_c)
    assert plan_c.actions[0].action == "reuse_version"
    receipt_c = kernel.apply_repository_import(
        manifest=manifest_c,
        expected_plan_digest=plan_c.plan_digest,
    )
    sources_c = resolve_governed_projection_sources(
        session,
        governing_manifest_digest=receipt_c.manifest_digest,
    )
    current_c = _source(
        sources_c,
        key="alpha",
        role=GovernedProjectionSourceRole.CURRENT,
    )
    prior_b = _source(
        sources_c,
        key="alpha",
        role=GovernedProjectionSourceRole.PRIOR_VERSION,
    )

    assert current_c.observation.resource_version_ref == version_a
    assert current_c.observation.observation_id != source_a.observation.observation_id
    assert current_c.governing_manifest_digest == receipt_c.manifest_digest
    assert current_c.projection_snapshot_digest != source_a.projection_snapshot_digest
    assert prior_b.observation.manifest_digest == receipt_b.manifest_digest
    assert prior_b.observation.resource_version_ref != version_a
    assert len(sources_c) == 2

    structural_c = segment_structural_content(
        resource_version_ref=current_c.observation.resource_version_ref,
        media_type="text/markdown",
        content=content_a,
    )
    assert [item.segment_key for item in structural_c.segments] == [
        item.segment_key for item in structural_a.segments
    ]
    session.close()


@pytest.mark.postgresql
def test_sr2_slice4_fails_closed_on_unreconstructable_governed_evidence(
    sr2_engine,
    tmp_path,
):
    a = "a" * 40
    content = b"# Alpha\ncontrol evidence\n"
    reader = FakeRepositoryReader()
    reader.put(a, "alpha.md", content)
    kernel, session = _kernel(sr2_engine, tmp_path, reader)
    manifest = _manifest(
        manifest_id="A",
        commit=a,
        entries=[_entry("alpha", "alpha.md", content)],
    )
    _plan, receipt = _apply(kernel, manifest)

    with pytest.raises(KnowledgeInvariantError, match="unknown governing"):
        resolve_governed_projection_sources(
            session,
            governing_manifest_digest="f" * 64,
        )

    row = session.get(RepositoryImportReceipt, receipt.manifest_digest)
    tampered = deepcopy(row.manifest_json)
    tampered["repository_locator"] = "memory://tampered"
    row.manifest_json = tampered
    session.commit()
    with pytest.raises(KnowledgeInvariantError, match="does not match its digest"):
        resolve_governed_projection_sources(
            session,
            governing_manifest_digest=receipt.manifest_digest,
        )
    session.close()
