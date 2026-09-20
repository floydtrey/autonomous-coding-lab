"""Contract-level self-checks for Planner V1."""
from __future__ import annotations

import unittest

from acl_roles.planner import (
    ExecutionPlan,
    PlannerDisposition,
    PlannerInput,
    PlannerInvocationMode,
    PlannerResult,
)
from acl_roles.common.errors import RoleContractError


def _task(task_id: str, instruction: str, *, write_path: str | None = None) -> dict:
    return {
        "task_id": task_id,
        "name": task_id,
        "instruction": instruction,
        "depends_on": [],
        "filesystem": {
            "read_paths": [],
            "write_paths": [] if write_path is None else [write_path],
            "create_paths": [],
            "delete_paths": [],
            "move_paths": [],
        },
        "reference_ids": [],
        "expected_result": "Requested task is completed.",
        "acceptance_criteria": [],
        "evidence_required": [],
    }


def _pass(pass_id: str, task: dict, *, depends_on: list[str] | None = None) -> dict:
    return {
        "pass_id": pass_id,
        "name": pass_id,
        "objective": f"Complete {pass_id}.",
        "complexity": "SMALL",
        "depends_on": depends_on or [],
        "working_directory": None,
        "output_directory": None,
        "reference_ids": [],
        "expected_outputs": [],
        "acceptance_criteria": [f"{pass_id} objective is satisfied."],
        "evidence_required": ["changed_files"],
        "tracking_requirements": ["changed_files"],
        "continuation_instructions": "Resume from the first incomplete task in this pass.",
        "tasks": [task],
    }


def _plan(*, staged: bool = False) -> dict:
    workspace = {
        "worker_working_directory": "C:/Projects/Example",
        "output_directory": "C:/Projects/Example",
        "artifact_directory": "C:/Projects/Example/.acl-artifacts",
        "temporary_directory": None,
    }
    common = {
        "project": {
            "project_name": "Example",
            "version_id": "v1",
            "project_root": "C:/Projects/Example",
        },
        "work_type_id": "1127",
        "task_type": "CODING",
        "complexity": "MEDIUM",
        "required_capabilities": ["code_edit"],
        "required_tools": ["filesystem", "test_runner"],
        "required_services": [],
        "research_requirements": [],
        "objective": "Make the requested change.",
        "acceptance_criteria": ["The requested behavior works."],
        "required_outputs": ["Updated project files"],
        "constraints": ["Preserve unrelated behavior."],
        "out_of_scope": [],
        "assumptions": [],
        "unresolved_questions": [],
        "workspace": workspace,
        "reference_material": [],
        "sources": [],
        "tracking_requirements": ["changed_files", "test_results"],
        "decomposition_reason": None,
    }
    if staged:
        common["decomposition_reason"] = "The work has a distinct implementation stage."
        common.update(
            {
                "plan_type": "STAGED",
                "passes": [],
                "stages": [
                    {
                        "stage_id": "S01",
                        "name": "Implementation",
                        "objective": "Implement and verify the change.",
                        "depends_on": [],
                        "acceptance_criteria": ["Implementation stage completes."],
                        "passes": [
                            _pass(
                                "P01",
                                _task(
                                    "T01",
                                    "Modify the recorder implementation.",
                                    write_path="C:/Projects/Example/recorder.html",
                                ),
                            )
                        ],
                    }
                ],
            }
        )
    else:
        common.update(
            {
                "plan_type": "SINGLE_PASS",
                "stages": [],
                "passes": [
                    _pass(
                        "P01",
                        _task(
                            "T01",
                            "Modify the recorder implementation.",
                            write_path="C:/Projects/Example/recorder.html",
                        ),
                    )
                ],
            }
        )
    return common


class PlannerContractTests(unittest.TestCase):
    def test_initial_input_round_trip(self) -> None:
        value = {
            "schema_version": "acl-planner-input:v1",
            "invocation_mode": "INITIAL_PLANNING",
            "request": {"text": "Fix the recorder."},
            "routing_context": {"work_type_id": "1127", "complexity": "MEDIUM"},
            "consultation": None,
            "elevation_answers": {},
            "correction": None,
            "metadata": {},
        }
        parsed = PlannerInput.from_mapping(value)
        self.assertEqual(parsed.invocation_mode, PlannerInvocationMode.INITIAL_PLANNING)
        self.assertEqual(parsed.to_objective(), value)

    def test_worker_consultation_input(self) -> None:
        value = {
            "schema_version": "acl-planner-input:v1",
            "invocation_mode": "WORKER_CONSULTATION",
            "request": {"text": "Continue the current pass."},
            "routing_context": {"work_type_id": "1127"},
            "consultation": {
                "plan_id": "plan:example123",
                "pass_id": "P01",
                "task_id": "T01",
                "question": "Should the existing public interface remain unchanged?",
                "reason": "Two implementations are possible.",
                "current_state_summary": "Implementation is paused before changing the interface.",
                "relevant_reference_ids": [],
                "relevant_evidence": [],
            },
            "elevation_answers": {},
            "metadata": {},
        }
        parsed = PlannerInput.from_mapping(value)
        self.assertEqual(parsed.invocation_mode, PlannerInvocationMode.WORKER_CONSULTATION)
        self.assertEqual(parsed.consultation.pass_id, "P01")

    def test_direct_response(self) -> None:
        result = PlannerResult.from_mapping(
            {
                "schema_version": "acl-planner-result:v1",
                "disposition": "DIRECT_RESPONSE",
                "answer": {
                    "answer": "Seven.",
                    "sources": [],
                    "references": [],
                },
                "plan": None,
                "questions": [],
                "reason_codes": [],
                "notes": None,
            }
        )
        self.assertEqual(result.disposition, PlannerDisposition.DIRECT_RESPONSE)

    def test_query_response(self) -> None:
        result = PlannerResult.from_mapping(
            {
                "schema_version": "acl-planner-result:v1",
                "disposition": "QUERY_RESPONSE",
                "answer": {
                    "answer": "The file is C:/Projects/Example/recorder.html.",
                    "sources": [],
                    "references": ["file:C:/Projects/Example/recorder.html"],
                },
                "plan": None,
                "questions": [],
                "reason_codes": [],
                "notes": None,
            }
        )
        self.assertEqual(result.disposition, PlannerDisposition.QUERY_RESPONSE)

    def test_elevation_required(self) -> None:
        result = PlannerResult.from_mapping(
            {
                "schema_version": "acl-planner-result:v1",
                "disposition": "ELEVATION_REQUIRED",
                "answer": None,
                "plan": None,
                "questions": [
                    {
                        "question_id": "Q01",
                        "question": "Replace the existing recorder or create a new version?",
                        "reason": "The requested output target is ambiguous.",
                        "options": ["Replace existing", "Create new version"],
                    }
                ],
                "reason_codes": ["OUTPUT_TARGET_AMBIGUOUS"],
                "notes": None,
            }
        )
        self.assertEqual(result.disposition, PlannerDisposition.ELEVATION_REQUIRED)

    def test_single_pass_execution_plan(self) -> None:
        result = PlannerResult.from_mapping(
            {
                "schema_version": "acl-planner-result:v1",
                "disposition": "EXECUTION_PLAN",
                "answer": None,
                "plan": _plan(),
                "questions": [],
                "reason_codes": [],
                "notes": None,
            }
        )
        self.assertEqual(result.plan.passes[0].tasks[0].task_id, "T01")
        self.assertEqual(result.plan.workspace.output_directory, "C:/Projects/Example")

    def test_staged_execution_plan(self) -> None:
        plan = ExecutionPlan.from_mapping(_plan(staged=True))
        self.assertEqual(plan.stages[0].stage_id, "S01")
        self.assertEqual(plan.stages[0].passes[0].pass_id, "P01")

    def test_multi_pass_execution_plan(self) -> None:
        value = _plan()
        value["plan_type"] = "MULTI_PASS"
        value["decomposition_reason"] = "The second pass depends on the first pass."
        value["passes"].append(
            _pass(
                "P02",
                _task("T02", "Run the follow-up verification."),
                depends_on=["P01"],
            )
        )
        plan = ExecutionPlan.from_mapping(value)
        self.assertEqual([item.pass_id for item in plan.passes], ["P01", "P02"])

    def test_execution_plan_requires_output_directory(self) -> None:
        value = _plan()
        value["workspace"]["output_directory"] = None
        with self.assertRaises(RoleContractError):
            ExecutionPlan.from_mapping(value)

    def test_pass_requires_continuation_instructions(self) -> None:
        value = _plan()
        value["passes"][0]["continuation_instructions"] = None
        with self.assertRaises(RoleContractError):
            ExecutionPlan.from_mapping(value)

    def test_disposition_payloads_are_exclusive(self) -> None:
        with self.assertRaises(RoleContractError):
            PlannerResult.from_mapping(
                {
                    "schema_version": "acl-planner-result:v1",
                    "disposition": "DIRECT_RESPONSE",
                    "answer": {
                        "answer": "Seven.",
                        "sources": [],
                        "references": [],
                    },
                    "plan": _plan(),
                    "questions": [],
                    "reason_codes": [],
                    "notes": None,
                }
            )


if __name__ == "__main__":
    unittest.main()
