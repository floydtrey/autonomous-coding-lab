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
- Runtime Selection V1 at `0ad1b212581fb7b18110b9155763bf49b42df442` protects the provider-neutral `coding-worker:v1` capability requirement.
- Generic framework `WorkerRequest` no longer has an implicit Codex executor fallback.

## Host Provider Qualification Contract V1 — accepted baseline

The first protected provider candidate is **Pydantic AI core + Ollama**, not the full Pydantic AI Harness.

The current accepted baseline candidate maps `coding-worker:v1` to:

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

The existing qualification mechanism is observation-only and does not send a chat/completion request or enable execution. The focused gate passed 31 tests. The measured Worker Lab production tree is `sha256:52086119d189f41aa6ab708f7e03ce57a1cc70c3b4eaaeffd661556917115b67` across 28 files. Portable verification reported all three components `MATCH`, `provider_runtime_qualified=false`, `execution_authority=DISABLED`, and `execution_ready=false`, with a clean working tree.

Commit `81882c94798de80af4d54f04f52e545e4ab3c8cb` records the accepted Worker Lab portable identity for that contract baseline.

The reconstruction plan will refine this area before first execution: provider installation metadata will not be treated as proof of end-to-end tool/context capability, and behavior-bearing runtime settings must be sealed explicitly in Provider Binding rather than inherited from provider defaults.

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

The deterministic focused adapter gate passed 14 tests. The portable-verifier contract regression passed 4 tests. The accepted Windows portable verification reported:

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

## Current stop condition

Execution remains disabled.

Do not:

- authorize or dispatch any historical invocation;
- install Codex to satisfy obsolete configuration;
- preserve Codex/Terra as an automatic fallback path;
- send Pydantic AI/Ollama chat or completion requests;
- run a local coding model;
- implement Provider Binding on top of the old runtime shell before the reconstruction tasks establish the new foundations;
- mechanically delete legitimate Git workspace mechanics merely because ACL is moving away from repository-centered identity.

## Immediate next gate

Begin only **Task 3 — Invocation/Result V3 + Provider Binding V1** from
`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` in a later bounded task.

Task 3 must introduce logical target/workspace identity independent of repository
locators, keep Git source-state facts capability-specific, seal provider/model/runtime
settings before authorization, and add fail-closed binding tests without executing a
provider. Repository-decoupling work still governed by the Task 1 inventory remains
for backend-only locator placement during dispatch/service migration in Tasks 4–5,
obsolete repository-centered path deletion in Task 7, and portable identity V2 plus
documentation cleanup in Task 8.

Do not begin Task 3 or any later task as part of the Task 2 checkpoint.
