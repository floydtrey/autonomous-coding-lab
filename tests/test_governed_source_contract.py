from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from knowledge_core.domain.governed_sources import (
    GOVERNED_SNAPSHOT_CONTRACT_VERSION,
    GovernedRetrievalSnapshot,
    GovernedSnapshotExclusion,
    GovernedSnapshotMember,
    GovernedSourceBinding,
    GovernedSourceDecision,
    GovernedSourceIdentity,
    GovernedSourceObservation,
    SourceEvidenceRef,
)
from knowledge_core.domain.retrieval import RetrievalLifecycleState


RESOURCE_A = UUID("11111111-1111-1111-1111-111111111111")
RESOURCE_B = UUID("22222222-2222-2222-2222-222222222222")
VERSION_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
VERSION_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
OBSERVATION_A = UUID("aaaaaaaa-1111-1111-1111-111111111111")
OBSERVATION_B = UUID("bbbbbbbb-2222-2222-2222-222222222222")
DECISION_A = UUID("aaaaaaaa-3333-3333-3333-333333333333")
DECISION_B = UUID("bbbbbbbb-4444-4444-4444-444444444444")
T0 = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)


def _sha(ch: str) -> str:
    return "sha256:" + ch * 64


def _repository_identity() -> GovernedSourceIdentity:
    return GovernedSourceIdentity(
        source_kind="git.repository-document",
        origin_scope="github:floydtrey/autonomous-coding-lab",
        collection_key="architecture/knowledge-core",
        item_key="docs/architecture/knowledge-core/CURRENT_STATE.md",
    )


def _note_identity(item: str = "note-001") -> GovernedSourceIdentity:
    return GovernedSourceIdentity(
        source_kind="local.user-note",
        origin_scope="local_owner",
        collection_key="personal-notes",
        item_key=item,
    )


def _observation(
    *,
    observation_id: UUID = OBSERVATION_A,
    identity: GovernedSourceIdentity | None = None,
    resource_ref: UUID = RESOURCE_A,
    resource_version_ref: UUID = VERSION_A,
    observed_at: datetime = T0,
    source_event_time: datetime | None = None,
    evidence_kind: str = "local.submission",
) -> GovernedSourceObservation:
    chosen = identity or _note_identity()
    return GovernedSourceObservation(
        observation_id=observation_id,
        binding=GovernedSourceBinding(
            source_identity=chosen,
            resource_ref=resource_ref,
        ),
        resource_version_ref=resource_version_ref,
        producer_id="kc.local-note-producer",
        producer_version="1",
        evidence=(
            SourceEvidenceRef(
                evidence_kind=evidence_kind,
                evidence_ref=f"evidence:{observation_id}",
                evidence_digest=_sha("a" if observation_id == OBSERVATION_A else "b"),
            ),
        ),
        observed_at=observed_at,
        source_event_time=source_event_time,
    )


def _decision(
    *,
    decision_id: UUID = DECISION_A,
    observation_id: UUID = OBSERVATION_A,
    lifecycle: RetrievalLifecycleState = RetrievalLifecycleState.CURRENT,
    classification: str = "approved",
    decided_at: datetime = T0,
) -> GovernedSourceDecision:
    return GovernedSourceDecision(
        decision_id=decision_id,
        observation_id=observation_id,
        policy_id="kc-governance-v1",
        classification=classification,
        retrieval_lifecycle=lifecycle,
        authority_rank=5,
        rationale="explicit governed fixture",
        decided_at=decided_at,
    )


def _member(
    observation: GovernedSourceObservation,
    decision: GovernedSourceDecision,
    *,
    project_keys: tuple[str, ...] = (),
) -> GovernedSnapshotMember:
    return GovernedSnapshotMember(
        source_identity_digest=observation.binding.source_identity.digest,
        resource_ref=observation.binding.resource_ref,
        resource_version_ref=observation.resource_version_ref,
        observation_id=observation.observation_id,
        observation_digest=observation.digest,
        decision_id=decision.decision_id,
        decision_digest=decision.digest,
        project_keys=project_keys,
    )


def test_source_identity_is_origin_identity_not_project_or_content_identity():
    note = _note_identity()
    assert note.digest == _note_identity().digest

    # Project membership is deliberately absent from source identity.
    obs = _observation(identity=note)
    decision = _decision()
    member_a = _member(obs, decision, project_keys=("knowledge-core",))
    member_b = _member(obs, decision, project_keys=("knowledge-core", "local-ai"))

    assert member_a.source_identity_digest == member_b.source_identity_digest
    assert member_a.canonical_payload != member_b.canonical_payload


def test_same_bytes_can_belong_to_two_distinct_logical_sources():
    first = _observation(
        identity=_note_identity("intentional-note-a"),
        resource_ref=RESOURCE_A,
        resource_version_ref=VERSION_A,
    )
    second = _observation(
        observation_id=OBSERVATION_B,
        identity=_note_identity("intentional-note-b"),
        resource_ref=RESOURCE_B,
        # Fixture intentionally represents identical bytes under another logical Resource.
        resource_version_ref=VERSION_B,
    )

    assert first.binding.source_identity.digest != second.binding.source_identity.digest
    assert first.binding.resource_ref != second.binding.resource_ref
    assert first.digest != second.digest


def test_reobservation_of_same_source_and_same_version_remains_distinct_evidence():
    first = _observation()
    second = _observation(
        observation_id=OBSERVATION_B,
        observed_at=T0 + timedelta(hours=1),
    )

    assert first.binding == second.binding
    assert first.resource_version_ref == second.resource_version_ref
    assert first.observation_id != second.observation_id
    assert first.digest != second.digest


def test_governance_change_does_not_rewrite_capture_observation():
    observation = _observation()
    current = _decision()
    superseded = _decision(
        decision_id=DECISION_B,
        lifecycle=RetrievalLifecycleState.SUPERSEDED,
        classification="historical",
        decided_at=T0 + timedelta(days=1),
    )

    assert current.observation_id == superseded.observation_id == observation.observation_id
    assert current.digest != superseded.digest
    assert observation.digest == _observation().digest


def test_source_event_time_is_not_kc_observation_time():
    event_time = T0 - timedelta(days=30)
    observation = _observation(
        observed_at=T0,
        source_event_time=event_time,
    )

    payload = observation.canonical_payload
    assert payload["source_event_time"] != payload["observed_at"]
    assert payload["source_event_time"] == "2026-08-15T12:00:00.000000Z"
    assert payload["observed_at"] == "2026-09-14T12:00:00.000000Z"


def test_repository_and_future_source_shapes_share_contract_without_fake_git_fields():
    fixtures = [
        (
            _repository_identity(),
            "git.repository-observation",
        ),
        (_note_identity(), "local.submission"),
        (
            GovernedSourceIdentity(
                source_kind="chat.message",
                origin_scope="chatgpt:user-account",
                collection_key="conversation-123",
                item_key="message-456",
            ),
            "chat.export-record",
        ),
        (
            GovernedSourceIdentity(
                source_kind="email.message",
                origin_scope="mailbox:local_owner",
                collection_key="thread-123",
                item_key="provider-message-456",
            ),
            "email.capture-record",
        ),
        (
            GovernedSourceIdentity(
                source_kind="benchmark.run",
                origin_scope="local-model-bench",
                collection_key="candidate-qualification",
                item_key="run-789",
            ),
            "benchmark.run-record",
        ),
    ]

    for index, (identity, evidence_kind) in enumerate(fixtures):
        observation = _observation(
            observation_id=UUID(int=index + 1),
            identity=identity,
            evidence_kind=evidence_kind,
        )
        payload = observation.canonical_payload
        assert payload["binding"]["source_identity_digest"] == identity.digest
        serialized = str(payload)
        assert "source_commit" not in serialized
        assert "git_blob_sha" not in serialized
        assert "manifest_digest" not in serialized


def test_snapshot_digest_is_order_independent_but_binds_complete_membership():
    obs_a = _observation()
    decision_a = _decision()
    obs_b = _observation(
        observation_id=OBSERVATION_B,
        identity=_repository_identity(),
        resource_ref=RESOURCE_B,
        resource_version_ref=VERSION_B,
        evidence_kind="git.repository-observation",
    )
    decision_b = _decision(
        decision_id=DECISION_B,
        observation_id=OBSERVATION_B,
    )
    member_a = _member(obs_a, decision_a, project_keys=("local-ai",))
    member_b = _member(obs_b, decision_b, project_keys=("knowledge-core",))

    first = GovernedRetrievalSnapshot(
        selection_policy_id="kc-complete-corpus-selection-v1",
        created_at=T0,
        members=(member_a, member_b),
    )
    reordered = GovernedRetrievalSnapshot(
        selection_policy_id="kc-complete-corpus-selection-v1",
        created_at=T0,
        members=(member_b, member_a),
    )
    note_only = GovernedRetrievalSnapshot(
        selection_policy_id="kc-complete-corpus-selection-v1",
        created_at=T0,
        members=(member_a,),
    )

    assert first.digest == reordered.digest
    assert first.digest != note_only.digest


def test_snapshot_digest_binds_predecessor_policy_exclusions_and_governance():
    observation = _observation()
    decision = _decision()
    member = _member(observation, decision)
    baseline = GovernedRetrievalSnapshot(
        selection_policy_id="kc-complete-corpus-selection-v1",
        created_at=T0,
        members=(member,),
    )

    with_predecessor = replace(
        baseline,
        predecessor_snapshot_digest=_sha("f"),
    )
    with_exclusion = replace(
        baseline,
        exclusions=(
            GovernedSnapshotExclusion(
                source_identity_digest=_repository_identity().digest,
                observation_id=OBSERVATION_B,
                reason_code="not-selected-by-policy",
            ),
        ),
    )
    changed_policy = replace(
        baseline,
        selection_policy_id="kc-complete-corpus-selection-v2",
    )
    changed_governance = replace(
        baseline,
        members=(
            _member(
                observation,
                _decision(
                    decision_id=DECISION_B,
                    lifecycle=RetrievalLifecycleState.SUPERSEDED,
                    decided_at=T0 + timedelta(minutes=1),
                ),
            ),
        ),
    )

    assert len({
        baseline.digest,
        with_predecessor.digest,
        with_exclusion.digest,
        changed_policy.digest,
        changed_governance.digest,
    }) == 5


def test_snapshot_contract_rejects_duplicate_selection_and_bad_digest_inputs():
    observation = _observation()
    decision = _decision()
    member = _member(observation, decision)

    with pytest.raises(ValueError, match="duplicate selected source observations"):
        GovernedRetrievalSnapshot(
            selection_policy_id="kc-complete-corpus-selection-v1",
            created_at=T0,
            members=(member, member),
        )

    with pytest.raises(ValueError, match="canonical sha256"):
        replace(member, source_identity_digest="not-a-digest")

    with pytest.raises(ValueError, match="timezone-aware"):
        replace(observation, observed_at=datetime(2026, 9, 14, 12, 0))


def test_snapshot_contract_version_is_explicit_and_frozen():
    snapshot = GovernedRetrievalSnapshot(
        selection_policy_id="kc-complete-corpus-selection-v1",
        created_at=T0,
        members=(),
    )
    assert snapshot.contract_version == GOVERNED_SNAPSHOT_CONTRACT_VERSION

    with pytest.raises(ValueError, match="unsupported governed retrieval snapshot"):
        replace(snapshot, contract_version="kc-governed-retrieval-snapshot-v2")
