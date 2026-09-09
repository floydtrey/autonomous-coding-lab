"""Task 1 canonical foundation and assertion lifecycle.

Revision ID: 0001_task1
Revises:
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_task1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS kc")

    op.create_table(
        "revision",
        sa.Column("revision_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("operation_id", sa.Uuid(), nullable=True, unique=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_revision", sa.String(length=64), nullable=False),
        sa.Column("authority_decision", sa.Text(), nullable=True),
        schema="kc",
    )
    op.create_table(
        "knowledge_ref",
        sa.Column("ref_id", sa.Uuid(), primary_key=True),
        sa.Column("ref_kind", sa.String(length=64), nullable=False),
        sa.Column(
            "created_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "payload_state",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        schema="kc",
    )
    op.create_table(
        "semantic_profile",
        sa.Column(
            "ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            primary_key=True,
        ),
        sa.Column("stable_name", sa.String(length=128), nullable=False, unique=True),
        sa.Column(
            "created_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        schema="kc",
    )
    op.create_table(
        "semantic_profile_revision",
        sa.Column(
            "ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "profile_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_profile.ref_id"),
            nullable=False,
        ),
        sa.Column("version_label", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active-capable','deprecated','retired-for-new-use')",
            name="ck_semantic_profile_revision_status",
        ),
        schema="kc",
    )
    op.create_table(
        "semantic_kind",
        sa.Column(
            "ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "profile_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_profile.ref_id"),
            nullable=False,
        ),
        sa.Column("stable_name", sa.String(length=128), nullable=False),
        sa.Column(
            "created_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        schema="kc",
    )
    op.create_table(
        "semantic_kind_revision",
        sa.Column(
            "ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "kind_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_kind.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "profile_revision_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_profile_revision.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "created_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        schema="kc",
    )
    op.create_table(
        "semantic_predicate",
        sa.Column(
            "ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "profile_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_profile.ref_id"),
            nullable=False,
        ),
        sa.Column("stable_name", sa.String(length=128), nullable=False),
        sa.Column(
            "created_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "profile_ref_id",
            "stable_name",
            name="uq_semantic_predicate_profile_stable_name",
        ),
        schema="kc",
    )
    op.create_table(
        "semantic_predicate_revision",
        sa.Column(
            "ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "predicate_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_predicate.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "profile_revision_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_profile_revision.ref_id"),
            nullable=False,
        ),
        sa.Column("value_shape", sa.String(length=32), nullable=False),
        sa.Column(
            "created_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "value_shape IN ('scalar','reference')",
            name="ck_semantic_predicate_revision_value_shape",
        ),
        schema="kc",
    )
    op.create_table(
        "entity",
        sa.Column(
            "ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "kind_revision_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_kind_revision.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "created_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        schema="kc",
    )
    op.create_table(
        "occurrence",
        sa.Column(
            "ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "kind_revision_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_kind_revision.ref_id"),
            nullable=False,
        ),
        sa.Column("happened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        schema="kc",
    )
    op.create_table(
        "assertion",
        sa.Column(
            "ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            primary_key=True,
        ),
        sa.Column(
            "subject_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "predicate_revision_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_predicate_revision.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "profile_revision_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.semantic_profile_revision.ref_id"),
            nullable=False,
        ),
        sa.Column("value_state", sa.String(length=32), nullable=False),
        sa.Column("epistemic_basis", sa.String(length=32), nullable=False),
        sa.Column(
            "created_revision_id",
            sa.BigInteger(),
            sa.ForeignKey("kc.revision.revision_id"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "value_state IN ('present','explicit_negative','known_no_value',"
            "'some_value_unknown','not_established')",
            name="ck_assertion_value_state",
        ),
        sa.CheckConstraint(
            "epistemic_basis IN ('stated','observed','imported','configured',"
            "'inferred','derived','verified','other-governed')",
            name="ck_assertion_epistemic_basis",
        ),
        schema="kc",
    )
    op.create_table(
        "assertion_value",
        sa.Column(
            "assertion_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.assertion.ref_id"),
            primary_key=True,
        ),
        sa.Column("value_kind", sa.String(length=32), nullable=False),
        sa.Column(
            "reference_value",
            sa.Uuid(),
            sa.ForeignKey("kc.knowledge_ref.ref_id"),
            nullable=True,
        ),
        sa.Column("text_value", sa.Text(), nullable=True),
        sa.Column("numeric_value", sa.Numeric(), nullable=True),
        sa.Column("boolean_value", sa.Boolean(), nullable=True),
        sa.Column("date_value", sa.Date(), nullable=True),
        sa.Column("timestamp_value", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "("
            "(value_kind='reference' AND reference_value IS NOT NULL AND text_value IS NULL "
            "AND numeric_value IS NULL AND boolean_value IS NULL AND date_value IS NULL "
            "AND timestamp_value IS NULL) OR "
            "(value_kind='text' AND reference_value IS NULL AND text_value IS NOT NULL "
            "AND numeric_value IS NULL AND boolean_value IS NULL AND date_value IS NULL "
            "AND timestamp_value IS NULL) OR "
            "(value_kind='numeric' AND reference_value IS NULL AND text_value IS NULL "
            "AND numeric_value IS NOT NULL AND boolean_value IS NULL AND date_value IS NULL "
            "AND timestamp_value IS NULL) OR "
            "(value_kind='boolean' AND reference_value IS NULL AND text_value IS NULL "
            "AND numeric_value IS NULL AND boolean_value IS NOT NULL AND date_value IS NULL "
            "AND timestamp_value IS NULL) OR "
            "(value_kind='date' AND reference_value IS NULL AND text_value IS NULL "
            "AND numeric_value IS NULL AND boolean_value IS NULL AND date_value IS NOT NULL "
            "AND timestamp_value IS NULL) OR "
            "(value_kind='timestamp' AND reference_value IS NULL AND text_value IS NULL "
            "AND numeric_value IS NULL AND boolean_value IS NULL AND date_value IS NULL "
            "AND timestamp_value IS NOT NULL)"
            ")",
            name="ck_assertion_value_exactly_one_typed_value",
        ),
        schema="kc",
    )
    op.create_table(
        "assertion_transition",
        sa.Column(
            "occurrence_ref_id",
            sa.Uuid(),
            sa.ForeignKey("kc.occurrence.ref_id"),
            primary_key=True,
        ),
        sa.Column("transition_type", sa.String(length=32), nullable=False),
        sa.Column(
            "source_assertion_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.assertion.ref_id"),
            nullable=False,
        ),
        sa.Column(
            "replacement_assertion_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.assertion.ref_id"),
            nullable=True,
        ),
        sa.Column(
            "reverses_transition_ref",
            sa.Uuid(),
            sa.ForeignKey("kc.assertion_transition.occurrence_ref_id"),
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
            "transition_type IN ('supersedes','corrects','invalidates','restores')",
            name="ck_assertion_transition_type",
        ),
        schema="kc",
    )


def downgrade() -> None:
    for table in (
        "assertion_transition",
        "assertion_value",
        "assertion",
        "occurrence",
        "entity",
        "semantic_predicate_revision",
        "semantic_predicate",
        "semantic_kind_revision",
        "semantic_kind",
        "semantic_profile_revision",
        "semantic_profile",
        "knowledge_ref",
        "revision",
    ):
        op.drop_table(table, schema="kc")
    op.execute("DROP SCHEMA IF EXISTS kc")
