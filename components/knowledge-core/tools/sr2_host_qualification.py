from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import uuid4


_POSTGRES_USER = "knowledge_core_sr2_host"
_POSTGRES_DB = "knowledge_core_sr2_host"
_POSTGRES_IMAGE = "postgres:18"
_EXPECTED_MANIFEST_ID = "sr2-g22-real-document-pilot-v1"
_EXPECTED_SOURCE_COMMIT = "bb42835442c03478da2b61c3f79b1c41c26e4e92"
_EXPECTED_DOCUMENT_KEYS = {
    "sr2-g22-contract",
    "sr2-g22-current-state",
    "sr2-g22-pause-handoff",
}


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        check=check,
        capture_output=capture,
        text=True,
    )


def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(["docker", *args], check=check)


def _require_empty_state_root(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise RuntimeError(f"state root is not a directory: {path}")
        if any(path.iterdir()):
            raise RuntimeError(
                "SR-2 intended-host qualification requires a new empty state root; "
                f"existing content found: {path}"
            )
    else:
        path.mkdir(parents=True, exist_ok=False)


def _require_port_available(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"loopback port {port} is not available") from exc


def _load_and_validate_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("manifest_id") != _EXPECTED_MANIFEST_ID:
        raise RuntimeError("SR-2 host qualification requires the accepted G22 manifest")
    if manifest.get("source_commit") != _EXPECTED_SOURCE_COMMIT:
        raise RuntimeError("SR-2 host qualification source commit differs from accepted G22")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("SR-2 host qualification manifest entries are invalid")
    keys = {entry.get("source_document_key") for entry in entries}
    if keys != _EXPECTED_DOCUMENT_KEYS or len(entries) != 3:
        raise RuntimeError("SR-2 host qualification requires exactly the three G22 sources")
    if manifest.get("retirements") != []:
        raise RuntimeError("SR-2 host qualification does not authorize retirements")
    return manifest


def _verify_manifest_sources(repository_root: Path, manifest: dict) -> None:
    source_commit = manifest["source_commit"]
    commit_check = _run(
        [
            "git",
            "-C",
            str(repository_root),
            "cat-file",
            "-e",
            f"{source_commit}^{{commit}}",
        ],
        check=False,
    )
    if commit_check.returncode != 0:
        raise RuntimeError(
            "SR-2 pinned source commit is not present in the local Git repository; "
            "fetch full history before qualification"
        )

    for entry in manifest["entries"]:
        resolved = _run(
            [
                "git",
                "-C",
                str(repository_root),
                "rev-parse",
                f"{source_commit}:{entry['path']}",
            ]
        ).stdout.strip()
        if resolved != entry["git_blob_sha"]:
            raise RuntimeError(
                f"manifest Git blob mismatch for {entry['path']}: "
                f"expected {entry['git_blob_sha']}, got {resolved}"
            )


def _wait_for_postgres(container_name: str, timeout_seconds: int = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    last = ""
    while time.monotonic() < deadline:
        result = _docker(
            "exec",
            container_name,
            "pg_isready",
            "-U",
            _POSTGRES_USER,
            "-d",
            _POSTGRES_DB,
            check=False,
        )
        last = (result.stdout or result.stderr or "").strip()
        if result.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError(f"PostgreSQL did not become ready: {last}")


def _run_phase(
    *,
    component_root: Path,
    repository_root: Path,
    manifest_path: Path,
    artifact_root: Path,
    database_url: str,
    phase: str,
) -> dict:
    env = os.environ.copy()
    env["KNOWLEDGE_CORE_DATABASE_URL"] = database_url
    completed = _run(
        [
            sys.executable,
            str(component_root / "tools" / "sr2_host_phase.py"),
            phase,
            "--artifact-root",
            str(artifact_root),
            "--repository-root",
            str(repository_root),
            "--manifest",
            str(manifest_path),
        ],
        cwd=component_root,
        env=env,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def _result_identities(search: dict) -> list[tuple[str, int | None, str | None]]:
    return [
        (
            item["resource_version_ref"],
            item["segment"]["segment_ordinal"] if item.get("segment") else None,
            item["segment"]["segment_key"] if item.get("segment") else None,
        )
        for item in search["results"]
    ]


def _assert_segment_search(search: dict, *, expected_generation_id: str) -> None:
    if search["generation_id"] != expected_generation_id:
        raise AssertionError("public retrieval is not serving the accepted SR-2 generation")
    if search["retrieval_mode"] != "segment":
        raise AssertionError("public retrieval did not dispatch to SR-2 segment serving")
    if not search.get("generation_config_digest"):
        raise AssertionError("public SR-2 retrieval omitted generation config identity")
    for key in (
        "structural_profile_id",
        "structural_profile_digest",
        "projection_profile_id",
        "projection_profile_digest",
    ):
        if not search.get(key):
            raise AssertionError(f"public SR-2 retrieval omitted {key}")
    if any(item.get("segment") is None for item in search["results"]):
        raise AssertionError("SR-2 retrieval returned a whole-ResourceVersion hit")


def _assert_query_behavior(
    *,
    current: dict,
    contract: dict,
    historical_default: dict,
    historical_explicit: dict,
    generation_id: str,
) -> None:
    for search in (current, contract, historical_default, historical_explicit):
        _assert_segment_search(search, expected_generation_id=generation_id)

    if not current["results"]:
        raise AssertionError("current SR-2 host query returned no results")
    if (
        current["results"][0]["segment"]["source_document_key"]
        != "sr2-g22-current-state"
    ):
        raise AssertionError("current SR-2 host query did not resolve to CURRENT_STATE")

    if not contract["results"]:
        raise AssertionError("contract SR-2 host query returned no results")
    if contract["results"][0]["segment"]["source_document_key"] != "sr2-g22-contract":
        raise AssertionError("contract SR-2 host query did not resolve to SR-1")

    leaked = [
        item
        for item in historical_default["results"]
        if item["segment"]["source_document_key"] == "sr2-g22-pause-handoff"
    ]
    if leaked:
        raise AssertionError("superseded G22 handoff leaked into default SR-2 retrieval")

    explicit = [
        item
        for item in historical_explicit["results"]
        if item["segment"]["source_document_key"] == "sr2-g22-pause-handoff"
    ]
    if not explicit:
        raise AssertionError("explicit historical SR-2 retrieval did not recover G22 handoff")
    if any(item["lifecycle_state"] != "superseded" for item in explicit):
        raise AssertionError("historical SR-2 hits lost effective superseded lifecycle")


def _validate_results(first: dict, recovered: dict) -> None:
    generation_id = first["receipt"]["resulting_text_generation_id"]
    if not generation_id:
        raise AssertionError("first SR-2 host apply did not publish a text generation")
    if first["receipt"]["status"] != "settled":
        raise AssertionError("first SR-2 host import receipt did not settle")
    if first["plan"]["replay"]:
        raise AssertionError("first SR-2 host apply unexpectedly used replay")

    _assert_query_behavior(
        current=first["current"],
        contract=first["contract"],
        historical_default=first["historical_default"],
        historical_explicit=first["historical_explicit"],
        generation_id=generation_id,
    )

    initial = first["snapshot"]
    if initial["serving_generation"]["generation_id"] != generation_id:
        raise AssertionError("snapshot current generation differs from import receipt")
    expected_counts = {
        "bindings": 3,
        "receipts": 1,
        "observations": 3,
        "resources": 3,
        "resource_versions": 3,
        "generations": 1,
        "resource_search_rows": 0,
        "text_generation_sources": 3,
        "text_generation_profiles": 1,
    }
    for key, expected in expected_counts.items():
        actual = initial["counts"][key]
        if actual != expected:
            raise AssertionError(f"unexpected durable {key}: expected {expected}, got {actual}")
    if initial["counts"]["segment_search_rows"] <= 3:
        raise AssertionError("SR-2 qualification did not persist section-level segment rows")
    if len(initial["provenance"]) != 3:
        raise AssertionError("expected exactly three governed G22 provenance records")
    if not all(item["artifact_verified"] for item in initial["provenance"]):
        raise AssertionError("one or more SR-2 canonical artifacts failed verification")

    if not recovered["plan"]["replay"]:
        raise AssertionError("recovery plan did not identify exact accepted replay")
    if recovered["receipt"] != first["receipt"]:
        raise AssertionError("exact replay returned a different SR-2 receipt")

    _assert_query_behavior(
        current=recovered["current_before_replay"],
        contract=recovered["contract_before_replay"],
        historical_default=recovered["historical_default_before_replay"],
        historical_explicit=recovered["historical_explicit_before_replay"],
        generation_id=generation_id,
    )

    if _result_identities(recovered["current_before_replay"]) != _result_identities(
        first["current"]
    ):
        raise AssertionError("current segment identities changed across PostgreSQL restart")
    if _result_identities(recovered["contract_before_replay"]) != _result_identities(
        first["contract"]
    ):
        raise AssertionError("contract segment identities changed across PostgreSQL restart")
    if _result_identities(
        recovered["historical_explicit_before_replay"]
    ) != _result_identities(first["historical_explicit"]):
        raise AssertionError("historical segment identities changed across PostgreSQL restart")

    if recovered["before"] != initial:
        raise AssertionError("durable SR-2 snapshot changed across PostgreSQL restart")
    if recovered["after"] != recovered["before"]:
        raise AssertionError("exact SR-2 replay mutated durable state after restart")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bounded SR-2 intended-host restart/recovery qualification. "
            "Exercises segment serving; it is not a production deployment."
        )
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--state-root", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--port", type=int, default=55433)
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove the stopped qualification container and Docker volume after success.",
    )
    args = parser.parse_args()

    component_root = Path(__file__).resolve().parents[1]
    repository_root = Path(args.repository_root).resolve()
    state_root = Path(args.state_root).resolve()
    manifest_path = (
        Path(args.manifest).resolve()
        if args.manifest
        else repository_root
        / "docs"
        / "architecture"
        / "knowledge-core"
        / "SR2_G22_REAL_DOCUMENT_PILOT_MANIFEST.json"
    )
    evidence_path = state_root / "SR2_HOST_QUALIFICATION_EVIDENCE.json"
    artifact_root = state_root / "artifacts"

    if not manifest_path.is_file():
        raise RuntimeError(f"SR-2 host qualification manifest does not exist: {manifest_path}")
    manifest = _load_and_validate_manifest(manifest_path)
    _verify_manifest_sources(repository_root, manifest)
    _require_port_available(args.port)
    if state_root == repository_root or repository_root in state_root.parents:
        raise RuntimeError("SR-2 host qualification state root must be outside the source Git repository")

    docker_version = _docker("version", "--format", "{{.Server.Version}}").stdout.strip()
    _require_empty_state_root(state_root)
    artifact_root.mkdir(parents=False, exist_ok=False)

    token = uuid4().hex[:12]
    container_name = f"knowledge-core-sr2-host-{token}"
    volume_name = f"knowledge-core-sr2-host-pg-{token}"
    database_url = (
        f"postgresql+psycopg://{_POSTGRES_USER}@127.0.0.1:{args.port}/{_POSTGRES_DB}"
    )

    evidence: dict = {
        "schema_version": 1,
        "qualification": "SR-2-intended-host",
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "manifest_id": manifest["manifest_id"],
        "source_commit": manifest["source_commit"],
        "manifest_path": str(manifest_path),
        "repository_root": str(repository_root),
        "state_root": str(state_root),
        "artifact_root": str(artifact_root),
        "postgres_image": _POSTGRES_IMAGE,
        "docker_server_version": docker_version,
        "postgres_container": container_name,
        "postgres_volume": volume_name,
        "loopback_port": args.port,
        "machine_reboot_performed": False,
        "backup_restore_performed": False,
    }

    container_created = False
    volume_created = False
    success = False
    try:
        _docker("volume", "create", volume_name)
        volume_created = True
        _docker(
            "run",
            "-d",
            "--name",
            container_name,
            "--mount",
            f"source={volume_name},target=/var/lib/postgresql",
            "-e",
            f"POSTGRES_USER={_POSTGRES_USER}",
            "-e",
            f"POSTGRES_DB={_POSTGRES_DB}",
            "-e",
            "POSTGRES_HOST_AUTH_METHOD=trust",
            "-p",
            f"127.0.0.1:{args.port}:5432",
            _POSTGRES_IMAGE,
        )
        container_created = True
        _wait_for_postgres(container_name)

        env = os.environ.copy()
        env["KNOWLEDGE_CORE_DATABASE_URL"] = database_url
        _run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=component_root,
            env=env,
        )

        first = _run_phase(
            component_root=component_root,
            repository_root=repository_root,
            manifest_path=manifest_path,
            artifact_root=artifact_root,
            database_url=database_url,
            phase="apply",
        )

        _docker("restart", container_name)
        _wait_for_postgres(container_name)

        recovered = _run_phase(
            component_root=component_root,
            repository_root=repository_root,
            manifest_path=manifest_path,
            artifact_root=artifact_root,
            database_url=database_url,
            phase="recovery",
        )
        _validate_results(first, recovered)

        evidence.update(
            {
                "status": "success",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "postgres_restart_verified": True,
                "application_reconstruction_verified": True,
                "segment_serving_verified": True,
                "current_historical_retrieval_verified": True,
                "artifact_integrity_verified": True,
                "structural_reconstruction_verified": True,
                "profile_identity_verified": True,
                "governed_provenance_verified": True,
                "exact_replay_verified": True,
                "first": first,
                "recovered": recovered,
            }
        )
        success = True
    except Exception as exc:
        evidence.update(
            {
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
        raise
    finally:
        if container_created:
            _docker("stop", container_name, check=False)
        state_root.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if success and args.cleanup:
            if container_created:
                _docker("rm", container_name, check=False)
            if volume_created:
                _docker("volume", "rm", volume_name, check=False)

    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
