from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.control_models import KC_CONTROL_SCHEMA
from knowledge_core.storage.models import Base, KC_DERIVED_SCHEMA, KC_SCHEMA


class TextGenerationSource(Base):
    """Exact governed source lineage for one parent in an SR-2 text generation."""

    __tablename__ = "text_generation_source"
    __table_args__ = (
        Index(
            "ix_text_generation_source_observation",
            "source_observation_id",
        ),
        Index(
            "ix_text_generation_source_governing_manifest",
            "governing_manifest_digest",
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
    source_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.repository_source_observation.observation_id"
        ),
        nullable=False,
    )
    governing_manifest_digest: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.repository_import_receipt.manifest_digest"
        ),
        nullable=False,
    )
    projection_snapshot_digest: Mapped[str] = mapped_column(
        String(71),
        nullable=False,
    )


class TextGenerationProfile(Base):
    """Recoverable SR-2 behavior-bearing profile identity for one generation."""

    __tablename__ = "text_generation_profile"
    __table_args__ = ({"schema": KC_DERIVED_SCHEMA},)

    generation_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_DERIVED_SCHEMA}.generation.generation_id"),
        primary_key=True,
    )
    structural_profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
    structural_profile_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    projection_profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
    projection_profile_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    generation_config_digest: Mapped[str] = mapped_column(String(71), nullable=False)


class ResourceSegmentTextSearch(Base):
    """Disposable SR-2 segment lexical projection for one governed text generation."""

    __tablename__ = "resource_segment_text_search"
    __table_args__ = (
        ForeignKeyConstraint(
            ["generation_id", "resource_version_ref"],
            [
                f"{KC_DERIVED_SCHEMA}.text_generation_source.generation_id",
                f"{KC_DERIVED_SCHEMA}.text_generation_source.resource_version_ref",
            ],
            name="fk_resource_segment_text_search_generation_source",
        ),
        CheckConstraint(
            "structural_kind IN ('document','preamble','section','continuation')",
            name="ck_resource_segment_text_search_kind",
        ),
        CheckConstraint(
            "parent_lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_segment_text_search_parent_lifecycle",
        ),
        CheckConstraint(
            "declared_lifecycle_state IS NULL OR "
            "declared_lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_segment_text_search_declared_lifecycle",
        ),
        CheckConstraint(
            "effective_lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_segment_text_search_effective_lifecycle",
        ),
        CheckConstraint(
            "(declared_lifecycle_state IS NULL "
            "AND declaration_source_line IS NULL "
            "AND declaration_byte_start IS NULL "
            "AND declaration_byte_end IS NULL) "
            "OR "
            "(declared_lifecycle_state IS NOT NULL "
            "AND declaration_source_line IS NOT NULL "
            "AND declaration_byte_start IS NOT NULL "
            "AND declaration_byte_end IS NOT NULL)",
            name="ck_resource_segment_text_search_declaration_coordinates",
        ),
        CheckConstraint(
            "segment_ordinal >= 0 AND base_block_ordinal >= 0 "
            "AND part_index >= 1 AND part_count >= 1 AND part_index <= part_count",
            name="ck_resource_segment_text_search_ordinals",
        ),
        CheckConstraint(
            "source_byte_start >= 0 AND source_byte_end >= source_byte_start "
            "AND source_line_start >= 1 AND source_line_end >= source_line_start",
            name="ck_resource_segment_text_search_coordinates",
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
            "effective_lifecycle_state",
            "authority_rank",
        ),
        {"schema": KC_DERIVED_SCHEMA},
    )

    generation_id: Mapped[UUID] = mapped_column(primary_key=True)
    resource_version_ref: Mapped[UUID] = mapped_column(primary_key=True)
    segment_ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)

    segment_key: Mapped[str] = mapped_column(String(71), nullable=False)
    structural_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    base_block_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    part_index: Mapped[int] = mapped_column(Integer, nullable=False)
    part_count: Mapped[int] = mapped_column(Integer, nullable=False)

    source_byte_start: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_byte_end: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_line_start: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_line_end: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_slice_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    heading_path: Mapped[list[dict]] = mapped_column(JSON, nullable=False)

    parent_lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    declared_lifecycle_state: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    declaration_source_line: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    declaration_byte_start: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    declaration_byte_end: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    effective_lifecycle_state: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    effective_control_provenance: Mapped[list[dict]] = mapped_column(
        JSON, nullable=False
    )

    authority_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repository: Mapped[str] = mapped_column(Text, nullable=False)
    source_repository_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_document_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_version: Mapped[str] = mapped_column(Text, nullable=False)

    search_vector: Mapped[str] = mapped_column(
        TSVECTOR().with_variant(Text(), "sqlite"),
        nullable=False,
    )
