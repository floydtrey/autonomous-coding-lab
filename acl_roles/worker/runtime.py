"""Provider- and harness-neutral Worker runtime port.

ACL talks to Worker through these semantic request/response records. Concrete
models, harnesses, providers, and transports live behind a WorkerRuntimeBackend
and remain replaceable configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable, Mapping, Protocol, runtime_checkable

from acl_core.canonical import canonical_digest
from acl_core.diagnostics import emit, span
from acl_roles.common.errors import RoleContractError

from .contract import WorkerInput, WorkerResult
from .validation import validate_worker_result


@dataclass(frozen=True)
class WorkerRuntimeRequest:
    workflow_id: str
    worker_input: WorkerInput
    authority_grant_id: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.workflow_id, str) or not self.workflow_id.strip():
            raise RoleContractError(
                "WORKER_RUNTIME_REQUEST_INVALID",
                "workflow_id must be nonblank text",
            )
        if not isinstance(self.worker_input, WorkerInput):
            raise RoleContractError(
                "WORKER_RUNTIME_REQUEST_INVALID",
                "worker_input must be WorkerInput",
            )
        if self.authority_grant_id is not None and (
            not isinstance(self.authority_grant_id, str)
            or not self.authority_grant_id.strip()
        ):
            raise RoleContractError(
                "WORKER_RUNTIME_REQUEST_INVALID",
                "authority_grant_id must be nonblank text when present",
            )
        if not isinstance(self.metadata, Mapping):
            raise RoleContractError(
                "WORKER_RUNTIME_REQUEST_INVALID",
                "runtime request metadata must be a mapping",
            )

    @property
    def work_type_id(self) -> str | None:
        value = self.worker_input.plan_context.get("work_type_id")
        return value if isinstance(value, str) and value.strip() else None

    @property
    def complexity(self) -> str | None:
        value = self.worker_input.pass_spec.complexity
        return value if isinstance(value, str) and value.strip() else None

    def digest(self) -> str:
        return canonical_digest(
            {
                "workflow_id": self.workflow_id,
                "worker_input": self.worker_input.to_objective(),
                "authority_grant_id": self.authority_grant_id,
                "metadata": dict(self.metadata),
            }
        )


@dataclass(frozen=True)
class WorkerRuntimeResponse:
    result: WorkerResult
    runtime_metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.result, WorkerResult):
            raise RoleContractError(
                "WORKER_RUNTIME_RESPONSE_INVALID",
                "runtime response result must be WorkerResult",
            )
        if not isinstance(self.runtime_metadata, Mapping):
            raise RoleContractError(
                "WORKER_RUNTIME_RESPONSE_INVALID",
                "runtime_metadata must be a mapping",
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "result": self.result.to_dict(),
            "runtime_metadata": dict(self.runtime_metadata),
        }


@runtime_checkable
class WorkerRuntimeBackend(Protocol):
    @property
    def backend_id(self) -> str: ...

    def invoke(self, request: WorkerRuntimeRequest) -> WorkerRuntimeResponse: ...


class WorkerRuntimeService:
    """Stable ACL-facing Worker interface."""

    component = "roles.worker.runtime"

    def __init__(self, backend: WorkerRuntimeBackend) -> None:
        if not isinstance(backend, WorkerRuntimeBackend):
            raise RoleContractError(
                "WORKER_RUNTIME_BACKEND_INVALID",
                "backend does not implement WorkerRuntimeBackend",
            )
        backend_id = getattr(backend, "backend_id", None)
        if not isinstance(backend_id, str) or not backend_id.strip():
            raise RoleContractError(
                "WORKER_RUNTIME_BACKEND_INVALID",
                "backend_id must be nonblank text",
            )
        self.backend = backend

    def invoke(self, request: WorkerRuntimeRequest) -> WorkerRuntimeResponse:
        if not isinstance(request, WorkerRuntimeRequest):
            raise RoleContractError(
                "WORKER_RUNTIME_REQUEST_INVALID",
                "request must be WorkerRuntimeRequest",
            )
        started = perf_counter()
        with span(
            self.component,
            "invoke",
            workflow_id=request.workflow_id,
            backend_id=self.backend.backend_id,
            plan_id=request.worker_input.plan_id,
            pass_id=request.worker_input.pass_id,
            work_type_id=request.work_type_id,
            complexity=request.complexity,
            request_digest=request.digest(),
        ):
            emit(
                "INFO",
                self.component,
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
            if not isinstance(response, WorkerRuntimeResponse):
                raise RoleContractError(
                    "WORKER_RUNTIME_RESPONSE_INVALID",
                    "backend returned an invalid Worker runtime response",
                    {"backend_id": self.backend.backend_id},
                )
            elapsed_ms = round((perf_counter() - started) * 1000, 3)
            execution_events = self._execution_events(
                response.runtime_metadata,
                request.worker_input,
            )
            try:
                validation = validate_worker_result(
                    response.result,
                    worker_input=request.worker_input,
                    execution_events=execution_events,
                )
            except RoleContractError as exc:
                raise RoleContractError(
                    exc.code,
                    exc.message,
                    {
                        **dict(exc.details or {}),
                        "previous_response": response.result.to_dict(),
                        "runtime_metadata": {
                            **dict(response.runtime_metadata),
                            "worker_elapsed_ms": elapsed_ms,
                            "backend_id": self.backend.backend_id,
                        },
                    },
                ) from exc

            runtime_metadata = {
                **dict(response.runtime_metadata),
                "worker_validation": validation,
                "worker_elapsed_ms": elapsed_ms,
                "backend_id": self.backend.backend_id,
            }
            validated = WorkerRuntimeResponse(
                result=response.result,
                runtime_metadata=runtime_metadata,
            )
            emit(
                "INFO",
                self.component,
                "invoke",
                "worker_runtime_finished",
                workflow_id=request.workflow_id,
                backend_id=self.backend.backend_id,
                plan_id=request.worker_input.plan_id,
                pass_id=request.worker_input.pass_id,
                outcome=str(validated.result.outcome),
                runtime_metadata=runtime_metadata,
            )
            return validated


    @staticmethod
    def _execution_events(
        runtime_metadata: Mapping[str, object],
        worker_input: WorkerInput,
    ) -> tuple[Mapping[str, object], ...]:
        events: list[Mapping[str, object]] = []

        role_metadata = runtime_metadata.get("role_metadata")
        if isinstance(role_metadata, Mapping):
            adapter_telemetry = role_metadata.get("adapter_telemetry")
            if isinstance(adapter_telemetry, Mapping):
                current = adapter_telemetry.get("tool_events", [])
                if isinstance(current, list):
                    events.extend(
                        item for item in current if isinstance(item, Mapping)
                    )

        if worker_input.correction is not None:
            prior = worker_input.correction.details.get("execution_evidence", [])
            if isinstance(prior, list):
                events.extend(
                    item for item in prior if isinstance(item, Mapping)
                )

        return tuple(events)


@dataclass
class FunctionWorkerRuntimeBackend:
    """Small deterministic/fake backend using the same runtime port as real Workers."""

    handler: Callable[[WorkerRuntimeRequest], WorkerResult | WorkerRuntimeResponse]
    backend_id: str = "worker.function"

    def __post_init__(self) -> None:
        if not callable(self.handler):
            raise RoleContractError(
                "WORKER_RUNTIME_BACKEND_INVALID",
                "function Worker backend requires a callable handler",
            )
        if not isinstance(self.backend_id, str) or not self.backend_id.strip():
            raise RoleContractError(
                "WORKER_RUNTIME_BACKEND_INVALID",
                "backend_id must be nonblank text",
            )

    def invoke(self, request: WorkerRuntimeRequest) -> WorkerRuntimeResponse:
        value = self.handler(request)
        if isinstance(value, WorkerRuntimeResponse):
            return value
        if isinstance(value, WorkerResult):
            return WorkerRuntimeResponse(
                result=value,
                runtime_metadata={"backend_id": self.backend_id},
            )
        raise RoleContractError(
            "WORKER_RUNTIME_RESPONSE_INVALID",
            "function Worker backend must return WorkerResult or WorkerRuntimeResponse",
            {"backend_id": self.backend_id},
        )
