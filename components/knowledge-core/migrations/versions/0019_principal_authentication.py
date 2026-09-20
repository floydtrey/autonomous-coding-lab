"""Durable principal identity and service-credential authentication.

Revision ID: 0019_principal_auth
Revises: 0018_memory_candidate
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0019_principal_auth"
down_revision = "0018_memory_candidate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "principal",
        sa.Column("principal_ref", sa.Uuid(), nullable=False),
        sa.Column("principal_code", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("principal_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "principal_type IN ('owner','human','service','ai')",
            name="ck_principal_type",
        ),
        sa.CheckConstraint(
            "status IN ('active','disabled')",
            name="ck_principal_status",
        ),
        sa.PrimaryKeyConstraint("principal_ref"),
        sa.UniqueConstraint("principal_code", name="uq_principal_code"),
        schema="kc_control",
    )

    op.create_table(
        "service_credential",
        sa.Column("credential_ref", sa.Uuid(), nullable=False),
        sa.Column("principal_ref", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("secret_hash_algo", sa.String(length=32), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active','revoked')",
            name="ck_service_credential_status",
        ),
        sa.CheckConstraint(
            "secret_hash_algo IN ('sha256-v1')",
            name="ck_service_credential_hash_algo",
        ),
        sa.ForeignKeyConstraint(
            ["principal_ref"],
            ["kc_control.principal.principal_ref"],
            name="fk_service_credential_principal",
        ),
        sa.PrimaryKeyConstraint("credential_ref"),
        schema="kc_control",
    )
    op.create_index(
        "ix_service_credential_principal_status",
        "service_credential",
        ["principal_ref", "status"],
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_service_credential_principal_status",
        table_name="service_credential",
        schema="kc_control",
    )
    op.drop_table("service_credential", schema="kc_control")
    op.drop_table("principal", schema="kc_control")
