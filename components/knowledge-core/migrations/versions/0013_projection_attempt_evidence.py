"""Provider-neutral projection attempt/evidence ledger.

Revision ID: 0013_projection_evidence
Revises: 0012_sr2_segments
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_projection_evidence"
down_revision = "0012_sr2_segments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projection_attempt",
        sa.Column("attempt_id", sa.Uuid(), primary_key=True),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("projection_kind", sa.String(length=64), nullable=False),
        sa.Column("target_kind", sa.String(length=64), nullable=False),
        sa.Column("namespace_key", sa.String(length=255), nullable=False),
        sa.Column("scope_key", sa.String(length=255), nullable=False),
        sa.Column("backend_identity", sa.String(length=255), nullable=False),
        sa.Column("backend_version", sa.String(length=128), nullable=True),
        sa.Column("profile_id", sa.String(length=128), nullable=True),
        sa.Column("profile_digest", sa.String(length=128), nullable=True),
        sa.Column("config_digest", sa.String(length=128), nullable=True),
        sa.Column("disposition", sa.String(length=32), nullable=False),
        sa.Column("validation_state", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("warnings_json", sa.JSON(), nullable=True),
        sa.Column("errors_json", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "disposition IN ('pending','succeeded','incomplete','failed','quarantined')",
            name="ck_projection_attempt_disposition",
        ),
        sa.CheckConstraint(
            "validation_state IN ('unvalidated','validated','rejected')",
            name="ck_projection_attempt_validation_state",
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_projection_attempt_target_scope",
        "projection_attempt",
        ["target_kind", "namespace_key", "scope_key"],
        schema="kc_control",
    )

    op.create_table(
        "projection_attempt_source",
        sa.Column(
            "attempt_id",
            sa.Uuid(),
            sa.ForeignKey("kc_control.projection_attempt.attempt_id"),
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
        schema="kc_control",
    )
    op.create_index(
        "ix_projection_attempt_source_ref",
        "projection_attempt_source",
        ["source_ref_id"],
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_projection_attempt_source_ref",
        table_name="projection_attempt_source",
        schema="kc_control",
    )
    op.drop_table("projection_attempt_source", schema="kc_control")
    op.drop_index(
        "ix_projection_attempt_target_scope",
        table_name="projection_attempt",
        schema="kc_control",
    )
    op.drop_table("projection_attempt", schema="kc_control")
