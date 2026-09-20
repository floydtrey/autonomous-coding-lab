from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.control_models import KC_CONTROL_SCHEMA
from knowledge_core.storage.models import Base, KC_SCHEMA


class RepositoryDocumentBinding(Base):
    __tablename__ = "repository_document_binding"
    __table_args__ = (
        UniqueConstraint("resource_ref", name="uq_repository_document_binding_resource"),
        {"schema": KC_CONTROL_SCHEMA},
    )

    source_repository_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_document_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    resource_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.resource.ref_id"), nullable=False
    )


class RepositoryImportReceipt(Base):
    __tablename__ = "repository_import_receipt"
    __table_args__ = (
        CheckConstraint(
            "status IN ('applying','settled','failed')",
            name="ck_repository_import_receipt_status",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    manifest_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    previous_manifest_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_repository_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    resulting_text_generation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("kc_derived.generation.generation_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RepositorySourceObservation(Base):
    __tablename__ = "repository_source_observation"
    __table_args__ = (
        UniqueConstraint(
            "manifest_digest",
            "source_document_key",
            name="uq_repository_source_observation_manifest_document",
        ),
        {"schema": KC_CONTROL_SCHEMA},
    )

    observation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    manifest_digest: Mapped[str] = mapped_column(
        ForeignKey(f"{KC_CONTROL_SCHEMA}.repository_import_receipt.manifest_digest"),
        nullable=False,
        index=True,
    )
    source_repository_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_document_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    git_blob_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.resource.ref_id"), nullable=False
    )
    resource_version_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.resource_version.ref_id"), nullable=False
    )
    classification: Mapped[str] = mapped_column(String(128), nullable=False)
    retrieval_lifecycle: Mapped[str] = mapped_column(String(32), nullable=False)
    authority_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
