"""Source-neutral governed evidence and legacy repository mapping.

Revision ID: 0013_governed_sources
Revises: 0012_sr2_segments
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_governed_sources"
down_revision = "0012_sr2_segments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "governed_source_binding",
        sa.Column("source_identity_digest", sa.String(length=71), primary_key=True),
        sa.Column("contract_version", sa.String(length=64), nullable=False),
        sa.Column("source_kind", sa.String(length=128), nullable=False),
        sa.Column("origin_scope", sa.Text(), nullable=False),
        sa.Column("collection_key", sa.Text(), nullable=False),
        sa.Column("item_key", sa.Text(), nullable=False),
        sa.Column("resource_ref", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["resource_ref"], ["kc.resource.ref_id"]),
        sa.UniqueConstraint(
            "source_kind",
            "origin_scope",
            "collection_key",
            "item_key",
            name="uq_governed_source_binding_identity",
        ),
        sa.UniqueConstraint(
            "source_identity_digest",
            "resource_ref",
            name="uq_governed_source_binding_digest_resource",
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_governed_source_binding_resource_ref",
        "governed_source_binding",
        ["resource_ref"],
        schema="kc_control",
    )

    op.create_table(
        "governed_source_observation",
        sa.Column("observation_id", sa.Uuid(), primary_key=True),
        sa.Column("contract_version", sa.String(length=64), nullable=False),
        sa.Column("source_identity_digest", sa.String(length=71), nullable=False),
        sa.Column("resource_version_ref", sa.Uuid(), nullable=False),
        sa.Column("producer_id", sa.String(length=128), nullable=False),
        sa.Column("producer_version", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_revision_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observation_digest", sa.String(length=71), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_identity_digest"],
            ["kc_control.governed_source_binding.source_identity_digest"],
        ),
        sa.ForeignKeyConstraint(
            ["resource_version_ref"],
            ["kc.resource_version.ref_id"],
        ),
        sa.UniqueConstraint(
            "observation_id",
            "source_identity_digest",
            "resource_version_ref",
            "observation_digest",
            name="uq_governed_source_observation_exact",
        ),
        sa.UniqueConstraint(
            "observation_digest",
            name="uq_governed_source_observation_digest",
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_governed_source_observation_source_identity_digest",
        "governed_source_observation",
        ["source_identity_digest"],
        schema="kc_control",
    )
    op.create_index(
        "ix_governed_source_observation_resource_version_ref",
        "governed_source_observation",
        ["resource_version_ref"],
        schema="kc_control",
    )

    op.create_table(
        "governed_source_evidence",
        sa.Column("observation_id", sa.Uuid(), primary_key=True),
        sa.Column("evidence_ordinal", sa.Integer(), primary_key=True),
        sa.Column("evidence_kind", sa.String(length=128), nullable=False),
        sa.Column("evidence_ref", sa.Text(), nullable=False),
        sa.Column("evidence_digest", sa.String(length=71), nullable=False),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["kc_control.governed_source_observation.observation_id"],
        ),
        sa.UniqueConstraint(
            "observation_id",
            "evidence_kind",
            "evidence_ref",
            "evidence_digest",
            name="uq_governed_source_evidence_exact",
        ),
        schema="kc_control",
    )

    op.create_table(
        "governed_source_decision",
        sa.Column("decision_id", sa.Uuid(), primary_key=True),
        sa.Column("contract_version", sa.String(length=64), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.String(length=128), nullable=False),
        sa.Column("classification", sa.String(length=128), nullable=False),
        sa.Column("retrieval_lifecycle", sa.String(length=32), nullable=False),
        sa.Column("authority_rank", sa.Integer(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_digest", sa.String(length=71), nullable=False),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["kc_control.governed_source_observation.observation_id"],
        ),
        sa.CheckConstraint(
            "retrieval_lifecycle IN ('current','unknown','superseded')",
            name="ck_governed_source_decision_lifecycle",
        ),
        sa.CheckConstraint(
            "authority_rank IS NULL OR authority_rank >= 0",
            name="ck_governed_source_decision_authority_rank",
        ),
        sa.UniqueConstraint(
            "decision_id",
            "observation_id",
            "decision_digest",
            name="uq_governed_source_decision_exact",
        ),
        sa.UniqueConstraint(
            "decision_digest",
            name="uq_governed_source_decision_digest",
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_governed_source_decision_observation_id",
        "governed_source_decision",
        ["observation_id"],
        schema="kc_control",
    )

    op.create_table(
        "governed_retrieval_snapshot",
        sa.Column("snapshot_digest", sa.String(length=71), primary_key=True),
        sa.Column("contract_version", sa.String(length=64), nullable=False),
        sa.Column("selection_policy_id", sa.String(length=128), nullable=False),
        sa.Column("predecessor_snapshot_digest", sa.String(length=71), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["predecessor_snapshot_digest"],
            ["kc_control.governed_retrieval_snapshot.snapshot_digest"],
        ),
        schema="kc_control",
    )
    op.create_index(
        "ix_governed_retrieval_snapshot_predecessor_snapshot_digest",
        "governed_retrieval_snapshot",
        ["predecessor_snapshot_digest"],
        schema="kc_control",
    )

    op.create_table(
        "governed_snapshot_member",
        sa.Column("snapshot_digest", sa.String(length=71), primary_key=True),
        sa.Column("source_identity_digest", sa.String(length=71), primary_key=True),
        sa.Column("observation_id", sa.Uuid(), primary_key=True),
        sa.Column("resource_ref", sa.Uuid(), nullable=False),
        sa.Column("resource_version_ref", sa.Uuid(), nullable=False),
        sa.Column("observation_digest", sa.String(length=71), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("decision_digest", sa.String(length=71), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_digest"],
            ["kc_control.governed_retrieval_snapshot.snapshot_digest"],
        ),
        sa.ForeignKeyConstraint(
            ["source_identity_digest", "resource_ref"],
            [
                "kc_control.governed_source_binding.source_identity_digest",
                "kc_control.governed_source_binding.resource_ref",
            ],
            name="fk_governed_snapshot_member_binding",
        ),
        sa.ForeignKeyConstraint(
            [
                "observation_id",
                "source_identity_digest",
                "resource_version_ref",
                "observation_digest",
            ],
            [
                "kc_control.governed_source_observation.observation_id",
                "kc_control.governed_source_observation.source_identity_digest",
                "kc_control.governed_source_observation.resource_version_ref",
                "kc_control.governed_source_observation.observation_digest",
            ],
            name="fk_governed_snapshot_member_observation",
        ),
        sa.ForeignKeyConstraint(
            ["decision_id", "observation_id", "decision_digest"],
            [
                "kc_control.governed_source_decision.decision_id",
                "kc_control.governed_source_decision.observation_id",
                "kc_control.governed_source_decision.decision_digest",
            ],
            name="fk_governed_snapshot_member_decision",
        ),
        schema="kc_control",
    )

    op.create_table(
        "governed_snapshot_project",
        sa.Column("snapshot_digest", sa.String(length=71), primary_key=True),
        sa.Column("source_identity_digest", sa.String(length=71), primary_key=True),
        sa.Column("observation_id", sa.Uuid(), primary_key=True),
        sa.Column("project_key", sa.String(length=255), primary_key=True),
        sa.ForeignKeyConstraint(
            ["snapshot_digest", "source_identity_digest", "observation_id"],
            [
                "kc_control.governed_snapshot_member.snapshot_digest",
                "kc_control.governed_snapshot_member.source_identity_digest",
                "kc_control.governed_snapshot_member.observation_id",
            ],
            name="fk_governed_snapshot_project_member",
        ),
        schema="kc_control",
    )

    op.create_table(
        "governed_snapshot_exclusion",
        sa.Column("snapshot_digest", sa.String(length=71), primary_key=True),
        sa.Column("exclusion_ordinal", sa.Integer(), primary_key=True),
        sa.Column("source_identity_digest", sa.String(length=71), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=True),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_digest"],
            ["kc_control.governed_retrieval_snapshot.snapshot_digest"],
        ),
        sa.ForeignKeyConstraint(
            ["source_identity_digest"],
            ["kc_control.governed_source_binding.source_identity_digest"],
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["kc_control.governed_source_observation.observation_id"],
        ),
        schema="kc_control",
    )

    op.create_table(
        "legacy_repository_observation_map",
        sa.Column("legacy_observation_id", sa.Uuid(), primary_key=True),
        sa.Column("generic_observation_id", sa.Uuid(), nullable=False),
        sa.Column("source_identity_digest", sa.String(length=71), nullable=False),
        sa.Column("capture_evidence_digest", sa.String(length=71), nullable=False),
        sa.Column("mapping_version", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["legacy_observation_id"],
            ["kc_control.repository_source_observation.observation_id"],
        ),
        sa.ForeignKeyConstraint(
            ["generic_observation_id"],
            ["kc_control.governed_source_observation.observation_id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_identity_digest"],
            ["kc_control.governed_source_binding.source_identity_digest"],
        ),
        sa.UniqueConstraint(
            "generic_observation_id",
            name="uq_legacy_repository_observation_map_generic",
        ),
        schema="kc_control",
    )

    op.create_table(
        "legacy_repository_decision_map",
        sa.Column("governing_manifest_digest", sa.String(length=64), primary_key=True),
        sa.Column("legacy_observation_id", sa.Uuid(), primary_key=True),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("selection_role", sa.String(length=32), nullable=False),
        sa.Column("mapping_version", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["governing_manifest_digest"],
            ["kc_control.repository_import_receipt.manifest_digest"],
        ),
        sa.ForeignKeyConstraint(
            ["legacy_observation_id"],
            ["kc_control.repository_source_observation.observation_id"],
        ),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["kc_control.governed_source_decision.decision_id"],
        ),
        sa.CheckConstraint(
            "selection_role IN ('current','prior_version','retirement_retain')",
            name="ck_legacy_repository_decision_map_role",
        ),
        sa.UniqueConstraint(
            "decision_id",
            name="uq_legacy_repository_decision_map_decision",
        ),
        schema="kc_control",
    )

    op.create_table(
        "legacy_repository_snapshot_map",
        sa.Column("governing_manifest_digest", sa.String(length=64), primary_key=True),
        sa.Column("snapshot_digest", sa.String(length=71), nullable=False),
        sa.Column("mapping_version", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["governing_manifest_digest"],
            ["kc_control.repository_import_receipt.manifest_digest"],
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_digest"],
            ["kc_control.governed_retrieval_snapshot.snapshot_digest"],
        ),
        sa.UniqueConstraint(
            "snapshot_digest",
            name="uq_legacy_repository_snapshot_map_snapshot",
        ),
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_table("legacy_repository_snapshot_map", schema="kc_control")
    op.drop_table("legacy_repository_decision_map", schema="kc_control")
    op.drop_table("legacy_repository_observation_map", schema="kc_control")
    op.drop_table("governed_snapshot_exclusion", schema="kc_control")
    op.drop_table("governed_snapshot_project", schema="kc_control")
    op.drop_table("governed_snapshot_member", schema="kc_control")
    op.drop_index(
        "ix_governed_retrieval_snapshot_predecessor_snapshot_digest",
        table_name="governed_retrieval_snapshot",
        schema="kc_control",
    )
    op.drop_table("governed_retrieval_snapshot", schema="kc_control")
    op.drop_index(
        "ix_governed_source_decision_observation_id",
        table_name="governed_source_decision",
        schema="kc_control",
    )
    op.drop_table("governed_source_decision", schema="kc_control")
    op.drop_table("governed_source_evidence", schema="kc_control")
    op.drop_index(
        "ix_governed_source_observation_resource_version_ref",
        table_name="governed_source_observation",
        schema="kc_control",
    )
    op.drop_index(
        "ix_governed_source_observation_source_identity_digest",
        table_name="governed_source_observation",
        schema="kc_control",
    )
    op.drop_table("governed_source_observation", schema="kc_control")
    op.drop_index(
        "ix_governed_source_binding_resource_ref",
        table_name="governed_source_binding",
        schema="kc_control",
    )
    op.drop_table("governed_source_binding", schema="kc_control")
