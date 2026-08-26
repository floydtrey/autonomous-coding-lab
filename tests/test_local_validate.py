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

    assert validator.discover_changed_paths("abc") == [
        "README.md",
        "tests/test_a.py",
        "tools/a.py",
        "tools/b.py",
    ]


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
