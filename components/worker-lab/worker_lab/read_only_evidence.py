"""Worker Lab-owned, fake-testable evidence collection for read-only proposals.

This module deliberately has no adapter, Codex, or lifecycle entry point.  It only
rechecks sealed protected inputs after process absence has already been proved.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .canonical import canonical_digest
from .errors import LabValidationError
from .integration import InvocationOperation, InvocationRecord, ValidationStage
from .storage import AtomicRecordStore
from .test_catalog import ChangeFacts, TestCatalog, TestDefinition, TestPlan


READ_ONLY_EVALUATION_PLAN_SCHEMA = "worker-lab-read-only-evaluation-plan:v1"


@dataclass(frozen=True)
class ReadOnlyEvaluationPlan:
    """Durably seal the exact protected catalog selection for one invocation."""

    schema_version: str
    invocation_id: str
    invocation_digest: str
    catalog_version: str
    catalog_digest: str
    selected_profile_ids: tuple[str, ...]
    test_ids: tuple[str, ...]
    test_plan_digest: str
    changed_paths: tuple[str, ...]
    capabilities: tuple[str, ...]
    risk_flags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "invocation_id": self.invocation_id,
            "invocation_digest": self.invocation_digest,
            "catalog_version": self.catalog_version,
            "catalog_digest": self.catalog_digest,
            "selected_profile_ids": list(self.selected_profile_ids),
            "test_ids": list(self.test_ids),
            "test_plan_digest": self.test_plan_digest,
            "changed_paths": list(self.changed_paths),
            "capabilities": list(self.capabilities),
            "risk_flags": list(self.risk_flags),
        }

    @classmethod
    def from_mapping(cls, value: Any) -> "ReadOnlyEvaluationPlan":
        fields = {
            "schema_version", "invocation_id", "invocation_digest", "catalog_version",
            "catalog_digest", "selected_profile_ids", "test_ids", "test_plan_digest",
            "changed_paths", "capabilities", "risk_flags",
        }
        if not isinstance(value, Mapping) or set(value) != fields:
            raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "evaluation plan fields are invalid")
        plan = cls(
            _exact(value["schema_version"], READ_ONLY_EVALUATION_PLAN_SCHEMA),
            _identifier(value["invocation_id"]), _digest(value["invocation_digest"]),
            _text(value["catalog_version"]), _digest(value["catalog_digest"]),
            _profile_ids(value["selected_profile_ids"]), _test_ids(value["test_ids"]),
            _digest(value["test_plan_digest"]), _paths(value["changed_paths"]),
            _texts(value["capabilities"]), _texts(value["risk_flags"]),
        )
        if not plan.selected_profile_ids:
            raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "evaluation plan must select profiles")
        return plan

    def facts(self) -> ChangeFacts:
        return ChangeFacts(
            self.changed_paths, self.capabilities, self.risk_flags,
            mutable_candidate=True, milestone=False,
        )

    def validate(self, record: InvocationRecord, catalog: TestCatalog) -> tuple[TestDefinition, ...]:
        if (
            self.invocation_id != record.invocation_id
            or self.invocation_digest != record.identity_digest()
            or self.catalog_version != record.test_catalog_version
            or self.catalog_digest != record.test_catalog_digest
            or catalog.catalog_version != self.catalog_version
            or catalog.digest() != self.catalog_digest
            or self.test_ids != record.test_ids
            or self.test_plan_digest != record.test_plan_digest
        ):
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "evaluation plan identity differs")
        selected = catalog.select(self.facts(), profile_ids=self.selected_profile_ids)
        if (
            selected.selected_profile_ids != self.selected_profile_ids
            or selected.test_ids != self.test_ids
            or canonical_digest(selected.to_dict()) != self.test_plan_digest
        ):
            raise LabValidationError("INTEGRATION_IDENTITY_INVALID", "evaluation plan selection differs")
        definitions = {item.test_id: item for item in catalog.tests}
        return tuple(definitions[test_id] for test_id in self.test_ids)


class ReadOnlyEvaluationPlanStore:
    def __init__(self, state_root: Path) -> None:
        self.records = AtomicRecordStore(state_root)

    def create(self, plan: ReadOnlyEvaluationPlan) -> None:
        path = self._path(plan.invocation_id)
        try:
            self.records.read(path, ReadOnlyEvaluationPlan.from_mapping)
        except LabValidationError as exc:
            if exc.code != "STORAGE_RECORD_MISSING":
                raise
        else:
            raise LabValidationError("INTEGRATION_EVALUATOR_EXISTS", "evaluation plan already exists")
        self.records.write(path, plan)

    def read(self, invocation_id: str) -> ReadOnlyEvaluationPlan:
        return self.records.read(self._path(_identifier(invocation_id)), ReadOnlyEvaluationPlan.from_mapping)

    @staticmethod
    def _path(invocation_id: str) -> str:
        return f"evaluation-plans/{_identifier(invocation_id)}.json"


@dataclass(frozen=True)
class ReadOnlyEvidence:
    workspace: object
    validation_stages: tuple[ValidationStage, ...]


TestExecutor = Callable[[TestDefinition, Path], int]
WorkspaceInspector = Callable[[InvocationRecord], object]


class ReadOnlyEvidenceCollector:
    """Collect evidence from protected plan/catalog inputs, never worker assertions."""

    def __init__(
        self,
        *,
        state_root: Path,
        workspace_path: Path,
        test_executor: TestExecutor | None = None,
        workspace_inspector: WorkspaceInspector | None = None,
    ) -> None:
        self.state_root = state_root.absolute()
        self.workspace_path = workspace_path.absolute()
        self.test_executor = test_executor
        self.workspace_inspector = workspace_inspector or self._inspect_workspace

    def collect(self, record: InvocationRecord) -> ReadOnlyEvidence:
        if record.operation is not InvocationOperation.READ_ONLY_PROPOSAL:
            raise LabValidationError("INTEGRATION_SCOPE_INVALID", "collector supports read-only proposals only")
        if self.test_executor is None:
            raise LabValidationError("INTEGRATION_EXECUTION_DISABLED", "a sealed test executor is required")
        catalog = self._load_catalog(record)
        definitions = ReadOnlyEvaluationPlanStore(self.state_root).read(record.invocation_id).validate(record, catalog)
        before = self.workspace_inspector(record)
        self._validate_workspace(before, record)
        stages: list[ValidationStage] = []
        for definition in definitions:
            try:
                exit_code = self.test_executor(definition, self.workspace_path)
            except (LabValidationError, OSError, TimeoutError) as exc:
                raise LabValidationError("INTEGRATION_VALIDATION_FAILED", "sealed evaluator did not complete") from exc
            if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code != 0:
                raise LabValidationError("INTEGRATION_VALIDATION_FAILED", "sealed evaluator reported failure")
            stages.append(ValidationStage(definition.test_id, "pass", None))
        after = self.workspace_inspector(record)
        self._validate_workspace(after, record)
        if after != before:
            raise LabValidationError("INTEGRATION_BOUNDARY_FAILED", "validation changed the workspace")
        return ReadOnlyEvidence(before, tuple(stages))

    def _load_catalog(self, record: InvocationRecord) -> TestCatalog:
        catalog_root = self.state_root.parent / "curricula"
        return AtomicRecordStore(catalog_root).read(
            f"catalogs/{record.test_catalog_version}.json", TestCatalog.from_mapping,
        )

    def _inspect_workspace(self, record: InvocationRecord) -> object:
        from .framework_adapter import inspect_acceptance_workspace

        return inspect_acceptance_workspace(
            record, state_root=self.state_root, workspace_path=self.workspace_path,
        )

    @staticmethod
    def _validate_workspace(evidence: object, record: InvocationRecord) -> None:
        from .framework_adapter import WorkspaceEvidence

        if not isinstance(evidence, WorkspaceEvidence) or (
            evidence.observed_head != record.starting_commit
            or evidence.changed_paths
            or evidence.workspace_receipt_digest != record.workspace_receipt_digest
            or evidence.workspace_root_digest != record.workspace_root_digest
            or evidence.workspace_path_digest != record.workspace_path_digest
        ):
            raise LabValidationError("INTEGRATION_BOUNDARY_FAILED", "workspace evidence differs")


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or "\x00" in value:
        raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "text value is invalid")
    return value


def _identifier(value: Any) -> str:
    text = _text(value)
    if not text.replace("-", "").replace("_", "").isalnum():
        raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "identifier is invalid")
    return text


def _digest(value: Any) -> str:
    text = _text(value)
    if not text.startswith("sha256:") or len(text) != 71 or any(item not in "0123456789abcdef" for item in text[7:]):
        raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "digest is invalid")
    return text


def _exact(value: Any, expected: str) -> str:
    if _text(value) != expected:
        raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "unsupported schema")
    return expected


def _texts(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "text list is invalid")
    result = tuple(_text(item) for item in value)
    if result != tuple(sorted(set(result))):
        raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "text list must be sorted and unique")
    return result


def _paths(value: Any) -> tuple[str, ...]:
    return _texts(value)


def _profile_ids(value: Any) -> tuple[str, ...]:
    result = _texts(value)
    if not all(item.endswith(":v1") and item.split(":", 1)[0].replace("_", "").isalnum() for item in result):
        raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "profile ID is invalid")
    return result


def _test_ids(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "test ID list is invalid")
    result = tuple(_text(item) for item in value)
    if (
        not result
        or len(result) != len(set(result))
        or not all(len(item) == 4 and item.startswith("T") and item[1:].isdigit() for item in result)
    ):
        raise LabValidationError("INTEGRATION_EVALUATOR_INVALID", "test ID is invalid")
    return result
