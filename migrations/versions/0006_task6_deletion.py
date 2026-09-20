"""Task 6 deletion/restriction serving fence and control ledger.

Revision ID: 0006_task6
Revises: 0005_task5
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_task6"
down_revision = "0005_task5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deletion_case",
        sa.Column("case_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "operation_id",
            sa.Uuid(),
            sa.ForeignKey("kc_control.operation.operation_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("policy_scope_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("minimal_metadata", postgresql.JSONB(), nullable=True),
        sa.CheckConstraint(
            "action_type IN ('restrict','erase','retention_exception')",
            name="ck_deletion_case_action_type",
        ),
        sa.CheckConstraint(
            "status IN ('requested','fenced','canonical_pending','derivatives_pending',"
            "'backup_fenced','settled','blocked','failed')",
            name="ck_deletion_case_status",
        ),
        schema="kc_control",
    )

    op.create_table(
        "deletion_target",
        sa.Column(
            "case_id",
            sa.Uuid(),
            sa.ForeignKey("kc_control.deletion_case.case_id"),
            primary_key=True,
        ),
        sa.Column(
            "target_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            primary_key=True,
        ),
        sa.Column("reconciliation_state", sa.String(length=32), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "reconciliation_state IN ('fenced','restricted_settled',"
            "'erased_tombstone','blocked')",
            name="ck_deletion_target_state",
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_deletion_target_target_ref_id",
        "deletion_target",
        ["target_ref_id"],
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_deletion_target_target_ref_id",
        table_name="deletion_target",
        schema="kc_control",
    )
    op.drop_table("deletion_target", schema="kc_control")
    op.drop_table("deletion_case", schema="kc_control")
