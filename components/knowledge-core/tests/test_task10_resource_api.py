from __future__ import annotations

import base64
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from knowledge_core.api.app import create_app
from knowledge_core.application.resource_service import ResourceServiceKnowledgeKernel
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
        f"sqlite+pysqlite:///{tmp_path / 'resource-api.db'}",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    sessions = create_session_factory(engine)
    artifacts = LocalArtifactStore(tmp_path / "artifacts")
    with sessions() as session:
        kernel = ResourceServiceKnowledgeKernel(session, artifact_store=artifacts)
        core = kernel.bootstrap_core_test_profile()
        resource = kernel.bootstrap_resource_test_profile()
    client = TestClient(create_app(session_factory=sessions, artifact_store=artifacts))
    return engine, sessions, artifacts, core, resource, client


def _status(client: TestClient) -> int:
    response = client.get("/v1/status", headers=CALLER)
    assert response.status_code == 200
    return int(response.json()["canonical_revision"])


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _create_resource(client: TestClient, kind_revision_ref: UUID) -> str:
    response = client.post(
        "/v1/resources",
        json={
            "operation_id": str(uuid4()),
            "kind_revision_ref": str(kind_revision_ref),
        },
        headers=CALLER,
    )
    assert response.status_code == 201
    return response.json()["resource_ref"]


def test_exact_duplicate_ingest_settles_as_control_only_noop(tmp_path):
    engine, sessions, artifacts, _core, resource, client = _fixture(tmp_path)
    try:
        resource_ref = _create_resource(client, resource.artifact_kind_revision_ref)
        first = client.post(
            "/v1/resources/ingest",
            json={
                "operation_id": str(uuid4()),
                "resource_ref": resource_ref,
                "content_base64": _b64(b"stable bytes"),
                "ingestion_kind_revision_ref": str(
                    resource.resource_ingestion_kind_revision_ref
                ),
                "media_type": "text/plain",
            },
            headers=CALLER,
        )
        assert first.status_code == 200
        first_version = first.json()["resource_version_ref"]
        revision_after_first = _status(client)

        noop_operation = uuid4()
        noop_request = {
            "operation_id": str(noop_operation),
            "expected_revision": revision_after_first,
            "resource_ref": resource_ref,
            "content_base64": _b64(b"stable bytes"),
            "ingestion_kind_revision_ref": str(
                resource.resource_ingestion_kind_revision_ref
            ),
            "media_type": "text/plain",
        }
        noop = client.post(
            "/v1/resources/ingest",
            json=noop_request,
            headers=CALLER,
        )
        replay = client.post(
            "/v1/resources/ingest",
            json=noop_request,
            headers=CALLER,
        )
        assert noop.status_code == replay.status_code == 200
        assert noop.json() == replay.json()
        assert noop.json()["resource_version_ref"] == first_version
        assert _status(client) == revision_after_first

        with sessions() as session:
            kernel = ResourceServiceKnowledgeKernel(session, artifact_store=artifacts)
            operation = kernel.read_operation(noop_operation)
            assert operation.status == "committed"
            assert operation.result_revision_id is None

        reused = dict(noop_request)
        reused["content_base64"] = _b64(b"different bytes")
        conflict = client.post(
            "/v1/resources/ingest",
            json=reused,
            headers=CALLER,
        )
        assert conflict.status_code == 409
        assert conflict.json()["error_code"] == "OperationReuseError"

        locator_operation = uuid4()
        locator = client.post(
            "/v1/resources/ingest",
            json={
                **noop_request,
                "operation_id": str(locator_operation),
                "locator_kind": "path",
                "locator_text": "/bounded/test/source.txt",
            },
            headers=CALLER,
        )
        assert locator.status_code == 200
        assert locator.json()["resource_version_ref"] == first_version
        assert _status(client) > revision_after_first
        with sessions() as session:
            kernel = ResourceServiceKnowledgeKernel(session, artifact_store=artifacts)
            assert kernel.read_operation(locator_operation).result_revision_id is not None
    finally:
        client.close()
        engine.dispose()


def test_resource_provenance_http_path_is_exact_and_serving_fenced(tmp_path):
    engine, sessions, artifacts, core, resource, client = _fixture(tmp_path)
    try:
        assert client.post("/v1/resources", json={}).status_code == 400

        entity = client.post(
            "/v1/entities",
            json={
                "operation_id": str(uuid4()),
                "kind_revision_ref": str(core.person_kind_revision_ref),
            },
            headers=CALLER,
        )
        assert entity.status_code == 201
        assertion = client.post(
            "/v1/assertions",
            json={
                "operation_id": str(uuid4()),
                "subject_ref": entity.json()["entity_ref"],
                "predicate_revision_ref": str(core.has_name_predicate_revision_ref),
                "profile_revision_ref": str(core.profile_revision_ref),
                "value": {"kind": "text", "value": "Robert Smith"},
            },
            headers=CALLER,
        )
        assert assertion.status_code == 201
        assertion_ref = assertion.json()["assertion_ref"]

        resource_ref = _create_resource(client, resource.artifact_kind_revision_ref)
        ingest_operation = uuid4()
        ingest_request = {
            "operation_id": str(ingest_operation),
            "resource_ref": resource_ref,
            "content_base64": _b64(b"Robert Smith evidence"),
            "ingestion_kind_revision_ref": str(
                resource.resource_ingestion_kind_revision_ref
            ),
            "media_type": "text/plain",
        }
        ingested = client.post(
            "/v1/resources/ingest",
            json=ingest_request,
            headers=CALLER,
        )
        assert ingested.status_code == 200
        version_ref = ingested.json()["resource_version_ref"]
        assert "artifact_key" not in ingested.text
        assert "artifact_backend" not in ingested.text

        link = client.post(
            f"/v1/assertions/{assertion_ref}/evidence",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": _status(client),
                "resource_version_ref": version_ref,
                "relation_revision_ref": str(
                    resource.supports_claim_relation_revision_ref
                ),
            },
            headers=CALLER,
        )
        assert link.status_code == 201

        explanation = client.get(
            f"/v1/assertions/{assertion_ref}/explain",
            headers=CALLER,
        )
        assert explanation.status_code == 200
        assert [
            item["resource_version"]["resource_version_ref"]
            for item in explanation.json()
        ] == [version_ref]

        impact = client.get(
            f"/v1/resources/{version_ref}/impact",
            headers=CALLER,
        )
        assert impact.status_code == 200
        assert [item["dependent_ref"] for item in impact.json()] == [assertion_ref]

        with sessions() as session:
            kernel = ResourceServiceKnowledgeKernel(session, artifact_store=artifacts)
            kernel.fence_target_operation(
                operation_id=uuid4(),
                target_ref=UUID(version_ref),
                action_type=DeletionActionType.RESTRICT,
                policy_scope_id="test-policy",
                caller_principal_ref="privacy-controller",
            )

        assert client.get(
            f"/v1/resource-versions/{version_ref}", headers=CALLER
        ).status_code == 404
        assert client.get(
            f"/v1/resources/{version_ref}/impact", headers=CALLER
        ).status_code == 404

        # The operation itself remains settled/replayable, but current serving policy
        # must prevent its old result from re-exposing the newly restricted version.
        replay_after_fence = client.post(
            "/v1/resources/ingest",
            json=ingest_request,
            headers=CALLER,
        )
        assert replay_after_fence.status_code == 404

        # The assertion remains serving-eligible; only its restricted evidence trace
        # disappears from explanation.
        explanation_after_fence = client.get(
            f"/v1/assertions/{assertion_ref}/explain",
            headers=CALLER,
        )
        assert explanation_after_fence.status_code == 200
        assert explanation_after_fence.json() == []

        openapi = client.get("/openapi.json").text.lower()
        assert "database_url" not in openapi
        assert "artifact_key" not in openapi
        assert "artifact_backend" not in openapi
    finally:
        client.close()
        engine.dispose()
