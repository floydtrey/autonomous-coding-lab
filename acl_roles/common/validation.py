"""Configuration-driven role-response validation plug-in boundary."""
from __future__ import annotations

import importlib
from typing import Any, Mapping

from acl_core.diagnostics import emit, span

from .errors import RoleContractError
from .response import RoleResponse


def validate_configured_response(
    response: RoleResponse,
    *,
    implementation: str | None,
    instructions: Mapping[str, Any],
    profile_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    if implementation is None:
        return {}
    if not isinstance(implementation, str) or ":" not in implementation:
        raise RoleContractError(
            "ROLE_VALIDATOR_INVALID",
            "response validator must use module:function syntax",
        )

    with span(
        "roles.validation",
        "validate",
        implementation=implementation,
        role_status=str(response.status),
    ):
        module_name, function_name = implementation.split(":", 1)
        try:
            module = importlib.import_module(module_name)
            validator = getattr(module, function_name)
        except (ImportError, AttributeError) as exc:
            raise RoleContractError(
                "ROLE_VALIDATOR_MISSING",
                "configured role response validator could not be imported",
                {"implementation": implementation},
            ) from exc

        try:
            value = validator(
                response,
                instructions=dict(instructions),
                profile_metadata=dict(profile_metadata),
            )
        except RoleContractError:
            raise
        except Exception as exc:
            raise RoleContractError(
                "ROLE_VALIDATOR_FAILED",
                "configured role response validator failed",
                {
                    "implementation": implementation,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
            ) from exc

        if value is None:
            value = {}
        if not isinstance(value, Mapping):
            raise RoleContractError(
                "ROLE_VALIDATOR_INVALID",
                "configured role response validator must return a mapping or None",
                {"implementation": implementation},
            )
        result = dict(value)
        emit(
            "INFO",
            "roles.validation",
            "validate",
            "role_response_validated",
            implementation=implementation,
            role_status=str(response.status),
            validation=result,
        )
        return result
