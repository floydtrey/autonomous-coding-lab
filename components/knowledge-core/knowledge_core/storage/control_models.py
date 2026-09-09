from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.models import Base, KC_SCHEMA, REVISION_ID_TYPE


KC_CONTROL_SCHEMA = "kc_control"


class Operation(Base):
    __tablename__ = "operation"
    __table_args__ = (
        CheckConstraint(
            "status IN ('received','running','committed','failed','conflict')",
            name="ck_operation_status",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    operation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    caller_principal_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    operation_class: Mapped[str] = mapped_column(String(64), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    result_revision_id: Mapped[int | None] = mapped_column(
        REVISION_ID_TYPE,
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"),
        nullable=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
