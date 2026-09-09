"""RF-2 PostgreSQL lexical retrieval derived projection.

Revision ID: 0009_rf2
Revises: 0008_task9
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_rf2"
down_revision = "0008_task9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resource_text_search",
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
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("authority_rank", sa.Integer(), nullable=True),
        sa.Column("repository", sa.Text(), nullable=True),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("source_version", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=False),
        sa.CheckConstraint(
            "lifecycle_state IN ('current','unknown','superseded')",
            name="ck_resource_text_search_lifecycle",
        ),
        schema="kc_derived",
    )
    op.create_index(
        "ix_resource_text_search_vector",
        "resource_text_search",
        ["search_vector"],
        schema="kc_derived",
        postgresql_using="gin",
    )
    op.create_index(
        "ix_resource_text_search_generation_rank",
        "resource_text_search",
        ["generation_id", "lifecycle_state", "authority_rank"],
        schema="kc_derived",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resource_text_search_generation_rank",
        table_name="resource_text_search",
        schema="kc_derived",
    )
    op.drop_index(
        "ix_resource_text_search_vector",
        table_name="resource_text_search",
        schema="kc_derived",
    )
    op.drop_table("resource_text_search", schema="kc_derived")
