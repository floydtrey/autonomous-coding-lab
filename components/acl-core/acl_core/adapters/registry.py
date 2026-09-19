"""Registry and invocation boundary for replaceable adapters."""
from __future__ import annotations

from ..diagnostics import span
from ..errors import CoreError
from .base import AdapterRequest, AdapterResponse, CoreAdapter


class AdapterRegistry:
    component = "core.adapters"

    def __init__(self) -> None:
        self._adapters: dict[str, CoreAdapter] = {}

    def register(self, adapter: CoreAdapter) -> CoreAdapter:
        adapter_id = getattr(adapter, "adapter_id", None)
        with span(self.component, "register", adapter_id=adapter_id):
            if not isinstance(adapter_id, str) or not adapter_id.strip():
                raise CoreError("ADAPTER_INVALID", "adapter must expose a nonblank adapter_id")
            existing = self._adapters.get(adapter_id)
            if existing is not None and existing is not adapter:
                raise CoreError("ADAPTER_CONFLICT", "adapter ID is already registered", {"adapter_id": adapter_id})
            self._adapters[adapter_id] = adapter
            return adapter

    def adapter(self, adapter_id: str) -> CoreAdapter:
        with span(self.component, "adapter", adapter_id=adapter_id):
            try:
                return self._adapters[adapter_id]
            except KeyError as exc:
                raise CoreError("ADAPTER_MISSING", "adapter is not registered", {"adapter_id": adapter_id}) from exc

    def invoke(self, adapter_id: str, request: AdapterRequest) -> AdapterResponse:
        with span(
            self.component,
            "invoke",
            adapter_id=adapter_id,
            request_id=request.request_id,
            adapter_operation=request.operation,
        ):
            adapter = self.adapter(adapter_id)
            try:
                response = adapter.invoke(request)
            except CoreError:
                raise
            except Exception as exc:
                raise CoreError(
                    "ADAPTER_EXECUTION_FAILED",
                    "adapter raised an exception",
                    {
                        "adapter_id": adapter_id,
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                    },
                ) from exc
            if not isinstance(response, AdapterResponse):
                raise CoreError("ADAPTER_RESPONSE_INVALID", "adapter returned an invalid response")
            if response.request_id != request.request_id:
                raise CoreError(
                    "ADAPTER_CORRELATION_INVALID",
                    "adapter response does not match the request",
                    {"expected": request.request_id, "observed": response.request_id},
                )
            return response

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))
