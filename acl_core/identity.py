"""Opaque Core identities and correlation context."""
from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import asdict, dataclass
import re
from uuid import uuid4

from .errors import CoreError


_KIND = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
_VALUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{5,127}$")


@dataclass(frozen=True)
class CoreIdentity:
    kind: str
    value: str

    def __post_init__(self) -> None:
        if not _KIND.fullmatch(self.kind) or not _VALUE.fullmatch(self.value):
            raise CoreError("CORE_IDENTITY_INVALID", "identity is malformed")

    @classmethod
    def new(cls, kind: str) -> "CoreIdentity":
        if not _KIND.fullmatch(kind):
            raise CoreError("CORE_IDENTITY_INVALID", "identity kind is malformed")
        return cls(kind, f"{kind}:{uuid4().hex}")

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class Correlation:
    request_id: str | None = None
    run_id: str | None = None
    task_id: str | None = None
    attempt_id: str | None = None
    grant_id: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)

    def merged(self, **updates: str | None) -> "Correlation":
        value = self.to_dict()
        value.update(updates)
        return Correlation(**value)


_CURRENT: ContextVar[Correlation] = ContextVar("acl_core_correlation", default=Correlation())


def current_correlation() -> Correlation:
    return _CURRENT.get()


def push_correlation(value: Correlation) -> Token:
    return _CURRENT.set(value)


def pop_correlation(token: Token) -> None:
    _CURRENT.reset(token)
