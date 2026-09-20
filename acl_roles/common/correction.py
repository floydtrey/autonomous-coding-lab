"""Shared correction helpers for ACL AI roles.

Role-specific modules still own their correction payloads and wording. These
helpers own only transport/controller error normalization, rejected-response
recovery, and stable no-progress signatures.
"""
from __future__ import annotations

from typing import Any, Mapping

from acl_core.canonical import canonical_digest
from .errors import RoleContractError


def deepest_failure(value: Mapping[str, Any]) -> dict[str, Any]:
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


def failure_from_error(
    error: BaseException | Mapping[str, Any],
    *,
    invalid_code: str = "ROLE_CORRECTION_FAILURE_INVALID",
) -> dict[str, Any]:
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

    failure = deepest_failure(value)
    code = failure.get("code")
    message = failure.get("message")
    details = failure.get("details", {})
    if not isinstance(code, str) or not code.strip():
        raise RoleContractError(
            invalid_code,
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


def previous_response_from_error(
    error: BaseException | Mapping[str, Any],
) -> Any | None:
    if isinstance(error, Mapping):
        current: Any = dict(error)
    else:
        to_dict = getattr(error, "to_dict", None)
        if callable(to_dict):
            current = to_dict()
        else:
            return None

    visited = 0
    while isinstance(current, Mapping) and visited < 12:
        details = current.get("details")
        if isinstance(details, Mapping):
            if "previous_response" in details:
                return details.get("previous_response")
            cause = details.get("cause")
            if isinstance(cause, Mapping):
                current = cause
                visited += 1
                continue
            adapter_error = details.get("adapter_error")
            if isinstance(adapter_error, Mapping):
                current = adapter_error
                visited += 1
                continue
        break
    return None


def response_digest(value: Any) -> str | None:
    try:
        return canonical_digest(value)
    except Exception:
        return None


def correction_signature(
    *,
    error_code: str,
    location: str | None,
    previous_response_digest: str | None,
) -> str:
    return canonical_digest(
        {
            "error_code": error_code,
            "location": location,
            "previous_response_digest": previous_response_digest,
        }
    )
