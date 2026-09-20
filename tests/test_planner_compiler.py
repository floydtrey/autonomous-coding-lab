"""Tests for deterministic compilation of semantic Planner output."""
from __future__ import annotations

import unittest

from acl_controller.planner.compiler import (
    WORKER_AUTHORITY_MODE_WORKSPACE,
    compile_planner_semantic_submission,
)
from acl_roles.planner import (
    PlannerInput,
    PlannerInvocationMode,
    PlannerSemanticSubmission,
)


def _input() -> PlannerInput:
    return PlannerInput(
        invocation_mode=PlannerInvocationMode.INITIAL_PLANNING,
        request={"text": "Repair the calculator."},
        routing_context={
            "work_type_id": "1127",
            "complexity": "MEDIUM",
        },
        metadata={
            "project_context": {
                "project_root": "C:/Projects/Example",
                "worker_working_directory": "C:/Projects/Example/work",
                "output_directory": "C:/Projects/Example/work",
                "artifact_directory": "C:/Projects/Example/.acl-artifacts",
            }
        },
    )


class PlannerCompilerTests(unittest.TestCase):
    def test_compiles_semantic_passes_without_model_controller_bookkeeping(self) -> None:
        submission = PlannerSemanticSubmission.from_mapping(
            {
                "schema_version": "acl-planner-semantic:v1",
                "disposition": "EXECUTION_PLAN",
                "objective": "Repair the calculator.",
                "constraints": ["Preserve unrelated behavior."],
                "passes": [
                    {
                        "objective": "Inspect the current implementation.",
                        "tasks": [
                            {"instruction": "Inspect the relevant files."},
                        ],
                    },
                    {
                        "objective": "Implement and verify the repair.",
                        "tasks": [
                            {"instruction": "Implement the requested behavior."},
                            {"instruction": "Verify the completed work."},
                        ],
                    },
                ],
            }
        )

        compiled = compile_planner_semantic_submission(submission, _input())
        plan = compiled.result.plan

        self.assertEqual(compiled.worker_authority_mode, WORKER_AUTHORITY_MODE_WORKSPACE)
        self.assertEqual(plan.work_type_id, "1127")
        self.assertEqual(plan.workspace.worker_working_directory, "C:/Projects/Example/work")
        self.assertEqual([item.pass_id for item in plan.passes], ["P01", "P02"])
        self.assertEqual(
            [task.task_id for item in plan.passes for task in item.tasks],
            ["T01", "T02", "T03"],
        )
        self.assertEqual(plan.passes[1].depends_on, ("P01",))
        self.assertEqual(plan.passes[1].tasks[1].depends_on, ("T02",))
        self.assertEqual(plan.passes[0].tasks[0].filesystem.write_paths, ())

    def test_assigns_question_ids_mechanically(self) -> None:
        submission = PlannerSemanticSubmission.from_mapping(
            {
                "schema_version": "acl-planner-semantic:v1",
                "disposition": "ELEVATION_REQUIRED",
                "questions": [
                    {
                        "question": "Which target?",
                        "reason": "Two targets are possible.",
                    }
                ],
            }
        )

        compiled = compile_planner_semantic_submission(submission, _input())

        self.assertEqual(compiled.result.questions[0].question_id, "Q01")

    def test_compiles_direct_response_without_project_context_use(self) -> None:
        submission = PlannerSemanticSubmission.from_mapping(
            {
                "schema_version": "acl-planner-semantic:v1",
                "disposition": "DIRECT_RESPONSE",
                "answer": "No Worker execution is required.",
            }
        )
        planner_input = PlannerInput(
            invocation_mode=PlannerInvocationMode.INITIAL_PLANNING,
            request={"text": "Answer directly."},
        )

        compiled = compile_planner_semantic_submission(submission, planner_input)

        self.assertEqual(
            compiled.result.answer.answer,
            "No Worker execution is required.",
        )


if __name__ == "__main__":
    unittest.main()
