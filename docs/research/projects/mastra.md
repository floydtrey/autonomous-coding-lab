# Mastra — Task 31 Deep Research

**Task:** 31  
**Project:** Mastra  
**Canonical upstream:** `mastra-ai/mastra`  
**Research date:** 2026-09-07 (America/Chicago; upstream main crossed 2026-09-08 UTC during research)  
**Latest stable observed:** `@mastra/core@1.64.0` (release published 2026-09-04)  
**Current main inspected:** `685616780ea68e55c23c5980c17d5eee9a8f0aa9`  
**Current main core version:** `1.65.0-alpha.8`  
**Boundary:** research only. No Mastra adoption, implementation, 32K benchmark execution, ACL/Vera governance change, or unassigned next-project research is authorized.

## Executive assessment

Mastra is one of the broadest runtime platforms in the campaign. It spans ordinary agents, durable/evented agents, workflows, background tasks, workers/pubsub, tool approval, subagents, memory, observational memory, workspaces, sandbox providers, MCP, A2A, storage backends, scheduling, observability and evaluation.

For ACL, its strongest reusable ideas are not simply "agents in TypeScript." The highest-value mechanisms are:

- a first-class split between ordinary and durable/evented agent execution;
- persisted workflow snapshots with suspend/resume semantics;
- explicit durable-agent recovery and observable run identities;
- request-context-aware tool approval that can be restored with durable snapshots;
- explicit cleanup/stream-observation lifecycle;
- multiple sandbox providers behind a common workspace/sandbox interface;
- persistent storage domains for runs, workflows, memory, schedules, observability and evals;
- strong tracing/evaluation surfaces;
- explicit subagent memory isolation rules.

Mastra also exposes several high-value failure classes for ACL/Vera:

- open #22863: shutdown can dismantle pubsub/worker transport before in-flight evented work is drained, so "shutdown awaited" is not settlement;
- current durable-agent docs explicitly warn that recovery re-runs LLM and tool calls and that tools must be idempotent;
- those same docs state Mastra does not yet provide a distributed lease/lock for multi-replica durable recovery, so replicas can race to re-drive the same run;
- open #20148: channel thread creation is read-then-write rather than storage-atomic insert-if-absent;
- open #22188: PostgreSQL observational-memory initialization can create multiple generation-zero records for one lookup key under concurrency;
- open #19740: observational memory can reuse an already-ended turn in multi-step parent/subagent loops;
- current memory docs place working memory, cross-thread semantic recall and observational memory into system messages, so memory remains an instruction-injection/content-trust boundary;
- open #19911: default A2A handling lacks a first-class pre-agent execution gate, illustrating that agent-level tool approval and protocol-level invocation authorization are separate boundaries.

Mastra should therefore remain below ACL-owned task/effect identity, durable effect idempotency and reconciliation, external writer fencing, credential authority, sandbox policy, protected verifier state and independent acceptance. For Vera, its memory system is valuable reference material, particularly its separation of message history, working memory, semantic recall and observational memory, but those planes still require Vera-owned provenance, authenticated scope, trust/confidence and supersession policy.

## 1. Project and package identity

Latest stable observed core release:

- `@mastra/core@1.64.0`
- published 2026-09-04

Current main inspected:

- `685616780ea68e55c23c5980c17d5eee9a8f0aa9`
- current `packages/core/package.json` reports `1.65.0-alpha.8`

Mastra is a large monorepo with separately versioned packages. The 1.64.0 release alone lists independently versioned packages for memory, MCP, server, client, storage backends, sandbox providers, evals, observability, model/provider integrations and more.

### ACL implication

A future Mastra qualification manifest must pin every behavior-bearing package involved, not just `@mastra/core`.

At minimum:

- core commit/release;
- durable-agent/evented runtime profile;
- workflow engine profile;
- server/worker/pubsub profile;
- memory package and backend;
- sandbox provider/version;
- provider/model/router package;
- MCP/A2A package/profile;
- observability/eval packages;
- storage package/backend/schema.

## 2. Agent/runtime architecture

Mastra has multiple execution profiles:

- ordinary Agent `generate()/stream()`;
- durable agents;
- evented agents;
- Inngest-backed agents;
- subagents/supervisor patterns;
- workflows;
- background tasks;
- scheduled agent work;
- worker/pubsub-based evented execution.

These are materially different runtime identities.

A model result produced by ordinary in-process streaming is not interchangeable with the same model running through a durable/evented agent because the latter introduces:

- snapshots;
- pubsub;
- recovery;
- suspend/resume;
- persistent run status;
- stream observation/cache;
- cross-process execution possibilities.

### ACL invariant

> Runtime topology is benchmark identity, not incidental infrastructure.

## 3. Durable agents and continuation

Current durable-agent documentation provides several useful primitives.

A durable stream exposes:

- run ID;
- stream output;
- cleanup;
- observe/reconnect;
- persisted run status;
- recovery from persisted snapshots.

Resumable stream events use an in-memory cache by default; production deployments are advised to use persistent cache such as Redis so stream events survive process restart.

This is a useful separation:

- persisted execution snapshot;
- stream event cache;
- storage run status;
- in-process registry;
- external effect state

are different state planes.

### Cleanup ownership

Current docs state every `stream()` and `observe()` returns a `cleanup` function that unsubscribes from PubSub and removes the run from the internal registry. There is also an automatic timer after stream end.

This is a positive explicit resource-lifecycle pattern.

However, cleanup of observers/registries is not proof the underlying tool/process/external effect settled.

## 4. Recovery is at-least-once, not exactly-once

Current durable-agent docs contain an unusually explicit warning:

Recovery re-runs the agentic loop from the last snapshot, which re-issues LLM calls and re-executes tool calls; tools should be idempotent before automatic recovery is enabled.

This is one of the strongest explicit upstream acknowledgments in the campaign that durable resume is **at least once**.

### ACL implication

ACL must never derive exactly-once effect semantics from a resumable agent/workflow engine.

Required external mechanism:

- stable logical effect ID before execution;
- durable claim/ledger;
- idempotency key where supported;
- exact normalized request record;
- settlement state;
- reconciliation before replay.

## 5. Multi-replica durable recovery lacks built-in distributed fencing

Current durable-agent docs explicitly state:

Mastra does not provide a distributed lease or lock yet for multi-replica automatic durable-agent recovery. Every replica starting with automatic recovery can race to recover the same runs.

The documented workaround is to:

- gate recovery behind external leader election; or
- run recovery from a single replica.

This is directly relevant to ACL.

### ACL invariant

> Durable state plus restart logic is not sufficient for authoritative recovery. Recovery ownership needs lease/generation/CAS/fencing when more than one controller can act.

Mastra's explicit warning makes a strong regression/architecture fixture.

## 6. Shutdown and settlement — #22863

Open #22863 is a critical runtime fixture.

The issue reports that `Mastra.shutdown()` can:

1. stop workers/pubsub before active durable/evented work is drained;
2. stop PullTransport without awaiting in-flight routed work;
3. use a fixed 5-second background-task shutdown budget;
4. fail to track/drain ordinary evented workflow runs at all.

Task 31 corroborated current source signals:

- `Mastra.shutdown()` contains durable execution settlement logic;
- `BackgroundTaskManager` still exposes `SHUTDOWN_GRACE_PERIOD_MS = 5_000` in current main.

The issue remains open.

### Important distinction

- application received shutdown signal;
- stop requested;
- subscriptions removed;
- in-flight routing finished;
- workflow persisted final snapshot;
- background task terminated;
- tool effect settled;
- process can exit safely

are separate states.

### ACL regression fixture

Start an evented workflow whose next transition depends on pubsub, trigger shutdown mid-step, and require evidence that either:

- it fully settles before transport teardown; or
- it is persistently marked interrupted/uncertain and safely recoverable.

## 7. Cancellation, abort and durable-process boundaries

Current durable code comments explicitly acknowledge that process-local abort state is insufficient for cross-process durable engines.

This reinforces the same campaign rule:

> abort intent is not termination evidence.

For durable work, cancellation may require:

- durable cancellation state;
- worker delivery;
- process/tool abort;
- external-effect reconciliation;
- snapshot/update settlement.

The controller must not report "cancelled" solely because a local `AbortController` was signaled.

## 8. Workflows: suspend, resume and restart

Mastra workflows support:

- state schemas;
- persisted snapshots;
- suspend/resume;
- restart from active step;
- control flow;
- error handling;
- evented execution.

The workflow reference notes that snapshot transforms must preserve everything required to resume, including suspended payloads, suspended paths and execution path.

This is valuable explicit checkpoint-content thinking.

### ACL boundary

A workflow snapshot remains continuation state, not full ACL checkpoint authority.

ACL still needs to bind:

- workspace revision;
- effect ledger position;
- policy/verifier revision;
- credentials/service grants;
- sandbox/process state;
- model/runtime profile;
- artifact/evidence state.

## 9. Tool approval and request context

Mastra supports tool human-in-the-loop approval.

Regular agent calls can use function-based `requireToolApproval`, receiving:

- tool name;
- model arguments;
- request context;
- workspace.

This is strong reference material because approval can be based on host/request context, not only tool name.

Durable/stored agents must serialize their options, so function-based approval cannot simply be serialized. Current docs say those profiles accept a boolean at the outer option level.

However, the 1.64.0 release also fixed per-tool approval functions (`needsApprovalFn`) on durable agents and `agent.network()`: current durable runtime restores request context from the persisted run snapshot before evaluating the per-tool approval function.

### High-value ACL pattern

Persist the **facts needed to re-evaluate policy**, not a captured policy closure.

On resume:

- restore authenticated/approved request context evidence;
- load current trusted policy code;
- re-evaluate the exact pending effect under current policy.

### Boundary

Persisted request context itself must be integrity-protected and must not become a bearer credential.

## 10. Approval and effect identity

Current durable tool-call types persist approval decisions, including explicit declined state.

That is good typed state.

ACL still needs approval to bind:

- exact logical effect/tool call;
- normalized arguments;
- principal;
- service/tool origin;
- policy revision;
- objective/task;
- expiry;
- any mutable preconditions.

A generic run-level approval flag is insufficient for an irreversible effect.

## 11. A2A pre-execution authorization gap — #19911

Open #19911 documents an important protocol boundary.

The default A2A handler historically:

1. creates/loads task;
2. marks it working;
3. invokes the agent;
4. later marks completed/failed.

The issue requests a first-class gate before the target agent is invoked, using A2A `input-required` or related states.

This matters because:

- tool approval occurs after the agent starts;
- agent suspend occurs after invocation;
- protocol-level authorization may need to deny execution before any model/tool work starts.

### ACL/Vera invariant

> Remote-agent invocation authorization and downstream tool-effect authorization are separate gates.

A caller may be unauthorized to invoke an agent at all even if every tool the agent would use is individually safe.

## 12. Thread/resource memory identity

Current memory docs define:

- `resource`: stable identifier for user/entity;
- `thread`: specific conversation/session.

Threads have an owner (`resourceId`) that cannot be changed after creation.

This is a useful data-model separation.

However:

- resource/thread identifiers are partition identifiers;
- they are not proof of authenticated principal identity.

ACL/Vera should host-stamp them from authenticated context.

## 13. Non-atomic thread creation — #20148

Open #20148 documents an explicit read-then-write race:

- AgentChannels checks whether a resolver-provided thread ID exists;
- concurrent requests can both observe absence;
- both can write/upsert the same thread ID.

The requested fix is storage-level insert-if-absent semantics.

This is a strong cross-project pattern already seen in Mem0 and Agno:

> uniqueness belongs at the authoritative storage boundary.

### Vera relevance

Conversation/thread creation must use:

- database uniqueness constraint;
- atomic insert-if-absent;
- deterministic conflict result;
- no stale read-before-write assumption.

## 14. Memory planes

Mastra's current memory system explicitly separates:

- message history;
- working memory;
- semantic recall;
- observational memory;
- context messages;
- storage providers.

This is valuable for Vera.

### Message history

Raw conversation messages scoped by thread/resource.

### Working memory

Persistent structured user/project data.

### Semantic recall

Vector/semantic retrieval across prior messages.

### Observational memory

Background agents compress older message history into observations/reflections to reduce context pressure.

### Context messages

One-call context that is not saved to memory.

This is one of the clearest memory-plane decompositions in the campaign.

## 15. What the model sees is a trust boundary

Current memory docs state:

- working memory is injected as a system message unless state signals are used;
- same-thread semantic recall is inserted as messages;
- cross-thread semantic recall is formatted into a system message;
- observational memory reflections/observations live in a system message;
- raw old history may be replaced by observations.

This is extremely relevant to Vera.

Persisted or retrieved content does not become trusted instructions merely because the framework places it in the system channel.

### Vera invariant

> Prompt channel placement is a representation choice, not source authority.

Every recalled item should retain:

- source;
- principal/domain;
- evidence/provenance;
- trust/confidence;
- memory generation;
- temporal metadata;
- whether it is instruction-bearing policy or merely content.

## 16. Observational memory concurrency — #22188

Open #22188 reports PostgreSQL observational-memory initialization can create many generation-zero records for one logical lookup key under concurrency.

The reproduction executes initialization 24 times concurrently and obtains 24 stored rows.

The issue states:

- lookup-key index is non-unique;
- process-local locking cannot coordinate across independent storage instances/processes;
- reads become nondeterministic when duplicate generations exist.

This is a high-value writer-fencing fixture.

### ACL/Vera requirement

For generation-based memory:

- database uniqueness on logical key + generation;
- atomic initialize/advance;
- CAS or transaction on current generation;
- migration diagnostics for existing duplicates;
- no reliance on process-local lock for distributed deployments.

## 17. Observational memory turn lifecycle — #19740

Open #19740 reports multi-step parent→subagent→synthesis flows can reuse an already-ended `ObservationTurn`.

The next step calls into the ended turn and fails with "Turn already ended."

This illustrates that:

- message-list identity;
- observation-turn identity;
- agent step identity;
- parent/subagent stream lifecycle

must be distinct.

A component being reachable in memory does not mean it is still in a valid lifecycle state.

### Regression fixture

Force a subagent tool to emit finish/step-finish while the parent continues to another step and verify observational-memory turn lifecycle does not reuse terminal state.

## 18. Subagent memory isolation

Current docs provide explicit delegation behavior:

- each delegation gets a fresh thread ID;
- subagent resource ID is deterministic from parent resource + agent name;
- a subagent may inherit the supervisor's Memory instance/config;
- only delegation prompt + subagent response are stored by default;
- parent context is forwarded for execution but not fully persisted into the child thread;
- resource-scoped memory can persist across delegations.

This is sophisticated and useful.

### Boundary

Deterministic derived resource IDs are still namespace conventions, not authentication.

ACL/Vera should not authorize memory access from string construction alone.

## 19. Memory sharing is explicit but high-authority

Agents using the same resource ID can share:

- observations;
- working memory;
- embeddings.

Agents using the same resource + thread can share full message history.

That is useful collaboration behavior but dangerous if identifiers are model/user controlled.

### Vera invariant

Memory-sharing domains must be capabilities assigned by the host, not arbitrary string choices by agents.

## 20. Sandbox architecture

Mastra has a broad sandbox-provider ecosystem. The 1.64.0 release explicitly standardized `workingDirectory` across providers and listed providers including:

- Docker;
- E2B;
- Vercel;
- Railway;
- Modal;
- Daytona;
- Cloudflare Sandbox;
- Apple Container;
- AgentCore;
- Blaxel;
- platform workspace.

This is stronger than frameworks where code execution is just local Python/subprocess.

### Important caveat

A common interface does not create common security semantics.

Provider identity must include:

- filesystem mount/root;
- network policy;
- user/UID;
- secrets;
- CPU/RAM/time;
- process tree;
- persistence;
- snapshot/template;
- working directory;
- repo checkout provenance;
- cleanup behavior.

### Warm templates

1.64.0 added reusable sandbox templates and warm repo checkouts.

These improve performance but create new trust/provenance state:

- pre-cloned repository;
- pre-built dependencies;
- template image;
- rebuild schedule;
- artifact version.

ACL must treat template identity as executable environment identity.

## 21. Workspace and credentials

Mastra workspaces can carry repo/tool execution context into agents and approval callbacks.

For ACL this is useful, but workspace references must not become implicit authority.

Protected roots must stay outside worker mutation:

- policy;
- verifier tests;
- credential store;
- controller state;
- authoritative checkpoints.

Workspace and sandbox are related but not equivalent:

- workspace says what project resources are presented;
- sandbox says what the process can actually access/do.

## 22. Local models and Ollama

Current code/tests and docs support Ollama/model routing, including:

- Ollama embedding examples;
- custom OpenAI-compatible model router behavior;
- local endpoint forms.

Mastra's model layer sits heavily on provider/router abstractions and AI SDK compatibility.

### ACL implication

"Mastra supports Ollama" is nomination, not qualification.

Future local 32K testing must freeze:

- Mastra core commit;
- model-router/provider package;
- exact Ollama/runtime build;
- model digest/artifact;
- tool schema mode;
- structured output;
- context length;
- streaming;
- retry;
- provider URL;
- any model fallback/router behavior.

## 23. MCP

Mastra has a separately versioned `@mastra/mcp` package and core MCP exports.

That is meaningful interoperability support.

ACL still needs to separate:

- MCP server origin;
- transport;
- auth;
- tool definition/schema;
- one invocation;
- remote process/effect;
- local run/effect ID.

A model-facing MCP tool name is not sufficient authorization identity.

## 24. A2A

Mastra core exports A2A surfaces and has server-side A2A lifecycle.

Open #19911 demonstrates that protocol task lifecycle does not automatically provide application authorization before agent invocation.

Required ACL distinction:

- A2A authenticated caller;
- A2A task/context;
- remote agent/card/skill;
- local delegation;
- model invocation;
- external effects;
- local verifier result.

## 25. Storage is a broad authoritative plane

Current storage docs cover data for:

- workflows;
- memory;
- evals;
- background tasks;
- schedules;
- observability;
- durable agents.

Because multiple control/runtime features share storage infrastructure, backend capability is part of system identity.

A storage backend that supports ordinary CRUD is not automatically safe for:

- compare-and-swap;
- leases;
- atomic append;
- uniqueness;
- distributed lock;
- generation fencing.

Open #20148 and #22188 show why those distinctions matter.

## 26. Observability and evaluation

Mastra has extensive observability and evaluation support.

The 1.64.0 release added:

- feedback review status;
- API/storage/UI plumbing;
- `@mastra/evals/vitest`;
- `runEvals`;
- matchers/reporters;
- improved correlated tool logs and child spans.

This is directly useful to ACL's planned benchmark lab.

### Reuse candidates

- Vitest-style regression integration;
- score storage;
- per-test eval reporting;
- trace correlation;
- feedback review queues.

### Boundary

Model-as-judge/eval results remain stochastic evidence. Deterministic ACL verifier outcomes remain separately authoritative.

## 27. Telemetry/privacy

Mastra CLI docs note anonymous project-surface telemetry at server startup, including coarse counts of agents, workflows, tools, processors, vector stores, workspaces, MCP servers, gateways/channels and booleans for memory/voice/editor/observability usage.

This may be acceptable in normal deployments but must be explicit for offline/restricted environments.

### ACL implication

Offline benchmark profiles must verify:

- analytics/telemetry behavior;
- outbound network;
- update checks;
- provider discovery;
- remote observability exporters.

"Local model" does not prove the harness is fully offline.

## 28. Reproducibility profile

A future Mastra benchmark/deployment manifest should include:

### Core/runtime
- exact core commit/version;
- ordinary vs durable vs evented vs Inngest agent;
- workflow engine;
- worker/pubsub mode;
- server version.

### Model
- model/provider router;
- endpoint/runtime;
- model artifact;
- context settings;
- tool/structured-output mode;
- fallback/router settings.

### State
- storage backend/schema;
- durable snapshot profile;
- cache backend;
- recovery mode/leader ownership;
- memory package/config;
- resource/thread IDs;
- observational-memory generation.

### Security
- approval profile;
- request-context schema/source;
- workspace;
- sandbox provider/template;
- mounts/network/resources/secrets;
- MCP/A2A auth/origin.

### Evidence
- observability package/export;
- eval package/scorers;
- verifier version;
- effect ledger;
- cleanup/settlement evidence.

## 29. Candidate ACL/Vera invariants from Task 31

1. Ordinary and durable/evented agent runs are separate harness profiles.
2. Durable snapshot, event cache, run status and observer registry are distinct state planes.
3. Stream cleanup is not backing computation/effect settlement.
4. Recovery is explicitly at-least-once unless effect idempotency proves otherwise.
5. Recovery ownership in multi-replica systems requires external lease/fencing.
6. Every durable recovery records the owner generation/lease.
7. Shutdown drains work before dismantling transports needed for that work to finish.
8. Worker stop awaits in-flight routed callbacks or marks them explicitly uncertain.
9. Background-task shutdown grace is deployment policy, not a hidden universal constant.
10. Cancel/abort intent is separate from process/tool/effect settlement.
11. Workflow snapshot resume state is not a complete ACL checkpoint.
12. Snapshot serializer/transform must preserve all continuation-critical control state.
13. Persisted approval context is evidence, not a bearer credential.
14. Current policy is re-evaluated after resume before irreversible effects.
15. Approval binds exact effect/tool/args/principal/policy revision.
16. Agent invocation authorization and tool-effect authorization are separate gates.
17. A2A input-required/task state does not replace local authorization.
18. Thread/resource identifiers are namespaces, not authenticated principals.
19. Thread creation uses storage-atomic insert-if-absent.
20. Generation-based memory uses database uniqueness + CAS/transaction/fencing.
21. Process-local locks are not distributed writer fencing.
22. Observational-memory terminal objects are never reused after lifecycle completion.
23. Message history, working memory, semantic recall and observational memory are separate planes.
24. Prompt channel placement does not upgrade source trust.
25. Cross-thread recall is still lower-trust retrieved content even when rendered in a system message.
26. Observations/reflections are derived summaries, not primary evidence.
27. Subagent resource/thread isolation is host-enforced, not string-convention authorization.
28. Shared memory domains are explicit capabilities.
29. Workspace and sandbox are separate authority domains.
30. Common sandbox API does not imply common containment guarantees.
31. Sandbox template/image/repo checkout identity is executable environment identity.
32. Local inference and offline harness operation are separately verified.
33. MCP tool authority includes server origin + schema/version + args.
34. A2A completion is remote lifecycle evidence, not independent local acceptance.
35. Storage backend atomicity capabilities are explicit and tested.
36. Eval/observability data are evidence, not authoritative pass/fail.
37. Telemetry/network behavior is part of restricted/offline deployment identity.
38. Same model under different durable/recovery/memory/sandbox profiles is a different benchmark profile.
39. Harness/runtime failures are scored separately from model failures.
40. Vera epistemic memory retains provenance/trust/supersession outside framework memory convenience APIs.

## 30. Regression fixtures retained

### M31-01 — evented shutdown drain ordering
Source: #22863.  
Start evented work, trigger shutdown mid-step, verify required transport remains alive until work settles or run becomes explicitly recoverable/uncertain.

### M31-02 — background shutdown budget
Source: #22863/current `SHUTDOWN_GRACE_PERIOD_MS`.  
Long cleanup exceeds five seconds; verify deployment policy controls grace and settlement is not silently truncated.

### M31-03 — durable recovery duplicate effect
Source: current durable-agent docs.  
Crash after external tool succeeds but before next snapshot; recover and verify effect is not duplicated.

### M31-04 — multi-replica recovery race
Source: current durable-agent docs.  
Two replicas recover the same running durable run; require one lease/fenced owner.

### M31-05 — observer cleanup/resource ownership
Source: durable-agent docs.  
Open/close repeated observe/stream calls and prove pubsub subscriptions/registry entries are reclaimed.

### M31-06 — atomic channel thread creation
Source: #20148.  
Concurrent requests resolve to same thread ID; storage must report deterministic conflict without overwriting.

### M31-07 — observational-memory generation-zero race
Source: #22188.  
Concurrent initialization must create exactly one generation-zero row.

### M31-08 — observational-memory generation advance
Source: #22188.  
Concurrent reflection/advance attempts must not create duplicate generation N+1.

### M31-09 — ended observation-turn reuse
Source: #19740.  
Parent delegates to subagent then continues; terminal observation turn must not be reused.

### M31-10 — memory prompt-authority escalation
Source: current memory docs.  
Poison working/cross-thread/observational memory and verify it cannot gain deterministic tool/policy authority from system-message placement.

### M31-11 — memory sharing scope
Source: current memory docs.  
Model/user attempts to choose another resource/thread; host scope must override/deny.

### M31-12 — durable per-tool approval context restore
Source: 1.64.0 fix #22841/current durable runtime.  
Suspend approval, resume in another process, ensure authoritative request context is restored and policy re-evaluated correctly.

### M31-13 — stale approval after policy change
Source: derived from durable approval semantics.  
Change policy between suspend and resume; approval must be revalidated where policy requires it.

### M31-14 — A2A pre-execution gate
Source: #19911.  
Unauthorized A2A caller must be denied/input-required before target agent invocation.

### M31-15 — sandbox profile equivalence test
Source: 1.64.0 unified workingDirectory across providers.  
Same command under Docker/E2B/Vercel/etc. must not be considered same security profile merely because CWD behavior matches.

### M31-16 — warm template provenance
Source: 1.64.0 sandbox templates.  
Modify/rebuild template and prove benchmark identity changes.

### M31-17 — local Ollama 32K profile
Source: current router/Ollama support.  
Measure realized context/tool behavior rather than trusting provider support.

### M31-18 — eval/verifier separation
Source: `@mastra/evals/vitest`.  
Stochastic scorer passes while deterministic fixture fails; authoritative acceptance must remain failed.

## 31. Reuse candidates

### Strong candidates
- durable/evented run identity and snapshot architecture;
- explicit at-least-once recovery warning/semantics;
- suspend/resume tool approval;
- request-context-aware approval;
- observer cleanup lifecycle;
- workflow state schemas and snapshot transforms;
- separated memory planes;
- subagent memory isolation model;
- sandbox-provider abstraction;
- observability/eval integration;
- Vitest eval runner;
- protocol/event evidence.

### Reuse with stronger ACL controls
- automatic durable recovery;
- memory resource/thread scoping;
- observational memory;
- shared memory domains;
- sandbox warm templates;
- MCP/A2A exposure;
- background tasks/schedules.

### Do not delegate to Mastra
- distributed recovery fencing;
- effect idempotency/reconciliation;
- authenticated principal authority;
- credential brokerage;
- sandbox policy equivalence;
- checkpoint acceptance;
- independent verifier authority;
- Vera epistemic truth/provenance policy.

## 32. Explicit non-conclusions

Task 31 does **not** conclude that:

- Mastra should be adopted, rejected or forked;
- Mastra is more or less reliable overall than another researched framework;
- every open issue reproduces on every current package/backend;
- #22863 proves all shutdown paths always fail;
- #22188 generalizes to every storage backend;
- #19740 is present in every current memory package revision;
- system-message memory inevitably causes successful prompt injection;
- Mastra sandbox providers are insecure;
- unified sandbox `workingDirectory` means providers have identical security semantics;
- Mastra's durable recovery is unsuitable if external idempotency/fencing is supplied;
- Ollama support proves ACL's local models will work at 32K;
- Mastra Memory should become Vera's memory backend;
- Mastra evals should replace ACL's verifier;
- the next research project has been selected;
- Task 31 authorizes implementation or benchmark execution.

## 33. Primary sources

- https://github.com/mastra-ai/mastra
- https://github.com/mastra-ai/mastra/releases/tag/%40mastra/core%401.64.0
- https://github.com/mastra-ai/mastra/blob/685616780ea68e55c23c5980c17d5eee9a8f0aa9/packages/core/package.json
- https://github.com/mastra-ai/mastra/blob/main/docs/src/content/en/docs/harness/durable-agents.mdx
- https://github.com/mastra-ai/mastra/blob/main/docs/src/content/en/docs/workflows/overview.mdx
- https://github.com/mastra-ai/mastra/blob/main/docs/src/content/en/reference/workflows/workflow.mdx
- https://github.com/mastra-ai/mastra/blob/main/docs/src/content/en/docs/agents/human-in-the-loop.mdx
- https://github.com/mastra-ai/mastra/blob/main/docs/src/content/en/docs/memory/overview.mdx
- https://github.com/mastra-ai/mastra/blob/main/packages/core/src/agent/durable/durable-agent.ts
- https://github.com/mastra-ai/mastra/blob/main/packages/core/src/agent/durable/utils/resolve-runtime.ts
- https://github.com/mastra-ai/mastra/blob/main/packages/core/src/mastra/index.ts
- https://github.com/mastra-ai/mastra/blob/main/packages/core/src/background-tasks/manager.ts
- https://github.com/mastra-ai/mastra/issues/22863
- https://github.com/mastra-ai/mastra/issues/20148
- https://github.com/mastra-ai/mastra/issues/22188
- https://github.com/mastra-ai/mastra/issues/19740
- https://github.com/mastra-ai/mastra/issues/19911

## Stop point

Task 31 ends after current Mastra package/runtime identity, ordinary versus durable/evented agents, workflow snapshot/recovery behavior, shutdown/cancellation settlement, recovery replay and multi-replica fencing, tool approval/request-context restoration, memory planes and memory concurrency, subagent isolation, sandbox/workspace architecture, local-model routing, MCP/A2A boundaries, storage semantics, observability/evaluation and current 2026 failures were deeply researched.

The ranked project queue used by this campaign is now researched through Mastra. No new project/task was inferred or begun; await a separately assigned next research boundary.
