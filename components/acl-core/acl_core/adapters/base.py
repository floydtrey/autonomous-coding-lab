"""Provider-neutral adapter contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from ..identity import CoreIdentity


@dataclass(frozen=True)
class AdapterRequest:
    operation: str
    payload: Mapping[str, Any]
    request_id: str = field(default_factory=lambda: CoreIdentity.new("adapterrequest").value)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterResponse:
    request_id: str
    ok: bool
    payload: Any = None
    error: Mapping[str, Any] | None = None


@runtime_checkable
class CoreAdapter(Protocol):
    @property
    def adapter_id(self) -> str: ...

    def invoke(self, request: AdapterRequest) -> AdapterResponse: ...
