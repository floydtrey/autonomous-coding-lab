from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.models import Base, KC_DERIVED_SCHEMA, KC_SCHEMA


class ResourceTextSearch(Base):
    __tablename__ = "resource_text_search"
    __table_args__ = (
        CheckConstraint(
            "lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_text_search_lifecycle",
        ),
        Index(
            "ix_resource_text_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        Index(
            "ix_resource_text_search_generation_rank",
            "generation_id",
            "lifecycle_state",
            "authority_rank",
        ),
        {"schema": KC_DERIVED_SCHEMA},
    )

    generation_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_DERIVED_SCHEMA}.generation.generation_id"),
        primary_key=True,
    )
    resource_version_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.resource_version.ref_id"),
        primary_key=True,
    )
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    authority_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repository: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR().with_variant(Text(), "sqlite"),
        nullable=False,
    )
