# OpenHands — deep research

**Task:** 11 — ranked project #7  
**Project:** OpenHands  
**Public control-center repository:** `OpenHands/OpenHands`  
**Canonical agent-runtime repository:** `OpenHands/software-agent-sdk`  
**Research date:** 2026-09-06  
**Runtime main examined:** `fe91d7dfc94d299e3751acb2b0c80ccbc582623c`  
**License:** MIT for the inspected OpenHands and software-agent-sdk repositories  
**Status:** active; research complete for this task; no dependency/adoption/fork decision made

## Why OpenHands is in scope

OpenHands is unusually relevant to ACL/Vera because it exposes a complete coding-agent execution stack rather than only an agent loop. During this research the public architecture had already separated into multiple repositories and responsibilities:

- `OpenHands/OpenHands` is the Agent Canvas/control-center product surface;
- `OpenHands/software-agent-sdk` owns the canonical Python SDK, Agent Server, tools, conversations, workspaces, events, REST/WebSocket API and browser-compatible TypeScript client;
- `OpenHands/automation` owns scheduling, webhooks, run history and dispatching;
- Agent Canvas consumes the TypeScript client and the Agent Server executes dispatched conversations.

That split overlaps directly with ACL's intended separation among operator/UI control, project/backlog orchestration, worker runtime, workspace execution and evidence.

The task is to extract mechanisms, failure surfaces and candidate ACL/Vera invariants. It does **not** decide whether ACL should adopt OpenHands, embed the Agent Server, reuse its workspace package, copy its persistence model, or use it as the primary local worker.

## Evidence discipline

Primary evidence was prioritized in this order:

1. current `OpenHands/software-agent-sdk` source and regression tests;
2. current `OpenHands/OpenHands` repository/license metadata where product identity mattered;
3. recent upstream issues/commits with deterministic reproductions;
4. maintainer design material when it explicitly described a desired future boundary.

Design proposals are labeled as such and are not treated as shipped guarantees. Open issues are failure evidence, not proof that every current installation is affected.

---

# 1. OpenHands is now a multi-repository system

## Observed

The current Software Agent SDK README explicitly assigns repository boundaries:

- SDK/Agent Server owns agents, tools, conversations, workspaces, events and runtime APIs;
- Agent Canvas is the UI/control surface;
- automation owns scheduling/webhooks/run history/dispatch;
- normal flow is Agent Server/SDK → OpenAPI → TypeScript client → Agent Canvas.

The SDK supports both:

- local-machine workspaces; and
- ephemeral/remote workspaces such as Docker or Kubernetes through the Agent Server.

## ACL/Vera relevance

This independently reinforces a pattern already seen in Cline and Codex: **the UI should not be runtime truth, and the model loop should not own project orchestration truth**.

A future ACL/Vera split can remain conceptually narrow:

1. project/backlog/supervisor control plane;
2. worker conversation/runtime plane;
3. isolated execution/workspace plane;
4. evidence/validation plane;
5. user/operator surfaces.

The OpenHands architecture is useful evidence for those seams without implying ACL needs the same package boundaries.

## Sources

- https://github.com/OpenHands/software-agent-sdk/blob/main/README.md
- https://github.com/OpenHands/OpenHands
- https://github.com/OpenHands/automation

---

# 2. Conversation state is explicit runtime state, not prompt text

## Observed

Current `ConversationState` persists validated runtime fields including:

- conversation ID;
- agent configuration;
- workspace;
- execution status;
- maximum iterations and stuck-detection settings;
- confirmation policy;
- optional security analyzer;
- activated skills/rules;
- blocked actions/messages;
- active conversation-tree HEAD (`leaf_event_id`);
- statistics;
- secret registry;
- tags;
- agent-specific durable state;
- hook configuration.

Execution status is explicit and includes states such as:

- `idle`;
- `running`;
- `paused`;
- `waiting_for_confirmation`;
- `finished`;
- `error`;
- `stuck`;
- `deleting`.

The event log is append-oriented while the conversation can have branches. `leaf_event_id` is the movable authoritative HEAD of the active branch. A derived `View` is rebuilt or incrementally replayed from that branch.

## ACL/Vera relevance

This is strong support for keeping worker lifecycle and history topology outside model prose. ACL should be able to answer deterministically:

- which logical run owns a task;
- whether it is active, paused, failed or settled;
- which event/effect branch is authoritative;
- which attempts are abandoned;
- what state a resume actually means.

Model-visible context may be condensed or rewritten; authoritative runtime state should not depend on the model correctly remembering it.

## Sources

- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/state.py
- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py

---

# 3. Branch-aware event history creates a real crash-recovery invariant

## Observed failure: issue #4487

A high-priority August 2026 failure is particularly relevant.

The failure window was:

1. an in-flight tool `ActionEvent` had been durably written;
2. the process died before `base_state.json` persisted the advanced `leaf_event_id`;
3. restart recovery used the stale HEAD;
4. the synthetic recovery error became a sibling of the tool action instead of its result on the active branch;
5. later context preparation saw a result without its originating action and raised `KeyError`;
6. subsequent turns repeatedly failed, leaving the persisted conversation unusable without repair.

The report reproduced the problem with real file-backed conversation state, lease takeover and follow-up execution rather than only mocks. The issue is now closed, but it exposes the important invariant.

## Reusable invariant

> Every tool result, rejection, recovery error or uncertain-effect record must remain linked to the exact originating action on the authoritative branch.

Persisting "an event happened" is not enough. A recoverable history must also preserve **relationship and branch identity**.

## ACL regression fixture

Simulate death after:

- action/event append succeeds;
- authoritative run/task/effect HEAD update has not yet committed.

On restart ACL should either:

- reconstruct the missing relationship from durable evidence and prove the active branch is valid; or
- mark the run/effect as recovery-required and block downstream work.

It must not fabricate a clean continuation.

## Source

- https://github.com/OpenHands/software-agent-sdk/issues/4487

---

# 4. Conversation leases provide a concrete single-writer/fencing model

## Observed

Current Agent Server uses `ConversationLease` with:

- `owner_instance_id`;
- monotonically increasing `generation`;
- expiry time / TTL;
- owner host;
- owner PID;
- file locking around claims, renewals and guarded writes.

A second owner cannot take a live lease. On a legitimate takeover the generation increments. A stale writer that no longer owns the current generation is rejected with `ConversationOwnershipLostError`.

Same-host process liveness can permit takeover before nominal TTL expiry when the previous owner is provably dead; ambiguous liveness is handled conservatively.

This mechanism directly addresses an earlier split-brain bug, issue #2966, where separate Agent Server processes could attach to the same persisted conversation path and resume active conversations.

## ACL/Vera relevance

This is one of the most directly reusable OpenHands patterns.

ACL has already identified the need for one authoritative writer for project/task/run state. OpenHands supplies concrete evidence that a useful ownership record contains at least:

- logical resource identity;
- owner identity;
- generation/epoch;
- expiry/renewal;
- guarded-write validation;
- takeover semantics;
- conservative handling of uncertain owner death.

## Candidate ACL invariant

> A worker that lost its lease/generation may finish local cleanup, but it may not commit authoritative task/effect/checkpoint state.

For distributed or remotely reconnecting Vera components, generation fencing is stronger than merely checking "is this process still marked running?"

## Sources

- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-agent-server/openhands/agent_server/conversation_lease.py
- https://github.com/OpenHands/software-agent-sdk/issues/2966

---

# 5. Startup recovery is selective, not "hydrate everything"

## Observed

`ConversationService` startup loads lightweight metadata rather than immediately hydrating every idle conversation.

Persisted conversations recorded as `RUNNING` receive special recovery handling because they may contain interrupted tool calls. Current source comments explicitly preserve this crash-recovery path while allowing idle conversations to remain lazy.

The service also uses a centralized lease-renewal loop and can evict idle conversations.

## ACL/Vera relevance

Long-running ACL does not need every project/worker fully resident in memory. Durable identity and summary state can remain cheap while active/interrupted runs receive stronger recovery scrutiny.

Candidate distinction:

- **known idle/settled:** lazily materializable;
- **known running at previous death:** recovery-required;
- **known interrupted/uncertain effect:** blocked until reconciled;
- **active owned:** fenced by current lease.

This supports the user's goal of many projects/backlogs without requiring every worker session to stay alive.

## Source

- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-agent-server/openhands/agent_server/conversation_service.py

---

# 6. Parallel tool execution uses declared-resource locking

## Observed

Current `ParallelToolExecutor` can run multiple tool calls concurrently in worker threads. It uses `ResourceLockManager` to serialize calls that declare overlapping resources such as files, terminal state or browser state.

The source is explicit about the contract:

- tools run in parallel threads sharing the same conversation;
- individual tools must correctly implement `declared_resources()` for resource locking to work;
- an undeclared resource path falls back to a tool-wide mutex;
- explicitly declared empty resources can run without locking.

## ACL/Vera relevance

This is useful because concurrency safety is not only "use a thread lock." The harness needs a **resource identity contract**.

Potential ACL resource identities include:

- project workspace/path;
- Git ref/worktree;
- terminal/process session;
- browser/profile;
- credential binding;
- external API object;
- shared task/checkpoint record.

A tool's resource declaration should be treated as privileged contract code, not model prose.

## Failure boundary

If a tool under-declares what it mutates, the concurrency layer cannot infer hidden shared state. Therefore resource declarations need tests and safe fallbacks.

## Source

- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/agent/parallel_executor.py

---

# 7. Open issue #4777: cancellation must be rechecked after waits

## Observed failure

Issue #4777 reports a deterministic race in `ParallelToolExecutor`:

1. cancellation is checked;
2. the tool waits for a resource lock;
3. the user interrupts while it is waiting;
4. the lock later becomes available;
5. execution proceeds because cancellation is not rechecked after the wait.

The result is particularly serious for coding agents: a queued file, terminal, browser or other resource operation can **begin after the user stopped the run**.

The report reproduced the issue on v1.44.1 and then-current main using the real cancellation token and resource lock manager. It remained open during Task 11.

## Reusable invariant

> Re-check authority/cancellation immediately before the irreversible boundary, especially after any blocking wait or lease acquisition.

Checking once before a wait is stale authorization.

This applies beyond cancellation:

- approval still active after queue wait;
- task still owns its lease after lock wait;
- dependency still valid after long planning/model call;
- workspace/ref baseline still matches before destructive restore;
- credential grant still valid before provider call.

## Candidate ACL fixture

Queue two conflicting file mutations. Cancel the second while it waits. Release the first lock. Assert the second never crosses the mutation boundary and emits a terminal cancelled effect record.

## Source

- https://github.com/OpenHands/software-agent-sdk/issues/4777

---

# 8. Current main demonstrates that cancelling async work does not stop blocking sync code

## Observed

The current runtime main inspected for Task 11 was commit:

`fe91d7dfc94d299e3751acb2b0c80ccbc582623c`

The commit adds failing/xfail regression tests specifically demonstrating that cancellation cannot free synchronous work blocked inside worker threads.

The tests document two manifestations:

- `AsyncExecutor.close()` can wait indefinitely on work blocked in a worker thread;
- an event-bus timeout can cancel the asyncio wrapper while the underlying blocking thread remains alive, creating zombie-thread accumulation.

The commit comments tie the production consequence to thread-pool exhaustion and stalled conversation creation.

## ACL/Vera relevance

This independently confirms the lifecycle rule already seen in Pydantic, LangGraph and Codex:

> Cancellation is a request; settlement is an observed state.

A task is not safely `stopped` merely because:

- its coroutine received `CancelledError`;
- the UI says cancelled;
- a timeout fired;
- the parent stopped awaiting it.

For local coding workers ACL needs process/thread/job custody and a terminal settlement record. For code executed in a killable subprocess/container, process isolation is preferable to uninterruptible in-process blocking work when hard cancellation matters.

## Source

- https://github.com/OpenHands/software-agent-sdk/commit/fe91d7dfc94d299e3751acb2b0c80ccbc582623c

---

# 9. Workspace transport and authority are separate concerns

## Observed

OpenHands exposes multiple workspace backends including:

- local;
- Docker;
- Apptainer;
- cloud;
- API-remote.

`DockerWorkspace` manages a containerized Agent Server and supports configuration for:

- host/container ports;
- forwarded environment variables;
- arbitrary volume mounts;
- Docker network selection;
- GPU exposure;
- platform;
- optional extra VS Code port;
- lifecycle cleanup/pause/resume.

Current defaults forward session/API-key-related environment variables required for the sandbox Agent Server to authenticate its network-bound requests.

## Security boundary

A Docker workspace is an **execution location**, not a complete authority policy.

The caller can still choose:

- what host paths are mounted;
- which environment values cross the boundary;
- which network the container joins;
- whether the GPU is exposed;
- which service ports are reachable.

Therefore "it runs in Docker" does not establish least privilege or secret isolation.

## ACL/Vera relevance

For ACL, worker provisioning should explicitly define a capability envelope before launch:

- workspace source projection;
- read/write/protected roots;
- environment projection;
- credential projection;
- outbound network policy;
- ports/services;
- CPU/RAM/GPU/process limits;
- lifetime and cleanup;
- evidence/output paths.

The workspace driver can implement that envelope, but should not define the policy implicitly.

## Sources

- https://github.com/OpenHands/software-agent-sdk/tree/main/openhands-workspace/openhands/workspace
- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-workspace/openhands/workspace/docker/workspace.py

---

# 10. Optional per-conversation Git worktrees separate workspace instances

## Observed

The Agent Server can prepare a conversation-specific Git worktree.

Current logic:

- validates the source as a Git repository;
- prefers an updated `origin/<default_branch>` start point when available;
- falls back to local `main`, then `master`, then `HEAD`;
- creates a conversation-specific branch/worktree;
- injects guidance telling the agent to remain inside the worktree.

## ACL/Vera relevance

This is useful operationally because multiple workers should not collide in one mutable checkout.

But the safety boundary remains important:

- a Git worktree is not a sandbox;
- a branch is not a worker identity;
- model guidance to stay inside a directory is not authorization;
- worktree state does not capture external API/network effects.

Candidate ACL design:

- task/run identity owns a workspace instance;
- workspace instance records source baseline and Git/worktree identity;
- worker process receives only that workspace path;
- filesystem enforcement prevents escape;
- merge/review is an explicit later operation.

## Source

- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-agent-server/openhands/agent_server/conversation_service.py

---

# 11. Confirmation policy exists, but confirmation is not sandbox authority

## Observed

OpenHands ships explicit confirmation policy types:

- `AlwaysConfirm`;
- `NeverConfirm`;
- `ConfirmRisky` with threshold and unknown-risk handling.

A `SecurityAnalyzerBase` can assign risk to action events. Analyzer errors are treated conservatively as high risk in `analyze_pending_actions()`.

The current `ConversationState` default confirmation policy is `NeverConfirm()` unless configured otherwise.

## Important boundary

The confirmation policy determines whether a proposed action requires user confirmation. It does not itself reduce OS/filesystem/network authority available to the underlying tool/workspace.

Likewise, a security analyzer classifies action risk; it is not a sandbox.

## ACL/Vera relevance

This supports the same separation found in Codex and Pydantic:

1. model proposes an action;
2. policy classifies/authorizes it;
3. optional approval can grant a narrow decision;
4. execution environment determines maximum real authority;
5. evidence records what actually happened.

No one layer should be treated as a substitute for the others.

## Sources

- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/security/confirmation_policy.py
- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/security/analyzer.py
- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/state.py

---

# 12. Credential history shows why redaction cannot be the primary security model

This is one of the strongest Vera-specific findings.

## Current design record: issue #4288

OpenHands maintainers published a consolidated design document for **reference-only credentials and safe runtime delivery**.

The corrected invariant in that design is conceptually important:

- outside the credential service, durable OpenHands state should contain credential references rather than secret values;
- runtime delivery can create bounded plaintext working copies in memory, environment or non-snapshotted storage;
- those runtime copies are not authoritative credential storage.

The design separates two delivery modes:

- **brokered:** runtime does not obtain the provider credential;
- **runtime_visible:** runtime receives plaintext because the consumer actually requires it.

It is explicit that arbitrary code in a runtime-visible sandbox can read/copy/exfiltrate that credential, and revocation cannot recall a value already delivered.

## Why the design exists

The issue catalogs multiple historical failure paths, including examples involving:

- credential-bearing conversation/schema state;
- trajectory export;
- MCP configuration/events;
- Git remote URLs echoed back to the agent;
- environment leakage across conversations;
- evaluation/log artifacts;
- plugin/extension URLs;
- sandbox/runtime key coupling.

The maintainer conclusion is architectural: adding an eighth redaction site does not solve a substrate that treats secrets as serializable ordinary configuration.

## Shipped-state caution

Issue #4288 is a **design document**, not evidence that all proposed credential-service/grant behavior is already shipped.

Current runtime code does include credential-binding and persisted-secret scrubbing paths, including removal of bound secrets from stored conversation/base-state material and runtime reauthorization mechanics. But the broader reference-only architecture should be treated as target design until verified in shipped code.

## ACL/Vera invariant

> Durable ACL/Vera task, memory, checkpoint and conversation state should carry credential references/capabilities, not reusable plaintext or portable ciphertext as ordinary fields.

When a worker genuinely requires a credential, record:

- which binding was delivered;
- to which run/runtime;
- permitted operation/target;
- delivery mode;
- version/expiry;
- delivery audit.

Do not claim runtime-visible material remains confidential from the worker.

## Source

- https://github.com/OpenHands/software-agent-sdk/issues/4288

---

# 13. Hidden host state can defeat a supposedly isolated persistence root

## Observed failure: issue #3815

Issue #3815 documented that setting `OH_PERSISTENCE_DIR` did not fully isolate Agent Server state.

LLM and agent profile stores still defaulted to `~/.openhands/...`, so a supposedly fresh test/server instance could silently inherit stale host-user model/base-URL settings and write them into the new persistence directory.

The issue was fixed/closed, but it exposes a broader requirement.

## ACL/Vera relevance

"Fresh workspace" and "fresh persistence directory" are meaningless if components can still read ambient state from:

- home directories;
- environment variables;
- global model caches/config;
- credential stores;
- OS keychains;
- shared browser profiles;
- provider SDK defaults;
- parent-process globals.

## Candidate ACL fixture

Launch a worker with a deliberately poisoned host/home configuration while providing a clean task/runtime state root. Assert the worker uses only explicitly projected profiles/configuration.

## Source

- https://github.com/OpenHands/software-agent-sdk/issues/3815

---

# 14. Provider abstraction uses explicit model metadata and capability overrides

## Observed

Current OpenHands `LLM` wraps providers through LiteLLM but adds its own control and metadata layer.

Relevant fields/mechanisms include:

- model ID;
- base URL;
- canonical model name for feature lookup;
- API mode selection;
- capability overrides;
- provider runtime metadata;
- retries/backoff;
- request timeout;
- maximum message characters;
- input/output token metadata;
- prompt/cache and feature flags.

Current source defines a minimum context-window expectation of 16,384 tokens unless explicitly overridden.

Capability overrides can represent features such as:

- reasoning support;
- sampling parameters;
- prompt cache behavior;
- responses API;
- vision;
- stop-word support.

## ACL/Vera relevance

This again validates the **ModelRuntimeCapabilityProfile** concept discovered in Pydantic/Cline/Codex.

The identity that matters is not only `model="X"`. It includes:

- model/quantization;
- runtime and version;
- provider adapter;
- endpoint mode;
- actual context limit;
- tool/function semantics;
- streaming behavior;
- timeout/retry behavior;
- capability overrides proven by tests.

## Source

- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/llm/llm.py

---

# 15. Open Ollama timeout issue shows configuration must be verified at the wire

## Observed failure: issue #4255

Issue #4255 reports that Ollama requests longer than five minutes were terminated at the default 300-second timeout even when users changed timeout settings through the UI/settings.

The report included an Ollama log showing a request ending at exactly five minutes and remained open during Task 11.

This is not evidence that every current Ollama path has the same bug, but it is strong boundary evidence: **configured timeout state and realized provider request behavior can diverge**.

## ACL/Vera relevance

ACL's local benchmark should probe runtime behavior rather than trusting configuration serialization:

- configured timeout actually reaches the adapter;
- context size actually reaches Ollama/llama.cpp;
- tool schema is actually supported;
- cancellation reaches the provider/process;
- stream termination is bounded;
- retry count at the harness matches underlying wire attempts.

## Source

- https://github.com/OpenHands/software-agent-sdk/issues/4255

---

# 16. Observability channels are deliberately separated by sensitivity and purpose

## Observed

The current Agent Server telemetry package explicitly distinguishes three different evidence channels:

1. **LLM completion logging** — high-fidelity prompts/responses written for debugging and privacy-sensitive by design;
2. **Laminar / OpenTelemetry tracing** — distributed traces for spans, latency and runtime analysis;
3. **product analytics telemetry** — small, versioned, allowlisted lifecycle/failure scalar events.

The product telemetry documentation states it should not contain prompts, messages, paths, secrets, request/response bodies or tracebacks.

## ACL/Vera relevance

This is a strong pattern for Vera's eventual observability design. "Telemetry" should not be one undifferentiated log stream.

Candidate audiences:

- worker-visible operational feedback;
- local operator diagnostics;
- independent verifier evidence;
- security audit;
- optional product/usage analytics;
- highly sensitive raw model/tool traces.

Each should have an explicit schema, retention policy, redaction policy and access boundary.

## Source

- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-agent-server/openhands/agent_server/telemetry/__init__.py

---

# 17. OpenHands has a critic/refinement layer, but it is not independent acceptance

## Observed

The SDK includes a `CriticBase` abstraction that can evaluate:

- conversation events;
- an optional Git patch;
- a success score/result.

An optional iterative-refinement configuration can automatically prompt the same conversation to retry when the critic score falls below a threshold.

This can be valuable for quality improvement.

## Boundary

The critic remains part of the runtime/agent stack. Depending on deployment it may share:

- runtime-owned event projections;
- workspace visibility;
- provider infrastructure;
- configuration controlled by the same application.

Therefore it is not automatically an independent acceptance authority.

## ACL/Vera relevance

Use a runtime critic for:

- self-correction;
- heuristic incompleteness detection;
- suggested retry.

Use ACL/promptfoo-style verifier-owned evidence for:

- regression acceptance;
- protected tests;
- security assertions;
- task completion gates;
- evidence the worker cannot rewrite.

## Source

- https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/critic/base.py

---

# 18. Repository instructions and persistent model-visible memory are trust inputs

## Observed

Current SDK prompt snapshots include a `<MEMORY>` section instructing the agent to use repository-root `AGENTS.md` as persistent repository-specific memory and to add important learnings there.

The SDK also supports skills/plugins and repository/project context that can affect future model behavior.

## ACL/Vera relevance

This is useful functionality but an important trust distinction:

- **worker-writable project memory** can help future work;
- **trusted ACL governance/authority** must not live in the same trust class.

If a worker can edit the file that future sessions treat as authoritative instructions, then persistence becomes a delayed self-modification/prompt-injection channel.

Candidate separation:

- trusted governance/policy: protected and operator-controlled;
- verified project facts: evidence/provenance-backed;
- worker observations/notes: writable, lower trust;
- external repository instructions: imported as untrusted project context unless explicitly promoted.

## Sources

- https://github.com/OpenHands/software-agent-sdk/tree/main/tests/sdk/context/prompts/snapshots
- https://github.com/OpenHands/software-agent-sdk/blob/main/AGENTS.md

---

# 19. OpenHands independently validates several earlier ACL research questions

This task did not perform a full cross-project winner comparison, but it is useful to record which prior questions received independent support.

## Independently reinforced

### Runtime state should be outside the model

OpenHands conversation/event/service state independently supports the Cline/LangGraph/Pydantic pattern that lifecycle, persistence and recovery are harness concerns.

### Single-writer/fencing is a first-class requirement

Conversation leases and prior split-brain issue #2966 strongly reinforce ACL's need for writer generations/leases rather than process-local assumptions.

### Persisted does not mean safely recoverable

Issue #4487 independently reinforces Pydantic StepPersistence and LangGraph findings: relationships, branch identity and side-effect state can still be inconsistent after a crash.

### Cancellation must settle real execution

Open issue #4777 plus current cancellation-deadlock regression tests independently reinforce the process/thread settlement lessons from Codex, LangGraph and Pydantic.

### Container/workspace abstraction is not authorization

DockerWorkspace configuration reinforces Strands/Pydantic/Codex findings that execution transport, mounts, environment, network and secrets require separate policy.

### Credential delivery is an authority decision

The reference-only credential design strongly reinforces the earlier rule that environment inheritance and serializable secret-bearing runtime state are dangerous implicit authority channels.

### Provider compatibility needs exact runtime capability evidence

LLM capability metadata and the Ollama timeout report reinforce the existing model/runtime/adapter/profile approach.

### Runtime telemetry is not independent acceptance

The critic and telemetry layers are useful, but promptfoo remains the stronger reference for verifier independence.

---

# 20. Highest-value OpenHands mechanisms for later comparison

These are **candidate mechanisms/invariants**, not adoption decisions.

1. **Control center / automation / agent-runtime separation** — UI and scheduling need not own runtime truth.
2. **Conversation lease generations** — live owner + epoch + expiry + guarded writes + takeover.
3. **Branch-aware append-only event history** — authoritative active HEAD separate from raw event inventory.
4. **Action→result/recovery pairing invariant** — recovery cannot orphan tool outcomes from their actions.
5. **Lazy idle hydration with special interrupted-run recovery** — cheap long-term state, strong scrutiny for prior RUNNING work.
6. **Declared-resource tool locking** — concurrency based on explicit shared-resource identity.
7. **Cancellation recheck at the side-effect boundary after waits**.
8. **Observed settlement rather than coroutine-cancelled state** for blocking work.
9. **Workspace backend as execution transport, not security-policy proof**.
10. **Conversation-specific Git worktrees** as collision reduction, distinct from sandbox/identity/effect recovery.
11. **Confirmation/security analysis separate from real execution authority**.
12. **Reference-only durable credentials plus explicit runtime-visible/brokered delivery semantics** as a target architecture.
13. **All ambient state roots must participate in isolation** — profile/home/global state cannot bypass a fresh runtime root.
14. **Model canonical identity + capability overrides + runtime metadata**.
15. **Separate sensitive traces, operational telemetry and product analytics**.
16. **Runtime critic/refinement separate from independent acceptance authority**.
17. **Worker-writable persistent repository memory kept below trusted governance**.

---

# 21. Candidate ACL regression fixtures derived from OpenHands

No tests were implemented in this research branch. These are future candidates.

## Ownership and recovery

1. Two worker services target the same task/run persistence root; only one generation may commit.
2. Old owner loses lease, continues running, then attempts a checkpoint/effect write; write is rejected.
3. Kill after action/effect intent append but before active-head/state commit; recovery preserves action→result relationship or blocks continuation.
4. Restart a run marked active with an unresolved tool/effect; downstream tasks stay blocked until reconciliation.

## Cancellation and concurrency

5. Cancel a tool while waiting for a resource lock; it must not start after the lock becomes available.
6. Cancel a blocking synchronous worker; UI/task status stays `cancelling/unsettled` until actual execution terminates or is classified unresolved.
7. Tool under-declares a shared resource; regression harness detects conflicting concurrent mutation rather than trusting declarations blindly.
8. Cancellation after approval/lease acquisition but before effect execution invalidates stale authority before the effect boundary.

## Workspace and authority

9. Docker worker receives only explicitly projected mounts/env/network; poisoned host state is invisible.
10. Worktree worker cannot escape into source checkout or control-plane/verifier roots.
11. Planner/read-only role cannot turn confirmation/approval settings into filesystem mutation authority.
12. Repository `AGENTS.md`/memory attempts to redefine ACL policy; trusted governance remains unchanged and the conflict is visible.

## Credentials

13. Durable task/checkpoint serialization contains credential reference IDs but no reusable plaintext/portable ciphertext.
14. Runtime-visible credential is delivered only to one named binding/runtime and never copied into checkpoint/memory/evidence logs.
15. Brokered credential path proves worker never receives provider secret material.
16. Missing/revoked credential disables only the binding/task action, not the ability to load the entire project/conversation state.

## Local models/provider behavior

17. Model/runtime profile claims a non-default timeout/context; wire-level probe proves the runtime actually receives it.
18. Provider adapter returns a capability mismatch; harness downgrades/refuses rather than entering an unbounded correction loop.

## Evidence

19. Product telemetry contains only allowlisted scalars; raw prompt/tool traces follow a different sensitive-evidence policy.
20. Runtime critic says task is complete while protected tests fail; independent verifier result controls acceptance.

---

# 22. Project health and maturity assessment

## Observed

Both inspected public repositories were not archived during Task 11.

The `software-agent-sdk` runtime is under very active development. The current main inspected during the task was a same-day commit adding explicit failing regression tests for a cancellation/thread-lifecycle problem.

That is positive maintenance evidence, but it also means runtime semantics are evolving quickly.

OpenHands is mature enough to expose production-shaped concerns that simpler harnesses do not always surface:

- cross-process ownership;
- branch-aware durable histories;
- browser/client/server runtime boundaries;
- credential migration/design pressure;
- multiple workspace backends;
- multi-channel telemetry;
- provider normalization;
- live concurrency/cancellation races.

## Assessment

OpenHands remains a **high-value research/component reference** for ACL/Vera, especially for:

- single-writer ownership/fencing;
- persisted conversation/event relationships;
- process/thread cancellation failure modes;
- execution-workspace boundaries;
- credential architecture;
- agent-server/control-center separation.

No evidence in Task 11 supports a wholesale adoption decision.

The same evidence also exposes reasons to avoid assuming the full runtime solves ACL's outer requirements:

- OpenHands persistence does not prove exactly-once external effects;
- container/worktree abstractions do not automatically provide ACL least privilege;
- confirmation is not sandbox authority;
- runtime critic is not independent acceptance;
- credential architecture is partly an active redesign area;
- repository memory/context is not trusted ACL governance;
- ACL still needs project/backlog dependency state, external-effect settlement, verifier ownership and Vera memory governance.

---

# 23. Explicit non-conclusions

Task 11 does **not** establish that:

- OpenHands is better or worse overall than Codex, Cline, Pydantic AI, LangGraph or Strands;
- OpenHands should become ACL's worker runtime;
- DockerWorkspace is a secure sandbox under every configuration;
- the credential design in issue #4288 is fully shipped;
- every historical credential leak remains exploitable;
- every Ollama path is still limited to 300 seconds;
- the closed crash-recovery/split-brain issues remain present on current main;
- OpenHands critic output is independent verification;
- OpenHands conversation persistence provides exactly-once external effects;
- repository-root `AGENTS.md` should be Vera's trusted long-term memory.

Those questions remain for later comparison or dedicated implementation/security tasks.

---

# 24. Task 11 synthesis

OpenHands' strongest contribution to ACL/Vera research is not a particular prompt format or agent class. It is the operational evidence produced by a coding-agent system that has had to handle **multiple servers, persistent sessions, real workspaces, cancellation, credentials, provider variability and restart recovery**.

The most important new candidate invariant from this task is:

> **Authoritative ownership, active history/effect relationships and execution settlement must agree before a long-running worker can be called safely resumable.**

OpenHands also adds a strong credential lesson:

> **Secret redaction is defense in depth; durable state should avoid owning reusable secret material in the first place, and runtime-visible delivery must be treated as an explicit authority grant.**

For ACL's long-term goal, the highest-value pieces to carry forward are therefore:

- generation-fenced single-writer ownership;
- branch/effect relationship integrity under crash recovery;
- side-effect-boundary cancellation rechecks;
- actual thread/process settlement evidence;
- explicit resource locking contracts;
- separate workspace/secret/network policy;
- reference-oriented credential design;
- capability-aware provider profiles;
- separated telemetry audiences;
- independent verification outside the worker runtime.

The next ranked slot is the already transition-aware **SWE-agent / mini-swe-agent** task. No SWE-agent deep research was begun here.
