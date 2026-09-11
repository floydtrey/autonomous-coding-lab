from pathlib import Path

root = Path.cwd()
provider = root / 'components/worker-lab/worker_lab/provider_qualification.py'
text = provider.read_text(encoding='utf-8')
text = text.replace('@dataclass(frozen=True)\n\n\nHttpJson =', 'HttpJson =')
provider.write_text(text, encoding='utf-8')

integration = root / 'components/worker-lab/worker_lab/integration_v3.py'
text = integration.read_text(encoding='utf-8')
text = text.replace('"openai_api_key", "codex_api_key", "github_token", "gh_token",', '"openai_api_key", "provider_api_key", "github_token", "gh_token",')
integration.write_text(text, encoding='utf-8')

# Shared provider-neutral fixtures for retained framework contracts.
fixture = root / 'components/autonomous-worker-framework/tests/current_test_fixtures.py'
fixture.write_text('''from __future__ import annotations\n\nfrom pathlib import Path\n\nfrom tools.consumer_profile import ConsumerProfile, PROFILE_VERSION, ValidationCommand\nfrom tools.repository_state import candidate_content_digest, changed_paths, repository_head\nfrom tools.worker_result import (\n    BoundaryResult, CONTRACT_VERSION, ValidationResult, ValidationStage, WorkerResult, WorkerStatus,\n)\n\nGENERIC_PROFILE = ConsumerProfile(\n    version=PROFILE_VERSION,\n    consumer="bounded-test-consumer",\n    authority_paths=("docs/authority.md",),\n    protected_prefixes=(".git/", ".github/", "protected/"),\n    protected_exact=("policy.lock",),\n    product_invariants=("A worker candidate is evidence, not authority.",),\n    full_validation=(\n        ValidationCommand("Run tests", ("python", "-m", "pytest", "-q"), 120),\n    ),\n)\n\n\ndef ready_worker_result(repo: Path) -> WorkerResult:\n    paths = tuple(changed_paths(repo, repository_head(repo)))\n    # changed_paths compares against HEAD, which is exactly the candidate base.\n    return WorkerResult(\n        contract_version=CONTRACT_VERSION,\n        task_id="bounded-fixture",\n        consumer=GENERIC_PROFILE.consumer,\n        task_contract_digest="sha256:" + "1" * 64,\n        base_sha=repository_head(repo),\n        candidate_sha=None,\n        candidate_content_digest=candidate_content_digest(repo, paths),\n        workspace_state="dirty-candidate",\n        changed_paths=paths,\n        patch_boundary=BoundaryResult("pass"),\n        quick_validation=ValidationResult("pass", (ValidationStage("quick", "pass"),)),\n        full_validation=ValidationResult("pass", (ValidationStage("full", "pass"),)),\n        worker=WorkerStatus("pass"),\n        first_failure=None,\n        ready_for_repository_handoff=True,\n    )\n''', encoding='utf-8')

# Context/code-task tests use only the test-local generic profile.
for name in ('test_consumer_profile.py', 'test_code_task.py', 'test_worker_runtime_seam.py'):
    path = root / 'components/autonomous-worker-framework/tests' / name
    text = path.read_text(encoding='utf-8')
    text = text.replace('MINE_TRACKER_PROFILE, ', '')
    text = text.replace('    MINE_TRACKER_PROFILE,\n', '')
    if 'from current_test_fixtures import GENERIC_PROFILE' not in text:
        insert = text.find('\n\n', text.find('from tools.'))
        # Put the test fixture import after the import block using a safe explicit anchor.
        if name == 'test_consumer_profile.py':
            anchor = 'from tools.code_task import run_code_task\n'
        elif name == 'test_code_task.py':
            anchor = 'from tools.worker_runtime import WorkerExecution\n'
        else:
            anchor = 'from tools.worker_runtime import PROVIDER_QUALIFIED, WorkerExecution, WorkerRequest\n'
        text = text.replace(anchor, anchor + 'from current_test_fixtures import GENERIC_PROFILE\n')
    text = text.replace('MINE_TRACKER_PROFILE', 'GENERIC_PROFILE')
    text = text.replace('tmp_path / "mine-tracker"', 'tmp_path / "consumer"')
    text = text.replace('"MT-TEST-1"', '"BOUNDED-TEST-1"')
    if name == 'test_consumer_profile.py':
        text = text.replace('def test_mine_tracker_profile_is_deterministic_and_uses_current_ci_commands():', 'def test_generic_profile_is_deterministic_and_has_validation():')
        old = '''    assert [item.argv for item in GENERIC_PROFILE.full_validation] == [\n        ("python", "-m", "compileall", "-q", "app", "tests", "tools", "run_app.py"),\n        ("python", "-m", "pytest", "-q"),\n        ("node", "--check", "web/app.js"),\n        ("node", "--check", "web/lite_ui.js"),\n    ]\n'''
        text = text.replace(old, '    assert GENERIC_PROFILE.full_validation\n')
        text = text.replace('''        ".github/workflows/ci.yml",\n        "data/mine_tracker.db",\n        "docs/governance/MINE_TRACKER_CURRENT_BASELINE.md",\n        "tests/test_autonomy_controller.py",\n        "tools/autonomy_controller.py",\n''', '''        ".github/workflows/ci.yml",\n        "protected/state.db",\n        "policy.lock",\n''')
    path.write_text(text, encoding='utf-8')

# Handoff/publication tests construct current WorkerResult evidence directly.
for name in ('test_repository_handoff.py', 'test_local_git_publisher.py'):
    path = root / 'components/autonomous-worker-framework/tests' / name
    text = path.read_text(encoding='utf-8')
    text = text.replace('from tools.local_worker_harness import FIXTURE_TASK_VERSION, FixtureTask, run_fixture_job\n', 'from current_test_fixtures import ready_worker_result\n')
    start = text.index('def _candidate(tmp_path: Path):')
    end = text.index('\n\ndef test_', start)
    helper = '''def _candidate(tmp_path: Path):\n    repo = tmp_path / "consumer"\n    repo.mkdir()\n    _git(repo, "init")\n    _git(repo, "config", "user.email", "fixture@example.com")\n    _git(repo, "config", "user.name", "Fixture")\n    (repo / "candidate").mkdir()\n    candidate = repo / "candidate" / "fixture_state.txt"\n    candidate.write_bytes(b"STATE=A\\n")\n    _git(repo, "add", ".")\n    _git(repo, "commit", "-m", "fixture baseline")\n    candidate.write_bytes(b"STATE=B\\n")\n    return repo, ready_worker_result(repo)\n'''
    text = text[:start] + helper + text[end:]
    text = text.replace('repo / "autonomy_smoke" / "fixture_state.txt"', 'repo / "candidate" / "fixture_state.txt"')
    path.write_text(text, encoding='utf-8')
