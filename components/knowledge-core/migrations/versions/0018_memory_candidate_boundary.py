"""Durable non-canonical memory candidate proposal/review boundary.

Revision ID: 0018_memory_candidate
Revises: 0017_sr2_source_neutral
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_memory_candidate"
down_revision = "0017_sr2_source_neutral"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_candidate",
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by_principal_ref", sa.String(length=255), nullable=False),
        sa.Column("proposer_ref", sa.String(length=255), nullable=False),
        sa.Column("project_key", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("review_operation_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_principal_ref", sa.String(length=255), nullable=True),
        sa.Column("review_decision_ref", sa.String(length=255), nullable=True),
        sa.Column("review_reason_code", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "state IN ('pending','approved','rejected')",
            name="ck_memory_candidate_state",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["kc_control.operation.operation_id"],
            name="fk_memory_candidate_proposal_operation",
        ),
        sa.ForeignKeyConstraint(
            ["review_operation_id"],
            ["kc_control.operation.operation_id"],
            name="fk_memory_candidate_review_operation",
        ),
        sa.PrimaryKeyConstraint("candidate_id"),
        sa.UniqueConstraint(
            "review_operation_id",
            name="uq_memory_candidate_review_operation",
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_memory_candidate_state_proposed",
        "memory_candidate",
        ["state", "proposed_at"],
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_memory_candidate_state_proposed",
        table_name="memory_candidate",
        schema="kc_control",
    )
    op.drop_table("memory_candidate", schema="kc_control")
