"""Determiner-specific input and output contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Sequence

from acl_core.canonical import canonical_digest
from acl_core.diagnostics import emit, span

from acl_roles.common import RoleResponse, RoleStatus
from acl_roles.common.errors import RoleContractError

from .taxonomy import DeterminerTaxonomy


DETERMINER_INPUT_SCHEMA = "acl-determiner-input:v1"
DETERMINER_RESULT_SCHEMA = "acl-determiner-result:v1"


class ClassificationStatus(StrEnum):
    CLASSIFIED = "CLASSIFIED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DeterminerInput:
    request: Mapping[str, Any]
    taxonomy: DeterminerTaxonomy
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.request, Mapping) or not isinstance(self.metadata, Mapping):
            raise RoleContractError("DETERMINER_INPUT_INVALID", "request and metadata must be mappings")

    def to_objective(self) -> dict[str, Any]:
        return {
            "schema_version": DETERMINER_INPUT_SCHEMA,
            "request": dict(self.request),
            "taxonomy": self.taxonomy.to_dict(),
            "metadata": dict(self.metadata),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_objective())


@dataclass(frozen=True)
class DeterminerResult:
    role_status: RoleStatus
    classification: ClassificationStatus | None = None
    work_type: str | None = None
    complexity: str | None = None
    confidence: float | None = None
    reason_codes: tuple[str, ...] = ()
    notes: str | None = None
    questions: tuple[Mapping[str, Any], ...] = ()
    raw_payload: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DETERMINER_RESULT_SCHEMA,
            "role_status": str(self.role_status),
            "classification": None if self.classification is None else str(self.classification),
            "work_type": self.work_type,
            "complexity": self.complexity,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "notes": self.notes,
            "questions": [dict(item) for item in self.questions],
            "raw_payload": dict(self.raw_payload),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def parse_determiner_response(
    response: RoleResponse,
    taxonomy: DeterminerTaxonomy,
) -> DeterminerResult:
    with span(
        "roles.determiner",
        "parse_response",
        role_status=str(response.status),
        taxonomy_digest=taxonomy.digest(),
    ):
        return _parse_determiner_response(response, taxonomy)


def _parse_determiner_response(
    response: RoleResponse,
    taxonomy: DeterminerTaxonomy,
) -> DeterminerResult:
    payload = response.payload

    if response.status is RoleStatus.NEEDS_CLARIFICATION:
        questions = payload.get("questions")
        if not isinstance(questions, list) or not questions or any(not isinstance(item, Mapping) for item in questions):
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "clarification response requires one or more structured questions",
            )
        result = DeterminerResult(
            role_status=response.status,
            questions=tuple(dict(item) for item in questions),
            raw_payload=dict(payload),
        )
        _emit_result(result, taxonomy)
        return result

    if response.status is not RoleStatus.COMPLETE:
        result = DeterminerResult(
            role_status=response.status,
            notes=payload.get("notes") if isinstance(payload.get("notes"), str) else None,
            raw_payload=dict(payload),
        )
        _emit_result(result, taxonomy)
        return result

    schema = payload.get("schema_version")
    if schema != DETERMINER_RESULT_SCHEMA:
        raise RoleContractError(
            "DETERMINER_RESULT_INVALID",
            "completed Determiner response has an invalid result schema",
            {"observed_schema": schema},
        )

    try:
        classification = ClassificationStatus(payload["classification"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RoleContractError(
            "DETERMINER_RESULT_INVALID",
            "completed Determiner response has an invalid classification status",
        ) from exc

    work_type = payload.get("work_type")
    complexity = payload.get("complexity")
    confidence = payload.get("confidence")
    reason_codes_raw = payload.get("reason_codes", [])
    notes = payload.get("notes")

    if not isinstance(reason_codes_raw, list) or any(
        not isinstance(item, str) or not item.strip() for item in reason_codes_raw
    ):
        raise RoleContractError("DETERMINER_RESULT_INVALID", "reason_codes must be a list of nonblank strings")
    reason_codes = tuple(reason_codes_raw)
    if len(reason_codes) != len(set(reason_codes)):
        raise RoleContractError("DETERMINER_RESULT_INVALID", "reason_codes must be unique")
    if notes is not None and not isinstance(notes, str):
        raise RoleContractError("DETERMINER_RESULT_INVALID", "notes must be text when present")

    if classification is ClassificationStatus.CLASSIFIED:
        if not isinstance(work_type, str) or not taxonomy.contains_work_type(work_type):
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "classified result must use a configured work type",
                {"work_type": work_type, "allowed": list(taxonomy.work_type_ids)},
            )
        if complexity is not None and (
            not isinstance(complexity, str) or not taxonomy.contains_complexity(complexity)
        ):
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "complexity must use a configured complexity level",
                {"complexity": complexity, "allowed": list(taxonomy.complexity_levels)},
            )
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "classified result confidence must be a number from 0 through 1",
            )
        confidence = float(confidence)
    else:
        if work_type is not None or complexity is not None:
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "UNKNOWN classification must not claim work_type or complexity",
            )
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
                raise RoleContractError(
                    "DETERMINER_RESULT_INVALID",
                    "UNKNOWN confidence must be a number from 0 through 1 when present",
                )
            confidence = float(confidence)

    result = DeterminerResult(
        role_status=response.status,
        classification=classification,
        work_type=work_type,
        complexity=complexity,
        confidence=confidence,
        reason_codes=reason_codes,
        notes=notes,
        raw_payload=dict(payload),
    )
    _emit_result(result, taxonomy)
    return result


def _emit_result(result: DeterminerResult, taxonomy: DeterminerTaxonomy) -> None:
    emit(
        "INFO",
        "roles.determiner",
        "parse_result",
        "determiner_result_parsed",
        role_status=str(result.role_status),
        classification=None if result.classification is None else str(result.classification),
        work_type=result.work_type,
        complexity=result.complexity,
        confidence=result.confidence,
        reason_codes=list(result.reason_codes),
        question_count=len(result.questions),
        taxonomy_digest=taxonomy.digest(),
        result_digest=result.digest(),
    )


def validate_determiner_role_response(
    response: RoleResponse,
    *,
    instructions: Mapping[str, Any],
    profile_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    taxonomy_raw = instructions.get("taxonomy")
    if not isinstance(taxonomy_raw, Mapping):
        raise RoleContractError(
            "DETERMINER_TAXONOMY_MISSING",
            "Determiner profile instructions do not contain the configured taxonomy",
        )
    taxonomy = DeterminerTaxonomy.from_mapping(taxonomy_raw)
    result = parse_determiner_response(response, taxonomy)
    return {
        "contract": DETERMINER_RESULT_SCHEMA,
        "result_digest": result.digest(),
        "classification": None if result.classification is None else str(result.classification),
        "work_type": result.work_type,
        "complexity": result.complexity,
        "confidence": result.confidence,
        "question_count": len(result.questions),
        "taxonomy_digest": taxonomy.digest(),
    }
