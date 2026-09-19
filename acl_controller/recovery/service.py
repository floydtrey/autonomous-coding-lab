"""Conservative stop/cancel/recovery for Controller workflows."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from acl_core import AdapterRequest, CoreIdentity, CoreServices
from acl_core.canonical import canonical_json
from acl_core.diagnostics import emit
from acl_core.errors import CoreError

from ..configuration import ProfileResolver
from ..diagnostics import controller_span
from ..errors import ControllerError
from ..models import TERMINAL_STATUSES, WorkflowRecord, WorkflowStatus, utc_now
from ..state import WorkflowStateService
from ..workflow import EngineReport, WorkflowEngine


class StopStatus(StrEnum):
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True)
class StopRecord:
    stop_id: str
    workflow_id: str
    requested_by: str
    active_attempt_id: str | None
    active_action: str | None
    active_role: str | None
    active_profile_id: str | None
    status: StopStatus = StopStatus.REQUESTED
    response: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    resolved_at: str | None = None

    @classmethod
    def create(cls, workflow: WorkflowRecord, requested_by: str) -> "StopRecord":
        if not isinstance(requested_by, str) or not requested_by.strip():
            raise ControllerError("CONTROLLER_STOP_INVALID", "requested_by is required")
        return cls(
            stop_id=CoreIdentity.new("stop").value,
            workflow_id=workflow.workflow_id,
            requested_by=requested_by,
            active_attempt_id=workflow.active_attempt_id,
            active_action=workflow.active_action,
            active_role=workflow.active_role,
            active_profile_id=workflow.active_profile_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "acl-controller-stop:v1",
            "stop_id": self.stop_id,
            "workflow_id": self.workflow_id,
            "requested_by": self.requested_by,
            "active_attempt_id": self.active_attempt_id,
            "active_action": self.active_action,
            "active_role": self.active_role,
            "active_profile_id": self.active_profile_id,
            "status": str(self.status),
            "response": dict(self.response),
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "StopRecord":
        if not isinstance(value, Mapping) or value.get("schema_version") != "acl-controller-stop:v1":
            raise ControllerError("CONTROLLER_STOP_INVALID", "stop record schema is invalid")
        try:
            return cls(
                stop_id=value["stop_id"],
                workflow_id=value["workflow_id"],
                requested_by=value["requested_by"],
                active_attempt_id=value.get("active_attempt_id"),
                active_action=value.get("active_action"),
                active_role=value.get("active_role"),
                active_profile_id=value.get("active_profile_id"),
                status=StopStatus(value["status"]),
                response=dict(value.get("response", {})),
                created_at=value["created_at"],
                resolved_at=value.get("resolved_at"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError("CONTROLLER_STOP_INVALID", "stop record is malformed") from exc


class JsonStopStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._lock = RLock()

    def create(self, record: StopRecord) -> StopRecord:
        with controller_span("stop_store.create", workflow_id=record.workflow_id, stop_id=record.stop_id):
            path = self._path(record.stop_id)
            with self._lock:
                if path.exists():
                    raise ControllerError("CONTROLLER_STOP_EXISTS", "stop request already exists")
                self._write(path, record)
            return record

    def read(self, stop_id: str) -> StopRecord:
        with controller_span("stop_store.read", stop_id=stop_id):
            try:
                return StopRecord.from_mapping(json.loads(self._path(stop_id).read_text(encoding="utf-8")))
            except FileNotFoundError as exc:
                raise ControllerError("CONTROLLER_STOP_MISSING", "stop request does not exist", {"stop_id": stop_id}) from exc
            except (OSError, json.JSONDecodeError) as exc:
                raise ControllerError("CONTROLLER_STOP_READ_FAILED", "stop request could not be read", {"stop_id": stop_id}) from exc

    def save(self, record: StopRecord) -> StopRecord:
        with controller_span("stop_store.save", workflow_id=record.workflow_id, stop_id=record.stop_id, stop_status=str(record.status)):
            path = self._path(record.stop_id)
            with self._lock:
                self._write(path, record)
            return record

    def for_workflow(self, workflow_id: str) -> tuple[StopRecord, ...]:
        directory = self.root / "stops"
        if not directory.exists():
            return ()
        records = []
        for path in sorted(directory.glob("stop_*.json")):
            try:
                record = StopRecord.from_mapping(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, ControllerError) as exc:
                raise ControllerError(
                    "CONTROLLER_STOP_READ_FAILED",
                    "one or more stop records are unreadable",
                    {"path": str(path)},
                ) from exc
            if record.workflow_id == workflow_id:
                records.append(record)
        return tuple(records)

    def latest_for_workflow(self, workflow_id: str) -> StopRecord | None:
        records = self.for_workflow(workflow_id)
        return records[-1] if records else None

    def _path(self, stop_id: str) -> Path:
        if not isinstance(stop_id, str) or not stop_id.startswith("stop:"):
            raise ControllerError("CONTROLLER_STOP_INVALID", "stop ID is invalid")
        return self.root / "stops" / f"{stop_id.replace(':', '_')}.json"

    @staticmethod
    def _write(path: Path, record: StopRecord) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        try:
            temp.write_text(canonical_json(record.to_dict()) + "\n", encoding="utf-8")
            os.replace(temp, path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ControllerError("CONTROLLER_STOP_WRITE_FAILED", "stop request could not be persisted") from exc


class RecoveryService:
    component = "controller.recovery"

    def __init__(
        self,
        *,
        core: CoreServices,
        state: WorkflowStateService,
        profiles: ProfileResolver,
        engine: WorkflowEngine,
        stops: JsonStopStore,
    ) -> None:
        self.core = core
        self.state = state
        self.profiles = profiles
        self.engine = engine
        self.stops = stops

    def request_stop(self, workflow_id: str, *, requested_by: str) -> StopRecord:
        with controller_span("recovery.request_stop", workflow_id=workflow_id, requested_by=requested_by):
            workflow = self.state.read(workflow_id)
            latest = self.stops.latest_for_workflow(workflow_id)
            if (
                latest is not None
                and latest.status is StopStatus.REQUESTED
                and latest.active_attempt_id == workflow.active_attempt_id
            ):
                return latest

            stop = self.stops.create(StopRecord.create(workflow, requested_by))
            emit(
                "INFO",
                self.component,
                "request_stop",
                "stop_requested",
                workflow_id=workflow_id,
                stop_id=stop.stop_id,
                requested_by=requested_by,
                workflow_status=str(workflow.status),
                active_attempt_id=workflow.active_attempt_id,
                active_action=workflow.active_action,
                active_role=workflow.active_role,
                active_profile_id=workflow.active_profile_id,
            )

            if workflow.status in TERMINAL_STATUSES:
                return self._resolve_stop(stop, StopStatus.CONFIRMED, {"reason": "workflow_already_terminal"})

            if workflow.active_attempt_id is None:
                self.state.transition(
                    workflow_id,
                    WorkflowStatus.CANCELLED,
                    active_action=None,
                    active_role=None,
                    active_profile_id=None,
                    active_attempt_id=None,
                    waiting_for=None,
                    blocker=None,
                )
                return self._resolve_stop(stop, StopStatus.CONFIRMED, {"reason": "no_active_execution"})

            if workflow.active_role is None or workflow.active_profile_id is None:
                self._block_uncertain(
                    workflow,
                    code="ACTION_STOP_UNCERTAIN",
                    message="active non-role action has no generic cancellation protocol",
                    stop_id=stop.stop_id,
                )
                return self._resolve_stop(
                    stop,
                    StopStatus.UNCERTAIN,
                    {"reason": "non_role_action_without_cancel_protocol"},
                )

            return self._cancel_role(workflow, stop)

    def recover(self, workflow_id: str) -> EngineReport | WorkflowRecord:
        with controller_span("recovery.recover", workflow_id=workflow_id):
            workflow = self.state.read(workflow_id)
            emit(
                "INFO",
                self.component,
                "recover",
                "recovery_started",
                workflow_id=workflow_id,
                status=str(workflow.status),
                stage=workflow.stage,
                active_attempt_id=workflow.active_attempt_id,
                active_action=workflow.active_action,
                active_role=workflow.active_role,
                active_profile_id=workflow.active_profile_id,
                waiting_for=workflow.waiting_for,
            )

            if workflow.status in TERMINAL_STATUSES:
                return workflow
            if workflow.status is WorkflowStatus.WAITING and workflow.waiting_for and not workflow.waiting_for.startswith("stop:"):
                return workflow
            if workflow.status in {WorkflowStatus.READY, WorkflowStatus.BLOCKED, WorkflowStatus.NEW}:
                return workflow
            if workflow.active_attempt_id is None:
                self._block_uncertain(
                    workflow,
                    code="RECOVERY_ACTIVE_IDENTITY_MISSING",
                    message="running or stop-waiting workflow has no active execution identity",
                )
                return self.state.read(workflow_id)
            if workflow.active_role is None or workflow.active_profile_id is None:
                self._block_uncertain(
                    workflow,
                    code="ACTION_RECOVERY_UNSUPPORTED",
                    message="active non-role action has no generic status protocol",
                )
                return self.state.read(workflow_id)

            profile = self.profiles.profile(workflow.active_profile_id)
            try:
                response = self._invoke_role_control(
                    profile.adapter_id,
                    "role.status",
                    workflow,
                    {
                        "workflow_id": workflow.workflow_id,
                        "attempt_id": workflow.active_attempt_id,
                        "role": workflow.active_role,
                        "profile_id": workflow.active_profile_id,
                    },
                )
            except (ControllerError, CoreError) as exc:
                if self._can_rerun_unqueryable_attempt(profile.adapter_id, exc):
                    prior_attempt_id = workflow.active_attempt_id
                    recovered = self.state.transition(
                        workflow_id,
                        WorkflowStatus.READY,
                        active_action=None,
                        active_role=None,
                        active_profile_id=None,
                        active_attempt_id=None,
                        waiting_for=None,
                        blocker=None,
                    )
                    emit(
                        "INFO",
                        self.component,
                        "recover",
                        "unqueryable_attempt_released_for_rerun",
                        workflow_id=workflow_id,
                        adapter_id=profile.adapter_id,
                        prior_attempt_id=prior_attempt_id,
                        stage=workflow.stage,
                    )
                    return recovered
                self._block_uncertain(
                    workflow,
                    code="RECOVERY_STATUS_QUERY_FAILED",
                    message="active role status could not be confirmed",
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                )
                return self.state.read(workflow_id)
            state = response.get("state")
            emit(
                "INFO",
                self.component,
                "recover",
                "role_status_observed",
                workflow_id=workflow_id,
                attempt_id=workflow.active_attempt_id,
                adapter_id=profile.adapter_id,
                observed_state=state,
            )

            if state == "running":
                return workflow
            if state in {"cancelled", "stopped"}:
                self.state.transition(
                    workflow_id,
                    WorkflowStatus.CANCELLED,
                    active_action=None,
                    active_role=None,
                    active_profile_id=None,
                    active_attempt_id=None,
                    waiting_for=None,
                    blocker=None,
                )
                latest = self.stops.latest_for_workflow(workflow_id)
                if latest is not None and latest.status is StopStatus.REQUESTED:
                    self._resolve_stop(latest, StopStatus.CONFIRMED, response)
                return self.state.read(workflow_id)
            if state == "absent":
                latest = self.stops.latest_for_workflow(workflow_id)
                if latest is not None and latest.status is StopStatus.REQUESTED:
                    self.state.transition(
                        workflow_id,
                        WorkflowStatus.CANCELLED,
                        active_action=None,
                        active_role=None,
                        active_profile_id=None,
                        active_attempt_id=None,
                        waiting_for=None,
                        blocker=None,
                    )
                    self._resolve_stop(latest, StopStatus.CONFIRMED, response)
                else:
                    self._block_uncertain(
                        workflow,
                        code="RECOVERY_ACTIVE_ATTEMPT_ABSENT",
                        message="active role execution is absent without terminal result evidence",
                    )
                return self.state.read(workflow_id)
            if state == "complete":
                result = response.get("result")
                if not isinstance(result, Mapping):
                    self._block_uncertain(
                        workflow,
                        code="RECOVERY_RESULT_MISSING",
                        message="adapter reports completion without a recoverable structured result",
                    )
                    return self.state.read(workflow_id)
                return self.engine.consume_recovered_role_response(
                    workflow_id,
                    response_payload=result,
                )
            if state == "failed":
                result = response.get("result")
                if isinstance(result, Mapping):
                    return self.engine.consume_recovered_role_response(
                        workflow_id,
                        response_payload=result,
                    )
                self.state.transition(
                    workflow_id,
                    WorkflowStatus.FAILED,
                    active_action=None,
                    active_role=None,
                    active_profile_id=None,
                    active_attempt_id=None,
                    waiting_for=None,
                    blocker={
                        "code": "RECOVERED_ROLE_FAILED",
                        "attempt_id": workflow.active_attempt_id,
                        "adapter_state": state,
                    },
                )
                return self.state.read(workflow_id)

            self._block_uncertain(
                workflow,
                code="RECOVERY_STATUS_UNKNOWN",
                message="adapter returned an unsupported or unknown recovery state",
                observed_state=state,
            )
            return self.state.read(workflow_id)

    def _cancel_role(self, workflow: WorkflowRecord, stop: StopRecord) -> StopRecord:
        profile = self.profiles.profile(workflow.active_profile_id or "")
        try:
            response = self._invoke_role_control(
                profile.adapter_id,
                "role.cancel",
                workflow,
                {
                    "workflow_id": workflow.workflow_id,
                    "attempt_id": workflow.active_attempt_id,
                    "role": workflow.active_role,
                    "profile_id": workflow.active_profile_id,
                    "stop_id": stop.stop_id,
                },
            )
        except (ControllerError, CoreError) as exc:
            self._block_uncertain(
                workflow,
                code="STOP_ADAPTER_FAILED",
                message="role cancellation could not be confirmed",
                stop_id=stop.stop_id,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )
            return self._resolve_stop(
                stop,
                StopStatus.UNCERTAIN,
                {"exception_type": type(exc).__name__, "exception_message": str(exc)},
            )

        state = response.get("state")
        emit(
            "INFO",
            self.component,
            "request_stop",
            "role_cancel_response",
            workflow_id=workflow.workflow_id,
            stop_id=stop.stop_id,
            attempt_id=workflow.active_attempt_id,
            adapter_id=profile.adapter_id,
            observed_state=state,
            response=response,
        )
        if state in {"cancelled", "stopped", "absent"}:
            self.state.transition(
                workflow.workflow_id,
                WorkflowStatus.CANCELLED,
                active_action=None,
                active_role=None,
                active_profile_id=None,
                active_attempt_id=None,
                waiting_for=None,
                blocker=None,
            )
            return self._resolve_stop(stop, StopStatus.CONFIRMED, response)
        if state in {"requested", "running"}:
            self.state.transition(
                workflow.workflow_id,
                WorkflowStatus.WAITING,
                waiting_for=f"stop:{stop.stop_id}",
                blocker=None,
            )
            pending = replace(stop, response=dict(response))
            self.stops.save(pending)
            return pending
        self._block_uncertain(
            workflow,
            code="STOP_STATUS_UNKNOWN",
            message="role cancellation returned an unsupported state",
            stop_id=stop.stop_id,
            observed_state=state,
        )
        return self._resolve_stop(stop, StopStatus.UNCERTAIN, response)

    def _can_rerun_unqueryable_attempt(
        self,
        adapter_id: str,
        exc: BaseException,
    ) -> bool:
        if not isinstance(exc, ControllerError) or exc.code != "CONTROLLER_RECOVERY_ADAPTER_FAILED":
            return False
        details = exc.details if isinstance(exc.details, Mapping) else {}
        adapter_error = details.get("error")
        if not isinstance(adapter_error, Mapping) or adapter_error.get("code") != "ADAPTER_OPERATION_UNSUPPORTED":
            return False

        adapter = self.core.adapters.adapter(adapter_id)
        capabilities = getattr(adapter, "recovery_capabilities", {})
        if callable(capabilities):
            capabilities = capabilities()
        if not isinstance(capabilities, Mapping):
            return False
        return capabilities.get("interrupted_attempt_policy") == "rerun_if_unqueryable"

    def _invoke_role_control(
        self,
        adapter_id: str,
        operation: str,
        workflow: WorkflowRecord,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        request = AdapterRequest(
            operation=operation,
            payload=dict(payload),
            metadata={
                "workflow_id": workflow.workflow_id,
                "attempt_id": workflow.active_attempt_id,
                "role": workflow.active_role,
                "profile_id": workflow.active_profile_id,
                "grant_id": workflow.authority_grant_id,
            },
        )
        response = self.core.adapters.invoke(adapter_id, request)
        if not response.ok:
            raise ControllerError(
                "CONTROLLER_RECOVERY_ADAPTER_FAILED",
                "role control adapter returned failure",
                {
                    "adapter_id": adapter_id,
                    "operation": operation,
                    "error": dict(response.error or {}),
                },
            )
        return self.core.normalization.mapping(response.payload)

    def _resolve_stop(
        self,
        stop: StopRecord,
        status: StopStatus,
        response: Mapping[str, Any],
    ) -> StopRecord:
        resolved = replace(
            stop,
            status=status,
            response=dict(response),
            resolved_at=utc_now(),
        )
        self.stops.save(resolved)
        emit(
            "INFO",
            self.component,
            "resolve_stop",
            "stop_resolved",
            workflow_id=stop.workflow_id,
            stop_id=stop.stop_id,
            stop_status=str(status),
            response=dict(response),
        )
        return resolved

    def _block_uncertain(
        self,
        workflow: WorkflowRecord,
        *,
        code: str,
        message: str,
        **details: Any,
    ) -> None:
        self.state.transition(
            workflow.workflow_id,
            WorkflowStatus.BLOCKED,
            waiting_for=None,
            blocker={
                "code": code,
                "message": message,
                "active_attempt_id": workflow.active_attempt_id,
                "active_action": workflow.active_action,
                "active_role": workflow.active_role,
                "active_profile_id": workflow.active_profile_id,
                **details,
            },
        )
        emit(
            "ERROR",
            self.component,
            "block_uncertain",
            "recovery_uncertain",
            workflow_id=workflow.workflow_id,
            code=code,
            message=message,
            active_attempt_id=workflow.active_attempt_id,
            active_action=workflow.active_action,
            active_role=workflow.active_role,
            active_profile_id=workflow.active_profile_id,
            **details,
        )
