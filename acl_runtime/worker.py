"""Manual Worker V1 integration runner.

This runner consumes an already-persisted Planner plan and executes exactly the
current deterministic next Pass through the configured Worker runtime.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from acl_controller import ControllerService
from acl_core.diagnostics import configure as configure_diagnostics
from acl_roles.common import RoleDiagnostics


def run_worker(
    *,
    config_root: Path,
    state_root: Path,
    project_root: Path,
    plan_id: str,
) -> dict:
    config_root = Path(config_root).expanduser().resolve()
    state_root = Path(state_root).expanduser().resolve()
    project_root = Path(project_root).expanduser().resolve()

    controller = ControllerService.create(
        state_root=state_root,
        config_root=config_root,
        project_root=project_root,
    )
    outcome = controller.run_next_worker_pass(
        plan_id,
        metadata={"integration_phase": "WORKER_V1"},
    )
    run = outcome.run
    review_packet = None
    if outcome.to_dict()["review_required"]:
        review_packet = controller.worker_review_packet(run.worker_run_id).to_dict()

    return {
        "ok": True,
        "worker": outcome.to_dict(),
        "review_packet": review_packet,
        "workflow": controller.status(run.workflow_id).to_dict(),
        "runtime_checkpoint": (
            None
            if controller.runtime_checkpoint(run.workflow_id) is None
            else controller.runtime_checkpoint(run.workflow_id).to_dict()
        ),
        "worker_telemetry": controller.worker_telemetry_summary(
            run.workflow_id
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the deterministic next ACL Planner Pass through Worker V1."
    )
    parser.add_argument("--config-root", default="config")
    parser.add_argument("--state-root", default=".acl-state")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--plan-id", required=True)
    parser.add_argument(
        "--model",
        help="Set ACL_WORKER_MODEL for this process.",
    )
    parser.add_argument(
        "--context-window",
        type=int,
        help="Set ACL_WORKER_CONTEXT_WINDOW for this process.",
    )
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--log-path", default="logs/acl-next.jsonl")
    parser.add_argument("--raw-role-artifacts", action="store_true")
    parser.add_argument("--raw-role-path", default="logs/role-artifacts")
    args = parser.parse_args()

    if args.model:
        os.environ["ACL_WORKER_MODEL"] = args.model
    if args.context_window is not None:
        if args.context_window <= 0:
            parser.error("--context-window must be positive")
        os.environ["ACL_WORKER_CONTEXT_WINDOW"] = str(args.context_window)

    if args.debug:
        configure_diagnostics(
            enabled=True,
            level="DEBUG",
            path=Path(args.log_path),
            stderr=True,
        )
    if args.raw_role_artifacts:
        RoleDiagnostics.configure_raw_artifacts(
            enabled=True,
            root=Path(args.raw_role_path),
        )

    try:
        result = run_worker(
            config_root=Path(args.config_root),
            state_root=Path(args.state_root),
            project_root=Path(args.project_root),
            plan_id=args.plan_id,
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
