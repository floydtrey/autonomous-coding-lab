from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class PrincipalType(StrEnum):
    OWNER = "owner"
    HUMAN = "human"
    SERVICE = "service"
    AI = "ai"


class PrincipalStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ServiceCredentialStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass(frozen=True)
class PrincipalSnapshot:
    principal_ref: UUID
    principal_code: str
    display_name: str
    principal_type: PrincipalType
    status: PrincipalStatus
    created_at: datetime


@dataclass(frozen=True)
class ServiceCredentialSnapshot:
    credential_ref: UUID
    principal_ref: UUID
    label: str
    status: ServiceCredentialStatus
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    principal_ref: UUID
    principal_code: str
    display_name: str
    principal_type: PrincipalType
    credential_ref: UUID
