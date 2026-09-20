from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from knowledge_core.application.assertions import KnowledgeKernel
from knowledge_core.domain.assertions import (
    KnowledgeInvariantError,
    TransitionType,
    TypedValue,
    ValueKind,
)
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)
from knowledge_core.storage.models import Assertion, AssertionTransition, AssertionValue


@pytest.fixture()
def kernel():
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    session = create_session_factory(engine)()
    service = KnowledgeKernel(session)
    refs = service.bootstrap_core_test_profile()
    try:
        yield service, refs, session
    finally:
        session.close()
        engine.dispose()


def test_typed_scalar_assertion_pins_exact_profile_and_predicate_revision(kernel):
    service, refs, session = kernel
    robert = service.create_entity(refs.person_kind_revision_ref)

    assertion_ref = service.append_assertion(
        subject_ref=robert,
        predicate_revision_ref=refs.has_name_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.text("Robert Smith"),
    )

    snapshot = service.read_assertion(assertion_ref)
    row = session.get(AssertionValue, assertion_ref)

    assert snapshot.subject_ref == robert
    assert snapshot.profile_revision_ref == refs.profile_revision_ref
    assert snapshot.predicate_revision_ref == refs.has_name_predicate_revision_ref
    assert snapshot.value.kind is ValueKind.TEXT
    assert snapshot.value.value == "Robert Smith"
    assert row.text_value == "Robert Smith"
    assert row.reference_value is None
    assert row.numeric_value is None
    assert row.boolean_value is None
    assert row.date_value is None
    assert row.timestamp_value is None


def test_reference_assertion_requires_real_reference_and_reference_predicate(kernel):
    service, refs, _session = kernel
    robert = service.create_entity(refs.person_kind_revision_ref)
    acme = service.create_entity(refs.organization_kind_revision_ref)

    assertion_ref = service.append_assertion(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.reference(acme),
    )
    assert service.read_assertion(assertion_ref).value == TypedValue.reference(acme)

    with pytest.raises(KnowledgeInvariantError):
        service.append_assertion(
            subject_ref=robert,
            predicate_revision_ref=refs.works_for_predicate_revision_ref,
            profile_revision_ref=refs.profile_revision_ref,
            value=TypedValue.text("Acme"),
        )

    with pytest.raises(KnowledgeInvariantError):
        service.append_assertion(
            subject_ref=robert,
            predicate_revision_ref=refs.works_for_predicate_revision_ref,
            profile_revision_ref=refs.profile_revision_ref,
            value=TypedValue.reference(uuid4()),
        )


def test_correction_appends_replacement_without_overwriting_source(kernel):
    service, refs, session = kernel
    robert = service.create_entity(refs.person_kind_revision_ref)
    acme = service.create_entity(refs.organization_kind_revision_ref)
    betacorp = service.create_entity(refs.organization_kind_revision_ref)

    original_ref = service.append_assertion(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.reference(acme),
    )
    original_before = service.read_assertion(original_ref)

    correction = service.correct_assertion(
        source_assertion_ref=original_ref,
        replacement_value=TypedValue.reference(betacorp),
        correction_kind_revision_ref=refs.correction_kind_revision_ref,
    )

    original_after = service.read_assertion(original_ref)
    replacement = service.read_assertion(correction.replacement_assertion_ref)

    assert original_after == original_before
    assert replacement.assertion_ref != original_ref
    assert replacement.value == TypedValue.reference(betacorp)
    assert correction.transition_type is TransitionType.CORRECTS
    assert correction.source_assertion_ref == original_ref
    assert correction.replacement_assertion_ref == replacement.assertion_ref
    assert correction.created_revision_id == replacement.created_revision_id
    assert session.scalar(select(func.count()).select_from(Assertion)) == 2


def test_explicit_reversal_restores_original_by_transition_and_keeps_history(kernel):
    service, refs, session = kernel
    robert = service.create_entity(refs.person_kind_revision_ref)
    acme = service.create_entity(refs.organization_kind_revision_ref)
    betacorp = service.create_entity(refs.organization_kind_revision_ref)

    original_ref = service.append_assertion(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.reference(acme),
    )
    correction = service.correct_assertion(
        source_assertion_ref=original_ref,
        replacement_value=TypedValue.reference(betacorp),
        correction_kind_revision_ref=refs.correction_kind_revision_ref,
    )
    original_snapshot = service.read_assertion(original_ref)
    mistaken_snapshot = service.read_assertion(correction.replacement_assertion_ref)

    reversal = service.reverse_transition(
        transition_ref=correction.transition_ref,
        correction_kind_revision_ref=refs.correction_kind_revision_ref,
    )

    assert reversal.transition_type is TransitionType.RESTORES
    assert reversal.source_assertion_ref == correction.replacement_assertion_ref
    assert reversal.replacement_assertion_ref == original_ref
    assert reversal.reverses_transition_ref == correction.transition_ref
    assert service.read_assertion(original_ref) == original_snapshot
    assert (
        service.read_assertion(correction.replacement_assertion_ref)
        == mistaken_snapshot
    )
    assert session.scalar(select(func.count()).select_from(Assertion)) == 2
    assert session.scalar(select(func.count()).select_from(AssertionTransition)) == 2

    with pytest.raises(KnowledgeInvariantError):
        service.reverse_transition(
            transition_ref=correction.transition_ref,
            correction_kind_revision_ref=refs.correction_kind_revision_ref,
        )
