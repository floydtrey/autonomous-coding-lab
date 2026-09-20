from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.control_models import KC_CONTROL_SCHEMA
from knowledge_core.storage.models import Base


class PrincipalRecord(Base):
    __tablename__ = "principal"
    __table_args__ = (
        CheckConstraint(
            "principal_type IN ('owner','human','service','ai')",
            name="ck_principal_type",
        ),
        CheckConstraint(
            "status IN ('active','disabled')",
            name="ck_principal_status",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    principal_ref: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    principal_code: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ServiceCredentialRecord(Base):
    __tablename__ = "service_credential"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','revoked')",
            name="ck_service_credential_status",
        ),
        CheckConstraint(
            "secret_hash_algo IN ('sha256-v1')",
            name="ck_service_credential_hash_algo",
        ),
        Index(
            "ix_service_credential_principal_status",
            "principal_ref",
            "status",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    credential_ref: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    principal_ref: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(f"{KC_CONTROL_SCHEMA}.principal.principal_ref"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    secret_hash_algo: Mapped[str] = mapped_column(String(32), nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
