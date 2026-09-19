"""Configurable Planner correction feedback.

ACL uses this policy after deterministic validation rejects a Planner response.
The policy selects a targeted repair instruction, preserves the original
PlannerInput, attaches the previous response and failure details, and produces
a new PlannerInput for the next Planner attempt.

This module does not own retry limits. ACL supplies the correction attempt number
and decides whether another attempt is allowed.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from acl_core.canonical import canonical_digest
from acl_core.diagnostics import emit, span

from acl_roles.common.errors import RoleContractError

from .contract import PlannerCorrection, PlannerInput


PLANNER_CORRECTION_POLICY_SCHEMA = "acl-planner-corrections:v1"


def load_planner_correction_policy(config_root: str | Path) -> "PlannerCorrectionPolicy":
    """Load the editable correction policy from ACL's config root."""
    return PlannerCorrectionPolicy.load(
        Path(config_root).expanduser().resolve() / "planner_corrections.json"
    )


@dataclass(frozen=True)
class PlannerCorrectionRule:
    code: str
    instruction: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.code, "correction rule code"),
            (self.instruction, "correction rule instruction"),
        ):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise RoleContractError(
                    "PLANNER_CORRECTION_POLICY_INVALID",
                    f"{label} must be trimmed nonblank text",
                )


@dataclass(frozen=True)
class PlannerCorrectionPolicy:
    default_instruction: str
    repeated_failure_instruction: str
    rules: tuple[PlannerCorrectionRule, ...]
    repairable_prefixes: tuple[str, ...] = ("PLANNER_",)
    non_repairable_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.default_instruction, "default_instruction"),
            (self.repeated_failure_instruction, "repeated_failure_instruction"),
        ):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise RoleContractError(
                    "PLANNER_CORRECTION_POLICY_INVALID",
                    f"{label} must be trimmed nonblank text",
                )
        if not isinstance(self.rules, tuple) or any(
            not isinstance(item, PlannerCorrectionRule) for item in self.rules
        ):
            raise RoleContractError(
                "PLANNER_CORRECTION_POLICY_INVALID",
                "rules must contain PlannerCorrectionRule values",
            )
        codes = tuple(item.code for item in self.rules)
        if len(codes) != len(set(codes)):
            raise RoleContractError(
                "PLANNER_CORRECTION_POLICY_INVALID",
                "correction rule codes must be unique",
            )
        if not isinstance(self.repairable_prefixes, tuple) or any(
            not isinstance(item, str) or not item.strip()
            for item in self.repairable_prefixes
        ):
            raise RoleContractError(
                "PLANNER_CORRECTION_POLICY_INVALID",
                "repairable_prefixes must contain nonblank text",
            )
        if not isinstance(self.non_repairable_codes, tuple) or any(
            not isinstance(item, str) or not item.strip()
            for item in self.non_repairable_codes
        ):
            raise RoleContractError(
                "PLANNER_CORRECTION_POLICY_INVALID",
                "non_repairable_codes must contain nonblank text",
            )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlannerCorrectionPolicy":
        if not isinstance(value, Mapping) or value.get("schema_version") != PLANNER_CORRECTION_POLICY_SCHEMA:
            raise RoleContractError(
                "PLANNER_CORRECTION_POLICY_INVALID",
                "Planner correction policy schema is invalid",
            )
        default_instruction = value.get("default_instruction")
        repeated = value.get("repeated_failure_instruction")
        rules_raw = value.get("rules", {})
        prefixes_raw = value.get("repairable_prefixes", ["PLANNER_"])
        non_repairable_raw = value.get("non_repairable_codes", [])
        if not isinstance(rules_raw, Mapping):
            raise RoleContractError(
                "PLANNER_CORRECTION_POLICY_INVALID",
                "rules must be a mapping keyed by error code",
            )
        if not isinstance(prefixes_raw, list):
            raise RoleContractError(
                "PLANNER_CORRECTION_POLICY_INVALID",
                "repairable_prefixes must be a list",
            )
        if not isinstance(non_repairable_raw, list):
            raise RoleContractError(
                "PLANNER_CORRECTION_POLICY_INVALID",
                "non_repairable_codes must be a list",
            )
        rules = tuple(
            PlannerCorrectionRule(code=str(code), instruction=instruction)
            for code, instruction in sorted(rules_raw.items())
        )
        return cls(
            default_instruction=default_instruction,
            repeated_failure_instruction=repeated,
            rules=rules,
            repairable_prefixes=tuple(prefixes_raw),
            non_repairable_codes=tuple(non_repairable_raw),
        )

    @classmethod
    def load(cls, path: str | Path) -> "PlannerCorrectionPolicy":
        path = Path(path).expanduser().resolve()
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RoleContractError(
                "PLANNER_CORRECTION_POLICY_MISSING",
                "Planner correction policy file is missing",
                {"path": str(path)},
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise RoleContractError(
                "PLANNER_CORRECTION_POLICY_INVALID",
                "Planner correction policy file cannot be read",
                {"path": str(path)},
            ) from exc
        return cls.from_mapping(value)

    def instruction_for(self, code: str, *, repeated_failure: bool) -> str:
        if repeated_failure:
            return self.repeated_failure_instruction
        for rule in self.rules:
            if rule.code == code:
                return rule.instruction
        if code in self.non_repairable_codes:
            raise RoleContractError(
                "PLANNER_CORRECTION_NOT_REPAIRABLE",
                "failure is explicitly excluded from Planner correction",
                {"error_code": code},
            )
        if any(code.startswith(prefix) for prefix in self.repairable_prefixes):
            return self.default_instruction
        raise RoleContractError(
            "PLANNER_CORRECTION_NOT_REPAIRABLE",
            "failure is not eligible for Planner correction",
            {"error_code": code},
        )


def _deepest_failure(value: Mapping[str, Any]) -> dict[str, Any]:
    """Prefer the most specific nested cause from wrapped Controller errors."""
    current = dict(value)
    while True:
        details = current.get("details")
        if not isinstance(details, Mapping):
            return current
        cause = details.get("cause")
        if isinstance(cause, Mapping) and isinstance(cause.get("code"), str):
            current = dict(cause)
            continue
        adapter_error = details.get("adapter_error")
        if isinstance(adapter_error, Mapping) and isinstance(adapter_error.get("code"), str):
            current = dict(adapter_error)
            continue
        return current


def planner_failure_from_error(error: BaseException | Mapping[str, Any]) -> dict[str, Any]:
    """Normalize Role/Controller-style failures into one correction record."""
    if isinstance(error, Mapping):
        value = dict(error)
    else:
        to_dict = getattr(error, "to_dict", None)
        if callable(to_dict):
            value = to_dict()
        else:
            code = getattr(error, "code", None)
            message = getattr(error, "message", None)
            value = {
                "code": code if isinstance(code, str) else type(error).__name__,
                "message": message if isinstance(message, str) else str(error),
                "details": {},
            }

    failure = _deepest_failure(value)
    code = failure.get("code")
    message = failure.get("message")
    details = failure.get("details", {})
    if not isinstance(code, str) or not code.strip():
        raise RoleContractError(
            "PLANNER_CORRECTION_FAILURE_INVALID",
            "correction failure does not contain an error code",
        )
    if not isinstance(message, str) or not message.strip():
        message = code
    if not isinstance(details, Mapping):
        details = {}

    location = details.get("location")
    return {
        "code": code.strip(),
        "message": message.strip(),
        "details": dict(details),
        "location": location if isinstance(location, str) and location.strip() else None,
    }


def _digest_previous_response(value: Any) -> str | None:
    try:
        return canonical_digest(value)
    except Exception:
        return None


def build_planner_correction_input(
    original: PlannerInput,
    *,
    previous_response: Any,
    error: BaseException | Mapping[str, Any],
    policy: PlannerCorrectionPolicy,
    attempt: int,
    prior_error_signatures: Sequence[str] = (),
) -> PlannerInput:
    """Construct a targeted correction attempt while preserving original intent."""
    if not isinstance(original, PlannerInput):
        raise RoleContractError(
            "PLANNER_CORRECTION_INVALID",
            "original must be PlannerInput",
        )
    if not isinstance(policy, PlannerCorrectionPolicy):
        raise RoleContractError(
            "PLANNER_CORRECTION_INVALID",
            "policy must be PlannerCorrectionPolicy",
        )
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise RoleContractError(
            "PLANNER_CORRECTION_INVALID",
            "attempt must be a positive integer",
        )

    failure = planner_failure_from_error(error)
    response_digest = _digest_previous_response(previous_response)
    signature_source = {
        "error_code": failure["code"],
        "location": failure["location"],
        "previous_response_digest": response_digest,
    }
    signature = canonical_digest(signature_source)
    repeated = signature in set(prior_error_signatures)
    instruction = policy.instruction_for(
        failure["code"],
        repeated_failure=repeated,
    )

    correction = PlannerCorrection(
        attempt=attempt,
        error_code=failure["code"],
        message=failure["message"],
        instruction=instruction,
        previous_response=previous_response,
        details=failure["details"],
        location=failure["location"],
        previous_response_digest=response_digest,
        repeated_failure=repeated,
    )

    emit(
        "INFO",
        "roles.planner",
        "build_correction",
        "planner_correction_prepared",
        attempt=attempt,
        error_code=failure["code"],
        location=failure["location"],
        previous_response_digest=response_digest,
        failure_signature=signature,
        repeated_failure=repeated,
    )

    return PlannerInput(
        invocation_mode=original.invocation_mode,
        request=dict(original.request),
        routing_context=dict(original.routing_context),
        consultation=original.consultation,
        elevation_answers=dict(original.elevation_answers),
        correction=correction,
        metadata=dict(original.metadata),
    )


def correction_signature(planner_input: PlannerInput) -> str | None:
    """Return the stable signature ACL can retain to detect no-progress repeats."""
    correction = planner_input.correction
    if correction is None:
        return None
    return canonical_digest(
        {
            "error_code": correction.error_code,
            "location": correction.location,
            "previous_response_digest": correction.previous_response_digest,
        }
    )
