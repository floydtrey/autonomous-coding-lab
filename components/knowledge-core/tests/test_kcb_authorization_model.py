from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from knowledge_core.application.authorization import (
    AuthorizationDeniedError,
    AuthorizationKernel,
)
from knowledge_core.application.principal_auth import PrincipalAuthenticationKernel
from knowledge_core.application.resources import ResourceKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.authorization import (
    GrantEffect,
    GrantSubjectType,
    GrantTargetType,
    KCOperation,
    ScopeLifecycleState,
    ScopeType,
    SensitivityClass,
    VisibilityClass,
)
from knowledge_core.domain.principals import PrincipalType
from knowledge_core.storage.authorization_models import ResourceAccessPolicyRecord
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)


_FIXED_NOW = datetime(2026, 9, 19, 21, 0, tzinfo=timezone.utc)


def _setup(tmp_path):
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    sessions = create_session_factory(engine)
    session = sessions()

    principals = PrincipalAuthenticationKernel(session, now=lambda: _FIXED_NOW)
    owner = principals.create_principal(
        principal_code="OWNER",
        display_name="Owner",
        principal_type=PrincipalType.OWNER,
    )
    user1 = principals.create_principal(
        principal_code="USER-1",
        display_name="User One",
        principal_type=PrincipalType.HUMAN,
    )
    user2 = principals.create_principal(
        principal_code="USER-2",
        display_name="User Two",
        principal_type=PrincipalType.HUMAN,
    )
    worker = principals.create_principal(
        principal_code="ACL-WORKER",
        display_name="ACL Worker",
        principal_type=PrincipalType.AI,
    )
    admin = principals.create_principal(
        principal_code="AUTH-ADMIN",
        display_name="Authorization Admin",
        principal_type=PrincipalType.SERVICE,
    )
    session.commit()

    authz = AuthorizationKernel(session, now=lambda: _FIXED_NOW)
    resources = ResourceKnowledgeKernel(
        session,
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )
    foundation = resources.bootstrap_resource_test_profile()

    def make_resource():
        return resources.create_resource(
            kind_revision_ref=foundation.artifact_kind_revision_ref
        ).resource_ref

    return engine, session, principals, authz, owner, user1, user2, worker, admin, make_resource


def _grant_global(authz, *, owner_ref, principal_ref, operation):
    return authz.create_grant(
        actor_principal_ref=owner_ref,
        subject_type=GrantSubjectType.PRINCIPAL,
        principal_ref=principal_ref,
        operation=operation,
        effect=GrantEffect.ALLOW,
        target_type=GrantTargetType.GLOBAL,
        reason="test operation capability",
    )


def _grant_scope(authz, *, owner_ref, principal_ref, operation, scope_ref, expires_at=None):
    return authz.create_grant(
        actor_principal_ref=owner_ref,
        subject_type=GrantSubjectType.PRINCIPAL,
        principal_ref=principal_ref,
        operation=operation,
        effect=GrantEffect.ALLOW,
        target_type=GrantTargetType.SCOPE,
        scope_ref=scope_ref,
        expires_at=expires_at,
        reason="test scope access",
    )


def test_owner_bypasses_grants_but_nonowner_requires_operation_capability(tmp_path):
    (
        engine,
        session,
        _principals,
        authz,
        owner,
        _user1,
        _user2,
        worker,
        _admin,
        _make_resource,
    ) = _setup(tmp_path)
    try:
        assert authz.evaluate(
            principal_ref=owner.principal_ref,
            operation=KCOperation.ADMIN,
        ).allowed

        decision = authz.evaluate(
            principal_ref=worker.principal_ref,
            operation=KCOperation.SEARCH,
        )
        assert not decision.allowed
        assert decision.reason_code == "operation-not-granted"
    finally:
        session.close()
        engine.dispose()


def test_human_user_gets_public_and_own_personal_but_not_another_users_personal(tmp_path):
    (
        engine,
        session,
        _principals,
        authz,
        owner,
        user1,
        user2,
        _worker,
        _admin,
        make_resource,
    ) = _setup(tmp_path)
    try:
        for principal in (user1, user2):
            _grant_global(
                authz,
                owner_ref=owner.principal_ref,
                principal_ref=principal.principal_ref,
                operation=KCOperation.GET_SOURCE,
            )

        public_ref = make_resource()
        authz.set_resource_access_policy(
            actor_principal_ref=owner.principal_ref,
            resource_ref=public_ref,
            owner_principal_ref=owner.principal_ref,
            origin_principal_ref=owner.principal_ref,
            visibility=VisibilityClass.PUBLIC,
            sensitivity=SensitivityClass.NORMAL,
        )

        user1_private_ref = make_resource()
        authz.set_resource_access_policy(
            actor_principal_ref=owner.principal_ref,
            resource_ref=user1_private_ref,
            owner_principal_ref=user1.principal_ref,
            origin_principal_ref=user1.principal_ref,
            visibility=VisibilityClass.PERSONAL,
            sensitivity=SensitivityClass.FINANCIAL,
        )

        user2_private_ref = make_resource()
        authz.set_resource_access_policy(
            actor_principal_ref=owner.principal_ref,
            resource_ref=user2_private_ref,
            owner_principal_ref=user2.principal_ref,
            origin_principal_ref=user2.principal_ref,
            visibility=VisibilityClass.PERSONAL,
            sensitivity=SensitivityClass.NORMAL,
        )
        session.commit()

        assert authz.evaluate(
            principal_ref=user1.principal_ref,
            operation=KCOperation.GET_SOURCE,
            resource_ref=public_ref,
        ).allowed

        own = authz.evaluate(
            principal_ref=user1.principal_ref,
            operation=KCOperation.GET_SOURCE,
            resource_ref=user1_private_ref,
        )
        assert own.allowed
        assert own.reason_code == "sensitive-personal-owner"

        other = authz.evaluate(
            principal_ref=user1.principal_ref,
            operation=KCOperation.GET_SOURCE,
            resource_ref=user2_private_ref,
        )
        assert not other.allowed
        assert other.reason_code == "personal-resource-not-owned"
    finally:
        session.close()
        engine.dispose()


def test_acl_scope_isolation_hierarchy_expiry_and_failed_lifecycle_are_separate(tmp_path):
    (
        engine,
        session,
        _principals,
        authz,
        owner,
        _user1,
        _user2,
        worker,
        _admin,
        make_resource,
    ) = _setup(tmp_path)
    try:
        acl_scope = authz.create_scope(
            actor_principal_ref=owner.principal_ref,
            scope_type=ScopeType.PROJECT,
            scope_key="acl",
            display_name="ACL",
        )
        worker_dir = authz.create_scope(
            actor_principal_ref=owner.principal_ref,
            scope_type=ScopeType.DIRECTORY,
            scope_key="acl/worker",
            display_name="ACL Worker",
            parent_scope_ref=acl_scope.scope_ref,
        )
        vera_scope = authz.create_scope(
            actor_principal_ref=owner.principal_ref,
            scope_type=ScopeType.PROJECT,
            scope_key="vera",
            display_name="Vera",
        )

        _grant_global(
            authz,
            owner_ref=owner.principal_ref,
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
        )
        _grant_scope(
            authz,
            owner_ref=owner.principal_ref,
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            scope_ref=acl_scope.scope_ref,
        )

        acl_resource = make_resource()
        authz.set_resource_access_policy(
            actor_principal_ref=owner.principal_ref,
            resource_ref=acl_resource,
            owner_principal_ref=owner.principal_ref,
            origin_principal_ref=worker.principal_ref,
            visibility=VisibilityClass.SCOPED,
            sensitivity=SensitivityClass.NORMAL,
            scope_refs=(worker_dir.scope_ref,),
        )

        vera_resource = make_resource()
        authz.set_resource_access_policy(
            actor_principal_ref=owner.principal_ref,
            resource_ref=vera_resource,
            owner_principal_ref=owner.principal_ref,
            origin_principal_ref=owner.principal_ref,
            visibility=VisibilityClass.SCOPED,
            sensitivity=SensitivityClass.NORMAL,
            scope_refs=(vera_scope.scope_ref,),
        )
        session.commit()

        assert authz.evaluate(
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            scope_ref=acl_scope.scope_ref,
            resource_ref=acl_resource,
        ).allowed

        assert not authz.evaluate(
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            scope_ref=acl_scope.scope_ref,
            resource_ref=vera_resource,
        ).allowed

        temporary = _grant_scope(
            authz,
            owner_ref=owner.principal_ref,
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            scope_ref=vera_scope.scope_ref,
            expires_at=_FIXED_NOW + timedelta(hours=1),
        )
        session.commit()

        before_expiry = authz.evaluate(
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            scope_ref=vera_scope.scope_ref,
            resource_ref=vera_resource,
            reference_time=_FIXED_NOW + timedelta(minutes=30),
        )
        assert before_expiry.allowed
        assert temporary.grant_ref in before_expiry.matched_grant_refs

        after_expiry = authz.evaluate(
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            scope_ref=vera_scope.scope_ref,
            resource_ref=vera_resource,
            reference_time=_FIXED_NOW + timedelta(hours=2),
        )
        assert not after_expiry.allowed

        failed_scope = authz.set_scope_lifecycle(
            actor_principal_ref=owner.principal_ref,
            scope_ref=acl_scope.scope_ref,
            lifecycle_state=ScopeLifecycleState.FAILED,
        )
        session.commit()
        assert failed_scope.lifecycle_state is ScopeLifecycleState.FAILED

        # Lifecycle affects retrieval relevance later; it does not secretly revoke
        # authority. Deliberate historical inspection remains possible.
        assert authz.evaluate(
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            scope_ref=acl_scope.scope_ref,
            resource_ref=acl_resource,
        ).allowed
    finally:
        session.close()
        engine.dispose()


def test_sensitive_resource_requires_exact_grant_and_explicit_deny_wins(tmp_path):
    (
        engine,
        session,
        _principals,
        authz,
        owner,
        _user1,
        _user2,
        worker,
        _admin,
        make_resource,
    ) = _setup(tmp_path)
    try:
        acl_scope = authz.create_scope(
            actor_principal_ref=owner.principal_ref,
            scope_type=ScopeType.PROJECT,
            scope_key="acl",
            display_name="ACL",
        )
        _grant_global(
            authz,
            owner_ref=owner.principal_ref,
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
        )
        _grant_scope(
            authz,
            owner_ref=owner.principal_ref,
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            scope_ref=acl_scope.scope_ref,
        )

        secret_ref = make_resource()
        authz.set_resource_access_policy(
            actor_principal_ref=owner.principal_ref,
            resource_ref=secret_ref,
            owner_principal_ref=owner.principal_ref,
            origin_principal_ref=owner.principal_ref,
            visibility=VisibilityClass.SCOPED,
            sensitivity=SensitivityClass.CREDENTIAL,
            scope_refs=(acl_scope.scope_ref,),
            classification_locked=True,
        )
        session.commit()

        scoped_only = authz.evaluate(
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            scope_ref=acl_scope.scope_ref,
            resource_ref=secret_ref,
        )
        assert not scoped_only.allowed
        assert scoped_only.reason_code == "sensitive-resource-requires-exact-grant"

        allow = authz.create_grant(
            actor_principal_ref=owner.principal_ref,
            subject_type=GrantSubjectType.PRINCIPAL,
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            effect=GrantEffect.ALLOW,
            target_type=GrantTargetType.RESOURCE,
            resource_ref=secret_ref,
            reason="temporary exact credential release",
        )
        session.commit()
        exact = authz.evaluate(
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            resource_ref=secret_ref,
        )
        assert exact.allowed
        assert allow.grant_ref in exact.matched_grant_refs

        deny = authz.create_grant(
            actor_principal_ref=owner.principal_ref,
            subject_type=GrantSubjectType.PRINCIPAL,
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            effect=GrantEffect.DENY,
            target_type=GrantTargetType.RESOURCE,
            resource_ref=secret_ref,
            reason="owner revoked disclosure while preserving grant history",
        )
        session.commit()
        denied = authz.evaluate(
            principal_ref=worker.principal_ref,
            operation=KCOperation.GET_SOURCE,
            resource_ref=secret_ref,
        )
        assert not denied.allowed
        assert denied.reason_code == "resource-explicitly-denied"
        assert deny.grant_ref in denied.matched_grant_refs
    finally:
        session.close()
        engine.dispose()


def test_group_membership_scales_operation_and_scope_grants(tmp_path):
    (
        engine,
        session,
        _principals,
        authz,
        owner,
        _user1,
        _user2,
        worker,
        _admin,
        make_resource,
    ) = _setup(tmp_path)
    try:
        acl_scope = authz.create_scope(
            actor_principal_ref=owner.principal_ref,
            scope_type=ScopeType.PROJECT,
            scope_key="acl",
            display_name="ACL",
        )
        group_ref = authz.create_group(
            actor_principal_ref=owner.principal_ref,
            group_code="ACL-WORKERS",
            display_name="ACL Workers",
        )
        authz.add_group_member(
            actor_principal_ref=owner.principal_ref,
            group_ref=group_ref,
            principal_ref=worker.principal_ref,
        )
        authz.create_grant(
            actor_principal_ref=owner.principal_ref,
            subject_type=GrantSubjectType.GROUP,
            group_ref=group_ref,
            operation=KCOperation.SEARCH,
            effect=GrantEffect.ALLOW,
            target_type=GrantTargetType.GLOBAL,
            reason="ACL workers may invoke search",
        )
        authz.create_grant(
            actor_principal_ref=owner.principal_ref,
            subject_type=GrantSubjectType.GROUP,
            group_ref=group_ref,
            operation=KCOperation.SEARCH,
            effect=GrantEffect.ALLOW,
            target_type=GrantTargetType.SCOPE,
            scope_ref=acl_scope.scope_ref,
            reason="ACL workers may search ACL project",
        )

        resource_ref = make_resource()
        authz.set_resource_access_policy(
            actor_principal_ref=owner.principal_ref,
            resource_ref=resource_ref,
            owner_principal_ref=owner.principal_ref,
            origin_principal_ref=worker.principal_ref,
            visibility=VisibilityClass.SCOPED,
            sensitivity=SensitivityClass.NORMAL,
            scope_refs=(acl_scope.scope_ref,),
        )
        session.commit()

        assert authz.evaluate(
            principal_ref=worker.principal_ref,
            operation=KCOperation.SEARCH,
            scope_ref=acl_scope.scope_ref,
            resource_ref=resource_ref,
        ).allowed
    finally:
        session.close()
        engine.dispose()


def test_locked_classification_preserves_owner_control_and_policy_history(tmp_path):
    (
        engine,
        session,
        _principals,
        authz,
        owner,
        _user1,
        _user2,
        _worker,
        admin,
        make_resource,
    ) = _setup(tmp_path)
    try:
        _grant_global(
            authz,
            owner_ref=owner.principal_ref,
            principal_ref=admin.principal_ref,
            operation=KCOperation.ADMIN,
        )

        locked_ref = make_resource()
        first = authz.set_resource_access_policy(
            actor_principal_ref=owner.principal_ref,
            resource_ref=locked_ref,
            owner_principal_ref=owner.principal_ref,
            origin_principal_ref=owner.principal_ref,
            visibility=VisibilityClass.PRIVATE,
            sensitivity=SensitivityClass.FINANCIAL,
            classification_locked=True,
        )
        session.commit()

        with pytest.raises(AuthorizationDeniedError):
            authz.set_resource_access_policy(
                actor_principal_ref=admin.principal_ref,
                resource_ref=locked_ref,
                owner_principal_ref=owner.principal_ref,
                origin_principal_ref=owner.principal_ref,
                visibility=VisibilityClass.PUBLIC,
                sensitivity=SensitivityClass.NORMAL,
                classification_locked=False,
            )

        unlocked_ref = make_resource()
        with pytest.raises(AuthorizationDeniedError):
            authz.set_resource_access_policy(
                actor_principal_ref=admin.principal_ref,
                resource_ref=unlocked_ref,
                owner_principal_ref=owner.principal_ref,
                origin_principal_ref=admin.principal_ref,
                visibility=VisibilityClass.PRIVATE,
                sensitivity=SensitivityClass.PROTECTED,
                classification_locked=True,
            )

        second = authz.set_resource_access_policy(
            actor_principal_ref=owner.principal_ref,
            resource_ref=locked_ref,
            owner_principal_ref=owner.principal_ref,
            origin_principal_ref=owner.principal_ref,
            visibility=VisibilityClass.PRIVATE,
            sensitivity=SensitivityClass.CREDENTIAL,
            classification_locked=True,
        )
        session.commit()

        assert second.supersedes_policy_ref == first.policy_ref
        assert session.scalar(
            select(func.count())
            .select_from(ResourceAccessPolicyRecord)
            .where(ResourceAccessPolicyRecord.resource_ref == locked_ref)
        ) == 2
        assert (
            authz.read_current_resource_access_policy(locked_ref).policy_ref
            == second.policy_ref
        )
    finally:
        session.close()
        engine.dispose()
