from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.control_models import KC_CONTROL_SCHEMA
from knowledge_core.storage.models import Base, KC_SCHEMA


class GovernedSourceBindingRecord(Base):
    """Stable source/origin identity mapped to one canonical KC Resource."""

    __tablename__ = "governed_source_binding"
    __table_args__ = (
        UniqueConstraint(
            "source_kind",
            "origin_scope",
            "collection_key",
            "item_key",
            name="uq_governed_source_binding_identity",
        ),
        UniqueConstraint(
            "source_identity_digest",
            "resource_ref",
            name="uq_governed_source_binding_digest_resource",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    source_identity_digest: Mapped[str] = mapped_column(String(71), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    origin_scope: Mapped[str] = mapped_column(Text, nullable=False)
    collection_key: Mapped[str] = mapped_column(Text, nullable=False)
    item_key: Mapped[str] = mapped_column(Text, nullable=False)
    resource_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.resource.ref_id"), nullable=False, index=True
    )


class GovernedSourceObservationRecord(Base):
    """Immutable producer capture/admission of one exact ResourceVersion."""

    __tablename__ = "governed_source_observation"
    __table_args__ = (
        UniqueConstraint(
            "observation_id",
            "source_identity_digest",
            "resource_version_ref",
            "observation_digest",
            name="uq_governed_source_observation_exact",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    observation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_identity_digest: Mapped[str] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.governed_source_binding.source_identity_digest"
        ),
        nullable=False,
        index=True,
    )
    resource_version_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.resource_version.ref_id"), nullable=False, index=True
    )
    producer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    producer_version: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_event_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_revision_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observation_digest: Mapped[str] = mapped_column(
        String(71), nullable=False, unique=True
    )


class GovernedSourceEvidenceRecord(Base):
    """Typed producer-specific proof references for one generic observation."""

    __tablename__ = "governed_source_evidence"
    __table_args__ = (
        UniqueConstraint(
            "observation_id",
            "evidence_kind",
            "evidence_ref",
            "evidence_digest",
            name="uq_governed_source_evidence_exact",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.governed_source_observation.observation_id"
        ),
        primary_key=True,
    )
    evidence_ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_ref: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_digest: Mapped[str] = mapped_column(String(71), nullable=False)


class GovernedSourceDecisionRecord(Base):
    """Immutable KC governance decision over one generic observation."""

    __tablename__ = "governed_source_decision"
    __table_args__ = (
        CheckConstraint(
            "retrieval_lifecycle IN ('current','unknown','superseded')",
            name="ck_governed_source_decision_lifecycle",
        ),
        CheckConstraint(
            "authority_rank IS NULL OR authority_rank >= 0",
            name="ck_governed_source_decision_authority_rank",
        ),
        UniqueConstraint(
            "decision_id",
            "observation_id",
            "decision_digest",
            name="uq_governed_source_decision_exact",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    decision_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.governed_source_observation.observation_id"
        ),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    classification: Mapped[str] = mapped_column(String(128), nullable=False)
    retrieval_lifecycle: Mapped[str] = mapped_column(String(32), nullable=False)
    authority_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision_digest: Mapped[str] = mapped_column(String(71), nullable=False, unique=True)


class GovernedRetrievalSnapshotRecord(Base):
    """Immutable complete governed source selection for one retrieval corpus."""

    __tablename__ = "governed_retrieval_snapshot"
    __table_args__ = ({"schema": KC_CONTROL_SCHEMA},)

    snapshot_digest: Mapped[str] = mapped_column(String(71), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    selection_policy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    predecessor_snapshot_digest: Mapped[str | None] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.governed_retrieval_snapshot.snapshot_digest"
        ),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GovernedSnapshotMemberRecord(Base):
    """Exact selected observation/governance evidence for one snapshot."""

    __tablename__ = "governed_snapshot_member"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_identity_digest", "resource_ref"],
            [
                f"{KC_CONTROL_SCHEMA}.governed_source_binding.source_identity_digest",
                f"{KC_CONTROL_SCHEMA}.governed_source_binding.resource_ref",
            ],
            name="fk_governed_snapshot_member_binding",
        ),
        ForeignKeyConstraint(
            [
                "observation_id",
                "source_identity_digest",
                "resource_version_ref",
                "observation_digest",
            ],
            [
                f"{KC_CONTROL_SCHEMA}.governed_source_observation.observation_id",
                f"{KC_CONTROL_SCHEMA}.governed_source_observation.source_identity_digest",
                f"{KC_CONTROL_SCHEMA}.governed_source_observation.resource_version_ref",
                f"{KC_CONTROL_SCHEMA}.governed_source_observation.observation_digest",
            ],
            name="fk_governed_snapshot_member_observation",
        ),
        ForeignKeyConstraint(
            ["decision_id", "observation_id", "decision_digest"],
            [
                f"{KC_CONTROL_SCHEMA}.governed_source_decision.decision_id",
                f"{KC_CONTROL_SCHEMA}.governed_source_decision.observation_id",
                f"{KC_CONTROL_SCHEMA}.governed_source_decision.decision_digest",
            ],
            name="fk_governed_snapshot_member_decision",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    snapshot_digest: Mapped[str] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.governed_retrieval_snapshot.snapshot_digest"
        ),
        primary_key=True,
    )
    source_identity_digest: Mapped[str] = mapped_column(String(71), primary_key=True)
    observation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    resource_ref: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    resource_version_ref: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    observation_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    decision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    decision_digest: Mapped[str] = mapped_column(String(71), nullable=False)


class GovernedSnapshotProjectRecord(Base):
    """Project/context membership is separate from source/origin identity."""

    __tablename__ = "governed_snapshot_project"
    __table_args__ = (
        ForeignKeyConstraint(
            ["snapshot_digest", "source_identity_digest", "observation_id"],
            [
                f"{KC_CONTROL_SCHEMA}.governed_snapshot_member.snapshot_digest",
                f"{KC_CONTROL_SCHEMA}.governed_snapshot_member.source_identity_digest",
                f"{KC_CONTROL_SCHEMA}.governed_snapshot_member.observation_id",
            ],
            name="fk_governed_snapshot_project_member",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    snapshot_digest: Mapped[str] = mapped_column(String(71), primary_key=True)
    source_identity_digest: Mapped[str] = mapped_column(String(71), primary_key=True)
    observation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    project_key: Mapped[str] = mapped_column(String(255), primary_key=True)


class GovernedSnapshotExclusionRecord(Base):
    """Explicit exclusion evidence preventing silent source resurrection."""

    __tablename__ = "governed_snapshot_exclusion"
    __table_args__ = ({"schema": KC_CONTROL_SCHEMA},)

    snapshot_digest: Mapped[str] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.governed_retrieval_snapshot.snapshot_digest"
        ),
        primary_key=True,
    )
    exclusion_ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_identity_digest: Mapped[str] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.governed_source_binding.source_identity_digest"
        ),
        nullable=False,
    )
    observation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.governed_source_observation.observation_id"
        ),
        nullable=True,
    )
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)


class LegacyRepositoryObservationMap(Base):
    """Explicit deterministic bridge from immutable RI evidence to generic capture."""

    __tablename__ = "legacy_repository_observation_map"
    __table_args__ = ({"schema": KC_CONTROL_SCHEMA},)

    legacy_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.repository_source_observation.observation_id"
        ),
        primary_key=True,
    )
    generic_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.governed_source_observation.observation_id"
        ),
        nullable=False,
        unique=True,
    )
    source_identity_digest: Mapped[str] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.governed_source_binding.source_identity_digest"
        ),
        nullable=False,
    )
    capture_evidence_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False)


class LegacyRepositoryDecisionMap(Base):
    """Bridge one governing RI selection to one generic governance decision."""

    __tablename__ = "legacy_repository_decision_map"
    __table_args__ = (
        CheckConstraint(
            "selection_role IN ('current','prior_version','retirement_retain')",
            name="ck_legacy_repository_decision_map_role",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    governing_manifest_digest: Mapped[str] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.repository_import_receipt.manifest_digest"
        ),
        primary_key=True,
    )
    legacy_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.repository_source_observation.observation_id"
        ),
        primary_key=True,
    )
    decision_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_CONTROL_SCHEMA}.governed_source_decision.decision_id"),
        nullable=False,
        unique=True,
    )
    selection_role: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False)


class LegacyRepositorySnapshotMap(Base):
    """Bridge one settled RI receipt to one complete generic retrieval snapshot."""

    __tablename__ = "legacy_repository_snapshot_map"
    __table_args__ = ({"schema": KC_CONTROL_SCHEMA},)

    governing_manifest_digest: Mapped[str] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.repository_import_receipt.manifest_digest"
        ),
        primary_key=True,
    )
    snapshot_digest: Mapped[str] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.governed_retrieval_snapshot.snapshot_digest"
        ),
        nullable=False,
        unique=True,
    )
    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False)
