from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from knowledge_core.api.unified_retrieval_schemas import (
    unified_retrieval_response_from_domain,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.retrieval import RetrievalSearchSnapshot
from knowledge_core.domain.unified_retrieval import (
    GraphRetrievalEvidence,
    GraphRetrievalHit,
    GraphRetrievalState,
    GraphSourceCorrelation,
    UNIFIED_RETRIEVAL_EVIDENCE_CONTRACT_VERSION,
    UnifiedRetrievalSearchSnapshot,
    UnifiedRetrievalWarning,
    UnifiedRetrievalWarningCode,
)


def _lexical() -> RetrievalSearchSnapshot:
    return RetrievalSearchSnapshot(
        query="Why did we choose Mason?",
        generation_id=uuid4(),
        source_revision_highwater=9,
        results=(),
        retrieval_mode="sr2_segment",
        generation_config_digest="sha256:text-generation",
        structural_profile_id="sr2-structure",
        structural_profile_digest="sha256:structure",
        projection_profile_id="sr2-projection",
        projection_profile_digest="sha256:projection",
    )


def _source() -> GraphSourceCorrelation:
    now = datetime.now(timezone.utc)
    return GraphSourceCorrelation(
        resource_version_ref=uuid4(),
        source_revision_id=9,
        segment_key="segment-0",
        segment_ordinal=0,
        source_slice_sha256="a" * 64,
        source_line_start=1,
        source_line_end=3,
        source_identity_digest="sha256:" + "b" * 64,
        source_kind="local.user-note",
        origin_scope="local_owner",
        collection_key="notes",
        item_key="mason-model-identity",
        project_keys=("local-ai",),
        governed_source_observation_id=uuid4(),
        governed_observation_digest="sha256:" + "c" * 64,
        governed_decision_id=uuid4(),
        governed_decision_digest="sha256:" + "d" * 64,
        governing_snapshot_digest="sha256:" + "e" * 64,
        governed_projection_digest="sha256:" + "f" * 64,
        reference_time=now,
        reference_time_policy="source-event-then-revision-then-observed-v1",
    )


def test_non_ready_graph_lane_requires_matching_degradation_warning():
    with pytest.raises(KnowledgeInvariantError, match="requires warning graph_stale"):
        UnifiedRetrievalSearchSnapshot(
            lexical=_lexical(),
            graph=GraphRetrievalEvidence(
                state=GraphRetrievalState.STALE,
                reason_code="current-text-generation-mismatch",
            ),
        )

    snapshot = UnifiedRetrievalSearchSnapshot(
        lexical=_lexical(),
        graph=GraphRetrievalEvidence(
            state=GraphRetrievalState.STALE,
            reason_code="current-text-generation-mismatch",
        ),
        warnings=(
            UnifiedRetrievalWarning(
                code=UnifiedRetrievalWarningCode.GRAPH_STALE,
                message="Validated graph evidence does not match the current text generation.",
            ),
        ),
    )
    assert snapshot.lexical.query == "Why did we choose Mason?"
    assert snapshot.graph.results == ()


def test_non_ready_graph_lane_cannot_expose_graph_results():
    hit = GraphRetrievalHit(
        provider_hit_id="edge-1",
        fact="Mason is the local MindsHub worker model.",
        valid_at=None,
        invalid_at=None,
        sources=(_source(),),
    )
    with pytest.raises(KnowledgeInvariantError, match="must not expose graph results"):
        GraphRetrievalEvidence(
            state=GraphRetrievalState.UNVALIDATED,
            results=(hit,),
        )


def test_ready_graph_lane_requires_current_build_identity():
    with pytest.raises(KnowledgeInvariantError, match="requires namespace_key"):
        GraphRetrievalEvidence(state=GraphRetrievalState.READY)

    graph = GraphRetrievalEvidence(
        state=GraphRetrievalState.READY,
        namespace_key="kc:graphiti-source-neutral-v1",
        scope_key="project:knowledge-core",
        generation_id=uuid4(),
        attempt_ids=(uuid4(),),
    )
    assert graph.results == ()


def test_additive_response_preserves_lexical_shape_and_separates_graph_lane():
    source = _source()
    graph = GraphRetrievalEvidence(
        state=GraphRetrievalState.READY,
        namespace_key="kc:graphiti-source-neutral-v1",
        scope_key="project:knowledge-core",
        generation_id=uuid4(),
        attempt_ids=(uuid4(),),
        results=(
            GraphRetrievalHit(
                provider_hit_id="edge-1",
                fact="Mason is the local MindsHub worker model.",
                valid_at=None,
                invalid_at=None,
                sources=(source,),
            ),
        ),
    )
    response = unified_retrieval_response_from_domain(
        UnifiedRetrievalSearchSnapshot(
            lexical=_lexical(),
            graph=graph,
        )
    )
    payload = response.model_dump(mode="json")

    assert payload["query"] == "Why did we choose Mason?"
    assert payload["evidence_contract_version"] == "kc-lexical-evidence-v2"
    assert (
        payload["unified_evidence_contract_version"]
        == UNIFIED_RETRIEVAL_EVIDENCE_CONTRACT_VERSION
    )
    assert payload["graph"]["state"] == "ready"
    assert payload["graph"]["results"][0]["fact"].startswith("Mason is")
    graph_source = payload["graph"]["results"][0]["sources"][0]
    assert graph_source["resource_version_ref"] == str(source.resource_version_ref)
    assert "content" not in graph_source
    assert "body" not in graph_source
    assert "combined_score" not in payload
    assert "score" not in payload["graph"]["results"][0]


def test_unavailable_graph_degrades_without_changing_lexical_contract():
    response = unified_retrieval_response_from_domain(
        UnifiedRetrievalSearchSnapshot(
            lexical=_lexical(),
            graph=GraphRetrievalEvidence(
                state=GraphRetrievalState.UNAVAILABLE,
                reason_code="graph-runtime-unreachable",
            ),
            warnings=(
                UnifiedRetrievalWarning(
                    code=UnifiedRetrievalWarningCode.GRAPH_UNAVAILABLE,
                    message="Graph evidence is unavailable; lexical evidence remains valid.",
                ),
            ),
        )
    )
    payload = response.model_dump(mode="json")
    assert payload["graph"]["state"] == "unavailable"
    assert payload["graph"]["results"] == []
    assert payload["results"] == []
    assert payload["warnings"][0]["code"] == "graph_unavailable"
