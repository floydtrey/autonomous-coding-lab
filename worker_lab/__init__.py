"""Protected contracts for the local Worker Lab."""

from .canonical import canonical_digest, canonical_json
from .models import (
    AttemptRecord,
    AttemptState,
    CurriculumRecord,
    EvidenceRecord,
    ExerciseRecord,
    FailureRecord,
)

__all__ = [
    "AttemptRecord",
    "AttemptState",
    "CurriculumRecord",
    "EvidenceRecord",
    "ExerciseRecord",
    "FailureRecord",
    "canonical_digest",
    "canonical_json",
]
