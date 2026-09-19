"""Shared AI-role contracts for ACL Next.

Role implementations live above Core and Controller. This package owns the common
request/response/context/instruction envelope used by Determiner, Planner, Worker,
Reviewer, and future roles.
"""
from .common import (
    ContextReference,
    InstructionSet,
    RoleContext,
    RoleDiagnostics,
    RoleRequest,
    RoleResponse,
    RoleStatus,
)

__all__ = [
    "ContextReference",
    "InstructionSet",
    "RoleContext",
    "RoleDiagnostics",
    "RoleRequest",
    "RoleResponse",
    "RoleStatus",
]
