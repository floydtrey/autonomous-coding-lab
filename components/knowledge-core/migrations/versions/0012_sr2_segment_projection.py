"""SR-2 segment-generation derived projection storage.

Revision ID: 0012_sr2_segments
Revises: 0011_sr2_lineage
Create Date: 2026-09-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0012_sr2_segments"
down_revision = "0011_sr2_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "text_generation_profile",
        sa.Column(
            "generation_id",
            sa.Uuid(),
            sa.ForeignKey("kc_derived.generation.generation_id"),
            primary_key=True,
        ),
        sa.Column("structural_profile_id", sa.String(length=128), nullable=False),
        sa.Column("structural_profile_digest", sa.String(length=71), nullable=False),
        sa.Column("projection_profile_id", sa.String(length=128), nullable=False),
        sa.Column("projection_profile_digest", sa.String(length=71), nullable=False),
        sa.Column("generation_config_digest", sa.String(length=71), nullable=False),
        schema="kc_derived",
    )

    op.create_table(
        "resource_segment_text_search",
        sa.Column("generation_id", sa.Uuid(), primary_key=True),
        sa.Column("resource_version_ref", sa.Uuid(), primary_key=True),
        sa.Column("segment_ordinal", sa.Integer(), primary_key=True),
        sa.Column("segment_key", sa.String(length=71), nullable=False),
        sa.Column("structural_kind", sa.String(length=16), nullable=False),
        sa.Column("base_block_ordinal", sa.Integer(), nullable=False),
        sa.Column("part_index", sa.Integer(), nullable=False),
        sa.Column("part_count", sa.Integer(), nullable=False),
        sa.Column("source_byte_start", sa.BigInteger(), nullable=False),
        sa.Column("source_byte_end", sa.BigInteger(), nullable=False),
        sa.Column("source_line_start", sa.BigInteger(), nullable=False),
        sa.Column("source_line_end", sa.BigInteger(), nullable=False),
        sa.Column("source_slice_sha256", sa.String(length=64), nullable=False),
        sa.Column("heading_path", sa.JSON(), nullable=False),
        sa.Column("parent_lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("declared_lifecycle_state", sa.String(length=32), nullable=True),
        sa.Column("declaration_source_line", sa.BigInteger(), nullable=True),
        sa.Column("declaration_byte_start", sa.BigInteger(), nullable=True),
        sa.Column("declaration_byte_end", sa.BigInteger(), nullable=True),
        sa.Column("effective_lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("effective_control_provenance", sa.JSON(), nullable=False),
        sa.Column("authority_rank", sa.Integer(), nullable=True),
        sa.Column("repository", sa.Text(), nullable=False),
        sa.Column("source_repository_key", sa.String(length=128), nullable=False),
        sa.Column("source_document_key", sa.String(length=128), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("source_version", sa.Text(), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_id", "resource_version_ref"],
            [
                "kc_derived.text_generation_source.generation_id",
                "kc_derived.text_generation_source.resource_version_ref",
            ],
            name="fk_resource_segment_text_search_generation_source",
        ),
        sa.CheckConstraint(
            "structural_kind IN ('document','preamble','section','continuation')",
            name="ck_resource_segment_text_search_kind",
        ),
        sa.CheckConstraint(
            "parent_lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_segment_text_search_parent_lifecycle",
        ),
        sa.CheckConstraint(
            "declared_lifecycle_state IS NULL OR "
            "declared_lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_segment_text_search_declared_lifecycle",
        ),
        sa.CheckConstraint(
            "effective_lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_segment_text_search_effective_lifecycle",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            "segment_ordinal >= 0 AND base_block_ordinal >= 0 "
            "AND part_index >= 1 AND part_count >= 1 AND part_index <= part_count",
            name="ck_resource_segment_text_search_ordinals",
        ),
        sa.CheckConstraint(
            "source_byte_start >= 0 AND source_byte_end >= source_byte_start "
            "AND source_line_start >= 1 AND source_line_end >= source_line_start",
            name="ck_resource_segment_text_search_coordinates",
        ),
        sa.UniqueConstraint(
            "generation_id",
            "segment_key",
            name="uq_resource_segment_text_search_generation_key",
        ),
        schema="kc_derived",
    )
    op.create_index(
        "ix_resource_segment_text_search_vector",
        "resource_segment_text_search",
        ["search_vector"],
        schema="kc_derived",
        postgresql_using="gin",
    )
    op.create_index(
        "ix_resource_segment_text_search_generation_rank",
        "resource_segment_text_search",
        ["generation_id", "effective_lifecycle_state", "authority_rank"],
        schema="kc_derived",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resource_segment_text_search_generation_rank",
        table_name="resource_segment_text_search",
        schema="kc_derived",
    )
    op.drop_index(
        "ix_resource_segment_text_search_vector",
        table_name="resource_segment_text_search",
        schema="kc_derived",
    )
    op.drop_table("resource_segment_text_search", schema="kc_derived")
    op.drop_table("text_generation_profile", schema="kc_derived")
