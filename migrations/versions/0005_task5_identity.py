"""Task 5 reversible identity transitions and current identity projection.

Revision ID: 0005_task5
Revises: 0004_task4
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_task5"
down_revision = "0004_task4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_transition",
        sa.Column(
            "occurrence_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.occurrence.ref_id"),
            primary_key=True,
        ),
        sa.Column("transition_type", sa.String(length=32), nullable=False),
        sa.Column(
            "reverses_transition_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.identity_transition.occurrence_ref_id"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "created_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "transition_type IN ('resolve_same','resolve_different','merge','split',"
            "'replace','reassign_identifier')",
            name="ck_identity_transition_type",
        ),
        schema="kc",
    )

    op.create_table(
        "identity_transition_member",
        sa.Column(
            "transition_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.identity_transition.occurrence_ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "entity_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.entity.ref_id"),
            primary_key=True,
        ),
        sa.Column("member_role", sa.String(length=32), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "member_role IN ('source','member','representative','old','new',"
            "'split_member','governed-other')",
            name="ck_identity_transition_member_role",
        ),
        schema="kc",
    )
    op.create_index(
        "ix_identity_transition_member_entity_ref_id",
        "identity_transition_member",
        ["entity_ref_id"],
        schema="kc",
    )

    op.create_table(
        "current_identity_member",
        sa.Column(
            "entity_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.entity.ref_id"),
            primary_key=True,
        ),
        sa.Column("resolution_group_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "representative_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.entity.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "source_transition_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.identity_transition.occurrence_ref_id"),
            nullable=False,
        ),
        sa.Column(
            "source_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "entity_ref_id",
            name="uq_current_identity_member_entity_ref",
        ),
        schema="kc_derived",
    )
    op.create_index(
        "ix_current_identity_member_resolution_group_id",
        "current_identity_member",
        ["resolution_group_id"],
        schema="kc_derived",
    )
    op.create_index(
        "ix_current_identity_member_representative_ref_id",
        "current_identity_member",
        ["representative_ref_id"],
        schema="kc_derived",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_current_identity_member_representative_ref_id",
        table_name="current_identity_member",
        schema="kc_derived",
    )
    op.drop_index(
        "ix_current_identity_member_resolution_group_id",
        table_name="current_identity_member",
        schema="kc_derived",
    )
    op.drop_table("current_identity_member", schema="kc_derived")

    op.drop_index(
        "ix_identity_transition_member_entity_ref_id",
        table_name="identity_transition_member",
        schema="kc",
    )
    op.drop_table("identity_transition_member", schema="kc")
    op.drop_table("identity_transition", schema="kc")
