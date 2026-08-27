from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_handoff_document_set_exists_and_is_linked_from_readme():
    readme = _read("README.md")
    for path in ("docs/START_HERE.md", "docs/CURRENT_STATE.md"):
        assert (ROOT / path).is_file()
        assert path in readme

    router = _read("docs/START_HERE.md")
    for path in (
        "ARCHITECTURE.md",
        "WORKING_AGREEMENTS.md",
        "DECISIONS.md",
        "PROVING_PROGRAM.md",
        "WORKER_LAB_DESIGN.md",
    ):
        assert (ROOT / "docs" / path).is_file()
        assert path in router


def test_agents_file_routes_without_loading_every_document():
    agents = _read("AGENTS.md")
    assert "docs/START_HERE.md" in agents
    assert "Do not load every document by default" in agents
    assert "Historical evidence and prior results do not grant current authority" in agents


def test_current_state_contains_resume_and_maintenance_boundaries():
    current = _read("docs/CURRENT_STATE.md")
    assert "## Exact repository state" in current
    assert "## Proven capabilities" in current
    assert "## What it cannot yet do reliably" in current
    assert "## Immediate next recommendation" in current
    assert "## New-chat handoff prompt" in current


def test_start_here_defines_authority_freshness_and_history_rules():
    router = _read("docs/START_HERE.md")
    assert "## Authority order" in router
    assert "## Task routing" in router
    assert "## Current versus historical material" in router
    assert "## Freshness rules" in router
    assert "never read all history during routine startup" in router
    assert "Stop and resolve any conflict or stale identity" in router


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


def test_worker_lab_design_preserves_three_repository_and_judge_boundaries():
    design = _read("docs/WORKER_LAB_DESIGN.md")
    assert "durable third repository" in design
    assert "autonomous-worker-framework" in design
    assert "advanced-mine-asset-inspection" in design
    assert "must not copy framework security logic or Mine Tracker product source" in design
    assert "expected evaluator behavior cannot be changed by the worker" in design
    assert "Track A — Mine Tracker completion" in design
    assert "Track B — Worker Lab and proving" in design
