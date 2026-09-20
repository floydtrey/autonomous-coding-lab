from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.control_models import KC_CONTROL_SCHEMA
from knowledge_core.storage.models import Base, KC_SCHEMA


class AuthorizationScopeRecord(Base):
    __tablename__ = "auth_scope"
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('project','directory','category','application','other')",
            name="ck_auth_scope_type",
        ),
        CheckConstraint(
            "lifecycle_state IN ('active','completed','failed','archived')",
            name="ck_auth_scope_lifecycle",
        ),
        UniqueConstraint("scope_type", "scope_key", name="uq_auth_scope_type_key"),
        {"schema": KC_CONTROL_SCHEMA},
    )

    scope_ref: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_scope_ref: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.auth_scope.scope_ref"),
        nullable=True,
        index=True,
    )
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by_principal_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal.principal_ref"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PrincipalGroupRecord(Base):
    __tablename__ = "principal_group"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','disabled')",
            name="ck_principal_group_status",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    group_ref: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    group_code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by_principal_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal.principal_ref"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GroupMembershipRecord(Base):
    __tablename__ = "group_membership"
    __table_args__ = (
        Index(
            "ix_group_membership_principal_group",
            "principal_ref",
            "group_ref",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    membership_ref: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    group_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal_group.group_ref"),
        nullable=False,
    )
    principal_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal.principal_ref"),
        nullable=False,
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_principal_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal.principal_ref"),
        nullable=False,
    )


class AuthorizationGrantRecord(Base):
    __tablename__ = "authorization_grant"
    __table_args__ = (
        CheckConstraint(
            "subject_type IN ('principal','group')",
            name="ck_authorization_grant_subject_type",
        ),
        CheckConstraint(
            "effect IN ('allow','deny')",
            name="ck_authorization_grant_effect",
        ),
        CheckConstraint(
            "target_type IN ('global','scope','resource')",
            name="ck_authorization_grant_target_type",
        ),
        CheckConstraint(
            "("
            "(subject_type = 'principal' AND principal_ref IS NOT NULL AND group_ref IS NULL)"
            " OR "
            "(subject_type = 'group' AND principal_ref IS NULL AND group_ref IS NOT NULL)"
            ")",
            name="ck_authorization_grant_subject_shape",
        ),
        CheckConstraint(
            "("
            "(target_type = 'global' AND scope_ref IS NULL AND resource_ref IS NULL)"
            " OR "
            "(target_type = 'scope' AND scope_ref IS NOT NULL AND resource_ref IS NULL)"
            " OR "
            "(target_type = 'resource' AND scope_ref IS NULL AND resource_ref IS NOT NULL)"
            ")",
            name="ck_authorization_grant_target_shape",
        ),
        Index(
            "ix_authorization_grant_principal_operation",
            "principal_ref",
            "operation",
        ),
        Index(
            "ix_authorization_grant_group_operation",
            "group_ref",
            "operation",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    grant_ref: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    principal_ref: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal.principal_ref"),
        nullable=True,
    )
    group_ref: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal_group.group_ref"),
        nullable=True,
    )
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    effect: Mapped[str] = mapped_column(String(16), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_ref: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.auth_scope.scope_ref"),
        nullable=True,
    )
    resource_ref: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_SCHEMA}.resource.ref_id"),
        nullable=True,
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_principal_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal.principal_ref"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class ResourceAccessPolicyRecord(Base):
    __tablename__ = "resource_access_policy"
    __table_args__ = (
        CheckConstraint(
            "visibility IN ('public','personal','scoped','private')",
            name="ck_resource_access_visibility",
        ),
        CheckConstraint(
            "sensitivity IN ('normal','protected','credential','financial')",
            name="ck_resource_access_sensitivity",
        ),
        Index(
            "ix_resource_access_policy_resource_created",
            "resource_ref",
            "created_at",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    policy_ref: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    resource_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_SCHEMA}.resource.ref_id"),
        nullable=False,
    )
    owner_principal_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal.principal_ref"),
        nullable=False,
    )
    origin_principal_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal.principal_ref"),
        nullable=False,
    )
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False)
    classification_locked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by_principal_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal.principal_ref"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_policy_ref: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.resource_access_policy.policy_ref"),
        nullable=True,
    )


class CurrentResourceAccessPolicyRecord(Base):
    __tablename__ = "current_resource_access_policy"
    __table_args__ = ({"schema": KC_CONTROL_SCHEMA},)

    resource_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_SCHEMA}.resource.ref_id"),
        primary_key=True,
    )
    policy_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.resource_access_policy.policy_ref"),
        nullable=False,
        unique=True,
    )


class ResourceAccessScopeRecord(Base):
    __tablename__ = "resource_access_scope"
    __table_args__ = ({"schema": KC_CONTROL_SCHEMA},)

    policy_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.resource_access_policy.policy_ref"),
        primary_key=True,
    )
    scope_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.auth_scope.scope_ref"),
        primary_key=True,
    )
