from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID

import pytest

from knowledge_core.domain.governed_sources import (
    GovernedRetrievalSnapshot,
    GovernedSnapshotMember,
    GovernedSourceBinding,
    GovernedSourceDecision,
    GovernedSourceIdentity,
    GovernedSourceObservation,
    SourceEvidenceRef,
)
from knowledge_core.domain.retrieval import RetrievalLifecycleState


T0 = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
OBSERVATION = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OTHER_OBSERVATION = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DECISION = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
OTHER_DECISION = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
RESOURCE = UUID("11111111-1111-1111-1111-111111111111")
VERSION = UUID("22222222-2222-2222-2222-222222222222")


def _observation() -> GovernedSourceObservation:
    return GovernedSourceObservation(
        observation_id=OBSERVATION,
        binding=GovernedSourceBinding(
            source_identity=GovernedSourceIdentity(
                source_kind="local.user-note",
                origin_scope="local_owner",
                collection_key="personal-notes",
                item_key="note-001",
            ),
            resource_ref=RESOURCE,
        ),
        resource_version_ref=VERSION,
        producer_id="kc.local-note-producer",
        producer_version="1",
        evidence=(
            SourceEvidenceRef(
                evidence_kind="local.submission",
                evidence_ref="request:001",
                evidence_digest="sha256:" + "a" * 64,
            ),
        ),
        observed_at=T0,
    )


def _decision(*, decision_id: UUID = DECISION) -> GovernedSourceDecision:
    return GovernedSourceDecision(
        decision_id=decision_id,
        observation_id=OBSERVATION,
        policy_id="kc-governance-v1",
        classification="approved",
        retrieval_lifecycle=RetrievalLifecycleState.CURRENT,
        authority_rank=5,
        rationale="accepted fixture",
        decided_at=T0,
    )


def test_snapshot_member_factory_rejects_decision_for_another_observation():
    observation = _observation()
    mismatched = replace(_decision(), observation_id=OTHER_OBSERVATION)

    with pytest.raises(ValueError, match="does not belong to selected observation"):
        GovernedSnapshotMember.from_selection(
            observation=observation,
            decision=mismatched,
        )


def test_snapshot_rejects_same_observation_selected_under_two_decisions():
    observation = _observation()
    first = GovernedSnapshotMember.from_selection(
        observation=observation,
        decision=_decision(),
    )
    second = GovernedSnapshotMember.from_selection(
        observation=observation,
        decision=_decision(decision_id=OTHER_DECISION),
    )

    with pytest.raises(ValueError, match="duplicate selected source observations"):
        GovernedRetrievalSnapshot(
            selection_policy_id="kc-complete-corpus-selection-v1",
            created_at=T0,
            members=(first, second),
        )
