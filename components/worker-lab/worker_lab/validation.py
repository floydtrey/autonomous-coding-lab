from __future__ import annotations

from collections.abc import Iterable

from .canonical import canonical_digest
from .errors import LabValidationError
from .models import (
    AttemptRecord, AttemptState, CurriculumRecord, EvidenceRecord, ExerciseRecord, FailureRecord,
)
from .policy import ContextManifest, PolicyRecord, RoleRecord, validate_authority
from .test_catalog import TestCatalog


def attempt_task_digest(
    exercise: ExerciseRecord,
    policy: PolicyRecord,
    role: RoleRecord,
    context: ContextManifest,
    catalog: TestCatalog,
) -> str:
    return canonical_digest({
        "exercise": exercise.to_dict(),
        "policy_digest": policy.digest(),
        "role_digest": role.digest(),
        "context_manifest_digest": context.digest(),
        "evaluator_catalog_digest": catalog.digest(),
    })


def validate_attempt_authority_binding(
    attempt: AttemptRecord,
    exercise: ExerciseRecord,
    policy: PolicyRecord,
    role: RoleRecord,
    context: ContextManifest,
    catalog: TestCatalog,
) -> None:
    """Verify one attempt still resolves to its exact protected authority inputs."""
    if (
        (exercise.exercise_id, exercise.exercise_version)
        != (attempt.exercise_id, attempt.exercise_version)
        or exercise.curriculum_id != attempt.curriculum_id
        or (policy.policy_id, policy.policy_version)
        != (exercise.policy_id, exercise.policy_version)
        or (role.role_id, role.role_version) != (exercise.role_id, exercise.role_version)
        or (context.manifest_id, context.manifest_version)
        != (exercise.context_manifest_id, exercise.context_manifest_version)
        or context.repository != exercise.template_repository
        or context.starting_commit != exercise.template_commit
        or catalog.catalog_version != exercise.evaluator_catalog_version
    ):
        raise LabValidationError(
            "RELATION_IDENTITY_MISMATCH", "attempt authority references differ"
        )
    if set(exercise.test_profile_ids) - {item.profile_id for item in catalog.profiles}:
        raise LabValidationError("RELATION_REFERENCE_MISSING", "exercise test profile is missing")
    validate_authority(
        policy,
        role,
        required_capabilities=exercise.required_capabilities,
        temporary_denied_capabilities=exercise.temporary_denied_capabilities,
    )
    expected = (
        exercise.template_commit,
        context.digest(),
        attempt_task_digest(exercise, policy, role, context, catalog),
        policy.policy_id,
        policy.policy_version,
        policy.digest(),
        role.role_id,
        role.role_version,
        role.digest(),
        exercise.sandbox_mode,
        catalog.catalog_version,
        catalog.digest(),
    )
    actual = (
        attempt.starting_commit,
        attempt.context_digest,
        attempt.task_digest,
        attempt.policy_id,
        attempt.policy_version,
        attempt.policy_digest,
        attempt.role_id,
        attempt.role_version,
        attempt.role_digest,
        attempt.sandbox_mode,
        attempt.evaluator_catalog_version,
        attempt.evaluator_catalog_digest,
    )
    if actual != expected:
        raise LabValidationError("RELATION_IDENTITY_MISMATCH", "attempt authority identity differs")


def validate_relations(
    *,
    curricula: Iterable[CurriculumRecord],
    exercises: Iterable[ExerciseRecord],
    policies: Iterable[PolicyRecord],
    roles: Iterable[RoleRecord],
    contexts: Iterable[ContextManifest],
    catalog: TestCatalog,
    attempts: Iterable[AttemptRecord] = (),
    evidence: Iterable[EvidenceRecord] = (),
    failures: Iterable[FailureRecord] = (),
) -> None:
    curricula_by_id = _unique(curricula, lambda item: item.curriculum_id, "curriculum")
    exercises_by_key = _unique(
        exercises, lambda item: (item.exercise_id, item.exercise_version), "exercise version"
    )
    policies_by_key = _unique(
        policies, lambda item: (item.policy_id, item.policy_version), "policy version"
    )
    roles_by_key = _unique(roles, lambda item: (item.role_id, item.role_version), "role version")
    contexts_by_key = _unique(
        contexts, lambda item: (item.manifest_id, item.manifest_version), "context version"
    )
    attempts_by_id = _unique(attempts, lambda item: item.attempt_id, "attempt")
    evidence_by_digest = _unique(evidence, lambda item: item.evidence_digest, "evidence")
    failures_by_id = _unique(failures, lambda item: item.failure_id, "failure")

    exercise_owners: dict[str, set[str]] = {}
    for exercise in exercises_by_key.values():
        exercise_owners.setdefault(exercise.exercise_id, set()).add(exercise.curriculum_id)
    ambiguous = sorted(identity for identity, owners in exercise_owners.items() if len(owners) != 1)
    if ambiguous:
        raise LabValidationError(
            "RELATION_MEMBERSHIP_INVALID", f"exercise IDs span curricula: {ambiguous}"
        )

    for curriculum in curricula_by_id.values():
        missing_prerequisites = set(curriculum.prerequisite_curriculum_ids) - set(curricula_by_id)
        missing_exercises = [
            identity for identity in curriculum.exercise_ids
            if exercise_owners.get(identity) != {curriculum.curriculum_id}
        ]
        if missing_prerequisites or missing_exercises:
            raise LabValidationError(
                "RELATION_REFERENCE_MISSING",
                f"curriculum {curriculum.curriculum_id}: prerequisites={sorted(missing_prerequisites)}, exercises={missing_exercises}",
            )
    _assert_acyclic(
        {identity: item.prerequisite_curriculum_ids for identity, item in curricula_by_id.items()},
        "curriculum prerequisite",
    )

    profile_ids = {profile.profile_id for profile in catalog.profiles}
    for exercise in exercises_by_key.values():
        curriculum = curricula_by_id.get(exercise.curriculum_id)
        if curriculum is None:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "exercise curriculum is missing")
        if exercise.exercise_id not in curriculum.exercise_ids:
            raise LabValidationError("RELATION_MEMBERSHIP_INVALID", "exercise is not in its curriculum")
        policy = policies_by_key.get((exercise.policy_id, exercise.policy_version))
        role = roles_by_key.get((exercise.role_id, exercise.role_version))
        context = contexts_by_key.get(
            (exercise.context_manifest_id, exercise.context_manifest_version)
        )
        if policy is None or role is None or context is None:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "exercise authority record is missing")
        if context.repository != exercise.template_repository or context.starting_commit != exercise.template_commit:
            raise LabValidationError("RELATION_IDENTITY_MISMATCH", "exercise context identity differs")
        if exercise.evaluator_catalog_version != catalog.catalog_version:
            raise LabValidationError("RELATION_IDENTITY_MISMATCH", "exercise catalog identity differs")
        if set(exercise.test_profile_ids) - profile_ids:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "exercise test profile is missing")
        validate_authority(
            policy,
            role,
            required_capabilities=exercise.required_capabilities,
            temporary_denied_capabilities=exercise.temporary_denied_capabilities,
        )

    for attempt in attempts_by_id.values():
        exercise = exercises_by_key.get((attempt.exercise_id, attempt.exercise_version))
        if exercise is None:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "attempt exercise is missing")
        policy = policies_by_key.get((exercise.policy_id, exercise.policy_version))
        role = roles_by_key.get((exercise.role_id, exercise.role_version))
        context = contexts_by_key.get(
            (exercise.context_manifest_id, exercise.context_manifest_version)
        )
        assert policy is not None and role is not None and context is not None
        validate_attempt_authority_binding(attempt, exercise, policy, role, context, catalog)
        if attempt.prior_attempt_id == attempt.attempt_id:
            raise LabValidationError("RELATION_CYCLE_INVALID", "attempt cannot reference itself")
        if attempt.prior_attempt_id is not None and attempt.prior_attempt_id not in attempts_by_id:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "prior attempt is missing")
    _assert_acyclic(
        {identity: (() if item.prior_attempt_id is None else (item.prior_attempt_id,))
         for identity, item in attempts_by_id.items()},
        "prior attempt",
    )
    for attempt in attempts_by_id.values():
        if attempt.prior_attempt_id is None:
            continue
        prior = attempts_by_id[attempt.prior_attempt_id]
        if prior.state not in {AttemptState.CLOSED, AttemptState.ABORTED}:
            raise LabValidationError("RELATION_STATE_INVALID", "prior attempt is not terminal")
        if attempt.created_at < prior.updated_at:
            raise LabValidationError("RELATION_TIME_INVALID", "retry predates prior completion")

    test_ids = {item.test_id for item in catalog.tests}
    for item in evidence_by_digest.values():
        attempt = attempts_by_id.get(item.attempt_id)
        if attempt is None:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "evidence attempt is missing")
        if (
            attempt.candidate_digest is None
            or item.candidate_digest != attempt.candidate_digest
            or item.base_commit != attempt.starting_commit
            or item.test_catalog_version != attempt.evaluator_catalog_version
            or item.test_catalog_digest != attempt.evaluator_catalog_digest
            or item.test_id not in test_ids
        ):
            raise LabValidationError("RELATION_IDENTITY_MISMATCH", "evidence identity differs")

    for failure in failures_by_id.values():
        if failure.attempt_id not in attempts_by_id:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "failure attempt is missing")
        if failure.failure_id in failure.related_failure_ids:
            raise LabValidationError("RELATION_CYCLE_INVALID", "failure cannot reference itself")
        if set(failure.related_failure_ids) - set(failures_by_id):
            raise LabValidationError("RELATION_REFERENCE_MISSING", "related failure is missing")
    _assert_acyclic(
        {identity: item.related_failure_ids for identity, item in failures_by_id.items()},
        "related failure",
    )


def _unique(values: Iterable[object], key, label: str) -> dict[object, object]:
    result: dict[object, object] = {}
    for value in values:
        identity = key(value)
        if identity in result:
            raise LabValidationError("RELATION_ID_DUPLICATE", f"duplicate {label}: {identity}")
        result[identity] = value
    return result


def _assert_acyclic(graph: dict[object, Iterable[object]], label: str) -> None:
    visiting: set[object] = set()
    visited: set[object] = set()

    def visit(identity: object) -> None:
        if identity in visiting:
            raise LabValidationError("RELATION_CYCLE_INVALID", f"{label} cycle")
        if identity in visited:
            return
        visiting.add(identity)
        for required in graph[identity]:
            if required in graph:
                visit(required)
        visiting.remove(identity)
        visited.add(identity)

    for identity in graph:
        visit(identity)
