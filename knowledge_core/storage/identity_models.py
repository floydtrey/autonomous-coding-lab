from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.models import (
    Base,
    KC_DERIVED_SCHEMA,
    KC_SCHEMA,
    REVISION_ID_TYPE,
)


class IdentityTransition(Base):
    __tablename__ = "identity_transition"
    __table_args__ = (
        CheckConstraint(
            "transition_type IN ('resolve_same','resolve_different','merge','split',"
            "'replace','reassign_identifier')",
            name="ck_identity_transition_type",
        ),
        {"schema": KC_SCHEMA},
    )

    occurrence_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.occurrence.ref_id"), primary_key=True
    )
    transition_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reverses_transition_ref: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.identity_transition.occurrence_ref_id"),
        nullable=True,
        unique=True,
    )
    created_revision_id: Mapped[int] = mapped_column(
        REVISION_ID_TYPE,
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"),
        nullable=False,
    )


class IdentityTransitionMember(Base):
    __tablename__ = "identity_transition_member"
    __table_args__ = (
        CheckConstraint(
            "member_role IN ('source','member','representative','old','new',"
            "'split_member','governed-other')",
            name="ck_identity_transition_member_role",
        ),
        {"schema": KC_SCHEMA},
    )

    transition_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.identity_transition.occurrence_ref_id"),
        primary_key=True,
    )
    entity_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.entity.ref_id"), primary_key=True, index=True
    )
    member_role: Mapped[str] = mapped_column(String(32), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)


class CurrentIdentityMember(Base):
    __tablename__ = "current_identity_member"
    __table_args__ = (
        UniqueConstraint(
            "entity_ref_id",
            name="uq_current_identity_member_entity_ref",
        ),
        {"schema": KC_DERIVED_SCHEMA},
    )

    entity_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.entity.ref_id"), primary_key=True
    )
    resolution_group_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, index=True)
    representative_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.entity.ref_id"), nullable=False, index=True
    )
    source_transition_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.identity_transition.occurrence_ref_id"),
        nullable=False,
    )
    source_revision_id: Mapped[int] = mapped_column(
        REVISION_ID_TYPE,
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"),
        nullable=False,
    )
