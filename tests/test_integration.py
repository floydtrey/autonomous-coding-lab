import json
import subprocess

import pytest

from worker_lab.canonical import canonical_json
from worker_lab.errors import LabValidationError
from worker_lab.framework_adapter import ADAPTER_COMMAND, MAX_ADAPTER_RESPONSE_BYTES, MAX_PROPOSAL_BYTES, ProposalStore, WorkspaceEvidence, accept_execute_response, inspect_acceptance_workspace, parse_result, prepare_invocation
from worker_lab.process_custody import PROCESS_CUSTODY_SCHEMA, ProcessCustodyRecord, ProcessCustodyStore
from worker_lab.models import WorkspaceReceipt
from worker_lab.storage import AtomicRecordStore
from worker_lab.workspace import canonical_path_digest
from worker_lab.integration import (
    FRAMEWORK_CONTRACT_VERSION,
    INVOCATION_SCHEMA,
    RUNTIME_PROFILE,
    WORKER_LAB_CONTRACT_VERSION,
    InvocationRecord,
    InvocationState,
    PathIdentity,
    RESULT_SCHEMA,
    RUNTIME_MODEL,
    RUNTIME_REASONING_EFFORT,
    RUNTIME_TIMEOUT_SECONDS,
    ResultRecord,
    ValidationStage,
    transition_invocation,
)


DIGEST = "sha256:" + "a" * 64
SHA = "a" * 40


def record(*, operation="read-only-proposal", state="PREPARED", writable_paths=(), **updates):
    value = {
        "schema_version": INVOCATION_SCHEMA, "invocation_id": "INVOCATION-001", "attempt_id": "ATTEMPT-001",
        "operation": operation, "exercise_id": "exercise", "exercise_version": 1, "exercise_digest": DIGEST,
        "policy_id": "policy", "policy_version": 1, "policy_digest": DIGEST, "role_id": "role", "role_version": 1,
        "role_digest": DIGEST, "context_manifest_id": "context", "context_manifest_version": 1,
        "context_digest": DIGEST, "task_digest": DIGEST, "test_catalog_version": "worker-lab-v3",
        "test_catalog_digest": DIGEST, "test_plan_digest": DIGEST, "test_ids": ["T001"], "worker_lab_commit": SHA,
        "worker_lab_contract_version": WORKER_LAB_CONTRACT_VERSION, "framework_commit": SHA,
        "framework_contract_version": FRAMEWORK_CONTRACT_VERSION, "workspace_receipt_digest": DIGEST,
        "workspace_root_digest": DIGEST, "workspace_path_digest": DIGEST, "starting_commit": SHA,
        "sandbox_mode": "read-only" if operation == "read-only-proposal" else "workspace-write",
        "runtime_profile_id": RUNTIME_PROFILE, "model": RUNTIME_MODEL,
        "reasoning_effort": RUNTIME_REASONING_EFFORT, "timeout_seconds": RUNTIME_TIMEOUT_SECONDS,
        "readable_paths": [{"path": "README.md", "digest": DIGEST}],
        "writable_paths": list(writable_paths), "prompt_digest": DIGEST,
        "authorized_by": None, "authorized_at": None, "state": state, "result_digest": None,
    }
    value.update(updates)
    return InvocationRecord.from_mapping(value)


def result_mapping(invocation):
    return {
        "schema_version": RESULT_SCHEMA, "invocation_digest": invocation.identity_digest(), "request_digest": invocation.identity_digest(),
        "invocation_id": invocation.invocation_id, "attempt_id": invocation.attempt_id, "operation": str(invocation.operation),
        "framework_commit": invocation.framework_commit, "framework_contract_version": invocation.framework_contract_version,
        "runtime_profile_id": invocation.runtime_profile_id, "runtime_identity": DIGEST, "prompt_digest": invocation.prompt_digest,
        "test_catalog_version": invocation.test_catalog_version, "test_catalog_digest": invocation.test_catalog_digest,
        "test_plan_digest": invocation.test_plan_digest, "test_ids": list(invocation.test_ids),
        "workspace_receipt_digest": invocation.workspace_receipt_digest, "workspace_root_digest": invocation.workspace_root_digest,
        "workspace_path_digest": invocation.workspace_path_digest, "starting_commit": invocation.starting_commit,
        "observed_head": SHA, "process_outcome": "pass", "process_identity": DIGEST,
        "process_started_at": "2026-08-28T00:00:00Z", "process_ended_at": "2026-08-28T00:00:01Z",
        "workspace_state": "unchanged", "changed_paths": [], "proposal_digest": DIGEST, "candidate_digest": None,
        "validation_stages": [{"test_id": "T001", "outcome": "pass", "failure_code": None}],
        "first_failure_boundary": None, "failure_code": None, "expected": "unchanged workspace",
        "observed": "unchanged workspace", "containment_outcome": "not-needed", "output_digest": DIGEST,
        "content_reference": "proposals/" + "a" * 64 + ".txt", "retryable": False,
    }


def test_invocation_rejects_unknown_fields_and_operation_scope_mismatch():
    value = record().to_dict()
    value["unexpected"] = True
    with pytest.raises(LabValidationError) as error:
        InvocationRecord.from_mapping(value)
    assert error.value.code == "INTEGRATION_FIELDS_INVALID"
    with pytest.raises(LabValidationError) as error:
        record(writable_paths=("app.py",))
    assert error.value.code == "INTEGRATION_SCOPE_INVALID"


def test_authorization_is_a_single_guarded_transition():
    prepared = record()
    authorized = transition_invocation(
        prepared, InvocationState.AUTHORIZED, authorized_by="trusted-controller", authorized_at="2026-08-28T00:00:00Z"
    )
    assert authorized.state is InvocationState.AUTHORIZED
    with pytest.raises(LabValidationError) as error:
        transition_invocation(authorized, InvocationState.DISPATCHING, authorized_by="other")
    assert error.value.code == "INTEGRATION_AUTHORIZATION_INVALID"


def test_adapter_requires_injected_runner_and_validates_canonical_response():
    invocation = record()
    with pytest.raises(LabValidationError) as error:
        prepare_invocation(invocation)
    assert error.value.code == "INTEGRATION_EXECUTION_DISABLED"

    def fake(command, payload):
        assert command == ADAPTER_COMMAND
        assert json.loads(payload)["schema_version"] == INVOCATION_SCHEMA
        return json.dumps(
            {"invocation_digest": invocation.identity_digest(), "prompt_digest": DIGEST, "runtime_identity": DIGEST},
            sort_keys=True, separators=(",", ":"),
        )

    response = prepare_invocation(invocation, runner=fake)
    assert response.invocation_digest == invocation.identity_digest()


def test_workspace_write_requires_exact_writable_paths():
    invocation = record(operation="workspace-write-code-task", writable_paths=("app.py",))
    assert invocation.sandbox_mode == "workspace-write"
    assert PathIdentity.from_mapping({"path": "app.py", "digest": DIGEST}).path == "app.py"


def test_result_requires_complete_evidence_and_binds_all_invocation_identities():
    invocation = record()
    result = ResultRecord.from_mapping(result_mapping(invocation))
    assert parse_result(canonical_json(result.to_dict()), invocation) == result
    incomplete = result_mapping(invocation)
    del incomplete["output_digest"]
    with pytest.raises(LabValidationError) as error:
        ResultRecord.from_mapping(incomplete)
    assert error.value.code == "INTEGRATION_FIELDS_INVALID"
    mismatched = result_mapping(invocation)
    mismatched["test_plan_digest"] = "sha256:" + "b" * 64
    with pytest.raises(LabValidationError) as error:
        parse_result(canonical_json(mismatched), invocation)
    assert error.value.code == "INTEGRATION_IDENTITY_INVALID"


def test_strict_path_authorization_and_stage_validation_fail_closed():
    with pytest.raises(LabValidationError) as error:
        PathIdentity.from_mapping({"path": ".", "digest": DIGEST})
    assert error.value.code == "INTEGRATION_PATH_INVALID"
    rejected = record().to_dict()
    rejected.update({"state": "REJECTED", "authorized_by": "controller", "authorized_at": "2026-08-28T00:00:00Z"})
    with pytest.raises(LabValidationError) as error:
        InvocationRecord.from_mapping(rejected)
    assert error.value.code == "INTEGRATION_AUTHORIZATION_INVALID"
    invalid = result_mapping(record())
    invalid["validation_stages"] *= 2
    with pytest.raises(LabValidationError) as error:
        ResultRecord.from_mapping(invalid)
    assert error.value.code == "INTEGRATION_RESULT_INVALID"
    invocation = record(test_ids=["T001", "T002"])
    invalid = result_mapping(invocation)
    invalid["validation_stages"] = [
        {"test_id": "T002", "outcome": "pass", "failure_code": None},
        {"test_id": "T001", "outcome": "pass", "failure_code": None},
    ]
    with pytest.raises(LabValidationError) as error:
        ResultRecord.from_mapping(invalid)
    assert error.value.code == "INTEGRATION_RESULT_INVALID"


def test_result_parser_rejects_invalid_type_and_oversized_input():
    invocation = record()
    for value in (None, "x" * (MAX_ADAPTER_RESPONSE_BYTES + 1)):
        with pytest.raises(LabValidationError) as error:
            parse_result(value, invocation)
        assert error.value.code == "INTEGRATION_RESULT_INVALID"


def test_result_enforces_structured_text_and_content_reference_limits():
    invocation = record()
    exact = result_mapping(invocation)
    exact["expected"] = "x" * 2_048
    exact["observed"] = "y" * 2_048
    assert ResultRecord.from_mapping(exact).expected == exact["expected"]

    for field in ("expected", "observed"):
        oversized = result_mapping(invocation)
        oversized[field] = "x" * 2_049
        with pytest.raises(LabValidationError) as error:
            ResultRecord.from_mapping(oversized)
        assert error.value.code == "INTEGRATION_FIELD_INVALID"

    for reference in ("C:/outside.txt", "proposals/" + "x" * 256):
        invalid = result_mapping(invocation)
        invalid["content_reference"] = reference
        with pytest.raises(LabValidationError) as error:
            ResultRecord.from_mapping(invalid)
        assert error.value.code in {"INTEGRATION_PATH_INVALID", "INTEGRATION_FIELD_INVALID"}


def test_acceptance_workspace_inspector_reloads_receipt_and_git_evidence(tmp_path):
    state_root = tmp_path / "state"
    workspace_root = tmp_path / "workspaces"
    workspace = workspace_root / "ATTEMPT-001"
    workspace.mkdir(parents=True)
    (workspace / "README.md").write_text("fixture\n", encoding="utf-8")
    for command in (
        ["git", "init"], ["git", "config", "core.autocrlf", "false"],
        ["git", "config", "user.email", "fixture@example.com"],
        ["git", "config", "user.name", "Fixture"], ["git", "add", "."],
        ["git", "commit", "-m", "fixture"],
    ):
        subprocess.run(command, cwd=workspace, check=True, capture_output=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=workspace, check=True, capture_output=True, text=True,
    ).stdout.strip()
    receipt = WorkspaceReceipt.from_mapping({
        "schema_version": "worker-lab-workspace-receipt:v1", "attempt_id": "ATTEMPT-001",
        "exercise_id": "exercise", "exercise_version": 1, "template_repository": "fixture",
        "template_commit": head, "workspace_root_digest": canonical_path_digest(workspace_root),
        "workspace_path_digest": canonical_path_digest(workspace),
        "workspace_relative_path": "ATTEMPT-001", "created_at": "2026-08-28T00:00:00Z",
        "state": "PREPARED",
    })
    AtomicRecordStore(state_root).write("workspaces/ATTEMPT-001.json", receipt)
    invocation = record(
        starting_commit=head, workspace_receipt_digest=receipt.digest(),
        workspace_root_digest=receipt.workspace_root_digest,
        workspace_path_digest=receipt.workspace_path_digest,
    )
    evidence = inspect_acceptance_workspace(invocation, state_root=state_root, workspace_path=workspace)
    assert evidence.observed_head == head
    assert evidence.changed_paths == ()
    (workspace / "unexpected.txt").write_text("dirty\n", encoding="utf-8")
    assert inspect_acceptance_workspace(
        invocation, state_root=state_root, workspace_path=workspace,
    ).changed_paths


def test_successful_proposal_is_bounded_checked_and_content_addressed(tmp_path):
    item = result_mapping(record())
    content = b"bounded proposal"
    item["proposal_digest"] = "sha256:" + __import__("hashlib").sha256(content).hexdigest()
    item["output_digest"] = item["proposal_digest"]
    item["content_reference"] = None
    # Strict result parsing requires its final reference; storage supplies it after acceptance.
    item["content_reference"] = "proposals/" + item["proposal_digest"][7:] + ".txt"
    result = ResultRecord.from_mapping(item)
    stored = ProposalStore(tmp_path / "state").store(result, content)
    assert stored.content_reference == item["content_reference"]
    for unsafe in (b"x" * (MAX_PROPOSAL_BYTES + 1), b"OPENAI_API_KEY=x", b"bad\x00content", b"\\\\server\\share"):
        with pytest.raises(LabValidationError):
            ProposalStore(tmp_path / "state").store(result, unsafe)


def test_actual_execute_response_becomes_custody_bound_strict_result(tmp_path):
    invocation = record()
    content = "bounded proposal"
    digest = "sha256:" + __import__("hashlib").sha256(content.encode()).hexdigest()
    store = ProcessCustodyStore(tmp_path / "state")
    prepared_custody = ProcessCustodyRecord.from_mapping({
        "schema_version": PROCESS_CUSTODY_SCHEMA, "invocation_digest": invocation.identity_digest(),
        "invocation_id": invocation.invocation_id, "controller_pid": 1, "controller_creation_time_100ns": 1,
        "adapter_pid": None, "adapter_creation_time_100ns": None, "containment_mode": "windows-job-kill-on-close",
        "state": "PREPARED", "request_sent": False, "exit_code": None, "active_process_count": None,
        "absence_verified_at": None, "first_failure": None,
    })
    store.create(prepared_custody)
    custody = ProcessCustodyRecord.from_mapping({
        **prepared_custody.to_dict(), "adapter_pid": 2, "adapter_creation_time_100ns": 2,
        "state": "ABSENCE_VERIFIED", "request_sent": True, "exit_code": 0, "active_process_count": 0,
        "absence_verified_at": "2026-08-28T00:00:01Z", "first_failure": None,
    })
    store.save_transition(
        ProcessCustodyRecord.from_mapping({**prepared_custody.to_dict(), "state": "ASSIGNED", "adapter_pid": 2, "adapter_creation_time_100ns": 2}),
        expected_digest=prepared_custody.digest(),
    )
    dispatching = ProcessCustodyRecord.from_mapping({**custody.to_dict(), "state": "DISPATCHING", "exit_code": None, "active_process_count": None, "absence_verified_at": None})
    store.save_transition(dispatching, expected_digest=store.read(invocation.invocation_id).digest())
    exited = ProcessCustodyRecord.from_mapping({**custody.to_dict(), "state": "EXITED", "absence_verified_at": None})
    store.save_transition(exited, expected_digest=dispatching.digest())
    store.save_transition(custody, expected_digest=exited.digest())
    workspace_evidence = WorkspaceEvidence(
        observed_head=invocation.starting_commit, changed_paths=(),
        workspace_receipt_digest=invocation.workspace_receipt_digest,
        workspace_root_digest=invocation.workspace_root_digest,
        workspace_path_digest=invocation.workspace_path_digest,
    )
    validation_stages = tuple(
        ValidationStage.from_mapping({"test_id": test_id, "outcome": "pass", "failure_code": None})
        for test_id in invocation.test_ids
    )
    raw = __import__("json").dumps({"invocation_digest": invocation.identity_digest(), "prompt_digest": invocation.prompt_digest,
        "runtime_identity": DIGEST, "proposal_digest": digest, "output_digest": digest, "proposal_content": content,
        "stdout_bytes": len(content.encode()), "stderr_bytes": 0}, sort_keys=True, separators=(",", ":")).encode()

    def accept(**overrides):
        kwargs = dict(
            runtime_identity=DIGEST, started_at="2026-08-28T00:00:00Z", ended_at="2026-08-28T00:00:01Z",
            state_root=tmp_path / "state", custody_store=store,
            workspace_verifier=lambda _: workspace_evidence,
            validation_verifier=lambda _: validation_stages,
        )
        used_custody = overrides.pop("custody", custody)
        kwargs.update(overrides)
        return accept_execute_response(raw, invocation, used_custody, **kwargs)

    accepted = accept()
    assert accepted.process_identity == custody.digest()
    assert (tmp_path / "state" / accepted.content_reference).read_text() == content
    malformed_calls = []
    with pytest.raises(LabValidationError):
        accept_execute_response(raw + b" ", invocation, custody, runtime_identity=DIGEST,
                                started_at="2026-08-28T00:00:00Z", ended_at="2026-08-28T00:00:01Z",
                                state_root=tmp_path / "state", custody_store=store,
                                workspace_verifier=lambda _: malformed_calls.append("workspace"),
                                validation_verifier=lambda _: malformed_calls.append("validation"))
    assert malformed_calls == []
    with pytest.raises(LabValidationError) as error:
        accept(custody=dispatching)
    with pytest.raises(LabValidationError) as error:
        accept(workspace_verifier=lambda _: WorkspaceEvidence(
            observed_head="9" * 40, changed_paths=(), workspace_receipt_digest=invocation.workspace_receipt_digest,
            workspace_root_digest=invocation.workspace_root_digest, workspace_path_digest=invocation.workspace_path_digest,
        ))
    assert error.value.code == "INTEGRATION_RESULT_INVALID"
    with pytest.raises(LabValidationError) as error:
        accept(workspace_verifier=lambda _: WorkspaceEvidence(
            observed_head=invocation.starting_commit, changed_paths=("app.py",),
            workspace_receipt_digest=invocation.workspace_receipt_digest,
            workspace_root_digest=invocation.workspace_root_digest, workspace_path_digest=invocation.workspace_path_digest,
        ))
    assert error.value.code == "INTEGRATION_RESULT_INVALID"
    with pytest.raises(LabValidationError) as error:
        accept(validation_verifier=lambda _: validation_stages[:-1] if len(validation_stages) > 1 else ())
    assert error.value.code == "INTEGRATION_RESULT_INVALID"
    failed_stage = tuple(
        ValidationStage.from_mapping({"test_id": test_id, "outcome": "fail", "failure_code": "BOUNDARY"})
        for test_id in invocation.test_ids
    )
    with pytest.raises(LabValidationError) as error:
        accept(validation_verifier=lambda _: failed_stage)
    assert error.value.code == "INTEGRATION_RESULT_INVALID"
    non_dispatched = ProcessCustodyRecord.from_mapping({**custody.to_dict(), "adapter_pid": None, "adapter_creation_time_100ns": None, "request_sent": False})
    with pytest.raises(LabValidationError) as error:
        accept_execute_response(raw, invocation, non_dispatched, runtime_identity=DIGEST,
                                started_at="2026-08-28T00:00:00Z", ended_at="2026-08-28T00:00:01Z",
                                state_root=tmp_path / "state", custody_store=store,
                                workspace_verifier=lambda _: workspace_evidence,
                                validation_verifier=lambda _: validation_stages)
    assert error.value.code == "INTEGRATION_OUTCOME_UNCERTAIN"

    calls = []
    with pytest.raises(LabValidationError) as error:
        accept(
            custody=dispatching,
            workspace_verifier=lambda _: calls.append("workspace"),
            validation_verifier=lambda _: calls.append("validation"),
        )
    assert error.value.code == "INTEGRATION_OUTCOME_UNCERTAIN"
    assert calls == []

    with pytest.raises(LabValidationError) as error:
        accept(workspace_verifier=None)
    assert error.value.code == "INTEGRATION_EXECUTION_DISABLED"


@pytest.mark.parametrize(
    "updates",
    [
        {"model": "gpt-5.6-sol"},
        {"reasoning_effort": "high"},
        {"timeout_seconds": RUNTIME_TIMEOUT_SECONDS + 1},
    ],
)
def test_runtime_profile_values_are_fixed(updates):
    with pytest.raises(LabValidationError) as error:
        record(**updates)
    assert error.value.code == "INTEGRATION_RUNTIME_INVALID"


@pytest.mark.parametrize(
    "timestamp",
    ["2026-08-28T00:00:00", "2026-08-28T00:00:00.000Z", "not-a-timeZ"],
)
def test_timestamps_require_canonical_utc_second_precision(timestamp):
    with pytest.raises(LabValidationError) as error:
        transition_invocation(
            record(), InvocationState.AUTHORIZED,
            authorized_by="trusted-controller", authorized_at=timestamp,
        )
    assert error.value.code == "INTEGRATION_FIELD_INVALID"
