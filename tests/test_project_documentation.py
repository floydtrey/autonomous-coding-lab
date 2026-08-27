from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_handoff_document_set_exists_and_is_linked_from_readme():
    readme = _read("README.md")
    for path in (
        "docs/CURRENT_STATE.md",
        "docs/ARCHITECTURE.md",
        "docs/WORKING_AGREEMENTS.md",
        "docs/DECISIONS.md",
        "docs/PROVING_PROGRAM.md",
    ):
        assert (ROOT / path).is_file()
        assert path in readme


def test_current_state_contains_resume_and_maintenance_boundaries():
    current = _read("docs/CURRENT_STATE.md")
    assert "## Exact repository state" in current
    assert "## Proven capabilities" in current
    assert "## What it cannot yet do reliably" in current
    assert "## Immediate next recommendation" in current
    assert "## New-chat handoff prompt" in current


def test_architecture_and_decisions_preserve_security_boundary_language():
    combined = (_read("docs/ARCHITECTURE.md") + _read("docs/DECISIONS.md")).lower()
    for requirement in (
        "chatgpt-managed",
        "read-only",
        "workspace-write",
        "one-time exact-head",
        "fail closed",
        "openai_api_key",
        "codex_api_key",
    ):
        assert requirement in combined


def test_working_agreements_require_current_state_maintenance():
    agreements = _read("docs/WORKING_AGREEMENTS.md")
    assert "`docs/CURRENT_STATE.md` is the handoff source of truth" in agreements
    assert "Stop at the first" in agreements
    assert "mix framework changes with Mine Tracker product changes" in agreements


def test_proving_program_defines_objective_mine_tracker_graduation():
    program = _read("docs/PROVING_PROGRAM.md")
    assert "## Graduation gates for Mine Tracker product work" in program
    assert "at least two disposable applications" in program
    assert "at least six bounded implementation tasks" in program
    assert "backup and rollback" in program.lower()
    assert "Standalone Vera" in program
    assert "Local OCR Document Library" in program
