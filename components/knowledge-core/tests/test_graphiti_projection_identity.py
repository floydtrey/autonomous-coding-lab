from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from knowledge_core.application.graph_retrieval import GraphProjectionRetrievalKnowledgeKernel
from knowledge_core.authority.retrieval import (
    RetrievalAuthorityOperation,
    RetrievalAuthorityRequest,
)
from knowledge_core.domain.projection_adapter import (
    ProjectionProviderSourceBinding,
    ProjectionSourceSegment,
)
from knowledge_core.integrations.graphiti import GraphitiLocalConfig, graphiti_partition_key


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

    assert first.behavioral_digest() == secret_change.behavioral_digest()
    assert first.behavioral_digest() != model_change.behavioral_digest()


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
