import copy
import subprocess

import pytest

from tools.task_contract import (
    CONTRACT_VERSION,
    TaskContractError,
    WorkerTaskContract,
    commissioning_assertions,
    run_codex_worker_task,
)
from tools.codex_runtime import CodexExecution


def _mapping():
    path = "autonomy_smoke/fixture_state.txt"
    return {
        "contract_version": CONTRACT_VERSION,
        "task_id": "mine-tracker-l1-fixture",
        "consumer": "mine-tracker",
        "controller_state": "AUTO",
        "title": "[QUEUED] Commission deterministic fixture",
        "risk": "low",
        "allowed_paths": [path],
        "fixture_path": path,
        "initial_state": "ABSENT",
        "target_state": "A",
        "acceptance_assertions": commissioning_assertions(path, "A"),
        "trusted_validation": {
            "quick": [{"name": "Focused tests", "argv": ["python", "-m", "pytest", "-q", "tests/test_worker_result.py"], "timeout_seconds": 300}],
            "full": [{"name": "Full tests", "argv": ["python", "-m", "pytest", "-q"], "timeout_seconds": 900}],
        },
    }


def test_valid_contract_round_trips_deterministically_and_converts_to_fixture():
    contract = WorkerTaskContract.from_mapping(_mapping())

    decoded = WorkerTaskContract.from_json(contract.to_json())

    assert decoded == contract
    assert decoded.to_json() == contract.to_json()
    assert decoded.digest() == contract.digest()
    assert decoded.canonical_title == "[AUTO] Commission deterministic fixture"
    assert decoded.to_fixture_task().allowed_paths == ("autonomy_smoke/fixture_state.txt",)


def test_unknown_version_fails_closed_with_contract_code():
    value = _mapping()
    value["contract_version"] = "worker-task:v2"

    with pytest.raises(TaskContractError) as error:
        WorkerTaskContract.from_mapping(value)

    assert error.value.code == "TASK_CONTRACT_INVALID"


@pytest.mark.parametrize("risk", ["medium", "high", "unknown"])
def test_commissioning_risk_must_be_low(risk):
    value = _mapping()
    value["risk"] = risk

    with pytest.raises(TaskContractError) as error:
        WorkerTaskContract.from_mapping(value)

    assert error.value.code == "TASK_RISK_INVALID"


def test_extra_allowed_path_fails_exact_scope_check():
    value = _mapping()
    value["allowed_paths"].append("autonomy_smoke/other.txt")

    with pytest.raises(TaskContractError) as error:
        WorkerTaskContract.from_mapping(value)

    assert error.value.code == "TASK_SCOPE_INVALID"


@pytest.mark.parametrize("path", [".github/workflows/worker.yml", "tools/autonomy_controller.py", "../escape.txt"])
def test_protected_or_traversing_scope_fails_closed(path):
    value = _mapping()
    value["fixture_path"] = path
    value["allowed_paths"] = [path]
    value["acceptance_assertions"] = commissioning_assertions(path, "A")

    with pytest.raises(TaskContractError) as error:
        WorkerTaskContract.from_mapping(value)

    assert error.value.code == "TASK_SCOPE_INVALID"


def test_acceptance_assertions_must_match_executable_operation_exactly():
    value = _mapping()
    value["acceptance_assertions"] = copy.deepcopy(value["acceptance_assertions"])
    value["acceptance_assertions"][1]["expected"] = "B"

    with pytest.raises(TaskContractError) as error:
        WorkerTaskContract.from_mapping(value)

    assert error.value.code == "TASK_CONTRACT_INVALID"


def test_validation_plan_is_part_of_contract_identity():
    first = WorkerTaskContract.from_mapping(_mapping())
    changed = _mapping()
    changed["trusted_validation"]["full"][0]["timeout_seconds"] = 901
    second = WorkerTaskContract.from_mapping(changed)

    assert first.digest() != second.digest()


def test_low_risk_contract_rejects_review_or_blocked_state():
    value = _mapping()
    value["controller_state"] = "REVIEW"

    with pytest.raises(TaskContractError) as error:
        WorkerTaskContract.from_mapping(value)

    assert error.value.code == "TASK_RISK_INVALID"


def test_contract_requires_both_quick_and_full_validation():
    value = _mapping()
    value["trusted_validation"]["quick"] = []

    with pytest.raises(TaskContractError) as error:
        WorkerTaskContract.from_mapping(value)

    assert error.value.code == "TASK_CONTRACT_INVALID"


def test_validated_contract_identity_reaches_worker_result(tmp_path):
    value = _mapping()
    value["trusted_validation"] = {
        "quick": [{"name": "Quick", "argv": ["git", "status", "--short"], "timeout_seconds": 30}],
        "full": [{"name": "Full", "argv": ["git", "diff", "--check"], "timeout_seconds": 30}],
    }
    contract = WorkerTaskContract.from_mapping(value)
    repo = tmp_path / "consumer"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=repo, check=True)
    (repo / "autonomy_smoke").mkdir()
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "baseline"], cwd=repo, check=True, capture_output=True)

    def executor(request):
        (repo / "autonomy_smoke" / "fixture_state.txt").write_bytes(b"STATE=A\n")
        return CodexExecution(("codex", "exec"), 0, "done", "")

    result = run_codex_worker_task(contract, repo, tmp_path / "framework", executor=executor)

    assert result.worker.result == "pass"
    assert result.task_contract_digest == contract.digest()
