from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence

try:
    from tools.codex_runtime import CodexExecution, CodexRequest, execute_codex
    from tools.consumer_profile import (
        WorkerContextPacket,
        build_context_packet,
        build_context_prompt,
        verify_context_packet,
    )
except ModuleNotFoundError:  # direct execution support
    from codex_runtime import CodexExecution, CodexRequest, execute_codex  # type: ignore
    from consumer_profile import (  # type: ignore
        WorkerContextPacket,
        build_context_packet,
        build_context_prompt,
        verify_context_packet,
    )


@dataclass(frozen=True)
class ContextProbeResult:
    context_digest: str
    repository_head: str
    sandbox: str
    response: str

    def to_json(self, *, pretty: bool = False) -> str:
        options = {"sort_keys": True}
        if pretty:
            options["indent"] = 2
        else:
            options["separators"] = (",", ":")
        return json.dumps(asdict(self), **options)


Executor = Callable[[CodexRequest], CodexExecution]


def run_context_probe(
    *,
    repo_root: Path,
    framework_repo: Path,
    objective: str,
    allowed_paths: Sequence[str],
    task_context_paths: Sequence[str] = (),
    executor: Executor = execute_codex,
) -> tuple[WorkerContextPacket, ContextProbeResult]:
    packet = build_context_packet(
        repo_root,
        allowed_paths=allowed_paths,
        task_context_paths=task_context_paths,
    )
    execution = executor(
        CodexRequest(
            prompt=build_context_prompt(packet, objective=objective),
            target_repo=repo_root,
            framework_repo=framework_repo,
            sandbox="read-only",
        )
    )
    response = execution.stdout.strip()
    if not response:
        raise ValueError("Codex context probe returned no analysis")
    verify_context_packet(packet, repo_root)
    return packet, ContextProbeResult(
        context_digest=packet.digest(),
        repository_head=packet.repository_head,
        sandbox="read-only",
        response=response,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a read-only repository context probe")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--framework-repo", required=True, type=Path)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--allowed-path", action="append", required=True)
    parser.add_argument("--context-path", action="append", default=[])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _, result = run_context_probe(
        repo_root=args.repo,
        framework_repo=args.framework_repo,
        objective=args.objective,
        allowed_paths=tuple(args.allowed_path),
        task_context_paths=tuple(args.context_path),
    )
    print(result.to_json(pretty=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
