from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.api.console_admission import ConsoleOwnerAdmission, ConsoleOwnerContract
from knowledge_core.application.consumer_read import ConsumerReadKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)


_BOOTSTRAP_KEY = "c03-worker-bootstrap-key"
_OWNER_KEY = "c03-console-owner-key"
_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)


def _bootstrap() -> BootstrapAdmission:
    return BootstrapAdmission(
        contract=BootstrapContract(),
        api_key=_BOOTSTRAP_KEY,
    )


def _console() -> ConsoleOwnerAdmission:
    return ConsoleOwnerAdmission(
        contract=ConsoleOwnerContract(
            allowed_projects=("inbox", "local-ai"),
            default_project="inbox",
        ),
        owner_key=_OWNER_KEY,
    )


def _build_app(sessions, artifacts):
    return create_app(
        session_factory=sessions,
        artifact_store=artifacts,
        bootstrap_admission=_bootstrap(),
        canonical_store_authority_evaluator=None,
        console_owner_admission=_console(),
        unified_graph_search_binding=None,
    )


def _login(client: TestClient) -> str:
    response = client.post(
        "/v1/kc/console/session",
        headers={"X-KC-Console-Key": _OWNER_KEY},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def _save(client: TestClient, csrf: str, key: str, content: str):
    return client.post(
        "/v1/kc/console/notes",
        headers={
            "X-KC-Console-CSRF": csrf,
            "Idempotency-Key": key,
        },
        json={
            "content": content,
            "title": "C03 Orchard Note",
            "category": "Research",
            "project": "inbox",
            "source_description": "C03 lexical retrieval qualification.",
        },
    )


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("C03 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("C03 qualification requires PostgreSQL")
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
            "TRUNCATE TABLE "
            + ", ".join(tables)
            + " RESTART IDENTITY CASCADE"
        )


@pytest.mark.postgresql
def test_c03_console_search_empty_evidence_original_and_status(tmp_path: Path):
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    artifacts = LocalArtifactStore(tmp_path / "c03-postgres-artifacts")

    try:
        with TestClient(_build_app(sessions, artifacts)) as client:
            assert client.post(
                "/v1/kc/console/search",
                json={"query": "anything"},
            ).status_code == 401
            assert client.get("/v1/kc/console/status").status_code == 401

            csrf = _login(client)

            empty_before = client.post(
                "/v1/kc/console/search",
                json={"query": "nothing indexed yet"},
            )
            assert empty_before.status_code == 200, empty_before.text
            assert empty_before.json()["result_state"] == "empty"
            assert empty_before.json()["results"] == []

            status_before = client.get("/v1/kc/console/status")
            assert status_before.status_code == 200, status_before.text
            before = status_before.json()
            assert before["text_state"] == "empty"
            assert before["search_state"] == "empty"
            assert before["write_admission_state"] == "owner-project-scoped"
            assert before["write_projects"] == ["inbox", "local-ai"]
            assert (
                before["graph_label"]
                == "Not required for this release / integration unverified"
            )

            content = (
                "Orchard lantern sentinel for C03 lexical retrieval.\n"
                "Exact second line remains in the canonical original.\n"
            )
            stored = _save(
                client,
                csrf,
                "c03-orchard-note",
                content,
            )
            assert stored.status_code == 201, stored.text
            stored_data = stored.json()
            assert stored_data["canonical_state"] == "stored"
            assert stored_data["text_state"] == "indexed"
            observation_id = stored_data["note"]["observation_id"]
            version_id = stored_data["note"]["version_id"]

            status_after = client.get("/v1/kc/console/status")
            assert status_after.status_code == 200, status_after.text
            after = status_after.json()
            assert after["text_state"] == "ready"
            assert after["search_state"] == "ready"
            assert after["text_source_count"] == 1
            assert after["canonical_revision"] > 0
            assert after["retrieval_mode"] == "segment"
            assert after["lineage_mode"] == "source-neutral"
            assert "successful save receipt" in after["write_proof_note"]

            search = client.post(
                "/v1/kc/console/search",
                json={"query": "orchard lantern", "limit": 10},
            )
            assert search.status_code == 200, search.text
            payload = search.json()
            assert payload["result_state"] == "matches"
            assert payload["retrieval_mode"] == "segment"
            assert len(payload["results"]) == 1
            assert "graph" not in payload
            assert "answer" not in payload

            hit = payload["results"][0]
            assert hit["display_title"] == "C03 Orchard Note"
            assert hit["category"] == "Research"
            assert hit["note_observation_id"] == observation_id
            assert hit["version_id"] == version_id
            assert hit["open_original_kind"] == "note"
            assert "Orchard lantern sentinel" in hit["excerpt"]
            assert hit["evidence"]["source_kind"] == "local.user-note"
            assert hit["evidence"]["source_id"].startswith("note-")
            assert hit["evidence"]["projects"] == ["inbox"]
            assert hit["evidence"]["captured_at"]
            assert hit["evidence"]["lifecycle_state"] == "current"

            original = client.get(
                f"/v1/kc/console/notes/{observation_id}"
            )
            assert original.status_code == 200, original.text
            assert original.json()["content"] == content

            # The generic current-source route is the path used by non-note
            # search results. A current direct note can also prove its integrity.
            current_source = client.get(
                f"/v1/kc/console/sources/{version_id}"
            )
            assert current_source.status_code == 200, current_source.text
            assert current_source.json()["content"] == content
            assert current_source.json()["version_id"] == version_id

            no_match = client.post(
                "/v1/kc/console/search",
                json={"query": "zzzz-no-c03-match-zzzz"},
            )
            assert no_match.status_code == 200, no_match.text
            assert no_match.json()["result_state"] == "empty"
            assert no_match.json()["results"] == []

            page = client.get("/console/")
            script = client.get("/console/app.js")
            assert page.status_code == script.status_code == 200
            assert "PostgreSQL lexical search" in page.text
            assert "not generated answers" in page.text
            assert "No matching notes or knowledge sources found." in script.text
            assert "Search is unavailable; your query was not completed." in script.text
            assert "Not required / unverified" in script.text
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def test_c03_failed_search_and_status_are_not_reported_as_empty(
    tmp_path: Path,
    monkeypatch,
):
    engine = create_database_engine(
        f"sqlite+pysqlite:///{tmp_path / 'c03-failure.db'}",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    sessions = create_session_factory(engine)
    artifacts = LocalArtifactStore(tmp_path / "c03-failure-artifacts")

    def fail_search(self, **_kwargs):
        raise RuntimeError("forced C03 search outage")

    def fail_status(self):
        raise RuntimeError("forced C03 status outage")

    monkeypatch.setattr(
        ConsumerReadKnowledgeKernel,
        "search_text",
        fail_search,
    )
    monkeypatch.setattr(
        ConsumerReadKnowledgeKernel,
        "retrieval_status",
        fail_status,
    )

    try:
        with TestClient(_build_app(sessions, artifacts)) as client:
            _login(client)

            search = client.post(
                "/v1/kc/console/search",
                json={"query": "must not become empty"},
            )
            assert search.status_code == 503
            assert search.json()["detail"]["error_code"] == "CONSOLE_SEARCH_UNAVAILABLE"
            assert (
                search.json()["detail"]["message"]
                == "Search is unavailable; your query was not completed."
            )
            assert "results" not in search.json()

            status = client.get("/v1/kc/console/status")
            assert status.status_code == 503
            assert status.json()["detail"]["error_code"] == "CONSOLE_STATUS_UNAVAILABLE"
    finally:
        engine.dispose()
