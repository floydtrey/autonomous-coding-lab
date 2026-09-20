"""Shared ACL workflow recovery CLI.

This is an operator wrapper around ControllerService.recover_workflow(). Recovery
semantics remain owned by Controller; the CLI performs no direct state edits.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from acl_controller import ControllerService
from acl_core.diagnostics import configure as configure_diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recover one ACL workflow through the shared Controller recovery service."
    )
    parser.add_argument("--config-root", default="config")
    parser.add_argument("--state-root", default=".acl-state")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--log-path", default="logs/acl-recovery.jsonl")
    args = parser.parse_args()

    if args.debug:
        configure_diagnostics(
            enabled=True,
            level="DEBUG",
            path=Path(args.log_path),
            stderr=True,
        )

    try:
        controller = ControllerService.create(
            state_root=Path(args.state_root),
            config_root=Path(args.config_root),
            project_root=Path(args.project_root),
        )
        result = controller.recover_workflow(args.workflow_id)
        workflow = controller.status(args.workflow_id).to_dict()
        checkpoint = controller.runtime_checkpoint(args.workflow_id)
        output = {
            "ok": True,
            "recovery_result": (
                result.to_dict()
                if hasattr(result, "to_dict")
                else str(result)
            ),
            "workflow": workflow,
            "runtime_checkpoint": (
                None if checkpoint is None else checkpoint.to_dict()
            ),
        }
    except Exception as exc:
        details = {}
        to_dict = getattr(exc, "to_dict", None)
        if callable(to_dict):
            try:
                details = to_dict()
            except Exception:
                details = {}
        output = {
            "ok": False,
            "error": {
                "exception_type": type(exc).__name__,
                "message": str(exc),
                "details": details,
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
        return 1

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
