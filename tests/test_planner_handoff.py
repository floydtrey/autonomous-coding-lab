"""Tests for the minimal Planner Handoff V1 parser."""
from __future__ import annotations

import unittest

from acl_roles.common.errors import RoleContractError
from acl_roles.planner.handoff import parse_planner_execution_handoff


class PlannerHandoffParserTests(unittest.TestCase):
    def test_parses_ordered_tasks_with_constraints(self) -> None:
        parsed = parse_planner_execution_handoff(
            """STATUS: READY

OBJECTIVE:
Repair the calculator.

CONSTRAINTS:
Stay inside worker_probe_case2.
Preserve the docstring.

T01: Inspect requirements
Read the requirements and current implementation.
Do not modify files yet.

T02: Implement repair
Modify the calculator using the T01 findings.

T03: Verify
Check the completed work.

END_PLAN
"""
        )

        self.assertEqual(parsed.status, "READY")
        self.assertEqual(parsed.objective, "Repair the calculator.")
        self.assertEqual(
            parsed.constraints,
            "Stay inside worker_probe_case2.\nPreserve the docstring.",
        )
        self.assertEqual(
            [task.task_id for task in parsed.tasks],
            ["T01", "T02", "T03"],
        )
        self.assertEqual(
            parsed.tasks[0].prompt,
            "Inspect requirements\nRead the requirements and current implementation.\nDo not modify files yet.",
        )

    def test_accepts_eof_as_final_task_terminator(self) -> None:
        parsed = parse_planner_execution_handoff(
            """STATUS: READY
OBJECTIVE:
Do the work.
T01: Perform work
Complete the bounded work.
"""
        )
        self.assertEqual(len(parsed.tasks), 1)
        self.assertEqual(
            parsed.tasks[0].prompt,
            "Perform work\nComplete the bounded work.",
        )

    def test_constraints_are_optional(self) -> None:
        parsed = parse_planner_execution_handoff(
            """STATUS: READY

OBJECTIVE:
Repair the parser.

T01: Inspect
Inspect the parser.

T02: Repair
Make the repair.
END_PLAN
"""
        )
        self.assertIsNone(parsed.constraints)
        self.assertEqual([task.task_id for task in parsed.tasks], ["T01", "T02"])

    def test_blank_lines_do_not_change_task_boundaries(self) -> None:
        parsed = parse_planner_execution_handoff(
            """

STATUS: READY


OBJECTIVE:

Repair the parser.


T01: Inspect

Inspect line one.

Inspect line two.


END_PLAN
"""
        )
        self.assertEqual(parsed.objective, "Repair the parser.")
        self.assertEqual(
            parsed.tasks[0].prompt,
            "Inspect\n\nInspect line one.\n\nInspect line two.",
        )

    def test_task_reference_inside_prose_is_not_a_heading(self) -> None:
        parsed = parse_planner_execution_handoff(
            """STATUS: READY
OBJECTIVE:
Verify prior work.
T01: Verify
Confirm T01 behavior is correct before finishing.
END_PLAN
"""
        )
        self.assertEqual(
            parsed.tasks[0].prompt,
            "Verify\nConfirm T01 behavior is correct before finishing.",
        )

    def test_text_after_end_plan_is_ignored(self) -> None:
        parsed = parse_planner_execution_handoff(
            """STATUS: READY
OBJECTIVE:
Do the work.
T01: Work
Perform the work.
END_PLAN
This text is outside the handoff.
T02: Not a real task
Ignore this.
"""
        )
        self.assertEqual(len(parsed.tasks), 1)
        self.assertEqual(parsed.tasks[0].task_id, "T01")

    def test_rejects_missing_ready_status(self) -> None:
        with self.assertRaises(RoleContractError) as caught:
            parse_planner_execution_handoff(
                """OBJECTIVE:
Do the work.
T01: Work
Perform it.
"""
            )
        self.assertEqual(caught.exception.code, "PLANNER_HANDOFF_INVALID")

    def test_rejects_missing_objective(self) -> None:
        with self.assertRaises(RoleContractError):
            parse_planner_execution_handoff(
                """STATUS: READY
T01: Work
Perform it.
"""
            )

    def test_rejects_empty_task_prompt(self) -> None:
        with self.assertRaises(RoleContractError):
            parse_planner_execution_handoff(
                """STATUS: READY
OBJECTIVE:
Do the work.
T01:
END_PLAN
"""
            )

    def test_accepts_bare_task_delimiter(self) -> None:
        parsed = parse_planner_execution_handoff(
            """STATUS: READY
OBJECTIVE:
Do the work.
T01:
Perform it.
"""
        )
        self.assertEqual(parsed.tasks[0].prompt, "Perform it.")

    def test_rejects_nonsequential_task_numbers(self) -> None:
        with self.assertRaises(RoleContractError) as caught:
            parse_planner_execution_handoff(
                """STATUS: READY
OBJECTIVE:
Do the work.
T01: First
Perform first work.
T03: Third
Perform third work.
"""
            )
        self.assertEqual(caught.exception.details["observed"], "T03")
        self.assertEqual(caught.exception.details["expected"], "T02")

    def test_rejects_duplicate_task_numbers(self) -> None:
        with self.assertRaises(RoleContractError) as caught:
            parse_planner_execution_handoff(
                """STATUS: READY
OBJECTIVE:
Do the work.
T01: First
Perform first work.
T01: Duplicate
Perform duplicate work.
"""
            )
        self.assertEqual(caught.exception.details["observed"], "T01")
        self.assertEqual(caught.exception.details["expected"], "T02")

    def test_rejects_noncanonical_task_number(self) -> None:
        with self.assertRaises(RoleContractError):
            parse_planner_execution_handoff(
                """STATUS: READY
OBJECTIVE:
Do the work.
T1: First
Perform it.
"""
            )


if __name__ == "__main__":
    unittest.main()
