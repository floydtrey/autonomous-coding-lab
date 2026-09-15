from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from knowledge_core.domain.projection_adapter import ProjectionSourceSegment


SOURCE_NEUTRAL_GRAPH_PLAN_VERSION = "kc-source-neutral-graph-plan-v1"
SOURCE_NEUTRAL_GRAPH_REFERENCE_TIME_POLICY = (
    "source-event-then-revision-then-observed-v1"
)


@dataclass(frozen=True)
class GovernedProjectionSourceSegment(ProjectionSourceSegment):
    """Task 4 graph input carrying exact source-neutral KC evidence.

    The inherited repository fields remain compatibility projection only and are
    null for non-Git sources. These generic fields are the authoritative
    correlation from a trusted graph hit back to the governed KC source evidence.
    """

    source_repository_key: str | None
    source_document_key: str | None
    source_path: str | None
    source_version: str | None

    governed_source_observation_id: UUID
    governed_observation_digest: str
    governed_decision_id: UUID
    governed_decision_digest: str
    governing_snapshot_digest: str
    governed_projection_digest: str
    source_identity_digest: str
    source_kind: str
    origin_scope: str
    collection_key: str
    item_key: str
    project_keys: tuple[str, ...]
    producer_id: str
    producer_version: str
    source_observed_at: datetime
    source_event_time: datetime | None
    source_revision_time: datetime | None
    governance_policy_id: str
    governance_rationale: str
    governance_decided_at: datetime
    reference_time_policy: str = SOURCE_NEUTRAL_GRAPH_REFERENCE_TIME_POLICY
