from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from fastapi import Cookie, Header, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles

from knowledge_core.api._base_app import SessionFactory
from knowledge_core.api.bootstrap_contract import BOOTSTRAP_PRINCIPAL_REF
from knowledge_core.api.console_admission import (
    ConsoleAuthenticationError,
    ConsoleOwnerAdmission,
    ConsoleSessionError,
    ConsoleSessionManager,
)
from knowledge_core.api.notebook_schemas import (
    ConsoleExportResponse,
    ConsoleNoteSaveRequest,
    ConsoleNoteSaveResponse,
    ConsoleSearchEvidenceResponse,
    ConsoleSearchHitResponse,
    ConsoleSearchRequest,
    ConsoleSearchResponse,
    ConsoleSessionResponse,
    ConsoleSourceOriginalResponse,
    ConsoleStatusResponse,
    NotebookNoteDetailResponse,
    NotebookRecentResponse,
    detail_response_from_domain,
    summary_response_from_domain,
)
from knowledge_core.application.direct_note_capture import (
    DirectNoteCaptureMetadataInput,
    DirectNoteReadKnowledgeKernel,
    capture_metadata_digest,
)
from knowledge_core.application.consumer_read import ConsumerReadKnowledgeKernel
from knowledge_core.application.direct_note_store import (
    DirectNoteStoreKnowledgeKernel,
    direct_note_operation_id,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.authority.console_store import (
    ConsoleCanonicalStoreAuthorityEvaluator,
)
from knowledge_core.authority.store import (
    CanonicalStoreAuthorityRequest,
    require_canonical_store_authority,
)


_SESSION_COOKIE = "kc_console_session"
_SESSION_PATH = "/v1/kc/console/session"
_NOTES_PATH = "/v1/kc/console/notes"
_SEARCH_PATH = "/v1/kc/console/search"
_STATUS_PATH = "/v1/kc/console/status"
_SOURCES_PATH = "/v1/kc/console/sources"
_EXPORT_PATH = "/v1/kc/console/export"


def install_console_routes(
    app,
    *,
    session_factory: SessionFactory,
    artifact_store: LocalArtifactStore,
    admission: ConsoleOwnerAdmission,
) -> None:
    """Install opt-in owner-only notebook routes and packaged static UI."""

    manager = ConsoleSessionManager()
    store_authority = ConsoleCanonicalStoreAuthorityEvaluator(
        frozenset(admission.contract.allowed_projects)
    )

    def _session_record(session_id: str | None):
        try:
            return manager.get(session_id)
        except ConsoleSessionError as exc:
            raise HTTPException(
                status_code=401,
                detail="console session is not authenticated",
            ) from exc

    def _write_session(
        session_id: str | None,
        csrf_token: str | None,
    ):
        try:
            return manager.require_csrf(
                session_id=session_id,
                supplied_csrf=csrf_token,
            )
        except ConsoleSessionError as exc:
            raise HTTPException(
                status_code=403,
                detail="console session or CSRF token is invalid",
            ) from exc

    def _session_response(record) -> ConsoleSessionResponse:
        return ConsoleSessionResponse(
            csrf_token=record.csrf_token,
            allowed_projects=list(admission.contract.allowed_projects),
            default_project=admission.contract.default_project,
            expires_at=record.expires_at,
        )

    @app.post(
        _SESSION_PATH,
        response_model=ConsoleSessionResponse,
    )
    def console_login(
        response: Response,
        x_kc_console_key: str | None = Header(
            default=None,
            alias="X-KC-Console-Key",
        ),
    ) -> ConsoleSessionResponse:
        try:
            admission.authenticate(x_kc_console_key)
        except ConsoleAuthenticationError as exc:
            raise HTTPException(
                status_code=401,
                detail="console owner authentication failed",
            ) from exc
        record = manager.issue()
        response.set_cookie(
            key=_SESSION_COOKIE,
            value=record.session_id,
            httponly=True,
            samesite="strict",
            secure=False,
            path="/v1/kc/console",
        )
        return _session_response(record)

    @app.get(
        _SESSION_PATH,
        response_model=ConsoleSessionResponse,
    )
    def console_session(
        kc_console_session: str | None = Cookie(
            default=None,
            alias=_SESSION_COOKIE,
        ),
    ) -> ConsoleSessionResponse:
        return _session_response(_session_record(kc_console_session))

    @app.delete(
        _SESSION_PATH,
        status_code=204,
    )
    def console_logout(
        response: Response,
        kc_console_session: str | None = Cookie(
            default=None,
            alias=_SESSION_COOKIE,
        ),
        x_kc_console_csrf: str | None = Header(
            default=None,
            alias="X-KC-Console-CSRF",
        ),
    ) -> Response:
        _write_session(kc_console_session, x_kc_console_csrf)
        manager.revoke(kc_console_session)
        response.status_code = 204
        response.delete_cookie(
            _SESSION_COOKIE,
            path="/v1/kc/console",
        )
        return response

    @app.post(
        _NOTES_PATH,
        response_model=ConsoleNoteSaveResponse,
        status_code=201,
    )
    def console_save_note(
        body: ConsoleNoteSaveRequest,
        idempotency_key: str = Header(alias="Idempotency-Key"),
        kc_console_session: str | None = Cookie(
            default=None,
            alias=_SESSION_COOKIE,
        ),
        x_kc_console_csrf: str | None = Header(
            default=None,
            alias="X-KC-Console-CSRF",
        ),
    ) -> ConsoleNoteSaveResponse:
        _write_session(kc_console_session, x_kc_console_csrf)
        project = body.project or admission.contract.default_project
        metadata = DirectNoteCaptureMetadataInput(
            title=body.title,
            category=body.category or "Note",
            category_supplied=body.category is not None,
            source_description=body.source_description,
            source_urls=tuple(body.source_urls),
            source_date=body.source_date,
        )
        try:
            operation_id = direct_note_operation_id(
                principal_ref=BOOTSTRAP_PRINCIPAL_REF,
                idempotency_key=idempotency_key,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        require_canonical_store_authority(
            store_authority,
            CanonicalStoreAuthorityRequest(
                caller_principal_ref=BOOTSTRAP_PRINCIPAL_REF,
                operation_id=operation_id,
                project_key=project,
                content_sha256=sha256(body.content.encode("utf-8")).hexdigest(),
                source_id=None,
                source_event_time=body.source_event_time,
                capture_metadata_digest=capture_metadata_digest(metadata),
            ),
        )

        with session_factory() as session:
            kernel = DirectNoteStoreKnowledgeKernel(
                session,
                artifact_store=artifact_store,
            )
            canonical = kernel.store_note_operation(
                operation_id=operation_id,
                caller_principal_ref=BOOTSTRAP_PRINCIPAL_REF,
                content=body.content,
                project_key=project,
                source_id=None,
                source_event_time=body.source_event_time,
                capture_metadata=metadata,
            )
            publication = kernel.publish_note_text(canonical)
            reader = DirectNoteReadKnowledgeKernel(
                session,
                artifact_store=artifact_store,
            )
            note = reader.read_note(
                principal_ref=BOOTSTRAP_PRINCIPAL_REF,
                observation_id=canonical.observation_id,
            )

        return ConsoleNoteSaveResponse(
            text_state=publication.text_state,
            text_generation_id=publication.generation_id,
            text_snapshot_digest=publication.snapshot_digest,
            text_error_code=publication.error_code,
            note=detail_response_from_domain(note),
        )

    @app.get(
        _NOTES_PATH,
        response_model=NotebookRecentResponse,
    )
    def console_recent_notes(
        limit: int = Query(default=25, ge=1, le=100),
        cursor: str | None = Query(default=None),
        kc_console_session: str | None = Cookie(
            default=None,
            alias=_SESSION_COOKIE,
        ),
    ) -> NotebookRecentResponse:
        _session_record(kc_console_session)
        with session_factory() as session:
            reader = DirectNoteReadKnowledgeKernel(
                session,
                artifact_store=artifact_store,
            )
            try:
                page = reader.recent_notes(
                    principal_ref=BOOTSTRAP_PRINCIPAL_REF,
                    limit=limit,
                    cursor=cursor,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return NotebookRecentResponse(
            items=[
                summary_response_from_domain(item)
                for item in page.items
            ],
            next_cursor=page.next_cursor,
        )

    @app.get(
        _NOTES_PATH + "/{observation_id}",
        response_model=NotebookNoteDetailResponse,
    )
    def console_get_note(
        observation_id: UUID,
        kc_console_session: str | None = Cookie(
            default=None,
            alias=_SESSION_COOKIE,
        ),
    ) -> NotebookNoteDetailResponse:
        _session_record(kc_console_session)
        with session_factory() as session:
            reader = DirectNoteReadKnowledgeKernel(
                session,
                artifact_store=artifact_store,
            )
            note = reader.read_note(
                principal_ref=BOOTSTRAP_PRINCIPAL_REF,
                observation_id=observation_id,
            )
        return detail_response_from_domain(note)

    @app.post(
        _SEARCH_PATH,
        response_model=ConsoleSearchResponse,
    )
    def console_search(
        body: ConsoleSearchRequest,
        kc_console_session: str | None = Cookie(
            default=None,
            alias=_SESSION_COOKIE,
        ),
    ) -> ConsoleSearchResponse:
        _session_record(kc_console_session)
        try:
            with session_factory() as session:
                reader = ConsumerReadKnowledgeKernel(
                    session,
                    artifact_store=artifact_store,
                )
                snapshot = reader.search_text(
                    query=body.query,
                    limit=body.limit,
                    include_superseded=False,
                )
                note_reader = DirectNoteReadKnowledgeKernel(
                    session,
                    artifact_store=artifact_store,
                )
                results: list[ConsoleSearchHitResponse] = []
                for rank, hit in enumerate(snapshot.results, start=1):
                    if hit.content_digest_algo != "sha256":
                        raise RuntimeError(
                            "console search encountered unsupported content digest"
                        )
                    segment = hit.segment
                    source_kind = (
                        segment.source_kind if segment is not None else None
                    )
                    source_id = (
                        segment.item_key if segment is not None else None
                    )
                    projects = (
                        list(segment.project_keys) if segment is not None else []
                    )
                    captured_at = (
                        segment.source_observed_at
                        if segment is not None
                        else hit.observed_at
                    )
                    source_event_time = (
                        segment.source_event_time
                        if segment is not None
                        else None
                    )
                    source_revision_time = (
                        segment.source_revision_time
                        if segment is not None
                        else None
                    )
                    source_classification = (
                        segment.source_classification
                        if segment is not None
                        else None
                    )
                    source_line_start = (
                        segment.source_line_start if segment is not None else None
                    )
                    source_line_end = (
                        segment.source_line_end if segment is not None else None
                    )
                    heading_path = (
                        list(segment.heading_path) if segment is not None else []
                    )

                    note_observation_id = None
                    category = None
                    display_title = ""
                    open_original_kind = "source"

                    if (
                        segment is not None
                        and segment.source_kind == "local.user-note"
                        and segment.origin_scope == BOOTSTRAP_PRINCIPAL_REF
                        and segment.governed_source_observation_id is not None
                    ):
                        note = note_reader.read_note(
                            principal_ref=BOOTSTRAP_PRINCIPAL_REF,
                            observation_id=segment.governed_source_observation_id,
                        )
                        if note.resource_version_ref != hit.resource_version_ref:
                            raise RuntimeError(
                                "search note evidence resolved to a different original"
                            )
                        note_observation_id = note.observation_id
                        display_title = note.display_title
                        category = note.category
                        source_id = note.source_id
                        projects = list(note.project_keys)
                        captured_at = note.captured_at
                        source_event_time = note.source_event_time
                        open_original_kind = "note"
                    else:
                        if heading_path:
                            last_heading = heading_path[-1].get("display_text")
                            if isinstance(last_heading, str) and last_heading.strip():
                                display_title = last_heading.strip()
                        if not display_title:
                            display_title = (
                                source_id
                                or hit.source_path
                                or hit.repository
                                or "Knowledge source"
                            )

                    results.append(
                        ConsoleSearchHitResponse(
                            rank=rank,
                            resource_id=hit.resource_ref,
                            version_id=hit.resource_version_ref,
                            sha256=hit.content_digest,
                            lexical_score=hit.lexical_score,
                            excerpt=hit.content,
                            display_title=display_title,
                            category=category,
                            note_observation_id=note_observation_id,
                            open_original_kind=open_original_kind,
                            evidence=ConsoleSearchEvidenceResponse(
                                source_kind=source_kind,
                                source_classification=source_classification,
                                source_id=source_id,
                                projects=projects,
                                captured_at=captured_at,
                                source_event_time=source_event_time,
                                source_revision_time=source_revision_time,
                                repository=hit.repository,
                                source_path=hit.source_path,
                                source_version=hit.source_version,
                                source_line_start=source_line_start,
                                source_line_end=source_line_end,
                                heading_path=heading_path,
                                lifecycle_state=hit.lifecycle_state.value,
                                authority_rank=hit.authority_rank,
                            ),
                        )
                    )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Search is unavailable; your query was not completed.",
                    "error_code": "CONSOLE_SEARCH_UNAVAILABLE",
                },
            ) from exc

        return ConsoleSearchResponse(
            query=snapshot.query,
            retrieval_mode=snapshot.retrieval_mode,
            generation_id=snapshot.generation_id,
            source_revision_highwater=snapshot.source_revision_highwater,
            results=results,
            result_state="matches" if results else "empty",
        )

    @app.get(
        _SOURCES_PATH + "/{resource_version_ref}",
        response_model=ConsoleSourceOriginalResponse,
    )
    def console_get_source_original(
        resource_version_ref: UUID,
        kc_console_session: str | None = Cookie(
            default=None,
            alias=_SESSION_COOKIE,
        ),
    ) -> ConsoleSourceOriginalResponse:
        _session_record(kc_console_session)
        with session_factory() as session:
            reader = ConsumerReadKnowledgeKernel(
                session,
                artifact_store=artifact_store,
            )
            item = reader.read_current_source(
                resource_version_ref=resource_version_ref,
            )
        if item.content_digest_algo != "sha256":
            raise HTTPException(
                status_code=503,
                detail="current source uses an unsupported content digest",
            )
        return ConsoleSourceOriginalResponse(
            resource_id=item.resource_ref,
            version_id=item.resource_version_ref,
            sha256=item.content_digest,
            byte_size=item.byte_size,
            media_type=item.media_type,
            content=item.content,
        )

    @app.get(
        _EXPORT_PATH,
        response_model=ConsoleExportResponse,
    )
    def console_export_notes(
        kc_console_session: str | None = Cookie(
            default=None,
            alias=_SESSION_COOKIE,
        ),
    ) -> ConsoleExportResponse:
        _session_record(kc_console_session)
        try:
            with session_factory() as session:
                reader = DirectNoteReadKnowledgeKernel(
                    session,
                    artifact_store=artifact_store,
                )
                export = reader.export_notes(
                    principal_ref=BOOTSTRAP_PRINCIPAL_REF,
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Note export is unavailable; no partial export was returned.",
                    "error_code": "CONSOLE_EXPORT_UNAVAILABLE",
                },
            ) from exc

        return ConsoleExportResponse(
            exported_at=datetime.now(timezone.utc),
            captured_through=export.captured_through,
            boundary_observation_id=export.boundary_observation_id,
            note_count=len(export.notes),
            notes=[
                detail_response_from_domain(note)
                for note in export.notes
            ],
        )

    @app.get(
        _STATUS_PATH,
        response_model=ConsoleStatusResponse,
    )
    def console_status(
        kc_console_session: str | None = Cookie(
            default=None,
            alias=_SESSION_COOKIE,
        ),
    ) -> ConsoleStatusResponse:
        _session_record(kc_console_session)
        try:
            with session_factory() as session:
                reader = ConsumerReadKnowledgeKernel(
                    session,
                    artifact_store=artifact_store,
                )
                status = reader.retrieval_status()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Knowledge Core read status is unavailable.",
                    "error_code": "CONSOLE_STATUS_UNAVAILABLE",
                },
            ) from exc

        return ConsoleStatusResponse(
            canonical_revision=status.canonical_revision,
            text_state=status.text_state.value,
            text_generation_id=status.text_generation_id,
            text_source_revision_highwater=status.text_source_revision_highwater,
            text_source_count=status.text_source_count,
            retrieval_mode=status.retrieval_mode,
            lineage_mode=status.lineage_mode,
            search_state=(
                "ready" if status.text_state.value == "ready" else "empty"
            ),
            write_projects=list(admission.contract.allowed_projects),
        )

    console_directory = Path(__file__).resolve().parents[1] / "console"
    if not console_directory.is_dir():
        raise RuntimeError("packaged KC console assets are missing")
    app.mount(
        "/console",
        StaticFiles(directory=console_directory, html=True),
        name="kc-console",
    )
