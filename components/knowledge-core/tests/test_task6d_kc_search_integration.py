from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.application.consumer_read import ConsumerReadKnowledgeKernel
from knowledge_core.application.source_neutral_graph import (
    SourceNeutralGraphProjectionKnowledgeKernel,
)
from knowledge_core.application.unified_retrieval import UnifiedGraphSearchBinding
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityDecision,
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
)
from knowledge_core.domain.projection_adapter import (
    TrustedProjectionHit,
    TrustedProjectionSearchSnapshot,
)
from knowledge_core.domain.retrieval import RetrievalSearchSnapshot
from knowledge_core.domain.source_neutral_projection import (
    GovernedProjectionSourceSegment,
    SOURCE_NEUTRAL_GRAPH_REFERENCE_TIME_POLICY,
)


_BOOTSTRAP_KEY = "task6d-bootstrap-key"


class _Session:
    def __init__(self):
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _Adapter:
    pass


class _GraphAuthority:
    pass


@dataclass
class _RecordingAuthority:
    allowed: bool
    requests: list[RetrievalAuthorityRequest] = field(default_factory=list)

    def evaluate_retrieval(
        self,
        request: RetrievalAuthorityRequest,
    ) -> RetrievalAuthorityDecision:
        self.requests.append(request)
        return RetrievalAuthorityDecision(
            allowed=self.allowed,
            decision_ref="task6d-text-authority",
            reason_code="task6d-test",
        )


def _admission() -> BootstrapAdmission:
    return BootstrapAdmission(
        contract=BootstrapContract(),
        api_key=_BOOTSTRAP_KEY,
    )


def _headers() -> dict[str, str]:
    return {"X-Knowledge-Key": _BOOTSTRAP_KEY}


def _session_factory(created: list[_Session]):
    def factory():
        session = _Session()
        created.append(session)
        return session

    return factory


def _lexical(*, generation_id) -> RetrievalSearchSnapshot:
    return RetrievalSearchSnapshot(
        query="Why did we choose Mason?",
        generation_id=generation_id,
        source_revision_highwater=9,
        results=(),
        retrieval_mode="segment",
        generation_config_digest="sha256:text-generation",
        structural_profile_id="sr2-structure",
        structural_profile_digest="sha256:structure",
        projection_profile_id="sr2-projection",
        projection_profile_digest="sha256:projection",
    )


def _binding(*, principal: str = "local_owner") -> UnifiedGraphSearchBinding:
    return UnifiedGraphSearchBinding(
        adapter=_Adapter(),
        authority_evaluator=_GraphAuthority(),
        caller_principal_ref=principal,
        namespace_key="kc:graphiti-source-neutral-v1",
        scope_key="project:knowledge-core",
    )


def _source(*, generation_id) -> GovernedProjectionSourceSegment:
    now = datetime.now(timezone.utc)
    return GovernedProjectionSourceSegment(
        generation_id=generation_id,
        resource_version_ref=uuid4(),
        source_revision_id=9,
        segment_key="segment-0",
        segment_ordinal=0,
        source_slice_sha256="a" * 64,
        source_byte_start=0,
        source_byte_end=12,
        source_line_start=1,
        source_line_end=1,
        effective_lifecycle_state="current",
        source_repository_key=None,
        source_document_key=None,
        source_path=None,
        source_version=None,
        heading_path=(),
        reference_time=now,
        body="Mason fact.",
        governed_source_observation_id=uuid4(),
        governed_observation_digest="sha256:" + "b" * 64,
        governed_decision_id=uuid4(),
        governed_decision_digest="sha256:" + "c" * 64,
        governing_snapshot_digest="sha256:" + "d" * 64,
        governed_projection_digest="sha256:" + "e" * 64,
        source_identity_digest="sha256:" + "f" * 64,
        source_kind="local.user-note",
        origin_scope="local_owner",
        collection_key="notes",
        item_key="mason-model-identity",
        project_keys=("local-ai",),
        producer_id="kc.direct-note",
        producer_version="kc-direct-note-producer-v1",
        source_observed_at=now,
        source_event_time=now,
        source_revision_time=None,
        governance_policy_id="kc-direct-note-governance-v1",
        governance_rationale="Authenticated local owner direct note submission.",
        governance_decided_at=now,
        reference_time_policy=SOURCE_NEUTRAL_GRAPH_REFERENCE_TIME_POLICY,
    )


def _ready_graph(*, generation_id) -> TrustedProjectionSearchSnapshot:
    source = _source(generation_id=generation_id)
    return TrustedProjectionSearchSnapshot(
        query="Why did we choose Mason?",
        namespace_key="kc:graphiti-source-neutral-v1",
        scope_key="project:knowledge-core",
        generation_id=generation_id,
        attempt_ids=(uuid4(),),
        results=(
            TrustedProjectionHit(
                provider_hit_id="edge-1",
                fact="Mason is the local MindsHub worker model.",
                valid_at=None,
                invalid_at=None,
                sources=(source,),
            ),
        ),
    )


def test_kc_search_keeps_existing_request_and_lexical_fields_when_graph_disabled(
    monkeypatch,
    tmp_path: Path,
):
    generation_id = uuid4()
    created: list[_Session] = []
    calls = []

    def fake_search(self, *, query, limit, include_superseded):
        calls.append((query, limit, include_superseded))
        return _lexical(generation_id=generation_id)

    monkeypatch.setattr(ConsumerReadKnowledgeKernel, "search_text", fake_search)

    app = create_app(
        session_factory=_session_factory(created),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
        bootstrap_admission=_admission(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1/kc/search",
            headers=_headers(),
            json={
                "query": "Why did we choose Mason?",
                "limit": 7,
                "include_superseded": False,
            },
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert calls == [("Why did we choose Mason?", 7, False)]
    assert payload["query"] == "Why did we choose Mason?"
    assert payload["generation_id"] == str(generation_id)
    assert payload["retrieval_mode"] == "segment"
    assert payload["evidence_contract_version"] == "kc-lexical-evidence-v2"
    assert payload["results"] == []
    assert payload["unified_evidence_contract_version"] == "kc-unified-retrieval-evidence-v1"
    assert payload["graph"]["state"] == "disabled"
    assert payload["graph"]["results"] == []
    assert payload["warnings"][0]["code"] == "graph_disabled"
    assert created and all(session.closed for session in created)


def test_kc_search_can_return_ready_graph_evidence_through_existing_route(
    monkeypatch,
    tmp_path: Path,
):
    generation_id = uuid4()
    created: list[_Session] = []
    graph_calls = []

    def fake_search(self, *, query, limit, include_superseded):
        return _lexical(generation_id=generation_id)

    async def fake_graph_search(self, **kwargs):
        graph_calls.append(kwargs)
        return _ready_graph(generation_id=generation_id)

    monkeypatch.setattr(ConsumerReadKnowledgeKernel, "search_text", fake_search)
    monkeypatch.setattr(
        SourceNeutralGraphProjectionKnowledgeKernel,
        "search_validated_projection",
        fake_graph_search,
    )

    app = create_app(
        session_factory=_session_factory(created),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
        bootstrap_admission=_admission(),
        unified_graph_search_binding=_binding(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1/kc/search",
            headers=_headers(),
            json={"query": "Why did we choose Mason?", "limit": 4},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["evidence_contract_version"] == "kc-lexical-evidence-v2"
    assert payload["unified_evidence_contract_version"] == "kc-unified-retrieval-evidence-v1"
    assert payload["graph"]["state"] == "ready"
    assert payload["graph"]["generation_id"] == str(generation_id)
    assert payload["graph"]["results"][0]["provider_hit_id"] == "edge-1"
    assert payload["graph"]["results"][0]["fact"].startswith("Mason is")
    source = payload["graph"]["results"][0]["sources"][0]
    assert source["source_kind"] == "local.user-note"
    assert source["origin_scope"] == "local_owner"
    assert "body" not in source
    assert "content" not in source
    assert graph_calls[0]["caller_principal_ref"] == "local_owner"
    assert graph_calls[0]["query"] == "Why did we choose Mason?"
    assert graph_calls[0]["limit"] == 4
    assert created and all(session.closed for session in created)


def test_kc_search_graph_binding_cannot_substitute_bootstrap_principal(tmp_path: Path):
    created: list[_Session] = []
    with pytest.raises(ValueError, match="principal must match bootstrap principal"):
        create_app(
            session_factory=_session_factory(created),
            artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
            bootstrap_admission=_admission(),
            unified_graph_search_binding=_binding(principal="different-principal"),
        )
    assert created == []


def test_kc_search_preserves_optional_fail_closed_text_authority_before_lexical_search(
    monkeypatch,
    tmp_path: Path,
):
    created: list[_Session] = []
    authority = _RecordingAuthority(allowed=False)

    def forbidden_search(self, *, query, limit, include_superseded):
        raise AssertionError("denied text Authority must run before lexical retrieval")

    monkeypatch.setattr(ConsumerReadKnowledgeKernel, "search_text", forbidden_search)

    app = create_app(
        session_factory=_session_factory(created),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
        bootstrap_admission=_admission(),
        retrieval_authority_evaluator=authority,
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1/kc/search",
            headers=_headers(),
            json={"query": "protected Mason evidence", "limit": 3},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "knowledge item is unavailable"}
    assert len(authority.requests) == 1
    request = authority.requests[0]
    assert request.caller_principal_ref == "local_owner"
    assert request.operation is RetrievalAuthorityOperation.SEARCH_TEXT
    assert request.limit == 3
    assert request.include_superseded is False
    assert created and all(session.closed for session in created)
