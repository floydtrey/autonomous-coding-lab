from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID

from knowledge_core.domain.retrieval import RetrievalLifecycleState


GOVERNED_SOURCE_CONTRACT_VERSION = "kc-governed-source-v1"
GOVERNED_SNAPSHOT_CONTRACT_VERSION = "kc-governed-retrieval-snapshot-v1"


def _require_nonblank(value: str, field: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field} must be non-blank")
    return value


def _canonical_sha256(value: str, field: str) -> str:
    prefix = "sha256:"
    if not value.startswith(prefix):
        raise ValueError(f"{field} must be a canonical sha256 digest")
    digest = value[len(prefix) :]
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError(f"{field} must be a canonical sha256 digest")
    return value


def _canonical_time(value: datetime, field: str) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


@dataclass(frozen=True)
class GovernedSourceIdentity:
    """Stable external/origin identity; never content identity or project identity."""

    source_kind: str
    origin_scope: str
    collection_key: str
    item_key: str

    def __post_init__(self) -> None:
        _require_nonblank(self.source_kind, "source_kind")
        _require_nonblank(self.origin_scope, "origin_scope")
        _require_nonblank(self.collection_key, "collection_key")
        _require_nonblank(self.item_key, "item_key")

    @property
    def canonical_payload(self) -> dict[str, object]:
        return {
            "contract_version": GOVERNED_SOURCE_CONTRACT_VERSION,
            "collection_key": self.collection_key,
            "item_key": self.item_key,
            "origin_scope": self.origin_scope,
            "source_kind": self.source_kind,
        }

    @property
    def digest(self) -> str:
        return _digest(self.canonical_payload)


@dataclass(frozen=True)
class GovernedSourceBinding:
    """Maps one stable source identity to one KC logical Resource."""

    source_identity: GovernedSourceIdentity
    resource_ref: UUID

    @property
    def canonical_payload(self) -> dict[str, object]:
        return {
            "resource_ref": str(self.resource_ref),
            "source_identity_digest": self.source_identity.digest,
        }


@dataclass(frozen=True)
class SourceEvidenceRef:
    """Typed reference to immutable producer-specific capture/proof evidence."""

    evidence_kind: str
    evidence_ref: str
    evidence_digest: str

    def __post_init__(self) -> None:
        _require_nonblank(self.evidence_kind, "evidence_kind")
        _require_nonblank(self.evidence_ref, "evidence_ref")
        _canonical_sha256(self.evidence_digest, "evidence_digest")

    @property
    def canonical_payload(self) -> dict[str, object]:
        return {
            "evidence_digest": self.evidence_digest,
            "evidence_kind": self.evidence_kind,
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True)
class GovernedSourceObservation:
    """Immutable capture/admission evidence for one exact ResourceVersion."""

    observation_id: UUID
    binding: GovernedSourceBinding
    resource_version_ref: UUID
    producer_id: str
    producer_version: str
    evidence: tuple[SourceEvidenceRef, ...]
    observed_at: datetime
    source_event_time: datetime | None = None
    source_revision_time: datetime | None = None

    def __post_init__(self) -> None:
        _require_nonblank(self.producer_id, "producer_id")
        _require_nonblank(self.producer_version, "producer_version")
        if not self.evidence:
            raise ValueError("governed source observation requires producer evidence")
        _canonical_time(self.observed_at, "observed_at")
        if self.source_event_time is not None:
            _canonical_time(self.source_event_time, "source_event_time")
        if self.source_revision_time is not None:
            _canonical_time(self.source_revision_time, "source_revision_time")

    @property
    def canonical_payload(self) -> dict[str, object]:
        evidence = sorted(
            (item.canonical_payload for item in self.evidence),
            key=lambda item: (
                str(item["evidence_kind"]),
                str(item["evidence_ref"]),
                str(item["evidence_digest"]),
            ),
        )
        return {
            "binding": self.binding.canonical_payload,
            "contract_version": GOVERNED_SOURCE_CONTRACT_VERSION,
            "evidence": evidence,
            "observation_id": str(self.observation_id),
            "observed_at": _canonical_time(self.observed_at, "observed_at"),
            "producer_id": self.producer_id,
            "producer_version": self.producer_version,
            "resource_version_ref": str(self.resource_version_ref),
            "source_event_time": (
                _canonical_time(self.source_event_time, "source_event_time")
                if self.source_event_time is not None
                else None
            ),
            "source_revision_time": (
                _canonical_time(self.source_revision_time, "source_revision_time")
                if self.source_revision_time is not None
                else None
            ),
        }

    @property
    def digest(self) -> str:
        return _digest(self.canonical_payload)


@dataclass(frozen=True)
class GovernedSourceDecision:
    """Immutable KC governance decision over an observation, separate from capture."""

    decision_id: UUID
    observation_id: UUID
    policy_id: str
    classification: str
    retrieval_lifecycle: RetrievalLifecycleState
    authority_rank: int | None
    rationale: str
    decided_at: datetime

    def __post_init__(self) -> None:
        _require_nonblank(self.policy_id, "policy_id")
        _require_nonblank(self.classification, "classification")
        _require_nonblank(self.rationale, "rationale")
        if self.authority_rank is not None and self.authority_rank < 0:
            raise ValueError("authority_rank must be non-negative when supplied")
        _canonical_time(self.decided_at, "decided_at")

    @property
    def canonical_payload(self) -> dict[str, object]:
        return {
            "authority_rank": self.authority_rank,
            "classification": self.classification,
            "contract_version": GOVERNED_SOURCE_CONTRACT_VERSION,
            "decided_at": _canonical_time(self.decided_at, "decided_at"),
            "decision_id": str(self.decision_id),
            "observation_id": str(self.observation_id),
            "policy_id": self.policy_id,
            "rationale": self.rationale,
            "retrieval_lifecycle": self.retrieval_lifecycle.value,
        }

    @property
    def digest(self) -> str:
        return _digest(self.canonical_payload)


@dataclass(frozen=True)
class GovernedSnapshotMember:
    """Exact source/observation/governance selection included in one serving corpus."""

    source_identity_digest: str
    resource_ref: UUID
    resource_version_ref: UUID
    observation_id: UUID
    observation_digest: str
    decision_id: UUID
    decision_digest: str
    project_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _canonical_sha256(self.source_identity_digest, "source_identity_digest")
        _canonical_sha256(self.observation_digest, "observation_digest")
        _canonical_sha256(self.decision_digest, "decision_digest")
        if any(not key or not key.strip() for key in self.project_keys):
            raise ValueError("project_keys must contain only non-blank values")
        if len(set(self.project_keys)) != len(self.project_keys):
            raise ValueError("project_keys must not contain duplicates")

    @classmethod
    def from_selection(
        cls,
        *,
        observation: GovernedSourceObservation,
        decision: GovernedSourceDecision,
        project_keys: tuple[str, ...] = (),
    ) -> GovernedSnapshotMember:
        if decision.observation_id != observation.observation_id:
            raise ValueError("governance decision does not belong to selected observation")
        return cls(
            source_identity_digest=observation.binding.source_identity.digest,
            resource_ref=observation.binding.resource_ref,
            resource_version_ref=observation.resource_version_ref,
            observation_id=observation.observation_id,
            observation_digest=observation.digest,
            decision_id=decision.decision_id,
            decision_digest=decision.digest,
            project_keys=project_keys,
        )

    @property
    def canonical_payload(self) -> dict[str, object]:
        return {
            "decision_digest": self.decision_digest,
            "decision_id": str(self.decision_id),
            "observation_digest": self.observation_digest,
            "observation_id": str(self.observation_id),
            "project_keys": sorted(self.project_keys),
            "resource_ref": str(self.resource_ref),
            "resource_version_ref": str(self.resource_version_ref),
            "source_identity_digest": self.source_identity_digest,
        }


@dataclass(frozen=True)
class GovernedSnapshotExclusion:
    """Explicit non-membership evidence retained for deterministic snapshot selection."""

    source_identity_digest: str
    reason_code: str
    observation_id: UUID | None = None

    def __post_init__(self) -> None:
        _canonical_sha256(self.source_identity_digest, "source_identity_digest")
        _require_nonblank(self.reason_code, "reason_code")

    @property
    def canonical_payload(self) -> dict[str, object]:
        return {
            "observation_id": (
                str(self.observation_id) if self.observation_id is not None else None
            ),
            "reason_code": self.reason_code,
            "source_identity_digest": self.source_identity_digest,
        }


@dataclass(frozen=True)
class GovernedRetrievalSnapshot:
    """Complete immutable source selection used to build one retrieval corpus."""

    selection_policy_id: str
    created_at: datetime
    members: tuple[GovernedSnapshotMember, ...]
    exclusions: tuple[GovernedSnapshotExclusion, ...] = ()
    predecessor_snapshot_digest: str | None = None
    contract_version: str = GOVERNED_SNAPSHOT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_nonblank(self.selection_policy_id, "selection_policy_id")
        _canonical_time(self.created_at, "created_at")
        if self.contract_version != GOVERNED_SNAPSHOT_CONTRACT_VERSION:
            raise ValueError("unsupported governed retrieval snapshot contract version")
        if self.predecessor_snapshot_digest is not None:
            _canonical_sha256(
                self.predecessor_snapshot_digest,
                "predecessor_snapshot_digest",
            )
        member_keys = [
            (item.source_identity_digest, item.observation_id) for item in self.members
        ]
        if len(set(member_keys)) != len(member_keys):
            raise ValueError("snapshot contains duplicate selected source observations")

    @property
    def canonical_payload(self) -> dict[str, object]:
        members = sorted(
            (item.canonical_payload for item in self.members),
            key=lambda item: (
                str(item["source_identity_digest"]),
                str(item["observation_id"]),
                str(item["decision_id"]),
            ),
        )
        exclusions = sorted(
            (item.canonical_payload for item in self.exclusions),
            key=lambda item: (
                str(item["source_identity_digest"]),
                str(item["observation_id"]),
                str(item["reason_code"]),
            ),
        )
        return {
            "contract_version": self.contract_version,
            "created_at": _canonical_time(self.created_at, "created_at"),
            "exclusions": exclusions,
            "members": members,
            "predecessor_snapshot_digest": self.predecessor_snapshot_digest,
            "selection_policy_id": self.selection_policy_id,
        }

    @property
    def digest(self) -> str:
        return _digest(self.canonical_payload)
