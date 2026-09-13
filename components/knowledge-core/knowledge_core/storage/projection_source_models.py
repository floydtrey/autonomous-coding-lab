from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.control_models import KC_CONTROL_SCHEMA
from knowledge_core.storage.models import Base, KC_SCHEMA, REVISION_ID_TYPE


class ProjectionSourceBindingRecord(Base):
    """Durable operational evidence correlating KC source slices to provider source IDs."""

    __tablename__ = "projection_source_binding"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "provider_source_id",
            name="uq_projection_source_binding_provider_source",
        ),
        Index(
            "ix_projection_source_binding_provider_lookup",
            "provider_partition_key",
            "provider_source_id",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    attempt_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.projection_attempt.attempt_id"),
        primary_key=True,
    )
    resource_version_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_SCHEMA}.resource_version.ref_id"),
        primary_key=True,
    )
    segment_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_revision_id: Mapped[int] = mapped_column(
        REVISION_ID_TYPE,
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"),
        nullable=False,
    )
    source_slice_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_partition_key: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
