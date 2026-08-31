import json

from tools.inventory_trees import analyze_text, classify_path, language_for, role_for
from tools.plan_repairs import build_plan


def test_path_semantics_are_language_independent():
    assert classify_path(r"C:\repo\file.py") == "absolute_host"
    assert classify_path("$PSScriptRoot", "$PSScriptRoot\\config.json") == "file_relative"
    assert classify_path("", "Path(__file__).resolve().parent") == "file_relative"
    assert classify_path("HEAD:tools/worker_lab_adapter.py") == "git_object_path"
    assert (
        classify_path("", 'f"{head}:tools/worker_lab_adapter.py"')
        == "git_object_path"
    )
    assert classify_path("components/worker-lab/pyproject.toml") == "repo_root_relative"
    assert classify_path("tests/test_x.py") == "component_root_relative"


def test_python_inventory_extracts_structure_and_prefix_signals():
    source = '''
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]

def discover_changed_paths():
    subprocess.run(("git", "diff", "--name-only"))
    return [path for path in ["tests/test_x.py"] if (ROOT / path).is_file()]

def changed_tests(paths):
    return [path for path in paths if path.startswith("tests/")]
'''
    result = analyze_text("tools/local_validate.py", "python", source)
    assert {item["name"] for item in result["structures"]["functions"]} == {
        "discover_changed_paths",
        "changed_tests",
    }
    assert "git_path_output" in result["signals"]
    assert "component_root_join" in result["signals"]
    assert "component_relative_test_selector" in result["signals"]
    assert any(
        item["path_type"] == "file_relative" for item in result["path_references"]
    )


def test_file_classification_keeps_tests_docs_and_configs_separate():
    assert language_for("tests/test_x.py", False) == "python"
    assert role_for("tests/test_x.py", "python") == "test"
    assert role_for("docs/CURRENT_STATE.md", "markdown") == "documentation"
    assert role_for("pyproject.toml", "toml") == "configuration"


def test_repair_plan_requires_an_active_registered_mechanical_finding(tmp_path):
    finding = {
        "finding_id": "AWF-PATH-008",
        "status": "FAIL",
        "repair_class": "MECHANICAL_REPAIR",
        "component": "AWF",
        "file_id": "AWF:tools/local_validate.py",
        "destination_path": "components/autonomous-worker-framework/tools/local_validate.py",
    }
    (tmp_path / "findings.json").write_text(
        json.dumps({"findings": [finding]}), encoding="utf-8"
    )
    for component in ("AWF", "WLAB", "LMB"):
        files = (
            [{"file_id": finding["file_id"], "git_blob": "abc123"}]
            if component == "AWF"
            else []
        )
        (tmp_path / f"{component.lower()}.json").write_text(
            json.dumps({"files": files}), encoding="utf-8"
        )
    plan = build_plan(tmp_path)
    assert plan["change_count"] == 1
    assert plan["changes"][0]["starting_blob"] == "abc123"
    assert plan["changes"][0]["automatic_commit"] is False
