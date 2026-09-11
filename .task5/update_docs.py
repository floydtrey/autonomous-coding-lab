from pathlib import Path

CURRENT_TASK5 = '''## Runtime reconstruction Task 5 — accepted checkpoint

Task 5 migrates the active Worker Lab application-service invocation,
dispatch, recovery, and workspace-write candidate-review path onto Invocation/Result
V3 without enabling a real provider.

Accepted changes:

- current `prepare-invocation` is workspace-write/V3 only and requires an explicit
  logical `target:` identity plus the exact durable Provider Binding ID/digest;
  repository/workspace paths remain backend locators and Git evidence rather than
  ACL target identity;
- the exact canonical Controller Task Packet is the sealed prompt, and authorization
  rechecks both the packet's controller identity and the exact current Provider
  Binding before changing state;
- public dispatch requires an explicitly injected V3 workspace dispatch runner; no
  V2 read-only/Codex shell, provider fallback, provider registry, or implicit model
  selection is reachable through the current service path;
- generic Result V3 acceptance requires exact request/invocation/binding identity,
  complete durable custody with verified workload absence, exact authorized changed
  paths, exact framework test claims, and independently executed sealed tests;
- `git_workspace_evidence.py` independently observes the Git-backed coding workspace
  and supplies capability-specific base/head/path/content/change evidence to generic
  acceptance rather than making repository facts universal ACL identity;
- the full Context Manifest digest still binds all protected source context, while
  Invocation V3 `readable_paths` excludes paths already granted by `writable_paths`;
  writable targets therefore have one explicit authority surface instead of being
  simultaneously classified as read-only context and write scope;
- recovery remains custody-backend-specific and fails closed unless exact controller,
  invocation, absence evidence, and unchanged workspace identity can be proven;
- historical V2 records remain parseable/reviewable during reconstruction, and the
  old private `_legacy_*` service helpers remain only for Task 7 deletion; new public
  invocation/dispatch/recovery operations no longer route through V2;
- the portable V1 Worker Lab production tree now contains 35 files and matches
  `sha256:e4da4781e1afb9dfa068a5e239a7dcb3d478fe918db5fab8e19103ccb1017649`;
- execution authority remains `DISABLED`; no provider/model request was sent.

Validation on the Task 5 materialized tree:

- Python compilation passed;
- V3 foundations plus Task 5 service acceptance: 35 passed;
- unaffected application-service regressions: 10 passed, with four legacy
  installation-status/doctor-boundary tests intentionally excluded;
- unaffected CLI regressions: 13 passed, with the legacy doctor test intentionally
  excluded;
- custody regressions: 10 passed and 20 Windows-native cases skipped on Linux;
- both portable component identities reported `MATCH` and portable contract tests passed 4/4;
- the excluded legacy checks were run separately and confirmed to fail only at the
  already-known obsolete `acl-installation-manifest:v2` framework-runtime-closure
  boundary (`framework runtime closure is incomplete`);
- the Task 5 suite used injected fake runners/custody only and performed no provider
  or model execution.

'''

CURRENT_TAIL = '''## Current stop condition

Execution remains disabled.

Do not:

- execute a provider/model or treat benchmark results as execution authority;
- bypass Provider Binding or substitute provider/model/runtime settings after V3 authorization;
- re-enable the historical V2 read-only/Codex dispatch shell as a fallback;
- install Codex to satisfy obsolete configuration;
- delete legacy runtime/configuration before Task 7;
- mechanically delete legitimate Git workspace mechanics merely because ACL is moving away from repository-centered identity.

## Immediate next gate

Begin only **Task 6 — provider qualification refinement** from
`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` in a later bounded task.

Task 6 must separate installation observation from controlled capability
qualification and adapt the Pydantic/Ollama provider adapter to consume the exact
sealed Provider Binding/runtime settings. Use deterministic/mocked tests during the
implementation. Actual model capability qualification or any model run remains a
separate explicitly authorized action; benchmark evidence may inform later role
assignment but must not bypass ACL qualification/binding contracts.
'''

PLAN_TASK5 = '''### Task 5 — migrate application service and current result acceptance

**Status:** complete in the Task 5 reconstruction checkpoint.

- migrate only the invocation/dispatch/recovery portion of `application_service.py`;
- preserve accepted lifecycle/storage/policy/test behavior;
- separate platform-specific workspace/process evidence from generic result acceptance;
- keep Git-specific workspace evidence behind the coding-workspace boundary instead of treating it as universal system identity.

**Stop gate:** current Worker Lab service path uses only V3/current dispatch contracts.

**Accepted Task 5 boundary:** current public application-service preparation,
authorization, dispatch, recovery, and workspace-write candidate review use
Invocation/Result V3 and the provider-neutral dispatch seam. Preparation requires an
explicit logical target plus the exact durable Provider Binding and exact Controller
Task Packet; authorization rechecks both before transition. Dispatch has no implicit
runner/provider fallback. Candidate acceptance depends on complete durable custody,
independent sealed tests, and independently observed Git workspace evidence rather
than trusting the worker/framework success claim. The Context Manifest continues to
bind all protected source context, while V3 readable scope excludes paths already in
the writable scope so one path is not granted through conflicting authority classes.
Git facts remain coding-workspace evidence, not ACL target identity. Historical V2
records/private helpers remain only as temporary Task 7 deletion debt and are not the
current public dispatch path. No provider/model request was sent and execution
remains `DISABLED`.

'''

PLAN_STARTUP = '''## New-chat startup / Task 6 boundary

A fresh implementation chat should read, in this order:

1. `AGENTS.md`
2. `docs/START_HERE.md`
3. `docs/CURRENT_STATE.md`
4. `docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md`
5. only the current source/tests directly relevant to **Task 6**

Then inspect the current branch/HEAD and working tree. Perform **Task 6 only**:
separate installation observation from controlled provider capability qualification,
bind explicit runtime/context settings, and adapt Pydantic/Ollama to consume the
sealed Provider Binding/settings. Use deterministic or mocked provider behavior while
implementing the contract. Do not perform an actual model capability run without a
separate explicit authorization, delete legacy modules/configuration, redesign
portable identity V2, or broaden the task into benchmark/model-role assignment.
'''

current_path = Path('docs/CURRENT_STATE.md')
current = current_path.read_text(encoding='utf-8')
marker = '## Current stop condition\n'
if '## Runtime reconstruction Task 5 — accepted checkpoint' not in current:
    if marker not in current:
        raise SystemExit('CURRENT_STATE Task 5 marker missing')
    current = current.replace(marker, CURRENT_TASK5 + marker, 1)
else:
    start = current.index('## Runtime reconstruction Task 5 — accepted checkpoint\n')
    end = current.index(marker, start)
    current = current[:start] + CURRENT_TASK5 + current[end:]
old_runtime_selection = '- Runtime Selection V1 at `0ad1b212581fb7b18110b9155763bf49b42df442` protects the historical `coding-worker:v1` capability requirement used by the still-live V2 application seam.'
new_runtime_selection = '- Runtime Selection V1 at `0ad1b212581fb7b18110b9155763bf49b42df442` preserves the historical `coding-worker:v1` qualification identity; the current public application-service execution path is Invocation/Result V3 and binds provider/model/settings through Provider Binding before authorization.'
if old_runtime_selection in current:
    current = current.replace(old_runtime_selection, new_runtime_selection, 1)
stop = current.index(marker)
current = current[:stop] + CURRENT_TAIL
current_path.write_text(current, encoding='utf-8')

plan_path = Path('docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md')
plan = plan_path.read_text(encoding='utf-8')
plan = plan.replace(
    '**Status:** approved plan; Tasks 1-4 complete; Task 5 next',
    '**Status:** approved plan; Tasks 1-5 complete; Task 6 next',
    1,
)
start = plan.index('### Task 5 — migrate application service and current result acceptance\n')
end = plan.index('### Task 6 — provider qualification refinement\n', start)
plan = plan[:start] + PLAN_TASK5 + plan[end:]
startup = plan.rfind('## New-chat startup / Task 5 boundary\n')
if startup < 0:
    startup = plan.rfind('## New-chat startup / Task 6 boundary\n')
    if startup < 0:
        raise SystemExit('Task 5/6 startup handoff marker missing')
plan = plan[:startup] + PLAN_STARTUP
plan_path.write_text(plan, encoding='utf-8')
