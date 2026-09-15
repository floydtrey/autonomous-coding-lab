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
    completed = subprocess.run(
        argv,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        check=False,
        capture_output=capture,
        text=True,
    )
    if check and completed.returncode != 0:
        command = " ".join(argv)
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        raise RuntimeError(
            f"command failed ({completed.returncode}): {command}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
    return completed


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


def _load_and_validate_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("manifest_id") != _EXPECTED_MANIFEST_ID:
        raise RuntimeError("SR-2 host qualification manifest id changed")
    if manifest.get("source_commit") != _EXPECTED_SOURCE_COMMIT:
        raise RuntimeError("SR-2 host qualification source commit changed")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or {
        item.get("source_document_key") for item in entries if isinstance(item, dict)
    } != _EXPECTED_DOCUMENT_KEYS:
        raise RuntimeError("SR-2 host qualification corpus changed")
    return manifest


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


def _validate_results(first: dict, recovered: dict) -> None:
    generation_id = first["receipt"]["resulting_text_generation_id"]
    if not generation_id:
        raise AssertionError("SR-2 first apply did not publish a text generation")
    if first["current"]["generation_id"] != generation_id:
        raise AssertionError("SR-2 first apply did not serve its resulting generation")
    if first["current"]["retrieval_mode"] != "segment":
        raise AssertionError("SR-2 first apply did not serve segment retrieval")
    if not first["current"]["results"]:
        raise AssertionError("SR-2 current retrieval returned no results")
    if first["historical_default"]["results"]:
        raise AssertionError("SR-2 superseded material leaked into default retrieval")

    historical = first["historical_explicit"]["results"]
    expected_path = "docs/architecture/knowledge-core/PAUSE_HANDOFF.md"
    if [item["source_path"] for item in historical] != [expected_path]:
        raise AssertionError("SR-2 explicit historical retrieval was not exact")
    if historical[0]["lifecycle_state"] != "superseded":
        raise AssertionError("SR-2 historical material lost superseded lifecycle")
    if historical[0]["source_version"] != _EXPECTED_SOURCE_COMMIT:
        raise AssertionError("SR-2 historical retrieval lost exact source commit")

    initial = first["snapshot"]
    expected_counts = {
        "bindings": 3,
        "receipts": 1,
        "observations": 3,
        "resources": 3,
        "resource_versions": 3,
        "text_generation_sources": 3,
    }
    for key, value in expected_counts.items():
        if initial["counts"][key] != value:
            raise AssertionError(f"unexpected {key}: {initial['counts'][key]}")
    if initial["counts"]["segment_rows"] <= 3:
        raise AssertionError("SR-2 host qualification did not persist segment rows")
    if len(initial["provenance"]) != 3:
        raise AssertionError("expected exactly three SR-2 provenance observations")
    if not all(item["artifact_verified"] for item in initial["provenance"]):
        raise AssertionError("one or more SR-2 artifacts failed integrity verification")
    if not initial["structural_reconstruction_verified"]:
        raise AssertionError("SR-2 exact structural reconstruction did not verify")
    if not initial["profile_identity_verified"]:
        raise AssertionError("SR-2 profile identity did not verify")
    if not initial["projection_lineage_verified"]:
        raise AssertionError("SR-2 projection lineage did not verify")

    if recovered["current_before_replay"]["generation_id"] != generation_id:
        raise AssertionError("SR-2 serving generation changed across PostgreSQL restart")
    if recovered["current_before_replay"]["retrieval_mode"] != "segment":
        raise AssertionError("SR-2 segment serving mode changed across restart")
    recovered_history = recovered["historical_before_replay"]["results"]
    if [item["source_path"] for item in recovered_history] != [expected_path]:
        raise AssertionError("SR-2 historical retrieval changed across restart")
    if not recovered["plan"]["replay"]:
        raise AssertionError("SR-2 recovery plan did not identify exact accepted replay")
    if recovered["receipt"] != first["receipt"]:
        raise AssertionError("SR-2 exact replay returned a different receipt")
    if recovered["before"] != recovered["after"]:
        raise AssertionError("SR-2 exact replay mutated durable state after restart")
    if recovered["after"] != initial:
        raise AssertionError("SR-2 persistent snapshot changed across restart/replay")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "SR-2 intended-host persistence/recovery qualification. "
            "This is a bounded test harness, not a production deployment."
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
                "exact_replay_verified": True,
                "segment_serving_verified": True,
                "artifact_integrity_verified": True,
                "structural_reconstruction_verified": True,
                "profile_identity_verified": True,
                "projection_lineage_verified": True,
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
