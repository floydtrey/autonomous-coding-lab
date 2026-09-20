from __future__ import annotations

from uuid import uuid4

import pytest

from knowledge_core.application.profiles import ProfileKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError, TypedValue
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)


CALLER = "profile-gate-test"


def _fixture(tmp_path):
    engine = create_database_engine(
        f"sqlite+pysqlite:///{tmp_path / 'profiles.db'}",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    session_factory = create_session_factory(engine)
    artifact_store = LocalArtifactStore(tmp_path / "artifacts")
    session = session_factory()
    kernel = ProfileKnowledgeKernel(session, artifact_store=artifact_store)
    core = kernel.bootstrap_core_test_profile()
    return engine, session, kernel, core


def _term_by_name(items, stable_name):
    return next(item for item in items if item.stable_name == stable_name)


def test_gate17_profile_activation_preserves_old_assertion_semantics(tmp_path):
    engine, session, kernel, core = _fixture(tmp_path)
    try:
        v1_activation = kernel.activate_profile_revision_operation(
            operation_id=uuid4(),
            profile_ref=core.profile_ref,
            profile_revision_ref=core.profile_revision_ref,
            caller_principal_ref=CALLER,
            expected_revision=kernel.current_revision(),
        )
        assert v1_activation.profile_revision_ref == core.profile_revision_ref

        person_v1 = kernel.create_entity_operation(
            operation_id=uuid4(),
            kind_revision_ref=core.person_kind_revision_ref,
            caller_principal_ref=CALLER,
            expected_revision=kernel.current_revision(),
        )
        assertion_v1 = kernel.append_assertion_operation(
            operation_id=uuid4(),
            subject_ref=person_v1,
            predicate_revision_ref=core.has_name_predicate_revision_ref,
            profile_revision_ref=core.profile_revision_ref,
            value=TypedValue.text("Robert Smith"),
            caller_principal_ref=CALLER,
            expected_revision=kernel.current_revision(),
        )
        before = kernel.resolve_assertion_semantics(assertion_v1)
        assert before.profile_version_label == "1"
        assert before.profile_revision_ref == core.profile_revision_ref
        assert before.predicate_revision_ref == core.has_name_predicate_revision_ref
        assert before.predicate_stable_name == "has_name"
        assert before.predicate_value_shape == "scalar"

        v2 = kernel.create_profile_revision_operation(
            operation_id=uuid4(),
            profile_ref=core.profile_ref,
            source_profile_revision_ref=core.profile_revision_ref,
            version_label="2",
            caller_principal_ref=CALLER,
            expected_revision=kernel.current_revision(),
        )
        vocabulary_v2 = kernel.profile_vocabulary(
            profile_revision_ref=v2.profile_revision_ref
        )
        person_kind_v2 = _term_by_name(vocabulary_v2.kinds, "person")
        has_name_v2 = _term_by_name(vocabulary_v2.predicates, "has_name")

        assert person_kind_v2.revision_ref != core.person_kind_revision_ref
        assert has_name_v2.revision_ref != core.has_name_predicate_revision_ref
        assert has_name_v2.semantic_ref == before.predicate_ref
        assert has_name_v2.value_shape == "scalar"

        kernel.activate_profile_revision_operation(
            operation_id=uuid4(),
            profile_ref=core.profile_ref,
            profile_revision_ref=v2.profile_revision_ref,
            caller_principal_ref=CALLER,
            expected_revision=kernel.current_revision(),
        )
        active = kernel.active_profile_revision(profile_ref=core.profile_ref)
        assert active.profile_revision_ref == v2.profile_revision_ref

        activation_history = kernel.profile_activation_history(
            profile_ref=core.profile_ref
        )
        assert [item.profile_revision_ref for item in activation_history] == [
            core.profile_revision_ref,
            v2.profile_revision_ref,
        ]

        after = kernel.resolve_assertion_semantics(assertion_v1)
        assert after == before

        person_v2 = kernel.create_entity_operation(
            operation_id=uuid4(),
            kind_revision_ref=person_kind_v2.revision_ref,
            caller_principal_ref=CALLER,
            expected_revision=kernel.current_revision(),
        )
        assertion_v2 = kernel.append_assertion_operation(
            operation_id=uuid4(),
            subject_ref=person_v2,
            predicate_revision_ref=has_name_v2.revision_ref,
            profile_revision_ref=v2.profile_revision_ref,
            value=TypedValue.text("Alice Smith"),
            caller_principal_ref=CALLER,
            expected_revision=kernel.current_revision(),
        )
        semantics_v2 = kernel.resolve_assertion_semantics(assertion_v2)
        assert semantics_v2.profile_version_label == "2"
        assert semantics_v2.profile_revision_ref == v2.profile_revision_ref
        assert semantics_v2.predicate_ref == before.predicate_ref

        assert kernel.resolve_assertion_semantics(assertion_v1) == before
    finally:
        session.close()
        engine.dispose()


def test_gate17_material_predicate_shape_change_requires_new_identity(tmp_path):
    engine, session, kernel, core = _fixture(tmp_path)
    try:
        old_predicate = kernel.read_predicate_revision(
            core.has_name_predicate_revision_ref
        )
        v2 = kernel.create_profile_revision_operation(
            operation_id=uuid4(),
            profile_ref=core.profile_ref,
            source_profile_revision_ref=core.profile_revision_ref,
            version_label="2",
            caller_principal_ref=CALLER,
            expected_revision=kernel.current_revision(),
        )

        revision_before_rejected_change = kernel.current_revision()
        with pytest.raises(
            KnowledgeInvariantError,
            match="material predicate meaning change requires a new semantic predicate identity",
        ):
            kernel.create_predicate_revision_operation(
                operation_id=uuid4(),
                predicate_ref=old_predicate.semantic_ref,
                profile_revision_ref=v2.profile_revision_ref,
                value_shape="reference",
                caller_principal_ref=CALLER,
                expected_revision=revision_before_rejected_change,
            )
        assert kernel.current_revision() == revision_before_rejected_change

        replacement_identity = kernel.create_predicate_identity_operation(
            operation_id=uuid4(),
            profile_revision_ref=v2.profile_revision_ref,
            stable_name="has_name_reference",
            value_shape="reference",
            caller_principal_ref=CALLER,
            expected_revision=kernel.current_revision(),
        )
        assert replacement_identity.semantic_ref != old_predicate.semantic_ref
        assert replacement_identity.revision_ref != old_predicate.revision_ref
        assert replacement_identity.value_shape == "reference"
    finally:
        session.close()
        engine.dispose()


def test_profile_revision_and_activation_operations_are_idempotent(tmp_path):
    engine, session, kernel, core = _fixture(tmp_path)
    try:
        create_operation = uuid4()
        expected = kernel.current_revision()
        first = kernel.create_profile_revision_operation(
            operation_id=create_operation,
            profile_ref=core.profile_ref,
            source_profile_revision_ref=core.profile_revision_ref,
            version_label="2",
            caller_principal_ref=CALLER,
            expected_revision=expected,
        )
        replay = kernel.create_profile_revision_operation(
            operation_id=create_operation,
            profile_ref=core.profile_ref,
            source_profile_revision_ref=core.profile_revision_ref,
            version_label="2",
            caller_principal_ref=CALLER,
            expected_revision=expected,
        )
        assert replay == first

        activation_operation = uuid4()
        activation_expected = kernel.current_revision()
        first_activation = kernel.activate_profile_revision_operation(
            operation_id=activation_operation,
            profile_ref=core.profile_ref,
            profile_revision_ref=first.profile_revision_ref,
            caller_principal_ref=CALLER,
            expected_revision=activation_expected,
        )
        replay_activation = kernel.activate_profile_revision_operation(
            operation_id=activation_operation,
            profile_ref=core.profile_ref,
            profile_revision_ref=first.profile_revision_ref,
            caller_principal_ref=CALLER,
            expected_revision=activation_expected,
        )
        assert replay_activation == first_activation
        assert len(
            kernel.profile_activation_history(profile_ref=core.profile_ref)
        ) == 1
    finally:
        session.close()
        engine.dispose()
