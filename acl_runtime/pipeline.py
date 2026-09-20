"""Connected ACL V1 intake runner.

This is a thin orchestration seam over the already-proven Controller services:
Determiner classifies the request, Planner receives the accepted route, and an
accepted Planner plan may optionally continue into the deterministic next Worker
Pass. Role semantics, routing, runtime residency, authority, and validation stay
owned by their existing services.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from acl_core import configure_diagnostics
from acl_roles.common import RoleDiagnostics

from .planner import run_planner_model_a
from .runner import run_program
from .worker import run_worker


def _load_request(
    *,
    request_text: str | None,
    request_json: str | None,
    request_file: str | None,
) -> dict[str, Any]:
    supplied = sum(
        value is not None
        for value in (request_text, request_json, request_file)
    )
    if supplied != 1:
        raise ValueError(
            "provide exactly one of request_text, request_json, or request_file"
        )
    if request_text is not None:
        return {"text": request_text}
    if request_json is not None:
        value = json.loads(request_json)
    else:
        value = json.loads(
            Path(request_file).expanduser().read_text(encoding="utf-8")
        )
    if not isinstance(value, dict):
        raise ValueError("request JSON must contain an object")
    return value


def _accepted_determiner_route(
    determiner: Mapping[str, Any],
) -> tuple[str, str | None] | None:
    inspection = determiner.get("inspection")
    if not isinstance(inspection, Mapping):
        return None
    results = inspection.get("results")
    if not isinstance(results, list):
        return None
    for item in reversed(results):
        if not isinstance(item, Mapping):
            continue
        if item.get("executor") != "ROLE":
            continue
        payload = item.get("payload")
        if not isinstance(payload, Mapping):
            continue
        if payload.get("classification") != "CLASSIFIED":
            return None
        work_type_id = payload.get("work_type_id")
        if not isinstance(work_type_id, str) or not work_type_id.strip():
            return None
        complexity = payload.get("complexity")
        if complexity is not None and (
            not isinstance(complexity, str) or not complexity.strip()
        ):
            complexity = None
        return work_type_id.strip(), (
            None if complexity is None else complexity.strip()
        )
    return None


def run_pipeline(
    *,
    config_root: Path,
    state_root: Path,
    project_root: Path,
    request_payload: Mapping[str, Any],
    requester: str | None = "operator",
    working_directory: Path | None = None,
    output_directory: Path | None = None,
    artifact_directory: Path | None = None,
    run_worker_after_plan: bool = False,
) -> dict[str, Any]:
    config_root = Path(config_root).expanduser().resolve()
    state_root = Path(state_root).expanduser().resolve()
    project_root = Path(project_root).expanduser().resolve()

    determiner = run_program(
        config_root=config_root,
        state_root=state_root,
        program_path=config_root / "workflows" / "determiner-only.json",
        request_kind="user_request",
        request_payload=dict(request_payload),
        requester=requester,
        max_operations=32,
    )
    route = _accepted_determiner_route(determiner)
    if route is None:
        return {
            "ok": True,
            "stage": "DETERMINER",
            "determiner": determiner,
            "planner": None,
            "worker": None,
        }

    work_type_id, complexity = route
    planner = run_planner_model_a(
        config_root=config_root,
        state_root=state_root,
        project_root=project_root,
        request_payload=dict(request_payload),
        work_type_id=work_type_id,
        complexity=complexity,
        requester=requester,
        working_directory=working_directory,
        output_directory=output_directory,
        artifact_directory=artifact_directory,
        intake_plan=True,
    )

    worker = None
    if run_worker_after_plan:
        intake = planner.get("plan_intake")
        plan = intake.get("plan") if isinstance(intake, Mapping) else None
        plan_id = plan.get("plan_id") if isinstance(plan, Mapping) else None
        if isinstance(plan_id, str) and plan_id.startswith("plan:"):
            worker = run_worker(
                config_root=config_root,
                state_root=state_root,
                project_root=project_root,
                plan_id=plan_id,
            )

    return {
        "ok": True,
        "stage": "WORKER" if worker is not None else "PLANNER",
        "routing": {
            "work_type_id": work_type_id,
            "complexity": complexity,
        },
        "determiner": determiner,
        "planner": planner,
        "worker": worker,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run connected ACL Determiner -> Planner -> optional Worker."
    )
    parser.add_argument("--config-root", default="config")
    parser.add_argument("--state-root", default=".acl-state")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--working-directory")
    parser.add_argument("--output-directory")
    parser.add_argument("--artifact-directory")
    parser.add_argument("--requester", default="operator")
    request_group = parser.add_mutually_exclusive_group(required=True)
    request_group.add_argument("--request-text")
    request_group.add_argument("--request-json")
    request_group.add_argument("--request-file")
    parser.add_argument(
        "--run-worker",
        action="store_true",
        help="Continue an accepted Planner plan into the deterministic next Worker Pass.",
    )
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--log-path", default="logs/acl-pipeline.jsonl")
    parser.add_argument("--raw-role-artifacts", action="store_true")
    parser.add_argument("--raw-role-path", default="logs/role-artifacts")
    args = parser.parse_args()

    if args.debug:
        configure_diagnostics(
            enabled=True,
            level="DEBUG",
            path=Path(args.log_path),
            stderr=False,
        )
    if args.raw_role_artifacts:
        RoleDiagnostics.configure_raw_artifacts(
            enabled=True,
            root=Path(args.raw_role_path),
        )

    try:
        result = run_pipeline(
            config_root=Path(args.config_root),
            state_root=Path(args.state_root),
            project_root=Path(args.project_root),
            working_directory=(
                None
                if args.working_directory is None
                else Path(args.working_directory)
            ),
            output_directory=(
                None
                if args.output_directory is None
                else Path(args.output_directory)
            ),
            artifact_directory=(
                None
                if args.artifact_directory is None
                else Path(args.artifact_directory)
            ),
            request_payload=_load_request(
                request_text=args.request_text,
                request_json=args.request_json,
                request_file=args.request_file,
            ),
            requester=args.requester,
            run_worker_after_plan=args.run_worker,
        )
    except Exception as exc:
        details = {}
        to_dict = getattr(exc, "to_dict", None)
        if callable(to_dict):
            try:
                details = to_dict()
            except Exception:
                details = {}
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": {
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                        "details": details,
                    },
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
