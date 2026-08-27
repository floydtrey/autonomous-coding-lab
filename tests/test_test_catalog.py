import pytest

from worker_lab.errors import LabValidationError
from worker_lab.test_catalog import (
    CATALOG_SCHEMA,
    ChangeFacts,
    CostClass,
    TestCatalog,
    TestDefinition,
    TestMode,
    TestProfile,
)


def definition(test_id, *, mode=TestMode.CONDITIONAL, cost=CostClass.SECOND, **kwargs):
    return TestDefinition(
        test_id=test_id,
        version=1,
        name=f"Test {test_id}",
        purpose=f"Purpose for {test_id}",
        command=("python", "-m", "pytest", "-q"),
        mode=mode,
        cost_class=cost,
        **kwargs,
    )


def catalog():
    return TestCatalog(
        CATALOG_SCHEMA,
        "worker-lab-v1",
        tests=(
            definition("T001", mode=TestMode.ALWAYS, cost=CostClass.MILLISECOND),
            definition("T002", mode=TestMode.ALWAYS, cost=CostClass.MILLISECOND),
            definition("T004", path_suffixes=(".py",), prerequisites=("T001",)),
            definition("T005", path_suffixes=(".json",), prerequisites=("T001",)),
            definition("T006", capabilities=("canonical-data",), prerequisites=("T005",)),
            definition("T020", mode=TestMode.MILESTONE, cost=CostClass.MINUTE),
        ),
        profiles=(
            TestProfile("JSON_RECORD_CHANGE:v1", "JSON record changes", ("T001", "T002", "T005", "T006")),
            TestProfile("PYTHON_CHANGE:v1", "Python source changes", ("T001", "T002", "T004")),
        ),
    )


def test_catalog_digest_and_selection_are_deterministic():
    value = catalog()
    facts = ChangeFacts(("worker_lab/models.py",), capabilities=("canonical-data",))
    first = value.select(facts, profile_ids=("PYTHON_CHANGE:v1",))
    second = value.select(facts, profile_ids=("PYTHON_CHANGE:v1",))
    assert first == second
    assert TestCatalog.from_mapping(value.to_dict()) == value
    assert first.catalog_digest == value.digest()
    assert first.test_ids == ("T001", "T002", "T004", "T005", "T006")


def test_catalog_loading_rejects_unknown_fields():
    value = catalog().to_dict()
    value["surprise"] = True
    with pytest.raises(LabValidationError) as error:
        TestCatalog.from_mapping(value)
    assert error.value.code == "TEST_CATALOG_INVALID"


@pytest.mark.parametrize(("field", "value"), [("version", "1"), ("name", None), ("owner", None)])
def test_catalog_loading_rejects_malformed_definition_types(field, value):
    data = catalog().to_dict()
    data["tests"][0][field] = value
    with pytest.raises(LabValidationError):
        TestCatalog.from_mapping(data)


def test_profiles_and_automatic_selection_form_a_union_without_duplicates():
    facts = ChangeFacts(("definition.json",), capabilities=("canonical-data",))
    plan = catalog().select(facts, profile_ids=("JSON_RECORD_CHANGE:v1",))
    assert plan.test_ids == ("T001", "T002", "T005", "T006")


def test_cheapest_tests_run_before_minute_tests_at_milestone():
    facts = ChangeFacts(("worker_lab/models.py",), milestone=True)
    plan = catalog().select(facts)
    assert plan.test_ids[:2] == ("T001", "T002")
    assert plan.test_ids[-1] == "T020"


def test_unmapped_changed_path_fails_closed():
    with pytest.raises(LabValidationError) as error:
        catalog().select(ChangeFacts(("styles/main.css",)))
    assert error.value.code == "TEST_SELECTION_UNMAPPED"


def test_unknown_profile_fails_closed():
    with pytest.raises(LabValidationError) as error:
        catalog().select(ChangeFacts(("worker_lab/models.py",)), profile_ids=("MISSING:v1",))
    assert error.value.code == "TEST_PROFILE_INVALID"


def test_unknown_prerequisite_is_rejected():
    with pytest.raises(LabValidationError) as error:
        TestCatalog(
            CATALOG_SCHEMA,
            "bad:v1",
            tests=(definition("T001", prerequisites=("T999",)),),
            profiles=(),
        )
    assert error.value.code == "TEST_DEPENDENCY_INVALID"


def test_prerequisite_cycles_are_rejected():
    with pytest.raises(LabValidationError) as error:
        TestCatalog(
            CATALOG_SCHEMA,
            "bad:v1",
            tests=(
                definition("T001", prerequisites=("T002",)),
                definition("T002", prerequisites=("T001",)),
            ),
            profiles=(),
        )
    assert error.value.code == "TEST_DEPENDENCY_INVALID"


def test_retired_test_cannot_be_selected_by_profile():
    value = TestCatalog(
        CATALOG_SCHEMA,
        "retired:v1",
        tests=(
            definition("T001", mode=TestMode.ALWAYS),
            definition("T005", mode=TestMode.RETIRED, replacement_test_id="T006"),
            definition("T006", path_suffixes=(".json",)),
        ),
        profiles=(TestProfile("JSON_RECORD_CHANGE:v1", "Old profile", ("T005",)),),
    )
    with pytest.raises(LabValidationError) as error:
        value.select(ChangeFacts(("definition.json",)), profile_ids=("JSON_RECORD_CHANGE:v1",))
    assert error.value.code == "TEST_SELECTION_RETIRED"


def test_change_facts_require_normalized_sorted_paths():
    with pytest.raises(LabValidationError) as error:
        ChangeFacts(("z.py", "a.py"))
    assert error.value.code == "TEST_FACTS_INVALID"


def test_test_ids_are_permanent_shape_not_ordinals_that_can_shift():
    with pytest.raises(LabValidationError) as error:
        definition("1")
    assert error.value.code == "TEST_ID_INVALID"
