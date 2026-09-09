from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select

from knowledge_core.application.history import _as_utc
from knowledge_core.application.identity import IdentityKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.deletion import (
    DeletionActionType,
    DeletionBlockedError,
    DeletionCaseSnapshot,
    DeletionCaseStatus,
    DeletionReconciliationState,
    DeletionTargetSnapshot,
    KnowledgeRestrictedError,
)
from knowledge_core.storage.deletion_models import DeletionCase, DeletionTarget
from knowledge_core.storage.identity_models import CurrentIdentityMember
from knowledge_core.storage.models import (
    Assertion,
    AssertionTransition,
    AssertionValue,
    CurrentAssertion,
    KnowledgeRef,
    Revision,
)
from knowledge_core.storage.resource_models import ResourceVersion


_ACTIVE_FENCE_STATUSES = {
    DeletionCaseStatus.FENCED.value,
    DeletionCaseStatus.CANONICAL_PENDING.value,
    DeletionCaseStatus.DERIVATIVES_PENDING.value,
    DeletionCaseStatus.BACKUP_FENCED.value,
    DeletionCaseStatus.SETTLED.value,
    DeletionCaseStatus.BLOCKED.value,
}


class DeletionKnowledgeKernel(IdentityKnowledgeKernel):
    """Task 6 serving fence, minimal erasure, and anti-resurrection replay."""

    def _new_revision(self) -> Revision:
        revision = Revision(
            schema_revision="task6",
            recorded_at=self._now(),
            operation_id=self._active_operation_id,
        )
        self.session.add(revision)
        self.session.flush()
        return revision

    def read_deletion_case(self, case_id: UUID) -> DeletionCaseSnapshot:
        row = self.session.get(DeletionCase, case_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown deletion case: {case_id}")
        targets = self.session.scalars(
            select(DeletionTarget)
            .where(DeletionTarget.case_id == case_id)
            .order_by(DeletionTarget.target_ref_id)
        ).all()
        return DeletionCaseSnapshot(
            case_id=row.case_id,
            operation_id=row.operation_id,
            action_type=DeletionActionType(row.action_type),
            policy_scope_id=row.policy_scope_id,
            status=DeletionCaseStatus(row.status),
            requested_at=_as_utc(row.requested_at),
            settled_at=_as_utc(row.settled_at) if row.settled_at is not None else None,
            targets=tuple(
                DeletionTargetSnapshot(
                    target_ref=target.target_ref_id,
                    reconciliation_state=DeletionReconciliationState(
                        target.reconciliation_state
                    ),
                    last_checked_at=_as_utc(target.last_checked_at),
                )
                for target in targets
            ),
        )

    def _active_fence_exists(self, target_ref: UUID) -> bool:
        return (
            self.session.execute(
                select(DeletionTarget.case_id)
                .join(DeletionCase, DeletionTarget.case_id == DeletionCase.case_id)
                .where(
                    DeletionTarget.target_ref_id == target_ref,
                    DeletionCase.action_type.in_(
                        [DeletionActionType.RESTRICT.value, DeletionActionType.ERASE.value]
                    ),
                    DeletionCase.status.in_(_ACTIVE_FENCE_STATUSES),
                )
                .limit(1)
            ).scalar_one_or_none()
            is not None
        )

    def _purge_derived_for_target(self, target_ref: UUID) -> None:
        referenced_assertions = self.session.scalars(
            select(AssertionValue.assertion_ref_id).where(
                AssertionValue.reference_value == target_ref
            )
        ).all()

        clauses = [
            CurrentAssertion.assertion_ref_id == target_ref,
            CurrentAssertion.subject_ref_id == target_ref,
        ]
        if referenced_assertions:
            clauses.append(CurrentAssertion.assertion_ref_id.in_(referenced_assertions))
        self.session.execute(delete(CurrentAssertion).where(or_(*clauses)))

        self.session.execute(
            delete(CurrentIdentityMember).where(
                or_(
                    CurrentIdentityMember.entity_ref_id == target_ref,
                    CurrentIdentityMember.representative_ref_id == target_ref,
                )
            )
        )

    def _apply_fence(self, target_ref: UUID) -> None:
        ref = self.session.get(KnowledgeRef, target_ref)
        if ref is None:
            raise KnowledgeInvariantError(f"unknown knowledge ref: {target_ref}")
        if ref.payload_state != "erased_tombstone":
            ref.payload_state = "restricted"
        self._purge_derived_for_target(target_ref)

    def fence_target_operation(
        self,
        *,
        operation_id: UUID,
        target_ref: UUID,
        action_type: DeletionActionType,
        policy_scope_id: str,
        caller_principal_ref: str = "kernel-test-privacy-controller",
    ) -> DeletionCaseSnapshot:
        if action_type is DeletionActionType.RETENTION_EXCEPTION:
            raise KnowledgeInvariantError(
                "Task 6 fence operation supports restrict or erase only"
            )
        if not policy_scope_id:
            raise KnowledgeInvariantError("policy_scope_id must not be empty")

        payload = {
            "target_ref": str(target_ref),
            "action_type": action_type.value,
            "policy_scope_id": policy_scope_id,
        }

        def action() -> DeletionCaseSnapshot:
            if self.session.get(KnowledgeRef, target_ref) is None:
                raise KnowledgeInvariantError(f"unknown knowledge ref: {target_ref}")
            if self._active_fence_exists(target_ref):
                raise KnowledgeInvariantError(
                    f"target already has an active deletion/restriction fence: {target_ref}"
                )

            revision = self._new_revision()
            now = revision.recorded_at
            case_id = uuid4()
            case = DeletionCase(
                case_id=case_id,
                operation_id=operation_id,
                action_type=action_type.value,
                policy_scope_id=policy_scope_id,
                status=DeletionCaseStatus.FENCED.value,
                requested_at=now,
                settled_at=None,
                minimal_metadata={"target_count": 1},
            )
            self.session.add(case)
            self.session.flush()
            self.session.add(
                DeletionTarget(
                    case_id=case_id,
                    target_ref_id=target_ref,
                    reconciliation_state=DeletionReconciliationState.FENCED.value,
                    last_checked_at=now,
                )
            )
            self._apply_fence(target_ref)
            self.session.flush()
            return self.read_deletion_case(case_id)

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="deletion_fence",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=None,
            action=action,
            encode_result=lambda result: {"case_id": str(result.case_id)},
            replay=lambda metadata: self.read_deletion_case(
                UUID(str(metadata["case_id"]))
            ),
        )

    def _case_target(
        self, *, case_id: UUID, target_ref: UUID
    ) -> tuple[DeletionCase, DeletionTarget]:
        case = self.session.get(DeletionCase, case_id)
        target = self.session.get(
            DeletionTarget,
            {"case_id": case_id, "target_ref_id": target_ref},
        )
        if case is None or target is None:
            raise KnowledgeInvariantError(
                f"target {target_ref} is not part of deletion case {case_id}"
            )
        return case, target

    def settle_restriction(self, *, case_id: UUID, target_ref: UUID) -> None:
        case, target = self._case_target(case_id=case_id, target_ref=target_ref)
        if case.action_type != DeletionActionType.RESTRICT.value:
            raise KnowledgeInvariantError("only restrict cases can settle as restriction")
        self._apply_fence(target_ref)
        now = self._now()
        target.reconciliation_state = (
            DeletionReconciliationState.RESTRICTED_SETTLED.value
        )
        target.last_checked_at = now
        case.status = DeletionCaseStatus.SETTLED.value
        case.settled_at = now
        self.session.commit()

    def erase_assertion_payload(self, *, case_id: UUID, target_ref: UUID) -> None:
        case, target = self._case_target(case_id=case_id, target_ref=target_ref)
        if case.action_type != DeletionActionType.ERASE.value:
            raise KnowledgeInvariantError("physical erasure requires an erase case")

        ref = self.session.get(KnowledgeRef, target_ref)
        if ref is None:
            raise KnowledgeInvariantError(f"unknown knowledge ref: {target_ref}")
        if ref.ref_kind != "assertion":
            raise KnowledgeInvariantError(
                "Task 6 minimal physical erasure supports assertion payloads only"
            )

        transition_dependency = self.session.execute(
            select(AssertionTransition.occurrence_ref_id)
            .where(
                or_(
                    AssertionTransition.source_assertion_ref == target_ref,
                    AssertionTransition.replacement_assertion_ref == target_ref,
                )
            )
            .limit(1)
        ).scalar_one_or_none()
        if transition_dependency is not None:
            now = self._now()
            target.reconciliation_state = DeletionReconciliationState.BLOCKED.value
            target.last_checked_at = now
            case.status = DeletionCaseStatus.BLOCKED.value
            self.session.commit()
            raise DeletionBlockedError(
                "assertion participates in lifecycle history and cannot be minimally erased"
            )

        self._purge_derived_for_target(target_ref)
        self.session.execute(
            delete(AssertionValue).where(AssertionValue.assertion_ref_id == target_ref)
        )
        self.session.execute(delete(Assertion).where(Assertion.ref_id == target_ref))
        ref.payload_state = "erased_tombstone"

        now = self._now()
        target.reconciliation_state = DeletionReconciliationState.ERASED_TOMBSTONE.value
        target.last_checked_at = now
        case.status = DeletionCaseStatus.SETTLED.value
        case.settled_at = now
        self.session.commit()

    def _direct_ref_serving_eligible(self, ref_id: UUID) -> bool:
        ref = self.session.get(KnowledgeRef, ref_id)
        if ref is None:
            return False
        if ref.payload_state != "active":
            return False
        return not self._active_fence_exists(ref_id)

    def assertion_serving_eligible(self, assertion_ref: UUID) -> bool:
        if not self._direct_ref_serving_eligible(assertion_ref):
            return False
        assertion = self.session.get(Assertion, assertion_ref)
        if assertion is None:
            return False
        if not self._direct_ref_serving_eligible(assertion.subject_ref_id):
            return False
        value = self.session.get(AssertionValue, assertion_ref)
        if value is not None and value.reference_value is not None:
            if not self._direct_ref_serving_eligible(value.reference_value):
                return False
        return True

    def resource_version_serving_eligible(self, resource_version_ref: UUID) -> bool:
        if not self._direct_ref_serving_eligible(resource_version_ref):
            return False
        version = self.session.get(ResourceVersion, resource_version_ref)
        if version is None:
            return False
        return self._direct_ref_serving_eligible(version.resource_ref_id)

    def read_assertion_serving(self, assertion_ref: UUID):
        if not self.assertion_serving_eligible(assertion_ref):
            raise KnowledgeRestrictedError(
                f"assertion is unavailable to serving reads: {assertion_ref}"
            )
        return super().read_assertion(assertion_ref)

    def read_resource_version_serving(self, resource_version_ref: UUID):
        if not self.resource_version_serving_eligible(resource_version_ref):
            raise KnowledgeRestrictedError(
                f"resource version is unavailable to serving reads: {resource_version_ref}"
            )
        return super().read_resource_version(resource_version_ref)

    def current_projection(self, **kwargs):
        return [
            item
            for item in super().current_projection(**kwargs)
            if self.assertion_serving_eligible(item.assertion.assertion_ref)
        ]

    def belief(self, **kwargs):
        return [
            item
            for item in super().belief(**kwargs)
            if self.assertion_serving_eligible(item.assertion.assertion_ref)
        ]

    def rebuild_current_projection(self, **kwargs) -> int:
        super().rebuild_current_projection(**kwargs)
        self.reapply_deletion_control_before_serving()
        return len(self.current_projection())

    def reapply_deletion_control_before_serving(self) -> int:
        rows = self.session.execute(
            select(DeletionCase, DeletionTarget)
            .join(DeletionTarget, DeletionCase.case_id == DeletionTarget.case_id)
            .where(
                DeletionCase.action_type.in_(
                    [DeletionActionType.RESTRICT.value, DeletionActionType.ERASE.value]
                ),
                DeletionCase.status.in_(_ACTIVE_FENCE_STATUSES),
            )
        ).all()

        for case, target in rows:
            ref = self.session.get(KnowledgeRef, target.target_ref_id)
            if ref is None:
                continue
            if (
                target.reconciliation_state
                == DeletionReconciliationState.ERASED_TOMBSTONE.value
            ):
                ref.payload_state = "erased_tombstone"
            else:
                ref.payload_state = "restricted"
            self._purge_derived_for_target(target.target_ref_id)
            target.last_checked_at = self._now()

        self.session.commit()
        return len(rows)
