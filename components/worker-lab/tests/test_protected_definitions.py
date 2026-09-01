from copy import deepcopy
import json
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.models import ATTEMPT_SCHEMA, AttemptRecord, CurriculumRecord, ExerciseRecord
from worker_lab.policy import PolicyRecord, RoleRecord
from worker_lab.policy import ContextManifest
from worker_lab.test_catalog import ChangeFacts, TestCatalog
from worker_lab.validation import (
    attempt_task_digest,
    validate_attempt_authority_binding,
    validate_relations,
)


ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_tracked_policy_and_roles_are_strict_and_deterministic() -> None:
    policy = PolicyRecord.from_mapping(load("curricula/policies/core-worker-policy/v1.json"))
    roles = [
        RoleRecord.from_mapping(load(f"curricula/roles/{name}/v1.json"))
        for name in ("coding-worker", "planner-worker", "verifier")
    ]
    assert policy.policy_id == "core-worker-policy"
    assert len(policy.invariants) == 8
    assert {role.role_id for role in roles} == {"coding-worker", "planner-worker", "verifier"}
    for role in roles:
        assert set(role.allowed_capabilities) <= set(policy.permanent_capabilities)


def test_tracked_catalog_uses_authoritative_permanent_ids() -> None:
    phase1_catalog = TestCatalog.from_mapping(load("curricula/catalogs/worker-lab-v1.json"))
    catalog = TestCatalog.from_mapping(load("curricula/catalogs/worker-lab-v2.json"))
    phase3_catalog = TestCatalog.from_mapping(load("curricula/catalogs/worker-lab-v3.json"))
    assert phase1_catalog.catalog_version == "worker-lab-v1"
    assert catalog.catalog_version == "worker-lab-v2"
    assert phase3_catalog.catalog_version == "worker-lab-v3"
    assert phase1_catalog.digest() == "sha256:9cf8a0229dada3d7eef4f96edf2e751b7bccff58c8eb585b441ef96c152334ec"
    assert catalog.digest() == "sha256:fe3d50c4c0692a3d0fee0ea97690a3f1d0272a31052c0afe0489cd4e6fce44aa"
    assert phase3_catalog.digest() == "sha256:df6f6cf7c96fb0b6921b36154082e7cc0760372ebf7a5d4b4d84389f3422c7c7"
    assert phase1_catalog.digest() != catalog.digest()
    meanings = {item.test_id: item.name for item in catalog.tests}
    assert meanings["T001"] == "Repository identity and clean start"
    assert meanings["T002"] == "Exact changed-path boundary"
    assert meanings["T003"] == "Diff and integrity check"
    assert meanings["T015"] == "Protected security regression profile"
    assert meanings["T018"] == "Dependency/runtime compatibility"
    assert meanings["T020"] == "Full project suite"
    assert meanings["T021"] == "Backup and rollback drill"
    phase3_meanings = {item.test_id: item.name for item in phase3_catalog.tests}
    assert phase3_meanings["T016"] == "Evidence substitution and result identity"
    assert phase3_meanings["T022"] == "Exact integration candidate verification"
    profiles = {item.profile_id: item.test_ids for item in catalog.profiles}
    assert profiles["WORKSPACE_CHANGE:v1"] == (
        "T001", "T002", "T003", "T004", "T006", "T007", "T008", "T009", "T011",
        "T015", "T017", "T018", "T019",
    )
    assert TestCatalog.from_mapping(catalog.to_dict()).digest() == catalog.digest()
    assert TestCatalog.from_mapping(phase3_catalog.to_dict()).digest() == phase3_catalog.digest()


def _phase4_definitions() -> tuple[
    CurriculumRecord, ExerciseRecord, PolicyRecord, RoleRecord, ContextManifest, TestCatalog,
]:
    return (
        CurriculumRecord.from_mapping(load("curricula/curricula/phase4-record-normalizer.json")),
        ExerciseRecord.from_mapping(
            load("curricula/exercises/phase4-record-normalizer-v1/v1.json")
        ),
        PolicyRecord.from_mapping(load("curricula/policies/core-worker-policy/v1.json")),
        RoleRecord.from_mapping(load("curricula/roles/coding-worker/v1.json")),
        ContextManifest.from_mapping(
            load("curricula/contexts/phase4-record-normalizer-v1/v1.json")
        ),
        TestCatalog.from_mapping(load("curricula/catalogs/phase4-record-normalizer-v1.json")),
    )


def _phase4_attempt(
    exercise: ExerciseRecord,
    policy: PolicyRecord,
    role: RoleRecord,
    context: ContextManifest,
    catalog: TestCatalog,
) -> AttemptRecord:
    return AttemptRecord.from_mapping({
        "schema_version": ATTEMPT_SCHEMA,
        "attempt_id": "ATTEMPT-PHASE4-000001",
        "curriculum_id": exercise.curriculum_id,
        "exercise_id": exercise.exercise_id,
        "exercise_version": exercise.exercise_version,
        "starting_commit": exercise.template_commit,
        "context_digest": context.digest(),
        "task_digest": attempt_task_digest(exercise, policy, role, context, catalog),
        "policy_id": policy.policy_id,
        "policy_version": policy.policy_version,
        "policy_digest": policy.digest(),
        "role_id": role.role_id,
        "role_version": role.role_version,
        "role_digest": role.digest(),
        "sandbox_mode": exercise.sandbox_mode,
        "state": "DRAFT",
        "created_at": "2026-09-01T00:00:00Z",
        "updated_at": "2026-09-01T00:00:00Z",
        "evaluator_catalog_version": catalog.catalog_version,
        "evaluator_catalog_digest": catalog.digest(),
        "runtime_identity": None,
        "candidate_digest": None,
        "cleanup_outcome": None,
        "prior_attempt_id": None,
    })


def test_phase4_record_normalizer_definitions_are_exact_and_admissible() -> None:
    curriculum, exercise, policy, role, context, catalog = _phase4_definitions()
    validate_relations(
        curricula=(curriculum,),
        exercises=(exercise,),
        policies=(policy,),
        roles=(role,),
        contexts=(context,),
        catalog=catalog,
    )

    assert curriculum.status == "active"
    assert curriculum.exercise_ids == ("phase4-record-normalizer-v1",)
    assert curriculum.digest() == "sha256:f0be43ca9c0b83785fe3cc5e00c62e5bc1e57d7f2ba2554ae90613f6641fe1ed"
    assert exercise.digest() == "sha256:d81836446a8dfaa8eca2fc0025567c969e97e5b30de97a35a39ce504bfac67fa"
    assert context.digest() == "sha256:e677c8ec088857e89c916a5cb7eb7c5f7447a6097eb571cc48cc81dc2fd29416"
    assert catalog.digest() == "sha256:8c5ee8dd7913e14556582ed3b6e9f989721c97c81e9573845dda1f10c8cf9f76"
    assert (exercise.policy_id, exercise.policy_version) == ("core-worker-policy", 1)
    assert (exercise.role_id, exercise.role_version) == ("coding-worker", 1)
    assert exercise.sandbox_mode == "workspace-write"
    assert exercise.template_repository == (
        "C:\\Users\\MineTrackerWorker\\Documents\\ChatGPT\\Autonomous Coding Lab\\"
        "phase4-proof-20260901-01"
    )
    assert exercise.template_commit == "a36049c5e4d97a2518d13578d6090fdd50738c02"
    assert context.repository == exercise.template_repository
    assert context.starting_commit == exercise.template_commit
    assert [(item.path, item.digest) for item in context.files] == [
        (
            "tests/test_models.py",
            "sha256:3a2f0faa16488f02fbfccdc0bf78ac43d7cd1e5446969627c2e19cc0817dcbd3",
        )
    ]
    assert exercise.writable_paths == ("record_ledger/models.py",)
    assert exercise.protected_paths == ("tests/test_models.py",)
    assert (
        "Do not dispatch unless a separate authorization binds ACL-primary-controller."
        in exercise.prohibited_shortcuts
    )

    plan = catalog.select(
        ChangeFacts(exercise.writable_paths), profile_ids=exercise.test_profile_ids
    )
    assert plan.selected_profile_ids == ("PHASE4_RECORD_NORMALIZER:v1",)
    assert plan.test_ids == ("T023", "T024")
    commands = {item.test_id: item.command for item in catalog.tests}
    assert commands == {
        "T023": ("git", "diff", "--check"),
        "T024": (
            "python", "-B", "-m", "unittest", "discover", "-s", "tests", "-p",
            "test_models.py", "-v",
        ),
    }


@pytest.mark.parametrize("substitution", ("path", "command", "commit"))
def test_phase4_record_normalizer_attempt_binding_rejects_substitutions(
    substitution: str,
) -> None:
    curriculum, exercise, policy, role, context, catalog = _phase4_definitions()
    attempt = _phase4_attempt(exercise, policy, role, context, catalog)
    assert curriculum.curriculum_id == attempt.curriculum_id

    if substitution == "path":
        altered_exercise_mapping = json.loads(exercise.to_json())
        altered_exercise_mapping["writable_paths"] = ["record_ledger/substituted.py"]
        altered_exercise = ExerciseRecord.from_mapping(altered_exercise_mapping)
        altered_context = context
        altered_catalog = catalog
    elif substitution == "command":
        altered_catalog_mapping = deepcopy(catalog.to_dict())
        altered_catalog_mapping["tests"][1]["command"][-2] = "substituted_models.py"
        altered_exercise = exercise
        altered_context = context
        altered_catalog = TestCatalog.from_mapping(altered_catalog_mapping)
    else:
        altered_commit = "f" * 40
        altered_exercise_mapping = json.loads(exercise.to_json())
        altered_exercise_mapping["template_commit"] = altered_commit
        altered_exercise = ExerciseRecord.from_mapping(altered_exercise_mapping)
        altered_context_mapping = json.loads(context.to_json())
        altered_context_mapping["starting_commit"] = altered_commit
        altered_context = ContextManifest.from_mapping(altered_context_mapping)
        altered_catalog = catalog

    with pytest.raises(LabValidationError) as error:
        validate_attempt_authority_binding(
            attempt, altered_exercise, policy, role, altered_context, altered_catalog
        )
    assert error.value.code == "RELATION_IDENTITY_MISMATCH"
