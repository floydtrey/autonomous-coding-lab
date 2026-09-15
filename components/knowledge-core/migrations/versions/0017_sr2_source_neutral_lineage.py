"""Source-neutral SR-2 governed lineage with repository compatibility fields.

Revision ID: 0017_sr2_source_neutral
Revises: 0016_governed_sources
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_sr2_source_neutral"
down_revision = "0016_governed_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "text_generation_source",
        sa.Column("governed_observation_id", sa.Uuid(), nullable=True),
        schema="kc_derived",
    )
    op.add_column(
        "text_generation_source",
        sa.Column("governed_decision_id", sa.Uuid(), nullable=True),
        schema="kc_derived",
    )
    op.add_column(
        "text_generation_source",
        sa.Column("governing_snapshot_digest", sa.String(length=71), nullable=True),
        schema="kc_derived",
    )
    op.add_column(
        "text_generation_source",
        sa.Column("governed_projection_digest", sa.String(length=71), nullable=True),
        schema="kc_derived",
    )
    op.create_foreign_key(
        "fk_text_generation_source_governed_observation",
        "text_generation_source",
        "governed_source_observation",
        ["governed_observation_id"],
        ["observation_id"],
        source_schema="kc_derived",
        referent_schema="kc_control",
    )
    op.create_foreign_key(
        "fk_text_generation_source_governed_decision",
        "text_generation_source",
        "governed_source_decision",
        ["governed_decision_id"],
        ["decision_id"],
        source_schema="kc_derived",
        referent_schema="kc_control",
    )
    op.create_foreign_key(
        "fk_text_generation_source_governing_snapshot",
        "text_generation_source",
        "governed_retrieval_snapshot",
        ["governing_snapshot_digest"],
        ["snapshot_digest"],
        source_schema="kc_derived",
        referent_schema="kc_control",
    )
    op.create_index(
        "ix_text_generation_source_governed_observation",
        "text_generation_source",
        ["governed_observation_id"],
        schema="kc_derived",
    )
    op.create_index(
        "ix_text_generation_source_governing_snapshot",
        "text_generation_source",
        ["governing_snapshot_digest"],
        schema="kc_derived",
    )

    # These are compatibility columns for V1 repository lineage. V2 generic
    # sources are permitted to leave them null rather than invent Git evidence.
    op.alter_column(
        "text_generation_source",
        "source_observation_id",
        existing_type=sa.Uuid(),
        nullable=True,
        schema="kc_derived",
    )
    op.alter_column(
        "text_generation_source",
        "governing_manifest_digest",
        existing_type=sa.String(length=64),
        nullable=True,
        schema="kc_derived",
    )
    op.alter_column(
        "text_generation_source",
        "projection_snapshot_digest",
        existing_type=sa.String(length=71),
        nullable=True,
        schema="kc_derived",
    )

    for column, type_ in (
        ("repository", sa.Text()),
        ("source_repository_key", sa.String(length=128)),
        ("source_document_key", sa.String(length=128)),
        ("source_path", sa.Text()),
        ("source_version", sa.Text()),
    ):
        op.alter_column(
            "resource_segment_text_search",
            column,
            existing_type=type_,
            nullable=True,
            schema="kc_derived",
        )


def downgrade() -> None:
    # A downgrade is valid only for databases that do not contain V2 non-Git SR-2
    # rows. PostgreSQL will reject SET NOT NULL if such rows exist, which is safer
    # than silently manufacturing repository provenance.
    for column, type_ in (
        ("repository", sa.Text()),
        ("source_repository_key", sa.String(length=128)),
        ("source_document_key", sa.String(length=128)),
        ("source_path", sa.Text()),
        ("source_version", sa.Text()),
    ):
        op.alter_column(
            "resource_segment_text_search",
            column,
            existing_type=type_,
            nullable=False,
            schema="kc_derived",
        )
    op.alter_column(
        "text_generation_source",
        "projection_snapshot_digest",
        existing_type=sa.String(length=71),
        nullable=False,
        schema="kc_derived",
    )
    op.alter_column(
        "text_generation_source",
        "governing_manifest_digest",
        existing_type=sa.String(length=64),
        nullable=False,
        schema="kc_derived",
    )
    op.alter_column(
        "text_generation_source",
        "source_observation_id",
        existing_type=sa.Uuid(),
        nullable=False,
        schema="kc_derived",
    )

    op.drop_index(
        "ix_text_generation_source_governing_snapshot",
        table_name="text_generation_source",
        schema="kc_derived",
    )
    op.drop_index(
        "ix_text_generation_source_governed_observation",
        table_name="text_generation_source",
        schema="kc_derived",
    )
    op.drop_constraint(
        "fk_text_generation_source_governing_snapshot",
        "text_generation_source",
        schema="kc_derived",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_text_generation_source_governed_decision",
        "text_generation_source",
        schema="kc_derived",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_text_generation_source_governed_observation",
        "text_generation_source",
        schema="kc_derived",
        type_="foreignkey",
    )
    op.drop_column(
        "text_generation_source", "governed_projection_digest", schema="kc_derived"
    )
    op.drop_column(
        "text_generation_source", "governing_snapshot_digest", schema="kc_derived"
    )
    op.drop_column(
        "text_generation_source", "governed_decision_id", schema="kc_derived"
    )
    op.drop_column(
        "text_generation_source", "governed_observation_id", schema="kc_derived"
    )
