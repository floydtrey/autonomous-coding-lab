from __future__ import annotations

import asyncio
import builtins
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from knowledge_core.application.graph_retrieval import GraphProjectionRetrievalKnowledgeKernel
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
)
from knowledge_core.domain.projection_adapter import (
    ProjectionLifecycleEdge,
    ProjectionLifecycleInventory,
    ProjectionProviderSourceBinding,
    ProjectionSourceSegment,
)
from knowledge_core.domain.projection_evidence import ProjectionDisposition
from knowledge_core.domain.projection_validation import (
    ProjectionCheckOutcome,
    ProjectionValidationOutcome,
)
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core_providers import graphiti as graphiti_provider
from knowledge_core_providers.graphiti import (
    GraphitiLocalConfig,
    GraphitiProjectionAdapter,
    GraphitiProjectionValidator,
    _resolve_governed_document_edges,
    graphiti_partition_key,
)


def _segment() -> ProjectionSourceSegment:
    return ProjectionSourceSegment(
        generation_id=uuid4(),
        resource_version_ref=uuid4(),
        source_revision_id=42,
        segment_key="sha256:segment-a",
        segment_ordinal=0,
        source_slice_sha256="a" * 64,
        source_byte_start=0,
        source_byte_end=12,
        source_line_start=1,
        source_line_end=1,
        effective_lifecycle_state="current",
        source_repository_key="repository-a",
        source_document_key="document-a",
        source_path="docs/current.md",
        source_version="abc123",
        heading_path=(),
        reference_time=datetime(2026, 9, 13, tzinfo=timezone.utc),
        body="Alpha fact.",
    )


def test_live_graph_modules_import_without_installing_optional_graphiti_dependency():
    # CI intentionally does not install the live Graphiti extra. Importing the KC
    # contracts must therefore remain independent from the external backend package.
    assert GraphProjectionRetrievalKnowledgeKernel.__name__ == "GraphProjectionRetrievalKnowledgeKernel"


def test_graphiti_partition_is_stable_and_rotates_with_scope_or_generation_profile():
    first = graphiti_partition_key(
        namespace_key="kc:acl",
        scope_key="project:alpha",
        projection_profile_id="sr2-generation:one",
    )
    replay = graphiti_partition_key(
        namespace_key="kc:acl",
        scope_key="project:alpha",
        projection_profile_id="sr2-generation:one",
    )
    changed_scope = graphiti_partition_key(
        namespace_key="kc:acl",
        scope_key="project:beta",
        projection_profile_id="sr2-generation:one",
    )
    changed_profile = graphiti_partition_key(
        namespace_key="kc:acl",
        scope_key="project:alpha",
        projection_profile_id="sr2-generation:two",
    )

    assert first == replay
    assert first.startswith("kc_")
    assert first != changed_scope
    assert first != changed_profile
    assert all(ch.islower() or ch.isdigit() or ch == "_" for ch in first)


def test_provider_source_binding_keeps_opaque_provider_id_as_evidence_only():
    segment = _segment()
    binding = ProjectionProviderSourceBinding(
        resource_version_ref=segment.resource_version_ref,
        source_revision_id=segment.source_revision_id,
        segment_key=segment.segment_key,
        source_slice_sha256=segment.source_slice_sha256,
        provider_partition_key="kc_deadbeef",
        provider_source_id="provider-minted-episode-id",
    )

    assert binding.resource_version_ref == segment.resource_version_ref
    assert binding.segment_key == segment.segment_key
    assert binding.provider_source_id == "provider-minted-episode-id"
    # KC must not silently reinterpret provider-owned identifiers as KC UUID identity.
    with pytest.raises(ValueError):
        UUID(binding.provider_source_id)


def test_graphiti_behavior_digest_excludes_secrets_but_binds_behavior():
    first = GraphitiLocalConfig(
        falkor_password="secret-a",
        ollama_api_key="key-a",
    )
    secret_change = GraphitiLocalConfig(
        falkor_password="secret-b",
        ollama_api_key="key-b",
    )
    model_change = GraphitiLocalConfig(
        falkor_password="secret-b",
        ollama_api_key="key-b",
        llm_model="another-qualified-model",
    )
    temperature_change = GraphitiLocalConfig(temperature=1.0)
    policy_change = GraphitiLocalConfig(projection_policy="governed-document-v2")

    assert first.behavioral_digest() == secret_change.behavioral_digest()
    assert first.behavioral_digest() != model_change.behavioral_digest()
    assert first.behavioral_digest() != temperature_change.behavioral_digest()
    assert first.behavioral_digest() != policy_change.behavioral_digest()


def test_default_graphiti_config_uses_governed_document_policy_at_temperature_zero():
    config = GraphitiLocalConfig()

    assert config.projection_policy == "governed-document-v1"
    assert config.temperature == 0.0


def test_graphiti_adapter_rejects_unsupported_projection_policy():
    with pytest.raises(KnowledgeInvariantError, match="unsupported Graphiti projection policy"):
        GraphitiProjectionAdapter(
            GraphitiLocalConfig(projection_policy="graphiti-semantic-defaults")
        )


def test_constructed_graphiti_client_receives_temperature_zero(monkeypatch):
    class FakeLLMConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeComponent:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeGraphiti(FakeComponent):
        pass

    real_import = builtins.__import__
    fake_imports = {
        "graphiti_core": SimpleNamespace(Graphiti=FakeGraphiti),
        "graphiti_core.cross_encoder.openai_reranker_client": SimpleNamespace(
            OpenAIRerankerClient=FakeComponent
        ),
        "graphiti_core.driver.falkordb_driver": SimpleNamespace(FalkorDriver=FakeComponent),
        "graphiti_core.embedder.openai": SimpleNamespace(
            OpenAIEmbedder=FakeComponent,
            OpenAIEmbedderConfig=FakeComponent,
        ),
        "graphiti_core.llm_client.config": SimpleNamespace(LLMConfig=FakeLLMConfig),
    }

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in fake_imports:
            return fake_imports[name]
        return real_import(name, globals, locals, fromlist, level)

    def fake_client(config, *, max_tokens, structured_output_mode):
        return SimpleNamespace(
            config=config,
            client=object(),
            max_tokens=max_tokens,
            structured_output_mode=structured_output_mode,
        )

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(graphiti_provider, "_require_graphiti_version", lambda: None)
    monkeypatch.setattr(graphiti_provider, "_reasoning_disabled_client", fake_client)

    graphiti = GraphitiProjectionAdapter()._build_graphiti(partition_key="kc_test")

    assert graphiti.llm_client.config.temperature == 0.0
    assert type(graphiti).__name__ == "GovernedDocumentGraphiti"


@dataclass
class _FakeEdge:
    uuid: str
    group_id: str
    source_node_uuid: str
    target_node_uuid: str
    name: str
    fact: str
    episodes: list[str] = field(default_factory=list)
    invalid_at: datetime | None = None
    expired_at: datetime | None = None
    valid_at: datetime | None = None
    fact_embedding: list[float] | None = None


def test_governed_edge_resolution_is_exact_and_preserves_source_contributions():
    existing = _FakeEdge(
        uuid="edge-existing",
        group_id="kc_test",
        source_node_uuid="source",
        target_node_uuid="target",
        name="DOCUMENTS",
        fact="The policy documents the accepted boundary.",
        episodes=["episode-old"],
    )
    duplicate = _FakeEdge(
        uuid="edge-new-duplicate",
        group_id="kc_test",
        source_node_uuid="source",
        target_node_uuid="target",
        name="documents",
        fact="  The policy documents   the accepted boundary. ",
        episodes=["episode-new"],
        invalid_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        expired_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    repeated_in_episode = _FakeEdge(
        uuid="edge-new-repeated",
        group_id="kc_test",
        source_node_uuid="source",
        target_node_uuid="target",
        name="DOCUMENTS",
        fact="The policy documents the accepted boundary.",
        episodes=["episode-second-source"],
    )
    compatible_paraphrase = _FakeEdge(
        uuid="edge-compatible",
        group_id="kc_test",
        source_node_uuid="source",
        target_node_uuid="target",
        name="HAS_ACCEPTANCE_STATE",
        fact=(
            "The G1-G21 prerequisite has been satisfied and checkpointed, "
            "enabling the next SR-2 task SR2-G22."
        ),
        episodes=["episode-new"],
        invalid_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        expired_at=datetime(2026, 1, 4, tzinfo=timezone.utc),
    )
    embedded: list[_FakeEdge] = []

    async def get_between_nodes(driver, source_node_uuid, target_node_uuid):
        assert driver == "driver"
        assert (source_node_uuid, target_node_uuid) == ("source", "target")
        return [existing]

    async def embed_edges(embedder, edges):
        assert embedder == "embedder"
        embedded.extend(edges)

    resolved, invalidated, new = asyncio.run(
        _resolve_governed_document_edges(
            clients=SimpleNamespace(
                driver="driver",
                embedder="embedder",
                llm_client=pytest.fail,
            ),
            extracted_edges=[duplicate, repeated_in_episode, compatible_paraphrase],
            episode=SimpleNamespace(uuid="episode-new"),
            get_between_nodes=get_between_nodes,
            embed_edges=embed_edges,
        )
    )

    assert resolved == [existing, compatible_paraphrase]
    assert invalidated == []
    assert new == [compatible_paraphrase]
    assert existing.episodes == ["episode-new", "episode-old", "episode-second-source"]
    assert compatible_paraphrase.invalid_at is None
    assert compatible_paraphrase.expired_at is None
    assert embedded == resolved


def test_governed_edge_resolution_does_not_revive_retired_exact_match():
    retired = _FakeEdge(
        uuid="edge-retired",
        group_id="kc_test",
        source_node_uuid="source",
        target_node_uuid="target",
        name="DOCUMENTS",
        fact="The policy documents the accepted boundary.",
        episodes=["episode-retired"],
        invalid_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        expired_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )
    extracted = _FakeEdge(
        uuid="edge-new",
        group_id="kc_test",
        source_node_uuid="source",
        target_node_uuid="target",
        name="DOCUMENTS",
        fact="The policy documents the accepted boundary.",
        episodes=["episode-current"],
    )

    async def get_between_nodes(*args):
        return [retired]

    async def embed_edges(*args):
        return None

    resolved, invalidated, new = asyncio.run(
        _resolve_governed_document_edges(
            clients=SimpleNamespace(driver=object(), embedder=object()),
            extracted_edges=[extracted],
            episode=SimpleNamespace(uuid="episode-current"),
            get_between_nodes=get_between_nodes,
            embed_edges=embed_edges,
        )
    )

    assert resolved == [extracted]
    assert invalidated == []
    assert new == [extracted]
    assert retired.invalid_at == datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert retired.expired_at == datetime(2025, 1, 2, tzinfo=timezone.utc)


class _LifecycleValidationAdapter:
    def __init__(self, inventory: ProjectionLifecycleInventory):
        self._descriptor = GraphitiProjectionAdapter().descriptor
        self._inventory = inventory

    @property
    def descriptor(self):
        return self._descriptor

    def partition_key(self, *, namespace_key, scope_key, projection_profile_id):
        return graphiti_partition_key(
            namespace_key=namespace_key,
            scope_key=scope_key,
            projection_profile_id=projection_profile_id,
        )

    async def existing_source_keys(self, *, source_keys, **kwargs):
        return frozenset(source_keys)

    async def lifecycle_inventory(self, **kwargs):
        return self._inventory

    async def search(self, **kwargs):
        return ()


def _validate_lifecycle_inventory(inventory: ProjectionLifecycleInventory):
    segment = _segment()
    namespace_key = "kc:acl"
    scope_key = "project:alpha"
    profile_id = "sr2-generation:one"
    partition = graphiti_partition_key(
        namespace_key=namespace_key,
        scope_key=scope_key,
        projection_profile_id=profile_id,
    )
    binding = ProjectionProviderSourceBinding(
        resource_version_ref=segment.resource_version_ref,
        source_revision_id=segment.source_revision_id,
        segment_key=segment.segment_key,
        source_slice_sha256=segment.source_slice_sha256,
        provider_partition_key=partition,
        provider_source_id="episode-current",
    )
    adapter = _LifecycleValidationAdapter(inventory)
    validator = GraphitiProjectionValidator(
        adapter=adapter,
        segments=(segment,),
        source_bindings=(binding,),
        namespace_key=namespace_key,
        scope_key=scope_key,
        projection_profile_id=profile_id,
        probe_query="accepted boundary",
    )
    report = validator.validate(
        SimpleNamespace(
            attempt_id=uuid4(),
            backend_identity=adapter.descriptor.backend_identity,
            backend_version=adapter.descriptor.backend_version,
            config_digest=adapter.descriptor.config_digest,
            namespace_key=namespace_key,
            scope_key=scope_key,
            profile_id=profile_id,
            warnings=(),
            disposition=ProjectionDisposition.SUCCEEDED,
        )
    )
    return adapter, validator, report


def test_graphiti_validator_requires_complete_active_lifecycle_inventory():
    partition = graphiti_partition_key(
        namespace_key="kc:acl",
        scope_key="project:alpha",
        projection_profile_id="sr2-generation:one",
    )
    adapter, validator, report = _validate_lifecycle_inventory(
        ProjectionLifecycleInventory(
            partition_key=partition,
            complete=True,
            edges=(
                ProjectionLifecycleEdge(
                    provider_edge_id="edge-current",
                    partition_key=partition,
                    source_correlation_keys=("episode-current",),
                    invalid_at=None,
                    expired_at=None,
                ),
            ),
        )
    )

    assert report.outcome is ProjectionValidationOutcome.VALIDATED
    lifecycle_check = next(
        check for check in report.checks if check.check_code == "governed-lifecycle-inventory"
    )
    assert lifecycle_check.outcome is ProjectionCheckOutcome.PASSED
    assert lifecycle_check.evidence["edge_count"] == 1
    assert lifecycle_check.evidence["inventory_digest"].startswith("sha256:")
    requirement = adapter.descriptor.validation_requirement
    assert requirement is not None
    assert validator.descriptor.validator_identity == requirement.validator_identity
    assert validator.descriptor.validator_version == requirement.validator_version
    assert validator.descriptor.ruleset_id == requirement.ruleset_id
    assert validator.descriptor.ruleset_digest == requirement.ruleset_digest


@pytest.mark.parametrize(
    ("inventory", "expected_outcome", "expected_check_outcome"),
    (
        (
            ProjectionLifecycleInventory(
                partition_key=graphiti_partition_key(
                    namespace_key="kc:acl",
                    scope_key="project:alpha",
                    projection_profile_id="sr2-generation:one",
                ),
                complete=True,
                edges=(
                    ProjectionLifecycleEdge(
                        provider_edge_id="edge-retired",
                        partition_key=graphiti_partition_key(
                            namespace_key="kc:acl",
                            scope_key="project:alpha",
                            projection_profile_id="sr2-generation:one",
                        ),
                        source_correlation_keys=("episode-current",),
                        invalid_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                        expired_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                    ),
                ),
            ),
            ProjectionValidationOutcome.REJECTED,
            ProjectionCheckOutcome.FAILED,
        ),
        (
            ProjectionLifecycleInventory(
                partition_key="kc_unavailable",
                complete=False,
                edges=(),
                error="provider inventory unavailable",
            ),
            ProjectionValidationOutcome.QUARANTINED,
            ProjectionCheckOutcome.INDETERMINATE,
        ),
    ),
)
def test_graphiti_validator_rejects_retirement_and_quarantines_missing_inventory(
    inventory,
    expected_outcome,
    expected_check_outcome,
):
    _, _, report = _validate_lifecycle_inventory(inventory)

    assert report.outcome is expected_outcome
    lifecycle_check = next(
        check for check in report.checks if check.check_code == "governed-lifecycle-inventory"
    )
    assert lifecycle_check.outcome is expected_check_outcome


def test_graph_authority_request_requires_explicit_namespace_and_scope():
    with pytest.raises(ValueError):
        RetrievalAuthorityRequest(
            caller_principal_ref="caller",
            operation=RetrievalAuthorityOperation.SEARCH_GRAPH,
            limit=10,
            include_superseded=False,
        )

    request = RetrievalAuthorityRequest(
        caller_principal_ref="caller",
        operation=RetrievalAuthorityOperation.SEARCH_GRAPH,
        limit=10,
        include_superseded=False,
        namespace_key="kc:acl",
        scope_key="project:alpha",
    )
    assert request.namespace_key == "kc:acl"
    assert request.scope_key == "project:alpha"


def test_text_authority_contract_remains_backward_compatible():
    request = RetrievalAuthorityRequest(
        caller_principal_ref="caller",
        operation=RetrievalAuthorityOperation.SEARCH_TEXT,
        limit=10,
        include_superseded=False,
    )
    assert request.namespace_key is None
    assert request.scope_key is None
