from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import re
import secrets
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_core.domain.principals import (
    AuthenticatedPrincipal,
    PrincipalSnapshot,
    PrincipalStatus,
    PrincipalType,
    ServiceCredentialSnapshot,
    ServiceCredentialStatus,
)
from knowledge_core.storage.principal_models import (
    PrincipalRecord,
    ServiceCredentialRecord,
)


_SERVICE_KEY_VERSION = "kc1"
_SECRET_HASH_ALGO = "sha256-v1"
_PRINCIPAL_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{0,127}$")


class PrincipalConflictError(RuntimeError):
    pass


class PrincipalAuthenticationError(RuntimeError):
    pass


@dataclass(frozen=True)
class IssuedServiceCredential:
    credential: ServiceCredentialSnapshot
    token: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _principal_snapshot(row: PrincipalRecord) -> PrincipalSnapshot:
    return PrincipalSnapshot(
        principal_ref=row.principal_ref,
        principal_code=row.principal_code,
        display_name=row.display_name,
        principal_type=PrincipalType(row.principal_type),
        status=PrincipalStatus(row.status),
        created_at=_as_aware_utc(row.created_at),
    )


def _credential_snapshot(row: ServiceCredentialRecord) -> ServiceCredentialSnapshot:
    return ServiceCredentialSnapshot(
        credential_ref=row.credential_ref,
        principal_ref=row.principal_ref,
        label=row.label,
        status=ServiceCredentialStatus(row.status),
        created_at=_as_aware_utc(row.created_at),
        expires_at=(
            _as_aware_utc(row.expires_at) if row.expires_at is not None else None
        ),
        revoked_at=(
            _as_aware_utc(row.revoked_at) if row.revoked_at is not None else None
        ),
    )


class PrincipalAuthenticationKernel:
    """Durable principal identity and independently revocable service credentials.

    This kernel intentionally does not decide authorization. Successful
    authentication proves only which principal presented the credential. KC-B/KC-C
    attach scopes and operation/resource grants to that authenticated identity.
    """

    def __init__(
        self,
        session: Session,
        *,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.session = session
        self._now = now

    @staticmethod
    def normalize_principal_code(value: str) -> str:
        normalized = value.strip().upper()
        if not _PRINCIPAL_CODE_PATTERN.fullmatch(normalized):
            raise ValueError(
                "principal_code must be 1-128 characters using A-Z, 0-9, '.', '_', ':', or '-'"
            )
        return normalized

    def create_principal(
        self,
        *,
        principal_code: str,
        display_name: str,
        principal_type: PrincipalType,
    ) -> PrincipalSnapshot:
        code = self.normalize_principal_code(principal_code)
        display = display_name.strip()
        if not display:
            raise ValueError("display_name must be non-blank")

        existing = self.session.scalar(
            select(PrincipalRecord).where(PrincipalRecord.principal_code == code)
        )
        if existing is not None:
            raise PrincipalConflictError(f"principal code already exists: {code}")

        row = PrincipalRecord(
            principal_ref=uuid4(),
            principal_code=code,
            display_name=display,
            principal_type=principal_type.value,
            status=PrincipalStatus.ACTIVE.value,
            created_at=_as_aware_utc(self._now()),
        )
        self.session.add(row)
        self.session.flush()
        return _principal_snapshot(row)

    def read_principal(self, principal_ref: UUID) -> PrincipalSnapshot:
        row = self.session.get(PrincipalRecord, principal_ref)
        if row is None:
            raise KeyError(f"unknown principal: {principal_ref}")
        return _principal_snapshot(row)

    def disable_principal(self, principal_ref: UUID) -> PrincipalSnapshot:
        row = self.session.get(PrincipalRecord, principal_ref)
        if row is None:
            raise KeyError(f"unknown principal: {principal_ref}")
        row.status = PrincipalStatus.DISABLED.value
        self.session.flush()
        return _principal_snapshot(row)

    def issue_service_credential(
        self,
        *,
        principal_ref: UUID,
        label: str,
        expires_at: datetime | None = None,
    ) -> IssuedServiceCredential:
        principal = self.session.get(PrincipalRecord, principal_ref)
        if principal is None:
            raise KeyError(f"unknown principal: {principal_ref}")
        if PrincipalStatus(principal.status) is not PrincipalStatus.ACTIVE:
            raise PrincipalAuthenticationError("principal is not active")

        normalized_label = label.strip()
        if not normalized_label:
            raise ValueError("credential label must be non-blank")

        now = _as_aware_utc(self._now())
        normalized_expiry = None
        if expires_at is not None:
            normalized_expiry = _as_aware_utc(expires_at)
            if normalized_expiry <= now:
                raise ValueError("credential expiration must be in the future")

        credential_ref = uuid4()
        secret = secrets.token_urlsafe(32)
        secret_hash = sha256(secret.encode("utf-8")).hexdigest()
        row = ServiceCredentialRecord(
            credential_ref=credential_ref,
            principal_ref=principal_ref,
            label=normalized_label,
            secret_hash_algo=_SECRET_HASH_ALGO,
            secret_hash=secret_hash,
            status=ServiceCredentialStatus.ACTIVE.value,
            created_at=now,
            expires_at=normalized_expiry,
            revoked_at=None,
        )
        self.session.add(row)
        self.session.flush()

        token = f"{_SERVICE_KEY_VERSION}.{credential_ref.hex}.{secret}"
        return IssuedServiceCredential(
            credential=_credential_snapshot(row),
            token=token,
        )

    def revoke_service_credential(
        self,
        credential_ref: UUID,
    ) -> ServiceCredentialSnapshot:
        row = self.session.get(ServiceCredentialRecord, credential_ref)
        if row is None:
            raise KeyError(f"unknown service credential: {credential_ref}")
        if ServiceCredentialStatus(row.status) is ServiceCredentialStatus.REVOKED:
            return _credential_snapshot(row)

        row.status = ServiceCredentialStatus.REVOKED.value
        row.revoked_at = _as_aware_utc(self._now())
        self.session.flush()
        return _credential_snapshot(row)

    def authenticate_service_token(self, token: str) -> AuthenticatedPrincipal:
        try:
            version, credential_hex, supplied_secret = token.split(".", 2)
            credential_ref = UUID(hex=credential_hex)
        except (AttributeError, TypeError, ValueError) as exc:
            raise PrincipalAuthenticationError("authentication failed") from exc

        if version != _SERVICE_KEY_VERSION or not supplied_secret:
            raise PrincipalAuthenticationError("authentication failed")

        credential = self.session.get(ServiceCredentialRecord, credential_ref)
        if credential is None:
            raise PrincipalAuthenticationError("authentication failed")
        if credential.secret_hash_algo != _SECRET_HASH_ALGO:
            raise PrincipalAuthenticationError("authentication failed")
        if (
            ServiceCredentialStatus(credential.status)
            is not ServiceCredentialStatus.ACTIVE
        ):
            raise PrincipalAuthenticationError("authentication failed")

        now = _as_aware_utc(self._now())
        if credential.expires_at is not None:
            if _as_aware_utc(credential.expires_at) <= now:
                raise PrincipalAuthenticationError("authentication failed")

        supplied_hash = sha256(supplied_secret.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(supplied_hash, credential.secret_hash):
            raise PrincipalAuthenticationError("authentication failed")

        principal = self.session.get(PrincipalRecord, credential.principal_ref)
        if principal is None:
            raise PrincipalAuthenticationError("authentication failed")
        if PrincipalStatus(principal.status) is not PrincipalStatus.ACTIVE:
            raise PrincipalAuthenticationError("authentication failed")

        return AuthenticatedPrincipal(
            principal_ref=principal.principal_ref,
            principal_code=principal.principal_code,
            display_name=principal.display_name,
            principal_type=PrincipalType(principal.principal_type),
            credential_ref=credential.credential_ref,
        )
