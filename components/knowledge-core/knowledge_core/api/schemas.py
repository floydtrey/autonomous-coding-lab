from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from knowledge_core.domain.assertions import EpistemicBasis, TypedValue, ValueKind
from knowledge_core.domain.temporal import WorldInterval


class OperationEnvelope(BaseModel):
    operation_id: UUID
    expected_revision: int | None = None


class EntityCreateRequest(OperationEnvelope):
    kind_revision_ref: UUID


class EntityResponse(BaseModel):
    entity_ref: UUID
    kind_revision_ref: UUID
    created_revision_id: int


class TypedValueRequest(BaseModel):
    kind: ValueKind
    value: Any

    @model_validator(mode="after")
    def validate_domain_value(self):
        self.to_domain()
        return self

    def to_domain(self) -> TypedValue:
        if self.kind is ValueKind.REFERENCE:
            return TypedValue.reference(UUID(str(self.value)))
        if self.kind is ValueKind.TEXT:
            if not isinstance(self.value, str):
                raise ValueError("text value must be a string")
            return TypedValue.text(self.value)
        if self.kind is ValueKind.NUMERIC:
            return TypedValue.numeric(Decimal(str(self.value)))
        if self.kind is ValueKind.BOOLEAN:
            if type(self.value) is not bool:
                raise ValueError("boolean value must be true or false")
            return TypedValue.boolean(self.value)
        if self.kind is ValueKind.DATE:
            value = self.value if isinstance(self.value, date) else date.fromisoformat(str(self.value))
            return TypedValue.date(value)
        if self.kind is ValueKind.TIMESTAMP:
            value = (
                self.value
                if isinstance(self.value, datetime)
                else datetime.fromisoformat(str(self.value).replace("Z", "+00:00"))
            )
            return TypedValue.timestamp(value)
        raise ValueError(f"unsupported value kind: {self.kind}")


class WorldIntervalRequest(BaseModel):
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    precision: str | None = "exact"

    @model_validator(mode="after")
    def validate_domain_interval(self):
        self.to_domain()
        return self

    def to_domain(self) -> WorldInterval:
        return WorldInterval(
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            precision=self.precision,
        )


class AssertionCreateRequest(OperationEnvelope):
    subject_ref: UUID
    predicate_revision_ref: UUID
    profile_revision_ref: UUID
    value: TypedValueRequest
    epistemic_basis: EpistemicBasis = EpistemicBasis.STATED
    world_interval: WorldIntervalRequest | None = None


class AssertionCorrectRequest(BaseModel):
    operation_id: UUID
    expected_revision: int
    replacement_value: TypedValueRequest
    correction_kind_revision_ref: UUID
    replacement_world_interval: WorldIntervalRequest | None = None


class TransitionReverseRequest(BaseModel):
    operation_id: UUID
    expected_revision: int
    correction_kind_revision_ref: UUID


class ValueResponse(BaseModel):
    kind: ValueKind
    value: Any


class AssertionResponse(BaseModel):
    assertion_ref: UUID
    subject_ref: UUID
    predicate_revision_ref: UUID
    profile_revision_ref: UUID
    value_state: str
    epistemic_basis: str
    value: ValueResponse
    created_revision_id: int


class BitemporalAssertionResponse(BaseModel):
    assertion: AssertionResponse
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    world_time_precision: str | None = None
    recorded_at: datetime


class TransitionResponse(BaseModel):
    transition_ref: UUID
    transition_type: str
    source_assertion_ref: UUID
    replacement_assertion_ref: UUID | None = None
    reverses_transition_ref: UUID | None = None
    created_revision_id: int


class IdentityMergeRequest(BaseModel):
    operation_id: UUID
    expected_revision: int
    entity_refs: list[UUID] = Field(min_length=2)
    representative_ref: UUID
    identity_kind_revision_ref: UUID


class IdentityReplaceRequest(BaseModel):
    operation_id: UUID
    expected_revision: int
    old_entity_ref: UUID
    new_entity_ref: UUID
    identity_kind_revision_ref: UUID


class IdentityReverseRequest(BaseModel):
    operation_id: UUID
    expected_revision: int
    identity_kind_revision_ref: UUID


class IdentityMemberResponse(BaseModel):
    entity_ref: UUID
    member_role: str
    ordinal: int


class IdentityTransitionResponse(BaseModel):
    transition_ref: UUID
    transition_type: str
    reverses_transition_ref: UUID | None = None
    members: list[IdentityMemberResponse]
    created_revision_id: int


class IdentityResolutionResponse(BaseModel):
    entity_ref: UUID
    resolution_group_id: UUID
    representative_ref: UUID
    member_refs: list[UUID]
    source_transition_ref: UUID | None = None
    source_revision_id: int


class StatusResponse(BaseModel):
    service: Literal["knowledge-core"] = "knowledge-core"
    api_version: Literal["v1"] = "v1"
    canonical_revision: int
    authority_mode: Literal["external-not-implemented"] = "external-not-implemented"
    database_credentials_exposed: Literal[False] = False


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
