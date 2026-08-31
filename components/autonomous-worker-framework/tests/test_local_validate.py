from tools import local_validate as validator


def test_quick_stages_compile_changed_python(tmp_path, monkeypatch):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    stages = validator.quick_stages(["tools/sample.py"])

    assert len(stages) == 1
    assert stages[0].failure_code == "LOCAL_COMPILE_FAILED"
    assert stages[0].command[-1] == "tools/sample.py"


def test_quick_stages_runs_changed_test(tmp_path, monkeypatch):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_sample.py").write_text(
        "def test_ok():\n    assert True\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    stages = validator.quick_stages(["tests/test_sample.py"])

    assert len(stages) == 2
    assert stages[0].failure_code == "LOCAL_COMPILE_FAILED"
    assert stages[1].failure_code == "LOCAL_FOCUSED_TESTS_FAILED"
    assert stages[1].command[-1] == "tests/test_sample.py"


def test_quick_stages_ignores_non_python_file(tmp_path, monkeypatch):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    monkeypatch.setattr(validator, "ROOT", tmp_path)

    assert validator.quick_stages(["README.md"]) == []


def test_full_stages_compile_then_test():
    stages = validator.full_stages()

    assert [stage.failure_code for stage in stages] == [
        "LOCAL_COMPILE_FAILED",
        "LOCAL_FULL_TESTS_FAILED",
    ]
    assert stages[0].command[-2:] == ("tools", "tests")
    assert stages[1].command[-2:] == ("pytest", "-q")


def test_discover_changed_paths_unions_git_sources(monkeypatch):
    responses = {
        ("diff", "--name-only", "--diff-filter=ACMR", "abc...HEAD"): {"tools/a.py"},
        ("diff", "--name-only", "--diff-filter=ACMR"): {"tests/test_a.py"},
        ("diff", "--cached", "--name-only", "--diff-filter=ACMR"): {"tools/b.py"},
        ("ls-files", "--others", "--exclude-standard"): {"README.md"},
    }

    monkeypatch.setattr(validator, "_git_lines", lambda *args: responses[args])
    monkeypatch.setattr(
        validator,
        "_run_capture",
        lambda command: f"{validator.ROOT}\n"
        if tuple(command) == ("git", "rev-parse", "--show-toplevel")
        else "",
    )

    assert validator.discover_changed_paths("abc") == [
        "README.md",
        "tests/test_a.py",
        "tools/a.py",
        "tools/b.py",
    ]


def test_discover_changed_paths_strips_monorepo_prefix_and_ignores_siblings(
    tmp_path, monkeypatch
):
    component_root = tmp_path / "components" / "autonomous-worker-framework"
    component_root.mkdir(parents=True)
    responses = {
        ("diff", "--name-only", "--diff-filter=ACMR", "abc...HEAD"): {
            "components/autonomous-worker-framework/tools/a.py",
            "components/worker-lab/worker_lab/a.py",
        },
        ("diff", "--name-only", "--diff-filter=ACMR"): {
            r"components\autonomous-worker-framework\tests\test_a.py"
        },
        ("diff", "--cached", "--name-only", "--diff-filter=ACMR"): {
            "docs/CURRENT_STATE.md"
        },
        ("ls-files", "--others", "--exclude-standard"): set(),
    }

    monkeypatch.setattr(validator, "ROOT", component_root)
    monkeypatch.setattr(validator, "_git_lines", lambda *args: responses[args])
    monkeypatch.setattr(
        validator,
        "_run_capture",
        lambda command: f"{tmp_path}\n"
        if tuple(command) == ("git", "rev-parse", "--show-toplevel")
        else "",
    )

    assert validator.discover_changed_paths("abc") == [
        "tests/test_a.py",
        "tools/a.py",
    ]


def test_component_relative_paths_rejects_component_outside_repository(
    tmp_path, monkeypatch
):
    repository_root = tmp_path / "repo"
    component_root = tmp_path / "elsewhere" / "framework"
    repository_root.mkdir()
    component_root.mkdir(parents=True)
    monkeypatch.setattr(validator, "ROOT", component_root)

    try:
        validator._component_relative_paths(
            ["tools/a.py"], repository_root=repository_root
        )
    except validator.ValidationSetupError as exc:
        assert "outside the Git repository root" in str(exc)
    else:
        raise AssertionError("Expected an out-of-repository component root to fail closed")


def test_resolve_base_uses_main(monkeypatch):
    monkeypatch.setattr(
        validator,
        "_run_capture",
        lambda command: "deadbeef\n"
        if tuple(command) == ("git", "merge-base", "HEAD", "main")
        else "",
    )

    assert validator.resolve_base() == "deadbeef"


def test_stage_result_passed_property():
    stage = validator.Stage("x", ("python", "-V"), "FAILED")

    assert validator.StageResult(stage, 0, 0.1).passed is True
    assert validator.StageResult(stage, 1, 0.1).passed is False
