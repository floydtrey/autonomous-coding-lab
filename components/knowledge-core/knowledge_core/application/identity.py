from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, select

from knowledge_core.application.resources import ResourceKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError, RefKind
from knowledge_core.domain.identity import (
    IdentityFoundationRefs,
    IdentityMemberRole,
    IdentityMemberSnapshot,
    IdentityResolutionSnapshot,
    IdentityTransitionSnapshot,
    IdentityTransitionType,
)
from knowledge_core.storage.identity_models import (
    CurrentIdentityMember,
    IdentityTransition,
    IdentityTransitionMember,
)
from knowledge_core.storage.models import (
    Entity,
    Occurrence,
    Revision,
    SemanticKind,
    SemanticKindRevision,
    SemanticPredicate,
    SemanticPredicateRevision,
    SemanticProfile,
    SemanticProfileRevision,
)


class IdentityKnowledgeKernel(ResourceKnowledgeKernel):
    """Task 5 reversible identity transitions and rebuildable equivalence state."""

    def _new_revision(self) -> Revision:
        revision = Revision(
            schema_revision="task5",
            recorded_at=self._now(),
            operation_id=self._active_operation_id,
        )
        self.session.add(revision)
        self.session.flush()
        return revision

    def bootstrap_identity_test_profile(self) -> IdentityFoundationRefs:
        existing = self.session.execute(
            select(SemanticProfile).where(
                SemanticProfile.stable_name == "identity-test"
            )
        ).scalar_one_or_none()
        if existing is not None:
            return self._load_identity_foundation_refs(existing.ref_id)

        revision = self._new_revision()
        profile_ref = self._new_ref(RefKind.SEMANTIC_PROFILE, revision.revision_id)
        profile_revision_ref = self._new_ref(
            RefKind.SEMANTIC_PROFILE_REVISION, revision.revision_id
        )
        self.session.add(
            SemanticProfile(
                ref_id=profile_ref,
                stable_name="identity-test",
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
        for stable_name in ("person", "device", "identity_resolution"):
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
                stable_name="has_name",
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()
        self.session.add(
            SemanticPredicateRevision(
                ref_id=predicate_revision_ref,
                predicate_ref_id=predicate_ref,
                profile_revision_ref_id=profile_revision_ref,
                value_shape="scalar",
                created_revision_id=revision.revision_id,
            )
        )

        self._commit()
        return IdentityFoundationRefs(
            profile_ref=profile_ref,
            profile_revision_ref=profile_revision_ref,
            person_kind_revision_ref=kind_refs["person"],
            device_kind_revision_ref=kind_refs["device"],
            identity_resolution_kind_revision_ref=kind_refs["identity_resolution"],
            has_name_predicate_revision_ref=predicate_revision_ref,
        )

    def _load_identity_foundation_refs(
        self, profile_ref: UUID
    ) -> IdentityFoundationRefs:
        profile_revision = self.session.execute(
            select(SemanticProfileRevision).where(
                SemanticProfileRevision.profile_ref_id == profile_ref,
                SemanticProfileRevision.version_label == "1",
            )
        ).scalar_one()

        kinds: dict[str, UUID] = {}
        for kind in self.session.execute(
            select(SemanticKind).where(SemanticKind.profile_ref_id == profile_ref)
        ).scalars():
            kind_revision = self.session.execute(
                select(SemanticKindRevision).where(
                    SemanticKindRevision.kind_ref_id == kind.ref_id,
                    SemanticKindRevision.profile_revision_ref_id
                    == profile_revision.ref_id,
                )
            ).scalar_one()
            kinds[kind.stable_name] = kind_revision.ref_id

        predicate = self.session.execute(
            select(SemanticPredicate).where(
                SemanticPredicate.profile_ref_id == profile_ref,
                SemanticPredicate.stable_name == "has_name",
            )
        ).scalar_one()
        predicate_revision = self.session.execute(
            select(SemanticPredicateRevision).where(
                SemanticPredicateRevision.predicate_ref_id == predicate.ref_id,
                SemanticPredicateRevision.profile_revision_ref_id
                == profile_revision.ref_id,
            )
        ).scalar_one()

        return IdentityFoundationRefs(
            profile_ref=profile_ref,
            profile_revision_ref=profile_revision.ref_id,
            person_kind_revision_ref=kinds["person"],
            device_kind_revision_ref=kinds["device"],
            identity_resolution_kind_revision_ref=kinds["identity_resolution"],
            has_name_predicate_revision_ref=predicate_revision.ref_id,
        )

    def _require_entity(self, entity_ref: UUID) -> Entity:
        entity = self.session.get(Entity, entity_ref)
        if entity is None:
            raise KnowledgeInvariantError(f"unknown entity: {entity_ref}")
        return entity

    def _append_identity_transition(
        self,
        *,
        transition_type: IdentityTransitionType,
        identity_kind_revision_ref: UUID,
        members: tuple[tuple[UUID, IdentityMemberRole], ...],
        reverses_transition_ref: UUID | None = None,
    ) -> IdentityTransitionSnapshot:
        self._require_kind_revision(identity_kind_revision_ref)
        entity_refs = [entity_ref for entity_ref, _role in members]
        if len(set(entity_refs)) != len(entity_refs):
            raise KnowledgeInvariantError(
                "an entity may appear only once in one identity transition"
            )
        for entity_ref in entity_refs:
            self._require_entity(entity_ref)

        revision = self._new_revision()
        occurrence_ref = self._new_ref(RefKind.OCCURRENCE, revision.revision_id)
        self.session.add(
            Occurrence(
                ref_id=occurrence_ref,
                kind_revision_ref=identity_kind_revision_ref,
                happened_at=revision.recorded_at,
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()
        self.session.add(
            IdentityTransition(
                occurrence_ref_id=occurrence_ref,
                transition_type=transition_type.value,
                reverses_transition_ref=reverses_transition_ref,
                created_revision_id=revision.revision_id,
            )
        )
        self.session.flush()
        for ordinal, (entity_ref, role) in enumerate(members):
            self.session.add(
                IdentityTransitionMember(
                    transition_ref_id=occurrence_ref,
                    entity_ref_id=entity_ref,
                    member_role=role.value,
                    ordinal=ordinal,
                )
            )
        self._commit()
        return self.read_identity_transition(occurrence_ref)

    def merge_entities(
        self,
        *,
        entity_refs: Iterable[UUID],
        representative_ref: UUID,
        identity_kind_revision_ref: UUID,
    ) -> IdentityTransitionSnapshot:
        refs = tuple(entity_refs)
        if len(refs) < 2:
            raise KnowledgeInvariantError("merge requires at least two entities")
        if len(set(refs)) != len(refs):
            raise KnowledgeInvariantError("merge entity refs must be unique")
        if representative_ref not in refs:
            raise KnowledgeInvariantError(
                "merge representative must be one of the merged entities"
            )

        members = tuple(
            (
                entity_ref,
                IdentityMemberRole.REPRESENTATIVE
                if entity_ref == representative_ref
                else IdentityMemberRole.MEMBER,
            )
            for entity_ref in refs
        )
        return self._append_identity_transition(
            transition_type=IdentityTransitionType.MERGE,
            identity_kind_revision_ref=identity_kind_revision_ref,
            members=members,
        )

    def reverse_identity_transition(
        self,
        *,
        transition_ref: UUID,
        identity_kind_revision_ref: UUID,
    ) -> IdentityTransitionSnapshot:
        transition = self.session.get(IdentityTransition, transition_ref)
        if transition is None:
            raise KnowledgeInvariantError(
                f"unknown identity transition: {transition_ref}"
            )
        if transition.transition_type != IdentityTransitionType.MERGE.value:
            raise KnowledgeInvariantError(
                "Task 5 reversal is defined only for merge transitions"
            )
        existing_reversal = self.session.execute(
            select(IdentityTransition).where(
                IdentityTransition.reverses_transition_ref == transition_ref
            )
        ).scalar_one_or_none()
        if existing_reversal is not None:
            raise KnowledgeInvariantError("identity transition has already been reversed")

        original_members = self.session.scalars(
            select(IdentityTransitionMember)
            .where(IdentityTransitionMember.transition_ref_id == transition_ref)
            .order_by(
                IdentityTransitionMember.ordinal,
                IdentityTransitionMember.entity_ref_id,
            )
        ).all()
        if len(original_members) < 2:
            raise KnowledgeInvariantError("merge transition has insufficient members")

        return self._append_identity_transition(
            transition_type=IdentityTransitionType.SPLIT,
            identity_kind_revision_ref=identity_kind_revision_ref,
            members=tuple(
                (row.entity_ref_id, IdentityMemberRole.SPLIT_MEMBER)
                for row in original_members
            ),
            reverses_transition_ref=transition_ref,
        )

    def replace_entity(
        self,
        *,
        old_entity_ref: UUID,
        new_entity_ref: UUID,
        identity_kind_revision_ref: UUID,
    ) -> IdentityTransitionSnapshot:
        if old_entity_ref == new_entity_ref:
            raise KnowledgeInvariantError("replacement requires two distinct entities")
        return self._append_identity_transition(
            transition_type=IdentityTransitionType.REPLACE,
            identity_kind_revision_ref=identity_kind_revision_ref,
            members=(
                (old_entity_ref, IdentityMemberRole.OLD),
                (new_entity_ref, IdentityMemberRole.NEW),
            ),
        )

    def read_identity_transition(
        self, transition_ref: UUID
    ) -> IdentityTransitionSnapshot:
        transition = self.session.get(IdentityTransition, transition_ref)
        if transition is None:
            raise KnowledgeInvariantError(
                f"unknown identity transition: {transition_ref}"
            )
        members = self.session.scalars(
            select(IdentityTransitionMember)
            .where(IdentityTransitionMember.transition_ref_id == transition_ref)
            .order_by(
                IdentityTransitionMember.ordinal,
                IdentityTransitionMember.entity_ref_id,
            )
        ).all()
        return IdentityTransitionSnapshot(
            transition_ref=transition.occurrence_ref_id,
            transition_type=IdentityTransitionType(transition.transition_type),
            reverses_transition_ref=transition.reverses_transition_ref,
            members=tuple(
                IdentityMemberSnapshot(
                    entity_ref=row.entity_ref_id,
                    member_role=IdentityMemberRole(row.member_role),
                    ordinal=row.ordinal,
                )
                for row in members
            ),
            created_revision_id=transition.created_revision_id,
        )

    def identity_history(
        self, *, entity_ref: UUID
    ) -> list[IdentityTransitionSnapshot]:
        self._require_entity(entity_ref)
        transition_refs = self.session.scalars(
            select(IdentityTransitionMember.transition_ref_id)
            .join(
                IdentityTransition,
                IdentityTransitionMember.transition_ref_id
                == IdentityTransition.occurrence_ref_id,
            )
            .where(IdentityTransitionMember.entity_ref_id == entity_ref)
            .order_by(
                IdentityTransition.created_revision_id,
                IdentityTransition.occurrence_ref_id,
            )
        ).all()
        return [self.read_identity_transition(ref) for ref in transition_refs]

    @staticmethod
    def _resolution_group_id(entity_refs: Iterable[UUID]) -> UUID:
        stable_members = ",".join(sorted(str(ref) for ref in entity_refs))
        return uuid5(
            NAMESPACE_URL,
            f"knowledge-core:identity-group:{stable_members}",
        )

    @staticmethod
    def _singleton_group_id(entity_ref: UUID) -> UUID:
        return uuid5(
            NAMESPACE_URL,
            f"knowledge-core:identity-singleton:{entity_ref}",
        )

    def rebuild_current_identity_projection(self) -> int:
        transitions = self.session.scalars(
            select(IdentityTransition).order_by(
                IdentityTransition.created_revision_id,
                IdentityTransition.occurrence_ref_id,
            )
        ).all()
        reversed_transition_refs = {
            transition.reverses_transition_ref
            for transition in transitions
            if transition.reverses_transition_ref is not None
        }
        active_equivalence_transitions = [
            transition
            for transition in transitions
            if transition.transition_type
            in {
                IdentityTransitionType.MERGE.value,
                IdentityTransitionType.RESOLVE_SAME.value,
            }
            and transition.occurrence_ref_id not in reversed_transition_refs
        ]

        parent: dict[UUID, UUID] = {}

        def find(entity_ref: UUID) -> UUID:
            parent.setdefault(entity_ref, entity_ref)
            root = entity_ref
            while parent[root] != root:
                root = parent[root]
            while parent[entity_ref] != entity_ref:
                next_ref = parent[entity_ref]
                parent[entity_ref] = root
                entity_ref = next_ref
            return root

        def union(left: UUID, right: UUID) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root == right_root:
                return
            if str(left_root) <= str(right_root):
                parent[right_root] = left_root
            else:
                parent[left_root] = right_root

        merge_records: list[
            tuple[IdentityTransition, tuple[UUID, ...], UUID]
        ] = []
        for transition in active_equivalence_transitions:
            member_rows = self.session.scalars(
                select(IdentityTransitionMember)
                .where(
                    IdentityTransitionMember.transition_ref_id
                    == transition.occurrence_ref_id
                )
                .order_by(
                    IdentityTransitionMember.ordinal,
                    IdentityTransitionMember.entity_ref_id,
                )
            ).all()
            member_refs = tuple(row.entity_ref_id for row in member_rows)
            if len(member_refs) < 2:
                continue
            first = member_refs[0]
            find(first)
            for member_ref in member_refs[1:]:
                union(first, member_ref)
            representative_rows = [
                row
                for row in member_rows
                if row.member_role == IdentityMemberRole.REPRESENTATIVE.value
            ]
            representative_ref = (
                representative_rows[0].entity_ref_id
                if representative_rows
                else min(member_refs, key=str)
            )
            merge_records.append(
                (transition, member_refs, representative_ref)
            )

        components: dict[UUID, list[UUID]] = defaultdict(list)
        for entity_ref in parent:
            components[find(entity_ref)].append(entity_ref)

        self.session.execute(delete(CurrentIdentityMember))
        self.session.flush()

        row_count = 0
        for component_members in components.values():
            if len(component_members) < 2:
                continue
            component_set = set(component_members)
            relevant_records = [
                record
                for record in merge_records
                if any(member in component_set for member in record[1])
            ]
            if not relevant_records:
                continue
            source_transition, _source_members, representative_ref = max(
                relevant_records,
                key=lambda record: (
                    record[0].created_revision_id,
                    str(record[0].occurrence_ref_id),
                ),
            )
            if representative_ref not in component_set:
                representative_ref = min(component_members, key=str)
            resolution_group_id = self._resolution_group_id(component_members)
            for entity_ref in sorted(component_members, key=str):
                self.session.add(
                    CurrentIdentityMember(
                        entity_ref_id=entity_ref,
                        resolution_group_id=resolution_group_id,
                        representative_ref_id=representative_ref,
                        source_transition_ref=source_transition.occurrence_ref_id,
                        source_revision_id=source_transition.created_revision_id,
                    )
                )
                row_count += 1

        self._commit()
        return row_count

    def clear_current_identity_projection(self) -> None:
        self.session.execute(delete(CurrentIdentityMember))
        self._commit()

    def current_identity(self, *, entity_ref: UUID) -> IdentityResolutionSnapshot:
        entity = self._require_entity(entity_ref)
        row = self.session.execute(
            select(CurrentIdentityMember).where(
                CurrentIdentityMember.entity_ref_id == entity_ref
            )
        ).scalar_one_or_none()
        if row is None:
            return IdentityResolutionSnapshot(
                entity_ref=entity_ref,
                resolution_group_id=self._singleton_group_id(entity_ref),
                representative_ref=entity_ref,
                member_refs=(entity_ref,),
                source_transition_ref=None,
                source_revision_id=entity.created_revision_id,
            )

        group_rows = self.session.scalars(
            select(CurrentIdentityMember)
            .where(
                CurrentIdentityMember.resolution_group_id
                == row.resolution_group_id
            )
            .order_by(CurrentIdentityMember.entity_ref_id)
        ).all()
        return IdentityResolutionSnapshot(
            entity_ref=entity_ref,
            resolution_group_id=row.resolution_group_id,
            representative_ref=row.representative_ref_id,
            member_refs=tuple(
                sorted((item.entity_ref_id for item in group_rows), key=str)
            ),
            source_transition_ref=row.source_transition_ref,
            source_revision_id=row.source_revision_id,
        )

    def are_currently_equivalent(
        self, *, left_entity_ref: UUID, right_entity_ref: UUID
    ) -> bool:
        left = self.current_identity(entity_ref=left_entity_ref)
        right = self.current_identity(entity_ref=right_entity_ref)
        return left.resolution_group_id == right.resolution_group_id
