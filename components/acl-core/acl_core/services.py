"""Convenient construction of Core mechanisms.

This is not a workflow engine. It only groups the independent Core services so a
future Controller can receive one object instead of constructing registries itself.
"""
from __future__ import annotations

from dataclasses import dataclass

from .adapters import AdapterRegistry
from .authority import AuthorityService
from .diagnostics import span
from .normalization import NormalizationService
from .resources import ResourceRegistry
from .tools import ToolRegistry


@dataclass(frozen=True)
class CoreServices:
    authority: AuthorityService
    resources: ResourceRegistry
    tools: ToolRegistry
    adapters: AdapterRegistry
    normalization: NormalizationService

    @classmethod
    def create(cls) -> "CoreServices":
        with span("core.services", "create"):
            authority = AuthorityService()
            return cls(
                authority=authority,
                resources=ResourceRegistry(),
                tools=ToolRegistry(authority),
                adapters=AdapterRegistry(),
                normalization=NormalizationService(),
            )
