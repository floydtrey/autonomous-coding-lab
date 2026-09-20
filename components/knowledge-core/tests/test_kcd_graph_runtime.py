from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.api.consumer_admission import ConsumerAdmission
from knowledge_core.application.authorization import AuthorizationKernel
from knowledge_core.application.graph_runtime import (
    GraphRuntimeSettings,
    KnowledgeGraphRuntime,
)
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
from knowledge_core.domain.projection_adapter import (
    ProjectionAdapterDescriptor,
    ProjectionAdapterReceipt,
    ProjectionLifecycleEdge,
    ProjectionLifecycleInventory,
    ProjectionProviderSourceBinding,
    ProjectionSearchHit,
)
from knowledge_core.domain.projection_evidence import ProjectionDisposition
from knowledge_core.storage.database import create_database_engine, create_session_factory


_BOOTSTRAP_KEY = "kcd-owner-bootstrap"
_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("PostgreSQL qualification URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("KC-D qualification requires PostgreSQL")
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


def _allow(
    authz,
    *,
    owner_ref,
    principal_ref,
    operation,
    target_type,
    scope_ref=None,
):
    return authz.create_grant(
        actor_principal_ref=owner_ref,
        subject_type=GrantSubjectType.PRINCIPAL,
        principal_ref=principal_ref,
        operation=operation,
        effect=GrantEffect.ALLOW,
        target_type=target_type,
        scope_ref=scope_ref,
        reason="KC-D qualification",
    )


class FakeProductionGraphAdapter:
    def __init__(self, *, config_digest: str = "sha256:kcd-adapter", fail=False):
        self.config_digest = config_digest
        self.fail = fail
        self.project_calls = 0
        self.search_calls = 0
        self.projected = {}

    @property
    def descriptor(self):
        return ProjectionAdapterDescriptor(
            backend_identity="kcd-fake-graph",
            backend_version="1",
            adapter_identity="kcd-fake-production-adapter",
            adapter_version="1",
            config_digest=self.config_digest,
        )

    def partition_key(
        self,
        *,
        namespace_key,
        scope_key,
        projection_profile_id,
        projection_attempt_id,
        adapter_config_digest,
    ):
        payload = "|".join(
            (
                namespace_key,
                scope_key,
                projection_profile_id,
                str(projection_attempt_id),
                adapter_config_digest,
            )
        )
        return "kcd_" + sha256(payload.encode("utf-8")).hexdigest()[:24]

    async def project(self, request):
        self.project_calls += 1
        if self.fail:
            raise RuntimeError("simulated Graphiti outage")
        partition = self.partition_key(
            namespace_key=request.attempt.namespace_key,
            scope_key=request.attempt.scope_key,
            projection_profile_id=request.attempt.profile_id,
            projection_attempt_id=request.attempt.attempt_id,
            adapter_config_digest=request.attempt.config_digest,
        )
        segments = tuple(request.segments)
        bindings = tuple(
            ProjectionProviderSourceBinding(
                resource_version_ref=segment.resource_version_ref,
                source_revision_id=segment.source_revision_id,
                segment_key=segment.segment_key,
                source_slice_sha256=segment.source_slice_sha256,
                provider_partition_key=partition,
                provider_source_id=f"kcd-source:{index}:{segment.segment_key}",
            )
            for index, segment in enumerate(segments)
        )
        self.projected[request.attempt.attempt_id] = {
            "partition": partition,
            "segments": segments,
            "bindings": bindings,
        }
        return ProjectionAdapterReceipt(
            disposition=ProjectionDisposition.SUCCEEDED,
            episode_count=len(segments),
            source_bindings=bindings,
        )

    async def existing_source_keys(self, *, source_keys, **_kwargs):
        return frozenset(source_keys)

    async def lifecycle_inventory(
        self,
        *,
        namespace_key,
        scope_key,
        projection_profile_id,
        projection_attempt_id,
        adapter_config_digest,
    ):
        projected = self.projected.get(projection_attempt_id)
        expected = self.partition_key(
            namespace_key=namespace_key,
            scope_key=scope_key,
            projection_profile_id=projection_profile_id,
            projection_attempt_id=projection_attempt_id,
            adapter_config_digest=adapter_config_digest,
        )
        if projected is None or projected["partition"] != expected:
            return ProjectionLifecycleInventory(
                partition_key=expected,
                complete=True,
                edges=(),
            )
        source_ids = tuple(
            binding.provider_source_id for binding in projected["bindings"]
        )
        return ProjectionLifecycleInventory(
            partition_key=expected,
            complete=True,
            edges=(
                ProjectionLifecycleEdge(
                    provider_edge_id="kcd-combined-edge",
                    partition_key=expected,
                    source_correlation_keys=source_ids,
                    invalid_at=None,
                    expired_at=None,
                ),
            ),
        )

    async def search(
        self,
        *,
        query,
        namespace_key,
        scope_key,
        projection_profile_id,
        projection_attempt_id,
        adapter_config_digest,
        limit,
    ):
        self.search_calls += 1
        projected = self.projected.get(projection_attempt_id)
        partition = self.partition_key(
            namespace_key=namespace_key,
            scope_key=scope_key,
            projection_profile_id=projection_profile_id,
            projection_attempt_id=projection_attempt_id,
            adapter_config_digest=adapter_config_digest,
        )
        if projected is None or projected["partition"] != partition:
            return ()
        source_ids = tuple(
            binding.provider_source_id for binding in projected["bindings"]
        )
        return (
            ProjectionSearchHit(
                provider_hit_id="kcd-combined-edge",
                partition_key=partition,
                fact="The ACL project contains two authorized implementation notes.",
                source_correlation_keys=source_ids,
            ),
        )[:limit]


def test_graph_runtime_env_is_opt_in_and_config_driven():
    disabled = GraphRuntimeSettings.from_env({})
    assert disabled.enabled is False

    enabled = GraphRuntimeSettings.from_env(
        {
            "KNOWLEDGE_CORE_GRAPH_ENABLED": "true",
            "KNOWLEDGE_CORE_GRAPH_NAMESPACE": "kc:test-graph",
            "KNOWLEDGE_CORE_GRAPH_MAX_SEGMENTS": "321",
            "KNOWLEDGE_CORE_GRAPH_MAX_ATTEMPTS": "2",
            "FALKORDB_HOST": "falkor.internal",
            "FALKORDB_PORT": "6380",
            "GRAPHITI_OLLAMA_BASE_URL": "http://model.internal:9931/v1",
            "GRAPHITI_LLM_MODEL": "graphiti-local-model",
            "GRAPHITI_EMBED_MODEL": "nomic-embed-text:latest",
        }
    )
    assert enabled.enabled is True
    assert enabled.namespace_key == "kc:test-graph"
    assert enabled.max_segments == 321
    assert enabled.provider.falkor_host == "falkor.internal"
    assert enabled.provider.falkor_port == 6380
    assert enabled.provider.ollama_base_url == "http://model.internal:9931/v1"
    assert enabled.provider.llm_model == "graphiti-local-model"


@pytest.mark.postgresql
def test_kcd_lazy_project_graph_reuse_sensitive_exclusion_and_all_source_authorization(
    tmp_path: Path,
):
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    store = LocalArtifactStore(tmp_path / "artifacts")
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
        reviewer = principals.create_principal(
            principal_code="ACL-REVIEWER",
            display_name="ACL Reviewer",
            principal_type=PrincipalType.AI,
        )
        worker_key = principals.issue_service_credential(
            principal_ref=worker.principal_ref,
            label="KC-D worker",
        ).token
        reviewer_key = principals.issue_service_credential(
            principal_ref=reviewer.principal_ref,
            label="KC-D reviewer",
        ).token
        session.commit()

        authz = AuthorizationKernel(session)
        acl_scope = authz.create_scope(
            actor_principal_ref=owner.principal_ref,
            scope_type=ScopeType.PROJECT,
            scope_key="acl",
            display_name="ACL",
        )

        for principal in (worker, reviewer):
            for operation in (KCOperation.SEARCH, KCOperation.GET_SOURCE):
                _allow(
                    authz,
                    owner_ref=owner.principal_ref,
                    principal_ref=principal.principal_ref,
                    operation=operation,
                    target_type=GrantTargetType.GLOBAL,
                )
                _allow(
                    authz,
                    owner_ref=owner.principal_ref,
                    principal_ref=principal.principal_ref,
                    operation=operation,
                    target_type=GrantTargetType.SCOPE,
                    scope_ref=acl_scope.scope_ref,
                )
        for operation in (KCOperation.STORE, KCOperation.MEMORY_PROPOSE):
            _allow(
                authz,
                owner_ref=owner.principal_ref,
                principal_ref=worker.principal_ref,
                operation=operation,
                target_type=GrantTargetType.GLOBAL,
            )
            _allow(
                authz,
                owner_ref=owner.principal_ref,
                principal_ref=worker.principal_ref,
                operation=operation,
                target_type=GrantTargetType.SCOPE,
                scope_ref=acl_scope.scope_ref,
            )
        session.commit()

    adapter = FakeProductionGraphAdapter()
    runtime = KnowledgeGraphRuntime(
        session_factory=sessions,
        artifact_store=store,
        adapter=adapter,
        max_segments=100,
    )
    app = create_app(
        session_factory=sessions,
        artifact_store=store,
        bootstrap_admission=bootstrap,
        consumer_admission=admission,
        graph_runtime=runtime,
    )
    worker_headers = {
        "X-Knowledge-Key": worker_key,
        "X-Knowledge-Scope": str(acl_scope.scope_ref),
    }
    reviewer_headers = {
        "X-Knowledge-Key": reviewer_key,
        "X-Knowledge-Scope": str(acl_scope.scope_ref),
    }

    try:
        with TestClient(app) as client:
            stored = []
            for index, text in enumerate(
                (
                    "ACL planner contract preserves bounded authority.",
                    "ACL worker execution uses the active project scope.",
                    "Bank account routing information must remain private.",
                ),
                start=1,
            ):
                response = client.post(
                    "/v1/kc/store",
                    headers={
                        **worker_headers,
                        "Idempotency-Key": f"kcd-store-{index}",
                    },
                    json={
                        "content": text,
                        "project": "acl",
                        "source_type": "user_note",
                        "source_id": f"kcd-note-{index}",
                    },
                )
                assert response.status_code == 201, response.text
                stored.append(response.json())

        sensitive_resource = UUID(stored[2]["resource_id"])
        sensitive_version = UUID(stored[2]["version_id"])
        denied_resource = UUID(stored[1]["resource_id"])

        with sessions() as session:
            authz = AuthorizationKernel(session)
            authz.set_resource_access_policy(
                actor_principal_ref=owner.principal_ref,
                resource_ref=sensitive_resource,
                owner_principal_ref=owner.principal_ref,
                origin_principal_ref=worker.principal_ref,
                visibility=VisibilityClass.PRIVATE,
                sensitivity=SensitivityClass.FINANCIAL,
                classification_locked=True,
            )
            authz.create_grant(
                actor_principal_ref=owner.principal_ref,
                subject_type=GrantSubjectType.PRINCIPAL,
                principal_ref=reviewer.principal_ref,
                operation=KCOperation.SEARCH,
                effect=GrantEffect.DENY,
                target_type=GrantTargetType.RESOURCE,
                resource_ref=denied_resource,
                reason="reviewer must not use the second supporting record",
            )
            session.commit()

        with TestClient(app) as client:
            first = client.post(
                "/v1/kc/search",
                headers=worker_headers,
                json={"query": "ACL project implementation", "limit": 10},
            )
            assert first.status_code == 200, first.text
            first_payload = first.json()
            assert first_payload["graph"]["state"] == "ready"
            assert first_payload["graph"]["results"]
            assert adapter.project_calls == 1

            projected_segments = tuple(
                segment
                for item in adapter.projected.values()
                for segment in item["segments"]
            )
            assert projected_segments
            assert sensitive_version not in {
                segment.resource_version_ref for segment in projected_segments
            }

            second = client.post(
                "/v1/kc/search",
                headers=worker_headers,
                json={"query": "ACL project implementation", "limit": 10},
            )
            assert second.status_code == 200, second.text
            assert second.json()["graph"]["state"] == "ready"
            assert adapter.project_calls == 1

            status = client.get("/v1/kc/status", headers=worker_headers)
            assert status.status_code == 200, status.text
            assert status.json()["graph"]["state"] == "ready"

            reviewer_search = client.post(
                "/v1/kc/search",
                headers=reviewer_headers,
                json={"query": "ACL project implementation", "limit": 10},
            )
            assert reviewer_search.status_code == 200, reviewer_search.text
            reviewer_payload = reviewer_search.json()
            assert reviewer_payload["graph"]["state"] == "ready"
            # The fake fact depends on every projected source. Denial of only one
            # source must suppress the whole graph fact.
            assert reviewer_payload["graph"]["results"] == []
            assert adapter.project_calls == 1
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


@pytest.mark.postgresql
def test_kcd_graph_provider_failure_degrades_to_lexical_success(tmp_path: Path):
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    store = LocalArtifactStore(tmp_path / "failure-artifacts")
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
        worker_key = principals.issue_service_credential(
            principal_ref=worker.principal_ref,
            label="KC-D failing graph worker",
        ).token
        session.commit()
        authz = AuthorizationKernel(session)
        scope = authz.create_scope(
            actor_principal_ref=owner.principal_ref,
            scope_type=ScopeType.PROJECT,
            scope_key="acl",
            display_name="ACL",
        )
        for operation in (KCOperation.SEARCH, KCOperation.STORE):
            _allow(
                authz,
                owner_ref=owner.principal_ref,
                principal_ref=worker.principal_ref,
                operation=operation,
                target_type=GrantTargetType.GLOBAL,
            )
            _allow(
                authz,
                owner_ref=owner.principal_ref,
                principal_ref=worker.principal_ref,
                operation=operation,
                target_type=GrantTargetType.SCOPE,
                scope_ref=scope.scope_ref,
            )
        session.commit()

    headers = {
        "X-Knowledge-Key": worker_key,
        "X-Knowledge-Scope": str(scope.scope_ref),
    }
    seed_app = create_app(
        session_factory=sessions,
        artifact_store=store,
        bootstrap_admission=bootstrap,
        consumer_admission=admission,
    )
    try:
        with TestClient(seed_app) as client:
            stored = client.post(
                "/v1/kc/store",
                headers={**headers, "Idempotency-Key": "kcd-failure-seed"},
                json={
                    "content": "lexical fallback survives graph provider failure",
                    "project": "acl",
                    "source_type": "user_note",
                    "source_id": "kcd-failure-note",
                },
            )
            assert stored.status_code == 201, stored.text

        failing = FakeProductionGraphAdapter(
            config_digest="sha256:kcd-failing-adapter",
            fail=True,
        )
        runtime = KnowledgeGraphRuntime(
            session_factory=sessions,
            artifact_store=store,
            adapter=failing,
            max_attempts=2,
        )
        app = create_app(
            session_factory=sessions,
            artifact_store=store,
            bootstrap_admission=bootstrap,
            consumer_admission=admission,
            graph_runtime=runtime,
        )
        with TestClient(app) as client:
            response = client.post(
                "/v1/kc/search",
                headers=headers,
                json={"query": "lexical fallback", "limit": 10},
            )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["results"]
        assert payload["graph"]["state"] == "unavailable"
        assert failing.project_calls == 2
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()
