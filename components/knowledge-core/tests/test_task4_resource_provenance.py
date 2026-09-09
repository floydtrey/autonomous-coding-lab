from __future__ import annotations

from hashlib import sha256

import pytest

from knowledge_core.application.resources import ResourceKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import TypedValue
from knowledge_core.domain.resources import ResourceLocatorKind
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)


@pytest.fixture()
def kernel(tmp_path):
    engine = create_database_engine("sqlite+pysqlite:///:memory:", sqlite_test_mode=True)
    create_test_schema(engine)
    session = create_session_factory(engine)()
    service = ResourceKnowledgeKernel(session, artifact_store=LocalArtifactStore(tmp_path / "artifacts"))
    core_refs = service.bootstrap_core_test_profile()
    resource_refs = service.bootstrap_resource_test_profile()
    try:
        yield service, core_refs, resource_refs, session, tmp_path
    finally:
        session.close()
        engine.dispose()


def test_mutable_path_ingests_distinct_exact_versions(kernel):
    service, _core, resource_refs, _session, tmp_path = kernel
    source = tmp_path / "source.txt"
    logical = service.create_resource(kind_revision_ref=resource_refs.artifact_kind_revision_ref)
    source.write_text("alpha", encoding="utf-8")
    first = service.ingest_resource_version(resource_ref=logical.resource_ref, content=source.read_bytes(), ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref, media_type="text/plain", locator_kind=ResourceLocatorKind.PATH, locator_text=str(source))
    source.write_text("beta", encoding="utf-8")
    second = service.ingest_resource_version(resource_ref=logical.resource_ref, content=source.read_bytes(), ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref, media_type="text/plain", locator_kind=ResourceLocatorKind.PATH, locator_text=str(source))
    assert first.resource_version_ref != second.resource_version_ref
    assert first.resource_ref == second.resource_ref == logical.resource_ref
    assert first.content_digest == sha256(b"alpha").hexdigest()
    assert second.content_digest == sha256(b"beta").hexdigest()
    assert service.artifact_store.read_bytes(first.artifact_key) == b"alpha"
    assert service.artifact_store.read_bytes(second.artifact_key) == b"beta"
    locators = service.locator_history(resource_ref=logical.resource_ref)
    assert [row.locator_text for row in locators] == [str(source), str(source)]
    assert [row.resource_version_ref for row in locators] == [first.resource_version_ref, second.resource_version_ref]


def test_assertion_explanation_stays_pinned_to_consumed_version(kernel):
    service, core_refs, resource_refs, _session, tmp_path = kernel
    robert = service.create_entity(core_refs.person_kind_revision_ref)
    assertion_ref = service.append_assertion(subject_ref=robert, predicate_revision_ref=core_refs.has_name_predicate_revision_ref, profile_revision_ref=core_refs.profile_revision_ref, value=TypedValue.text("Robert Smith"))
    source = tmp_path / "evidence.txt"
    logical = service.create_resource(kind_revision_ref=resource_refs.artifact_kind_revision_ref)
    source.write_text("Robert Smith", encoding="utf-8")
    consumed = service.ingest_resource_version(resource_ref=logical.resource_ref, content=source.read_bytes(), ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref, media_type="text/plain", locator_kind=ResourceLocatorKind.PATH, locator_text=str(source))
    service.link_assertion_evidence(assertion_ref=assertion_ref, resource_version_ref=consumed.resource_version_ref, relation_revision_ref=resource_refs.supports_claim_relation_revision_ref)
    source.write_text("Different later bytes", encoding="utf-8")
    later = service.ingest_resource_version(resource_ref=logical.resource_ref, content=source.read_bytes(), ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref, media_type="text/plain", locator_kind=ResourceLocatorKind.PATH, locator_text=str(source))
    explanation = service.explain_assertion(assertion_ref=assertion_ref)
    assert len(explanation) == 1
    assert explanation[0].resource_version.resource_version_ref == consumed.resource_version_ref
    assert explanation[0].resource_version.content_digest == sha256(b"Robert Smith").hexdigest()
    assert explanation[0].resource_version.resource_version_ref != later.resource_version_ref
    consumed_impact = service.impact_from_resource_version(resource_version_ref=consumed.resource_version_ref)
    later_impact = service.impact_from_resource_version(resource_version_ref=later.resource_version_ref)
    assert [(item.dependent_ref, item.dependent_ref_kind) for item in consumed_impact] == [(assertion_ref, "assertion")]
    assert later_impact == []


def test_same_bytes_do_not_merge_distinct_logical_resources(kernel):
    service, _core, resource_refs, _session, _tmp_path = kernel
    first_resource = service.create_resource(kind_revision_ref=resource_refs.artifact_kind_revision_ref)
    second_resource = service.create_resource(kind_revision_ref=resource_refs.artifact_kind_revision_ref)
    first_version = service.ingest_resource_version(resource_ref=first_resource.resource_ref, content=b"identical bytes", ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref)
    second_version = service.ingest_resource_version(resource_ref=second_resource.resource_ref, content=b"identical bytes", ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref)
    assert first_resource.resource_ref != second_resource.resource_ref
    assert first_version.resource_version_ref != second_version.resource_version_ref
    assert first_version.content_digest == second_version.content_digest
    assert first_version.artifact_key == second_version.artifact_key


def test_reingesting_same_exact_version_is_stable(kernel):
    service, _core, resource_refs, _session, _tmp_path = kernel
    logical = service.create_resource(kind_revision_ref=resource_refs.artifact_kind_revision_ref)
    first = service.ingest_resource_version(resource_ref=logical.resource_ref, content=b"stable content", ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref)
    revision_after_first = service.current_revision()
    second = service.ingest_resource_version(resource_ref=logical.resource_ref, content=b"stable content", ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref)
    assert second == first
    assert service.current_revision() == revision_after_first
