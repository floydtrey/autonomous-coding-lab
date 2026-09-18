from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import and_, or_, select

from knowledge_core.application.history import _as_utc
from knowledge_core.application.operations import _request_digest
from knowledge_core.application.resource_service import ResourceServiceKnowledgeKernel
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.generations import DerivedKind, GenerationStatus
from knowledge_core.domain.retrieval import KnowledgeSourceUnavailableError
from knowledge_core.storage.generation_models import DerivedGeneration
from knowledge_core.storage.governed_source_models import (
    DirectNoteCaptureMetadataRecord,
    GovernedSnapshotProjectRecord,
    GovernedSourceBindingRecord,
    GovernedSourceObservationRecord,
)
from knowledge_core.storage.resource_models import ResourceVersion
from knowledge_core.storage.section_retrieval_models import TextGenerationSource


DIRECT_NOTE_CAPTURE_METADATA_VERSION = "kc-direct-note-capture-metadata-v1"
_DIRECT_NOTE_PRODUCER_ID = "kc.direct-note"
_DIRECT_NOTE_SOURCE_KIND = "local.user-note"


@dataclass(frozen=True)
class DirectNoteCaptureMetadataInput:
    title: str | None = None
    category: str = "Note"
    category_supplied: bool = False
    source_description: str | None = None
    source_urls: tuple[str, ...] = ()
    source_date: date | None = None

    def __post_init__(self) -> None:
        if self.title is not None:
            if not self.title.strip():
                raise ValueError("title must be null or non-blank")
            if len(self.title) > 500:
                raise ValueError("title must be at most 500 characters")
        category = self.category.strip()
        if not category:
            raise ValueError("category must be non-blank")
        if len(category) > 128:
            raise ValueError("category must be at most 128 characters")
        object.__setattr__(self, "category", category)
        if self.source_description is not None:
            if not self.source_description.strip():
                raise ValueError("source_description must be null or non-blank")
            if len(self.source_description) > 4000:
                raise ValueError("source_description must be at most 4000 characters")
        normalized_urls: list[str] = []
        if len(self.source_urls) > 20:
            raise ValueError("source_urls must contain at most 20 values")
        for item in self.source_urls:
            value = item.strip()
            if not value:
                raise ValueError("source_urls cannot contain blank values")
            if len(value) > 2048:
                raise ValueError("source URL must be at most 2048 characters")
            normalized_urls.append(value)
        object.__setattr__(self, "source_urls", tuple(normalized_urls))


@dataclass(frozen=True)
class DirectNoteSummarySnapshot:
    observation_id: UUID
    submission_id: UUID | None
    source_id: str
    resource_ref: UUID
    resource_version_ref: UUID
    content_sha256: str
    byte_size: int
    media_type: str | None
    captured_at: datetime
    project_keys: tuple[str, ...]
    title: str | None
    title_supplied: bool
    display_title: str
    category: str
    category_supplied: bool
    source_description: str | None
    source_urls: tuple[str, ...]
    source_event_time: datetime | None
    source_date: date | None
    source_time_precision: str
    search_ready: bool


@dataclass(frozen=True)
class DirectNoteDetailSnapshot(DirectNoteSummarySnapshot):
    content: str


@dataclass(frozen=True)
class DirectNoteRecentPage:
    items: tuple[DirectNoteSummarySnapshot, ...]
    next_cursor: str | None


def capture_metadata_payload(
    metadata: DirectNoteCaptureMetadataInput,
) -> dict[str, object]:
    return {
        "metadata_version": DIRECT_NOTE_CAPTURE_METADATA_VERSION,
        "title": metadata.title,
        "title_supplied": metadata.title is not None,
        "category": metadata.category,
        "category_supplied": metadata.category_supplied,
        "source_description": metadata.source_description,
        "source_urls": list(metadata.source_urls),
        "source_date": metadata.source_date,
    }


def capture_metadata_digest(metadata: DirectNoteCaptureMetadataInput) -> str:
    return _request_digest(capture_metadata_payload(metadata))


def _capture_request_fingerprint(
    *,
    operation_id: UUID,
    principal_ref: str,
    source_id: str,
    project_key: str,
    resource_version_ref: UUID,
    content_sha256: str,
    source_event_time: datetime | None,
    metadata: DirectNoteCaptureMetadataInput,
) -> str:
    return _request_digest(
        {
            "metadata_version": DIRECT_NOTE_CAPTURE_METADATA_VERSION,
            "operation_id": operation_id,
            "principal_ref": principal_ref,
            "source_id": source_id,
            "project_key": project_key,
            "resource_version_ref": resource_version_ref,
            "content_sha256": content_sha256,
            "source_event_time": source_event_time,
            "capture_metadata": capture_metadata_payload(metadata),
        }
    )


def persist_direct_note_capture_metadata(
    session,
    *,
    observation_id: UUID,
    operation_id: UUID,
    resource_version_ref: UUID,
    principal_ref: str,
    source_id: str,
    project_key: str,
    content_sha256: str,
    source_event_time: datetime | None,
    metadata: DirectNoteCaptureMetadataInput,
) -> DirectNoteCaptureMetadataRecord:
    if metadata.source_date is not None and source_event_time is not None:
        raise KnowledgeInvariantError(
            "direct note source_date and source_event_time are mutually exclusive"
        )
    source_time_precision = (
        "date"
        if metadata.source_date is not None
        else "timestamp"
        if source_event_time is not None
        else "unsupplied"
    )
    fingerprint = _capture_request_fingerprint(
        operation_id=operation_id,
        principal_ref=principal_ref,
        source_id=source_id,
        project_key=project_key,
        resource_version_ref=resource_version_ref,
        content_sha256=content_sha256,
        source_event_time=source_event_time,
        metadata=metadata,
    )
    expected = {
        "operation_id": operation_id,
        "resource_version_ref": resource_version_ref,
        "principal_ref": principal_ref,
        "project_key": project_key,
        "metadata_version": DIRECT_NOTE_CAPTURE_METADATA_VERSION,
        "request_fingerprint": fingerprint,
        "title": metadata.title,
        "title_supplied": metadata.title is not None,
        "category": metadata.category,
        "category_supplied": metadata.category_supplied,
        "source_description": metadata.source_description,
        "source_urls": list(metadata.source_urls),
        "source_date": metadata.source_date,
        "source_time_precision": source_time_precision,
    }
    existing = session.get(DirectNoteCaptureMetadataRecord, observation_id)
    if existing is not None:
        actual = {
            "operation_id": existing.operation_id,
            "resource_version_ref": existing.resource_version_ref,
            "principal_ref": existing.principal_ref,
            "project_key": existing.project_key,
            "metadata_version": existing.metadata_version,
            "request_fingerprint": existing.request_fingerprint,
            "title": existing.title,
            "title_supplied": bool(existing.title_supplied),
            "category": existing.category,
            "category_supplied": bool(existing.category_supplied),
            "source_description": existing.source_description,
            "source_urls": list(existing.source_urls or []),
            "source_date": existing.source_date,
            "source_time_precision": existing.source_time_precision,
        }
        if actual != expected:
            raise KnowledgeInvariantError(
                "direct note capture metadata identity was reused with different values"
            )
        return existing

    row = DirectNoteCaptureMetadataRecord(
        observation_id=observation_id,
        **expected,
    )
    session.add(row)
    session.flush()
    return row


def _encode_cursor(observed_at: datetime, observation_id: UUID) -> str:
    payload = json.dumps(
        {
            "observed_at": _as_utc(observed_at).isoformat(),
            "observation_id": str(observation_id),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(value: str) -> tuple[datetime, UUID]:
    try:
        padding = "=" * (-len(value) % 4)
        payload = json.loads(urlsafe_b64decode(value + padding).decode("utf-8"))
        observed_at = datetime.fromisoformat(str(payload["observed_at"]))
        observation_id = UUID(str(payload["observation_id"]))
    except Exception as exc:
        raise ValueError("invalid recent-note cursor") from exc
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("invalid recent-note cursor")
    return _as_utc(observed_at), observation_id


class DirectNoteReadKnowledgeKernel(ResourceServiceKnowledgeKernel):
    """Bounded canonical-note list/read path independent of text publication."""

    def _comparison_time(self, value: datetime) -> datetime:
        value = _as_utc(value)
        if self.session.get_bind().dialect.name == "sqlite":
            return value.replace(tzinfo=None)
        return value

    def _read_exact_content(self, version: ResourceVersion) -> str:
        if not self.resource_version_serving_eligible(version.ref_id):
            raise KnowledgeSourceUnavailableError("knowledge source is unavailable")
        if version.content_digest_algo != "sha256":
            raise KnowledgeInvariantError(
                "direct note original read supports only SHA-256 ResourceVersions"
            )
        content = self.artifact_store.read_bytes(version.artifact_key)
        if len(content) != int(version.byte_size):
            raise KnowledgeInvariantError(
                "direct note byte size does not match immutable artifact"
            )
        if sha256(content).hexdigest() != version.content_digest:
            raise KnowledgeInvariantError(
                "direct note digest does not match immutable artifact"
            )
        try:
            return content.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise KnowledgeInvariantError(
                "direct note original is not strict UTF-8"
            ) from exc

    def _search_ready(self, resource_version_ref: UUID) -> bool:
        generation_id = self.session.scalar(
            select(DerivedGeneration.generation_id).where(
                DerivedGeneration.derived_kind == DerivedKind.TEXT.value,
                DerivedGeneration.status == GenerationStatus.CURRENT.value,
            )
        )
        if generation_id is None:
            return False
        return (
            self.session.execute(
                select(TextGenerationSource.resource_version_ref)
                .where(
                    TextGenerationSource.generation_id == generation_id,
                    TextGenerationSource.resource_version_ref == resource_version_ref,
                )
                .limit(1)
            ).scalar_one_or_none()
            is not None
        )

    def _legacy_project_keys(self, observation_id: UUID) -> tuple[str, ...]:
        values = self.session.scalars(
            select(GovernedSnapshotProjectRecord.project_key)
            .where(GovernedSnapshotProjectRecord.observation_id == observation_id)
            .distinct()
            .order_by(GovernedSnapshotProjectRecord.project_key)
        ).all()
        return tuple(values)

    @staticmethod
    def _display_title(content: str, title: str | None) -> str:
        if title is not None:
            return title
        for line in content.splitlines():
            if line.strip():
                return line.strip()
        return "Untitled note"

    def _snapshot(
        self,
        observation: GovernedSourceObservationRecord,
        binding: GovernedSourceBindingRecord,
        *,
        include_content: bool,
    ) -> DirectNoteSummarySnapshot | DirectNoteDetailSnapshot:
        version = self.session.get(ResourceVersion, observation.resource_version_ref)
        if version is None:
            raise KnowledgeInvariantError(
                "direct note observation references a missing ResourceVersion"
            )
        if version.resource_ref_id != binding.resource_ref:
            raise KnowledgeInvariantError(
                "direct note observation ResourceVersion does not belong to its binding"
            )
        content = self._read_exact_content(version)
        metadata = self.session.get(
            DirectNoteCaptureMetadataRecord,
            observation.observation_id,
        )
        if metadata is not None:
            if metadata.resource_version_ref != observation.resource_version_ref:
                raise KnowledgeInvariantError(
                    "direct note capture metadata references a different ResourceVersion"
                )
            if metadata.principal_ref != binding.origin_scope:
                raise KnowledgeInvariantError(
                    "direct note capture metadata principal does not match source binding"
                )
            reconstructed_metadata = DirectNoteCaptureMetadataInput(
                title=metadata.title,
                category=metadata.category,
                category_supplied=bool(metadata.category_supplied),
                source_description=metadata.source_description,
                source_urls=tuple(metadata.source_urls or []),
                source_date=metadata.source_date,
            )
            expected_fingerprint = _capture_request_fingerprint(
                operation_id=metadata.operation_id,
                principal_ref=metadata.principal_ref,
                source_id=binding.item_key,
                project_key=metadata.project_key,
                resource_version_ref=metadata.resource_version_ref,
                content_sha256=version.content_digest,
                source_event_time=observation.source_event_time,
                metadata=reconstructed_metadata,
            )
            if metadata.request_fingerprint != expected_fingerprint:
                raise KnowledgeInvariantError(
                    "direct note capture metadata fingerprint does not match its bound capture"
                )
            expected_precision = (
                "date"
                if metadata.source_date is not None
                else "timestamp"
                if observation.source_event_time is not None
                else "unsupplied"
            )
            if metadata.source_time_precision != expected_precision:
                raise KnowledgeInvariantError(
                    "direct note capture source-time precision is inconsistent"
                )
            if bool(metadata.title_supplied) != (metadata.title is not None):
                raise KnowledgeInvariantError(
                    "direct note capture title-supplied marker is inconsistent"
                )

            project_keys = (metadata.project_key,)
            title = metadata.title
            title_supplied = bool(metadata.title_supplied)
            category = metadata.category
            category_supplied = bool(metadata.category_supplied)
            source_description = metadata.source_description
            source_urls = tuple(metadata.source_urls or [])
            source_date = metadata.source_date
            source_time_precision = metadata.source_time_precision
            submission_id = metadata.operation_id
        else:
            project_keys = self._legacy_project_keys(observation.observation_id)
            title = None
            title_supplied = False
            category = "Note"
            category_supplied = False
            source_description = None
            source_urls = ()
            source_date = None
            source_time_precision = (
                "timestamp"
                if observation.source_event_time is not None
                else "unsupplied"
            )
            submission_id = None

        base = dict(
            observation_id=observation.observation_id,
            submission_id=submission_id,
            source_id=binding.item_key,
            resource_ref=binding.resource_ref,
            resource_version_ref=version.ref_id,
            content_sha256=version.content_digest,
            byte_size=int(version.byte_size),
            media_type=version.media_type,
            captured_at=_as_utc(observation.observed_at),
            project_keys=project_keys,
            title=title,
            title_supplied=title_supplied,
            display_title=self._display_title(content, title),
            category=category,
            category_supplied=category_supplied,
            source_description=source_description,
            source_urls=source_urls,
            source_event_time=(
                _as_utc(observation.source_event_time)
                if observation.source_event_time is not None
                else None
            ),
            source_date=source_date,
            source_time_precision=source_time_precision,
            search_ready=self._search_ready(version.ref_id),
        )
        if include_content:
            return DirectNoteDetailSnapshot(content=content, **base)
        return DirectNoteSummarySnapshot(**base)

    def read_note(
        self,
        *,
        principal_ref: str,
        observation_id: UUID,
    ) -> DirectNoteDetailSnapshot:
        row = self.session.execute(
            select(
                GovernedSourceObservationRecord,
                GovernedSourceBindingRecord,
            )
            .join(
                GovernedSourceBindingRecord,
                GovernedSourceBindingRecord.source_identity_digest
                == GovernedSourceObservationRecord.source_identity_digest,
            )
            .where(
                GovernedSourceObservationRecord.observation_id == observation_id,
                GovernedSourceObservationRecord.producer_id == _DIRECT_NOTE_PRODUCER_ID,
                GovernedSourceBindingRecord.source_kind == _DIRECT_NOTE_SOURCE_KIND,
                GovernedSourceBindingRecord.origin_scope == principal_ref,
            )
        ).one_or_none()
        if row is None:
            raise KnowledgeSourceUnavailableError("knowledge source is unavailable")
        observation, binding = row
        result = self._snapshot(observation, binding, include_content=True)
        assert isinstance(result, DirectNoteDetailSnapshot)
        return result

    def recent_notes(
        self,
        *,
        principal_ref: str,
        limit: int = 25,
        cursor: str | None = None,
    ) -> DirectNoteRecentPage:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        scan_time: datetime | None = None
        scan_id: UUID | None = None
        if cursor is not None:
            scan_time, scan_id = _decode_cursor(cursor)

        eligible: list[DirectNoteSummarySnapshot] = []
        batch_size = max(50, min(250, limit * 4))
        while len(eligible) < limit + 1:
            stmt = (
                select(
                    GovernedSourceObservationRecord,
                    GovernedSourceBindingRecord,
                )
                .join(
                    GovernedSourceBindingRecord,
                    GovernedSourceBindingRecord.source_identity_digest
                    == GovernedSourceObservationRecord.source_identity_digest,
                )
                .where(
                    GovernedSourceObservationRecord.producer_id
                    == _DIRECT_NOTE_PRODUCER_ID,
                    GovernedSourceBindingRecord.source_kind
                    == _DIRECT_NOTE_SOURCE_KIND,
                    GovernedSourceBindingRecord.origin_scope == principal_ref,
                )
            )
            if scan_time is not None and scan_id is not None:
                comparison_time = self._comparison_time(scan_time)
                stmt = stmt.where(
                    or_(
                        GovernedSourceObservationRecord.observed_at < comparison_time,
                        and_(
                            GovernedSourceObservationRecord.observed_at
                            == comparison_time,
                            GovernedSourceObservationRecord.observation_id < scan_id,
                        ),
                    )
                )
            rows = self.session.execute(
                stmt.order_by(
                    GovernedSourceObservationRecord.observed_at.desc(),
                    GovernedSourceObservationRecord.observation_id.desc(),
                ).limit(batch_size)
            ).all()
            if not rows:
                break

            for observation, binding in rows:
                scan_time = _as_utc(observation.observed_at)
                scan_id = observation.observation_id
                if not self.resource_version_serving_eligible(
                    observation.resource_version_ref
                ):
                    continue
                result = self._snapshot(observation, binding, include_content=False)
                assert isinstance(result, DirectNoteSummarySnapshot)
                eligible.append(result)
                if len(eligible) >= limit + 1:
                    break
            if len(rows) < batch_size:
                break

        next_cursor = None
        if len(eligible) > limit:
            last = eligible[limit - 1]
            next_cursor = _encode_cursor(last.captured_at, last.observation_id)
        return DirectNoteRecentPage(
            items=tuple(eligible[:limit]),
            next_cursor=next_cursor,
        )
