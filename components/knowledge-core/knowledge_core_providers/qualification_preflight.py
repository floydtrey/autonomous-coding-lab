from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import shutil
import socket
import subprocess
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from sqlalchemy import create_engine, text


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    required: bool
    status: str
    detail: str
    suggestion: str | None = None


@dataclass(frozen=True)
class PreflightReport:
    checks: tuple[PreflightCheck, ...]

    @property
    def ready(self) -> bool:
        return all(
            check.status == "PASS"
            for check in self.checks
            if check.required
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "checks": [asdict(check) for check in self.checks],
        }


def _run(command: list[str], *, timeout: float = 8.0) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    output = (completed.stdout or completed.stderr or "").strip()
    return completed.returncode == 0, output


def tcp_check(host: str, port: int, *, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True, f"{host}:{port} reachable"
    except Exception as exc:
        return False, f"{host}:{port} unavailable: {type(exc).__name__}: {exc}"


def _model_aliases(name: str) -> set[str]:
    normalized = name.strip()
    if not normalized:
        return set()
    aliases = {normalized}
    if ":" not in normalized:
        aliases.add(f"{normalized}:latest")
    elif normalized.endswith(":latest"):
        aliases.add(normalized[:-7])
    return aliases


def model_is_installed(requested: str, installed: set[str]) -> bool:
    wanted = _model_aliases(requested)
    available: set[str] = set()
    for item in installed:
        available.update(_model_aliases(item))
    return bool(wanted & available)


def _ollama_tags(base_url: str) -> tuple[bool, set[str], str]:
    parsed = urlsplit(base_url)
    if not parsed.scheme or not parsed.netloc:
        return False, set(), f"invalid Ollama base URL: {base_url}"
    root = f"{parsed.scheme}://{parsed.netloc}"
    request = Request(f"{root}/api/tags", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=4.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return False, set(), f"{type(exc).__name__}: {exc}"
    names = {
        str(item.get("name") or item.get("model") or "").strip()
        for item in payload.get("models", [])
        if str(item.get("name") or item.get("model") or "").strip()
    }
    return True, names, f"{len(names)} installed model(s)"


def evidence_container_name(evidence_file: Path | None) -> tuple[str | None, str | None]:
    if evidence_file is None:
        return None, None
    try:
        payload = json.loads(Path(evidence_file).read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    name = str(payload.get("postgres_container") or "").strip()
    return (name or None), None


def run_graphiti_preflight(
    *,
    artifact_root: Path,
    database_url: str | None,
    evidence_file: Path | None,
    falkor_host: str,
    falkor_port: int,
    falkor_container: str,
    falkor_ui_port: int,
    ollama_base_url: str,
    llm_model: str,
    embed_model: str,
) -> PreflightReport:
    checks: list[PreflightCheck] = []

    docker = shutil.which("docker")
    docker_ready = False
    if docker is None:
        checks.append(
            PreflightCheck(
                "Docker daemon",
                True,
                "FAIL",
                "docker executable was not found",
                "Install/start Docker Desktop before this qualification.",
            )
        )
    else:
        docker_ready, detail = _run([docker, "info", "--format", "{{.ServerVersion}}"])
        checks.append(
            PreflightCheck(
                "Docker daemon",
                True,
                "PASS" if docker_ready else "FAIL",
                detail or "Docker daemon reachable",
                None if docker_ready else "Start Docker Desktop, then rerun preflight.",
            )
        )

    kc_container, evidence_error = evidence_container_name(evidence_file)
    if evidence_error is not None:
        checks.append(
            PreflightCheck(
                "KC host evidence",
                False,
                "WARN",
                evidence_error,
                "Verify SR2_HOST_QUALIFICATION_EVIDENCE.json for container diagnostics.",
            )
        )
    elif kc_container:
        if docker_ready:
            ok, detail = _run([docker, "inspect", "-f", "{{.State.Running}}", kc_container])
            running = ok and detail.strip().lower() == "true"
            checks.append(
                PreflightCheck(
                    "KC PostgreSQL container",
                    True,
                    "PASS" if running else "FAIL",
                    f"{kc_container}: {'running' if running else detail or 'stopped'}",
                    None if running else f"docker start {kc_container}",
                )
            )
        else:
            checks.append(
                PreflightCheck(
                    "KC PostgreSQL container",
                    True,
                    "FAIL",
                    f"{kc_container}: Docker daemon unavailable",
                    "Start Docker Desktop first.",
                )
            )
    else:
        checks.append(
            PreflightCheck(
                "KC PostgreSQL container",
                False,
                "WARN",
                "container name unavailable; direct SQL connectivity will still be checked",
            )
        )

    if docker_ready:
        ok, detail = _run([docker, "inspect", "-f", "{{.State.Running}}", falkor_container])
        running = ok and detail.strip().lower() == "true"
        checks.append(
            PreflightCheck(
                "FalkorDB container",
                True,
                "PASS" if running else "FAIL",
                f"{falkor_container}: {'running' if running else detail or 'stopped'}",
                None if running else f"docker start {falkor_container}",
            )
        )
        if running:
            ping_ok, ping_detail = _run([docker, "exec", falkor_container, "redis-cli", "PING"])
            checks.append(
                PreflightCheck(
                    "FalkorDB graph service",
                    True,
                    "PASS" if ping_ok and "PONG" in ping_detail.upper() else "FAIL",
                    ping_detail or "redis-cli returned no output",
                    None if ping_ok else f"docker logs {falkor_container}",
                )
            )
    else:
        checks.append(
            PreflightCheck(
                "FalkorDB container",
                True,
                "FAIL",
                "Docker daemon unavailable",
                "Start Docker Desktop first.",
            )
        )

    tcp_ok, tcp_detail = tcp_check(falkor_host, falkor_port)
    checks.append(
        PreflightCheck(
            "FalkorDB TCP",
            True,
            "PASS" if tcp_ok else "FAIL",
            tcp_detail,
            None if tcp_ok else f"Verify {falkor_container} publishes port {falkor_port}.",
        )
    )

    if not database_url:
        checks.append(
            PreflightCheck(
                "KC DATABASE_URL",
                True,
                "FAIL",
                "KNOWLEDGE_CORE_DATABASE_URL is not set",
                "Set KNOWLEDGE_CORE_DATABASE_URL before launching the qualification.",
            )
        )
    else:
        try:
            engine = create_engine(
                database_url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 4},
            )
            try:
                with engine.connect() as connection:
                    db_ok = connection.execute(text("SELECT 1")).scalar_one() == 1
                db_detail = "SQL SELECT 1 succeeded"
            finally:
                engine.dispose()
        except Exception as exc:
            db_ok = False
            db_detail = f"{type(exc).__name__}: {exc}"
        checks.append(
            PreflightCheck(
                "KC PostgreSQL SQL",
                True,
                "PASS" if db_ok else "FAIL",
                db_detail,
                None if db_ok else (
                    f"Start {kc_container} and verify the database URL."
                    if kc_container
                    else "Verify the KC PostgreSQL service and database URL."
                ),
            )
        )

    ollama_ok, installed, ollama_detail = _ollama_tags(ollama_base_url)
    checks.append(
        PreflightCheck(
            "Ollama API",
            True,
            "PASS" if ollama_ok else "FAIL",
            ollama_detail,
            None if ollama_ok else "Start Ollama before launching the qualification.",
        )
    )
    extraction_ok = ollama_ok and model_is_installed(llm_model, installed)
    checks.append(
        PreflightCheck(
            "Extraction model",
            True,
            "PASS" if extraction_ok else "FAIL",
            f"{llm_model}: {'installed' if extraction_ok else 'not found'}",
            None if extraction_ok else f"ollama pull {llm_model}",
        )
    )
    embed_ok = ollama_ok and model_is_installed(embed_model, installed)
    checks.append(
        PreflightCheck(
            "Embedding model",
            True,
            "PASS" if embed_ok else "FAIL",
            f"{embed_model}: {'installed' if embed_ok else 'not found'}",
            None if embed_ok else f"ollama pull {embed_model}",
        )
    )

    try:
        installed_graphiti = version("graphiti-core")
        graphiti_ok = installed_graphiti == "0.30.2"
        graphiti_detail = f"graphiti-core {installed_graphiti}"
    except PackageNotFoundError:
        graphiti_ok = False
        graphiti_detail = "graphiti-core is not installed"
    checks.append(
        PreflightCheck(
            "Graphiti package",
            True,
            "PASS" if graphiti_ok else "FAIL",
            graphiti_detail,
            None if graphiti_ok else 'python -m pip install -e ".[graphiti]"',
        )
    )

    artifact_ok = Path(artifact_root).is_dir()
    checks.append(
        PreflightCheck(
            "KC artifact root",
            True,
            "PASS" if artifact_ok else "FAIL",
            str(Path(artifact_root).resolve()),
            None if artifact_ok else "Verify the retained KC host artifact directory.",
        )
    )

    ui_ok, ui_detail = tcp_check(falkor_host, falkor_ui_port, timeout=1.0)
    checks.append(
        PreflightCheck(
            "FalkorDB UI",
            False,
            "PASS" if ui_ok else "WARN",
            ui_detail,
        )
    )

    return PreflightReport(tuple(checks))


def print_preflight(report: PreflightReport) -> None:
    print("KC GRAPHITI QUALIFICATION PREFLIGHT")
    print("=" * 72)
    for check in report.checks:
        requirement = "REQ" if check.required else "OPT"
        print(f"[{check.status:4}] [{requirement}] {check.name}: {check.detail}")
        if check.suggestion and check.status != "PASS":
            print(f"             -> {check.suggestion}")
    print("-" * 72)
    print(f"PRECHECK RESULT: {'READY' if report.ready else 'BLOCKED'}")
    print("Other ACL/benchmark servers are not required by this qualification.")
