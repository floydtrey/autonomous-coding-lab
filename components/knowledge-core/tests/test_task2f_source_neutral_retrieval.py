from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha1
import os
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.application.resource_service import ResourceServiceKnowledgeKernel
from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.application.section_publication_v2 import (
    SourceNeutralSectionPublicationKnowledgeKernel,
)
from knowledge_core.application.section_repository_import import (
    SectionRepositoryImportKnowledgeKernel,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.deletion import DeletionActionType
from knowledge_core.domain.repository_import import RepositorySourceProof
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.section_retrieval_models import TextGenerationSource


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_BOOTSTRAP_KEY = "task2f-bootstrap-key"
_CALLER = {"X-Knowledge-Caller": "task2f-consumer"}


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("Task 2F PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("Task 2F requires PostgreSQL")
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
def task2f_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _admission() -> BootstrapAdmission:
    return BootstrapAdmission(contract=BootstrapContract(), api_key=_BOOTSTRAP_KEY)


def _app(sessions, store):
    return create_app(
        session_factory=sessions,
        artifact_store=store,
        bootstrap_admission=_admission(),
    )


def _store_headers(key: str) -> dict[str, str]:
    return {
        "X-Knowledge-Key": _BOOTSTRAP_KEY,
        "Idempotency-Key": key,
    }


def _note(content: str, *, source_id: str, project: str = "local-ai") -> dict[str, str]:
    return {
        "content": content,
        "project": project,
        "source_type": "user_note",
        "source_id": source_id,
    }


class FakeRepositoryReader:
    def __init__(self):
        self.repository_locator = "memory://task2f-repository"
        self.objects: dict[tuple[str, str], bytes] = {}

    def put(self, commit: str, path: str, content: bytes) -> None:
        self.objects[(commit, path)] = content

    def read_exact(self, *, source_commit: str, path: str) -> RepositorySourceProof:
        content = self.objects[(source_commit, path)]
        digest = sha1()
        digest.update(f"blob {len(content)}\0".encode("ascii"))
        digest.update(content)
        return RepositorySourceProof(
            source_commit=source_commit,
            path=path,
            git_blob_sha=digest.hexdigest(),
            content=content,
            object_mode="100644",
            object_type="blob",
        )


def _repository_manifest(commit: str, content: bytes) -> dict:
    digest = sha1()
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return {
        "schema_version": 2,
        "manifest_id": "task2f-repository-A",
        "source_repository_key": "repo-task2f",
        "repository_locator": "memory://task2f-repository",
        "source_commit": commit,
        "previous_manifest_digest": None,
        "history_policy": "retain_prior_versions_as_superseded",
        "entries": [
            {
                "source_document_key": "repo-alpha",
                "path": "alpha.md",
                "git_blob_sha": digest.hexdigest(),
                "media_type": "text/markdown",
                "classification": "approved",
                "retrieval_lifecycle": "current",
                "authority_rank": 5,
                "rationale": "Task 2F repository compatibility fixture",
            }
        ],
        "retirements": [],
    }


def _seed_repository(sessions, store) -> str:
    commit = "f" * 40
    content = b"# Repository Alpha\nrepository papaya evidence signal\n"
    reader = FakeRepositoryReader()
    reader.put(commit, "alpha.md", content)
    session = sessions()
    try:
        importer = SectionRepositoryImportKnowledgeKernel(
            session,
            artifact_store=store,
            source_readers={"repo-task2f": reader},
        )
        manifest = _repository_manifest(commit, content)
        plan = importer.plan_repository_import(manifest)
        receipt = importer.apply_repository_import(
            manifest=manifest,
            expected_plan_digest=plan.plan_digest,
        )
        assert receipt.status == "settled"
        return receipt.manifest_digest
    finally:
        session.close()


@pytest.mark.postgresql
def test_task2f_mixed_public_search_restart_and_privacy_dominance(
    task2f_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task2f_engine)
    store = LocalArtifactStore(tmp_path / "task2f-mixed")
    manifest_digest = _seed_repository(sessions, store)

    with TestClient(_app(sessions, store)) as client:
        stored = client.post(
            "/v1/kc/store",
            json=_note(
                "Mason cobalt memory signal belongs to the direct note.\n",
                source_id="mason-memory",
            ),
            headers=_store_headers("mason-memory-1"),
        )
        assert stored.status_code == 201, stored.text
        stored_data = stored.json()
        assert stored_data["text_state"] == "indexed"

        note_response = client.post(
            "/v1/retrieval/search",
            json={"query": "Mason cobalt memory signal"},
            headers=_CALLER,
        )
        assert note_response.status_code == 200, note_response.text
        note_payload = note_response.json()
        assert note_payload["evidence_contract_version"] == "kc-lexical-evidence-v2"
        assert len(note_payload["results"]) == 1
        note_hit = note_payload["results"][0]
        note_provenance = note_hit["segment"]
        assert note_provenance["provenance_contract_version"] == "governed-source-sr2-v2"
        assert note_provenance["source_kind"] == "local.user-note"
        assert note_provenance["origin_scope"] == "local_owner"
        assert note_provenance["collection_key"] == "notes"
        assert note_provenance["item_key"] == "mason-memory"
        assert note_provenance["project_keys"] == ["local-ai"]
        assert note_provenance["governing_snapshot_digest"] == stored_data["text_snapshot_digest"]
        assert note_provenance["governed_observation_digest"].startswith("sha256:")
        assert note_provenance["governed_decision_digest"].startswith("sha256:")
        assert note_provenance["governed_projection_digest"].startswith("sha256:")
        assert note_provenance["producer_id"] == "kc.direct-note"
        assert note_hit["repository"] is None
        assert note_hit["source_path"] is None
        assert note_hit["source_version"] is None
        for field in (
            "legacy_repository_observation_id",
            "governing_manifest_digest",
            "projection_snapshot_digest",
            "source_repository_key",
            "source_document_key",
        ):
            assert note_provenance[field] is None

        repo_response = client.post(
            "/v1/retrieval/search",
            json={"query": "repository papaya evidence signal"},
            headers=_CALLER,
        )
        assert repo_response.status_code == 200, repo_response.text
        repo_hit = repo_response.json()["results"][0]
        repo_provenance = repo_hit["segment"]
        assert repo_provenance["provenance_contract_version"] == "governed-source-sr2-v2"
        assert repo_provenance["source_kind"] == "git.repository-document"
        assert repo_provenance["origin_scope"] == "repository:repo-task2f"
        assert repo_provenance["legacy_repository_observation_id"]
        assert repo_provenance["governing_manifest_digest"] == manifest_digest
        assert repo_provenance["source_repository_key"] == "repo-task2f"
        assert repo_provenance["source_document_key"] == "repo-alpha"
        assert repo_hit["repository"] == "memory://task2f-repository"
        assert repo_hit["source_path"] == "alpha.md"
        assert repo_hit["source_version"] == "f" * 40

        forbidden = (note_response.text + repo_response.text).lower()
        for token in (
            "artifact_key",
            "artifact_backend",
            "database_url",
            "raw_sql",
            str(store.root).lower(),
        ):
            assert token not in forbidden

    # Reconstruct the application/session boundary and prove both producer types
    # remain searchable from the same accepted current generation.
    with TestClient(_app(sessions, store)) as client:
        assert client.post(
            "/v1/retrieval/search",
            json={"query": "Mason cobalt memory signal"},
            headers=_CALLER,
        ).json()["results"]
        assert client.post(
            "/v1/retrieval/search",
            json={"query": "repository papaya evidence signal"},
            headers=_CALLER,
        ).json()["results"]

    session = sessions()
    try:
        retrieval = RetrievalServiceKnowledgeKernel(session, artifact_store=store)
        resource_ref = UUID(stored_data["resource_id"])
        case = retrieval.fence_target_operation(
            operation_id=uuid4(),
            target_ref=resource_ref,
            action_type=DeletionActionType.RESTRICT,
            policy_scope_id="task2f-privacy",
        )
        retrieval.settle_restriction(case_id=case.case_id, target_ref=resource_ref)
        assert retrieval.search_text(query="Mason cobalt memory signal").results == ()
        assert retrieval.search_text(query="repository papaya evidence signal").results
    finally:
        session.close()


@pytest.mark.postgresql
def test_task2f_generic_lineage_tamper_fails_closed(
    task2f_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task2f_engine)
    store = LocalArtifactStore(tmp_path / "task2f-tamper")
    with TestClient(_app(sessions, store)) as client:
        stored = client.post(
            "/v1/kc/store",
            json=_note("lineage tamper persimmon signal\n", source_id="tamper-note"),
            headers=_store_headers("tamper-note-1"),
        )
        assert stored.status_code == 201, stored.text
        data = stored.json()

    session = sessions()
    try:
        lineage = session.scalars(
            select(TextGenerationSource).where(
                TextGenerationSource.generation_id == UUID(data["text_generation_id"])
            )
        ).one()
        lineage.governed_projection_digest = "sha256:" + "0" * 64
        session.commit()

        retrieval = RetrievalServiceKnowledgeKernel(session, artifact_store=store)
        with pytest.raises(
            KnowledgeInvariantError,
            match="governed lineage mismatch: governed_projection_digest",
        ):
            retrieval.search_text(query="lineage tamper persimmon signal")
    finally:
        session.close()


@pytest.mark.postgresql
def test_task2f_concurrent_public_store_converges_after_exact_retry(
    task2f_engine,
    tmp_path: Path,
    monkeypatch,
):
    sessions = create_session_factory(task2f_engine)
    store = LocalArtifactStore(tmp_path / "task2f-concurrent")
    app = _app(sessions, store)

    # Establish foundation/current generation before introducing the forced race.
    with TestClient(app) as client:
        baseline = client.post(
            "/v1/kc/store",
            json=_note("baseline guava signal\n", source_id="baseline"),
            headers=_store_headers("baseline-1"),
        )
        assert baseline.status_code == 201, baseline.text
        assert baseline.json()["text_state"] == "indexed"

    barrier = Barrier(2)
    original_build = (
        SourceNeutralSectionPublicationKnowledgeKernel.build_segment_generation_candidate
    )

    def synchronized_build(self, **kwargs):
        result = original_build(self, **kwargs)
        barrier.wait(timeout=20)
        return result

    monkeypatch.setattr(
        SourceNeutralSectionPublicationKnowledgeKernel,
        "build_segment_generation_candidate",
        synchronized_build,
    )

    requests = (
        (
            "race-a-1",
            _note("concurrent kumquat alpha signal\n", source_id="race-a"),
        ),
        (
            "race-b-1",
            _note("concurrent kumquat beta signal\n", source_id="race-b"),
        ),
    )

    def submit(item):
        key, body = item
        with TestClient(app) as client:
            response = client.post(
                "/v1/kc/store",
                json=body,
                headers=_store_headers(key),
            )
            return key, body, response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(submit, requests))

    assert all(status == 201 for _key, _body, status, _data in outcomes)
    states = [data["text_state"] for _key, _body, _status, data in outcomes]
    assert sorted(states) == ["indexed", "pending"]

    # Remove the synchronization hook before replaying the loser. Exact replay keeps
    # canonical identity but may legitimately publish a newer complete generation.
    monkeypatch.setattr(
        SourceNeutralSectionPublicationKnowledgeKernel,
        "build_segment_generation_candidate",
        original_build,
    )
    pending = next(item for item in outcomes if item[3]["text_state"] == "pending")
    pending_key, pending_body, _status, pending_data = pending
    with TestClient(app) as client:
        healed = client.post(
            "/v1/kc/store",
            json=pending_body,
            headers=_store_headers(pending_key),
        )
        assert healed.status_code == 201, healed.text
        healed_data = healed.json()
        assert healed_data["text_state"] == "indexed"
        assert healed_data["resource_id"] == pending_data["resource_id"]
        assert healed_data["version_id"] == pending_data["version_id"]

        alpha = client.post(
            "/v1/retrieval/search",
            json={"query": "concurrent kumquat alpha signal"},
            headers=_CALLER,
        )
        beta = client.post(
            "/v1/retrieval/search",
            json={"query": "concurrent kumquat beta signal"},
            headers=_CALLER,
        )
        assert alpha.status_code == 200 and alpha.json()["results"]
        assert beta.status_code == 200 and beta.json()["results"]
        assert (
            alpha.json()["generation_id"]
            == beta.json()["generation_id"]
            == healed_data["text_generation_id"]
        )
