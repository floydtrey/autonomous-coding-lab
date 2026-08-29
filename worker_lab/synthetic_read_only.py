"""One bounded controller-owned synthetic read-only proposal run.

This module deliberately creates its authority records in a caller-selected
*external* run directory.  It never alters Worker Lab definitions or an
external product repository.  A successful run stops at ``CANDIDATE`` as
specified for Phase 3C; it does not commit or publish anything.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .attempt_store import AttemptStore
from .canonical import canonical_digest, canonical_json
from .errors import LabValidationError
from .framework_adapter import accept_execute_response
from .framework_client import (
    FRAMEWORK_CONTRACT_VERSION,
    PINNED_FRAMEWORK_COMMIT,
    call_adapter,
    inspect_configuration,
    inspect_worker_lab_identity,
    pinned_framework_configuration,
    runtime_identity,
)
from .integration import (
    INVOCATION_SCHEMA,
    RUNTIME_MODEL,
    RUNTIME_PROFILE,
    RUNTIME_REASONING_EFFORT,
    RUNTIME_TIMEOUT_SECONDS,
    WORKER_LAB_CONTRACT_VERSION,
    InvocationOperation,
    InvocationRecord,
    InvocationState,
    transition_invocation,
)
from .invocation_store import InvocationStore
from .lifecycle import transition_attempt
from .models import (
    ATTEMPT_SCHEMA,
    CURRICULUM_SCHEMA,
    EXERCISE_SCHEMA,
    AttemptRecord,
    AttemptState,
    CurriculumRecord,
    ExerciseRecord,
    WorkspaceReceipt,
)
from .policy import CONTEXT_MANIFEST_SCHEMA, POLICY_SCHEMA, ROLE_SCHEMA, ContextManifest, PolicyRecord, RoleRecord
from .process_custody import ProcessCustodyStore
from .read_only_evidence import (
    READ_ONLY_EVALUATION_PLAN_SCHEMA,
    ReadOnlyEvaluationPlan,
    ReadOnlyEvaluationPlanStore,
    ReadOnlyEvidenceCollector,
)
from .storage import AtomicRecordStore
from .test_catalog import CATALOG_SCHEMA, ChangeFacts, CostClass, TestCatalog, TestDefinition, TestMode, TestProfile, TestRunner
from .validation import attempt_task_digest
from .windows_job import WindowsJobAdapterRunner
from .workspace import prepare_workspace


SYNTHETIC_CATALOG_VERSION = "synthetic-read-only-v1"
SYNTHETIC_PROFILE_ID = "READ_ONLY_INVOCATION:v1"
SYNTHETIC_TEST_ID = "T001"


def run(run_root: Path) -> str:
    """Create and execute exactly one isolated read-only synthetic proposal.

    ``run_root`` must not exist.  Its durable evidence is retained there for
    review.  This function is the only production entry point in this module.
    """
    root = _new_root(run_root)
    template = root / "template"
    lab = root / "lab"
    workspace_root = root / "workspaces"
    workspace_root.mkdir()
    _make_template(template)
    records = _write_authority(lab, template)
    attempt = _create_attempt(lab, records)
    receipt = prepare_workspace(lab, attempt.attempt_id, template, workspace_root, occurred_at=_now())
    workspace = workspace_root / attempt.attempt_id
    attempt = AttemptStore(lab / "state").read(attempt.attempt_id)
    invocation, prompt = _invocation(lab, attempt, records, receipt, workspace)
    invocations = InvocationStore(lab / "state")
    launcher = _codex_launcher()
    configuration = pinned_framework_configuration(
        codex_launcher=launcher,
        codex_launcher_digest=_digest_bytes(launcher.read_bytes()),
    )
    framework_evidence = inspect_configuration(configuration)
    worker_evidence = inspect_worker_lab_identity(Path(__file__).resolve().parents[1], invocation.worker_lab_commit)
    _direct_adapter_runner(
        invocation, configuration, "prepare", prompt, framework_evidence, worker_evidence,
    )
    invocations.create(invocation)
    authorized = transition_invocation(
        invocation, InvocationState.AUTHORIZED, authorized_by="trusted-controller",
        authorized_at=_now(),
    )
    invocations.save_transition(authorized, expected_digest=invocation.digest())
    _direct_adapter_runner(
        authorized, configuration, "preflight", prompt, framework_evidence, worker_evidence,
    )
    attempts = AttemptStore(lab / "state")
    running = attempts.bind_authorized_invocation(
        invocations, invocation_id=authorized.invocation_id,
        expected_invocation_identity=authorized.identity_digest(), occurred_at=_now(),
    )
    dispatching = transition_invocation(authorized, InvocationState.DISPATCHING)
    invocations.save_transition(dispatching, expected_digest=authorized.digest())
    custody_store = ProcessCustodyStore(lab / "state")
    runner = WindowsJobAdapterRunner(
        custody_store, invocation=dispatching, timeout_seconds=RUNTIME_TIMEOUT_SECONDS,
        workspace_path=workspace,
    )
    started = _now()
    response = call_adapter(
        dispatching, configuration, "execute-read-only", prompt=prompt,
        evidence=framework_evidence, worker_lab_evidence=worker_evidence, runner=runner,
    )
    ended = _now()
    custody = custody_store.read(dispatching.invocation_id)
    collector = ReadOnlyEvidenceCollector(
        state_root=lab / "state", workspace_path=workspace, test_executor=_run_sealed_test,
    )
    result = accept_execute_response(
        response, dispatching, custody,
        runtime_identity=runtime_identity(configuration, dispatching, evidence=framework_evidence),
        started_at=started, ended_at=ended, state_root=lab / "state", custody_store=custody_store,
        evidence_collector=collector,
    )
    AtomicRecordStore(lab / "state").write(f"results/{dispatching.invocation_id}.json", result)
    completed = transition_invocation(dispatching, InvocationState.COMPLETED, result_digest=result.digest())
    invocations.save_transition(completed, expected_digest=dispatching.digest())
    candidate = transition_attempt(
        attempts.read(running.attempt_id), AttemptState.CANDIDATE, occurred_at=_now(),
        candidate_digest=result.digest(),
    )
    attempts.save_transition(candidate)
    return canonical_json(result.to_dict())


def _new_root(root: Path) -> Path:
    if root.exists() or os.path.lexists(root):
        raise LabValidationError("SYNTHETIC_RUN_ROOT_EXISTS", "synthetic run root must not already exist")
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir()
    return root.resolve(strict=True)


def _make_template(template: Path) -> None:
    template.mkdir()
    (template / "README.md").write_text(
        "# Synthetic Worker Lab Repository\n\nThis repository exists only for one read-only proposal.\n",
        encoding="utf-8",
    )
    for command in (("init",), ("config", "user.email", "synthetic@example.invalid"),
                    ("config", "user.name", "Synthetic Controller"), ("add", "README.md"),
                    ("commit", "-m", "Synthetic baseline")):
        _git(template, *command)


def _write_authority(lab: Path, template: Path) -> tuple[CurriculumRecord, ExerciseRecord, PolicyRecord, RoleRecord, ContextManifest, TestCatalog]:
    definitions = AtomicRecordStore(lab / "curricula")
    commit = _git(template, "rev-parse", "HEAD").decode("ascii").strip()
    readme_digest = _digest_bytes((template / "README.md").read_bytes())
    policy = PolicyRecord.from_mapping({"schema_version": POLICY_SCHEMA, "policy_id": "synthetic-policy", "policy_version": 1, "invariants": [], "permanent_capabilities": ["read.proposal"]})
    role = RoleRecord.from_mapping({"schema_version": ROLE_SCHEMA, "role_id": "synthetic-reader", "role_version": 1, "purpose": "Read synthetic content only.", "allowed_capabilities": ["read.proposal"], "denied_capabilities": [], "required_outputs": ["proposal"]})
    context = ContextManifest.from_mapping({"schema_version": CONTEXT_MANIFEST_SCHEMA, "manifest_id": "synthetic-context", "manifest_version": 1, "repository": "synthetic-template", "starting_commit": commit, "files": [{"path": "README.md", "digest": readme_digest, "purpose": "Synthetic review input."}]})
    catalog = TestCatalog(CATALOG_SCHEMA, SYNTHETIC_CATALOG_VERSION,
        (TestDefinition(SYNTHETIC_TEST_ID, 1, "Clean workspace", "Verify the synthetic workspace is clean.", ("git", "status", "--porcelain=v1"), TestMode.ALWAYS, CostClass.MILLISECOND, TestRunner.COMMAND, "trusted-controller"),),
        (TestProfile(SYNTHETIC_PROFILE_ID, "Synthetic read-only verification.", (SYNTHETIC_TEST_ID,)),))
    exercise = ExerciseRecord.from_mapping({"schema_version": EXERCISE_SCHEMA, "exercise_id": "synthetic-read-only", "exercise_version": 1, "curriculum_id": "synthetic-curriculum", "objective": "Produce a bounded read-only proposal for the synthetic README.", "template_repository": "synthetic-template", "template_commit": commit, "policy_id": policy.policy_id, "policy_version": policy.policy_version, "role_id": role.role_id, "role_version": role.role_version, "sandbox_mode": "read-only", "context_manifest_id": context.manifest_id, "context_manifest_version": context.manifest_version, "evaluator_catalog_version": catalog.catalog_version, "required_capabilities": ["read.proposal"], "temporary_denied_capabilities": [], "writable_paths": ["README.md"], "protected_paths": [], "acceptance_criteria": ["Workspace remains unchanged."], "test_profile_ids": [SYNTHETIC_PROFILE_ID], "prohibited_shortcuts": ["Do not modify files."], "expected_failure_behavior": ["Reject any workspace change."]})
    curriculum = CurriculumRecord.from_mapping({"schema_version": CURRICULUM_SCHEMA, "curriculum_id": "synthetic-curriculum", "title": "Synthetic read-only", "purpose": "One isolated integration proof.", "capabilities": ["read.proposal"], "prerequisite_curriculum_ids": [], "exercise_ids": [exercise.exercise_id], "status": "active"})
    definitions.write("policies/synthetic-policy/v1.json", policy)
    definitions.write("roles/synthetic-reader/v1.json", role)
    definitions.write("contexts/synthetic-context/v1.json", context)
    definitions.write("catalogs/synthetic-read-only-v1.json", catalog)
    definitions.write("exercises/synthetic-read-only/v1.json", exercise)
    definitions.write("curricula/synthetic-curriculum.json", curriculum)
    return curriculum, exercise, policy, role, context, catalog


def _create_attempt(lab: Path, records: tuple[CurriculumRecord, ExerciseRecord, PolicyRecord, RoleRecord, ContextManifest, TestCatalog]) -> AttemptRecord:
    curriculum, exercise, policy, role, context, catalog = records
    now = _now()
    attempt = AttemptRecord.from_mapping({"schema_version": ATTEMPT_SCHEMA, "attempt_id": "SYNTHETIC-" + uuid.uuid4().hex.upper(), "curriculum_id": curriculum.curriculum_id, "exercise_id": exercise.exercise_id, "exercise_version": exercise.exercise_version, "starting_commit": exercise.template_commit, "context_digest": context.digest(), "task_digest": attempt_task_digest(exercise, policy, role, context, catalog), "policy_id": policy.policy_id, "policy_version": policy.policy_version, "policy_digest": policy.digest(), "role_id": role.role_id, "role_version": role.role_version, "role_digest": role.digest(), "sandbox_mode": "read-only", "state": "DRAFT", "created_at": now, "updated_at": now, "evaluator_catalog_version": catalog.catalog_version, "evaluator_catalog_digest": catalog.digest(), "runtime_identity": None, "candidate_digest": None, "cleanup_outcome": None, "prior_attempt_id": None})
    AttemptStore(lab / "state").create(attempt)
    return attempt


def _invocation(lab: Path, attempt: AttemptRecord, records: tuple[CurriculumRecord, ExerciseRecord, PolicyRecord, RoleRecord, ContextManifest, TestCatalog], receipt: WorkspaceReceipt, workspace: Path) -> tuple[InvocationRecord, str]:
    _, exercise, policy, role, context, catalog = records
    plan = catalog.select(ChangeFacts(()), profile_ids=(SYNTHETIC_PROFILE_ID,))
    prompt = "Review the synthetic README and return one short plain-text improvement proposal. Do not modify files, run commands, include paths, URLs, credentials, or code fences."
    worker_root = Path(__file__).resolve().parents[1]
    worker_commit = _git(worker_root, "rev-parse", "HEAD").decode("ascii").strip()
    invocation = InvocationRecord.from_mapping({"schema_version": INVOCATION_SCHEMA, "invocation_id": "INVOCATION-" + uuid.uuid4().hex.upper(), "attempt_id": attempt.attempt_id, "operation": str(InvocationOperation.READ_ONLY_PROPOSAL), "exercise_id": exercise.exercise_id, "exercise_version": exercise.exercise_version, "exercise_digest": exercise.digest(), "policy_id": policy.policy_id, "policy_version": policy.policy_version, "policy_digest": policy.digest(), "role_id": role.role_id, "role_version": role.role_version, "role_digest": role.digest(), "context_manifest_id": context.manifest_id, "context_manifest_version": context.manifest_version, "context_digest": context.digest(), "task_digest": attempt.task_digest, "test_catalog_version": catalog.catalog_version, "test_catalog_digest": catalog.digest(), "test_plan_digest": canonical_digest(plan.to_dict()), "test_ids": list(plan.test_ids), "worker_lab_commit": worker_commit, "worker_lab_contract_version": WORKER_LAB_CONTRACT_VERSION, "framework_commit": PINNED_FRAMEWORK_COMMIT, "framework_contract_version": FRAMEWORK_CONTRACT_VERSION, "workspace_receipt_digest": receipt.digest(), "workspace_root_digest": receipt.workspace_root_digest, "workspace_path_digest": receipt.workspace_path_digest, "starting_commit": attempt.starting_commit, "sandbox_mode": "read-only", "runtime_profile_id": RUNTIME_PROFILE, "model": RUNTIME_MODEL, "reasoning_effort": RUNTIME_REASONING_EFFORT, "timeout_seconds": RUNTIME_TIMEOUT_SECONDS, "readable_paths": [{"path": "README.md", "digest": _digest_bytes((workspace / "README.md").read_bytes())}], "writable_paths": [], "prompt_digest": _digest_bytes(prompt.encode("utf-8")), "authorized_by": None, "authorized_at": None, "state": "PREPARED", "result_digest": None})
    sealed = ReadOnlyEvaluationPlan.from_mapping({"schema_version": READ_ONLY_EVALUATION_PLAN_SCHEMA, "invocation_id": invocation.invocation_id, "invocation_digest": invocation.identity_digest(), "catalog_version": catalog.catalog_version, "catalog_digest": catalog.digest(), "selected_profile_ids": list(plan.selected_profile_ids), "test_ids": list(plan.test_ids), "test_plan_digest": invocation.test_plan_digest, "changed_paths": [], "capabilities": [], "risk_flags": []})
    ReadOnlyEvaluationPlanStore(lab / "state").create(sealed)
    return invocation, prompt


def _direct_adapter_runner(record, config, mode, prompt, evidence, worker_evidence) -> bytes:
    def runner(command: tuple[str, ...], payload: bytes) -> bytes:
        process = subprocess.run(list(command), input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=config.framework_root, timeout=45, check=False)
        if process.returncode != 0:
            # The adapter intentionally emits only a stable code on this path.
            # Preserve that controller-visible classification without retaining
            # stderr, absolute paths, or other diagnostic content.
            try:
                failure = json.loads(process.stdout.decode("utf-8"))
                code = failure.get("failure_code") if isinstance(failure, dict) else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                code = None
            if isinstance(code, str) and re.fullmatch(r"[A-Z0-9_]{3,96}", code):
                raise LabValidationError(code, "adapter pre-execution check failed")
            raise LabValidationError("INTEGRATION_EXECUTION_FAILED", "adapter pre-execution check failed")
        return process.stdout
    return call_adapter(record, config, mode, prompt=prompt, evidence=evidence, worker_lab_evidence=worker_evidence, runner=runner)


def _run_sealed_test(definition: TestDefinition, workspace: Path) -> int:
    if definition.test_id != SYNTHETIC_TEST_ID or definition.command != ("git", "status", "--porcelain=v1") or definition.runner is not TestRunner.COMMAND:
        raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "synthetic evaluator definition differs")
    result = subprocess.run(list(definition.command), cwd=workspace, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
    return result.returncode if not result.stdout else 1


def _codex_launcher() -> Path:
    launcher = shutil.which("codex")
    if launcher is None:
        raise LabValidationError("CODEX_UNAVAILABLE", "could not resolve Codex launcher")
    return Path(launcher).resolve(strict=True)


def _git(root: Path, *args: str) -> bytes:
    environment = {"PATH": os.environ.get("PATH", ""), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    result = subprocess.run(
        ["git", "-c", f"safe.directory={root}", *args], cwd=root, env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=30, check=False,
    )
    if result.returncode:
        raise LabValidationError("SYNTHETIC_GIT_FAILED", "synthetic Git operation failed")
    return result.stdout


def _digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
