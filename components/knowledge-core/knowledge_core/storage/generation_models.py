from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.models import Base, KC_DERIVED_SCHEMA, KC_SCHEMA, REVISION_ID_TYPE


class DerivedGeneration(Base):
    __tablename__ = "generation"
    __table_args__ = (
        CheckConstraint(
            "derived_kind IN ('current_state','identity','classification','text',"
            "'chunks','embeddings','relation_closure','other')",
            name="ck_generation_derived_kind",
        ),
        CheckConstraint(
            "status IN ('building','current','stale','failed','superseded',"
            "'restricted','deletion_pending')",
            name="ck_generation_status",
        ),
        Index(
            "uq_generation_current_derived_kind",
            "derived_kind",
            unique=True,
            postgresql_where=text("status = 'current'"),
            sqlite_where=text("status = 'current'"),
        ),
        Index(
            "ix_generation_kind_sequence",
            "derived_kind",
            "generation_sequence",
            unique=True,
        ),
        {"schema": KC_DERIVED_SCHEMA},
    )

    generation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    generation_sequence: Mapped[int] = mapped_column(REVISION_ID_TYPE, nullable=False, unique=True)
    derived_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_revision_highwater: Mapped[int] = mapped_column(
        REVISION_ID_TYPE,
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"),
        nullable=False,
    )
    profile_revision_ref: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_profile_revision.ref_id"),
        nullable=True,
    )
    model_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_generation: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{KC_DERIVED_SCHEMA}.generation.generation_id"), nullable=True
    )


class GenerationSource(Base):
    __tablename__ = "generation_source"
    __table_args__ = (
        Index("ix_generation_source_source_ref", "source_ref_id"),
        {"schema": KC_DERIVED_SCHEMA},
    )

    generation_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_DERIVED_SCHEMA}.generation.generation_id"), primary_key=True
    )
    source_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    source_revision_id: Mapped[int | None] = mapped_column(
        REVISION_ID_TYPE,
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"),
        nullable=True,
    )
