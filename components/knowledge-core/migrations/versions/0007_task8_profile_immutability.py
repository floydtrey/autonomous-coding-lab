"""Task 8 semantic profile activation control for Gate 17.

Revision ID: 0007_task8
Revises: 0006_task6
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_task8"
down_revision = "0006_task6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profile_activation",
        sa.Column("activation_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "profile_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_profile.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "profile_revision_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_profile_revision.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "activated_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        schema="kc_control",
    )
    op.create_index(
        "ix_profile_activation_profile_ref_id",
        "profile_activation",
        ["profile_ref_id"],
        schema="kc_control",
    )
    op.create_index(
        "ix_profile_activation_activated_revision_id",
        "profile_activation",
        ["activated_revision_id"],
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_profile_activation_activated_revision_id",
        table_name="profile_activation",
        schema="kc_control",
    )
    op.drop_index(
        "ix_profile_activation_profile_ref_id",
        table_name="profile_activation",
        schema="kc_control",
    )
    op.drop_table("profile_activation", schema="kc_control")
