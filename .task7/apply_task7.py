from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path.cwd()


def remove_file(rel: str) -> None:
    path = ROOT / rel
    if path.exists():
        path.unlink()


def remove_nodes(path: Path, *, top_level=(), class_methods: dict[str, set[str]] | None = None) -> None:
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text)
    ranges: list[tuple[int, int]] = []
    tops = set(top_level)
    class_methods = class_methods or {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in tops:
            ranges.append((node.lineno, node.end_lineno))
        if isinstance(node, ast.ClassDef) and node.name in class_methods:
            wanted = class_methods[node.name]
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name in wanted:
                    ranges.append((child.lineno, child.end_lineno))
    lines = text.splitlines(keepends=True)
    for start, end in sorted(ranges, reverse=True):
        del lines[start - 1:end]
    path.write_text(''.join(lines), encoding='utf-8')


# Obsolete production/configuration and their dedicated legacy tests.
for rel in (
    'components/autonomous-worker-framework/tools/codex_runtime.py',
    'components/autonomous-worker-framework/tools/context_probe.py',
    'components/autonomous-worker-framework/tools/local_worker_harness.py',
    'components/autonomous-worker-framework/tools/monorepo_identity.py',
    'components/autonomous-worker-framework/tools/task_contract.py',
    'components/autonomous-worker-framework/tools/worker_fixture_validator.py',
    'components/autonomous-worker-framework/tools/worker_lab_adapter.py',
    'components/autonomous-worker-framework/tools/workspace_write_adapter.py',
    'components/autonomous-worker-framework/tests/test_codex_runtime.py',
    'components/autonomous-worker-framework/tests/test_context_probe.py',
    'components/autonomous-worker-framework/tests/test_local_worker_harness.py',
    'components/autonomous-worker-framework/tests/test_monorepo_identity.py',
    'components/autonomous-worker-framework/tests/test_task_contract.py',
    'components/autonomous-worker-framework/tests/test_worker_fixture_validator.py',
    'components/autonomous-worker-framework/tests/test_worker_lab_adapter.py',
    'components/autonomous-worker-framework/tests/test_controller_task_packet.py',
    'components/worker-lab/worker_lab/framework_adapter.py',
    'components/worker-lab/worker_lab/framework_client.py',
    'components/worker-lab/worker_lab/installation_manifest.py',
    'components/worker-lab/worker_lab/integration.py',
    'components/worker-lab/worker_lab/invocation_store.py',
    'components/worker-lab/worker_lab/read_only_evidence.py',
    'components/worker-lab/worker_lab/synthetic_read_only.py',
    'components/worker-lab/tests/test_framework_adapter.py',
    'components/worker-lab/tests/test_framework_client.py',
    'components/worker-lab/tests/test_integration.py',
    'components/worker-lab/tests/test_invocation_store.py',
    'components/worker-lab/tests/test_read_only_evidence.py',
    'components/worker-lab/tests/test_runtime_selection.py',
    'components/worker-lab/tests/test_synthetic_read_only.py',
    'config/installation-manifest.json',
    'config/monorepo-identity.json',
    # Obsolete commissioning proof bundle with a hard-coded MineTrackerWorker repository.
    'components/worker-lab/curricula/catalogs/phase4-record-normalizer-v1.json',
    'components/worker-lab/curricula/contexts/phase4-record-normalizer-v1/v1.json',
    'components/worker-lab/curricula/curricula/phase4-record-normalizer.json',
    'components/worker-lab/curricula/exercises/phase4-record-normalizer-v1/v1.json',
    # Superseded commissioning handoff/workplan documents.
    'docs/VS_CODE_HANDOFF.md',
    'docs/WORKPLAN.md',
):
    remove_file(rel)

# Provider-neutral runtime requirement only.
runtime_selection = ROOT / 'components/worker-lab/worker_lab/runtime_selection.py'
runtime_selection.write_text('''from __future__ import annotations\n\nfrom dataclasses import asdict, dataclass\nfrom typing import Any\n\nfrom .canonical import canonical_digest\nfrom .errors import LabValidationError\n\n\nRUNTIME_REQUIREMENT_SCHEMA_V2 = "worker-lab-runtime-requirement:v2"\n\n\n@dataclass(frozen=True)\nclass RuntimeRequirementV2:\n    """Provider-neutral protected capability requirement for Invocation V3."""\n\n    schema_version: str\n    requirement_id: str\n    requirement_version: int\n    capability: str\n    profile_id: str\n    timeout_seconds: int\n    provider_binding_required: bool\n\n    def to_dict(self) -> dict[str, Any]:\n        return asdict(self)\n\n    def digest(self) -> str:\n        return canonical_digest(self.to_dict())\n\n\nCODING_WORKER_V2 = RuntimeRequirementV2(\n    schema_version=RUNTIME_REQUIREMENT_SCHEMA_V2,\n    requirement_id="coding-worker",\n    requirement_version=2,\n    capability="bounded-code-task",\n    profile_id="coding-worker:v2",\n    timeout_seconds=900,\n    provider_binding_required=True,\n)\n\nPROTECTED_RUNTIME_REQUIREMENTS_V3 = (CODING_WORKER_V2,)\n\n\ndef selected_runtime_requirement_v3() -> RuntimeRequirementV2:\n    return CODING_WORKER_V2\n\n\ndef resolve_runtime_identity(profile_id: Any, requirement_digest: Any) -> RuntimeRequirementV2:\n    for requirement in PROTECTED_RUNTIME_REQUIREMENTS_V3:\n        if profile_id == requirement.profile_id and requirement_digest == requirement.digest():\n            return requirement\n    raise LabValidationError(\n        "INTEGRATION_RUNTIME_INVALID",\n        "runtime identity does not resolve to a protected Worker Lab V3 requirement",\n    )\n''', encoding='utf-8')

# Remove Mine Tracker as a production consumer profile. Profiles remain explicit task data.
consumer = ROOT / 'components/autonomous-worker-framework/tools/consumer_profile.py'
remove_nodes(consumer, top_level=('MINE_TRACKER_PROFILE',))  # assignment is not AST class/function; fallback below
ctext = consumer.read_text(encoding='utf-8')
start = ctext.find('\nMINE_TRACKER_PROFILE = ConsumerProfile(')
if start >= 0:
    marker = '\n\ndef build_context_packet('
    end = ctext.index(marker, start)
    ctext = ctext[:start] + marker + ctext[end + len(marker):]
consumer.write_text(ctext, encoding='utf-8')

# Current qualification: remove metadata-only HostProviderQualification and bind candidate to V3 requirement.
provider = ROOT / 'components/worker-lab/worker_lab/provider_qualification.py'
remove_nodes(provider, top_level=('HostProviderQualification', 'inspect_host_provider', '_validate_qualification'))
ptext = provider.read_text(encoding='utf-8')
ptext = ptext.replace('from .runtime_selection import CODING_WORKER_V1, selected_runtime_requirement_v3', 'from .runtime_selection import CODING_WORKER_V2, selected_runtime_requirement_v3')
ptext = re.sub(r'QUALIFICATION_SCHEMA = .*?\nQUALIFICATION_IDENTITY_SCHEMA = .*?\n', '', ptext)
ptext = ptext.replace('runtime_requirement_profile_id=CODING_WORKER_V1.profile_id,', 'runtime_requirement_profile_id=CODING_WORKER_V2.profile_id,')
ptext = ptext.replace('runtime_requirement_digest=CODING_WORKER_V1.digest(),', 'runtime_requirement_digest=CODING_WORKER_V2.digest(),')
# Observation-only command entry point; never performs a capability probe.
main_start = ptext.find('\ndef main(argv: list[str] | None = None) -> int:')
if main_start >= 0:
    ptext = ptext[:main_start] + '''\ndef main(argv: list[str] | None = None) -> int:\n    parser = argparse.ArgumentParser(\n        description="Inspect one protected ACL provider installation without capability execution"\n    )\n    parser.add_argument("--model", required=True)\n    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE_URL)\n    parser.add_argument("--ollama-executable", default="ollama")\n    args = parser.parse_args(argv)\n    repository_root = Path(__file__).resolve().parents[3]\n    try:\n        report = inspect_provider_installation(\n            model=args.model,\n            repository_root=repository_root,\n            base_url=args.base_url,\n            executable_name=args.ollama_executable,\n        )\n    except LabValidationError as exc:\n        print(f"ERROR {exc.code}: {exc}", file=sys.stderr)\n        return 1\n    print(canonical_json({**report.to_dict(), "observation_digest": report.digest()}))\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'''
provider.write_text(ptext, encoding='utf-8')

binding = ROOT / 'components/worker-lab/worker_lab/provider_binding.py'
btext = binding.read_text(encoding='utf-8').replace('    CODING_WORKER_V1,\n', '')
binding.write_text(btext, encoding='utf-8')

# V3-only lifecycle binding.
lifecycle = ROOT / 'components/worker-lab/worker_lab/lifecycle.py'
ltext = lifecycle.read_text(encoding='utf-8')
ltext = ltext.replace('from .integration import InvocationRecord, InvocationState', 'from .integration_v3 import InvocationRecordV3, InvocationState')
ltext = ltext.replace('    invocation: InvocationRecord,', '    invocation: InvocationRecordV3,')
ltext = ltext.replace('        invocation.starting_commit == attempt.starting_commit,', '        invocation.source_state is not None,\n        invocation.source_state is not None and invocation.source_state.base_commit == attempt.starting_commit,')
lifecycle.write_text(ltext, encoding='utf-8')

attempt_store = ROOT / 'components/worker-lab/worker_lab/attempt_store.py'
atext = attempt_store.read_text(encoding='utf-8')
atext = atext.replace('        from .integration import InvocationState', '        from .integration_v3 import InvocationState')
attempt_store.write_text(atext, encoding='utf-8')

# Current record loading is V3-only; historical V2 state is no longer active-tree input.
service_runtime = ROOT / 'components/worker-lab/worker_lab/service_runtime_v3.py'
sr = service_runtime.read_text(encoding='utf-8')
sr = re.sub(
    r'def load_invocation_record\(value: Any\):\n(?:    .*\n)+?\n\ndef load_result_record\(value: Any\):\n(?:    .*\n)+?\n\n',
    'def load_invocation_record(value: Any) -> InvocationRecordV3:\n    return InvocationRecordV3.from_mapping(value)\n\n\ndef load_result_record(value: Any) -> ResultRecordV3:\n    return ResultRecordV3.from_mapping(value)\n\n\n',
    sr,
)
service_runtime.write_text(sr, encoding='utf-8')

# Remove the old V2 adapter runner but retain Windows custody backend and workspace evidence.
windows_job = ROOT / 'components/worker-lab/worker_lab/windows_job.py'
remove_nodes(windows_job, top_level=('WindowsJobAdapterRunner', '_create_job', '_active_process_count', '_wait_for_zero_active', '_drain_bounded', '_utc_now'))
wtext = windows_job.read_text(encoding='utf-8')
wtext = wtext.replace('from .integration import InvocationRecord\n', '')
wtext = wtext.replace('import threading\n', '').replace('import time\n', '')
wtext = wtext.replace('from datetime import datetime, timezone\n', '')
wtext = wtext.replace('from typing import BinaryIO, Callable\n', 'from typing import Callable\n')
windows_job.write_text(wtext, encoding='utf-8')

# Portable-manifest doctor replaces acl-installation-manifest:v2/Codex activation evidence.
operator = ROOT / 'components/worker-lab/worker_lab/operator_control.py'
operator.write_text('''from __future__ import annotations\n\nimport hashlib\nimport json\nimport re\nfrom dataclasses import dataclass\nfrom pathlib import Path\nfrom typing import Any, Mapping\n\nfrom .canonical import canonical_digest, canonical_json\nfrom .errors import LabValidationError\n\n\nDOCTOR_SCHEMA = "worker-lab-installation-doctor:v2"\n_CONTROLLER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")\n\n\n@dataclass(frozen=True)\nclass DoctorReport:\n    installation_id: str\n    manifest_digest: str\n    execution_authority: str\n    participant_states: Mapping[str, str]\n    component_digests: Mapping[str, str]\n    execution_ready: bool\n\n    def to_dict(self) -> dict[str, Any]:\n        return {\n            "schema_version": DOCTOR_SCHEMA,\n            "installation_id": self.installation_id,\n            "manifest_digest": self.manifest_digest,\n            "execution_authority": self.execution_authority,\n            "participant_states": dict(sorted(self.participant_states.items())),\n            "component_digests": dict(sorted(self.component_digests.items())),\n            "execution_ready": self.execution_ready,\n        }\n\n    def to_json(self) -> str:\n        return canonical_json(self.to_dict())\n\n\ndef inspect_installation(path: Path | None = None) -> tuple[Mapping[str, Any], DoctorReport]:\n    repository_root = Path(__file__).resolve().parents[3]\n    manifest_path = repository_root / "config" / "portable-installation-manifest.json" if path is None else path\n    if manifest_path.is_dir():\n        manifest_path = manifest_path / "config" / "portable-installation-manifest.json"\n    try:\n        raw = manifest_path.read_bytes()\n        value = json.loads(raw.decode("utf-8"))\n    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:\n        raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable installation manifest is unavailable") from exc\n    if not isinstance(value, dict) or value.get("schema_version") != "acl-portable-installation-manifest:v1":\n        raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable installation manifest identity differs")\n    policy = value.get("activation_policy")\n    components = value.get("components")\n    if not isinstance(policy, dict) or not isinstance(components, dict):\n        raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable installation manifest fields are invalid")\n    authority = policy.get("execution_authority")\n    participants = policy.get("participants")\n    if authority != "DISABLED" or not isinstance(participants, dict):\n        raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable execution authority differs")\n    observed: dict[str, str] = {}\n    for name, component in components.items():\n        if not isinstance(component, dict):\n            raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable component identity is invalid")\n        root = repository_root / str(component.get("root", ""))\n        production_root = root / str(component.get("production_root", ""))\n        if component.get("scope") == "runtime-dependency-closure":\n            files = component.get("files")\n            if not isinstance(files, list):\n                raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable runtime closure is invalid")\n            paths = [root / item for item in files]\n            relatives = list(files)\n        elif component.get("scope") == "python-production-tree":\n            if not production_root.is_dir():\n                raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable production root is unavailable")\n            paths = sorted(p for p in production_root.rglob("*.py") if "__pycache__" not in p.parts)\n            relatives = [p.relative_to(root).as_posix() for p in paths]\n        else:\n            raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable component scope is invalid")\n        entries = []\n        for relative, file_path in zip(relatives, paths):\n            if not file_path.is_file():\n                raise LabValidationError("OPERATOR_INSTALLATION_INVALID", "portable component file is unavailable")\n            entries.append({"path": relative, "sha256": _bytes_digest(file_path.read_bytes())})\n        digest = canonical_digest(entries)\n        if digest != component.get("digest"):\n            raise LabValidationError("OPERATOR_INSTALLATION_INVALID", f"{name} installed bytes differ")\n        observed[name] = digest\n    report = DoctorReport(\n        installation_id=str(value.get("installation_id")),\n        manifest_digest=_bytes_digest(raw),\n        execution_authority=authority,\n        participant_states={str(k): str(v) for k, v in participants.items()},\n        component_digests=observed,\n        execution_ready=False,\n    )\n    return value, report\n\n\ndef validate_controller_identity(value: Any) -> str:\n    if not isinstance(value, str) or not _CONTROLLER_RE.fullmatch(value):\n        raise LabValidationError("OPERATOR_CONTROLLER_INVALID", "controller identity is invalid")\n    return value\n\n\ndef _bytes_digest(value: bytes) -> str:\n    return "sha256:" + hashlib.sha256(value).hexdigest()\n''', encoding='utf-8')

# CLI: remove synthetic commissioning commands and handlers.
cli = ROOT / 'components/worker-lab/worker_lab/cli.py'
remove_nodes(cli, top_level=('_synthetic_read_only', '_recover_synthetic_read_only'))
clitext = cli.read_text(encoding='utf-8')
clitext = clitext.replace('from .operator_control import ONE_TIME_CONFIRMATION, inspect_installation', 'from .operator_control import inspect_installation')
clitext = re.sub(r'    command = commands\.add_parser\("synthetic-read-only"\).*?    command\.set_defaults\(handler=_recover_synthetic_read_only\)\n', '', clitext, flags=re.S)
cli.write_text(clitext, encoding='utf-8')

# Application service: V3-only public path; remove legacy methods/helpers and old imports/injection knobs.
app = ROOT / 'components/worker-lab/worker_lab/application_service.py'
remove_nodes(
    app,
    top_level=(
        '_prompt_bytes','_bytes_digest','_store_prompt','_load_prompt','_require_no_dispatch_artifacts',
        '_execute_read_only_adapter','_execute_workspace_write_adapter','_workspace_write_contract',
        '_run_workspace_write_tests','_verify_workspace_write_candidate_manifest',
        '_validate_recovery_attempt_binding','_validate_dispatch_attempt_binding','_validate_dispatch_definitions',
        '_validate_running_dispatch_binding','_validate_recovery_workspace','_validate_prepared_attempt',
    ),
    class_methods={'WorkerLabApplicationService': {
        '_legacy_review_candidate','_legacy_prepare_invocation','_legacy_authorize_invocation',
        '_legacy_reject_invocation','_legacy_cancel_invocation','_legacy_dispatch_invocation',
        '_legacy_recover_invocation',
    }},
)
apptext = app.read_text(encoding='utf-8')
apptext = apptext.replace('import hashlib\n', '')
apptext = re.sub(r'from \.integration import \(.*?\)\n', '', apptext, flags=re.S)
apptext = re.sub(r'from \.framework_adapter import \(.*?\)\n', '', apptext, flags=re.S)
apptext = re.sub(r'from \.framework_client import \(.*?\)\n', '', apptext, flags=re.S)
apptext = apptext.replace('from .invocation_store import InvocationStore\n', '')
apptext = apptext.replace('from .installation_manifest import require_execution_enabled\n', '')
apptext = re.sub(r'from \.read_only_evidence import \(.*?\)\n', '', apptext, flags=re.S)
apptext = re.sub(r'from \.windows_job import \(.*?\)\n', 'from .windows_job import WindowsJobCustodyBackend, WorkspaceLaunchEvidence\n', apptext, flags=re.S)
apptext = re.sub(r'ReadOnlyAdapter = Callable\[.*?\]\nWorkspaceWriteAdapter = Callable\[.*?\]\n', '', apptext, flags=re.S)
apptext = apptext.replace('CANDIDATE_REVIEW_SCHEMA = "worker-lab-service-candidate-review:v1"\n', '')
apptext = re.sub(r'RECOVERY_CLEANUP_OUTCOME = \(.*?\)\n\n', '', apptext, flags=re.S)
apptext = apptext.replace('_MAX_PROMPT_BYTES = 32_768\n', '')
apptext = apptext.replace('    invocation: InvocationRecord | InvocationRecordV3\n', '    invocation: InvocationRecordV3\n')
apptext = apptext.replace('''        value[\n            "proposal_content_digest"\n            if self.schema_version == CANDIDATE_REVIEW_SCHEMA\n            else "candidate_content_digest"\n        ] = self.proposal_content_digest\n''', '        value["candidate_content_digest"] = self.proposal_content_digest\n')
apptext = apptext.replace('''        if timeline.invocations[0].record.get("schema_version") != INVOCATION_SCHEMA_V3:\n            return self._legacy_review_candidate(attempt_id)\n''', '''        if timeline.invocations[0].record.get("schema_version") != INVOCATION_SCHEMA_V3:\n            raise LabValidationError(\n                "SERVICE_CANDIDATE_IDENTITY_INVALID",\n                "candidate invocation is not a current V3 record",\n            )\n''')
# Remove old adapter constructor parameters/validation/defaults.
apptext = apptext.replace('''        read_only_adapter: ReadOnlyAdapter | None = None,\n        workspace_write_adapter: WorkspaceWriteAdapter | None = None,\n''', '')
apptext = re.sub(r'        if read_only_adapter is not None.*?        if sealed_test_executor is not None', '        if sealed_test_executor is not None', apptext, flags=re.S)
apptext = apptext.replace('''        self._read_only_adapter = read_only_adapter or _execute_read_only_adapter\n        self._workspace_write_adapter = workspace_write_adapter or _execute_workspace_write_adapter\n''', '')
app.write_text(apptext, encoding='utf-8')

# V3 catalog integration tests point at current contracts, not deleted V2 files.
catalog = ROOT / 'components/worker-lab/curricula/catalogs/worker-lab-v3.json'
if catalog.exists():
    value = json.loads(catalog.read_text(encoding='utf-8'))
    for test in value.get('tests', []):
        if test.get('test_id') in {'T016','T022'}:
            test['command'] = ['python','-m','pytest','-q','tests/test_integration_v3.py','tests/test_invocation_store_v3.py','tests/test_application_service_v3.py']
            test['path_prefixes'] = ['worker_lab/integration_v3.py','worker_lab/invocation_store_v3.py','worker_lab/service_runtime_v3.py']
            test['name'] = 'V3 integration identity and acceptance' if test['test_id']=='T016' else 'Exact V3 integration candidate verification'
            test['purpose'] = 'Verify current V3 invocation/result identity, storage, dispatch, and independent candidate acceptance.'
    catalog.write_text(json.dumps(value, indent=2, sort_keys=False) + '\n', encoding='utf-8')

# Existing portable V1 closure is mechanically reduced to current runtime dependencies; Task 8 will redesign the schema.
verifier = ROOT / 'tools/verify_portable_installation.py'
vtext = verifier.read_text(encoding='utf-8')
vtext = re.sub(r'_FRAMEWORK_FILES = \(.*?\n\)\n', '''_FRAMEWORK_FILES = (\n    "tools/code_task.py",\n    "tools/consumer_profile.py",\n    "tools/dispatch_adapter.py",\n    "tools/pydantic_ollama_worker.py",\n    "tools/repository_handoff.py",\n    "tools/repository_state.py",\n    "tools/worker_result.py",\n    "tools/worker_runtime.py",\n)\n''', vtext, flags=re.S)
verifier.write_text(vtext, encoding='utf-8')
manifest = ROOT / 'config/portable-installation-manifest.json'
m = json.loads(manifest.read_text(encoding='utf-8'))
m['components']['autonomous-worker-framework']['files'] = list(eval(re.search(r'_FRAMEWORK_FILES = (\(.*?\n\))', vtext, re.S).group(1)))
manifest.write_text(json.dumps(m, indent=2) + '\n', encoding='utf-8')

print('Task 7 initial cleanup candidate materialized')
