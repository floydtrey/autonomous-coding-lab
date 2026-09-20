from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.control_models import KC_CONTROL_SCHEMA
from knowledge_core.storage.models import Base, KC_SCHEMA, REVISION_ID_TYPE


class ProjectionAttempt(Base):
    __tablename__ = "projection_attempt"
    __table_args__ = (
        CheckConstraint(
            "disposition IN ('pending','succeeded','incomplete','failed','quarantined')",
            name="ck_projection_attempt_disposition",
        ),
        CheckConstraint(
            "validation_state IN ('unvalidated','validated','incomplete','rejected','quarantined')",
            name="ck_projection_attempt_validation_state",
        ),
        Index(
            "ix_projection_attempt_target_scope",
            "target_kind",
            "namespace_key",
            "scope_key",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    attempt_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    projection_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    namespace_key: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(255), nullable=False)
    backend_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    backend_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    profile_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    profile_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_state: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warnings_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    errors_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)


class ProjectionAttemptSource(Base):
    __tablename__ = "projection_attempt_source"
    __table_args__ = (
        Index("ix_projection_attempt_source_ref", "source_ref_id"),
        {"schema": KC_CONTROL_SCHEMA},
    )

    attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_CONTROL_SCHEMA}.projection_attempt.attempt_id"),
        primary_key=True,
    )
    source_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"),
        primary_key=True,
    )
    source_revision_id: Mapped[int | None] = mapped_column(
        REVISION_ID_TYPE,
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"),
        nullable=True,
    )
