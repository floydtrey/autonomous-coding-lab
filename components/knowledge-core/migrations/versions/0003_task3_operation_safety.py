"""Task 3 operation idempotency and stale-writer control.

Revision ID: 0003_task3
Revises: 0002_task2
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_task3"
down_revision = "0002_task2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS kc_control")

    op.create_table(
        "operation",
        sa.Column("operation_id", sa.Uuid(), primary_key=True),
        sa.Column("caller_principal_ref", sa.String(length=255), nullable=False),
        sa.Column("operation_class", sa.String(length=64), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "result_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=True,
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("response_metadata", postgresql.JSONB(), nullable=True),
        sa.CheckConstraint(
            "status IN ('received','running','committed','failed','conflict')",
            name="ck_operation_status",
        ),
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_table("operation", schema="kc_control")
    op.execute("DROP SCHEMA IF EXISTS kc_control")
