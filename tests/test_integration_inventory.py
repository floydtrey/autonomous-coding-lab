from tools.inventory_integration import build_component_delta, structural_delta


def file_record(path, blob, *, imports=None, paths=None, signals=None):
    return {
        "source_path": path,
        "git_blob": blob,
        "path_references": paths or [],
        "signals": signals or [],
        "structures": {
            "imports": imports or [],
            "functions": [],
            "classes": [],
            "calls": [],
            "git_object_lookups": [],
            "environment_variables": [],
        },
        "parse_error": None,
    }


def test_component_delta_classifies_every_source_to_integration_change():
    source = {
        "component": "WLAB",
        "source_commit": "1" * 40,
        "source_tree": "2" * 40,
        "destination_prefix": "components/worker-lab",
        "files": [
            file_record("same.py", "a" * 40),
            file_record("changed.py", "b" * 40),
            file_record("removed.py", "c" * 40),
        ],
    }
    integrated = {
        "component_prefix": "components/worker-lab",
        "component_tree": "3" * 40,
        "files": [
            file_record("same.py", "a" * 40),
            file_record("changed.py", "d" * 40),
            file_record("added.py", "e" * 40),
        ],
    }

    result = build_component_delta(source, integrated)

    assert result["change_counts"] == {
        "UNCHANGED": 1,
        "MODIFIED": 1,
        "ADDED": 1,
        "REMOVED": 1,
    }
    assert [item["status"] for item in result["changes"]] == [
        "ADDED",
        "MODIFIED",
        "REMOVED",
    ]
    assert result["changes"][1]["structural_delta"] == {"content_only": True}


def test_structural_delta_reports_exact_path_import_and_signal_changes():
    source = file_record(
        "worker_lab/framework_adapter.py",
        "a" * 40,
        imports=[{"module": "old", "line": 1}],
        paths=[
            {
                "reference_id": "old-id",
                "line": 4,
                "column": 2,
                "expression": "../framework",
                "literal": "../framework",
                "path_type": "hierarchy_relative",
            }
        ],
        signals=["framework_standalone_pin"],
    )
    integrated = file_record(
        "worker_lab/framework_adapter.py",
        "b" * 40,
        imports=[{"module": "new", "line": 1}],
        paths=[
            {
                "reference_id": "new-id",
                "line": 4,
                "column": 2,
                "expression": "components/autonomous-worker-framework",
                "literal": "components/autonomous-worker-framework",
                "path_type": "repo_root_relative",
            }
        ],
    )

    result = structural_delta(source, integrated)

    assert result["path_references"]["removed"][0]["literal"] == "../framework"
    assert "reference_id" not in result["path_references"]["added"][0]
    assert result["structures"]["imports"] == {
        "added": [{"module": "new", "line": 1}],
        "removed": [{"module": "old", "line": 1}],
    }
    assert result["signals"] == {
        "added": [],
        "removed": ["framework_standalone_pin"],
    }


def test_structural_delta_ignores_line_only_movement():
    source = file_record(
        "module.py",
        "a" * 40,
        imports=[{"module": "same", "line": 1}],
        paths=[
            {
                "reference_id": "source-id",
                "line": 2,
                "column": 4,
                "expression": "tests/test_x.py",
                "literal": "tests/test_x.py",
                "path_type": "component_root_relative",
            }
        ],
    )
    integrated = file_record(
        "module.py",
        "b" * 40,
        imports=[{"module": "same", "line": 20}],
        paths=[
            {
                "reference_id": "integrated-id",
                "line": 30,
                "column": 8,
                "expression": "tests/test_x.py",
                "literal": "tests/test_x.py",
                "path_type": "component_root_relative",
            }
        ],
    )

    assert structural_delta(source, integrated) == {"content_only": True}
