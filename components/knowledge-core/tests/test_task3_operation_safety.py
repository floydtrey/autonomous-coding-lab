from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from knowledge_core.application.operations import OperationKnowledgeKernel
from knowledge_core.domain.operations import OperationReuseError, StaleWriteError
from knowledge_core.domain.assertions import TransitionType, TypedValue
from knowledge_core.storage.control_models import Operation
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)
from knowledge_core.storage.models import Assertion, AssertionTransition, Revision


@pytest.fixture()
def kernel():
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    session = create_session_factory(engine)()
    service = OperationKnowledgeKernel(session)
    refs = service.bootstrap_core_test_profile()
    try:
        yield service, refs, session
    finally:
        session.close()
        engine.dispose()


def test_stale_writer_rejected_without_canonical_transition(kernel):
    service, refs, session = kernel
    robert = service.create_entity(refs.person_kind_revision_ref)
    acme = service.create_entity(refs.organization_kind_revision_ref)
    betacorp = service.create_entity(refs.organization_kind_revision_ref)
    gammacorp = service.create_entity(refs.organization_kind_revision_ref)
    original_ref = service.append_assertion(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.reference(acme),
    )

    shared_revision = service.current_revision()
    first = service.correct_assertion_operation(
        operation_id=uuid4(),
        expected_revision=shared_revision,
        source_assertion_ref=original_ref,
        replacement_value=TypedValue.reference(betacorp),
        correction_kind_revision_ref=refs.correction_kind_revision_ref,
    )
    assert first.transition_type is TransitionType.CORRECTS

    revisions_after_first = service.current_revision()
    transitions_after_first = session.scalar(
        select(func.count()).select_from(AssertionTransition)
    )
    assertions_after_first = session.scalar(select(func.count()).select_from(Assertion))

    stale_operation_id = uuid4()
    with pytest.raises(StaleWriteError) as excinfo:
        service.correct_assertion_operation(
            operation_id=stale_operation_id,
            expected_revision=shared_revision,
            source_assertion_ref=original_ref,
            replacement_value=TypedValue.reference(gammacorp),
            correction_kind_revision_ref=refs.correction_kind_revision_ref,
        )

    assert excinfo.value.expected_revision == shared_revision
    assert excinfo.value.actual_revision == revisions_after_first
    assert service.current_revision() == revisions_after_first
    assert session.scalar(select(func.count()).select_from(AssertionTransition)) == transitions_after_first
    assert session.scalar(select(func.count()).select_from(Assertion)) == assertions_after_first

    operation = session.get(Operation, stale_operation_id)
    assert operation is not None
    assert operation.status == "conflict"
    assert operation.result_revision_id is None
    assert operation.error_code == "STALE_REVISION"


def test_identical_retry_returns_same_assertion_and_one_revision(kernel):
    service, refs, session = kernel
    robert = service.create_entity(refs.person_kind_revision_ref)
    operation_id = uuid4()
    expected_revision = service.current_revision()

    first_ref = service.append_assertion_operation(
        operation_id=operation_id,
        expected_revision=expected_revision,
        subject_ref=robert,
        predicate_revision_ref=refs.has_name_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.text("Robert Smith"),
    )
    revision_after_first = service.current_revision()

    second_ref = service.append_assertion_operation(
        operation_id=operation_id,
        expected_revision=expected_revision,
        subject_ref=robert,
        predicate_revision_ref=refs.has_name_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.text("Robert Smith"),
    )

    assert second_ref == first_ref
    assert service.current_revision() == revision_after_first
    assert session.scalar(
        select(func.count()).select_from(Revision).where(Revision.operation_id == operation_id)
    ) == 1

    operation = session.get(Operation, operation_id)
    assert operation is not None
    assert operation.status == "committed"
    assert operation.result_revision_id == revision_after_first
    assert operation.response_metadata == {"assertion_ref": str(first_ref)}


def test_same_operation_id_with_different_payload_is_rejected(kernel):
    service, refs, session = kernel
    robert = service.create_entity(refs.person_kind_revision_ref)
    operation_id = uuid4()

    first_ref = service.append_assertion_operation(
        operation_id=operation_id,
        subject_ref=robert,
        predicate_revision_ref=refs.has_name_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.text("Robert Smith"),
    )
    revision_after_first = service.current_revision()
    assertion_count = session.scalar(select(func.count()).select_from(Assertion))

    with pytest.raises(OperationReuseError):
        service.append_assertion_operation(
            operation_id=operation_id,
            subject_ref=robert,
            predicate_revision_ref=refs.has_name_predicate_revision_ref,
            profile_revision_ref=refs.profile_revision_ref,
            value=TypedValue.text("Bob Smith"),
        )

    assert service.read_assertion(first_ref).value == TypedValue.text("Robert Smith")
    assert service.current_revision() == revision_after_first
    assert session.scalar(select(func.count()).select_from(Assertion)) == assertion_count


def test_correction_retry_replays_transition_without_duplicate_history(kernel):
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
    operation_id = uuid4()
    expected_revision = service.current_revision()

    first = service.correct_assertion_operation(
        operation_id=operation_id,
        expected_revision=expected_revision,
        source_assertion_ref=original_ref,
        replacement_value=TypedValue.reference(betacorp),
        correction_kind_revision_ref=refs.correction_kind_revision_ref,
    )
    revision_after_first = service.current_revision()

    second = service.correct_assertion_operation(
        operation_id=operation_id,
        expected_revision=expected_revision,
        source_assertion_ref=original_ref,
        replacement_value=TypedValue.reference(betacorp),
        correction_kind_revision_ref=refs.correction_kind_revision_ref,
    )

    assert second == first
    assert service.current_revision() == revision_after_first
    assert session.scalar(select(func.count()).select_from(AssertionTransition)) == 1
    assert session.scalar(
        select(func.count()).select_from(Revision).where(Revision.operation_id == operation_id)
    ) == 1
