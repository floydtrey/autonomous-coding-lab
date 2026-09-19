"""Registry for already-structured Controller actions.

This module does not inspect natural language or choose an action type. It only
routes an action type that a caller/role has already supplied.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Mapping

from acl_core import CoreIdentity
from acl_core.diagnostics import emit

from ..diagnostics import controller_span
from ..errors import ControllerError


@dataclass(frozen=True)
class ActionRequest:
    workflow_id: str
    action_type: str
    payload: Mapping[str, Any]
    role: str | None = None
    profile_id: str | None = None
    action_id: str = field(default_factory=lambda: CoreIdentity.new("action").value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "workflow_id": self.workflow_id,
            "action_type": self.action_type,
            "payload": dict(self.payload),
            "role": self.role,
            "profile_id": self.profile_id,
        }


@dataclass(frozen=True)
class ActionResponse:
    action_id: str
    status: str
    payload: Any = None
    reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "status": self.status,
            "payload": self.payload,
            "reference": self.reference,
            "metadata": dict(self.metadata),
        }


ActionHandler = Callable[[ActionRequest], ActionResponse]


class ActionRegistry:
    component = "controller.routing"

    def __init__(self) -> None:
        self._handlers: dict[str, ActionHandler] = {}

    def register(self, action_type: str, handler: ActionHandler) -> None:
        with controller_span("routing.register", action_type=action_type):
            _action_type(action_type)
            if not callable(handler):
                raise ControllerError("CONTROLLER_ACTION_HANDLER_INVALID", "action handler must be callable")
            existing = self._handlers.get(action_type)
            if existing is not None and existing is not handler:
                raise ControllerError(
                    "CONTROLLER_ACTION_CONFLICT",
                    "action type already has a different handler",
                    {"action_type": action_type},
                )
            self._handlers[action_type] = handler
            emit(
                "INFO",
                self.component,
                "register",
                "action_registered",
                action_type=action_type,
                handler=getattr(handler, "__qualname__", repr(handler)),
            )

    def handler(self, action_type: str) -> ActionHandler:
        with controller_span("routing.handler", action_type=action_type):
            _action_type(action_type)
            try:
                return self._handlers[action_type]
            except KeyError as exc:
                raise ControllerError(
                    "CONTROLLER_ACTION_UNREGISTERED",
                    "no handler is registered for the action type",
                    {"action_type": action_type},
                ) from exc

    def dispatch(self, request: ActionRequest) -> ActionResponse:
        with controller_span(
            "routing.dispatch",
            workflow_id=request.workflow_id,
            action_id=request.action_id,
            action_type=request.action_type,
            role=request.role,
            profile_id=request.profile_id,
        ):
            handler = self.handler(request.action_type)
            emit(
                "INFO",
                self.component,
                "dispatch",
                "action_dispatch_started",
                action_id=request.action_id,
                action_type=request.action_type,
                workflow_id=request.workflow_id,
                role=request.role,
                profile_id=request.profile_id,
            )
            try:
                response = handler(request)
            except ControllerError:
                raise
            except Exception as exc:
                raise ControllerError(
                    "CONTROLLER_ACTION_FAILED",
                    "action handler raised an exception",
                    {
                        "action_id": request.action_id,
                        "action_type": request.action_type,
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                    },
                ) from exc
            if not isinstance(response, ActionResponse):
                raise ControllerError(
                    "CONTROLLER_ACTION_RESPONSE_INVALID",
                    "action handler returned an invalid response",
                    {"action_id": request.action_id, "action_type": request.action_type},
                )
            if response.action_id != request.action_id:
                raise ControllerError(
                    "CONTROLLER_ACTION_CORRELATION_INVALID",
                    "action response does not match its request",
                    {"expected": request.action_id, "observed": response.action_id},
                )
            emit(
                "INFO",
                self.component,
                "dispatch",
                "action_dispatch_finished",
                action_id=request.action_id,
                action_type=request.action_type,
                workflow_id=request.workflow_id,
                response_status=response.status,
                reference=response.reference,
            )
            return response

    def action_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))


def _action_type(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ControllerError("CONTROLLER_ACTION_INVALID", "action type must be trimmed nonblank text")
    return value
