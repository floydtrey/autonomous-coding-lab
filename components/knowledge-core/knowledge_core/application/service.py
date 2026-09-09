from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from knowledge_core.application.assertions import KnowledgeKernel
from knowledge_core.application.deletion import DeletionKnowledgeKernel
from knowledge_core.application.history import TemporalKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError, TypedValue
from knowledge_core.domain.deletion import KnowledgeRestrictedError
from knowledge_core.domain.identity import IdentityTransitionSnapshot
from knowledge_core.domain.temporal import BitemporalAssertion
from knowledge_core.storage.models import Entity


@dataclass(frozen=True)
class EntitySnapshot:
    entity_ref: UUID
    kind_revision_ref: UUID
    created_revision_id: int


class ServiceKnowledgeKernel(DeletionKnowledgeKernel):
    """Semantic application operations safe for the Task 7 HTTP boundary."""

    def read_entity_serving(self, entity_ref: UUID) -> EntitySnapshot:
        if not self._direct_ref_serving_eligible(entity_ref):
            raise KnowledgeRestrictedError(
                f"entity is unavailable to serving reads: {entity_ref}"
            )
        row = self.session.get(Entity, entity_ref)
        if row is None:
            raise KnowledgeInvariantError(f"unknown entity: {entity_ref}")
        return EntitySnapshot(
            entity_ref=row.ref_id,
            kind_revision_ref=row.kind_revision_ref,
            created_revision_id=row.created_revision_id,
        )

    def _require_serving_entity(self, entity_ref: UUID) -> None:
        if not self._direct_ref_serving_eligible(entity_ref):
            raise KnowledgeRestrictedError(
                f"entity is unavailable to serving mutations: {entity_ref}"
            )
        if self.session.get(Entity, entity_ref) is None:
            raise KnowledgeInvariantError(f"unknown entity: {entity_ref}")

    def serving_current(
        self,
        *,
        subject_ref: UUID | None = None,
        predicate_revision_ref: UUID | None = None,
    ) -> list[BitemporalAssertion]:
        anchor = self._now()
        return self.belief(
            world_at=anchor,
            knowledge_at=anchor,
            subject_ref=subject_ref,
            predicate_revision_ref=predicate_revision_ref,
        )

    def assertion_history_serving(
        self,
        *,
        subject_ref: UUID,
        predicate_revision_ref: UUID,
    ) -> list[BitemporalAssertion]:
        return [
            item
            for item in self.assertion_history(
                subject_ref=subject_ref,
                predicate_revision_ref=predicate_revision_ref,
            )
            if self.assertion_serving_eligible(item.assertion.assertion_ref)
        ]

    def create_entity_operation(
        self,
        *,
        operation_id: UUID,
        kind_revision_ref: UUID,
        caller_principal_ref: str,
        expected_revision: int | None = None,
    ) -> UUID:
        payload = {"kind_revision_ref": str(kind_revision_ref)}

        def action() -> UUID:
            return KnowledgeKernel.create_entity(self, kind_revision_ref)

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="create_entity",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {"entity_ref": str(result)},
            replay=lambda metadata: UUID(str(metadata["entity_ref"])),
        )

    def correct_assertion_operation(
        self,
        *,
        operation_id: UUID,
        expected_revision: int,
        source_assertion_ref: UUID,
        replacement_value: TypedValue,
        correction_kind_revision_ref: UUID,
        replacement_world_interval=None,
        caller_principal_ref: str,
    ):
        if not self.assertion_serving_eligible(source_assertion_ref):
            raise KnowledgeRestrictedError(
                f"assertion is unavailable to serving mutations: {source_assertion_ref}"
            )
        return super().correct_assertion_operation(
            operation_id=operation_id,
            expected_revision=expected_revision,
            source_assertion_ref=source_assertion_ref,
            replacement_value=replacement_value,
            correction_kind_revision_ref=correction_kind_revision_ref,
            replacement_world_interval=replacement_world_interval,
            caller_principal_ref=caller_principal_ref,
        )

    def reverse_assertion_transition_operation(
        self,
        *,
        operation_id: UUID,
        expected_revision: int,
        transition_ref: UUID,
        correction_kind_revision_ref: UUID,
        caller_principal_ref: str,
    ):
        transition = self.read_transition(transition_ref)
        for assertion_ref in (
            transition.source_assertion_ref,
            transition.replacement_assertion_ref,
        ):
            if assertion_ref is not None and not self.assertion_serving_eligible(assertion_ref):
                raise KnowledgeRestrictedError(
                    f"transition references unavailable assertion: {assertion_ref}"
                )

        payload = {
            "transition_ref": str(transition_ref),
            "correction_kind_revision_ref": str(correction_kind_revision_ref),
        }

        def action():
            return TemporalKnowledgeKernel.reverse_transition(
                self,
                transition_ref=transition_ref,
                correction_kind_revision_ref=correction_kind_revision_ref,
            )

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="reverse_assertion_transition",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {"transition_ref": str(result.transition_ref)},
            replay=lambda metadata: self.read_transition(
                UUID(str(metadata["transition_ref"]))
            ),
        )

    def merge_entities_operation(
        self,
        *,
        operation_id: UUID,
        expected_revision: int,
        entity_refs: Iterable[UUID],
        representative_ref: UUID,
        identity_kind_revision_ref: UUID,
        caller_principal_ref: str,
    ) -> IdentityTransitionSnapshot:
        refs = tuple(entity_refs)
        for entity_ref in refs:
            self._require_serving_entity(entity_ref)
        self._require_serving_entity(representative_ref)
        payload = {
            "entity_refs": [str(ref) for ref in refs],
            "representative_ref": str(representative_ref),
            "identity_kind_revision_ref": str(identity_kind_revision_ref),
        }

        def action() -> IdentityTransitionSnapshot:
            return self.merge_entities(
                entity_refs=refs,
                representative_ref=representative_ref,
                identity_kind_revision_ref=identity_kind_revision_ref,
            )

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="identity_merge",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {"transition_ref": str(result.transition_ref)},
            replay=lambda metadata: self.read_identity_transition(
                UUID(str(metadata["transition_ref"]))
            ),
        )

    def replace_entity_operation(
        self,
        *,
        operation_id: UUID,
        expected_revision: int,
        old_entity_ref: UUID,
        new_entity_ref: UUID,
        identity_kind_revision_ref: UUID,
        caller_principal_ref: str,
    ) -> IdentityTransitionSnapshot:
        self._require_serving_entity(old_entity_ref)
        self._require_serving_entity(new_entity_ref)
        payload = {
            "old_entity_ref": str(old_entity_ref),
            "new_entity_ref": str(new_entity_ref),
            "identity_kind_revision_ref": str(identity_kind_revision_ref),
        }

        def action() -> IdentityTransitionSnapshot:
            return self.replace_entity(
                old_entity_ref=old_entity_ref,
                new_entity_ref=new_entity_ref,
                identity_kind_revision_ref=identity_kind_revision_ref,
            )

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="identity_replace",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {"transition_ref": str(result.transition_ref)},
            replay=lambda metadata: self.read_identity_transition(
                UUID(str(metadata["transition_ref"]))
            ),
        )

    def reverse_identity_transition_operation(
        self,
        *,
        operation_id: UUID,
        expected_revision: int,
        transition_ref: UUID,
        identity_kind_revision_ref: UUID,
        caller_principal_ref: str,
    ) -> IdentityTransitionSnapshot:
        transition = self.read_identity_transition(transition_ref)
        for member in transition.members:
            self._require_serving_entity(member.entity_ref)
        payload = {
            "transition_ref": str(transition_ref),
            "identity_kind_revision_ref": str(identity_kind_revision_ref),
        }

        def action() -> IdentityTransitionSnapshot:
            return self.reverse_identity_transition(
                transition_ref=transition_ref,
                identity_kind_revision_ref=identity_kind_revision_ref,
            )

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="identity_reverse",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {"transition_ref": str(result.transition_ref)},
            replay=lambda metadata: self.read_identity_transition(
                UUID(str(metadata["transition_ref"]))
            ),
        )
