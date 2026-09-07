# Ollama — Task 17 Deep Research

**Research date:** 2026-09-06  
**Research target:** current Ollama local inference/runtime/API architecture and directly relevant official project material  
**Canonical repository:** `ollama/ollama`  
**Revision inspected:** `83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8` (2026-09-05)  
**Latest release observed:** `v0.33.3` (published 2026-09-02; release assets refreshed 2026-09-03)  
**License:** MIT  
**Decision status:** research only; no adoption/dependency/runtime winner decision

## Scope

Task 17 studies Ollama as a local-model runtime and deployment boundary for ACL/Vera. The research focuses on:

- exact Ollama runtime/API identity;
- the pinned and patched llama.cpp relationship;
- the separate MLX execution path;
- model manifests, layers, Modelfiles, templates and artifact identity;
- context-length precedence, prompt truncation/context shifting and realized context;
- KV-cache, flash-attention, batch/parallel and memory-fit behavior;
- scheduler concurrency, model loading, eviction, keep-alive and OOM handling;
- GPU/backend discovery and resource observability;
- tool/function calling, template/parser capability discovery and tool-schema fidelity;
- structured output and tool + structured-output composition;
- native API, OpenAI compatibility and local-versus-cloud behavior;
- service/process lifecycle and cancellation;
- network, authentication and offline/cloud boundaries;
- telemetry, request reproduction and benchmark evidence;
- Ollama's own integration/stress-test patterns;
- current failure surfaces that should become ACL regression fixtures.

Task 17 does **not** deep-research Letta Code, choose a cross-project winner, start the ACL benchmark lab, alter ACL/Vera governance, or run candidate worker models.

---

## Executive assessment

Ollama is valuable to ACL primarily as a **deployment runtime and packaging/scheduling layer above local inference engines**, not as an authority, agent-state or verifier layer.

The most important Task 17 conclusion is that the meaningful unit of qualification is not simply:

> `model = qwen...` and `runtime = Ollama`

It is much closer to:

> **Ollama build/revision + execution engine + pinned engine revision/patches + immutable model artifact + template/parser + API route + context/KV/batch/parallel/memory-fit settings + hardware/backend/driver + realized offload/context + harness/client parser + tested capability combination**.

That conclusion is supported directly by current Ollama architecture and current failure evidence:

1. Ollama does not embed a generic timeless llama.cpp. Current builds pin a specific llama.cpp revision and apply Ollama compatibility patches before building it.
2. Ollama also has a distinct MLX runner with different implemented capabilities, so `engine=llama.cpp` versus `engine=MLX` is behavior-bearing.
3. Current context defaults vary by detected VRAM and can be only 4K below 24 GiB even though Ollama's own agent/coding guidance recommends at least 64K.
4. Memory estimation and realized GPU/CPU split can change sharply between Ollama releases and can produce large throughput cliffs without a model change.
5. Ollama's model capability labels are assembled from metadata/template/parser heuristics. They nominate a capability for testing; they do not prove end-to-end behavior.
6. Ollama's current tool-schema structs preserve only a subset of JSON Schema. Some constraints are silently dropped before reaching the model, and surviving constraints such as `enum` are not necessarily enforced during tool-call decoding.
7. Structured-output constraints and tool-call schemas take different paths. A model/runtime can support each independently yet fail when the two are combined.
8. The scheduler contains useful bounded queue, load, keep-alive and OOM-retry mechanisms, but a current open concurrency report exposes an eviction/reuse race that can deadlock cold model loads.
9. Local APIs default to loopback, but normal inference/model-management routes do not install a general authentication middleware. Binding Ollama to a network interface changes the security boundary materially.
10. Ollama now includes cloud/remote inference behavior. `Ollama` therefore no longer automatically means local/offline execution; the realized remote/local mode must be recorded and policy-controlled.

For ACL, Ollama is therefore a strong **runtime-under-test and possible production inference service**, provided ACL retains ownership of:

- model/runtime capability qualification;
- authoritative tool schemas and post-generation argument validation;
- task/effect identity and authorization;
- worker OS/process sandboxing and credential projection;
- long-running project/checkpoint state;
- independent success/security verification;
- benchmark manifests and regression classification.

---

# 1. Current project identity and release boundary

## 1.1 Canonical repository

Observed at the Task 17 checkpoint:

- canonical upstream: `ollama/ollama`;
- public, active and not archived;
- inspected current-main revision: `83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8` dated 2026-09-05;
- latest release observed: `v0.33.3`;
- project license: MIT.

Primary sources:

- https://github.com/ollama/ollama
- https://github.com/ollama/ollama/tree/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8
- https://github.com/ollama/ollama/releases/tag/v0.33.3
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/LICENSE

## 1.2 Release assets are part of runtime identity

The v0.33.3 release publishes platform-specific artifacts including ordinary, ROCm and MLX distributions. GitHub release metadata includes SHA-256 digests for assets.

### ACL implication

A benchmark manifest should be able to record both:

- semantic version / Git revision; and
- exact installed package/archive digest.

That makes it possible to distinguish two machines both reporting `v0.33.3` but installed from different platform packages or locally rebuilt binaries.

---

# 2. Ollama is an orchestration/runtime layer above multiple inference engines

The common shorthand that "Ollama is a wrapper around llama.cpp" is materially incomplete for reproducibility.

Current Ollama owns or participates in:

- HTTP/API compatibility;
- model reference resolution and content-addressed storage;
- template/parser selection;
- context/default option precedence;
- GPU discovery and memory estimation;
- model load/unload scheduling;
- request queueing and per-model reuse;
- local/cloud routing;
- inference-runner subprocess lifecycle;
- local capability presentation;
- model packaging via Modelfile/manifests;
- client/harness compatibility surfaces.

The underlying engine remains important, but these Ollama layers can change realized behavior independently of model weights.

### Candidate ACL runtime identity

At minimum:

```text
ollama_release_or_commit
ollama_package_digest
engine_kind
engine_revision
engine_patch_profile
model_manifest_digest
model_layer_digests
model_artifact_digest
model_quantization
model_template_digest
model_parser_renderer
api_route
requested_context
realized_context
kv_cache_type
flash_attention
parallel_slots
batch_settings
memory_fit_settings
requested_gpu_policy
realized_gpu_cpu_split
backend
visible_device_identity
driver/runtime_stack
harness_adapter_version
verified_fixture_set
```

---

# 3. Pinned llama.cpp plus Ollama compatibility patches

## 3.1 The engine revision is explicit

Current `LLAMA_CPP_VERSION` pins Ollama's llama.cpp source to `b10760`.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/LLAMA_CPP_VERSION

## 3.2 Ollama modifies the pinned engine

Current `llama/README.md` explicitly documents the build relationship:

1. fetch the pinned llama.cpp source;
2. apply Ollama compatibility patches under `llama/compat/`;
3. build that patched source as part of Ollama.

The document also warns that upstream engine updates can affect model loading, GPU discovery, scheduler inputs, runtime logging, streaming and compatibility behavior, and that validation should include real platform integration rather than a successful compilation alone.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/llama/README.md

### ACL inference

Do not label an Ollama result with only a llama.cpp upstream tag or commit. Ollama's engine is a **pinned-and-patched derivative** for that build.

Two useful identities are distinct:

- direct llama.cpp deployment from Task 13;
- Ollama deployment containing its pinned/compat-patched llama.cpp.

They must pass the same ACL fixtures before results can be compared as equivalent runtime backends.

---

# 4. MLX is a distinct engine profile, not a transparent replacement

Current `MLX_VERSION` pins an MLX-side revision:

`37c26e5755da637255d57ea34b4879196a485301`

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/MLX_VERSION

Current `x/mlxrunner/client.go` shows an execution path that is not feature-identical to the llama-server path.

Observed current differences include:

- separate runner subprocess and HTTP client;
- loopback connection;
- completion support;
- structural-output handling using MLX-side structural tags;
- no native llama-server `Chat` implementation in this client;
- no native llama-server chat-template method;
- no embeddings implementation in this runner path;
- no `DeviceInfos` implementation here;
- current load/memory path using the first GPU for relevant check logic.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/x/mlxrunner/client.go

### ACL invariant

`engine=mlx` and `engine=llama.cpp` are different verified capability profiles even if they serve the same model label through the same Ollama API endpoint.

Do not silently carry tool/structured-output/embedding/performance qualification from one engine to another.

---

# 5. Runner subprocess and environment boundary

## 5.1 llama-server is a loopback child process

Current `llm/llama_server.go` launches llama-server with controls including:

- loopback host;
- no web UI;
- offline mode;
- context size based on per-slot context × parallel slots;
- parallel slot count;
- KV cache types;
- flash attention;
- batch/microbatch controls;
- optional GPU-layer and thread controls;
- memory-fit behavior.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/llm/llama_server.go

## 5.2 Runner environment inherits the service environment

Both inspected local runner launch paths begin from the parent process environment and add/override runtime/library settings.

This is a normal native-runtime design choice, but it matters to ACL's stronger credential boundary.

### ACL implication

Ollama itself should run as a deliberately provisioned service identity with a controlled environment. ACL should not assume a child llama-server/MLX process automatically receives a secret-minimized environment if the Ollama service process itself contains unrelated credentials.

This is distinct from model-selected worker-tool processes; those still need their own stronger least-privilege environment policy.

---

# 6. Model artifact identity: tags are aliases, manifests/layers are evidence

## 6.1 Content-addressed layers

Current manifest/layer code records:

- media type;
- size;
- SHA-256 digest.

`NewLayer` computes the SHA-256 digest from content and stores blobs under content-addressed names.

Pull/download logic verifies content digest and rejects mismatch.

Primary sources:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/manifest/layer.go
- https://github.com/ollama/ollama/tree/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/server

## 6.2 Modelfile is behavior-bearing model configuration

Current Modelfile supports directives including:

- `FROM`;
- `PARAMETER`;
- `TEMPLATE`;
- `SYSTEM`;
- `ADAPTER`;
- `LICENSE`;
- `MESSAGE`;
- `REQUIRES`.

`FROM` can refer to an Ollama model, a Safetensors directory for supported architectures, or a GGUF artifact.

`REQUIRES` can constrain minimum Ollama runtime version.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/modelfile.mdx

## 6.3 `ollama show` exposes useful deployment evidence

Current API/types/routes support showing model metadata including:

- Modelfile representation;
- template;
- system text;
- parameters;
- model details;
- capabilities;
- model metadata.

Generated Modelfiles can resolve a model to a content-addressed SHA-256 blob reference.

### ACL rule

A mutable tag such as `qwen...:latest` is not sufficient benchmark identity.

Record immutable content identity plus behavior-bearing Modelfile fields. If a tag later resolves to different content, it becomes a different benchmark deployment even if the human-readable label is unchanged.

---

# 7. Context length is multi-source state with explicit precedence

## 7.1 Current VRAM-tier defaults

Current Ollama behavior sets the server context default by total VRAM approximately as:

- less than 24 GiB: 4K;
- 24–48 GiB: 32K;
- at least 48 GiB: 256K.

The current server implementation uses thresholds around 23/47 GiB and context values 4096 / 32768 / 262144.

Primary sources:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/envconfig/config.go
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/context-length.mdx

## 7.2 Ollama's agent/coding guidance expects more than the small default

Current context-length documentation says agent/coding/web-search workloads should use at least 64K context.

That creates an important distinction:

- default chosen for available VRAM;
- context necessary for a particular agent workload.

The default should not be interpreted as an endorsed coding-agent benchmark context.

## 7.3 Current option precedence

Current source/tests establish the effective precedence for `num_ctx` approximately as:

1. request-level `num_ctx`;
2. model/Modelfile `num_ctx`;
3. `OLLAMA_CONTEXT_LENGTH`;
4. VRAM-derived service default;
5. bounded by model/train context where applicable.

### ACL implication

Every benchmark must set the intended context explicitly and record both:

- requested context;
- realized runner context.

A benchmark should fail qualification or at least be marked non-comparable if it silently falls back to 4K/another value.

---

# 8. Prompt truncation/context shifting must be observable benchmark state

Current llama-server integration contains explicit prompt-truncation/context-shift behavior and logs a warning such as `truncating input prompt` when input exceeds allowed context.

The implementation preserves configured `num_keep` and, for context shifting, frees a substantial portion of remaining context to make room for continued generation.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/llm/llama_server.go

### ACL risk

A harness can believe it sent a 30K or 60K history while the runtime silently dropped earlier tokens.

That can be misdiagnosed as:

- model forgetting;
- bad long-horizon reasoning;
- poor retrieval;
- tool-selection regression.

### Candidate benchmark evidence

Record:

- requested context;
- realized runner context;
- prompt token count;
- cached prompt count;
- whether truncation/context shift occurred;
- compaction event if the harness compacted before Ollama;
- final model-visible history digest/summary if practical.

This separates harness compaction from runtime truncation.

---

# 9. KV cache and optimization settings are behavior-bearing deployment state

Current environment configuration exposes controls including:

- `OLLAMA_FLASH_ATTENTION`;
- `OLLAMA_KV_CACHE_TYPE`;
- `OLLAMA_GPU_OVERHEAD`;
- `LLAMA_ARG_FIT`;
- `LLAMA_ARG_FIT_TARGET`;
- `OLLAMA_NUM_PARALLEL`;
- `OLLAMA_MAX_LOADED_MODELS`;
- `OLLAMA_MAX_QUEUE`;
- `OLLAMA_LOAD_TIMEOUT`;
- `OLLAMA_KEEP_ALIVE`;
- `OLLAMA_SCHED_SPREAD`.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/envconfig/config.go

Current project guidance describes KV-cache quantization tradeoffs:

- f16 as default;
- q8_0 around half the KV memory with small quality impact;
- q4_0 around quarter of f16 with greater possible quality impact, especially at larger contexts;
- quantized KV cache depends on flash attention.

### ACL inference

These are not merely tuning notes when comparing models. They affect:

- whether a model fits fully on GPU;
- maximum feasible context;
- prompt-cache memory;
- throughput;
- potentially output quality.

They belong in the benchmark deployment manifest.

---

# 10. Scheduler architecture and useful mechanisms

Current `server/sched.go` owns resource-mediated model acquisition and reuse.

Observed mechanisms include:

- bounded pending request queue;
- loaded-runner tracking;
- model reuse when equivalent runner/model options are already loaded;
- request/reference counting;
- keep-alive-based expiry;
- GPU/system memory refresh before load decisions;
- model memory estimation and fit prediction;
- eviction to make room for another model;
- one active new-model load path at a time;
- configurable maximum loaded models;
- configurable request parallelism;
- architecture/model-specific forced single-parallel behavior for models known unsafe under parallel requests;
- finite retry after runtime load OOM rather than unbounded retry.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/server/sched.go

## 10.1 Keep-alive semantics

Current behavior supports:

- service/default keep-alive around five minutes;
- request/model-specific keep-alive;
- zero to unload immediately after request;
- negative duration for effectively indefinite retention.

### ACL interpretation

Keep-alive controls **runtime cache residency**, not durable agent state. A model staying loaded is not a checkpoint, and a model unload says nothing about task/effect settlement.

---

# 11. Current scheduler deadlock report: #17408

Open issue #17408 is a high-value scheduler-concurrency fixture.

The reported scenario on 0.31.1 is:

1. scheduler chooses an existing loaded runner as an eviction target;
2. it marks eviction through session-duration state;
3. a concurrent request reuses/resurrects that runner and replaces the duration with a normal keep-alive;
4. the original scheduler path waits for an unload notification that never occurs;
5. cold model loads can then block indefinitely while already-loaded models can continue serving;
6. restarting Ollama recovers.

The reporter states the relevant logic remained on then-current main, and Task 17 inspection found the same structural risk pattern in current scheduler code.

A proposed explicit `expiring`-style fix exists in PR #17416 but remained unmerged during Task 17. A related PR #17515 was closed without merge.

Primary sources:

- https://github.com/ollama/ollama/issues/17408
- https://github.com/ollama/ollama/pull/17416
- https://github.com/ollama/ollama/pull/17515

## 11.1 ACL lessons

### Explicit transition state

Do not encode a lifecycle transition only as a magic value such as duration=0 if another path can legitimately overwrite that same field.

Represent resource state explicitly, for example:

```text
LOADED
EXPIRING
UNLOADING
UNLOADED
LOADING
FAILED
```

with legal transition ownership.

### No indefinite scheduler waits

A wait for resource settlement needs a hard deadline and an observable terminal error. "Waiting for another goroutine/process forever" is not safe runtime state.

### Health must test cold-load capability

A health endpoint that proves HTTP availability or inference from already-loaded models can miss a scheduler deadlock affecting new work.

ACL runtime health should distinguish at least:

- API alive;
- current loaded model usable;
- scheduler accepting work;
- cold model load/replacement path healthy;
- GPU memory telemetry available.

---

# 12. Memory-estimation regression: #17099

Open issue #17099 supplies strong version-sensitive performance evidence.

The report compares 0.31.1 and 0.31.2 using the same model/hardware/options and observes:

- larger estimated memory requirement;
- a previously full-GPU load becoming partial CPU offload;
- large generation throughput collapse;
- large prompt-evaluation slowdown.

A maintainer acknowledged the regression and suggested `LLAMA_ARG_FIT_TARGET=1024` as a temporary workaround until release correction. Another report in the thread showed similar behavior with a text model, not only a vision model.

Primary source:

- https://github.com/ollama/ollama/issues/17099

## 12.1 ACL lesson: realized offload is evidence

A benchmark cannot trust only:

- requested `num_gpu`;
- model size estimate;
- "GPU detected";
- previous release behavior.

It should record actual realized GPU/CPU split and reject a comparison if the deployment moved between full GPU and partial CPU without being intentionally classified as a different profile.

This is an example of a discontinuous performance cliff caused by runtime/memory-placement behavior rather than model reasoning quality.

---

# 13. Hardware backends and device identity

Current GPU documentation covers major execution paths including:

- NVIDIA CUDA;
- AMD ROCm/HIP;
- Apple Metal;
- Vulkan on supported Windows/Linux setups;
- Jetson-specific packaging/support cases.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/gpu.mdx

## 13.1 Visible-device controls

Current environment supports controls such as:

- `CUDA_VISIBLE_DEVICES`;
- `HIP_VISIBLE_DEVICES`;
- `ROCR_VISIBLE_DEVICES`;
- `GGML_VK_VISIBLE_DEVICES`;
- `GPU_DEVICE_ORDINAL`;
- relevant AMD override settings.

Where stable device UUIDs are available, upstream recommends them over unstable numeric ordering.

## 13.2 Memory observability affects scheduler quality

The runtime scheduler depends on discovery/free-memory information. Some Vulkan/Linux environments may not expose strong free-VRAM telemetry without additional privilege/capability, forcing best-effort estimates.

### ACL inference

Record not only:

`backend = vulkan`

but also:

- exact device identity;
- driver/runtime version;
- whether accurate free-memory telemetry is available;
- detected total/free VRAM;
- realized runner placement.

Scheduler reliability can differ even when the same model executes on the same nominal GPU family.

---

# 14. API surfaces: native, OpenAI-compatible and cloud are separate profiles

## 14.1 Native Ollama API

Current native routes cover inference and model management such as:

- chat;
- generate;
- embeddings;
- show;
- list/tags;
- process/running-model status;
- pull/push/create/copy/delete;
- version/status.

## 14.2 OpenAI compatibility is explicitly partial

Current Ollama documentation describes compatibility with **parts** of the OpenAI API rather than universal API equivalence.

Current surfaces include routes such as:

- `/v1/chat/completions`;
- `/v1/responses`;
- `/v1/responses/compact`;
- embeddings/models and related supported paths.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/api/openai-compatibility.mdx

### ACL invariant

`adapter=native_ollama` and `adapter=openai_compat_ollama` are not automatically the same capability profile.

An ACL benchmark that uses a framework through OpenAI-compatible routes must record that adapter path and run its own tool/structured-output/stream/error fixtures.

## 14.3 Cloud/remote inference changes the meaning of "Ollama"

Current Ollama supports remote/cloud behavior and exposes policy controls including:

- `OLLAMA_NO_CLOUD` to disable cloud features/remote inference/web search;
- `OLLAMA_REMOTES` to constrain allowed remote model hosts.

API response types can include remote-model and remote-host identity.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/envconfig/config.go

### ACL offline invariant

For an offline/local qualification profile:

1. explicitly disable cloud behavior;
2. apply external network policy where the worker/runtime requires a stronger guarantee;
3. verify response metadata shows local execution;
4. keep cloud and local results in separate benchmark profiles.

---

# 15. Capability discovery is heuristic metadata, not verification

Current model capability assembly in `server/images.go` considers sources such as:

- model config declarations;
- GGUF metadata;
- projector metadata;
- chat template content;
- parser/renderer availability;
- model-family-specific rules;
- unsupported-capability filtering.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/server/images.go

For tools, current detection can include simple template indicators such as the presence of `tools` or `tool_call`. Thinking/reasoning capability similarly depends partly on template/parser indicators.

### ACL distinction

Define at least two states:

```text
DiscoveredCapability
VerifiedDeploymentCapability
```

`ollama show` / capability metadata can nominate a deployment for a test. It cannot promote itself to verified tool reliability.

Promotion requires ACL-owned fixtures using the exact:

- model artifact;
- Ollama build;
- engine;
- template/parser;
- API route;
- context settings;
- tool schema set;
- client/harness.

---

# 16. Tool calling: Ollama's native schema is intentionally narrower than full JSON Schema

Current API structs are highly relevant to ACL authority.

`ToolProperty` currently preserves fields such as:

- `anyOf`;
- `type`;
- `items`;
- `description`;
- `enum`;
- nested `properties`;
- `required`.

`ToolFunctionParameters` currently carries:

- `type`;
- `$defs`;
- `items`;
- `required`;
- `properties`.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/api/types.go

That is not the same thing as accepting and preserving arbitrary JSON Schema semantics.

---

# 17. Open tool-schema loss: #17142

Open issue #17142 documents and explains a current schema-translation failure class.

It identifies commonly used JSON-Schema fields that are silently dropped at request-unmarshal time because current Go structs have no destination for them, including examples such as:

- numeric minimum/maximum and exclusive bounds;
- multipleOf;
- default;
- format;
- pattern;
- string length bounds;
- array length bounds;
- const.

The issue reproduces this on 0.31.1 and states that it reproduces against current main; Task 17's current-main struct inspection confirms the relevant fields remain absent.

Primary source:

- https://github.com/ollama/ollama/issues/17142

## 17.1 Why this matters to model benchmarks

A model can be incorrectly blamed for invalid tool arguments when the constraint never reached it.

For evaluation classification, distinguish:

1. ACL authoritative schema;
2. adapter-downconverted Ollama schema;
3. model-visible rendered schema;
4. generated tool arguments;
5. host validation result.

A loss at stage 2/3 is an adapter/runtime failure, not automatically a model failure.

---

# 18. Open tool-argument enforcement gap: #17597

Open issue #17597 isolates a different layer.

The reported `enum` constraint:

- survives Ollama parsing;
- is visible to the model;
- can be recited correctly by the model;
- is nevertheless not enforced during tool-call argument decoding;
- can be violated by the generated tool call.

The same enum constraint is enforced when used as a `response_format` structured-output schema in the reproduction.

Primary source:

- https://github.com/ollama/ollama/issues/17597

## 18.1 ACL security invariant

**Never treat Ollama's tool schema as execution validation.**

The host must validate generated arguments against the authoritative ACL schema before:

- policy evaluation;
- approval presentation;
- tool dispatch;
- effect recording as started.

The authorization system must operate on validated, normalized arguments, not model output assumed valid because a schema was supplied to Ollama.

This rule remains valuable even if upstream later adds constrained tool decoding, because host validation protects against:

- adapter bugs;
- parser bugs;
- future regressions;
- schema-subset mismatch;
- alternate model/engine paths.

---

# 19. Structured output is a different constraint path

Current structured-output documentation supports:

- `format: "json"`;
- JSON Schema as native `format`;
- OpenAI-compatible `response_format` on supported paths.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/capabilities/structured-outputs.mdx

Current llama-server integration passes local structured-output schema to the underlying runner's JSON-schema grammar path rather than relying on the model simply following descriptive tool-schema text.

The MLX runner uses its separate structural constraint representation.

Current documentation also distinguishes local behavior from Ollama Cloud support; structured-output capability should therefore not be blindly carried between local and cloud profiles.

### ACL implication

Structured-output validation has at least these layers:

```text
ACL schema
adapter schema representation
engine grammar/compiler
model constrained generation
host parse
host schema validation
```

A failure in one layer must not be attributed automatically to model intelligence.

---

# 20. Tools + structured output can fail as a capability combination: #17957

Open issue #17957 reports a useful composition failure on Ollama 0.32.15.

For `ornith-1.5:35b`:

- tools alone work;
- response-format schema alone works;
- tools + response-format schema together fail while initializing sampler grammar;
- a Qwen model works with the same combined request;
- logs identify the combined template/grammar path rather than a generic out-of-memory failure.

Primary source:

- https://github.com/ollama/ollama/issues/17957

### ACL test rule

Do not model capability as independent booleans only:

```text
tools=true
structured_output=true
thinking=true
```

Also test required **combinations**:

- tools + streaming;
- tools + structured output;
- tools + thinking;
- tools + long context;
- parallel/multi-tool + long context;
- structured output + long context;
- tool continuation after cache reuse.

A deployment can pass each individual feature and fail composition.

---

# 21. Harness/client compatibility is another behavior-bearing layer

Open issue #17444 reported VS Code/Copilot tool-call failure after updating Ollama versions, with rollback helping the reporter.

Task 17 does **not** classify this as a universal Ollama tool regression.

Follow-up investigation in the issue compared raw OpenAI-compatible outputs and found no simple universal response-shape break between the cited builds; the same current Ollama tool path also worked with another harness.

Primary source:

- https://github.com/ollama/ollama/issues/17444

### Useful conclusion

The strongest supported lesson is integration-scoped:

> Model + Ollama can produce a tool response that one client/harness consumes correctly and another does not.

Therefore include client/harness/parser version in the capability profile.

Do not promote a raw API success directly to "works in VS Code/Goose/OpenHands/ACL" without adapter-level testing.

---

# 22. Service and process lifecycle

## 22.1 Runner stop semantics

The llama-server path owns its subprocess and kills it during unload/stop. The MLX client attempts interrupt and escalates to force-kill after a bounded wait.

Current service startup/shutdown code handles service termination and scheduler/runner cleanup.

Primary sources:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/llm/llama_server.go
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/x/mlxrunner/client.go

### ACL boundary

These are **inference-runner lifecycle** semantics.

They do not terminate arbitrary worker tool subprocesses, revert repository mutations, undo network/API effects or settle ACL task state.

Keep:

- Ollama runner process ID;
- ACL worker process ID/tree;
- tool process/effect IDs;
- logical run/task IDs

as separate identities.

---

# 23. Network boundary: default loopback is doing real security work

Current environment default:

`OLLAMA_HOST = 127.0.0.1:11434`

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/envconfig/config.go

Current route construction installs:

- CORS policy;
- allowed-host checking designed to constrain requests to a loopback-bound service;
- inference/model-management routes.

Current ordinary local API route construction does not install a general authentication/authorization middleware protecting all normal local inference/model-management endpoints.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/server/routes.go

The OpenAI-client examples can supply a placeholder API key because the local Ollama compatibility endpoint does not use that placeholder as a normal access-control secret.

### ACL/Vera consequence

Loopback is part of the default trust boundary.

If Ollama is rebound to `0.0.0.0`, a LAN address or other remotely reachable interface, ACL/Vera should not assume CORS provides authentication.

Use an explicit outer boundary as required, e.g.:

- authenticated reverse proxy;
- mTLS/service mesh;
- host firewall/VPN;
- ACL-owned authenticated local service broker.

Exact deployment depends on use case, but **network exposure must be deliberate and recorded**.

---

# 24. Host-header and CORS protection are not general authorization

Current `allowedHostsMiddleware` does useful host validation when Ollama is loopback-bound, reducing hostile Host-header/DNS-rebinding style access paths.

When Ollama is intentionally bound to a non-loopback address, the middleware does not pretend that local-host restrictions are the authorization mechanism.

This is appropriate behavior, but it means the operator has taken responsibility for the new network trust boundary.

### ACL invariant

Separate:

- CORS/browser-origin policy;
- host-header/DNS-rebinding defenses;
- service authentication;
- model/tool authorization;
- worker network egress policy.

They solve different problems.

---

# 25. Offline/local policy must be explicit

Current Ollama provides cloud-related functionality and remote inference behavior.

`OLLAMA_NO_CLOUD` disables Ollama cloud features including remote inference and web search. Configuration state can also disable cloud behavior.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/envconfig/config.go

### ACL local-first profile

For a benchmark intended to measure local hardware/model capability:

- set/verify no-cloud mode;
- prohibit or account for remote inference;
- record any remote host fields in responses;
- optionally isolate the runtime's external network during strict offline fixtures;
- keep model pulls/setup outside the measured run when measuring inference.

Otherwise a future runtime change could cause a nominally "Ollama" benchmark to use a remote model and invalidate the comparison.

---

# 26. Debug request logging is useful but sensitive evidence

Current `OLLAMA_DEBUG_LOG_REQUESTS` enables reproducibility-oriented logging.

The implementation writes complete inference request bodies and replay commands into a temporary directory using restricted file permissions.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/server/inference_request_log.go

### ACL value

This can be extremely useful in the benchmark lab because a failing run can preserve the exact API request needed for reproduction.

### Security caveat

Those request bodies may contain:

- user/project text;
- system prompts;
- tool schemas;
- source code;
- file contents;
- images/data;
- potentially secret-bearing context supplied by a harness.

Treat debug-request captures as sensitive test evidence with explicit retention and access policy, not ordinary low-sensitivity logs.

---

# 27. Native metrics are valuable but not complete benchmark evidence

Current responses expose inference-oriented metrics including fields such as:

- load duration;
- prompt-evaluation count;
- prompt-evaluation cached count;
- prompt-evaluation duration;
- generated token count;
- generation duration;
- total duration.

Current `/api/ps` / running-model status exposes useful realized state including:

- loaded model;
- memory size;
- VRAM size;
- context length;
- expiry/keep-alive state.

Primary sources:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/api/types.go
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/api.md

### ACL benchmark evidence

Capture Ollama's native metrics, but combine them with independent host evidence for:

- wall-clock time;
- CPU utilization;
- GPU utilization;
- VRAM/RAM high-water mark;
- process exits/restarts;
- workspace/effect outcomes;
- verifier result.

The runtime cannot be the sole judge of whether the coding task succeeded.

---

# 28. Ollama's own integration suite is useful architecture evidence

Current `integration/README.md` describes end-to-end tests that are not part of ordinary lightweight `go test` execution.

It supports scopes such as:

- fast;
- release;
- library.

The full library scope can be very large, reinforcing why upstream does not execute every model combination in every routine test.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/integration/README.md

## 28.1 Coding-agent-like tool stress test

Current `integration/tools_stress_test.go` is particularly relevant.

The fixture uses:

- a large coding-agent-like system prompt;
- many verbose tool definitions;
- repeated requests;
- prompt-cache reuse;
- changed user messages;
- multi-turn tool responses.

The test also avoids interpreting extreme CPU fallback as a normal model-quality result by requiring a strong GPU-loaded condition for relevant cases.

Primary source:

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/integration/tools_stress_test.go

### ACL reuse

This is a useful fixture-design reference because toy `get_weather` tests can miss:

- realistic prompt/tool-schema pressure;
- cache interactions;
- parser drift over multiple turns;
- context behavior;
- tool-result continuation;
- hardware-placement performance cliffs.

ACL should still own its own fixtures and independent validation.

---

# 29. Failure classification suggested by Task 17

When a local coding-agent run fails, classify at least these domains separately.

## 29.1 Model-decision failure

Examples:

- chooses wrong tool;
- poor plan;
- fails task semantics despite correct runtime/tool transport.

## 29.2 Adapter/schema failure

Examples:

- schema keyword dropped;
- wrong API route semantics;
- client cannot parse valid tool response;
- renderer/template changes arguments.

## 29.3 Constraint/compiler failure

Examples:

- structured-output grammar cannot compile;
- tool+response schema combination produces invalid grammar.

## 29.4 Scheduler/resource failure

Examples:

- queue saturation;
- deadlock during eviction;
- memory fit changes offload;
- cold load stalls.

## 29.5 Hardware/backend failure

Examples:

- GPU not detected after suspend;
- Vulkan free-memory telemetry unavailable;
- driver/backend regression.

## 29.6 Context-state failure

Examples:

- unintended 4K fallback;
- unexpected truncation/context shift;
- cache invalidation changes prompt processing.

## 29.7 Harness/client failure

Examples:

- raw Ollama API works but consuming client fails to recognize tool call;
- provider adapter strips an Ollama-specific option.

Separating these categories prevents the benchmark from rejecting a model for a harness/runtime bug—or approving a model because the runtime hid a constraint error.

---

# 30. Candidate ACL/Vera invariants from Ollama

These are **derived engineering candidates**, not adopted governance decisions.

## OLLAMA-I1 — Exact runtime engine identity

Record Ollama release/commit, package digest, engine kind, pinned engine revision and compatibility patch profile.

## OLLAMA-I2 — Immutable model identity

Record manifest/layer/model artifact digests; mutable model tags remain aliases only.

## OLLAMA-I3 — Template/parser is capability state

Record exact template/system/parameters/parser/renderer and verify the resulting tool protocol.

## OLLAMA-I4 — Requested context must equal qualified context

Set benchmark context explicitly and record realized context. Silent fallback is non-comparable.

## OLLAMA-I5 — Runtime truncation is an observable event

Unexpected prompt truncation/context shift fails or invalidates a benchmark case that requires full retained context.

## OLLAMA-I6 — KV/cache/fit settings are benchmark identity

Pin KV cache type, flash attention, parallel slots, memory-fit target and other behavior-bearing runtime settings.

## OLLAMA-I7 — Realized offload is benchmark evidence

Record actual GPU/CPU placement. A full-GPU result and a partially offloaded result are distinct deployment profiles.

## OLLAMA-I8 — Scheduler transitions need explicit state and deadlines

Resource eviction/load transitions should not rely on overwriteable magic values or unbounded waits.

## OLLAMA-I9 — Runtime health includes cold-load/scheduling path

"HTTP alive" or "already-loaded model answers" is insufficient evidence that the runtime can accept new model work.

## OLLAMA-I10 — Capability metadata does not self-verify

`ollama show` capability labels nominate tests; only ACL fixtures create verified capability status.

## OLLAMA-I11 — Authoritative tool schema remains outside Ollama

Never discard ACL's full schema after translating it into Ollama's narrower representation.

## OLLAMA-I12 — Generated tool args are always host-validated

Validate against the original authoritative schema before policy/approval/effect dispatch.

## OLLAMA-I13 — Capability combinations are tested

Verify required combinations, not only independent feature flags.

## OLLAMA-I14 — API adapter is part of profile

Native Ollama API, OpenAI-compatible API and framework-specific provider adapters are separate qualified surfaces.

## OLLAMA-I15 — Local versus cloud is explicit

A local benchmark must prove local execution/no-cloud state; remote execution is a separate profile.

## OLLAMA-I16 — Network exposure is explicit authority configuration

Loopback default, LAN binding and externally exposed service each have different authentication/firewall requirements.

## OLLAMA-I17 — Sensitive debug requests have evidence policy

Replay/debug payloads get explicit audience and retention handling.

## OLLAMA-I18 — Upstream metrics are corroborated

Use Ollama metrics for runtime detail but independent host/verifier evidence for performance and task success.

---

# 31. Candidate Task 17 regression fixtures

## Fixture O-01 — Context precedence

Configure conflicting request/model/env/default context values and verify documented precedence plus realized `/api/ps` context.

## Fixture O-02 — 32K/64K explicit context

Start from a machine whose automatic tier would choose 4K. Explicitly request the benchmark context and fail if realized context differs.

## Fixture O-03 — Hidden truncation detector

Send a uniquely tagged long prompt near/over context and verify whether required early markers survive; capture truncation logs/evidence.

## Fixture O-04 — KV equivalence

Compare f16/q8/q4 KV configurations for memory, throughput, exact tool/structured-output fixtures and long-context quality.

## Fixture O-05 — Full-GPU placement gate

Record realized VRAM/offload; refuse model-quality comparison when one run silently moves to CPU.

## Fixture O-06 — Scheduler eviction concurrency

Load A, pressure runtime to evict A for B while sending a concurrent A reuse request; require bounded settlement and subsequent successful cold load.

## Fixture O-07 — Cold-load health

After multiple keep-alive/eviction cycles, verify both already-loaded inference and loading a different model under a hard deadline.

## Fixture O-08 — Tool-schema preservation

Submit a schema using numeric bounds, pattern, default, const, lengths, enums and nested constraints. Diff authoritative schema against model-visible/adapter representation.

## Fixture O-09 — Tool host validation

Force a model to generate a value outside enum/bounds. Verify ACL rejects it before tool dispatch regardless of Ollama acceptance.

## Fixture O-10 — Tool + response schema composition

For every promoted model, test tools and structured output individually and together.

## Fixture O-11 — Tool continuation/cache

Large coding-agent prompt + tool catalog; first call, repeated prompt cache reuse, changed user turn, tool result continuation and second tool request.

## Fixture O-12 — Native vs OpenAI-compatible parity

Run equivalent tool/structured-output/stream/error cases across native and OpenAI-compatible paths; record divergences rather than masking them.

## Fixture O-13 — Harness parser matrix

Same raw Ollama endpoint/model across ACL, Goose/provider adapter and another relevant client harness. Save raw responses when interpretation differs.

## Fixture O-14 — Offline enforcement

Enable no-cloud profile, prevent external egress where practical and verify a local model completes while remote/cloud paths fail closed.

## Fixture O-15 — Artifact immutability

Resolve model tag to manifest/layer digest, rerun after tag update and prove benchmark treats changed digest as a new deployment.

## Fixture O-16 — Runtime release regression

Run frozen fixtures on previous/current Ollama builds with same immutable model and compare context, realized offload, throughput, tool/structured-output outcomes and errors.

## Fixture O-17 — GPU discovery degradation

Where applicable, simulate/observe device discovery changes and ensure CPU fallback is explicit rather than silently accepted as comparable.

## Fixture O-18 — Request reproduction

Enable debug request logging in an isolated fixture, reproduce a failure from saved request, then securely retire the sensitive capture.

---

# 32. What Ollama does not provide for ACL/Vera

Task 17 found no basis to treat Ollama as:

- ACL's project scheduler;
- a worker sandbox;
- a credential broker;
- a filesystem/Git checkpoint manager;
- an external-effect exactly-once ledger;
- a durable agent conversation/task state machine;
- a verifier-owned acceptance system;
- a replacement for MCP/ACL authorization semantics;
- a Vera long-term memory system.

It is best evaluated as an inference/runtime service underneath those layers.

---

# 33. Explicit non-conclusions

Task 17 does **not** conclude:

- that Ollama is better or worse than direct llama.cpp for ACL;
- that Ollama is better or worse than vLLM;
- that any particular local model is the ACL worker winner;
- that MLX and llama.cpp engines are globally equivalent or globally unequal;
- that issue #17408 affects every current Ollama deployment;
- that issue #17099 means all newer releases are slower than older releases;
- that every JSON-Schema keyword must be implemented by Ollama to use tools safely;
- that structured output is unsafe;
- that #17444 is a universal Ollama tool regression;
- that binding Ollama to LAN is inherently unsafe if a proper outer security boundary exists;
- that `OLLAMA_NO_CLOUD` alone is a complete network sandbox;
- that upstream integration tests replace ACL-owned benchmarks;
- that ACL should start its benchmark lab before the separate research campaign/handoff says it is ready.

These remain later comparison/implementation questions.

---

# 34. Primary-source inventory

## Project/release/license

- https://github.com/ollama/ollama
- https://github.com/ollama/ollama/tree/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8
- https://github.com/ollama/ollama/releases/tag/v0.33.3
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/LICENSE

## Engine identity

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/LLAMA_CPP_VERSION
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/llama/README.md
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/MLX_VERSION
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/x/mlxrunner/client.go
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/llm/llama_server.go

## Configuration/context/scheduler

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/envconfig/config.go
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/context-length.mdx
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/server/routes_options_test.go
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/server/sched.go
- https://github.com/ollama/ollama/issues/17408
- https://github.com/ollama/ollama/pull/17416
- https://github.com/ollama/ollama/pull/17515
- https://github.com/ollama/ollama/issues/17099

## Hardware

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/gpu.mdx

## Models/manifests/templates

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/modelfile.mdx
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/manifest/layer.go
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/server/images.go

## Tools/structured output/API

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/capabilities/tool-calling.mdx
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/capabilities/structured-outputs.mdx
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/api/types.go
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/docs/api/openai-compatibility.mdx
- https://github.com/ollama/ollama/issues/17142
- https://github.com/ollama/ollama/issues/17597
- https://github.com/ollama/ollama/issues/17957
- https://github.com/ollama/ollama/issues/17444

## Security/network/debug

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/server/routes.go
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/SECURITY.md
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/server/inference_request_log.go

## Evaluation/integration

- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/integration/README.md
- https://github.com/ollama/ollama/blob/83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8/integration/tools_stress_test.go

---

# 35. Conclusion

Ollama is a strong candidate local-runtime layer for ACL because it solves many operational problems that direct engine integration would otherwise require ACL to own immediately: model packaging, local server API, engine distribution, GPU detection, memory placement, scheduling, model residency, templates/parsers, model metadata and common client compatibility.

The same convenience creates the central qualification requirement: **Ollama adds behavior-bearing layers above the model and above llama.cpp.** Those layers must be captured rather than erased by a generic `runtime=ollama` label.

The most reusable Task 17 lessons are:

1. pin immutable model and runtime/engine identities;
2. treat requested versus realized context/offload as separate evidence;
3. make scheduler/resource transitions explicit and bounded;
4. treat capability metadata as discovery rather than proof;
5. retain an authoritative full tool schema outside provider-specific representations;
6. host-validate every generated tool call before authorization/effect execution;
7. test capability combinations and exact harness adapters;
8. separate native/OpenAI-compatible/local/cloud profiles;
9. preserve realistic coding-agent stress/cache/continuation fixtures;
10. classify runtime, adapter, parser, constraint, scheduler and hardware failures separately from model failures.

For ACL/Vera, the appropriate conceptual placement remains:

```text
ACL/Vera policy + task/effect state + sandbox + verifier
                         |
                  harness/provider adapter
                         |
                      Ollama
               /                       \
    patched/pinned llama.cpp          MLX
               \                       /
          immutable model artifact + config
```

Ollama should be judged as a powerful, evolving inference-runtime component underneath ACL's control plane—not as the control plane itself.

**Task boundary:** Ollama research complete. No Letta Code research, cross-project winner selection, benchmark-lab execution, dependency adoption or worker/model execution was begun in Task 17.
