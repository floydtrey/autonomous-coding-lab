from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_core.storage.control_models import KC_CONTROL_SCHEMA
from knowledge_core.storage.models import Base, KC_DERIVED_SCHEMA, KC_SCHEMA


class TextGenerationSource(Base):
    """Exact governed source lineage for one parent in an SR-2 text generation."""

    __tablename__ = "text_generation_source"
    __table_args__ = (
        Index(
            "ix_text_generation_source_observation",
            "source_observation_id",
        ),
        Index(
            "ix_text_generation_source_governing_manifest",
            "governing_manifest_digest",
        ),
        {"schema": KC_DERIVED_SCHEMA},
    )

    generation_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_DERIVED_SCHEMA}.generation.generation_id"),
        primary_key=True,
    )
    resource_version_ref: Mapped[UUID] = mapped_column(
        ForeignKey(f"{KC_SCHEMA}.resource_version.ref_id"),
        primary_key=True,
    )
    source_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.repository_source_observation.observation_id"
        ),
        nullable=False,
    )
    governing_manifest_digest: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            f"{KC_CONTROL_SCHEMA}.repository_import_receipt.manifest_digest"
        ),
        nullable=False,
    )
    projection_snapshot_digest: Mapped[str] = mapped_column(
        String(71),
        nullable=False,
    )
