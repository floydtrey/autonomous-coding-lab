"""Narrow transport/syntax normalization.

Core may repair representation only when meaning is unchanged and unambiguous.
It never invents missing keys, arguments, tasks, authority, or semantic content.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping

from .diagnostics import emit, span
from .errors import CoreError


_FENCE = re.compile(r"^\s*\x60\x60\x60(?:json)?\s*\n(?P<body>.*)\n\x60\x60\x60\s*$", re.IGNORECASE | re.DOTALL)


class NormalizationService:
    component = "core.normalization"

    def json_value(self, value: str | bytes | Mapping[str, Any] | list[Any]) -> Any:
        with span(self.component, "json_value", input_type=type(value).__name__):
            if isinstance(value, Mapping):
                return dict(value)
            if isinstance(value, list):
                return list(value)
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise CoreError("NORMALIZATION_INVALID", "structured bytes are not UTF-8") from exc
            if not isinstance(value, str):
                raise CoreError("NORMALIZATION_INVALID", "structured input must be text, bytes, mapping, or list")

            original = value
            text = value.lstrip("\ufeff").strip()
            match = _FENCE.fullmatch(text)
            if match is not None:
                text = match.group("body").strip()
                emit("INFO", self.component, "json_value", "normalized", transform="strip_json_fence")
            elif original != text:
                emit("DEBUG", self.component, "json_value", "normalized", transform="trim_transport_whitespace")

            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise CoreError(
                    "NORMALIZATION_INVALID",
                    "structured text is not unambiguous JSON",
                    {"line": exc.lineno, "column": exc.colno, "message": exc.msg},
                ) from exc

    def mapping(self, value: Any) -> dict[str, Any]:
        with span(self.component, "mapping", input_type=type(value).__name__):
            normalized = self.json_value(value)
            if not isinstance(normalized, dict):
                raise CoreError("NORMALIZATION_INVALID", "expected a JSON object")
            return normalized
