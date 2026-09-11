from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path.cwd()
TESTS = ROOT / 'components/worker-lab/tests'


def remove_functions(path: Path, names: set[str]) -> None:
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    ranges = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            start = min([node.lineno, *[d.lineno for d in node.decorator_list]])
            ranges.append((start, node.end_lineno))
    for start, end in sorted(ranges, reverse=True):
        del lines[start - 1:end]
    path.write_text(''.join(lines), encoding='utf-8')


# The old application-service suite is V2-shaped; current service behavior is covered by
# test_application_service_v3 plus dedicated CLI/backup/workspace/model suites.
old_service = TESTS / 'test_application_service.py'
if old_service.exists():
    old_service.unlink()

# The Windows adapter-runner was deleted. Keep current custody coverage in test_process_custody;
# retain one direct Git workspace evidence test here.
windows = TESTS / 'test_windows_job.py'
windows.write_text('''import subprocess\nfrom pathlib import Path\n\nfrom worker_lab.windows_job import inspect_launch_workspace\n\n\ndef _git(repo: Path, *args: str) -> str:\n    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()\n\n\ndef test_launch_workspace_inspector_seals_exact_clean_git_root(tmp_path):\n    workspace = (tmp_path / "workspace").resolve()\n    workspace.mkdir()\n    (workspace / "README.md").write_text("fixture\\n", encoding="utf-8")\n    _git(workspace, "init")\n    _git(workspace, "config", "core.autocrlf", "false")\n    _git(workspace, "config", "user.email", "fixture@example.com")\n    _git(workspace, "config", "user.name", "Fixture")\n    _git(workspace, "add", ".")\n    _git(workspace, "commit", "-m", "fixture")\n    _git(workspace, "checkout", "--detach")\n    evidence = inspect_launch_workspace(workspace)\n    assert evidence.workspace_path == workspace\n    assert evidence.observed_head == _git(workspace, "rev-parse", "HEAD")\n    assert evidence.status == ""\n    assert evidence.content_digest.startswith("sha256:")\n''', encoding='utf-8')

# CLI keeps current operations and the reusable authority fixture; remove synthetic command coverage.
cli = TESTS / 'test_cli.py'
ctext = cli.read_text(encoding='utf-8')
ctext = ctext.replace('from worker_lab.operator_control import ONE_TIME_CONFIRMATION\n', '')
remove_functions(cli, {'test_synthetic_operator_command_passes_explicit_one_time_authority'})
ctext = cli.read_text(encoding='utf-8')
ctext = ctext.replace('"worker-lab-installation-doctor:v1"', '"worker-lab-installation-doctor:v2"')
cli.write_text(ctext, encoding='utf-8')

# Operator control now exposes only portable-installation inspection and controller validation.
operator = TESTS / 'test_operator_control.py'
operator.write_text('''import json\n\nimport pytest\n\nfrom worker_lab.errors import LabValidationError\nfrom worker_lab.operator_control import inspect_installation, validate_controller_identity\n\n\ndef test_doctor_verifies_portable_identity_without_enabling_execution():\n    manifest, report = inspect_installation()\n    value = json.loads(report.to_json())\n    assert value["schema_version"] == "worker-lab-installation-doctor:v2"\n    assert value["installation_id"] == manifest["installation_id"]\n    assert value["execution_authority"] == "DISABLED"\n    assert value["execution_ready"] is False\n    assert value["component_digests"]["worker-lab"] == manifest["components"]["worker-lab"]["digest"]\n    assert value["component_digests"]["autonomous-worker-framework"] == manifest["components"]["autonomous-worker-framework"]["digest"]\n\n\ndef test_controller_identity_is_strict_and_provider_neutral():\n    assert validate_controller_identity("trusted-controller") == "trusted-controller"\n    for invalid in ("", "a", "bad controller", "../controller"):\n        with pytest.raises(LabValidationError) as error:\n            validate_controller_identity(invalid)\n        assert error.value.code == "OPERATOR_CONTROLLER_INVALID"\n''', encoding='utf-8')

# V3 tests no longer import historical metadata-only qualification identities.
for name in ('test_dispatch_client.py', 'test_integration_v3.py'):
    path = TESTS / name
    text = path.read_text(encoding='utf-8')
    text = text.replace('''from worker_lab.provider_qualification import (\n    QUALIFICATION_SCHEMA,\n    PYDANTIC_AI_OLLAMA_V1,\n    HostProviderQualification,\n)\n''', '')
    path.write_text(text, encoding='utf-8')

binding = TESTS / 'test_provider_binding.py'
btext = binding.read_text(encoding='utf-8')
btext = btext.replace('''from worker_lab.provider_qualification import (\n    QUALIFICATION_SCHEMA,\n    PYDANTIC_AI_OLLAMA_V1,\n    HostProviderQualification,\n)\n''', 'from worker_lab.provider_qualification import PYDANTIC_AI_OLLAMA_V1\n')
binding.write_text(btext, encoding='utf-8')

# Provider qualification retains only current installation-observation + controlled capability tests.
qualification = TESTS / 'test_provider_qualification.py'
remove_functions(qualification, {
    'test_host_qualification_uses_metadata_only_and_never_chat',
    'test_qualification_rejects_non_loopback_or_enabled_authority',
    'test_qualification_rejects_missing_tools_or_insufficient_context',
    'test_qualification_record_cannot_claim_execution_readiness',
})
qtext = qualification.read_text(encoding='utf-8')
qtext = qtext.replace('    HostProviderQualification,\n    inspect_host_provider,\n', '')
qtext = qtext.replace('from worker_lab.runtime_selection import CODING_WORKER_V1\n', 'from worker_lab.runtime_selection import CODING_WORKER_V2\n')
qtext = qtext.replace('CODING_WORKER_V1.profile_id', 'CODING_WORKER_V2.profile_id')
qtext = qtext.replace('CODING_WORKER_V1.digest()', 'CODING_WORKER_V2.digest()')
qualification.write_text(qtext, encoding='utf-8')

# Runtime selection is now V3-only.
runtime = TESTS / 'test_runtime_selection_v3.py'
runtime.write_text('''import pytest\n\nfrom worker_lab.errors import LabValidationError\nfrom worker_lab.runtime_selection import CODING_WORKER_V2, resolve_runtime_identity, selected_runtime_requirement_v3\n\n\ndef test_v3_requirement_is_provider_neutral_and_current():\n    requirement = selected_runtime_requirement_v3()\n    assert requirement is CODING_WORKER_V2\n    assert requirement.profile_id == "coding-worker:v2"\n    assert requirement.provider_binding_required is True\n    assert set(requirement.to_dict()) == {\n        "schema_version", "requirement_id", "requirement_version", "capability",\n        "profile_id", "timeout_seconds", "provider_binding_required",\n    }\n    assert "model" not in requirement.to_dict()\n    assert "reasoning" not in requirement.to_dict()\n    assert resolve_runtime_identity(requirement.profile_id, requirement.digest()) is requirement\n\n\ndef test_v3_digest_cannot_be_substituted():\n    with pytest.raises(LabValidationError) as error:\n        resolve_runtime_identity(CODING_WORKER_V2.profile_id, "sha256:" + "a" * 64)\n    assert error.value.code == "INTEGRATION_RUNTIME_INVALID"\n''', encoding='utf-8')

# Attempt lifecycle/store retain generic state behavior; old V2 invocation-binding tests are removed
# because current binding is covered by InvocationStoreV3/application-service V3 tests.
lifecycle = TESTS / 'test_lifecycle.py'
remove_functions(lifecycle, {'test_running_binding_revalidates_exact_authorized_invocation'})
ltext = lifecycle.read_text(encoding='utf-8')
ltext = ltext.replace('from worker_lab.integration import InvocationRecord, InvocationState, transition_invocation\n', '')
ltext = ltext.replace('from worker_lab.lifecycle import bind_authorized_invocation, transition_attempt\n', 'from worker_lab.lifecycle import transition_attempt\n')
lifecycle.write_text(ltext, encoding='utf-8')

attempt_store = TESTS / 'test_attempt_store.py'
remove_functions(attempt_store, {'test_running_binding_reloads_exact_authorized_invocation'})
atext = attempt_store.read_text(encoding='utf-8')
atext = atext.replace('from worker_lab.integration import InvocationRecord, InvocationState, transition_invocation\n', '')
atext = atext.replace('from worker_lab.invocation_store import InvocationStore\n', '')
atext = atext.replace('from tests.test_integration import record\n', '')
attempt_store.write_text(atext, encoding='utf-8')

print('Worker Lab tests migrated to Task 7 current contracts')
