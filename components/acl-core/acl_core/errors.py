"""Core error contract.

Errors are intentionally small and transport-neutral. Higher layers may render
or persist them however they choose.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CoreError(Exception):
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
        raise CoreError(code, message, details or None)
