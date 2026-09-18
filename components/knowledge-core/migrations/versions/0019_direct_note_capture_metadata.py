"""C02 immutable direct-note capture metadata.

Revision ID: 0019_direct_note_capture
Revises: 0018_memory_candidate
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0019_direct_note_capture"
down_revision = "0018_memory_candidate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "direct_note_capture_metadata",
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("resource_version_ref", sa.Uuid(), nullable=False),
        sa.Column("principal_ref", sa.String(length=255), nullable=False),
        sa.Column("project_key", sa.String(length=255), nullable=False),
        sa.Column("metadata_version", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("title_supplied", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("category_supplied", sa.Boolean(), nullable=False),
        sa.Column("source_description", sa.Text(), nullable=True),
        sa.Column("source_urls", sa.JSON(), nullable=False),
        sa.Column("source_date", sa.Date(), nullable=True),
        sa.Column("source_time_precision", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "source_time_precision IN ('unsupplied','date','timestamp')",
            name="ck_direct_note_capture_source_time_precision",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["kc_control.governed_source_observation.observation_id"],
            name="fk_direct_note_capture_observation",
        ),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["kc_control.operation.operation_id"],
            name="fk_direct_note_capture_operation",
        ),
        sa.ForeignKeyConstraint(
            ["resource_version_ref"],
            ["kc.resource_version.ref_id"],
            name="fk_direct_note_capture_resource_version",
        ),
        sa.PrimaryKeyConstraint("observation_id"),
        sa.UniqueConstraint(
            "operation_id",
            name="uq_direct_note_capture_operation",
        ),
        sa.UniqueConstraint(
            "request_fingerprint",
            name="uq_direct_note_capture_request_fingerprint",
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_direct_note_capture_resource_version",
        "direct_note_capture_metadata",
        ["resource_version_ref"],
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_direct_note_capture_resource_version",
        table_name="direct_note_capture_metadata",
        schema="kc_control",
    )
    op.drop_table("direct_note_capture_metadata", schema="kc_control")
