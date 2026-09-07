# Google Agent Development Kit (ADK) — Task 22 Deep Research

**Research date:** 2026-09-07  
**Research target:** current Google ADK Python runtime, workflow, session/memory, tool, provider, interoperability, evaluation and deployment architecture  
**Canonical repository:** `google/adk-python`  
**Revision inspected:** `b0180620f4c2f4f4467a89c37a30f75bf849700b` (2026-09-06)  
**Latest stable release observed:** `v2.8.0` (2026-08-26)  
**License:** Apache-2.0  
**Decision status:** research only; no dependency, provider, model, sandbox, workflow, memory or deployment decision

## Scope

Task 22 studies Google ADK as a concrete agent/runtime and interoperability framework relevant to ACL/Vera.

The research focuses on:

- current ADK runtime and agent architecture;
- deterministic workflow execution and replay;
- sessions, scoped state and long-term memory;
- resumability, idempotency and failure semantics;
- tool calling, human confirmation and authority identity;
- code execution and sandbox boundaries;
- local/provider portability through ADK model adapters;
- MCP and A2A interoperability;
- self-hosted API/deployment trust boundaries;
- plugins, guardrails and security interception;
- evaluation and observability;
- current failure/security surfaces;
- reusable mechanisms and non-conclusions for ACL/Vera.

Task 22 does **not** deep-research LiteLLM as an independent project, run model benchmarks, select an architecture/runtime/provider, start Task 23, or authorize worker/model execution.

---

# Executive assessment

Google ADK is a high-value ACL/Vera reference because it separates several concepts that are often collapsed in smaller agent frameworks:

1. agent definition from Runner execution;
2. deterministic Workflow orchestration from model-selected reasoning;
3. session event history from scoped key-value state;
4. session/state from opt-in cross-session memory;
5. provider/model adapters from agent/tool semantics;
6. workflow replay from effect idempotency;
7. application-level tool confirmation from code-execution sandboxing;
8. in-process multi-agent composition from A2A remote-agent composition;
9. runtime plugins/guardrails from host authentication/authorization;
10. operational telemetry/evaluation from authoritative effect and approval evidence.

ADK is particularly useful for ACL because its current resumability documentation says the quiet part explicitly: resumability is **experimental**, **best-effort**, and provides **at-least-once** tool execution. ADK itself says side-effecting tools must be idempotent because a tool can run again if its response event was not persisted. This is direct upstream evidence that replayable orchestration is not exactly-once effect settlement.

ADK also provides a strong current human-confirmation mechanism at the *action-occurrence* level: confirmation is tied back to the exact historical function call ID/name/arguments. However, the approval identity is still derived from `event.author == "user"`. Open/reopened #6461 shows why this is insufficient across remote A2A or unauthenticated HTTP boundaries: a channel/role label is not an authenticated principal. For Vera's future mobile/remote approval path, ADK therefore provides both a pattern to reuse and a failure to avoid:

> bind approval to the exact effect occurrence **and** to a cryptographically/authentically established principal under current policy.

The strongest Task 22 findings for later comparison are:

- Workflow graph validation, dependency-ready concurrency and history-derived resume are strong deterministic orchestration patterns.
- ADK's resumability contract explicitly requires idempotency and admits at-least-once replay.
- DatabaseSessionService now has revision markers, session locking, row locking where supported and stale-writer rejection, but shared state still has semantic read-modify-write risks and app/user scopes are not authority domains.
- Session history, scoped state and long-term memory are explicitly separate systems.
- `partial` streaming events are not session-durable in DatabaseSessionService.
- `temp:` state is invocation-local and deliberately stripped before persistence.
- Code executor choices range from explicitly unsafe local subprocesses to Docker, GKE/gVisor and managed sandboxes; executor identity is behavior/security-bearing deployment state.
- Container execution has useful no-network/cap-drop/no-new-privileges/process-group controls but is not equivalent to high-assurance containment.
- LiteLLM-backed portability is real but current source contains provider/model/backend-specific rewrites; open #6482 demonstrates model-name heuristics can break another OpenAI-compatible backend.
- Current MCP code embodies a strong effect-aware retry rule: retry session establishment only while no remote tool call could yet have occurred.
- A2A remote composition does not automatically preserve in-process shared state semantics (#6854).
- Remote HITL/function-response forwarding remains a current open semantic boundary (#6721).
- Self-hosted FastAPI authentication/authorization is application-owned; helper defaults can fall back from local durable storage to in-memory storage.
- Model Armor is a useful guardrail but does not screen tool outputs and does not replace authorization or sandboxing.
- Runner-global plugins can mutate/short-circuit model/tool/event execution and therefore belong in protected control-plane trust.
- ADK evaluation explicitly separates response quality from tool trajectory and supports repeated runs, which is useful for ACL's future stochastic-model qualification.
- Open #6099 documents a still-missing unified decision ledger connecting tool call, principal/authority, policy refusal and confirmation semantics.

The architectural conclusion is not “use ADK unchanged.” It is:

> Google ADK provides strong reference mechanisms for deterministic workflow orchestration, event/state persistence, explicit memory separation, occurrence-bound confirmations, provider/protocol adapters, sandbox tiers and repeated agent evaluation. ACL/Vera still need stronger authenticated-principal approval, exact effect settlement, protected policy/verifier state, explicit required-durability gates, credential brokering and deployment-specific capability qualification above those mechanisms.

---

# 1. Current project identity and maturity

## 1.1 Canonical upstream

Observed at the Task 22 checkpoint:

- canonical Python repository: `google/adk-python`;
- public and active;
- default branch: `main`;
- current revision inspected: `b0180620f4c2f4f4467a89c37a30f75bf849700b`;
- latest stable release observed: `v2.8.0`;
- Apache-2.0 licensed;
- current upstream describes ADK as code-first and model/deployment agnostic while optimized for Gemini/Google infrastructure.

Primary sources:

- https://github.com/google/adk-python
- https://github.com/google/adk-python/tree/b0180620f4c2f4f4467a89c37a30f75bf849700b
- https://github.com/google/adk-python/releases/tag/v2.8.0
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/README.md

## 1.2 ADK 2.x is a behaviorally meaningful generation boundary

Current README/release material makes ADK 2.0 a material API/runtime generation, not merely cosmetic versioning.

Session/event/agent schemas and workflow/task surfaces have changed through the 2.x line.

### ACL lesson

Do not store `framework=google-adk` as sufficient benchmark or checkpoint identity.

At minimum later profiles need:

`ADK revision/version + model adapter/provider + session service + memory service + executor + workflow/resumability configuration + protocol integrations + plugin/guardrail profile`.

---

# 2. Runtime decomposition

A useful conceptual decomposition is:

`Application / API / client`
→ `Runner`
→ `Agent / Workflow`
→ `model/tool/plugin flows`
→ `SessionService`
→ `MemoryService / ArtifactService / CredentialService`

with additional execution/protocol adapters:

- `CodeExecutor`;
- MCP toolsets;
- A2A remote agents;
- provider/model adapters;
- deployment/runtime host.

This separation is important for ACL/Vera because no one of those components is authoritative for every state/effect domain.

---

# 3. Workflow: deterministic orchestration outside model reasoning

ADK 2.x Workflow provides a graph-oriented deterministic orchestration layer.

Observed capabilities include:

- up-front graph validation;
- ordinary Python nodes;
- `LlmAgent` nodes;
- tools;
- nested workflows;
- dependencies;
- fan-out/fan-in;
- loops;
- retry;
- workflow state;
- dynamic node execution;
- human-in-the-loop;
- typed input/output/state schemas;
- timeout and concurrency controls.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/workflow/workflow/index.md

## 3.1 Dependency-ready branches execute concurrently

The runtime can execute graph-ready branches concurrently while preserving dependency ordering.

### ACL reuse candidate

This is strong precedent for keeping deterministic dependencies and concurrency in the controller/harness rather than expressing them as prose inside a planning prompt.

## 3.2 Dynamic child execution has a distinct scheduling lane

Dynamic `ctx.run_node()` execution is handled differently from normal graph scheduling because the parent waits inline and forcing it through the same graph concurrency limiter could deadlock.

### ACL lesson

Nested/dynamic tasks need explicit resource-accounting semantics.

`parent waits for child` is different from `independent graph node runs when dependency-ready`.

## 3.3 Resume derives completion from durable history

Workflow replay reconstructs which nodes completed from session events and skips completed work.

Nested workflows can replay their graph while suppressing already-completed child execution.

### High-value pattern

Persist enough semantic execution evidence to derive the next legal deterministic transition rather than depending on hidden in-memory control flow.

### Boundary

Skipping a node because its completion event exists does not prove every real-world effect inside that node occurred exactly once.

This distinction is made even clearer by ADK's own experimental resumability contract.

---

# 4. Resumability is explicitly at-least-once

`ResumabilityConfig` is among the most useful Task 22 findings.

Current upstream labels resumability:

- experimental;
- best-effort;
- not guaranteed;
- dependent on resumable tools/agents;
- dependent on durable event state;
- unable to restore transient in-memory state automatically.

Critically, current documentation/source states that resumed tool execution can be **at least once**.

A tool can execute, crash before its response event is persisted, and then execute again on resume.

Upstream therefore requires side-effecting tools to be idempotent or otherwise replay-safe.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/apps/_configs.py

## 4.1 ACL/Vera invariant

A replayable orchestration engine is not an effect ledger.

For effect-bearing work, ACL still needs:

- stable effect ID;
- proposed parameters/resources;
- authorization identity;
- start evidence;
- completion/failure evidence;
- idempotency key where possible;
- reconciliation state after uncertain transport/process failure.

## 4.2 Isolation scope matters on resume

ADK supports resumability isolation scopes to reduce ambiguity when matching function responses in nested/parallel execution.

### ACL lesson

Function/tool response identity should include the logical actor/track/task domain, not only an opaque provider-generated call ID.

---

# 5. Session: event history plus scoped state

Current `Session` separates:

- stable session identity;
- app name;
- user ID;
- state;
- ordered events;
- update time;
- internal storage revision marker.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/sessions/session.py

## 5.1 State is persisted through event deltas

ADK documentation strongly recommends event/action `state_delta` for persisted state changes.

Directly mutating the in-memory `Session.state` snapshot is not equivalent to durable state mutation.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/sessions/state/index.md

### ACL lesson

State mutations should be explicit events/transactions, not incidental mutation of whatever Python object a worker currently holds.

## 5.2 Four state scopes

Current state scopes include:

- ordinary session state;
- `app:` shared application state;
- `user:` shared user/application state;
- `temp:` invocation-only state.

`temp:` values are deliberately not durable.

### Vera relevance

This is useful conceptual separation, but names/scopes are not authorization boundaries.

A value stored under `user:` must still be bound to an authenticated Vera principal, not to a client-provided user string.

## 5.3 `state_schema` has a coverage boundary

Current documentation notes prefixed keys containing `:` are outside normal state-schema validation.

### ACL lesson

If a state subset is security/continuation critical, schema coverage must be explicit and mechanically checked rather than assumed from one root schema declaration.

---

# 6. DatabaseSessionService: meaningful stale-writer protection

Current database-backed session persistence is substantially stronger than a naive append-only chat store.

Observed behavior in `append_event`:

- partial events are not persisted;
- temp state is applied for same-invocation use then stripped before durable write;
- one session append path is guarded by `_with_session_lock`;
- row-level locks are used where supported;
- exact storage revision markers are compared;
- stale session writers raise `StaleSessionError`;
- fallback revision matching exists for older/marker-less session objects;
- state deltas and event insertion are committed together in the SQL transaction;
- the in-memory Session is updated only after storage commit.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/sessions/database_session_service.py

## 6.1 Strong reuse pattern

Use optimistic/durable revision identity rather than timestamp-only “latest” assumptions.

A worker attempting to append against stale state should fail rather than silently overwrite newer state.

## 6.2 Shared-state read-modify-write still needs care

Locking the append transaction does not automatically make arbitrary application-level shared-state read-modify-write atomic.

Two invocations can both read an earlier shared value, independently compute replacements and later serialize writes.

### ACL/Vera rule

For counters, balances, leases, quotas, approval consumption or other concurrency-sensitive values, provide explicit atomic operations/CAS semantics instead of generic dictionary replacement.

---

# 7. Partial stream delivery is not durable session state

Current DatabaseSessionService immediately returns `event.partial` without durable append.

This is a valuable explicit distinction.

### ACL/Vera rule

Separate:

- live progress;
- durable semantic event;
- authoritative state transition;
- verifier/effect evidence.

A user seeing streamed text does not prove the corresponding state is durable or safely resumable.

---

# 8. Session, state and memory are three different systems

ADK's memory architecture is valuable because long-term memory is not implicitly “whatever is in the session.”

Current memory services are separate from session services.

Memory can be:

- added from sessions;
- searched across sessions;
- loaded explicitly through a model tool;
- preloaded automatically into context.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/memory/memory_service/index.md

## 8.1 Memory is opt-in ingestion

A completed conversation does not automatically become cross-session memory merely because a memory service exists.

### Vera reuse candidate

This is a good default:

`conversation happened`
!=
`fact should become long-term memory`.

## 8.2 InMemory and managed memory are materially different

Current options range from process-local keyword memory to Vertex-managed semantic/consolidating memory and other managed retrieval systems.

### ACL/Vera lesson

Memory backend and ingestion/consolidation policy are behavior-bearing identity.

## 8.3 Memory retrieval text is not canonical truth

Preloaded memory becomes model-visible context.

That does not make it:

- verified fact;
- current policy;
- authenticated instruction;
- safe authority input.

Task 18/20 epistemic/provenance lessons remain applicable above ADK memory services.

---

# 9. Tool confirmation: excellent effect binding, weak principal identity

ADK's current confirmation machinery has strong action-occurrence binding.

The confirmation path resolves the original historical function call and checks:

- the function call exists;
- the tool is registered;
- confirmation was actually required/requested;
- tool name matches;
- arguments match;
- response maps to the original call ID.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/flows/llm_flows/request_confirmation.py

## 9.1 High-value ACL pattern

Approval is permission for **one defined action occurrence**, not a general statement such as “yes, allow shell.”

Bind approval to:

- effect occurrence ID;
- canonical tool origin;
- tool definition/schema version;
- normalized arguments/resources;
- task/run/project;
- policy version.

## 9.2 Current security gap: role label is not principal — #6461

Open/reopened #6461 reports that an A2A peer can forge the confirmation response because current code identifies the human response primarily through:

`event.author == "user"`

rather than an authenticated principal carried from the network trust edge.

The issue's attempted fix was reverted because transport-origin metadata was not the same thing as authenticated human identity.

Primary source:

- https://github.com/google/adk-python/issues/6461

### ACL/Vera invariant

A correct approval needs both:

1. exact action/effect binding;
2. authenticated approver principal under current policy.

`role=user`, `channel=mobile`, `came through A2A`, or a user-supplied `user_id` is not enough.

This is directly relevant to Vera's future phone/watch/voice confirmations.

---

# 10. Confirmation is a control-plane pause, not an ordinary tool result

Closed #6977 documented an MCP confirmation loop where the confirmation request was not marked to skip summarization, so it could be fed back through normal model summarization/tool-result flow.

Current main sets `tool_context.actions.skip_summarization = True` for this pause path.

Primary sources:

- https://github.com/google/adk-python/issues/6977
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/tools/mcp_tool/mcp_tool.py

### Regression lesson

Approval/pause state is control-plane state.

Do not accidentally reinterpret it as ordinary model-visible task output and then let the model “resolve” it.

---

# 11. Code execution: multiple containment tiers

ADK supports materially different code-execution backends.

Current documented options include:

- BuiltInCodeExecutor;
- UnsafeLocalCodeExecutor;
- ContainerCodeExecutor;
- GkeCodeExecutor;
- Vertex/Agent Engine sandbox executors.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/code_executors/code_executor/index.md

## 11.1 UnsafeLocal is explicitly unsafe

Upstream explicitly warns against using UnsafeLocalCodeExecutor with untrusted generated code in production.

### ACL lesson

Framework-owned “code execution support” is not a single security property.

## 11.2 ContainerCodeExecutor has meaningful hardening

Current source includes:

- network disabled by default;
- capability dropping;
- `no-new-privileges`;
- process timeout;
- internal process-group/supervisor handling;
- container lifecycle reuse/cleanup.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/code_executors/container_code_executor.py

## 11.3 Process-group settlement is not universal descendant containment

Current source/docs acknowledge malicious code can deliberately detach from an ordinary process group, for example through new sessions/double-fork patterns, until the stronger container boundary is torn down.

### ACL rule

For untrusted code, process-group kill is useful but the authoritative settlement boundary should be the whole sandbox/container/VM/job object/cgroup.

## 11.4 GKE/gVisor and managed sandbox tiers are different capabilities

The stronger backends move isolation responsibilities into Kubernetes/gVisor/managed systems.

### ACL deployment identity

Record:

`executor kind + image/runtime + mounts + network + user + resources + environment + cleanup policy + realized backend`.

Do not reduce this to `sandbox=true`.

---

# 12. Model portability: framework agnostic does not mean adapter uniformity

ADK exposes a broad model abstraction and supports non-Gemini providers.

`LiteLlm` is one current portability adapter.

Task 22 intentionally does not deep-research LiteLLM itself; that is Task 23.

The ADK-side finding is that the adapter contains significant provider/model-specific protocol conversion.

Observed source behavior includes:

- provider-specific message conversion;
- Ollama-specific content handling;
- vLLM reasoning/stream handling;
- Gemma family tool-result role handling;
- thought-signature recovery;
- multiple tool-argument parse/repair paths.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/models/lite_llm.py

## 12.1 Open #6482: model-name heuristic breaks another OpenAI-compatible backend

Open #6482 reports Gemma-4 through LM Studio failing after the first tool call because ADK sets:

`role="tool_responses"`

based on model-name matching.

LM Studio's OpenAI-compatible endpoint validates the standard role set and rejects the non-standard role.

Task 22 checked current main; the model-name-based branch remains present.

Primary source:

- https://github.com/google/adk-python/issues/6482

### ACL lesson

`same model + llama.cpp-family serving stack + OpenAI-compatible endpoint`

does not imply identical tool protocol semantics.

Capability identity must include the serving API and adapter path.

## 12.2 Structured output + tools is a composition capability

Closed #5130 documented a local vLLM/Qwen case where structured output could suppress the expected tool path.

Current API direction has moved toward explicit model capabilities, but exact composition remains deployment-specific.

### ACL lesson

Qualify combinations:

- tools;
- structured output;
- thinking/reasoning;
- streaming;
- long context;
- multimodal;
- provider-specific tool role/message formats.

Do not infer combination support from separate feature flags.

## 12.3 Current provider-specific schema path — #6984

Open #6984 reports ADK 2.8.0/current-main Vertex declaration failure in a legacy tool-schema fallback path where nested Pydantic `$ref/$defs` handling differs from Gemini API behavior.

The reporter explicitly narrowed the bug to the legacy path with `JSON_SCHEMA_FOR_FUNC_DECL` disabled.

### ACL lesson

Tool schema compilation belongs in provider capability qualification, not just model qualification.

---

# 13. MCP integration

Current ADK pins:

`mcp>=1.24,<3`

and current CI explicitly exercises MCP 2.x.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/pyproject.toml

Current `McpTool` supports current input/output schema handling and confirmation behavior.

## 13.1 High-value effect-aware retry rule

Current MCP code contains a particularly useful retry boundary: session establishment/connect retry is allowed only while no tool call could yet have created a remote side effect.

Once the remote effect boundary may have been crossed, blind retry is avoided.

### ACL reuse candidate

Retry automatically only while the system can prove:

`effect_started == false`.

After effect initiation:

- use idempotency identity;
- query/reconcile remote state;
- or escalate uncertain settlement.

## 13.2 MCP protocol identity remains exact-profile state

Task 15 already established the broader MCP version/extension/transport/auth model.

For ADK qualification later, record:

`ADK revision + Python MCP SDK version + protocol era + transport + auth + negotiated extensions + server identity + tool definition digests`.

---

# 14. A2A: remote agents are a real trust and state boundary

ADK's current A2A support is substantial and actively evolving.

Current optional dependency range:

`a2a-sdk[http-server]>=0.3.4,<2`

Current source contains an explicit compatibility layer spanning A2A SDK 0.3.x and 1.x.

Primary sources:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/pyproject.toml
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/a2a/_compat.py

The exact Task 22 head itself fixes an AgentCard capability default, another indication that interoperability metadata is active behavior-bearing code.

## 14.1 Remote state is not in-process shared state — #6854

Open #6854 documents a topology-dependent semantic gap:

- in-process composed agents can share ADK state directly;
- RemoteA2aAgent does not automatically serialize that shared state across the protocol boundary;
- a remote agent can therefore operate without state that an in-process equivalent would see.

Primary source:

- https://github.com/google/adk-python/issues/6854

### ACL/Vera invariant

Remote boundaries require explicit/versioned state contracts.

Do not assume moving a child agent out of process preserves Python-object/session-state semantics.

## 14.2 Remote HITL/function-response relay — #6721

Open #6721 reports ADK 2.7 behavior where a human/function response relayed across A2A can be flattened/reinterpreted such that the remote paused tool does not receive the proper function-response semantics.

Current main still contains explicit logic that sanitizes/rewrites human-input function responses before forwarding, so this remains a meaningful current interoperability fixture even without Task 22 claiming a fresh end-to-end reproduction at `b018062`.

Primary sources:

- https://github.com/google/adk-python/issues/6721
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/agents/remote_a2a_agent.py

### ACL lesson

Approval/control messages must retain:

- effect occurrence identity;
- authenticated principal;
- origin/protocol path;
- expected response type;
- exact destination paused operation.

A string that “looks like a human answer” is not enough.

---

# 15. Current A2A source has meaningful credential/content hardening

Task 22 also found positive current-main behavior in RemoteA2aAgent:

- credential-bearing request/response parts are detected and removed from forwarded history;
- remote AgentCard descriptions are bounded/quoted when sourced over the network;
- remote task/context IDs are carried as protocol metadata;
- request interceptors exist around remote calls.

### ACL/Vera lesson

Remote peer descriptions/messages/agent cards are untrusted data, even when they advertise capabilities.

Credentials should not be flattened into ordinary transcript text where later agents can see/replay them.

---

# 16. Self-hosted FastAPI boundary

ADK's FastAPI helper is useful but deliberately leaves network trust to the application.

The helper can expose:

- run/run_sse;
- sessions;
- artifacts;
- memory/evaluation services;
- optional A2A routes.

Current documentation explicitly instructs applications to add their own authentication/authorization middleware.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/cli/fast_api/index.md

## 16.1 ACL/Vera rule

Authenticate the principal **before** accepting user/session/agent/task IDs as authoritative routing keys.

A URL parameter such as `user_id` is not identity proof.

## 16.2 Durability fallback needs explicit production policy

The helper can use SQLite when the local agents directory is available/writable but can fall back to in-memory services when local persistence is unavailable.

That is convenient for development.

### ACL boundary

For checkpoint/evidence-required unattended work, persistence loss/unavailability must not silently degrade into an in-memory “looks operational” mode.

Make required durability a deployment gate.

---

# 17. Plugin architecture is a powerful protected control plane

Current `BasePlugin` exposes Runner-wide callbacks around:

- user input;
- before/after run;
- events;
- before/after agent;
- before/after model;
- model errors;
- before/after tools;
- tool errors;
- and other lifecycle points.

Plugins execute before ordinary agent callbacks, can mutate inputs and can short-circuit execution.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/plugins/base_plugin.py

### ACL reuse candidate

This is strong precedent for deterministic controller-owned hooks around:

- before_model;
- before_tool;
- before_effect;
- after_tool;
- before_persist;
- before_acceptance;
- on_checkpoint/resume.

### Security boundary

Plugins are privileged executable policy/control-plane code.

A worker must not be allowed to rewrite the plugin that constrains/verifies the worker.

---

# 18. Model Armor: useful guardrail, incomplete trust boundary

ADK 2.8 introduced Model Armor integration.

Current documentation describes screening of model input/output and configurable fail-open/fail-closed behavior on screening failures.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/integrations/model_armor/index.md

Important documented exclusions include:

- text-only scope;
- no image/file screening in the described plugin path;
- tool outputs are not universally screened.

### ACL/Vera lesson

Prompt-injection/content screening is a signal/control layer.

It does not replace:

- source provenance;
- deterministic authorization;
- memory trust policy;
- sandboxing;
- host-side tool argument validation;
- external-effect verification.

Tool/RAG/MCP output can still inject hostile instructions unless the host preserves trust provenance and policy separation.

---

# 19. Current security hardening in v2.8

The v2.8 release contains several security/reliability fixes worth retaining as regression classes rather than present bugs, including:

- BigQuery SQL-injection hardening;
- blocked YAML/ruamel deserialization in agent-config references;
- atomic artifact publication;
- authentication scheme provenance fixes;
- logging fixes to keep sensitive A2A file payloads out of debug lines;
- CLI environment logging reduced to variable names rather than values;
- subprocess cleanup fixes.

Primary source:

- https://github.com/google/adk-python/releases/tag/v2.8.0

### ACL lesson

Agent frameworks combine model reasoning with ordinary privileged software-security surfaces:

- deserialization;
- SQL;
- logs;
- subprocesses;
- path publication;
- auth metadata.

A secure agent architecture still needs conventional software security discipline and regression testing.

---

# 20. Decision provenance remains incomplete — open #6099

Open #6099 asks ADK to emit a first-class decision ledger that joins currently separate evidence:

- tool call;
- authority/principal;
- policy refusal;
- confirmation request/resolution;
- model rationale typed as untrusted.

The issue explicitly notes that ADK already has pieces distributed across:

- session Events;
- callbacks/plugins;
- tool auth config;
- Agent Analytics/telemetry;
- Model Armor;

but not one authoritative decision-semantics record.

Primary source:

- https://github.com/google/adk-python/issues/6099

### ACL reuse lesson

This directly matches ACL's emerging effect/approval evidence model.

The authoritative effect ledger should record **why/under whose authority execution became permissible**, not merely that a tool happened.

Model rationale can be stored, but it is generated/untrusted explanatory text rather than authority evidence.

---

# 21. Evaluation: response quality and tool trajectory are separate

ADK's `AgentEvaluator` supports explicit test cases and metrics.

Current default-style metrics include:

- response matching;
- tool trajectory scoring.

Tool trajectory considers expected tool calls/arguments.

The evaluator supports repeated runs and averages scores, acknowledging model stochasticity.

Current v2.8 adds custom metrics and parallelized LLM-as-judge evaluation.

Primary source:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/evaluation/agent_evaluator/index.md

### Strong ACL benchmark lesson

Score separately:

1. deterministic harness/runtime correctness;
2. required/forbidden tool trajectory;
3. task artifact/verifier success;
4. stochastic semantic/model quality;
5. performance/resource behavior.

Do not collapse everything into one “agent score.”

## 21.1 Repeated runs are useful capability evidence

A model/runtime deployment that passes once is weaker evidence than one that repeatedly passes under a frozen harness/fixture profile.

This aligns with Gemini CLI's `USUALLY_PASSES` lesson.

---

# 22. Observability

ADK exposes OpenTelemetry-style traces/metrics and continues expanding runtime telemetry.

v2.8 includes experimental opt-in metrics such as:

- per-invocation token spend;
- per-workflow inference count;
- per-workflow tool-call count;
- per-workflow token spend;
- MCP HTTP exchange records;
- context-cache metadata.

Primary source:

- https://github.com/google/adk-python/releases/tag/v2.8.0

### ACL boundary

Operational telemetry is useful for:

- runtime diagnosis;
- latency/cost;
- model/tool behavior;
- correlation.

It is not independent acceptance evidence.

Prompt/tool/result content can also be sensitive and needs destination/redaction/retention controls.

---

# 23. Deployment/runtime identity

ADK can run:

- locally/in process;
- through its FastAPI server;
- on Cloud Run;
- on Vertex/Agent Engine;
- with various external sandbox/execution services.

### ACL/Vera lesson

Framework behavior must be qualified in the deployment topology that will actually run.

Important deployment identity includes:

- host/API mode;
- authentication middleware;
- session service/backend;
- memory backend;
- artifact backend;
- credential service;
- code executor/sandbox;
- model/provider;
- A2A/MCP versions/transports;
- plugins/guardrails;
- concurrency/resumability settings.

---

# 24. Current/open failure surfaces worth turning into fixtures

## 24.1 #6461 — forged HITL principal boundary

Current/open/reopened.

Fixture:

- create an effect requiring approval;
- inject a structurally correct FunctionResponse from an unauthenticated/remote actor;
- exact call ID/name/args still match;
- runtime must reject because principal is not authorized.

## 24.2 #6854 — remote A2A state topology mismatch

Current/open.

Fixture:

- run same logical agent graph in-process and over A2A;
- explicitly declare state transferred to remote node;
- assert remote node sees only the contracted state;
- absence must fail visibly, never silently fall back to stale/previous content.

## 24.3 #6721 — remote HITL response-semantic preservation

Current/open.

Fixture:

- remote agent pauses on function/HITL response;
- human resolves it through upstream parent;
- preserve typed function-response semantics, occurrence ID and principal all the way to the paused remote operation;
- assert no fabricated tool-success content occurs.

## 24.4 #6482 — provider/backend tool-role compatibility

Current/open.

Fixture:

- same model through multiple OpenAI-compatible serving backends;
- tool call then tool result;
- validate exact backend-accepted roles/message schema;
- classify adapter/backend failure separately from model reasoning.

## 24.5 #6984 — provider-specific tool-schema compilation

Current/open legacy-path issue.

Fixture:

- nested schemas + fallback-parsed parameters;
- generate declarations for Gemini API and Vertex variants;
- require semantically equivalent accepted schema or explicit unsupported failure;
- never silently change required constraint meaning.

## 24.6 #6977 — confirmation control-state regression

Fixed/current-main lesson.

Fixture:

- confirmation request must pause as control-plane state;
- it must not be summarized/interpreted as ordinary tool output before the authorized response arrives.

## 24.7 Persistence fallback

Deployment fixture:

- intentionally make configured durable store unavailable;
- production ACL/Vera profile must refuse checkpoint-required execution rather than silently switching to process-local state.

---

# 25. Failure taxonomy derived from ADK

Task 22 reinforces separate failure classes:

1. model reasoning failure;
2. provider adapter/protocol failure;
3. tool schema compilation failure;
4. structured-output/tool composition failure;
5. session stale-writer failure;
6. semantic shared-state race;
7. replay/idempotency failure;
8. confirmation occurrence mismatch;
9. confirmation principal-authentication failure;
10. A2A state-transfer failure;
11. A2A typed-control-message conversion failure;
12. MCP transport/session failure before effect;
13. MCP/effect uncertainty after effect boundary;
14. sandbox/executor containment failure;
15. process-tree cleanup failure;
16. persistence/durability degradation;
17. plugin/guardrail policy failure;
18. memory provenance/epistemic failure;
19. evaluator/telemetry evidence failure;
20. deployment auth/authz failure.

Do not score all of these as “the model failed.”

---

# 26. Concrete ACL/Vera candidate invariants from Google ADK

1. Deterministic workflow/dependency execution lives outside model reasoning prompts.
2. Workflow topology is validated before execution.
3. Dynamic child execution and graph-scheduled execution have explicit different resource semantics.
4. Durable history can drive replay/skip decisions, but replay safety is not exactly-once effects.
5. Resumability has an explicit contract and known guarantee level.
6. At-least-once tool replay requires idempotency/effect identity/reconciliation.
7. Temporary in-memory state is explicitly excluded from continuation guarantees.
8. Session, key-value state and long-term memory are separate planes.
9. Session state changes use explicit durable deltas/events rather than incidental object mutation.
10. Shared app/user state scope is not authenticated principal identity.
11. Concurrency-sensitive shared state needs atomic operations/CAS, not generic dictionary replacement.
12. Durable sessions carry exact revision/generation markers where possible.
13. Stale writers fail rather than silently overwriting newer state.
14. Partial streaming output is distinct from durable session state.
15. `temp:` state is never mistaken for durable continuation state.
16. Long-term memory ingestion is explicit rather than every conversation automatically becoming memory.
17. Retrieved memory remains untrusted/contextual evidence until provenance/truth policy says otherwise.
18. Approval binds to one exact effect occurrence and normalized arguments.
19. Approval also binds to an authenticated principal; `author=user` is not enough.
20. Protocol/channel/role identity never substitutes for authentication.
21. Confirmation/pause state is control-plane state, not ordinary tool output.
22. Local/unsafe/container/GKE/managed code executors are separately qualified capability profiles.
23. Process-group termination is not equivalent to whole-sandbox or external-effect settlement.
24. Worker/code-execution environments have explicit network/mount/user/resource/credential policy.
25. Framework/provider model agnosticism does not imply deployment behavior parity.
26. Exact model adapter + serving backend + API route + model artifact/settings is deployment identity.
27. Tool/schema and structured-output capabilities are tested in required combinations.
28. Provider-specific schema compilers/adapters are part of the trusted effect path.
29. MCP retries are automatic only before the system can prove any remote effect may have occurred.
30. Once an effect boundary may be crossed, retry requires idempotency/reconciliation evidence.
31. Remote A2A agents receive explicit serialized state contracts; in-process shared state never crosses implicitly.
32. Remote HITL responses preserve typed semantics, effect identity, destination and principal provenance.
33. Remote agent descriptions/cards/messages are untrusted content.
34. Credential-bearing protocol parts are filtered before history is flattened/re-shared.
35. Self-hosted API authentication/authorization is an explicit deployment requirement.
36. Client-supplied user/session/task IDs are routing data until bound to an authenticated principal.
37. Required persistence cannot silently fall back to memory-only storage.
38. Plugins/guardrails are privileged executable control-plane code protected from worker mutation.
39. Guardrail/content screening is distinct from deterministic authorization and sandboxing.
40. Tool outputs/RAG/MCP content need provenance and prompt-injection treatment even when model input/output screening exists.
41. Decision evidence records authority/principal, policy/refusal and approval semantics separately from model rationale.
42. Model rationale is untrusted generated explanation, not permission evidence.
43. Evaluation separates tool trajectory, deterministic artifact verification and semantic response quality.
44. Stochastic behavioral capability requires repeated trials under one frozen deployment profile.
45. Runtime telemetry and authoritative verifier evidence have different trust/audience/retention semantics.
46. Deployment topology is part of behavior/security identity.
47. Fixed upstream bugs remain versioned regression fixtures after repair.
48. Current open issues are evidence-scoped and must be rechecked before dependency selection.
49. ADK does not own ACL project/task/effect scheduling or exactly-once external-effect settlement.
50. No framework-level “agentic” feature may bypass ACL's outer policy/effect/verifier authority.

---

# 27. High-value ACL/Vera regression fixtures from Task 22

## Fixture A — authenticated exact approval

- tool occurrence requires confirmation;
- exact ID/name/args are known;
- authorized principal approves → accepted;
- unauthenticated remote actor sends identical payload → rejected;
- different args under same call name → rejected.

## Fixture B — replay after effect-before-response crash

- side-effecting tool executes;
- crash before response event persists;
- resume occurs;
- no duplicate effect without idempotency/reconciliation proof.

## Fixture C — stale session writer

- load same durable session into two workers;
- writer A commits;
- writer B attempts append against stale revision;
- B must fail and reload/reconcile.

## Fixture D — semantic shared-state race

- two invocations read same user/app counter;
- both update concurrently;
- generic last-write-wins must not be accepted for an atomic counter requirement.

## Fixture E — partial stream versus durable history

- emit partial user-visible output;
- crash before final durable event;
- resume must not claim partial output is settled session/effect state.

## Fixture F — A2A explicit state contract

- remote child needs one task field;
- field absent → explicit failure;
- stale prior-session content must not substitute.

## Fixture G — remote HITL type preservation

- remote child pauses with typed function response request;
- parent/UI resolves;
- typed response + occurrence/principal survives transport unchanged.

## Fixture H — provider tool protocol matrix

- exact same model through Ollama/vLLM/LM Studio/OpenAI-compatible endpoint;
- tool call/result/structured-output fixtures;
- record adapter/backend-specific failures separately.

## Fixture I — executor containment

- child process spawns descendants/attempts detach;
- timeout/cancel;
- sandbox boundary must prove no surviving workload under the required profile.

## Fixture J — persistence unavailable

- configured durable state path fails;
- checkpoint-required task must refuse to start/continue rather than silently switch to ephemeral state.

## Fixture K — MCP pre-effect retry

- connection fails before tool dispatch → retry allowed under policy;
- failure after ambiguous tool dispatch → no blind replay.

## Fixture L — decision ledger completeness

For every effect-bearing call, protected evidence can answer:

- what action;
- who/which role proposed it;
- which principal authorized it;
- which policy version allowed/refused it;
- whether confirmation was required/resolved;
- whether effect started/settled;
- independent verification result.

---

# 28. What Google ADK does not solve for ACL/Vera

Task 22 found no basis to delegate these responsibilities to ADK itself:

- ACL project/backlog/dependency scheduling;
- local-worker role selection;
- benchmark promotion policy;
- protected worker workspace policy;
- exactly-once external-effect identity;
- external-effect reconciliation after ambiguous failure;
- independent verifier ownership;
- credential vault/broker policy;
- authenticated Vera household/user/device identity;
- distributed authoritative writer fencing across arbitrary project state;
- Vera epistemic memory truth/provenance/conflict policy;
- cross-project component selection;
- final ACL/Vera architecture.

ADK is strongest as reference/product infrastructure for:

- deterministic workflows;
- session/event/state service boundaries;
- opt-in memory;
- resumability semantics;
- exact-call HITL binding;
- provider/model adapters;
- MCP/A2A integration;
- code-executor tiers;
- plugins/guardrails;
- repeated agent evaluation and telemetry.

---

# 29. Later comparison questions

When the research campaign reaches synthesis:

1. Does ACL need ADK's full Workflow graph runtime, MAF/LangGraph equivalent, or a smaller durable scheduler implementing only dependency/state essentials?
2. Which ADK SessionService revision/stale-writer ideas outperform the prior runtime candidates?
3. Should Vera use ADK memory services directly, Letta/Graphiti memory layers, or a composed custom memory architecture?
4. Can ADK's exact-call confirmation structure be reused while replacing `author=user` with ACL/Vera authenticated principal policy?
5. Which ADK sandbox/code-executor tiers provide value beyond Codex/OpenHands/MAF candidates?
6. Which provider/local-model path is transparent enough for the user's future 32K benchmark?
7. How much of ADK's non-Gemini portability actually comes from LiteLLM, and what remains ADK-specific after Task 23?
8. Which A2A semantics are genuinely useful for Vera remote agents after MAF/Gemini CLI/ADK comparison?
9. Does ADK's MCP adapter preserve enough modern protocol identity/security to consume directly under ACL-owned authorization?
10. Which ADK plugin/interceptor mechanisms are stable enough to host protected ACL policy/verifier hooks?
11. Should required persistence fail closed rather than inherit ADK development fallback behavior?
12. Which evaluator metrics/trajectory machinery should influence ACL's 32K benchmark lab?
13. Is ADK more valuable as a complete runtime, protocol/provider adapter collection, or pattern source?

No answer is selected in Task 22.

---

# 30. Primary source inventory

Canonical project/release:

- https://github.com/google/adk-python
- https://github.com/google/adk-python/tree/b0180620f4c2f4f4467a89c37a30f75bf849700b
- https://github.com/google/adk-python/releases/tag/v2.8.0
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/README.md

Workflow/resume:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/workflow/workflow/index.md
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/apps/_configs.py

Sessions/state/memory:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/sessions/session.py
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/sessions/database_session_service.py
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/sessions/state/index.md
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/memory/memory_service/index.md

Confirmation/tools/security:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/flows/llm_flows/request_confirmation.py
- https://github.com/google/adk-python/issues/6461
- https://github.com/google/adk-python/issues/6977
- https://github.com/google/adk-python/issues/6099

Execution/sandbox:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/code_executors/code_executor/index.md
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/code_executors/container_code_executor.py

Provider/local compatibility:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/models/lite_llm.py
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/utils/output_schema_utils.py
- https://github.com/google/adk-python/issues/6482
- https://github.com/google/adk-python/issues/5130
- https://github.com/google/adk-python/issues/6984

MCP:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/tools/mcp_tool/mcp_tool.py
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/pyproject.toml

A2A:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/agents/remote_a2a_agent.py
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/a2a/_compat.py
- https://github.com/google/adk-python/issues/6854
- https://github.com/google/adk-python/issues/6721

Self-host/plugin/guardrail:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/cli/fast_api/index.md
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/src/google/adk/plugins/base_plugin.py
- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/integrations/model_armor/index.md

Evaluation/telemetry:

- https://github.com/google/adk-python/blob/b0180620f4c2f4f4467a89c37a30f75bf849700b/docs/guides/evaluation/agent_evaluator/index.md
- https://github.com/google/adk-python/releases/tag/v2.8.0

---

# Conclusion

Google ADK is a high-value architecture reference because it combines deterministic workflows, explicit event/state/session boundaries, opt-in long-term memory, provider/protocol portability, human confirmation, multiple code-execution tiers, plugins/guardrails and repeated agent evaluation in one active framework.

The strongest mechanisms to carry forward are:

- graph validation and dependency-ready deterministic Workflow execution;
- history-derived replay/skip semantics;
- explicit experimental/best-effort resumability contract;
- direct acknowledgment of at-least-once tool replay;
- exact revision markers/stale-writer rejection in database session persistence;
- explicit partial/temp versus durable state distinctions;
- separate session/state/memory planes;
- exact function-call confirmation binding;
- code-executor tiers and process/resource isolation controls;
- effect-aware MCP retry before any remote effect can occur;
- explicit A2A compatibility/state boundaries;
- runner-global plugin/interception seams;
- repeated tool-trajectory/response evaluation;
- expanding OpenTelemetry/runtime metrics.

The strongest warnings are:

- at-least-once replay is not exactly-once effect settlement;
- `author=user` is not authenticated approval authority;
- remote A2A composition does not preserve in-process state automatically;
- remote HITL response conversion is still a current open semantic boundary;
- model/provider compatibility requires exact adapter/backend qualification;
- self-hosted authentication/authorization is application-owned;
- local persistence can have development-friendly memory fallback behavior that is unsuitable for mandatory durable ACL work;
- plugins/guardrails are powerful trusted code, not a sandbox;
- Model Armor does not cover every tool/retrieval output path;
- runtime events/telemetry still do not form the unified authority/policy/approval decision ledger requested in #6099;
- framework checkpoints, sessions and remote protocol tasks remain below ACL/Vera effect identity and independent verification.

Task 22 therefore supports treating Google ADK as a serious later comparison candidate for **workflow/session/provider/protocol/evaluation mechanisms**, while retaining ACL/Vera ownership of authenticated principal identity, external-effect settlement, protected policy/verifier code, credential governance, required-durability policy and provenance-aware long-term memory.

No Google ADK dependency, workflow engine, provider, model, sandbox, memory backend, A2A/MCP architecture or cross-project winner is selected here.

**Stopped before LiteLLM.**
