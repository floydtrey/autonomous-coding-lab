from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.application.governed_snapshot_policy import (
    validate_complete_snapshot,
)
from knowledge_core.application.governed_source_evidence import (
    GovernedSourceEvidenceKnowledgeKernel,
)
from knowledge_core.application.section_publication_v2 import (
    PublicationPredecessorConflictError,
    SourceNeutralSectionPublicationKnowledgeKernel,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.domain.assertions import KnowledgeInvariantError
from knowledge_core.domain.governed_sources import (
    GovernedRetrievalSnapshot,
    GovernedSnapshotExclusion,
    GovernedSnapshotMember,
)
from knowledge_core.storage.control_models import Operation
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core.storage.resource_models import Resource


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_BOOTSTRAP_KEY = "task2e1-bootstrap-key"


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("Task 2E.1 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("Task 2E.1 requires PostgreSQL")
    return engine


def _truncate_kernel_tables(engine) -> None:
    inspector = inspect(engine)
    preparer = engine.dialect.identifier_preparer
    tables: list[str] = []
    for schema in ("kc", "kc_control", "kc_derived"):
        for table_name in inspector.get_table_names(schema=schema):
            tables.append(
                f"{preparer.quote_schema(schema)}.{preparer.quote(table_name)}"
            )
    if not tables:
        raise AssertionError("Knowledge Core schemas are not migrated")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"
        )


@pytest.fixture()
def task2e1_engine():
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    try:
        yield engine
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def _admission() -> BootstrapAdmission:
    return BootstrapAdmission(
        contract=BootstrapContract(),
        api_key=_BOOTSTRAP_KEY,
    )


def _headers(key: str) -> dict[str, str]:
    return {
        "X-Knowledge-Key": _BOOTSTRAP_KEY,
        "Idempotency-Key": key,
    }


def _body(
    content: str,
    *,
    source_id: str,
    project: str,
) -> dict[str, str]:
    return {
        "content": content,
        "project": project,
        "source_type": "user_note",
        "source_id": source_id,
    }


def _app(sessions, store):
    return create_app(
        session_factory=sessions,
        artifact_store=store,
        bootstrap_admission=_admission(),
    )


def test_generic_complete_snapshot_validation_is_not_repository_owned():
    source_digest = "sha256:" + "1" * 64
    observation_digest = "sha256:" + "2" * 64
    decision_digest = "sha256:" + "3" * 64
    observation_id = UUID("11111111-1111-1111-1111-111111111111")
    member = GovernedSnapshotMember(
        source_identity_digest=source_digest,
        resource_ref=UUID("22222222-2222-2222-2222-222222222222"),
        resource_version_ref=UUID("33333333-3333-3333-3333-333333333333"),
        observation_id=observation_id,
        observation_digest=observation_digest,
        decision_id=UUID("44444444-4444-4444-4444-444444444444"),
        decision_digest=decision_digest,
    )
    snapshot = GovernedRetrievalSnapshot(
        selection_policy_id="kc-complete-corpus-selection-v1",
        created_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        members=(member,),
        exclusions=(
            GovernedSnapshotExclusion(
                source_identity_digest=source_digest,
                observation_id=observation_id,
                reason_code="fixture-overlap",
            ),
        ),
    )

    with pytest.raises(KnowledgeInvariantError, match="both selects and excludes"):
        validate_complete_snapshot(snapshot)


@pytest.mark.postgresql
def test_task2e1_rejects_oversized_project_before_canonical_writes(
    task2e1_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task2e1_engine)
    store = LocalArtifactStore(tmp_path / "task2e1-project-bound")
    with TestClient(_app(sessions, store)) as client:
        response = client.post(
            "/v1/kc/store",
            json=_body(
                "must never reach canonical storage\n",
                source_id="oversized-project",
                project="p" * 256,
            ),
            headers=_headers("oversized-project-1"),
        )
        assert response.status_code == 422

    session = sessions()
    try:
        assert session.scalar(select(func.count()).select_from(Operation)) == 0
        assert session.scalar(select(func.count()).select_from(Resource)) == 0
    finally:
        session.close()


@pytest.mark.postgresql
def test_task2e1_same_source_update_preserves_project_memberships(
    task2e1_engine,
    tmp_path: Path,
):
    sessions = create_session_factory(task2e1_engine)
    store = LocalArtifactStore(tmp_path / "task2e1-project-union")

    with TestClient(_app(sessions, store)) as client:
        first = client.post(
            "/v1/kc/store",
            json=_body(
                "shared source first version\n",
                source_id="shared-note",
                project="knowledge-core",
            ),
            headers=_headers("shared-note-1"),
        )
        assert first.status_code == 201, first.text
        assert first.json()["text_state"] == "indexed"

        second = client.post(
            "/v1/kc/store",
            json=_body(
                "shared source second version\n",
                source_id="shared-note",
                project="local-ai",
            ),
            headers=_headers("shared-note-2"),
        )
        assert second.status_code == 201, second.text
        second_data = second.json()
        assert second_data["text_state"] == "indexed"
        assert second_data["resource_id"] == first.json()["resource_id"]

    session = sessions()
    try:
        snapshot = GovernedSourceEvidenceKnowledgeKernel(session).load_snapshot(
            second_data["text_snapshot_digest"]
        )
        matching = [
            member
            for member in snapshot.members
            if str(member.resource_ref) == second_data["resource_id"]
        ]
        assert len(matching) == 1
        assert matching[0].project_keys == ("knowledge-core", "local-ai")
    finally:
        session.close()


@pytest.mark.postgresql
def test_task2e1_only_predecessor_conflict_is_pending(
    task2e1_engine,
    tmp_path: Path,
    monkeypatch,
):
    sessions = create_session_factory(task2e1_engine)
    store = LocalArtifactStore(tmp_path / "task2e1-pending-classification")

    with TestClient(_app(sessions, store)) as client:
        baseline = client.post(
            "/v1/kc/store",
            json=_body(
                "baseline corpus\n",
                source_id="baseline",
                project="knowledge-core",
            ),
            headers=_headers("baseline-1"),
        )
        assert baseline.status_code == 201, baseline.text
        assert baseline.json()["text_state"] == "indexed"

    def conflict(self, **_kwargs):
        raise PublicationPredecessorConflictError("forced predecessor race")

    monkeypatch.setattr(
        SourceNeutralSectionPublicationKnowledgeKernel,
        "promote_segment_generation",
        conflict,
    )
    with TestClient(_app(sessions, store)) as client:
        response = client.post(
            "/v1/kc/store",
            json=_body(
                "retryable publication\n",
                source_id="retryable",
                project="knowledge-core",
            ),
            headers=_headers("retryable-1"),
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["canonical_state"] == "stored"
        assert payload["text_state"] == "pending"
        assert payload["text_error_code"] == "PublicationPredecessorConflictError"


@pytest.mark.postgresql
def test_task2e1_permanent_invariant_failure_is_failed_not_pending(
    task2e1_engine,
    tmp_path: Path,
    monkeypatch,
):
    sessions = create_session_factory(task2e1_engine)
    store = LocalArtifactStore(tmp_path / "task2e1-failed-classification")

    def invariant_failure(self, **_kwargs):
        raise KnowledgeInvariantError("forced non-retryable invariant")

    monkeypatch.setattr(
        SourceNeutralSectionPublicationKnowledgeKernel,
        "build_segment_generation_candidate",
        invariant_failure,
    )
    with TestClient(_app(sessions, store)) as client:
        response = client.post(
            "/v1/kc/store",
            json=_body(
                "permanent derived failure\n",
                source_id="failed-note",
                project="knowledge-core",
            ),
            headers=_headers("failed-note-1"),
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["canonical_state"] == "stored"
        assert payload["text_state"] == "failed"
        assert payload["text_error_code"] == "KnowledgeInvariantError"
