"""Conservative context-pressure estimates for agent requests.

These estimates are intentionally labeled as estimates. A generic adapter cannot
prove provider tokenization or actually loaded context capacity. The estimator
therefore uses the configured route capacity and reserves output budget before
deciding whether the next request is approaching that declared capacity.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Mapping

from acl_core.canonical import canonical_json


@dataclass(frozen=True)
class ContextPressureEstimate:
    configured_context_window: int | None
    estimated_input_tokens: int
    reserved_output_tokens: int
    projected_tokens: int
    projected_ratio: float | None
    capacity_source: str | None
    action: str
    warning_ratio: float | None
    stop_ratio: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "configured_context_window": self.configured_context_window,
            "estimated_input_tokens": self.estimated_input_tokens,
            "reserved_output_tokens": self.reserved_output_tokens,
            "projected_tokens": self.projected_tokens,
            "projected_ratio": self.projected_ratio,
            "capacity_source": self.capacity_source,
            "action": self.action,
            "warning_ratio": self.warning_ratio,
            "stop_ratio": self.stop_ratio,
        }


def estimate_context_pressure(
    request_body: Mapping[str, Any],
    *,
    configured_context_window: int | None,
    reserved_output_tokens: int | None,
    characters_per_token: float = 4.0,
    warning_ratio: float | None = 0.8,
    stop_ratio: float | None = None,
) -> ContextPressureEstimate:
    if not isinstance(request_body, Mapping):
        raise TypeError("request_body must be a mapping")
    if (
        not isinstance(characters_per_token, (int, float))
        or isinstance(characters_per_token, bool)
        or characters_per_token <= 0
    ):
        raise ValueError("characters_per_token must be positive")
    for value, label in (
        (warning_ratio, "warning_ratio"),
        (stop_ratio, "stop_ratio"),
    ):
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value <= 0
            or value > 1
        ):
            raise ValueError(f"{label} must be within (0, 1]")
    if (
        warning_ratio is not None
        and stop_ratio is not None
        and warning_ratio > stop_ratio
    ):
        raise ValueError("warning_ratio must not exceed stop_ratio")

    serialized = canonical_json(dict(request_body))
    estimated_input = max(1, ceil(len(serialized) / float(characters_per_token)))
    reserved = (
        reserved_output_tokens
        if isinstance(reserved_output_tokens, int)
        and not isinstance(reserved_output_tokens, bool)
        and reserved_output_tokens > 0
        else 0
    )
    projected = estimated_input + reserved

    capacity = (
        configured_context_window
        if isinstance(configured_context_window, int)
        and not isinstance(configured_context_window, bool)
        and configured_context_window > 0
        else None
    )
    ratio = None if capacity is None else round(projected / capacity, 6)
    action = "UNKNOWN"
    if ratio is not None:
        action = "OK"
        if warning_ratio is not None and ratio >= warning_ratio:
            action = "WARN"
        if stop_ratio is not None and ratio >= stop_ratio:
            action = "STOP"

    return ContextPressureEstimate(
        configured_context_window=capacity,
        estimated_input_tokens=estimated_input,
        reserved_output_tokens=reserved,
        projected_tokens=projected,
        projected_ratio=ratio,
        capacity_source=None if capacity is None else "configured_route_estimate",
        action=action,
        warning_ratio=warning_ratio,
        stop_ratio=stop_ratio,
    )
