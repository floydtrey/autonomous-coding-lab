from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.control_models import KC_CONTROL_SCHEMA
from knowledge_core.storage.models import Base


class MemoryCandidateRecord(Base):
    __tablename__ = "memory_candidate"
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending','approved','rejected')",
            name="ck_memory_candidate_state",
        ),
        Index("ix_memory_candidate_state_proposed", "state", "proposed_at"),
        {"schema": KC_CONTROL_SCHEMA},
    )

    candidate_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.operation.operation_id"),
        primary_key=True,
    )
    submitted_by_principal_ref: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    proposer_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    project_key: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_event_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    proposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)

    review_operation_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.operation.operation_id"),
        nullable=True,
        unique=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewer_principal_ref: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    review_decision_ref: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    review_reason_code: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
