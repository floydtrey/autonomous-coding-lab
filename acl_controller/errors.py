"""Controller error contract.

Controller errors describe orchestration and configuration failures. Core errors
remain owned by acl_core and are not rewritten into Controller-specific meanings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class ControllerError(Exception):
    code: str
    message: str
    details: Mapping[str, Any] | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": dict(self.details or {}),
        }


def require(condition: bool, code: str, message: str, **details: Any) -> None:
    if not condition:
        raise ControllerError(code, message, details or None)
