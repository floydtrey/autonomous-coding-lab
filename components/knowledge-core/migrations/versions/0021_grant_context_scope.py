"""Bind exact resource grants to optional request context scopes.

Revision ID: 0021_grant_context_scope
Revises: 0020_authorization_model
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0021_grant_context_scope"
down_revision = "0020_authorization_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "authorization_grant",
        sa.Column("context_scope_ref", sa.Uuid(), nullable=True),
        schema="kc_control",
    )
    op.create_foreign_key(
        "fk_authorization_grant_context_scope",
        "authorization_grant",
        "auth_scope",
        ["context_scope_ref"],
        ["scope_ref"],
        source_schema="kc_control",
        referent_schema="kc_control",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_authorization_grant_context_scope",
        "authorization_grant",
        schema="kc_control",
        type_="foreignkey",
    )
    op.drop_column(
        "authorization_grant",
        "context_scope_ref",
        schema="kc_control",
    )
