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


def test_prepare_controller_invocation_uses_public_service_and_seals_packet_digest():
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

        def prepare_invocation(self, attempt_id, workspace_root, prompt):
            assert attempt_id == attempt.attempt_id
            assert str(workspace_root) == "workspace-root"
            captured["prompt"] = prompt
            return FakeInvocation(prompt)

    prepared = prepare_controller_task_invocation(
        FakeService(),
        attempt_id=attempt.attempt_id,
        workspace_root="workspace-root",
        controller_identity="trusted-controller",
        user_request="Use retrieved guidance but do not expand scope.",
        kc_search_response=kc_response(),
    )
    assert captured["prompt"] == prepared.packet.to_json()
    assert prepared.packet_digest == prepared.invocation.to_dict()["record"]["prompt_digest"]
