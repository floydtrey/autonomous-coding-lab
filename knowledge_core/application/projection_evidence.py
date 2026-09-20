from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import select

from knowledge_core.application.generations import GenerationKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.projection_evidence import (
    ProjectionAttemptReuseError,
    ProjectionAttemptSnapshot,
    ProjectionAttemptStateError,
    ProjectionDisposition,
    ProjectionSourceEvidence,
    ProjectionValidationState,
)
from knowledge_core.storage.models import KnowledgeRef, Revision
from knowledge_core.storage.projection_models import ProjectionAttempt, ProjectionAttemptSource


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _request_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _required_text(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise KnowledgeInvariantError(f"{name} must not be empty")
    return normalized


class ProjectionEvidenceKnowledgeKernel(GenerationKnowledgeKernel):
    """Provider-neutral durable evidence for external derived-projection attempts."""

    def read_projection_attempt(self, attempt_id: UUID) -> ProjectionAttemptSnapshot:
        row = self.session.get(ProjectionAttempt, attempt_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown projection attempt: {attempt_id}")
        source_rows = self.session.scalars(
            select(ProjectionAttemptSource)
            .where(ProjectionAttemptSource.attempt_id == attempt_id)
            .order_by(ProjectionAttemptSource.source_ref_id)
        ).all()
        return ProjectionAttemptSnapshot(
            attempt_id=row.attempt_id,
            request_digest=row.request_digest,
            projection_kind=row.projection_kind,
            target_kind=row.target_kind,
            namespace_key=row.namespace_key,
            scope_key=row.scope_key,
            backend_identity=row.backend_identity,
            backend_version=row.backend_version,
            profile_id=row.profile_id,
            profile_digest=row.profile_digest,
            config_digest=row.config_digest,
            disposition=ProjectionDisposition(row.disposition),
            validation_state=ProjectionValidationState(row.validation_state),
            started_at=_utc(row.started_at),
            settled_at=_utc(row.settled_at) if row.settled_at is not None else None,
            warnings=tuple(row.warnings_json or ()),
            errors=tuple(row.errors_json or ()),
            sources=tuple(
                ProjectionSourceEvidence(
                    source_ref=source.source_ref_id,
                    source_revision_id=(
                        int(source.source_revision_id)
                        if source.source_revision_id is not None
                        else None
                    ),
                )
                for source in source_rows
            ),
        )

    def start_projection_attempt(
        self,
        *,
        attempt_id: UUID,
        projection_kind: str,
        target_kind: str,
        namespace_key: str,
        scope_key: str,
        backend_identity: str,
        backend_version: str | None = None,
        profile_id: str | None = None,
        profile_digest: str | None = None,
        config_digest: str | None = None,
        sources: tuple[tuple[UUID, int | None], ...] = (),
    ) -> ProjectionAttemptSnapshot:
        projection_kind = _required_text("projection_kind", projection_kind)
        target_kind = _required_text("target_kind", target_kind)
        namespace_key = _required_text("namespace_key", namespace_key)
        scope_key = _required_text("scope_key", scope_key)
        backend_identity = _required_text("backend_identity", backend_identity)

        normalized_sources = tuple(sorted(sources, key=lambda item: str(item[0])))
        if len({source_ref for source_ref, _ in normalized_sources}) != len(normalized_sources):
            raise KnowledgeInvariantError("projection attempt sources must be unique")

        for source_ref, source_revision_id in normalized_sources:
            if self.session.get(KnowledgeRef, source_ref) is None:
                raise KnowledgeInvariantError(f"unknown projection source ref: {source_ref}")
            if source_revision_id is not None and self.session.get(Revision, source_revision_id) is None:
                raise KnowledgeInvariantError(
                    f"unknown projection source revision: {source_revision_id}"
                )

        request_digest = _request_digest(
            {
                "backend_identity": backend_identity,
                "backend_version": backend_version,
                "config_digest": config_digest,
                "namespace_key": namespace_key,
                "profile_digest": profile_digest,
                "profile_id": profile_id,
                "projection_kind": projection_kind,
                "scope_key": scope_key,
                "sources": [
                    {
                        "source_ref": str(source_ref).lower(),
                        "source_revision_id": source_revision_id,
                    }
                    for source_ref, source_revision_id in normalized_sources
                ],
                "target_kind": target_kind,
            }
        )

        existing = self.session.get(ProjectionAttempt, attempt_id)
        if existing is not None:
            if existing.request_digest != request_digest:
                raise ProjectionAttemptReuseError(
                    f"projection attempt {attempt_id} was reused with different inputs"
                )
            return self.read_projection_attempt(attempt_id)

        row = ProjectionAttempt(
            attempt_id=attempt_id,
            request_digest=request_digest,
            projection_kind=projection_kind,
            target_kind=target_kind,
            namespace_key=namespace_key,
            scope_key=scope_key,
            backend_identity=backend_identity,
            backend_version=backend_version,
            profile_id=profile_id,
            profile_digest=profile_digest,
            config_digest=config_digest,
            disposition=ProjectionDisposition.PENDING.value,
            validation_state=ProjectionValidationState.UNVALIDATED.value,
            started_at=self._now(),
            settled_at=None,
            warnings_json=None,
            errors_json=None,
        )
        self.session.add(row)
        self.session.flush()
        for source_ref, source_revision_id in normalized_sources:
            self.session.add(
                ProjectionAttemptSource(
                    attempt_id=attempt_id,
                    source_ref_id=source_ref,
                    source_revision_id=source_revision_id,
                )
            )
        self.session.commit()
        return self.read_projection_attempt(attempt_id)

    def settle_projection_attempt(
        self,
        *,
        attempt_id: UUID,
        disposition: ProjectionDisposition,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
    ) -> ProjectionAttemptSnapshot:
        if disposition is ProjectionDisposition.PENDING:
            raise ProjectionAttemptStateError("a settled projection attempt cannot remain pending")

        row = self.session.get(ProjectionAttempt, attempt_id)
        if row is None:
            raise KnowledgeInvariantError(f"unknown projection attempt: {attempt_id}")

        normalized_warnings = tuple(str(item) for item in warnings)
        normalized_errors = tuple(str(item) for item in errors)
        current = ProjectionDisposition(row.disposition)
        if current is not ProjectionDisposition.PENDING:
            if (
                current is disposition
                and tuple(row.warnings_json or ()) == normalized_warnings
                and tuple(row.errors_json or ()) == normalized_errors
            ):
                return self.read_projection_attempt(attempt_id)
            raise ProjectionAttemptStateError(
                f"projection attempt {attempt_id} already settled as {current.value}"
            )

        row.disposition = disposition.value
        row.settled_at = self._now()
        row.warnings_json = list(normalized_warnings) or None
        row.errors_json = list(normalized_errors) or None
        # V1 deliberately does not infer trust from backend outcome. A later,
        # independent validation gate owns transitions away from UNVALIDATED.
        row.validation_state = ProjectionValidationState.UNVALIDATED.value
        self.session.commit()
        return self.read_projection_attempt(attempt_id)
