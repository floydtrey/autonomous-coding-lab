import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from worker_lab.errors import LabValidationError
from worker_lab.job_plan import JobPlan

FIXTURE = Path(__file__).parent / "fixtures" / "two-task-job-plan.json"


def fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_two_task_fixture_is_canonical_and_immutable():
    plan = JobPlan.from_mapping(fixture())
    assert plan.task("B").dependencies == ("A",)
    assert JobPlan.from_mapping(json.loads(plan.to_json())) == plan
    with pytest.raises(FrozenInstanceError):
        plan.revision = 2
    with pytest.raises(FrozenInstanceError):
        plan.task("A").budget.max_attempts = 2
    changed = plan.to_dict()
    changed["tasks"][0]["description"] = "Different work"
    assert JobPlan.from_mapping(changed).digest() != plan.digest()
    changed = fixture()
    changed["tasks"].reverse()
    assert JobPlan.from_mapping(changed).digest() == plan.digest()


@pytest.mark.parametrize("mutation", [
    lambda d: d.pop("plan_id"),
    lambda d: d["objective"].update(target_id="C:/repo"),
    lambda d: d.update(revision=True),
    lambda d: d["tasks"][0].pop("task_id"),
    lambda d: d["tasks"][0].update(task_id=""),
    lambda d: d["tasks"][1].update(task_id="A"),
    lambda d: d["tasks"][1].update(dependencies=["missing"]),
    lambda d: d["tasks"][0].update(acceptance_criteria=[]),
    lambda d: d["tasks"][0].update(acceptance_criteria=["looks good"]),
    lambda d: d["tasks"][0]["acceptance_criteria"][0].update(description=" "),
    lambda d: d["tasks"][0]["acceptance_criteria"][0].update(test_ids=[]),
    lambda d: d["tasks"][0]["acceptance_criteria"][0].update(test_ids=["run anything"]),
    lambda d: d["tasks"][0]["authority_ref"].pop("digest"),
    lambda d: d["tasks"][0]["budget"].update(max_attempts=0),
    lambda d: d["tasks"][0].update(required_outputs=[]),
])
def test_bad_plans_reject(mutation):
    value = fixture()
    mutation(value)
    with pytest.raises(LabValidationError):
        JobPlan.from_mapping(value)


@pytest.mark.parametrize("edges, cycle", [
    ({"A": ["A"], "B": []}, "A -> A"),
    ({"A": ["B"], "B": ["A"]}, "A -> B -> A"),
    ({"A": ["B"], "B": ["C"], "C": ["A"]}, "A -> B -> C -> A"),
])
def test_cycles_report_deterministic_path(edges, cycle):
    value = fixture()
    prototype = value["tasks"][0]
    value["tasks"] = [dict(prototype, task_id=key, dependencies=deps) for key, deps in edges.items()]
    for tasks in (value["tasks"], list(reversed(value["tasks"]))):
        value["tasks"] = tasks
        with pytest.raises(LabValidationError) as error:
            JobPlan.from_mapping(value)
        assert error.value.code == "JOB_PLAN_DEPENDENCY_CYCLE"
        assert cycle in error.value.summary


def test_chain_and_shared_dependency_accept():
    value = fixture()
    prototype = value["tasks"][0]
    edges = {"A": ["B"], "B": ["C"], "C": [], "D": ["B", "C"]}
    value["tasks"] = [dict(prototype, task_id=key, dependencies=deps) for key, deps in edges.items()]
    assert len(JobPlan.from_mapping(value).tasks) == 4
