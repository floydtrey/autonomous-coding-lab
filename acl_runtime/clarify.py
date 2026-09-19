"""Generic operator command for answering a pending ACL clarification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from acl_controller import ClarificationStatus, ControllerError, ControllerService
from acl_core import configure_diagnostics

from .services import LocalServiceSupervisor


def _load_answer(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--answer-json must be valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("--answer-json must contain a JSON object.")
    return value


def answer_and_resume(
    *,
    clarification_id: str,
    answer: Mapping[str, Any],
    answered_by: str,
    config_root: Path,
    state_root: Path,
    max_operations: int = 32,
) -> dict[str, Any]:
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
    current = controller.clarification.read(clarification_id)
    requested_answer = dict(answer)

    if current.status is ClarificationStatus.PENDING:
        clarification = controller.answer_clarification(
            clarification_id,
            answer=requested_answer,
            answered_by=answered_by,
        )
        resume_mode = "answered_now"
    elif current.status is ClarificationStatus.ANSWERED:
        recorded_answer = dict(current.answer or {})
        if recorded_answer != requested_answer:
            raise ControllerError(
                "CONTROLLER_CLARIFICATION_ANSWER_CONFLICT",
                "clarification is already answered with a different operator response",
                {
                    "clarification_id": clarification_id,
                    "recorded_answer": recorded_answer,
                    "requested_answer": requested_answer,
                },
            )
        clarification = current
        resume_mode = "already_answered_same_value"
    else:
        raise ControllerError(
            "CONTROLLER_CLARIFICATION_NOT_RESUMABLE",
            "clarification is not pending or answered and cannot be resumed",
            {
                "clarification_id": clarification_id,
                "status": str(current.status),
            },
        )
    recovery_result = controller.recover_workflow(clarification.workflow_id)
    to_dict = getattr(recovery_result, "to_dict", None)
    recovery = to_dict() if callable(to_dict) else {"value": str(recovery_result)}

    report = controller.run_workflow(
        clarification.workflow_id,
        max_operations=max_operations,
    )
    inspection = controller.inspect_workflow(clarification.workflow_id)
    return {
        "ok": True,
        "services": list(service_status),
        "clarification": clarification.to_dict(),
        "resume_mode": resume_mode,
        "recovery": recovery,
        "engine": report.to_dict(),
        "inspection": inspection.to_dict(),
        "planner_telemetry": controller.planner_telemetry_summary(clarification.workflow_id),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Answer a pending ACL clarification and resume its workflow."
    )
    parser.add_argument("--clarification-id", required=True)
    answer_group = parser.add_mutually_exclusive_group(required=True)
    answer_group.add_argument(
        "--work-type-id",
        help="Convenience answer for routing clarifications using a four-digit work type ID.",
    )
    answer_group.add_argument(
        "--answer-json",
        help="Generic clarification answer as a JSON object.",
    )
    parser.add_argument("--answered-by", default="operator")
    parser.add_argument("--config-root", default="config")
    parser.add_argument("--state-root", default=".acl-state")
    parser.add_argument("--max-operations", type=int, default=32)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--log-path", default="logs/acl-next.jsonl")
    args = parser.parse_args()

    if args.debug:
        configure_diagnostics(
            enabled=True,
            level="DEBUG",
            path=Path(args.log_path),
            stderr=False,
        )

    if args.work_type_id is not None:
        if len(args.work_type_id) != 4 or not args.work_type_id.isdigit():
            parser.error("--work-type-id must be exactly four digits.")
        answer = {"work_type_id": args.work_type_id}
    else:
        answer = _load_answer(args.answer_json)

    try:
        result = answer_and_resume(
            clarification_id=args.clarification_id,
            answer=answer,
            answered_by=args.answered_by,
            config_root=Path(args.config_root),
            state_root=Path(args.state_root),
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
        print(json.dumps(
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
        ))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
