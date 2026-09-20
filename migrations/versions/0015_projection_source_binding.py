"""Projection provider-source correlation evidence.

Revision ID: 0015_projection_source_binding
Revises: 0014_projection_validation
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_projection_source_binding"
down_revision = "0014_projection_validation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projection_source_binding",
        sa.Column(
            "attempt_id",
            sa.Uuid(),
            sa.ForeignKey("kc_control.projection_attempt.attempt_id"),
            primary_key=True,
        ),
        sa.Column(
            "resource_version_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.resource_version.ref_id"),
            primary_key=True,
        ),
        sa.Column("segment_key", sa.String(length=128), primary_key=True),
        sa.Column(
            "source_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.Column("source_slice_sha256", sa.String(length=64), nullable=False),
        sa.Column("provider_partition_key", sa.String(length=128), nullable=False),
        sa.Column("provider_source_id", sa.String(length=255), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "attempt_id",
            "provider_source_id",
            name="uq_projection_source_binding_provider_source",
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_projection_source_binding_provider_lookup",
        "projection_source_binding",
        ["provider_partition_key", "provider_source_id"],
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_projection_source_binding_provider_lookup",
        table_name="projection_source_binding",
        schema="kc_control",
    )
    op.drop_table("projection_source_binding", schema="kc_control")
