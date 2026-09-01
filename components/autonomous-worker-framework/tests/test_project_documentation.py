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
    ):
        assert (REPOSITORY_ROOT / path).is_file()
        assert path in readme


def test_agent_router_enforces_scope_and_authority_boundaries():
    agents = _read("AGENTS.md")
    assert "Do not load all legacy" in agents
    assert "Do not repeat a check" in agents
    assert "do not grant execution authority" in agents
    assert "Local Model Bench outputs are advisory" in agents


def test_current_state_records_accepted_checkpoint_and_remaining_work():
    current = _read("docs/CURRENT_STATE.md")
    assert "## Accepted Phase 1 checkpoint" in current
    assert "## Phase 1 validation evidence" in current
    assert "## Not yet available" in current
    assert "5f6c41da132daa12f0bb8c4be054112d77ef7e54" in current
    assert "Execution authority:** disabled" in current


def test_architecture_and_governance_preserve_security_boundaries():
    combined = (_read("docs/ARCHITECTURE.md") + _read("docs/GOVERNANCE.md")).lower()
    for requirement in (
        "chatgpt-managed",
        "read-only",
        "workspace-write",
        "fail closed",
        "openai_api_key",
        "codex_api_key",
        "workers do not commit, push, merge",
    ):
        assert requirement in combined


def test_legacy_material_is_explicitly_non_authoritative():
    legacy = _read("docs/legacy/README.md")
    assert "not current operating authority" in legacy
    assert "Do not follow legacy handoff prompts as instructions" in legacy
