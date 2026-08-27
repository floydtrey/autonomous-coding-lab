from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Mapping

from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError


CURRICULUM_SCHEMA = "worker-lab-curriculum:v1"
EXERCISE_SCHEMA = "worker-lab-exercise:v2"
ATTEMPT_SCHEMA = "worker-lab-attempt:v2"
EVIDENCE_SCHEMA = "worker-lab-evidence:v2"
FAILURE_SCHEMA = "worker-lab-failure:v1"

ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
ATTEMPT_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{5,95}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
TEST_PROFILE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}:v[1-9][0-9]*$")


class AttemptState(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    RUNNING = "RUNNING"
    CANDIDATE = "CANDIDATE"
    EVALUATING = "EVALUATING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CLOSED = "CLOSED"
    ABORTED = "ABORTED"


@dataclass(frozen=True)
class _Record:
    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        _convert_enums(value)
        return value

    def to_json(self, *, pretty: bool = False) -> str:
        if not pretty:
            return canonical_json(self.to_dict())
        return __import__("json").dumps(
            self.to_dict(), ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class CurriculumRecord(_Record):
    schema_version: str
    curriculum_id: str
    title: str
    purpose: str
    capabilities: tuple[str, ...]
    prerequisite_curriculum_ids: tuple[str, ...]
    exercise_ids: tuple[str, ...]
    status: str

    @classmethod
    def from_mapping(cls, value: Any) -> "CurriculumRecord":
        data = _object(value, {
            "schema_version", "curriculum_id", "title", "purpose", "capabilities",
            "prerequisite_curriculum_ids", "exercise_ids", "status",
        })
        _schema(data, CURRICULUM_SCHEMA)
        curriculum_id = _id(data["curriculum_id"], "curriculum_id")
        prerequisites = _ids(data["prerequisite_curriculum_ids"], "prerequisite_curriculum_ids")
        if curriculum_id in prerequisites:
            raise LabValidationError("RECORD_REFERENCE_INVALID", "curriculum cannot require itself")
        status = _choice(data["status"], "status", {"active", "retired"})
        return cls(
            CURRICULUM_SCHEMA,
            curriculum_id,
            _text(data["title"], "title"),
            _text(data["purpose"], "purpose"),
            _texts(data["capabilities"], "capabilities", nonempty=True),
            prerequisites,
            _ordered_ids(data["exercise_ids"], "exercise_ids"),
            status,
        )


@dataclass(frozen=True)
class ExerciseRecord(_Record):
    schema_version: str
    exercise_id: str
    exercise_version: int
    curriculum_id: str
    objective: str
    template_repository: str
    template_commit: str
    policy_id: str
    policy_version: int
    role_id: str
    role_version: int
    sandbox_mode: str
    context_manifest_id: str
    context_manifest_version: int
    evaluator_catalog_version: str
    required_capabilities: tuple[str, ...]
    temporary_denied_capabilities: tuple[str, ...]
    writable_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    test_profile_ids: tuple[str, ...]
    prohibited_shortcuts: tuple[str, ...]
    expected_failure_behavior: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> "ExerciseRecord":
        data = _object(value, {
            "schema_version", "exercise_id", "exercise_version", "curriculum_id", "objective",
            "template_repository", "template_commit", "writable_paths", "protected_paths",
            "acceptance_criteria", "test_profile_ids", "prohibited_shortcuts",
            "expected_failure_behavior", "policy_id", "policy_version", "role_id",
            "role_version", "sandbox_mode", "context_manifest_id", "context_manifest_version",
            "evaluator_catalog_version", "required_capabilities",
            "temporary_denied_capabilities",
        })
        _schema(data, EXERCISE_SCHEMA)
        writable = _paths(data["writable_paths"], "writable_paths", nonempty=True)
        protected = _paths(data["protected_paths"], "protected_paths")
        overlap = sorted(
            (writable_path, protected_path)
            for writable_path in writable
            for protected_path in protected
            if _paths_overlap(writable_path, protected_path)
        )
        if overlap:
            raise LabValidationError(
                "RECORD_SCOPE_INVALID", f"writable and protected paths overlap: {overlap}"
            )
        profiles = _texts(data["test_profile_ids"], "test_profile_ids", nonempty=True)
        if not all(TEST_PROFILE_RE.fullmatch(item) for item in profiles):
            raise LabValidationError("RECORD_TEST_PROFILE_INVALID", "test profile ID is invalid")
        return cls(
            EXERCISE_SCHEMA,
            _id(data["exercise_id"], "exercise_id"),
            _positive_int(data["exercise_version"], "exercise_version"),
            _id(data["curriculum_id"], "curriculum_id"),
            _text(data["objective"], "objective"),
            _text(data["template_repository"], "template_repository"),
            _sha(data["template_commit"], "template_commit"),
            _id(data["policy_id"], "policy_id"),
            _positive_int(data["policy_version"], "policy_version"),
            _id(data["role_id"], "role_id"),
            _positive_int(data["role_version"], "role_version"),
            _choice(data["sandbox_mode"], "sandbox_mode", {"read-only", "workspace-write"}),
            _id(data["context_manifest_id"], "context_manifest_id"),
            _positive_int(data["context_manifest_version"], "context_manifest_version"),
            _text(data["evaluator_catalog_version"], "evaluator_catalog_version"),
            _texts(data["required_capabilities"], "required_capabilities", nonempty=True),
            _texts(data["temporary_denied_capabilities"], "temporary_denied_capabilities"),
            writable,
            protected,
            _texts(data["acceptance_criteria"], "acceptance_criteria", nonempty=True),
            profiles,
            _texts(data["prohibited_shortcuts"], "prohibited_shortcuts"),
            _texts(data["expected_failure_behavior"], "expected_failure_behavior", nonempty=True),
        )


@dataclass(frozen=True)
class AttemptRecord(_Record):
    schema_version: str
    attempt_id: str
    curriculum_id: str
    exercise_id: str
    exercise_version: int
    starting_commit: str
    context_digest: str
    task_digest: str
    policy_id: str
    policy_version: int
    policy_digest: str
    role_id: str
    role_version: int
    role_digest: str
    sandbox_mode: str
    state: AttemptState
    created_at: str
    updated_at: str
    evaluator_catalog_version: str
    evaluator_catalog_digest: str
    runtime_identity: str | None
    candidate_digest: str | None
    cleanup_outcome: str | None
    prior_attempt_id: str | None

    @classmethod
    def from_mapping(cls, value: Any) -> "AttemptRecord":
        data = _object(value, {
            "schema_version", "attempt_id", "curriculum_id", "exercise_id", "exercise_version",
            "starting_commit", "context_digest", "task_digest", "state", "created_at",
            "updated_at", "evaluator_catalog_version", "runtime_identity", "candidate_digest",
            "cleanup_outcome", "prior_attempt_id", "policy_id", "policy_version",
            "policy_digest", "role_id", "role_version", "role_digest", "sandbox_mode",
            "evaluator_catalog_digest",
        })
        _schema(data, ATTEMPT_SCHEMA)
        created = _timestamp(data["created_at"], "created_at")
        updated = _timestamp(data["updated_at"], "updated_at")
        if updated < created:
            raise LabValidationError("RECORD_TIME_INVALID", "updated_at cannot precede created_at")
        return cls(
            ATTEMPT_SCHEMA,
            _attempt_id(data["attempt_id"], "attempt_id"),
            _id(data["curriculum_id"], "curriculum_id"),
            _id(data["exercise_id"], "exercise_id"),
            _positive_int(data["exercise_version"], "exercise_version"),
            _sha(data["starting_commit"], "starting_commit"),
            _digest(data["context_digest"], "context_digest"),
            _digest(data["task_digest"], "task_digest"),
            _id(data["policy_id"], "policy_id"),
            _positive_int(data["policy_version"], "policy_version"),
            _digest(data["policy_digest"], "policy_digest"),
            _id(data["role_id"], "role_id"),
            _positive_int(data["role_version"], "role_version"),
            _digest(data["role_digest"], "role_digest"),
            _choice(data["sandbox_mode"], "sandbox_mode", {"read-only", "workspace-write"}),
            _attempt_state(data["state"]),
            data["created_at"],
            data["updated_at"],
            _text(data["evaluator_catalog_version"], "evaluator_catalog_version"),
            _digest(data["evaluator_catalog_digest"], "evaluator_catalog_digest"),
            _optional_text(data["runtime_identity"], "runtime_identity"),
            _optional_digest(data["candidate_digest"], "candidate_digest"),
            _optional_text(data["cleanup_outcome"], "cleanup_outcome"),
            _optional_attempt_id(data["prior_attempt_id"], "prior_attempt_id"),
        )


@dataclass(frozen=True)
class EvidenceRecord(_Record):
    schema_version: str
    evidence_digest: str
    evidence_type: str
    attempt_id: str
    test_id: str
    test_catalog_version: str
    test_catalog_digest: str
    candidate_digest: str
    base_commit: str
    environment_digest: str
    content_path: str | None
    external_reference: str | None
    created_at: str
    verification_state: str

    @classmethod
    def from_mapping(cls, value: Any) -> "EvidenceRecord":
        data = _object(value, {
            "schema_version", "evidence_digest", "evidence_type", "attempt_id", "test_id",
            "test_catalog_version", "test_catalog_digest", "candidate_digest", "base_commit",
            "environment_digest", "content_path", "external_reference", "created_at",
            "verification_state",
        })
        _schema(data, EVIDENCE_SCHEMA)
        content_path = None if data["content_path"] is None else _path(data["content_path"], "content_path")
        external = _optional_text(data["external_reference"], "external_reference")
        if (content_path is None) == (external is None):
            raise LabValidationError(
                "RECORD_EVIDENCE_LOCATION_INVALID",
                "evidence requires exactly one content_path or external_reference",
            )
        return cls(
            EVIDENCE_SCHEMA,
            _digest(data["evidence_digest"], "evidence_digest"),
            _text(data["evidence_type"], "evidence_type"),
            _attempt_id(data["attempt_id"], "attempt_id"),
            _test_id(data["test_id"]),
            _text(data["test_catalog_version"], "test_catalog_version"),
            _digest(data["test_catalog_digest"], "test_catalog_digest"),
            _digest(data["candidate_digest"], "candidate_digest"),
            _sha(data["base_commit"], "base_commit"),
            _digest(data["environment_digest"], "environment_digest"),
            content_path,
            external,
            _validated_timestamp_text(data["created_at"], "created_at"),
            _choice(data["verification_state"], "verification_state", {"unverified", "verified", "invalid"}),
        )


@dataclass(frozen=True)
class FailureRecord(_Record):
    schema_version: str
    failure_id: str
    attempt_id: str
    first_failed_boundary: str
    expected: str
    observed: str
    classification: str
    containment_outcome: str
    proposed_control: str | None
    accepted_limitation: str | None
    related_failure_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> "FailureRecord":
        data = _object(value, {
            "schema_version", "failure_id", "attempt_id", "first_failed_boundary", "expected",
            "observed", "classification", "containment_outcome", "proposed_control",
            "accepted_limitation", "related_failure_ids",
        })
        _schema(data, FAILURE_SCHEMA)
        control = _optional_text(data["proposed_control"], "proposed_control")
        limitation = _optional_text(data["accepted_limitation"], "accepted_limitation")
        if control is None and limitation is None:
            raise LabValidationError(
                "RECORD_FAILURE_RESPONSE_INVALID",
                "failure requires a proposed control or accepted limitation",
            )
        return cls(
            FAILURE_SCHEMA,
            _attempt_id(data["failure_id"], "failure_id"),
            _attempt_id(data["attempt_id"], "attempt_id"),
            _text(data["first_failed_boundary"], "first_failed_boundary"),
            _text(data["expected"], "expected"),
            _text(data["observed"], "observed"),
            _choice(data["classification"], "classification", {
                "worker-reasoning", "context", "contract", "test", "framework",
                "environment", "controller-judgment",
            }),
            _text(data["containment_outcome"], "containment_outcome"),
            control,
            limitation,
            _attempt_ids(data["related_failure_ids"], "related_failure_ids"),
        )


def _object(value: Any, expected: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LabValidationError("RECORD_INVALID", "record must be an object")
    if set(value) != expected:
        missing = sorted(expected - set(value))
        unknown = sorted(set(value) - expected)
        raise LabValidationError("RECORD_FIELDS_INVALID", f"missing={missing}, unknown={unknown}")
    return value


def _schema(data: Mapping[str, Any], expected: str) -> None:
    if data["schema_version"] != expected:
        raise LabValidationError("RECORD_SCHEMA_INVALID", f"expected {expected}")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise LabValidationError("RECORD_TEXT_INVALID", f"{field} must be trimmed non-empty text")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    return None if value is None else _text(value, field)


def _id(value: Any, field: str) -> str:
    text = _text(value, field)
    if not ID_RE.fullmatch(text):
        raise LabValidationError("RECORD_ID_INVALID", f"{field} is invalid")
    return text


def _attempt_id(value: Any, field: str) -> str:
    text = _text(value, field)
    if not ATTEMPT_ID_RE.fullmatch(text):
        raise LabValidationError("RECORD_ID_INVALID", f"{field} is invalid")
    return text


def _optional_attempt_id(value: Any, field: str) -> str | None:
    return None if value is None else _attempt_id(value, field)


def _texts(value: Any, field: str, *, nonempty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LabValidationError("RECORD_LIST_INVALID", f"{field} must be an array")
    result = tuple(_text(item, field) for item in value)
    if nonempty and not result:
        raise LabValidationError("RECORD_LIST_INVALID", f"{field} must not be empty")
    if result != tuple(sorted(set(result))):
        raise LabValidationError("RECORD_LIST_INVALID", f"{field} must be sorted and unique")
    return result


def _ids(value: Any, field: str) -> tuple[str, ...]:
    items = _texts(value, field)
    for item in items:
        _id(item, field)
    return items


def _ordered_ids(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LabValidationError("RECORD_LIST_INVALID", f"{field} must be an array")
    items = tuple(_id(item, field) for item in value)
    if len(items) != len(set(items)):
        raise LabValidationError("RECORD_LIST_INVALID", f"{field} must be unique")
    return items


def _attempt_ids(value: Any, field: str) -> tuple[str, ...]:
    items = _texts(value, field)
    for item in items:
        _attempt_id(item, field)
    return items


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LabValidationError("RECORD_INTEGER_INVALID", f"{field} must be a positive integer")
    return value


def _sha(value: Any, field: str) -> str:
    text = _text(value, field)
    if not SHA_RE.fullmatch(text):
        raise LabValidationError("RECORD_SHA_INVALID", f"{field} must be a full lowercase Git SHA")
    return text


def _digest(value: Any, field: str) -> str:
    text = _text(value, field)
    if not DIGEST_RE.fullmatch(text):
        raise LabValidationError("RECORD_DIGEST_INVALID", f"{field} must be a SHA-256 digest")
    return text


def _optional_digest(value: Any, field: str) -> str | None:
    return None if value is None else _digest(value, field)


def _path(value: Any, field: str) -> str:
    text = _text(value, field)
    if "\\" in text:
        raise LabValidationError("RECORD_PATH_INVALID", f"{field} must use forward slashes")
    candidate = PurePosixPath(text)
    if (
        candidate.is_absolute()
        or text.startswith("/")
        or ".." in candidate.parts
        or candidate.as_posix() != text
        or not candidate.parts
        or ":" in candidate.parts[0]
    ):
        raise LabValidationError("RECORD_PATH_INVALID", f"{field} is not a normalized relative path")
    return text


def _paths_overlap(first: str, second: str) -> bool:
    return first == second or first.startswith(second + "/") or second.startswith(first + "/")


def _paths(value: Any, field: str, *, nonempty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LabValidationError("RECORD_LIST_INVALID", f"{field} must be an array")
    result = tuple(_path(item, field) for item in value)
    if nonempty and not result:
        raise LabValidationError("RECORD_LIST_INVALID", f"{field} must not be empty")
    if result != tuple(sorted(set(result))):
        raise LabValidationError("RECORD_LIST_INVALID", f"{field} must be sorted and unique")
    return result


def _choice(value: Any, field: str, choices: set[str]) -> str:
    text = _text(value, field)
    if text not in choices:
        raise LabValidationError("RECORD_CHOICE_INVALID", f"{field} is unsupported")
    return text


def _attempt_state(value: Any) -> AttemptState:
    try:
        return AttemptState(_text(value, "state"))
    except ValueError as exc:
        raise LabValidationError("RECORD_STATE_INVALID", "attempt state is unsupported") from exc


def _timestamp(value: Any, field: str) -> datetime:
    text = _text(value, field)
    if not text.endswith("Z"):
        raise LabValidationError("RECORD_TIME_INVALID", f"{field} must be UTC with Z suffix")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise LabValidationError("RECORD_TIME_INVALID", f"{field} is invalid") from exc
    if parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != text:
        raise LabValidationError("RECORD_TIME_INVALID", f"{field} must use second precision")
    return parsed


def _validated_timestamp_text(value: Any, field: str) -> str:
    _timestamp(value, field)
    return value


def _test_id(value: Any) -> str:
    text = _text(value, "test_id")
    if not re.fullmatch(r"T[0-9]{3}", text):
        raise LabValidationError("RECORD_TEST_ID_INVALID", "test_id is invalid")
    return text


def _convert_enums(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, StrEnum):
                value[key] = str(child)
            else:
                _convert_enums(child)
    elif isinstance(value, list):
        for child in value:
            _convert_enums(child)
