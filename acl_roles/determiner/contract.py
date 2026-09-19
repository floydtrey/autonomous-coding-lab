"""Determiner-specific input and output contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from acl_core.canonical import canonical_digest
from acl_core.diagnostics import emit, span

from acl_roles.common import RoleResponse, RoleStatus
from acl_roles.common.errors import RoleContractError

from .taxonomy import DeterminerTaxonomy


DETERMINER_INPUT_SCHEMA = "acl-determiner-input:v2"
DETERMINER_RESULT_SCHEMA = "acl-determiner-result:v2"
_LEGACY_RESULT_SCHEMA = "acl-determiner-result:v1"


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
            raise RoleContractError(
                "DETERMINER_INPUT_INVALID",
                "request and metadata must be mappings",
            )

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
    work_type_id: str | None = None
    work_type_label: str | None = None
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
            "work_type_id": self.work_type_id,
            "work_type_label": self.work_type_label,
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


def _normalize_clarification_options(
    options: Any,
    taxonomy: DeterminerTaxonomy,
) -> list[dict[str, Any]]:
    if options is None:
        return []
    if not isinstance(options, list) or not options:
        raise RoleContractError(
            "DETERMINER_RESULT_INVALID",
            "clarification options must be a nonempty list when present",
        )

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in options:
        source_value = None
        if isinstance(item, str):
            source_value = item
        elif isinstance(item, Mapping):
            for key in ("work_type_id", "work_type", "id", "label"):
                if item.get(key) is not None:
                    source_value = item.get(key)
                    break
        else:
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "clarification options must contain text or mappings",
            )

        work_type_id = taxonomy.resolve_id(source_value)
        if work_type_id is None:
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "clarification option is not a configured work type",
                {"option": source_value},
            )
        if work_type_id in seen:
            continue
        seen.add(work_type_id)
        definition = taxonomy.definition_for_id(work_type_id)
        normalized.append({
            "work_type_id": work_type_id,
            "label": definition.label,
        })

    if not normalized:
        raise RoleContractError(
            "DETERMINER_RESULT_INVALID",
            "clarification options resolved to an empty set",
        )
    return normalized


def _validate_clarification_questions(
    questions: Any,
    taxonomy: DeterminerTaxonomy,
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(questions, list) or not questions or any(
        not isinstance(item, Mapping) for item in questions
    ):
        raise RoleContractError(
            "DETERMINER_RESULT_INVALID",
            "clarification response requires one or more structured questions",
        )

    normalized_questions = []
    for index, raw in enumerate(questions, start=1):
        question = raw.get("question")
        if not isinstance(question, str) or not question.strip():
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "clarification question text is required",
            )
        item = dict(raw)
        item["question_id"] = (
            item.get("question_id")
            if isinstance(item.get("question_id"), str) and item.get("question_id").strip()
            else f"q{index}"
        )
        item["question"] = question.strip()

        options = item.get("options")
        if options is not None:
            item["options"] = _normalize_clarification_options(options, taxonomy)
        normalized_questions.append(item)

    return tuple(normalized_questions)


def _parse_determiner_response(
    response: RoleResponse,
    taxonomy: DeterminerTaxonomy,
) -> DeterminerResult:
    payload = response.payload

    if response.status is RoleStatus.NEEDS_CLARIFICATION:
        questions = _validate_clarification_questions(
            payload.get("questions"),
            taxonomy,
        )
        result = DeterminerResult(
            role_status=response.status,
            questions=questions,
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

    work_type_id = payload.get("work_type_id")
    complexity = payload.get("complexity")
    confidence = payload.get("confidence")
    reason_codes_raw = payload.get("reason_codes", [])
    notes = payload.get("notes")

    if not isinstance(reason_codes_raw, list) or any(
        not isinstance(item, str) or not item.strip() for item in reason_codes_raw
    ):
        raise RoleContractError(
            "DETERMINER_RESULT_INVALID",
            "reason_codes must be a list of nonblank strings",
        )
    reason_codes = tuple(reason_codes_raw)
    if len(reason_codes) != len(set(reason_codes)):
        raise RoleContractError(
            "DETERMINER_RESULT_INVALID",
            "reason_codes must be unique",
        )
    if notes is not None and not isinstance(notes, str):
        raise RoleContractError(
            "DETERMINER_RESULT_INVALID",
            "notes must be text when present",
        )

    work_type_label = None
    if classification is ClassificationStatus.CLASSIFIED:
        if not isinstance(work_type_id, str) or not taxonomy.contains_work_type_id(work_type_id):
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "classified result must use a configured four-digit work_type_id",
                {
                    "work_type_id": work_type_id,
                    "allowed": list(taxonomy.work_type_ids),
                },
            )
        work_type_label = taxonomy.label_for_id(work_type_id)
        if complexity is not None and (
            not isinstance(complexity, str)
            or not taxonomy.contains_complexity(complexity)
        ):
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "complexity must use a configured complexity level",
                {
                    "complexity": complexity,
                    "allowed": list(taxonomy.complexity_levels),
                },
            )
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0 <= float(confidence) <= 1
        ):
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "classified result confidence must be a number from 0 through 1",
            )
        confidence = float(confidence)
    else:
        if work_type_id is not None or complexity is not None:
            raise RoleContractError(
                "DETERMINER_RESULT_INVALID",
                "UNKNOWN classification must not claim work_type_id or complexity",
            )
        if confidence is not None:
            if (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not 0 <= float(confidence) <= 1
            ):
                raise RoleContractError(
                    "DETERMINER_RESULT_INVALID",
                    "UNKNOWN confidence must be a number from 0 through 1 when present",
                )
            confidence = float(confidence)

    result = DeterminerResult(
        role_status=response.status,
        classification=classification,
        work_type_id=work_type_id,
        work_type_label=work_type_label,
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
        work_type_id=result.work_type_id,
        work_type_label=result.work_type_label,
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
        "work_type_id": result.work_type_id,
        "work_type_label": result.work_type_label,
        "complexity": result.complexity,
        "confidence": result.confidence,
        "question_count": len(result.questions),
        "taxonomy_digest": taxonomy.digest(),
    }


def normalize_determiner_role_response(
    value: Mapping[str, Any],
    *,
    instructions: Mapping[str, Any],
    profile_metadata: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Repair only exact, unambiguous Determiner shape drift."""
    taxonomy_raw = instructions.get("taxonomy")
    if not isinstance(taxonomy_raw, Mapping):
        raise RoleContractError(
            "DETERMINER_TAXONOMY_MISSING",
            "Determiner profile instructions do not contain the configured taxonomy",
        )
    taxonomy = DeterminerTaxonomy.from_mapping(taxonomy_raw)
    repairs: list[str] = []

    envelope = dict(value)
    shared_status_values = {str(item) for item in RoleStatus}
    top_status = envelope.get("status")

    if top_status in shared_status_values:
        payload_raw = envelope.get("payload")
        if payload_raw is None:
            payload_keys = {
                "schema_version",
                "classification",
                "work_type_id",
                "work_type",
                "complexity",
                "confidence",
                "reason_codes",
                "notes",
                "questions",
                "question",
                "clarification",
            }
            payload = {
                key: envelope.pop(key)
                for key in list(envelope)
                if key in payload_keys and key != "status"
            }
            envelope["payload"] = payload
            if payload:
                repairs.append("top_level_role_fields_moved_to_payload")
        elif not isinstance(payload_raw, Mapping):
            raise RoleContractError(
                "DETERMINER_NORMALIZATION_AMBIGUOUS",
                "shared status is present but payload is not a mapping",
                {"payload_type": type(payload_raw).__name__},
            )
        else:
            payload = dict(payload_raw)
            envelope["payload"] = payload
    else:
        payload = dict(envelope)
        envelope = {}

        resolved_status_id = taxonomy.resolve_id(top_status)
        if resolved_status_id is not None:
            payload.pop("status", None)
            payload["work_type_id"] = resolved_status_id
            payload["classification"] = str(ClassificationStatus.CLASSIFIED)
            repairs.append("top_level_status_work_type_moved_to_id")
        elif top_status in {
            str(ClassificationStatus.CLASSIFIED),
            str(ClassificationStatus.UNKNOWN),
        }:
            payload.pop("status", None)
            payload["classification"] = top_status
            repairs.append("top_level_status_moved_to_classification")
        elif top_status is not None:
            raise RoleContractError(
                "DETERMINER_NORMALIZATION_AMBIGUOUS",
                "top-level status is not a shared role status, classification state, or configured work type",
                {"status": top_status},
            )

    if "clarification" in payload:
        clarification = payload.pop("clarification")
        if "questions" in payload or "question" in payload:
            raise RoleContractError(
                "DETERMINER_NORMALIZATION_AMBIGUOUS",
                "response contains clarification together with question/questions",
            )

        if isinstance(clarification, str) and clarification.strip():
            payload["question"] = clarification.strip()
            repairs.append("clarification_string_normalized")
        elif isinstance(clarification, Mapping):
            clarification = dict(clarification)
            question_text = None
            for key in ("question", "message", "prompt"):
                candidate = clarification.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    question_text = candidate.strip()
                    break

            options = None
            for key in ("options", "candidates", "choices"):
                if clarification.get(key) is not None:
                    options = clarification.get(key)
                    break

            if question_text is None:
                if options is None:
                    raise RoleContractError(
                        "DETERMINER_NORMALIZATION_AMBIGUOUS",
                        "clarification mapping has neither question text nor route options",
                        {"observed_keys": sorted(str(key) for key in clarification)},
                    )
                question_text = "Which work type should this request use?"
                repairs.append("clarification_question_defaulted")

            question_item: dict[str, Any] = {
                "question_id": "q1",
                "question": question_text,
            }
            reason = clarification.get("reason")
            if isinstance(reason, str) and reason.strip():
                question_item["reason"] = reason.strip()
            if options is not None:
                question_item["options"] = _normalize_clarification_options(
                    options,
                    taxonomy,
                )

            payload["questions"] = [question_item]
            repairs.append("clarification_mapping_normalized")
        elif isinstance(clarification, list) and clarification and all(
            isinstance(item, Mapping) for item in clarification
        ):
            payload["questions"] = [dict(item) for item in clarification]
            repairs.append("clarification_list_normalized")
        else:
            raise RoleContractError(
                "DETERMINER_NORMALIZATION_AMBIGUOUS",
                "clarification field has an unsupported shape",
                {"clarification_type": type(clarification).__name__},
            )

    if isinstance(payload.get("question"), str) and payload["question"].strip():
        if "questions" in payload:
            raise RoleContractError(
                "DETERMINER_NORMALIZATION_AMBIGUOUS",
                "response contains both question and questions fields",
            )
        payload["questions"] = [{
            "question_id": "q1",
            "question": payload.pop("question").strip(),
            "reason": "model requested clarification",
        }]
        repairs.append("single_question_normalized")

    classification_raw = payload.get("classification")
    canonical_classification = (
        classification_raw
        if classification_raw in {
            str(ClassificationStatus.CLASSIFIED),
            str(ClassificationStatus.UNKNOWN),
        }
        else None
    )

    candidate_values = []
    if "work_type_id" in payload:
        candidate_values.append(("work_type_id", payload.get("work_type_id")))
    if "work_type" in payload:
        candidate_values.append(("legacy_work_type", payload.get("work_type")))
    if classification_raw is not None and canonical_classification is None:
        candidate_values.append(("classification", classification_raw))

    resolved_candidates: list[tuple[str, str]] = []
    for source, candidate in candidate_values:
        resolved = taxonomy.resolve_id(candidate)
        if resolved is not None:
            resolved_candidates.append((source, resolved))

    candidate_ids = {item[1] for item in resolved_candidates}
    if len(candidate_ids) > 1:
        raise RoleContractError(
            "DETERMINER_NORMALIZATION_AMBIGUOUS",
            "response contains conflicting work type identities",
            {
                "candidates": [
                    {"source": source, "work_type_id": work_type_id}
                    for source, work_type_id in resolved_candidates
                ]
            },
        )

    resolved_work_type_id = next(iter(candidate_ids), None)

    if classification_raw is not None and canonical_classification is None:
        resolved_from_classification = taxonomy.resolve_id(classification_raw)
        if resolved_from_classification is not None:
            payload["classification"] = str(ClassificationStatus.CLASSIFIED)
            canonical_classification = str(ClassificationStatus.CLASSIFIED)
            repairs.append("classification_work_type_moved_to_id")

    if resolved_work_type_id is not None:
        if payload.get("work_type_id") != resolved_work_type_id:
            payload["work_type_id"] = resolved_work_type_id
            repairs.append("work_type_id_canonicalized")
        if "work_type" in payload:
            payload.pop("work_type", None)
            repairs.append("legacy_work_type_removed")
        if canonical_classification is None:
            payload["classification"] = str(ClassificationStatus.CLASSIFIED)
            canonical_classification = str(ClassificationStatus.CLASSIFIED)
            repairs.append("classification_added_from_work_type_id")

    if canonical_classification == str(ClassificationStatus.UNKNOWN):
        if resolved_work_type_id is not None:
            raise RoleContractError(
                "DETERMINER_NORMALIZATION_AMBIGUOUS",
                "UNKNOWN classification conflicts with a configured work type",
                {"work_type_id": resolved_work_type_id},
            )
        payload["work_type_id"] = None

    recognized_result = (
        payload.get("schema_version") in {DETERMINER_RESULT_SCHEMA, _LEGACY_RESULT_SCHEMA}
        or canonical_classification in {
            str(ClassificationStatus.CLASSIFIED),
            str(ClassificationStatus.UNKNOWN),
        }
        or resolved_work_type_id is not None
    )
    questions = payload.get("questions")
    recognized_questions = (
        isinstance(questions, list)
        and bool(questions)
        and all(isinstance(item, Mapping) for item in questions)
    )

    if "status" not in envelope:
        if recognized_questions and not recognized_result:
            envelope["status"] = str(RoleStatus.NEEDS_CLARIFICATION)
            envelope["payload"] = payload
            repairs.append("shared_status_added_for_clarification")
        elif recognized_result:
            envelope["status"] = str(RoleStatus.COMPLETE)
            envelope["payload"] = payload
            repairs.append("shared_complete_envelope_added")
        else:
            raise RoleContractError(
                "DETERMINER_NORMALIZATION_AMBIGUOUS",
                "response lacks shared status and is not an unambiguous Determiner result",
                {
                    "observed_keys": sorted(str(key) for key in payload),
                    "classification": payload.get("classification"),
                    "work_type_id": payload.get("work_type_id"),
                    "legacy_work_type": payload.get("work_type"),
                    "has_questions": isinstance(payload.get("questions"), list),
                },
            )
    else:
        envelope["payload"] = payload

    if recognized_result and payload.get("schema_version") != DETERMINER_RESULT_SCHEMA:
        payload["schema_version"] = DETERMINER_RESULT_SCHEMA
        repairs.append("determiner_schema_upgraded")

    return envelope, {
        "changed": bool(repairs),
        "repairs": repairs,
    }
