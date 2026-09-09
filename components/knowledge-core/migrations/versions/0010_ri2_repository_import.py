"""RI-2 governed repository import control state.

Revision ID: 0010_ri2
Revises: 0009_rf2
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_ri2"
down_revision = "0009_rf2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_document_binding",
        sa.Column("source_repository_key", sa.String(length=128), primary_key=True),
        sa.Column("source_document_key", sa.String(length=128), primary_key=True),
        sa.Column(
            "resource_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.resource.ref_id"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "resource_ref",
            name="uq_repository_document_binding_resource",
        ),
        schema="kc_control",
    )
    op.create_table(
        "repository_import_receipt",
        sa.Column("manifest_digest", sa.String(length=64), primary_key=True),
        sa.Column("previous_manifest_digest", sa.String(length=64), nullable=True),
        sa.Column("source_repository_key", sa.String(length=128), nullable=False),
        sa.Column("source_commit", sa.String(length=64), nullable=False),
        sa.Column("plan_digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column(
            "resulting_text_generation_id",
            sa.Uuid(),
            sa.ForeignKey("kc_derived.generation.generation_id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('applying','settled','failed')",
            name="ck_repository_import_receipt_status",
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_repository_import_receipt_source_repository_key",
        "repository_import_receipt",
        ["source_repository_key"],
        schema="kc_control",
    )
    op.create_table(
        "repository_source_observation",
        sa.Column("observation_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "manifest_digest",
            sa.String(length=64),
            sa.ForeignKey("kc_control.repository_import_receipt.manifest_digest"),
            nullable=False,
        ),
        sa.Column("source_repository_key", sa.String(length=128), nullable=False),
        sa.Column("source_document_key", sa.String(length=128), nullable=False),
        sa.Column("source_commit", sa.String(length=64), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("git_blob_sha", sa.String(length=64), nullable=False),
        sa.Column(
            "resource_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.resource.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "resource_version_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.resource_version.ref_id"),
            nullable=False,
        ),
        sa.Column("classification", sa.String(length=128), nullable=False),
        sa.Column("retrieval_lifecycle", sa.String(length=32), nullable=False),
        sa.Column("authority_rank", sa.Integer(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "manifest_digest",
            "source_document_key",
            name="uq_repository_source_observation_manifest_document",
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_repository_source_observation_manifest_digest",
        "repository_source_observation",
        ["manifest_digest"],
        schema="kc_control",
    )
    op.create_index(
        "ix_repository_source_observation_source_document_key",
        "repository_source_observation",
        ["source_document_key"],
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_repository_source_observation_source_document_key",
        table_name="repository_source_observation",
        schema="kc_control",
    )
    op.drop_index(
        "ix_repository_source_observation_manifest_digest",
        table_name="repository_source_observation",
        schema="kc_control",
    )
    op.drop_table("repository_source_observation", schema="kc_control")
    op.drop_index(
        "ix_repository_import_receipt_source_repository_key",
        table_name="repository_import_receipt",
        schema="kc_control",
    )
    op.drop_table("repository_import_receipt", schema="kc_control")
    op.drop_table("repository_document_binding", schema="kc_control")
