from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract, BootstrapOperation
from knowledge_core.application.retrieval import RetrievalServiceKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.deletion import DeletionActionType
from knowledge_core.storage.database import create_database_engine, create_session_factory


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_BOOTSTRAP_KEY = "task3-bootstrap-key"
_FACT = "Mason is my local MindsHub worker model.\n"


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("Task 3 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("Task 3 requires PostgreSQL")
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
def task3_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _admission(
    *,
    allowed: frozenset[BootstrapOperation] | None = None,
) -> BootstrapAdmission:
    contract = (
        BootstrapContract()
        if allowed is None
        else BootstrapContract(allowed_operations=allowed)
    )
    return BootstrapAdmission(contract=contract, api_key=_BOOTSTRAP_KEY)


def _app(sessions, store, *, admission: BootstrapAdmission | None = None):
    return create_app(
        session_factory=sessions,
        artifact_store=store,
        bootstrap_admission=admission,
    )


def _key_headers() -> dict[str, str]:
    return {"X-Knowledge-Key": _BOOTSTRAP_KEY}


def _store_headers() -> dict[str, str]:
    return {
        "X-Knowledge-Key": _BOOTSTRAP_KEY,
        "Idempotency-Key": "task3-mason-1",
    }


@pytest.mark.postgresql
def test_task3_fresh_client_searches_and_follows_exact_source(
    task3_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task3_engine)
    store = LocalArtifactStore(tmp_path / "task3-read-surface")
    app = _app(sessions, store, admission=_admission())

    with TestClient(app) as client:
        empty = client.get("/v1/kc/status", headers=_key_headers())
        assert empty.status_code == 200, empty.text
        assert empty.json()["text_state"] == "empty"
        assert empty.json()["text_generation_id"] is None

        stored = client.post(
            "/v1/kc/store",
            json={
                "content": _FACT,
                "project": "local-ai",
                "source_type": "user_note",
                "source_id": "mason",
            },
            headers=_store_headers(),
        )
        assert stored.status_code == 201, stored.text
        stored_data = stored.json()
        assert stored_data["text_state"] == "indexed"

    # Reconstruct the application/client boundary. No X-Knowledge-Caller is required
    # for the bootstrap read surface; shared-key admission fixes principal local_owner.
    with TestClient(_app(sessions, store, admission=_admission())) as client:
        search = client.post(
            "/v1/kc/search",
            json={"query": "What is Mason?"},
            headers=_key_headers(),
        )
        assert search.status_code == 200, search.text
        payload = search.json()
        assert payload["evidence_contract_version"] == "kc-lexical-evidence-v2"
        assert payload["retrieval_mode"] == "segment"
        assert payload["generation_id"] == stored_data["text_generation_id"]
        assert payload["results"]

        hit = payload["results"][0]
        assert hit["content"] == _FACT
        assert hit["resource_ref"] == stored_data["resource_id"]
        assert hit["resource_version_ref"] == stored_data["version_id"]
        assert hit["content_digest"] == stored_data["sha256"]
        assert hit["segment"]["source_kind"] == "local.user-note"
        assert hit["segment"]["origin_scope"] == "local_owner"
        assert hit["segment"]["item_key"] == "mason"
        assert hit["segment"]["project_keys"] == ["local-ai"]
        assert hit["repository"] is None
        assert hit["source_path"] is None
        assert hit["source_version"] is None

        exact = client.post(
            "/v1/kc/get-source",
            json={"resource_version_ref": hit["resource_version_ref"]},
            headers=_key_headers(),
        )
        assert exact.status_code == 200, exact.text
        source = exact.json()
        assert source["evidence_contract_version"] == "kc-lexical-evidence-v2"
        assert source["generation_id"] == payload["generation_id"]
        assert source["retrieval_mode"] == "segment"
        assert source["lineage_mode"] == "source-neutral"
        assert source["resource_ref"] == hit["resource_ref"]
        assert source["resource_version_ref"] == hit["resource_version_ref"]
        assert source["content_digest_algo"] == "sha256"
        assert source["content_digest"] == sha256(_FACT.encode("utf-8")).hexdigest()
        assert source["byte_size"] == len(_FACT.encode("utf-8"))
        assert source["media_type"] == "text/plain"
        assert source["content"] == _FACT

        status = client.get("/v1/kc/status", headers=_key_headers())
        assert status.status_code == 200, status.text
        status_data = status.json()
        assert status_data["text_state"] == "ready"
        assert status_data["text_generation_id"] == payload["generation_id"]
        assert status_data["text_source_count"] == 1
        assert status_data["retrieval_mode"] == "segment"
        assert status_data["lineage_mode"] == "source-neutral"
        assert status_data["evidence_contract_version"] == "kc-lexical-evidence-v2"

        exposed = (search.text + exact.text + status.text).lower()
        for token in (
            "artifact_key",
            "artifact_backend",
            "database_url",
            "raw_sql",
            str(store.root).lower(),
        ):
            assert token not in exposed


@pytest.mark.postgresql
def test_task3_bootstrap_auth_scope_and_privacy_remain_fail_closed(
    task3_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task3_engine)
    store = LocalArtifactStore(tmp_path / "task3-auth-privacy")
    app = _app(sessions, store, admission=_admission())

    with TestClient(app) as client:
        for method, path, body in (
            ("post", "/v1/kc/search", {"query": "Mason"}),
            ("post", "/v1/kc/get-source", {"resource_version_ref": str(uuid4())}),
            ("get", "/v1/kc/status", None),
        ):
            response = getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)
            assert response.status_code == 401

        stored = client.post(
            "/v1/kc/store",
            json={
                "content": _FACT,
                "project": "local-ai",
                "source_type": "user_note",
                "source_id": "mason-private",
            },
            headers={
                "X-Knowledge-Key": _BOOTSTRAP_KEY,
                "Idempotency-Key": "task3-private-1",
            },
        )
        assert stored.status_code == 201, stored.text
        refs = stored.json()

        missing = client.post(
            "/v1/kc/get-source",
            json={"resource_version_ref": str(uuid4())},
            headers=_key_headers(),
        )
        assert missing.status_code == 404

    session = sessions()
    try:
        retrieval = RetrievalServiceKnowledgeKernel(session, artifact_store=store)
        resource_ref = UUID(refs["resource_id"])
        case = retrieval.fence_target_operation(
            operation_id=uuid4(),
            target_ref=resource_ref,
            action_type=DeletionActionType.RESTRICT,
            policy_scope_id="task3-privacy",
        )
        retrieval.settle_restriction(case_id=case.case_id, target_ref=resource_ref)
    finally:
        session.close()

    with TestClient(_app(sessions, store, admission=_admission())) as client:
        hidden = client.post(
            "/v1/kc/search",
            json={"query": "What is Mason?"},
            headers=_key_headers(),
        )
        assert hidden.status_code == 200, hidden.text
        assert hidden.json()["results"] == []

        exact = client.post(
            "/v1/kc/get-source",
            json={"resource_version_ref": refs["version_id"]},
            headers=_key_headers(),
        )
        assert exact.status_code == 404

    status_only = _app(
        sessions,
        store,
        admission=_admission(allowed=frozenset({BootstrapOperation.STATUS})),
    )
    with TestClient(status_only) as client:
        denied_search = client.post(
            "/v1/kc/search",
            json={"query": "Mason"},
            headers=_key_headers(),
        )
        denied_source = client.post(
            "/v1/kc/get-source",
            json={"resource_version_ref": refs["version_id"]},
            headers=_key_headers(),
        )
        allowed_status = client.get("/v1/kc/status", headers=_key_headers())
        assert denied_search.status_code == 403
        assert denied_source.status_code == 403
        assert allowed_status.status_code == 200


@pytest.mark.postgresql
def test_task3_read_routes_are_absent_without_bootstrap_admission(
    task3_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task3_engine)
    store = LocalArtifactStore(tmp_path / "task3-no-bootstrap")
    with TestClient(_app(sessions, store, admission=None)) as client:
        assert client.post("/v1/kc/search", json={"query": "Mason"}).status_code == 404
        assert client.post(
            "/v1/kc/get-source",
            json={"resource_version_ref": str(uuid4())},
        ).status_code == 404
        assert client.get("/v1/kc/status").status_code == 404
