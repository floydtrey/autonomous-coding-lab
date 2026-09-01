from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Mapping

from .canonical import canonical_digest
from .errors import LabValidationError


INVOCATION_SCHEMA = "worker-lab-framework-invocation:v2"
RESULT_SCHEMA = "worker-lab-framework-result:v2"
RUNTIME_PROFILE = "terra-medium:v1"
RUNTIME_MODEL = "gpt-5.6-terra"
RUNTIME_REASONING_EFFORT = "medium"
RUNTIME_TIMEOUT_SECONDS = 900
WORKER_LAB_CONTRACT_VERSION = "worker-lab-framework-client:v2"
# Version 2 remains the immutable read-only protocol.  Workspace writes use a
# deliberately separate version so a v2 consumer cannot acquire write behavior.
FRAMEWORK_CONTRACT_VERSION = "worker-lab-framework-adapter:v2"
WORKSPACE_WRITE_FRAMEWORK_CONTRACT_VERSION = "worker-lab-framework-adapter:v3"
MAX_STRUCTURED_TEXT_BYTES = 2_048
MAX_CONTENT_REFERENCE_BYTES = 256


class InvocationOperation(StrEnum):
    READ_ONLY_PROPOSAL = "read-only-proposal"
    WORKSPACE_WRITE_CODE_TASK = "workspace-write-code-task"


class InvocationState(StrEnum):
    PREPARED = "PREPARED"
    AUTHORIZED = "AUTHORIZED"
    DISPATCHING = "DISPATCHING"
    COMPLETED = "COMPLETED"
    UNCERTAIN = "UNCERTAIN"
    REJECTED = "REJECTED"
    ABORTED = "ABORTED"


LEGAL_INVOCATION_TRANSITIONS = {
    InvocationState.PREPARED: frozenset({InvocationState.AUTHORIZED, InvocationState.REJECTED}),
    InvocationState.AUTHORIZED: frozenset({InvocationState.DISPATCHING, InvocationState.ABORTED}),
    InvocationState.DISPATCHING: frozenset({InvocationState.COMPLETED, InvocationState.UNCERTAIN}),
    InvocationState.COMPLETED: frozenset(),
    InvocationState.UNCERTAIN: frozenset({InvocationState.ABORTED}),
    InvocationState.REJECTED: frozenset(),
    InvocationState.ABORTED: frozenset(),
}

_TERMINAL_STATES = frozenset({InvocationState.COMPLETED, InvocationState.REJECTED, InvocationState.ABORTED})
_DIGEST_PREFIX = "sha256:"


@dataclass(frozen=True)
class PathIdentity:
    path: str
    digest: str

    @classmethod
    def from_mapping(cls, value: Any) -> "PathIdentity":
        data = _object(value, {"path", "digest"})
        return cls(_path(data["path"]), _digest(data["digest"]))

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class InvocationRecord:
    schema_version: str
    invocation_id: str
    attempt_id: str
    operation: InvocationOperation
    exercise_id: str
    exercise_version: int
    exercise_digest: str
    policy_id: str
    policy_version: int
    policy_digest: str
    role_id: str
    role_version: int
    role_digest: str
    context_manifest_id: str
    context_manifest_version: int
    context_digest: str
    task_digest: str
    test_catalog_version: str
    test_catalog_digest: str
    test_plan_digest: str
    test_ids: tuple[str, ...]
    worker_lab_installation_digest: str
    worker_lab_contract_version: str
    framework_installation_digest: str
    framework_contract_version: str
    workspace_receipt_digest: str
    workspace_root_digest: str
    workspace_path_digest: str
    starting_commit: str
    sandbox_mode: str
    runtime_profile_id: str
    model: str
    reasoning_effort: str
    timeout_seconds: int
    readable_paths: tuple[PathIdentity, ...]
    writable_paths: tuple[str, ...]
    prompt_digest: str
    authorized_by: str | None
    authorized_at: str | None
    state: InvocationState
    result_digest: str | None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["operation"] = str(self.operation)
        value["state"] = str(self.state)
        value["test_ids"] = list(self.test_ids)
        value["readable_paths"] = [item.to_dict() for item in self.readable_paths]
        value["writable_paths"] = list(self.writable_paths)
        return value

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def identity_digest(self) -> str:
        """Return the stable execution identity, excluding mutable custody fields."""
        value = self.to_dict()
        for field in ("authorized_by", "authorized_at", "state", "result_digest"):
            value.pop(field)
        return canonical_digest({
            "schema_version": "worker-lab-framework-invocation-identity:v2",
            "invocation": value,
        })

    @classmethod
    def from_mapping(cls, value: Any) -> "InvocationRecord":
        expected = set(cls.__dataclass_fields__)
        data = _object(value, expected)
        try:
            operation = InvocationOperation(data["operation"])
            state = InvocationState(data["state"])
        except (TypeError, ValueError) as exc:
            raise LabValidationError("INTEGRATION_INVOCATION_INVALID", "unsupported operation or state") from exc
        paths = _path_identities(data["readable_paths"])
        writable = _paths(data["writable_paths"])
        record = cls(
            _exact(data["schema_version"], INVOCATION_SCHEMA, "schema_version"),
            _id(data["invocation_id"]), _id(data["attempt_id"]), operation,
            _id(data["exercise_id"]), _positive(data["exercise_version"]), _digest(data["exercise_digest"]),
            _id(data["policy_id"]), _positive(data["policy_version"]), _digest(data["policy_digest"]),
            _id(data["role_id"]), _positive(data["role_version"]), _digest(data["role_digest"]),
            _id(data["context_manifest_id"]), _positive(data["context_manifest_version"]), _digest(data["context_digest"]),
            _digest(data["task_digest"]), _text(data["test_catalog_version"]), _digest(data["test_catalog_digest"]),
            _digest(data["test_plan_digest"]), _texts(data["test_ids"]), _digest(data["worker_lab_installation_digest"]),
            _exact(data["worker_lab_contract_version"], WORKER_LAB_CONTRACT_VERSION, "worker_lab_contract_version"),
            _digest(data["framework_installation_digest"]),
            _framework_contract_version(data["framework_contract_version"], operation),
            _digest(data["workspace_receipt_digest"]), _digest(data["workspace_root_digest"]),
            _digest(data["workspace_path_digest"]), _sha(data["starting_commit"]), _text(data["sandbox_mode"]),
            _exact(data["runtime_profile_id"], RUNTIME_PROFILE, "runtime_profile_id"), _text(data["model"]),
            _text(data["reasoning_effort"]), _positive(data["timeout_seconds"]), paths, writable,
            _digest(data["prompt_digest"]), _optional_text(data["authorized_by"]),
            _optional_timestamp(data["authorized_at"]), state, _optional_digest(data["result_digest"]),
        )
        _validate_invocation(record)
        return record


@dataclass(frozen=True)
class ValidationStage:
    test_id: str
    outcome: str
    failure_code: str | None

    @classmethod
    def from_mapping(cls, value: Any) -> "ValidationStage":
        data = _object(value, {"test_id", "outcome", "failure_code"})
        outcome = _choice(data["outcome"], {"pass", "fail", "not-run"}, "validation outcome")
        failure = _optional_text(data["failure_code"])
        if (outcome == "fail") != (failure is not None):
            raise LabValidationError("INTEGRATION_RESULT_INVALID", "failed validation requires exactly one failure code")
        return cls(_test_id(data["test_id"]), outcome, failure)

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class ResultRecord:
    schema_version: str
    invocation_digest: str
    request_digest: str
    invocation_id: str
    attempt_id: str
    operation: InvocationOperation
    framework_installation_digest: str
    framework_contract_version: str
    runtime_profile_id: str
    runtime_identity: str
    prompt_digest: str
    test_catalog_version: str
    test_catalog_digest: str
    test_plan_digest: str
    test_ids: tuple[str, ...]
    workspace_receipt_digest: str
    workspace_root_digest: str
    workspace_path_digest: str
    starting_commit: str
    observed_head: str
    process_outcome: str
    process_identity: str | None
    process_started_at: str
    process_ended_at: str
    workspace_state: str
    changed_paths: tuple[str, ...]
    proposal_digest: str | None
    candidate_digest: str | None
    validation_stages: tuple[ValidationStage, ...]
    first_failure_boundary: str | None
    failure_code: str | None
    expected: str
    observed: str
    containment_outcome: str
    output_digest: str
    content_reference: str | None
    retryable: bool

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["operation"] = str(self.operation)
        value["test_ids"] = list(self.test_ids)
        value["changed_paths"] = list(self.changed_paths)
        value["validation_stages"] = [item.to_dict() for item in self.validation_stages]
        return value

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: Any) -> "ResultRecord":
        data = _object(value, set(cls.__dataclass_fields__))
        try:
            operation = InvocationOperation(data["operation"])
        except (TypeError, ValueError) as exc:
            raise LabValidationError("INTEGRATION_RESULT_INVALID", "unsupported operation") from exc
        stages = _stages(data["validation_stages"])
        result = cls(
            _exact(data["schema_version"], RESULT_SCHEMA, "schema_version"), _digest(data["invocation_digest"]),
            _digest(data["request_digest"]), _id(data["invocation_id"]), _id(data["attempt_id"]), operation, _digest(data["framework_installation_digest"]),
            _framework_contract_version(data["framework_contract_version"], operation),
            _exact(data["runtime_profile_id"], RUNTIME_PROFILE, "runtime_profile_id"), _digest(data["runtime_identity"]),
            _digest(data["prompt_digest"]), _text(data["test_catalog_version"]), _digest(data["test_catalog_digest"]),
            _digest(data["test_plan_digest"]), _texts(data["test_ids"]), _digest(data["workspace_receipt_digest"]),
            _digest(data["workspace_root_digest"]), _digest(data["workspace_path_digest"]), _sha(data["starting_commit"]), _sha(data["observed_head"]),
            _choice(data["process_outcome"], {"pass", "fail", "not-run", "uncertain"}, "process outcome"),
            _optional_digest(data["process_identity"]), _timestamp(data["process_started_at"]), _timestamp(data["process_ended_at"]),
            _choice(data["workspace_state"], {"unchanged", "changed", "boundary-failed", "unknown"}, "workspace state"), _paths(data["changed_paths"]),
            _optional_digest(data["proposal_digest"]), _optional_digest(data["candidate_digest"]), stages,
            _optional_text(data["first_failure_boundary"]), _optional_text(data["failure_code"]),
            _bounded_text(data["expected"], MAX_STRUCTURED_TEXT_BYTES, "expected"),
            _bounded_text(data["observed"], MAX_STRUCTURED_TEXT_BYTES, "observed"),
            _text(data["containment_outcome"]), _digest(data["output_digest"]),
            _optional_content_reference(data["content_reference"]), data["retryable"],
        )
        _validate_result(result)
        return result


def transition_invocation(
    record: InvocationRecord,
    target: InvocationState,
    *,
    authorized_by: str | None = None,
    authorized_at: str | None = None,
    result_digest: str | None = None,
) -> InvocationRecord:
    if target not in LEGAL_INVOCATION_TRANSITIONS[record.state]:
        raise LabValidationError("INTEGRATION_TRANSITION_INVALID", "invocation transition is not legal")
    if target is InvocationState.COMPLETED and result_digest is None:
        raise LabValidationError("INTEGRATION_RESULT_REQUIRED", "completed invocation requires a result digest")
    if target is not InvocationState.COMPLETED and result_digest is not None:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "only completed invocation accepts a result digest")
    if target is InvocationState.AUTHORIZED:
        if authorized_by is None or authorized_at is None:
            raise LabValidationError("INTEGRATION_AUTHORIZATION_INVALID", "authorization requires controller identity and time")
    elif authorized_by is not None or authorized_at is not None:
        raise LabValidationError("INTEGRATION_AUTHORIZATION_INVALID", "authorization is only set once")
    value = record.to_dict()
    value["state"] = str(target)
    if target is InvocationState.AUTHORIZED:
        value["authorized_by"] = authorized_by
        value["authorized_at"] = authorized_at
    value["result_digest"] = result_digest
    return InvocationRecord.from_mapping(value)


def _validate_invocation(record: InvocationRecord) -> None:
    expected_sandbox = "read-only" if record.operation is InvocationOperation.READ_ONLY_PROPOSAL else "workspace-write"
    if record.sandbox_mode != expected_sandbox:
        raise LabValidationError("INTEGRATION_OPERATION_INVALID", "operation and sandbox differ")
    if record.operation is InvocationOperation.READ_ONLY_PROPOSAL and record.writable_paths:
        raise LabValidationError("INTEGRATION_SCOPE_INVALID", "read-only proposal cannot name writable paths")
    if record.operation is InvocationOperation.WORKSPACE_WRITE_CODE_TASK and not record.writable_paths:
        raise LabValidationError("INTEGRATION_SCOPE_INVALID", "code task requires writable paths")
    if (
        record.model != RUNTIME_MODEL
        or record.reasoning_effort != RUNTIME_REASONING_EFFORT
        or record.timeout_seconds != RUNTIME_TIMEOUT_SECONDS
    ):
        raise LabValidationError(
            "INTEGRATION_RUNTIME_INVALID", "runtime profile values differ from the protected profile"
        )
    if record.state is InvocationState.PREPARED and (record.authorized_by is not None or record.authorized_at is not None):
        raise LabValidationError("INTEGRATION_AUTHORIZATION_INVALID", "prepared invocation cannot be authorized")
    if record.state is InvocationState.REJECTED and (record.authorized_by is not None or record.authorized_at is not None):
        raise LabValidationError("INTEGRATION_AUTHORIZATION_INVALID", "rejected invocation cannot be authorized")
    if record.state not in {InvocationState.PREPARED, InvocationState.REJECTED} and (
        record.authorized_by is None or record.authorized_at is None
    ):
        raise LabValidationError("INTEGRATION_AUTHORIZATION_INVALID", "state requires authorization identity")
    if (record.state is InvocationState.COMPLETED) != (record.result_digest is not None):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "only completed invocation has a result digest")


def _validate_result(result: ResultRecord) -> None:
    if result.retryable is not False:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "Phase 3 results cannot be retryable")
    failed = result.process_outcome in {"fail", "uncertain"}
    if failed != (result.first_failure_boundary is not None and result.failure_code is not None):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "failure outcome requires first boundary and code")
    if result.process_outcome == "pass" and (result.first_failure_boundary or result.failure_code):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "successful result cannot report a failure")
    if result.process_ended_at < result.process_started_at:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "process end cannot precede start")
    stage_ids = tuple(stage.test_id for stage in result.validation_stages)
    if stage_ids != result.test_ids[:len(stage_ids)]:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "validation stages must follow the sealed test plan")
    if result.operation is InvocationOperation.READ_ONLY_PROPOSAL:
        if result.changed_paths or result.candidate_digest is not None:
            raise LabValidationError("INTEGRATION_RESULT_INVALID", "proposal cannot report candidate changes")
        if result.process_outcome == "pass" and (
            result.proposal_digest is None or result.process_identity is None or result.content_reference is None
        ):
            raise LabValidationError("INTEGRATION_RESULT_INVALID", "accepted proposal requires custody and content evidence")
    else:
        if result.proposal_digest is not None:
            raise LabValidationError("INTEGRATION_RESULT_INVALID", "code task cannot report proposal content")
        if result.process_outcome == "pass" and (
            result.process_identity is None
            or result.workspace_state != "changed"
            or not result.changed_paths
            or result.candidate_digest is None
            or result.content_reference is None
            or tuple(stage.test_id for stage in result.validation_stages) != result.test_ids
            or any(stage.outcome != "pass" or stage.failure_code is not None for stage in result.validation_stages)
        ):
            raise LabValidationError(
                "INTEGRATION_RESULT_INVALID",
                "accepted code task requires candidate, custody, and complete validation evidence",
            )


def _object(value: Any, expected: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise LabValidationError("INTEGRATION_FIELDS_INVALID", "fields are missing or unknown")
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "text field is invalid")
    return value


def _optional_text(value: Any) -> str | None:
    return None if value is None else _text(value)


def _bounded_text(value: Any, limit: int, field: str) -> str:
    text = _text(value)
    if "\x00" in text or len(text.encode("utf-8")) > limit:
        raise LabValidationError("INTEGRATION_FIELD_INVALID", f"{field} exceeds its retained-text limit")
    lowered = text.lower()
    if any(marker in lowered for marker in (
        "openai_api_key", "codex_api_key", "github_token", "gh_token", "authorization:", "bearer ",
        "\\\\", "//", ":\\", ":/",
    )):
        raise LabValidationError("INTEGRATION_FIELD_INVALID", f"{field} contains forbidden retained content")
    return text


def _optional_content_reference(value: Any) -> str | None:
    if value is None:
        return None
    reference = _path(value)
    if len(reference.encode("utf-8")) > MAX_CONTENT_REFERENCE_BYTES:
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "content reference exceeds its limit")
    return reference


def _exact(value: Any, expected: str, field: str) -> str:
    text = _text(value)
    if text != expected:
        raise LabValidationError("INTEGRATION_VERSION_INVALID", f"unsupported {field}")
    return text


def _framework_contract_version(value: Any, operation: InvocationOperation) -> str:
    expected = (
        FRAMEWORK_CONTRACT_VERSION
        if operation is InvocationOperation.READ_ONLY_PROPOSAL
        else WORKSPACE_WRITE_FRAMEWORK_CONTRACT_VERSION
    )
    return _exact(value, expected, "framework_contract_version")


def _id(value: Any) -> str:
    text = _text(value)
    if not text.replace("-", "").replace("_", "").isalnum():
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "identifier is invalid")
    return text


def validate_invocation_id(value: Any) -> str:
    """Validate an invocation identifier before constructing a storage path."""
    return _id(value)


def _sha(value: Any) -> str:
    text = _text(value)
    if len(text) != 40 or any(character not in "0123456789abcdef" for character in text):
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "commit must be a lowercase SHA")
    return text


def _digest(value: Any) -> str:
    text = _text(value)
    if not text.startswith(_DIGEST_PREFIX) or len(text) != 71 or any(character not in "0123456789abcdef" for character in text[7:]):
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "digest is invalid")
    return text


def _optional_digest(value: Any) -> str | None:
    return None if value is None else _digest(value)


def _positive(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "integer must be positive")
    return value


def _path(value: Any) -> str:
    text = _text(value)
    path = PurePosixPath(text)
    if (
        "\x00" in text
        or "\\" in text
        or text == "."
        or not path.parts
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != text
        or ":" in path.parts[0]
    ):
        raise LabValidationError("INTEGRATION_PATH_INVALID", "path must be normalized and relative")
    return text


def _paths(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LabValidationError("INTEGRATION_PATH_INVALID", "paths must be an array")
    paths = tuple(_path(item) for item in value)
    if paths != tuple(sorted(set(paths))):
        raise LabValidationError("INTEGRATION_PATH_INVALID", "paths must be sorted and unique")
    return paths


def _texts(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "text list is invalid")
    items = tuple(_text(item) for item in value)
    if not items or items != tuple(sorted(set(items))):
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "text list must be non-empty, sorted, and unique")
    return items


def _test_id(value: Any) -> str:
    text = _text(value)
    if len(text) != 4 or not text.startswith("T") or not text[1:].isdigit():
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "test ID is invalid")
    return text


def _path_identities(value: Any) -> tuple[PathIdentity, ...]:
    if not isinstance(value, list):
        raise LabValidationError("INTEGRATION_PATH_INVALID", "readable paths must be an array")
    items = tuple(PathIdentity.from_mapping(item) for item in value)
    if not items or tuple(item.path for item in items) != tuple(sorted({item.path for item in items})):
        raise LabValidationError("INTEGRATION_PATH_INVALID", "readable paths must be sorted and unique")
    return items


def _stages(value: Any) -> tuple[ValidationStage, ...]:
    if not isinstance(value, list):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "validation stages must be an array")
    stages = tuple(ValidationStage.from_mapping(item) for item in value)
    identifiers = tuple(stage.test_id for stage in stages)
    if len(identifiers) != len(set(identifiers)):
        raise LabValidationError("INTEGRATION_RESULT_INVALID", "validation stages must be unique")
    return stages


def _choice(value: Any, choices: set[str], field: str) -> str:
    text = _text(value)
    if text not in choices:
        raise LabValidationError("INTEGRATION_RESULT_INVALID", f"unsupported {field}")
    return text


def _optional_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    text = _text(value)
    if not text.endswith("Z"):
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "timestamp must use UTC Z format")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "timestamp is invalid") from exc
    if parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != text:
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "timestamp must use UTC second precision")
    return text


def _timestamp(value: Any) -> str:
    text = _optional_timestamp(value)
    if text is None:
        raise LabValidationError("INTEGRATION_FIELD_INVALID", "timestamp is required")
    return text
