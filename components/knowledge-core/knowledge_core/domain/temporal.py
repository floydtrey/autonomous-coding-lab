from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from knowledge_core.domain.assertions import AssertionSnapshot, KnowledgeInvariantError


def _require_aware(value: datetime | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise KnowledgeInvariantError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class WorldInterval:
    """Half-open world-valid interval [valid_from, valid_to)."""

    valid_from: datetime | None = None
    valid_to: datetime | None = None
    precision: str | None = "exact"

    def __post_init__(self) -> None:
        valid_from = _require_aware(self.valid_from, "valid_from")
        valid_to = _require_aware(self.valid_to, "valid_to")
        if valid_from is not None and valid_to is not None and valid_to <= valid_from:
            raise KnowledgeInvariantError("valid_to must be later than valid_from")
        object.__setattr__(self, "valid_from", valid_from)
        object.__setattr__(self, "valid_to", valid_to)

    def contains(self, moment: datetime) -> bool:
        moment = _require_aware(moment, "world_at")
        assert moment is not None
        if self.valid_from is not None and moment < self.valid_from:
            return False
        if self.valid_to is not None and moment >= self.valid_to:
            return False
        return True


@dataclass(frozen=True)
class BitemporalAssertion:
    assertion: AssertionSnapshot
    valid_from: datetime | None
    valid_to: datetime | None
    world_time_precision: str | None
    recorded_at: datetime
