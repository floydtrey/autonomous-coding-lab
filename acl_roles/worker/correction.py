"""Configurable Worker correction feedback built on shared ACL helpers."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from acl_core.diagnostics import emit
from acl_roles.common.correction import (
    correction_signature as shared_correction_signature,
    failure_from_error,
    previous_response_from_error,
    response_digest,
)
from acl_roles.common.errors import RoleContractError

from .contract import WorkerCorrection, WorkerInput


WORKER_CORRECTION_POLICY_SCHEMA = "acl-worker-corrections:v1"


def load_worker_correction_policy(config_root: str | Path) -> "WorkerCorrectionPolicy":
    return WorkerCorrectionPolicy.load(
        Path(config_root).expanduser().resolve() / "worker_corrections.json"
    )


@dataclass(frozen=True)
class WorkerCorrectionRule:
    code: str
    instruction: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.code, "correction rule code"),
            (self.instruction, "correction rule instruction"),
        ):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise RoleContractError(
                    "WORKER_CORRECTION_POLICY_INVALID",
                    f"{label} must be trimmed nonblank text",
                )


@dataclass(frozen=True)
class WorkerCorrectionPolicy:
    default_instruction: str
    repeated_failure_instruction: str
    rules: tuple[WorkerCorrectionRule, ...]
    max_correction_attempts: int = 3
    repairable_prefixes: tuple[str, ...] = ("WORKER_",)
    non_repairable_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.default_instruction, "default_instruction"),
            (self.repeated_failure_instruction, "repeated_failure_instruction"),
        ):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise RoleContractError(
                    "WORKER_CORRECTION_POLICY_INVALID",
                    f"{label} must be trimmed nonblank text",
                )
        if (
            isinstance(self.max_correction_attempts, bool)
            or not isinstance(self.max_correction_attempts, int)
            or self.max_correction_attempts < 0
        ):
            raise RoleContractError(
                "WORKER_CORRECTION_POLICY_INVALID",
                "max_correction_attempts must be a nonnegative integer",
            )
        if not isinstance(self.rules, tuple) or any(
            not isinstance(item, WorkerCorrectionRule) for item in self.rules
        ):
            raise RoleContractError(
                "WORKER_CORRECTION_POLICY_INVALID",
                "rules must contain WorkerCorrectionRule values",
            )
        codes = tuple(item.code for item in self.rules)
        if len(codes) != len(set(codes)):
            raise RoleContractError(
                "WORKER_CORRECTION_POLICY_INVALID",
                "correction rule codes must be unique",
            )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkerCorrectionPolicy":
        if (
            not isinstance(value, Mapping)
            or value.get("schema_version") != WORKER_CORRECTION_POLICY_SCHEMA
        ):
            raise RoleContractError(
                "WORKER_CORRECTION_POLICY_INVALID",
                "Worker correction policy schema is invalid",
            )
        rules_raw = value.get("rules", {})
        prefixes_raw = value.get("repairable_prefixes", ["WORKER_"])
        non_repairable_raw = value.get("non_repairable_codes", [])
        if not isinstance(rules_raw, Mapping):
            raise RoleContractError(
                "WORKER_CORRECTION_POLICY_INVALID",
                "rules must be a mapping keyed by error code",
            )
        if not isinstance(prefixes_raw, list) or not isinstance(non_repairable_raw, list):
            raise RoleContractError(
                "WORKER_CORRECTION_POLICY_INVALID",
                "repairable/non-repairable code collections must be lists",
            )
        return cls(
            default_instruction=value.get("default_instruction"),
            repeated_failure_instruction=value.get("repeated_failure_instruction"),
            rules=tuple(
                WorkerCorrectionRule(code=str(code), instruction=instruction)
                for code, instruction in sorted(rules_raw.items())
            ),
            max_correction_attempts=value.get("max_correction_attempts", 3),
            repairable_prefixes=tuple(prefixes_raw),
            non_repairable_codes=tuple(non_repairable_raw),
        )

    @classmethod
    def load(cls, path: str | Path) -> "WorkerCorrectionPolicy":
        path = Path(path).expanduser().resolve()
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RoleContractError(
                "WORKER_CORRECTION_POLICY_MISSING",
                "Worker correction policy file is missing",
                {"path": str(path)},
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise RoleContractError(
                "WORKER_CORRECTION_POLICY_INVALID",
                "Worker correction policy file cannot be read",
                {"path": str(path)},
            ) from exc
        return cls.from_mapping(value)

    def instruction_for(self, code: str, *, repeated_failure: bool) -> str:
        for rule in self.rules:
            if rule.code == code:
                return (
                    self.repeated_failure_instruction
                    if repeated_failure
                    else rule.instruction
                )
        if code in self.non_repairable_codes:
            raise RoleContractError(
                "WORKER_CORRECTION_NOT_REPAIRABLE",
                "failure is explicitly excluded from Worker correction",
                {"error_code": code},
            )
        if any(code.startswith(prefix) for prefix in self.repairable_prefixes):
            return (
                self.repeated_failure_instruction
                if repeated_failure
                else self.default_instruction
            )
        raise RoleContractError(
            "WORKER_CORRECTION_NOT_REPAIRABLE",
            "failure is not eligible for Worker correction",
            {"error_code": code},
        )


def worker_previous_response_from_error(
    error: BaseException | Mapping[str, Any],
) -> Any | None:
    return previous_response_from_error(error)


def build_worker_correction_input(
    original: WorkerInput,
    *,
    previous_response: Any,
    error: BaseException | Mapping[str, Any],
    policy: WorkerCorrectionPolicy,
    attempt: int,
    prior_error_signatures: Sequence[str] = (),
) -> WorkerInput:
    if not isinstance(original, WorkerInput):
        raise RoleContractError(
            "WORKER_CORRECTION_INVALID",
            "original must be WorkerInput",
        )
    if not isinstance(policy, WorkerCorrectionPolicy):
        raise RoleContractError(
            "WORKER_CORRECTION_INVALID",
            "policy must be WorkerCorrectionPolicy",
        )
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise RoleContractError(
            "WORKER_CORRECTION_INVALID",
            "attempt must be a positive integer",
        )

    failure = failure_from_error(
        error,
        invalid_code="WORKER_CORRECTION_FAILURE_INVALID",
    )
    previous_digest = response_digest(previous_response)
    signature = shared_correction_signature(
        error_code=failure["code"],
        location=failure["location"],
        previous_response_digest=previous_digest,
    )
    repeated = signature in set(prior_error_signatures)
    instruction = policy.instruction_for(
        failure["code"],
        repeated_failure=repeated,
    )
    details = dict(failure["details"])
    execution_evidence: list[dict[str, Any]] = []
    if original.correction is not None:
        prior_evidence = original.correction.details.get("execution_evidence", [])
        if isinstance(prior_evidence, list):
            execution_evidence.extend(
                dict(item) for item in prior_evidence if isinstance(item, Mapping)
            )
    adapter_telemetry = details.get("adapter_telemetry")
    if isinstance(adapter_telemetry, Mapping):
        current_events = adapter_telemetry.get("tool_events", [])
        if isinstance(current_events, list):
            execution_evidence.extend(
                dict(item) for item in current_events if isinstance(item, Mapping)
            )
    if execution_evidence:
        # Preserve order while removing exact canonical duplicates.
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for item in execution_evidence:
            key = canonical_digest(item)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        details["execution_evidence"] = unique

    correction = WorkerCorrection(
        attempt=attempt,
        error_code=failure["code"],
        message=failure["message"],
        instruction=instruction,
        previous_response=previous_response,
        details=details,
        location=failure["location"],
        previous_response_digest=previous_digest,
        repeated_failure=repeated,
    )
    emit(
        "INFO",
        "roles.worker",
        "build_correction",
        "worker_correction_prepared",
        attempt=attempt,
        error_code=failure["code"],
        location=failure["location"],
        previous_response_digest=previous_digest,
        failure_signature=signature,
        repeated_failure=repeated,
    )
    return WorkerInput(
        plan_id=original.plan_id,
        plan_version=original.plan_version,
        semantic_plan_digest=original.semantic_plan_digest,
        pass_id=original.pass_id,
        stage_id=original.stage_id,
        pass_spec=original.pass_spec,
        plan_context=dict(original.plan_context),
        completed_passes=original.completed_passes,
        prior_worker_results=original.prior_worker_results,
        continuation_handoff=original.continuation_handoff,
        correction=correction,
        metadata=dict(original.metadata),
    )


def correction_signature(worker_input: WorkerInput) -> str | None:
    correction = worker_input.correction
    if correction is None:
        return None
    return shared_correction_signature(
        error_code=correction.error_code,
        location=correction.location,
        previous_response_digest=correction.previous_response_digest,
    )
