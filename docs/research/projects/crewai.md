# CrewAI — Task 30 Deep Research

**Task:** 30  
**Project:** CrewAI  
**Canonical upstream:** `crewAIInc/crewAI`  
**Research date:** 2026-09-07  
**Latest stable observed:** `1.15.20` (published 2026-09-04)  
**Current main inspected:** `1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81` (2026-09-07)  
**Current package dependency identity:** `crewai-core==1.15.20`, `crewai-cli==1.15.20`; optional `crewai-tools==1.15.20`  
**Boundary:** research only. No CrewAI adoption, implementation, benchmark execution, ACL/Vera governance change, or Mastra research is authorized by this task.

## Executive assessment

CrewAI is now best understood as a broad agent/orchestration framework with several separable execution planes: individual Agents, multi-agent Crews, deterministic/event-driven Flows, unified persistent Memory, Knowledge/RAG, tool hooks, provider adapters, MCP integration, A2A delegation, and extensive event/observability surfaces.

For ACL, the strongest reusable ideas are not the role-play prompt layer itself. The highest-value mechanisms are:

- explicit separation of Crew process topology from Flow orchestration;
- pre-tool hooks that can deterministically mutate arguments or fail closed before an effect;
- explicit Flow resume versus fork semantics;
- typed/persisted Flow state with identifiable restore behavior;
- memory write draining/close semantics that acknowledge background persistence as a separate lifecycle;
- explicit protocol event surfaces for MCP and A2A;
- local-model provider abstraction, including documented Ollama support;
- rich event/telemetry integration.

The strongest failure evidence also maps closely to ACL/Vera concerns:

- open #5802: effect-bearing tools can execute again on retry because CrewAI has no durable idempotency/effect ledger;
- open #5057 plus current source: retrieved memory is appended into a system message in LiteAgent, turning lower-trust persistent content into higher-authority model context;
- current Flow restore source plus closed #6706: dict-state checkpoint restore can erase newly introduced defaults, demonstrating schema/version compatibility is part of checkpoint identity;
- closed #4168: threaded async execution can make shared-agent token accounting race, proving run-local observations cannot safely be derived from mutable aggregate state after concurrent work;
- open #6439: callback/config mutation and sync/async boundary errors can corrupt control/output state;
- current tool-hook source: pre-tool hooks are a real deterministic intervention seam, but their global registry and hook-error behavior still do not themselves constitute ACL policy authority, tenancy, sandboxing, or durable approval/effect state.

CrewAI should therefore remain below ACL-owned task/effect identity, durable idempotency/reconciliation, sandbox/process custody, credentials, protected policy/verifier state, writer fencing, checkpoint compatibility authority, and independent acceptance. For Vera, CrewAI's unified memory is useful implementation reference material, but its LLM-driven scope/consolidation and prompt injection path reinforce that memory remains evidence/claims, not authenticated truth or policy.

## 1. Project identity and release profile

The latest observed stable CrewAI release is **1.15.20**, published 2026-09-04. The current main branch inspected for this task is commit:

`1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81`

The current `lib/crewai/pyproject.toml` pins:

- `crewai-core==1.15.20`
- `crewai-cli==1.15.20`
- optional `crewai-tools==1.15.20`
- MCP dependency `mcp~=1.28.1`
- optional A2A dependencies including `a2a-sdk~=0.3.10`

The main commit inspected is post-release documentation work while the package component pins remain 1.15.20. Exact source revision therefore remains behavior-bearing identity even when the package version family appears unchanged.

### ACL implication

Future qualification should record at minimum:

- CrewAI release/commit;
- `crewai-core` / CLI / tools versions;
- Python version;
- Crew versus Flow versus direct Agent/LiteAgent entry path;
- process topology;
- provider adapter and exact model/runtime;
- tool hook registry/config;
- memory and knowledge backend/profile;
- MCP/A2A profile;
- persistence backend and Flow-state schema;
- context-window policy;
- execution/sandbox profile;
- telemetry/evaluation profile.

A generic label such as “CrewAI 1.15” is not enough.

## 2. Architecture: Agent, Crew, Process, Flow and protocol layers

### 2.1 Agent

Current Agent documentation defines an Agent as an autonomous unit that can:

- perform tasks;
- use tools;
- delegate when allowed;
- maintain memory;
- use knowledge;
- run reasoning/planning;
- use a separate function-calling LLM;
- enforce iteration, request-rate and execution-time limits.

Important behavior-bearing fields include `max_iter`, `max_execution_time`, `max_retry_limit`, `allow_delegation`, `function_calling_llm`, `respect_context_window`, memory and knowledge configuration.

### 2.2 Crew and Process

CrewAI supports at least two materially different Crew process topologies:

- **sequential** — tasks execute in explicit sequence;
- **hierarchical** — a manager agent/manager LLM coordinates/delegates.

These are not cosmetic labels. They alter task assignment, model calls, delegation and context propagation.

For ACL, the equivalent invariant is:

> orchestration topology is harness identity.

A manager model is not merely another worker model; it changes control flow and therefore belongs in the benchmark profile.

### 2.3 Flows

Flows are a separate orchestration abstraction from Crews. They provide deterministic/event-driven methods, listeners, routing, state and persistence. Current docs explicitly expose two state continuation semantics:

- `kickoff(inputs={"id": <uuid>})` — **resume** under the same flow identity/history;
- `kickoff(restore_from_state_id=<uuid>)` — **fork** from stored state into a new run identity.

This distinction is excellent reference material for ACL: “continue this run” and “branch from this checkpoint” should be different operations.

### 2.4 A2A and MCP

CrewAI now has first-class protocol-facing surfaces.

Current event documentation exposes MCP connection events with server name, URL, transport, connection timeout and reconnect information.

A2A delegation events expose:

- endpoint URL;
- task description;
- agent ID;
- context ID;
- multi-turn status;
- turn number;
- protocol version;
- provider information;
- optional skill ID;
- completion statuses such as `completed`, `input_required`, and `failed`.

These event fields are useful evidence. They do not imply that A2A context ID, MCP connection, Crew task, ACL run, and external effect are the same identity.

## 3. Tools, hooks and effect authorization

CrewAI's current tool-hook system is a significant positive mechanism.

`BeforeToolCallHook` receives a `ToolCallHookContext` containing:

- tool name;
- mutable tool input;
- tool object;
- agent;
- task;
- crew.

The hook may:

- mutate `tool_input` in place;
- return `False` to block execution;
- return `True` or `None` to allow.

Current implementation maps `False` to `HookAborted`, and `run_before_tool_call_hooks()` reports the call as blocked.

After-tool hooks can replace the model-visible string result while preserving a separate `raw_tool_result`.

### High-value reuse pattern

This is a strong deterministic seam for:

- replacing model-chosen tenant/customer IDs with host-authenticated IDs;
- canonicalizing paths;
- enforcing destination allowlists;
- checking risk policy;
- requiring confirmation;
- rate/cost limiting;
- redacting or shrinking tool results before model exposure.

### Important boundary

The hook registry is global and process-local. It is not by itself:

- authenticated policy identity;
- tenant isolation;
- durable approval state;
- distributed writer fencing;
- process sandboxing;
- exactly-once effect handling.

Open #4877 is useful design evidence: users want a standardized fail-closed policy-provider contract on top of the existing hook seam. Task 30 does **not** conclude CrewAI lacks pre-tool control; current source proves it exists. The gap is standardized external policy authority and durable semantics.

### Candidate ACL invariant

> Every effect-bearing tool call crosses one deterministic host-owned authorization boundary immediately before execution, with authoritative principal, exact tool origin/schema, normalized arguments, destination/credential scope and policy revision attached.

## 4. Retry, side effects and idempotency

Open issue **#5802** is one of the strongest Task 30 fixtures.

The report describes this sequence:

1. an effect-bearing tool succeeds;
2. the task/run fails before confirmation is incorporated;
3. retry occurs;
4. the same logical tool action executes again.

The example uses payments, but the failure class also covers:

- email;
- ticket creation;
- trades;
- mutations;
- deployments;
- file deletion;
- external workflow starts.

CrewAI agents expose `max_retry_limit`, but retries do not constitute proof that replay is safe.

### ACL implication

Retries must be separated into:

- model-generation retry;
- parser/schema retry;
- provider transport retry;
- pure computation/tool retry;
- ambiguous external-effect retry.

For an effect-bearing call, ACL needs:

- a stable logical effect ID generated before crossing the boundary;
- durable claim/ledger state outside the worker;
- idempotency key when the remote service supports it;
- recorded normalized request;
- explicit result/uncertain/settled states;
- reconciliation before replay after ambiguous failure.

A CrewAI task ID or model tool-call ID is useful correlation, but it is not automatically a durable idempotency/effect ID.

## 5. Timeouts, cancellation and lifecycle settlement

Agents expose `max_execution_time`, iteration limits and retry limits. These are useful run-control primitives.

However, Task 30 found no evidence that an agent timeout by itself proves:

- a backing provider request ended;
- a tool subprocess exited;
- a remote MCP/A2A task ended;
- an external side effect did not occur;
- background memory writes completed.

This preserves a campaign-wide rule:

> timeout/cancel/control-return and settlement are separate lifecycle states.

Open #6180 also reflects the current transition away from built-in code execution toward external sandbox services, which makes process/resource settlement an application responsibility rather than something the deprecated Agent flags can prove.

## 6. Code execution and sandbox boundary

Current Agent docs still list legacy `allow_code_execution` and `code_execution_mode` fields for compatibility, but explicitly mark them deprecated.

The docs state that `CodeInterpreterTool` has been removed from `crewai-tools` and recommend dedicated sandbox services such as E2B or Modal for secure execution.

This is a meaningful architecture signal: CrewAI is no longer presenting its old built-in execution mode as the preferred security boundary.

### ACL implication

If CrewAI is ever evaluated as an ACL worker harness:

- generated code must execute in an ACL-owned sandbox or a separately qualified sandbox service;
- filesystem mounts, working tree, Git credentials, network, user, process tree, CPU/RAM/time, secrets and artifact export must be explicit;
- “CrewAI agent can execute code” and “code is contained” remain different capability claims.

Open #6180 is retained as evidence that production execution guidance/standardization remains an active concern, not as proof that CrewAI cannot be securely deployed with an external sandbox.

## 7. Flow state, persistence and checkpoint compatibility

CrewAI Flows provide automatic persistence via `@persist`, with SQLite persistence documented as the default reference path.

This is valuable for ACL because the API already distinguishes same-history resume from fork.

### #6706: schema-drift restore fixture

Closed issue **#6706** reported that current dict-state restore logic did:

`self._state.clear(); self._state.update(stored_state)`

When a newer Flow version added a new default field, restoring an older checkpoint erased the fresh default because the old snapshot did not contain the new key.

Current main inspected for Task 30 still contains this clear/update pattern.

The issue was closed for inactivity, not because Task 30 verified a code fix. Therefore it remains a valid **current-source checkpoint-compatibility fixture**.

### Why this matters

Checkpoint identity must include:

- flow/workflow definition revision;
- state schema version;
- serializer/storage profile;
- code/harness revision;
- migration function/version;
- external-effect ledger position;
- policy/credential revision requirements.

A checkpoint being syntactically loadable is not enough.

### Preferred ACL pattern

- typed versioned state;
- immutable checkpoint generation ID;
- explicit schema migration;
- compatibility validation before mutation;
- resume versus fork as separate commands;
- no destructive replacement of newly introduced required defaults unless migration explicitly says so.

## 8. Concurrency and writer ownership

Closed **#4168** documented a race in threaded `async_execution` token attribution when two tasks shared one agent.

The important lesson is broader than tokens:

- both tasks observed the same aggregate “before” state;
- they ran concurrently;
- attribution was computed later from a shared aggregate “after” state;
- each task could be credited with work performed by the other.

This is a general shared-state accounting anti-pattern.

### ACL invariant

Per-attempt evidence must be captured in the attempt's execution context, not reverse-calculated from shared mutable aggregates after concurrent work.

This applies to:

- tokens;
- cost;
- tool counts;
- memory writes;
- process/resource usage;
- external effects;
- artifacts.

If one agent/runtime object is shared across concurrent tasks, mutable invocation state must be either isolated per attempt or protected with explicit synchronization and attribution semantics.

## 9. Async/sync integration and callback state

Open **#6439** contains four separate reproducible integration problems reported against 1.15.2a2:

1. unknown agent role causing a cryptic `StopIteration`;
2. after-kickoff callback return value replacing the crew result with `None`;
3. async callback using `asyncio.run()` inside an already-running event loop;
4. input config dict mutation by task construction.

Task 30 does not generalize every detail to current 1.15.20 without source verification. The issue is retained as a **callback/config state regression family**.

The ACL-relevant invariants are:

- observational callbacks must not silently replace canonical output unless declared as transformers;
- async and sync entry points need explicit event-loop ownership;
- caller-supplied immutable configuration should not be mutated as hidden runtime state;
- callback failures must be typed separately from task/model failure.

## 10. Unified memory architecture

CrewAI's current unified `Memory` is a substantial redesign compared with older separated short-term/long-term/entity abstractions.

Current Memory:

- is usable standalone, with Agents, Crews and Flows;
- defaults to an LLM-driven analysis path;
- infers scope, categories and importance when not explicitly supplied;
- uses semantic, recency and importance scoring;
- supports configurable half-life;
- uses a consolidation threshold;
- supports adaptive/deeper recall;
- has pluggable storage;
- defaults to LanceDB;
- supports optional Qdrant Edge and other configured storage;
- uses a background single-worker save pool;
- tracks pending writes;
- exposes `drain_writes()`;
- exposes `close()` to drain, close storage and shut down the pool.

### Positive mechanism: persistence settlement is explicit

The existence of `drain_writes()` is valuable. CrewAI explicitly recognizes that memory save submission and durable completion are different states.

Current source states background save failures emit `MemorySaveFailedEvent` and should not fail the task/crew/flow that produced the output.

This means memory persistence can fail while the main run is otherwise successful.

### ACL/Vera consequence

For optional personalization memory, that may be acceptable.

For authoritative memory required for safe continuation, ACL/Vera must decide whether memory persistence is:

- advisory;
- required;
- blocking;
- degraded-but-continuable.

A successful crew/task must not silently imply required memory settled.

## 11. Memory scope, consolidation and epistemic authority

Unified Memory uses an LLM to infer scope/categories/importance and may use an LLM when similarity exceeds the consolidation threshold.

That is useful product behavior, but not a truth policy.

For Vera:

- inferred scope is metadata, not authenticated principal identity;
- importance is a ranking hint, not authority;
- recency is not truth;
- consolidation is an epistemic mutation;
- similarity is not contradiction;
- LLM-generated consolidation must not silently overwrite verified facts in high-risk domains.

Memory records should retain:

- authenticated subject/domain scope;
- source/evidence provenance;
- observation time;
- world-valid time where relevant;
- system-ingest/mutation time;
- trust/confidence;
- supersession relationship;
- verifier/approval state for sensitive facts.

## 12. Persistent prompt injection and trust-boundary failure

Open **#5057** is especially important because Task 30 corroborated the core behavior against current main source.

Current `LiteAgent._inject_memory_context()` is documented as recalling relevant memories and appending them to the **system message**. Search against current main shows the recalled `m.record.content` values are formatted into a memory block and appended to `self._messages[0]["content"]` when that message has role `system`.

This means lower-trust persisted/retrieved content can be placed in a high-authority model channel.

LiteAgent is deprecated for v2 and users are directed toward `Agent().kickoff()`, but the fixture remains high-value because the trust-boundary lesson is general.

### Vera/ACL invariant

> Retrieved memory, documents, web content, tool output, remote-agent output and historical transcripts remain untrusted data regardless of which prompt location an integration chooses.

Sanitization/delimiters can help representation, but they are not authorization. Sensitive effects must be gated by deterministic policy outside model obedience.

## 13. Knowledge/RAG versus memory

CrewAI Agent supports `knowledge_sources` and an `embedder` independently from Memory.

This reinforces a useful separation:

- **Knowledge/RAG:** relatively stable reference corpus/retrieval;
- **Memory:** learned or accumulated interaction/project context;
- **Flow state:** operational continuation state;
- **Crew/task output:** run evidence;
- **policy/config:** trusted control-plane state.

These must not collapse into one store or one trust level.

For Vera, a document retrieved from a knowledge index should not become personal memory simply because the model mentions it. Likewise, memory is not automatically suitable as authoritative RAG source.

## 14. Local models and provider portability

CrewAI docs explicitly show local Ollama usage:

`LLM(model="ollama/llama3.2", base_url="http://localhost:11434")`

CrewAI also has a broad provider layer and an optional LiteLLM integration.

This is relevant to ACL's local-model goals, but “supports Ollama” is only nomination for testing.

Future 32K qualification must freeze:

- CrewAI commit;
- exact provider adapter;
- Ollama/runtime version;
- model artifact/tag/digest;
- tokenizer/chat template;
- tool-call mode;
- structured-output behavior;
- context setting and realized context;
- streaming;
- retries/fallback;
- context summarization policy;
- function-calling LLM if separate.

A local model used for ordinary chat and a different model used for function calling is a multi-model harness profile and must be scored as such.

## 15. Context-window management

Agents expose `respect_context_window=True` by default and can summarize when the context approaches limits.

This is useful operationally but behavior-bearing.

For ACL benchmark design:

- full replay versus summarization is a harness variable;
- summary model/provider is part of profile identity;
- model success after summarization cannot be compared directly to raw 32K replay unless the benchmark lane explicitly permits that policy;
- the benchmark must record requested context and realized context.

## 16. Guardrails: output validation versus pre-effect authorization

CrewAI has task/agent guardrails that validate generated output and can retry.

Separately, pre-tool hooks can block tool execution before effects.

These are different mechanisms and should remain different.

### Required distinction

- **output guardrail:** is this response/result acceptable?
- **tool authorization:** may this effect occur?
- **sandbox:** what damage is technically possible?
- **verification:** did the intended state change actually occur?
- **idempotency/reconciliation:** can this effect be safely retried/resumed?

Open #4877 correctly highlights this difference in its motivation. Task 30 retains the distinction without endorsing the proposed third-party provider design.

## 17. MCP integration

CrewAI includes MCP dependencies and explicit MCP connection lifecycle events.

For ACL, MCP adds at least these identities:

- configured server;
- transport;
- authenticated connection;
- remote tool definition/schema;
- one tool invocation;
- remote computation/effect;
- CrewAI task/run;
- ACL effect record.

Do not authorize a tool from display name alone.

MCP-origin tools should carry:

- trusted server origin;
- transport/auth profile;
- tool schema/version/hash;
- normalized arguments;
- credential audience;
- effect risk class.

MCP connection success is not remote-tool trust, task completion, or effect settlement.

## 18. A2A integration

CrewAI's A2A surface is now material, not merely an external example.

Current code wraps local agent/task execution with A2A delegation and exposes completion states including `input_required` and `failed`.

### ACL implications

Remote-agent delegation needs separate identities for:

- local delegation attempt;
- A2A context/task handle;
- remote agent/card/skill;
- each turn;
- any external effects;
- final accepted result.

A2A “completed” is remote protocol lifecycle evidence. ACL still needs local verification for authoritative tasks.

Multi-turn remote context must not be treated as a bearer credential merely because it is a context ID.

## 19. Credentials, outbound authority and content trust

CrewAI's broad tool/provider/MCP/A2A surfaces mean credentials may exist at multiple levels:

- model provider keys;
- tool/service keys;
- MCP server auth;
- A2A auth;
- storage/vector DB credentials;
- observability exporters.

ACL should not inject all of these into one worker process.

Recommended boundary:

- control-plane/provider keys remain outside tool sandboxes when possible;
- each effect tool receives only service-scoped credentials;
- credentials bind to destination/audience and action;
- outbound network scope is explicit;
- tool and remote content remain untrusted model data.

## 20. Observability and events

CrewAI has a broad event system and documents integrations such as OpenTelemetry-compatible tracing, MLflow, Langfuse and Braintrust.

Event surfaces include agent, task, memory, MCP and A2A lifecycle data.

This is valuable for:

- timing;
- provider calls;
- tool calls;
- delegation;
- memory save/retrieval;
- debugging;
- cost/token accounting;
- protocol transitions.

### Boundary

Telemetry is evidence, not authority.

A trace does not itself prove:

- authenticated principal;
- policy revision;
- approval;
- exact idempotency/effect identity;
- process termination;
- external settlement;
- independent correctness.

The #4168 accounting race is a useful warning that metrics can be internally consistent at one aggregate level while incorrect at a per-task attribution level.

## 21. Reproducibility profile for ACL

A future CrewAI benchmark manifest should include:

### Harness
- CrewAI release/commit;
- core/CLI/tools versions;
- Python version;
- Crew/Flow/direct-Agent path.

### Orchestration
- sequential/hierarchical/Flow;
- manager agent/model;
- delegation settings;
- async mode;
- retry/iteration/time limits.

### Model/runtime
- model artifact;
- provider adapter;
- local/cloud;
- endpoint/runtime revision;
- tool-calling model if separate;
- context policy;
- structured output;
- streaming.

### Tools/security
- exact tool definitions/schemas;
- pre/post hooks;
- MCP/A2A tool origins;
- sandbox;
- filesystem/network/credential grants;
- policy revision.

### State
- Flow schema version;
- persistence backend;
- resume/fork mode;
- Memory config/storage/embedder/LLM;
- Knowledge/index version;
- caches.

### Evidence
- events/traces;
- token/cost capture path;
- verifier version;
- effect ledger;
- process/resource settlement.

## 22. Candidate ACL/Vera invariants from Task 30

1. Crew, Flow, Agent invocation, protocol request and external effect are separate identities.
2. Orchestration topology is benchmark identity.
3. Hierarchical manager behavior is a control-plane model profile, not just prompt text.
4. Resume and fork are separate operations with separate IDs.
5. Checkpoint state includes schema/code/harness compatibility identity.
6. Restoring old state never silently discards new required defaults without a migration decision.
7. Pre-tool argument mediation occurs deterministically outside model control.
8. Effect authorization is distinct from output guardrails.
9. Hook registry/process state is not durable approval authority.
10. Effect-bearing retry requires durable idempotency/reconciliation.
11. Tool-call correlation ID is not automatically an effect ID.
12. Timeout/cancel is not backing-work settlement.
13. Generated-code support is distinct from sandbox containment.
14. Sandbox provider/profile is deployment identity.
15. Shared concurrent agent state requires isolated invocation accounting or explicit synchronization.
16. Per-attempt evidence is captured at the attempt, not reconstructed from shared aggregates.
17. Observational callbacks cannot silently replace canonical output.
18. Sync/async event-loop ownership is explicit.
19. Caller configuration is immutable unless mutation is explicit in the API contract.
20. Memory save submission and durable memory settlement are separate.
21. Required persistence failures produce explicit degraded/failure state.
22. Memory scope is not authenticated principal identity.
23. LLM-inferred memory scope/importance/consolidation is advisory epistemic processing.
24. Retrieved memory remains untrusted data.
25. Retrieved content never gains effect authority from system-message placement.
26. Knowledge, memory, operational Flow state and policy are separate trust planes.
27. Memory consolidation preserves provenance/supersession.
28. Context summarization/compaction is harness identity.
29. Local-provider support requires exact end-to-end profile qualification.
30. MCP connection identity differs from remote-tool/effect identity.
31. A2A context/task IDs are routing/lifecycle handles, not local authorization.
32. Remote A2A completion still requires local acceptance/verification where authoritative.
33. Credentials bind to service/audience/action and are not ambient worker state.
34. Telemetry is evidence, never independent verifier authority.
35. Model/tool/protocol/harness failures are classified separately.
36. Memory/traces can contain sensitive data and need explicit retention/audience.
37. Background memory write pools have close/drain ownership.
38. Persistent state required for safe resume is reconciled before continuation.
39. Policy hooks fail closed when policy availability is mandatory.
40. Same model under different CrewAI orchestration/context/tool profiles is a different benchmark profile.

## 23. Regression fixtures retained for later harness testing

### C30-01 — effect retry duplication
Source: #5802.  
Simulate tool success followed by lost acknowledgement/task failure. Retry must not duplicate the external effect.

### C30-02 — Flow checkpoint schema drift
Source: #6706 + current `_restore_state` clear/update source.  
Restore an older dict snapshot after adding a new required/default field. Migration/compatibility behavior must be explicit.

### C30-03 — shared-agent concurrent attribution
Source: #4168.  
Run concurrent tasks through one agent and verify per-attempt tokens/cost/tool/effect evidence cannot include sibling work.

### C30-04 — callback output clobber
Source: #6439.  
An observational after-run callback returning `None` must not silently convert canonical output to `None`.

### C30-05 — nested event-loop callback
Source: #6439.  
Async callback under async kickoff/Jupyter-style loop must not invoke nested `asyncio.run()`.

### C30-06 — caller config mutation
Source: #6439.  
Repeatedly reuse input configuration and verify first construction does not destructively mutate it.

### C30-07 — persistent memory prompt injection
Source: #5057 + current LiteAgent source.  
Store hostile retrieved content, recall it later, and verify it cannot gain trusted policy/effect authority.

### C30-08 — pre-tool host identity injection
Source: current hook system.  
Model provides attacker-chosen tenant/customer ID; pre-hook replaces with authenticated host identity before execution.

### C30-09 — pre-tool fail closed
Source: current hook system.  
Required policy denies or aborts; tool must not execute.

### C30-10 — post-tool redaction
Source: current after-hook/raw-result separation.  
Raw service result contains secret fields; model-visible result is redacted without altering audit evidence.

### C30-11 — memory background-save settlement
Source: current Memory `drain_writes()/close()`.  
Run completes while save is pending/fails; authoritative continuation must not mislabel memory as settled.

### C30-12 — resume versus fork identity
Source: Flow docs.  
Verify resume extends original identity/history while fork creates an independent continuation identity.

### C30-13 — local Ollama tool profile
Source: current LLM docs.  
Freeze Ollama/model/context/tool-call profile and separately score transport/schema/tool correctness from reasoning.

### C30-14 — context summarization profile
Source: `respect_context_window`.  
Same model/task with full context versus automatic summarization must be treated as distinct harness profiles.

### C30-15 — MCP lifecycle
Source: MCP events.  
Connection success followed by remote tool timeout/failure must preserve separate connection/request/effect states.

### C30-16 — A2A input-required lifecycle
Source: A2A completion statuses.  
Remote agent returns `input_required`; local caller must not treat the delegation as completed success.

### C30-17 — A2A result verification
Source: A2A wrapper/events.  
Remote `completed` response containing wrong output must fail independent local acceptance.

### C30-18 — policy versus output guardrail
Source: current hooks + task guardrails.  
A model output passes response guardrail but requests unauthorized tool effect; pre-effect policy must still deny.

## 24. Reuse candidates

### Strong candidates
- pre-tool deterministic hook seam;
- post-tool model-view transformation with raw result retained separately;
- explicit Flow resume versus fork semantics;
- typed Flow state plus explicit persistence adapter;
- memory `drain_writes()/close()` lifecycle;
- structured protocol events for MCP/A2A;
- event-based operational observability;
- separate function-calling LLM support as an explicit profile;
- declarative orchestration/process identities.

### Reuse with stronger ACL controls
- unified Memory scoring/consolidation;
- hierarchical manager/agent topology;
- A2A delegation;
- MCP tools;
- automatic context summarization;
- retries;
- async task execution.

### Do not delegate to CrewAI
- authenticated principal authority;
- durable effect ledger/idempotency;
- process/OS sandbox authority;
- credential brokerage;
- distributed writer fencing;
- checkpoint compatibility/migration authority;
- independent verifier acceptance;
- Vera epistemic truth policy.

## 25. Explicit non-conclusions

Task 30 does **not** conclude that:

- CrewAI should be adopted, rejected or forked;
- CrewAI is safer or less safe overall than other researched frameworks;
- every issue report remains reproducible on 1.15.20 unless current source was separately corroborated;
- closed #6706 or #4168 means the underlying design class is fixed;
- LiteAgent #5057 represents every modern Agent memory path;
- CrewAI cannot execute code securely with a correctly configured external sandbox;
- Ollama support proves any local model is suitable for ACL;
- MCP/A2A support proves remote tools/agents are trustworthy;
- CrewAI Memory should become Vera's memory backend;
- automatic memory consolidation is safe for authoritative facts;
- Task 30 authorizes 32K benchmark execution;
- Task 30 authorizes ACL/Vera implementation changes;
- Mastra research has begun.

## 26. Sources

Primary sources inspected:

- https://github.com/crewAIInc/crewAI
- https://github.com/crewAIInc/crewAI/releases/tag/1.15.20
- https://github.com/crewAIInc/crewAI/blob/1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81/lib/crewai/pyproject.toml
- https://github.com/crewAIInc/crewAI/blob/1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81/docs/edge/en/concepts/agents.mdx
- https://github.com/crewAIInc/crewAI/blob/1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81/docs/edge/en/concepts/processes.mdx
- https://github.com/crewAIInc/crewAI/blob/1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81/docs/edge/en/concepts/flows.mdx
- https://github.com/crewAIInc/crewAI/blob/1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81/docs/edge/en/concepts/memory.mdx
- https://github.com/crewAIInc/crewAI/blob/1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81/docs/edge/en/learn/llm-connections.mdx
- https://github.com/crewAIInc/crewAI/blob/1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81/lib/crewai/src/crewai/hooks/types.py
- https://github.com/crewAIInc/crewAI/blob/1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81/lib/crewai/src/crewai/hooks/tool_hooks.py
- https://github.com/crewAIInc/crewAI/blob/1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81/lib/crewai/src/crewai/flow/runtime/__init__.py
- https://github.com/crewAIInc/crewAI/blob/1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81/lib/crewai/src/crewai/memory/unified_memory.py
- https://github.com/crewAIInc/crewAI/blob/1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81/lib/crewai/src/crewai/lite_agent.py
- https://github.com/crewAIInc/crewAI/issues/5802
- https://github.com/crewAIInc/crewAI/issues/5057
- https://github.com/crewAIInc/crewAI/issues/6706
- https://github.com/crewAIInc/crewAI/issues/4168
- https://github.com/crewAIInc/crewAI/issues/6439
- https://github.com/crewAIInc/crewAI/issues/4877
- https://github.com/crewAIInc/crewAI/issues/6180

## Stop point

Task 30 ends after CrewAI's current Agent/Crew/Process/Flow layering, persistence/resume/fork semantics, retry/effect behavior, concurrency/accounting evidence, pre/post tool-hook controls, code-execution boundary, unified Memory architecture and settlement, prompt-injection risk, provider/local-model support, MCP/A2A surfaces, credential/content-trust boundaries, observability and reproducibility requirements were researched.

No Mastra research, framework winner selection, model-role assignment, 32K benchmark execution or ACL/Vera implementation/governance change was begun.
