"""Configuration-driven role-response validation plug-in boundary."""
from __future__ import annotations

import importlib
from typing import Any, Mapping

from acl_core.diagnostics import emit, span

from .errors import RoleContractError
from .request import RoleRequest
from .response import RoleResponse


def normalize_configured_response(
    value: Mapping[str, Any],
    *,
    implementation: str | None,
    instructions: Mapping[str, Any],
    profile_metadata: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, Mapping):
        raise RoleContractError("ROLE_NORMALIZER_INVALID", "role response must be a mapping")
    if implementation is None:
        return dict(value), {}
    if not isinstance(implementation, str) or ":" not in implementation:
        raise RoleContractError(
            "ROLE_NORMALIZER_INVALID",
            "response normalizer must use module:function syntax",
        )

    with span(
        "roles.validation",
        "normalize",
        implementation=implementation,
    ):
        module_name, function_name = implementation.split(":", 1)
        try:
            module = importlib.import_module(module_name)
            normalizer = getattr(module, function_name)
        except (ImportError, AttributeError) as exc:
            raise RoleContractError(
                "ROLE_NORMALIZER_MISSING",
                "configured role response normalizer could not be imported",
                {"implementation": implementation},
            ) from exc

        try:
            normalized = normalizer(
                dict(value),
                instructions=dict(instructions),
                profile_metadata=dict(profile_metadata),
            )
        except RoleContractError:
            raise
        except Exception as exc:
            raise RoleContractError(
                "ROLE_NORMALIZER_FAILED",
                "configured role response normalizer failed",
                {
                    "implementation": implementation,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
            ) from exc

        if not isinstance(normalized, tuple) or len(normalized) != 2:
            raise RoleContractError(
                "ROLE_NORMALIZER_INVALID",
                "response normalizer must return (mapping, metadata)",
                {"implementation": implementation},
            )
        repaired, metadata = normalized
        if not isinstance(repaired, Mapping) or not isinstance(metadata, Mapping):
            raise RoleContractError(
                "ROLE_NORMALIZER_INVALID",
                "response normalizer outputs must be mappings",
                {"implementation": implementation},
            )
        repaired = dict(repaired)
        metadata = dict(metadata)
        emit(
            "INFO",
            "roles.validation",
            "normalize",
            "role_response_normalized",
            implementation=implementation,
            normalization=metadata,
        )
        return repaired, metadata


def validate_configured_response(
    response: RoleResponse,
    *,
    implementation: str | None,
    instructions: Mapping[str, Any],
    profile_metadata: Mapping[str, Any],
    request: RoleRequest | None = None,
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
                request=request,
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
