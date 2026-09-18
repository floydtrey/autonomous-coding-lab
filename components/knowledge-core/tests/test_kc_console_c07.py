from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from knowledge_core.api.app import create_app
from knowledge_core.api.bootstrap_admission import BootstrapAdmission
from knowledge_core.api.bootstrap_contract import BootstrapContract
from knowledge_core.api.console_admission import ConsoleOwnerAdmission, ConsoleOwnerContract
from knowledge_core.application.direct_note_capture import DirectNoteReadKnowledgeKernel
from knowledge_core.application.direct_note_store import (
    DirectNotePublicationResult,
    DirectNoteStoreKnowledgeKernel,
)
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.storage.database import (
    create_database_engine,
    create_session_factory,
    create_test_schema,
)


_BOOTSTRAP_KEY = "c07-worker-bootstrap-key"
_OWNER_KEY = "c07-console-owner-key"
_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)


def _bootstrap() -> BootstrapAdmission:
    return BootstrapAdmission(
        contract=BootstrapContract(),
        api_key=_BOOTSTRAP_KEY,
    )


def _console() -> ConsoleOwnerAdmission:
    return ConsoleOwnerAdmission(
        contract=ConsoleOwnerContract(
            allowed_projects=("inbox",),
            default_project="inbox",
        ),
        owner_key=_OWNER_KEY,
    )


def _app(sessions, artifacts):
    return create_app(
        session_factory=sessions,
        artifact_store=artifacts,
        bootstrap_admission=_bootstrap(),
        canonical_store_authority_evaluator=None,
        console_owner_admission=_console(),
        unified_graph_search_binding=None,
    )


def _login(client: TestClient) -> str:
    response = client.post(
        "/v1/kc/console/session",
        headers={"X-KC-Console-Key": _OWNER_KEY},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def _save(client: TestClient, csrf: str, key: str, content: str):
    response = client.post(
        "/v1/kc/console/notes",
        headers={
            "X-KC-Console-CSRF": csrf,
            "Idempotency-Key": key,
        },
        json={
            "content": content,
            "title": f"Title {key}",
            "category": "Note",
            "project": "inbox",
            "source_description": "C07 export qualification.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def c07_sqlite(tmp_path: Path, monkeypatch):
    engine = create_database_engine(
        f"sqlite+pysqlite:///{tmp_path / 'c07.db'}",
        sqlite_test_mode=True,
    )
    create_test_schema(engine)
    sessions = create_session_factory(engine)
    artifacts = LocalArtifactStore(tmp_path / "artifacts")

    def no_text_publication(self, canonical):
        return DirectNotePublicationResult(
            text_state="failed",
            generation_id=None,
            snapshot_digest=None,
            error_code="C07NoTextPublication",
        )

    monkeypatch.setattr(
        DirectNoteStoreKnowledgeKernel,
        "publish_note_text",
        no_text_publication,
    )

    try:
        yield engine, sessions, artifacts
    finally:
        engine.dispose()


def test_c07_export_is_complete_beyond_recent_page_limit_and_contains_originals(
    c07_sqlite,
):
    _engine, sessions, artifacts = c07_sqlite

    with TestClient(_app(sessions, artifacts)) as client:
        assert client.get("/v1/kc/console/export").status_code == 401
        csrf = _login(client)

        expected = {}
        for ordinal in range(105):
            key = f"c07-export-{ordinal:03d}"
            content = (
                f"C07 export note {ordinal:03d} — exact Unicode Ω\n"
                f"second line {ordinal:03d} with trailing spaces  \n"
            )
            saved = _save(client, csrf, key, content)
            expected[saved["note"]["observation_id"]] = content
            assert saved["text_state"] == "failed"

        recent = client.get("/v1/kc/console/notes?limit=100")
        assert recent.status_code == 200, recent.text
        assert len(recent.json()["items"]) == 100
        assert recent.json()["next_cursor"]

        exported = client.get("/v1/kc/console/export")
        assert exported.status_code == 200, exported.text
        payload = exported.json()
        assert payload["schema_version"] == "kc-console-export-v1"
        assert payload["note_count"] == 105
        assert len(payload["notes"]) == 105
        assert payload["boundary_observation_id"]
        assert "next_cursor" not in payload
        actual = {
            item["observation_id"]: item["content"]
            for item in payload["notes"]
        }
        assert actual == expected
        assert all(item["projects"] == ["inbox"] for item in payload["notes"])
        assert all(item["sha256"] for item in payload["notes"])

        page = client.get("/console/")
        script = client.get("/console/app.js")
        assert page.status_code == script.status_code == 200
        assert "Export notes" in page.text
        assert "/v1/kc/console/export" in script.text
        assert "no partial export was downloaded" in script.text


def test_c07_export_failure_is_explicit_and_never_partial(
    c07_sqlite,
    monkeypatch,
):
    _engine, sessions, artifacts = c07_sqlite

    def fail_export(self, *, principal_ref):
        raise RuntimeError("forced C07 export failure")

    monkeypatch.setattr(
        DirectNoteReadKnowledgeKernel,
        "export_notes",
        fail_export,
    )

    with TestClient(_app(sessions, artifacts)) as client:
        _login(client)
        response = client.get("/v1/kc/console/export")
        assert response.status_code == 503
        assert response.json()["detail"]["error_code"] == "CONSOLE_EXPORT_UNAVAILABLE"
        assert "partial export" in response.json()["detail"]["message"]
        assert "notes" not in response.json()


def _require_postgres_engine():
    if not _POSTGRES_URL:
        pytest.skip("C07 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("C07 qualification requires PostgreSQL")
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
            "TRUNCATE TABLE "
            + ", ".join(tables)
            + " RESTART IDENTITY CASCADE"
        )


@pytest.mark.postgresql
def test_c07_postgres_export_survives_application_reconstruction(tmp_path: Path):
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    sessions = create_session_factory(engine)
    artifacts = LocalArtifactStore(tmp_path / "c07-postgres-artifacts")

    try:
        first_ids = []
        with TestClient(_app(sessions, artifacts)) as client:
            csrf = _login(client)
            for ordinal in range(3):
                saved = _save(
                    client,
                    csrf,
                    f"c07-postgres-{ordinal}",
                    f"C07 PostgreSQL persistent export sentinel {ordinal}\n",
                )
                assert saved["text_state"] == "indexed"
                first_ids.append(saved["note"]["observation_id"])

            export = client.get("/v1/kc/console/export")
            assert export.status_code == 200, export.text
            assert export.json()["note_count"] == 3
            assert {
                item["observation_id"]
                for item in export.json()["notes"]
            } == set(first_ids)

        # Rebuild FastAPI/session composition against the same durable stores.
        with TestClient(_app(sessions, artifacts)) as client:
            _login(client)
            export = client.get("/v1/kc/console/export")
            assert export.status_code == 200, export.text
            assert export.json()["note_count"] == 3
            assert {
                item["observation_id"]
                for item in export.json()["notes"]
            } == set(first_ids)
            for observation_id in first_ids:
                original = client.get(
                    f"/v1/kc/console/notes/{observation_id}"
                )
                assert original.status_code == 200, original.text
                assert "persistent export sentinel" in original.json()["content"]
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()


def test_c07_windows_helpers_keep_daily_start_bounded():
    component = Path(__file__).resolve().parents[1]
    windows = component / "tools" / "windows"

    start = (windows / "Start-KCConsole.ps1").read_text(encoding="utf-8")
    stop = (windows / "Stop-KCConsole.ps1").read_text(encoding="utf-8")
    migrate = (windows / "Apply-KCConsoleMigration.ps1").read_text(encoding="utf-8")
    prepare = (windows / "Prepare-KCConsoleConfig.ps1").read_text(encoding="utf-8")
    shortcut = (windows / "Install-KCConsoleShortcut.ps1").read_text(encoding="utf-8")
    disable_gateway = (windows / "Disable-KCLegacyGateway.ps1").read_text(
        encoding="utf-8"
    )
    restore_gateway = (windows / "Restore-KCLegacyGateway.ps1").read_text(
        encoding="utf-8"
    )

    assert "kc_bootstrap_service.py" in start
    assert "KNOWLEDGE_CORE_POSTGRES_CONTAINER" in start
    assert "No process was killed" in start
    assert "alembic upgrade" not in start
    assert "taskkill" not in start.lower()
    assert "llama-server" not in start.lower()
    assert "cowork-server" not in start.lower()
    assert "alembic upgrade head" in migrate
    assert "Get-Content -LiteralPath $ExistingLauncherPath" in prepare
    assert "& $ExistingLauncherPath" not in prepare
    assert "Knowledge Core.lnk" in shortcut
    assert "update --restart=no" in disable_gateway
    assert " stop $Name" in disable_gateway
    assert " docker rm" not in disable_gateway.lower()
    assert "--restart=$Policy" in restore_gateway
    assert "Stop-Process" in stop

    operations = (
        component.parents[1]
        / "docs"
        / "architecture"
        / "knowledge-core"
        / "KC_CONSOLE_V1_OPERATIONS.md"
    ).read_text(encoding="utf-8")
    assert "knowledge-core-sr2-host-62329544d83c" in operations
    assert "Do **not** use it as the daily notebook launcher" in operations
    assert "five genuine notes" in operations.lower()


@pytest.mark.parametrize(
    "script_name",
    [
        "Start-KCConsole.ps1",
        "Stop-KCConsole.ps1",
        "Apply-KCConsoleMigration.ps1",
        "Prepare-KCConsoleConfig.ps1",
        "Install-KCConsoleShortcut.ps1",
        "Disable-KCLegacyGateway.ps1",
        "Restore-KCLegacyGateway.ps1",
    ],
)
def test_c07_windows_powershell_helpers_parse_when_pwsh_is_available(script_name):
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("pwsh is not available on this runner")

    component = Path(__file__).resolve().parents[1]
    script = component / "tools" / "windows" / script_name
    escaped = str(script).replace("'", "''")
    command = (
        "$ErrorActionPreference='Stop';"
        "$null=[ScriptBlock]::Create([IO.File]::ReadAllText('"
        + escaped
        + "'))"
    )
    result = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
