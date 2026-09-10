from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
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
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR().with_variant(Text(), "sqlite"),
        nullable=False,
    )


class ResourceSegmentTextSearch(Base):
    __tablename__ = "resource_segment_text_search"
    __table_args__ = (
        CheckConstraint(
            "segment_ordinal >= 0 AND base_block_ordinal >= 0",
            name="ck_resource_segment_text_search_ordinals",
        ),
        CheckConstraint(
            "segment_kind IN ('preamble','section','document','continuation')",
            name="ck_resource_segment_text_search_kind",
        ),
        CheckConstraint(
            "part_index >= 1 AND part_count >= 1 AND part_index <= part_count",
            name="ck_resource_segment_text_search_parts",
        ),
        CheckConstraint(
            "source_byte_start >= 0 AND source_byte_end >= source_byte_start",
            name="ck_resource_segment_text_search_bytes",
        ),
        CheckConstraint(
            "source_line_start >= 1 AND source_line_end >= source_line_start",
            name="ck_resource_segment_text_search_lines",
        ),
        CheckConstraint(
            "lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_segment_text_search_lifecycle",
        ),
        CheckConstraint(
            "parent_lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_segment_text_search_parent_lifecycle",
        ),
        CheckConstraint(
            "lifecycle_origin IN ('document','section-directive','ancestor-directive')",
            name="ck_resource_segment_text_search_lifecycle_origin",
        ),
        UniqueConstraint(
            "generation_id",
            "segment_key",
            name="uq_resource_segment_text_search_generation_key",
        ),
        Index(
            "ix_resource_segment_text_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        Index(
            "ix_resource_segment_text_search_generation_rank",
            "generation_id",
            "lifecycle_state",
            "authority_rank",
        ),
        Index(
            "ix_resource_segment_text_search_parent",
            "resource_version_ref",
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
    segment_ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    segment_key: Mapped[str] = mapped_column(String(80), nullable=False)
    segment_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    base_block_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    part_index: Mapped[int] = mapped_column(Integer, nullable=False)
    part_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_byte_start: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_byte_end: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_line_start: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_line_end: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_slice_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    heading_path: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_directive_line: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    authority_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repository: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR().with_variant(Text(), "sqlite"),
        nullable=False,
    )
