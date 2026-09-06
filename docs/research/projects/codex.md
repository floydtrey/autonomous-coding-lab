# Codex — deep research

**Task:** 10 — ranked project #6  
**Project:** OpenAI Codex  
**Canonical repository:** `openai/codex`  
**Research date:** 2026-09-06  
**Upstream main examined:** `6af345407d9c2a568da9d01b6c4b81a9e61495c0`  
**License:** Apache-2.0  
**Status:** active; research complete for this task; no dependency/adoption/fork decision made

## Why Codex is in scope

Codex is unusually relevant to ACL/Vera because it is not only an agent loop. The current implementation exposes concrete, shipped machinery for:

- command/file execution authority;
- explicit sandbox profiles;
- approval and execution-policy composition;
- protected control-plane metadata inside otherwise writable workspaces;
- subagent/child-session authority inheritance;
- local Ollama/LM Studio providers;
- persistent thread/turn/item protocol state;
- fork/resume semantics;
- managed Git worktrees;
- process-group cancellation and output settlement;
- OpenTelemetry runtime evidence;
- an auto-review/Guardian layer that treats authorization evidence as versioned state.

The task is to extract mechanisms, invariants and current failure surfaces. It does **not** decide whether ACL should use Codex as its worker runtime, copy its permission model, wrap it, fork it, or replace existing ACL components.

## Evidence discipline

Primary sources were preferred in this order:

1. current `openai/codex` source and regression tests;
2. current OpenAI Codex documentation;
3. recent merged commits explaining a concrete bug/fix;
4. current GitHub issues for unresolved failure evidence.

A documentation statement is not treated as a shipped guarantee when current code/tests contradict it. Open issues are treated as failure reports, not proof that every current path/version remains affected.

---

# 1. Project health and architectural shape

## Observed

The canonical repository is active, public, Apache-2.0 licensed and under rapid development. On 2026-09-06, main was `6af345407d9c2a568da9d01b6c4b81a9e61495c0`, whose change itself concerned child-session capability inheritance.

Codex has several distinct runtime layers rather than one monolithic prompt loop:

- protocol types for sandbox/permissions/session events;
- core session/turn execution;
- execution policy and command matching;
- sandbox adapters;
- model-provider normalization;
- app-server thread/turn/item protocol;
- multi-agent delegation;
- managed worktrees;
- OTEL telemetry;
- auto-review/Guardian approval routing.

## ACL/Vera relevance

This is useful because the same conceptual boundary keeps appearing across the projects researched so far: **model reasoning is only one plane**. Authority, persistence, recovery, process custody, approval provenance and validation require separate deterministic owners.

## Source

- https://github.com/openai/codex
- https://github.com/openai/codex/tree/6af345407d9c2a568da9d01b6c4b81a9e61495c0

---

# 2. Sandbox policy is explicit authority state

## Shipped policy model

Current `SandboxPolicy` has explicit variants including:

- `DangerFullAccess`;
- `ReadOnly`;
- `WorkspaceWrite`;
- `ExternalSandbox`.

`WorkspaceWrite` is not simply “cwd writable.” It computes writable roots and attaches protected/read-only subpaths and protected metadata names.

Current protected metadata includes:

- `.git`;
- `.agents`;
- `.codex`.

This matters because these paths are control-plane state. A coding worker that can modify source files but also rewrite Git hooks, agent instructions or Codex configuration has qualitatively greater authority than a source-only writer.

## Permission-profile semantics

Current permission code represents filesystem access as explicit `Read`, `Write`, or `Deny` decisions. Equal-specificity conflicts are fail-safe: deny outranks write, and write outranks read. Invalid/unresolved permission state can resolve to deny rather than silently widening.

Legacy conversion also refuses some policies it cannot safely represent instead of broadening them into a permissive approximation.

## Security implication

**A writable workspace needs internal protected roots.** “The repo is writable” should not imply that worker-owned source code, Git authority, harness configuration, verifier definitions, agent instructions and secrets share one trust class.

For ACL, candidate protected roots include at minimum:

- Git metadata / ref-changing surfaces;
- ACL policy and worker-definition files;
- protected validator fixtures;
- evidence/receipt roots;
- credentials or secret material;
- task/project authority state.

## Sources

- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/protocol/src/protocol.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/protocol/src/permissions.rs
- https://learn.chatgpt.com/docs/sandboxing
- https://learn.chatgpt.com/docs/permissions

---

# 3. Approval policy and sandbox authority are orthogonal

## Observed

Current Codex separates:

- **what an execution environment permits**; and
- **when a request may require human approval**.

`approval_policy="never"` does not mean danger-full-access. If an action requires an approval that cannot be requested under the current policy, the action fails rather than silently escalating.

The core execution-policy path likewise distinguishes allow, prompt/approval-needed and forbidden decisions. A prompt-required command under a `Never` approval policy does not become allowed merely because no person can be asked.

## Reusable invariant

> **No approval != full authority.**

ACL should never encode “unattended” or “auto-run” as a synonym for broad permissions. A local worker can run without approval while still being deterministically constrained to a narrow filesystem/network/tool capability set.

## Reusable approval-prefix lesson

Codex’s reusable command-approval logic deliberately rejects dangerously broad reusable prefixes such as generic shells/interpreters, package script runners, `git`, `rm`, `sudo`, Python, Node and PowerShell.

That is important for Vera: “always allow this action” must bind to the narrowest stable operation identity. Approving `python`, `powershell`, `git`, or an unrestricted shell prefix effectively approves arbitrary future programs.

## Sources

- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/exec_policy.rs
- https://learn.chatgpt.com/docs/agent-approvals-security
- https://learn.chatgpt.com/docs/permissions

---

# 4. Child-agent authority is intentionally one-way

This is one of the strongest Codex findings for ACL.

## Live authority inheritance

When Codex spawns a child session, current code starts from the parent effective configuration and refreshes live turn-owned authority such as:

- current sandbox/permission state;
- approval policy/reviewer;
- cwd;
- model/reasoning settings.

The source explicitly notes that stale inherited config could otherwise make a child disagree with its parent on sandbox, approval or cwd.

## Role customization is deliberately constrained

Current role code states that roles may customize a child or **reduce its capabilities**, but may not replace the parent session’s authority.

Role configuration can change things such as:

- developer instructions;
- model;
- reasoning effort/summary;
- verbosity/personality/service tier;
- selected feature/skill disables.

It is not supposed to replace parent authority fields such as:

- sandbox policy;
- approval policy;
- provider/provider URLs;
- MCP servers;
- apps;
- notification commands.

## Hostile configuration regression tests

Current tests are unusually valuable because they do not merely test a friendly role. A hostile custom role attempts to configure:

- `danger-full-access`;
- `approval_policy="never"`;
- alternate provider/base URLs;
- Ollama provider selection;
- attacker-controlled MCP servers;
- apps;
- notification commands;
- other authority-bearing runtime changes.

The tests assert that these authority-expanding changes do **not** replace the parent’s effective sandbox/provider/reviewer/MCP authority, while legitimate model/instruction changes and capability reductions remain possible.

There is also a dedicated regression test that the parent sandbox permissions survive role application.

## Documentation mismatch

Current subagent documentation includes wording broad enough to imply per-agent sandbox overrides. The shipped role implementation and tests are narrower: roles can reduce/customize behavior but cannot replace parent session authority.

For this research, current source/tests control. The docs statement is recorded as a **documentation/code mismatch**, not as evidence that custom roles may widen sandbox authority.

## ACL/Vera invariant

> **Child authority should be derived by intersection/restriction, never by child-supplied widening.**

A child worker may receive a narrower role. It should not be able to increase its authority by choosing a different worker definition, model, plugin set or provider configuration.

## Sources

- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/tools/handlers/multi_agents_common.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/agent/role.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/agent/role_tests.rs
- https://learn.chatgpt.com/docs/agent-configuration/subagents

---

# 5. Child authority inheritance and child capability inheritance are different

Main on the research date contains a particularly relevant fix: **“Gate experimental context by model capability at session startup (#43147)”**.

## Failure

Fresh child sessions could inherit experimental context activation from a parent even when the child switched to a model that did not support that capability.

The flaw was not primarily permission widening. It was **capability-state inheritance** being copied across a model boundary without recomputation.

## Fix pattern

The current fix:

- gives model metadata an explicit capability field;
- defaults unsupported/unknown capability to false;
- reapplies startup capability checks against the child’s own model;
- resets/reconstructs fresh-child preference/capability state instead of blindly copying the parent’s activation;
- preserves appropriate history-fork behavior separately.

## ACL/Vera invariant

Two inheritance operations should remain distinct:

1. **Authority inheritance:** parent establishes the ceiling; child may only narrow it.
2. **Capability inheritance:** recompute against the child’s exact model/runtime/adapter/environment.

The parent successfully using feature X does not prove a child model/runtime supports feature X.

## Source

- https://github.com/openai/codex/commit/6af345407d9c2a568da9d01b6c4b81a9e61495c0

---

# 6. Reviewer/delegate surfaces can be deliberately smaller than worker surfaces

## Observed

`codex_delegate.rs` distinguishes ordinary worker/subagent delegation from Guardian review delegation.

Important current behavior includes:

- delegates do not request approvals;
- an interactive delegate path requires approval policy `Never`;
- Guardian reviewer uses an empty extension registry;
- ordinary subagents can inherit parent extension surfaces;
- parent/root turn identity is carried into one-shot delegate work;
- cancellation is propagated and the one-shot delegate is shut down after terminal turn state.

`Never` here does not itself grant full system authority; deterministic sandbox/exec permissions still govern what the delegate can do.

## ACL/Vera lesson

Validator/reviewer workers should generally have a **smaller capability surface** than coding/execution workers. A reviewer that only needs evidence should not automatically inherit shell, writable workspace, external MCP servers or broad network access merely because the worker being reviewed has them.

## Source

- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/codex_delegate.rs

---

# 7. Guardian treats approval as versioned authorization evidence

This is the highest-value Codex approval finding for future Vera behavior.

## Root authorization preservation — recent fix

Commit `87628df77ab1a2622d1193ad835df02ced565bf2` hardens Guardian review so an approval decision is tied to the current root authorization evidence rather than only to the worker’s compacted/current prompt.

The change preserves/reconstructs bounded evidence from:

- root user instructions;
- verified answers/authorization context;
- retained history after compaction.

It also versions that root authorization state so an earlier allow decision can be cancelled/staled when the underlying root authorization evidence changes.

## Compaction fail-closed behavior

Commit `4636819a352bfd4271c669c568a92f1bccfcd7e0` further hardens review after context compaction.

Reusable review/checkpoint state is accepted only when compatible evidence is recoverable. Missing, unusable, incompatible or unknown review checkpoint state fails closed rather than pretending the previous authorization still applies.

## Other current Guardian hardening themes

Recent changes also show:

- executor-native paths must be preserved rather than blindly normalized through the host OS;
- approval routing must remain usable even when async scoring fails;
- approval decisions are request-scoped;
- telemetry failure reasons should be low-cardinality and should not leak arbitrary infrastructure error text;
- reviewer lineage/state needs explicit identifiers rather than loose tickets.

## ACL/Vera approval invariant

A future Vera approval should not mean only:

> “Floyd once said yes to something that looks similar.”

It should bind to something closer to:

- approval/request ID;
- principal/user identity;
- exact task/objective version;
- exact material arguments/effect target;
- relevant workspace/environment identity;
- authorization-context version;
- reviewer/policy version where applicable;
- terminal/expiry state.

If any material authorization evidence changes, previous approval must be revalidated or invalidated.

## Sources

- https://github.com/openai/codex/commit/87628df77ab1a2622d1193ad835df02ced565bf2
- https://github.com/openai/codex/commit/4636819a352bfd4271c669c568a92f1bccfcd7e0

---

# 8. Sandbox adapter bridges are security boundaries

Recent Windows sandbox fixes expose a recurring failure class: **permission information can be correct in the high-level policy and still be lost while crossing an adapter/wrapper boundary.**

## Current examples

Recent changes include:

- preserving managed denied-read paths when invoking the Windows sandbox wrapper;
- rejecting unsupported sandbox fallback rather than pretending the requested policy was applied;
- preserving `SystemRoot` for wrapper setup while preventing that host environment value from leaking into the sandboxed child command;
- reducing redundant path resolution around sandbox setup.

## ACL/Vera lesson

For every execution adapter, test the full path:

`ACL policy -> worker request -> adapter serialization -> OS/container primitive -> actual child effect`

A correct policy object is not enough. ACL should have fixtures that prove denied roots, network rules, environment scrubbing and other restrictions survive every platform/runtime bridge.

## Relevant commits

- https://github.com/openai/codex/commit/a482e65b
- https://github.com/openai/codex/commit/f1aac1e8
- https://github.com/openai/codex/commit/60888d08
- https://github.com/openai/codex/commit/3b2d9a69

The short SHAs are recorded as transition references; re-resolve/recheck current upstream before dependency decisions.

---

# 9. Symlink exceptions are explicit trust grants

Current Codex has an `allow_symlinked_codex_home` escape hatch.

Important characteristics:

- disabled by default;
- intended to be enabled only in top-level user-owned config rather than project configuration;
- explicitly warns that trusting a symlink means trusting its target even if that target lies outside `CODEX_HOME` or changes between operations;
- does not generalize the exception to arbitrary writable roots.

## ACL/Vera lesson

Trust exceptions should be:

- narrow;
- explicit;
- user/administrator-owned;
- non-transitive by default;
- excluded from project/worker-controlled configuration.

A repository should not be able to enable a path-trust exception that lets its own worker escape the repository’s intended boundary.

## Sources

- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/config/src/codex_home_symlink.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/config/src/config_toml.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/sandboxing/src/seatbelt.rs

---

# 10. Managed worktrees isolate working directories, not every trust domain

Current Codex worktree docs are directly relevant to parallel ACL workers.

## Observed

Managed worktrees:

- give chats separate working directories;
- are generally associated one-to-one with a chat;
- begin from a selected branch HEAD;
- use detached HEADs by default;
- can copy selected ignored files through `.worktreeinclude`;
- may copy files such as `.env`, `.env.local`, or other ignored setup/secret files when configured;
- skip source symlinks and do not overwrite existing destination files in the copy path;
- preserve/snapshot work before automatic cleanup;
- retain a bounded number of recent managed worktrees by default;
- offer restore from cleanup snapshots.

## Important boundary

A separate working directory does **not** automatically imply:

- separate credentials;
- separate Git-object/control authority;
- separate network identity;
- separate external-service effects;
- separate verifier roots.

The ability to copy ignored secret files is intentionally useful, but it proves that **workspace isolation and secret isolation are separate policies**.

## ACL/Vera lesson

Parallel workers should receive per-run workspaces plus an explicit secret projection policy. A worker should not inherit every ignored file merely because the project’s main checkout needs it.

Candidate design:

- workspace ID distinct from branch/ref ID;
- detached/owned worker branch or ref policy;
- explicit source baseline commit;
- explicit copied/generated fixture manifest;
- minimum secret projection;
- pre-cleanup snapshot;
- independent external-effect ledger.

## Source

- https://learn.chatgpt.com/docs/environments/git-worktrees

---

# 11. Thread/turn/item protocol provides useful persistent identities

The current app-server architecture models conversation/execution around durable protocol objects:

- **Thread**;
- **Turn**;
- **Item**.

Threads can be durable or ephemeral. Turns can carry runtime configuration such as model, cwd, sandbox/permission and approval/reviewer information.

## Version-specific schema

The app server can generate TypeScript/JSON schemas that are guaranteed to match that exact Codex build.

### ACL lesson

Persisted protocol/evidence schemas should be versioned against the exact runtime build. “Same field names” across versions is not sufficient when authority-bearing semantics may change.

## Bounded queues / backpressure

The app server uses bounded ingress/request/outbound queues. Saturation produces an explicit overloaded error and clients are expected to retry with backoff/jitter.

This is a good long-running supervisor invariant: **backpressure should be explicit state, not unbounded buffering**.

## Source

- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/app-server/README.md

---

# 12. Resume/fork semantics preserve provenance instead of silently inventing continuity

## Resume

Current app-server behavior tracks thread-owned settings snapshots. If resume does not provide a cwd, Codex can recover the latest retained setting **owned by that thread**; older/unowned snapshots do not silently override.

This is an important provenance pattern: a value in history does not automatically become authoritative current state unless the runtime can prove ownership/context.

## Fork

Current fork semantics can target completed turn boundaries or cut before a turn. If a source thread is mid-turn and no completed boundary cleanly represents the fork, the fork path records an explicit interruption marker rather than silently copying an unmarked partial suffix as though it were complete history.

## ACL/Vera invariant

> Partial/in-progress execution must remain visibly partial.

On crash, cancel, fork, compaction or migration, do not turn an incomplete worker attempt into an apparently clean completed task simply because enough transcript text survived.

## Source

- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/app-server/README.md

---

# 13. Persistent create/import operations use idempotency identity

Current experimental project APIs use idempotency keys for mutation-like create/import operations.

Observed semantics include:

- repeated use of the same key returns/reuses the original operation identity rather than creating duplicates;
- the key remains reserved even if the project is later deleted;
- logical project deletion clears assignment state but is not the same as deleting every thread/directory/file.

## ACL/Vera lessons

1. Durable create/import/enqueue operations need caller-stable idempotency IDs.
2. Deleting a logical project identity is different from deleting historical evidence/workspaces/files.
3. A deleted identity should not be silently resurrected by replaying an old create request.

These fit directly with ACL’s existing need for project/task IDs, retry-safe operations and retirement fencing.

## Source

- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/app-server/README.md

---

# 14. Local Ollama/LM Studio support is real but adapter semantics remain part of capability

## Current provider architecture

Codex currently supports built-in and user-defined model providers. The current provider layer uses the Responses API path; legacy chat-wire configuration is rejected/migrated rather than silently mapped.

Ollama and LM Studio have first-class provider definitions using Responses-compatible endpoints.

Provider configuration also owns operational settings such as:

- base URL/auth/header handling;
- request retry limits;
- stream retry limits;
- stream idle timeout;
- web-search capability declarations.

## Open issue #30994 — provider scope contamination

Current open issue #30994 reports a Codex App/Ollama setup path writing top-level `model_provider`/catalog configuration, causing local provider state to affect later OpenAI model selection/routing rather than remaining profile-scoped.

The broader lesson is stronger than the one UI bug:

> **Provider/runtime selection is scoped authority/configuration state.**

A temporary/local profile should not silently rewrite global model/provider identity.

## Open issue #42488 — namespaced tool-call normalization

Current open issue #42488 reports a custom/Ollama provider emitting a flattened dotted multi-agent tool name (for example `multi_agent_v1.spawn_agent`) without the namespace representation expected by the router, yielding an unsupported-call failure.

The issue includes a proposed normalization direction, but this task did **not** establish a merged current fix. It remains open failure evidence.

## ACL/Vera local-runtime invariant

“OpenAI-compatible” or “Responses-compatible” is not enough. Record and test:

- exact model;
- exact runtime (Ollama/LM Studio/etc.);
- runtime version;
- provider adapter;
- wire protocol;
- tool namespace/call encoding;
- structured-output behavior;
- context settings;
- streaming semantics;
- timeout/retry settings.

## Sources

- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/model-provider-info/src/lib.rs
- https://github.com/openai/codex/issues/30994
- https://github.com/openai/codex/issues/42488

---

# 15. Cancellation targets the process group, not only the async task

Current execution source provides a strong process-custody reference.

## Observed cancellation behavior

For spawned command execution, Codex handles several termination paths:

- timeout;
- explicit cancellation;
- Ctrl-C / interrupt.

The cancellation path can:

1. signal the process group for termination;
2. give TERM-aware programs a grace window to clean up;
3. escalate to killing the process group/child when required.

Timeout/interrupt paths also kill the process group rather than only dropping the parent future.

## Pipe/output settlement

Stdout/stderr reader tasks have bounded drain behavior. If output pipes do not close, the runtime can abort the reader task rather than allowing an orphaned pipe to hang completion indefinitely.

The runtime continues reading output to avoid child-process backpressure even when user-visible capture is bounded.

## ACL/Vera invariant

> **Cancel the effect tree, not merely the coroutine that started it.**

For local coding workers, cancellation needs an execution lease/process/job identity that can terminate descendants and prove settlement.

However, process-group death still does **not** roll back:

- files already written;
- Git refs already changed;
- network requests already sent;
- remote APIs already mutated;
- database effects already committed.

Therefore Codex process settlement complements, but does not replace, ACL’s external-effect ledger and uncertain-after-crash state.

## Source

- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/exec.rs

---

# 16. Telemetry is evidence, not acceptance authority

Codex has an OpenTelemetry layer with:

- logs;
- traces;
- metrics;
- session metadata;
- W3C trace propagation;
- explicit shutdown/flush support.

Current configuration allows logging user prompts into traces but defaults that sensitive behavior off.

## ACL/Vera lesson

This reinforces two separate requirements:

1. runtime telemetry should be rich enough to reconstruct lifecycle and correlate parent/child work;
2. evidence audience/privacy rules must be explicit because prompts/tool inputs/environment details may contain secrets.

This task did **not** find a promptfoo-like independent acceptance/evaluation subsystem inside Codex itself. Codex has extensive regression/integration testing and useful runtime telemetry, but that is not the same as an independent verifier deciding whether an ACL task passed.

That preserves the earlier campaign conclusion: the system under test should not be the sole authority defining its own success.

## Source

- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/otel/README.md

---

# 17. Cross-cutting failure patterns

Codex’s recent fixes/issues reinforce several boundary classes already seen in Cline, LangGraph, promptfoo and Strands.

## 17.1 Correct policy, lost adapter state

Example: denied-read paths not surviving a Windows sandbox bridge.

**Invariant:** test the realized child authority, not only the parent policy object.

## 17.2 Parent capability copied into incompatible child

Example: experimental context inherited across child model switch.

**Invariant:** recompute child capabilities from exact child runtime/model; authority inheritance and capability inheritance are separate.

## 17.3 Approval outlives authorization evidence

Guardian hardening invalidates/rejects review reuse when root authorization context changes or required checkpoint evidence is missing.

**Invariant:** approval binds to a versioned authorization snapshot.

## 17.4 Workspace isolation mistaken for secret isolation

Managed worktrees may intentionally copy ignored secrets.

**Invariant:** secret projection is explicit and least-privilege per worker/run.

## 17.5 Provider compatibility hides tool-contract mismatch

Open Ollama/custom-provider tool namespace failures show a model can be API-compatible while tool encoding still differs.

**Invariant:** capability includes the full model/runtime/adapter/tool protocol tuple.

## 17.6 Transcript continuity mistaken for execution continuity

Fork/resume semantics explicitly mark in-progress interruption instead of silently presenting partial work as completed.

**Invariant:** incomplete execution remains visibly incomplete.

## 17.7 Async cancellation mistaken for effect settlement

Codex kills process groups and drains pipes, but process death cannot undo external side effects.

**Invariant:** process custody and external-effect custody are separate.

---

# 18. Candidate ACL/Vera invariants from Codex

These are **research candidates**, not governance changes made by this task.

1. **Parent authority ceiling** — child roles/configuration may narrow authority but cannot widen parent sandbox, provider, MCP, network or approval authority.
2. **Child capability recomputation** — recompute model/runtime capabilities after child model/provider changes; do not clone parent feature activation blindly.
3. **Control-plane roots** — protect Git metadata, ACL policy/config, agent definitions, verifier fixtures and evidence roots inside writable projects.
4. **Approval/sandbox orthogonality** — unattended execution and full authority are separate knobs.
5. **Fail-closed missing approval** — if a required approval cannot be requested, deny rather than auto-allow.
6. **Narrow durable approvals** — never persist generic shell/interpreter/package-runner prefixes as broad trusted capabilities.
7. **Versioned authorization evidence** — approval validity includes task/objective/instruction/verified-answer version, not merely command text.
8. **Compaction-safe authorization** — context reduction cannot silently erase the evidence required to prove an approval is still valid.
9. **Reviewer least privilege** — validation/review workers receive only the minimum tools/extensions required for review.
10. **Adapter realization tests** — verify deny/read/write/network/environment semantics after every OS/container/sandbox bridge.
11. **User-owned trust exceptions** — symlink/path/security exceptions are top-level operator settings, never repository-controlled authority escalation.
12. **Workspace != secrets** — worker workspace creation has a separate explicit secret/ignored-file projection manifest.
13. **Workspace identity != Git branch** — each run/worker has stable workspace identity and source-baseline evidence.
14. **Versioned runtime protocol** — persist the exact schema/runtime version that gives authority/state fields their meaning.
15. **Explicit overload/backpressure** — bounded supervisor queues should fail/retry explicitly rather than buffer indefinitely.
16. **Owned restore state** — resume may use only thread/run-owned settings/checkpoints, not arbitrary matching historical values.
17. **Visible interruption** — forks/recovery from partial work include explicit interruption/uncertainty state.
18. **Mutation idempotency** — create/import/enqueue APIs need caller-stable idempotency IDs.
19. **Retirement != destruction** — logical project/task deletion has a separate evidence/workspace/file retention contract.
20. **Scoped provider profiles** — local/provider setup does not mutate unrelated/global provider/model selection.
21. **Full local capability tuple** — benchmark model + runtime + adapter + protocol + tool encoding + context/stream settings.
22. **Process-tree custody** — cancellation targets child process groups/jobs and has bounded pipe/output settlement.
23. **Process settlement != external-effect settlement** — external side effects need idempotency/reconciliation/effect evidence.
24. **Sensitive telemetry opt-in/minimized** — user prompts/tool data have explicit audience/redaction policy.
25. **Independent acceptance** — Codex runtime evidence may feed ACL validation, but Codex itself should not be the sole definition of pass/fail.

---

# 19. ACL regression-fixture ideas derived from Codex

These are test ideas for later implementation work, not tests executed in this research branch.

## Authority composition

- Malicious child-role fixture attempts to set danger-full-access, approval never, attacker provider URL, attacker MCP server, network widening and notification command; assert parent authority survives and only allowed behavior/model reductions apply.
- Child switches to a model lacking a parent-active feature; assert capability is recomputed and feature is disabled.
- Parent changes sandbox/approval/cwd after initial config snapshot; newly spawned child receives current live authority, not stale startup values.

## Permission realization

- Workspace-write fixture asserts source file write succeeds while `.git`, `.codex`, `.agents`, ACL policy and protected verifier roots remain unwritable.
- Adapter bridge fixture carries deny-read and deny-write paths through every supported Windows/Linux/container execution adapter and probes actual child access.
- Unknown permission/config token fixture must fail closed or produce explicit unsupported configuration rather than widening.

## Approval provenance

- Approve action under task/instruction version A, mutate root objective or verified answer to version B, retry same action; prior approval must be stale.
- Compact history after approval; if required authorization evidence cannot be reconstructed, approval must fail closed.
- Fork child history and assert parent-only Guardian/reviewer approval state is not silently inherited.

## Worktrees/secrets

- Spawn two parallel workspaces from one source commit; prove uncommitted writes do not cross working directories.
- Secret projection fixture copies only declared credentials; unlisted `.env`/ignored secret files must remain absent.
- Cleanup fixture snapshots workspace before deletion and proves restore identity; external effect records remain separate.

## Local providers

- Enable Ollama in one worker/profile; verify unrelated project/global OpenAI provider selection remains unchanged.
- Dotted/namespaced tool-call fixture against local/custom provider verifies router normalization or explicit incompatibility.
- Freeze exact Ollama version/model/context/tool schema and compare tool-call encoding to cloud provider baseline.

## Process custody

- Worker spawns child/grandchild processes; cancel run and prove process group/job tree is gone.
- Child holds stdout pipe open after parent exit; completion must not hang forever.
- Command performs filesystem/API effect then receives cancellation; process settles but effect ledger records committed/uncertain state rather than claiming rollback.

## Thread/recovery

- Resume from thread-owned cwd/settings snapshot; foreign/unowned matching historical snapshot must not override.
- Fork while source is mid-turn; fork must contain explicit interruption/partial marker.
- Duplicate create/import request with same idempotency key produces one logical project/task identity.

---

# 20. What Codex does not solve for ACL/Vera

Even if Codex later proves useful as a worker runtime, current evidence does **not** make it a replacement for:

- ACL’s outer project/backlog/dependency scheduler;
- authoritative cross-project task state;
- a durable external-effect ledger with reconciliation;
- independent acceptance/security verification;
- long-term Vera memory provenance/governance;
- dependency/supply-chain governance;
- deployment-specific sandbox image/network/credential policy;
- cross-worker distributed leases/fencing for ACL-owned persistent state;
- ACL’s local-model benchmark identity and model-role selection logic.

Codex is strongest in this research as a reference implementation for **runtime authority, child-session boundaries, workspaces, approval provenance and process custody**.

---

# 21. Assessment

## Strongest reusable ideas

### Very high value

- child roles cannot widen parent authority;
- hostile role/config regression tests;
- protected metadata roots inside writable workspaces;
- approval policy separated from sandbox authority;
- versioned root authorization evidence for approval reuse;
- compaction-safe/fail-closed review evidence;
- process-group cancellation and bounded pipe settlement;
- explicit fork interruption markers;
- thread-owned restore provenance;
- idempotency keys on persistent create/import operations.

### High value

- managed worktrees as per-chat/per-worker working directories;
- explicit secret projection distinction;
- bounded app-server queues/backpressure;
- local Ollama/LM Studio provider layer;
- version-matched protocol schemas;
- user-owned symlink trust exceptions;
- OTEL runtime telemetry with sensitive prompt logging disabled by default.

### Needs caution/current recheck

- local provider/profile scoping because #30994 remains open;
- custom/local tool namespace behavior because #42488 remains open;
- cross-platform sandbox adapter behavior because recent fixes show bridge regressions are realistic;
- subagent documentation wording around sandbox overrides because current role code/tests are more restrictive.

## Overall Task 10 conclusion

Codex remains a high-value ACL/Vera research reference. Its best evidence is not “Codex can code.” It is the amount of engineering devoted to **authority composition and state transition correctness** around the coding model:

- sandbox and approval are separate;
- protected control-plane roots survive inside writable workspaces;
- child roles are intentionally one-way with respect to authority;
- child model capability is recomputed separately;
- auto-review approval is tied to versioned root authorization evidence;
- worktree isolation is explicit but secrets remain a separate policy;
- thread/fork/resume state carries provenance;
- process cancellation targets descendant effects and output settlement.

At the same time, current open local-provider/tool reports and recent sandbox/Guardian fixes reinforce the campaign’s larger pattern: **the dangerous bugs live at boundaries between valid components**—policy to adapter, parent to child, approval to changed context, provider to tool router, workspace to secret projection, transcript to execution state.

No wholesale adoption decision is supported by this task. Later comparison should test Codex mechanisms against the ACL-specific authority, crash/replay, local-model, verifier and workspace fixtures already emerging from Pydantic AI, Cline, LangGraph, promptfoo and Strands.

---

# Primary source index

## Canonical / architecture
- https://github.com/openai/codex
- https://github.com/openai/codex/tree/6af345407d9c2a568da9d01b6c4b81a9e61495c0
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/app-server/README.md

## Permissions / authority
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/protocol/src/protocol.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/protocol/src/permissions.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/exec_policy.rs
- https://learn.chatgpt.com/docs/sandboxing
- https://learn.chatgpt.com/docs/permissions
- https://learn.chatgpt.com/docs/agent-approvals-security

## Children / roles / review
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/tools/handlers/multi_agents_common.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/agent/role.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/agent/role_tests.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/codex_delegate.rs
- https://github.com/openai/codex/commit/6af345407d9c2a568da9d01b6c4b81a9e61495c0
- https://github.com/openai/codex/commit/87628df77ab1a2622d1193ad835df02ced565bf2
- https://github.com/openai/codex/commit/4636819a352bfd4271c669c568a92f1bccfcd7e0
- https://learn.chatgpt.com/docs/agent-configuration/subagents

## Worktrees
- https://learn.chatgpt.com/docs/environments/git-worktrees

## Local providers
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/model-provider-info/src/lib.rs
- https://github.com/openai/codex/issues/30994
- https://github.com/openai/codex/issues/42488

## Process custody
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/core/src/exec.rs

## Telemetry
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/otel/README.md

## Symlink trust
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/config/src/codex_home_symlink.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/config/src/config_toml.rs
- https://github.com/openai/codex/blob/6af345407d9c2a568da9d01b6c4b81a9e61495c0/codex-rs/sandboxing/src/seatbelt.rs

---

## Stop boundary

Task 10 ends with this Codex research, catalog/watchlist/state updates and one research-only commit. **OpenHands has not been researched in this task.**
