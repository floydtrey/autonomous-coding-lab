import hashlib
from copy import deepcopy
from types import SimpleNamespace
from uuid import UUID

import pytest

from tests.test_models import attempt_mapping
from worker_lab.controller_task_packet import (
    AUTHORITY_EFFECT,
    CONTROLLER_TASK_PACKET_SCHEMA,
    build_controller_task_packet,
    parse_controller_task_packet,
    prepare_controller_task_invocation,
)
from worker_lab.errors import LabValidationError
from worker_lab.models import AttemptRecord


def kc_response(content="# Project Guidance\nUse the bounded implementation path.\n"):
    content_bytes = content.encode("utf-8")
    return {
        "query": "bounded implementation path",
        "generation_id": str(UUID("11111111-1111-4111-8111-111111111111")),
        "source_revision_highwater": 7,
        "retrieval_mode": "segment",
        "generation_config_digest": "sha256:" + "1" * 64,
        "structural_profile_id": "kc-section-segmentation-v1",
        "structural_profile_digest": "sha256:" + "2" * 64,
        "projection_profile_id": "kc-section-retrieval-projection-v1",
        "projection_profile_digest": "sha256:" + "3" * 64,
        "results": [
            {
                "resource_ref": str(UUID("22222222-2222-4222-8222-222222222222")),
                "resource_version_ref": str(UUID("33333333-3333-4333-8333-333333333333")),
                "lifecycle_state": "current",
                "repository": "floydtrey/autonomous-coding-lab",
                "source_path": "docs/ARCHITECTURE.md",
                "source_version": "4ac3ff963f569a14db47447ee5bd0f5ac8041e4a",
                "content": content,
                "segment": {
                    "governing_manifest_digest": "4" * 64,
                    "projection_snapshot_digest": "sha256:" + "5" * 64,
                    "source_repository_key": "acl",
                    "source_document_key": "architecture",
                    "segment_key": "segment-0001",
                    "segment_ordinal": 1,
                    "source_byte_start": 100,
                    "source_byte_end": 100 + len(content_bytes),
                    "source_line_start": 5,
                    "source_line_end": 6,
                    "source_slice_sha256": hashlib.sha256(content_bytes).hexdigest(),
                    "effective_lifecycle_state": "current",
                },
            }
        ],
    }


def ready_attempt():
    value = attempt_mapping()
    value["state"] = "READY"
    return AttemptRecord.from_mapping(value)


def test_controller_packet_preserves_exact_kc_bytes_and_cannot_grant_authority():
    packet = build_controller_task_packet(
        ready_attempt(),
        controller_identity="trusted-controller",
        user_request="Use the current project guidance for this bounded task.",
        kc_search_response=kc_response(),
    )
    assert packet.schema_version == CONTROLLER_TASK_PACKET_SCHEMA
    assert packet.authority_effect == AUTHORITY_EFFECT
    assert packet.knowledge_evidence[0].content.endswith("\n")
    assert parse_controller_task_packet(packet.to_json()) == packet
    assert packet.digest().startswith("sha256:")

    changed = packet.to_dict()
    changed["authority_effect"] = "scope-authority"
    with pytest.raises(LabValidationError) as error:
        parse_controller_task_packet(
            __import__("worker_lab.canonical", fromlist=["canonical_json"]).canonical_json(changed)
        )
    assert error.value.code == "CONTROLLER_PACKET_AUTHORITY_INVALID"


def test_controller_packet_rejects_tampered_or_historical_kc_evidence():
    response = kc_response()
    tampered = deepcopy(response)
    tampered["results"][0]["content"] += "tamper"
    with pytest.raises(LabValidationError) as error:
        build_controller_task_packet(
            ready_attempt(),
            controller_identity="trusted-controller",
            user_request="Bounded task.",
            kc_search_response=tampered,
        )
    assert error.value.code == "CONTROLLER_PACKET_EVIDENCE_INVALID"

    historical = kc_response()
    historical["results"][0]["lifecycle_state"] = "superseded"
    historical["results"][0]["segment"]["effective_lifecycle_state"] = "superseded"
    with pytest.raises(LabValidationError) as error:
        build_controller_task_packet(
            ready_attempt(),
            controller_identity="trusted-controller",
            user_request="Bounded task.",
            kc_search_response=historical,
        )
    assert error.value.code == "CONTROLLER_PACKET_LIFECYCLE_INVALID"


@pytest.mark.parametrize("no_context", [False, True])
def test_prepare_controller_invocation_uses_public_service_and_seals_packet_digest(no_context):
    attempt = ready_attempt()
    captured = {}

    class FakeInvocation:
        def __init__(self, prompt):
            self.prompt = prompt

        def to_dict(self):
            digest_value = "sha256:" + hashlib.sha256(self.prompt.encode("utf-8")).hexdigest()
            return {"record": {"prompt_digest": digest_value}}

    class FakeService:
        def show_record(self, collection, identity):
            assert collection == "attempts"
            assert identity == attempt.attempt_id
            return SimpleNamespace(record=attempt.to_dict())

        def prepare_invocation(
            self, attempt_id, workspace_root, prompt, *,
            logical_target_id, provider_binding_id, provider_binding_digest,
        ):
            assert attempt_id == attempt.attempt_id
            assert str(workspace_root) == "workspace-root"
            assert logical_target_id == "target:record-model"
            assert provider_binding_id == "BINDING-0001"
            assert provider_binding_digest == "sha256:" + "a" * 64
            captured["prompt"] = prompt
            return FakeInvocation(prompt)

    prepared = prepare_controller_task_invocation(
        FakeService(),
        attempt_id=attempt.attempt_id,
        workspace_root="workspace-root",
        logical_target_id="target:record-model",
        provider_binding_id="BINDING-0001",
        provider_binding_digest="sha256:" + "a" * 64,
        controller_identity="trusted-controller",
        user_request="Use retrieved guidance but do not expand scope.",
        **({"no_context": True} if no_context else {"kc_search_response": kc_response()}),
    )
    assert captured["prompt"] == prepared.packet.to_json()
    assert prepared.packet_digest == prepared.invocation.to_dict()["record"]["prompt_digest"]


def test_explicit_no_context_is_deterministic_without_retrieval(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("no-context preparation must not consume a KC search response")
    monkeypatch.setattr("worker_lab.controller_task_packet.knowledge_evidence_from_search_response", forbidden)
    kwargs = dict(controller_identity="trusted-controller", user_request="Self-contained task.", no_context=True)
    packet = build_controller_task_packet(ready_attempt(), **kwargs)
    assert packet.schema_version == "worker-lab-controller-task-packet:v2"
    assert packet.context_mode == "none"
    assert packet.knowledge_evidence == ()
    assert parse_controller_task_packet(packet.to_json()) == packet
    assert build_controller_task_packet(ready_attempt(), **kwargs).digest() == packet.digest()


@pytest.mark.parametrize("kwargs", [
    {}, {"no_context": "true"}, {"no_context": True, "kc_search_response": {}},
    {"no_context": True, "result_indexes": ()}, {"kc_search_response": {"results": []}},
])
def test_missing_or_contradictory_context_input_is_rejected(kwargs):
    with pytest.raises(LabValidationError):
        build_controller_task_packet(ready_attempt(), controller_identity="trusted-controller",
                                     user_request="Bounded task.", **kwargs)


@pytest.mark.parametrize("schema,mode,has_evidence,valid", [
    ("v1", None, True, True), ("v1", None, False, False),
    ("v1", "none", False, False), ("v2", None, False, False),
    ("v2", "none", False, True), ("v2", "none", True, False),
    ("v2", "knowledge-core", True, True), ("v2", "knowledge-core", False, False),
    ("v2", "unknown", False, False), ("v3", "none", False, False),
])
def test_packet_context_schema_matrix(schema, mode, has_evidence, valid):
    from worker_lab.canonical import canonical_json
    packet = build_controller_task_packet(ready_attempt(), controller_identity="trusted-controller",
        user_request="Bounded task.", kc_search_response=kc_response()).to_dict()
    packet["schema_version"] = "worker-lab-controller-task-packet:" + schema
    if mode is not None:
        packet["context_mode"] = mode
    if not has_evidence:
        packet["knowledge_evidence"] = []
    raw = canonical_json(packet)
    if valid:
        assert parse_controller_task_packet(raw).to_json() == raw
    else:
        with pytest.raises(LabValidationError):
            parse_controller_task_packet(raw)
