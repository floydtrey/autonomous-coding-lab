from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from knowledge_core.application.assertions import KnowledgeKernel
from knowledge_core.domain.assertions import (
    EpistemicBasis,
    KnowledgeInvariantError,
    RefKind,
    TransitionSnapshot,
    TransitionType,
    TypedValue,
)
from knowledge_core.domain.temporal import BitemporalAssertion, WorldInterval
from knowledge_core.storage.models import (
    Assertion,
    AssertionTransition,
    CurrentAssertion,
    Occurrence,
    Revision,
    SemanticPredicateRevision,
)


Clock = Callable[[], datetime]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class TemporalKnowledgeKernel(KnowledgeKernel):
    """Task 2 bitemporal history and rebuildable current projection."""

    def __init__(self, session: Session, *, clock: Clock | None = None):
        super().__init__(session)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self) -> datetime:
        return _as_utc(self._clock())

    def _new_revision(self) -> Revision:
        revision = Revision(
            schema_revision="task2",
            recorded_at=self._now(),
        )
        self.session.add(revision)
        self.session.flush()
        return revision

    @staticmethod
    def _window_from_assertion(assertion: Assertion) -> WorldInterval:
        return WorldInterval(
            valid_from=_as_utc(assertion.valid_from)
            if assertion.valid_from is not None
            else None,
            valid_to=_as_utc(assertion.valid_to)
            if assertion.valid_to is not None
            else None,
            precision=assertion.world_time_precision,
        )

    def append_assertion(
        self,
        *,
        subject_ref: UUID,
        predicate_revision_ref: UUID,
        profile_revision_ref: UUID,
        value: TypedValue,
        epistemic_basis: EpistemicBasis = EpistemicBasis.STATED,
        world_interval: WorldInterval | None = None,
    ) -> UUID:
        self._require_active_ref(subject_ref)
        predicate_revision = self.session.get(
            SemanticPredicateRevision, predicate_revision_ref
        )
        if predicate_revision is None:
            raise KnowledgeInvariantError(
                f"unknown semantic predicate revision: {predicate_revision_ref}"
            )
        value = self._validate_assertion_value(
            predicate_revision=predicate_revision,
            profile_revision_ref=profile_revision_ref,
            value=value,
        )
        interval = world_interval or WorldInterval()
        revision = self._new_revision()
        assertion_ref = self._append_assertion_rows(
            revision_id=revision.revision_id,
            subject_ref=subject_ref,
            predicate_revision=predicate_revision,
            profile_revision_ref=profile_revision_ref,
            value=value,
            epistemic_basis=epistemic_basis,
        )
        row = self.session.get(Assertion, assertion_ref)
        assert row is not None
        row.valid_from = interval.valid_from
        row.valid_to = interval.valid_to
        row.world_time_precision = interval.precision
        self._commit()
        return assertion_ref

    def correct_assertion(
        self,
        *,
        source_assertion_ref: UUID,
        replacement_value: TypedValue,
        correction_kind_revision_ref: UUID,
        replacement_world_interval: WorldInterval | None = None,
    ) -> TransitionSnapshot:
        source = self.session.get(Assertion, source_assertion_ref)
        if source is None:
            raise KnowledgeInvariantError(f"unknown assertion: {source_assertion_ref}")
        self._require_kind_revision(correction_kind_revision_ref)
        predicate_revision = self.session.get(
            SemanticPredicateRevision, source.predicate_revision_ref
        )
        assert predicate_revision is not None
        replacement_value = self._validate_assertion_value(
            predicate_revision=predicate_revision,
            profile_revision_ref=source.profile_revision_ref,
            value=replacement_value,
        )
        interval = (
            replacement_world_interval
            if replacement_world_interval is not None
            else self._window_from_assertion(source)
        )

        revision = self._new_revision()
        occurrence_ref = self._new_ref(RefKind.OCCURRENCE, revision.revision_id)
        replacement_ref = self._append_assertion_rows(
            revision_id=revision.revision_id,
            subject_ref=source.subject_ref_id,
            predicate_revision=predicate_revision,
            profile_revision_ref=source.profile_revision_ref,
            value=replacement_value,
            epistemic_basis=EpistemicBasis(source.epistemic_basis),
        )
        replacement = self.session.get(Assertion, replacement_ref)
        assert replacement is not None
        replacement.valid_from = interval.valid_from
        replacement.valid_to = interval.valid_to
        replacement.world_time_precision = interval.precision
        self.session.add(
            Occurrence(
                ref_id=occurrence_ref,
                kind_revision_ref=correction_kind_revision_ref,
                happened_at=revision.recorded_at,
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()
        self.session.add(
            AssertionTransition(
                occurrence_ref_id=occurrence_ref,
                transition_type=TransitionType.CORRECTS.value,
                source_assertion_ref=source_assertion_ref,
                replacement_assertion_ref=replacement_ref,
                reverses_transition_ref=None,
                created_revision_id=revision.revision_id,
            )
        )
        self._commit()
        return self.read_transition(occurrence_ref)

    def reverse_transition(
        self,
        *,
        transition_ref: UUID,
        correction_kind_revision_ref: UUID,
    ) -> TransitionSnapshot:
        transition = self.session.get(AssertionTransition, transition_ref)
        if transition is None:
            raise KnowledgeInvariantError(f"unknown transition: {transition_ref}")
        if transition.transition_type != TransitionType.CORRECTS.value:
            raise KnowledgeInvariantError("Task 2 reverses correction transitions only")
        if transition.replacement_assertion_ref is None:
            raise KnowledgeInvariantError("correction has no replacement assertion")
        existing_reversal = self.session.execute(
            select(AssertionTransition).where(
                AssertionTransition.reverses_transition_ref == transition_ref
            )
        ).scalar_one_or_none()
        if existing_reversal is not None:
            raise KnowledgeInvariantError("transition has already been reversed")
        self._require_kind_revision(correction_kind_revision_ref)

        revision = self._new_revision()
        occurrence_ref = self._new_ref(RefKind.OCCURRENCE, revision.revision_id)
        self.session.add(
            Occurrence(
                ref_id=occurrence_ref,
                kind_revision_ref=correction_kind_revision_ref,
                happened_at=revision.recorded_at,
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()
        self.session.add(
            AssertionTransition(
                occurrence_ref_id=occurrence_ref,
                transition_type=TransitionType.RESTORES.value,
                source_assertion_ref=transition.replacement_assertion_ref,
                replacement_assertion_ref=transition.source_assertion_ref,
                reverses_transition_ref=transition_ref,
                created_revision_id=revision.revision_id,
            )
        )
        self._commit()
        return self.read_transition(occurrence_ref)

    def read_bitemporal_assertion(self, assertion_ref: UUID) -> BitemporalAssertion:
        assertion = self.session.get(Assertion, assertion_ref)
        if assertion is None:
            raise KnowledgeInvariantError(f"unknown assertion: {assertion_ref}")
        revision = self.session.get(Revision, assertion.created_revision_id)
        assert revision is not None
        return BitemporalAssertion(
            assertion=self.read_assertion(assertion_ref),
            valid_from=_as_utc(assertion.valid_from)
            if assertion.valid_from is not None
            else None,
            valid_to=_as_utc(assertion.valid_to)
            if assertion.valid_to is not None
            else None,
            world_time_precision=assertion.world_time_precision,
            recorded_at=_as_utc(revision.recorded_at),
        )

    def assertion_history(
        self,
        *,
        subject_ref: UUID,
        predicate_revision_ref: UUID,
    ) -> list[BitemporalAssertion]:
        refs = self.session.scalars(
            select(Assertion.ref_id)
            .where(
                Assertion.subject_ref_id == subject_ref,
                Assertion.predicate_revision_ref == predicate_revision_ref,
            )
            .order_by(Assertion.created_revision_id, Assertion.ref_id)
        ).all()
        return [self.read_bitemporal_assertion(ref) for ref in refs]

    def belief(
        self,
        *,
        world_at: datetime,
        knowledge_at: datetime,
        subject_ref: UUID | None = None,
        predicate_revision_ref: UUID | None = None,
    ) -> list[BitemporalAssertion]:
        world_at = _as_utc(world_at)
        knowledge_at = _as_utc(knowledge_at)

        statement = select(Assertion, Revision).join(
            Revision, Assertion.created_revision_id == Revision.revision_id
        )
        if subject_ref is not None:
            statement = statement.where(Assertion.subject_ref_id == subject_ref)
        if predicate_revision_ref is not None:
            statement = statement.where(
                Assertion.predicate_revision_ref == predicate_revision_ref
            )

        candidates: dict[UUID, Assertion] = {}
        for assertion, revision in self.session.execute(statement):
            if _as_utc(revision.recorded_at) > knowledge_at:
                continue
            if not self._window_from_assertion(assertion).contains(world_at):
                continue
            candidates[assertion.ref_id] = assertion

        transition_rows: list[tuple[AssertionTransition, Revision]] = []
        transition_statement = (
            select(AssertionTransition, Revision)
            .join(
                Revision,
                AssertionTransition.created_revision_id == Revision.revision_id,
            )
            .order_by(AssertionTransition.created_revision_id)
        )
        for transition, revision in self.session.execute(transition_statement):
            if _as_utc(revision.recorded_at) <= knowledge_at:
                transition_rows.append((transition, revision))

        reversed_transition_refs = {
            transition.reverses_transition_ref
            for transition, _revision in transition_rows
            if transition.transition_type == TransitionType.RESTORES.value
            and transition.reverses_transition_ref is not None
        }

        inactive: set[UUID] = set()
        for transition, _revision in transition_rows:
            transition_type = TransitionType(transition.transition_type)
            if (
                transition_type is not TransitionType.RESTORES
                and transition.occurrence_ref_id in reversed_transition_refs
            ):
                continue
            if transition_type in {
                TransitionType.CORRECTS,
                TransitionType.SUPERSEDES,
                TransitionType.INVALIDATES,
            }:
                inactive.add(transition.source_assertion_ref)
                if transition.replacement_assertion_ref is not None:
                    inactive.discard(transition.replacement_assertion_ref)
            elif transition_type is TransitionType.RESTORES:
                inactive.add(transition.source_assertion_ref)
                if transition.replacement_assertion_ref is not None:
                    inactive.discard(transition.replacement_assertion_ref)

        result = [
            self.read_bitemporal_assertion(ref)
            for ref, assertion in candidates.items()
            if ref not in inactive
        ]
        result.sort(
            key=lambda item: (
                str(item.assertion.subject_ref),
                str(item.assertion.predicate_revision_ref),
                item.assertion.created_revision_id,
                str(item.assertion.assertion_ref),
            )
        )
        return result

    @staticmethod
    def _conflict_group_id(items: list[BitemporalAssertion]) -> UUID | None:
        if len(items) < 2:
            return None
        refs = ",".join(
            sorted(str(item.assertion.assertion_ref) for item in items)
        )
        subject = items[0].assertion.subject_ref
        predicate = items[0].assertion.predicate_revision_ref
        return uuid5(
            NAMESPACE_URL,
            f"knowledge-core:conflict:{subject}:{predicate}:{refs}",
        )

    def rebuild_current_projection(
        self,
        *,
        world_at: datetime | None = None,
        knowledge_at: datetime | None = None,
    ) -> int:
        anchor = self._now()
        world_at = _as_utc(world_at or anchor)
        knowledge_at = _as_utc(knowledge_at or anchor)
        current = self.belief(world_at=world_at, knowledge_at=knowledge_at)

        self.session.execute(delete(CurrentAssertion))
        self.session.flush()

        revision_rows = self.session.scalars(
            select(Revision).order_by(Revision.revision_id)
        ).all()
        eligible_revision_ids = [
            revision.revision_id
            for revision in revision_rows
            if _as_utc(revision.recorded_at) <= knowledge_at
        ]
        projection_revision_id = (
            max(eligible_revision_ids) if eligible_revision_ids else None
        )
        if current and projection_revision_id is None:
            raise KnowledgeInvariantError(
                "current assertions exist without an eligible canonical revision"
            )

        groups: dict[tuple[UUID, UUID], list[BitemporalAssertion]] = defaultdict(list)
        for item in current:
            groups[
                (
                    item.assertion.subject_ref,
                    item.assertion.predicate_revision_ref,
                )
            ].append(item)

        for items in groups.values():
            conflict_group_id = self._conflict_group_id(items)
            selection_reason = (
                "conflict-preserved" if conflict_group_id is not None else "lifecycle-current"
            )
            for item in items:
                self.session.add(
                    CurrentAssertion(
                        assertion_ref_id=item.assertion.assertion_ref,
                        subject_ref_id=item.assertion.subject_ref,
                        predicate_revision_ref=item.assertion.predicate_revision_ref,
                        conflict_group_id=conflict_group_id,
                        source_revision_id=item.assertion.created_revision_id,
                        projection_revision_id=projection_revision_id,
                        selection_reason=selection_reason,
                    )
                )
        self._commit()
        return len(current)

    def clear_current_projection(self) -> None:
        self.session.execute(delete(CurrentAssertion))
        self._commit()

    def current_projection(
        self,
        *,
        subject_ref: UUID | None = None,
        predicate_revision_ref: UUID | None = None,
    ) -> list[BitemporalAssertion]:
        statement = select(CurrentAssertion).order_by(
            CurrentAssertion.subject_ref_id,
            CurrentAssertion.predicate_revision_ref,
            CurrentAssertion.source_revision_id,
            CurrentAssertion.assertion_ref_id,
        )
        if subject_ref is not None:
            statement = statement.where(CurrentAssertion.subject_ref_id == subject_ref)
        if predicate_revision_ref is not None:
            statement = statement.where(
                CurrentAssertion.predicate_revision_ref == predicate_revision_ref
            )
        rows = self.session.scalars(statement).all()
        return [
            self.read_bitemporal_assertion(row.assertion_ref_id)
            for row in rows
        ]
