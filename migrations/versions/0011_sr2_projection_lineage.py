"""SR-2 exact governed projection lineage.

Revision ID: 0011_sr2_lineage
Revises: 0010_ri2
Create Date: 2026-09-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_sr2_lineage"
down_revision = "0010_ri2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "text_generation_source",
        sa.Column(
            "generation_id",
            sa.Uuid(),
            sa.ForeignKey("kc_derived.generation.generation_id"),
            primary_key=True,
        ),
        sa.Column(
            "resource_version_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.resource_version.ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "source_observation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "kc_control.repository_source_observation.observation_id"
            ),
            nullable=False,
        ),
        sa.Column(
            "governing_manifest_digest",
            sa.String(length=64),
            sa.ForeignKey(
                "kc_control.repository_import_receipt.manifest_digest"
            ),
            nullable=False,
        ),
        sa.Column(
            "projection_snapshot_digest",
            sa.String(length=71),
            nullable=False,
        ),
        schema="kc_derived",
    )
    op.create_index(
        "ix_text_generation_source_observation",
        "text_generation_source",
        ["source_observation_id"],
        schema="kc_derived",
    )
    op.create_index(
        "ix_text_generation_source_governing_manifest",
        "text_generation_source",
        ["governing_manifest_digest"],
        schema="kc_derived",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_text_generation_source_governing_manifest",
        table_name="text_generation_source",
        schema="kc_derived",
    )
    op.drop_index(
        "ix_text_generation_source_observation",
        table_name="text_generation_source",
        schema="kc_derived",
    )
    op.drop_table("text_generation_source", schema="kc_derived")
