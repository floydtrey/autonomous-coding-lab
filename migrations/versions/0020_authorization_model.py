"""Canonical scopes, grants, groups, and resource access policy.

Revision ID: 0020_authorization_model
Revises: 0019_principal_auth
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0020_authorization_model"
down_revision = "0019_principal_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_scope",
        sa.Column("scope_ref", sa.Uuid(), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_key", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("parent_scope_ref", sa.Uuid(), nullable=True),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("created_by_principal_ref", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scope_type IN ('project','directory','category','application','other')",
            name="ck_auth_scope_type",
        ),
        sa.CheckConstraint(
            "lifecycle_state IN ('active','completed','failed','archived')",
            name="ck_auth_scope_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["parent_scope_ref"],
            ["kc_control.auth_scope.scope_ref"],
            name="fk_auth_scope_parent",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_principal_ref"],
            ["kc_control.principal.principal_ref"],
            name="fk_auth_scope_creator",
        ),
        sa.PrimaryKeyConstraint("scope_ref"),
        sa.UniqueConstraint("scope_type", "scope_key", name="uq_auth_scope_type_key"),
        schema="kc_control",
    )
    op.create_index(
        "ix_auth_scope_parent",
        "auth_scope",
        ["parent_scope_ref"],
        schema="kc_control",
    )

    op.create_table(
        "principal_group",
        sa.Column("group_ref", sa.Uuid(), nullable=False),
        sa.Column("group_code", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by_principal_ref", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active','disabled')",
            name="ck_principal_group_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_principal_ref"],
            ["kc_control.principal.principal_ref"],
            name="fk_principal_group_creator",
        ),
        sa.PrimaryKeyConstraint("group_ref"),
        sa.UniqueConstraint("group_code", name="uq_principal_group_code"),
        schema="kc_control",
    )

    op.create_table(
        "group_membership",
        sa.Column("membership_ref", sa.Uuid(), nullable=False),
        sa.Column("group_ref", sa.Uuid(), nullable=False),
        sa.Column("principal_ref", sa.Uuid(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_principal_ref", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_ref"],
            ["kc_control.principal_group.group_ref"],
            name="fk_group_membership_group",
        ),
        sa.ForeignKeyConstraint(
            ["principal_ref"],
            ["kc_control.principal.principal_ref"],
            name="fk_group_membership_principal",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_principal_ref"],
            ["kc_control.principal.principal_ref"],
            name="fk_group_membership_creator",
        ),
        sa.PrimaryKeyConstraint("membership_ref"),
        schema="kc_control",
    )
    op.create_index(
        "ix_group_membership_principal_group",
        "group_membership",
        ["principal_ref", "group_ref"],
        schema="kc_control",
    )

    op.create_table(
        "authorization_grant",
        sa.Column("grant_ref", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("principal_ref", sa.Uuid(), nullable=True),
        sa.Column("group_ref", sa.Uuid(), nullable=True),
        sa.Column("operation", sa.String(length=128), nullable=False),
        sa.Column("effect", sa.String(length=16), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("scope_ref", sa.Uuid(), nullable=True),
        sa.Column("resource_ref", sa.Uuid(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_principal_ref", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "subject_type IN ('principal','group')",
            name="ck_authorization_grant_subject_type",
        ),
        sa.CheckConstraint(
            "effect IN ('allow','deny')",
            name="ck_authorization_grant_effect",
        ),
        sa.CheckConstraint(
            "target_type IN ('global','scope','resource')",
            name="ck_authorization_grant_target_type",
        ),
        sa.CheckConstraint(
            "((subject_type = 'principal' AND principal_ref IS NOT NULL AND group_ref IS NULL)"
            " OR (subject_type = 'group' AND principal_ref IS NULL AND group_ref IS NOT NULL))",
            name="ck_authorization_grant_subject_shape",
        ),
        sa.CheckConstraint(
            "((target_type = 'global' AND scope_ref IS NULL AND resource_ref IS NULL)"
            " OR (target_type = 'scope' AND scope_ref IS NOT NULL AND resource_ref IS NULL)"
            " OR (target_type = 'resource' AND scope_ref IS NULL AND resource_ref IS NOT NULL))",
            name="ck_authorization_grant_target_shape",
        ),
        sa.ForeignKeyConstraint(
            ["principal_ref"],
            ["kc_control.principal.principal_ref"],
            name="fk_authorization_grant_principal",
        ),
        sa.ForeignKeyConstraint(
            ["group_ref"],
            ["kc_control.principal_group.group_ref"],
            name="fk_authorization_grant_group",
        ),
        sa.ForeignKeyConstraint(
            ["scope_ref"],
            ["kc_control.auth_scope.scope_ref"],
            name="fk_authorization_grant_scope",
        ),
        sa.ForeignKeyConstraint(
            ["resource_ref"],
            ["kc.resource.ref_id"],
            name="fk_authorization_grant_resource",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_principal_ref"],
            ["kc_control.principal.principal_ref"],
            name="fk_authorization_grant_creator",
        ),
        sa.PrimaryKeyConstraint("grant_ref"),
        schema="kc_control",
    )
    op.create_index(
        "ix_authorization_grant_principal_operation",
        "authorization_grant",
        ["principal_ref", "operation"],
        schema="kc_control",
    )
    op.create_index(
        "ix_authorization_grant_group_operation",
        "authorization_grant",
        ["group_ref", "operation"],
        schema="kc_control",
    )

    op.create_table(
        "resource_access_policy",
        sa.Column("policy_ref", sa.Uuid(), nullable=False),
        sa.Column("resource_ref", sa.Uuid(), nullable=False),
        sa.Column("owner_principal_ref", sa.Uuid(), nullable=False),
        sa.Column("origin_principal_ref", sa.Uuid(), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("sensitivity", sa.String(length=32), nullable=False),
        sa.Column("classification_locked", sa.Boolean(), nullable=False),
        sa.Column("created_by_principal_ref", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_policy_ref", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "visibility IN ('public','personal','scoped','private')",
            name="ck_resource_access_visibility",
        ),
        sa.CheckConstraint(
            "sensitivity IN ('normal','protected','credential','financial')",
            name="ck_resource_access_sensitivity",
        ),
        sa.ForeignKeyConstraint(
            ["resource_ref"],
            ["kc.resource.ref_id"],
            name="fk_resource_access_policy_resource",
        ),
        sa.ForeignKeyConstraint(
            ["owner_principal_ref"],
            ["kc_control.principal.principal_ref"],
            name="fk_resource_access_policy_owner",
        ),
        sa.ForeignKeyConstraint(
            ["origin_principal_ref"],
            ["kc_control.principal.principal_ref"],
            name="fk_resource_access_policy_origin",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_principal_ref"],
            ["kc_control.principal.principal_ref"],
            name="fk_resource_access_policy_creator",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_policy_ref"],
            ["kc_control.resource_access_policy.policy_ref"],
            name="fk_resource_access_policy_supersedes",
        ),
        sa.PrimaryKeyConstraint("policy_ref"),
        schema="kc_control",
    )
    op.create_index(
        "ix_resource_access_policy_resource_created",
        "resource_access_policy",
        ["resource_ref", "created_at"],
        schema="kc_control",
    )

    op.create_table(
        "current_resource_access_policy",
        sa.Column("resource_ref", sa.Uuid(), nullable=False),
        sa.Column("policy_ref", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["resource_ref"],
            ["kc.resource.ref_id"],
            name="fk_current_resource_access_resource",
        ),
        sa.ForeignKeyConstraint(
            ["policy_ref"],
            ["kc_control.resource_access_policy.policy_ref"],
            name="fk_current_resource_access_policy",
        ),
        sa.PrimaryKeyConstraint("resource_ref"),
        sa.UniqueConstraint("policy_ref", name="uq_current_resource_access_policy"),
        schema="kc_control",
    )

    op.create_table(
        "resource_access_scope",
        sa.Column("policy_ref", sa.Uuid(), nullable=False),
        sa.Column("scope_ref", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["policy_ref"],
            ["kc_control.resource_access_policy.policy_ref"],
            name="fk_resource_access_scope_policy",
        ),
        sa.ForeignKeyConstraint(
            ["scope_ref"],
            ["kc_control.auth_scope.scope_ref"],
            name="fk_resource_access_scope_scope",
        ),
        sa.PrimaryKeyConstraint("policy_ref", "scope_ref"),
        schema="kc_control",
    )


def downgrade() -> None:
    op.drop_table("resource_access_scope", schema="kc_control")
    op.drop_table("current_resource_access_policy", schema="kc_control")
    op.drop_index(
        "ix_resource_access_policy_resource_created",
        table_name="resource_access_policy",
        schema="kc_control",
    )
    op.drop_table("resource_access_policy", schema="kc_control")
    op.drop_index(
        "ix_authorization_grant_group_operation",
        table_name="authorization_grant",
        schema="kc_control",
    )
    op.drop_index(
        "ix_authorization_grant_principal_operation",
        table_name="authorization_grant",
        schema="kc_control",
    )
    op.drop_table("authorization_grant", schema="kc_control")
    op.drop_index(
        "ix_group_membership_principal_group",
        table_name="group_membership",
        schema="kc_control",
    )
    op.drop_table("group_membership", schema="kc_control")
    op.drop_table("principal_group", schema="kc_control")
    op.drop_index(
        "ix_auth_scope_parent",
        table_name="auth_scope",
        schema="kc_control",
    )
    op.drop_table("auth_scope", schema="kc_control")
