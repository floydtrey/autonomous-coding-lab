# llama.cpp deep research

**Task:** 13 — ranked project #9
**Repository:** `ggml-org/llama.cpp`
**Research date:** 2026-09-06
**Inspected upstream revision:** `9e0e220594af405a62835dc3a27495729fd8506b`
**Scope:** local inference/runtime architecture, chat templates and tool parsing, constrained output, context/KV/cache semantics, server lifecycle/concurrency/cancellation, backend portability, reproducibility, current failure surfaces, and ACL/Vera implications.
**Decision status:** research complete for this task; no dependency/adoption/fork decision.

## Scope and evidence discipline

This task treats llama.cpp primarily as an **inference/runtime substrate**, not as an agent framework. The goal is to determine what ACL can rely on from a local runtime, what must be capability-tested per deployment, and which runtime states must stay separate from ACL's authoritative project/task/effect state.

Evidence priority remained upstream source, upstream documentation, open/closed issues, commits, and release metadata. Issue reports are kept version/configuration scoped unless current source or maintainer resolution supports a broader claim. No OpenAI Agents SDK research was begun.

## Executive finding

llama.cpp is a strong local-runtime reference for ACL because it exposes the layers that are often hidden behind a nominally "OpenAI-compatible" endpoint:

1. model/GGUF and quantization;
2. tokenizer and embedded/overridden chat template;
3. template capability analysis;
4. model-family/specialized parser or automatic parser;
5. tool schema conversion and constrained-decoding backend;
6. context/KV/cache/checkpoint policy;
7. sampling/speculative-decoding settings;
8. server slot/concurrency/streaming behavior;
9. compiled backend, hardware and driver realization.

The strongest conclusion is therefore not "llama.cpp supports tools" or "llama.cpp supports JSON Schema." The useful unit for ACL is a **verified deployment capability profile** for the exact runtime tuple.

Two current failure surfaces make that distinction concrete. Open issue #28429 reports a grammar rule-name collision where non-ASCII tool argument names can be silently collapsed, making the constrained sampler force the wrong argument even though the model can produce the correct call through another runtime. Open issue #25923 reports valid/edge JSON Schemas that compile to invalid/rejected grammar and can break an entire multi-tool request because tool schemas are combined into one grammar. Both failures occur below the model-reasoning layer.

This makes llama.cpp valuable both as a candidate local inference backend and as evidence that the **template/parser/constraint compiler itself is trusted execution infrastructure**.

---

## 1. Project health and maintenance signal

### Observed

- Canonical repository: `https://github.com/ggml-org/llama.cpp`
- License: MIT.
- Repository was not archived when checked.
- `master` examined at `9e0e220594af405a62835dc3a27495729fd8506b` on 2026-09-06.
- That revision was same-day active work (`grammar : fix max repetition threshold (#28469)`).
- Releases/prebuilt artifacts remain frequent; `b10819` was visible from 2026-09-05 during this task.

### ACL relevance

Current maintenance health is strong, but the same pace means behavior and integration details are moving. ACL should pin exact runtime revisions/releases for benchmark and production profiles rather than using an unqualified "latest" runtime identity.

---

## 2. Runtime architecture and backend portability

Primary source:
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/README.md`

### Observed

llama.cpp targets broad local execution and supports multiple hardware/backend paths, including CPU implementations, CUDA, HIP, Metal, Vulkan, SYCL and other accelerator paths, plus hybrid CPU+GPU and multi-device configurations. It also exposes an OpenAI-compatible HTTP server.

The project supports quantized GGUF models and multiple quantization levels. Backend and offload choices materially alter the realized inference path even when the logical model name is unchanged.

### ACL lesson

**Hardware portability is not behavioral portability.**

For ACL, the useful model identity should include at least:

- llama.cpp commit/release;
- binary/build/compiler/build flags;
- OS/platform;
- backend (CPU/CUDA/HIP/Metal/Vulkan/SYCL/etc.);
- hardware/device and driver/runtime version;
- GGUF digest and model metadata;
- quantization;
- tokenizer;
- chat template and any override;
- parser/handler/autoparser path;
- grammar backend;
- context and KV configuration;
- sampling/speculation configuration;
- server concurrency/cache flags.

A model benchmark result that omits these can hide a runtime-specific capability or failure.

---

## 3. Chat templates, tool contracts and parsing

Primary sources:
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/docs/function-calling.md`
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/common/chat.h`
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/docs/autoparser.md`
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/common/jinja/caps.cpp`

### 3.1 Tool-call representation is explicit

`common/chat.h` defines structured representations for messages and tool calls rather than treating every conversation as undifferentiated text. The chat pipeline can carry tool name, argument JSON, tool-call IDs, reasoning/content, tool-choice configuration, parallel-tool flags, grammar/JSON-schema input and parser state.

The generated chat parameters can include prompt text, grammar, lazy grammar triggers, preserved tokens, parser configuration and reasoning/content delimiters.

### 3.2 Template capability analysis

Current Jinja capability analysis actively probes a chat template for properties including:

- string versus typed content handling;
- tools;
- tool calls;
- parallel tool calls;
- system-role behavior;
- reasoning preservation/effort behavior;
- object-form arguments.

This is more robust than assuming a template supports tools because metadata says so.

However, it remains **template analysis**, not end-to-end model verification. A template may format and parse the protocol while the model still fails a real tool-use fixture.

### Candidate ACL distinction

Maintain separate states:

- `DiscoveredTemplateCapability`
- `VerifiedDeploymentCapability`

Only the latter should authorize a worker profile for production tool use.

### 3.3 Automatic parser

`docs/autoparser.md` describes a system that differentially renders templates and infers message/tool markers, function-name markers, argument serialization, call-ID placement and related protocol structure. It can generate parser and grammar behavior dynamically rather than hardcoding every model family.

This is high-leverage compatibility machinery, but it creates another versioned dependency in the capability tuple. Auto-inference can be wrong even if the model and endpoint are otherwise healthy.

### ACL lesson

Tool-call reliability is a property of:

`model + tokenizer + template + parser/handler + constraint backend + server/build configuration`

—not just the model name or the HTTP API shape.

---

## 4. Constrained structured output: built-in GBNF path

Primary source:
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/grammars/README.md`

### Observed

llama.cpp supports GBNF grammar-constrained generation and can convert a subset of JSON Schema into grammar.

The upstream grammar documentation explicitly lists limitations and semantics that matter for ACL:

- the built-in converter does not implement all JSON Schema features;
- unsupported features can be silently skipped in some paths;
- users are advised to inspect converter warnings/generated grammar and validate behavior;
- `additionalProperties` defaults false in the built-in converter, unlike normal JSON Schema semantics;
- several composition/reference/pattern/tuple/advanced-keyword cases are unsupported or limited;
- numeric bound support is constrained;
- nested/remote reference behavior is limited;
- complex grammar can affect sampling performance.

For `response_format`, the schema constrains output but is not necessarily model-visible as descriptive task context; a model may therefore satisfy structure without understanding intended semantics unless the prompt communicates them. Tool schemas, in contrast, participate in the tool prompt path.

### Critical ACL conclusion

**Syntactically valid constrained output does not prove faithful schema enforcement.**

A constraint compiler can:

1. reject a valid schema;
2. silently weaken it;
3. change its semantics;
4. generate a grammar that makes the correct answer impossible.

For authority-bearing tool calls, ACL should preflight the exact schema set and fail closed on unsupported/ambiguous conversion rather than discovering the mismatch during a worker run.

---

## 5. LLGuidance alternative constraint backend

Primary source:
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/docs/llguidance.md`

### Observed

llama.cpp can optionally be built with LLGuidance support. The upstream documentation describes materially different structured-output behavior from the built-in converter:

- broader JSON Schema support;
- `additionalProperties` defaults true, matching the normal JSON Schema default;
- unsupported schema is reported as an error rather than simply being skipped in the same way;
- the backend adds a Rust/cargo build dependency;
- current error handling can report failures to stderr while generation behavior continues, which upstream documentation itself identifies as an area that could be improved.

### ACL lesson

"JSON Schema support" must include the **constraint backend** as a first-class capability field.

For high-authority structured actions, ACL should prefer behavior that fails explicitly when a schema cannot be represented. If a chosen backend can log a compilation error and continue generation, ACL needs an outer preflight/gate so that compile failure cannot degrade silently into unconstrained execution.

---

## 6. Open constraint failure #28429: constrained decoding can force wrong tool arguments

Primary source:
- `https://github.com/ggml-org/llama.cpp/issues/28429`

### Observed

The open report demonstrates a collision in grammar rule-name sanitization for distinct non-ASCII tool parameter names. Two schema properties can map to the same generated grammar rule; one parameter is then lost/overwritten in the grammar representation.

The important consequence is stronger than "the parser rejects a response." Under constrained sampling, the correct field can become **unrepresentable**, causing generation to emit the wrong/duplicated field despite evidence that the model can issue the correct call through another runtime/control configuration.

Controls in the report distinguish the model capability from the grammar/compiler path.

### ACL relevance

This is direct evidence that a deterministic constraint layer can corrupt a capable model's action.

### Candidate invariant

For every authority-bearing tool schema:

- schema names and fields must remain unique after all normalization/sanitization;
- conversion must prove all required fields survived;
- unsupported/colliding fields fail registration;
- Unicode, normalization, case and rule-name collision fixtures belong in regression tests;
- post-generation validation cannot be the only defense if the grammar itself made the intended call impossible.

Constraint compilation belongs inside ACL's trusted computing base when ACL relies on constrained tool calls.

---

## 7. Open constraint failure #25923: one bad schema can poison a whole tool set

Primary source:
- `https://github.com/ggml-org/llama.cpp/issues/25923`

### Observed

The open report covers valid/edge schemas whose conversion can produce invalid/rejected grammar, including an empty-object schema case and a large `maxLength` case. The practical failure is amplified because multiple tools are compiled into a combined tool-call grammar: one unsupported/broken schema can prevent the entire request/tool set from initializing correctly.

Current upstream work includes grammar repetition changes, but this task did **not** classify #25923 as fully fixed; the issue remained open and covers more than one cause.

### ACL candidate invariant

Treat the worker's `ToolCapabilitySet` as an **atomic preflight artifact**:

- compile every schema before the worker starts;
- verify all required semantics survived conversion;
- reject the profile if any tool cannot be represented faithfully;
- store the schema-set digest plus compiler/backend/runtime version in the worker capability profile.

This should happen during model/runtime qualification, not halfway through a long-running coding task.

---

## 8. Server architecture, slots and concurrency

Primary sources:
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/tools/server/README-dev.md`
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/tools/server/server-task.h`
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/tools/server/README.md`

### Observed architecture

The server has explicit request/task/slot structure rather than one global text-generation loop.

Current server concepts include:

- `server_context` owning the inference context and slots;
- `server_slot` representing an active request/sequence;
- typed server tasks for completion, embeddings, reranking, infill, cancellation, control, response continuation, metrics, slot save/restore/erase and related operations;
- task/response queues;
- per-slot chat parser/tool-call streaming state;
- continuous batching where compatible slots can share batches;
- prompt caching/context checkpoint behavior;
- router mode/model routing surfaces;
- resumable stream management.

The server intentionally differentiates HTTP/API handling from inference-context ownership.

### ACL lesson

This is a useful boundary for local workers: inference concurrency and batching can remain inside the runtime while ACL maintains the authoritative worker/project/task scheduler above it.

ACL should not turn llama.cpp slot IDs into task/run/effect IDs. They are runtime transport/execution identities with a different lifecycle.

---

## 9. Server scope explicitly excludes a server-side agentic loop

Primary source:
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/tools/server/README-dev.md`

### Observed

The development documentation explicitly scopes the server around inference, chat/tool calling, API compatibility, model/context management and related runtime concerns while keeping complex repeated external API/agent-loop logic outside the server.

It also notes that features reading/writing external files should be disabled by default where applicable.

### ACL relevance

This independently reinforces the Task 12 SWE-ReX/mini-swe-agent finding:

**keep model/inference runtime model-agnostic and keep agent orchestration/effect authority outside it.**

For ACL, llama.cpp should not own:

- project backlog state;
- planner authority;
- dependency gates;
- tool authorization;
- worker filesystem/network credentials;
- effect idempotency/settlement;
- verifier pass/fail;
- durable run recovery.

Those remain ACL responsibilities even if llama.cpp provides the local model endpoint.

---

## 10. Cancellation and timeout ownership

Primary source:
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/tools/server/server-task.h`

### Observed

Current server task types include cancellation/control paths, and generation-time limiting is represented in task parameters.

A notable current source marker is that prompt-time maximum duration remains a `TODO` while generation-time maximum duration exists. This is not evidence that every prompt can hang indefinitely; it is evidence that different blocking phases do not share one uniform deadline implementation.

### ACL lesson

One `worker_timeout` is too coarse. ACL should preserve separate timeout/cancellation owners for at least:

1. connect/request establishment;
2. prompt rendering/tokenization;
3. prompt evaluation/prefill;
4. model generation/stream idle;
5. tool/process execution;
6. remote runtime/network effect;
7. whole task/run budget.

Inference cancellation also does not undo filesystem/network/API effects already performed by an ACL worker. Server cancellation and ACL effect settlement remain separate contracts.

---

## 11. Resumable streaming is transport continuity, not durable task state

Primary source:
- `https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/tools/server/README-dev.md`

### Observed

The server supports resumable-stream behavior where a client can detach and reattach while generation continues server-side. The design uses a bounded ring buffer/session lifecycle, one live session per identifier and cancellation/TTL/garbage-collection behavior.

### Vera/ACL relevance

This is a useful transport pattern for future mobile/remote Vera clients: **client disconnect need not imply model-run death**.

But the runtime conversation/stream identifier is not:

- a project/task ID;
- an approval ID;
- an effect ID;
- an audit log;
- a durable checkpoint.

The bounded stream buffer can drop old bytes and should not be treated as authoritative evidence. ACL's event/effect log must remain above it.

---

## 12. Prompt cache, KV cache and context checkpoints

Primary sources:
- server/common configuration at the inspected revision;
- `tools/server/README-dev.md`.

### Observed

llama.cpp exposes prompt/KV reuse and context-checkpoint mechanisms. Current server/common defaults include prompt caching and context checkpoint controls, and the server can track message spans/shared prefixes for reuse. KV behavior is additionally affected by context size, K/V data types, offload, slot layout and backend realization.

### Critical ACL distinction

A llama.cpp **context/KV checkpoint is not an ACL checkpoint**.

It preserves/reuses inference state. It does not establish:

- authoritative message semantics;
- project/task state;
- workspace contents;
- Git state;
- tool authorization;
- credential validity;
- process settlement;
- external-effect settlement;
- verifier evidence;
- permission to resume a worker.

### Candidate vocabulary

Avoid overloading `checkpoint` across layers:

- `InferenceContextSnapshot` / `KVCheckpoint`
- `ConversationEvidenceCheckpoint`
- `WorkspaceCheckpoint`
- `EffectSettlementCheckpoint`
- `ACLContinuationCheckpoint`

Only the last category should authorize automatic task continuation after the required evidence planes agree.

---

## 13. Long-horizon failure surface #23577

Primary source:
- `https://github.com/ggml-org/llama.cpp/issues/23577`

### Observed

The open report describes a long-running Qwen3.6/MTP session that works for hours before entering pathological repeated-token output. The reported configuration includes Windows/CUDA and quantized/speculative context behavior.

The issue is useful as a long-horizon failure signal, but the root cause remained unresolved in this task. It would be incorrect to attribute the failure specifically to prompt cache, context checkpoints, quantization or MTP without further evidence.

### ACL lesson

Local-runtime qualification cannot be only one-shot coding prompts.

Future ACL endurance fixtures should test:

- many turns/hours;
- high context occupancy;
- context shifts;
- cache reuse/restore;
- repeated tool-call cycles;
- pathological token-loop detection;
- restart/reconnect behavior;
- memory/VRAM/resource stability.

The outer harness should detect obvious output pathology independently of whether the runtime itself considers generation successful.

---

## 14. Speculative decoding failure surface #25618

Primary source:
- `https://github.com/ggml-org/llama.cpp/issues/25618`

### Observed

The open `bug-unconfirmed` report shows a configuration where greedy output from a quantized target differs when model-based speculative decoding is enabled, while comparison controls differ by target precision/speculation path. The report includes multiple model/backend observations and does not establish that all speculative decoding is lossy.

### ACL relevance

Performance optimization is part of behavior.

A reproducibility record that says only:

`model=X, temperature=0, seed=Y`

is incomplete if one run used:

- a draft model;
- MTP/draft speculation;
- n-gram speculation;
- different quantization;
- different backend;
- different KV/cache settings.

### Candidate rule

Enable throughput optimizations in a production worker profile only after the exact profile passes ACL semantic/tool-call equivalence fixtures. If an optimization changes behavior, it becomes a distinct profile rather than an invisible tuning flag.

---

## 15. Reproducibility manifest for ACL local workers

Task 13 supports a stronger local-model manifest than the earlier generic `model + runtime + adapter` shorthand.

For a reproducible llama.cpp worker benchmark, record:

### Runtime build
- llama.cpp commit/release;
- binary/package source;
- compiler and important build flags;
- enabled constraint backends (built-in GBNF, LLGuidance);
- server/API mode/version.

### Hardware realization
- OS;
- CPU/GPU/device(s);
- backend;
- driver/runtime versions;
- thread/offload/device-split settings.

### Model artifact
- exact GGUF filename/digest;
- architecture/model metadata;
- quantization;
- tokenizer metadata;
- relevant model adapter/draft artifacts.

### Chat/tool protocol
- embedded chat template digest;
- template override, if any;
- detected template capability result;
- specialized handler vs autoparser path;
- parser/runtime revision;
- tool schema set/digest;
- grammar backend;
- tool-choice/parallel-tool configuration.

### Context and cache
- `n_ctx` and rope/context-extension settings;
- KV K/V types and offload;
- unified/per-slot behavior where applicable;
- flash attention;
- prompt-cache/context-checkpoint settings;
- batch/ubatch and slot/concurrency settings.

### Generation
- sampler parameters;
- seed;
- reasoning/tool options;
- speculative mode and draft model;
- generation/request/idle deadlines.

### ACL evidence
- benchmark fixture version/commit;
- ACL worker/harness version;
- workspace/reset identity;
- verifier version;
- repeat count/concurrency;
- observed tool-call/schema/stream capability results.

This is likely the minimum needed to distinguish a model regression from a runtime/template/backend/configuration regression.

---

## 16. Security and authority boundaries

llama.cpp can parse and constrain tool-call output, but it does not thereby authorize the tool's real-world effect.

ACL should preserve the sequence:

`model proposes → runtime parses/constrains → ACL validates → ACL authorizes → ACL executes in bounded environment → ACL records effect → verifier evaluates`

The grammar/parser sits before authorization. It must not be allowed to widen the tool schema or silently alter required fields.

The server's narrow internal tool/execution capabilities observed in development documentation are not a stable substitute for ACL's worker tool authority; they are explicitly internal/subject to change and were not treated as an adoption target in Task 13.

---

## 17. Highest-value candidate invariants

Task 13 adds the following candidates for later cross-project comparison:

1. **Deployment capability is realized behavior, not endpoint identity.**
2. **Template capability discovery and model/runtime capability verification are separate states.**
3. **Template/parser/constraint compiler are part of the trusted tool-call path.**
4. **Unsupported schema semantics must fail closed for authority-bearing tools.**
5. **Tool-schema registration is atomic: the complete worker tool set preflights before execution begins.**
6. **Schema conversion must prove required fields survive normalization/sanitization.**
7. **Constraint backend/version belongs in the capability profile.**
8. **Valid JSON is not evidence that the schema was compiled faithfully.**
9. **Runtime slot/session/stream identity is separate from ACL task/run/effect identity.**
10. **Inference cancellation is separate from worker/effect settlement.**
11. **Each blocking inference phase needs its own timeout owner.**
12. **KV/prompt checkpoints are inference optimization state, not continuation authority.**
13. **Performance optimizations are behavior-bearing configuration until equivalence is verified.**
14. **Local-worker reproducibility requires binary/build/backend/driver/model/template/parser/grammar/context/KV/sampling identity.**
15. **The inference runtime should remain model-agnostic; project orchestration/effect authority remains outside it.**
16. **Long-horizon qualification must include endurance and pathological-output tests, not only one-shot benchmark accuracy.**
17. **Bounded/resumable transport buffers are not durable evidence logs.**

---

## 18. Candidate ACL regression fixtures derived from llama.cpp

These are future test candidates only; Task 13 did not implement them.

1. Two Unicode schema property names that collide under rule sanitization must cause preflight failure, never silent field loss.
2. Empty-object and large-bound schemas must either compile faithfully or reject the whole worker profile before runtime.
3. One invalid tool schema must not leave a partially registered tool capability set.
4. Built-in GBNF and LLGuidance profiles must advertise different verified schema capabilities rather than sharing one `structured_output=true` bit.
5. A model/template that passes template capability detection must still pass a real tool-use probe before production enablement.
6. Parallel-tool support must be verified with actual multi-call output and parser correlation.
7. Same model/seed/temp with speculative decoding enabled/disabled must pass semantic/tool-call equivalence before profiles are considered interchangeable.
8. Cache/context checkpoint save/restore must preserve inference equivalence but must never be accepted as an ACL continuation checkpoint.
9. Client stream disconnect/reconnect must not duplicate or lose ACL-owned run/effect identities.
10. Cancellation during prompt evaluation, generation and stream idle must produce phase-specific state and must not be confused with worker-process cancellation.
11. Multi-hour/many-turn run should detect repeated-token/output collapse and surface runtime/profile failure rather than model task success.
12. The same GGUF/profile across two hardware backends should run a small deterministic capability suite before ACL treats the deployments as equivalent.
13. Capability-profile evidence should invalidate automatically when runtime commit, GGUF digest, template, constraint backend or relevant server flags change.

---

## 19. Possible reuse versus non-conclusions

### Strong reuse/comparison candidates

- llama.cpp as a local inference/server backend;
- exact model/runtime capability profiling;
- chat-template capability probing;
- specialized + automatic tool parser patterns;
- GBNF constrained generation where schema compatibility is proven;
- LLGuidance as an alternate fail-more-explicit constraint path;
- continuous-batching/slot runtime separation;
- resumable generation transport patterns;
- local backend portability;
- context/KV caching as an inference optimization only.

### Do not infer from Task 13

- llama.cpp should be ACL's final local runtime;
- built-in GBNF is safer/better than every alternative;
- LLGuidance should automatically be adopted;
- all llama.cpp backends behave identically;
- all reported open issues affect current master in every configuration;
- template capability detection proves a model is good at tools;
- a grammar-valid tool call is authorized or semantically correct;
- a KV/context checkpoint is a durable worker checkpoint;
- llama.cpp should own the ACL/Vera agent loop;
- OpenAI Agents SDK is inferior/superior; it was not researched in this task.

---

## 20. Project assessment for later comparison

llama.cpp remains a high-value Tier-A research reference and likely local-runtime candidate because it exposes exactly the layer ACL must understand rather than abstract away: local model artifact + build/backend + template/parser + constrained output + context/cache + server behavior.

Its most important contribution to ACL is the proof that **local model capability is realized at the full deployment stack**, not at the model-name or OpenAI-compatible API layer. The current grammar/schema failures show that deterministic infrastructure can be the cause of a wrong tool call even when the model itself is capable.

That makes llama.cpp strongest as:

- an inference/runtime substrate;
- a local capability-profiling target;
- a constrained-output/parser research reference;
- a reproducibility and endurance-test target.

It does **not** replace ACL's outer scheduler, dependency blocking, workspace/process sandbox, credential governance, effect ledger, crash recovery, protected verifier or Vera memory/governance.

Task 13 supports later component comparison. It makes no dependency, fork, architecture-winner or deployment decision.

---

## Primary source index

- Repository: https://github.com/ggml-org/llama.cpp
- Inspected revision: https://github.com/ggml-org/llama.cpp/commit/9e0e220594af405a62835dc3a27495729fd8506b
- README/runtime backends: https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/README.md
- Function calling: https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/docs/function-calling.md
- Chat structures: https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/common/chat.h
- Auto parser: https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/docs/autoparser.md
- Jinja capability analysis: https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/common/jinja/caps.cpp
- GBNF / JSON Schema: https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/grammars/README.md
- LLGuidance: https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/docs/llguidance.md
- Server development architecture/scope: https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/tools/server/README-dev.md
- Server task structure: https://github.com/ggml-org/llama.cpp/blob/9e0e220594af405a62835dc3a27495729fd8506b/tools/server/server-task.h
- Constraint collision #28429: https://github.com/ggml-org/llama.cpp/issues/28429
- Tool-schema grammar failure #25923: https://github.com/ggml-org/llama.cpp/issues/25923
- Long-horizon repeated-output #23577: https://github.com/ggml-org/llama.cpp/issues/23577
- Speculative decoding divergence #25618: https://github.com/ggml-org/llama.cpp/issues/25618

## Stop boundary

Research stops here. No OpenAI Agents SDK deep research, MCP research, dependency/fork decision, ACL/Vera runtime implementation, governance change or worker/model execution was begun in Task 13.
