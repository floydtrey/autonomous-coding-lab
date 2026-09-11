# Current State

**Last updated:** 2026-09-11

**Repository location:** portable; current laptop checkout is `C:\projects\autonomous-coding-lab`

**Active branch:** `architecture/knowledge-core`

**Execution authority:** `DISABLED`

## Current vertical-slice position

The project is deliberately moving toward one supervised end-to-end coding slice:

`user objective -> controller/Foreman -> Knowledge Core retrieval -> bounded task/context packet -> Worker Lab runtime requirement -> qualified provider binding -> bounded worker adapter -> coding worker -> independent verification -> verified/retry/blocked -> controller/human review`

Knowledge Core supplies governed project context. It does not authorize execution. Project Control Center is a separate status/dashboard project and is not ACL architecture or runtime authority.

ACL is being reconstructed as a **system**, not as a repository wrapper. A Git repository may remain the substrate for a coding workspace and exact source-state evidence, but repository names, URLs, remotes, branches, checkout paths, or GitHub locations must not stand in for the logical system/project/target identity. Current reconstruction work must audit repo-bound fields and retain them only where Git-backed coding mechanics/evidence genuinely require them.

## Accepted foundations

- Knowledge Core SR-2 through G22 and intended-host PostgreSQL restart/recovery qualification are complete.
- Knowledge Core Consumer V1 at `37f08f4090d59573108100ddf1b35a4923f01c29` returns verified segment content with exact provenance while preserving canonical evidence and privacy/serving checks.
- Portable ACL component identity separates committed component/source identity from per-host provider qualification, although the current portable-host contract still contains Windows-specific assumptions that are scheduled for reconstruction.
- Controller Task Packet V1 seals the user request and exact Knowledge Core evidence as informational context without granting authority.
- Runtime Selection V1 at `0ad1b212581fb7b18110b9155763bf49b42df442` preserves the historical `coding-worker:v1` qualification identity; the current public application-service execution path is Invocation/Result V3 and binds provider/model/settings through Provider Binding before authorization.
- Generic framework `WorkerRequest` no longer has an implicit Codex executor fallback.

## Host Provider Qualification Contract V1 — accepted baseline

The first protected provider candidate is **Pydantic AI core + Ollama**, not the full Pydantic AI Harness.

The current accepted baseline candidate maps historical `coding-worker:v1` qualification evidence to:

```text
candidate: pydantic-ai-ollama-files
harness distribution: pydantic-ai-slim
provider: ollama
transport: loopback HTTP only
tool surface: acl-bounded-file-tools:v1
minimum advertised context: 32768 tokens
required advertised model capability: tools
allowed effects: bounded file read/write only
forbidden effects: approval, git, network, process, publication, shell
```

The existing qualification mechanism is observation-only and does not send a chat/completion request or enable execution. The focused gate passed 31 tests. The measured Worker Lab production tree at that baseline was `sha256:52086119d189f41aa6ab708f7e03ce57a1cc70c3b4eaaeffd661556917115b67` across 28 files. Portable verification reported all three components `MATCH`, `provider_runtime_qualified=false`, `execution_authority=DISABLED`, and `execution_ready=false`, with a clean working tree.

Commit `81882c94798de80af4d54f04f52e545e4ab3c8cb` records the accepted Worker Lab portable identity for that contract baseline.

The reconstruction plan will refine provider qualification before first execution: provider installation metadata will not be treated as proof of end-to-end tool/context capability. Task 3 now seals behavior-bearing runtime settings in Provider Binding; Task 6 remains responsible for controlled capability qualification and making the provider adapter consume those sealed settings.

## Bounded Pydantic/Ollama worker adapter — accepted baseline

The bounded adapter was introduced at `0313e42c9f1d1f869e4298ac7eaee977985997d3`, followed by the Windows exact-byte regression correction and portable-closure consistency guard.

Accepted behavior includes:

- exact readable and writable file paths explicit in `WorkerRequest`;
- ACL-owned `read_file` and `write_file` tools only;
- SHA-256 stale-write preconditions;
- exact-byte-preserving UTF-8 reads;
- exact authorized relative-path enforcement;
- traversal, `.git`, symlink/reparse substitution, and unsafe hard-link writes rejected;
- loopback-only provider endpoint;
- bounded model requests/tool calls/tool execution/concurrency/output;
- no exposed shell, Git, arbitrary process, publication, approval, directory-enumeration, or arbitrary network tool.

The deterministic focused adapter gate passed 14 tests. The portable-verifier contract regression passed 4 tests. The accepted Windows portable verification for that baseline reported:

- Autonomous Worker Framework: `sha256:cb76f6ed59a5fb57b5b22faa31103fd285302b042b2bb3af7722b41e580d1414` across 10 files — `MATCH`;
- Local Model Bench: `sha256:139331ea42c914575d1119125a702ac5de2129b9bedc235bfc189700e8265afc` across 10 files — `MATCH`;
- Worker Lab: `sha256:52086119d189f41aa6ab708f7e03ce57a1cc70c3b4eaaeffd661556917115b67` across 28 files — `MATCH`;
- `provider_runtime_qualified=false`;
- `execution_authority=DISABLED`;
- `execution_ready=false`;
- working tree clean.

Commit `99a581f7ddf75041a8f3584966ce8652bf6afc13` is the accepted portable-verifier consistency checkpoint for this baseline.

## Runtime-pipeline audit — reconstruction approved

Before implementing Provider Binding V1, the active runtime pipeline was audited against the post-research architecture. The audit found that several execution-path modules still encode obsolete Codex, Terra, Mine Tracker commissioning, legacy installation-manifest, Windows-universal, and repository-as-system assumptions.

The project will **not** extend those paths with new provider-binding semantics. The approved cleanup/reconstruction plan is authoritative at:

`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md`

Key decisions:

- current Git tree should describe current architecture only; Git history is the historical record;
- do not preserve obsolete runtime code or stale architecture under `docs/legacy/`, migration copies, fallback modules, or compatibility shims solely for history;
- ACL logical target/system identity must be independent of repository locator/path/URL/branch/remote; Git-specific facts survive only as bounded coding-workspace/backend evidence where justified;
- Task 1 must inventory and classify repo-bound fields such as `template_repository`, `target_repository`, repository paths/URLs/remotes/branches, and direct `.git` assumptions before later tasks preserve or version them;
- remove `codex_runtime.py` after dependencies are migrated rather than genericizing it;
- replace `worker_lab_adapter.py` and `framework_client.py` around provider-neutral dispatch rather than patching their old Codex/installation-manifest architecture;
- introduce Invocation/Result V3 and Provider Binding V1 before authorization/dispatch integration;
- make process custody platform-neutral with Windows Job Objects as one backend;
- remove Mine Tracker defaults and commissioning fixtures from generic runtime code;
- make portable source identity host-independent; host/platform/provider facts belong to qualification/local state;
- no actual provider/model execution occurs during reconstruction.

## Runtime reconstruction Task 1 — accepted checkpoint

Task 1 extracted the provider-neutral Git-backed coding-workspace primitives from
the commissioning harness and recorded the complete classification at
`docs/REPOSITORY_COUPLING_INVENTORY.md`.

Accepted changes:

- `repository_state.py` owns exact HEAD, changed-path, clean-workspace,
  repository-root, and candidate-content inspection;
- `code_task.py`, `repository_handoff.py`, and `local_git_publisher.py` no longer
  import repository helpers from `local_worker_harness.py`;
- generic context creation, context verification, and code-task execution require
  an explicit `ConsumerProfile`; Mine Tracker is no longer an implicit generic
  default;
- legitimate Git source-state verification, candidate evidence, workspace
  containment, publication separation, and Knowledge Core source provenance remain;
- the portable V1 Autonomous Worker Framework runtime closure contains 11 files and
  matches `sha256:22c519673bb8f2b5826687b3e8b8df22b004865b702b8fb2215d4e8bd84861d6`;
- execution authority remains `DISABLED` and no provider/model request was sent.

Validation on the Task 1 working tree:

- focused deterministic framework gate: 61 passed;
- portable V1 contract tests: 4 passed;
- direct Autonomous Worker Framework portable-closure inspection: `MATCH`;
- broader framework diagnostic on this Linux workspace: 225 passed and 8 failed.
  Seven failures are confined to the obsolete Windows/Codex
  `worker_lab_adapter.py` / `acl-installation-manifest:v2` path because its hard-coded
  Windows runtime paths are not valid Linux paths; one is the pre-existing
  `test_project_documentation.py` assertion for superseded Phase 1 headings absent
  from the accepted starting commit. The transitional disabled manifest's file-set
  closure was refreshed only for exact Task 1 dependency bytes; its repository/Codex
  semantics remain unchanged and obsolete.

## Runtime reconstruction Task 2 — accepted checkpoint

Task 2 versioned process custody to
`worker-lab-process-custody:v2` without granting execution authority.

Accepted changes:

- the durable custody schema now binds a versioned backend identifier, opaque
  controller and worker identities, a generic active-workload count, and a digest
  of backend-produced absence evidence;
- generic transition, storage, recovery, service recovery, and result-acceptance
  code no longer requires Windows PIDs, process creation times, a Job Object mode,
  or a Windows-named active-process count;
- Windows Job Objects remain the only implemented backend, with Windows process
  identity parsing, PID-reuse detection, Job Object accounting, and absence-evidence
  construction confined to `windows_job.py`;
- recovery requires the backend named by the durable record and remains
  fail-closed for active controllers, backend substitution, incomplete dispatch
  evidence, unknown/nonzero workloads, and absent or malformed absence evidence;
- the portable Worker Lab production tree contains 28 files and matches
  `sha256:5bf7aaffc87c04c5018d028a34c32e68c7edd7f9ab23cc4251b7f57d26a814dc`;
- execution authority remains `DISABLED`; no Linux backend, provider binding,
  dispatch reconstruction, provider/model qualification, or provider/model request
  was performed.

Validation on the Task 2 working tree:

- focused custody and result-acceptance gate: 29 passed;
- application-service suite with a deterministic injected installation report:
  33 passed;
- deterministic Windows Job backend seams exercised without native process/model
  execution: 15 passed;
- root tests: 13 passed;
- portable identity contract tests: 4 passed;
- direct Worker Lab portable production-tree inspection: `MATCH`.

The direct Linux Worker Lab full-suite diagnostic reported 340 passed, 36 failed,
and 21 skipped. All 36 failures are blocked by the accepted starting tree's
obsolete `acl-installation-manifest:v2` loader: its
hard-coded runtime contract is Windows/Codex-specific and its Autonomous Worker
Framework closure predates the Task 1 `repository_state.py` addition. These failures
occur before the affected application/runtime tests reach custody behavior. The
legacy manifest/loader was not expanded in Task 2 because it is scheduled for
removal in Task 7. Native Windows Job Object execution was not performed.

## Runtime reconstruction Task 3 — accepted checkpoint

Task 3 introduces the provider-neutral authorization foundations without migrating
the still-live V2 application/dispatch path and without executing a provider.

Accepted changes:

- historical `coding-worker:v1` and Host Provider Qualification V1 identities remain
  unchanged for the legacy V2 seam; new `coding-worker:v2` is a separate
  provider-neutral runtime requirement containing no fake `model` or
  `reasoning_effort` selectors;
- Provider Binding V1 seals the exact runtime-requirement digest, Host Provider
  Qualification digest, provider adapter identity, tool-surface identity, exact
  model identity/digests, and the protected behavior-bearing runtime-settings
  profile before authorization;
- the protected settings profile seals requested context (`32768`), request/tool
  limits, tool timeout, retry counts, and concurrency. No temperature is invented
  because the current adapter does not explicitly control one;
- Invocation V3 binds logical `target:` and `workspace:` identities independent of
  repository locator, Controller Task Packet/prompt identities, protected tests,
  framework/source contract identities, exact read/write scope, runtime requirement,
  and Provider Binding;
- Git base commit and workspace digests are nested coding-workspace source evidence,
  not ACL target identity;
- the authorization transition requires the exact durable Provider Binding and
  fails closed for missing, stale, invalid, or substituted binding evidence;
- Result V3 preserves the existing independent-acceptance evidence needed for later
  service migration, including request/invocation linkage, process/custody identity,
  candidate/proposal digest, validation stages, containment outcome, exact changed
  paths, and capability-specific Git result evidence;
- model or harness qualification substitution invalidates the binding;
- benchmark and controlled qualification evidence may later determine which exact
  model/configuration is fit for an ACL role, but Task 3 does not select or hard-code
  a preferred model;
- the portable V1 Worker Lab production tree now contains 30 files and matches
  `sha256:6172ab988f48896128beb143fc2f6bc0529d891b1eb2a5310f4016aad0bc6a25`;
- execution authority remains `DISABLED`; no provider/model request was sent.

Validation on the Task 3 candidate tree:

- Python compilation passed;
- required V2 compatibility plus Task 3 focused suites: 48 passed;
- portable Worker Lab file-count/digest check: 30 files, exact manifest match;
- portable installation contract tests: 4 passed;
- isolated deterministic V3 contract harness: 20 passed;
- legacy `framework_client.py` / `application_service.py` diagnostic: 23 passed and
  29 failed, with all failures blocked by the already-known obsolete
  `acl-installation-manifest:v2` framework-runtime-closure boundary before V3 logic.

Task 3 intentionally does **not** migrate `framework_client.py`,
`worker_lab_adapter.py`, or `application_service.py` to V3. That work remains
ordered under Tasks 4–5 so the new contracts are not layered onto the obsolete
Codex/installation-manifest shell.

## Runtime reconstruction Task 4 — accepted checkpoint

Task 4 establishes the current V3 dispatch foundations without migrating
`application_service.py` and without invoking a real provider.

Accepted changes:

- `dispatch_client.py` accepts only an authorized `DISPATCHING` Invocation V3
  workspace-write task, requires the exact durable Provider Binding and protected
  runtime-settings profile, verifies the exact Controller Task Packet/prompt and
  sealed task/test/scope, and emits one bounded canonical dispatch envelope;
- logical target/workspace identities and capability-specific Git source evidence
  remain in the sealed V3 record, while local workspace/framework paths are passed
  separately to the framework adapter as backend locators rather than durable ACL
  target identity;
- `dispatch_adapter.py` independently validates the V3 envelope, reconstructs the
  bounded consumer profile/context/code task, and accepts exactly one explicitly
  injected `BoundProviderExecutor`; it contains no provider registry, default
  provider, fallback provider, Codex path, or Terra path;
- the injected executor must match the sealed provider-adapter identity,
  tool-surface identity, Provider Binding digest, and runtime-settings digest
  before workspace mutation can occur;
- a nonzero provider execution result fails closed as `DISPATCH_PROVIDER_FAILED`
  even when the authorized file changes would otherwise satisfy validation;
- existing provider-neutral `code_task.py` containment, exact changed-path,
  candidate-identity, diff, and independent validation behavior is reused rather
  than duplicated or weakened;
- the existing portable V1 Autonomous Worker Framework runtime closure now contains
  12 files and matches
  `sha256:81926dbde5d8ac45408c9d0d0ab9819f65c977e166cbe34d802cf445de29d9ac`;
- the portable V1 Worker Lab production tree now contains 31 files and matches
  `sha256:eecac00f96a46f25a6dab03eef933192956572c49a8b5f542784d24935175695`;
- execution authority remains `DISABLED`; no provider/model request was sent.

Validation on the Task 4 candidate and committed-byte temp tree:

- Python compilation passed;
- framework Task 4 plus stable generic regressions: 28 passed;
- Worker Lab Task 4 plus V3/Provider Binding regressions: 24 passed;
- Worker Lab/framework dispatch protocol constants matched exactly;
- direct portable component inspection: Autonomous Worker Framework `MATCH`, Worker
  Lab `MATCH`;
- portable installation contract tests: 4 passed;
- the same validation passed again against the committed portable identities with
  no further portable-source changes required.

Task 4 intentionally does **not** migrate the live `application_service.py` path.
The old V2 `framework_client.py` / `worker_lab_adapter.py` shell remains reachable
only through that not-yet-migrated service path until Task 5, and obsolete modules
remain scheduled for deletion in Task 7.

## Runtime reconstruction Task 5 — accepted checkpoint

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

## Runtime reconstruction Task 6 — accepted checkpoint

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

## Runtime reconstruction Task 7 — accepted checkpoint

Task 7 removes obsolete active-tree runtime/commissioning implementation after the current V3 replacements were accepted. It does not perform the portable-identity V2 redesign or enable execution.

Accepted changes:

- deleted obsolete Codex/Terra commissioning modules, the old local commissioning harness/fixture contracts, and old Worker Lab V2 bridge/client/invocation/read-only/synthetic execution modules rather than retaining compatibility shims;
- deleted `config/installation-manifest.json` and `config/monorepo-identity.json`; current operator health/installation inspection uses the disabled portable manifest rather than the obsolete Codex-era installation contract;
- removed the embedded production Mine Tracker consumer profile and the active Phase 4 record-normalizer proof bundle tied to the old `MineTrackerWorker` repository;
- retained Windows Job Object custody/absence evidence as the current containment backend while removing the obsolete V2 Windows adapter runner;
- retained Git repository/head/change evidence only where the coding-workspace, handoff, publication, or source-state boundary requires it; repository identity is not restored as ACL logical target identity;
- current application-service record handling, lifecycle binding, runtime selection, provider qualification, and tests no longer depend on the deleted V2/commissioning modules;
- protected Worker Lab V3 tests T016/T022 now exercise `test_integration_v3.py`, `test_invocation_store_v3.py`, and `test_application_service_v3.py`; the protected catalog digest was re-baselined for that explicit authority change;
- superseded `docs/VS_CODE_HANDOFF.md` and `docs/WORKPLAN.md` were removed because they could be mistaken for current instructions;
- portable V1 byte identity was refreshed only to describe the reduced current tree: Autonomous Worker Framework is 8 files at `sha256:edac32b728348d6a2e2c7521d1c846e5021fe6e40f33db70e7df625d1ca584c5`, Worker Lab is 29 files at `sha256:8b92b879d555d3c695318809895947b0a6ac9b1e87cf6caef5db5ad7541549e7`, and Local Model Bench remains 10 files at `sha256:139331ea42c914575d1119125a702ac5de2129b9bedc235bfc189700e8265afc`;
- execution authority remains `DISABLED`; no provider/model request or actual capability qualification was performed.

Validation on the Task 7 materialized candidate:

- Python production compilation and current Worker Lab service imports passed;
- complete surviving Autonomous Worker Framework suite: 76 passed;
- complete surviving Worker Lab suite: 319 passed, 1 skipped because symlink creation was unavailable on the Linux runner;
- portable installation contract: 4 passed;
- production/configuration scan returned zero references for the retired Codex/Terra/MineTrackerWorker/commissioning/V2 bridge/legacy-manifest terms targeted by Task 7.

## Current stop condition

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

Begin only **Task 8 — portable identity V2 and documentation cleanup** from
`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` in a later bounded task.

Task 8 rebuilds the portable component/source identity around the now-current modules,
separates source identity from host qualification/local activation, and cleans current
documentation to describe one system-centered architecture. Do not broaden Task 8 into
actual provider/model execution; that remains behind the Task 9 reconstruction
acceptance gate and separate authorization.
