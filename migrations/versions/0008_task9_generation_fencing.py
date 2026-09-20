"""Task 9 derived generation lineage and out-of-order finish fencing.

Revision ID: 0008_task9
Revises: 0007_task8
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_task9"
down_revision = "0007_task8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generation",
        sa.Column("generation_id", sa.Uuid(), primary_key=True),
        sa.Column("generation_sequence", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("derived_kind", sa.String(length=32), nullable=False),
        sa.Column(
            "source_revision_highwater",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.Column(
            "profile_revision_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_profile_revision.ref_id"),
            nullable=True,
        ),
        sa.Column("model_identity", sa.String(length=255), nullable=True),
        sa.Column("model_version", sa.String(length=128), nullable=True),
        sa.Column("config_digest", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "supersedes_generation",
            sa.Uuid(),
            sa.ForeignKey("kc_derived.generation.generation_id"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "derived_kind IN ('current_state','identity','classification','text',"
            "'chunks','embeddings','relation_closure','other')",
            name="ck_generation_derived_kind",
        ),
        sa.CheckConstraint(
            "status IN ('building','current','stale','failed','superseded',"
            "'restricted','deletion_pending')",
            name="ck_generation_status",
        ),
        schema="kc_derived",
    )
    op.create_index(
        "ix_generation_kind_sequence",
        "generation",
        ["derived_kind", "generation_sequence"],
        unique=True,
        schema="kc_derived",
    )
    op.create_index(
        "uq_generation_current_derived_kind",
        "generation",
        ["derived_kind"],
        unique=True,
        schema="kc_derived",
        postgresql_where=sa.text("status = 'current'"),
    )

    op.create_table(
        "generation_source",
        sa.Column(
            "generation_id",
            sa.Uuid(),
            sa.ForeignKey("kc_derived.generation.generation_id"),
            primary_key=True,
        ),
        sa.Column(
            "source_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "source_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=True,
        ),
        schema="kc_derived",
    )
    op.create_index(
        "ix_generation_source_source_ref",
        "generation_source",
        ["source_ref_id"],
        schema="kc_derived",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generation_source_source_ref",
        table_name="generation_source",
        schema="kc_derived",
    )
    op.drop_table("generation_source", schema="kc_derived")
    op.drop_index(
        "uq_generation_current_derived_kind",
        table_name="generation",
        schema="kc_derived",
    )
    op.drop_index(
        "ix_generation_kind_sequence",
        table_name="generation",
        schema="kc_derived",
    )
    op.drop_table("generation", schema="kc_derived")
