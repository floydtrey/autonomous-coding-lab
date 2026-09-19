"""Generic Controller workflow contracts.

These records contain orchestration state only. Role-specific payloads remain
opaque references or mappings owned by the role contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Mapping

from acl_core import CoreIdentity

from .errors import ControllerError


class WorkflowStatus(StrEnum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATUSES = frozenset({
    WorkflowStatus.COMPLETE,
    WorkflowStatus.FAILED,
    WorkflowStatus.CANCELLED,
})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class RequestRecord:
    request_id: str
    kind: str
    payload: Mapping[str, Any]
    requester: str | None = None
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        kind: str,
        payload: Mapping[str, Any],
        *,
        requester: str | None = None,
    ) -> "RequestRecord":
        _text(kind, "request kind")
        if not isinstance(payload, Mapping):
            raise ControllerError("CONTROLLER_REQUEST_INVALID", "request payload must be a mapping")
        return cls(
            request_id=CoreIdentity.new("request").value,
            kind=kind,
            payload=dict(payload),
            requester=requester,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "kind": self.kind,
            "payload": dict(self.payload),
            "requester": self.requester,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ResultReference:
    result_id: str
    result_type: str
    producer: str
    reference: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "result_type": self.result_type,
            "producer": self.producer,
            "reference": self.reference,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WorkflowRecord:
    workflow_id: str
    request: RequestRecord
    status: WorkflowStatus
    stage: str
    program_id: str | None = None
    active_action: str | None = None
    active_role: str | None = None
    active_profile_id: str | None = None
    active_attempt_id: str | None = None
    authority_grant_id: str | None = None
    retry_count: int = 0
    waiting_for: str | None = None
    blocker: Mapping[str, Any] | None = None
    result_references: tuple[ResultReference, ...] = ()
    generation: int = 1
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def create(cls, request: RequestRecord) -> "WorkflowRecord":
        return cls(
            workflow_id=CoreIdentity.new("workflow").value,
            request=request,
            status=WorkflowStatus.NEW,
            stage="intake",
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = str(self.status)
        value["request"] = self.request.to_dict()
        value["result_references"] = [item.to_dict() for item in self.result_references]
        value["blocker"] = dict(self.blocker) if self.blocker is not None else None
        return value

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkflowRecord":
        if not isinstance(value, Mapping):
            raise ControllerError("CONTROLLER_STATE_INVALID", "workflow record must be a mapping")
        try:
            request_raw = value["request"]
            request = RequestRecord(
                request_id=request_raw["request_id"],
                kind=request_raw["kind"],
                payload=dict(request_raw["payload"]),
                requester=request_raw.get("requester"),
                created_at=request_raw["created_at"],
            )
            results = tuple(
                ResultReference(
                    result_id=item["result_id"],
                    result_type=item["result_type"],
                    producer=item["producer"],
                    reference=item["reference"],
                    metadata=dict(item.get("metadata", {})),
                )
                for item in value.get("result_references", [])
            )
            return cls(
                workflow_id=value["workflow_id"],
                request=request,
                status=WorkflowStatus(value["status"]),
                stage=value["stage"],
                program_id=value.get("program_id"),
                active_action=value.get("active_action"),
                active_role=value.get("active_role"),
                active_profile_id=value.get("active_profile_id"),
                active_attempt_id=value.get("active_attempt_id"),
                authority_grant_id=value.get("authority_grant_id"),
                retry_count=int(value.get("retry_count", 0)),
                waiting_for=value.get("waiting_for"),
                blocker=dict(value["blocker"]) if value.get("blocker") is not None else None,
                result_references=results,
                generation=int(value.get("generation", 1)),
                created_at=value["created_at"],
                updated_at=value["updated_at"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ControllerError("CONTROLLER_STATE_INVALID", "workflow record fields are invalid") from exc

    def evolved(self, **changes: Any) -> "WorkflowRecord":
        return replace(
            self,
            **changes,
            generation=self.generation + 1,
            updated_at=utc_now(),
        )


@dataclass(frozen=True)
class ControllerStatus:
    workflow: WorkflowRecord

    def to_dict(self) -> dict[str, Any]:
        return self.workflow.to_dict()


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ControllerError("CONTROLLER_REQUEST_INVALID", f"{label} must be trimmed nonblank text")
    return value
