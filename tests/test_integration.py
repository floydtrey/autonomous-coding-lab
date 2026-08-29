import json

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.framework_adapter import ADAPTER_COMMAND, MAX_ADAPTER_RESPONSE_BYTES, parse_result, prepare_invocation
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
        "schema_version": RESULT_SCHEMA, "invocation_digest": invocation.digest(), "request_digest": invocation.digest(),
        "invocation_id": invocation.invocation_id, "attempt_id": invocation.attempt_id, "operation": str(invocation.operation),
        "framework_commit": invocation.framework_commit, "framework_contract_version": invocation.framework_contract_version,
        "runtime_profile_id": invocation.runtime_profile_id, "runtime_identity": DIGEST, "prompt_digest": invocation.prompt_digest,
        "test_catalog_version": invocation.test_catalog_version, "test_catalog_digest": invocation.test_catalog_digest,
        "test_plan_digest": invocation.test_plan_digest, "test_ids": list(invocation.test_ids),
        "workspace_receipt_digest": invocation.workspace_receipt_digest, "workspace_root_digest": invocation.workspace_root_digest,
        "workspace_path_digest": invocation.workspace_path_digest, "starting_commit": invocation.starting_commit,
        "observed_head": SHA, "process_outcome": "pass", "process_identity": "process-1",
        "process_started_at": "2026-08-28T00:00:00Z", "process_ended_at": "2026-08-28T00:00:01Z",
        "workspace_state": "unchanged", "changed_paths": [], "proposal_digest": DIGEST, "candidate_digest": None,
        "validation_stages": [{"test_id": "T001", "outcome": "pass", "failure_code": None}],
        "first_failure_boundary": None, "failure_code": None, "expected": "unchanged workspace",
        "observed": "unchanged workspace", "containment_outcome": "not-needed", "output_digest": DIGEST,
        "content_reference": None, "retryable": False,
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
        return json.dumps({"invocation_digest": invocation.digest(), "prompt_digest": DIGEST, "runtime_identity": DIGEST})

    response = prepare_invocation(invocation, runner=fake)
    assert response.invocation_digest == invocation.digest()


def test_workspace_write_requires_exact_writable_paths():
    invocation = record(operation="workspace-write-code-task", writable_paths=("app.py",))
    assert invocation.sandbox_mode == "workspace-write"
    assert PathIdentity.from_mapping({"path": "app.py", "digest": DIGEST}).path == "app.py"


def test_result_requires_complete_evidence_and_binds_all_invocation_identities():
    invocation = record()
    result = ResultRecord.from_mapping(result_mapping(invocation))
    assert parse_result(json.dumps(result.to_dict()), invocation) == result
    incomplete = result_mapping(invocation)
    del incomplete["output_digest"]
    with pytest.raises(LabValidationError) as error:
        ResultRecord.from_mapping(incomplete)
    assert error.value.code == "INTEGRATION_FIELDS_INVALID"
    mismatched = result_mapping(invocation)
    mismatched["test_plan_digest"] = "sha256:" + "b" * 64
    with pytest.raises(LabValidationError) as error:
        parse_result(json.dumps(mismatched), invocation)
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
