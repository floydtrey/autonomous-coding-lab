from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


KC_SCHEMA = "kc"
KC_DERIVED_SCHEMA = "kc_derived"
REVISION_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    pass


class Revision(Base):
    __tablename__ = "revision"
    __table_args__ = {"schema": KC_SCHEMA}

    revision_id: Mapped[int] = mapped_column(
        REVISION_ID_TYPE, primary_key=True, autoincrement=True
    )
    operation_id: Mapped[UUID | None] = mapped_column(Uuid, unique=True, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    schema_revision: Mapped[str] = mapped_column(
        String(64), nullable=False, default="task1"
    )
    authority_decision: Mapped[str | None] = mapped_column(Text, nullable=True)


class KnowledgeRef(Base):
    __tablename__ = "knowledge_ref"
    __table_args__ = {"schema": KC_SCHEMA}

    ref_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    ref_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    payload_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active"
    )


class SemanticProfile(Base):
    __tablename__ = "semantic_profile"
    __table_args__ = {"schema": KC_SCHEMA}

    ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    stable_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class SemanticProfileRevision(Base):
    __tablename__ = "semantic_profile_revision"
    __table_args__ = (
        CheckConstraint("status IN ('active-capable','deprecated','retired-for-new-use')"),
        {"schema": KC_SCHEMA},
    )

    ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    profile_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_profile.ref_id"), nullable=False
    )
    version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active-capable"
    )
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class SemanticKind(Base):
    __tablename__ = "semantic_kind"
    __table_args__ = {"schema": KC_SCHEMA}

    ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    profile_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_profile.ref_id"), nullable=False
    )
    stable_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class SemanticKindRevision(Base):
    __tablename__ = "semantic_kind_revision"
    __table_args__ = {"schema": KC_SCHEMA}

    ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    kind_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_kind.ref_id"), nullable=False
    )
    profile_revision_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_profile_revision.ref_id"), nullable=False
    )
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class SemanticPredicate(Base):
    __tablename__ = "semantic_predicate"
    __table_args__ = (
        UniqueConstraint("profile_ref_id", "stable_name"),
        {"schema": KC_SCHEMA},
    )

    ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    profile_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_profile.ref_id"), nullable=False
    )
    stable_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class SemanticPredicateRevision(Base):
    __tablename__ = "semantic_predicate_revision"
    __table_args__ = (
        CheckConstraint("value_shape IN ('scalar','reference')"),
        {"schema": KC_SCHEMA},
    )

    ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    predicate_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_predicate.ref_id"), nullable=False
    )
    profile_revision_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_profile_revision.ref_id"), nullable=False
    )
    value_shape: Mapped[str] = mapped_column(String(32), nullable=False)
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class Entity(Base):
    __tablename__ = "entity"
    __table_args__ = {"schema": KC_SCHEMA}

    ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    kind_revision_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_kind_revision.ref_id"), nullable=False
    )
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class Occurrence(Base):
    __tablename__ = "occurrence"
    __table_args__ = {"schema": KC_SCHEMA}

    ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    kind_revision_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_kind_revision.ref_id"), nullable=False
    )
    happened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class Assertion(Base):
    __tablename__ = "assertion"
    __table_args__ = (
        CheckConstraint(
            "value_state IN ('present','explicit_negative','known_no_value',"
            "'some_value_unknown','not_established')"
        ),
        CheckConstraint(
            "epistemic_basis IN ('stated','observed','imported','configured',"
            "'inferred','derived','verified','other-governed')"
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from",
            name="ck_assertion_valid_interval",
        ),
        {"schema": KC_SCHEMA},
    )

    ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    subject_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), nullable=False
    )
    predicate_revision_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_predicate_revision.ref_id"), nullable=False
    )
    profile_revision_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_profile_revision.ref_id"), nullable=False
    )
    value_state: Mapped[str] = mapped_column(String(32), nullable=False)
    epistemic_basis: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    world_time_precision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class AssertionValue(Base):
    __tablename__ = "assertion_value"
    __table_args__ = (
        CheckConstraint(
            "("
            "(value_kind='reference' AND reference_value IS NOT NULL AND text_value IS NULL "
            "AND numeric_value IS NULL AND boolean_value IS NULL AND date_value IS NULL "
            "AND timestamp_value IS NULL) OR "
            "(value_kind='text' AND reference_value IS NULL AND text_value IS NOT NULL "
            "AND numeric_value IS NULL AND boolean_value IS NULL AND date_value IS NULL "
            "AND timestamp_value IS NULL) OR "
            "(value_kind='numeric' AND reference_value IS NULL AND text_value IS NULL "
            "AND numeric_value IS NOT NULL AND boolean_value IS NULL AND date_value IS NULL "
            "AND timestamp_value IS NULL) OR "
            "(value_kind='boolean' AND reference_value IS NULL AND text_value IS NULL "
            "AND numeric_value IS NULL AND boolean_value IS NOT NULL AND date_value IS NULL "
            "AND timestamp_value IS NULL) OR "
            "(value_kind='date' AND reference_value IS NULL AND text_value IS NULL "
            "AND numeric_value IS NULL AND boolean_value IS NULL AND date_value IS NOT NULL "
            "AND timestamp_value IS NULL) OR "
            "(value_kind='timestamp' AND reference_value IS NULL AND text_value IS NULL "
            "AND numeric_value IS NULL AND boolean_value IS NULL AND date_value IS NULL "
            "AND timestamp_value IS NOT NULL)"
            ")",
            name="ck_assertion_value_exactly_one_typed_value",
        ),
        {"schema": KC_SCHEMA},
    )

    assertion_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.assertion.ref_id"), primary_key=True
    )
    value_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_value: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), nullable=True
    )
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    boolean_value: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    date_value: Mapped[date | None] = mapped_column(Date, nullable=True)
    timestamp_value: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AssertionTransition(Base):
    __tablename__ = "assertion_transition"
    __table_args__ = (
        CheckConstraint(
            "transition_type IN ('supersedes','corrects','invalidates','restores')"
        ),
        {"schema": KC_SCHEMA},
    )

    occurrence_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.occurrence.ref_id"), primary_key=True
    )
    transition_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_assertion_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.assertion.ref_id"), nullable=False
    )
    replacement_assertion_ref: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.assertion.ref_id"), nullable=True
    )
    reverses_transition_ref: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.assertion_transition.occurrence_ref_id"),
        nullable=True,
        unique=True,
    )
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class CurrentAssertion(Base):
    __tablename__ = "current_assertion"
    __table_args__ = {"schema": KC_DERIVED_SCHEMA}

    assertion_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.assertion.ref_id"), primary_key=True
    )
    subject_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), nullable=False, index=True
    )
    predicate_revision_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_predicate_revision.ref_id"),
        nullable=False,
        index=True,
    )
    conflict_group_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    source_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )
    projection_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )
    selection_reason: Mapped[str] = mapped_column(String(64), nullable=False)
