"""Task 2 bitemporal history and current projection.

Revision ID: 0002_task2
Revises: 0001_task1
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_task2"
down_revision = "0001_task1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS kc_derived")

    op.add_column(
        "assertion",
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        schema="kc",
    )
    op.add_column(
        "assertion",
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        schema="kc",
    )
    op.add_column(
        "assertion",
        sa.Column("world_time_precision", sa.String(length=32), nullable=True),
        schema="kc",
    )
    op.create_check_constraint(
        "ck_assertion_valid_interval",
        "assertion",
        "valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from",
        schema="kc",
    )

    op.create_table(
        "current_assertion",
        sa.Column(
            "assertion_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.assertion.ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "subject_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "predicate_revision_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_predicate_revision.ref_id"),
            nullable=False,
        ),
        sa.Column("conflict_group_id", sa.Uuid(), nullable=True),
        sa.Column(
            "source_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.Column(
            "projection_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.Column("selection_reason", sa.String(length=64), nullable=False),
        schema="kc_derived",
    )
    op.create_index(
        "ix_current_assertion_subject_ref_id",
        "current_assertion",
        ["subject_ref_id"],
        schema="kc_derived",
    )
    op.create_index(
        "ix_current_assertion_predicate_revision_ref",
        "current_assertion",
        ["predicate_revision_ref"],
        schema="kc_derived",
    )
    op.create_index(
        "ix_current_assertion_conflict_group_id",
        "current_assertion",
        ["conflict_group_id"],
        schema="kc_derived",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_current_assertion_conflict_group_id",
        table_name="current_assertion",
        schema="kc_derived",
    )
    op.drop_index(
        "ix_current_assertion_predicate_revision_ref",
        table_name="current_assertion",
        schema="kc_derived",
    )
    op.drop_index(
        "ix_current_assertion_subject_ref_id",
        table_name="current_assertion",
        schema="kc_derived",
    )
    op.drop_table("current_assertion", schema="kc_derived")

    op.drop_constraint(
        "ck_assertion_valid_interval",
        "assertion",
        type_="check",
        schema="kc",
    )
    op.drop_column("assertion", "world_time_precision", schema="kc")
    op.drop_column("assertion", "valid_to", schema="kc")
    op.drop_column("assertion", "valid_from", schema="kc")
    op.execute("DROP SCHEMA IF EXISTS kc_derived")
