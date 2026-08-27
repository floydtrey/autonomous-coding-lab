from copy import deepcopy

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.models import WorkspaceReceipt, WorkspaceReceiptState
from tests.test_models import workspace_receipt_mapping


def test_receipt_round_trips_without_mutating_input() -> None:
    value = workspace_receipt_mapping()
    before = deepcopy(value)
    receipt = WorkspaceReceipt.from_mapping(value)
    assert value == before
    assert WorkspaceReceipt.from_mapping(receipt.to_dict()) == receipt
    assert receipt.to_json() == receipt.to_json()


@pytest.mark.parametrize(
    "relative_path",
    ["OTHER-ATTEMPT", "nested/ATTEMPT-000001", "../ATTEMPT-000001", "/ATTEMPT-000001", "C:/ATTEMPT-000001", "a\\b"],
)
def test_prepared_receipt_rejects_any_path_other_than_attempt_id(relative_path: str) -> None:
    value = workspace_receipt_mapping()
    value["workspace_relative_path"] = relative_path
    with pytest.raises(LabValidationError) as error:
        WorkspaceReceipt.from_mapping(value)
    assert error.value.code in {"RECORD_PATH_INVALID", "RECORD_WORKSPACE_PATH_INVALID"}


def test_quarantined_receipt_requires_deterministic_attempt_bound_name() -> None:
    value = workspace_receipt_mapping()
    value["state"] = "QUARANTINED"
    value["workspace_relative_path"] = ".worker-lab-quarantine-ATTEMPT-000001"
    receipt = WorkspaceReceipt.from_mapping(value)
    assert receipt.state is WorkspaceReceiptState.QUARANTINED

    value["workspace_relative_path"] = ".worker-lab-quarantine-OTHER-ATTEMPT"
    with pytest.raises(LabValidationError) as error:
        WorkspaceReceipt.from_mapping(value)
    assert error.value.code == "RECORD_WORKSPACE_PATH_INVALID"


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("template_commit", "A" * 40),
        ("workspace_root_digest", "sha256:" + "A" * 64),
        ("workspace_path_digest", "sha256:" + "b" * 63),
        ("created_at", "2026-08-27T12:00:00+00:00"),
        ("state", "READY"),
    ],
)
def test_receipt_rejects_malformed_identity_fields(field: str, replacement: str) -> None:
    value = workspace_receipt_mapping()
    value[field] = replacement
    with pytest.raises(LabValidationError):
        WorkspaceReceipt.from_mapping(value)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("exercise_version", 2),
        ("template_repository", "local/other-template"),
        ("template_commit", "c" * 40),
        ("workspace_root_digest", "sha256:" + "c" * 64),
        ("workspace_path_digest", "sha256:" + "d" * 64),
    ],
)
def test_every_workspace_binding_changes_canonical_identity(field: str, replacement: object) -> None:
    original = WorkspaceReceipt.from_mapping(workspace_receipt_mapping())
    changed_mapping = workspace_receipt_mapping()
    changed_mapping[field] = replacement
    changed = WorkspaceReceipt.from_mapping(changed_mapping)
    assert changed.digest() != original.digest()
