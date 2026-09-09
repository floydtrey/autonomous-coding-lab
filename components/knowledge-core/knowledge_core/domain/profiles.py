from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ProfileRevisionSnapshot:
    profile_revision_ref: UUID
    profile_ref: UUID
    version_label: str
    status: str
    created_revision_id: int


@dataclass(frozen=True)
class VocabularyRevisionSnapshot:
    semantic_ref: UUID
    revision_ref: UUID
    stable_name: str
    value_shape: str | None = None


@dataclass(frozen=True)
class ProfileVocabularySnapshot:
    profile_revision: ProfileRevisionSnapshot
    kinds: tuple[VocabularyRevisionSnapshot, ...]
    predicates: tuple[VocabularyRevisionSnapshot, ...]


@dataclass(frozen=True)
class ProfileActivationSnapshot:
    activation_id: UUID
    profile_ref: UUID
    profile_revision_ref: UUID
    activated_revision_id: int
    activated_at: datetime


@dataclass(frozen=True)
class AssertionSemanticResolution:
    assertion_ref: UUID
    profile_ref: UUID
    profile_revision_ref: UUID
    profile_version_label: str
    predicate_ref: UUID
    predicate_revision_ref: UUID
    predicate_stable_name: str
    predicate_value_shape: str
