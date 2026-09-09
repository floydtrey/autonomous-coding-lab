from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select

from knowledge_core.application.service import ServiceKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError, RefKind
from knowledge_core.domain.profiles import (
    AssertionSemanticResolution,
    ProfileActivationSnapshot,
    ProfileRevisionSnapshot,
    ProfileVocabularySnapshot,
    VocabularyRevisionSnapshot,
)
from knowledge_core.storage.control_models import ProfileActivation
from knowledge_core.storage.models import (
    Assertion,
    Revision,
    SemanticKind,
    SemanticKindRevision,
    SemanticPredicate,
    SemanticPredicateRevision,
    SemanticProfile,
    SemanticProfileRevision,
)


_ALLOWED_VALUE_SHAPES = {"scalar", "reference"}


class ProfileKnowledgeKernel(ServiceKnowledgeKernel):
    """Task 8 immutable semantic-profile revisions and operational activation."""

    def _new_revision(self) -> Revision:
        revision = Revision(
            schema_revision="task8",
            recorded_at=self._now(),
            operation_id=self._active_operation_id,
        )
        self.session.add(revision)
        self.session.flush()
        return revision

    def read_profile_revision(
        self, profile_revision_ref: UUID
    ) -> ProfileRevisionSnapshot:
        row = self.session.get(SemanticProfileRevision, profile_revision_ref)
        if row is None:
            raise KnowledgeInvariantError(
                f"unknown semantic profile revision: {profile_revision_ref}"
            )
        return ProfileRevisionSnapshot(
            profile_revision_ref=row.ref_id,
            profile_ref=row.profile_ref_id,
            version_label=row.version_label,
            status=row.status,
            created_revision_id=row.created_revision_id,
        )

    def read_profile_activation(
        self, activation_id: UUID
    ) -> ProfileActivationSnapshot:
        row = self.session.get(ProfileActivation, activation_id)
        if row is None:
            raise KnowledgeInvariantError(
                f"unknown semantic profile activation: {activation_id}"
            )
        return ProfileActivationSnapshot(
            activation_id=row.activation_id,
            profile_ref=row.profile_ref_id,
            profile_revision_ref=row.profile_revision_ref_id,
            activated_revision_id=row.activated_revision_id,
            activated_at=row.activated_at,
        )

    def profile_activation_history(
        self, *, profile_ref: UUID
    ) -> tuple[ProfileActivationSnapshot, ...]:
        rows = self.session.scalars(
            select(ProfileActivation)
            .where(ProfileActivation.profile_ref_id == profile_ref)
            .order_by(
                ProfileActivation.activated_revision_id,
                ProfileActivation.activation_id,
            )
        ).all()
        return tuple(self.read_profile_activation(row.activation_id) for row in rows)

    def active_profile_revision(self, *, profile_ref: UUID) -> ProfileRevisionSnapshot:
        row = self.session.scalars(
            select(ProfileActivation)
            .where(ProfileActivation.profile_ref_id == profile_ref)
            .order_by(
                ProfileActivation.activated_revision_id.desc(),
                ProfileActivation.activation_id.desc(),
            )
            .limit(1)
        ).first()
        if row is None:
            raise KnowledgeInvariantError(
                f"semantic profile has no active revision: {profile_ref}"
            )
        return self.read_profile_revision(row.profile_revision_ref_id)

    def profile_vocabulary(
        self, *, profile_revision_ref: UUID
    ) -> ProfileVocabularySnapshot:
        profile_revision = self.read_profile_revision(profile_revision_ref)

        kind_rows = self.session.execute(
            select(SemanticKindRevision, SemanticKind)
            .join(
                SemanticKind,
                SemanticKindRevision.kind_ref_id == SemanticKind.ref_id,
            )
            .where(
                SemanticKindRevision.profile_revision_ref_id == profile_revision_ref
            )
            .order_by(SemanticKind.stable_name, SemanticKindRevision.ref_id)
        ).all()

        predicate_rows = self.session.execute(
            select(SemanticPredicateRevision, SemanticPredicate)
            .join(
                SemanticPredicate,
                SemanticPredicateRevision.predicate_ref_id == SemanticPredicate.ref_id,
            )
            .where(
                SemanticPredicateRevision.profile_revision_ref_id
                == profile_revision_ref
            )
            .order_by(
                SemanticPredicate.stable_name,
                SemanticPredicateRevision.ref_id,
            )
        ).all()

        return ProfileVocabularySnapshot(
            profile_revision=profile_revision,
            kinds=tuple(
                VocabularyRevisionSnapshot(
                    semantic_ref=kind.ref_id,
                    revision_ref=kind_revision.ref_id,
                    stable_name=kind.stable_name,
                )
                for kind_revision, kind in kind_rows
            ),
            predicates=tuple(
                VocabularyRevisionSnapshot(
                    semantic_ref=predicate.ref_id,
                    revision_ref=predicate_revision.ref_id,
                    stable_name=predicate.stable_name,
                    value_shape=predicate_revision.value_shape,
                )
                for predicate_revision, predicate in predicate_rows
            ),
        )

    def read_predicate_revision(
        self, predicate_revision_ref: UUID
    ) -> VocabularyRevisionSnapshot:
        row = self.session.get(SemanticPredicateRevision, predicate_revision_ref)
        if row is None:
            raise KnowledgeInvariantError(
                f"unknown semantic predicate revision: {predicate_revision_ref}"
            )
        predicate = self.session.get(SemanticPredicate, row.predicate_ref_id)
        assert predicate is not None
        return VocabularyRevisionSnapshot(
            semantic_ref=predicate.ref_id,
            revision_ref=row.ref_id,
            stable_name=predicate.stable_name,
            value_shape=row.value_shape,
        )

    def resolve_assertion_semantics(
        self, assertion_ref: UUID
    ) -> AssertionSemanticResolution:
        assertion = self.session.get(Assertion, assertion_ref)
        if assertion is None:
            raise KnowledgeInvariantError(f"unknown assertion: {assertion_ref}")

        profile_revision = self.session.get(
            SemanticProfileRevision, assertion.profile_revision_ref
        )
        predicate_revision = self.session.get(
            SemanticPredicateRevision, assertion.predicate_revision_ref
        )
        if profile_revision is None or predicate_revision is None:
            raise KnowledgeInvariantError(
                f"assertion has missing semantic revision refs: {assertion_ref}"
            )
        if predicate_revision.profile_revision_ref_id != profile_revision.ref_id:
            raise KnowledgeInvariantError(
                "assertion predicate revision is not pinned to assertion profile revision"
            )

        profile = self.session.get(SemanticProfile, profile_revision.profile_ref_id)
        predicate = self.session.get(
            SemanticPredicate, predicate_revision.predicate_ref_id
        )
        assert profile is not None and predicate is not None
        return AssertionSemanticResolution(
            assertion_ref=assertion.ref_id,
            profile_ref=profile.ref_id,
            profile_revision_ref=profile_revision.ref_id,
            profile_version_label=profile_revision.version_label,
            predicate_ref=predicate.ref_id,
            predicate_revision_ref=predicate_revision.ref_id,
            predicate_stable_name=predicate.stable_name,
            predicate_value_shape=predicate_revision.value_shape,
        )

    def create_profile_revision_operation(
        self,
        *,
        operation_id: UUID,
        profile_ref: UUID,
        source_profile_revision_ref: UUID,
        version_label: str,
        caller_principal_ref: str = "kernel-profile-admin",
        expected_revision: int | None = None,
    ) -> ProfileRevisionSnapshot:
        if not version_label.strip():
            raise KnowledgeInvariantError("profile version_label must not be empty")

        payload = {
            "profile_ref": str(profile_ref),
            "source_profile_revision_ref": str(source_profile_revision_ref),
            "version_label": version_label,
        }

        def action() -> ProfileRevisionSnapshot:
            profile = self.session.get(SemanticProfile, profile_ref)
            source = self.session.get(
                SemanticProfileRevision, source_profile_revision_ref
            )
            if profile is None:
                raise KnowledgeInvariantError(
                    f"unknown semantic profile: {profile_ref}"
                )
            if source is None or source.profile_ref_id != profile_ref:
                raise KnowledgeInvariantError(
                    "source profile revision does not belong to semantic profile"
                )

            existing = self.session.execute(
                select(SemanticProfileRevision).where(
                    SemanticProfileRevision.profile_ref_id == profile_ref,
                    SemanticProfileRevision.version_label == version_label,
                )
            ).scalar_one_or_none()
            if existing is not None:
                raise KnowledgeInvariantError(
                    f"profile version already exists: {profile.stable_name}@{version_label}"
                )

            revision = self._new_revision()
            new_profile_revision_ref = self._new_ref(
                RefKind.SEMANTIC_PROFILE_REVISION, revision.revision_id
            )
            self.session.add(
                SemanticProfileRevision(
                    ref_id=new_profile_revision_ref,
                    profile_ref_id=profile_ref,
                    version_label=version_label,
                    status="active-capable",
                    created_revision_id=revision.revision_id,
                )
            )
            self.session.flush()

            source_kinds = self.session.scalars(
                select(SemanticKindRevision).where(
                    SemanticKindRevision.profile_revision_ref_id
                    == source_profile_revision_ref
                )
            ).all()
            for source_kind in source_kinds:
                kind_revision_ref = self._new_ref(
                    RefKind.SEMANTIC_KIND_REVISION, revision.revision_id
                )
                self.session.add(
                    SemanticKindRevision(
                        ref_id=kind_revision_ref,
                        kind_ref_id=source_kind.kind_ref_id,
                        profile_revision_ref_id=new_profile_revision_ref,
                        created_revision_id=revision.revision_id,
                    )
                )

            source_predicates = self.session.scalars(
                select(SemanticPredicateRevision).where(
                    SemanticPredicateRevision.profile_revision_ref_id
                    == source_profile_revision_ref
                )
            ).all()
            for source_predicate in source_predicates:
                predicate_revision_ref = self._new_ref(
                    RefKind.SEMANTIC_PREDICATE_REVISION, revision.revision_id
                )
                self.session.add(
                    SemanticPredicateRevision(
                        ref_id=predicate_revision_ref,
                        predicate_ref_id=source_predicate.predicate_ref_id,
                        profile_revision_ref_id=new_profile_revision_ref,
                        value_shape=source_predicate.value_shape,
                        created_revision_id=revision.revision_id,
                    )
                )

            self._commit()
            return self.read_profile_revision(new_profile_revision_ref)

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="create_profile_revision",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {
                "profile_revision_ref": str(result.profile_revision_ref)
            },
            replay=lambda metadata: self.read_profile_revision(
                UUID(str(metadata["profile_revision_ref"]))
            ),
        )

    def activate_profile_revision_operation(
        self,
        *,
        operation_id: UUID,
        profile_ref: UUID,
        profile_revision_ref: UUID,
        caller_principal_ref: str = "kernel-profile-admin",
        expected_revision: int | None = None,
    ) -> ProfileActivationSnapshot:
        payload = {
            "profile_ref": str(profile_ref),
            "profile_revision_ref": str(profile_revision_ref),
        }

        def action() -> ProfileActivationSnapshot:
            profile = self.session.get(SemanticProfile, profile_ref)
            profile_revision = self.session.get(
                SemanticProfileRevision, profile_revision_ref
            )
            if profile is None:
                raise KnowledgeInvariantError(
                    f"unknown semantic profile: {profile_ref}"
                )
            if (
                profile_revision is None
                or profile_revision.profile_ref_id != profile_ref
            ):
                raise KnowledgeInvariantError(
                    "profile revision does not belong to semantic profile"
                )
            if profile_revision.status != "active-capable":
                raise KnowledgeInvariantError(
                    "only active-capable profile revisions can be activated for new writes"
                )

            revision = self._new_revision()
            activation_id = uuid4()
            self.session.add(
                ProfileActivation(
                    activation_id=activation_id,
                    profile_ref_id=profile_ref,
                    profile_revision_ref_id=profile_revision_ref,
                    activated_revision_id=revision.revision_id,
                    activated_at=revision.recorded_at,
                )
            )
            self._commit()
            return self.read_profile_activation(activation_id)

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="activate_profile_revision",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {"activation_id": str(result.activation_id)},
            replay=lambda metadata: self.read_profile_activation(
                UUID(str(metadata["activation_id"]))
            ),
        )

    def create_predicate_revision_operation(
        self,
        *,
        operation_id: UUID,
        predicate_ref: UUID,
        profile_revision_ref: UUID,
        value_shape: str,
        caller_principal_ref: str = "kernel-profile-admin",
        expected_revision: int | None = None,
    ) -> VocabularyRevisionSnapshot:
        payload = {
            "predicate_ref": str(predicate_ref),
            "profile_revision_ref": str(profile_revision_ref),
            "value_shape": value_shape,
        }

        def action() -> VocabularyRevisionSnapshot:
            if value_shape not in _ALLOWED_VALUE_SHAPES:
                raise KnowledgeInvariantError(
                    f"unsupported predicate value shape: {value_shape}"
                )
            predicate = self.session.get(SemanticPredicate, predicate_ref)
            profile_revision = self.session.get(
                SemanticProfileRevision, profile_revision_ref
            )
            if predicate is None:
                raise KnowledgeInvariantError(
                    f"unknown semantic predicate: {predicate_ref}"
                )
            if (
                profile_revision is None
                or profile_revision.profile_ref_id != predicate.profile_ref_id
            ):
                raise KnowledgeInvariantError(
                    "predicate and profile revision do not belong to the same profile"
                )

            prior_shapes = set(
                self.session.scalars(
                    select(SemanticPredicateRevision.value_shape).where(
                        SemanticPredicateRevision.predicate_ref_id == predicate_ref
                    )
                ).all()
            )
            if prior_shapes and value_shape not in prior_shapes:
                raise KnowledgeInvariantError(
                    "material predicate meaning change requires a new semantic "
                    "predicate identity or explicit migration path"
                )

            existing = self.session.execute(
                select(SemanticPredicateRevision).where(
                    SemanticPredicateRevision.predicate_ref_id == predicate_ref,
                    SemanticPredicateRevision.profile_revision_ref_id
                    == profile_revision_ref,
                )
            ).scalar_one_or_none()
            if existing is not None:
                raise KnowledgeInvariantError(
                    "predicate already has a revision in the target profile revision"
                )

            revision = self._new_revision()
            predicate_revision_ref = self._new_ref(
                RefKind.SEMANTIC_PREDICATE_REVISION, revision.revision_id
            )
            self.session.add(
                SemanticPredicateRevision(
                    ref_id=predicate_revision_ref,
                    predicate_ref_id=predicate_ref,
                    profile_revision_ref_id=profile_revision_ref,
                    value_shape=value_shape,
                    created_revision_id=revision.revision_id,
                )
            )
            self._commit()
            return self.read_predicate_revision(predicate_revision_ref)

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="create_predicate_revision",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {
                "predicate_revision_ref": str(result.revision_ref)
            },
            replay=lambda metadata: self.read_predicate_revision(
                UUID(str(metadata["predicate_revision_ref"]))
            ),
        )

    def create_predicate_identity_operation(
        self,
        *,
        operation_id: UUID,
        profile_revision_ref: UUID,
        stable_name: str,
        value_shape: str,
        caller_principal_ref: str = "kernel-profile-admin",
        expected_revision: int | None = None,
    ) -> VocabularyRevisionSnapshot:
        if not stable_name.strip():
            raise KnowledgeInvariantError("predicate stable_name must not be empty")

        payload = {
            "profile_revision_ref": str(profile_revision_ref),
            "stable_name": stable_name,
            "value_shape": value_shape,
        }

        def action() -> VocabularyRevisionSnapshot:
            if value_shape not in _ALLOWED_VALUE_SHAPES:
                raise KnowledgeInvariantError(
                    f"unsupported predicate value shape: {value_shape}"
                )
            profile_revision = self.session.get(
                SemanticProfileRevision, profile_revision_ref
            )
            if profile_revision is None:
                raise KnowledgeInvariantError(
                    f"unknown semantic profile revision: {profile_revision_ref}"
                )
            existing = self.session.execute(
                select(SemanticPredicate).where(
                    SemanticPredicate.profile_ref_id
                    == profile_revision.profile_ref_id,
                    SemanticPredicate.stable_name == stable_name,
                )
            ).scalar_one_or_none()
            if existing is not None:
                raise KnowledgeInvariantError(
                    f"semantic predicate identity already exists: {stable_name}"
                )

            revision = self._new_revision()
            predicate_ref = self._new_ref(
                RefKind.SEMANTIC_PREDICATE, revision.revision_id
            )
            predicate_revision_ref = self._new_ref(
                RefKind.SEMANTIC_PREDICATE_REVISION, revision.revision_id
            )
            self.session.add(
                SemanticPredicate(
                    ref_id=predicate_ref,
                    profile_ref_id=profile_revision.profile_ref_id,
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
            self._commit()
            return self.read_predicate_revision(predicate_revision_ref)

        return self._execute_operation(
            operation_id=operation_id,
            operation_class="create_predicate_identity",
            caller_principal_ref=caller_principal_ref,
            payload=payload,
            expected_revision=expected_revision,
            action=action,
            encode_result=lambda result: {
                "predicate_revision_ref": str(result.revision_ref)
            },
            replay=lambda metadata: self.read_predicate_revision(
                UUID(str(metadata["predicate_revision_ref"]))
            ),
        )
