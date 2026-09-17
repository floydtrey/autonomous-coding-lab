from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (REPOSITORY_ROOT / path).read_text(encoding="utf-8")


def test_current_document_set_exists_and_is_linked_from_readme():
    readme = _read("README.md")
    for path in (
        "docs/START_HERE.md",
        "docs/CURRENT_STATE.md",
        "docs/ARCHITECTURE.md",
        "docs/OPERATIONS.md",
        "docs/DEVELOPMENT.md",
        "docs/GOVERNANCE.md",
        "docs/PORTABLE_SOURCE_IDENTITY.md",
    ):
        assert (REPOSITORY_ROOT / path).is_file()
        assert path in readme


def test_agent_router_enforces_current_scope_and_authority_boundaries():
    agents = _read("AGENTS.md")
    assert "Git history is the archive" in agents
    assert "Do not repeat a check" in agents
    assert "do not grant execution authority" in agents
    assert "Local Model Bench outputs are advisory" in agents


def test_current_state_records_reconstruction_authority_and_remaining_work():
    current = _read("docs/CURRENT_STATE.md")
    assert "# Current State" in current
    assert "**Execution authority:** `DISABLED`" in current
    assert "docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md" in current
    assert "Task 9" in current
    assert "no actual provider/model request or real capability qualification occurred during reconstruction" in current


def test_architecture_and_governance_preserve_security_boundaries():
    combined = (_read("docs/ARCHITECTURE.md") + _read("docs/GOVERNANCE.md")).lower()
    for requirement in (
        "read-only",
        "workspace-write",
        "fail closed",
        "provider binding",
        "local activation",
        "workers do not commit, push, merge",
    ):
        assert requirement in combined


def test_no_active_legacy_documentation_tree():
    assert not (REPOSITORY_ROOT / "docs" / "legacy").exists()
    assert not (REPOSITORY_ROOT / "migration" / "inventory").exists()
