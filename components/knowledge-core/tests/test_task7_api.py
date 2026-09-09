from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from knowledge_core.api.app import create_app
from knowledge_core.application.service import ServiceKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.deletion import DeletionActionType
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)


CALLER = {"X-Knowledge-Caller": "simulated-client"}


def _fixture(tmp_path):
    engine = create_database_engine(
        f"sqlite+pysqlite:///{tmp_path / 'api.db'}",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    session_factory = create_session_factory(engine)
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    with session_factory() as session:
        kernel = ServiceKnowledgeKernel(session, artifact_store=artifact_store)
        core = kernel.bootstrap_core_test_profile()
        identity = kernel.bootstrap_identity_test_profile()
    app = create_app(
        session_factory=session_factory,
        artifact_store=artifact_store,
    )
    return engine, session_factory, artifact_store, core, identity, TestClient(app)


def _status(client: TestClient) -> int:
    response = client.get("/v1/status", headers=CALLER)
    assert response.status_code == 200
    return int(response.json()["canonical_revision"])


def test_service_only_entity_assertion_path_is_idempotent_and_hides_credentials(tmp_path):
    engine, _sessions, _artifacts, core, _identity, client = _fixture(tmp_path)
    try:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        assert client.get("/v1/status").status_code == 400

        status = client.get("/v1/status", headers=CALLER)
        assert status.status_code == 200
        assert status.json()["database_credentials_exposed"] is False
        assert "database_url" not in status.text.lower()
        assert "sqlite" not in status.text.lower()

        entity_operation = uuid4()
        entity_request = {
            "operation_id": str(entity_operation),
            "kind_revision_ref": str(core.person_kind_revision_ref),
        }
        first = client.post("/v1/entities", json=entity_request, headers=CALLER)
        second = client.post("/v1/entities", json=entity_request, headers=CALLER)
        assert first.status_code == second.status_code == 201
        assert first.json() == second.json()
        entity_ref = first.json()["entity_ref"]

        assertion_operation = uuid4()
        assertion_request = {
            "operation_id": str(assertion_operation),
            "subject_ref": entity_ref,
            "predicate_revision_ref": str(core.has_name_predicate_revision_ref),
            "profile_revision_ref": str(core.profile_revision_ref),
            "value": {"kind": "text", "value": "Robert Smith"},
        }
        first_assertion = client.post(
            "/v1/assertions", json=assertion_request, headers=CALLER
        )
        replay_assertion = client.post(
            "/v1/assertions", json=assertion_request, headers=CALLER
        )
        assert first_assertion.status_code == replay_assertion.status_code == 201
        assert first_assertion.json() == replay_assertion.json()
        assertion_ref = first_assertion.json()["assertion_ref"]

        read = client.get(f"/v1/assertions/{assertion_ref}", headers=CALLER)
        assert read.status_code == 200
        assert read.json()["value"] == {"kind": "text", "value": "Robert Smith"}

        current = client.get(
            "/v1/knowledge/current",
            params={
                "subject_ref": entity_ref,
                "predicate_revision_ref": str(core.has_name_predicate_revision_ref),
            },
            headers=CALLER,
        )
        assert current.status_code == 200
        assert [item["assertion"]["assertion_ref"] for item in current.json()] == [
            assertion_ref
        ]

        openapi_text = client.get("/openapi.json").text.lower()
        assert "database_url" not in openapi_text
        assert "postgresql" not in openapi_text
    finally:
        client.close()
        engine.dispose()


def test_correction_uses_stale_revision_conflict_and_serving_fence(tmp_path):
    engine, sessions, artifacts, core, _identity, client = _fixture(tmp_path)
    try:
        entity = client.post(
            "/v1/entities",
            json={
                "operation_id": str(uuid4()),
                "kind_revision_ref": str(core.person_kind_revision_ref),
            },
            headers=CALLER,
        ).json()
        assertion = client.post(
            "/v1/assertions",
            json={
                "operation_id": str(uuid4()),
                "subject_ref": entity["entity_ref"],
                "predicate_revision_ref": str(core.has_name_predicate_revision_ref),
                "profile_revision_ref": str(core.profile_revision_ref),
                "value": {"kind": "text", "value": "Robert Smith"},
            },
            headers=CALLER,
        ).json()

        expected = _status(client)
        correction_operation = uuid4()
        correction_request = {
            "operation_id": str(correction_operation),
            "expected_revision": expected,
            "replacement_value": {"kind": "text", "value": "Rob Smith"},
            "correction_kind_revision_ref": str(core.correction_kind_revision_ref),
        }
        correction = client.post(
            f"/v1/assertions/{assertion['assertion_ref']}/correct",
            json=correction_request,
            headers=CALLER,
        )
        assert correction.status_code == 200
        replacement_ref = correction.json()["replacement_assertion_ref"]

        replay = client.post(
            f"/v1/assertions/{assertion['assertion_ref']}/correct",
            json=correction_request,
            headers=CALLER,
        )
        assert replay.status_code == 200
        assert replay.json() == correction.json()

        stale = client.post(
            f"/v1/assertions/{replacement_ref}/correct",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": expected,
                "replacement_value": {"kind": "text", "value": "Robert Smith"},
                "correction_kind_revision_ref": str(core.correction_kind_revision_ref),
            },
            headers=CALLER,
        )
        assert stale.status_code == 409
        assert stale.json()["error_code"] == "STALE_REVISION"

        with sessions() as session:
            kernel = ServiceKnowledgeKernel(session, artifact_store=artifacts)
            kernel.fence_target_operation(
                operation_id=uuid4(),
                target_ref=UUID(replacement_ref),
                action_type=DeletionActionType.RESTRICT,
                policy_scope_id="test-policy",
                caller_principal_ref="privacy-controller",
            )

        restricted = client.get(
            f"/v1/assertions/{replacement_ref}", headers=CALLER
        )
        assert restricted.status_code == 404
    finally:
        client.close()
        engine.dispose()


def test_identity_mutations_are_managed_and_replayable(tmp_path):
    engine, _sessions, _artifacts, _core, identity, client = _fixture(tmp_path)
    try:
        entities = []
        for _ in range(2):
            response = client.post(
                "/v1/entities",
                json={
                    "operation_id": str(uuid4()),
                    "kind_revision_ref": str(identity.person_kind_revision_ref),
                },
                headers=CALLER,
            )
            assert response.status_code == 201
            entities.append(response.json()["entity_ref"])

        expected = _status(client)
        merge_operation = uuid4()
        merge_request = {
            "operation_id": str(merge_operation),
            "expected_revision": expected,
            "entity_refs": entities,
            "representative_ref": entities[0],
            "identity_kind_revision_ref": str(
                identity.identity_resolution_kind_revision_ref
            ),
        }
        merge = client.post("/v1/identity/merge", json=merge_request, headers=CALLER)
        replay = client.post("/v1/identity/merge", json=merge_request, headers=CALLER)
        assert merge.status_code == replay.status_code == 200
        assert merge.json() == replay.json()

        reverse = client.post(
            f"/v1/identity/transitions/{merge.json()['transition_ref']}/reverse",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": _status(client),
                "identity_kind_revision_ref": str(
                    identity.identity_resolution_kind_revision_ref
                ),
            },
            headers=CALLER,
        )
        assert reverse.status_code == 200
        assert reverse.json()["transition_type"] == "split"
    finally:
        client.close()
        engine.dispose()


def test_unmanaged_privileged_and_resource_write_routes_are_not_exposed(tmp_path):
    engine, _sessions, _artifacts, _core, _identity, client = _fixture(tmp_path)
    try:
        paths = set(client.get("/openapi.json").json()["paths"])
        assert "/v1/resources/ingest" not in paths
        assert not any("deletion" in path or "admin" in path for path in paths)
    finally:
        client.close()
        engine.dispose()
