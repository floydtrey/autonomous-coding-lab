from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Callable, Iterable
from uuid import UUID, uuid4

from sqlalchemy import and_, exists, false, not_, or_, select
from sqlalchemy.orm import Session

from knowledge_core.domain.authorization import (
    AuthorizationDecision,
    AuthorizationGrantSnapshot,
    GrantEffect,
    GrantSubjectType,
    GrantTargetType,
    KCOperation,
    PrincipalGroupStatus,
    ResourceAccessPolicySnapshot,
    ScopeLifecycleState,
    ScopeSnapshot,
    ScopeType,
    SensitivityClass,
    VisibilityClass,
)
from knowledge_core.domain.principals import PrincipalStatus, PrincipalType
from knowledge_core.storage.authorization_models import (
    AuthorizationGrantRecord,
    AuthorizationScopeRecord,
    CurrentResourceAccessPolicyRecord,
    GroupMembershipRecord,
    PrincipalGroupRecord,
    ResourceAccessPolicyRecord,
    ResourceAccessScopeRecord,
)
from knowledge_core.storage.principal_models import PrincipalRecord
from knowledge_core.storage.resource_models import Resource


_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{0,127}$")


class AuthorizationConflictError(RuntimeError):
    pass


class AuthorizationDeniedError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _scope_snapshot(row: AuthorizationScopeRecord) -> ScopeSnapshot:
    return ScopeSnapshot(
        scope_ref=row.scope_ref,
        scope_type=ScopeType(row.scope_type),
        scope_key=row.scope_key,
        display_name=row.display_name,
        parent_scope_ref=row.parent_scope_ref,
        lifecycle_state=ScopeLifecycleState(row.lifecycle_state),
        created_by_principal_ref=row.created_by_principal_ref,
        created_at=_as_utc(row.created_at),
    )


def _grant_snapshot(row: AuthorizationGrantRecord) -> AuthorizationGrantSnapshot:
    return AuthorizationGrantSnapshot(
        grant_ref=row.grant_ref,
        subject_type=GrantSubjectType(row.subject_type),
        principal_ref=row.principal_ref,
        group_ref=row.group_ref,
        operation=row.operation,
        effect=GrantEffect(row.effect),
        target_type=GrantTargetType(row.target_type),
        scope_ref=row.scope_ref,
        resource_ref=row.resource_ref,
        context_scope_ref=row.context_scope_ref,
        valid_from=_as_utc(row.valid_from),
        expires_at=_as_utc(row.expires_at) if row.expires_at is not None else None,
        revoked_at=_as_utc(row.revoked_at) if row.revoked_at is not None else None,
        created_by_principal_ref=row.created_by_principal_ref,
        reason=row.reason,
    )


class AuthorizationKernel:
    """Canonical KC-B authorization model.

    Global grants are operation capabilities. They permit a principal to invoke an
    operation but do not disclose non-public resources by themselves. Resource
    visibility/sensitivity and scoped/resource grants are evaluated separately.

    Scope lifecycle is deliberately not an authorization signal. Failed or archived
    projects may be excluded by retrieval relevance policy while remaining
    authorized for deliberate historical inspection.
    """

    def __init__(
        self,
        session: Session,
        *,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.session = session
        self._now = now

    @staticmethod
    def _normalize_code(value: str, field_name: str) -> str:
        normalized = value.strip().upper()
        if not _CODE_PATTERN.fullmatch(normalized):
            raise ValueError(
                f"{field_name} must be 1-128 characters using A-Z, 0-9, '.', '_', ':', or '-'"
            )
        return normalized

    @staticmethod
    def _operation_value(operation: KCOperation | str) -> str:
        value = operation.value if isinstance(operation, KCOperation) else str(operation)
        value = value.strip()
        if not value or len(value) > 128:
            raise ValueError("operation must be non-blank and at most 128 characters")
        return value

    def _principal(self, principal_ref: UUID) -> PrincipalRecord:
        row = self.session.get(PrincipalRecord, principal_ref)
        if row is None:
            raise KeyError(f"unknown principal: {principal_ref}")
        return row

    def _require_active_principal(self, principal_ref: UUID) -> PrincipalRecord:
        row = self._principal(principal_ref)
        if PrincipalStatus(row.status) is not PrincipalStatus.ACTIVE:
            raise AuthorizationDeniedError("principal is not active")
        return row

    def _is_owner(self, principal_ref: UUID) -> bool:
        row = self._principal(principal_ref)
        return (
            PrincipalStatus(row.status) is PrincipalStatus.ACTIVE
            and PrincipalType(row.principal_type) is PrincipalType.OWNER
        )

    def _require_admin(self, principal_ref: UUID) -> None:
        if self._is_owner(principal_ref):
            return
        decision = self.evaluate(
            principal_ref=principal_ref,
            operation=KCOperation.ADMIN,
        )
        if not decision.allowed:
            raise AuthorizationDeniedError("authorization administration is denied")

    def create_scope(
        self,
        *,
        actor_principal_ref: UUID,
        scope_type: ScopeType,
        scope_key: str,
        display_name: str,
        parent_scope_ref: UUID | None = None,
        lifecycle_state: ScopeLifecycleState = ScopeLifecycleState.ACTIVE,
    ) -> ScopeSnapshot:
        self._require_admin(actor_principal_ref)
        key = scope_key.strip()
        display = display_name.strip()
        if not key or len(key) > 255:
            raise ValueError("scope_key must be non-blank and at most 255 characters")
        if not display or len(display) > 255:
            raise ValueError("display_name must be non-blank and at most 255 characters")
        if parent_scope_ref is not None:
            if self.session.get(AuthorizationScopeRecord, parent_scope_ref) is None:
                raise KeyError(f"unknown parent scope: {parent_scope_ref}")

        existing = self.session.scalar(
            select(AuthorizationScopeRecord).where(
                AuthorizationScopeRecord.scope_type == scope_type.value,
                AuthorizationScopeRecord.scope_key == key,
            )
        )
        if existing is not None:
            raise AuthorizationConflictError(
                f"scope already exists: {scope_type.value}:{key}"
            )

        row = AuthorizationScopeRecord(
            scope_ref=uuid4(),
            scope_type=scope_type.value,
            scope_key=key,
            display_name=display,
            parent_scope_ref=parent_scope_ref,
            lifecycle_state=lifecycle_state.value,
            created_by_principal_ref=actor_principal_ref,
            created_at=_as_utc(self._now()),
        )
        self.session.add(row)
        self.session.flush()
        return _scope_snapshot(row)

    def read_scope(self, scope_ref: UUID) -> ScopeSnapshot:
        row = self.session.get(AuthorizationScopeRecord, scope_ref)
        if row is None:
            raise KeyError(f"unknown scope: {scope_ref}")
        return _scope_snapshot(row)

    def project_scope_for(self, scope_ref: UUID) -> ScopeSnapshot:
        current: UUID | None = scope_ref
        seen: set[UUID] = set()
        while current is not None:
            if current in seen:
                raise RuntimeError("authorization scope hierarchy contains a cycle")
            seen.add(current)
            row = self.session.get(AuthorizationScopeRecord, current)
            if row is None:
                raise KeyError(f"unknown scope: {current}")
            if ScopeType(row.scope_type) is ScopeType.PROJECT:
                return _scope_snapshot(row)
            current = row.parent_scope_ref
        raise AuthorizationDeniedError("active scope is not inside a project scope")

    def set_scope_lifecycle(
        self,
        *,
        actor_principal_ref: UUID,
        scope_ref: UUID,
        lifecycle_state: ScopeLifecycleState,
    ) -> ScopeSnapshot:
        self._require_admin(actor_principal_ref)
        row = self.session.get(AuthorizationScopeRecord, scope_ref)
        if row is None:
            raise KeyError(f"unknown scope: {scope_ref}")
        row.lifecycle_state = lifecycle_state.value
        self.session.flush()
        return _scope_snapshot(row)

    def create_group(
        self,
        *,
        actor_principal_ref: UUID,
        group_code: str,
        display_name: str,
    ) -> UUID:
        self._require_admin(actor_principal_ref)
        code = self._normalize_code(group_code, "group_code")
        display = display_name.strip()
        if not display or len(display) > 255:
            raise ValueError("display_name must be non-blank and at most 255 characters")
        existing = self.session.scalar(
            select(PrincipalGroupRecord).where(PrincipalGroupRecord.group_code == code)
        )
        if existing is not None:
            raise AuthorizationConflictError(f"group code already exists: {code}")
        row = PrincipalGroupRecord(
            group_ref=uuid4(),
            group_code=code,
            display_name=display,
            status=PrincipalGroupStatus.ACTIVE.value,
            created_by_principal_ref=actor_principal_ref,
            created_at=_as_utc(self._now()),
        )
        self.session.add(row)
        self.session.flush()
        return row.group_ref

    def add_group_member(
        self,
        *,
        actor_principal_ref: UUID,
        group_ref: UUID,
        principal_ref: UUID,
        valid_from: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> UUID:
        self._require_admin(actor_principal_ref)
        group = self.session.get(PrincipalGroupRecord, group_ref)
        if group is None:
            raise KeyError(f"unknown group: {group_ref}")
        self._require_active_principal(principal_ref)
        start = _as_utc(valid_from or self._now())
        expiry = _as_utc(expires_at) if expires_at is not None else None
        if expiry is not None and expiry <= start:
            raise ValueError("membership expiration must be after valid_from")
        row = GroupMembershipRecord(
            membership_ref=uuid4(),
            group_ref=group_ref,
            principal_ref=principal_ref,
            valid_from=start,
            expires_at=expiry,
            revoked_at=None,
            created_by_principal_ref=actor_principal_ref,
        )
        self.session.add(row)
        self.session.flush()
        return row.membership_ref

    def create_grant(
        self,
        *,
        actor_principal_ref: UUID,
        subject_type: GrantSubjectType,
        operation: KCOperation | str,
        effect: GrantEffect,
        target_type: GrantTargetType,
        principal_ref: UUID | None = None,
        group_ref: UUID | None = None,
        scope_ref: UUID | None = None,
        resource_ref: UUID | None = None,
        context_scope_ref: UUID | None = None,
        valid_from: datetime | None = None,
        expires_at: datetime | None = None,
        reason: str,
    ) -> AuthorizationGrantSnapshot:
        self._require_admin(actor_principal_ref)
        operation_value = self._operation_value(operation)
        reason_value = reason.strip()
        if not reason_value:
            raise ValueError("grant reason must be non-blank")

        if subject_type is GrantSubjectType.PRINCIPAL:
            if principal_ref is None or group_ref is not None:
                raise ValueError("principal grant requires only principal_ref")
            self._require_active_principal(principal_ref)
        else:
            if group_ref is None or principal_ref is not None:
                raise ValueError("group grant requires only group_ref")
            group = self.session.get(PrincipalGroupRecord, group_ref)
            if group is None:
                raise KeyError(f"unknown group: {group_ref}")

        if context_scope_ref is not None:
            if self.session.get(AuthorizationScopeRecord, context_scope_ref) is None:
                raise KeyError(f"unknown context scope: {context_scope_ref}")
            if target_type is not GrantTargetType.RESOURCE:
                raise ValueError("context_scope_ref is supported only for resource grants")

        if target_type is GrantTargetType.GLOBAL:
            if scope_ref is not None or resource_ref is not None:
                raise ValueError("global grant cannot specify scope/resource")
        elif target_type is GrantTargetType.SCOPE:
            if scope_ref is None or resource_ref is not None:
                raise ValueError("scope grant requires only scope_ref")
            if self.session.get(AuthorizationScopeRecord, scope_ref) is None:
                raise KeyError(f"unknown scope: {scope_ref}")
        else:
            if resource_ref is None or scope_ref is not None:
                raise ValueError("resource grant requires only resource_ref")
            if self.session.get(Resource, resource_ref) is None:
                raise KeyError(f"unknown resource: {resource_ref}")

        start = _as_utc(valid_from or self._now())
        expiry = _as_utc(expires_at) if expires_at is not None else None
        if expiry is not None and expiry <= start:
            raise ValueError("grant expiration must be after valid_from")

        row = AuthorizationGrantRecord(
            grant_ref=uuid4(),
            subject_type=subject_type.value,
            principal_ref=principal_ref,
            group_ref=group_ref,
            operation=operation_value,
            effect=effect.value,
            target_type=target_type.value,
            scope_ref=scope_ref,
            resource_ref=resource_ref,
            context_scope_ref=context_scope_ref,
            valid_from=start,
            expires_at=expiry,
            revoked_at=None,
            created_by_principal_ref=actor_principal_ref,
            reason=reason_value,
        )
        self.session.add(row)
        self.session.flush()
        return _grant_snapshot(row)

    def revoke_grant(
        self,
        *,
        actor_principal_ref: UUID,
        grant_ref: UUID,
    ) -> AuthorizationGrantSnapshot:
        self._require_admin(actor_principal_ref)
        row = self.session.get(AuthorizationGrantRecord, grant_ref)
        if row is None:
            raise KeyError(f"unknown authorization grant: {grant_ref}")
        if row.revoked_at is None:
            row.revoked_at = _as_utc(self._now())
            self.session.flush()
        return _grant_snapshot(row)

    def set_resource_access_policy(
        self,
        *,
        actor_principal_ref: UUID,
        resource_ref: UUID,
        owner_principal_ref: UUID,
        origin_principal_ref: UUID,
        visibility: VisibilityClass,
        sensitivity: SensitivityClass,
        scope_refs: Iterable[UUID] = (),
        classification_locked: bool = False,
    ) -> ResourceAccessPolicySnapshot:
        actor = self._require_active_principal(actor_principal_ref)
        self._require_admin(actor_principal_ref)
        if self.session.get(Resource, resource_ref) is None:
            raise KeyError(f"unknown resource: {resource_ref}")
        self._require_active_principal(owner_principal_ref)
        self._require_active_principal(origin_principal_ref)

        normalized_scopes = tuple(sorted(set(scope_refs), key=str))
        for scope_ref in normalized_scopes:
            if self.session.get(AuthorizationScopeRecord, scope_ref) is None:
                raise KeyError(f"unknown scope: {scope_ref}")
        if visibility is VisibilityClass.SCOPED and not normalized_scopes:
            raise ValueError("scoped resource policy requires at least one scope")
        if visibility is VisibilityClass.PUBLIC and sensitivity is not SensitivityClass.NORMAL:
            raise ValueError("non-normal sensitivity cannot be public")

        current = self.session.get(CurrentResourceAccessPolicyRecord, resource_ref)
        supersedes = current.policy_ref if current is not None else None
        if current is not None:
            previous = self.session.get(ResourceAccessPolicyRecord, current.policy_ref)
            if previous is None:
                raise RuntimeError("current resource access policy lost its policy row")
            if previous.classification_locked and PrincipalType(actor.principal_type) is not PrincipalType.OWNER:
                raise AuthorizationDeniedError(
                    "locked resource classification requires owner authority"
                )
        if classification_locked and PrincipalType(actor.principal_type) is not PrincipalType.OWNER:
            raise AuthorizationDeniedError(
                "only an owner principal may lock resource classification"
            )

        row = ResourceAccessPolicyRecord(
            policy_ref=uuid4(),
            resource_ref=resource_ref,
            owner_principal_ref=owner_principal_ref,
            origin_principal_ref=origin_principal_ref,
            visibility=visibility.value,
            sensitivity=sensitivity.value,
            classification_locked=classification_locked,
            created_by_principal_ref=actor_principal_ref,
            created_at=_as_utc(self._now()),
            supersedes_policy_ref=supersedes,
        )
        self.session.add(row)
        self.session.flush()
        for scope_ref in normalized_scopes:
            self.session.add(
                ResourceAccessScopeRecord(
                    policy_ref=row.policy_ref,
                    scope_ref=scope_ref,
                )
            )
        if current is None:
            self.session.add(
                CurrentResourceAccessPolicyRecord(
                    resource_ref=resource_ref,
                    policy_ref=row.policy_ref,
                )
            )
        else:
            current.policy_ref = row.policy_ref
        self.session.flush()
        return self._resource_policy_snapshot(row)

    def set_initial_scoped_policy_for_authorized_store(
        self,
        *,
        actor_principal_ref: UUID,
        resource_ref: UUID,
        scope_ref: UUID,
    ) -> ResourceAccessPolicySnapshot:
        self._require_active_principal(actor_principal_ref)
        if self.session.get(Resource, resource_ref) is None:
            raise KeyError(f"unknown resource: {resource_ref}")
        if self.session.get(AuthorizationScopeRecord, scope_ref) is None:
            raise KeyError(f"unknown scope: {scope_ref}")
        if self.session.get(CurrentResourceAccessPolicyRecord, resource_ref) is not None:
            raise AuthorizationConflictError(
                "authorized store cannot replace an existing resource access policy"
            )

        row = ResourceAccessPolicyRecord(
            policy_ref=uuid4(),
            resource_ref=resource_ref,
            owner_principal_ref=actor_principal_ref,
            origin_principal_ref=actor_principal_ref,
            visibility=VisibilityClass.SCOPED.value,
            sensitivity=SensitivityClass.NORMAL.value,
            classification_locked=False,
            created_by_principal_ref=actor_principal_ref,
            created_at=_as_utc(self._now()),
            supersedes_policy_ref=None,
        )
        self.session.add(row)
        self.session.flush()
        self.session.add(
            ResourceAccessScopeRecord(
                policy_ref=row.policy_ref,
                scope_ref=scope_ref,
            )
        )
        self.session.add(
            CurrentResourceAccessPolicyRecord(
                resource_ref=resource_ref,
                policy_ref=row.policy_ref,
            )
        )
        self.session.flush()
        return self._resource_policy_snapshot(row)

    def _resource_policy_snapshot(
        self,
        row: ResourceAccessPolicyRecord,
    ) -> ResourceAccessPolicySnapshot:
        scope_refs = tuple(
            self.session.scalars(
                select(ResourceAccessScopeRecord.scope_ref)
                .where(ResourceAccessScopeRecord.policy_ref == row.policy_ref)
                .order_by(ResourceAccessScopeRecord.scope_ref)
            ).all()
        )
        return ResourceAccessPolicySnapshot(
            policy_ref=row.policy_ref,
            resource_ref=row.resource_ref,
            owner_principal_ref=row.owner_principal_ref,
            origin_principal_ref=row.origin_principal_ref,
            visibility=VisibilityClass(row.visibility),
            sensitivity=SensitivityClass(row.sensitivity),
            classification_locked=row.classification_locked,
            scope_refs=scope_refs,
            created_by_principal_ref=row.created_by_principal_ref,
            created_at=_as_utc(row.created_at),
            supersedes_policy_ref=row.supersedes_policy_ref,
        )

    def read_current_resource_access_policy(
        self,
        resource_ref: UUID,
    ) -> ResourceAccessPolicySnapshot:
        current = self.session.get(CurrentResourceAccessPolicyRecord, resource_ref)
        if current is None:
            raise KeyError(f"resource has no access policy: {resource_ref}")
        row = self.session.get(ResourceAccessPolicyRecord, current.policy_ref)
        if row is None:
            raise RuntimeError("current resource access policy lost its policy row")
        return self._resource_policy_snapshot(row)

    @staticmethod
    def _temporal_active(
        *,
        valid_from: datetime,
        expires_at: datetime | None,
        revoked_at: datetime | None,
        at: datetime,
    ) -> bool:
        if _as_utc(valid_from) > at:
            return False
        if expires_at is not None and _as_utc(expires_at) <= at:
            return False
        if revoked_at is not None and _as_utc(revoked_at) <= at:
            return False
        return True

    def _active_group_refs(self, principal_ref: UUID, at: datetime) -> tuple[UUID, ...]:
        rows = self.session.scalars(
            select(GroupMembershipRecord).where(
                GroupMembershipRecord.principal_ref == principal_ref
            )
        ).all()
        active: list[UUID] = []
        for row in rows:
            group = self.session.get(PrincipalGroupRecord, row.group_ref)
            if group is None or PrincipalGroupStatus(group.status) is not PrincipalGroupStatus.ACTIVE:
                continue
            if self._temporal_active(
                valid_from=row.valid_from,
                expires_at=row.expires_at,
                revoked_at=row.revoked_at,
                at=at,
            ):
                active.append(row.group_ref)
        return tuple(active)

    def _active_grants(
        self,
        *,
        principal_ref: UUID,
        operation: str,
        at: datetime,
    ) -> tuple[AuthorizationGrantRecord, ...]:
        group_refs = self._active_group_refs(principal_ref, at)
        subject_clause = AuthorizationGrantRecord.principal_ref == principal_ref
        if group_refs:
            subject_clause = or_(
                subject_clause,
                AuthorizationGrantRecord.group_ref.in_(group_refs),
            )
        rows = self.session.scalars(
            select(AuthorizationGrantRecord).where(
                AuthorizationGrantRecord.operation == operation,
                subject_clause,
            )
        ).all()
        return tuple(
            row
            for row in rows
            if self._temporal_active(
                valid_from=row.valid_from,
                expires_at=row.expires_at,
                revoked_at=row.revoked_at,
                at=at,
            )
        )

    def _scope_ancestors(self, scope_ref: UUID) -> tuple[UUID, ...]:
        current = scope_ref
        seen: set[UUID] = set()
        ordered: list[UUID] = []
        while current is not None:
            if current in seen:
                raise RuntimeError("authorization scope hierarchy contains a cycle")
            seen.add(current)
            row = self.session.get(AuthorizationScopeRecord, current)
            if row is None:
                raise KeyError(f"unknown scope: {current}")
            ordered.append(current)
            current = row.parent_scope_ref
        return tuple(ordered)

    def _context_scope_matches(
        self,
        *,
        grant_context_scope_ref: UUID | None,
        request_scope_ref: UUID | None,
    ) -> bool:
        if grant_context_scope_ref is None:
            return True
        if request_scope_ref is None:
            return False
        request_ancestors = set(self._scope_ancestors(request_scope_ref))
        grant_ancestors = set(self._scope_ancestors(grant_context_scope_ref))
        return (
            grant_context_scope_ref in request_ancestors
            or request_scope_ref in grant_ancestors
        )

    def _descendant_scope_refs(self, root_scope_ref: UUID) -> set[UUID]:
        rows = self.session.scalars(select(AuthorizationScopeRecord)).all()
        children: dict[UUID | None, list[UUID]] = {}
        for row in rows:
            children.setdefault(row.parent_scope_ref, []).append(row.scope_ref)
        descendants: set[UUID] = set()
        stack = [root_scope_ref]
        while stack:
            current = stack.pop()
            if current in descendants:
                continue
            descendants.add(current)
            stack.extend(children.get(current, ()))
        return descendants

    def _related_scope_refs(self, scope_ref: UUID) -> set[UUID]:
        related = set(self._scope_ancestors(scope_ref))
        related.update(self._descendant_scope_refs(scope_ref))
        return related

    def authorized_resource_refs_statement(
        self,
        *,
        principal_ref: UUID,
        operation: KCOperation | str,
        scope_ref: UUID | None = None,
        reference_time: datetime | None = None,
    ):
        principal = self._principal(principal_ref)
        if PrincipalStatus(principal.status) is not PrincipalStatus.ACTIVE:
            return select(Resource.ref_id).where(false())
        if PrincipalType(principal.principal_type) is PrincipalType.OWNER:
            return select(Resource.ref_id)

        operation_value = self._operation_value(operation)
        at = _as_utc(reference_time or self._now())
        grants = self._active_grants(
            principal_ref=principal_ref,
            operation=operation_value,
            at=at,
        )

        global_rows = tuple(
            row
            for row in grants
            if GrantTargetType(row.target_type) is GrantTargetType.GLOBAL
        )
        if any(GrantEffect(row.effect) is GrantEffect.DENY for row in global_rows):
            return select(Resource.ref_id).where(false())
        if not any(GrantEffect(row.effect) is GrantEffect.ALLOW for row in global_rows):
            return select(Resource.ref_id).where(false())

        exact_allow: set[UUID] = set()
        exact_deny: set[UUID] = set()
        allow_scope_roots: set[UUID] = set()
        deny_scope_roots: set[UUID] = set()

        for row in grants:
            target_type = GrantTargetType(row.target_type)
            effect = GrantEffect(row.effect)
            if target_type is GrantTargetType.RESOURCE:
                if row.resource_ref is None:
                    continue
                if not self._context_scope_matches(
                    grant_context_scope_ref=row.context_scope_ref,
                    request_scope_ref=scope_ref,
                ):
                    continue
                (exact_allow if effect is GrantEffect.ALLOW else exact_deny).add(
                    row.resource_ref
                )
            elif target_type is GrantTargetType.SCOPE and row.scope_ref is not None:
                (allow_scope_roots if effect is GrantEffect.ALLOW else deny_scope_roots).add(
                    row.scope_ref
                )

        allowed_scope_refs: set[UUID] = set()
        for root in allow_scope_roots:
            allowed_scope_refs.update(self._descendant_scope_refs(root))
        denied_scope_refs: set[UUID] = set()
        for root in deny_scope_roots:
            denied_scope_refs.update(self._descendant_scope_refs(root))

        if scope_ref is not None:
            related = self._related_scope_refs(scope_ref)
            allowed_scope_refs.intersection_update(related)
            denied_scope_refs.intersection_update(related)
        else:
            allowed_scope_refs.clear()
            denied_scope_refs.clear()

        policy = ResourceAccessPolicyRecord
        current = CurrentResourceAccessPolicyRecord
        resource = Resource

        exact_allow_condition = (
            resource.ref_id.in_(tuple(exact_allow)) if exact_allow else false()
        )
        personal_owner_condition = and_(
            policy.visibility == VisibilityClass.PERSONAL.value,
            policy.owner_principal_ref == principal_ref,
        )
        public_condition = policy.visibility == VisibilityClass.PUBLIC.value

        if allowed_scope_refs:
            allowed_scope_condition = exists(
                select(ResourceAccessScopeRecord.policy_ref).where(
                    ResourceAccessScopeRecord.policy_ref == policy.policy_ref,
                    ResourceAccessScopeRecord.scope_ref.in_(
                        tuple(allowed_scope_refs)
                    ),
                )
            )
        else:
            allowed_scope_condition = false()

        scoped_condition = and_(
            policy.visibility == VisibilityClass.SCOPED.value,
            policy.sensitivity.notin_(
                (
                    SensitivityClass.CREDENTIAL.value,
                    SensitivityClass.FINANCIAL.value,
                )
            ),
            allowed_scope_condition,
        )

        allowed_condition = or_(
            public_condition,
            personal_owner_condition,
            scoped_condition,
            exact_allow_condition,
        )

        deny_conditions = []
        if exact_deny:
            deny_conditions.append(resource.ref_id.in_(tuple(exact_deny)))
        if denied_scope_refs:
            deny_conditions.append(
                exists(
                    select(ResourceAccessScopeRecord.policy_ref).where(
                        ResourceAccessScopeRecord.policy_ref == policy.policy_ref,
                        ResourceAccessScopeRecord.scope_ref.in_(
                            tuple(denied_scope_refs)
                        ),
                    )
                )
            )

        statement = (
            select(resource.ref_id)
            .join(current, current.resource_ref == resource.ref_id)
            .join(policy, policy.policy_ref == current.policy_ref)
            .where(allowed_condition)
        )
        if deny_conditions:
            statement = statement.where(not_(or_(*deny_conditions)))
        return statement

    @staticmethod
    def _decision(
        allowed: bool,
        reason_code: str,
        rows: Iterable[AuthorizationGrantRecord] = (),
    ) -> AuthorizationDecision:
        return AuthorizationDecision(
            allowed=allowed,
            reason_code=reason_code,
            matched_grant_refs=tuple(sorted((row.grant_ref for row in rows), key=str)),
        )

    def evaluate(
        self,
        *,
        principal_ref: UUID,
        operation: KCOperation | str,
        scope_ref: UUID | None = None,
        resource_ref: UUID | None = None,
        reference_time: datetime | None = None,
    ) -> AuthorizationDecision:
        principal = self._principal(principal_ref)
        if PrincipalStatus(principal.status) is not PrincipalStatus.ACTIVE:
            return self._decision(False, "principal-disabled")
        if PrincipalType(principal.principal_type) is PrincipalType.OWNER:
            return self._decision(True, "owner-bypass")

        operation_value = self._operation_value(operation)
        at = _as_utc(reference_time or self._now())
        grants = self._active_grants(
            principal_ref=principal_ref,
            operation=operation_value,
            at=at,
        )

        global_rows = tuple(
            row for row in grants if GrantTargetType(row.target_type) is GrantTargetType.GLOBAL
        )
        global_denies = tuple(
            row for row in global_rows if GrantEffect(row.effect) is GrantEffect.DENY
        )
        if global_denies:
            return self._decision(False, "operation-explicitly-denied", global_denies)
        global_allows = tuple(
            row for row in global_rows if GrantEffect(row.effect) is GrantEffect.ALLOW
        )
        if not global_allows:
            return self._decision(False, "operation-not-granted")

        if resource_ref is None and scope_ref is None:
            return self._decision(True, "operation-granted", global_allows)

        if resource_ref is None:
            requested_ancestors = set(self._scope_ancestors(scope_ref))
            scope_rows = tuple(
                row
                for row in grants
                if GrantTargetType(row.target_type) is GrantTargetType.SCOPE
                and row.scope_ref in requested_ancestors
            )
            denies = tuple(
                row for row in scope_rows if GrantEffect(row.effect) is GrantEffect.DENY
            )
            if denies:
                return self._decision(False, "scope-explicitly-denied", denies)
            allows = tuple(
                row for row in scope_rows if GrantEffect(row.effect) is GrantEffect.ALLOW
            )
            if allows:
                return self._decision(True, "scope-granted", (*global_allows, *allows))
            return self._decision(False, "scope-not-granted", global_allows)

        try:
            policy = self.read_current_resource_access_policy(resource_ref)
        except KeyError:
            return self._decision(False, "resource-policy-missing", global_allows)

        resource_rows = tuple(
            row
            for row in grants
            if GrantTargetType(row.target_type) is GrantTargetType.RESOURCE
            and row.resource_ref == resource_ref
            and self._context_scope_matches(
                grant_context_scope_ref=row.context_scope_ref,
                request_scope_ref=scope_ref,
            )
        )
        resource_denies = tuple(
            row for row in resource_rows if GrantEffect(row.effect) is GrantEffect.DENY
        )
        if resource_denies:
            return self._decision(False, "resource-explicitly-denied", resource_denies)
        resource_allows = tuple(
            row for row in resource_rows if GrantEffect(row.effect) is GrantEffect.ALLOW
        )

        policy_scope_ancestors: set[UUID] = set()
        related_policy_scopes: set[UUID] = set(policy.scope_refs)
        for policy_scope_ref in policy.scope_refs:
            policy_scope_ancestors.update(self._scope_ancestors(policy_scope_ref))

        if scope_ref is not None and policy.scope_refs:
            requested_ancestors = set(self._scope_ancestors(scope_ref))
            related_policy_scopes = {
                policy_scope_ref
                for policy_scope_ref in policy.scope_refs
                if (
                    scope_ref in set(self._scope_ancestors(policy_scope_ref))
                    or policy_scope_ref in requested_ancestors
                )
            }
            if not related_policy_scopes and policy.visibility is VisibilityClass.SCOPED:
                if resource_allows:
                    return self._decision(
                        True,
                        "resource-explicitly-granted",
                        (*global_allows, *resource_allows),
                    )
                return self._decision(False, "resource-outside-request-scope", global_allows)
            policy_scope_ancestors = set()
            for policy_scope_ref in related_policy_scopes:
                policy_scope_ancestors.update(self._scope_ancestors(policy_scope_ref))

        scope_rows = tuple(
            row
            for row in grants
            if GrantTargetType(row.target_type) is GrantTargetType.SCOPE
            and row.scope_ref in policy_scope_ancestors
        )
        scope_denies = tuple(
            row for row in scope_rows if GrantEffect(row.effect) is GrantEffect.DENY
        )
        if scope_denies:
            return self._decision(False, "resource-scope-explicitly-denied", scope_denies)
        scope_allows = tuple(
            row for row in scope_rows if GrantEffect(row.effect) is GrantEffect.ALLOW
        )

        if policy.sensitivity in {
            SensitivityClass.CREDENTIAL,
            SensitivityClass.FINANCIAL,
        }:
            if (
                policy.visibility is VisibilityClass.PERSONAL
                and policy.owner_principal_ref == principal_ref
            ):
                return self._decision(True, "sensitive-personal-owner", global_allows)
            if resource_allows:
                return self._decision(
                    True,
                    "sensitive-resource-explicitly-granted",
                    (*global_allows, *resource_allows),
                )
            return self._decision(False, "sensitive-resource-requires-exact-grant")

        if policy.visibility is VisibilityClass.PUBLIC:
            return self._decision(True, "public-resource", global_allows)

        if policy.visibility is VisibilityClass.PERSONAL:
            if policy.owner_principal_ref == principal_ref:
                return self._decision(True, "personal-owner", global_allows)
            if resource_allows:
                return self._decision(
                    True,
                    "personal-resource-explicitly-granted",
                    (*global_allows, *resource_allows),
                )
            return self._decision(False, "personal-resource-not-owned")

        if policy.visibility is VisibilityClass.SCOPED:
            if resource_allows:
                return self._decision(
                    True,
                    "resource-explicitly-granted",
                    (*global_allows, *resource_allows),
                )
            if scope_allows:
                return self._decision(
                    True,
                    "resource-scope-granted",
                    (*global_allows, *scope_allows),
                )
            return self._decision(False, "resource-scope-not-granted")

        if resource_allows:
            return self._decision(
                True,
                "private-resource-explicitly-granted",
                (*global_allows, *resource_allows),
            )
        return self._decision(False, "private-resource-not-granted", global_allows)
