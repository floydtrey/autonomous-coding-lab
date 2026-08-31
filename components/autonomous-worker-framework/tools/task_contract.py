from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

try:
    from tools.local_worker_harness import (
        ConsumerValidationPlan,
        FixtureTask,
        TrustedValidationCommand,
        run_codex_fixture_job,
    )
except ModuleNotFoundError:  # direct execution support
    from local_worker_harness import (  # type: ignore
        ConsumerValidationPlan,
        FixtureTask,
        TrustedValidationCommand,
        run_codex_fixture_job,
    )


CONTRACT_VERSION = "worker-task:v1"
CONTROLLER_STATES = {"AUTO", "QUEUED", "REVIEW", "BLOCKED"}
CONTROLLER_PREFIX_RE = re.compile(
    r"^(?:\[(?:AUTO|QUEUED|REVIEW|BLOCKED)\]\s*)+", re.IGNORECASE
)
PROTECTED_PREFIXES = (
    ".git/",
    ".github/",
    "docs/governance/",
    "docs/patch_system/",
    "docs/current_direction/",
    "docs/core_contract/",
    "docs/vera_baseline/",
    "tools/autonomy_",
    "tests/test_autonomy_",
    "data/",
    "logs/",
    "voice_models/",
    ".amt_updates/",
)
PROTECTED_EXACT = {
    ".gitignore",
    "PROJECT_BASELINE.json",
    "README_CURRENT_CHECKPOINT.md",
    "docs/00_START_HERE.md",
    "tools/agent_patch_guard.py",
}


class TaskContractError(ValueError):
    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


@dataclass(frozen=True)
class AcceptanceAssertion:
    kind: str
    path: str | None = None
    expected: str | tuple[str, ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        if isinstance(value["expected"], tuple):
            value["expected"] = list(value["expected"])
        return value


@dataclass(frozen=True)
class WorkerTaskContract:
    contract_version: str
    task_id: str
    consumer: str
    controller_state: str
    title: str
    risk: str
    allowed_paths: tuple[str, ...]
    fixture_path: str
    initial_state: str
    target_state: str
    acceptance_assertions: tuple[AcceptanceAssertion, ...]
    validation_plan: ConsumerValidationPlan

    @property
    def canonical_title(self) -> str:
        return f"[{self.controller_state}] {self.title}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "task_id": self.task_id,
            "consumer": self.consumer,
            "controller_state": self.controller_state,
            "title": self.title,
            "risk": self.risk,
            "allowed_paths": list(self.allowed_paths),
            "fixture_path": self.fixture_path,
            "initial_state": self.initial_state,
            "target_state": self.target_state,
            "acceptance_assertions": [item.to_dict() for item in self.acceptance_assertions],
            "trusted_validation": self.validation_plan.to_dict(),
        }

    def to_json(self, *, pretty: bool = False) -> str:
        options: dict[str, Any] = {"sort_keys": True}
        if pretty:
            options["indent"] = 2
        else:
            options["separators"] = (",", ":")
        return json.dumps(self.to_dict(), **options)

    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    def to_fixture_task(self) -> FixtureTask:
        return FixtureTask.from_mapping(
            {
                "contract_version": "fixture-task:v1",
                "task_id": self.task_id,
                "consumer": self.consumer,
                "allowed_paths": list(self.allowed_paths),
                "fixture_path": self.fixture_path,
                "initial_state": self.initial_state,
                "target_state": self.target_state,
            }
        )

    @classmethod
    def from_json(cls, value: str) -> "WorkerTaskContract":
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise TaskContractError("TASK_CONTRACT_INVALID", f"invalid JSON: {exc.msg}") from exc
        return cls.from_mapping(decoded)

    @classmethod
    def from_mapping(cls, value: Any) -> "WorkerTaskContract":
        if not isinstance(value, Mapping):
            raise TaskContractError("TASK_CONTRACT_INVALID", "task contract must be an object")
        expected_fields = {
            "contract_version", "task_id", "consumer", "controller_state", "title",
            "risk", "allowed_paths", "fixture_path", "initial_state", "target_state",
            "acceptance_assertions", "trusted_validation",
        }
        _strict_fields(value, expected_fields)
        version = _text(value["contract_version"], "contract_version")
        if version != CONTRACT_VERSION:
            raise TaskContractError(
                "TASK_CONTRACT_INVALID",
                f"unsupported contract_version {version!r}; expected {CONTRACT_VERSION!r}",
            )
        task_id = _text(value["task_id"], "task_id")
        consumer = _text(value["consumer"], "consumer")
        state = _text(value["controller_state"], "controller_state").upper()
        if state not in CONTROLLER_STATES:
            raise TaskContractError("TASK_CONTRACT_INVALID", "unsupported controller_state")
        title = CONTROLLER_PREFIX_RE.sub("", _text(value["title"], "title")).strip()
        if not title:
            raise TaskContractError("TASK_CONTRACT_INVALID", "title requires non-prefix text")
        risk = _text(value["risk"], "risk").lower()
        if risk != "low":
            raise TaskContractError(
                "TASK_RISK_INVALID",
                "the deterministic commissioning fixture must be classified low risk",
            )
        if state not in {"AUTO", "QUEUED"}:
            raise TaskContractError(
                "TASK_RISK_INVALID",
                "a low-risk commissioning task must be AUTO or QUEUED",
            )
        fixture_path = _repo_path(value["fixture_path"], "fixture_path")
        allowed_paths = _path_list(value["allowed_paths"], "allowed_paths")
        if allowed_paths != (fixture_path,):
            raise TaskContractError(
                "TASK_SCOPE_INVALID",
                "allowed_paths must equal the single deterministic fixture path",
            )
        if not fixture_path.startswith("autonomy_smoke/"):
            raise TaskContractError(
                "TASK_SCOPE_INVALID", "commissioning fixture must stay inside autonomy_smoke/"
            )
        _reject_protected(fixture_path)
        initial = _state(value["initial_state"], "initial_state")
        target = _state(value["target_state"], "target_state")
        if initial == target:
            raise TaskContractError("TASK_CONTRACT_INVALID", "initial and target states must differ")
        assertions = _parse_assertions(value["acceptance_assertions"])
        required_assertions = _required_assertions(fixture_path, target)
        if assertions != required_assertions:
            raise TaskContractError(
                "TASK_CONTRACT_INVALID",
                "acceptance_assertions must exactly match executable commissioning assertions",
            )
        validation_plan = _parse_validation_plan(value["trusted_validation"])
        if not validation_plan.quick or not validation_plan.full:
            raise TaskContractError(
                "TASK_CONTRACT_INVALID",
                "commissioning tasks require explicit quick and full trusted validation",
            )
        return cls(
            version, task_id, consumer, state, title, risk, allowed_paths, fixture_path,
            initial, target, assertions, validation_plan,
        )


def _required_assertions(path: str, target: str) -> tuple[AcceptanceAssertion, ...]:
    return (
        AcceptanceAssertion("changed-paths-exact", expected=(path,)),
        AcceptanceAssertion("fixture-state-exact", path=path, expected=target),
        AcceptanceAssertion("quick-validation-pass"),
        AcceptanceAssertion("full-validation-pass"),
    )


def commissioning_assertions(path: str, target: str) -> list[dict[str, Any]]:
    return [item.to_dict() for item in _required_assertions(path, target)]


def run_codex_worker_task(contract: WorkerTaskContract, repo_root, framework_repo, *, executor=None):
    options = {
        "validation_plan": contract.validation_plan,
        "task_contract_digest_override": contract.digest(),
    }
    if executor is not None:
        options["executor"] = executor
    return run_codex_fixture_job(
        contract.to_fixture_task(),
        repo_root,
        framework_repo,
        **options,
    )


def _parse_assertions(value: Any) -> tuple[AcceptanceAssertion, ...]:
    if not isinstance(value, list):
        raise TaskContractError("TASK_CONTRACT_INVALID", "acceptance_assertions must be an array")
    parsed: list[AcceptanceAssertion] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {"kind", "path", "expected"}:
            raise TaskContractError("TASK_CONTRACT_INVALID", "acceptance assertion fields are invalid")
        expected = item["expected"]
        if isinstance(expected, list):
            expected = tuple(_repo_path(path, "assertion expected path") for path in expected)
        elif expected is not None and not isinstance(expected, str):
            raise TaskContractError("TASK_CONTRACT_INVALID", "assertion expected value is invalid")
        path = item["path"]
        if path is not None:
            path = _repo_path(path, "assertion path")
        parsed.append(AcceptanceAssertion(_text(item["kind"], "assertion kind"), path, expected))
    return tuple(parsed)


def _parse_validation_plan(value: Any) -> ConsumerValidationPlan:
    if not isinstance(value, Mapping) or set(value) != {"quick", "full"}:
        raise TaskContractError("TASK_CONTRACT_INVALID", "trusted_validation fields are invalid")
    return ConsumerValidationPlan(
        quick=_parse_commands(value["quick"], "quick"),
        full=_parse_commands(value["full"], "full"),
    )


def _parse_commands(value: Any, field: str) -> tuple[TrustedValidationCommand, ...]:
    if not isinstance(value, list):
        raise TaskContractError("TASK_CONTRACT_INVALID", f"trusted_validation.{field} must be an array")
    commands: list[TrustedValidationCommand] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {"name", "argv", "timeout_seconds"}:
            raise TaskContractError("TASK_CONTRACT_INVALID", "trusted validation command fields are invalid")
        argv = item["argv"]
        timeout = item["timeout_seconds"]
        if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) and arg for arg in argv):
            raise TaskContractError("TASK_CONTRACT_INVALID", "trusted validation argv is invalid")
        if isinstance(timeout, bool) or not isinstance(timeout, int):
            raise TaskContractError("TASK_CONTRACT_INVALID", "trusted validation timeout is invalid")
        try:
            commands.append(TrustedValidationCommand(_text(item["name"], "validation name"), tuple(argv), timeout))
        except ValueError as exc:
            raise TaskContractError("TASK_CONTRACT_INVALID", str(exc)) from exc
    return tuple(commands)


def _reject_protected(path: str) -> None:
    if path in PROTECTED_EXACT or any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES):
        raise TaskContractError("TASK_SCOPE_INVALID", f"protected path is forbidden: {path}")


def _path_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise TaskContractError("TASK_SCOPE_INVALID", f"{field} must be a non-empty array")
    paths = tuple(_repo_path(item, field) for item in value)
    if paths != tuple(sorted(set(paths))):
        raise TaskContractError("TASK_SCOPE_INVALID", f"{field} must be sorted and unique")
    for path in paths:
        _reject_protected(path)
    return paths


def _repo_path(value: Any, field: str) -> str:
    text = _text(value, field).replace("\\", "/")
    candidate = PurePosixPath(text)
    if candidate.is_absolute() or text.startswith("/") or ".." in candidate.parts or candidate.as_posix() != text or ":" in candidate.parts[0]:
        raise TaskContractError("TASK_SCOPE_INVALID", f"{field} is not a normalized repository path")
    return text


def _state(value: Any, field: str) -> str:
    state = _text(value, field).upper()
    if state not in {"A", "B", "ABSENT"}:
        raise TaskContractError("TASK_CONTRACT_INVALID", f"{field} must be A, B, or ABSENT")
    return state


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskContractError("TASK_CONTRACT_INVALID", f"{field} must be non-empty text")
    return value.strip()


def _strict_fields(value: Mapping[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        unknown = sorted(set(value) - expected)
        raise TaskContractError(
            "TASK_CONTRACT_INVALID", f"task contract fields invalid: missing={missing}, unknown={unknown}"
        )
