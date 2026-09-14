from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import traceback
from typing import Any

from sqlalchemy import text

import graphiti_host_phase
from knowledge_core.application.graph_retrieval import GraphProjectionRetrievalKnowledgeKernel
from knowledge_core.artifacts.store import LocalArtifactStore
from knowledge_core.storage.database import create_database_engine, create_session_factory
from knowledge_core_providers.graphiti import GraphitiLocalConfig, GraphitiProjectionAdapter
from knowledge_core_providers.host_metrics import (
    HostResourceTelemetry,
    _cpu_counters,
    _gpu_snapshot,
    _memory_snapshot,
    _ollama_ps_snapshot,
)
from knowledge_core_providers.qualification_events import (
    ObservableGraphitiProjectionAdapter,
    QualificationEventRecorder,
    aggregate_llm_metrics,
    latest_event,
    open_llm_requests,
)
from knowledge_core_providers.qualification_preflight import (
    print_preflight,
    run_graphiti_preflight,
)


_GIB = 1024 ** 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight, launch, and live-monitor the real KC -> Graphiti/FalkorDB/Ollama "
            "host qualification without changing KC trust or Graphiti extraction behavior."
        )
    )
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--source-path", action="append", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--namespace", default="kc:graphiti-live")
    parser.add_argument("--scope", default="project:knowledge-core")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--attempt-salt", default="primary")
    parser.add_argument("--falkor-host", default=os.environ.get("FALKORDB_HOST", "localhost"))
    parser.add_argument("--falkor-port", type=int, default=int(os.environ.get("FALKORDB_PORT", "6379")))
    parser.add_argument("--falkor-container", default="falkordb")
    parser.add_argument("--falkor-ui-port", type=int, default=3000)
    parser.add_argument("--ollama-base-url", default="http://localhost:11434/v1")
    parser.add_argument("--llm-model", default="graphiti-qwen35-9b-32k")
    parser.add_argument("--embed-model", default="nomic-embed-text:latest")
    parser.add_argument("--evidence-file")
    parser.add_argument("--run-root")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--stall-seconds", type=float, default=300.0)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--no-clear", action="store_true")
    return parser


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
    return completed.returncode == 0, (completed.stdout or completed.stderr or "").strip()


def _first_integer(output: str) -> int | None:
    for line in output.splitlines():
        candidate = line.strip()
        if re.fullmatch(r"\d+", candidate):
            return int(candidate)
    return None


def _graph_count(container: str, partition: str, query: str) -> int | None:
    ok, output = _run(
        ["docker", "exec", container, "redis-cli", "--raw", "GRAPH.QUERY", partition, query],
        timeout=10.0,
    )
    return _first_integer(output) if ok else None


def _graph_snapshot(container: str, partition: str) -> dict[str, int | None]:
    return {
        "episodes": _graph_count(container, partition, "MATCH (n:Episodic) RETURN count(n)"),
        "entities": _graph_count(container, partition, "MATCH (n:Entity) RETURN count(n)"),
        "edges": _graph_count(container, partition, "MATCH ()-[r]->() RETURN count(r)"),
    }


class _LiveHostView:
    def __init__(self) -> None:
        try:
            self.previous_cpu = _cpu_counters()
        except Exception:
            self.previous_cpu = None

    def sample(self) -> dict[str, Any]:
        result: dict[str, Any] = {"errors": []}
        try:
            memory = _memory_snapshot()
            result["ram_used_gib"] = round(memory["ram_used_bytes"] / _GIB, 2)
            result["ram_total_gib"] = round(memory["ram_total_bytes"] / _GIB, 2)
            result["commit_used_gib"] = round(memory.get("commit_used_bytes", 0) / _GIB, 2)
            result["commit_limit_gib"] = round(memory.get("commit_limit_bytes", 0) / _GIB, 2)
        except Exception as exc:
            result["errors"].append(f"memory: {type(exc).__name__}: {exc}")
        try:
            current = _cpu_counters()
            cpu = None
            if self.previous_cpu is not None:
                idle_delta = current[0] - self.previous_cpu[0]
                total_delta = current[1] - self.previous_cpu[1]
                if total_delta > 0:
                    cpu = ((total_delta - idle_delta) / total_delta) * 100.0
            self.previous_cpu = current
            result["cpu_percent"] = round(max(0.0, min(100.0, cpu)), 2) if cpu is not None else None
        except Exception as exc:
            result["cpu_percent"] = None
            result["errors"].append(f"cpu: {type(exc).__name__}: {exc}")
        try:
            result["gpus"] = _gpu_snapshot()
        except Exception as exc:
            result["gpus"] = []
            result["errors"].append(f"gpu: {type(exc).__name__}: {exc}")
        result["ollama"] = _ollama_ps_snapshot()
        return result


def _database_snapshot(engine, attempt_id: str) -> dict[str, Any]:
    try:
        with engine.connect() as connection:
            attempt = connection.execute(
                text(
                    "SELECT disposition, validation_state "
                    "FROM kc_control.projection_attempt "
                    "WHERE attempt_id = CAST(:attempt_id AS uuid)"
                ),
                {"attempt_id": attempt_id},
            ).first()

            binding_count = connection.execute(
                text(
                    "SELECT count(*) "
                    "FROM kc_control.projection_source_binding "
                    "WHERE attempt_id = CAST(:attempt_id AS uuid)"
                ),
                {"attempt_id": attempt_id},
            ).scalar_one()

            lifecycle = connection.execute(
                text(
                    """
                    SELECT c.outcome, c.evidence_json
                    FROM kc_control.projection_validation v
                    JOIN kc_control.projection_validation_check c
                      ON c.validation_id = v.validation_id
                    WHERE v.attempt_id = CAST(:attempt_id AS uuid)
                      AND c.check_code = 'governed-lifecycle-inventory'
                    ORDER BY v.started_at DESC
                    LIMIT 1
                    """
                ),
                {"attempt_id": attempt_id},
            ).first()

        lifecycle_outcome = None
        retired_count = None

        if lifecycle is not None:
            lifecycle_outcome = lifecycle[0]
            evidence = lifecycle[1] or {}
            retired = evidence.get("retired_edge_ids")
            if isinstance(retired, list):
                retired_count = len(retired)

        return {
            "attempt_present": attempt is not None,
            "disposition": attempt[0] if attempt is not None else None,
            "validation_state": attempt[1] if attempt is not None else None,
            "binding_count": int(binding_count),
            "lifecycle_outcome": lifecycle_outcome,
            "retired_count": retired_count,
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}

def _prepare_plan(args, database_url: str) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    sessions = create_session_factory(engine)
    session = sessions()
    try:
        artifacts = LocalArtifactStore(Path(args.artifact_root).resolve())
        kernel = GraphProjectionRetrievalKnowledgeKernel(session, artifact_store=artifacts)
        config = GraphitiLocalConfig(
            falkor_host=args.falkor_host,
            falkor_port=args.falkor_port,
            falkor_username=os.environ.get("FALKORDB_USERNAME"),
            falkor_password=os.environ.get("FALKORDB_PASSWORD"),
            ollama_base_url=args.ollama_base_url,
            ollama_api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            llm_model=args.llm_model,
            embed_model=args.embed_model,
        )
        adapter = GraphitiProjectionAdapter(config)
        refs = kernel.resolve_current_sr2_resource_versions(source_paths=tuple(args.source_path))
        plan = kernel.build_sr2_projection_plan(resource_version_refs=refs)
        attempt_id = graphiti_host_phase._stable_uuid(
            graphiti_host_phase._ATTEMPT_NAMESPACE,
            graphiti_host_phase._attempt_payload(
                plan=plan,
                adapter=adapter,
                namespace_key=args.namespace,
                scope_key=args.scope,
                attempt_salt=args.attempt_salt,
            ),
        )
        partition = adapter.partition_key(
            namespace_key=args.namespace,
            scope_key=args.scope,
            projection_profile_id=plan.profile_id,
        )
        segments = [
            {
                "segment_key": segment.segment_key,
                "segment_ordinal": segment.segment_ordinal,
                "source_path": segment.source_path,
                "source_line_start": segment.source_line_start,
                "source_line_end": segment.source_line_end,
                "source_byte_start": segment.source_byte_start,
                "source_byte_end": segment.source_byte_end,
                "source_slice_sha256": segment.source_slice_sha256,
                "body_bytes": len(segment.body.encode("utf-8")),
            }
            for segment in plan.segments
        ]
        return {
            "attempt_id": str(attempt_id),
            "partition": partition,
            "generation_id": str(plan.generation_id),
            "profile_id": plan.profile_id,
            "segment_count": len(plan.segments),
            "segments": segments,
        }
    finally:
        session.close()
        engine.dispose()


def _inner_argv(args) -> list[str]:
    values = [
        "graphiti_host_phase.py",
        "--artifact-root", args.artifact_root,
        "--query", args.query,
        "--namespace", args.namespace,
        "--scope", args.scope,
        "--limit", str(args.limit),
        "--attempt-salt", args.attempt_salt,
        "--falkor-host", args.falkor_host,
        "--falkor-port", str(args.falkor_port),
        "--ollama-base-url", args.ollama_base_url,
        "--llm-model", args.llm_model,
        "--embed-model", args.embed_model,
    ]
    for path in args.source_path:
        values.extend(["--source-path", path])
    return values


def _health(events: list[dict[str, Any]], host: dict[str, Any], *, alive: bool, stall_seconds: float) -> tuple[str, str]:
    if not alive:
        return "STOPPED", "qualification worker exited"
    now_ns = time.monotonic_ns()
    open_requests = open_llm_requests(events)
    gpu_util = max(
        [float(gpu.get("gpu_utilization_percent") or 0.0) for gpu in host.get("gpus", [])] or [0.0]
    )
    cpu_util = float(host.get("cpu_percent") or 0.0)
    if open_requests:
        request = open_requests[-1]
        age = (now_ns - int(request["monotonic_ns"])) / 1_000_000_000
        if age >= stall_seconds and gpu_util < 5.0 and cpu_util < 5.0:
            return "POSSIBLE_STALL", f"LLM request open {age:.0f}s; CPU/GPU both quiet"
        if age >= stall_seconds:
            return "LONG_MODEL_CALL", f"LLM request open {age:.0f}s; compute remains active"
        return "WAITING_ON_LLM", f"LLM request open {age:.0f}s"
    if events:
        age = (now_ns - int(events[-1]["monotonic_ns"])) / 1_000_000_000
        if age >= stall_seconds and gpu_util < 5.0 and cpu_util < 5.0:
            return "POSSIBLE_STALL", f"no observer event for {age:.0f}s; CPU/GPU both quiet"
    return "ACTIVE", "forward progress observed"


def _stage(events: list[dict[str, Any]]) -> str:
    open_requests = open_llm_requests(events)
    if open_requests:
        return f"LLM:{open_requests[-1].get('stage', 'unknown')}"
    last = events[-1].get("event_type") if events else None
    mapping = {
        "segment_started": "Graphiti episode ingestion",
        "segment_completed": "Between segments",
        "projection_started": "Projection startup",
        "projection_completed": "Validation",
        "source_lookup_started": "Validation source lookup",
        "source_lookup_completed": "Validation",
        "graph_search_started": "Graph search",
        "graph_search_completed": "Validation/retrieval",
    }
    return mapping.get(last, last or "Starting")


def _print_live(
    *,
    args,
    plan: dict[str, Any],
    events: list[dict[str, Any]],
    host: dict[str, Any],
    graph: dict[str, Any],
    db: dict[str, Any],
    alive: bool,
    started: float,
) -> None:
    if not args.no_clear:
        os.system("cls" if os.name == "nt" else "clear")

    completed = [
        event for event in events
        if event.get("event_type") == "segment_completed"
    ]
    warnings = [
        event for event in events
        if event.get("event_type") == "graphiti_warning"
    ]

    llm = aggregate_llm_metrics(events)
    health, _ = _health(
        events,
        host,
        alive=alive,
        stall_seconds=args.stall_seconds,
    )

    elapsed = int(time.monotonic() - started)
    hh = elapsed // 3600
    mm = (elapsed % 3600) // 60
    ss = elapsed % 60
    elapsed_text = f"{hh:02d}:{mm:02d}:{ss:02d}"

    stage = str(_stage(events))
    if len(stage) > 34:
        stage = stage[:31] + "..."

    current = latest_event(events, "segment_started")
    segment_text = "-- / " + str(plan["segment_count"])
    line_text = "--"

    if current:
        key = current.get("segment_key")
        metadata = next(
            (
                item for item in plan["segments"]
                if item["segment_key"] == key
            ),
            None,
        )
        if metadata:
            ordinal = int(metadata["segment_ordinal"]) + 1
            segment_text = f"{ordinal} / {plan['segment_count']}"
            line_text = (
                f"{metadata['source_line_start']}-"
                f"{metadata['source_line_end']}"
            )

    open_requests = open_llm_requests(events)
    open_text = "--"
    if open_requests:
        request = open_requests[-1]
        age = (
            time.monotonic_ns() - int(request["monotonic_ns"])
        ) / 1_000_000_000
        open_text = f"{age:.0f}s"

    tokens = (
        int(llm.get("prompt_tokens") or 0)
        + int(llm.get("completion_tokens") or 0)
    )

    rate = llm.get("aggregate_completion_tokens_per_second")
    rate_text = f"{rate:.1f}" if rate is not None else "--"

    gpu_util = "--"
    vram_text = "--"
    gpus = host.get("gpus", [])
    if gpus:
        gpu = gpus[0]
        gpu_util = str(gpu.get("gpu_utilization_percent") or "--")
        used = gpu.get("vram_used_mib")
        total = gpu.get("vram_total_mib")
        if used is not None and total is not None:
            vram_text = f"{float(used)/1024:.1f}/{float(total)/1024:.1f} GB"

    ram_used = host.get("ram_used_gib")
    ram_total = host.get("ram_total_gib")
    ram_text = (
        f"{ram_used}/{ram_total} GB"
        if ram_used is not None and ram_total is not None
        else "--"
    )

    bindings = db.get("binding_count")
    disposition = db.get("disposition") or "not-opened"
    validation = db.get("validation_state") or "not-started"

    lifecycle = db.get("lifecycle_outcome") or "--"
    retired = db.get("retired_count")
    retired_text = "--" if retired is None else str(retired)

    print("KC GRAPHITI GOVERNED QUALIFICATION")
    print("=" * 78)
    print(
        f"Elapsed {elapsed_text:<9} "
        f"Health {health:<18} "
        f"Stage {stage}"
    )
    print(
        f"Segment {segment_text:<9} "
        f"Lines {line_text}"
    )
    print()
    print(
        f"GRAPH   Episodes {str(graph.get('episodes')):<5} / {plan['segment_count']:<2}   "
        f"Entities {str(graph.get('entities')):<6} "
        f"Edges {str(graph.get('edges'))}"
    )
    print(
        f"MODEL   Requests {llm['request_count']:<5} "
        f"Open {open_text:<7} "
        f"Tokens {tokens:<9,} "
        f"Rate {rate_text} tok/s"
    )
    print(
        f"SYSTEM  GPU {gpu_util}%      "
        f"VRAM {vram_text:<15} "
        f"RAM {ram_text}"
    )
    print(
        f"WARN    {len(warnings)}"
        + (
            f"   Last: {str(warnings[-1].get('message'))[:55]}"
            if warnings else ""
        )
    )
    print()
    print(
        f"KC      Disposition {disposition:<12} "
        f"Validation {validation:<12} "
        f"Bindings {bindings if bindings is not None else '--'}/{plan['segment_count']}"
    )
    print(
        f"LIFE    Check {lifecycle:<14} "
        f"Retired edges {retired_text}"
    )
    print("=" * 78)
    print(
        f"Observer segments {len(completed)}/{plan['segment_count']} | "
        f"Refresh {args.poll_seconds:g}s | Ctrl+C interrupts launcher + worker"
    )

def main() -> int:
    args = _parser().parse_args()
    if args.poll_seconds <= 0 or args.stall_seconds <= 0:
        raise SystemExit("--poll-seconds and --stall-seconds must be positive")

    artifact_root = Path(args.artifact_root).resolve()
    evidence_file = (
        Path(args.evidence_file).resolve()
        if args.evidence_file
        else artifact_root.parent / "SR2_HOST_QUALIFICATION_EVIDENCE.json"
    )
    database_url = os.environ.get("KNOWLEDGE_CORE_DATABASE_URL")

    report = run_graphiti_preflight(
        artifact_root=artifact_root,
        database_url=database_url,
        evidence_file=evidence_file,
        falkor_host=args.falkor_host,
        falkor_port=args.falkor_port,
        falkor_container=args.falkor_container,
        falkor_ui_port=args.falkor_ui_port,
        ollama_base_url=args.ollama_base_url,
        llm_model=args.llm_model,
        embed_model=args.embed_model,
    )
    print_preflight(report)
    if not report.ready:
        return 2
    if database_url is None:
        return 2

    try:
        plan = _prepare_plan(args, database_url)
    except Exception as exc:
        print("\nSOURCE/PLAN PREFLIGHT: BLOCKED")
        print(f"{type(exc).__name__}: {exc}")
        return 2

    print("\nSOURCE/PLAN PREFLIGHT: PASS")
    print(f"Canonical source(s): {', '.join(args.source_path)}")
    print(f"Verified segments:   {plan['segment_count']}")
    print(f"Physical partition:  {plan['partition']}")
    print(f"Attempt ID:          {plan['attempt_id']}")
    if args.preflight_only:
        return 0

    run_root = (
        Path(args.run_root).resolve()
        if args.run_root
        else artifact_root.parent / "graphiti-runs"
    )
    run_dir = run_root / plan["attempt_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    recorder = QualificationEventRecorder(run_dir / "events.jsonl")
    recorder.emit(
        "qualification_plan",
        model=args.llm_model,
        embed_model=args.embed_model,
        attempt_id=plan["attempt_id"],
        partition_key=plan["partition"],
        generation_id=plan["generation_id"],
        profile_id=plan["profile_id"],
        segment_count=plan["segment_count"],
        segments=plan["segments"],
    )

    telemetry = HostResourceTelemetry(sample_interval_seconds=1.0, gpu_interval_seconds=2.0).start()
    live_host = _LiveHostView()
    status: dict[str, Any] = {"exit_code": None, "payload": None, "exception": None}
    captured_payloads: list[dict[str, Any]] = []

    original_adapter = graphiti_host_phase.GraphitiProjectionAdapter
    original_print = graphiti_host_phase._print
    original_argv = list(sys.argv)

    def adapter_factory(config):
        return ObservableGraphitiProjectionAdapter(config, recorder=recorder)

    def capture_payload(payload: dict[str, Any]) -> None:
        captured_payloads.append(payload)
        recorder.emit("qualification_payload", payload=payload)

    def worker() -> None:
        graphiti_host_phase.GraphitiProjectionAdapter = adapter_factory
        graphiti_host_phase._print = capture_payload
        sys.argv = _inner_argv(args)
        recorder.emit("qualification_started")
        try:
            status["exit_code"] = graphiti_host_phase.main()
        except BaseException as exc:
            status["exception"] = f"{type(exc).__name__}: {exc}"
            recorder.emit("qualification_exception", error=status["exception"])
            traceback.print_exc()
            status["exit_code"] = 1
        finally:
            status["payload"] = captured_payloads[-1] if captured_payloads else None
            recorder.emit(
                "qualification_finished",
                exit_code=status["exit_code"],
                exception=status["exception"],
            )
            graphiti_host_phase.GraphitiProjectionAdapter = original_adapter
            graphiti_host_phase._print = original_print
            sys.argv = original_argv

    thread = threading.Thread(target=worker, name="kc-graphiti-qualification", daemon=False)
    started = time.monotonic()
    thread.start()

    monitor_engine = create_database_engine(database_url)
    graph_cache: dict[str, Any] = {"episodes": None, "entities": None, "edges": None}
    db_cache: dict[str, Any] = {}
    last_deep_sample = 0.0
    try:
        while thread.is_alive():
            now = time.monotonic()
            host = live_host.sample()
            if now - last_deep_sample >= 5.0:
                graph_cache = _graph_snapshot(args.falkor_container, plan["partition"])
                db_cache = _database_snapshot(monitor_engine, plan["attempt_id"])
                last_deep_sample = now
            _print_live(
                args=args,
                plan=plan,
                events=recorder.snapshot(),
                host=host,
                graph=graph_cache,
                db=db_cache,
                alive=True,
                started=started,
            )
            thread.join(timeout=args.poll_seconds)
    except KeyboardInterrupt:
        print("\nMonitor interrupted. The qualification thread is still in this process; exiting now may terminate it.")
        raise
    finally:
        monitor_engine.dispose()

    thread.join()
    metrics = telemetry.stop()
    events = recorder.snapshot()
    llm_metrics = aggregate_llm_metrics(events)
    final_db_engine = create_database_engine(database_url)
    try:
        final_db = _database_snapshot(final_db_engine, plan["attempt_id"])
    finally:
        final_db_engine.dispose()
    final_graph = _graph_snapshot(args.falkor_container, plan["partition"])

    summary = {
        "observer_version": 1,
        "attempt_id": plan["attempt_id"],
        "partition": plan["partition"],
        "model": args.llm_model,
        "embed_model": args.embed_model,
        "source_paths": list(args.source_path),
        "planned_segment_count": plan["segment_count"],
        "observed_segment_count": sum(1 for event in events if event.get("event_type") == "segment_completed"),
        "graphiti_warning_count": sum(1 for event in events if event.get("event_type") == "graphiti_warning"),
        "llm_metrics": llm_metrics,
        "host_metrics": metrics,
        "final_database": final_db,
        "final_graph": final_graph,
        "qualification_exit_code": status["exit_code"],
        "qualification_payload": status["payload"],
        "qualification_exception": status["exception"],
        "preflight": report.as_dict(),
        "event_log": str(recorder.path),
        "event_journal_errors": list(recorder.errors),
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True, indent=2, default=str), encoding="utf-8")

    if not args.no_clear:
        os.system("cls" if os.name == "nt" else "clear")
    print("KC GRAPHITI QUALIFICATION COMPLETE")
    print("=" * 72)
    print(f"Exit code:          {status['exit_code']}")
    print(f"Segments observed:  {summary['observed_segment_count']} / {plan['segment_count']}")
    print(f"Warnings observed:  {summary['graphiti_warning_count']}")
    print(f"LLM requests:       {llm_metrics['request_count']}")
    print(f"Completion tok/s:   {llm_metrics['aggregate_completion_tokens_per_second'] or 'n/a'}")
    print(f"KC disposition:     {final_db.get('disposition')}")
    print(f"KC validation:      {final_db.get('validation_state')}")
    print(f"KC bindings:        {final_db.get('binding_count')}")
    print(f"Falkor episodes:    {final_graph.get('episodes')}")
    print(f"Event log:          {recorder.path}")
    print(f"Summary:            {summary_path}")
    return int(status["exit_code"] or 0)


if __name__ == "__main__":
    raise SystemExit(main())
