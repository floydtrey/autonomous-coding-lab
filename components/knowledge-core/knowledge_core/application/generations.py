from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select, text

from knowledge_core.application.profiles import ProfileKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import (
    DerivedKind,
    GenerationFenceError,
    GenerationSnapshot,
    GenerationSourceSnapshot,
    GenerationStatus,
)
from knowledge_core.storage.generation_models import DerivedGeneration, GenerationSource
from knowledge_core.storage.models import KnowledgeRef, Revision, SemanticProfileRevision


_POSTGRES_DERIVED_GENERATION_LOCK = 1262702417


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class GenerationKnowledgeKernel(ProfileKnowledgeKernel):
    """Task 9 generation lineage, staleness, and out-of-order finish fencing."""

    def _acquire_generation_lock(self) -> None:
        bind = self.session.get_bind()
        if bind.dialect.name == "postgresql":
            self.session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": _POSTGRES_DERIVED_GENERATION_LOCK},
            )

    def acquire_generation_publication_lock(self) -> None:
        """Hold the accepted generation publication fence in the caller transaction."""

        self._acquire_generation_lock()

    def _next_generation_sequence(self) -> int:
        return int(self.session.scalar(select(func.max(DerivedGeneration.generation_sequence))) or 0) + 1

    def read_generation(self, generation_id: UUID) -> GenerationSnapshot:
        row = self.session.get(DerivedGeneration, generation_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown derived generation: {generation_id}")
        source_rows = self.session.scalars(
            select(GenerationSource)
            .where(GenerationSource.generation_id == generation_id)
            .order_by(GenerationSource.source_ref_id)
        ).all()
        return GenerationSnapshot(
            generation_id=row.generation_id,
            generation_sequence=int(row.generation_sequence),
            derived_kind=DerivedKind(row.derived_kind),
            source_revision_highwater=int(row.source_revision_highwater),
            profile_revision_ref=row.profile_revision_ref,
            model_identity=row.model_identity,
            model_version=row.model_version,
            config_digest=row.config_digest,
            status=GenerationStatus(row.status),
            created_at=_utc(row.created_at),
            settled_at=_utc(row.settled_at) if row.settled_at is not None else None,
            supersedes_generation=row.supersedes_generation,
            sources=tuple(
                GenerationSourceSnapshot(
                    source_ref=source.source_ref_id,
                    source_revision_id=(int(source.source_revision_id) if source.source_revision_id is not None else None),
                )
                for source in source_rows
            ),
        )

    def generation_history(self, *, derived_kind: DerivedKind) -> tuple[GenerationSnapshot, ...]:
        rows = self.session.scalars(
            select(DerivedGeneration)
            .where(DerivedGeneration.derived_kind == derived_kind.value)
            .order_by(DerivedGeneration.generation_sequence)
        ).all()
        return tuple(self.read_generation(row.generation_id) for row in rows)

    def current_generation(self, *, derived_kind: DerivedKind) -> GenerationSnapshot | None:
        row = self.session.scalars(
            select(DerivedGeneration)
            .where(
                DerivedGeneration.derived_kind == derived_kind.value,
                DerivedGeneration.status == GenerationStatus.CURRENT.value,
            )
            .limit(1)
        ).first()
        return self.read_generation(row.generation_id) if row is not None else None

    def start_generation(
        self,
        *,
        derived_kind: DerivedKind,
        source_revision_highwater: int,
        profile_revision_ref: UUID | None = None,
        sources: Iterable[tuple[UUID, int | None]] = (),
        model_identity: str | None = None,
        model_version: str | None = None,
        config_digest: str | None = None,
    ) -> GenerationSnapshot:
        if source_revision_highwater <= 0:
            raise KnowledgeInvariantError("source_revision_highwater must identify an existing canonical revision")
        if self.session.get(Revision, source_revision_highwater) is None:
            raise KnowledgeInvariantError(f"unknown source revision highwater: {source_revision_highwater}")
        if profile_revision_ref is not None and self.session.get(SemanticProfileRevision, profile_revision_ref) is None:
            raise KnowledgeInvariantError(f"unknown profile revision: {profile_revision_ref}")

        normalized_sources = tuple(sources)
        if len({ref for ref, _revision in normalized_sources}) != len(normalized_sources):
            raise KnowledgeInvariantError("generation sources must be unique")

        for source_ref, source_revision_id in normalized_sources:
            if self.session.get(KnowledgeRef, source_ref) is None:
                raise KnowledgeInvariantError(f"unknown generation source ref: {source_ref}")
            if source_revision_id is not None:
                if source_revision_id > source_revision_highwater:
                    raise KnowledgeInvariantError("source revision cannot exceed generation highwater")
                if self.session.get(Revision, source_revision_id) is None:
                    raise KnowledgeInvariantError(f"unknown generation source revision: {source_revision_id}")

        self._acquire_generation_lock()
        generation_id = uuid4()
        row = DerivedGeneration(
            generation_id=generation_id,
            generation_sequence=self._next_generation_sequence(),
            derived_kind=derived_kind.value,
            source_revision_highwater=source_revision_highwater,
            profile_revision_ref=profile_revision_ref,
            model_identity=model_identity,
            model_version=model_version,
            config_digest=config_digest,
            status=GenerationStatus.BUILDING.value,
            created_at=self._now(),
            settled_at=None,
            supersedes_generation=None,
        )
        self.session.add(row)
        self.session.flush()
        for source_ref, source_revision_id in normalized_sources:
            self.session.add(
                GenerationSource(
                    generation_id=generation_id,
                    source_ref_id=source_ref,
                    source_revision_id=source_revision_id,
                )
            )
        self._commit()
        return self.read_generation(generation_id)

    def mark_generation_stale(self, *, generation_id: UUID) -> GenerationSnapshot:
        row = self.session.get(DerivedGeneration, generation_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown derived generation: {generation_id}")
        if GenerationStatus(row.status) is GenerationStatus.STALE:
            return self.read_generation(generation_id)

        self._acquire_generation_lock()
        self.session.refresh(row)
        status = GenerationStatus(row.status)
        if status is GenerationStatus.STALE:
            self.session.commit()
            return self.read_generation(generation_id)
        if status not in {GenerationStatus.BUILDING, GenerationStatus.CURRENT}:
            self.session.rollback()
            raise GenerationFenceError(f"generation {generation_id} cannot become stale from {status.value}")
        row.status = GenerationStatus.STALE.value
        if row.settled_at is None:
            row.settled_at = self._now()
        self._commit()
        return self.read_generation(generation_id)

    def settle_generation(
        self,
        *,
        generation_id: UUID,
        commit_transaction: bool = True,
        publication_lock_held: bool = False,
    ) -> GenerationSnapshot:
        """Promote one building generation under the accepted one-current fence.

        ``commit_transaction=False`` is reserved for a caller that must compose
        generation promotion with another publication record in the same database
        transaction. Existing callers retain the original commit-on-settle behavior.
        """

        row = self.session.get(DerivedGeneration, generation_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown derived generation: {generation_id}")
        if GenerationStatus(row.status) is GenerationStatus.CURRENT:
            return self.read_generation(generation_id)

        if not publication_lock_held:
            self._acquire_generation_lock()
        self.session.refresh(row)
        status = GenerationStatus(row.status)
        if status is GenerationStatus.CURRENT:
            if commit_transaction:
                self.session.commit()
            return self.read_generation(generation_id)
        if status is not GenerationStatus.BUILDING:
            if commit_transaction:
                self.session.rollback()
            raise GenerationFenceError(f"generation {generation_id} cannot settle from {status.value}")

        current = self.session.scalars(
            select(DerivedGeneration)
            .where(
                DerivedGeneration.derived_kind == row.derived_kind,
                DerivedGeneration.status == GenerationStatus.CURRENT.value,
            )
            .limit(1)
        ).first()

        if current is not None and int(current.generation_sequence) > int(row.generation_sequence):
            row.status = GenerationStatus.STALE.value
            row.settled_at = self._now()
            if commit_transaction:
                self._commit()
            else:
                self.session.flush()
            raise GenerationFenceError("an older finishing generation cannot replace a newer current generation")

        if current is not None and current.generation_id != row.generation_id:
            current.status = GenerationStatus.SUPERSEDED.value
            row.supersedes_generation = current.generation_id
            # Release the partial unique "one current per derived kind" slot before
            # promoting the new generation. This ordering matters on PostgreSQL.
            self.session.flush()

        row.status = GenerationStatus.CURRENT.value
        row.settled_at = self._now()
        if commit_transaction:
            self._commit()
        else:
            self.session.flush()
        return self.read_generation(generation_id)
