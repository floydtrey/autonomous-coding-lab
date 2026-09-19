"""Worker V1 semantic contract.

Worker executes exactly one accepted Planner Pass. It may report work ready for
review, request continuation, request Planner guidance, or report a blocker.
Worker never approves its own Pass and never marks Planner state complete.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Sequence

from acl_core.canonical import canonical_digest
from acl_roles.common import RoleResponse, RoleStatus
from acl_roles.common.errors import RoleContractError
from acl_roles.planner import PassSpec


WORKER_INPUT_SCHEMA = "acl-worker-input:v1"
WORKER_RESULT_SCHEMA = "acl-worker-result:v1"


class WorkerOutcome(StrEnum):
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    NEEDS_CONTINUATION = "NEEDS_CONTINUATION"
    NEEDS_PLANNER = "NEEDS_PLANNER"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class WorkerEvidence:
    kind: str
    description: str
    reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _text(self.kind, "evidence kind")
        _text(self.description, "evidence description")
        if self.reference is not None:
            _text(self.reference, "evidence reference")
        if not isinstance(self.metadata, Mapping):
            raise RoleContractError(
                "WORKER_RESULT_INVALID",
                "evidence metadata must be a mapping",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "description": self.description,
            "reference": self.reference,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkerEvidence":
        value = _mapping(value, "worker evidence")
        return cls(
            kind=value.get("kind"),
            description=value.get("description"),
            reference=value.get("reference"),
            metadata=_mapping(value.get("metadata", {}), "evidence metadata"),
        )


@dataclass(frozen=True)
class WorkerPlannerRequest:
    question: str
    reason: str
    current_state_summary: str
    task_id: str | None = None
    relevant_reference_ids: tuple[str, ...] = ()
    relevant_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.question, "Planner question")
        _text(self.reason, "Planner question reason")
        _text(self.current_state_summary, "current_state_summary")
        if self.task_id is not None:
            _text(self.task_id, "task_id")
        object.__setattr__(
            self,
            "relevant_reference_ids",
            _text_tuple(self.relevant_reference_ids, "relevant_reference_ids"),
        )
        object.__setattr__(
            self,
            "relevant_evidence",
            _text_tuple(self.relevant_evidence, "relevant_evidence"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "reason": self.reason,
            "current_state_summary": self.current_state_summary,
            "task_id": self.task_id,
            "relevant_reference_ids": list(self.relevant_reference_ids),
            "relevant_evidence": list(self.relevant_evidence),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkerPlannerRequest":
        value = _mapping(value, "Planner request")
        return cls(
            question=value.get("question"),
            reason=value.get("reason"),
            current_state_summary=value.get("current_state_summary"),
            task_id=value.get("task_id"),
            relevant_reference_ids=_text_tuple(
                value.get("relevant_reference_ids", []),
                "relevant_reference_ids",
            ),
            relevant_evidence=_text_tuple(
                value.get("relevant_evidence", []),
                "relevant_evidence",
            ),
        )


@dataclass(frozen=True)
class WorkerInput:
    plan_id: str
    plan_version: int
    semantic_plan_digest: str
    pass_id: str
    stage_id: str | None
    pass_spec: PassSpec
    plan_context: Mapping[str, Any]
    completed_passes: tuple[str, ...] = ()
    prior_worker_results: tuple[Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _text(self.plan_id, "plan_id")
        if isinstance(self.plan_version, bool) or not isinstance(self.plan_version, int) or self.plan_version < 1:
            raise RoleContractError("WORKER_INPUT_INVALID", "plan_version must be positive")
        _text(self.semantic_plan_digest, "semantic_plan_digest")
        _text(self.pass_id, "pass_id")
        if self.stage_id is not None:
            _text(self.stage_id, "stage_id")
        if not isinstance(self.pass_spec, PassSpec):
            raise RoleContractError("WORKER_INPUT_INVALID", "pass_spec must be PassSpec")
        if self.pass_spec.pass_id != self.pass_id:
            raise RoleContractError(
                "WORKER_INPUT_INVALID",
                "pass_spec identity differs from pass_id",
            )
        if not isinstance(self.plan_context, Mapping):
            raise RoleContractError("WORKER_INPUT_INVALID", "plan_context must be a mapping")
        object.__setattr__(
            self,
            "completed_passes",
            _text_tuple(self.completed_passes, "completed_passes"),
        )
        if not isinstance(self.prior_worker_results, tuple) or any(
            not isinstance(item, Mapping) for item in self.prior_worker_results
        ):
            raise RoleContractError(
                "WORKER_INPUT_INVALID",
                "prior_worker_results must contain mappings",
            )
        if not isinstance(self.metadata, Mapping):
            raise RoleContractError("WORKER_INPUT_INVALID", "metadata must be a mapping")

    def to_objective(self) -> dict[str, Any]:
        return {
            "schema_version": WORKER_INPUT_SCHEMA,
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "semantic_plan_digest": self.semantic_plan_digest,
            "pass_id": self.pass_id,
            "stage_id": self.stage_id,
            "pass": self.pass_spec.to_dict(),
            "plan_context": dict(self.plan_context),
            "completed_passes": list(self.completed_passes),
            "prior_worker_results": [dict(item) for item in self.prior_worker_results],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkerInput":
        value = _mapping(value, "worker input")
        if value.get("schema_version") != WORKER_INPUT_SCHEMA:
            raise RoleContractError("WORKER_INPUT_INVALID", "worker input schema is invalid")
        prior = value.get("prior_worker_results", [])
        if not isinstance(prior, list):
            raise RoleContractError(
                "WORKER_INPUT_INVALID",
                "prior_worker_results must be a list",
            )
        return cls(
            plan_id=value.get("plan_id"),
            plan_version=value.get("plan_version"),
            semantic_plan_digest=value.get("semantic_plan_digest"),
            pass_id=value.get("pass_id"),
            stage_id=value.get("stage_id"),
            pass_spec=PassSpec.from_mapping(value.get("pass")),
            plan_context=_mapping(value.get("plan_context"), "plan_context"),
            completed_passes=_text_tuple(
                value.get("completed_passes", []),
                "completed_passes",
            ),
            prior_worker_results=tuple(
                _mapping(item, "prior worker result") for item in prior
            ),
            metadata=_mapping(value.get("metadata", {}), "metadata"),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_objective())


@dataclass(frozen=True)
class WorkerResult:
    plan_id: str
    plan_version: int
    pass_id: str
    outcome: WorkerOutcome
    summary: str
    completed_task_ids: tuple[str, ...] = ()
    changed_paths: tuple[str, ...] = ()
    evidence: tuple[WorkerEvidence, ...] = ()
    planner_request: WorkerPlannerRequest | None = None
    continuation_reason: str | None = None
    blocker: str | None = None
    assumptions: tuple[str, ...] = ()
    unresolved_risks: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        _text(self.plan_id, "plan_id")
        if isinstance(self.plan_version, bool) or not isinstance(self.plan_version, int) or self.plan_version < 1:
            raise RoleContractError("WORKER_RESULT_INVALID", "plan_version must be positive")
        _text(self.pass_id, "pass_id")
        if not isinstance(self.outcome, WorkerOutcome):
            raise RoleContractError("WORKER_RESULT_INVALID", "outcome is invalid")
        _text(self.summary, "summary")
        object.__setattr__(
            self,
            "completed_task_ids",
            _text_tuple(self.completed_task_ids, "completed_task_ids"),
        )
        object.__setattr__(
            self,
            "changed_paths",
            _text_tuple(self.changed_paths, "changed_paths"),
        )
        if not isinstance(self.evidence, tuple) or any(
            not isinstance(item, WorkerEvidence) for item in self.evidence
        ):
            raise RoleContractError(
                "WORKER_RESULT_INVALID",
                "evidence must contain WorkerEvidence values",
            )
        object.__setattr__(self, "assumptions", _text_tuple(self.assumptions, "assumptions"))
        object.__setattr__(
            self,
            "unresolved_risks",
            _text_tuple(self.unresolved_risks, "unresolved_risks"),
        )
        if self.notes is not None:
            _text(self.notes, "notes")

        if self.outcome is WorkerOutcome.READY_FOR_REVIEW:
            if not self.evidence:
                raise RoleContractError(
                    "WORKER_EVIDENCE_MISSING",
                    "READY_FOR_REVIEW requires evidence for Reviewer",
                )
            if self.planner_request is not None or self.continuation_reason is not None or self.blocker is not None:
                raise RoleContractError(
                    "WORKER_RESULT_INVALID",
                    "READY_FOR_REVIEW cannot include Planner/continuation/blocker state",
                )
        elif self.outcome is WorkerOutcome.NEEDS_PLANNER:
            if not isinstance(self.planner_request, WorkerPlannerRequest):
                raise RoleContractError(
                    "WORKER_PLANNER_REQUEST_MISSING",
                    "NEEDS_PLANNER requires planner_request",
                )
            if self.continuation_reason is not None or self.blocker is not None:
                raise RoleContractError(
                    "WORKER_RESULT_INVALID",
                    "NEEDS_PLANNER cannot include continuation_reason or blocker",
                )
        elif self.outcome is WorkerOutcome.NEEDS_CONTINUATION:
            _text(self.continuation_reason, "continuation_reason")
            if self.planner_request is not None or self.blocker is not None:
                raise RoleContractError(
                    "WORKER_RESULT_INVALID",
                    "NEEDS_CONTINUATION cannot include planner_request or blocker",
                )
        elif self.outcome in {WorkerOutcome.BLOCKED, WorkerOutcome.FAILED}:
            _text(self.blocker, "blocker")
            if self.planner_request is not None or self.continuation_reason is not None:
                raise RoleContractError(
                    "WORKER_RESULT_INVALID",
                    "blocked/failed result cannot include Planner or continuation state",
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": WORKER_RESULT_SCHEMA,
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "pass_id": self.pass_id,
            "outcome": str(self.outcome),
            "summary": self.summary,
            "completed_task_ids": list(self.completed_task_ids),
            "changed_paths": list(self.changed_paths),
            "evidence": [item.to_dict() for item in self.evidence],
            "planner_request": None if self.planner_request is None else self.planner_request.to_dict(),
            "continuation_reason": self.continuation_reason,
            "blocker": self.blocker,
            "assumptions": list(self.assumptions),
            "unresolved_risks": list(self.unresolved_risks),
            "notes": self.notes,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkerResult":
        value = _mapping(value, "worker result")
        if value.get("schema_version") != WORKER_RESULT_SCHEMA:
            raise RoleContractError("WORKER_RESULT_INVALID", "worker result schema is invalid")
        evidence_raw = value.get("evidence", [])
        if not isinstance(evidence_raw, list):
            raise RoleContractError("WORKER_RESULT_INVALID", "evidence must be a list")
        planner_request_raw = value.get("planner_request")
        try:
            outcome = WorkerOutcome(value.get("outcome"))
        except (TypeError, ValueError) as exc:
            raise RoleContractError("WORKER_RESULT_INVALID", "outcome is invalid") from exc
        return cls(
            plan_id=value.get("plan_id"),
            plan_version=value.get("plan_version"),
            pass_id=value.get("pass_id"),
            outcome=outcome,
            summary=value.get("summary"),
            completed_task_ids=_text_tuple(
                value.get("completed_task_ids", []),
                "completed_task_ids",
            ),
            changed_paths=_text_tuple(value.get("changed_paths", []), "changed_paths"),
            evidence=tuple(WorkerEvidence.from_mapping(item) for item in evidence_raw),
            planner_request=(
                None
                if planner_request_raw is None
                else WorkerPlannerRequest.from_mapping(planner_request_raw)
            ),
            continuation_reason=value.get("continuation_reason"),
            blocker=value.get("blocker"),
            assumptions=_text_tuple(value.get("assumptions", []), "assumptions"),
            unresolved_risks=_text_tuple(
                value.get("unresolved_risks", []),
                "unresolved_risks",
            ),
            notes=value.get("notes"),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def parse_worker_role_response(response: RoleResponse) -> WorkerResult:
    if not isinstance(response, RoleResponse):
        raise RoleContractError("WORKER_RESULT_INVALID", "response must be RoleResponse")
    return WorkerResult.from_mapping(response.payload)


def expected_role_status(outcome: WorkerOutcome) -> RoleStatus:
    return {
        WorkerOutcome.READY_FOR_REVIEW: RoleStatus.COMPLETE,
        WorkerOutcome.NEEDS_CONTINUATION: RoleStatus.NEEDS_CONTINUATION,
        WorkerOutcome.NEEDS_PLANNER: RoleStatus.NEEDS_CLARIFICATION,
        WorkerOutcome.BLOCKED: RoleStatus.BLOCKED,
        WorkerOutcome.FAILED: RoleStatus.FAILED,
    }[outcome]


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RoleContractError("WORKER_CONTRACT_INVALID", f"{label} must be a mapping")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise RoleContractError(
            "WORKER_CONTRACT_INVALID",
            f"{label} must be trimmed nonblank text",
        )
    return value


def _text_tuple(value: Any, label: str) -> tuple[str, ...]:
    if isinstance(value, list):
        value = tuple(value)
    if not isinstance(value, tuple) or any(
        not isinstance(item, str) or not item.strip() or item != item.strip()
        for item in value
    ):
        raise RoleContractError(
            "WORKER_CONTRACT_INVALID",
            f"{label} must contain trimmed nonblank text",
        )
    if len(value) != len(set(value)):
        raise RoleContractError(
            "WORKER_CONTRACT_INVALID",
            f"{label} must not contain duplicates",
        )
    return value
