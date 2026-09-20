from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.api.consumer_admission import ConsumerAdmission
from knowledge_core.application.authorization import AuthorizationKernel
from knowledge_core.application.principal_auth import PrincipalAuthenticationKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.authorization import (
    GrantEffect,
    GrantSubjectType,
    GrantTargetType,
    KCOperation,
    ScopeType,
    SensitivityClass,
    VisibilityClass,
)
from knowledge_core.domain.principals import PrincipalType
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.resource_models import ResourceVersion


_BOOTSTRAP_KEY = "kcc-owner-bootstrap"
_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("PostgreSQL qualification URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("KC-C qualification requires PostgreSQL")
    return engine


def _truncate_kernel_tables(engine) -> None:
    inspector = inspect(engine)
    preparer = engine.dialect.identifier_preparer
    tables: list[str] = []
    for schema in ("kc", "kc_control", "kc_derived"):
        for table_name in inspector.get_table_names(schema=schema):
            tables.append(
                f"{preparer.quote_schema(schema)}.{preparer.quote(table_name)}"
            )
    if not tables:
        raise AssertionError("Knowledge Core schemas are not migrated")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"
        )


def _allow(authz, *, owner_ref, principal_ref, operation, target_type, scope_ref=None):
    return authz.create_grant(
        actor_principal_ref=owner_ref,
        subject_type=GrantSubjectType.PRINCIPAL,
        principal_ref=principal_ref,
        operation=operation,
        effect=GrantEffect.ALLOW,
        target_type=target_type,
        scope_ref=scope_ref,
        reason="KC-C qualification",
    )


@pytest.mark.postgresql
def test_hardened_consumer_api_auth_scope_search_source_and_legacy_isolation(
    tmp_path: Path,
):
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    bootstrap = BootstrapAdmission(
        contract=BootstrapContract(),
        api_key=_BOOTSTRAP_KEY,
    )
    admission = ConsumerAdmission(
        session_factory=sessions,
        owner_bootstrap=bootstrap,
    )
    owner = admission.ensure_owner_principal()
    assert owner is not None

    with sessions() as session:
        principals = PrincipalAuthenticationKernel(session)
        worker = principals.create_principal(
            principal_code="ACL-WORKER",
            display_name="ACL Worker",
            principal_type=PrincipalType.AI,
        )
        outsider = principals.create_principal(
            principal_code="OTHER-SERVICE",
            display_name="Other Service",
            principal_type=PrincipalType.SERVICE,
        )
        worker_key = principals.issue_service_credential(
            principal_ref=worker.principal_ref,
            label="KC-C worker",
        ).token
        outsider_key = principals.issue_service_credential(
            principal_ref=outsider.principal_ref,
            label="KC-C outsider",
        ).token
        session.commit()

        authz = AuthorizationKernel(session)
        acl_scope = authz.create_scope(
            actor_principal_ref=owner.principal_ref,
            scope_type=ScopeType.PROJECT,
            scope_key="acl",
            display_name="ACL",
        )
        other_scope = authz.create_scope(
            actor_principal_ref=owner.principal_ref,
            scope_type=ScopeType.PROJECT,
            scope_key="other",
            display_name="Other",
        )

        for operation in (
            KCOperation.STATUS,
            KCOperation.SEARCH,
            KCOperation.GET_SOURCE,
            KCOperation.STORE,
            KCOperation.MEMORY_PROPOSE,
        ):
            _allow(
                authz,
                owner_ref=owner.principal_ref,
                principal_ref=worker.principal_ref,
                operation=operation,
                target_type=GrantTargetType.GLOBAL,
            )

        for operation in (
            KCOperation.SEARCH,
            KCOperation.GET_SOURCE,
            KCOperation.STORE,
            KCOperation.MEMORY_PROPOSE,
        ):
            _allow(
                authz,
                owner_ref=owner.principal_ref,
                principal_ref=worker.principal_ref,
                operation=operation,
                target_type=GrantTargetType.SCOPE,
                scope_ref=acl_scope.scope_ref,
            )

        for operation in (KCOperation.SEARCH, KCOperation.GET_SOURCE):
            _allow(
                authz,
                owner_ref=owner.principal_ref,
                principal_ref=outsider.principal_ref,
                operation=operation,
                target_type=GrantTargetType.GLOBAL,
            )
        session.commit()

    app = create_app(
        session_factory=sessions,
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
        bootstrap_admission=bootstrap,
        consumer_admission=admission,
    )

    worker_headers = {
        "X-Knowledge-Key": worker_key,
        "X-Knowledge-Scope": str(acl_scope.scope_ref),
    }
    outsider_headers = {
        "X-Knowledge-Key": outsider_key,
        "X-Knowledge-Scope": str(other_scope.scope_ref),
    }

    try:
        with TestClient(app) as client:
            # The hardened network surface must not publish broad kernel routes.
            assert client.post(
                "/v1/entities",
                headers={"X-Knowledge-Caller": "forged-owner"},
                json={},
            ).status_code == 404
            assert client.post(
                "/v1/retrieval/search",
                headers={"X-Knowledge-Caller": "forged-owner"},
                json={"query": "anything"},
            ).status_code == 404

            assert client.get(
                "/v1/kc/status",
                headers={"X-Knowledge-Key": worker_key},
            ).status_code == 200

            missing_scope = client.post(
                "/v1/kc/store",
                headers={
                    "X-Knowledge-Key": worker_key,
                    "Idempotency-Key": "worker-store-missing-scope",
                },
                json={
                    "content": "ACL worker scoped note.",
                    "project": "acl",
                    "source_type": "user_note",
                    "source_id": "worker-note",
                },
            )
            assert missing_scope.status_code == 400

            wrong_project = client.post(
                "/v1/kc/store",
                headers={
                    **worker_headers,
                    "Idempotency-Key": "worker-store-wrong-project",
                },
                json={
                    "content": "Must not escape into another project.",
                    "project": "other",
                    "source_type": "user_note",
                    "source_id": "wrong-project-note",
                },
            )
            assert wrong_project.status_code == 409

            stored = client.post(
                "/v1/kc/store",
                headers={
                    **worker_headers,
                    "Idempotency-Key": "worker-store-1",
                },
                json={
                    "content": "ACL worker scoped note.",
                    "project": "acl",
                    "source_type": "user_note",
                    "source_id": "worker-note",
                },
            )
            assert stored.status_code == 201, stored.text
            stored_payload = stored.json()
            resource_ref = UUID(stored_payload["resource_id"])
            version_ref = UUID(stored_payload["version_id"])

            worker_search = client.post(
                "/v1/kc/search",
                headers=worker_headers,
                json={"query": "ACL worker scoped note", "limit": 10},
            )
            assert worker_search.status_code == 200, worker_search.text
            worker_results = worker_search.json()["results"]
            assert any(
                item["resource_ref"] == str(resource_ref)
                for item in worker_results
            )

            outsider_search = client.post(
                "/v1/kc/search",
                headers=outsider_headers,
                json={"query": "ACL worker scoped note", "limit": 10},
            )
            assert outsider_search.status_code == 200, outsider_search.text
            assert all(
                item["resource_ref"] != str(resource_ref)
                for item in outsider_search.json()["results"]
            )

            exact = client.post(
                "/v1/kc/get-source",
                headers=worker_headers,
                json={"resource_version_ref": str(version_ref)},
            )
            assert exact.status_code == 200, exact.text
            assert exact.json()["content"] == "ACL worker scoped note."

            denied_exact = client.post(
                "/v1/kc/get-source",
                headers=outsider_headers,
                json={"resource_version_ref": str(version_ref)},
            )
            assert denied_exact.status_code == 404

            proposer_mismatch = client.post(
                "/v1/kc/memory-candidates",
                headers={
                    **worker_headers,
                    "Idempotency-Key": "proposal-mismatch",
                },
                json={
                    "content": "A bounded observation.",
                    "project": "acl",
                    "proposer_ref": "OWNER",
                },
            )
            assert proposer_mismatch.status_code == 409

            proposal = client.post(
                "/v1/kc/memory-candidates",
                headers={
                    **worker_headers,
                    "Idempotency-Key": "proposal-1",
                },
                json={
                    "content": "A bounded observation.",
                    "project": "acl",
                    "proposer_ref": "ACL-WORKER",
                },
            )
            assert proposal.status_code == 202, proposal.text

        # Reclassify the AI-created resource as locked financial data. The AI's
        # stable source ID must no longer give it authority to rewrite that resource.
        with sessions() as session:
            authz = AuthorizationKernel(session)
            authz.set_resource_access_policy(
                actor_principal_ref=owner.principal_ref,
                resource_ref=resource_ref,
                owner_principal_ref=owner.principal_ref,
                origin_principal_ref=worker.principal_ref,
                visibility=VisibilityClass.PRIVATE,
                sensitivity=SensitivityClass.FINANCIAL,
                classification_locked=True,
            )
            exact_grant = authz.create_grant(
                actor_principal_ref=owner.principal_ref,
                subject_type=GrantSubjectType.PRINCIPAL,
                principal_ref=worker.principal_ref,
                operation=KCOperation.GET_SOURCE,
                effect=GrantEffect.ALLOW,
                target_type=GrantTargetType.RESOURCE,
                resource_ref=resource_ref,
                context_scope_ref=acl_scope.scope_ref,
                reason="temporary project-bound release",
            )
            session.commit()

        with TestClient(app) as client:
            # Context-bound exact release works only in the intended project.
            released = client.post(
                "/v1/kc/get-source",
                headers=worker_headers,
                json={"resource_version_ref": str(version_ref)},
            )
            assert released.status_code == 200, released.text

            no_context = client.post(
                "/v1/kc/get-source",
                headers={"X-Knowledge-Key": worker_key},
                json={"resource_version_ref": str(version_ref)},
            )
            assert no_context.status_code == 404

            rewrite_locked = client.post(
                "/v1/kc/store",
                headers={
                    **worker_headers,
                    "Idempotency-Key": "worker-store-2",
                },
                json={
                    "content": "Attempted rewrite after owner protection.",
                    "project": "acl",
                    "source_type": "user_note",
                    "source_id": "worker-note",
                },
            )
            assert rewrite_locked.status_code in {403, 409}

            # Owner bootstrap remains an all-authority migration/admin path, but the
            # same hardened service still does not expose legacy kernel routes.
            owner_status = client.get(
                "/v1/kc/status",
                headers={"X-Knowledge-Key": _BOOTSTRAP_KEY},
            )
            assert owner_status.status_code == 200
            assert client.post(
                "/v1/identity/merge",
                headers={
                    "X-Knowledge-Key": _BOOTSTRAP_KEY,
                    "X-Knowledge-Caller": "local_owner",
                },
                json={},
            ).status_code == 404

        with sessions() as session:
            # The exact release is durable policy evidence, not a mutation of the
            # protected resource itself.
            assert session.get(ResourceVersion, version_ref) is not None
            assert exact_grant.context_scope_ref == acl_scope.scope_ref
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()
