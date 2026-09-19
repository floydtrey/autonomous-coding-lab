"""Generic ACL workflow runner used for local integration and later operation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from acl_controller import ControllerService, WorkflowProgram
from acl_core import configure_diagnostics
from acl_roles.common import RoleDiagnostics
from .services import LocalServiceSupervisor


def load_program(path: Path) -> WorkflowProgram:
    path = Path(path).expanduser().resolve()
    value = json.loads(path.read_text(encoding="utf-8"))
    return WorkflowProgram.from_mapping(value)


def run_program(
    *,
    config_root: Path,
    state_root: Path,
    program_path: Path,
    request_kind: str,
    request_payload: Mapping[str, Any],
    requester: str | None = None,
    max_operations: int = 32,
):
    config_root = Path(config_root).expanduser().resolve()
    state_root = Path(state_root).expanduser().resolve()
    project_root = config_root.parent

    service_status = LocalServiceSupervisor(
        project_root=project_root,
    ).ensure_file(config_root / "services.json")

    controller = ControllerService.create(
        state_root=state_root,
        config_root=config_root,
    )
    program = load_program(program_path)
    controller.install_program(program)
    workflow = controller.create_workflow(
        request_kind,
        request_payload,
        requester=requester,
    )
    controller.bind_program(workflow.workflow_id, program.program_id)
    report = controller.run_workflow(
        workflow.workflow_id,
        max_operations=max_operations,
    )
    inspection = controller.inspect_workflow(workflow.workflow_id)
    return {
        "ok": True,
        "services": list(service_status),
        "engine": report.to_dict(),
        "inspection": inspection.to_dict(),
    }


def _request_payload(args: argparse.Namespace) -> dict[str, Any]:
    supplied = sum(
        value is not None
        for value in (args.request_text, args.request_json, args.request_file)
    )
    if supplied != 1:
        raise SystemExit("Provide exactly one of --request-text, --request-json, or --request-file.")

    if args.request_text is not None:
        return {"text": args.request_text}
    if args.request_json is not None:
        value = json.loads(args.request_json)
    else:
        value = json.loads(Path(args.request_file).expanduser().read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("Request JSON must contain an object.")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an ACL Next workflow program.")
    parser.add_argument("--config-root", default="config")
    parser.add_argument("--state-root", default=".acl-state")
    parser.add_argument("--program", required=True)
    parser.add_argument("--request-kind", default="user_request")
    parser.add_argument("--requester")
    parser.add_argument("--request-text")
    parser.add_argument("--request-json")
    parser.add_argument("--request-file")
    parser.add_argument("--max-operations", type=int, default=32)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--log-path", default="logs/acl-next.jsonl")
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
        result = run_program(
            config_root=Path(args.config_root),
            state_root=Path(args.state_root),
            program_path=Path(args.program),
            request_kind=args.request_kind,
            request_payload=_request_payload(args),
            requester=args.requester,
            max_operations=args.max_operations,
        )
    except Exception as exc:
        details = {}
        to_dict = getattr(exc, "to_dict", None)
        if callable(to_dict):
            try:
                details = to_dict()
            except Exception:
                details = {}
        error_result = {
            "ok": False,
            "error": {
                "exception_type": type(exc).__name__,
                "message": str(exc),
                "details": details,
            },
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2, default=str))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
