"""Provider-neutral Worker runtime port."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from acl_core.diagnostics import emit, span

from .contract import WorkerInput, WorkerResult
from .validation import validate_worker_result


@dataclass(frozen=True)
class WorkerRuntimeRequest:
    workflow_id: str
    worker_input: WorkerInput
    authority_grant_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def work_type_id(self) -> str | None:
        value = self.worker_input.plan_context.get("work_type_id")
        return value if isinstance(value, str) and value.strip() else None

    @property
    def complexity(self) -> str | None:
        value = self.worker_input.pass_spec.complexity
        return value if isinstance(value, str) and value.strip() else None


@dataclass(frozen=True)
class WorkerRuntimeResponse:
    result: WorkerResult
    runtime_metadata: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class WorkerRuntimeBackend(Protocol):
    backend_id: str

    def invoke(self, request: WorkerRuntimeRequest) -> WorkerRuntimeResponse: ...


@dataclass
class WorkerRuntimeService:
    backend: WorkerRuntimeBackend

    def invoke(self, request: WorkerRuntimeRequest) -> WorkerRuntimeResponse:
        with span(
            "roles.worker.runtime",
            "invoke",
            workflow_id=request.workflow_id,
            backend_id=self.backend.backend_id,
            plan_id=request.worker_input.plan_id,
            pass_id=request.worker_input.pass_id,
            work_type_id=request.work_type_id,
            complexity=request.complexity,
        ):
            emit(
                "INFO",
                "roles.worker.runtime",
                "invoke",
                "worker_runtime_started",
                workflow_id=request.workflow_id,
                backend_id=self.backend.backend_id,
                plan_id=request.worker_input.plan_id,
                pass_id=request.worker_input.pass_id,
                work_type_id=request.work_type_id,
                complexity=request.complexity,
            )
            response = self.backend.invoke(request)
            validation = validate_worker_result(
                response.result,
                worker_input=request.worker_input,
            )
            return WorkerRuntimeResponse(
                result=response.result,
                runtime_metadata={
                    **dict(response.runtime_metadata),
                    "worker_validation": validation,
                },
            )


@dataclass
class FunctionWorkerRuntimeBackend:
    handler: Any
    backend_id: str = "function.worker"

    def invoke(self, request: WorkerRuntimeRequest) -> WorkerRuntimeResponse:
        value = self.handler(request)
        if isinstance(value, WorkerRuntimeResponse):
            return value
        if isinstance(value, WorkerResult):
            return WorkerRuntimeResponse(result=value)
        raise TypeError("Worker runtime handler must return WorkerResult or WorkerRuntimeResponse")
