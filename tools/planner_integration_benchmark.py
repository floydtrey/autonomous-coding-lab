"""Production-path integration benchmark for ACL Planner candidates.

Unlike tools/planner_output_benchmark.py, this benchmark does not loosen the
Planner contract. Each candidate runs through the real configured Planner path:

profile resolution -> production read-only tools/authority -> generic agent loop ->
semantic Planner response -> semantic validator -> deterministic compiler ->
internal ExecutionPlan validation -> optional plan intake.

Determiner is intentionally bypassed so this remains a Planner benchmark. The
accepted work_type_id/complexity are supplied per case exactly as Determiner
would supply them.

The benchmark never edits a candidate workspace. Planner is read-only and Worker
execution is not started.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from acl_core import configure_diagnostics
from acl_roles.common import RoleDiagnostics
from acl_runtime.planner import run_planner_model_a


BENCHMARK_SCHEMA = "acl-planner-integration-benchmark:v1"
BENCHMARK_MODE = "PRODUCTION_INTEGRATION"


@dataclass(frozen=True)
class Candidate:
    name: str
    model: str
    enabled: bool = True
    context_window: int | None = None
    max_tokens: int | None = None
    timeout_seconds: float | None = None
    max_agent_turns: int | None = None
    max_tool_calls: int | None = None


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    name: str
    request: str
    workspace_root: str
    work_type_id: str = "1127"
    complexity: str = "MEDIUM"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    selected = [
        ch.lower() if ch.isalnum() else "-"
        for ch in value.strip()
    ]
    result = "".join(selected)
    while "--" in result:
        result = result.replace("--", "-")
    return result.strip("-") or "candidate"


def _load_config(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != BENCHMARK_SCHEMA:
        raise ValueError(
            f"integration benchmark config must use {BENCHMARK_SCHEMA}"
        )
    return value


def _candidate(value: Mapping[str, Any]) -> Candidate:
    name = value.get("name")
    model = value.get("model")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("candidate name must be nonblank text")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("candidate model must be nonblank text")

    def optional_positive_int(key: str) -> int | None:
        observed = value.get(key)
        if observed is None:
            return None
        if isinstance(observed, bool) or not isinstance(observed, int) or observed <= 0:
            raise ValueError(f"{key} must be a positive integer when supplied")
        return observed

    timeout = value.get("timeout_seconds")
    if timeout is not None and (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or timeout <= 0
    ):
        raise ValueError("timeout_seconds must be positive when supplied")

    enabled = value.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("candidate enabled must be boolean")

    return Candidate(
        name=name.strip(),
        model=model.strip(),
        enabled=enabled,
        context_window=optional_positive_int("context_window"),
        max_tokens=optional_positive_int("max_tokens"),
        timeout_seconds=None if timeout is None else float(timeout),
        max_agent_turns=optional_positive_int("max_agent_turns"),
        max_tool_calls=optional_positive_int("max_tool_calls"),
    )


def _benchmark_case(value: Mapping[str, Any]) -> BenchmarkCase:
    case_id = value.get("case_id")
    name = value.get("name")
    request = value.get("request")
    workspace_root = value.get("workspace_root")
    work_type_id = value.get("work_type_id", "1127")
    complexity = value.get("complexity", "MEDIUM")

    for observed, label in (
        (case_id, "case_id"),
        (name, "case name"),
        (request, "case request"),
        (workspace_root, "workspace_root"),
        (work_type_id, "work_type_id"),
        (complexity, "complexity"),
    ):
        if not isinstance(observed, str) or not observed.strip():
            raise ValueError(f"{label} must be nonblank text")

    if complexity not in {"SMALL", "MEDIUM", "LARGE"}:
        raise ValueError("case complexity must be SMALL, MEDIUM, or LARGE")

    return BenchmarkCase(
        case_id=case_id.strip(),
        name=name.strip(),
        request=request.strip(),
        workspace_root=workspace_root.strip(),
        work_type_id=work_type_id.strip(),
        complexity=complexity,
    )


def _path_is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _run_command(command: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        return {
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "command": command,
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }


def _ollama_ps() -> dict[str, Any]:
    return _run_command(["ollama", "ps"])


def _unload_model(model: str) -> dict[str, Any]:
    return _run_command(["ollama", "stop", model])


def _prepare_candidate_config(
    *,
    source_config_root: Path,
    destination_root: Path,
    candidate: Candidate,
) -> tuple[Path, str]:
    config_root = destination_root / "config"
    shutil.copytree(source_config_root, config_root)

    routing_path = config_root / "routing.json"
    routing = json.loads(routing_path.read_text(encoding="utf-8"))
    planner_runtime_ids = {
        item.get("runtime_id")
        for item in routing.get("routes", [])
        if isinstance(item, Mapping)
        and item.get("role") == "planner"
        and isinstance(item.get("runtime_id"), str)
    }
    if len(planner_runtime_ids) != 1:
        raise ValueError(
            "production Planner routes must resolve to exactly one runtime_id "
            f"for integration benchmarking; observed={sorted(planner_runtime_ids)}"
        )
    runtime_id = next(iter(planner_runtime_ids))

    catalog_path = config_root / "runtime_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    matches = [
        item
        for item in catalog.get("runtimes", [])
        if isinstance(item, dict) and item.get("runtime_id") == runtime_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Planner runtime {runtime_id!r} must exist exactly once"
        )

    runtime = matches[0]
    runtime["model"] = candidate.model
    settings = runtime.setdefault("settings", {})
    if not isinstance(settings, dict):
        raise ValueError("Planner runtime settings must be an object")

    optional_overrides = {
        "context_window": candidate.context_window,
        "max_tokens": candidate.max_tokens,
        "timeout_seconds": candidate.timeout_seconds,
        "max_agent_turns": candidate.max_agent_turns,
        "max_tool_calls": candidate.max_tool_calls,
    }
    for key, observed in optional_overrides.items():
        if observed is not None:
            settings[key] = observed

    catalog_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return config_root, runtime_id


def run_benchmark(
    *,
    config_path: Path,
    output_root: Path,
    start_at: str | None = None,
) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    source_config_root = REPO_ROOT / "config"

    config = _load_config(config_path)
    base_url = config.get("base_url", "http://127.0.0.1:11434/v1")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("base_url must be nonblank text")
    base_url = base_url.strip().rstrip("/")

    raw_cases = config.get("cases")
    raw_candidates = config.get("models")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("integration benchmark cases must be a nonempty list")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("integration benchmark models must be a nonempty list")

    cases = tuple(
        _benchmark_case(item)
        for item in raw_cases
        if isinstance(item, Mapping)
    )
    candidates = tuple(
        _candidate(item)
        for item in raw_candidates
        if isinstance(item, Mapping)
    )
    if len(cases) != len(raw_cases) or len(candidates) != len(raw_candidates):
        raise ValueError("every case/model entry must be an object")
    if len({item.case_id for item in cases}) != len(cases):
        raise ValueError("case_id values must be unique")

    enabled = tuple(item for item in candidates if item.enabled)
    if not enabled:
        raise ValueError("integration benchmark has no enabled candidates")
    if start_at is not None:
        matches = [
            index
            for index, item in enumerate(enabled)
            if item.name == start_at or item.model == start_at
        ]
        if not matches:
            raise ValueError(f"--start-at did not match a candidate: {start_at}")
        enabled = enabled[matches[0]:]

    for case in cases:
        workspace = Path(case.workspace_root).expanduser().resolve()
        if _path_is_within(output_root, workspace):
            raise ValueError(
                "--output-root must be outside every benchmark workspace; "
                f"{output_root} is inside {workspace}"
            )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = output_root / f"planner-integration-{stamp}"
    run_root.mkdir(parents=True, exist_ok=False)

    configure_diagnostics(
        enabled=True,
        level="DEBUG",
        path=run_root / "acl-integration.jsonl",
        stderr=False,
    )
    RoleDiagnostics.configure_raw_artifacts(
        enabled=True,
        root=run_root / "role-artifacts",
    )

    previous_base_url = os.environ.get("ACL_OPENAI_COMPAT_BASE_URL")
    os.environ["ACL_OPENAI_COMPAT_BASE_URL"] = base_url

    initial_ollama_ps = _ollama_ps()
    results: list[dict[str, Any]] = []
    try:
        for index, candidate in enumerate(enabled, start=1):
            candidate_started = time.perf_counter()
            candidate_started_at = _utc_now()
            candidate_root = run_root / (
                f"{index:02d}-{_slug(candidate.name)}"
            )
            candidate_root.mkdir(parents=True, exist_ok=False)
            config_root, runtime_id = _prepare_candidate_config(
                source_config_root=source_config_root,
                destination_root=candidate_root,
                candidate=candidate,
            )

            before = _ollama_ps()
            pre_unload = _unload_model(candidate.model)
            case_results: list[dict[str, Any]] = []

            for case_index, case in enumerate(cases, start=1):
                case_started = time.perf_counter()
                case_started_at = _utc_now()
                workspace = Path(case.workspace_root).expanduser().resolve()
                state_root = candidate_root / "state" / _slug(case.case_id)
                artifact_root = candidate_root / "artifacts" / _slug(case.case_id)

                error = None
                result = None
                try:
                    result = run_planner_model_a(
                        config_root=config_root,
                        state_root=state_root,
                        project_root=workspace,
                        request_payload={"text": case.request},
                        work_type_id=case.work_type_id,
                        complexity=case.complexity,
                        requester="planner-integration-benchmark",
                        working_directory=workspace,
                        output_directory=workspace,
                        artifact_directory=artifact_root,
                        intake_plan=True,
                    )
                except Exception as exc:
                    error = {
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                    }
                    to_dict = getattr(exc, "to_dict", None)
                    if callable(to_dict):
                        try:
                            error["details"] = to_dict()
                        except Exception:
                            pass

                loaded = _ollama_ps()
                elapsed = round(time.perf_counter() - case_started, 3)
                record = {
                    "schema_version": BENCHMARK_SCHEMA,
                    "benchmark_mode": BENCHMARK_MODE,
                    "candidate_index": index,
                    "candidate_name": candidate.name,
                    "model": candidate.model,
                    "configured_context_window": candidate.context_window,
                    "runtime_id": runtime_id,
                    "case_index": case_index,
                    "case_id": case.case_id,
                    "case_name": case.name,
                    "workspace_root": str(workspace),
                    "work_type_id": case.work_type_id,
                    "complexity": case.complexity,
                    "request": case.request,
                    "started_at": case_started_at,
                    "finished_at": _utc_now(),
                    "elapsed_seconds": elapsed,
                    "ok": result is not None and error is None,
                    "result": result,
                    "error": error,
                    "ollama_loaded": loaded,
                    "production_surface": {
                        "planner_profile": "planner-model-a",
                        "semantic_contract": "acl-planner-semantic:v1",
                        "worker_started": False,
                        "config_root": str(config_root),
                    },
                }
                result_path = candidate_root / (
                    f"{case_index:02d}-{_slug(case.case_id)}.json"
                )
                result_path.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2, default=str)
                    + "\n",
                    encoding="utf-8",
                )
                case_results.append(
                    {
                        "case_id": case.case_id,
                        "ok": record["ok"],
                        "elapsed_seconds": elapsed,
                        "result_file": str(result_path.relative_to(run_root)),
                    }
                )
                print(
                    f"[{index}/{len(enabled)} case {case_index}/{len(cases)}] "
                    f"{candidate.name}/{case.case_id}: "
                    f"{'OK' if record['ok'] else 'ERROR'} "
                    f"({elapsed}s)"
                )

            unload = _unload_model(candidate.model)
            candidate_record = {
                "candidate_name": candidate.name,
                "model": candidate.model,
                "runtime_id": runtime_id,
                "started_at": candidate_started_at,
                "finished_at": _utc_now(),
                "elapsed_seconds": round(
                    time.perf_counter() - candidate_started,
                    3,
                ),
                "ollama_before": before,
                "pre_unload": pre_unload,
                "unload": unload,
                "cases": case_results,
                "config_root": str(config_root),
            }
            summary_path = candidate_root / "summary.json"
            summary_path.write_text(
                json.dumps(
                    candidate_record,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
                + "\n",
                encoding="utf-8",
            )
            results.append(
                {
                    "candidate_name": candidate.name,
                    "model": candidate.model,
                    "cases": case_results,
                    "result_file": str(summary_path.relative_to(run_root)),
                }
            )
    finally:
        if previous_base_url is None:
            os.environ.pop("ACL_OPENAI_COMPAT_BASE_URL", None)
        else:
            os.environ["ACL_OPENAI_COMPAT_BASE_URL"] = previous_base_url

    summary = {
        "schema_version": BENCHMARK_SCHEMA,
        "benchmark_mode": BENCHMARK_MODE,
        "created_at": _utc_now(),
        "config_path": str(config_path),
        "repo_root": str(REPO_ROOT),
        "output_root": str(run_root),
        "base_url": base_url,
        "production_surface": {
            "planner_profile": "planner-model-a",
            "semantic_contract": "acl-planner-semantic:v1",
            "determiner_bypassed": True,
            "worker_started": False,
        },
        "initial_ollama_ps": initial_ollama_ps,
        "cases": [
            {
                "case_id": item.case_id,
                "name": item.name,
                "workspace_root": item.workspace_root,
                "work_type_id": item.work_type_id,
                "complexity": item.complexity,
                "request": item.request,
            }
            for item in cases
        ],
        "results": results,
    }
    (run_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"Results: {run_root}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run candidate Planner models through ACL's production semantic/"
            "compiler integration path without starting Worker execution."
        )
    )
    parser.add_argument(
        "--config",
        default="config/planner_integration_benchmark.json",
    )
    parser.add_argument(
        "--output-root",
        default=r"C:\AI\Benchmarks\ACL-Planner-Integration",
    )
    parser.add_argument("--start-at")
    args = parser.parse_args()

    run_benchmark(
        config_path=Path(args.config),
        output_root=Path(args.output_root),
        start_at=args.start_at,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
