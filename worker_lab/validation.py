from __future__ import annotations

from collections.abc import Iterable

from .errors import LabValidationError
from .models import AttemptRecord, CurriculumRecord, EvidenceRecord, ExerciseRecord, FailureRecord
from .test_catalog import TestCatalog


def validate_relations(
    *,
    curricula: Iterable[CurriculumRecord],
    exercises: Iterable[ExerciseRecord],
    attempts: Iterable[AttemptRecord] = (),
    evidence: Iterable[EvidenceRecord] = (),
    failures: Iterable[FailureRecord] = (),
    catalog: TestCatalog | None = None,
) -> None:
    curricula_by_id = _unique(curricula, lambda item: item.curriculum_id, "curriculum")
    exercises_by_key = _unique(
        exercises, lambda item: (item.exercise_id, item.exercise_version), "exercise version"
    )
    attempts_by_id = _unique(attempts, lambda item: item.attempt_id, "attempt")
    evidence_by_digest = _unique(evidence, lambda item: item.evidence_digest, "evidence")
    failures_by_id = _unique(failures, lambda item: item.failure_id, "failure")

    for curriculum in curricula_by_id.values():
        missing_prerequisites = set(curriculum.prerequisite_curriculum_ids) - set(curricula_by_id)
        known_exercise_ids = {key[0] for key in exercises_by_key}
        missing_exercises = set(curriculum.exercise_ids) - known_exercise_ids
        if missing_prerequisites or missing_exercises:
            raise LabValidationError(
                "RELATION_REFERENCE_MISSING",
                f"curriculum {curriculum.curriculum_id}: prerequisites={sorted(missing_prerequisites)}, exercises={sorted(missing_exercises)}",
            )
    _assert_curriculum_acyclic(curricula_by_id)

    profile_ids = {profile.profile_id for profile in catalog.profiles} if catalog else None
    for exercise in exercises_by_key.values():
        if exercise.curriculum_id not in curricula_by_id:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "exercise curriculum is missing")
        if exercise.exercise_id not in curricula_by_id[exercise.curriculum_id].exercise_ids:
            raise LabValidationError("RELATION_MEMBERSHIP_INVALID", "exercise is not in its curriculum")
        if profile_ids is not None and set(exercise.test_profile_ids) - profile_ids:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "exercise test profile is missing")

    for attempt in attempts_by_id.values():
        if (attempt.exercise_id, attempt.exercise_version) not in exercises_by_key:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "attempt exercise is missing")
        if attempt.curriculum_id != exercises_by_key[(attempt.exercise_id, attempt.exercise_version)].curriculum_id:
            raise LabValidationError("RELATION_MEMBERSHIP_INVALID", "attempt curriculum does not match exercise")
        if attempt.prior_attempt_id is not None and attempt.prior_attempt_id not in attempts_by_id:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "prior attempt is missing")

    for item in evidence_by_digest.values():
        if item.attempt_id not in attempts_by_id:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "evidence attempt is missing")
    for failure in failures_by_id.values():
        if failure.attempt_id not in attempts_by_id:
            raise LabValidationError("RELATION_REFERENCE_MISSING", "failure attempt is missing")
        if set(failure.related_failure_ids) - set(failures_by_id):
            raise LabValidationError("RELATION_REFERENCE_MISSING", "related failure is missing")


def _unique(values: Iterable[object], key, label: str) -> dict[object, object]:
    result: dict[object, object] = {}
    for value in values:
        identity = key(value)
        if identity in result:
            raise LabValidationError("RELATION_ID_DUPLICATE", f"duplicate {label}: {identity}")
        result[identity] = value
    return result


def _assert_curriculum_acyclic(curricula: dict[object, object]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identity: str) -> None:
        if identity in visiting:
            raise LabValidationError("RELATION_CYCLE_INVALID", "curriculum prerequisite cycle")
        if identity in visited:
            return
        visiting.add(identity)
        for required in curricula[identity].prerequisite_curriculum_ids:
            visit(required)
        visiting.remove(identity)
        visited.add(identity)

    for identity in curricula:
        visit(identity)
