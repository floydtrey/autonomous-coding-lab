from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.control_models import KC_CONTROL_SCHEMA
from knowledge_core.storage.models import Base, KC_SCHEMA


class DeletionCase(Base):
    __tablename__ = "deletion_case"
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('restrict','erase','retention_exception')",
            name="ck_deletion_case_action_type",
        ),
        CheckConstraint(
            "status IN ('requested','fenced','canonical_pending','derivatives_pending',"
            "'backup_fenced','settled','blocked','failed')",
            name="ck_deletion_case_status",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    case_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    operation_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_CONTROL_SCHEMA}.operation.operation_id"),
        nullable=False,
        unique=True,
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_scope_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    minimal_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeletionTarget(Base):
    __tablename__ = "deletion_target"
    __table_args__ = (
        CheckConstraint(
            "reconciliation_state IN ('fenced','restricted_settled',"
            "'erased_tombstone','blocked')",
            name="ck_deletion_target_state",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_CONTROL_SCHEMA}.deletion_case.case_id"),
        primary_key=True,
    )
    target_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"),
        primary_key=True,
        index=True,
    )
    reconciliation_state: Mapped[str] = mapped_column(String(32), nullable=False)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
