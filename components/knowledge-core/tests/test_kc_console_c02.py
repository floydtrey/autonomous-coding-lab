from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.api.console_admission import (
    ConsoleOwnerAdmission,
    ConsoleOwnerContract,
)
from knowledge_core.application.direct_note_store import (
    DirectNotePublicationResult,
    DirectNoteStoreKnowledgeKernel,
    direct_note_operation_id,
)
from knowledge_core.application.direct_note_capture import DirectNoteReadKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.deletion import DeletionActionType
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)
from knowledge_core.storage.governed_source_models import (
    DirectNoteCaptureMetadataRecord,
)


_BOOTSTRAP_KEY = "c02-worker-bootstrap-key"
_OWNER_KEY = "c02-console-owner-key"


@pytest.fixture()
def c02_fixture(tmp_path: Path, monkeypatch):
    engine = create_database_engine(
        f"sqlite+pysqlite:///{tmp_path / 'c02.db'}",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    sessions = create_session_factory(engine)
    artifacts = LocalArtifactStore(tmp_path / "artifacts")

    def forced_publication_failure(self, canonical):
        return DirectNotePublicationResult(
            text_state="failed",
            generation_id=None,
            snapshot_digest=None,
            error_code="C02ForcedIndexFailure",
        )

    monkeypatch.setattr(
        DirectNoteStoreKnowledgeKernel,
        "publish_note_text",
        forced_publication_failure,
    )

    bootstrap = BootstrapAdmission(
        contract=BootstrapContract(),
        api_key=_BOOTSTRAP_KEY,
    )
    console = ConsoleOwnerAdmission(
        contract=ConsoleOwnerContract(
            allowed_projects=("inbox", "local-ai"),
            default_project="inbox",
        ),
        owner_key=_OWNER_KEY,
    )
    app = create_app(
        session_factory=sessions,
        artifact_store=artifacts,
        bootstrap_admission=bootstrap,
        canonical_store_authority_evaluator=None,
        console_owner_admission=console,
    )
    client = TestClient(app)
    try:
        yield client, sessions, artifacts
    finally:
        client.close()
        engine.dispose()


def _login(client: TestClient) -> str:
    response = client.post(
        "/v1/kc/console/session",
        headers={"X-KC-Console-Key": _OWNER_KEY},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["allowed_projects"] == ["inbox", "local-ai"]
    assert payload["default_project"] == "inbox"
    return payload["csrf_token"]


def _save_headers(csrf: str, key: str) -> dict[str, str]:
    return {
        "X-KC-Console-CSRF": csrf,
        "Idempotency-Key": key,
    }


def test_c02_console_is_separate_from_worker_store_authority(c02_fixture):
    client, _sessions, _artifacts = c02_fixture

    assert client.get("/console/").status_code == 200
    assert client.get("/v1/kc/console/notes").status_code == 401

    wrong = client.post(
        "/v1/kc/console/session",
        headers={"X-KC-Console-Key": _BOOTSTRAP_KEY},
    )
    assert wrong.status_code == 401

    worker_store = client.post(
        "/v1/kc/store",
        headers={
            "X-Knowledge-Key": _BOOTSTRAP_KEY,
            "Idempotency-Key": "worker-cannot-inherit-console-authority",
        },
        json={
            "content": "Worker bootstrap authentication is not owner save approval.",
            "project": "inbox",
        },
    )
    assert worker_store.status_code == 503
    assert (
        worker_store.json()["error_code"]
        == "CANONICAL_STORE_AUTHORITY_UNAVAILABLE"
    )

    csrf = _login(client)

    missing_csrf = client.post(
        "/v1/kc/console/notes",
        headers={"Idempotency-Key": "missing-csrf"},
        json={"content": "Must not save without CSRF."},
    )
    assert missing_csrf.status_code == 403

    denied_project = client.post(
        "/v1/kc/console/notes",
        headers=_save_headers(csrf, "wrong-project"),
        json={
            "content": "This project is not in the console allowlist.",
            "project": "not-authorized",
        },
    )
    assert denied_project.status_code == 403
    assert (
        denied_project.json()["error_code"]
        == "CANONICAL_STORE_NOT_AUTHORIZED"
    )


def test_c02_metadata_retry_recent_and_exact_original_survive_index_failure(
    c02_fixture,
):
    client, sessions, artifacts = c02_fixture
    csrf = _login(client)

    content = "  First line café 🚧\nsecond line with trailing spaces  \n"
    body = {
        "content": content,
        "project": None,
        "title": None,
        "category": "Field Note",
        "source_description": "Typed locally during C02 qualification.",
        "source_urls": [
            "https://example.invalid/source-a",
            "file:///C:/notes/source-b.txt",
        ],
        "source_date": "2026-09-18",
    }

    first = client.post(
        "/v1/kc/console/notes",
        headers=_save_headers(csrf, "c02-exact-save-1"),
        json=body,
    )
    assert first.status_code == 201, first.text
    first_data = first.json()
    assert first_data["canonical_state"] == "stored"
    assert first_data["text_state"] == "failed"
    assert first_data["text_error_code"] == "C02ForcedIndexFailure"

    note = first_data["note"]
    assert note["content"] == content
    assert note["projects"] == ["inbox"]
    assert note["title"] is None
    assert note["title_supplied"] is False
    assert note["display_title"] == "First line café 🚧"
    assert note["category"] == "Field Note"
    assert note["category_supplied"] is True
    assert note["source_date"] == "2026-09-18"
    assert note["source_time_precision"] == "date"
    assert note["search_ready"] is False
    assert note["submission_id"]
    assert note["observation_id"]

    replay = client.post(
        "/v1/kc/console/notes",
        headers=_save_headers(csrf, "c02-exact-save-1"),
        json=body,
    )
    assert replay.status_code == 201, replay.text
    assert replay.json()["note"]["observation_id"] == note["observation_id"]
    assert replay.json()["note"]["version_id"] == note["version_id"]
    assert replay.json()["note"]["content"] == content

    changed_metadata = dict(body)
    changed_metadata["title"] = "Changed under reused submission"
    conflict = client.post(
        "/v1/kc/console/notes",
        headers=_save_headers(csrf, "c02-exact-save-1"),
        json=changed_metadata,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "OperationReuseError"

    second = client.post(
        "/v1/kc/console/notes",
        headers=_save_headers(csrf, "c02-intentional-duplicate-2"),
        json=body,
    )
    assert second.status_code == 201, second.text
    second_note = second.json()["note"]
    assert second_note["observation_id"] != note["observation_id"]
    assert second_note["submission_id"] != note["submission_id"]
    assert second_note["version_id"] != note["version_id"]
    assert second_note["content"] == content

    recent = client.get("/v1/kc/console/notes?limit=1")
    assert recent.status_code == 200, recent.text
    recent_data = recent.json()
    assert len(recent_data["items"]) == 1
    assert recent_data["items"][0]["observation_id"] == second_note["observation_id"]
    assert recent_data["next_cursor"]

    next_page = client.get(
        "/v1/kc/console/notes",
        params={"limit": 1, "cursor": recent_data["next_cursor"]},
    )
    assert next_page.status_code == 200, next_page.text
    assert next_page.json()["items"][0]["observation_id"] == note["observation_id"]

    exact = client.get(
        f"/v1/kc/console/notes/{note['observation_id']}"
    )
    assert exact.status_code == 200, exact.text
    assert exact.json()["content"] == content

    with sessions() as session:
        row = session.get(
            DirectNoteCaptureMetadataRecord,
            UUID(note["observation_id"]),
        )
        assert row is not None
        assert row.operation_id == UUID(note["submission_id"])
        assert row.project_key == "inbox"
        assert row.category == "Field Note"
        assert row.source_date.isoformat() == "2026-09-18"

        # The original remains in the existing immutable artifact store rather
        # than being copied into the metadata table.
        reader = DirectNoteReadKnowledgeKernel(
            session,
            artifact_store=artifacts,
        )
        original = reader.read_note(
            principal_ref="local_owner",
            observation_id=UUID(note["observation_id"]),
        )
        assert original.content == content


def test_c02_legacy_note_and_serving_restriction_are_honored(c02_fixture):
    client, sessions, artifacts = c02_fixture

    with sessions() as session:
        kernel = DirectNoteStoreKnowledgeKernel(
            session,
            artifact_store=artifacts,
        )
        operation_id = direct_note_operation_id(
            principal_ref="local_owner",
            idempotency_key="legacy-before-c02",
        )
        legacy = kernel.store_note_operation(
            operation_id=operation_id,
            caller_principal_ref="local_owner",
            content="Legacy note title\nLegacy exact body.\n",
            project_key="local-ai",
            source_id="legacy-note",
        )
        legacy_observation = legacy.observation_id
        legacy_version = legacy.resource_version_ref

    csrf = _login(client)
    recent = client.get("/v1/kc/console/notes")
    assert recent.status_code == 200, recent.text
    legacy_item = next(
        item
        for item in recent.json()["items"]
        if item["observation_id"] == str(legacy_observation)
    )
    assert legacy_item["submission_id"] is None
    assert legacy_item["display_title"] == "Legacy note title"
    assert legacy_item["category"] == "Note"
    assert legacy_item["category_supplied"] is False
    assert legacy_item["projects"] == []

    original = client.get(
        f"/v1/kc/console/notes/{legacy_observation}"
    )
    assert original.status_code == 200
    assert original.json()["content"] == "Legacy note title\nLegacy exact body.\n"

    with sessions() as session:
        reader = DirectNoteReadKnowledgeKernel(
            session,
            artifact_store=artifacts,
        )
        reader.fence_target_operation(
            operation_id=uuid4(),
            target_ref=legacy_version,
            action_type=DeletionActionType.RESTRICT,
            policy_scope_id="c02-test-restriction",
            caller_principal_ref="c02-test-privacy-controller",
        )

    restricted = client.get(
        f"/v1/kc/console/notes/{legacy_observation}"
    )
    assert restricted.status_code == 404

    recent_after_fence = client.get("/v1/kc/console/notes")
    assert recent_after_fence.status_code == 200
    assert str(legacy_observation) not in {
        item["observation_id"]
        for item in recent_after_fence.json()["items"]
    }

    # Keep csrf referenced so the login itself remains part of the test boundary.
    assert csrf
