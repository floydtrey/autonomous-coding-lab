"""Serial loose-output benchmark for candidate ACL Planner models.

This intentionally bypasses Determiner and the Planner result schema. It reuses
ACL's OpenAI-compatible agent/tool loop, gives Planner read-only filesystem tools,
captures the model's raw final handoff, unloads the model, and continues.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from acl_adapters.openai_agent import OpenAICompatibleAgentAdapter
from acl_controller.authority.filesystem import FilesystemAuthorityCoordinator
from acl_controller.tools.filesystem import FilesystemToolService
from acl_core import (
    AdapterRequest,
    AuthorityEnvelope,
    AuthorityRequest,
    CoreServices,
)


BENCHMARK_SCHEMA = "acl-planner-output-benchmark:v1"

DEFAULT_SYSTEM_PROMPT = """You are the planning model in an experimental coding-agent benchmark.

Understand the user's request and prepare a handoff for another coding Worker.
Break the work into manageable sequential tasks so the Worker can receive one
bounded task at a time. Inspect the available workspace with the read-only tools
when that helps you understand the work.

Do not execute the requested changes and do not modify project files.

Choose the handoff format yourself. Use whatever structure you can produce most
clearly, reliably, and consistently. Focus on communicating the work another
capable coding agent needs to perform."""


@dataclass(frozen=True)
class Candidate:
    name: str
    model: str
    enabled: bool = True
    context_window: int | None = None
    max_tokens: int = 4096
    timeout_seconds: float = 300.0
    max_agent_turns: int = 16
    max_tool_calls: int = 32


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    name: str
    request: str
    workspace_root: str


class LoosePlannerBenchmarkAdapter(OpenAICompatibleAgentAdapter):
    """Existing ACL tool loop with no ACL role-envelope/output-format demand."""

    def __post_init__(self) -> None:
        super().__post_init__()
        self._benchmark_candidate = None
        self._benchmark_turn = 0
        self._benchmark_tool_calls = 0

    def begin_candidate(self, candidate_name: str, model: str) -> None:
        self._benchmark_candidate = candidate_name
        self._benchmark_turn = 0
        self._benchmark_tool_calls = 0
        print(f"\n=== {candidate_name} ===")
        print(f"Model: {model}")
        print("Status: loaded candidate")

    def begin_case(self, case_id: str, case_name: str) -> None:
        self._benchmark_turn = 0
        self._benchmark_tool_calls = 0
        self._benchmark_case = case_id
        print(f"\n--- {case_id}: {case_name} ---")

    def _request_completion(self, *, request_id, body, runtime):
        self._benchmark_turn += 1
        candidate = self._benchmark_candidate or runtime.get("model") or "candidate"
        case_id = getattr(self, "_benchmark_case", None)
        label = candidate if not case_id else f"{candidate}/{case_id}"
        print(
            f"[{label}] turn {self._benchmark_turn} "
            f"| tool calls {self._benchmark_tool_calls}"
        )
        return super()._request_completion(
            request_id=request_id,
            body=body,
            runtime=runtime,
        )

    def _execute_tool_call(self, value, *, allowed_tool_ids, grant):
        self._benchmark_tool_calls += 1
        try:
            tool_name = self._tool_call_name(value)
        except Exception:
            tool_name = "unknown"
        candidate = self._benchmark_candidate or "candidate"
        case_id = getattr(self, "_benchmark_case", None)
        label = candidate if not case_id else f"{candidate}/{case_id}"
        print(
            f"[{label}] tool {self._benchmark_tool_calls}: {tool_name}"
        )
        return super()._execute_tool_call(
            value,
            allowed_tool_ids=allowed_tool_ids,
            grant=grant,
        )

    def _build_chat_body(
        self,
        role_request: Mapping[str, Any],
        runtime: Mapping[str, Any],
    ) -> dict[str, Any]:
        system_prompt = role_request.get("benchmark_system_prompt")
        user_prompt = role_request.get("benchmark_user_prompt")
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ValueError("benchmark_system_prompt must be nonblank text")
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise ValueError("benchmark_user_prompt must be nonblank text")

        body: dict[str, Any] = {
            "model": runtime["model"],
            "messages": [
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            "stream": False,
        }
        for key in ("temperature", "max_tokens", "top_p", "seed"):
            if runtime.get(key) is not None:
                body[key] = runtime[key]
        extra_body = runtime.get("extra_body")
        if isinstance(extra_body, Mapping):
            for key, value in extra_body.items():
                if key not in body:
                    body[key] = value
        return body


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return text or "model"


def _load_config(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != BENCHMARK_SCHEMA:
        raise ValueError(f"{path} is not a {BENCHMARK_SCHEMA} config")
    return value


def _candidate(value: Mapping[str, Any]) -> Candidate:
    name = value.get("name")
    model = value.get("model")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("candidate name is required")
    if not isinstance(model, str) or not model.strip():
        raise ValueError(f"candidate {name!r} model is required")
    enabled = value.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError(f"candidate {name!r} enabled must be boolean")

    context_window = value.get("context_window")
    if context_window is not None and (
        isinstance(context_window, bool)
        or not isinstance(context_window, int)
        or context_window <= 0
    ):
        raise ValueError(f"candidate {name!r} context_window must be positive")

    return Candidate(
        name=name.strip(),
        model=model.strip(),
        enabled=enabled,
        context_window=context_window,
        max_tokens=int(value.get("max_tokens", 4096)),
        timeout_seconds=float(value.get("timeout_seconds", 300)),
        max_agent_turns=int(value.get("max_agent_turns", 16)),
        max_tool_calls=int(value.get("max_tool_calls", 32)),
    )


def _benchmark_case(value: Mapping[str, Any], *, default_workspace: Path) -> BenchmarkCase:
    case_id = value.get("case_id")
    name = value.get("name")
    request = value.get("request")
    workspace_root = value.get("workspace_root", str(default_workspace))
    for observed, label in (
        (case_id, "case_id"),
        (name, "case name"),
        (request, "case request"),
        (workspace_root, "case workspace_root"),
    ):
        if not isinstance(observed, str) or not observed.strip():
            raise ValueError(f"{label} must be nonblank text")
    return BenchmarkCase(
        case_id=case_id.strip(),
        name=name.strip(),
        request=request.strip(),
        workspace_root=workspace_root.strip(),
    )


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


def _register_read_tools(
    core: CoreServices,
    *,
    project_root: Path,
    state_root: Path,
    config_root: Path,
) -> tuple[str, ...]:
    filesystem_authority = FilesystemAuthorityCoordinator.create(
        project_root=project_root,
        state_root=state_root,
        config_root=config_root,
    )
    registered = FilesystemToolService(filesystem_authority).register(core.tools)
    return tuple(
        tool_id
        for tool_id in registered
        if tool_id in {"filesystem.list_directory", "filesystem.read_text"}
    )


def _read_grant(core: CoreServices, *, tool_ids: tuple[str, ...], subject: str):
    envelope = AuthorityEnvelope(
        capabilities=("filesystem.read",),
        resource_scopes=("filesystem:READ:*",),
        tool_scopes=tuple(sorted(tool_ids)),
    )
    return core.authority.issue(
        envelope,
        AuthorityRequest(
            capabilities=envelope.capabilities,
            resource_scopes=envelope.resource_scopes,
            tool_scopes=envelope.tool_scopes,
            reason="Planner output benchmark read-only inspection",
        ),
        issuer="planner-output-benchmark",
        subject=subject,
    )


def _user_prompt(*, request_text: str, workspace_root: str) -> str:
    return (
        "USER REQUEST\n"
        f"{request_text.strip()}\n\n"
        "WORKSPACE\n"
        f"Primary workspace: {workspace_root}\n"
        "You may inspect files and directories with the available read-only tools "
        "before producing the handoff."
    )


def run_benchmark(
    *,
    config_path: Path,
    project_root: Path,
    output_root: Path,
    start_at: str | None = None,
) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    project_root = project_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    config_root = project_root / "config"

    config = _load_config(config_path)
    base_url = config.get("base_url", "http://127.0.0.1:11434/v1")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("base_url must be nonblank text")

    raw_cases = config.get("cases")
    if raw_cases is None:
        request_text = config.get("request")
        if not isinstance(request_text, str) or not request_text.strip():
            raise ValueError("benchmark request must be nonblank text")
        cases = (
            BenchmarkCase(
                case_id="case-01",
                name="legacy single request",
                request=request_text.strip(),
                workspace_root=str(project_root),
            ),
        )
    else:
        if not isinstance(raw_cases, list) or not raw_cases:
            raise ValueError("cases must be a nonempty list")
        cases = tuple(
            _benchmark_case(item, default_workspace=project_root)
            for item in raw_cases
            if isinstance(item, Mapping)
        )
        if len(cases) != len(raw_cases):
            raise ValueError("every case must be an object")
        case_ids = [item.case_id for item in cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("case_id values must be unique")

    system_prompt = config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError("system_prompt must be nonblank text")

    raw_candidates = config.get("models")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("models must be a nonempty list")
    candidates = tuple(_candidate(item) for item in raw_candidates if isinstance(item, Mapping))
    enabled = tuple(item for item in candidates if item.enabled)
    if not enabled:
        raise ValueError("benchmark has no enabled model candidates")
    if start_at is not None:
        matches = [
            index
            for index, item in enumerate(enabled)
            if item.name == start_at or item.model == start_at
        ]
        if not matches:
            raise ValueError(f"--start-at did not match a candidate: {start_at}")
        enabled = enabled[matches[0]:]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = output_root / f"planner-output-{stamp}"
    run_root.mkdir(parents=True, exist_ok=False)
    state_root = run_root / "state"

    core = CoreServices.create()
    tool_ids = _register_read_tools(
        core,
        project_root=project_root,
        state_root=state_root,
        config_root=config_root,
    )
    adapter = LoosePlannerBenchmarkAdapter(
        adapter_id="openai-compatible.agent",
        settings={},
        services=core,
    )

    initial_ollama_ps = _ollama_ps()
    candidate_cleanup = [
        {
            "model": candidate.model,
            "result": _unload_model(candidate.model),
        }
        for candidate in enabled
    ]

    results: list[dict[str, Any]] = []

    for index, candidate in enumerate(enabled, start=1):
        model_started = time.perf_counter()
        model_started_at = _utc_now()
        grant = _read_grant(core, tool_ids=tool_ids, subject=candidate.model)
        before = _ollama_ps()
        adapter.begin_candidate(candidate.name, candidate.model)

        execution: dict[str, Any] = {
            "base_url": base_url.rstrip("/"),
            "model": candidate.model,
            "max_tokens": candidate.max_tokens,
            "timeout_seconds": candidate.timeout_seconds,
            "max_agent_turns": candidate.max_agent_turns,
            "max_tool_calls": candidate.max_tool_calls,
            "max_identical_tool_failures": 3,
            "response_format_json": False,
        }
        if candidate.context_window is not None:
            execution["context_window"] = candidate.context_window

        case_results: list[dict[str, Any]] = []
        for case_index, benchmark_case in enumerate(cases, start=1):
            adapter.begin_case(benchmark_case.case_id, benchmark_case.name)
            case_started = time.perf_counter()
            case_started_at = _utc_now()
            user_prompt = _user_prompt(
                request_text=benchmark_case.request,
                workspace_root=benchmark_case.workspace_root,
            )
            role_request = {
                "schema_version": BENCHMARK_SCHEMA,
                "workflow_id": (
                    f"benchmark:{stamp}:{index:02d}:{case_index:02d}"
                ),
                "attempt_id": f"attempt:{index:02d}:{case_index:02d}",
                "role": "planner",
                "benchmark_system_prompt": system_prompt,
                "benchmark_user_prompt": user_prompt,
                "objective": {"request": benchmark_case.request},
                "context": {"workspace_root": benchmark_case.workspace_root},
                "authority_grant_id": grant.grant_id,
                "tool_ids": list(tool_ids),
                "metadata": {
                    "benchmark": True,
                    "candidate_name": candidate.name,
                    "case_id": benchmark_case.case_id,
                },
                "execution": execution,
            }

            candidate_exception = None
            try:
                response = adapter.invoke(
                    AdapterRequest(
                        operation="role.invoke",
                        payload={
                            "role_request": role_request,
                            "authority": {"grant": grant.to_dict()},
                        },
                    )
                )
            except Exception as exc:
                candidate_exception = {
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                }
                to_dict = getattr(exc, "to_dict", None)
                if callable(to_dict):
                    try:
                        candidate_exception["details"] = to_dict()
                    except Exception:
                        pass
                response = None
                print(
                    f"[{candidate.name}/{benchmark_case.case_id}] "
                    f"candidate exception: "
                    f"{candidate_exception['exception_type']}: "
                    f"{candidate_exception['message']}"
                )

            case_finished_at = _utc_now()
            case_elapsed_seconds = round(time.perf_counter() - case_started, 3)
            case_record = {
                "schema_version": BENCHMARK_SCHEMA,
                "candidate_index": index,
                "candidate_name": candidate.name,
                "model": candidate.model,
                "case_index": case_index,
                "case_id": benchmark_case.case_id,
                "case_name": benchmark_case.name,
                "workspace_root": benchmark_case.workspace_root,
                "request": benchmark_case.request,
                "started_at": case_started_at,
                "finished_at": case_finished_at,
                "elapsed_seconds": case_elapsed_seconds,
                "ok": bool(response is not None and response.ok),
                "raw_response": (
                    response.payload
                    if response is not None and response.ok
                    else None
                ),
                "error": (
                    candidate_exception
                    if response is None
                    else (None if response.ok else dict(response.error or {}))
                ),
                "adapter_metadata": (
                    {} if response is None else dict(response.metadata)
                ),
                "tool_ids": list(tool_ids),
                "turns": adapter._benchmark_turn,
                "tool_calls": adapter._benchmark_tool_calls,
            }
            result_path = run_root / (
                f"{index:02d}-{_slug(candidate.name)}-"
                f"{case_index:02d}-{_slug(benchmark_case.case_id)}.json"
            )
            result_path.write_text(
                json.dumps(case_record, ensure_ascii=False, indent=2, default=str)
                + "\n",
                encoding="utf-8",
            )
            case_results.append(
                {
                    "case_id": benchmark_case.case_id,
                    "case_name": benchmark_case.name,
                    "ok": bool(response is not None and response.ok),
                    "elapsed_seconds": case_elapsed_seconds,
                    "turns": adapter._benchmark_turn,
                    "tool_calls": adapter._benchmark_tool_calls,
                    "result_file": result_path.name,
                }
            )
            print(
                f"[{index}/{len(enabled)} case {case_index}/{len(cases)}] "
                f"{candidate.name}/{benchmark_case.case_id}: "
                f"{'OK' if response is not None and response.ok else 'ERROR'} "
                f"({case_elapsed_seconds}s) "
                f"| turns {adapter._benchmark_turn} "
                f"| tool calls {adapter._benchmark_tool_calls}"
            )

        loaded = _ollama_ps()
        unload = (
            _unload_model(candidate.model)
            if config.get("unload_after_each", True)
            else {"skipped": True}
        )
        after = _ollama_ps()
        model_finished_at = _utc_now()
        model_elapsed_seconds = round(time.perf_counter() - model_started, 3)

        model_record = {
            "candidate_name": candidate.name,
            "model": candidate.model,
            "started_at": model_started_at,
            "finished_at": model_finished_at,
            "elapsed_seconds": model_elapsed_seconds,
            "cases": case_results,
            "ollama_before": before,
            "ollama_loaded": loaded,
            "unload": unload,
            "ollama_after": after,
        }
        model_path = run_root / f"{index:02d}-{_slug(candidate.name)}-summary.json"
        model_path.write_text(
            json.dumps(model_record, ensure_ascii=False, indent=2, default=str)
            + "\n",
            encoding="utf-8",
        )
        results.append(
            {
                "candidate_name": candidate.name,
                "model": candidate.model,
                "elapsed_seconds": model_elapsed_seconds,
                "cases": case_results,
                "result_file": model_path.name,
            }
        )

    summary = {
        "schema_version": BENCHMARK_SCHEMA,
        "created_at": _utc_now(),
        "config_path": str(config_path),
        "project_root": str(project_root),
        "output_root": str(run_root),
        "base_url": base_url,
        "system_prompt": system_prompt,
        "cases": [
            {
                "case_id": item.case_id,
                "name": item.name,
                "request": item.request,
                "workspace_root": item.workspace_root,
            }
            for item in cases
        ],
        "tool_ids": list(tool_ids),
        "initial_ollama_ps": initial_ollama_ps,
        "candidate_cleanup": candidate_cleanup,
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
        description="Run a serial loose-output benchmark across Planner model candidates."
    )
    parser.add_argument(
        "--config",
        default="config/planner_output_benchmark.json",
        help="Benchmark configuration JSON.",
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-root", default="planner_benchmark_results")
    parser.add_argument(
        "--start-at",
        help="Start at the named candidate/model and continue through the remaining list.",
    )
    args = parser.parse_args()

    try:
        run_benchmark(
            config_path=Path(args.config),
            project_root=Path(args.project_root),
            output_root=Path(args.output_root),
            start_at=args.start_at,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
