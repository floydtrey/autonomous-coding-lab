# OpenAI Agents SDK — Task 14 deep research

**Project:** OpenAI Agents SDK for Python  
**Canonical repository:** `openai/openai-agents-python`  
**Task date:** 2026-09-06  
**Inspected upstream revision:** `1d471a4775bf2f40179f411824da383deb4c3fca` (2026-09-05)  
**Latest published release observed:** `v0.22.0` (2026-08-19)  
**License:** MIT  
**Research status:** complete for this ranked slot; no dependency/adoption/fork decision made.

## Scope and research boundary

Task 14 examined the OpenAI Agents SDK only, with the ACL/Vera end goal controlling scope. The investigation focused on:

- current `Runner` and agent-loop ownership;
- tool, handoff and nested-agent boundaries;
- human approval identity and durable pause/resume;
- `RunState` serialization/versioning and trusted restoration;
- guardrail coverage and timing semantics;
- sandbox-agent execution, mounts, credentials and resume;
- sessions, compaction and state ownership;
- provider/model retry and replay safety;
- cancellation and streaming lifecycle;
- tracing/evidence and sensitive-data handling;
- custom/non-OpenAI provider support;
- current open failure surfaces that reveal real state/authority bugs;
- project health and directly relevant contributor/release signal;
- concrete ACL/Vera invariants and regression-fixture candidates.

The older `openai/swarm` repository was read only to verify the documented predecessor relationship and the operational boundary of the redesign. No separate Swarm research task was started. Model Context Protocol was not researched as a project; MCP-related SDK behavior appears here only where it is part of the Agents SDK's own approval/tool/runtime boundary.

## Executive assessment

The OpenAI Agents SDK is a high-value ACL reference because its current architecture is substantially more than the lightweight Swarm-style agent loop. The strongest reusable ideas are:

1. a deliberately versioned serializable `RunState` whose schema changelog tracks changes to approval, tool, sandbox, trace and resume semantics;
2. exact-call human approvals plus separately scoped sticky approvals;
3. fail-closed approval inspection when model arguments cannot be safely parsed;
4. sandbox state that can persist while credential/authority acknowledgements do not automatically persist;
5. trusted authority re-binding from current application configuration after resume;
6. provider retry policy that separates ordinary retry from explicit permission to replay a request that may already have had effects;
7. explicit distinction among session history, provider continuation state, `RunState`, sandbox session state and workspace snapshots;
8. deterministic model/provider testing utilities and a rapidly evolving release/test discipline.

The current failure surfaces are just as important. Open reports show that durable state can still become corrupt if an approval-resume path writes a tool output without its parent call, plain transcript replay can lose program/caller relationships that `RunState` preserves, a cancelled producer can strand a stream consumer, and a filesystem rename can report success while deleting the file because path-string identity did not match filesystem object identity.

For ACL, the main conclusion is selective mechanism reuse/comparison rather than whole-framework adoption. The SDK provides unusually strong references for **resume-state versioning, replay authorization, approval identity, sandbox authority re-binding and lifecycle testing**, but ACL would still need to own project/dependency scheduling, external-effect settlement, protected verification, role-specific capability ceilings, credential policy, worker/process custody, distributed writer fencing and Vera memory governance.

---

## 1. Project status and maintenance signal

### Observed current status

The canonical repository is public, active, non-archived and MIT licensed. The inspected `main` revision was:

- `1d471a4775bf2f40179f411824da383deb4c3fca`
- dated 2026-09-05
- commit message: `fix: route verification changes and require confirmed docs-only pushes (#4880)`

The latest published release observed was `v0.22.0`, published 2026-08-19. Recent release notes show ongoing runtime hardening rather than only feature additions. Examples from `v0.21.1` and `v0.22.0` include:

- model-call timeouts;
- Docker network isolation;
- exact-call approval precedence;
- provider-child cleanup after failures;
- RunState/checkpoint hardening;
- guardrail-output redaction from persisted/replay state;
- sandbox path and patch fixes;
- tracing redaction and processor cleanup;
- deterministic testing utilities.

Kazuhiro Sera (`seratch`), already ranked in the recurring-contributor queue for this project, appears repeatedly in current release, verification, cancellation/lifecycle, approval and sandbox-related work. This task records that only as directly relevant project-maintenance signal; it does not begin person-level research or infer formal role beyond attributable public work.

### Assessment

**Confidence:** high.

The project is actively maintained and the state/sandbox/lifecycle contracts are changing rapidly. That makes it a strong current research source and a higher API/semantic-churn dependency risk than a mature frozen substrate.

### Primary sources

- https://github.com/openai/openai-agents-python
- https://github.com/openai/openai-agents-python/commit/1d471a4775bf2f40179f411824da383deb4c3fca
- https://github.com/openai/openai-agents-python/releases/tag/v0.22.0
- https://github.com/openai/openai-agents-python/releases/tag/v0.21.1

---

## 2. Swarm predecessor boundary: primitives survived, operational state grew around them

The canonical Swarm README describes Swarm as **experimental, educational**, says it has been replaced by the Agents SDK, calls the Agents SDK a production-ready evolution, and recommends migration for production use.

Swarm intentionally centered two lightweight primitives:

- agents;
- handoffs/functions.

Its normal run loop was client-side and stateless between calls: model completion, tool execution, possible agent switch, context-variable update, return. The caller could manually feed returned messages/context back into a later invocation.

The current Agents SDK retains the small conceptual agent/handoff/tool loop but adds explicit operational layers around it:

- serializable `RunState`;
- human-in-the-loop interruption/resume;
- sessions;
- tool/handoff/agent guardrails;
- tracing;
- model-provider abstractions and retry policy;
- sandbox agents and resumable workspace state;
- structured cancellation/streaming behavior;
- richer tool/caller identity.

### ACL/Vera lesson

A successful simplification target is not necessarily “few features.” Swarm shows the value of a small model-facing primitive set; the successor shows that production operation still needs explicit lifecycle, authority, persistence and evidence systems around those primitives.

This independently agrees with the SWE-agent → SWE-ReX → mini-swe-agent evidence: **keep model-facing orchestration simple, but do not confuse simplicity with absence of runtime control.**

### Primary source

- https://github.com/openai/swarm/blob/main/README.md

---

## 3. Runner and agent-loop ownership

The SDK exposes:

- `Runner.run()`;
- `Runner.run_sync()`;
- `Runner.run_streamed()`.

A run can begin from:

- a string;
- Responses-format input items;
- a `RunState` when resuming an interrupted/paused run or one intentionally stopped after the current turn.

The core loop remains straightforward:

1. call the model for the current agent;
2. finish if final output is accepted;
3. transfer control if a handoff is selected;
4. execute tool calls and feed results back;
5. repeat until completion or `max_turns`.

`RunConfig` contains important runtime controls outside prompt prose, including:

- model/model provider overrides;
- session behavior;
- guardrails;
- handoff input/history shaping;
- tracing;
- local function-tool concurrency;
- pre-approval guardrail timing;
- unknown-tool behavior;
- tool-name collision policy.

### Local concurrency boundary

`ToolExecutionConfig.max_function_tool_concurrency` limits how many model-emitted local function calls the SDK executes at once. This is separate from model/provider `parallel_tool_calls`, which controls what the model may emit.

This distinction is useful for ACL:

- **model protocol concurrency** is a capability setting;
- **real effect concurrency** is an execution-authority/lifecycle setting.

They should not be represented by one flag.

### Tool-name collision behavior

The current default unnamespaced function-tool/handoff collision policy is `warn`, exposing the current dispatch winner. Applications can choose `error` to fail before the model call.

For ACL authority-bearing tools, the safer candidate invariant is stricter than the SDK default:

> If two model-visible effect capabilities collide in identity, fail closed before worker execution. Do not warn and choose a winner.

### Primary source

- https://github.com/openai/openai-agents-python/blob/main/docs/running_agents.md

---

## 4. `RunState`: a versioned durable execution envelope

`RunState` is explicitly documented in source as a **serializable snapshot of an agent run** and a durable pause/resume boundary for human-in-the-loop workflows.

### Current schema version

At the inspected revision:

- current schema version: `1.17`;
- released schema versions are intended to remain readable;
- serialization emits the current schema;
- unsupported newer schemas are rejected rather than guessed forward.

This is unusually relevant to ACL because the source keeps a semantic version history explaining why the snapshot changed.

Examples include:

- 1.2 — reasoning-item ID policy;
- 1.3 — resumed trace reattachment semantics;
- 1.4 — request ID on model responses;
- 1.6 — explicit approval rejection messages;
- 1.7 — duplicate-name agent identity across agent-owned and sandbox resume state;
- 1.8 — prompt-cache key;
- 1.9 — pending custom-tool calls and tool origin;
- 1.10 — nullable max turns;
- 1.11 — custom data on tool outputs;
- 1.13 — programmatic tool calling and nested-handoff history ownership;
- 1.14 — hosted-MCP approval identity scoped by server label;
- 1.15 — canonical tool invocation identity, sanitized mount authority, trusted rebind metadata, durable pending input and resumable next-model-call state;
- 1.16 — Docker network-isolation state and exact-call approval precedence;
- 1.17 — Docker labels, current-response generated-item ownership and pending resumed-session writes.

### Why this matters

This schema history demonstrates that a “conversation snapshot” becomes operationally meaningful only when it also preserves identity and state needed to interpret what can safely happen next.

ACL's eventual checkpoint envelope should similarly version the semantics of fields such as:

- project/task identity;
- authoritative task-definition version;
- worker/agent definition version;
- model/runtime capability profile;
- pending approval identity;
- workspace baseline/snapshot identity;
- external-effect records;
- credential references/grants;
- verifier/evidence identity;
- next executable state.

### Fail-fast forward compatibility

The SDK's explicit rejection of unsupported future schema versions is a strong ACL pattern. A worker should not silently interpret a checkpoint created under newer authority/replay semantics.

Candidate ACL invariant:

> A persistent execution checkpoint may be resumed only by code that declares compatibility with its exact checkpoint semantic version; unknown newer versions fail closed.

### Serialization is a trust boundary

The SDK also contains defensive serialization/copy handling intended to avoid arbitrary subtype hooks and unsafe payload shapes, with checks around JSON-compatible bounded structures, cycles, key types/collisions and non-finite numeric values.

This reinforces that restored execution state is **trusted executable input**, not inert data.

### Primary source

- https://github.com/openai/openai-agents-python/blob/main/src/agents/run_state.py

---

## 5. Human approval identity and durable resume

The current approval system is run-wide. An interruption can originate from:

- the current agent's tool;
- a tool after a handoff;
- an `Agent.as_tool()` wrapper itself;
- a tool inside the nested agent;
- local shell/apply-patch surfaces;
- local or hosted MCP approval paths.

### Exact-call approval

For an ordinary pending call, approval is associated with the specific call identity. Resume flow is:

1. model proposes a tool call;
2. SDK evaluates approval requirement;
3. unresolved call becomes a `ToolApprovalItem` interruption;
4. caller converts the result to `RunState`;
5. caller approves/rejects a specific interruption;
6. original top-level run resumes from that state.

### Sticky approval

`always_approve=True` / `always_reject=True` can persist a broader same-tool decision for the rest of that run.

For hosted MCP, sticky identity includes both:

- `server_label`;
- tool name.

That prevents a tool named `lookup_account` on one hosted server from automatically inheriting a decision intended for another server.

### Malformed arguments fail closed

When approval is decided by a callable, the SDK does not invoke that callback if arguments cannot be safely inspected, including:

- malformed JSON;
- valid JSON that is not an object;
- non-standard constants such as NaN/Infinity.

The call instead requires manual approval.

This is a strong ACL pattern:

> If the policy engine cannot parse the exact proposed effect parameters under the expected schema, do not guess approval. Escalate or reject.

### Partial approval resolution

A run can contain several pending approvals; only some need to be resolved before resume. Resolved calls can proceed while unresolved calls remain pending.

ACL should preserve the same concept with explicit approval-item IDs rather than treating “task approved” as a single boolean.

### Approval and code/policy versioning

The HITL documentation explicitly recommends storing a version marker for agent definitions or the SDK when approvals may sit for a long time.

ACL should strengthen this into an invariant:

> A pending approval is bound to the exact proposed effect, task/objective version, capability definition and policy version. Changes that affect those semantics invalidate or require re-review of the approval.

### Sensitive serialized state

The documentation warns that serialized `RunState` includes application context and SDK-managed metadata such as approvals, usage, serialized tool input, nested resumptions, trace metadata and server-managed continuation settings.

`include_tracing_api_key=True` can intentionally include a tracing credential in serialized trace state.

Therefore:

- a parked `RunState` is sensitive state;
- storage/transmission policy must be explicit;
- app context should not casually hold secrets;
- ACL should prefer durable credential references rather than reusable secret values.

### Primary source

- https://github.com/openai/openai-agents-python/blob/main/docs/human_in_the_loop.md

---

## 6. Guardrails: validation coverage is not universal authority

The SDK has multiple guardrail classes, but their scope and timing differ materially.

### Agent-level input guardrails

Input guardrails apply to the **first agent** in the chain.

Default mode is parallel execution: the guardrail and agent start concurrently. The documentation explicitly warns that by the time a tripwire fires, the agent may already have consumed tokens or executed tools.

Blocking mode (`run_in_parallel=False`) completes the guardrail before starting the agent.

### ACL consequence

If a check is intended to guarantee **no effect happens unless it passes**, parallel mode is not an authority boundary.

Candidate invariant:

> Any control whose requirement is “nothing may execute before this passes” must be blocking and must complete before authority is granted.

### Output guardrails

Output guardrails run after the final candidate output. They can reject/sanitize what becomes durable/model-visible output, but they do not undo tool effects that already happened.

The SDK contains careful persistence rules for rejected terminal-tool outputs, including replacing blocked payloads with fixed text when it can retain a replay-valid call/output shape and dropping a response suffix when it cannot sanitize it safely.

This is useful evidence for ACL's evidence-plane design, but the authority rule remains:

> Post-effect output validation cannot substitute for pre-effect authorization.

### Function-tool guardrails

Tool guardrails can run before/after `FunctionTool` execution.

If a function tool requires approval, input guardrails normally run after approval immediately before execution. The SDK can optionally also run them **before** the approval interruption, and then re-runs them after approval before the effect.

That repeated execution is a valuable TOCTOU mitigation pattern:

- early check informs the approver;
- final check verifies current conditions at the irreversible boundary.

### Coverage gaps are explicit

The ordinary function-tool guardrail pipeline does **not** automatically cover:

- handoff calls;
- hosted tools such as web/file search, hosted MCP, code interpreter, image generation;
- built-in Computer/Shell/ApplyPatch/LocalShell tools;
- `Agent.as_tool()` directly.

Therefore “guardrails enabled” is not a meaningful single security capability bit.

ACL capability profiles should instead record exact policy coverage for each effect surface.

### Primary source

- https://github.com/openai/openai-agents-python/blob/main/docs/guardrails.md

---

## 7. Handoffs: delegation tool != delegation authorization

Handoffs are model-visible transfer tools. They can define:

- destination agent;
- tool name/description;
- structured `input_type`;
- `on_handoff` callback;
- dynamic `is_enabled`;
- input/history filters.

### Key authorization boundary

The docs make an important distinction:

- `is_enabled` is evaluated while preparing the available handoffs;
- therefore it cannot authorize fields the model later puts in the handoff arguments.

If authorization depends on parsed handoff data, the docs say to check it **at the beginning of `on_handoff`, before application side effects**, and raise on failure.

Additionally, function-tool input guardrails do not apply to the handoff call itself.

### ACL lesson

A model choosing to delegate is not the same thing as the system authorizing the scope carried by that delegation.

Candidate ACL invariant:

> Parent→child delegation has a stable destination identity plus an ACL-owned capability/scope grant. Model-generated delegation metadata is untrusted proposal data until validated and authorized at the handoff boundary.

This aligns with earlier findings from Codex and Pydantic Harness: child roles should be able to reduce authority but should not manufacture a wider ceiling from model-controlled configuration.

### History boundary

The receiving agent sees prior conversation history by default unless filtered. Nested handoff-history transformation is currently beta and disabled by default.

This reinforces that:

- delegation authority;
- visible conversation context;
- durable parent/child task identity

are separate concerns.

### Primary source

- https://github.com/openai/openai-agents-python/blob/main/docs/handoffs.md

---

## 8. Tool execution boundary

The tool catalog distinguishes:

- OpenAI-hosted tools;
- local/runtime execution tools;
- Python function tools;
- agents as tools;
- experimental workspace-scoped Codex tool.

Local/runtime tools execute in an environment supplied or controlled by the application. A Python `FunctionTool` can run arbitrary application code. This means the Agents SDK's tool schema/approval/guardrail machinery is not itself an OS sandbox for arbitrary local functions.

### Programmatic Tool Calling

Programmatic Tool Calling is especially instructive because it explicitly separates:

- generated program orchestration in a fresh hosted V8 environment;
- explicitly allowed callable tools;
- SDK-owned child-call identity;
- approval/guardrail/retry/session/RunState behavior around those child calls.

The generated program has no ordinary Node.js APIs, filesystem, network or persistent process, and can interact only with allowed tools.

The SDK also uses a stricter model-retry boundary when Programmatic Tool Calling is present: provider-managed retry is disabled and Runner retry is permitted only when provider advice explicitly marks replay safe.

### ACL lesson

Generated orchestration code and effect authority can be separated. A model may coordinate a local plan/program, but the actual effect boundary should remain an ACL-owned tool contract with:

- canonical identity;
- parameter validation;
- authorization;
- idempotency/effect state;
- process/sandbox custody;
- independent verification.

### Primary source

- https://github.com/openai/openai-agents-python/blob/main/docs/tools.md

---

## 9. Sandbox Agents: workspace state and live authority are separate

Sandbox Agents are explicitly marked **beta**.

The architecture separates:

- `SandboxAgent` — agent definition plus sandbox defaults;
- `Manifest` — desired contents/layout for a fresh workspace;
- sandbox session — live environment where commands/files change;
- `SandboxRunConfig` — session/client/resume source for a run;
- saved session state/snapshots — continuity mechanisms.

### Critical ownership split

The documentation explicitly says:

- the **outer runtime** owns approvals, tracing, handoffs and runner state needed for resume;
- the **sandbox session** owns commands, file changes and environment isolation.

This is a useful ACL reference because workspace/runtime complexity does not need to be model-facing scheduler complexity.

### Manifest is not live truth

A fresh-session `Manifest` is not automatically the full source of truth after the workflow reuses/resumes an existing sandbox session. Effective state can come from:

- existing live session;
- serialized sandbox session state;
- chosen snapshot.

ACL should therefore record both:

- intended baseline/provisioning manifest identity;
- realized live workspace/session identity.

### Default capabilities are broad

`Capabilities.default()` includes:

- Filesystem;
- Shell;
- Compaction.

A default SandboxAgent therefore has a broad model-facing action surface even though execution is isolated from the host to some degree.

For ACL, least privilege should be role-specific:

- research/planner: read-only or narrow inspection;
- coder: bounded workspace mutation + test execution;
- reviewer: protected read/test evidence without worker mutation authority;
- deployment/service actions: separately granted and generally not inherited.

### Sandbox clients are not equivalent permission profiles

Current options include:

- Unix-local development;
- Docker;
- multiple hosted sandbox providers.

The docs position Unix-local as fastest local development, Docker as basic container isolation, and hosted providers for production-style isolation.

Docker can explicitly set `network_mode="none"`, and that network setting is persisted in sandbox session state and reapplied when a replacement container is created during resume.

Mounts default read-only, but mount/network/user/resource/credential choices remain authority-bearing configuration outside the mere word “sandbox.”

### Primary sources

- https://github.com/openai/openai-agents-python/blob/main/docs/sandbox_agents.md
- https://github.com/openai/openai-agents-python/blob/main/docs/sandbox/guide.md
- https://github.com/openai/openai-agents-python/blob/main/docs/sandbox/clients.md

---

## 10. Sandbox credential authority is deliberately stripped and re-bound

This is one of Task 14's strongest ACL/Vera findings.

### Authority is broader than secret strings

Current `_mount_security.py` explicitly comments that some fields are **authority, not merely secrets**. Examples include identifiers or configuration that may select managed/workload identity even if the value is not secret itself.

The module classifies authority-bearing fields for S3, GCS, Azure, Box, R2 and other strategies, including files/config paths that can expose ambient authority.

Opaque third-party mount configuration is treated conservatively: it cannot be safely classified by option name, so authority-bearing opaque configuration is removed from durable state as a unit rather than trusted by serialization.

### Explicit exposure acknowledgement

In-container mount strategies that require protected credentials/ambient authority require explicit application acknowledgement for the exact mount path before the helper starts.

The documentation is careful not to overclaim the acknowledgement:

- acknowledgement permits the helper to receive credentials;
- it does **not** confine credential use to the mount path;
- short-lived least-privilege sandbox-scoped credentials are preferred.

### Acknowledgement is not serialized

These credential-exposure acknowledgements are runtime-only and not persisted as reusable grants.

### Trusted rebind after resume

Serialized sandbox state can carry redacted/sanitized mount authority plus metadata needed to reconnect that state to current configuration. Current code/tests require a **current trusted manifest** to rebind persisted authority; a missing trusted manifest fails rather than silently reconstructing credentials from the old snapshot.

Tests also verify that current secret values do not appear in serialized representations before later trusted rebind.

### ACL/Vera candidate invariant

> Persist capability/resource identity and sanitized continuation metadata, not reusable live authority. On resume, current trusted application policy must explicitly rebind credentials, mounts, network grants and other live authority.

This applies beyond sandbox mounts to future Vera integrations such as:

- Toyota/vehicle control;
- email/calendar actions;
- cloud APIs;
- GitHub credentials;
- home automation;
- remote worker hosts.

A months-old checkpoint should not automatically reactivate a credential simply because it once had access.

### Primary sources

- https://github.com/openai/openai-agents-python/blob/main/src/agents/sandbox/_mount_security.py
- https://github.com/openai/openai-agents-python/blob/main/src/agents/sandbox/session/sandbox_session_state.py
- https://github.com/openai/openai-agents-python/blob/main/tests/test_run_state_compatibility_corpus.py
- https://github.com/openai/openai-agents-python/blob/main/docs/sandbox/clients.md

---

## 11. Sessions: conversation memory is a separate state owner

The SDK `Session` interface maintains client-side conversation history between runs.

The docs explicitly disallow mixing a session with run-level continuation options such as:

- `conversation_id`;
- `previous_response_id`;
- `auto_previous_response_id`

within the same run.

This is important because it acknowledges that two different continuation mechanisms should not simultaneously claim ownership of the same conversation state.

### ACL lesson

For every durable state domain, choose one authoritative owner/version. Do not layer multiple partially overlapping history stores and assume they remain consistent.

### Sessions are not checkpoints

A session stores conversation items. It does not by itself establish:

- workspace state;
- process settlement;
- side-effect settlement;
- approval validity;
- credential validity;
- task/dependency state;
- verifier state.

This matches the campaign's recurring distinction: transcript/history is evidence and context, not necessarily permission to resume real work.

### Primary source

- https://github.com/openai/openai-agents-python/blob/main/docs/sessions/index.md

---

## 12. Compaction: clear/rewrite is a real concurrent state mutation

`OpenAIResponsesCompactionSession` provides one of the clearest current examples of why context compaction needs explicit state ownership.

### Observed behavior

Automatic compaction can continue after the last visible token and delay streamed-run completion because the SDK waits for compaction to settle.

Compaction can clear and rewrite underlying session history. If replacement fails or is cancelled after underlying history changed, the wrapper attempts to restore prior history and waits for that recovery before surfacing the original error/cancellation.

If recovery itself fails, the previous history can remain unrestored and the failure is logged.

The wrapper serializes its own mutation methods around replacement/recovery. However, the docs explicitly warn that a mutation can complete while the **remote compaction request** is still in flight and then be overwritten by the later successful replacement.

The docs therefore recommend manual compaction between turns and warn against directly mutating the underlying session while compaction runs.

### ACL/Vera lessons

1. Model-context compaction is mutable state, not a harmless token-count operation.
2. Clear/rewrite operations need one writer or generation/CAS fencing.
3. Recovery attempt needs explicit settlement evidence.
4. A context-memory subsystem must not silently overwrite newer authoritative state after a long remote summary operation finishes.
5. Vera memory compaction and ACL execution checkpoints must remain separate domains.

### Candidate fixture

- Start remote/slow compaction from history version N.
- Commit new mutation N+1 before compact result returns.
- Ensure compact N cannot overwrite N+1 without a generation/version precondition.

### Primary source

- https://github.com/openai/openai-agents-python/blob/main/docs/sessions/index.md

---

## 13. Retry architecture: retry permission is not replay permission

This is another unusually high-value ACL mechanism.

### Normalized retry facts

The SDK's runner-managed retry layer normalizes facts such as:

- status/error code;
- message;
- request ID;
- retry-after;
- network/timeout classification;
- abort classification.

Provider adapters can additionally supply `ModelRetryAdvice` containing:

- whether retry is suggested;
- retry delay;
- reason;
- `response_started`;
- **`replay_safety`** (`safe`, `unsafe` or unknown).

`RetryPolicyContext` also knows whether the request is stateful through `previous_response_id` or `conversation_id`.

### Explicit unsafe-replay approval

`RetryDecision` has a separate `approve_unsafe_replay` field.

The source explicitly documents that ordinary `RetryDecision(retry=True)` never bypasses replay protection. An application must make a distinct decision if repeating a possibly already-executed provider request is acceptable.

This is almost directly reusable as an ACL effect/recovery concept.

### ACL candidate invariant

> `retry` means “attempt the operation again under normal safe-replay rules.” `replay_unsafe_effect` is a separate authority decision that cannot be implied by retry count, transient-error classification or user patience.

For ACL, this distinction should extend beyond provider calls to:

- shell effects;
- Git writes/pushes;
- API mutations;
- database changes;
- email/messages;
- vehicle/home-automation commands;
- deployment actions.

### Runtime policy is not serialized

`ModelRetrySettings.policy` is runtime-only and intentionally excluded from serialization.

That supports another important pattern:

> Persistent state can record retry/effect facts, but executable policy must be rebound from current trusted application code after resume.

### Primary source

- https://github.com/openai/openai-agents-python/blob/main/src/agents/retry.py

---

## 14. Model/provider portability: exact feature path must be qualified

The SDK supports:

- OpenAI Responses models;
- OpenAI Chat Completions models;
- custom `Model` implementations;
- `ModelProvider` implementations;
- custom OpenAI-compatible base URLs/clients;
- MultiProvider routing;
- Any-LLM adapter;
- optional LiteLLM adapter.

### Feature matrices matter

Several capabilities are Responses-only and are rejected on other paths, including current tool-search/programmatic-tool-calling surfaces.

The OpenAI provider also supports `strict_feature_validation=True`, which can convert unsupported-feature warnings into errors.

For ACL qualification, fail-closed strict validation is preferable when a worker task depends on a feature.

### Third-party adapters

The documentation explicitly warns that Any-LLM capability gaps and provider dependencies are determined upstream, and tells users to validate the exact provider backend when relying on:

- structured output;
- tool calling;
- usage reporting;
- Responses-specific behavior.

LiteLLM is separately optional.

This independently confirms the conclusion from Pydantic AI, Cline, Codex, OpenHands, mini-swe-agent and llama.cpp:

> “OpenAI-compatible” describes a protocol shape, not realized capability equivalence.

ACL should qualify the exact:

- SDK revision;
- adapter/provider;
- runtime endpoint;
- model/quantization;
- transport;
- tool/structured-output mode;
- timeout/retry behavior;
- context configuration.

### WebSocket continuity boundary

Responses WebSocket transport can reuse a connection across runs, but the docs note:

- one response at a time per connection;
- 60-minute connection limit;
- `store=False`/ZDR state may not have a persisted fallback after reconnect;
- callers may need to rebuild context from local session state.

Transport reuse therefore remains distinct from durable workflow state.

### Primary source

- https://github.com/openai/openai-agents-python/blob/main/docs/models/index.md

---

## 15. Streaming and cancellation

A streaming run is not considered complete merely because the last visible token arrived. The docs explicitly require consuming `stream_events()` until the iterator finishes because post-processing may still be doing:

- session persistence;
- approval bookkeeping;
- history compaction.

This is an important evidence/GUI rule for ACL:

> “Last token received” is not a terminal worker state.

### Cancellation modes

`RunResultStreaming.cancel()` defaults to immediate cancellation.

`cancel(mode="after_turn")` lets the current turn finish cleanly before stopping. That stopped run can then be continued from `RunState`; staged user input can be attached before the next model call.

This gives ACL a useful distinction between:

- abort now;
- stop at the next safe/settled boundary.

ACL should make such semantics explicit in UI/API rather than giving one ambiguous “Stop” button state.

### Current open cancellation failure surface: #4805

Open issue #4805 reports a reproducible voice-pipeline case where a streamed transcription producer exits with `asyncio.CancelledError` but the public consumer remains waiting forever because no terminal event reaches the queue.

No API key/network is required for the provided reproduction.

The architectural lesson is broader than voice:

> Producer cancellation/death does not automatically settle consumers. Every owned queue/stream needs an explicit terminal-notification or cancellation propagation contract.

ACL regression fixtures should kill/cancel every producer class and assert all waiters either receive a terminal state or are explicitly cancelled within a bound.

### Primary sources

- https://github.com/openai/openai-agents-python/blob/main/docs/streaming.md
- https://github.com/openai/openai-agents-python/issues/4805

---

## 16. Tracing: strong operational evidence, sensitive by default

The Agents SDK traces:

- whole runner workflows;
- task/turn spans;
- agents;
- generations;
- function calls;
- guardrails;
- handoffs;
- voice/audio operations.

It supports custom trace processors and replacement exporters.

### Sensitive-data default

The docs state generation spans and function spans can contain model/tool inputs and outputs. `trace_include_sensitive_data` is **true by default** unless configured otherwise. Voice tracing can also include audio data.

ACL should not inherit that default blindly for a local personal assistant or privileged coding worker.

Evidence design should separately specify:

- worker/model-visible evidence;
- operator/debug evidence;
- verifier evidence;
- product analytics, if any;
- sensitive payload retention/redaction.

### Export settlement

The default batch processor exports asynchronously. For long-running/background workers, the docs recommend `flush_traces()` when an immediate delivery guarantee is required at the end of a unit of work.

This gives another useful state distinction:

- run settled;
- trace generated;
- trace export settled.

If ACL requires trace evidence for an acceptance gate, the gate should wait for the required evidence channel rather than assume background export will eventually happen.

### Tracing is not independent acceptance

The SDK's tracing is comprehensive runtime evidence, but Task 14 found no reason to treat it as an independent verifier-owned definition of task success.

ACL should still preserve promptfoo-style protected acceptance fixtures outside worker mutation authority.

### Primary source

- https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md

---

# Current failure surfaces

## 17. Open #4827 — approval resume can persist an orphaned tool output

**Status observed 2026-09-06:** open.

Issue #4827 provides a deterministic `ScriptedModel` + `SQLiteSession` reproduction involving:

- output guardrails;
- non-default `tool_use_behavior`;
- a tool requiring approval;
- serialized `RunState` round-trip;
- approval resume where the approved tool is not terminal.

The report says the interrupted turn's function call can be deferred from session persistence. On resume, the SDK persists the resolved tool **output** but not the matching deferred function **call**. The session then contains an orphaned `function_call_output`.

A later run sends that corrupt history to the provider and receives an error because no matching tool call exists. The issue describes the conversation as durably poisoned for subsequent runs.

### Why this matters more than the specific bug

This is direct evidence for a general checkpoint invariant:

> A durable action/result relationship is atomic semantic state. It is corruption to persist a result whose required parent action identity is absent.

This independently matches OpenHands issue #4487, where crash recovery could separate a tool action from its correct branch/result relationship.

### Candidate ACL rule

For any effect record:

- proposed call;
- authorization;
- started effect;
- completed/failed/uncertain result

must share a stable logical identity and be committed in a way that cannot create an authoritative child/result without its required parent relationship.

### Important migration lesson

The issue also reports a version sequence in which one earlier failure blocked the resume path and a later fix exposed the deeper persistence corruption. This is useful test-planning evidence:

> Fixing one lifecycle failure can reveal another previously unreachable state. Regression suites need state-machine path coverage, not only one-bug fixtures.

### Primary source

- https://github.com/openai/openai-agents-python/issues/4827

---

## 18. Open #4839 — plain transcript replay is weaker than authoritative `RunState`

**Status observed 2026-09-06:** open.

Issue #4839 reports Programmatic Tool Calling across a human-in-the-loop pause with client-managed input history.

The earlier `program` item is replayed as plain input on a fresh run. The later `program_output` refers to that parent program, but the current path does not count the replayed input program as a valid parent and raises `ModelBehaviorError`.

The issue explicitly notes that the **RunState resume path already tracks/scans durable program-parent identities**; the gap is specific to plain-input replay.

### ACL lesson

Not every representation of “the same conversation” carries the same execution semantics.

Candidate invariant:

> Only an explicitly qualified checkpoint/resume representation may authorize continuation of in-progress work. A transcript reconstructed from messages is not automatically equivalent to the authoritative execution checkpoint.

ACL should distinguish APIs such as:

- `continue_from_transcript` — new inference using historical evidence;
- `resume_checkpoint` — continuation of authoritative in-progress work with identity/effect preconditions.

They should not be aliases.

### Primary source

- https://github.com/openai/openai-agents-python/issues/4839

---

## 19. Open #4889 — lexical path identity can delete the file while reporting success

**Status observed 2026-09-06:** open; created 2026-09-06.

Issue #4889 reports a sandbox `apply_patch` update with `move_to` where a case-only rename can delete the file on a case-folding filesystem.

The reported mechanism is:

1. write updated content to destination;
2. compare normalized source and destination path objects;
3. if they compare unequal, delete source;
4. on a case-insensitive underlying filesystem, differently cased names may refer to the same file;
5. deleting the source therefore deletes the destination just written.

The tool can report an update/move while the file is gone.

### ACL lessons

1. Filesystem object identity is not always equivalent to normalized lexical path identity.
2. Mutation tools need explicit create/update/move/overwrite semantics.
3. High-value mutations need execution-time preconditions and postconditions.
4. A worker/tool saying “success” is lower-trust than verifier-owned filesystem evidence.
5. Cross-platform case-folding/symlink/path-equivalence fixtures belong in the worker benchmark.

The issue also raises, without separately claiming a second filed bug, that `move_to` targeting an existing different file can overwrite it without a precondition. This task records that only as issue-author observation, not as a separately verified failure classification.

### Primary source

- https://github.com/openai/openai-agents-python/issues/4889

---

## 20. Open #4852 — sandbox restore/extraction can partially mutate before platform failure

**Status observed 2026-09-06:** open.

Issue #4852 reports Windows failures when safe tar extraction attempts to recreate symlinks under ordinary non-elevated conditions where symlink creation is not available.

The report notes a particularly important state shape: regular files may already have been extracted before the later symlink operation fails, leaving a partially mutated extraction target.

### ACL lesson

Workspace restore/import is itself a state transition and needs explicit semantics:

- stage then commit/rename where possible;
- or retain an explicit `partial_restore` / failed-reconciliation state;
- do not label the workspace restored simply because extraction began successfully.

Cross-platform archive/symlink/case/path behavior must be part of sandbox qualification, especially because ACL development/use will include Windows hosts.

### Primary source

- https://github.com/openai/openai-agents-python/issues/4852

---

## 21. Failure-surface synthesis

Across #4827, #4839, #4805, #4889 and #4852, the common pressure is not “the model made a bad choice.” The failures occur at state/identity/lifecycle boundaries:

- parent call ↔ persisted result;
- `RunState` ↔ plain transcript representation;
- producer cancellation ↔ consumer terminal notification;
- lexical path ↔ underlying filesystem object identity;
- archive restore intent ↔ partially realized platform state.

That repeats the strongest cross-project research pattern so far:

> The hardest long-running-agent failures cluster at representation and ownership boundaries. Every transition between model state, runtime state, workspace state, authority state and evidence state needs stable identity, explicit owner, preconditions and postconditions.

---

# Reusable ACL/Vera mechanisms and candidate invariants

## 22. Highest-value mechanisms to carry into comparison

### 22.1 Versioned execution checkpoint semantics

Borrow the idea, whether or not the code is adopted:

- explicit checkpoint schema version;
- semantic changelog for authority/replay fields;
- fail-fast unsupported future version;
- compatibility fixtures across released versions.

### 22.2 Exact approval identity

Approval should bind to:

- project/task/objective version;
- tool origin/provider/server;
- tool/capability identity;
- exact proposed call/effect identity;
- argument digest / normalized parameters;
- policy version;
- expiry if applicable.

Sticky decisions should be narrower and separately represented.

### 22.3 Current-policy authority rebind

Persist sanitized resource identity; rebind live credentials/network/mount grants from current trusted policy after resume.

Do not allow a serialized checkpoint to become a reusable bearer token for old authority.

### 22.4 Replay-safety classification

Separate:

- retry safe;
- replay unsafe;
- replay state unknown;
- explicit operator/application override.

Do not make `max_retries > 0` an implicit permission to duplicate possible effects.

### 22.5 Runtime-only policy callbacks

Persist policy identity/version and facts needed for review, but reconstruct executable policy from trusted current application code rather than serializing executable closures/clients.

### 22.6 State-owner separation

Keep distinct:

- conversation/session history;
- provider continuation ID/state;
- authoritative execution checkpoint;
- sandbox/workspace state;
- external-effect ledger;
- verifier/evidence state;
- memory.

Each domain has one authoritative owner/version.

### 22.7 Finish/drain semantics

A unit of work is not terminal at the last visible token. Terminal state may require:

- tool settlement;
- session persistence;
- approval bookkeeping;
- compaction settlement;
- trace/evidence flush;
- sandbox/process cleanup.

### 22.8 Revalidate before irreversible effect

Where a condition can change while waiting for approval, run the relevant precondition both:

- before presenting approval;
- immediately before effect execution.

### 22.9 Fail closed on authority ambiguity

Examples:

- malformed approval arguments;
- tool-name collisions;
- missing current trusted manifest for authority rebind;
- unsupported checkpoint schema;
- unverified provider/tool feature;
- missing parent action/result relationship.

---

## 23. Areas where ACL would need stronger outer controls

### 23.1 Project/task dependency scheduling

Agents SDK handoffs/nested agents do not replace ACL's authoritative project backlog, parent/child task dependency gate, blocked-task semantics or cross-repository routing.

### 23.2 External-effect ledger

`RunState` is strong execution state but is not a complete ACL exactly-once external-effect ledger. ACL still needs proposed/authorized/started/completed/failed/unknown-after-crash records and effect idempotency/reconciliation.

### 23.3 Independent acceptance verifier

Tracing and guardrails are runtime controls/evidence. The system under test still should not own the authoritative definition of whether code/task/security acceptance passed.

### 23.4 Distributed writer fencing

This task did not establish a general distributed lease/generation mechanism for every persistent ACL state domain comparable to the OpenHands conversation lease. ACL still needs writer ownership/CAS/fencing where multiple supervisors/workers/processes can touch one task/checkpoint.

### 23.5 Role-specific least privilege

Default SandboxAgent capabilities are broader than several ACL roles should receive. ACL should define capability ceilings by worker role/project/task, not rely on general sandbox defaults.

### 23.6 Process/effect custody

Sandbox/runtime abstraction does not by itself prove every descendant process/effect settled. ACL still needs platform/backend-specific cancellation/cleanup tests.

### 23.7 Vera memory governance

Sessions and compaction are conversation/context mechanisms, not a complete provenance/trust/verification model for Vera's long-term memory.

---

# Proposed ACL regression fixtures derived from Task 14

These are research-derived candidates only. They were not implemented in Task 14.

## State/resume

1. Serialize checkpoint under schema/policy version N; attempt resume under unsupported future/older incompatible version; fail closed.
2. Park approval, modify tool definition/policy/task scope, then resume; prior approval must invalidate or require explicit compatibility proof.
3. Replay the same transcript through “new run” and “resume checkpoint”; ensure the system does not silently treat them as equivalent authority.
4. Corrupt/remove a required parent action while preserving its result; checkpoint/session validation must reject before model/provider use.
5. Resume nested agent/tool state after serialization and prove stable parent/child/call identity.

## Approval / authority

6. Approval callback receives malformed JSON/list/NaN; effect must not execute.
7. Two same-named tools from different origins/servers; sticky approval for one must not authorize the other.
8. Two authority-bearing tool names collide; production profile must fail before model invocation.
9. Approval waits while policy/resource changes; final pre-effect revalidation catches change.
10. Handoff metadata proposes broader scope; `is_enabled` alone must not authorize it; deterministic ACL scope check denies before effect.

## Replay / retry

11. Provider failure marked replay unsafe after response start; ordinary retry policy cannot repeat request.
12. Explicit unsafe-replay approval is separately logged with operator/task/policy identity.
13. Runtime retry callback missing after state restore; system must rebind trusted policy or fail rather than silently use a permissive default.

## Sandbox / credentials

14. Serialize sandbox state containing credential-backed mount; serialized form contains no reusable credential authority.
15. Resume without current trusted manifest/policy; mount authority remains unavailable.
16. Resume with changed credential reference/grant; current policy wins, not stale snapshot authority.
17. Default/new role capability set attempts shell/filesystem access not granted to that role; deterministic denial.
18. Docker `network_mode=none` survives session replacement/resume and is verified from realized container state.

## Filesystem

19. Case-only rename on case-folding filesystem preserves file and postcondition.
20. Move onto existing different file requires explicit overwrite precondition.
21. Symlink/path escape and case/path-equivalence matrix across Windows/Linux/container mounts.
22. Archive restore fails mid-way on unsupported symlink; workspace is either atomically unchanged or explicitly marked partial/unsettled.

## Streaming / cancellation

23. Cancel every producer while consumers are blocked; every consumer receives terminal/cancel signal within bound.
24. `cancel(immediate)` and `cancel(after_turn)` produce distinct, documented checkpoint/effect settlement states.
25. Last visible token arrives while session/compaction/evidence work remains; UI/task state must remain nonterminal until required settlement completes.

## Session / compaction

26. Slow compaction starts at version N; mutation N+1 lands before remote compaction returns; stale compact result cannot overwrite N+1.
27. Compaction replacement fails, recovery also fails; state is explicit `recovery_failed`/unsettled rather than silently complete.

## Tracing / evidence

28. Sensitive model/tool input appears in trace; ACL redaction/audience policy prevents forbidden export/retention.
29. Required trace/evidence exporter is unavailable; acceptance run becomes invalid/degraded explicitly rather than pass.
30. Trace queue still buffered at task completion; explicit flush/evidence settlement gate behaves deterministically.

## Provider portability

31. Exact local/custom provider is asked to use Responses-only feature; strict qualification rejects unsupported path.
32. Same model through two adapters/transports; capability profile records and separately validates tool/schema/stream/retry behavior.

---

# Comparison questions to carry forward

Task 14 does not answer these yet; they belong to later component comparison after the ranked project research is complete.

1. Is Agents SDK `RunState` a useful direct dependency, or should ACL independently implement only the versioning/approval/replay invariants?
2. How does its durable pause/resume model compare with Pydantic Harness StepPersistence and LangGraph checkpoints under ACL's external-effect crash fixtures?
3. Should ACL reuse an Agents SDK sandbox client/interface, a Codex/OpenHands/SWE-ReX runtime, or a smaller custom execution adapter?
4. Can Agents SDK's approval identity/rebind model coexist cleanly with ACL's future centralized authorization/effect ledger?
5. Which retry/replay-safety semantics should become framework-independent ACL types?
6. Does the default Agents SDK tool/handoff model remain small enough for the user's local-model constraints, or would a mini-swe-agent-style narrower worker protocol perform better?
7. Which trace/evidence fields map cleanly to OpenTelemetry/ACL GUI fields without coupling acceptance evidence to one runtime?
8. How much of Sandbox Agents beta API churn is acceptable if ACL uses a thin pinned adapter rather than importing the entire abstraction into governance?

---

# Explicit non-conclusions

Task 14 does **not** conclude that:

- OpenAI Agents SDK should be adopted as ACL's primary framework;
- OpenAI Agents SDK should be forked;
- `RunState` is a complete ACL checkpoint/effect ledger;
- sandbox agents provide complete security merely because execution is called a sandbox;
- Docker or a hosted sandbox is automatically least privilege;
- guardrails are a universal authorization system;
- human approval alone makes an effect safe;
- tracing is independent validation;
- sessions are Vera's long-term memory solution;
- custom/OpenAI-compatible model support means local models have feature parity;
- every current open issue reproduces on every configuration or future release;
- Swarm's lightweight architecture “failed.” Upstream describes it as an experimental/educational predecessor replaced by a production-oriented successor.

No ACL/Vera runtime, governance, dependency or worker code was changed in this task.

---

# Primary source index

## Project / predecessor / releases

- https://github.com/openai/openai-agents-python
- https://github.com/openai/openai-agents-python/commit/1d471a4775bf2f40179f411824da383deb4c3fca
- https://github.com/openai/openai-agents-python/releases/tag/v0.22.0
- https://github.com/openai/openai-agents-python/releases/tag/v0.21.1
- https://github.com/openai/swarm/blob/main/README.md

## Core lifecycle / state / approvals

- https://github.com/openai/openai-agents-python/blob/main/docs/running_agents.md
- https://github.com/openai/openai-agents-python/blob/main/src/agents/run_state.py
- https://github.com/openai/openai-agents-python/blob/main/docs/human_in_the_loop.md
- https://github.com/openai/openai-agents-python/blob/main/docs/streaming.md

## Guardrails / handoffs / tools

- https://github.com/openai/openai-agents-python/blob/main/docs/guardrails.md
- https://github.com/openai/openai-agents-python/blob/main/docs/handoffs.md
- https://github.com/openai/openai-agents-python/blob/main/docs/tools.md

## Sandbox / authority

- https://github.com/openai/openai-agents-python/blob/main/docs/sandbox_agents.md
- https://github.com/openai/openai-agents-python/blob/main/docs/sandbox/guide.md
- https://github.com/openai/openai-agents-python/blob/main/docs/sandbox/clients.md
- https://github.com/openai/openai-agents-python/blob/main/src/agents/sandbox/_mount_security.py
- https://github.com/openai/openai-agents-python/blob/main/src/agents/sandbox/session/sandbox_session_state.py
- https://github.com/openai/openai-agents-python/blob/main/tests/test_run_state_compatibility_corpus.py

## Sessions / retry / models / traces

- https://github.com/openai/openai-agents-python/blob/main/docs/sessions/index.md
- https://github.com/openai/openai-agents-python/blob/main/src/agents/retry.py
- https://github.com/openai/openai-agents-python/blob/main/docs/models/index.md
- https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md

## Current failure surfaces

- https://github.com/openai/openai-agents-python/issues/4827
- https://github.com/openai/openai-agents-python/issues/4839
- https://github.com/openai/openai-agents-python/issues/4805
- https://github.com/openai/openai-agents-python/issues/4889
- https://github.com/openai/openai-agents-python/issues/4852

---

# Final Task 14 assessment

OpenAI Agents SDK deserves its Tier-A ranking because it exposes several mature-looking runtime concepts while also providing unusually concrete current evidence of where they still fail under real pause/resume, persistence, cancellation and cross-platform filesystem conditions.

The strongest ACL/Vera contribution is the combination of:

- **versioned durable `RunState`;**
- **exact approval identity;**
- **current-policy authority rebind;**
- **retry vs unsafe-replay separation;**
- **explicit state-owner boundaries;**
- **deterministic testing of provider-free lifecycle paths.**

The strongest warning is equally clear:

> A state system is only as reliable as the relationships it preserves across transitions. Serialization can be valid while the execution state is semantically corrupt. Transcript replay can look complete while it lacks resume identity. A sandbox can report a mutation succeeded while filesystem identity made the opposite happen. A cancelled producer can be gone while its consumer remains stuck forever.

For ACL, the design target should therefore remain **small model-facing primitives plus rigorous outer identity, authority, effect, recovery and evidence contracts**.

**Next research boundary:** Model Context Protocol only, when separately authorized. Stop before Goose.
