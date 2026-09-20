from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.models import Base, KC_SCHEMA, REVISION_ID_TYPE


class Resource(Base):
    __tablename__ = "resource"
    __table_args__ = {"schema": KC_SCHEMA}

    ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    kind_revision_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_kind_revision.ref_id"), nullable=False
    )
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class ResourceVersion(Base):
    __tablename__ = "resource_version"
    __table_args__ = (
        UniqueConstraint(
            "resource_ref_id",
            "content_digest_algo",
            "content_digest",
            name="uq_resource_version_exact_content",
        ),
        {"schema": KC_SCHEMA},
    )

    ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), primary_key=True
    )
    resource_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.resource.ref_id"), nullable=False, index=True
    )
    content_digest_algo: Mapped[str] = mapped_column(String(16), nullable=False)
    content_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(REVISION_ID_TYPE, nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    artifact_backend: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_key: Mapped[str] = mapped_column(Text, nullable=False)
    observed_occurrence_ref: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.occurrence.ref_id"), nullable=True
    )
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class ResourceLocator(Base):
    __tablename__ = "resource_locator"
    __table_args__ = (
        CheckConstraint(
            "locator_kind IN ('path','url','git_ref','mailbox_locator','governed-other')",
            name="ck_resource_locator_kind",
        ),
        {"schema": KC_SCHEMA},
    )

    locator_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    resource_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.resource.ref_id"), nullable=False, index=True
    )
    resource_version_ref: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.resource_version.ref_id"), nullable=True, index=True
    )
    locator_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    locator_text: Mapped[str] = mapped_column(Text, nullable=False)
    observed_occurrence_ref: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.occurrence.ref_id"), nullable=True
    )
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )


class ProvenanceLink(Base):
    __tablename__ = "provenance_link"
    __table_args__ = (
        Index(
            "ix_provenance_link_source_relation",
            "source_ref_id",
            "relation_revision_ref",
        ),
        Index(
            "ix_provenance_link_target_relation",
            "target_ref_id",
            "relation_revision_ref",
        ),
        Index(
            "ix_provenance_link_activity",
            "activity_occurrence_ref",
        ),
        {"schema": KC_SCHEMA},
    )

    link_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    relation_revision_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.semantic_predicate_revision.ref_id"),
        nullable=False,
    )
    source_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), nullable=False
    )
    target_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.knowledge_ref.ref_id"), nullable=False
    )
    activity_occurrence_ref: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.occurrence.ref_id"), nullable=True
    )
    created_revision_id: Mapped[int] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.revision.revision_id"), nullable=False
    )
