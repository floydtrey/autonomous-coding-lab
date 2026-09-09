"""Task 4 exact resource versions and traversable provenance.

Revision ID: 0004_task4
Revises: 0003_task3
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_task4"
down_revision = "0003_task3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resource",
        sa.Column("ref_id", sa.Uuid(), sa.ForeignKey("kc.knowledge_ref.ref_id"), primary_key=True),
        sa.Column("kind_revision_ref", sa.Uuid(), sa.ForeignKey("kc.semantic_kind_revision.ref_id"), nullable=False),
        sa.Column("created_revision_id", sa.BigInteger(), sa.ForeignKey("kc.revision.revision_id"), nullable=False),
        schema="kc",
    )
    op.create_table(
        "resource_version",
        sa.Column("ref_id", sa.Uuid(), sa.ForeignKey("kc.knowledge_ref.ref_id"), primary_key=True),
        sa.Column("resource_ref_id", sa.Uuid(), sa.ForeignKey("kc.resource.ref_id"), nullable=False),
        sa.Column("content_digest_algo", sa.String(length=16), nullable=False),
        sa.Column("content_digest", sa.String(length=128), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("media_type", sa.String(length=255), nullable=True),
        sa.Column("artifact_backend", sa.String(length=64), nullable=False),
        sa.Column("artifact_key", sa.Text(), nullable=False),
        sa.Column("observed_occurrence_ref", sa.Uuid(), sa.ForeignKey("kc.occurrence.ref_id"), nullable=True),
        sa.Column("created_revision_id", sa.BigInteger(), sa.ForeignKey("kc.revision.revision_id"), nullable=False),
        sa.UniqueConstraint("resource_ref_id", "content_digest_algo", "content_digest", name="uq_resource_version_exact_content"),
        schema="kc",
    )
    op.create_index("ix_resource_version_resource_ref_id", "resource_version", ["resource_ref_id"], schema="kc")
    op.create_table(
        "resource_locator",
        sa.Column("locator_id", sa.Uuid(), primary_key=True),
        sa.Column("resource_ref_id", sa.Uuid(), sa.ForeignKey("kc.resource.ref_id"), nullable=False),
        sa.Column("resource_version_ref", sa.Uuid(), sa.ForeignKey("kc.resource_version.ref_id"), nullable=True),
        sa.Column("locator_kind", sa.String(length=32), nullable=False),
        sa.Column("locator_text", sa.Text(), nullable=False),
        sa.Column("observed_occurrence_ref", sa.Uuid(), sa.ForeignKey("kc.occurrence.ref_id"), nullable=True),
        sa.Column("created_revision_id", sa.BigInteger(), sa.ForeignKey("kc.revision.revision_id"), nullable=False),
        sa.CheckConstraint("locator_kind IN ('path','url','git_ref','mailbox_locator','governed-other')", name="ck_resource_locator_kind"),
        schema="kc",
    )
    op.create_index("ix_resource_locator_resource_ref_id", "resource_locator", ["resource_ref_id"], schema="kc")
    op.create_index("ix_resource_locator_resource_version_ref", "resource_locator", ["resource_version_ref"], schema="kc")
    op.create_table(
        "provenance_link",
        sa.Column("link_id", sa.Uuid(), primary_key=True),
        sa.Column("relation_revision_ref", sa.Uuid(), sa.ForeignKey("kc.semantic_predicate_revision.ref_id"), nullable=False),
        sa.Column("source_ref_id", sa.Uuid(), sa.ForeignKey("kc.knowledge_ref.ref_id"), nullable=False),
        sa.Column("target_ref_id", sa.Uuid(), sa.ForeignKey("kc.knowledge_ref.ref_id"), nullable=False),
        sa.Column("activity_occurrence_ref", sa.Uuid(), sa.ForeignKey("kc.occurrence.ref_id"), nullable=True),
        sa.Column("created_revision_id", sa.BigInteger(), sa.ForeignKey("kc.revision.revision_id"), nullable=False),
        schema="kc",
    )
    op.create_index("ix_provenance_link_source_relation", "provenance_link", ["source_ref_id", "relation_revision_ref"], schema="kc")
    op.create_index("ix_provenance_link_target_relation", "provenance_link", ["target_ref_id", "relation_revision_ref"], schema="kc")
    op.create_index("ix_provenance_link_activity", "provenance_link", ["activity_occurrence_ref"], schema="kc")


def downgrade() -> None:
    op.drop_index("ix_provenance_link_activity", table_name="provenance_link", schema="kc")
    op.drop_index("ix_provenance_link_target_relation", table_name="provenance_link", schema="kc")
    op.drop_index("ix_provenance_link_source_relation", table_name="provenance_link", schema="kc")
    op.drop_table("provenance_link", schema="kc")
    op.drop_index("ix_resource_locator_resource_version_ref", table_name="resource_locator", schema="kc")
    op.drop_index("ix_resource_locator_resource_ref_id", table_name="resource_locator", schema="kc")
    op.drop_table("resource_locator", schema="kc")
    op.drop_index("ix_resource_version_resource_ref_id", table_name="resource_version", schema="kc")
    op.drop_table("resource_version", schema="kc")
    op.drop_table("resource", schema="kc")
