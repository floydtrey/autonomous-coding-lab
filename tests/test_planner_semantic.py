"""Tests for the small model-facing Planner semantic contract."""
from __future__ import annotations

import unittest

from acl_roles.common import RoleResponse, RoleStatus
from acl_roles.common.errors import RoleContractError
from acl_roles.planner import (
    PlannerDisposition,
    PlannerSemanticSubmission,
    parse_planner_semantic_role_response,
)


class PlannerSemanticTests(unittest.TestCase):
    def test_compact_execution_submission(self) -> None:
        response = RoleResponse(
            status=RoleStatus.COMPLETE,
            payload={
                "schema_version": "acl-planner-semantic:v1",
                "disposition": "EXECUTION_PLAN",
                "objective": "Repair the calculator.",
                "constraints": ["Preserve unrelated behavior."],
                "passes": [
                    {
                        "objective": "Inspect and implement the repair.",
                        "tasks": [
                            {"instruction": "Inspect the relevant files."},
                            {
                                "instruction": "Implement the required behavior.",
                                "acceptance_criteria": [
                                    "The requested behavior is implemented."
                                ],
                            },
                        ],
                    }
                ],
            },
        )

        parsed = parse_planner_semantic_role_response(response)

        self.assertEqual(parsed.disposition, PlannerDisposition.EXECUTION_PLAN)
        self.assertEqual(parsed.objective, "Repair the calculator.")
        self.assertEqual(len(parsed.passes), 1)
        self.assertEqual(len(parsed.passes[0].tasks), 2)

    def test_elevation_questions_do_not_require_controller_ids(self) -> None:
        response = RoleResponse(
            status=RoleStatus.NEEDS_CLARIFICATION,
            payload={
                "schema_version": "acl-planner-semantic:v1",
                "disposition": "ELEVATION_REQUIRED",
                "questions": [
                    {
                        "question": "Which output should be replaced?",
                        "reason": "The request names two possible targets.",
                        "options": ["first", "second"],
                    }
                ],
            },
        )

        parsed = parse_planner_semantic_role_response(response)

        self.assertEqual(len(parsed.questions), 1)
        self.assertEqual(parsed.questions[0].question, "Which output should be replaced?")

    def test_direct_response_is_small(self) -> None:
        parsed = PlannerSemanticSubmission.from_mapping(
            {
                "schema_version": "acl-planner-semantic:v1",
                "disposition": "DIRECT_RESPONSE",
                "answer": "Seven.",
            }
        )
        self.assertEqual(parsed.answer, "Seven.")
        self.assertEqual(
            parsed.to_dict(),
            {
                "schema_version": "acl-planner-semantic:v1",
                "disposition": "DIRECT_RESPONSE",
                "answer": "Seven.",
            },
        )

    def test_rejects_controller_shaped_execution_fields(self) -> None:
        with self.assertRaises(RoleContractError):
            PlannerSemanticSubmission.from_mapping(
                {
                    "schema_version": "acl-planner-semantic:v1",
                    "disposition": "EXECUTION_PLAN",
                    "objective": "Do the work.",
                    "passes": [],
                    "workspace": {
                        "worker_working_directory": "C:/Projects/Example"
                    },
                }
            )

    def test_status_must_match_elevation(self) -> None:
        with self.assertRaises(RoleContractError):
            parse_planner_semantic_role_response(
                RoleResponse(
                    status=RoleStatus.COMPLETE,
                    payload={
                        "schema_version": "acl-planner-semantic:v1",
                        "disposition": "ELEVATION_REQUIRED",
                        "questions": [
                            {
                                "question": "Which target?",
                                "reason": "Two targets are possible.",
                            }
                        ],
                    },
                )
            )


if __name__ == "__main__":
    unittest.main()
