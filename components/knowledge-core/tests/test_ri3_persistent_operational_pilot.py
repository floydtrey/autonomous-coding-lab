from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from knowledge_core.storage.database import create_database_engine


_POSTGRES_URL = os.environ.get("KNOWLEDGE_CORE_POSTGRES_TEST_URL") or os.environ.get(
    "KNOWLEDGE_CORE_DATABASE_URL"
)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_PATH = (
    _REPO_ROOT
    / "docs"
    / "architecture"
    / "knowledge-core"
    / "RI3_PERSISTENT_PILOT_MANIFEST.json"
)
_SOURCE_COMMIT = "3e675f0ffb584d6b270e0a7c52428c74a5496be3"
_EXPECTED_PATHS = {
    "docs/architecture/knowledge-core/CURRENT_STATE.md": {
        "blob": "d6f33cb5aa98888e4c600bbcc7fd71ccb3f37c71",
        "lifecycle": "current",
    },
    "docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI2.md": {
        "blob": "bc12a15dbac70e1ba538e313ce87dfed41b9e831",
        "lifecycle": "current",
    },
    "docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md": {
        "blob": "457472f7928994ab40e1c8f4faea7e70e93b7449",
        "lifecycle": "superseded",
    },
}


def _require_postgres_engine() -> Engine:
    if not _POSTGRES_URL:
        pytest.skip("RI-3 PostgreSQL URL is not configured")
    engine = create_database_engine(_POSTGRES_URL)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("RI-3 requires PostgreSQL")
    return engine


def _truncate_kernel_tables(engine: Engine) -> None:
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


def _run_phase(phase: str, artifact_root: Path) -> dict:
    env = os.environ.copy()
    env["KNOWLEDGE_CORE_DATABASE_URL"] = _POSTGRES_URL
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("ri3_pilot_process.py")),
            phase,
            "--artifact-root",
            str(artifact_root),
            "--repository-root",
            str(_REPO_ROOT),
            "--manifest",
            str(_MANIFEST_PATH),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.mark.postgresql
def test_ri3_persistent_operational_import_survives_process_restart_and_replay(
    tmp_path,
):
    engine = _require_postgres_engine()
    _truncate_kernel_tables(engine)
    artifact_root = tmp_path / "ri3-persistent-artifacts"
    try:
        manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        assert manifest["source_commit"] == _SOURCE_COMMIT
        assert manifest["previous_manifest_digest"] is None
        assert manifest["retirements"] == []
        assert {
            entry["path"]: {
                "blob": entry["git_blob_sha"],
                "lifecycle": entry["retrieval_lifecycle"],
            }
            for entry in manifest["entries"]
        } == _EXPECTED_PATHS

        source_check = subprocess.run(
            [
                "git",
                "-C",
                str(_REPO_ROOT),
                "cat-file",
                "-e",
                f"{_SOURCE_COMMIT}^{{commit}}",
            ],
            capture_output=True,
            text=True,
        )
        assert source_check.returncode == 0, (
            "RI-3 requires the pinned parent source commit to be present; "
            "CI checkout must retain sufficient Git history"
        )

        first = _run_phase("apply", artifact_root)
        assert first["phase"] == "apply"
        assert first["plan"]["replay"] is False
        assert first["receipt"]["status"] == "settled"
        generation_id = first["receipt"]["resulting_text_generation_id"]
        assert generation_id
        assert first["current"]["generation_id"] == generation_id
        assert first["current"]["results"]
        assert all(
            hit["lifecycle_state"] != "superseded"
            for hit in first["current"]["results"]
        )
        assert first["historical_default"]["results"] == []
        historical = first["historical_explicit"]["results"]
        assert [hit["source_path"] for hit in historical] == [
            "docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md"
        ]
        assert historical[0]["lifecycle_state"] == "superseded"
        assert historical[0]["source_version"] == _SOURCE_COMMIT

        initial_snapshot = first["snapshot"]
        assert initial_snapshot["counts"]["bindings"] == 3
        assert initial_snapshot["counts"]["receipts"] == 1
        assert initial_snapshot["counts"]["observations"] == 3
        assert initial_snapshot["counts"]["resources"] == 3
        assert initial_snapshot["counts"]["resource_versions"] == 3
        # `search_rows` is the historical RF-2 ResourceTextSearch table count.
        # The live repository API now publishes SR-2, so RI-3 restart/replay must
        # prove serving and canonical persistence without requiring that obsolete
        # derived storage shape. The original RI-3 acceptance remains preserved at
        # its historical checkpoint.
        assert len(initial_snapshot["provenance"]) == 3
        for row in initial_snapshot["provenance"]:
            expected = _EXPECTED_PATHS[row["path"]]
            assert row["source_commit"] == _SOURCE_COMMIT
            assert row["git_blob_sha"] == expected["blob"]
            assert row["content_digest_algo"] == "sha256"
            assert row["artifact_verified"] is True

        artifact_files = [
            path
            for path in (artifact_root / "sha256").rglob("*")
            if path.is_file()
        ]
        assert len(artifact_files) == 3

        restarted = _run_phase("restart", artifact_root)
        assert restarted["phase"] == "restart"
        assert restarted["serving_before_replay"]["generation_id"] == generation_id
        assert restarted["serving_before_replay"]["results"]
        historical_after_restart = restarted["historical_before_replay"]["results"]
        assert [hit["source_path"] for hit in historical_after_restart] == [
            "docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI1.md"
        ]
        assert restarted["plan"]["replay"] is True
        assert restarted["receipt"] == first["receipt"]
        assert restarted["before"] == restarted["after"]
        assert restarted["after"] == initial_snapshot
    finally:
        _truncate_kernel_tables(engine)
        engine.dispose()
