from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping

from .canonical import canonical_digest
from .errors import LabValidationError


CATALOG_SCHEMA = "worker-lab-test-catalog:v2"
TEST_ID_RE = re.compile(r"^T[0-9]{3}$")
PROFILE_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}:v[1-9][0-9]*$")


class CostClass(StrEnum):
    MILLISECOND = "millisecond"
    SECOND = "second"
    MINUTE = "minute"


class TestMode(StrEnum):
    __test__ = False

    ALWAYS = "always"
    CONDITIONAL = "conditional"
    MILESTONE = "milestone"
    RETIRED = "retired"


class TestRunner(StrEnum):
    COMMAND = "command"
    FRAMEWORK_EVALUATOR = "framework-evaluator"
    CONTROLLER_DRILL = "controller-drill"


COST_ORDER = {
    CostClass.MILLISECOND: 0,
    CostClass.SECOND: 1,
    CostClass.MINUTE: 2,
}


@dataclass(frozen=True)
class TestDefinition:
    __test__ = False
    test_id: str
    version: int
    name: str
    purpose: str
    command: tuple[str, ...]
    mode: TestMode
    cost_class: CostClass
    runner: TestRunner = TestRunner.COMMAND
    owner: str = "worker-lab"
    path_prefixes: tuple[str, ...] = ()
    path_suffixes: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    replacement_test_id: str | None = None
    environment_requirements: tuple[str, ...] = ()
    evidence_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not TEST_ID_RE.fullmatch(self.test_id):
            raise LabValidationError("TEST_ID_INVALID", f"invalid test ID: {self.test_id!r}")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version <= 0:
            raise LabValidationError("TEST_VERSION_INVALID", "test version must be positive")
        if (
            not isinstance(self.name, str)
            or not isinstance(self.purpose, str)
            or not self.name.strip()
            or not self.purpose.strip()
            or not self.command
        ):
            raise LabValidationError("TEST_DEFINITION_INVALID", "name, purpose, and command are required")
        if not all(isinstance(arg, str) and arg for arg in self.command):
            raise LabValidationError("TEST_DEFINITION_INVALID", "command arguments must be text")
        if not isinstance(self.mode, TestMode) or not isinstance(self.cost_class, CostClass):
            raise LabValidationError("TEST_DEFINITION_INVALID", "mode and cost class must be enums")
        if (
            not isinstance(self.runner, TestRunner)
            or not isinstance(self.owner, str)
            or not self.owner.strip()
        ):
            raise LabValidationError("TEST_DEFINITION_INVALID", "runner and owner are required")
        for field, values in (
            ("path_prefixes", self.path_prefixes),
            ("path_suffixes", self.path_suffixes),
            ("capabilities", self.capabilities),
            ("risk_flags", self.risk_flags),
            ("prerequisites", self.prerequisites),
            ("environment_requirements", self.environment_requirements),
            ("evidence_fields", self.evidence_fields),
        ):
            if values != tuple(sorted(set(values))):
                raise LabValidationError("TEST_DEFINITION_INVALID", f"{field} must be sorted and unique")
        if not all(TEST_ID_RE.fullmatch(item) for item in self.prerequisites):
            raise LabValidationError("TEST_ID_INVALID", "prerequisite test ID is invalid")
        if self.test_id in self.prerequisites:
            raise LabValidationError("TEST_DEPENDENCY_INVALID", "test cannot require itself")
        if self.mode is TestMode.RETIRED:
            if self.replacement_test_id is not None and not TEST_ID_RE.fullmatch(self.replacement_test_id):
                raise LabValidationError("TEST_ID_INVALID", "replacement test ID is invalid")
        elif self.replacement_test_id is not None:
            raise LabValidationError(
                "TEST_DEFINITION_INVALID", "only retired tests may name a replacement"
            )

    def matches_path(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.path_prefixes) or any(
            path.endswith(suffix) for suffix in self.path_suffixes
        )

    def matches_facts(self, facts: "ChangeFacts") -> bool:
        return (
            any(self.matches_path(path) for path in facts.changed_paths)
            or bool(set(self.capabilities).intersection(facts.capabilities))
            or bool(set(self.risk_flags).intersection(facts.risk_flags))
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["command"] = list(self.command)
        for field in (
            "path_prefixes", "path_suffixes", "capabilities", "risk_flags", "prerequisites",
            "environment_requirements", "evidence_fields",
        ):
            value[field] = list(value[field])
        value["mode"] = str(self.mode)
        value["cost_class"] = str(self.cost_class)
        value["runner"] = str(self.runner)
        return value

    @classmethod
    def from_mapping(cls, value: Any) -> "TestDefinition":
        expected = {
            "test_id", "version", "name", "purpose", "command", "mode", "cost_class",
            "runner", "owner", "path_prefixes", "path_suffixes", "capabilities",
            "risk_flags", "prerequisites", "replacement_test_id",
            "environment_requirements", "evidence_fields",
        }
        data = _strict_object(value, expected, "TEST_DEFINITION_INVALID")
        try:
            mode = TestMode(data["mode"])
            cost_class = CostClass(data["cost_class"])
            runner = TestRunner(data["runner"])
        except (TypeError, ValueError) as exc:
            raise LabValidationError("TEST_DEFINITION_INVALID", "unsupported enum value") from exc
        return cls(
            test_id=data["test_id"],
            version=data["version"],
            name=data["name"],
            purpose=data["purpose"],
            command=_text_tuple(data["command"], "command"),
            mode=mode,
            cost_class=cost_class,
            runner=runner,
            owner=data["owner"],
            path_prefixes=_text_tuple(data["path_prefixes"], "path_prefixes"),
            path_suffixes=_text_tuple(data["path_suffixes"], "path_suffixes"),
            capabilities=_text_tuple(data["capabilities"], "capabilities"),
            risk_flags=_text_tuple(data["risk_flags"], "risk_flags"),
            prerequisites=_text_tuple(data["prerequisites"], "prerequisites"),
            replacement_test_id=data["replacement_test_id"],
            environment_requirements=_text_tuple(
                data["environment_requirements"], "environment_requirements"
            ),
            evidence_fields=_text_tuple(data["evidence_fields"], "evidence_fields"),
        )


@dataclass(frozen=True)
class TestProfile:
    __test__ = False
    profile_id: str
    purpose: str
    test_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not PROFILE_ID_RE.fullmatch(self.profile_id):
            raise LabValidationError("TEST_PROFILE_INVALID", "profile ID is invalid")
        if not isinstance(self.purpose, str) or not self.purpose.strip() or not self.test_ids:
            raise LabValidationError("TEST_PROFILE_INVALID", "profile purpose and tests are required")
        if self.test_ids != tuple(sorted(set(self.test_ids))):
            raise LabValidationError("TEST_PROFILE_INVALID", "profile test IDs must be sorted and unique")
        if not all(TEST_ID_RE.fullmatch(item) for item in self.test_ids):
            raise LabValidationError("TEST_ID_INVALID", "profile test ID is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {"profile_id": self.profile_id, "purpose": self.purpose, "test_ids": list(self.test_ids)}

    @classmethod
    def from_mapping(cls, value: Any) -> "TestProfile":
        data = _strict_object(
            value, {"profile_id", "purpose", "test_ids"}, "TEST_PROFILE_INVALID"
        )
        return cls(
            data["profile_id"], data["purpose"], _text_tuple(data["test_ids"], "test_ids")
        )


@dataclass(frozen=True)
class ChangeFacts:
    changed_paths: tuple[str, ...]
    capabilities: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()
    mutable_candidate: bool = True
    milestone: bool = False

    def __post_init__(self) -> None:
        for field, values in (
            ("changed_paths", self.changed_paths),
            ("capabilities", self.capabilities),
            ("risk_flags", self.risk_flags),
        ):
            if values != tuple(sorted(set(values))):
                raise LabValidationError("TEST_FACTS_INVALID", f"{field} must be sorted and unique")
        for path in self.changed_paths:
            candidate = PurePosixPath(path)
            if (
                not path
                or candidate.is_absolute()
                or ".." in candidate.parts
                or candidate.as_posix() != path
                or ":" in candidate.parts[0]
            ):
                raise LabValidationError("TEST_FACTS_INVALID", f"invalid changed path: {path!r}")


@dataclass(frozen=True)
class TestPlan:
    catalog_version: str
    catalog_digest: str
    selected_profile_ids: tuple[str, ...]
    test_ids: tuple[str, ...]
    reused_evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "catalog_version": self.catalog_version,
            "catalog_digest": self.catalog_digest,
            "selected_profile_ids": list(self.selected_profile_ids),
            "test_ids": list(self.test_ids),
            "reused_evidence": list(self.reused_evidence),
        }


@dataclass(frozen=True)
class TestCatalog:
    __test__ = False
    schema_version: str
    catalog_version: str
    tests: tuple[TestDefinition, ...]
    profiles: tuple[TestProfile, ...]

    def __post_init__(self) -> None:
        if self.schema_version != CATALOG_SCHEMA:
            raise LabValidationError("TEST_CATALOG_INVALID", "unsupported catalog schema")
        if not isinstance(self.catalog_version, str) or not self.catalog_version.strip():
            raise LabValidationError("TEST_CATALOG_INVALID", "catalog version is required")
        ids = tuple(item.test_id for item in self.tests)
        if ids != tuple(sorted(set(ids))):
            raise LabValidationError("TEST_CATALOG_INVALID", "tests must use sorted unique IDs")
        profile_ids = tuple(item.profile_id for item in self.profiles)
        if profile_ids != tuple(sorted(set(profile_ids))):
            raise LabValidationError("TEST_CATALOG_INVALID", "profiles must use sorted unique IDs")
        known = set(ids)
        for test in self.tests:
            missing = set(test.prerequisites) - known
            if missing:
                raise LabValidationError(
                    "TEST_DEPENDENCY_INVALID", f"{test.test_id} has unknown prerequisites: {sorted(missing)}"
                )
        for profile in self.profiles:
            missing = set(profile.test_ids) - known
            if missing:
                raise LabValidationError(
                    "TEST_PROFILE_INVALID", f"{profile.profile_id} has unknown tests: {sorted(missing)}"
                )
        self._assert_acyclic()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "catalog_version": self.catalog_version,
            "tests": [item.to_dict() for item in self.tests],
            "profiles": [item.to_dict() for item in self.profiles],
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: Any) -> "TestCatalog":
        data = _strict_object(
            value,
            {"schema_version", "catalog_version", "tests", "profiles"},
            "TEST_CATALOG_INVALID",
        )
        if not isinstance(data["tests"], list) or not isinstance(data["profiles"], list):
            raise LabValidationError("TEST_CATALOG_INVALID", "tests and profiles must be arrays")
        return cls(
            schema_version=data["schema_version"],
            catalog_version=data["catalog_version"],
            tests=tuple(TestDefinition.from_mapping(item) for item in data["tests"]),
            profiles=tuple(TestProfile.from_mapping(item) for item in data["profiles"]),
        )

    def select(self, facts: ChangeFacts, *, profile_ids: Iterable[str] = ()) -> TestPlan:
        requested_profiles = tuple(sorted(set(profile_ids)))
        profiles = {item.profile_id: item for item in self.profiles}
        unknown_profiles = set(requested_profiles) - set(profiles)
        if unknown_profiles:
            raise LabValidationError(
                "TEST_PROFILE_INVALID", f"unknown profiles: {sorted(unknown_profiles)}"
            )

        tests = {item.test_id: item for item in self.tests}
        selected: set[str] = set()
        for profile_id in requested_profiles:
            selected.update(profiles[profile_id].test_ids)
        for test in self.tests:
            if test.mode is TestMode.RETIRED:
                continue
            if test.mode is TestMode.ALWAYS and facts.mutable_candidate:
                selected.add(test.test_id)
            if test.mode is TestMode.MILESTONE and facts.milestone:
                selected.add(test.test_id)
            if test.mode is TestMode.CONDITIONAL and test.matches_facts(facts):
                selected.add(test.test_id)

        unmapped = [
            path
            for path in facts.changed_paths
            if not any(
                test.mode is not TestMode.RETIRED and test.matches_path(path)
                for test in self.tests
            )
        ]
        if unmapped:
            raise LabValidationError(
                "TEST_SELECTION_UNMAPPED", f"changed paths have no trusted test mapping: {unmapped}"
            )

        self._include_prerequisites(selected, tests)
        active_selected = [tests[test_id] for test_id in selected]
        retired = [test.test_id for test in active_selected if test.mode is TestMode.RETIRED]
        if retired:
            raise LabValidationError(
                "TEST_SELECTION_RETIRED", f"selected profiles depend on retired tests: {sorted(retired)}"
            )
        ordered = tuple(
            test.test_id
            for test in sorted(active_selected, key=lambda item: (COST_ORDER[item.cost_class], item.test_id))
        )
        return TestPlan(
            self.catalog_version,
            self.digest(),
            requested_profiles,
            ordered,
        )

    def _include_prerequisites(
        self, selected: set[str], tests: Mapping[str, TestDefinition]
    ) -> None:
        pending = list(selected)
        while pending:
            current = pending.pop()
            for required in tests[current].prerequisites:
                if required not in selected:
                    selected.add(required)
                    pending.append(required)

    def _assert_acyclic(self) -> None:
        graph = {item.test_id: item.prerequisites for item in self.tests}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(test_id: str) -> None:
            if test_id in visiting:
                raise LabValidationError("TEST_DEPENDENCY_INVALID", "test prerequisite cycle detected")
            if test_id in visited:
                return
            visiting.add(test_id)
            for required in graph[test_id]:
                visit(required)
            visiting.remove(test_id)
            visited.add(test_id)

        for test_id in graph:
            visit(test_id)


def _strict_object(value: Any, expected: set[str], code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise LabValidationError(code, "fields are missing or unknown")
    return value


def _text_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise LabValidationError("TEST_DEFINITION_INVALID", f"{field} must be a text array")
    return tuple(value)
