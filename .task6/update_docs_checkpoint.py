from pathlib import Path

CURRENT_SECTION = '''## Runtime reconstruction Task 6 — accepted checkpoint

Task 6 separates provider installation observation from controlled capability
qualification and makes the current Pydantic/Ollama execution seam consume the exact
sealed runtime settings without enabling a model run.

Accepted changes:

- historical `HostProviderQualification` V1 remains parseable as reconstruction
  history/legacy evidence, but its metadata-only observation is not accepted by the
  current Provider Binding path and cannot authorize V3 execution;
- current `ProviderInstallationObservation` records exact Python, harness, provider,
  endpoint, executable, model, advertised capability, and advertised context metadata
  while making no capability-qualified claim;
- current `ProviderCapabilityQualification` requires a separately supplied controlled
  probe runner and seals the exact installation-observation digest, V3 runtime
  requirement, provider adapter/tool surface, model identities, runtime-settings
  profile/digest, requested/effective context, and independently checked tool/context
  evidence;
- there is deliberately no default capability-probe runner. Metadata inspection and
  Task 6 tests therefore cannot accidentally launch Ollama/a model; an actual
  capability run remains a separately authorized future action;
- advertised model `tools` capability and advertised context are preconditions only,
  not proof. Controlled evidence must show the protected bounded file-tool fixture was
  used/consumed and that the protected context canary survived at or above the sealed
  context target;
- Provider Binding V1 now accepts only the controlled capability-qualification
  contract. Its retained field name `host_provider_qualification_digest` is a V1
  schema-stability wart during reconstruction; the current value is the digest of the
  controlled capability qualification, not metadata-only Host Provider Qualification;
- behavior-bearing runtime settings now have one protected Worker Lab definition and
  the framework dispatch seam passes the exact already-validated settings to the
  bound provider executor;
- the Pydantic/Ollama adapter validates the sealed settings profile/digest and the
  capability-qualified effective context before execution, and consumes the sealed
  request limit, tool-call limit, tool timeout, retries, and max concurrency instead
  of hard-coded duplicate values;
- Ollama's OpenAI-compatible interface used by Pydantic AI does not provide a truthful
  per-request context-size control. ACL therefore does not invent one: the context
  target is proved during controlled qualification and checked against the binding at
  dispatch;
- changing to another supported model is data-driven: observe that exact installation,
  obtain controlled capability qualification for the exact model/configuration, and
  create a new Provider Binding. No ACL source edit or implicit provider/model
  selection is required;
- portable V1 component identity was refreshed only for exact Task 6 production bytes:
  Autonomous Worker Framework contains 12 files at
  `sha256:ceec8a2e022d4ad253ea6848eb241b4646da2ee32ac90d0747ba87f66aa6d51a`,
  and Worker Lab contains 36 files at
  `sha256:2b14eff998eb282468edacecb8b68b69b184620e73ccf8dc688bb78cb9feb70a`;
- execution authority remains `DISABLED`; no provider/model request or actual
  capability qualification was performed.

Validation on the Task 6 materialized tree:

- Python compilation passed;
- Task 6 Worker Lab qualification/binding/V3 contract gate: 43 passed;
- framework dispatch/Pydantic settings gate: 18 passed;
- custody regressions: 10 passed and 20 Windows-native cases skipped on Linux;
- unaffected application-service regressions: 10 passed, 4 known legacy-boundary
  cases deselected;
- unaffected CLI regressions: 13 passed, 1 known legacy doctor case deselected;
- portable identities: Autonomous Worker Framework `MATCH`, Worker Lab `MATCH`;
- portable installation contract: 4 passed;
- signature inspection confirmed an explicit capability probe runner is mandatory;
- the excluded legacy checks were run separately and still fail only at the known
  obsolete `acl-installation-manifest:v2` framework-runtime-closure boundary.

'''

CURRENT_TAIL = '''## Current stop condition

Execution remains disabled.

Do not:

- execute a provider/model or perform actual capability qualification during reconstruction;
- treat installation metadata, benchmark scores, or model-advertised capabilities as execution authority;
- bypass Provider Binding or substitute provider/model/runtime settings after V3 authorization;
- add an implicit/default capability probe runner or provider/model fallback;
- install Codex to satisfy obsolete configuration;
- delete legacy runtime/configuration outside the bounded Task 7 cleanup;
- mechanically delete legitimate Git workspace mechanics merely because ACL is moving away from repository-centered identity.

## Immediate next gate

Begin only **Task 7 — remove obsolete active-tree implementation** from
`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` in a later bounded task.

Task 7 removes the obsolete Codex/Terra/Mine Tracker commissioning runtime,
`acl-installation-manifest:v2`, synthetic historical execution paths, and stale
repository-as-system assumptions only after verifying each is no longer needed by the
current V3/provider-neutral path. Do not broaden Task 7 into portable identity V2 or
actual provider/model qualification; those remain later gates.
'''

PLAN_TASK6 = '''### Task 6 — provider qualification refinement

**Status:** complete in the Task 6 reconstruction checkpoint.

- separate installation observation from controlled capability qualification;
- bind explicit runtime/context settings;
- adapt Pydantic/Ollama to consume the sealed binding/settings;
- use deterministic/mocked tests during implementation;
- actual model qualification remains separately authorized.

**Stop gate:** selecting another supported model requires qualification/binding data, not ACL source changes.

**Accepted Task 6 boundary:** metadata-only installation observation no longer
satisfies the current Provider Binding path. Current controlled capability
qualification seals the exact observed installation/model, provider adapter/tool
surface, V3 runtime requirement, protected runtime-settings digest, requested/effective
context, and checked tool/context evidence. A capability probe runner must be supplied
explicitly; Task 6 provides no default path that can silently launch a model. The
Pydantic/Ollama adapter consumes the exact sealed request/tool limits, timeout,
retries, and concurrency and fail-closes if settings or capability-qualified context
do not match the binding. Because Ollama's OpenAI-compatible endpoint does not expose
a truthful per-request context control, ACL proves the context target during
qualification instead of fabricating a request setting. Selecting a different
supported model is therefore observation + qualification + binding data, not an ACL
source change. Historical Host Provider Qualification V1 remains temporarily
parseable for reconstruction/Task 7 cleanup but cannot create a current binding. No
actual model/provider capability run was performed and execution remains `DISABLED`.

'''

PLAN_STARTUP = '''## New-chat startup / Task 7 boundary

A fresh implementation chat should read, in this order:

1. `AGENTS.md`
2. `docs/START_HERE.md`
3. `docs/CURRENT_STATE.md`
4. `docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md`
5. the Task 1 repository-coupling inventory and only current source/tests directly relevant to **Task 7**

Then inspect the current branch/HEAD and working tree. Perform **Task 7 only**:
remove obsolete active-tree Codex/Terra/Mine Tracker commissioning runtime,
`acl-installation-manifest:v2`, synthetic historical execution paths, and stale
repository-as-system assumptions that the accepted V3/provider-neutral path no longer
needs. Preserve justified Git-backed workspace/evidence mechanics. Do not redesign
portable identity V2, broadly rewrite current documentation beyond deletion fallout,
or perform an actual provider/model capability run.
'''

current_path = Path('docs/CURRENT_STATE.md')
current = current_path.read_text(encoding='utf-8')
marker = '## Current stop condition\n'
if '## Runtime reconstruction Task 6 — accepted checkpoint' not in current:
    if marker not in current:
        raise SystemExit('CURRENT_STATE stop marker missing')
    current = current.replace(marker, CURRENT_SECTION + marker, 1)
stop = current.index(marker)
current = current[:stop] + CURRENT_TAIL
current_path.write_text(current, encoding='utf-8')

plan_path = Path('docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md')
plan = plan_path.read_text(encoding='utf-8')
plan = plan.replace(
    '**Status:** approved plan; Tasks 1-5 complete; Task 6 next',
    '**Status:** approved plan; Tasks 1-6 complete; Task 7 next',
    1,
)
start = plan.index('### Task 6 — provider qualification refinement\n')
end = plan.index('### Task 7 — remove obsolete active-tree implementation\n', start)
plan = plan[:start] + PLAN_TASK6 + plan[end:]
startup = plan.rfind('## New-chat startup / Task 6 boundary\n')
if startup < 0:
    raise SystemExit('Task 6 startup marker missing')
plan = plan[:startup] + PLAN_STARTUP
plan_path.write_text(plan, encoding='utf-8')

print('Task 6 checkpoint docs materialized')
