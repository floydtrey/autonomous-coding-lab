import json
from pathlib import Path

from worker_lab.policy import PolicyRecord, RoleRecord
from worker_lab.test_catalog import TestCatalog


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
    assert phase1_catalog.catalog_version == "worker-lab-v1"
    assert catalog.catalog_version == "worker-lab-v2"
    assert phase1_catalog.digest() == "sha256:9cf8a0229dada3d7eef4f96edf2e751b7bccff58c8eb585b441ef96c152334ec"
    assert catalog.digest() == "sha256:fe3d50c4c0692a3d0fee0ea97690a3f1d0272a31052c0afe0489cd4e6fce44aa"
    assert phase1_catalog.digest() != catalog.digest()
    meanings = {item.test_id: item.name for item in catalog.tests}
    assert meanings["T001"] == "Repository identity and clean start"
    assert meanings["T002"] == "Exact changed-path boundary"
    assert meanings["T003"] == "Diff and integrity check"
    assert meanings["T015"] == "Protected security regression profile"
    assert meanings["T018"] == "Dependency/runtime compatibility"
    assert meanings["T020"] == "Full project suite"
    assert meanings["T021"] == "Backup and rollback drill"
    profiles = {item.profile_id: item.test_ids for item in catalog.profiles}
    assert profiles["WORKSPACE_CHANGE:v1"] == (
        "T001", "T002", "T003", "T004", "T006", "T007", "T008", "T009", "T011",
        "T015", "T017", "T018", "T019",
    )
    assert TestCatalog.from_mapping(catalog.to_dict()).digest() == catalog.digest()
