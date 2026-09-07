# LlamaIndex deep research

**Task:** 29  
**Project:** `run-llama/llama_index` plus its separately versioned `llama-index-workflows` runtime in `run-llama/llama-agents`  
**Research date:** 2026-09-07  
**Scope:** research only; no adoption, framework winner, model/runtime assignment, benchmark execution, or ACL/Vera implementation decision

## Executive assessment

LlamaIndex is no longer usefully described as only a RAG/indexing library. Current OSS combines a large data/retrieval integration ecosystem with agents, typed event-driven Workflows, multi-agent handoffs, memory, MCP/AG-UI protocol integrations, observability and code-action agents. Its strongest ACL/Vera value is as reference material for separating model-facing agent logic from explicit workflow state, memory, retrieval/index state and pluggable provider/tool integrations.

A particularly important current architecture fact is that the workflow runtime has been split out of `llama-index-core`: current core imports `Workflow` from the separately versioned `llama-index-workflows` package, whose source lives in the `run-llama/llama-agents` repository. Therefore a future benchmark or deployment manifest cannot identify behavior with the `llama-index-core` version alone. It must also identify the Workflows runtime revision/profile and every behavior-bearing integration package.

Latest observed stable LlamaIndex release is **v0.14.24**, published 2026-08-19. Current `run-llama/llama_index` main is `d2ac544a27c73d2a68e9c57efec4b2ac0ef99892` (2026-09-03), while `llama-index-core/pyproject.toml` still reports **0.14.24**. Exact commit therefore remains part of identity even when the package version has not advanced.

Task 29 found several high-value ACL/Vera regression fixtures. Open #22559 shows a workflow step waiting for external input can replay from the top and repeat a pre-wait side effect; a fresh nondeterministic waiter ID can also break response matching. Open #22071 shows `workflow_as_mcp()` reusing one mutable Workflow instance across MCP clients, allowing `self.*` state to leak between tenants despite per-run Context objects. Open #22701 shows a shared `VectorMemoryBlock` pinning later sessions to the first session's filter. Open #22248 shows host workflow state and the model-visible state projection can diverge. The separate Workflows runtime's current `cancel_run()` also makes cancellation request and cancellation settlement explicitly different states.

These are harness/runtime/state failures, not model-quality failures. LlamaIndex does not replace ACL-owned effect identity/idempotency, process and sandbox custody, credential policy, durable writer fencing, reconciliation, checkpoint authority or independent verification. For Vera, LlamaIndex Memory/RAG mechanisms likewise do not replace authenticated memory scope, provenance/truth policy, memory-poisoning controls or erasure settlement.

## 1. Project and package identity

### Observed facts

- Latest observed GitHub release: **v0.14.24**, published 2026-08-19.
- Current `llama_index` main: `d2ac544a27c73d2a68e9c57efec4b2ac0ef99892`.
- Current `llama-index-core/pyproject.toml` still reports **0.14.24**.
- The starter `llama-index` package bundles core plus selected integrations; `llama-index-core` supports a customized install with chosen integration packages.
- The current README says the ecosystem contains more than 300 integration packages.
- LlamaParse/LlamaCloud/LlamaAgents hosted products are separate deployment/product surfaces from OSS framework behavior and must not be treated as equivalent to self-hosted OSS.

### ACL implication

A reproducible LlamaIndex profile should record at least:
- `llama-index-core` release and source commit;
- `llama-index-workflows` release/revision/runtime adapter;
- agent class/profile (`FunctionAgent`, `ReActAgent`, `CodeActAgent`, `AgentWorkflow`);
- every LLM/embedding/vector/tool/protocol integration package and version;
- model artifact/runtime/template/context/tool mode;
- memory implementation and storage backend;
- workflow Context serializer/durability profile;
- sandbox/code executor profile if code execution is enabled;
- observability/evaluator profile.

A package name such as `llama-index` is too coarse to establish behavior.

## 2. Workflows are a separately versioned runtime boundary

### Observed fact

Current `llama-index-core/llama_index/core/workflow/workflow.py` simply re-exports `Workflow` and `WorkflowMeta` from `workflows.workflow`. Core declares `llama-index-workflows>=2.14.0,<3` as a dependency. The current Workflows source is maintained in `run-llama/llama-agents`, not inside `run-llama/llama_index`.

The Workflows runtime is an event-driven orchestrator with typed steps/events, streaming, external events, cancellation and pluggable runtime/durability concepts. `WorkflowHandler` has a `run_id`, streams events and delegates lifecycle operations to an external runtime adapter.

### ACL implication

This is a useful architectural precedent: **framework surface and execution runtime are separate behavior-bearing identities**. A model benchmark could change solely because the Workflows package/runtime changed while `llama-index-core` stayed at the same version.

### Candidate invariant

Benchmark manifests record both high-level framework and low-level workflow/runtime identities. An apparently unchanged framework package does not imply unchanged lifecycle semantics.

## 3. Agent architecture

Current agent API exposes:
- `FunctionAgent` for native/function-calling tool use;
- `ReActAgent`;
- `CodeActAgent` for model-authored code actions;
- `AgentWorkflow` for multi-agent handoff orchestration;
- typed stream/input/output/tool-call events.

`AgentWorkflow` is itself a Workflow. It stores active-agent identity, shared state, memory, handoff configuration and iteration data in Workflow `Context`. Multiple agents require explicit names/descriptions and one root agent. `can_handoff_to` can restrict which named agent may be selected next.

### ACL implication

This is useful separation of **agent definition**, **workflow orchestration** and **runtime state**, but `can_handoff_to` remains an orchestration route constraint, not a security capability. A child or peer agent's effect authority still needs host-owned credentials, tool capabilities, filesystem/network limits and task/effect policy.

### Candidate invariant

Agent definition identity, agent invocation identity, workflow run ID, Context/session identity, protocol request identity, tool-call identity and external-effect identity remain distinct.

## 4. Workflow Context is runtime state, not a full checkpoint

Current documentation states `AgentWorkflow` is stateless between runs by default. Reusing a `Context(workflow)` preserves state/history between runs. Context can be serialized and restored through `Context.to_dict()` / `Context.from_dict()` using `JsonSerializer`, or `JsonPickleSerializer` when arbitrary objects require pickle.

Tools can receive the Context and atomically edit an in-process state view through `ctx.store.edit_state()`.

### ACL implication

Serializable Context is useful continuation evidence, but it is not an ACL-safe checkpoint by itself. It does not prove:
- workspace state is committed/settled;
- child processes terminated;
- provider/tool requests stopped;
- external effects were reconciled;
- credentials/policy remain valid;
- verifier acceptance occurred;
- derived index/vector state is synchronized.

`JsonPickleSerializer` also creates an executable-deserialization trust boundary: pickle-backed Context artifacts must be treated as trusted executable state, not untrusted data.

### Candidate invariant

A restored Context may nominate where execution should continue, but ACL revalidates current authority and settlement before allowing effect-bearing continuation.

## 5. Context and Memory are separate state planes

LlamaIndex documentation explicitly separates Workflow `Context` from agent `Memory`. Context carries runtime/workflow state; Memory carries conversation history and optional longer-term memory blocks. HITL/resume deployments can require both.

This distinction is high value for Vera. Conversation/runtime continuation, long-term memory, raw evidence and derived retrieval/index state should not collapse into one store simply because all can influence a prompt.

### Candidate invariant

Maintain separate identities and lifecycle rules for:
- workflow/runtime Context;
- conversational memory;
- long-term semantic memory;
- raw source evidence/documents;
- embeddings/vector index;
- graph/index metadata;
- model-visible assembled context.

Persistence in one plane does not prove persistence, freshness or authorization in another.

## 6. Replay semantics and external effects — issue #22559

### Observed failure

Open issue #22559 reproduces `ctx.wait_for_event(...)` on `llama-index-core==0.14.23` with a single non-parallel step. When an event arrives while waiting, the step can re-enter from the top using the same original event. Any side effect before the wait therefore executes again.

The reporter observed a billed external verdict API execute seven times for one logical gated action. The same issue demonstrates a second failure: generating a fresh UUID waiter ID inside the replayed step means the resumed execution waits on a different ID from the response already sent, eventually hanging until timeout.

### ACL implication

This is a direct at-least-once execution lesson. Workflow replay/resume is not exactly-once effect execution.

### Candidate invariants

- Every effect-bearing operation has a stable logical effect/idempotency identity before it crosses an external boundary.
- Persist effect request/settlement state before replay points such as human waits.
- Stable continuation/waiter IDs are derived from logical invocation identity, not generated anew on each replay.
- A resumed step must reconcile already-attempted effects instead of blindly reissuing them.

### Regression fixture

Place a deterministic counted/billed fake effect before `wait_for_event`; inject several unrelated/matching events and verify one logical effect occurs exactly once or is explicitly reconciled rather than repeated.

## 7. Cancellation request is not cancellation settlement

Current `llama-index-workflows` `WorkflowHandler.cancel_run(timeout=5.0)` calls the runtime adapter's `cancel()`, then waits for the result task only up to a timeout. Exceptions, timeout and cancellation exceptions are swallowed in that method. The older hard `cancel()` path is deprecated and can be unavailable when the runtime does not support the compatibility abort operation.

### ACL implication

`await handler.cancel_run()` returning is not, by itself, proof that every underlying provider request, tool process, external API operation or effect has stopped. Cancellation support also depends on the selected runtime adapter.

### Candidate lifecycle states

1. cancellation requested;
2. runtime acknowledged;
3. workflow no longer dispatches new work;
4. provider/tool/process work terminated;
5. external effects reconciled;
6. resources/workspace settled.

Retry/replay is safe only after the relevant settlement state is known.

## 8. Tool failures can become model-visible data

Current `AgentWorkflow._call_tool()` catches ordinary tool exceptions and converts them into `ToolOutput` with `is_error=True`, exception text/content and the original input. The workflow can therefore continue and the model may react to the error rather than the entire run failing.

### ACL implication

This can be useful for recovery, but a caught tool exception does not establish that the tool had no side effect. The failure may have occurred after an external service committed an operation.

### Candidate invariant

Tool execution status and effect settlement status are separate. Model-visible `is_error=True` must never by itself authorize automatic replay of an effect-bearing operation.

## 9. Deterministic tool I/O remains an application control-plane concern

Open feature request #20386 documents a production need for reusable pre/post tool I/O mediation, especially for MCP:
- host-stamp an authenticated/customer identifier instead of trusting an LLM-provided argument;
- deterministically reduce/redact a large tool result before it enters model context.

LlamaIndex offers tool wrappers/callback patterns, but the issue argues there is not one generalized cross-tool/MCP middleware seam that automatically provides this policy.

### ACL implication

This strongly aligns with ACL's existing design direction: authoritative identity/credentials/effect arguments are injected by protected host policy, not proposed by the model. Tool results should likewise cross an explicit deterministic projection/redaction boundary before reaching a model.

### Non-conclusion

This issue is a feature/design signal, not proof that secure mediation is impossible in LlamaIndex; applications can wrap tools today. ACL should preserve the invariant independently of whichever wrapper/hook mechanism is used.

## 10. Multi-agent handoffs do not create security isolation

`AgentWorkflow` builds a handoff tool that allows the model to nominate another configured agent, subject to `can_handoff_to`. Active agent identity is stored in Context and updated as orchestration proceeds.

### ACL implication

Useful routing semantics should remain below a stronger authority model. A parent handing off to a child must not automatically transfer all parent credentials, filesystem/network authority or external-effect capability.

### Candidate invariant

Handoff transfers task/control context, not ambient authority. Child capability is independently derived and cannot exceed the parent/task ceiling.

## 11. MCP workflow serving can leak mutable instance state — issue #22071

### Observed failure

Open issue #22071 reports `workflow_as_mcp(workflow: Workflow, ...)` registering a closure over one Workflow object and calling `workflow.run(...)` on that same instance for every MCP client. Each run has its own Context, but anything stored on mutable `self.*` fields is shared.

The issue's two-client reproduction stores tenant IDs on the workflow instance. Bob's result includes Alice's earlier tenant ID. Concurrent calls interleave the same shared instance state. Current main still exposes `workflow_as_mcp(workflow: Workflow, ...)`, corroborating the relevant API shape.

### ACL implication

Per-request Context does not imply per-request object isolation. Workflow object lifetime is a security/lifecycle profile of an MCP server.

### Candidate invariants

- Request/session/principal state lives in request/session-scoped containers, not reusable workflow instance fields.
- Shared workflow definitions are immutable or explicitly synchronized.
- Where mutable instance state is required, instantiate a fresh workflow per isolated principal/run or enforce equivalent fencing.
- MCP server identity, workflow instance identity, Context identity and ACL effect identity are recorded separately.

### Regression fixture

Serve one workflow to alternating concurrent tenant A/B calls; mutate both Context and `self.*`; verify no cross-tenant data appears.

## 12. Memory session isolation — issue #22701

### Observed failure

Open #22701 reports a current-main `VectorMemoryBlock` bug. `_aget()` mutates the block's own `query_kwargs` by inserting the first `session_id` metadata filter it sees. Reusing the same block for Session B therefore retains Session A's filter and can retrieve A's messages instead of B's. It also mutates caller-owned `MetadataFilters` and `_aput()` removes `session_id` from caller-owned ChatMessage metadata.

### Vera implication

A reusable memory component must not cache per-principal/per-session scope into shared mutable configuration. Session IDs are scope-bearing metadata, not authenticated identity, and caller-owned objects should not be silently mutated across state boundaries.

### Candidate invariants

- authoritative memory scope is host-stamped per call;
- per-call filters are copied/constructed per invocation;
- shared memory definitions remain immutable across principals;
- retrieval tests include alternating and concurrent tenant schedules;
- storage namespace is not authentication.

## 13. Workflow state and model-visible state projection can diverge — issue #22248

Open #22248 reports that after a tool updates `ctx.store["state"]`, a subsequent LLM step can fail to receive the refreshed `state_prompt`; the stored state changes but the model-visible projection remains stale/raw.

### ACL/Vera implication

Canonical host state and its prompt projection are different representations. A successful state mutation does not prove the next model call saw it.

### Candidate invariant

Every model-visible state projection has an explicit source-state version/hash. Integration tests prove that mutations become visible at the intended next reasoning boundary, while stale projections are rejected or labeled.

## 14. Memory poisoning and epistemic authority

Open #21666 requests a generalized memory-poisoning defense for persistent LlamaIndex memory. The issue is a design/security signal rather than proof of one specific exploit, but the underlying principle is important: content surviving in Memory, a vector store or an index does not become trusted instruction or verified truth through persistence.

### Vera implications

- Retrieved memory remains untrusted evidence/content.
- Memory text cannot grant tool, credential, policy or role authority.
- High-risk persistent facts need provenance, source trust, verification and supersession semantics.
- Memory-write screening is defense-in-depth, not a replacement for authorization.

## 15. CodeActAgent delegates containment to the supplied executor

Current `CodeActAgent` asks the model to emit Python inside `<execute>...</execute>` tags. It requires a caller-provided `code_execute_fn` and wraps that callback as the `execute` tool. It does not itself define an OS sandbox.

The prompt explicitly encourages persistent top-level variables/functions across snippets. A scratchpad is stored in Workflow Context, and code output is fed back into model context.

### ACL implication

`CodeActAgent` support is **not sandbox support**. Isolation quality is entirely determined by the supplied executor and its deployment:
- process/container/VM boundary;
- user/capabilities;
- mounts;
- network;
- resource limits;
- environment/credentials;
- process-tree cleanup;
- persistence/snapshot policy.

### Candidate invariant

Record the exact `code_execute_fn` implementation and realized sandbox profile as first-class harness identity. Generated code output is untrusted model input when returned to the reasoning loop.

## 16. RAG/indexing is a multi-plane state machine

LlamaIndex's data framework separates source documents/nodes, transformations, embeddings, indices/vector stores, retrieval and response/citation projections. The v0.14.24 release contains several recent fixes demonstrating that these representations can diverge:
- #22133 fixed `IngestionPipeline` upserts dropping nodes from a document;
- #22537 gave citation nodes independent IDs/offsets;
- #22125 skipped empty HTML nodes;
- #22126 corrected an MMR filtering edge case.

### Vera/ACL implication

If LlamaIndex-style retrieval becomes part of Vera, a successful ingestion call cannot be treated as proof every derived plane is complete or current. Updates/deletes/migrations need explicit accounting across source, parsed nodes, embeddings, vector/index metadata, caches and citations.

### Candidate invariant

Primary evidence is canonical; embeddings/indexes/citations are rebuildable derived state with recorded generation/model/schema identity and explicit reconciliation status.

## 17. Chat/message/protocol projections require cross-plane tests

The v0.14.24 release also fixed several representation-boundary failures:
- #22124 preserved multiblock chat history writes;
- #22179 populated streamed response text before memory persistence;
- #22162 honored agent-specific structured-output configuration inside `AgentWorkflow`;
- AG-UI #22103 now raises rather than fabricating a missing `tool_call_id`;
- AG-UI #22109 persists frontend tool messages;
- AG-UI #22189 isolates initial state copies.

### ACL implication

Provider response, canonical `ChatMessage` blocks, memory persistence, protocol/UI representation and evaluator input are separate representations. Regression tests must prove identity/content survives every intended projection.

The AG-UI choice to fail rather than fabricate a tool-call ID is particularly useful: missing authoritative correlation identity should become explicit failure, not invented state.

## 18. Local/model/provider portability

LlamaIndex has a broad integration ecosystem. Current source includes official Ollama LLM and embedding integrations; the Ollama LLM implements the framework's function-calling interface. The v0.14.24 release also includes a `llama-index-llms-llama-cpp` fix to report the model's **effective context window**.

### ACL implication

Nominal “supports Ollama/llama.cpp/provider X” is not enough. Future 32K qualification records:
- exact model artifact/tokenizer/template;
- inference runtime/version;
- exact LlamaIndex integration package/version;
- requested and measured/effective context;
- native tool/function-calling behavior;
- structured-output path;
- streaming behavior;
- retries/timeouts;
- embedding model/dimension for retrieval profiles.

A provider integration is a behavior-bearing adapter, not a transparent transport.

## 19. Context budget and retrieval profile are benchmark identity

LlamaIndex can assemble prompt context from Memory, retrieved nodes, tool results, state prompts and agent scratchpads. A result measured with one retrieval top-k, reranker, memory budget, context trimming policy or embedding/index profile is not directly comparable to another.

### Candidate benchmark manifest

Record:
- source corpus and document version;
- parser/chunker/transformation versions;
- embedding model/dimension;
- vector/index backend and filter semantics;
- retriever/top-k/MMR/reranker settings;
- memory blocks and budgets;
- agent state/context projection policy;
- model effective context;
- exact agent/workflow runtime profile.

## 20. Observability and evaluation

Current documentation exposes OpenTelemetry instrumentation (`LlamaIndexOpenTelemetry`) and integrations such as LlamaTrace. LlamaIndex also provides evaluation surfaces for retrieval/response quality.

### ACL implication

These are useful evidence sources but are not independent acceptance authority. Runtime traces are produced by/around the system under test, while model-as-judge evaluation is itself a stochastic model profile.

### Candidate invariant

For any evaluation record, freeze evaluator implementation/model/prompt/dataset and preserve independent deterministic host evidence where machine-observable. Traces containing queries, retrieved documents, memory, tool inputs/outputs or model prompts are sensitive operational data with separate retention/access policy.

## 21. Current failure taxonomy for ACL/Vera

Task 29 suggests classifying LlamaIndex failures into distinct lanes rather than “model failed”:

- **workflow replay/effect failure:** #22559;
- **workflow object isolation failure:** #22071;
- **memory scope/isolation failure:** #22701;
- **state projection freshness failure:** #22248;
- **tool/effect ambiguity:** exception converted to `ToolOutput` after possible side effect;
- **cancellation settlement failure:** graceful cancel timeout/unknown backing work;
- **representation/protocol failure:** recent AG-UI/chat-history/stream-memory fixes;
- **ingestion/index integrity failure:** #22133 and related node/citation fixes;
- **provider/adapter/context metadata failure:** llama.cpp effective-context fix and integration-specific behavior;
- **model capability failure:** only after the surrounding harness/runtime/integration passed its deterministic fixtures.

## 22. Candidate ACL/Vera invariants derived from Task 29

1. Framework package and independently versioned workflow runtime are separate identity fields.
2. Every integration package/version is behavior-bearing deployment identity.
3. Agent definition, invocation, workflow run, Context, protocol request, tool call and effect IDs remain distinct.
4. Workflow replay is at-least-once unless exact-once effect behavior is independently established.
5. Effect IDs/idempotency state are created before replay/HITL boundaries.
6. Continuation/waiter correlation IDs remain stable across replay.
7. Resume reconciles previous effect attempts before issuing replacements.
8. Cancellation request, loop stop, backing operation termination and effect settlement are separate states.
9. Returning from a bounded cancel wait cannot be interpreted as proof of settlement.
10. Tool exception/error payload is not proof the effect did not execute.
11. Authoritative principal/domain arguments are host-stamped before tool execution.
12. Tool output crosses deterministic projection/redaction before model exposure where required.
13. Handoff/routing constraints are not security capabilities.
14. Per-run Context does not isolate mutable workflow instance fields.
15. Shared workflow definitions are immutable or explicitly synchronized/fenced.
16. Memory/session filters are constructed per call and do not mutate shared reusable configuration.
17. Memory namespace/session ID is not authenticated principal identity.
18. Canonical state and model-visible state projection carry separate identities/versions.
19. Workflow Context, Memory and retrieval/index state are separate persistence planes.
20. Pickle-based Context restoration is trusted executable deserialization.
21. Code-action support and sandboxing are separate capabilities.
22. Code executor implementation/profile is first-class security and benchmark identity.
23. Generated code/tool/retrieved outputs remain untrusted model content.
24. Primary source evidence and derived nodes/embeddings/index/citations remain separate state planes.
25. Ingestion/update/delete completion requires derived-state reconciliation where consistency matters.
26. Embedding model/dimension and parser/chunker generation are durable retrieval schema.
27. Missing authoritative protocol/tool IDs fail explicitly rather than being fabricated.
28. Streaming/model/provider output and memory/UI/protocol projections are cross-tested for loss or mutation.
29. Requested context and effective context are separately measured.
30. Provider/LLM integration identity is part of model profile.
31. Retrieval top-k/filter/reranker/memory-budget policy is benchmark identity.
32. Runtime telemetry is evidence, not effect settlement or verifier authority.
33. Model-as-judge evaluation is separately versioned/stochastic evidence.
34. Persistent memory does not gain instruction/policy authority through storage.
35. High-risk memory requires provenance/trust/verification/supersession outside generic retrieval.
36. ACL-owned checkpoint authority revalidates workspace/process/effect/credential/policy/verifier state after restoring framework Context.

## 23. Regression fixtures worth preserving

1. **#22559 pre-wait effect replay** — one logical external effect around HITL must not multiply.
2. **#22559 stable waiter identity** — replay cannot regenerate an incompatible correlation key.
3. **#22071 MCP shared workflow instance** — concurrent tenant calls must not see each other's `self.*` state.
4. **#22701 VectorMemory session pinning** — alternating A/B session retrieval must use the call's current scope.
5. **#22701 caller-object mutation** — memory operations must not mutate caller filters/messages unexpectedly.
6. **#22248 state projection freshness** — model's next step observes the intended committed state revision.
7. **tool exception after fake effect commit** — caught error must become `unknown_after_effect`/reconciled rather than automatic replay.
8. **cancel timeout** — cancellation return while fake backing operation remains alive must not count as settled.
9. **CodeAct executor wedge** — outer ACL owner must terminate/settle process tree independently of agent loop.
10. **Context restore with stale credentials/policy** — restored runtime state must not restore old authority.
11. **pickle Context provenance** — untrusted serialized executable state is refused.
12. **#22133 ingestion completeness** — all expected nodes survive document upsert.
13. **chat multiblock persistence** — canonical blocks survive memory save/load.
14. **stream-to-memory projection** — final streamed text survives persistence exactly as expected.
15. **missing tool-call ID** — fail explicitly rather than fabricate identity.
16. **AG-UI initial-state isolation** — independent runs cannot alias shared mutable initial state.
17. **local effective-context fixture** — requested 32K is checked against realized/effective runtime capacity.
18. **provider tool/schema composition** — exact integration + local runtime profile is tested end-to-end rather than inferred from capability labels.

## 24. Reuse candidates for later design comparison

Task 29 does not authorize reuse, but several mechanisms merit later comparison:

- typed event/step Workflow model;
- separately versioned workflow runtime beneath a high-level framework;
- serializable Context as one continuation evidence plane;
- explicit Context state editing API;
- distinct Context and Memory abstractions;
- agent classes that make action style explicit;
- multi-agent handoff graph as orchestration metadata;
- dynamic tool retrieval;
- broad integration-package boundary;
- OpenTelemetry instrumentation;
- fail-loud protocol identity handling rather than fabricated IDs;
- explicit user-supplied CodeAct executor boundary, provided ACL supplies the actual containment contract.

## 25. Explicit non-conclusions

Task 29 does **not** conclude:
- that ACL should adopt, fork or embed LlamaIndex;
- that LlamaIndex is better or worse than previously researched harnesses;
- that Workflows/LlamaAgents should become ACL's scheduler/runtime;
- that LlamaIndex Memory should become Vera's memory system;
- that LlamaIndex's 300+ integrations are equally safe or reliable;
- that a supported local provider/model is qualified for ACL's 32K baseline;
- that Context serialization is an exactly-once checkpoint;
- that MCP compatibility supplies authorization;
- that `CodeActAgent` supplies a sandbox;
- that current hosted LlamaParse/LlamaAgents product behavior is equivalent to OSS;
- that Task 30 CrewAI research has begun.

## Sources

Primary sources accessed 2026-09-07:

- LlamaIndex repository: https://github.com/run-llama/llama_index
- v0.14.24 release: https://github.com/run-llama/llama_index/releases/tag/v0.14.24
- Current main commit observed: https://github.com/run-llama/llama_index/commit/d2ac544a27c73d2a68e9c57efec4b2ac0ef99892
- Core package identity: https://github.com/run-llama/llama_index/blob/main/llama-index-core/pyproject.toml
- AgentWorkflow source: https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/agent/workflow/multi_agent_workflow.py
- CodeActAgent source: https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/agent/workflow/codeact_agent.py
- Agent state/Context docs: https://github.com/run-llama/llama_index/blob/main/docs/src/content/docs/framework/understanding/agent/state.md
- Workflow re-export boundary: https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/workflow/workflow.py
- Workflows/LlamaAgents repository: https://github.com/run-llama/llama-agents
- Workflow handler/cancellation source: https://github.com/run-llama/llama-agents/blob/main/packages/llama-index-workflows/src/workflows/handler.py
- Open issue #22559, replay and waiter identity: https://github.com/run-llama/llama_index/issues/22559
- Open issue #22071, shared MCP Workflow instance: https://github.com/run-llama/llama_index/issues/22071
- Open issue #22701, VectorMemoryBlock session-filter mutation: https://github.com/run-llama/llama_index/issues/22701
- Open issue #22248, stale model-visible state projection: https://github.com/run-llama/llama_index/issues/22248
- Open feature/design issue #20386, deterministic tool I/O mediation: https://github.com/run-llama/llama_index/issues/20386
- Open feature/security issue #21666, memory poisoning defense: https://github.com/run-llama/llama_index/issues/21666
- Official Ollama integration source: https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/llms/llama-index-llms-ollama
- Observability documentation: https://github.com/run-llama/llama_index/blob/main/docs/src/content/docs/framework/module_guides/observability/index.md

## Stop point

LlamaIndex Task 29 research is complete at the evidence/report stage represented by this file. No CrewAI research, cross-project winner selection, model execution, 32K benchmark, adoption decision or ACL/Vera implementation/governance change is authorized by this report.