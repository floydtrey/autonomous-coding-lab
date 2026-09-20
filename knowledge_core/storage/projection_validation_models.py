from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.control_models import KC_CONTROL_SCHEMA
from knowledge_core.storage.models import Base


class ProjectionValidationRecord(Base):
    __tablename__ = "projection_validation"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('pending','validated','incomplete','rejected','quarantined')",
            name="ck_projection_validation_outcome",
        ),
        Index("ix_projection_validation_attempt", "attempt_id"),
        {"schema": KC_CONTROL_SCHEMA},
    )

    validation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_CONTROL_SCHEMA}.projection_attempt.attempt_id"),
        nullable=False,
    )
    attempt_request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    validator_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    validator_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ruleset_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ruleset_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProjectionValidationCheckRecord(Base):
    __tablename__ = "projection_validation_check"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('passed','failed','indeterminate')",
            name="ck_projection_validation_check_outcome",
        ),
        UniqueConstraint(
            "validation_id",
            "check_code",
            name="uq_projection_validation_check_code",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    validation_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_CONTROL_SCHEMA}.projection_validation.validation_id"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    check_code: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
