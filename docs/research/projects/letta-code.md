# Letta Code Deep Research

**Task:** 18 — Letta Code  
**Campaign branch:** `research/agent-landscape`  
**Research date:** 2026-09-06  
**Starting ACL checkpoint:** `5366e7bd0b2402b3338679bd7c9fc2bb5556fe17`  
**Canonical upstream:** `letta-ai/letta-code`  
**Inspected upstream revision:** `701f2a5367828847313876c735ade27b9df97689`  
**Observed package/release:** `0.31.12` / `v0.31.12`  
**License:** Apache-2.0  
**Status:** deep research complete; no adoption, dependency, fork, architecture-winner, or benchmark decision made.

---

# 1. Scope and task boundary

This task evaluates Letta Code as a current stateful-agent harness, with emphasis on the parts most relevant to ACL and future Vera:

- persistent agent identity and memory;
- separation of agent, conversation, and runtime state;
- MemFS, Git-backed memory mutation, dreaming/reflection, and memory synchronization;
- memory provenance, conflict handling, and epistemic safety;
- context compaction, recall, transcript projection, and conversation forks;
- provider/local-model portability and context configuration;
- tools, permissions, secrets, trusted mods, subagents, cancellation, and retry;
- memory-worker confinement and realized sandbox behavior;
- App Server lifecycle/reconnect/protocol identity;
- trajectory import/evidence surfaces;
- current issue-scoped failure modes.

The task does **not** select Letta Code for Vera, redesign ACL/Vera governance, execute Letta workers, run benchmarks, or begin Gemini CLI research.

---

# 2. Executive assessment

Letta Code is one of the strongest **memory-specific architecture references** found in this campaign so far. Its distinctive contribution is not merely storing old chat text. It gives a persistent agent its own long-term, Git-backed memory filesystem, separates that state from individual conversation threads, supports background reflection/dreaming, and treats memory updates as mergeable state with explicit integration outcomes.

That architecture maps unusually well to the long-term Vera goal: one persistent assistant identity can have many conversations, devices, clients, and tasks without equating any one transport/session/thread with the assistant's identity.

The most valuable reusable ideas are:

1. persistent agent identity separate from conversation and runtime connection;
2. an agent-owned memory filesystem separate from recall/transcript history;
3. Git-backed memory history and concurrent reflection worktrees;
4. explicit reflection settlement states before updates count as integrated memory;
5. separate personal-agent and shared/project memory concepts;
6. memory/skills/trusted executable configuration as different state classes;
7. context compaction separated from canonical history and persistent memory;
8. request-addressed runtime protocol state for reconnect/approval flows;
9. secret references/substitution rather than putting plaintext into model context;
10. side-effect-aware subagent retry policy that refuses ambiguous replay.

The same research exposes several boundaries ACL/Vera should strengthen rather than copy directly:

- persistence is not truth;
- Git provenance is not epistemic provenance;
- newer evidence is not automatically more authoritative;
- learned memory must never silently become security policy or trusted executable configuration;
- configured sandboxing is not the same as realized sandboxing;
- Letta subagents currently inherit the parent process environment;
- runtime idempotency/request/event IDs are not an external-effect ledger;
- transcript projection defects can poison downstream reflection even if provider output was correct;
- restore and background-memory integration need transactional recovery semantics.

The correct research conclusion is **selective mechanism comparison**, not wholesale adoption.

---

# 3. Current project and version boundary

## 3.1 Canonical project

The canonical current repository is:

- https://github.com/letta-ai/letta-code

The repository was active and non-archived when inspected. Current package metadata identifies the project as Apache-2.0 and version `0.31.12`.

Task 18 inspected main at:

`701f2a5367828847313876c735ade27b9df97689`

The observed latest release was `v0.31.12`, published 2026-09-03.

Relevant package/runtime dependencies include:

- `@letta-ai/letta-client`;
- `@letta-ai/trajectory`;
- Model Context Protocol SDK;
- provider/model adapter machinery;
- Bun/Node runtime requirements.

### ACL implication

Letta capability should be versioned as an exact harness/runtime/provider configuration. `Letta Code` or `v0.31.x` alone is not sufficient evidence for behavior across memory, provider, tool, protocol, or sandbox surfaces.

---

# 4. The central architecture: agent identity is not a conversation

Letta's most important conceptual boundary is that a persistent **agent** is not the same thing as one conversation.

A useful simplified model is:

- `agent_id` — long-lived identity and memory owner;
- `conversation_id` — one bounded conversation/context thread belonging to that agent;
- runtime/App Server connection — one live execution/transport attachment;
- provider/model state — behavior-bearing execution configuration;
- filesystem/project state — separate external state;
- external effects — separately settled real-world actions.

Multiple conversations can belong to one agent while sharing the same long-term memory.

This is materially different from systems where the durable identity is essentially a saved chat thread.

## 4.1 Vera relevance

For Vera, these should remain distinct:

- Vera identity;
- person/user profile;
- household/project/shared memory;
- individual conversation;
- device/session connection;
- current task/run;
- provider/model runtime;
- action/effect identity.

A phone reconnect should not create a new Vera identity. A new conversation should not erase long-term identity. A task checkpoint should not become a personal-memory record merely because both persist.

### Candidate invariant

`AgentIdentity != ConversationIdentity != RuntimeSession != TaskRun != EffectIdentity`.

---

# 5. MemFS: persistent memory is its own state plane

The local MemFS prompt and current memory code show a deliberate separation between:

- in-context memory;
- agent-owned files outside immediate context;
- recall/full message history;
- current conversation messages;
- skills/procedures;
- trusted harness configuration.

One agent owns a persistent memory filesystem backed by Git.

The prompt describes `system/` memory files as automatically loaded into the system prompt on subsequent turns, while other memory files remain outside immediate context until read. The memory tree itself acts as a set of signposts for discoverability.

Relevant source:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/prompts/letta_local_memfs.md

## 5.1 Memory is not recall history

Letta retains full conversation/recall history separately from the memory filesystem.

This is a valuable distinction:

- recall/history answers: **what happened / what was said?**
- persistent memory answers: **what should the agent carry forward?**

For Vera, a raw source record should remain available even when a derived memory statement is compacted, revised, or superseded.

## 5.2 Memory mutations are future-facing

Current prompt semantics make memory changes apply on future turns/recompilation rather than magically rewriting the current context.

That prevents one memory edit from being confused with retroactive truth about the current model call.

## 5.3 Memory constraints

Current memory constraints include a versioned configuration and bounded depth/file-size defaults.

Source:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/memory-constraints.ts

### ACL/Vera implication

Memory needs bounded injection and bounded physical shape independently. Unbounded persistence can still create unusable prompt/context behavior even when disk capacity is ample.

---

# 6. Git-backed memory: strong history, incomplete truth model

Letta's use of Git for memory is a high-value design choice because it gives memory mutation:

- commit identity;
- historical versions;
- branch/worktree mechanics;
- diffability;
- merge/conflict behavior;
- rollback material;
- synchronization primitives.

This gives a better provenance substrate than opaque mutable key/value memory.

However, Git proves **what content was committed**, not whether the content was:

- true;
- correctly inferred;
- authorized;
- still current;
- derived from a trusted source;
- safe to use in a high-authority decision.

### Vera requirement

A durable memory record should eventually carry fields or linked evidence for concepts such as:

- source/evidence identity;
- source trust class;
- observed vs inferred;
- confidence;
- verification status;
- created/observed time;
- supersession/conflict state;
- applicability scope;
- sensitivity;
- retention/expiry where appropriate;
- whether the memory may influence security/financial/health/identity-critical actions.

The Git commit remains mutation provenance. It does not replace epistemic provenance.

---

# 7. Personal memory and shared/project memory are different authority domains

Letta's memory architecture distinguishes agent-owned memory from shared/organization memory concepts.

That is directly relevant to Vera.

Examples of distinct future Vera memory domains:

- personal identity memory;
- user-specific preferences;
- household/shared facts;
- work/project memory;
- temporary task memory;
- public/reference knowledge cache;
- trusted policy/configuration.

These should not be flattened into one namespace merely because all are retrievable text.

### Candidate invariant

Memory ownership and write authority are first-class fields. A project agent should not overwrite personal identity memory; a shared household record should not silently supersede a user-specific private preference.

---

# 8. Memory, skills, and trusted executable configuration must remain separate

Letta makes a useful conceptual distinction among:

- memory — learned facts/preferences/context;
- skills — reusable procedures/instructions;
- mods/configuration — executable or control-plane behavior.

Current Letta prompts describe mods as **trusted local code** that can register tools, providers, commands, lifecycle events, permission overlays, panels, and other behavior.

That makes mods qualitatively different from memory.

### ACL/Vera rule

`LearnedMemory != TrustedCode != SecurityPolicy`.

A memory worker may suggest that a new integration, rule, or automation is useful. It must not silently convert that learned suggestion into:

- new executable code;
- expanded filesystem/network authority;
- new credentials;
- changed approval rules;
- modified verifier code;
- altered security policy.

Agent-editable trusted code/configuration needs a separate deployment lifecycle with provenance, review/authorization, protected roots, versioning, tests, rollback, and policy revalidation.

---

# 9. Dreaming/reflection is a background state-integration problem

Letta can run background memory workers that inspect trajectories/conversations and consolidate memory.

This is one of the most directly Vera-like mechanisms in the research queue.

A future personal assistant cannot keep every historical interaction in active context. It needs background consolidation that can:

- identify durable facts/preferences/patterns;
- revise stale beliefs;
- reduce duplicated memory;
- preserve useful evidence links;
- avoid turning transient conversation into permanent identity.

## 9.1 Reflection worktrees

Current `src/agent/memory-worktree.ts` uses separate Git worktrees/branches for memory reflection and explicit finalization outcomes.

Observed settlement states include:

- `merged`;
- `no_changes`;
- `parent_dirty`;
- `merge_conflict`;
- `dirty_uncommitted`;
- `failed`.

Source:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/memory-worktree.ts

This is strong reference material because the system does not treat “the reflection model produced text” as synonymous with “memory was safely integrated.”

## 9.2 Transcript settlement

The current implementation only treats successful integration states as consuming the reflection input/trajectory. Failed integration remains retryable rather than silently pretending memory was updated.

### ACL/Vera reusable pattern

A background memory mutation should have an explicit lifecycle such as:

`proposed -> staged -> committed -> integration_pending -> integrated`

with explicit alternatives:

`rejected | conflicted | dirty | failed | uncertain`.

A transcript should not be marked “learned” until the authoritative memory store confirms settlement.

---

# 10. Epistemic safety: newer evidence is not automatically better evidence

Open issue #4029 provides unusually useful evidence because it focuses not on storage corruption but on **memory judgment**.

The issue reports controlled reflection tests where action-oriented conflicts performed better than restraint-oriented conflicts, including examples where newer content could drive unsafe or overconfident replacement/merging.

Source:

- https://github.com/letta-ai/letta-code/issues/4029

Current reflection prompt:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/subagents/builtin/reflection.md

This should be treated as issue/evaluation evidence, not proof every Letta deployment produces those failures.

The architectural lesson is stronger than the exact score:

> chronological recency is not an authority hierarchy.

Examples:

- a joking statement should not overwrite a repeatedly verified preference;
- an injected webpage should not overwrite a user-provided security rule;
- an uncertain observation should not overwrite verified identity information;
- a one-off anomaly should not automatically become a permanent habit;
- newer unverified medical/financial/security content should not supersede trusted evidence merely because it is newer.

### Candidate Vera memory rule

Conflict resolution should consider provenance, trust, confidence, verification, domain risk, and evidence strength before recency.

Safety-, security-, identity-, credential-, legal-, health-, or financial-critical memories may need stronger confirmation or separate source-of-truth integration.

---

# 11. Memory confinement and the realized-sandbox distinction

Task 18 found an important difference between two related Letta memory-worker paths.

## 11.1 Exported memory-confinement API

`src/memory-confinement.ts` and its launcher are designed for unattended memory workers and require a supported kernel sandbox. This surface fails closed when a required sandbox backend cannot be realized.

Sources:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/memory-confinement.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/permissions/memory-confinement-launcher.ts

## 11.2 Internal memory-subagent launcher

The ordinary internal memory-subagent sandbox path behaves differently.

Current `src/agent/subagents/sandbox.ts` attempts to provide an appropriate filesystem sandbox for `memory-subagent` launches, but if sandboxing is disabled, unavailable, or no appropriate writable root can be determined, the launcher can warn and proceed without that filesystem sandbox.

Source:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/subagents/sandbox.ts

Therefore the blanket statement “Letta memory agents always fail closed without a sandbox” would be inaccurate.

### ACL invariant

`ConfiguredSandbox != RealizedSandbox`.

Production unattended memory workers should have an explicit required-isolation profile. If that required profile cannot be realized, ACL/Vera should fail closed rather than silently degrade to host authority.

---

# 12. Cross-agent memory protection is useful but not a complete sandbox

Letta includes explicit protection against one agent directly accessing another agent's memory paths.

This is valuable because per-agent memory identity should be enforced by code rather than by natural-language instruction.

But cross-agent memory guards do not automatically restrict:

- unrelated filesystem paths;
- shell process authority;
- network access;
- ambient credentials;
- external APIs;
- user account permissions.

### ACL implication

Memory namespace confinement should be one layer inside a broader process/filesystem/network/credential permission profile.

---

# 13. Context, compaction, recall, and memory are separate state classes

Letta retains full conversation history while active model context can be compacted/summarized.

This is the right architectural distinction for long-lived agents.

A compaction summary is useful for:

- preserving task continuity;
- reducing tokens;
- keeping recent context manageable.

It is not a canonical replacement for the source history.

### Vera invariant

`CompactionSummary != CanonicalEvidence`.

A compacted summary may omit wording, uncertainty, provenance, timing, or contradictory detail. It should never be the sole source used to rewrite authoritative historical evidence.

Durable learned memory should refer back to canonical evidence where feasible.

---

# 14. Transcript projection is part of memory integrity

Current local message projection code converts source model/provider events into projected stored/display records.

Relevant source:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/backend/local/local-message-projection.ts

The code maintains deterministic projected identities and parent/tool-call relationships and includes repair/cleanup logic for orphaned tool results.

That is valuable because action/result relationships are semantic state, not UI decoration.

## 14.1 Current reasoning projection issue #4247

Open issue #4247 reports reasoning chunks being joined with `"\n\n"`, which can alter token/word continuity.

Current main still contains the relevant `pendingReasoningContent.join("\n\n")` path at the inspected revision.

Source:

- https://github.com/letta-ai/letta-code/issues/4247

### Why this matters beyond UI

When a memory/reflection system learns from stored transcripts, projection defects can become persistent-memory defects.

The useful separation is:

`RawProviderEvidence -> CanonicalSemanticMessage -> StoredProjection -> UI/ReflectionInput`.

Each boundary needs tests. A pretty UI transcript should not automatically be treated as byte-faithful provider evidence.

---

# 15. Conversation forks and source/projection identity

Current local conversation forking code carefully operates across source and projected message boundaries.

Source:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/backend/local/local-conversation-fork.ts

This is useful reference material for ACL because a forked conversation/task should preserve logical ancestry without implying that external effects, workspace state, or approval state were cloned safely.

### Candidate invariant

Forking model context is not permission to fork/replay external effects.

---

# 16. Provider and local-model boundary

Letta Code is model/provider agnostic and supports multiple provider styles, including local/OpenAI-compatible paths.

Observed local/provider integrations include Ollama, LM Studio, llama.cpp/OpenAI-compatible endpoints, and cloud provider paths.

The important research conclusion is familiar from Tasks 6, 12, 13, 16, and 17:

`LettaSupportsProvider != VerifiedDeploymentCapability`.

A meaningful capability identity includes at least:

- Letta Code revision/package;
- backend mode;
- provider adapter;
- exact model/runtime endpoint;
- model artifact/revision where available;
- context window and model settings;
- dynamic toolset/tool schema;
- streaming/tool-call behavior;
- harness configuration;
- consuming client path.

---

# 17. Context-window propagation is a current regression fixture

Open issue #3132 reports that local-backend new conversations can fail to inherit an agent's configured `context_window_limit` and instead use a hardcoded `128000` fallback.

Source:

- https://github.com/letta-ai/letta-code/issues/3132

Current `src/backend/local/local-store.ts` still contains the `128000` legacy fallback and stores a top-level conversation context limit separately from other model settings.

Source:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/backend/local/local-store.ts

Task 18 did not rerun the current GUI/provider path, so it would be too strong to claim every current new conversation reproduces the original issue.

What is verified is the continuing **configuration propagation seam**.

### ACL benchmark implication

Requested model/context configuration must be compared with realized runtime/session configuration before a result is considered comparable.

---

# 18. Permission mode, tool visibility, and execution authority are separate

Letta exposes multiple permission modes and tool-availability controls.

Current behavior/documentation distinguishes concepts such as:

- unrestricted/yolo;
- standard;
- accept-edits;
- strict;
- explicit allow/deny patterns;
- toolset visibility/availability.

This maps well to an ACL rule already supported by Cline, Strands, Codex, Goose, and OpenHands research:

`ToolVisible != ToolAllowed != EffectAuthorized != ProcessCapability`.

Removing a tool schema from model context is useful context minimization. It is not an OS permission boundary.

Likewise, an approval mode does not automatically remove ambient shell/network/filesystem authority from a process that already has it.

---

# 19. Secrets: references are better than prompt plaintext

Letta's secret model uses names/references in model-facing flows and substitutes secret values at execution time. Current source includes result/stdout/stderr scrubbing paths.

This is a useful pattern for Vera integrations because the model does not need reusable plaintext credentials simply to name a service or request an operation.

However:

- the execution process still receives plaintext at the moment it needs the credential;
- a process that can read/copy/exfiltrate that value cannot be made unaware of it later by redaction;
- logs/results must remain separate from credential authority;
- ambient process environment can defeat a narrower secret-injection model.

### Vera implication

Prefer brokered service operations or narrowly scoped runtime grants where possible. Where plaintext must be delivered, record that authority exposure as part of the effect/runtime state.

Do not persist plaintext credentials into memory.

Letta's own MemFS prompt explicitly warns against storing secrets in Git-backed memory.

---

# 20. Subagents: strong retry discipline, broad child environment

Letta subagents are launched as subprocess/headless agents.

Relevant sources:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/subagents/manager.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/subagents/subagent-launcher.ts

## 20.1 Capability shaping

Subagents can receive filtered tool sets and parent/session allow/deny constraints. Memory-only worker types can receive a narrower surface than ordinary coding agents.

This is useful model-facing minimization.

## 20.2 Retry is side-effect aware

The current launcher has an especially useful recovery pattern:

- certain provider incompatibilities may retry once;
- missing stream completion markers may allow a bounded retry;
- clearly truncated structured output may allow a bounded retry;
- ambiguous parse failures are **not** automatically retried because the child may already have performed side effects.

That is a high-value ACL invariant.

### Candidate rule

`UnknownOutput != SafeToReplay`.

If execution status is ambiguous and a child may already have changed files, called APIs, or launched processes, retry requires reconciliation/idempotency evidence rather than optimism.

---

# 21. Subagent child environment conflicts with ACL's stronger credential rule

Current `subagent-launcher.ts` begins child environment construction from the parent process environment and then applies Letta-specific variables.

This means a subagent can inherit unrelated ambient environment values from the supervisor process.

For ACL, that should remain a rejected production pattern.

### ACL invariant

Child worker processes receive a **minimal explicit environment**, not `{...parentEnv}` with selective additions/removals.

Model/tool filtering does not provide credential least privilege if the subprocess already inherits unrelated secrets.

---

# 22. Subagent cancellation is not process/effect settlement

Current subagent management can send `SIGTERM` to the child process.

This is useful cancellation intent, but it does not establish:

- all grandchildren exited;
- remote/provider work stopped;
- filesystem/API effects were rolled back;
- buffered output/evidence settled.

### ACL rule

Cancellation needs separate evidence for:

1. cancellation requested;
2. direct child exited;
3. owned process tree settled;
4. remote work settled or timed out;
5. external effects reconciled;
6. evidence channels closed/flushed.

---

# 23. Stateless subagent retention issue #3523

Open issue #3523 reports that subagents described as stateless can leave persistent agent/stub state after their subprocess work ends, especially under repeated reflection use.

Source:

- https://github.com/letta-ai/letta-code/issues/3523

Task 18 did not independently execute the current system to reproduce the leak, so this remains an issue-scoped lifecycle/retention fixture.

The broader lesson is important:

`StatelessModelContext != NoPersistentRuntimeRecord`.

ACL should give temporary children explicit retention/retirement semantics rather than infer cleanup from a conceptual label.

---

# 24. App Server protocol: useful runtime identity, not an effect ledger

Letta's App Server protocol is a valuable remote-client/runtime reference.

Current Protocol V2 types include runtime scoping and event/request metadata such as:

- `agent_id`;
- `conversation_id`;
- event sequence;
- emission time;
- idempotency key;
- stable request IDs for control flows.

Source:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/types/protocol_v2.ts

This is useful for Vera because clients can reconnect to a persistent assistant runtime without making the UI/client the authoritative owner of state.

## 24.1 Useful runtime pattern

A future Vera phone/watch/desktop client could:

- connect;
- resolve persistent assistant + conversation identity;
- synchronize visible state;
- receive pending approval/control requests;
- disconnect/reconnect without redefining the assistant identity.

## 24.2 Boundary

Protocol/event/request idempotency does not automatically prove an external action happened exactly once.

An App Server `idempotency_key` belongs to a runtime/protocol contract unless explicitly bound to a durable ACL/Vera effect record and external reconciliation mechanism.

### Candidate invariant

`RuntimeIdempotencyKey != ExternalEffectSettlement`.

---

# 25. Connection cleanup and cancellation remain separate from task settlement

The runtime can own connection-scoped resources and request cancellation when no live subscribers remain.

That is good lifecycle hygiene.

It still should not imply:

- project task complete;
- process tree terminated;
- provider stream settled;
- action effects reconciled.

A disconnected Vera client must be able to reconnect and inspect authoritative task/effect state rather than infer it from transport closure.

---

# 26. Trajectory ingestion is powerful and dangerous

Letta integrates `@letta-ai/trajectory` and can normalize historical coding-agent sessions for later analysis/reflection.

This is strategically valuable to ACL/Vera because memory can learn from:

- its own prior runs;
- imported historical sessions;
- multiple harness/provider formats;
- past failures and corrections.

But an imported trajectory remains **data**, not authority.

A trajectory may be:

- incomplete;
- malformed;
- generated by a compromised or lower-trust harness;
- missing external-effect context;
- carrying prompt injection or adversarial content;
- incorrectly projected from raw provider output.

### Vera/ACL rule

Imported trajectories require provenance/trust labels and cannot silently become privileged memory, policy, or trusted executable configuration.

---

# 27. Current destructive restore bug #4195

Open issue #4195 is a particularly strong current failure surface because current main was cross-checked.

The reported memory-restore path can delete active memory before copying the replacement backup. If the backup is nested under the active memory path—or if the subsequent copy fails—the authoritative state can be left missing or partial.

Source:

- https://github.com/letta-ai/letta-code/issues/4195

Current implementation inspected:

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/cli/subcommands/memory.ts

The inspected revision still performs the destructive ordering relevant to the issue.

### High-value recovery invariant

Restore should use a transactional pattern:

1. validate source backup;
2. stage replacement in a separate path;
3. verify staged state;
4. establish recovery point for current state;
5. atomically switch authoritative root where possible;
6. verify postcondition;
7. only then retire old state.

Never destroy the only known-good current state before the replacement is known valid and durable.

---

# 28. Background reflection can commit but fail to settle parent memory — #4249

Open issue #4249 reports a Windows case where reflection commits in its worktree but the parent memory repo refresh/integration fails.

Source:

- https://github.com/letta-ai/letta-code/issues/4249

Current `memory-worktree.ts` contains the corresponding parent-refresh integration failure path.

This should remain issue-scoped evidence; Task 18 did not establish one universal root cause across all Windows/Git credential-manager configurations.

The architectural lesson is strong:

`ReflectionCommit != IntegratedMemory`.

A background memory worker needs separate evidence for:

- generated change;
- committed branch state;
- parent synchronization;
- merge/integration;
- authoritative store update;
- downstream visibility.

---

# 29. Reflection truth failure #4029 and storage failures are different categories

It is important not to collapse Letta's memory risks into one generic “memory bug” category.

They are distinct:

- **epistemic failure** — wrong/confabulated/overconfident belief consolidation (#4029);
- **projection failure** — stored transcript differs from intended semantic content (#4247);
- **integration failure** — reflection commit exists but parent memory not refreshed (#4249);
- **restore failure** — recovery operation destroys/loses authoritative state (#4195);
- **retention failure** — supposedly temporary child records remain (#3523);
- **configuration propagation failure** — context/runtime settings diverge (#3132).

ACL/Vera tests should preserve these categories so a memory model is not blamed for a filesystem bug and a Git merge is not blamed for a model's epistemic mistake.

---

# 30. Candidate ACL/Vera invariants from Task 18

The following are candidates for later synthesis, not governance changes made by this task.

1. Persistent assistant identity is separate from conversation identity.
2. Conversation identity is separate from runtime connection identity.
3. Task/run/effect identity remains separate from persistent agent identity.
4. Personal identity memory, shared/project memory, task memory, and policy/configuration are separate domains.
5. Memory ownership and write authority are explicit.
6. Recall/history and persistent learned memory are separate stores/semantics.
7. Context compaction summary is not canonical evidence.
8. Persistent memory mutation is not verified truth.
9. Every important memory should retain or reference provenance/evidence.
10. Memory conflict resolution uses trust/evidence/confidence/domain risk, not recency alone.
11. Safety/security/identity-critical memory requires stronger contradiction/confirmation policy.
12. Git commit history is mutation provenance, not epistemic authority.
13. Memory, skills/procedures, trusted executable config, and security policy remain distinct.
14. Learned memory cannot silently expand tool, filesystem, network, credential, or approval authority.
15. Agent-editable trusted code/config requires a separate deployment/review path.
16. Background reflection has explicit proposal/commit/integration/settlement states.
17. A transcript is not marked consumed/learned until its memory update settles or is explicitly rejected.
18. Failed/conflicted reflection remains visible/retryable rather than silently discarded.
19. Required memory-worker sandboxing is verified at runtime; missing required sandbox fails closed.
20. Configured sandbox and realized sandbox are separately recorded.
21. Cross-agent memory guards do not replace OS/process/network/credential isolation.
22. Child workers receive minimal explicit environments.
23. Secret references are preferable to model-visible plaintext.
24. Runtime-visible plaintext credential exposure is explicitly represented as authority.
25. Tool visibility, approval policy, validation, and process capability are separate.
26. Ambiguous subagent output after possible effects is not automatically retryable.
27. Child-process cancellation is not process-tree/effect settlement.
28. Temporary/stateless child retention semantics are explicit.
29. Raw provider evidence, canonical semantic messages, stored projection, UI representation, and reflection input are distinct representations.
30. Projected transcript correctness is security/memory integrity, not merely presentation quality.
31. Action/result parent relationships remain atomic durable semantic state.
32. Conversation fork does not authorize effect replay.
33. Exact provider/model/context/tool configuration is realized and recorded per run.
34. Requested context and realized context are separately verified.
35. Runtime request/event/idempotency identity does not replace the external-effect ledger.
36. Client disconnect/reconnect does not define task completion.
37. Imported trajectories remain untrusted data until provenance/trust is evaluated.
38. Restore stages and verifies replacement before destructive switch.
39. Background memory commit and parent-memory integration are separate settlement steps.
40. Memory failure classification distinguishes epistemic, projection, integration, restore, retention, and runtime-configuration failures.

---

# 31. Candidate regression fixtures

Later ACL/Vera implementation/benchmark work should consider fixtures derived from this task.

## 31.1 Identity and memory

- same agent, two conversations: durable memory shared, conversation context isolated;
- new runtime connection: agent identity/memory preserved without duplicating task state;
- two users/shared project: personal memory cannot overwrite private state through shared namespace;
- forked conversation: no duplicate external action authority inherited from context fork.

## 31.2 Provenance and truth

- newer low-trust statement conflicts with older verified memory;
- joke/speculation conflicts with high-confidence preference;
- malicious imported trajectory tries to rewrite protected identity/security memory;
- source memory is superseded but canonical evidence remains retrievable;
- contradictory memory remains unresolved rather than confidently merged.

## 31.3 Reflection settlement

- reflection produces no change;
- reflection produces clean commit and clean merge;
- parent memory dirty before merge;
- merge conflict;
- reflection leaves uncommitted files;
- remote refresh fails after branch commit;
- client crashes between commit and integration;
- retry uses same transcript identity without duplicate integration.

## 31.4 Sandbox and authority

- required memory sandbox unavailable -> fail closed;
- configured sandbox disabled through environment/config -> qualification fails;
- child attempts to read another agent's memory;
- child attempts to read unrelated home/repo paths;
- child environment contains decoy supervisor secret -> must not inherit it;
- memory worker attempts to modify trusted mod/policy/verifier root.

## 31.5 Restore

- backup inside current memory root;
- copy failure during restore;
- destination permission error;
- power/process crash before authoritative switch;
- verify old state remains recoverable until replacement passes validation.

## 31.6 Transcript/projection

- reasoning chunks split mid-word;
- tool call/result parent relationships survive persistence/reload;
- orphan result rejected/isolated;
- compaction summary differs from source wording but cannot overwrite source evidence;
- reflection receives canonical intended text, not corrupted UI projection.

## 31.7 Provider/local model

- agent configured for 32K starts a new conversation and realized context remains 32K;
- provider switch mid-conversation preserves semantic state without silently changing tool capability assumptions;
- local OpenAI-compatible endpoint lacks one required feature -> profile fails qualification rather than optimistic fallback.

## 31.8 Subagent retry/cancel

- truncated stream before any effects -> one bounded retry allowed;
- ambiguous parse after possible filesystem write -> no automatic replay;
- child SIGTERM -> verify process tree settlement separately;
- temporary child retires persistent metadata according to explicit policy.

## 31.9 App Server

- reconnect with same agent/conversation -> state sync correct;
- duplicated request ID/idempotency key -> no duplicate protocol mutation;
- duplicated protocol request that wraps external effect -> effect ledger still independently reconciles;
- disconnect during pending approval -> approval remains addressed to stable logical request.

---

# 32. What Letta Code does not solve for ACL/Vera

Even if Letta memory mechanisms are reused, Letta Code does not automatically provide the complete ACL/Vera control plane.

Task 18 found no basis to treat it as replacing:

- ACL project scheduler/dependency graph;
- authoritative external-effect ledger;
- exactly-once/reconciliation machinery;
- durable distributed writer fencing for all ACL state planes;
- independent verifier/pass-fail authority;
- hardened minimal child environment policy;
- cross-platform process-tree custody for every tool/subagent;
- Vera credential vault/broker and service-specific grants;
- Vera epistemic memory provenance/truth policy;
- protected governance/configuration deployment path;
- complete workspace checkpoint/recovery system;
- production network/auth policy for all deployment modes.

Its memory architecture is therefore a **component/reference candidate**, not a substitute for ACL/Vera governance.

---

# 33. Later comparison questions

When the campaign reaches component synthesis, compare Letta mechanisms against prior and later candidates with questions such as:

1. Can Letta's MemFS be reused independently of the full Letta harness/runtime?
2. Is Git-backed memory preferable to a database/event-store model for Vera's personal memory, or should Git only back curated memory artifacts?
3. Which memory fields must exist outside free-form files to support provenance/confidence/verification?
4. Should Vera background reflection use worktrees/branches or a transactional database staging model?
5. Can Letta's reflection settlement model coexist cleanly with ACL checkpoints/effect state?
6. How should personal memory and shared/project memory authorize cross-domain reads/writes?
7. Which memory facts require user confirmation versus background consolidation?
8. What memory classes can be safely written autonomously?
9. Which Letta provider/local-model paths qualify under the user's 32K benchmark baseline?
10. Can App Server protocol ideas simplify Vera mobile/watch/desktop clients without importing Letta's whole runtime?
11. Which runtime IDs are useful for observability versus durable business/effect identity?
12. Does trajectory normalization add enough value to become an ACL evidence-ingestion component?
13. What sandbox/process wrapper is needed around Letta memory workers to satisfy ACL's stronger environment/authority rules?
14. How should trusted mods/configuration be fenced from learning/memory workers?
15. Which current issue surfaces are fixed upstream before any dependency decision?

---

# 34. Primary source inventory

## Project/release

- https://github.com/letta-ai/letta-code
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/README.md
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/package.json
- https://github.com/letta-ai/letta-code/releases/tag/v0.31.12

## Memory / MemFS / constraints

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/prompts/letta_local_memfs.md
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/memory-constraints.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/memory-worktree.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/subagents/builtin/reflection.md

## Memory confinement / subagents

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/memory-confinement.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/permissions/memory-confinement-launcher.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/subagents/sandbox.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/subagents/manager.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/agent/subagents/subagent-launcher.ts

## Local state / projection / fork / protocol

- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/backend/local/local-agent-record.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/backend/local/local-store.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/backend/local/local-message-projection.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/backend/local/local-conversation-fork.ts
- https://github.com/letta-ai/letta-code/blob/701f2a5367828847313876c735ade27b9df97689/src/types/protocol_v2.ts

## Current/open issue evidence

- Epistemic reflection/conflict handling: https://github.com/letta-ai/letta-code/issues/4029
- Destructive memory restore: https://github.com/letta-ai/letta-code/issues/4195
- Windows reflection parent-refresh failure: https://github.com/letta-ai/letta-code/issues/4249
- Reasoning projection joining: https://github.com/letta-ai/letta-code/issues/4247
- Local context-window propagation: https://github.com/letta-ai/letta-code/issues/3132
- Stateless-subagent retention: https://github.com/letta-ai/letta-code/issues/3523

---

# 35. Conclusion

Letta Code materially advances the campaign's understanding of what a persistent personal agent can look like.

Its strongest architectural contribution is the separation of a durable agent identity and memory from individual conversations and live runtime connections, combined with a Git-backed memory filesystem and background reflection workers that have explicit integration outcomes.

For Vera, that is a much better starting concept than treating “memory” as a giant chat transcript or a vector database full of undifferentiated snippets.

The equally important lesson is that **persistent memory needs a trust model**. Git can tell Vera what changed; it cannot tell Vera whether the new belief is true, safe, authorized, or stronger than the evidence it replaces. Reflection needs provenance and epistemic restraint. Memory workers need verified containment. Trusted executable configuration must remain separate from learning. Restore and integration need transactional settlement. Imported trajectories remain lower-trust evidence.

Accordingly, Letta Code should remain a high-value candidate for selective reuse or pattern extraction around MemFS, reflection settlement, identity separation, runtime protocol, secrets, and trajectory ingestion. No whole-project adoption decision is supported by Task 18.

**Task boundary preserved:** Gemini CLI research was not started.
