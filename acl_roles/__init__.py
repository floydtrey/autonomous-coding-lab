"""Shared AI-role contracts for ACL Next.

Role implementations live above Core and Controller. This package owns the common
request/response/context/instruction envelope used by Determiner, Planner, Worker,
Reviewer, and future roles.
"""
from .common import (
    ContextReference,
    InstructionSet,
    RoleContext,
    RoleContractError,
    RoleDiagnostics,
    RoleRequest,
    RoleResponse,
    RoleStatus,
)

__all__ = [
    "ContextReference",
    "InstructionSet",
    "RoleContext",
    "RoleContractError",
    "RoleDiagnostics",
    "RoleRequest",
    "RoleResponse",
    "RoleStatus",
]

from .determiner import (
    ClassificationStatus,
    DeterminerInput,
    DeterminerResult,
    DeterminerTaxonomy,
    WorkTypeDefinition,
    parse_determiner_response,
)

__all__ += [
    "ClassificationStatus",
    "DeterminerInput",
    "DeterminerResult",
    "DeterminerTaxonomy",
    "WorkTypeDefinition",
    "parse_determiner_response",
]


from .planner import (
    PLANNER_INPUT_SCHEMA,
    PLANNER_RESULT_SCHEMA,
    ExecutionPlan,
    FilesystemIntent,
    MoveIntent,
    PassSpec,
    PlanType,
    PlannerAnswer,
    PlannerCorrection,
    PlannerCorrectionPolicy,
    PlannerDisposition,
    PlannerInput,
    PlannerInvocationMode,
    PlannerQuestion,
    PlannerResult,
    ProjectReference,
    ReferenceMaterial,
    StageSpec,
    TaskSpec,
    WorkerConsultation,
    WorkspaceSpec,
    build_planner_correction_input,
    correction_signature,
    planner_failure_from_error,
    validate_planner_result,
    validate_planner_role_response,
)

__all__ += [
    "PLANNER_INPUT_SCHEMA",
    "PLANNER_RESULT_SCHEMA",
    "ExecutionPlan",
    "FilesystemIntent",
    "MoveIntent",
    "PassSpec",
    "PlanType",
    "PlannerAnswer",
    "PlannerCorrection",
    "PlannerCorrectionPolicy",
    "PlannerDisposition",
    "PlannerInput",
    "PlannerInvocationMode",
    "PlannerQuestion",
    "PlannerResult",
    "ProjectReference",
    "ReferenceMaterial",
    "StageSpec",
    "TaskSpec",
    "WorkerConsultation",
    "WorkspaceSpec",
    "build_planner_correction_input",
    "correction_signature",
    "planner_failure_from_error",
    "validate_planner_result",
    "validate_planner_role_response",
]
