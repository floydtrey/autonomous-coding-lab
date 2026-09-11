# Runtime Core Reconstruction Plan

**Status:** approved plan; Task 1 complete; Task 2 not started

**Purpose:** reconstruct the ACL execution/runtime shell around the accepted Worker Lab authority model so the active tree is provider-neutral, model-swappable, host-portable, target-system-centered, and no longer carries obsolete Codex/Terra/Mine Tracker commissioning paths.

**Execution authority:** `DISABLED`

## Why this reconstruction happens now

The current authority, lifecycle, evidence, Knowledge Core handoff, runtime-requirement, provider-qualification, and bounded Pydantic/Ollama work established the shape of the intended vertical slice. A focused audit of the surrounding runtime pipeline found that several older files still encode assumptions from before the deep-research campaign and before the provider-neutral architecture was defined.

Do not add Provider Binding V1 on top of those obsolete paths. Reconstruct the runtime shell first, then bind the provider into the cleaner architecture.

The active Git tree should describe current architecture only. Git history is the historical record. Do not preserve obsolete Codex/Terra/MineTrackerWorker execution design in `docs/legacy/`, migration copies, compatibility modules, or fallback code merely for historical context.

ACL is a system, not a repository wrapper. A Git repository may be one workspace/version-control substrate for a coding task, but repository names, URLs, remotes, branches, checkout paths, and GitHub locations must not become durable ACL system identity or authorization merely because the first vertical slice edits code. During reconstruction, every active field or assumption that points to a repository must be classified as either justified Git-backed workspace evidence or obsolete repo-as-system coupling. The latter must be redesigned or removed.

## Architectural invariants

The reconstructed path must preserve these rules:

1. Worker Lab remains the authority for exercise, policy, role, context, lifecycle, test-plan selection, task authorization, and result acceptance.
2. The Autonomous Worker Framework remains responsible for bounded execution, workspace containment, candidate identity, and provider-neutral worker execution contracts.
3. Knowledge Core provides governed informational context; it never grants execution authority.
4. A controller/Foreman may request capability but must not choose an arbitrary executable, provider, model, or tool surface after authorization.
5. Provider/model selection must be represented by immutable qualification and binding evidence before dispatch.
6. Provider qualification is evidence, never task authorization.
7. The worker receives only the exact ACL-owned tools and file scope granted by the protected task contract.
8. No shell, Git, arbitrary process, network, publication, approval, or directory-enumeration authority is granted merely because a harness or model supports it.
9. Model/provider changes must not require changes to Worker Lab authority, Knowledge Core, Controller Task Packet, candidate verification, or lifecycle logic.
10. Host-specific executable paths, model paths/digests, GPU/runtime details, and process-containment evidence belong to host/provider qualification, not committed architecture.
11. Moving ACL to another compatible host must not require source edits solely because paths or provider installations differ.
12. Windows is the first containment backend; Linux must be possible later through a separate backend without changing the authority contracts.
13. Execution remains disabled throughout reconstruction. No model/chat/completion request is part of this plan unless separately authorized after the reconstruction acceptance gate.
14. ACL target identity is a logical system/project/workspace identity, not a repository locator. Repository metadata is allowed only where a Git-backed coding workspace needs exact source-state evidence.
15. Core authority/runtime contracts must not require every future target to be a Git repository. The first coding slice may require a Git-backed workspace, but that requirement belongs to the coding-workspace capability/backend rather than universal ACL identity.
16. Fields or code named `repository`, `template_repository`, `target_repository`, repository URL/path/remote/branch, or direct `.git` assumptions must be audited before preservation. Keep them only when they are necessary bounded evidence or mechanics for a Git-backed workspace; do not use them as a proxy for the actual target system.

## Target execution path

```text
User objective
    ↓
Controller / Foreman
    ↓
Knowledge Core retrieval
    ↓
Controller Task Packet
    ↓
Worker Lab protected authority
    ↓
Invocation V3
  - target/workspace identity
  - runtime requirement digest
  - provider binding digest
  - exact scope/context/tests
    ↓
Generic dispatch client
    ↓
Platform containment backend
  - Windows Job Object first
  - Linux backend later
    ↓
Generic dispatch adapter
    ↓
WorkerRequest
    ↓
Selected qualified provider adapter
  - Pydantic AI + Ollama first
  - other adapters later
    ↓
Selected qualified model
    ↓
WorkerExecution
    ↓
Independent verification
    ↓
verified / retry / blocked
    ↓
Controller / human review
```

A Git repository, base commit, changed-path set, or local checkout may appear below the target/workspace boundary when the selected task capability is a Git-backed coding task. Those facts are substrate evidence, not ACL's universal target identity.

## File disposition from the runtime-pipeline audit

### Remove after dependencies are migrated

- `components/autonomous-worker-framework/tools/codex_runtime.py`
  - obsolete Codex/Terra provider implementation.
- `components/autonomous-worker-framework/tools/local_worker_harness.py`
  - old commissioning/Codex harness; extract only provider-neutral repository-state helpers first.
- `components/autonomous-worker-framework/tools/task_contract.py`
  - old `autonomy_smoke` commissioning contract and Codex fixture runner.
- `components/autonomous-worker-framework/tools/worker_fixture_validator.py`
  - commissioning-only A/B/ABSENT fixture validator.
- `components/autonomous-worker-framework/tools/context_probe.py`
  - obsolete Codex read-only probe.
- `components/worker-lab/worker_lab/installation_manifest.py`
  - legacy Codex-specific `acl-installation-manifest:v2` loader.
- `config/installation-manifest.json`
  - obsolete host/Codex-specific manifest.
- `components/worker-lab/worker_lab/synthetic_read_only.py`
  - historical synthetic Codex proof path.
- Codex/Terra/commissioning-only tests after equivalent current-contract coverage exists.

### Replace cleanly rather than patch in place

- `components/autonomous-worker-framework/tools/worker_lab_adapter.py`
  - replace with a small provider-neutral dispatch adapter.
- `components/worker-lab/worker_lab/framework_client.py`
  - rewrite around portable component identity, Provider Binding, and generic dispatch; remove Codex launcher/install-manifest identity.
- `components/worker-lab/worker_lab/integration.py`
  - introduce Invocation/Result V3 instead of extending V2 with more changed semantics; V3 must distinguish logical target/workspace identity from any Git repository evidence.
- `components/worker-lab/worker_lab/process_custody.py`
  - create platform-neutral custody V2; Windows-specific process identity must not be durable universal schema.
- portable installation identity contract/verifier
  - create a truly host-independent V2 rather than encoding Windows/AMD64 as the portable architecture.

### Split/refactor while preserving useful behavior

- `components/autonomous-worker-framework/tools/workspace_write_adapter.py`
  - preserve canonical parsing, task reconstruction, Controller Task Packet enrichment, candidate verification behavior as appropriate; remove Codex typing and old adapter coupling, or fold the responsibility into the new dispatch adapter.
- `components/autonomous-worker-framework/tools/code_task.py`
  - keep provider-neutral task and verification behavior; remove Mine Tracker default and dependency on old commissioning harness.
- `components/autonomous-worker-framework/tools/consumer_profile.py`
  - preserve generic context/fingerprint concepts but remove the embedded `MINE_TRACKER_PROFILE` default; current authority comes from protected Exercise/Policy/Role/Context data.
- `components/autonomous-worker-framework/tools/repository_handoff.py`
  - keep Git-backed coding handoff behavior; change imports to new provider-neutral repository-state helpers and do not elevate repository identity into universal system identity.
- `components/autonomous-worker-framework/tools/local_git_publisher.py`
  - keep publication separated from execution as an optional Git-backed publication backend; change imports to generic repository-state helpers.
- `components/worker-lab/worker_lab/framework_adapter.py`
  - preserve independent candidate/result acceptance; separate transport/read-only legacy behavior and platform-specific workspace inspection.
- `components/worker-lab/worker_lab/operator_control.py`
  - preserve genuinely current controller/operator validation only; remove legacy doctor/Codex/synthetic activation machinery or replace it with current local activation controls.
- `components/worker-lab/worker_lab/application_service.py`
  - do not rewrite wholesale. Replace only invocation preparation/authorization/dispatch/recovery dependencies required by Invocation V3 and the new dispatch path.
- `components/worker-lab/worker_lab/cli.py`
  - remove commands for deleted legacy paths; retain current administrative/authority operations.
- Worker Lab records containing repository-specific fields such as `template_repository`, `template_commit`, `starting_commit`, or equivalent repository locators
  - audit rather than blindly preserve. Distinguish logical target/workspace identity from optional Git-backed source-state evidence; version the record only when needed to remove repo-as-system coupling.

### Keep as current architectural foundations unless a concrete dependency requires a bounded change

- Worker Lab lifecycle and authority semantics
- attempt and invocation storage concepts
- policy, role, context and test-catalog authority
- canonical serialization/digest primitives
- evidence storage and verification
- workspace preparation/verification/disposal behavior, while auditing Git-specific identity fields as described above
- Controller Task Packet V1
- `components/autonomous-worker-framework/tools/worker_result.py`
- current bounded file-tool security behavior in `pydantic_ollama_worker.py`
- Windows Job Object implementation as the Windows containment backend, not as the universal contract

## New foundations to introduce

### 1. Target-system/workspace boundary and repository-state module

Introduce an explicit distinction between the logical ACL target and the substrate used to work on it.

The logical target/system/workspace identity must not be a repository URL, clone path, branch, remote, or GitHub repository name. Git-specific facts belong to a Git-backed workspace/source-state adapter or evidence record.

Create a small provider-neutral repository-state module such as `repository_state.py` containing only Git-backed coding-workspace inspection primitives needed by current execution/verification, for example:

- `repository_head()`
- `changed_paths()`
- `candidate_content_digest()`
- `require_clean_workspace()` if still required

Do not carry commissioning/fixture/model behavior into this module. Do not let this module become the universal ACL target abstraction.

As part of this foundation, inventory active production/domain references to repository names, URLs, paths, remotes, branches, `.git`, `template_repository`, `target_repository`, and similar fields. Classify each as:

- justified Git-backed coding-workspace mechanics/evidence;
- a locator that belongs in a backend/adapter rather than a durable authority record; or
- obsolete repo-as-system coupling that should be removed or versioned away in a later reconstruction task.

### 2. Generic worker context

Remove Mine Tracker from the framework default. Context and invariants must be supplied from the protected current task/authority records. Do not hard-code a product profile into the generic runtime.

### 3. Platform containment contract

Define a provider-neutral containment/custody interface. Windows Job Objects become one implementation. Durable invocation/result schemas bind the containment evidence without assuming Windows-specific fields. A later Linux backend must fit the same contract.

### 4. Invocation / Result V3

V3 must bind the behavior-bearing identities before authorization, including at least:

- logical target/workspace identity independent of repository locator;
- protected runtime requirement identity/digest;
- exact Provider Binding identity/digest;
- framework/source identity needed for dispatch;
- exact authorized read/write scope;
- Controller Task Packet/prompt identity;
- protected test plan/catalog identities;
- substrate-specific source state only when required by the selected capability, such as a base commit for a Git-backed coding workspace.

Do not keep fake provider-neutral values in fields named `model` or `reasoning_effort`. Provider/model/settings belong to the sealed provider binding.

### 5. Provider Binding V1

Provider Binding is separate from Host Provider Qualification.

It must bind the exact qualified combination needed for one execution-capable runtime, including:

- runtime requirement digest;
- host/provider qualification digest;
- provider adapter identity;
- tool-surface identity;
- exact model identity/digest;
- behavior-bearing runtime settings profile.

Provider Binding exists before task authorization. Dispatch must fail closed if the authorized binding is absent, unknown, stale, or mismatched.

### 6. Runtime settings profile

The provider binding must explicitly bind settings that can materially change worker behavior, including the effective/requested context configuration rather than merely trusting a model metadata maximum. Pydantic/Ollama must consume the sealed settings rather than silently using provider defaults.

### 7. Provider capability qualification

Do not treat provider/model metadata labels as proof of end-to-end capability. Separate:

```text
installation identity
    ↓
controlled capability qualification
    ↓
provider binding
    ↓
task authorization
```

At minimum, tool-calling behavior and the usable context target must be validated with controlled fixtures before the provider/model is accepted for the supervised slice. Those tests remain non-authoritative evidence and do not grant execution permission for product work.

### 8. Host-independent portable identity

The committed portable identity should describe ACL source/component requirements, not one operating system or executable path. Host qualification records platform/Python/containment/provider facts separately.

A source checkout should not be edited from `DISABLED` to `ENABLED` merely to run a worker. If a host-level activation/kill switch is required, store that in local operator state, separate from committed source identity and separate again from one-invocation authorization.

## Ordered reconstruction tasks

Complete these one bounded task at a time. Do not collapse them into one broad rewrite.

### Task 1 — extract provider-neutral foundations and audit repository coupling

**Status:** complete in the Task 1 reconstruction checkpoint. The classified
inventory is `docs/REPOSITORY_COUPLING_INVENTORY.md`.

- inventory current runtime/domain references to repository names, URLs, paths, remotes, branches, `.git`, `template_repository`, `target_repository`, and equivalent repo-bound identity fields;
- classify each reference as justified Git-backed workspace evidence/mechanics, backend-only locator, or obsolete repo-as-system coupling;
- add generic repository-state helpers only for the justified Git-backed coding-workspace functions;
- migrate current consumers away from `local_worker_harness.py` helpers;
- remove Mine Tracker default coupling from the generic code-task/context seam only as required;
- add focused deterministic tests;
- no execution.

**Stop gate:** generic current code no longer needs commissioning harness helpers, and the repository-coupling inventory is explicit enough that later tasks will not accidentally preserve repository identity as ACL system identity.

**Accepted Task 1 boundary:** provider-neutral Git-backed workspace inspection is
isolated in `tools/repository_state.py`; current generic context/code-task consumers
no longer import repository helpers from `local_worker_harness.py`; generic context
and code-task entry points require an explicitly supplied protected profile; and the
inventory distinguishes justified Git evidence, backend locators, and obsolete
repository-as-system coupling. No custody, V3, Provider Binding, dispatch, deletion,
qualification, or execution work was performed.

### Task 2 — define platform-neutral containment/custody contract

- design custody V2;
- preserve current fail-closed/absence-proof semantics;
- make Windows Job Objects one backend;
- no Linux backend implementation required yet;
- no provider execution.

**Stop gate:** durable authority/result contracts no longer require Windows-only process fields.

### Task 3 — Invocation/Result V3 + Provider Binding V1

- define exact immutable binding semantics;
- introduce target/workspace identity independent of repository locator;
- keep Git base-commit/repository facts capability-specific rather than universal where possible;
- remove fake model/reasoning placeholders from the generic requirement;
- ensure binding exists before authorization;
- add tamper/stale/unknown-binding rejection tests;
- no provider execution.

**Stop gate:** provider/model/runtime settings cannot be chosen after authorization, and Invocation V3 does not use a repository locator as the logical target identity.

### Task 4 — generic dispatch client + dispatch adapter

- replace `framework_client.py` and `worker_lab_adapter.py` responsibilities with minimal current modules;
- migrate workspace-write task reconstruction/verification from the old bridge as needed;
- explicit no-fallback behavior;
- injected fake provider executors only.

**Stop gate:** workspace-write dispatch has no Codex/Terra dependency and no implicit provider selection.

### Task 5 — migrate application service and current result acceptance

- migrate only the invocation/dispatch/recovery portion of `application_service.py`;
- preserve accepted lifecycle/storage/policy/test behavior;
- separate platform-specific workspace/process evidence from generic result acceptance;
- keep Git-specific workspace evidence behind the coding-workspace boundary instead of treating it as universal system identity.

**Stop gate:** current Worker Lab service path uses only V3/current dispatch contracts.

### Task 6 — provider qualification refinement

- separate installation observation from controlled capability qualification;
- bind explicit runtime/context settings;
- adapt Pydantic/Ollama to consume the sealed binding/settings;
- use deterministic/mocked tests during implementation;
- actual model qualification remains separately authorized.

**Stop gate:** selecting another supported model requires qualification/binding data, not ACL source changes.

### Task 7 — remove obsolete active-tree implementation

After current replacements are accepted, delete the obsolete modules/configuration/tests listed above. Remove active-tree references to:

- Codex
- Terra
- MineTrackerWorker
- `autonomy_smoke`
- `acl-installation-manifest:v2`
- synthetic historical execution paths
- obsolete repository-as-system assumptions identified by the Task 1 inventory

Do not move these into `docs/legacy/` or a compatibility directory. Git history is sufficient.

**Stop gate:** repository scan finds no obsolete runtime architecture in current production code/configuration and no stale documents capable of being mistaken for current architecture; any surviving repository-specific contract is explicitly justified as a Git-backed workspace/backend concern.

### Task 8 — portable identity V2 and documentation cleanup

- rebuild portable component closure around current modules;
- separate source identity from host qualification and local activation;
- make documentation describe ACL as a system with optional task/workspace backends rather than as a repository-centered runtime;
- update `START_HERE`, `CURRENT_STATE`, operations/development/governance docs to current terms only;
- remove stale historical/legacy runtime documents from the current tree where they add retrieval ambiguity;
- retain only historical information that is still operationally necessary and clearly current-purpose.

**Stop gate:** fresh clone/current docs describe one architecture only, and moving or reconfiguring a target does not require repository identity to stand in for system identity.

### Task 9 — full deterministic reconstruction acceptance

Before any model run:

- current focused tests pass;
- relevant full component tests pass;
- portable identity V2 passes;
- working tree clean;
- zero obsolete runtime references in active production/config/current docs;
- no unjustified repository-as-system identity remains in current runtime/domain contracts;
- execution remains disabled;
- no provider/model request has been sent.

Only after this gate should ACL perform actual provider/model host qualification and prepare the supervised disposable vertical slice.

## Out of scope during reconstruction

Do not:

- run a local model;
- call Ollama chat/completions;
- enable task execution;
- add autonomous retry loops;
- add GUI work;
- expand Knowledge Core retrieval;
- redesign stable Worker Lab policy/lifecycle/storage merely because adjacent runtime code changes;
- mechanically remove all Git/repository operations that are legitimately required by the first coding-workspace backend;
- build Linux containment yet;
- start a new broad harness/model research campaign;
- preserve obsolete runtime code as fallback compatibility.

## Decision rules during implementation

- Prefer deletion over compatibility shims when the old capability is no longer part of current ACL.
- Prefer clean replacement over incremental patching when a module's responsibility no longer matches the current architecture.
- Treat repository/Git as a workspace/backend concern, not ACL system identity. Preserve it where exact code-state evidence is required; remove or relocate it where it merely stands in for the system/project/target.
- Do not mechanically rename `repository` to `system`; resolve the responsibility boundary instead.
- Preserve stable authority/evidence code unless a specific new contract requires a bounded change.
- Stop at architectural ambiguity rather than silently choosing a more permissive design.
- After every task, keep the tree clean and update this plan/current state only with accepted evidence.

## New-chat startup / Task 1 boundary

A fresh implementation chat should read, in this order:

1. `AGENTS.md`
2. `docs/START_HERE.md`
3. `docs/CURRENT_STATE.md`
4. `docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md`
5. only the current source/tests directly relevant to **Task 1**

Then inspect the current branch/HEAD and working tree. Perform **Task 1 only**: first inventory and classify repository-bound assumptions so Git/repository remains a coding-workspace substrate rather than ACL system identity; then extract provider-neutral repository-state foundations and migrate the current consumers needed to remove their dependency on the old commissioning harness. Do not proceed into custody, Invocation V3, Provider Binding, dispatch reconstruction, deletion, or execution in the same task.
