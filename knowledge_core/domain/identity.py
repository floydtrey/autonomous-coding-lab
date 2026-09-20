from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class IdentityTransitionType(StrEnum):
    RESOLVE_SAME = "resolve_same"
    RESOLVE_DIFFERENT = "resolve_different"
    MERGE = "merge"
    SPLIT = "split"
    REPLACE = "replace"
    REASSIGN_IDENTIFIER = "reassign_identifier"


class IdentityMemberRole(StrEnum):
    SOURCE = "source"
    MEMBER = "member"
    REPRESENTATIVE = "representative"
    OLD = "old"
    NEW = "new"
    SPLIT_MEMBER = "split_member"
    GOVERNED_OTHER = "governed-other"


@dataclass(frozen=True)
class IdentityFoundationRefs:
    profile_ref: UUID
    profile_revision_ref: UUID
    person_kind_revision_ref: UUID
    device_kind_revision_ref: UUID
    identity_resolution_kind_revision_ref: UUID
    has_name_predicate_revision_ref: UUID


@dataclass(frozen=True)
class IdentityMemberSnapshot:
    entity_ref: UUID
    member_role: IdentityMemberRole
    ordinal: int


@dataclass(frozen=True)
class IdentityTransitionSnapshot:
    transition_ref: UUID
    transition_type: IdentityTransitionType
    reverses_transition_ref: UUID | None
    members: tuple[IdentityMemberSnapshot, ...]
    created_revision_id: int


@dataclass(frozen=True)
class IdentityResolutionSnapshot:
    entity_ref: UUID
    resolution_group_id: UUID
    representative_ref: UUID
    member_refs: tuple[UUID, ...]
    source_transition_ref: UUID | None
    source_revision_id: int
