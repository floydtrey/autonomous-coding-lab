"""Provider- and harness-neutral Planner runtime port.

ACL talks to Planner through these semantic request/response records. Concrete
model servers, providers, harnesses, and transport protocols live behind a
PlannerRuntimeBackend implementation and remain replaceable configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from acl_core.canonical import canonical_digest
from acl_core.diagnostics import emit, span

from acl_roles.common.errors import RoleContractError

from .contract import PlannerInput, PlannerResult
from .validation import validate_planner_result


@dataclass(frozen=True)
class PlannerRuntimeRequest:
    workflow_id: str
    planner_input: PlannerInput
    authority_grant_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.workflow_id, str) or not self.workflow_id.strip():
            raise RoleContractError(
                "PLANNER_RUNTIME_REQUEST_INVALID",
                "workflow_id must be nonblank text",
            )
        if not isinstance(self.planner_input, PlannerInput):
            raise RoleContractError(
                "PLANNER_RUNTIME_REQUEST_INVALID",
                "planner_input must be PlannerInput",
            )
        if self.authority_grant_id is not None and (
            not isinstance(self.authority_grant_id, str)
            or not self.authority_grant_id.strip()
        ):
            raise RoleContractError(
                "PLANNER_RUNTIME_REQUEST_INVALID",
                "authority_grant_id must be nonblank text when present",
            )
        if not isinstance(self.metadata, Mapping):
            raise RoleContractError(
                "PLANNER_RUNTIME_REQUEST_INVALID",
                "runtime request metadata must be a mapping",
            )

    @property
    def work_type_id(self) -> str | None:
        value = self.planner_input.routing_context.get("work_type_id")
        return value if isinstance(value, str) and value.strip() else None

    @property
    def complexity(self) -> str | None:
        value = self.planner_input.routing_context.get("complexity")
        return value if isinstance(value, str) and value.strip() else None

    def digest(self) -> str:
        return canonical_digest(
            {
                "workflow_id": self.workflow_id,
                "planner_input": self.planner_input.to_objective(),
                "authority_grant_id": self.authority_grant_id,
                "metadata": dict(self.metadata),
            }
        )


@dataclass(frozen=True)
class PlannerRuntimeResponse:
    result: PlannerResult
    runtime_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.result, PlannerResult):
            raise RoleContractError(
                "PLANNER_RUNTIME_RESPONSE_INVALID",
                "runtime response result must be PlannerResult",
            )
        if not isinstance(self.runtime_metadata, Mapping):
            raise RoleContractError(
                "PLANNER_RUNTIME_RESPONSE_INVALID",
                "runtime_metadata must be a mapping",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "result": self.result.to_dict(),
            "runtime_metadata": dict(self.runtime_metadata),
        }


@runtime_checkable
class PlannerRuntimeBackend(Protocol):
    """Replaceable Planner execution backend."""

    @property
    def backend_id(self) -> str: ...

    def invoke(self, request: PlannerRuntimeRequest) -> PlannerRuntimeResponse: ...


class PlannerRuntimeService:
    """Stable ACL-facing Planner interface."""

    component = "roles.planner.runtime"

    def __init__(self, backend: PlannerRuntimeBackend) -> None:
        if not isinstance(backend, PlannerRuntimeBackend):
            raise RoleContractError(
                "PLANNER_RUNTIME_BACKEND_INVALID",
                "backend does not implement PlannerRuntimeBackend",
            )
        backend_id = getattr(backend, "backend_id", None)
        if not isinstance(backend_id, str) or not backend_id.strip():
            raise RoleContractError(
                "PLANNER_RUNTIME_BACKEND_INVALID",
                "backend_id must be nonblank text",
            )
        self.backend = backend

    def invoke(self, request: PlannerRuntimeRequest) -> PlannerRuntimeResponse:
        if not isinstance(request, PlannerRuntimeRequest):
            raise RoleContractError(
                "PLANNER_RUNTIME_REQUEST_INVALID",
                "request must be PlannerRuntimeRequest",
            )
        started = perf_counter()
        with span(
            self.component,
            "invoke",
            backend_id=self.backend.backend_id,
            workflow_id=request.workflow_id,
            invocation_mode=str(request.planner_input.invocation_mode),
            work_type_id=request.work_type_id,
            complexity=request.complexity,
            request_digest=request.digest(),
        ):
            emit(
                "INFO",
                self.component,
                "invoke",
                "planner_runtime_started",
                backend_id=self.backend.backend_id,
                workflow_id=request.workflow_id,
                invocation_mode=str(request.planner_input.invocation_mode),
                work_type_id=request.work_type_id,
                complexity=request.complexity,
                correction_attempt=(
                    None
                    if request.planner_input.correction is None
                    else request.planner_input.correction.attempt
                ),
            )
            response = self.backend.invoke(request)
            if not isinstance(response, PlannerRuntimeResponse):
                raise RoleContractError(
                    "PLANNER_RUNTIME_RESPONSE_INVALID",
                    "backend returned an invalid Planner runtime response",
                    {"backend_id": self.backend.backend_id},
                )
            validation = validate_planner_result(
                response.result,
                planner_input=request.planner_input,
            )
            runtime_metadata = {
                **dict(response.runtime_metadata),
                "planner_validation": validation,
                "planner_elapsed_ms": round((perf_counter() - started) * 1000, 3),
                "backend_id": self.backend.backend_id,
            }
            validated = PlannerRuntimeResponse(
                result=response.result,
                runtime_metadata=runtime_metadata,
            )
            emit(
                "INFO",
                self.component,
                "invoke",
                "planner_runtime_finished",
                backend_id=self.backend.backend_id,
                workflow_id=request.workflow_id,
                disposition=str(validated.result.disposition),
                runtime_metadata=runtime_metadata,
            )
            return validated


@dataclass
class FunctionPlannerRuntimeBackend:
    """Small deterministic/fake backend using the same runtime port as real models."""

    handler: Callable[[PlannerRuntimeRequest], PlannerResult | PlannerRuntimeResponse]
    backend_id: str = "planner.function"

    def __post_init__(self) -> None:
        if not callable(self.handler):
            raise RoleContractError(
                "PLANNER_RUNTIME_BACKEND_INVALID",
                "function Planner backend requires a callable handler",
            )
        if not isinstance(self.backend_id, str) or not self.backend_id.strip():
            raise RoleContractError(
                "PLANNER_RUNTIME_BACKEND_INVALID",
                "backend_id must be nonblank text",
            )

    def invoke(self, request: PlannerRuntimeRequest) -> PlannerRuntimeResponse:
        value = self.handler(request)
        if isinstance(value, PlannerRuntimeResponse):
            return value
        if isinstance(value, PlannerResult):
            return PlannerRuntimeResponse(
                result=value,
                runtime_metadata={"backend_id": self.backend_id},
            )
        raise RoleContractError(
            "PLANNER_RUNTIME_RESPONSE_INVALID",
            "function Planner backend must return PlannerResult or PlannerRuntimeResponse",
            {"backend_id": self.backend_id},
        )
