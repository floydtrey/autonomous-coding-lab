from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_core.domain.assertions import (
    AssertionSnapshot,
    EpistemicBasis,
    FoundationRefs,
    KnowledgeInvariantError,
    RefKind,
    TransitionSnapshot,
    TransitionType,
    TypedValue,
    ValueKind,
    ValueState,
)
from knowledge_core.storage.models import (
    Assertion,
    AssertionTransition,
    AssertionValue,
    Entity,
    KnowledgeRef,
    Occurrence,
    Revision,
    SemanticKind,
    SemanticKindRevision,
    SemanticPredicate,
    SemanticPredicateRevision,
    SemanticProfile,
    SemanticProfileRevision,
)


class KnowledgeKernel:
    """Task 1 semantic write/read surface.

    It intentionally has no current projection or bitemporal query behavior.
    """

    def __init__(self, session: Session):
        self.session = session

    def _commit(self) -> None:
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def _new_revision(self) -> Revision:
        revision = Revision(schema_revision="task1")
        self.session.add(revision)
        self.session.flush()
        return revision

    def _new_ref(self, ref_kind: RefKind, revision_id: int) -> UUID:
        ref_id = uuid4()
        self.session.add(
            KnowledgeRef(
                ref_id=ref_id,
                ref_kind=ref_kind.value,
                created_revision_id=revision_id,
                payload_state="active",
            )
        )
        self.session.flush()
        return ref_id

    def _require_active_ref(self, ref_id: UUID) -> KnowledgeRef:
        row = self.session.get(KnowledgeRef, ref_id)
        if row is None or row.payload_state != "active":
            raise KnowledgeInvariantError(f"unknown or inactive knowledge ref: {ref_id}")
        return row

    def _require_kind_revision(self, ref_id: UUID) -> SemanticKindRevision:
        revision = self.session.get(SemanticKindRevision, ref_id)
        if revision is None:
            raise KnowledgeInvariantError(f"unknown semantic kind revision: {ref_id}")
        return revision

    def bootstrap_core_test_profile(self) -> FoundationRefs:
        existing = self.session.execute(
            select(SemanticProfile).where(SemanticProfile.stable_name == "core-test")
        ).scalar_one_or_none()
        if existing is not None:
            return self._load_foundation_refs(existing.ref_id)

        revision = self._new_revision()
        profile_ref = self._new_ref(RefKind.SEMANTIC_PROFILE, revision.revision_id)
        profile_revision_ref = self._new_ref(
            RefKind.SEMANTIC_PROFILE_REVISION, revision.revision_id
        )
        self.session.add(
            SemanticProfile(
                ref_id=profile_ref,
                stable_name="core-test",
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()
        self.session.add(
            SemanticProfileRevision(
                ref_id=profile_revision_ref,
                profile_ref_id=profile_ref,
                version_label="1",
                status="active-capable",
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()

        kind_refs: dict[str, UUID] = {}
        for stable_name in ("person", "organization", "correction"):
            kind_ref = self._new_ref(RefKind.SEMANTIC_KIND, revision.revision_id)
            kind_revision_ref = self._new_ref(
                RefKind.SEMANTIC_KIND_REVISION, revision.revision_id
            )
            self.session.add(
                SemanticKind(
                    ref_id=kind_ref,
                    profile_ref_id=profile_ref,
                    stable_name=stable_name,
                    created_revision_id=revision.revision_id,
                )
            )
            self.session.flush()
            self.session.add(
                SemanticKindRevision(
                    ref_id=kind_revision_ref,
                    kind_ref_id=kind_ref,
                    profile_revision_ref_id=profile_revision_ref,
                    created_revision_id=revision.revision_id,
                )
            )
            kind_refs[stable_name] = kind_revision_ref

        predicate_refs: dict[str, UUID] = {}
        for stable_name, value_shape in (
            ("has_name", "scalar"),
            ("works_for", "reference"),
        ):
            predicate_ref = self._new_ref(
                RefKind.SEMANTIC_PREDICATE, revision.revision_id
            )
            predicate_revision_ref = self._new_ref(
                RefKind.SEMANTIC_PREDICATE_REVISION, revision.revision_id
            )
            self.session.add(
                SemanticPredicate(
                    ref_id=predicate_ref,
                    profile_ref_id=profile_ref,
                    stable_name=stable_name,
                    created_revision_id=revision.revision_id,
                )
            )
            self.session.flush()
            self.session.add(
                SemanticPredicateRevision(
                    ref_id=predicate_revision_ref,
                    predicate_ref_id=predicate_ref,
                    profile_revision_ref_id=profile_revision_ref,
                    value_shape=value_shape,
                    created_revision_id=revision.revision_id,
                )
            )
            predicate_refs[stable_name] = predicate_revision_ref

        self._commit()
        return FoundationRefs(
            profile_ref=profile_ref,
            profile_revision_ref=profile_revision_ref,
            person_kind_revision_ref=kind_refs["person"],
            organization_kind_revision_ref=kind_refs["organization"],
            correction_kind_revision_ref=kind_refs["correction"],
            has_name_predicate_revision_ref=predicate_refs["has_name"],
            works_for_predicate_revision_ref=predicate_refs["works_for"],
        )

    def _load_foundation_refs(self, profile_ref: UUID) -> FoundationRefs:
        profile_revision = self.session.execute(
            select(SemanticProfileRevision).where(
                SemanticProfileRevision.profile_ref_id == profile_ref,
                SemanticProfileRevision.version_label == "1",
            )
        ).scalar_one()

        kinds = {}
        for kind in self.session.execute(
            select(SemanticKind).where(SemanticKind.profile_ref_id == profile_ref)
        ).scalars():
            revision = self.session.execute(
                select(SemanticKindRevision).where(
                    SemanticKindRevision.kind_ref_id == kind.ref_id,
                    SemanticKindRevision.profile_revision_ref_id
                    == profile_revision.ref_id,
                )
            ).scalar_one()
            kinds[kind.stable_name] = revision.ref_id

        predicates = {}
        for predicate in self.session.execute(
            select(SemanticPredicate).where(
                SemanticPredicate.profile_ref_id == profile_ref
            )
        ).scalars():
            revision = self.session.execute(
                select(SemanticPredicateRevision).where(
                    SemanticPredicateRevision.predicate_ref_id == predicate.ref_id,
                    SemanticPredicateRevision.profile_revision_ref_id
                    == profile_revision.ref_id,
                )
            ).scalar_one()
            predicates[predicate.stable_name] = revision.ref_id

        return FoundationRefs(
            profile_ref=profile_ref,
            profile_revision_ref=profile_revision.ref_id,
            person_kind_revision_ref=kinds["person"],
            organization_kind_revision_ref=kinds["organization"],
            correction_kind_revision_ref=kinds["correction"],
            has_name_predicate_revision_ref=predicates["has_name"],
            works_for_predicate_revision_ref=predicates["works_for"],
        )

    def create_entity(self, kind_revision_ref: UUID) -> UUID:
        self._require_kind_revision(kind_revision_ref)
        revision = self._new_revision()
        entity_ref = self._new_ref(RefKind.ENTITY, revision.revision_id)
        self.session.add(
            Entity(
                ref_id=entity_ref,
                kind_revision_ref=kind_revision_ref,
                created_revision_id=revision.revision_id,
            )
        )
        self._commit()
        return entity_ref

    def _validate_assertion_value(
        self,
        *,
        predicate_revision: SemanticPredicateRevision,
        profile_revision_ref: UUID,
        value: TypedValue,
    ) -> TypedValue:
        value = value.validated()
        if predicate_revision.profile_revision_ref_id != profile_revision_ref:
            raise KnowledgeInvariantError(
                "predicate revision is not pinned to the supplied profile revision"
            )
        if predicate_revision.value_shape == "reference":
            if value.kind is not ValueKind.REFERENCE:
                raise KnowledgeInvariantError(
                    "reference predicate requires reference-valued assertion"
                )
            self._require_active_ref(value.value)
        elif predicate_revision.value_shape == "scalar":
            if value.kind is ValueKind.REFERENCE:
                raise KnowledgeInvariantError(
                    "scalar predicate cannot accept a reference value"
                )
        else:
            raise KnowledgeInvariantError(
                f"unsupported predicate value shape: {predicate_revision.value_shape}"
            )
        return value

    @staticmethod
    def _value_columns(value: TypedValue) -> dict[str, object | None]:
        columns: dict[str, object | None] = {
            "reference_value": None,
            "text_value": None,
            "numeric_value": None,
            "boolean_value": None,
            "date_value": None,
            "timestamp_value": None,
        }
        key = {
            ValueKind.REFERENCE: "reference_value",
            ValueKind.TEXT: "text_value",
            ValueKind.NUMERIC: "numeric_value",
            ValueKind.BOOLEAN: "boolean_value",
            ValueKind.DATE: "date_value",
            ValueKind.TIMESTAMP: "timestamp_value",
        }[value.kind]
        columns[key] = (
            Decimal(str(value.value))
            if value.kind is ValueKind.NUMERIC
            else value.value
        )
        return columns

    def _append_assertion_rows(
        self,
        *,
        revision_id: int,
        subject_ref: UUID,
        predicate_revision: SemanticPredicateRevision,
        profile_revision_ref: UUID,
        value: TypedValue,
        epistemic_basis: EpistemicBasis,
    ) -> UUID:
        assertion_ref = self._new_ref(RefKind.ASSERTION, revision_id)
        self.session.add(
            Assertion(
                ref_id=assertion_ref,
                subject_ref_id=subject_ref,
                predicate_revision_ref=predicate_revision.ref_id,
                profile_revision_ref=profile_revision_ref,
                value_state=ValueState.PRESENT.value,
                epistemic_basis=epistemic_basis.value,
                created_revision_id=revision_id,
            )
        )
        self.session.flush()
        self.session.add(
            AssertionValue(
                assertion_ref_id=assertion_ref,
                value_kind=value.kind.value,
                **self._value_columns(value),
            )
        )
        return assertion_ref

    def append_assertion(
        self,
        *,
        subject_ref: UUID,
        predicate_revision_ref: UUID,
        profile_revision_ref: UUID,
        value: TypedValue,
        epistemic_basis: EpistemicBasis = EpistemicBasis.STATED,
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
        revision = self._new_revision()
        assertion_ref = self._append_assertion_rows(
            revision_id=revision.revision_id,
            subject_ref=subject_ref,
            predicate_revision=predicate_revision,
            profile_revision_ref=profile_revision_ref,
            value=value,
            epistemic_basis=epistemic_basis,
        )
        self._commit()
        return assertion_ref

    def correct_assertion(
        self,
        *,
        source_assertion_ref: UUID,
        replacement_value: TypedValue,
        correction_kind_revision_ref: UUID,
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
        self.session.add(
            Occurrence(
                ref_id=occurrence_ref,
                kind_revision_ref=correction_kind_revision_ref,
                happened_at=datetime.now(timezone.utc),
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
            raise KnowledgeInvariantError("Task 1 reverses correction transitions only")
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
                happened_at=datetime.now(timezone.utc),
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

    def read_assertion(self, assertion_ref: UUID) -> AssertionSnapshot:
        assertion = self.session.get(Assertion, assertion_ref)
        if assertion is None:
            raise KnowledgeInvariantError(f"unknown assertion: {assertion_ref}")
        value_row = self.session.get(AssertionValue, assertion_ref)
        if value_row is None:
            raise KnowledgeInvariantError(
                f"present assertion has no typed value: {assertion_ref}"
            )
        value = self._typed_value_from_row(value_row)
        return AssertionSnapshot(
            assertion_ref=assertion.ref_id,
            subject_ref=assertion.subject_ref_id,
            predicate_revision_ref=assertion.predicate_revision_ref,
            profile_revision_ref=assertion.profile_revision_ref,
            value_state=ValueState(assertion.value_state),
            epistemic_basis=EpistemicBasis(assertion.epistemic_basis),
            value=value,
            created_revision_id=assertion.created_revision_id,
        )

    @staticmethod
    def _typed_value_from_row(row: AssertionValue) -> TypedValue:
        kind = ValueKind(row.value_kind)
        value = {
            ValueKind.REFERENCE: row.reference_value,
            ValueKind.TEXT: row.text_value,
            ValueKind.NUMERIC: row.numeric_value,
            ValueKind.BOOLEAN: row.boolean_value,
            ValueKind.DATE: row.date_value,
            ValueKind.TIMESTAMP: row.timestamp_value,
        }[kind]
        return TypedValue(kind=kind, value=value).validated()

    def read_transition(self, transition_ref: UUID) -> TransitionSnapshot:
        row = self.session.get(AssertionTransition, transition_ref)
        if row is None:
            raise KnowledgeInvariantError(f"unknown transition: {transition_ref}")
        return TransitionSnapshot(
            transition_ref=row.occurrence_ref_id,
            transition_type=TransitionType(row.transition_type),
            source_assertion_ref=row.source_assertion_ref,
            replacement_assertion_ref=row.replacement_assertion_ref,
            reverses_transition_ref=row.reverses_transition_ref,
            created_revision_id=row.created_revision_id,
        )
