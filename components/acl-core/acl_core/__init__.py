"""Autonomous Coding Lab Core.

Core provides mechanisms only. It does not plan, route workflows, choose models,
operate Git, manage KC semantics, or perform role reasoning.
"""
from .adapters import AdapterRegistry, AdapterRequest, AdapterResponse, CoreAdapter
from .authority import AuthorityEnvelope, AuthorityGrant, AuthorityRequest, AuthorityService
from .diagnostics import DiagnosticConfig, config as diagnostic_config, configure as configure_diagnostics
from .errors import CoreError
from .identity import Correlation, CoreIdentity, current_correlation, pop_correlation, push_correlation
from .normalization import NormalizationService
from .resources import ResourceRef, ResourceRegistry, TargetRef
from .services import CoreServices
from .tools import ToolCall, ToolDefinition, ToolRegistry, ToolResult

__all__ = [
    "AdapterRegistry",
    "AdapterRequest",
    "AdapterResponse",
    "AuthorityEnvelope",
    "AuthorityGrant",
    "AuthorityRequest",
    "AuthorityService",
    "CoreAdapter",
    "CoreError",
    "CoreIdentity",
    "CoreServices",
    "Correlation",
    "DiagnosticConfig",
    "NormalizationService",
    "ResourceRef",
    "ResourceRegistry",
    "TargetRef",
    "ToolCall",
    "ToolDefinition",
    "ToolRegistry",
    "ToolResult",
    "configure_diagnostics",
    "current_correlation",
    "diagnostic_config",
    "pop_correlation",
    "push_correlation",
]
