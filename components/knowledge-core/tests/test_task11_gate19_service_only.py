from __future__ import annotations

import base64
import inspect
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from knowledge_core.api.app import create_app
from knowledge_core.application.generations import GenerationKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.deletion import DeletionActionType
from knowledge_core.domain.generations import DerivedKind, GenerationFenceError
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)
from knowledge_core.storage.models import KnowledgeRef


class SimulatedVeraAclClient:
    """Gate 19 client: HTTP transport + caller identity, nothing storage-specific."""

    __slots__ = ("_http", "_headers")

    def __init__(self, http: TestClient, *, caller: str = "simulated-vera-acl"):
        self._http = http
        self._headers = {"X-Knowledge-Caller": caller}

    def get(self, path: str, *, params: dict | None = None):
        return self._http.get(path, params=params, headers=self._headers)

    def post(self, path: str, *, json: dict):
        return self._http.post(path, json=json, headers=self._headers)

    def status_revision(self) -> int:
        response = self.get("/v1/status")
        assert response.status_code == 200
        return int(response.json()["canonical_revision"])



def _fixture(tmp_path):
    engine = create_database_engine(
        f"sqlite+pysqlite:///{tmp_path / 'gate19.db'}",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    sessions = create_session_factory(engine)
    artifacts = LocalArtifactStore(tmp_path / "artifacts")
    with sessions() as session:
        kernel = GenerationKnowledgeKernel(session, artifact_store=artifacts)
        core = kernel.bootstrap_core_test_profile()
        identity = kernel.bootstrap_identity_test_profile()
        resource = kernel.bootstrap_resource_test_profile()
    http = TestClient(create_app(session_factory=sessions, artifact_store=artifacts))
    client = SimulatedVeraAclClient(http)
    return engine, sessions, artifacts, core, identity, resource, http, client



def _create_entity(client: SimulatedVeraAclClient, kind_revision_ref: UUID, *, operation_id=None):
    operation_id = operation_id or uuid4()
    response = client.post(
        "/v1/entities",
        json={
            "operation_id": str(operation_id),
            "kind_revision_ref": str(kind_revision_ref),
        },
    )
    assert response.status_code == 201
    return response, operation_id



def _append_assertion(
    client: SimulatedVeraAclClient,
    *,
    subject_ref: str,
    predicate_revision_ref: UUID,
    profile_revision_ref: UUID,
    value_kind: str,
    value,
    world_interval: dict | None = None,
    operation_id=None,
):
    body = {
        "operation_id": str(operation_id or uuid4()),
        "subject_ref": subject_ref,
        "predicate_revision_ref": str(predicate_revision_ref),
        "profile_revision_ref": str(profile_revision_ref),
        "value": {"kind": value_kind, "value": value},
    }
    if world_interval is not None:
        body["world_interval"] = world_interval
    response = client.post("/v1/assertions", json=body)
    assert response.status_code == 201
    return response



def _current_values(client, subject_ref: str, predicate_revision_ref: UUID):
    response = client.get(
        "/v1/knowledge/current",
        params={
            "subject_ref": subject_ref,
            "predicate_revision_ref": str(predicate_revision_ref),
        },
    )
    assert response.status_code == 200
    return {item["assertion"]["value"]["value"] for item in response.json()}



def _term(items, stable_name: str):
    return next(item for item in items if item.stable_name == stable_name)



def test_gate19_client_has_no_database_or_storage_contract(tmp_path):
    engine, _sessions, _artifacts, _core, _identity, _resource, http, client = _fixture(tmp_path)
    try:
        source = inspect.getsource(SimulatedVeraAclClient).lower()
        for forbidden in (
            "sqlalchemy",
            "session_factory",
            "database_url",
            "knowledge_core_database_url",
            "artifact_store",
            "create_database_engine",
            "postgresql",
        ):
            assert forbidden not in source
        assert set(SimulatedVeraAclClient.__slots__) == {"_http", "_headers"}

        status = client.get("/v1/status")
        assert status.status_code == 200
        assert status.json()["database_credentials_exposed"] is False
        assert status.json()["authority_mode"] == "external-not-implemented"

        openapi = http.get("/openapi.json").text.lower()
        for forbidden in (
            "database_url",
            "knowledge_core_database_url",
            "postgresql://",
            "artifact_key",
            "artifact_backend",
        ):
            assert forbidden not in openapi
        paths = set(http.get("/openapi.json").json()["paths"])
        assert "/v1/identity/entities/{entity_ref}" in paths
        assert not any(
            token in path
            for path in paths
            for token in ("deletion", "erase", "admin", "generation", "profile-activation")
        )
    finally:
        http.close()
        engine.dispose()



def test_gate19_assertion_temporal_conflict_projection_stale_and_retry_via_http(tmp_path):
    engine, sessions, artifacts, core, _identity, _resource, http, client = _fixture(tmp_path)
    try:
        robert, _ = _create_entity(client, core.person_kind_revision_ref)
        acme, _ = _create_entity(client, core.organization_kind_revision_ref)
        beta, _ = _create_entity(client, core.organization_kind_revision_ref)
        robert_ref = robert.json()["entity_ref"]
        acme_ref = acme.json()["entity_ref"]
        beta_ref = beta.json()["entity_ref"]

        # Gate 1: typed scalar + exact semantic revision pins.
        name = _append_assertion(
            client,
            subject_ref=robert_ref,
            predicate_revision_ref=core.has_name_predicate_revision_ref,
            profile_revision_ref=core.profile_revision_ref,
            value_kind="text",
            value="Robert Smith",
        )
        assert name.json()["value"] == {"kind": "text", "value": "Robert Smith"}
        assert name.json()["predicate_revision_ref"] == str(core.has_name_predicate_revision_ref)
        assert name.json()["profile_revision_ref"] == str(core.profile_revision_ref)

        # Gates 2-4: reference relationship, correction without overwrite, reversal.
        original = _append_assertion(
            client,
            subject_ref=robert_ref,
            predicate_revision_ref=core.works_for_predicate_revision_ref,
            profile_revision_ref=core.profile_revision_ref,
            value_kind="reference",
            value=acme_ref,
        )
        original_ref = original.json()["assertion_ref"]
        original_bytes = client.get(f"/v1/assertions/{original_ref}").json()
        expected = client.status_revision()
        corrected = client.post(
            f"/v1/assertions/{original_ref}/correct",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": expected,
                "replacement_value": {"kind": "reference", "value": beta_ref},
                "correction_kind_revision_ref": str(core.correction_kind_revision_ref),
            },
        )
        assert corrected.status_code == 200
        assert client.get(f"/v1/assertions/{original_ref}").json() == original_bytes
        assert _current_values(client, robert_ref, core.works_for_predicate_revision_ref) == {beta_ref}
        history = client.get(
            "/v1/knowledge/history",
            params={
                "subject_ref": robert_ref,
                "predicate_revision_ref": str(core.works_for_predicate_revision_ref),
            },
        )
        assert history.status_code == 200
        assert len(history.json()) == 2

        reversal = client.post(
            f"/v1/transitions/{corrected.json()['transition_ref']}/reverse",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": client.status_revision(),
                "correction_kind_revision_ref": str(core.correction_kind_revision_ref),
            },
        )
        assert reversal.status_code == 200
        assert reversal.json()["transition_type"] == "restores"
        assert _current_values(client, robert_ref, core.works_for_predicate_revision_ref) == {acme_ref}

        # Gate 5: world-valid time is independent from knowledge-record time.
        temporal_person, _ = _create_entity(client, core.person_kind_revision_ref)
        temporal_ref = temporal_person.json()["entity_ref"]
        temporal_original = _append_assertion(
            client,
            subject_ref=temporal_ref,
            predicate_revision_ref=core.works_for_predicate_revision_ref,
            profile_revision_ref=core.profile_revision_ref,
            value_kind="reference",
            value=acme_ref,
            world_interval={"valid_from": "2026-06-02T00:00:00Z"},
        )
        temporal_original_ref = temporal_original.json()["assertion_ref"]
        pre_correction_history = client.get(
            "/v1/knowledge/history",
            params={
                "subject_ref": temporal_ref,
                "predicate_revision_ref": str(core.works_for_predicate_revision_ref),
            },
        ).json()
        before_correction = pre_correction_history[0]["recorded_at"]
        temporal_correction = client.post(
            f"/v1/assertions/{temporal_original_ref}/correct",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": client.status_revision(),
                "replacement_value": {"kind": "reference", "value": beta_ref},
                "correction_kind_revision_ref": str(core.correction_kind_revision_ref),
                "replacement_world_interval": {"valid_from": "2026-05-15T00:00:00Z"},
            },
        )
        assert temporal_correction.status_code == 200
        old_belief = client.get(
            "/v1/knowledge/belief",
            params={
                "world_at": "2026-06-15T00:00:00Z",
                "knowledge_at": before_correction,
                "subject_ref": temporal_ref,
                "predicate_revision_ref": str(core.works_for_predicate_revision_ref),
            },
        )
        assert {item["assertion"]["value"]["value"] for item in old_belief.json()} == {acme_ref}
        reconstructed = client.get(
            "/v1/knowledge/belief",
            params={
                "world_at": "2026-05-20T00:00:00Z",
                "knowledge_at": "2100-01-01T00:00:00Z",
                "subject_ref": temporal_ref,
                "predicate_revision_ref": str(core.works_for_predicate_revision_ref),
            },
        )
        assert {item["assertion"]["value"]["value"] for item in reconstructed.json()} == {beta_ref}

        # Gate 6: unresolved conflict stays plural, not silently collapsed.
        conflict_person, _ = _create_entity(client, core.person_kind_revision_ref)
        conflict_ref = conflict_person.json()["entity_ref"]
        _append_assertion(
            client,
            subject_ref=conflict_ref,
            predicate_revision_ref=core.works_for_predicate_revision_ref,
            profile_revision_ref=core.profile_revision_ref,
            value_kind="reference",
            value=acme_ref,
        )
        _append_assertion(
            client,
            subject_ref=conflict_ref,
            predicate_revision_ref=core.works_for_predicate_revision_ref,
            profile_revision_ref=core.profile_revision_ref,
            value_kind="reference",
            value=beta_ref,
        )
        before_rebuild = _current_values(client, conflict_ref, core.works_for_predicate_revision_ref)
        assert before_rebuild == {acme_ref, beta_ref}

        # Gate 9: destroy/rebuild physical projection; client semantic result is identical.
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=artifacts)
            kernel.rebuild_current_projection()
            kernel.clear_current_projection()
        assert _current_values(client, conflict_ref, core.works_for_predicate_revision_ref) == before_rebuild
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=artifacts)
            kernel.rebuild_current_projection()
        assert _current_values(client, conflict_ref, core.works_for_predicate_revision_ref) == before_rebuild

        # Gate 10: stale expected revision fails before an unintended second transition.
        stale_person, _ = _create_entity(client, core.person_kind_revision_ref)
        stale_ref = stale_person.json()["entity_ref"]
        stale_source = _append_assertion(
            client,
            subject_ref=stale_ref,
            predicate_revision_ref=core.works_for_predicate_revision_ref,
            profile_revision_ref=core.profile_revision_ref,
            value_kind="reference",
            value=acme_ref,
        )
        stale_expected = client.status_revision()
        first = client.post(
            f"/v1/assertions/{stale_source.json()['assertion_ref']}/correct",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": stale_expected,
                "replacement_value": {"kind": "reference", "value": beta_ref},
                "correction_kind_revision_ref": str(core.correction_kind_revision_ref),
            },
        )
        assert first.status_code == 200
        second = client.post(
            f"/v1/assertions/{stale_source.json()['assertion_ref']}/correct",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": stale_expected,
                "replacement_value": {"kind": "reference", "value": acme_ref},
                "correction_kind_revision_ref": str(core.correction_kind_revision_ref),
            },
        )
        assert second.status_code == 409
        assert second.json()["error_code"] == "STALE_REVISION"

        # Gate 11: same operation retries; different payload reuse is rejected.
        replay_operation = uuid4()
        replay_first, _ = _create_entity(
            client, core.person_kind_revision_ref, operation_id=replay_operation
        )
        replay_second, _ = _create_entity(
            client, core.person_kind_revision_ref, operation_id=replay_operation
        )
        assert replay_first.json() == replay_second.json()
        reused = client.post(
            "/v1/entities",
            json={
                "operation_id": str(replay_operation),
                "kind_revision_ref": str(core.organization_kind_revision_ref),
            },
        )
        assert reused.status_code == 409
        assert reused.json()["error_code"] == "OperationReuseError"
    finally:
        http.close()
        engine.dispose()



def test_gate19_resource_provenance_privacy_and_anti_resurrection_via_http(tmp_path):
    engine, sessions, artifacts, core, _identity, resource, http, client = _fixture(tmp_path)
    try:
        person, _ = _create_entity(client, core.person_kind_revision_ref)
        assertion = _append_assertion(
            client,
            subject_ref=person.json()["entity_ref"],
            predicate_revision_ref=core.has_name_predicate_revision_ref,
            profile_revision_ref=core.profile_revision_ref,
            value_kind="text",
            value="Robert Smith",
        )
        assertion_ref = assertion.json()["assertion_ref"]

        logical = client.post(
            "/v1/resources",
            json={
                "operation_id": str(uuid4()),
                "kind_revision_ref": str(resource.artifact_kind_revision_ref),
            },
        )
        assert logical.status_code == 201
        resource_ref = logical.json()["resource_ref"]
        source_path = "/bounded/evidence.txt"

        v1 = client.post(
            "/v1/resources/ingest",
            json={
                "operation_id": str(uuid4()),
                "resource_ref": resource_ref,
                "content_base64": base64.b64encode(b"Robert Smith evidence").decode(),
                "ingestion_kind_revision_ref": str(resource.resource_ingestion_kind_revision_ref),
                "media_type": "text/plain",
                "locator_kind": "path",
                "locator_text": source_path,
            },
        )
        assert v1.status_code == 200
        v1_ref = v1.json()["resource_version_ref"]
        link = client.post(
            f"/v1/assertions/{assertion_ref}/evidence",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": client.status_revision(),
                "resource_version_ref": v1_ref,
                "relation_revision_ref": str(resource.supports_claim_relation_revision_ref),
            },
        )
        assert link.status_code == 201

        # Gates 7-8: same mutable locator can change, provenance stays pinned to v1.
        v2 = client.post(
            "/v1/resources/ingest",
            json={
                "operation_id": str(uuid4()),
                "resource_ref": resource_ref,
                "content_base64": base64.b64encode(b"later different bytes").decode(),
                "ingestion_kind_revision_ref": str(resource.resource_ingestion_kind_revision_ref),
                "media_type": "text/plain",
                "locator_kind": "path",
                "locator_text": source_path,
            },
        )
        assert v2.status_code == 200
        v2_ref = v2.json()["resource_version_ref"]
        assert v2_ref != v1_ref
        explanation = client.get(f"/v1/assertions/{assertion_ref}/explain")
        assert explanation.status_code == 200
        assert [item["resource_version"]["resource_version_ref"] for item in explanation.json()] == [v1_ref]
        impact_v1 = client.get(f"/v1/resources/{v1_ref}/impact")
        impact_v2 = client.get(f"/v1/resources/{v2_ref}/impact")
        assert [item["dependent_ref"] for item in impact_v1.json()] == [assertion_ref]
        assert impact_v2.json() == []

        # Gate 14: restriction becomes a serving fence before physical cleanup.
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=artifacts)
            kernel.fence_target_operation(
                operation_id=uuid4(),
                target_ref=UUID(v1_ref),
                action_type=DeletionActionType.RESTRICT,
                policy_scope_id="gate19-resource-fence",
                caller_principal_ref="privacy-controller",
            )
        assert client.get(f"/v1/resource-versions/{v1_ref}").status_code == 404
        assert client.get(f"/v1/resources/{v1_ref}/impact").status_code == 404
        assert client.get(f"/v1/assertions/{assertion_ref}/explain").json() == []

        # Gate 15: bounded assertion erasure leaves no substantive client retrieval.
        erasure_person, _ = _create_entity(client, core.person_kind_revision_ref)
        erased = _append_assertion(
            client,
            subject_ref=erasure_person.json()["entity_ref"],
            predicate_revision_ref=core.has_name_predicate_revision_ref,
            profile_revision_ref=core.profile_revision_ref,
            value_kind="text",
            value="Erase Me",
        )
        erased_ref = UUID(erased.json()["assertion_ref"])
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=artifacts)
            case = kernel.fence_target_operation(
                operation_id=uuid4(),
                target_ref=erased_ref,
                action_type=DeletionActionType.ERASE,
                policy_scope_id="gate19-erasure",
                caller_principal_ref="privacy-controller",
            )
            kernel.erase_assertion_payload(case_id=case.case_id, target_ref=erased_ref)
        assert client.get(f"/v1/assertions/{erased_ref}").status_code == 404

        # Gate 16: stale restored payload state cannot beat the newer deletion ledger.
        restore_person, _ = _create_entity(client, core.person_kind_revision_ref)
        restore_assertion = _append_assertion(
            client,
            subject_ref=restore_person.json()["entity_ref"],
            predicate_revision_ref=core.has_name_predicate_revision_ref,
            profile_revision_ref=core.profile_revision_ref,
            value_kind="text",
            value="Do Not Resurrect",
        )
        restore_ref = UUID(restore_assertion.json()["assertion_ref"])
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=artifacts)
            kernel.fence_target_operation(
                operation_id=uuid4(),
                target_ref=restore_ref,
                action_type=DeletionActionType.RESTRICT,
                policy_scope_id="gate19-restore",
                caller_principal_ref="privacy-controller",
            )
        with sessions() as session:
            stale_ref = session.get(KnowledgeRef, restore_ref)
            stale_ref.payload_state = "active"
            session.commit()
        assert client.get(f"/v1/assertions/{restore_ref}").status_code == 404
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=artifacts)
            kernel.reapply_deletion_control_before_serving()
        assert client.get(f"/v1/assertions/{restore_ref}").status_code == 404
    finally:
        http.close()
        engine.dispose()



def test_gate19_identity_profile_and_generation_boundaries(tmp_path):
    engine, sessions, artifacts, core, identity, _resource, http, client = _fixture(tmp_path)
    try:
        # Gate 12: same-name entities merge without rewriting assertion subjects, then split.
        people = []
        assertions = []
        for _ in range(2):
            person, _ = _create_entity(client, identity.person_kind_revision_ref)
            people.append(person.json()["entity_ref"])
            named = _append_assertion(
                client,
                subject_ref=people[-1],
                predicate_revision_ref=identity.has_name_predicate_revision_ref,
                profile_revision_ref=identity.profile_revision_ref,
                value_kind="text",
                value="Robert Smith",
            )
            assertions.append(named.json())

        merge = client.post(
            "/v1/identity/merge",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": client.status_revision(),
                "entity_refs": people,
                "representative_ref": people[0],
                "identity_kind_revision_ref": str(identity.identity_resolution_kind_revision_ref),
            },
        )
        assert merge.status_code == 200
        left = client.get(f"/v1/identity/entities/{people[0]}").json()
        right = client.get(f"/v1/identity/entities/{people[1]}").json()
        assert left["resolution_group_id"] == right["resolution_group_id"]
        assert set(left["member_refs"]) == set(people)
        assert left["representative_ref"] == people[0]
        for expected_assertion in assertions:
            current = client.get(f"/v1/assertions/{expected_assertion['assertion_ref']}")
            assert current.status_code == 200
            assert current.json()["subject_ref"] == expected_assertion["subject_ref"]

        split = client.post(
            f"/v1/identity/transitions/{merge.json()['transition_ref']}/reverse",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": client.status_revision(),
                "identity_kind_revision_ref": str(identity.identity_resolution_kind_revision_ref),
            },
        )
        assert split.status_code == 200
        left_after = client.get(f"/v1/identity/entities/{people[0]}").json()
        right_after = client.get(f"/v1/identity/entities/{people[1]}").json()
        assert left_after["member_refs"] == [people[0]]
        assert right_after["member_refs"] == [people[1]]
        assert left_after["resolution_group_id"] != right_after["resolution_group_id"]

        # Gate 13: replacement records succession but never equivalence.
        old_device, _ = _create_entity(client, identity.device_kind_revision_ref)
        new_device, _ = _create_entity(client, identity.device_kind_revision_ref)
        old_ref = old_device.json()["entity_ref"]
        new_ref = new_device.json()["entity_ref"]
        replace = client.post(
            "/v1/identity/replace",
            json={
                "operation_id": str(uuid4()),
                "expected_revision": client.status_revision(),
                "old_entity_ref": old_ref,
                "new_entity_ref": new_ref,
                "identity_kind_revision_ref": str(identity.identity_resolution_kind_revision_ref),
            },
        )
        assert replace.status_code == 200
        assert replace.json()["transition_type"] == "replace"
        old_resolution = client.get(f"/v1/identity/entities/{old_ref}").json()
        new_resolution = client.get(f"/v1/identity/entities/{new_ref}").json()
        assert old_resolution["member_refs"] == [old_ref]
        assert new_resolution["member_refs"] == [new_ref]
        assert old_resolution["resolution_group_id"] != new_resolution["resolution_group_id"]

        # Gate 17: client-created v1 assertion stays pinned after server activates v2.
        v1_person, _ = _create_entity(client, core.person_kind_revision_ref)
        v1_assertion = _append_assertion(
            client,
            subject_ref=v1_person.json()["entity_ref"],
            predicate_revision_ref=core.has_name_predicate_revision_ref,
            profile_revision_ref=core.profile_revision_ref,
            value_kind="text",
            value="Pinned V1",
        )
        v1_assertion_ref = v1_assertion.json()["assertion_ref"]
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=artifacts)
            kernel.activate_profile_revision_operation(
                operation_id=uuid4(),
                profile_ref=core.profile_ref,
                profile_revision_ref=core.profile_revision_ref,
                caller_principal_ref="profile-controller",
                expected_revision=kernel.current_revision(),
            )
            v2 = kernel.create_profile_revision_operation(
                operation_id=uuid4(),
                profile_ref=core.profile_ref,
                source_profile_revision_ref=core.profile_revision_ref,
                version_label="2",
                caller_principal_ref="profile-controller",
                expected_revision=kernel.current_revision(),
            )
            vocab = kernel.profile_vocabulary(profile_revision_ref=v2.profile_revision_ref)
            person_v2 = _term(vocab.kinds, "person")
            has_name_v2 = _term(vocab.predicates, "has_name")
            kernel.activate_profile_revision_operation(
                operation_id=uuid4(),
                profile_ref=core.profile_ref,
                profile_revision_ref=v2.profile_revision_ref,
                caller_principal_ref="profile-controller",
                expected_revision=kernel.current_revision(),
            )

        old_after_activation = client.get(f"/v1/assertions/{v1_assertion_ref}")
        assert old_after_activation.status_code == 200
        assert old_after_activation.json()["profile_revision_ref"] == str(core.profile_revision_ref)
        assert old_after_activation.json()["predicate_revision_ref"] == str(core.has_name_predicate_revision_ref)
        v2_person, _ = _create_entity(client, person_v2.revision_ref)
        v2_assertion = _append_assertion(
            client,
            subject_ref=v2_person.json()["entity_ref"],
            predicate_revision_ref=has_name_v2.revision_ref,
            profile_revision_ref=v2.profile_revision_ref,
            value_kind="text",
            value="Pinned V2",
        )
        assert v2_assertion.json()["profile_revision_ref"] == str(v2.profile_revision_ref)
        assert v2_assertion.json()["predicate_revision_ref"] == str(has_name_v2.revision_ref)
        assert v2_assertion.json()["predicate_revision_ref"] != old_after_activation.json()["predicate_revision_ref"]

        # Gate 18 remains an internal derived-control concern; the normal client gets no
        # generation/admin route. Its server-side race fence remains intact while the
        # same service-only client continues to operate normally.
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=artifacts)
            highwater = kernel.current_revision()
            older = kernel.start_generation(
                derived_kind=DerivedKind.CURRENT_STATE,
                source_revision_highwater=highwater,
                profile_revision_ref=v2.profile_revision_ref,
            )
            newer = kernel.start_generation(
                derived_kind=DerivedKind.CURRENT_STATE,
                source_revision_highwater=highwater,
                profile_revision_ref=v2.profile_revision_ref,
            )
            kernel.settle_generation(generation_id=newer.generation_id)
            with pytest.raises(GenerationFenceError):
                kernel.settle_generation(generation_id=older.generation_id)
        assert client.get("/v1/status").status_code == 200
        paths = set(http.get("/openapi.json").json()["paths"])
        assert not any("generation" in path for path in paths)
    finally:
        http.close()
        engine.dispose()
