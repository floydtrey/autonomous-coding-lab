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
import time
from typing import Any, Mapping

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


class LoosePlannerBenchmarkAdapter(OpenAICompatibleAgentAdapter):
    """Existing ACL tool loop with no ACL role-envelope/output-format demand."""

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


def _user_prompt(*, request_text: str, project_root: Path) -> str:
    return (
        "USER REQUEST\n"
        f"{request_text.strip()}\n\n"
        "WORKSPACE\n"
        f"Project root: {project_root}\n"
        "You may inspect files and directories with the available read-only tools "
        "before producing the handoff."
    )


def run_benchmark(
    *,
    config_path: Path,
    project_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    project_root = project_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    config_root = project_root / "config"

    config = _load_config(config_path)
    base_url = config.get("base_url", "http://127.0.0.1:11434/v1")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("base_url must be nonblank text")

    request_text = config.get("request")
    if not isinstance(request_text, str) or not request_text.strip():
        raise ValueError("benchmark request must be nonblank text")

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

    user_prompt = _user_prompt(request_text=request_text, project_root=project_root)
    results: list[dict[str, Any]] = []

    for index, candidate in enumerate(enabled, start=1):
        model_started = time.perf_counter()
        started_at = _utc_now()
        grant = _read_grant(core, tool_ids=tool_ids, subject=candidate.model)
        before = _ollama_ps()

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

        role_request = {
            "schema_version": BENCHMARK_SCHEMA,
            "workflow_id": f"benchmark:{stamp}:{index:02d}",
            "attempt_id": f"attempt:{index:02d}",
            "role": "planner",
            "benchmark_system_prompt": system_prompt,
            "benchmark_user_prompt": user_prompt,
            "objective": {"request": request_text},
            "context": {"project_root": str(project_root)},
            "authority_grant_id": grant.grant_id,
            "tool_ids": list(tool_ids),
            "metadata": {
                "benchmark": True,
                "candidate_name": candidate.name,
            },
            "execution": execution,
        }
        response = adapter.invoke(
            AdapterRequest(
                operation="role.invoke",
                payload={
                    "role_request": role_request,
                    "authority": {"grant": grant.to_dict()},
                },
            )
        )

        unload = (
            _unload_model(candidate.model)
            if config.get("unload_after_each", True)
            else {"skipped": True}
        )
        after = _ollama_ps()
        finished_at = _utc_now()
        elapsed_seconds = round(time.perf_counter() - model_started, 3)

        record = {
            "schema_version": BENCHMARK_SCHEMA,
            "candidate_index": index,
            "candidate_name": candidate.name,
            "model": candidate.model,
            "started_at": started_at,
            "finished_at": finished_at,
            "elapsed_seconds": elapsed_seconds,
            "ok": response.ok,
            "raw_response": response.payload if response.ok else None,
            "error": None if response.ok else dict(response.error or {}),
            "adapter_metadata": dict(response.metadata),
            "tool_ids": list(tool_ids),
            "ollama_before": before,
            "unload": unload,
            "ollama_after": after,
        }
        result_path = run_root / f"{index:02d}-{_slug(candidate.name)}.json"
        result_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        results.append(
            {
                "candidate_name": candidate.name,
                "model": candidate.model,
                "ok": response.ok,
                "elapsed_seconds": elapsed_seconds,
                "result_file": result_path.name,
            }
        )
        print(
            f"[{index}/{len(enabled)}] {candidate.name}: "
            f"{'OK' if response.ok else 'ERROR'} ({elapsed_seconds}s)"
        )

    summary = {
        "schema_version": BENCHMARK_SCHEMA,
        "created_at": _utc_now(),
        "config_path": str(config_path),
        "project_root": str(project_root),
        "output_root": str(run_root),
        "base_url": base_url,
        "system_prompt": system_prompt,
        "request": request_text,
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
    args = parser.parse_args()

    try:
        run_benchmark(
            config_path=Path(args.config),
            project_root=Path(args.project_root),
            output_root=Path(args.output_root),
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
