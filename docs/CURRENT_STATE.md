# Current State

**Last updated:** 2026-09-10

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

Begin **Task 1 — extract provider-neutral foundations and audit repository coupling** from `docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md`.

Task 1 is intentionally narrow:

- inventory current runtime/domain references to repository names, URLs, paths, remotes, branches, `.git`, `template_repository`, `target_repository`, and equivalent repo-bound identity fields;
- classify each as justified Git-backed workspace evidence/mechanics, backend-only locator, or obsolete repo-as-system coupling;
- create provider-neutral repository-state helpers only for justified Git-backed coding-workspace behavior;
- migrate current consumers away from `local_worker_harness.py` helper imports;
- remove Mine Tracker default coupling from the generic context/code-task seam only where required for that migration;
- add focused deterministic tests;
- keep execution disabled;
- stop when current generic code no longer depends on commissioning-harness helpers and the repo-coupling inventory clearly identifies what later tasks must redesign or preserve.

Do not continue into platform-neutral custody, Invocation V3, Provider Binding, dispatch reconstruction, legacy deletion, documentation purge, or model execution in the same task.
