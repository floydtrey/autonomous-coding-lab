from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from knowledge_core.application.history import TemporalKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError, TypedValue
from knowledge_core.domain.temporal import WorldInterval
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)
from knowledge_core.storage.models import Assertion, CurrentAssertion


UTC = timezone.utc


class MutableClock:
    def __init__(self, current: datetime):
        self.current = current

    def __call__(self) -> datetime:
        return self.current

    def set(self, value: datetime) -> None:
        self.current = value


@pytest.fixture()
def kernel():
    clock = MutableClock(datetime(2026, 6, 2, 12, 0, tzinfo=UTC))
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    session = create_session_factory(engine)()
    service = TemporalKnowledgeKernel(session, clock=clock)
    refs = service.bootstrap_core_test_profile()
    try:
        yield service, refs, session, clock
    finally:
        session.close()
        engine.dispose()


def _values(items):
    return {item.assertion.value.value for item in items}


def test_world_time_and_knowledge_time_are_independent(kernel):
    service, refs, _session, clock = kernel
    robert = service.create_entity(refs.person_kind_revision_ref)
    acme = service.create_entity(refs.organization_kind_revision_ref)
    betacorp = service.create_entity(refs.organization_kind_revision_ref)

    original = service.append_assertion(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.reference(acme),
        world_interval=WorldInterval(
            valid_from=datetime(2026, 6, 2, tzinfo=UTC)
        ),
    )
    before_correction = datetime(2026, 7, 1, tzinfo=UTC)

    clock.set(datetime(2026, 9, 8, 12, 0, tzinfo=UTC))
    correction = service.correct_assertion(
        source_assertion_ref=original,
        replacement_value=TypedValue.reference(betacorp),
        correction_kind_revision_ref=refs.correction_kind_revision_ref,
        replacement_world_interval=WorldInterval(
            valid_from=datetime(2026, 5, 15, tzinfo=UTC)
        ),
    )

    may20_old_belief = service.belief(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        world_at=datetime(2026, 5, 20, tzinfo=UTC),
        knowledge_at=before_correction,
    )
    june15_old_belief = service.belief(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        world_at=datetime(2026, 6, 15, tzinfo=UTC),
        knowledge_at=before_correction,
    )
    may20_reconstructed = service.belief(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        world_at=datetime(2026, 5, 20, tzinfo=UTC),
        knowledge_at=datetime(2026, 9, 9, tzinfo=UTC),
    )

    assert may20_old_belief == []
    assert _values(june15_old_belief) == {acme}
    assert _values(may20_reconstructed) == {betacorp}
    assert service.read_bitemporal_assertion(
        correction.replacement_assertion_ref
    ).recorded_at == datetime(2026, 9, 8, 12, 0, tzinfo=UTC)


def test_conflicts_remain_current_and_are_grouped_without_false_certainty(kernel):
    service, refs, session, clock = kernel
    robert = service.create_entity(refs.person_kind_revision_ref)
    acme = service.create_entity(refs.organization_kind_revision_ref)
    betacorp = service.create_entity(refs.organization_kind_revision_ref)

    service.append_assertion(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.reference(acme),
    )
    service.append_assertion(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.reference(betacorp),
    )

    clock.set(datetime(2026, 9, 9, tzinfo=UTC))
    assert service.rebuild_current_projection() == 2
    projected = service.current_projection(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
    )
    rows = session.scalars(
        select(CurrentAssertion).where(CurrentAssertion.subject_ref_id == robert)
    ).all()

    assert _values(projected) == {acme, betacorp}
    assert len(rows) == 2
    assert rows[0].conflict_group_id is not None
    assert rows[0].conflict_group_id == rows[1].conflict_group_id
    assert {row.selection_reason for row in rows} == {"conflict-preserved"}


def test_correction_and_reversal_drive_projection_without_rewriting_history(kernel):
    service, refs, session, clock = kernel
    robert = service.create_entity(refs.person_kind_revision_ref)
    acme = service.create_entity(refs.organization_kind_revision_ref)
    betacorp = service.create_entity(refs.organization_kind_revision_ref)

    original = service.append_assertion(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.reference(acme),
    )
    original_before = service.read_assertion(original)

    clock.set(datetime(2026, 7, 1, tzinfo=UTC))
    correction = service.correct_assertion(
        source_assertion_ref=original,
        replacement_value=TypedValue.reference(betacorp),
        correction_kind_revision_ref=refs.correction_kind_revision_ref,
    )
    service.rebuild_current_projection()
    assert _values(service.current_projection()) == {betacorp}

    clock.set(datetime(2026, 8, 1, tzinfo=UTC))
    service.reverse_transition(
        transition_ref=correction.transition_ref,
        correction_kind_revision_ref=refs.correction_kind_revision_ref,
    )
    service.rebuild_current_projection()

    assert _values(service.current_projection()) == {acme}
    assert service.read_assertion(original) == original_before
    assert session.scalar(select(func.count()).select_from(Assertion)) == 2
    assert len(
        service.assertion_history(
            subject_ref=robert,
            predicate_revision_ref=refs.works_for_predicate_revision_ref,
        )
    ) == 2


def test_current_projection_can_be_destroyed_and_rebuilt_identically(kernel):
    service, refs, session, clock = kernel
    robert = service.create_entity(refs.person_kind_revision_ref)
    acme = service.create_entity(refs.organization_kind_revision_ref)
    betacorp = service.create_entity(refs.organization_kind_revision_ref)

    service.append_assertion(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.reference(acme),
    )
    service.append_assertion(
        subject_ref=robert,
        predicate_revision_ref=refs.works_for_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.reference(betacorp),
    )
    clock.set(datetime(2026, 9, 9, tzinfo=UTC))

    service.rebuild_current_projection()
    before = {
        (
            row.assertion_ref_id,
            row.conflict_group_id,
            row.source_revision_id,
            row.projection_revision_id,
            row.selection_reason,
        )
        for row in session.scalars(select(CurrentAssertion)).all()
    }

    service.clear_current_projection()
    assert session.scalar(select(func.count()).select_from(CurrentAssertion)) == 0

    service.rebuild_current_projection()
    after = {
        (
            row.assertion_ref_id,
            row.conflict_group_id,
            row.source_revision_id,
            row.projection_revision_id,
            row.selection_reason,
        )
        for row in session.scalars(select(CurrentAssertion)).all()
    }
    assert after == before


def test_world_interval_rejects_naive_or_inverted_bounds():
    with pytest.raises(KnowledgeInvariantError):
        WorldInterval(valid_from=datetime(2026, 1, 1))

    with pytest.raises(KnowledgeInvariantError):
        WorldInterval(
            valid_from=datetime(2026, 2, 1, tzinfo=UTC),
            valid_to=datetime(2026, 1, 1, tzinfo=UTC),
        )
