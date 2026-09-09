from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from knowledge_core.application.identity import IdentityKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError, TypedValue
from knowledge_core.domain.identity import (
    IdentityMemberRole,
    IdentityTransitionType,
)
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)
from knowledge_core.storage.identity_models import CurrentIdentityMember
from knowledge_core.storage.models import Assertion


@pytest.fixture()
def kernel(tmp_path):
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    session = create_session_factory(engine)()
    service = IdentityKnowledgeKernel(
        session,
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )
    refs = service.bootstrap_identity_test_profile()
    try:
        yield service, refs, session
    finally:
        session.close()
        engine.dispose()


def test_reversible_merge_preserves_assertions_and_recovers_separate_identities(kernel):
    service, refs, session = kernel
    first_person = service.create_entity(refs.person_kind_revision_ref)
    second_person = service.create_entity(refs.person_kind_revision_ref)
    first_name_assertion = service.append_assertion(
        subject_ref=first_person,
        predicate_revision_ref=refs.has_name_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.text("Robert Smith"),
    )
    second_name_assertion = service.append_assertion(
        subject_ref=second_person,
        predicate_revision_ref=refs.has_name_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.text("Robert Smith"),
    )
    first_before = service.read_assertion(first_name_assertion)
    second_before = service.read_assertion(second_name_assertion)
    assertion_count_before = session.scalar(select(func.count()).select_from(Assertion))

    merge = service.merge_entities(
        entity_refs=(first_person, second_person),
        representative_ref=first_person,
        identity_kind_revision_ref=refs.identity_resolution_kind_revision_ref,
    )
    assert merge.transition_type is IdentityTransitionType.MERGE
    assert {
        (member.entity_ref, member.member_role) for member in merge.members
    } == {
        (first_person, IdentityMemberRole.REPRESENTATIVE),
        (second_person, IdentityMemberRole.MEMBER),
    }
    assert service.read_assertion(first_name_assertion) == first_before
    assert service.read_assertion(second_name_assertion) == second_before
    assert session.scalar(select(func.count()).select_from(Assertion)) == assertion_count_before

    assert service.rebuild_current_identity_projection() == 2
    first_merged = service.current_identity(entity_ref=first_person)
    second_merged = service.current_identity(entity_ref=second_person)
    assert first_merged.resolution_group_id == second_merged.resolution_group_id
    assert first_merged.representative_ref == second_merged.representative_ref == first_person
    assert set(first_merged.member_refs) == {first_person, second_person}
    assert service.are_currently_equivalent(
        left_entity_ref=first_person,
        right_entity_ref=second_person,
    )

    split = service.reverse_identity_transition(
        transition_ref=merge.transition_ref,
        identity_kind_revision_ref=refs.identity_resolution_kind_revision_ref,
    )
    assert split.transition_type is IdentityTransitionType.SPLIT
    assert split.reverses_transition_ref == merge.transition_ref
    assert all(
        member.member_role is IdentityMemberRole.SPLIT_MEMBER
        for member in split.members
    )

    assert service.rebuild_current_identity_projection() == 0
    first_restored = service.current_identity(entity_ref=first_person)
    second_restored = service.current_identity(entity_ref=second_person)
    assert first_restored.member_refs == (first_person,)
    assert second_restored.member_refs == (second_person,)
    assert first_restored.resolution_group_id != second_restored.resolution_group_id
    assert not service.are_currently_equivalent(
        left_entity_ref=first_person,
        right_entity_ref=second_person,
    )
    assert service.read_assertion(first_name_assertion) == first_before
    assert service.read_assertion(second_name_assertion) == second_before
    assert session.scalar(select(func.count()).select_from(Assertion)) == assertion_count_before

    history = service.identity_history(entity_ref=first_person)
    assert [item.transition_type for item in history] == [
        IdentityTransitionType.MERGE,
        IdentityTransitionType.SPLIT,
    ]


def test_merge_reversal_is_explicit_and_cannot_be_applied_twice(kernel):
    service, refs, _session = kernel
    first_person = service.create_entity(refs.person_kind_revision_ref)
    second_person = service.create_entity(refs.person_kind_revision_ref)
    merge = service.merge_entities(
        entity_refs=(first_person, second_person),
        representative_ref=first_person,
        identity_kind_revision_ref=refs.identity_resolution_kind_revision_ref,
    )
    service.reverse_identity_transition(
        transition_ref=merge.transition_ref,
        identity_kind_revision_ref=refs.identity_resolution_kind_revision_ref,
    )

    with pytest.raises(KnowledgeInvariantError, match="already been reversed"):
        service.reverse_identity_transition(
            transition_ref=merge.transition_ref,
            identity_kind_revision_ref=refs.identity_resolution_kind_revision_ref,
        )


def test_replace_transition_is_succession_not_identity_equivalence(kernel):
    service, refs, session = kernel
    old_device = service.create_entity(refs.device_kind_revision_ref)
    new_device = service.create_entity(refs.device_kind_revision_ref)
    old_name_assertion = service.append_assertion(
        subject_ref=old_device,
        predicate_revision_ref=refs.has_name_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.text("Controller v1"),
    )
    new_name_assertion = service.append_assertion(
        subject_ref=new_device,
        predicate_revision_ref=refs.has_name_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.text("Controller v2"),
    )

    replacement = service.replace_entity(
        old_entity_ref=old_device,
        new_entity_ref=new_device,
        identity_kind_revision_ref=refs.identity_resolution_kind_revision_ref,
    )
    assert replacement.transition_type is IdentityTransitionType.REPLACE
    assert [(member.entity_ref, member.member_role) for member in replacement.members] == [
        (old_device, IdentityMemberRole.OLD),
        (new_device, IdentityMemberRole.NEW),
    ]

    assert service.rebuild_current_identity_projection() == 0
    assert not service.are_currently_equivalent(
        left_entity_ref=old_device,
        right_entity_ref=new_device,
    )
    assert service.current_identity(entity_ref=old_device).member_refs == (old_device,)
    assert service.current_identity(entity_ref=new_device).member_refs == (new_device,)
    assert session.scalar(select(func.count()).select_from(CurrentIdentityMember)) == 0

    assert service.read_assertion(old_name_assertion).subject_ref == old_device
    assert service.read_assertion(new_name_assertion).subject_ref == new_device
    assert [
        item.transition_type for item in service.identity_history(entity_ref=old_device)
    ] == [IdentityTransitionType.REPLACE]
    assert [
        item.transition_type for item in service.identity_history(entity_ref=new_device)
    ] == [IdentityTransitionType.REPLACE]


def test_current_identity_projection_rebuild_is_deterministic(kernel):
    service, refs, session = kernel
    first_person = service.create_entity(refs.person_kind_revision_ref)
    second_person = service.create_entity(refs.person_kind_revision_ref)
    merge = service.merge_entities(
        entity_refs=(first_person, second_person),
        representative_ref=second_person,
        identity_kind_revision_ref=refs.identity_resolution_kind_revision_ref,
    )

    assert service.rebuild_current_identity_projection() == 2
    first_rows = session.execute(
        select(
            CurrentIdentityMember.entity_ref_id,
            CurrentIdentityMember.resolution_group_id,
            CurrentIdentityMember.representative_ref_id,
            CurrentIdentityMember.source_transition_ref,
            CurrentIdentityMember.source_revision_id,
        ).order_by(CurrentIdentityMember.entity_ref_id)
    ).all()
    assert {row.source_transition_ref for row in first_rows} == {merge.transition_ref}

    service.clear_current_identity_projection()
    assert session.scalar(select(func.count()).select_from(CurrentIdentityMember)) == 0
    assert service.rebuild_current_identity_projection() == 2
    second_rows = session.execute(
        select(
            CurrentIdentityMember.entity_ref_id,
            CurrentIdentityMember.resolution_group_id,
            CurrentIdentityMember.representative_ref_id,
            CurrentIdentityMember.source_transition_ref,
            CurrentIdentityMember.source_revision_id,
        ).order_by(CurrentIdentityMember.entity_ref_id)
    ).all()
    assert second_rows == first_rows


def test_invalid_identity_transition_shapes_are_rejected(kernel):
    service, refs, _session = kernel
    person = service.create_entity(refs.person_kind_revision_ref)
    other = service.create_entity(refs.person_kind_revision_ref)

    with pytest.raises(KnowledgeInvariantError, match="at least two"):
        service.merge_entities(
            entity_refs=(person,),
            representative_ref=person,
            identity_kind_revision_ref=refs.identity_resolution_kind_revision_ref,
        )
    with pytest.raises(KnowledgeInvariantError, match="must be unique"):
        service.merge_entities(
            entity_refs=(person, person),
            representative_ref=person,
            identity_kind_revision_ref=refs.identity_resolution_kind_revision_ref,
        )
    with pytest.raises(KnowledgeInvariantError, match="must be one of"):
        service.merge_entities(
            entity_refs=(person, other),
            representative_ref=uuid4(),
            identity_kind_revision_ref=refs.identity_resolution_kind_revision_ref,
        )
    with pytest.raises(KnowledgeInvariantError, match="distinct"):
        service.replace_entity(
            old_entity_ref=person,
            new_entity_ref=person,
            identity_kind_revision_ref=refs.identity_resolution_kind_revision_ref,
        )
