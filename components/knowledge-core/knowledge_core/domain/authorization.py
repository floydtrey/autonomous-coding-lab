from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ScopeType(StrEnum):
    PROJECT = "project"
    DIRECTORY = "directory"
    CATEGORY = "category"
    APPLICATION = "application"
    OTHER = "other"


class ScopeLifecycleState(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class PrincipalGroupStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class GrantEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class GrantSubjectType(StrEnum):
    PRINCIPAL = "principal"
    GROUP = "group"


class GrantTargetType(StrEnum):
    GLOBAL = "global"
    SCOPE = "scope"
    RESOURCE = "resource"


class VisibilityClass(StrEnum):
    PUBLIC = "public"
    PERSONAL = "personal"
    SCOPED = "scoped"
    PRIVATE = "private"


class SensitivityClass(StrEnum):
    NORMAL = "normal"
    PROTECTED = "protected"
    CREDENTIAL = "credential"
    FINANCIAL = "financial"


class KCOperation(StrEnum):
    STATUS = "kc.status"
    SEARCH = "kc.search"
    GET_SOURCE = "kc.get_source"
    STORE = "kc.store"
    MEMORY_PROPOSE = "kc.memory_propose"
    RESTRICT = "kc.restrict"
    DELETE = "kc.delete"
    ADMIN = "kc.admin"


@dataclass(frozen=True)
class ScopeSnapshot:
    scope_ref: UUID
    scope_type: ScopeType
    scope_key: str
    display_name: str
    parent_scope_ref: UUID | None
    lifecycle_state: ScopeLifecycleState
    created_by_principal_ref: UUID
    created_at: datetime


@dataclass(frozen=True)
class AuthorizationGrantSnapshot:
    grant_ref: UUID
    subject_type: GrantSubjectType
    principal_ref: UUID | None
    group_ref: UUID | None
    operation: str
    effect: GrantEffect
    target_type: GrantTargetType
    scope_ref: UUID | None
    resource_ref: UUID | None
    valid_from: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    created_by_principal_ref: UUID
    reason: str


@dataclass(frozen=True)
class ResourceAccessPolicySnapshot:
    policy_ref: UUID
    resource_ref: UUID
    owner_principal_ref: UUID
    origin_principal_ref: UUID
    visibility: VisibilityClass
    sensitivity: SensitivityClass
    classification_locked: bool
    scope_refs: tuple[UUID, ...]
    created_by_principal_ref: UUID
    created_at: datetime
    supersedes_policy_ref: UUID | None


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason_code: str
    matched_grant_refs: tuple[UUID, ...] = ()
