from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from knowledge_core.application.deletion import DeletionKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import TypedValue
from knowledge_core.domain.deletion import (
    DeletionActionType,
    DeletionReconciliationState,
    KnowledgeRestrictedError,
)
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)
from knowledge_core.storage.deletion_models import DeletionCase
from knowledge_core.storage.models import (
    Assertion,
    AssertionValue,
    CurrentAssertion,
    KnowledgeRef,
)


@pytest.fixture()
def kernel(tmp_path):
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    session = create_session_factory(engine)()
    service = DeletionKnowledgeKernel(
        session,
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )
    refs = service.bootstrap_identity_test_profile()
    resource_refs = service.bootstrap_resource_test_profile()
    try:
        yield service, refs, resource_refs, session
    finally:
        session.close()
        engine.dispose()


def _named_person(service, refs, name="Robert Smith"):
    person = service.create_entity(refs.person_kind_revision_ref)
    assertion_ref = service.append_assertion(
        subject_ref=person,
        predicate_revision_ref=refs.has_name_predicate_revision_ref,
        profile_revision_ref=refs.profile_revision_ref,
        value=TypedValue.text(name),
    )
    return person, assertion_ref


def test_restriction_fence_hides_assertion_before_payload_cleanup(kernel):
    service, refs, _resource_refs, session = kernel
    _person, assertion_ref = _named_person(service, refs)
    assert service.rebuild_current_projection() == 1
    assert service.read_assertion_serving(assertion_ref).assertion_ref == assertion_ref

    case = service.fence_target_operation(
        operation_id=uuid4(),
        target_ref=assertion_ref,
        action_type=DeletionActionType.RESTRICT,
        policy_scope_id="privacy:test",
    )

    assert case.targets[0].reconciliation_state is DeletionReconciliationState.FENCED
    assert session.get(Assertion, assertion_ref) is not None
    assert session.scalar(
        select(func.count())
        .select_from(CurrentAssertion)
        .where(CurrentAssertion.assertion_ref_id == assertion_ref)
    ) == 0
    with pytest.raises(KnowledgeRestrictedError):
        service.read_assertion_serving(assertion_ref)
    assert service.current_projection() == []

    service.settle_restriction(case_id=case.case_id, target_ref=assertion_ref)
    assert service.read_deletion_case(case.case_id).status.value == "settled"


def test_resource_fence_hides_exact_version_serving_read(kernel):
    service, _refs, resource_refs, _session = kernel
    resource = service.create_resource(
        kind_revision_ref=resource_refs.artifact_kind_revision_ref
    )
    version = service.ingest_resource_version(
        resource_ref=resource.resource_ref,
        content=b"sensitive source",
        ingestion_kind_revision_ref=resource_refs.resource_ingestion_kind_revision_ref,
    )
    assert service.read_resource_version_serving(
        version.resource_version_ref
    ).content_digest == version.content_digest

    service.fence_target_operation(
        operation_id=uuid4(),
        target_ref=resource.resource_ref,
        action_type=DeletionActionType.RESTRICT,
        policy_scope_id="privacy:resource",
    )

    with pytest.raises(KnowledgeRestrictedError):
        service.read_resource_version_serving(version.resource_version_ref)


def test_minimal_assertion_erasure_leaves_only_opaque_tombstone(kernel):
    service, refs, _resource_refs, session = kernel
    _person, assertion_ref = _named_person(service, refs, "Erase Me")
    case = service.fence_target_operation(
        operation_id=uuid4(),
        target_ref=assertion_ref,
        action_type=DeletionActionType.ERASE,
        policy_scope_id="privacy:erase",
    )

    service.erase_assertion_payload(
        case_id=case.case_id,
        target_ref=assertion_ref,
    )

    assert session.get(Assertion, assertion_ref) is None
    assert session.get(AssertionValue, assertion_ref) is None
    tombstone = session.get(KnowledgeRef, assertion_ref)
    assert tombstone is not None
    assert tombstone.ref_kind == "assertion"
    assert tombstone.payload_state == "erased_tombstone"

    settled = service.read_deletion_case(case.case_id)
    assert settled.status.value == "settled"
    assert (
        settled.targets[0].reconciliation_state
        is DeletionReconciliationState.ERASED_TOMBSTONE
    )
    with pytest.raises(KnowledgeRestrictedError):
        service.read_assertion_serving(assertion_ref)


def test_anti_resurrection_control_fence_wins_over_stale_restored_state(kernel):
    service, refs, _resource_refs, session = kernel
    _person, assertion_ref = _named_person(service, refs)
    assert service.rebuild_current_projection() == 1

    case = service.fence_target_operation(
        operation_id=uuid4(),
        target_ref=assertion_ref,
        action_type=DeletionActionType.RESTRICT,
        policy_scope_id="privacy:restore-fence",
    )
    service.settle_restriction(case_id=case.case_id, target_ref=assertion_ref)

    # Simulate restoration of stale canonical/derived state that predates the fence
    # while the higher-durability deletion-control ledger remains newer.
    ref = session.get(KnowledgeRef, assertion_ref)
    ref.payload_state = "active"
    assertion = session.get(Assertion, assertion_ref)
    session.add(
        CurrentAssertion(
            assertion_ref_id=assertion_ref,
            subject_ref_id=assertion.subject_ref_id,
            predicate_revision_ref=assertion.predicate_revision_ref,
            conflict_group_id=None,
            source_revision_id=assertion.created_revision_id,
            projection_revision_id=service.current_revision(),
            selection_reason="stale-restored-fixture",
        )
    )
    session.commit()

    # Even before reconciliation, serving reads consult the newer control ledger.
    assert service.current_projection() == []
    with pytest.raises(KnowledgeRestrictedError):
        service.read_assertion_serving(assertion_ref)

    assert service.reapply_deletion_control_before_serving() == 1
    assert session.get(KnowledgeRef, assertion_ref).payload_state == "restricted"
    assert session.scalar(
        select(func.count())
        .select_from(CurrentAssertion)
        .where(CurrentAssertion.assertion_ref_id == assertion_ref)
    ) == 0


def test_identical_fence_retry_replays_one_case(kernel):
    service, refs, _resource_refs, session = kernel
    _person, assertion_ref = _named_person(service, refs)
    operation_id = uuid4()

    first = service.fence_target_operation(
        operation_id=operation_id,
        target_ref=assertion_ref,
        action_type=DeletionActionType.RESTRICT,
        policy_scope_id="privacy:retry",
    )
    second = service.fence_target_operation(
        operation_id=operation_id,
        target_ref=assertion_ref,
        action_type=DeletionActionType.RESTRICT,
        policy_scope_id="privacy:retry",
    )

    assert second == first
    assert session.scalar(select(func.count()).select_from(DeletionCase)) == 1


def test_projection_rebuild_cannot_resurrect_fenced_assertion(kernel):
    service, refs, _resource_refs, session = kernel
    _person, assertion_ref = _named_person(service, refs)
    assert service.rebuild_current_projection() == 1

    service.fence_target_operation(
        operation_id=uuid4(),
        target_ref=assertion_ref,
        action_type=DeletionActionType.RESTRICT,
        policy_scope_id="privacy:projection",
    )

    assert service.rebuild_current_projection() == 0
    assert session.scalar(
        select(func.count())
        .select_from(CurrentAssertion)
        .where(CurrentAssertion.assertion_ref_id == assertion_ref)
    ) == 0
