from __future__ import annotations

from pathlib import Path

from tools.consumer_profile import ConsumerProfile, PROFILE_VERSION, ValidationCommand
from tools.repository_state import candidate_content_digest, changed_paths, repository_head
from tools.worker_result import (
    BoundaryResult, CONTRACT_VERSION, ValidationResult, ValidationStage, WorkerResult, WorkerStatus,
)

GENERIC_PROFILE = ConsumerProfile(
    version=PROFILE_VERSION,
    consumer="bounded-test-consumer",
    authority_paths=("docs/authority.md",),
    protected_prefixes=(".git/", ".github/", "protected/"),
    protected_exact=("policy.lock",),
    product_invariants=("A worker candidate is evidence, not authority.",),
    full_validation=(
        ValidationCommand("Run tests", ("python", "-m", "pytest", "-q"), 120),
    ),
)


def ready_worker_result(repo: Path) -> WorkerResult:
    paths = tuple(changed_paths(repo, repository_head(repo)))
    # changed_paths compares against HEAD, which is exactly the candidate base.
    return WorkerResult(
        contract_version=CONTRACT_VERSION,
        task_id="bounded-fixture",
        consumer=GENERIC_PROFILE.consumer,
        task_contract_digest="sha256:" + "1" * 64,
        base_sha=repository_head(repo),
        candidate_sha=None,
        candidate_content_digest=candidate_content_digest(repo, paths),
        workspace_state="dirty-candidate",
        changed_paths=paths,
        patch_boundary=BoundaryResult("pass"),
        quick_validation=ValidationResult("pass", (ValidationStage("quick", "pass"),)),
        full_validation=ValidationResult("pass", (ValidationStage("full", "pass"),)),
        worker=WorkerStatus("pass"),
        first_failure=None,
        ready_for_repository_handoff=True,
    )
