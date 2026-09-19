"""Run Planner Model A through the real ACL Planner V1 path.

This is a local integration runner, not a benchmark harness. It creates an ACL
workflow, invokes Planner through ControllerService, applies fast-path handling,
optionally persists an execution plan through PL10 intake, and prints Planner
telemetry.

Model/server selection remains external. --model only sets ACL_PLANNER_MODEL for
this process; Controller/Planner code never contains a concrete model name.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

from acl_controller import ControllerService, PlannerOutcomeStatus
from acl_core import configure_diagnostics
from acl_roles.common import RoleDiagnostics
from acl_roles.planner import PlannerInput, PlannerInvocationMode

from .services import LocalServiceSupervisor


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
        raise ValueError("Planner request JSON must contain an object")
    return value


def run_planner_model_a(
    *,
    config_root: Path,
    state_root: Path,
    project_root: Path,
    request_payload: Mapping[str, Any],
    work_type_id: str,
    complexity: str | None,
    requester: str | None = None,
    working_directory: Path | None = None,
    output_directory: Path | None = None,
    artifact_directory: Path | None = None,
    intake_plan: bool = True,
) -> dict[str, Any]:
    config_root = Path(config_root).expanduser().resolve()
    state_root = Path(state_root).expanduser().resolve()
    project_root = Path(project_root).expanduser().resolve()
    working_directory = (
        project_root
        if working_directory is None
        else Path(working_directory).expanduser().resolve()
    )
    output_directory = (
        project_root
        if output_directory is None
        else Path(output_directory).expanduser().resolve()
    )
    artifact_directory = (
        None
        if artifact_directory is None
        else Path(artifact_directory).expanduser().resolve()
    )

    service_status = LocalServiceSupervisor(
        project_root=project_root,
    ).ensure_file(config_root / "services.json")

    controller = ControllerService.create(
        state_root=state_root,
        config_root=config_root,
        project_root=project_root,
    )
    workflow = controller.create_workflow(
        "planner_request",
        dict(request_payload),
        requester=requester,
    )
    planner_input = PlannerInput(
        invocation_mode=PlannerInvocationMode.INITIAL_PLANNING,
        request=dict(request_payload),
        routing_context={
            "work_type_id": work_type_id,
            "complexity": complexity,
        },
        metadata={
            "project_context": {
                "project_root": str(project_root),
                "worker_working_directory": str(working_directory),
                "output_directory": str(output_directory),
                "artifact_directory": (
                    None if artifact_directory is None else str(artifact_directory)
                ),
            }
        },
    )

    outcome = controller.run_planner(
        workflow.workflow_id,
        planner_input=planner_input,
        metadata={"integration_phase": "PL12_MODEL_A"},
    )

    intake = None
    if intake_plan and outcome.status is PlannerOutcomeStatus.PLAN_READY:
        intake = controller.intake_planner_outcome(
            outcome,
            metadata={"integration_phase": "PL12_MODEL_A"},
        )

    return {
        "ok": True,
        "services": list(service_status),
        "workflow_id": workflow.workflow_id,
        "planner": outcome.to_dict(),
        "plan_intake": None if intake is None else intake.to_dict(),
        "workflow": controller.status(workflow.workflow_id).to_dict(),
        "planner_telemetry": controller.planner_telemetry_summary(
            workflow.workflow_id
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run ACL Planner Model A through Planner V1."
    )
    parser.add_argument("--config-root", default="config")
    parser.add_argument("--state-root", default=".acl-state")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--working-directory")
    parser.add_argument("--output-directory")
    parser.add_argument("--artifact-directory")
    parser.add_argument("--work-type-id", default="1127")
    parser.add_argument(
        "--complexity",
        choices=("SMALL", "MEDIUM", "LARGE"),
        default="MEDIUM",
    )
    parser.add_argument("--requester", default="operator")
    request_group = parser.add_mutually_exclusive_group(required=True)
    request_group.add_argument("--request-text")
    request_group.add_argument("--request-json")
    request_group.add_argument("--request-file")
    parser.add_argument(
        "--model",
        help="Set ACL_PLANNER_MODEL for this process. If omitted, use the existing environment.",
    )
    parser.add_argument(
        "--context-window",
        type=int,
        help="Set ACL_PLANNER_CONTEXT_WINDOW for telemetry/runtime configuration.",
    )
    parser.add_argument("--no-intake", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--log-path", default="logs/acl-next.jsonl")
    parser.add_argument("--raw-role-artifacts", action="store_true")
    parser.add_argument("--raw-role-path", default="logs/role-artifacts")
    args = parser.parse_args()

    if args.model:
        os.environ["ACL_PLANNER_MODEL"] = args.model
    if args.context_window is not None:
        if args.context_window <= 0:
            parser.error("--context-window must be positive")
        os.environ["ACL_PLANNER_CONTEXT_WINDOW"] = str(args.context_window)

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
        result = run_planner_model_a(
            config_root=Path(args.config_root),
            state_root=Path(args.state_root),
            project_root=Path(args.project_root),
            working_directory=(
                None
                if args.working_directory is None
                else Path(args.working_directory)
            ),
            output_directory=(
                None if args.output_directory is None else Path(args.output_directory)
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
            work_type_id=args.work_type_id,
            complexity=args.complexity,
            requester=args.requester,
            intake_plan=not args.no_intake,
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
