from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from knowledge_core.application.unified_retrieval import (
    UnifiedGraphSearchBinding,
    UnifiedRetrievalCoordinator,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.projection_adapter import (
    TrustedProjectionHit,
    TrustedProjectionSearchSnapshot,
)
from knowledge_core.domain.retrieval import RetrievalSearchSnapshot
from knowledge_core.domain.source_neutral_projection import (
    GovernedProjectionSourceSegment,
    SOURCE_NEUTRAL_GRAPH_REFERENCE_TIME_POLICY,
)
from knowledge_core.domain.unified_retrieval import GraphRetrievalState


class _LexicalKernel:
    def __init__(self, snapshot=None, error: Exception | None = None):
        self.snapshot = snapshot
        self.error = error
        self.calls = []

    def search_text(self, *, query, limit, include_superseded):
        self.calls.append(
            {
                "query": query,
                "limit": limit,
                "include_superseded": include_superseded,
            }
        )
        if self.error is not None:
            raise self.error
        return self.snapshot


class _GraphKernel:
    def __init__(self, snapshot=None, error: Exception | None = None):
        self.snapshot = snapshot
        self.error = error
        self.calls = []

    async def search_validated_projection(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.snapshot


class _Adapter:
    pass


class _Authority:
    pass


def _lexical(*, generation_id=None) -> RetrievalSearchSnapshot:
    return RetrievalSearchSnapshot(
        query="Why did we choose Mason?",
        generation_id=generation_id,
        source_revision_highwater=(9 if generation_id is not None else None),
        results=(),
        retrieval_mode="segment",
        generation_config_digest=("sha256:text" if generation_id is not None else None),
    )


def _binding() -> UnifiedGraphSearchBinding:
    return UnifiedGraphSearchBinding(
        adapter=_Adapter(),
        authority_evaluator=_Authority(),
        caller_principal_ref="local_owner",
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


def test_graph_not_configured_returns_lexical_plus_disabled_warning():
    generation_id = uuid4()
    lexical = _LexicalKernel(_lexical(generation_id=generation_id))
    graph = _GraphKernel(error=AssertionError("graph must not be called"))
    coordinator = UnifiedRetrievalCoordinator(
        lexical_kernel=lexical,
        graph_kernel=graph,
        graph_binding=None,
    )

    result = asyncio.run(
        coordinator.search(query="Why did we choose Mason?", limit=5)
    )

    assert result.lexical.generation_id == generation_id
    assert result.graph.state is GraphRetrievalState.DISABLED
    assert result.graph.results == ()
    assert result.warnings[0].code.value == "graph_disabled"
    assert graph.calls == []


def test_lexical_failure_is_not_masked_by_graph_degradation():
    lexical_error = KnowledgeInvariantError("lexical lineage failed")
    lexical = _LexicalKernel(error=lexical_error)
    graph = _GraphKernel(error=AssertionError("graph must not be called"))
    coordinator = UnifiedRetrievalCoordinator(
        lexical_kernel=lexical,
        graph_kernel=graph,
        graph_binding=_binding(),
    )

    with pytest.raises(KnowledgeInvariantError, match="lexical lineage failed"):
        asyncio.run(coordinator.search(query="Mason"))
    assert graph.calls == []


def test_empty_lexical_generation_does_not_call_graph_provider():
    lexical = _LexicalKernel(_lexical(generation_id=None))
    graph = _GraphKernel(error=AssertionError("graph must not be called"))
    coordinator = UnifiedRetrievalCoordinator(
        lexical_kernel=lexical,
        graph_kernel=graph,
        graph_binding=_binding(),
    )

    result = asyncio.run(coordinator.search(query="Mason"))

    assert result.graph.state is GraphRetrievalState.NO_BUILD
    assert result.graph.reason_code == "no-current-text-generation"
    assert graph.calls == []


def test_historical_lexical_request_does_not_mix_current_graph_evidence():
    generation_id = uuid4()
    lexical = _LexicalKernel(_lexical(generation_id=generation_id))
    graph = _GraphKernel(error=AssertionError("graph must not be called"))
    coordinator = UnifiedRetrievalCoordinator(
        lexical_kernel=lexical,
        graph_kernel=graph,
        graph_binding=_binding(),
    )

    result = asyncio.run(
        coordinator.search(
            query="old Mason data",
            include_superseded=True,
        )
    )

    assert result.graph.state is GraphRetrievalState.DISABLED
    assert result.graph.reason_code == "graph-augmentation-current-only"
    assert lexical.calls[0]["include_superseded"] is True
    assert graph.calls == []


def test_no_compatible_validated_build_degrades_as_unavailable():
    generation_id = uuid4()
    lexical = _LexicalKernel(_lexical(generation_id=generation_id))
    graph = _GraphKernel(
        TrustedProjectionSearchSnapshot(
            query="Mason",
            namespace_key="kc:graphiti-source-neutral-v1",
            scope_key="project:knowledge-core",
            generation_id=generation_id,
            attempt_ids=(),
            results=(),
        )
    )
    coordinator = UnifiedRetrievalCoordinator(
        lexical_kernel=lexical,
        graph_kernel=graph,
        graph_binding=_binding(),
    )

    result = asyncio.run(coordinator.search(query="Mason", limit=4))

    assert result.graph.state is GraphRetrievalState.UNAVAILABLE
    assert result.graph.reason_code == "no-compatible-validated-graph-build"
    assert result.graph.results == ()
    assert result.warnings[0].code.value == "graph_unavailable"
    assert graph.calls[0]["limit"] == 4
    assert graph.calls[0]["query"] == "Mason"


def test_generation_change_drops_graph_lane_as_stale():
    lexical_generation = uuid4()
    graph_generation = uuid4()
    lexical = _LexicalKernel(_lexical(generation_id=lexical_generation))
    graph = _GraphKernel(_ready_graph(generation_id=graph_generation))
    coordinator = UnifiedRetrievalCoordinator(
        lexical_kernel=lexical,
        graph_kernel=graph,
        graph_binding=_binding(),
    )

    result = asyncio.run(coordinator.search(query="Mason"))

    assert result.graph.state is GraphRetrievalState.STALE
    assert result.graph.results == ()
    assert result.graph.reason_code == "text-generation-changed-before-graph-correlation"


def test_graph_exception_is_nondisclosing_and_lexical_remains_valid():
    generation_id = uuid4()
    lexical = _LexicalKernel(_lexical(generation_id=generation_id))
    graph = _GraphKernel(error=RuntimeError("secret provider detail"))
    coordinator = UnifiedRetrievalCoordinator(
        lexical_kernel=lexical,
        graph_kernel=graph,
        graph_binding=_binding(),
    )

    result = asyncio.run(coordinator.search(query="Mason"))

    assert result.lexical.generation_id == generation_id
    assert result.graph.state is GraphRetrievalState.UNAVAILABLE
    assert result.graph.reason_code == "graph-evidence-unavailable"
    assert "secret" not in result.warnings[0].message


def test_ready_graph_maps_exact_source_neutral_correlation_without_body():
    generation_id = uuid4()
    lexical = _LexicalKernel(_lexical(generation_id=generation_id))
    graph_snapshot = _ready_graph(generation_id=generation_id)
    graph = _GraphKernel(graph_snapshot)
    coordinator = UnifiedRetrievalCoordinator(
        lexical_kernel=lexical,
        graph_kernel=graph,
        graph_binding=_binding(),
    )

    result = asyncio.run(
        coordinator.search(query="Why did we choose Mason?")
    )

    assert result.graph.state is GraphRetrievalState.READY
    assert result.graph.generation_id == generation_id
    assert result.graph.attempt_ids == graph_snapshot.attempt_ids
    assert result.graph.results[0].fact.startswith("Mason is")
    source = result.graph.results[0].sources[0]
    original = graph_snapshot.results[0].sources[0]
    assert source.resource_version_ref == original.resource_version_ref
    assert source.segment_key == original.segment_key
    assert source.governing_snapshot_digest == original.governing_snapshot_digest
    assert not hasattr(source, "body")
    assert not hasattr(source, "content")


def test_non_source_neutral_trusted_hit_is_quarantined_to_graph_lane():
    generation_id = uuid4()
    lexical = _LexicalKernel(_lexical(generation_id=generation_id))
    malformed = TrustedProjectionSearchSnapshot(
        query="Mason",
        namespace_key="kc:graphiti-source-neutral-v1",
        scope_key="project:knowledge-core",
        generation_id=generation_id,
        attempt_ids=(uuid4(),),
        results=(
            TrustedProjectionHit(
                provider_hit_id="edge-legacy",
                fact="legacy",
                valid_at=None,
                invalid_at=None,
                sources=(object(),),
            ),
        ),
    )
    graph = _GraphKernel(malformed)
    coordinator = UnifiedRetrievalCoordinator(
        lexical_kernel=lexical,
        graph_kernel=graph,
        graph_binding=_binding(),
    )

    result = asyncio.run(coordinator.search(query="Mason"))

    assert result.graph.state is GraphRetrievalState.UNAVAILABLE
    assert result.graph.results == ()
