from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.retrieval import RetrievalSearchSnapshot


UNIFIED_RETRIEVAL_EVIDENCE_CONTRACT_VERSION = "kc-unified-retrieval-evidence-v1"


class GraphRetrievalState(StrEnum):
    """Bounded public graph-lane state for unified search.

    ``ready`` is the only state allowed to carry graph results. Every other state
    explicitly degrades to the independently authorized lexical lane. Authorization
    failures are intentionally not exposed as a distinct public state; callers may
    receive ``unavailable`` without learning graph policy details.
    """

    DISABLED = "disabled"
    NO_BUILD = "no_build"
    READY = "ready"
    STALE = "stale"
    PENDING = "pending"
    UNVALIDATED = "unvalidated"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class UnifiedRetrievalWarningCode(StrEnum):
    GRAPH_DISABLED = "graph_disabled"
    GRAPH_NO_BUILD = "graph_no_build"
    GRAPH_STALE = "graph_stale"
    GRAPH_PENDING = "graph_pending"
    GRAPH_UNVALIDATED = "graph_unvalidated"
    GRAPH_FAILED = "graph_failed"
    GRAPH_UNAVAILABLE = "graph_unavailable"


_GRAPH_WARNING_FOR_STATE = {
    GraphRetrievalState.DISABLED: UnifiedRetrievalWarningCode.GRAPH_DISABLED,
    GraphRetrievalState.NO_BUILD: UnifiedRetrievalWarningCode.GRAPH_NO_BUILD,
    GraphRetrievalState.STALE: UnifiedRetrievalWarningCode.GRAPH_STALE,
    GraphRetrievalState.PENDING: UnifiedRetrievalWarningCode.GRAPH_PENDING,
    GraphRetrievalState.UNVALIDATED: UnifiedRetrievalWarningCode.GRAPH_UNVALIDATED,
    GraphRetrievalState.FAILED: UnifiedRetrievalWarningCode.GRAPH_FAILED,
    GraphRetrievalState.UNAVAILABLE: UnifiedRetrievalWarningCode.GRAPH_UNAVAILABLE,
}


@dataclass(frozen=True)
class UnifiedRetrievalWarning:
    code: UnifiedRetrievalWarningCode
    message: str

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise KnowledgeInvariantError("unified retrieval warning message must not be blank")


@dataclass(frozen=True)
class GraphSourceCorrelation:
    """Exact KC evidence that supports one trusted graph fact.

    Full canonical content is deliberately not duplicated here. Consumers follow
    ``resource_version_ref`` through the accepted ``kc_get_source`` operation when
    they need exact source content.
    """

    resource_version_ref: UUID
    source_revision_id: int
    segment_key: str
    segment_ordinal: int
    source_slice_sha256: str
    source_line_start: int
    source_line_end: int
    source_identity_digest: str
    source_kind: str
    origin_scope: str
    collection_key: str
    item_key: str
    project_keys: tuple[str, ...]
    governed_source_observation_id: UUID
    governed_observation_digest: str
    governed_decision_id: UUID
    governed_decision_digest: str
    governing_snapshot_digest: str
    governed_projection_digest: str
    reference_time: datetime
    reference_time_policy: str
    source_repository_key: str | None = None
    source_document_key: str | None = None
    source_path: str | None = None
    source_version: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "segment_key",
            "source_slice_sha256",
            "source_identity_digest",
            "source_kind",
            "origin_scope",
            "collection_key",
            "item_key",
            "governed_observation_digest",
            "governed_decision_digest",
            "governing_snapshot_digest",
            "governed_projection_digest",
            "reference_time_policy",
        ):
            if not str(getattr(self, name)).strip():
                raise KnowledgeInvariantError(
                    f"graph source correlation {name} must not be blank"
                )
        if self.source_revision_id < 1:
            raise KnowledgeInvariantError(
                "graph source correlation source_revision_id must be positive"
            )
        if self.segment_ordinal < 0:
            raise KnowledgeInvariantError(
                "graph source correlation segment_ordinal must be non-negative"
            )
        if self.source_line_start < 1 or self.source_line_end < self.source_line_start:
            raise KnowledgeInvariantError(
                "graph source correlation line range is invalid"
            )


@dataclass(frozen=True)
class GraphRetrievalHit:
    provider_hit_id: str
    fact: str
    valid_at: datetime | None
    invalid_at: datetime | None
    sources: tuple[GraphSourceCorrelation, ...]

    def __post_init__(self) -> None:
        if not self.provider_hit_id.strip():
            raise KnowledgeInvariantError("graph provider_hit_id must not be blank")
        if not self.fact.strip():
            raise KnowledgeInvariantError("graph fact must not be blank")
        if not self.sources:
            raise KnowledgeInvariantError(
                "trusted graph retrieval hit must have at least one exact KC source"
            )


@dataclass(frozen=True)
class GraphRetrievalEvidence:
    state: GraphRetrievalState
    namespace_key: str | None = None
    scope_key: str | None = None
    generation_id: UUID | None = None
    attempt_ids: tuple[UUID, ...] = ()
    results: tuple[GraphRetrievalHit, ...] = ()
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if len(set(self.attempt_ids)) != len(self.attempt_ids):
            raise KnowledgeInvariantError(
                "graph retrieval attempt_ids must not contain duplicates"
            )

        if self.state is GraphRetrievalState.READY:
            if not self.namespace_key or not self.namespace_key.strip():
                raise KnowledgeInvariantError(
                    "ready graph retrieval evidence requires namespace_key"
                )
            if not self.scope_key or not self.scope_key.strip():
                raise KnowledgeInvariantError(
                    "ready graph retrieval evidence requires scope_key"
                )
            if self.generation_id is None:
                raise KnowledgeInvariantError(
                    "ready graph retrieval evidence requires generation_id"
                )
            if not self.attempt_ids:
                raise KnowledgeInvariantError(
                    "ready graph retrieval evidence requires validated attempt_ids"
                )
        else:
            if self.results:
                raise KnowledgeInvariantError(
                    "non-ready graph retrieval evidence must not expose graph results"
                )
            if self.reason_code is None or not self.reason_code.strip():
                raise KnowledgeInvariantError(
                    "non-ready graph retrieval evidence requires bounded reason_code"
                )

        if self.reason_code is not None and not self.reason_code.strip():
            raise KnowledgeInvariantError(
                "graph retrieval reason_code must not be blank when supplied"
            )


@dataclass(frozen=True)
class UnifiedRetrievalSearchSnapshot:
    """Task 6B contract for one future ``kc_search`` response.

    The lexical snapshot is mandatory and keeps its existing evidence contract.
    Graph evidence is additive, separately stateful, and never permitted to make
    otherwise-valid lexical retrieval unavailable.
    """

    lexical: RetrievalSearchSnapshot
    graph: GraphRetrievalEvidence
    warnings: tuple[UnifiedRetrievalWarning, ...] = ()
    evidence_contract_version: str = UNIFIED_RETRIEVAL_EVIDENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if (
            self.evidence_contract_version
            != UNIFIED_RETRIEVAL_EVIDENCE_CONTRACT_VERSION
        ):
            raise KnowledgeInvariantError(
                "unsupported unified retrieval evidence contract version"
            )

        if self.graph.state is GraphRetrievalState.READY:
            if self.graph.generation_id != self.lexical.generation_id:
                raise KnowledgeInvariantError(
                    "ready graph evidence must match the lexical text generation"
                )
            return

        expected = _GRAPH_WARNING_FOR_STATE[self.graph.state]
        if not any(item.code is expected for item in self.warnings):
            raise KnowledgeInvariantError(
                f"graph state {self.graph.state.value} requires warning {expected.value}"
            )
