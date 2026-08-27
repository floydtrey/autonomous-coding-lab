from copy import deepcopy

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.models import AttemptRecord, CurriculumRecord, ExerciseRecord
from worker_lab.validation import validate_relations
from tests.test_models import attempt_mapping, curriculum_mapping, exercise_mapping


def test_valid_related_records_pass() -> None:
    validate_relations(
        curricula=[CurriculumRecord.from_mapping(curriculum_mapping())],
        exercises=[ExerciseRecord.from_mapping(exercise_mapping())],
        attempts=[AttemptRecord.from_mapping(attempt_mapping())],
    )


def test_missing_exercise_fails_closed() -> None:
    with pytest.raises(LabValidationError) as raised:
        validate_relations(curricula=[CurriculumRecord.from_mapping(curriculum_mapping())], exercises=[])
    assert raised.value.code == "RELATION_REFERENCE_MISSING"


def test_attempt_cannot_claim_different_curriculum() -> None:
    value = deepcopy(attempt_mapping())
    value["curriculum_id"] = "other-curriculum"
    with pytest.raises(LabValidationError) as raised:
        validate_relations(
            curricula=[CurriculumRecord.from_mapping(curriculum_mapping())],
            exercises=[ExerciseRecord.from_mapping(exercise_mapping())],
            attempts=[AttemptRecord.from_mapping(value)],
        )
    assert raised.value.code == "RELATION_MEMBERSHIP_INVALID"
