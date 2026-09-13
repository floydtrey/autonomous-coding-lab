from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from knowledge_core.application.projection_evidence import ProjectionEvidenceKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.projection_evidence import (
    ProjectionAttemptReuseError,
    ProjectionAttemptStateError,
    ProjectionDisposition,
    ProjectionValidationState,
)
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)
from knowledge_core.storage.models import KnowledgeRef
from knowledge_core.storage.projection_models import ProjectionAttempt


def _kernel(tmp_path):
    engine = create_database_engine(
        f"sqlite+pysqlite:///{tmp_path / 'projection-evidence.db'}",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    sessions = create_session_factory(engine)
    store = LocalArtifactStore(tmp_path / "artifacts")
    return engine, sessions, store


def _start(kernel, *, attempt_id, source_ref, source_revision, backend="graph-adapter", config="cfg-a"):
    return kernel.start_projection_attempt(
        attempt_id=attempt_id,
        projection_kind="relationship_graph",
        target_kind="knowledge_relationship_projection",
        namespace_key="acl:project-alpha",
        scope_key="project:alpha",
        backend_identity=backend,
        backend_version="1",
        profile_id="graph-projection-v1",
        profile_digest="sha256:profile-a",
        config_digest=config,
        sources=((source_ref, source_revision),),
    )


def test_projection_attempt_replay_is_idempotent_and_preserves_exact_scope(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionEvidenceKnowledgeKernel(session, artifact_store=store)
            refs = kernel.bootstrap_core_test_profile()
            entity = kernel.create_entity(refs.person_kind_revision_ref)
            highwater = kernel.current_revision()
            attempt_id = uuid4()

            first = _start(
                kernel,
                attempt_id=attempt_id,
                source_ref=entity,
                source_revision=highwater,
            )
            replay = _start(
                kernel,
                attempt_id=attempt_id,
                source_ref=entity,
                source_revision=highwater,
            )

            assert replay == first
            assert first.namespace_key == "acl:project-alpha"
            assert first.scope_key == "project:alpha"
            assert first.sources[0].source_ref == entity
            assert first.sources[0].source_revision_id == highwater
            assert session.scalar(select(func.count()).select_from(ProjectionAttempt)) == 1
    finally:
        engine.dispose()


def test_stable_attempt_identity_rejects_changed_backend_or_config(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionEvidenceKnowledgeKernel(session, artifact_store=store)
            refs = kernel.bootstrap_core_test_profile()
            entity = kernel.create_entity(refs.person_kind_revision_ref)
            highwater = kernel.current_revision()
            attempt_id = uuid4()
            _start(kernel, attempt_id=attempt_id, source_ref=entity, source_revision=highwater)

            with pytest.raises(ProjectionAttemptReuseError):
                _start(
                    kernel,
                    attempt_id=attempt_id,
                    source_ref=entity,
                    source_revision=highwater,
                    config="cfg-b",
                )
    finally:
        engine.dispose()


def test_backend_and_config_changes_are_distinguishable_evidence(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionEvidenceKnowledgeKernel(session, artifact_store=store)
            refs = kernel.bootstrap_core_test_profile()
            entity = kernel.create_entity(refs.person_kind_revision_ref)
            highwater = kernel.current_revision()

            first = _start(
                kernel,
                attempt_id=uuid4(),
                source_ref=entity,
                source_revision=highwater,
                backend="graph-adapter-a",
                config="cfg-a",
            )
            second = _start(
                kernel,
                attempt_id=uuid4(),
                source_ref=entity,
                source_revision=highwater,
                backend="graph-adapter-b",
                config="cfg-b",
            )

            assert first.request_digest != second.request_digest
            assert first.backend_identity != second.backend_identity
            assert first.config_digest != second.config_digest
    finally:
        engine.dispose()


def test_failed_projection_is_durable_without_mutating_canonical_source(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionEvidenceKnowledgeKernel(session, artifact_store=store)
            refs = kernel.bootstrap_core_test_profile()
            entity = kernel.create_entity(refs.person_kind_revision_ref)
            canonical_revision = kernel.current_revision()
            attempt = _start(
                kernel,
                attempt_id=uuid4(),
                source_ref=entity,
                source_revision=canonical_revision,
            )

            failed = kernel.settle_projection_attempt(
                attempt_id=attempt.attempt_id,
                disposition=ProjectionDisposition.FAILED,
                errors=("backend unavailable",),
            )

            assert failed.disposition is ProjectionDisposition.FAILED
            assert failed.errors == ("backend unavailable",)
            assert failed.validation_state is ProjectionValidationState.UNVALIDATED
            assert kernel.current_revision() == canonical_revision
            assert session.get(KnowledgeRef, entity) is not None
    finally:
        engine.dispose()


def test_incomplete_projection_and_settlement_replay_are_durable(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionEvidenceKnowledgeKernel(session, artifact_store=store)
            refs = kernel.bootstrap_core_test_profile()
            entity = kernel.create_entity(refs.person_kind_revision_ref)
            highwater = kernel.current_revision()
            attempt = _start(
                kernel,
                attempt_id=uuid4(),
                source_ref=entity,
                source_revision=highwater,
            )

            settled = kernel.settle_projection_attempt(
                attempt_id=attempt.attempt_id,
                disposition=ProjectionDisposition.INCOMPLETE,
                warnings=("missing relationship endpoint",),
            )
            replay = kernel.settle_projection_attempt(
                attempt_id=attempt.attempt_id,
                disposition=ProjectionDisposition.INCOMPLETE,
                warnings=("missing relationship endpoint",),
            )

            assert replay == settled
            with pytest.raises(ProjectionAttemptStateError):
                kernel.settle_projection_attempt(
                    attempt_id=attempt.attempt_id,
                    disposition=ProjectionDisposition.SUCCEEDED,
                )
    finally:
        engine.dispose()


def test_backend_success_is_explicitly_not_trusted_until_validation(tmp_path):
    engine, sessions, store = _kernel(tmp_path)
    try:
        with sessions() as session:
            kernel = ProjectionEvidenceKnowledgeKernel(session, artifact_store=store)
            refs = kernel.bootstrap_core_test_profile()
            entity = kernel.create_entity(refs.person_kind_revision_ref)
            highwater = kernel.current_revision()
            attempt = _start(
                kernel,
                attempt_id=uuid4(),
                source_ref=entity,
                source_revision=highwater,
            )

            success = kernel.settle_projection_attempt(
                attempt_id=attempt.attempt_id,
                disposition=ProjectionDisposition.SUCCEEDED,
            )

            assert success.disposition is ProjectionDisposition.SUCCEEDED
            assert success.validation_state is ProjectionValidationState.UNVALIDATED
    finally:
        engine.dispose()
