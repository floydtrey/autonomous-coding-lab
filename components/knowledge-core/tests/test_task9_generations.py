from __future__ import annotations

from uuid import uuid4

import pytest

from knowledge_core.application.generations import GenerationKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.generations import DerivedKind, GenerationFenceError, GenerationStatus
from knowledge_core.storage.database import create_database_engine, create_session_factory, create_test_schema


def _kernel(tmp_path):
    engine = create_database_engine(
        f"sqlite+pysqlite:///{tmp_path / 'generation.db'}",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    sessions = create_session_factory(engine)
    store = LocalArtifactStore(tmp_path / "artifacts")
    return engine, sessions, store


def test_gate18_stale_generation_cannot_finish_after_new_generation(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=store)
            refs = kernel.bootstrap_core_test_profile()
            entity = kernel.create_entity(refs.person_kind_revision_ref)
            highwater1 = kernel.current_revision()

            old = kernel.start_generation(
                derived_kind=DerivedKind.CURRENT_STATE,
                source_revision_highwater=highwater1,
                profile_revision_ref=refs.profile_revision_ref,
                sources=((entity, highwater1),),
            )
            kernel.mark_generation_stale(generation_id=old.generation_id)

            profile2 = kernel.create_profile_revision_operation(
                operation_id=uuid4(),
                profile_ref=refs.profile_ref,
                source_profile_revision_ref=refs.profile_revision_ref,
                version_label="2",
                caller_principal_ref="generation-test",
            )
            highwater2 = kernel.current_revision()
            new = kernel.start_generation(
                derived_kind=DerivedKind.CURRENT_STATE,
                source_revision_highwater=highwater2,
                profile_revision_ref=profile2.profile_revision_ref,
                sources=((entity, highwater1),),
            )
            settled = kernel.settle_generation(generation_id=new.generation_id)
            assert settled.status is GenerationStatus.CURRENT

            with pytest.raises(GenerationFenceError):
                kernel.settle_generation(generation_id=old.generation_id)

            current = kernel.current_generation(derived_kind=DerivedKind.CURRENT_STATE)
            assert current is not None
            assert current.generation_id == new.generation_id
    finally:
        engine.dispose()


def test_gate18_newer_current_fences_older_builder_even_without_explicit_stale(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=store)
            refs = kernel.bootstrap_core_test_profile()
            highwater = kernel.current_revision()

            old = kernel.start_generation(
                derived_kind=DerivedKind.IDENTITY,
                source_revision_highwater=highwater,
                profile_revision_ref=refs.profile_revision_ref,
            )
            new = kernel.start_generation(
                derived_kind=DerivedKind.IDENTITY,
                source_revision_highwater=highwater,
                profile_revision_ref=refs.profile_revision_ref,
            )
            kernel.settle_generation(generation_id=new.generation_id)

            with pytest.raises(GenerationFenceError):
                kernel.settle_generation(generation_id=old.generation_id)

            assert kernel.read_generation(old.generation_id).status is GenerationStatus.STALE
            assert kernel.current_generation(derived_kind=DerivedKind.IDENTITY).generation_id == new.generation_id
    finally:
        engine.dispose()


def test_newer_generation_supersedes_older_current_atomically(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=store)
            refs = kernel.bootstrap_core_test_profile()
            highwater = kernel.current_revision()
            first = kernel.start_generation(
                derived_kind=DerivedKind.CLASSIFICATION,
                source_revision_highwater=highwater,
                profile_revision_ref=refs.profile_revision_ref,
            )
            first = kernel.settle_generation(generation_id=first.generation_id)

            second = kernel.start_generation(
                derived_kind=DerivedKind.CLASSIFICATION,
                source_revision_highwater=highwater,
                profile_revision_ref=refs.profile_revision_ref,
            )
            second = kernel.settle_generation(generation_id=second.generation_id)

            assert kernel.read_generation(first.generation_id).status is GenerationStatus.SUPERSEDED
            assert second.status is GenerationStatus.CURRENT
            assert second.supersedes_generation == first.generation_id
            assert second.generation_sequence > first.generation_sequence
    finally:
        engine.dispose()


def test_generation_records_exact_source_lineage(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = GenerationKnowledgeKernel(session, artifact_store=store)
            refs = kernel.bootstrap_core_test_profile()
            entity = kernel.create_entity(refs.person_kind_revision_ref)
            highwater = kernel.current_revision()
            generation = kernel.start_generation(
                derived_kind=DerivedKind.OTHER,
                source_revision_highwater=highwater,
                profile_revision_ref=refs.profile_revision_ref,
                sources=((entity, highwater),),
                model_identity="test-model",
                model_version="1",
                config_digest="abc123",
            )
            assert generation.sources[0].source_ref == entity
            assert generation.sources[0].source_revision_id == highwater
            assert generation.profile_revision_ref == refs.profile_revision_ref
            assert generation.model_identity == "test-model"
            assert generation.config_digest == "abc123"
    finally:
        engine.dispose()
