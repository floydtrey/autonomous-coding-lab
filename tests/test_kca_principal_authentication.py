from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from knowledge_core.application.principal_auth import (
    PrincipalAuthenticationError,
    PrincipalAuthenticationKernel,
    PrincipalConflictError,
)
from knowledge_core.domain.principals import (
    PrincipalStatus,
    PrincipalType,
    ServiceCredentialStatus,
)
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)
from knowledge_core.storage.principal_models import ServiceCredentialRecord


def _kernel():
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    sessions = create_session_factory(engine)
    session = sessions()
    return engine, session, PrincipalAuthenticationKernel(session)


def test_principal_identity_is_uuid_backed_and_code_is_normalized():
    engine, session, kernel = _kernel()
    try:
        principal = kernel.create_principal(
            principal_code="acl-worker",
            display_name="ACL Worker",
            principal_type=PrincipalType.AI,
        )
        session.commit()

        assert principal.principal_code == "ACL-WORKER"
        assert principal.display_name == "ACL Worker"
        assert principal.status is PrincipalStatus.ACTIVE

        with pytest.raises(PrincipalConflictError):
            kernel.create_principal(
                principal_code="ACL-WORKER",
                display_name="Different Display Name",
                principal_type=PrincipalType.SERVICE,
            )
    finally:
        session.close()
        engine.dispose()


def test_service_secret_is_returned_once_and_only_hash_is_persisted():
    engine, session, kernel = _kernel()
    try:
        principal = kernel.create_principal(
            principal_code="ACL-PLANNER",
            display_name="ACL Planner",
            principal_type=PrincipalType.AI,
        )
        issued = kernel.issue_service_credential(
            principal_ref=principal.principal_ref,
            label="initial ACL planner credential",
        )
        session.commit()

        assert issued.token.startswith(
            f"kc1.{issued.credential.credential_ref.hex}."
        )
        raw_secret = issued.token.split(".", 2)[2]

        stored = session.scalar(
            select(ServiceCredentialRecord).where(
                ServiceCredentialRecord.credential_ref
                == issued.credential.credential_ref
            )
        )
        assert stored is not None
        assert stored.secret_hash != raw_secret
        assert raw_secret not in stored.secret_hash

        authenticated = kernel.authenticate_service_token(issued.token)
        assert authenticated.principal_ref == principal.principal_ref
        assert authenticated.principal_code == "ACL-PLANNER"
        assert authenticated.credential_ref == issued.credential.credential_ref
    finally:
        session.close()
        engine.dispose()


def test_wrong_secret_revocation_and_principal_disable_fail_closed():
    engine, session, kernel = _kernel()
    try:
        principal = kernel.create_principal(
            principal_code="ACL-REVIEWER",
            display_name="ACL Reviewer",
            principal_type=PrincipalType.AI,
        )
        first = kernel.issue_service_credential(
            principal_ref=principal.principal_ref,
            label="first",
        )
        second = kernel.issue_service_credential(
            principal_ref=principal.principal_ref,
            label="second",
        )
        session.commit()

        version, credential_hex, _secret = first.token.split(".", 2)
        with pytest.raises(PrincipalAuthenticationError):
            kernel.authenticate_service_token(
                f"{version}.{credential_hex}.not-the-secret"
            )

        revoked = kernel.revoke_service_credential(first.credential.credential_ref)
        session.commit()
        assert revoked.status is ServiceCredentialStatus.REVOKED
        with pytest.raises(PrincipalAuthenticationError):
            kernel.authenticate_service_token(first.token)

        assert kernel.authenticate_service_token(second.token).principal_ref == (
            principal.principal_ref
        )

        disabled = kernel.disable_principal(principal.principal_ref)
        session.commit()
        assert disabled.status is PrincipalStatus.DISABLED
        with pytest.raises(PrincipalAuthenticationError):
            kernel.authenticate_service_token(second.token)
    finally:
        session.close()
        engine.dispose()


def test_expired_or_malformed_service_tokens_are_rejected():
    fixed_now = datetime(2026, 9, 19, 21, 0, tzinfo=timezone.utc)
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    sessions = create_session_factory(engine)
    session = sessions()
    try:
        kernel = PrincipalAuthenticationKernel(session, now=lambda: fixed_now)
        principal = kernel.create_principal(
            principal_code="CHATGPT-IMPORTER",
            display_name="ChatGPT Importer",
            principal_type=PrincipalType.SERVICE,
        )
        issued = kernel.issue_service_credential(
            principal_ref=principal.principal_ref,
            label="short-lived importer token",
            expires_at=fixed_now + timedelta(minutes=5),
        )
        session.commit()

        assert kernel.authenticate_service_token(issued.token).principal_ref == (
            principal.principal_ref
        )

        later = PrincipalAuthenticationKernel(
            session,
            now=lambda: fixed_now + timedelta(minutes=6),
        )
        with pytest.raises(PrincipalAuthenticationError):
            later.authenticate_service_token(issued.token)

        for malformed in (
            "",
            "not-a-kc-key",
            "kc1.not-a-uuid.secret",
            "kc2.00000000000000000000000000000000.secret",
        ):
            with pytest.raises(PrincipalAuthenticationError):
                kernel.authenticate_service_token(malformed)
    finally:
        session.close()
        engine.dispose()
