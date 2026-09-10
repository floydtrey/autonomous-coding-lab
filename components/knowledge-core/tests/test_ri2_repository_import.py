from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
import os
from pathlib import Path
import subprocess

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.engine import Engine

from knowledge_core.api.repository_import_app import create_repository_import_app
from knowledge_core.application.repository_import import RepositoryImportKnowledgeKernel
from knowledge_core.application.repository_source import GitRepositorySourceReader
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.repository_import_models import (
    RepositoryDocumentBinding,
    RepositoryImportReceipt,
    RepositorySourceObservation,
)
from knowledge_core.storage.resource_models import Resource, ResourceLocator, ResourceVersion


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CALLER = {"X-Knowledge-Caller": "ri2-test"}


def _blob_sha(content: bytes) -> str:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest()


class FakeRepositoryReader:
    def __init__(self, repository_locator: str = "memory://ri2"):
        self.repository_locator = repository_locator
        self.objects: dict[tuple[str, str], tuple[bytes, str, str]] = {}
        self.calls: list[tuple[str, str]] = []

    def put(
        self,
        commit: str,
        path: str,
        content: bytes,
        *,
        mode: str = "100644",
        object_type: str = "blob",
    ) -> None:
        self.objects[(commit, path)] = (content, mode, object_type)

    def read_exact(self, *, source_commit: str, path: str) -> RepositorySourceProof:
        self.calls.append((source_commit, path))
        try:
            content, mode, object_type = self.objects[(source_commit, path)]
        except KeyError as exc:
            raise KnowledgeInvariantError(
                f"source path does not exist at exact commit: {path}"
            ) from exc
        return RepositorySourceProof(
            source_commit=source_commit,
            path=path,
            git_blob_sha=_blob_sha(content),
            content=content,
            object_mode=mode,
            object_type=object_type,
        )


def _entry(
    key: str,
    path: str,
    content: bytes,
    *,
    lifecycle: str = "current",
    authority: int | None = 10,
    classification: str = "approved",
    rationale: str = "explicit RI-2 fixture classification",
    continuity: str | None = None,
) -> dict:
    item = {
        "source_document_key": key,
        "path": path,
        "git_blob_sha": _blob_sha(content),
        "media_type": "text/markdown",
        "classification": classification,
        "retrieval_lifecycle": lifecycle,
        "authority_rank": authority,
        "rationale": rationale,
    }
    if continuity is not None:
        item["continuity_rationale"] = continuity
    return item


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
        "source_repository_key": "repo-1",
        "repository_locator": "memory://ri2",
        "source_commit": commit,
        "previous_manifest_digest": previous,
        "history_policy": "retain_prior_versions_as_superseded",
        "entries": entries,
        "retirements": retirements or [],
    }


def _require_postgres_engine() -> Engine:
    if not _POSTGRES_URL:
        pytest.skip("RI-2 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("RI-2 requires PostgreSQL")
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
def ri2_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _kernel(engine: Engine, tmp_path, reader: FakeRepositoryReader):
    sessions = create_session_factory(engine)
    session = sessions()
    return (
        RepositoryImportKnowledgeKernel(
            session,
            artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
            source_readers={"repo-1": reader},
        ),
        session,
        sessions,
    )


def _count(session, model) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


@pytest.mark.postgresql
def test_ri2_g1_g2_and_g18_manifest_is_bounded_and_verifies_before_writes(
    ri2_engine,
    tmp_path,
):
    a = "a" * 40
    alpha = b"# Alpha\nalpha orchard\n"
    beta = b"# Beta\nbeta canyon\n"
    secret = b"# Secret\nnever read me\n"
    reader = FakeRepositoryReader()
    reader.put(a, "alpha.md", alpha)
    reader.put(a, "beta.md", beta)
    reader.put(a, "secret.md", secret)
    kernel, session, _sessions = _kernel(ri2_engine, tmp_path, reader)

    base = _manifest(
        manifest_id="A",
        commit=a,
        entries=[
            _entry("alpha", "alpha.md", alpha),
            _entry("beta", "beta.md", beta),
        ],
    )
    bad = deepcopy(base)
    bad["entries"][1]["git_blob_sha"] = "f" * 40
    with pytest.raises(KnowledgeInvariantError, match="blob"):
        kernel.plan_repository_import(bad)

    assert set(reader.calls) == {(a, "alpha.md"), (a, "beta.md")}
    assert (a, "secret.md") not in reader.calls
    assert _count(session, RepositoryDocumentBinding) == 0
    assert _count(session, RepositoryImportReceipt) == 0
    assert _count(session, RepositorySourceObservation) == 0
    assert _count(session, Resource) == 0
    assert _count(session, ResourceVersion) == 0
    assert _count(session, DerivedGeneration) == 0

    invalids = []
    item = deepcopy(base)
    item["source_commit"] = "main"
    invalids.append(item)
    item = deepcopy(base)
    item["entries"][1]["source_document_key"] = "alpha"
    invalids.append(item)
    item = deepcopy(base)
    item["entries"][1]["path"] = "alpha.md"
    invalids.append(item)
    item = deepcopy(base)
    item["entries"][0]["path"] = "../alpha.md"
    invalids.append(item)
    item = deepcopy(base)
    item["entries"][0]["path"] = "*.md"
    invalids.append(item)
    item = deepcopy(base)
    item["entries"][0]["media_type"] = "application/pdf"
    invalids.append(item)
    item = deepcopy(base)
    del item["entries"][0]["classification"]
    invalids.append(item)
    for invalid in invalids:
        with pytest.raises(KnowledgeInvariantError):
            kernel.plan_repository_import(invalid)

    link_content = b"target"
    link_manifest = _manifest(
        manifest_id="link",
        commit=a,
        entries=[_entry("link", "link.md", link_content)],
    )
    reader.put(a, "link.md", link_content, mode="120000")
    with pytest.raises(KnowledgeInvariantError, match="regular Git blobs"):
        kernel.plan_repository_import(link_manifest)
    session.close()


@pytest.mark.postgresql
def test_ri2_g3_g4_g8_g16_first_import_replay_duplicate_content_and_provenance(
    ri2_engine,
    tmp_path,
):
    a = "a" * 40
    alpha = b"# Alpha\nalpha orchard signal\n"
    beta = b"# Beta\nbeta canyon signal\n"
    reader = FakeRepositoryReader()
    reader.put(a, "alpha.md", alpha)
    reader.put(a, "beta.md", beta)
    reader.put(a, "alpha-copy.md", alpha)
    manifest = _manifest(
        manifest_id="A",
        commit=a,
        entries=[
            _entry("alpha", "alpha.md", alpha),
            _entry("beta", "beta.md", beta),
            _entry("alpha-copy", "alpha-copy.md", alpha),
        ],
    )
    kernel, session, _sessions = _kernel(ri2_engine, tmp_path, reader)
    plan = kernel.plan_repository_import(manifest)
    assert [item.action for item in plan.actions] == [
        "create_resource",
        "create_resource",
        "create_resource",
    ]
    receipt = kernel.apply_repository_import(
        manifest=manifest,
        expected_plan_digest=plan.plan_digest,
    )
    assert receipt.status == "settled"
    assert receipt.resulting_text_generation_id is not None

    bindings = {
        row.source_document_key: row
        for row in session.scalars(select(RepositoryDocumentBinding)).all()
    }
    assert len(bindings) == 3
    assert bindings["alpha"].resource_ref != bindings["alpha-copy"].resource_ref

    observations = session.scalars(
        select(RepositorySourceObservation).where(
            RepositorySourceObservation.manifest_digest == receipt.manifest_digest
        )
    ).all()
    assert len(observations) == 3
    alpha_obs = next(x for x in observations if x.source_document_key == "alpha")
    copy_obs = next(
        x for x in observations if x.source_document_key == "alpha-copy"
    )
    assert alpha_obs.resource_ref != copy_obs.resource_ref
    assert alpha_obs.resource_version_ref != copy_obs.resource_version_ref
    alpha_version = session.get(ResourceVersion, alpha_obs.resource_version_ref)
    copy_version = session.get(ResourceVersion, copy_obs.resource_version_ref)
    assert alpha_version.content_digest == copy_version.content_digest

    hits = kernel.search_text(
        query="orchard",
        include_superseded=False,
        limit=10,
    )
    assert {hit.source_path for hit in hits.results} == {
        "alpha.md",
        "alpha-copy.md",
    }
    for hit in hits.results:
        obs = next(
            x
            for x in observations
            if x.resource_version_ref == hit.resource_version_ref
        )
        assert obs.source_commit == a
        assert obs.git_blob_sha == _blob_sha(alpha)
        assert obs.resource_ref == hit.resource_ref

    counts = {
        model: _count(session, model)
        for model in (
            RepositoryDocumentBinding,
            RepositoryImportReceipt,
            RepositorySourceObservation,
            Resource,
            ResourceVersion,
            ResourceLocator,
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
    assert {model: _count(session, model) for model in counts} == counts
    assert all(path != "secret.md" for _commit, path in reader.calls)
    session.close()


@pytest.mark.postgresql
def test_ri2_g5_g6_g7_g15_edit_rename_and_rename_edit_preserve_identity(
    ri2_engine,
    tmp_path,
):
    a, b, c, d = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)
    alpha1 = b"# Alpha\nlegacy apricot\n"
    alpha2 = b"# Alpha\ncurrent blackberry\n"
    alpha3 = b"# Alpha moved\ncurrent dragonfruit\n"
    beta = b"# Beta\nsteady canyon\n"
    reader = FakeRepositoryReader()
    for commit, alpha_path, alpha_content, beta_path in (
        (a, "alpha.md", alpha1, "beta.md"),
        (b, "alpha.md", alpha2, "beta.md"),
        (c, "alpha.md", alpha2, "renamed/beta.md"),
        (d, "moved/alpha.md", alpha3, "renamed/beta.md"),
    ):
        reader.put(commit, alpha_path, alpha_content)
        reader.put(commit, beta_path, beta)

    kernel, session, _sessions = _kernel(ri2_engine, tmp_path, reader)
    ma = _manifest(
        manifest_id="A",
        commit=a,
        entries=[
            _entry("alpha", "alpha.md", alpha1),
            _entry("beta", "beta.md", beta),
        ],
    )
    pa = kernel.plan_repository_import(ma)
    ra = kernel.apply_repository_import(
        manifest=ma,
        expected_plan_digest=pa.plan_digest,
    )
    alpha_binding = kernel._binding("repo-1", "alpha")
    beta_binding = kernel._binding("repo-1", "beta")
    alpha_resource = alpha_binding.resource_ref
    beta_resource = beta_binding.resource_ref
    alpha_v1 = kernel._observation_for_manifest(
        ra.manifest_digest,
        "alpha",
    ).resource_version_ref
    beta_v1 = kernel._observation_for_manifest(
        ra.manifest_digest,
        "beta",
    ).resource_version_ref

    mb = _manifest(
        manifest_id="B",
        commit=b,
        previous=ra.manifest_digest,
        entries=[
            _entry("alpha", "alpha.md", alpha2),
            _entry("beta", "beta.md", beta),
        ],
    )
    pb = kernel.plan_repository_import(mb)
    assert next(
        x for x in pb.actions if x.source_document_key == "alpha"
    ).action == "create_version"
    rb = kernel.apply_repository_import(
        manifest=mb,
        expected_plan_digest=pb.plan_digest,
    )
    alpha_v2 = kernel._observation_for_manifest(
        rb.manifest_digest,
        "alpha",
    ).resource_version_ref
    assert kernel._binding("repo-1", "alpha").resource_ref == alpha_resource
    assert alpha_v2 != alpha_v1
    assert _count(session, ResourceVersion) == 3
    assert not kernel.search_text(query="apricot").results
    old = kernel.search_text(query="apricot", include_superseded=True)
    assert [x.source_path for x in old.results] == ["alpha.md"]
    assert (
        kernel.search_text(query="blackberry").generation_id
        == rb.resulting_text_generation_id
    )

    mc = _manifest(
        manifest_id="C",
        commit=c,
        previous=rb.manifest_digest,
        entries=[
            _entry("alpha", "alpha.md", alpha2),
            _entry("beta", "renamed/beta.md", beta),
        ],
    )
    pc = kernel.plan_repository_import(mc)
    assert next(
        x for x in pc.actions if x.source_document_key == "beta"
    ).action == "add_locator"
    rc = kernel.apply_repository_import(
        manifest=mc,
        expected_plan_digest=pc.plan_digest,
    )
    beta_v2 = kernel._observation_for_manifest(
        rc.manifest_digest,
        "beta",
    ).resource_version_ref
    assert beta_v2 == beta_v1
    assert kernel._binding("repo-1", "beta").resource_ref == beta_resource
    beta_locators = session.scalars(
        select(ResourceLocator).where(
            ResourceLocator.resource_ref_id == beta_resource
        )
    ).all()
    assert {x.locator_text for x in beta_locators} == {
        "beta.md",
        "renamed/beta.md",
    }

    md_no = _manifest(
        manifest_id="D-no-continuity",
        commit=d,
        previous=rc.manifest_digest,
        entries=[
            _entry("alpha", "moved/alpha.md", alpha3),
            _entry("beta", "renamed/beta.md", beta),
        ],
    )
    with pytest.raises(KnowledgeInvariantError, match="continuity"):
        kernel.plan_repository_import(md_no)

    md = deepcopy(md_no)
    md["manifest_id"] = "D"
    md["entries"][0]["continuity_rationale"] = (
        "same governed design document moved and edited"
    )
    pd = kernel.plan_repository_import(md)
    rd = kernel.apply_repository_import(
        manifest=md,
        expected_plan_digest=pd.plan_digest,
    )
    alpha_v3 = kernel._observation_for_manifest(
        rd.manifest_digest,
        "alpha",
    ).resource_version_ref
    assert kernel._binding("repo-1", "alpha").resource_ref == alpha_resource
    assert alpha_v3 not in {alpha_v1, alpha_v2}
    assert (
        kernel.search_text(query="dragonfruit").generation_id
        == rd.resulting_text_generation_id
    )
    current_generations = session.scalars(
        select(DerivedGeneration).where(
            DerivedGeneration.derived_kind == DerivedKind.TEXT.value,
            DerivedGeneration.status == "current",
        )
    ).all()
    assert [g.generation_id for g in current_generations] == [
        rd.resulting_text_generation_id
    ]
    session.close()


@pytest.mark.postgresql
def test_ri2_g9_g10_g11_classification_and_explicit_retirements(
    ri2_engine,
    tmp_path,
):
    a, b, c, d = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)
    alpha = b"# Alpha\nalphaclass word\n"
    beta = b"# Beta\nbetaretire word\n"
    reader = FakeRepositoryReader()
    for commit in (a, b, c, d):
        reader.put(commit, "alpha.md", alpha)
        reader.put(commit, "beta.md", beta)

    kernel, session, _sessions = _kernel(ri2_engine, tmp_path, reader)
    ma = _manifest(
        manifest_id="A",
        commit=a,
        entries=[
            _entry("alpha", "alpha.md", alpha),
            _entry("beta", "beta.md", beta),
        ],
    )
    pa = kernel.plan_repository_import(ma)
    ra = kernel.apply_repository_import(
        manifest=ma,
        expected_plan_digest=pa.plan_digest,
    )
    alpha_obs_a = kernel._observation_for_manifest(ra.manifest_digest, "alpha")
    version_count = _count(session, ResourceVersion)

    mb = _manifest(
        manifest_id="B",
        commit=b,
        previous=ra.manifest_digest,
        entries=[
            _entry(
                "alpha",
                "alpha.md",
                alpha,
                lifecycle="superseded",
                authority=2,
            ),
            _entry("beta", "beta.md", beta),
        ],
    )
    pb = kernel.plan_repository_import(mb)
    assert next(
        x for x in pb.actions if x.source_document_key == "alpha"
    ).action == "classification_only"
    rb = kernel.apply_repository_import(
        manifest=mb,
        expected_plan_digest=pb.plan_digest,
    )
    alpha_obs_b = kernel._observation_for_manifest(rb.manifest_digest, "alpha")
    assert alpha_obs_b.resource_version_ref == alpha_obs_a.resource_version_ref
    assert _count(session, ResourceVersion) == version_count
    assert not kernel.search_text(query="alphaclass").results
    assert kernel.search_text(
        query="alphaclass",
        include_superseded=True,
    ).results

    omitted = _manifest(
        manifest_id="C-bad",
        commit=c,
        previous=rb.manifest_digest,
        entries=[
            _entry(
                "alpha",
                "alpha.md",
                alpha,
                lifecycle="superseded",
                authority=2,
            )
        ],
    )
    with pytest.raises(KnowledgeInvariantError, match="omits"):
        kernel.plan_repository_import(omitted)

    retain = deepcopy(omitted)
    retain["manifest_id"] = "C"
    retain["retirements"] = [
        {
            "source_document_key": "beta",
            "reason": "superseded by external policy",
            "historical_retrieval": "retain",
        }
    ]
    pc = kernel.plan_repository_import(retain)
    rc = kernel.apply_repository_import(
        manifest=retain,
        expected_plan_digest=pc.plan_digest,
    )
    assert not kernel.search_text(query="betaretire").results
    hist = kernel.search_text(query="betaretire", include_superseded=True)
    assert [x.source_path for x in hist.results] == ["beta.md"]

    exclude = _manifest(
        manifest_id="D",
        commit=d,
        previous=rc.manifest_digest,
        entries=[
            _entry(
                "alpha",
                "alpha.md",
                alpha,
                lifecycle="superseded",
                authority=2,
            )
        ],
        retirements=[
            {
                "source_document_key": "beta",
                "reason": "remove from retrieval but retain canonical history",
                "historical_retrieval": "exclude",
            }
        ],
    )
    pd = kernel.plan_repository_import(exclude)
    kernel.apply_repository_import(
        manifest=exclude,
        expected_plan_digest=pd.plan_digest,
    )
    assert not kernel.search_text(
        query="betaretire",
        include_superseded=True,
    ).results
    beta_old = kernel._observation_for_manifest(ra.manifest_digest, "beta")
    assert session.get(ResourceVersion, beta_old.resource_version_ref) is not None
    session.close()


@pytest.mark.postgresql
def test_ri2_g12_g13_g14_stale_source_chain_and_failed_publication_are_non_serving(
    ri2_engine,
    tmp_path,
):
    a, b, c, d = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)
    alpha1 = b"# Alpha\nversionone token\n"
    alpha2 = b"# Alpha\nversiontwo token\n"
    alpha_bad = b"# Alpha\nchanged after plan\n"
    reader = FakeRepositoryReader()
    reader.put(a, "alpha.md", alpha1)
    reader.put(b, "alpha.md", alpha2)
    reader.put(c, "alpha.md", alpha1)
    reader.put(d, "alpha.md", alpha2)

    kernel, session, _sessions = _kernel(ri2_engine, tmp_path, reader)
    ma = _manifest(
        manifest_id="A",
        commit=a,
        entries=[_entry("alpha", "alpha.md", alpha1)],
    )
    pa = kernel.plan_repository_import(ma)
    ra = kernel.apply_repository_import(
        manifest=ma,
        expected_plan_digest=pa.plan_digest,
    )

    mb = _manifest(
        manifest_id="B",
        commit=b,
        previous=ra.manifest_digest,
        entries=[_entry("alpha", "alpha.md", alpha2)],
    )
    pb = kernel.plan_repository_import(mb)

    mc = _manifest(
        manifest_id="C",
        commit=c,
        previous=ra.manifest_digest,
        entries=[_entry("alpha", "alpha.md", alpha1, authority=1)],
    )
    pc = kernel.plan_repository_import(mc)
    rc = kernel.apply_repository_import(
        manifest=mc,
        expected_plan_digest=pc.plan_digest,
    )
    with pytest.raises(KnowledgeInvariantError, match="chain"):
        kernel.apply_repository_import(
            manifest=mb,
            expected_plan_digest=pb.plan_digest,
        )
    assert (
        kernel._generation_kernel()
        .current_generation(derived_kind=DerivedKind.TEXT)
        .generation_id
        == rc.resulting_text_generation_id
    )

    md = _manifest(
        manifest_id="D",
        commit=d,
        previous=rc.manifest_digest,
        entries=[_entry("alpha", "alpha.md", alpha2)],
    )
    pd = kernel.plan_repository_import(md)
    reader.put(d, "alpha.md", alpha_bad)
    receipts_before = _count(session, RepositoryImportReceipt)
    with pytest.raises(KnowledgeInvariantError, match="blob"):
        kernel.apply_repository_import(
            manifest=md,
            expected_plan_digest=pd.plan_digest,
        )
    assert _count(session, RepositoryImportReceipt) == receipts_before
    assert (
        kernel._generation_kernel()
        .current_generation(derived_kind=DerivedKind.TEXT)
        .generation_id
        == rc.resulting_text_generation_id
    )

    reader.put(d, "alpha.md", alpha2)
    pd = kernel.plan_repository_import(md)

    def fail_before_publish():
        raise RuntimeError("injected publish failure")

    with pytest.raises(RuntimeError, match="injected"):
        kernel.apply_repository_import(
            manifest=md,
            expected_plan_digest=pd.plan_digest,
            before_publish_hook=fail_before_publish,
        )
    failed = session.get(RepositoryImportReceipt, pd.manifest_digest)
    assert failed.status == "failed"
    assert (
        kernel._generation_kernel()
        .current_generation(derived_kind=DerivedKind.TEXT)
        .generation_id
        == rc.resulting_text_generation_id
    )
    versions_after_failure = _count(session, ResourceVersion)

    retry_plan = kernel.plan_repository_import(md)
    rd = kernel.apply_repository_import(
        manifest=md,
        expected_plan_digest=retry_plan.plan_digest,
    )
    assert rd.status == "settled"
    assert _count(session, ResourceVersion) == versions_after_failure
    assert (
        kernel.search_text(query="versiontwo").generation_id
        == rd.resulting_text_generation_id
    )
    session.close()


@pytest.mark.postgresql
def test_ri2_g17_service_only_plan_apply_query_has_no_storage_credentials(
    ri2_engine,
    tmp_path,
):
    a = "a" * 40
    alpha = b"# Alpha\nserviceboundary kiwi\n"
    reader = FakeRepositoryReader()
    reader.put(a, "alpha.md", alpha)
    manifest = _manifest(
        manifest_id="service-A",
        commit=a,
        entries=[_entry("alpha", "alpha.md", alpha)],
    )
    sessions = create_session_factory(ri2_engine)
    app = create_repository_import_app(
        session_factory=sessions,
        artifact_store=LocalArtifactStore(tmp_path / "service-artifacts"),
        source_readers={"repo-1": reader},
    )
    with TestClient(app) as client:
        planned = client.post(
            "/v1/repository-import/plan",
            headers=_CALLER,
            json={"manifest": manifest},
        )
        assert planned.status_code == 200, planned.text
        plan_body = planned.json()
        applied = client.post(
            "/v1/repository-import/apply",
            headers=_CALLER,
            json={
                "manifest": manifest,
                "plan_digest": plan_body["plan_digest"],
            },
        )
        assert applied.status_code == 200, applied.text
        queried = client.post(
            "/v1/retrieval/search",
            headers=_CALLER,
            json={
                "query": "serviceboundary",
                "limit": 10,
                "include_superseded": False,
            },
        )
        assert queried.status_code == 200, queried.text
        assert queried.json()["results"][0]["source_path"] == "alpha.md"
        openapi = client.get("/openapi.json").json()

    serialized = json.dumps(
        {
            "plan": plan_body,
            "apply": applied.json(),
            "query": queried.json(),
            "openapi": openapi,
        },
        sort_keys=True,
    )
    for secret_name in (
        "KNOWLEDGE_CORE_DATABASE_URL",
        "artifact_key",
        "artifact_backend",
        "repository_root",
        "repository_token",
        "database_url",
    ):
        assert secret_name not in serialized
    assert (a, "alpha.md") in reader.calls


def test_ri2_tiny_real_git_reader_uses_exact_git_object_not_working_tree():
    path = "docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md"
    source_commit = "f7f12c04163ecbe3b6143191008cf393726b8def"
    expected_blob = "457472f7928994ab40e1c8f4faea7e70e93b7449"
    reader = GitRepositorySourceReader(
        repository_locator="git://acl-ci",
        repository_root=_REPO_ROOT,
    )
    proof = reader.read_exact(source_commit=source_commit, path=path)
    assert proof.source_commit == source_commit
    assert proof.path == path
    assert proof.git_blob_sha == expected_blob
    assert proof.content.startswith(
        b"# Knowledge Core Repository Import RI-1"
    )