"""Provider-neutral projection validation ledger.

Revision ID: 0014_projection_validation
Revises: 0013_projection_evidence
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_projection_validation"
down_revision = "0013_projection_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_projection_attempt_validation_state",
        "projection_attempt",
        schema="kc_control",
        type_="check",
    )
    op.create_check_constraint(
        "ck_projection_attempt_validation_state",
        "projection_attempt",
        "validation_state IN ('unvalidated','validated','incomplete','rejected','quarantined')",
        schema="kc_control",
    )

    op.create_table(
        "projection_validation",
        sa.Column("validation_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Uuid(),
            sa.ForeignKey("kc_control.projection_attempt.attempt_id"),
            nullable=False,
        ),
        sa.Column("attempt_request_digest", sa.String(length=64), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("validator_identity", sa.String(length=255), nullable=False),
        sa.Column("validator_version", sa.String(length=128), nullable=True),
        sa.Column("ruleset_id", sa.String(length=128), nullable=True),
        sa.Column("ruleset_digest", sa.String(length=128), nullable=True),
        sa.Column("config_digest", sa.String(length=128), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "outcome IN ('pending','validated','incomplete','rejected','quarantined')",
            name="ck_projection_validation_outcome",
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_projection_validation_attempt",
        "projection_validation",
        ["attempt_id"],
        schema="kc_control",
    )

    op.create_table(
        "projection_validation_check",
        sa.Column(
            "validation_id",
            sa.Uuid(),
            sa.ForeignKey("kc_control.projection_validation.validation_id"),
            primary_key=True,
        ),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("check_code", sa.String(length=128), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("evidence_digest", sa.String(length=64), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "outcome IN ('passed','failed','indeterminate')",
            name="ck_projection_validation_check_outcome",
        ),
        sa.UniqueConstraint(
            "validation_id",
            "check_code",
            name="uq_projection_validation_check_code",
        ),
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_table("projection_validation_check", schema="kc_control")
    op.drop_index(
        "ix_projection_validation_attempt",
        table_name="projection_validation",
        schema="kc_control",
    )
    op.drop_table("projection_validation", schema="kc_control")

    op.drop_constraint(
        "ck_projection_attempt_validation_state",
        "projection_attempt",
        schema="kc_control",
        type_="check",
    )
    op.create_check_constraint(
        "ck_projection_attempt_validation_state",
        "projection_attempt",
        "validation_state IN ('unvalidated','validated','rejected')",
        schema="kc_control",
    )
