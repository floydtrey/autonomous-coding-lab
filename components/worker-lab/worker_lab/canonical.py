from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .errors import LabValidationError


def canonical_json(value: Any) -> str:
    _validate_json_value(value, "$")
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise LabValidationError("CANONICAL_VALUE_INVALID", str(exc)) from exc


def canonical_digest(value: Any) -> str:
    encoded = canonical_json(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _validate_json_value(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        raise LabValidationError(
            "CANONICAL_FLOAT_FORBIDDEN",
            f"floating-point values are forbidden in canonical records at {path}",
        )
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise LabValidationError(
                    "CANONICAL_KEY_INVALID", f"object key at {path} must be text"
                )
            _validate_json_value(child, f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _validate_json_value(child, f"{path}[{index}]")
        return
    raise LabValidationError(
        "CANONICAL_VALUE_INVALID", f"unsupported canonical value at {path}: {type(value).__name__}"
    )
