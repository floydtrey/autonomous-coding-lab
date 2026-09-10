"""SR-2 deterministic section retrieval derived projection.

Revision ID: 0011_sr2
Revises: 0010_ri2
Create Date: 2026-09-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0011_sr2"
down_revision = "0010_ri2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resource_segment_text_search",
        sa.Column(
            "generation_id",
            sa.Uuid(),
            sa.ForeignKey("kc_derived.generation.generation_id"),
            primary_key=True,
        ),
        sa.Column(
            "resource_version_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.resource_version.ref_id"),
            primary_key=True,
        ),
        sa.Column("segment_ordinal", sa.Integer(), primary_key=True),
        sa.Column("segment_key", sa.String(length=80), nullable=False),
        sa.Column("segment_kind", sa.String(length=16), nullable=False),
        sa.Column("base_block_ordinal", sa.Integer(), nullable=False),
        sa.Column("part_index", sa.Integer(), nullable=False),
        sa.Column("part_count", sa.Integer(), nullable=False),
        sa.Column("source_byte_start", sa.BigInteger(), nullable=False),
        sa.Column("source_byte_end", sa.BigInteger(), nullable=False),
        sa.Column("source_line_start", sa.BigInteger(), nullable=False),
        sa.Column("source_line_end", sa.BigInteger(), nullable=False),
        sa.Column("source_slice_sha256", sa.String(length=64), nullable=False),
        sa.Column("heading_path", sa.JSON(), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("parent_lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_origin", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_directive_line", sa.BigInteger(), nullable=True),
        sa.Column("authority_rank", sa.Integer(), nullable=True),
        sa.Column("repository", sa.Text(), nullable=True),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("source_version", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=False),
        sa.CheckConstraint(
            "segment_ordinal >= 0 AND base_block_ordinal >= 0",
            name="ck_resource_segment_text_search_ordinals",
        ),
        sa.CheckConstraint(
            "segment_kind IN ('preamble','section','document','continuation')",
            name="ck_resource_segment_text_search_kind",
        ),
        sa.CheckConstraint(
            "part_index >= 1 AND part_count >= 1 AND part_index <= part_count",
            name="ck_resource_segment_text_search_parts",
        ),
        sa.CheckConstraint(
            "source_byte_start >= 0 AND source_byte_end >= source_byte_start",
            name="ck_resource_segment_text_search_bytes",
        ),
        sa.CheckConstraint(
            "source_line_start >= 1 AND source_line_end >= source_line_start",
            name="ck_resource_segment_text_search_lines",
        ),
        sa.CheckConstraint(
            "lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_segment_text_search_lifecycle",
        ),
        sa.CheckConstraint(
            "parent_lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_segment_text_search_parent_lifecycle",
        ),
        sa.CheckConstraint(
            "lifecycle_origin IN "
            "('document','section-directive','ancestor-directive')",
            name="ck_resource_segment_text_search_lifecycle_origin",
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
        ["generation_id", "lifecycle_state", "authority_rank"],
        schema="kc_derived",
    )
    op.create_index(
        "ix_resource_segment_text_search_parent",
        "resource_segment_text_search",
        ["resource_version_ref"],
        schema="kc_derived",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resource_segment_text_search_parent",
        table_name="resource_segment_text_search",
        schema="kc_derived",
    )
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
