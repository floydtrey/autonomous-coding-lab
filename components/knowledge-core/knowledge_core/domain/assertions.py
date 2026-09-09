from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class KnowledgeInvariantError(ValueError):
    """Raised when a requested semantic mutation violates a kernel invariant."""


class RefKind(StrEnum):
    ENTITY = "entity"
    ASSERTION = "assertion"
    OCCURRENCE = "occurrence"
    SEMANTIC_PROFILE = "semantic_profile"
    SEMANTIC_PROFILE_REVISION = "semantic_profile_revision"
    SEMANTIC_KIND = "semantic_kind"
    SEMANTIC_KIND_REVISION = "semantic_kind_revision"
    SEMANTIC_PREDICATE = "semantic_predicate"
    SEMANTIC_PREDICATE_REVISION = "semantic_predicate_revision"


class ValueKind(StrEnum):
    REFERENCE = "reference"
    TEXT = "text"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"


class ValueState(StrEnum):
    PRESENT = "present"
    EXPLICIT_NEGATIVE = "explicit_negative"
    KNOWN_NO_VALUE = "known_no_value"
    SOME_VALUE_UNKNOWN = "some_value_unknown"
    NOT_ESTABLISHED = "not_established"


class EpistemicBasis(StrEnum):
    STATED = "stated"
    OBSERVED = "observed"
    IMPORTED = "imported"
    CONFIGURED = "configured"
    INFERRED = "inferred"
    DERIVED = "derived"
    VERIFIED = "verified"
    OTHER_GOVERNED = "other-governed"


class TransitionType(StrEnum):
    SUPERSEDES = "supersedes"
    CORRECTS = "corrects"
    INVALIDATES = "invalidates"
    RESTORES = "restores"


@dataclass(frozen=True)
class TypedValue:
    kind: ValueKind
    value: Any

    @classmethod
    def reference(cls, value: UUID) -> "TypedValue":
        return cls(ValueKind.REFERENCE, value)

    @classmethod
    def text(cls, value: str) -> "TypedValue":
        return cls(ValueKind.TEXT, value)

    @classmethod
    def numeric(cls, value: Decimal | int | float | str) -> "TypedValue":
        return cls(ValueKind.NUMERIC, Decimal(str(value)))

    @classmethod
    def boolean(cls, value: bool) -> "TypedValue":
        return cls(ValueKind.BOOLEAN, value)

    @classmethod
    def date(cls, value: date) -> "TypedValue":
        return cls(ValueKind.DATE, value)

    @classmethod
    def timestamp(cls, value: datetime) -> "TypedValue":
        return cls(ValueKind.TIMESTAMP, value)

    def validated(self) -> "TypedValue":
        if self.kind is ValueKind.REFERENCE:
            if not isinstance(self.value, UUID):
                raise KnowledgeInvariantError("reference values must be UUIDs")
        elif self.kind is ValueKind.TEXT:
            if not isinstance(self.value, str):
                raise KnowledgeInvariantError("text values must be strings")
        elif self.kind is ValueKind.NUMERIC:
            if isinstance(self.value, bool):
                raise KnowledgeInvariantError("boolean is not a numeric value")
            try:
                Decimal(str(self.value))
            except Exception as exc:
                raise KnowledgeInvariantError("numeric value is not Decimal-compatible") from exc
        elif self.kind is ValueKind.BOOLEAN:
            if type(self.value) is not bool:
                raise KnowledgeInvariantError("boolean values must be bool")
        elif self.kind is ValueKind.DATE:
            if not isinstance(self.value, date) or isinstance(self.value, datetime):
                raise KnowledgeInvariantError("date values must be date without time")
        elif self.kind is ValueKind.TIMESTAMP:
            if not isinstance(self.value, datetime) or self.value.tzinfo is None:
                raise KnowledgeInvariantError("timestamp values must be timezone-aware")
        else:
            raise KnowledgeInvariantError(f"unsupported value kind: {self.kind!r}")
        return self


@dataclass(frozen=True)
class FoundationRefs:
    profile_ref: UUID
    profile_revision_ref: UUID
    person_kind_revision_ref: UUID
    organization_kind_revision_ref: UUID
    correction_kind_revision_ref: UUID
    has_name_predicate_revision_ref: UUID
    works_for_predicate_revision_ref: UUID


@dataclass(frozen=True)
class AssertionSnapshot:
    assertion_ref: UUID
    subject_ref: UUID
    predicate_revision_ref: UUID
    profile_revision_ref: UUID
    value_state: ValueState
    epistemic_basis: EpistemicBasis
    value: TypedValue
    created_revision_id: int


@dataclass(frozen=True)
class TransitionSnapshot:
    transition_ref: UUID
    transition_type: TransitionType
    source_assertion_ref: UUID
    replacement_assertion_ref: UUID | None
    reverses_transition_ref: UUID | None
    created_revision_id: int
