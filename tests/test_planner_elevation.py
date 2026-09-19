"""Planner elevation/resume checks using ACL's generic clarification state."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from acl_controller import (
    ClarificationService,
    JsonClarificationStore,
    JsonWorkflowStore,
    RequestRecord,
    WorkflowRecord,
    WorkflowStateService,
    WorkflowStatus,
)
from acl_roles.common import RoleResponse, RoleStatus
from acl_roles.common.errors import RoleContractError
from acl_roles.planner import (
    PlannerDisposition,
    PlannerInput,
    PlannerInvocationMode,
    PlannerQuestion,
    PlannerResult,
    parse_planner_role_response,
    planner_result_to_role_response,
    resume_planner_input,
    validate_elevation_answers,
)


def _original_input() -> PlannerInput:
    return PlannerInput(
        invocation_mode=PlannerInvocationMode.INITIAL_PLANNING,
        request={"text": "Update the recorder."},
        routing_context={
            "work_type_id": "1127",
            "work_type_label": "CODING",
            "complexity": "SMALL",
        },
        metadata={"request_origin": "test"},
    )


def _elevation() -> PlannerResult:
    return PlannerResult(
        disposition=PlannerDisposition.ELEVATION_REQUIRED,
        questions=(
            PlannerQuestion(
                question_id="Q01",
                question="Replace the existing recorder or create a new version?",
                reason="The requested target is materially ambiguous.",
                options=("Replace existing", "Create new version"),
            ),
        ),
        reason_codes=("OUTPUT_TARGET_AMBIGUOUS",),
    )


class PlannerElevationTests(unittest.TestCase):
    def test_elevation_maps_to_shared_clarification_status(self) -> None:
        semantic = _elevation()
        response = planner_result_to_role_response(semantic)
        self.assertEqual(response.status, RoleStatus.NEEDS_CLARIFICATION)
        self.assertEqual(response.payload["disposition"], "ELEVATION_REQUIRED")
        self.assertEqual(response.payload["questions"][0]["question_id"], "Q01")
        parsed = parse_planner_role_response(response)
        self.assertEqual(parsed.disposition, PlannerDisposition.ELEVATION_REQUIRED)

    def test_non_elevation_maps_to_complete(self) -> None:
        semantic = PlannerResult.from_mapping(
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
        response = planner_result_to_role_response(semantic)
        self.assertEqual(response.status, RoleStatus.COMPLETE)

    def test_shared_status_must_match_semantic_disposition(self) -> None:
        response = RoleResponse(
            status=RoleStatus.COMPLETE,
            payload=_elevation().to_dict(),
        )
        with self.assertRaises(RoleContractError) as captured:
            parse_planner_role_response(response)
        self.assertEqual(captured.exception.code, "PLANNER_STATUS_MISMATCH")

    def test_elevation_answers_are_keyed_by_question_id(self) -> None:
        normalized = validate_elevation_answers(
            _elevation().questions,
            {"Q01": " Replace existing "},
        )
        self.assertEqual(normalized, {"Q01": "Replace existing"})

        with self.assertRaises(RoleContractError):
            validate_elevation_answers(_elevation().questions, {})
        with self.assertRaises(RoleContractError):
            validate_elevation_answers(
                _elevation().questions,
                {"Q01": "Replace existing", "Q99": "unexpected"},
            )

    def test_resume_preserves_original_input(self) -> None:
        original = _original_input()
        resumed = resume_planner_input(
            original,
            _elevation(),
            {"Q01": "Replace existing"},
        )
        self.assertEqual(resumed.invocation_mode, original.invocation_mode)
        self.assertEqual(dict(resumed.request), dict(original.request))
        self.assertEqual(dict(resumed.routing_context), dict(original.routing_context))
        self.assertEqual(dict(resumed.metadata), dict(original.metadata))
        self.assertEqual(
            dict(resumed.elevation_answers),
            {"Q01": "Replace existing"},
        )

    def test_conflicting_answer_cannot_silently_replace_recorded_answer(self) -> None:
        original = resume_planner_input(
            _original_input(),
            _elevation(),
            {"Q01": "Replace existing"},
        )
        with self.assertRaises(RoleContractError) as captured:
            resume_planner_input(
                original,
                _elevation(),
                {"Q01": "Create new version"},
            )
        self.assertEqual(
            captured.exception.code,
            "PLANNER_ELEVATION_ANSWER_CONFLICT",
        )

    def test_generic_controller_persists_wait_answer_and_resume_state(self) -> None:
        original = _original_input()
        elevation = _elevation()
        shared = planner_result_to_role_response(elevation)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            state = WorkflowStateService(JsonWorkflowStore(root))
            clarification = ClarificationService(
                state,
                JsonClarificationStore(root),
            )

            workflow = WorkflowRecord.create(
                RequestRecord.create(
                    "planner-test",
                    {"planner_input": original.to_objective()},
                    requester="operator",
                )
            )
            state.create(workflow)
            state.transition(
                workflow.workflow_id,
                WorkflowStatus.READY,
                stage="plan",
            )
            state.transition(
                workflow.workflow_id,
                WorkflowStatus.RUNNING,
                stage="plan",
                active_action="role.invoke",
                active_role="planner",
                active_profile_id="planner-test",
                active_attempt_id="attempt:planner-test",
            )

            pending = clarification.request(
                workflow.workflow_id,
                requested_by="role:plan",
                questions=shared.payload["questions"],
                context={
                    "role": "planner",
                    "planner_input": original.to_objective(),
                    "planner_result": elevation.to_dict(),
                },
            )
            waiting = state.read(workflow.workflow_id)
            self.assertEqual(waiting.status, WorkflowStatus.WAITING)
            self.assertEqual(
                waiting.waiting_for,
                f"clarification:{pending.clarification_id}",
            )
            self.assertEqual(
                pending.context["planner_input"]["request"]["text"],
                "Update the recorder.",
            )

            resolved = clarification.answer(
                pending.clarification_id,
                answer={"Q01": "Replace existing"},
                answered_by="operator",
            )
            ready = state.read(workflow.workflow_id)
            self.assertEqual(ready.status, WorkflowStatus.READY)
            self.assertEqual(ready.stage, "plan")
            self.assertIsNone(ready.waiting_for)

            persisted = clarification.read(pending.clarification_id)
            self.assertEqual(
                persisted.answer,
                {"Q01": "Replace existing"},
            )
            self.assertEqual(persisted.to_dict(), resolved.to_dict())

            resumed = resume_planner_input(
                PlannerInput.from_mapping(persisted.context["planner_input"]),
                PlannerResult.from_mapping(persisted.context["planner_result"]),
                persisted.answer or {},
            )
            self.assertEqual(
                resumed.elevation_answers["Q01"],
                "Replace existing",
            )
            self.assertEqual(
                resumed.request["text"],
                "Update the recorder.",
            )


if __name__ == "__main__":
    unittest.main()
