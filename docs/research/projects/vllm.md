# vLLM — Task 24 Deep Research

**Research date:** 2026-09-07  
**Research target:** current vLLM inference/runtime architecture, OpenAI-compatible serving, scheduler/concurrency/KV-cache/context behavior, structured output/tool calling, cancellation/timeouts, local hardware/quantization/backend compatibility, observability, distributed execution, security/current failures, reproducibility and reusable mechanisms  
**Canonical repository:** `vllm-project/vllm`  
**Pinned current-main revision:** `58ad1f3b8973b23943107b51230d594050b42ec3` (2026-09-07)  
**Latest stable release observed:** `v0.28.0` (published 2026-08-26)  
**License:** Apache-2.0  
**Scope boundary:** vLLM only. OpenCode remains Task 25 and was not researched.

## Executive assessment

vLLM is a high-value runtime reference for ACL because it exposes, in unusually explicit form, the difference between **a model artifact** and a **realized inference deployment**. The behavior ACL would observe depends not only on model weights but on exact vLLM revision/build, model/tokenizer revisions, chat template, tool parser, structured-output backend, quantization, attention/kernel backend, scheduler settings, KV-cache configuration, parallel topology, hardware, and request/API mode.

The strongest reusable lesson is not “use vLLM.” It is that ACL's future local-model qualification must treat the inference runtime as a behavior-bearing component with its own correctness, security, cancellation, cache, and reproducibility profile. A model that appears capable through one vLLM profile is not automatically qualified through another.

vLLM V1 provides mature runtime mechanisms that are useful reference material:

- a centralized scheduler with explicit waiting/running/request state;
- continuous batching under explicit request/token budgets;
- block-managed KV cache and automatic prefix caching;
- recomputation/preemption behavior under KV pressure;
- model-specific structured-output and tool-call parser paths;
- extensive OpenAI-compatible and other serving interfaces;
- Prometheus metrics around queueing, prefill, decode, KV use and request lifecycle;
- multiple local hardware and quantization backends;
- tensor/pipeline/data/context parallelism and experimental prefill/decode disaggregation;
- explicit reproducibility controls and caveats;
- unusually candid security documentation about API, network, cache, plugin, tool-server and distributed-cluster trust.

The strongest warnings for ACL are equally important:

1. **Advertised context is not realized trustworthy context.** Current open #54521 demonstrates a specific long-context execution path in which identical greedy requests diverge and silently corrupt text after a sparse-attention threshold even though HTTP succeeds.
2. **Protocol metadata can become model-visible behavior.** Current main still serializes full tool objects through `model_dump()`, corroborating open #52741 where server-side `strict` changes the prompt and tool behavior.
3. **Route cancellation does not prove child engine work stopped.** Open #55502 on stable v0.28.0 shows `/rerank` continuing all queued document work after client disconnect despite `@with_cancellation`.
4. **Distributed runtime recovery is not transparent.** Open #49238 and still-open #50047 show stale NIXL peer/metadata state can survive P/D peer replacement and require explicit invalidation/re-handshake.
5. **Built-in HTTP API-key auth is not a complete server security boundary.** Current security docs explicitly list inference and operational endpoints that remain unauthenticated even with `--api-key`.
6. **Distributed workers are a shared trust domain by default.** Inter-node traffic is unencrypted/unauthenticated by default, and RayExecutorV2 uses driver-environment copy-all-except-denylist semantics.
7. **Inference-level tools and effect-level tools are different authority domains.** vLLM can merely parse tool calls, but optional tool servers can also execute model-generated code/browser operations. ACL should keep effect execution outside the inference runtime.

Task 24 therefore supports later comparison of vLLM as an inference substrate or direct local serving runtime. It does **not** support choosing vLLM over Ollama, llama.cpp, another serving engine, or a gateway; selecting a model; choosing a quantization; adopting P/D disaggregation; or changing ACL/Vera architecture.

---

## 1. Project identity, maturity and reproducibility anchor

### 1.1 Canonical upstream

Observed on 2026-09-07:

- repository: `https://github.com/vllm-project/vllm`
- default branch: `main`
- pinned research revision: `58ad1f3b8973b23943107b51230d594050b42ec3`
- pinned commit date: 2026-09-07
- stable release observed: `v0.28.0`, published 2026-08-26
- license: Apache License 2.0

The stable release provides platform-specific wheel assets with SHA-256 digests in GitHub release metadata. These asset digests are useful immutable package evidence, but they do not identify a complete runtime because CUDA/PyTorch/driver/container/model configuration still affects execution.

### 1.2 Deployment identity is broader than `vllm==x.y.z`

Current `EngineArgs`/`ModelConfig` exposes behavior-bearing fields including:

- `model`;
- `runner`;
- `tokenizer` and tokenizer mode;
- `trust_remote_code`;
- model `dtype`;
- seed;
- model revision;
- code revision;
- tokenizer revision;
- `max_model_len`;
- quantization;
- model/HF overrides;
- local/remote media policy.

Cache/runtime settings add:

- GPU-memory utilization;
- explicit KV-cache memory bytes;
- KV-cache dtype/layout/block size;
- prefix caching and hash algorithm;
- KV offloading and backend;
- tensor/pipeline/data/context parallel topology;
- scheduler token/sequence limits;
- compilation/kernel/attention choices;
- speculative decode configuration;
- distributed/KV connector selection.

For ACL benchmarking, the minimum vLLM profile therefore needs exact:

`vLLM commit/release + package/container digest + model artifact/revision + tokenizer/revision + chat template + parser/constraint backend + quantization + dtype + hardware/driver/backend + max_model_len + KV profile + scheduler profile + parallel topology + API route + streaming/tool mode`.

### 1.3 Mutable aliases are insufficient

A model repository name, Docker tag such as `latest`, or vLLM version string alone is insufficient benchmark provenance. When possible retain immutable model revision/digest and image/wheel digest.

### 1.4 `trust_remote_code` is executable authority

`--trust-remote-code` is a model-loading trust decision, not an ordinary model compatibility knob. ACL should default to pinned reviewed model code/artifacts and record whether external model repository code was permitted to execute.

---

## 2. V1 runtime architecture and scheduler

### 2.1 Central scheduler owns inference-resource state

Pinned current `vllm/v1/core/sched/scheduler.py` owns explicit runtime collections and limits, including:

- request-ID → request object mapping;
- waiting queue;
- skipped-waiting queue;
- running requests;
- finished and preempted request IDs;
- maximum concurrent requests;
- maximum scheduled-token budget;
- `max_model_len`;
- KV-cache manager;
- optional KV connectors/offloading;
- structured-output manager;
- encoder/multimodal cache managers.

This is strong reference material for deterministic resource ownership. It is **not** ACL task state: scheduler request IDs and queues disappear with runtime state and do not establish task/effect settlement.

### 2.2 Scheduling policy is deployment behavior

Current V1 supports explicit scheduling policy including FCFS and priority. Batching decisions affect latency, preemption, kernel/batch shape, and potentially reproducibility; therefore scheduler policy and load conditions should be part of benchmark identity.

### 2.3 Token budget is distinct from context ceiling

The scheduler's per-step token budget and max running sequences determine how work is batched. `max_model_len` defines an upper sequence boundary, but serving a 32K request safely also requires sufficient KV/cache/runtime capacity and compatible kernels.

### 2.4 Preemption is runtime recomputation, not task rollback

vLLM may preempt requests when KV resources are insufficient and later resume/recompute inference work. Metrics expose PREEMPTED/SCHEDULED lifecycle events. This is inference-resource scheduling only:

- it does not roll back agent workspace effects;
- it does not roll back external API calls;
- it does not provide an ACL continuation checkpoint;
- generated token handling and cache behavior remain runtime concerns.

### 2.5 Multiple in-flight batches create explicit KV ordering hazards

Current scheduler source contains specific protection for overlapping batches with KV consumers: freed blocks may need deferred release because a prior batch can still be writing them while a connector might otherwise reallocate/load into them. This is an important pattern: performance concurrency requires explicit resource-lifetime ownership and fences.

ACL implication: inference runtime “request finished” and resource memory actually safe for reuse can be separate transitions internally. The inference runtime owns that boundary; ACL should not infer task semantics from it.

---

## 3. KV cache, prefix caching and realized context

### 3.1 KV capacity is realized runtime state

Pinned `CacheConfig` currently defaults `gpu_memory_utilization` to **0.92** per vLLM instance. `kv_cache_memory_bytes`, when explicitly set, overrides the inferred cache size based on GPU-memory utilization.

The runtime records derived values such as:

- number of GPU blocks;
- group-aware KV-cache token capacity;
- estimated maximum concurrency at `max_model_len`.

This directly supports an ACL rule: **requested context and realized capacity are separate evidence**.

### 3.2 KV dtype is behavior/performance state

Current cache types include model dtype, FP8 families, NVFP4 and other quantized cache modes. KV quantization can alter memory capacity and numerical behavior. A “32K vLLM” qualification must retain KV dtype, not just model quantization.

### 3.3 KV offload changes the runtime path

vLLM can offload KV cache to CPU through native or LMCache-backed paths. Offload changes latency, resource pressure and failure surface. It should be treated as a separate benchmark profile rather than transparent capacity expansion.

### 3.4 Automatic Prefix Caching (APC)

vLLM V1 uses a block-hash-based prefix cache. Hash components include:

- parent block hash;
- exact block token IDs;
- extra hashes such as LoRA identity, multimodal identity and cache salt.

Only full blocks are cached. Request blocks and shared cache blocks use explicit reference counts/free queues.

### 3.5 Prefix-cache hash choice is reproducibility/security state

Current choices include:

- `sha256` — default, but uses Pickle serialization and may not reproduce across Python/vLLM versions;
- `sha256_cbor` — canonical CBOR, reproducible and cross-language compatible;
- `xxhash` / `xxhash_cbor` — faster non-cryptographic alternatives with documented collision/privacy tradeoffs.

For ACL reproducibility, `sha256_cbor` is a stronger deterministic cache-identity candidate than default Pickle-based `sha256` when cache identity itself needs to be compared across environments. This is not a recommendation to change production settings without benchmark evidence.

### 3.6 Prefix caching is a tenant confidentiality boundary

Current security documentation explicitly cites CVE-2025-46570: shared prefix caching creates a timing side-channel where an attacker can infer whether another request's guessed prefix is cached by measuring TTFT.

vLLM supports optional request `cache_salt`, mixed into the first block hash. Requests only share cached prefixes when they use the same salt.

Current upstream recommendations:

- multi-tenant deployments should set per-user/per-tenant secret salts;
- salts must be unpredictable, not usernames/account IDs;
- no salt retains global sharing behavior.

ACL/Vera implication: if a shared vLLM service ever serves multiple principals or trust groups, cache isolation belongs to the trusted gateway/control plane. A model-generated or predictable cache-salt value is not a security boundary.

### 3.7 Multimodal caller UUIDs are cache authority

Current security docs say optional client-supplied media `uuid` values can become cache identity. Reusing the same UUID for different media in a shared server can produce:

- integrity failure: later caller's media silently replaced by earlier cached media;
- confidentiality failure: caller can receive output derived from another caller's media.

Use cryptographically random media UUIDs in multi-tenant deployments or omit UUID and use content hashing. This is a strong general ACL/Vera lesson: caller-provided cache keys can become authority-bearing input.

---

## 4. 32K local-context qualification

### 4.1 `max_model_len=32768` is a request, not proof

A configured 32K ceiling does not establish:

- that the model artifact actually supports that positional/context regime correctly;
- that enough KV capacity exists at the selected batch/concurrency level;
- that the attention backend/kernel remains correct across the full range;
- that quantization/KV quantization remains accurate;
- that tool calling remains reliable at long context;
- that preemption is bounded;
- that latency is acceptable;
- that repeated identical requests are stable.

### 4.2 Recommended later 32K vLLM fixture classes

When ACL eventually benchmarks vLLM, the vLLM-specific profile should include at minimum:

1. cold 32K single request;
2. warm repeated 32K request;
3. identical greedy requests repeated several times;
4. contexts spanning attention/kernel transition thresholds;
5. 32K with tool schemas/system prompt/workspace context;
6. 32K with concurrency pressure;
7. 32K with prefix cache both enabled and disabled;
8. 32K with required structured output;
9. observed KV capacity and preemption count;
10. OOM/timeout/cancellation cleanup and subsequent service health.

### 4.3 Current #54521: long-context silent-corruption fixture

Open issue #54521 was updated on 2026-09-07 and reports a narrowly scoped but severe profile:

- model: `Qwen/Qwen3.8-Flash-Next-FP8`;
- vLLM development build from official Qwen/vLLM image lineage;
- two NVIDIA DGX Spark GB10 (SM121), TP=2;
- sparse-attention QSA path;
- identical `temperature=0` requests.

Observed with `indexer_budget=8192`:

- below threshold: 1 unique completion across 5 runs;
- above threshold: 3–4 unique completions across 5 runs;
- user-visible text can be silently corrupted while HTTP remains 200.

Reporter disabled prefix caching, used eager execution, tested multiple weight-loading and quantization paths, and reproduced through raw completions. The reporter did **not** test the model's default indexer budget, so the exact threshold beyond their override remains unverified.

Do not generalize #54521 to all vLLM, all Qwen, all GPUs, or all sparse attention. Its value is as a fixture proving that **successful long-context serving and greedy sampling do not prove deterministic/correct long-context execution**.

ACL consequence: model/runtime promotion at 32K should repeat deterministic probes on the exact intended hardware/kernel profile and include non-English/byte-sensitive correctness where relevant, not merely measure whether the request completes.

---

## 5. Structured outputs and tool calling

### 5.1 Tool-call mode is a runtime capability profile

Current vLLM supports:

- named function calling;
- `tool_choice="auto"`;
- `tool_choice="required"`;
- `tool_choice="none"`.

These modes have materially different constraint paths.

### 5.2 Named and required calls use structured output

Current docs say named function calling and `required` use structured-output constraints against the function parameter JSON schema and guarantee a validly parseable/schema-conforming call. Upstream explicitly warns that this is **not a guarantee of high-quality tool choice**.

This maps cleanly to ACL:

- schema validity is one capability;
- choosing the correct tool is another;
- authorization to execute the chosen tool is a third.

### 5.3 Auto tool calling depends on parser/template/profile

`auto` requires operator-selected model-specific behavior:

- `--enable-auto-tool-choice`;
- `--tool-call-parser`;
- optional parser plugin;
- compatible chat template.

Without strict structural constraints, auto tool calls are parsed from raw model text and may be malformed.

### 5.4 Strict-auto semantics are configuration-dependent

Current docs say structural constraints in `auto` require:

- `VLLM_ENFORCE_STRICT_TOOL_CALLING=true` (default);
- at least one tool with `strict:true`;
- a parser that supports structural tags.

Thus “vLLM tool calling” is not one capability. Benchmark identity must include parser, template, strict flag/profile and structured-output backend.

### 5.5 Structured-output backend `auto` is mutable behavior

Current structured-output configuration can select a backend automatically. Upstream documentation warns the automatic choice is opinionated and subject to change across releases. ACL qualification should therefore record the realized backend rather than only the requested `auto` value when backend behavior matters.

### 5.6 Current #52741: server-control field leaks into model prompt

Open #52741 reports that OpenAI protocol `tools[].function.strict` is sent into the model-visible tool block. The issue's reproduction on v0.24 found:

- prompt token count changes when `strict` is present;
- `strict:false` materially degraded tool-call formatting in a realistic 24-tool Qwen workload;
- server-side constraint selection treated absent and false equivalently, isolating prompt exposure as the behavioral difference.

Pinned current main still contains:

```python
tool_dicts = [tool.model_dump() for tool in request.tools]
```

in `vllm/renderers/online_renderer.py`, and the tokenize path has equivalent full model dumping. No `strict` exclusion is visible in that projection.

Task 24 did not freshly execute the reproduction on v0.28/current main, so this is recorded as a **current-source-correlated open failure surface**, not a new runtime reproduction.

High-value ACL invariant: keep server-only policy/constraint metadata separate from the authoritative model-visible tool schema unless intentional. Model prompt projection and server-side authorization/validation should be separately testable representations.

---

## 6. Request identity, streaming, cancellation and abort

### 6.1 HTTP request completion is not engine settlement

Current routes use `with_cancellation`, which creates two tasks:

- the route handler;
- a disconnect listener.

Whichever completes first causes the other task to be cancelled. The decorator therefore provides a handler-level cancellation mechanism.

The key limitation is architectural: cancelling the handler coroutine only settles underlying work if the handler propagates cancellation to every engine child request/resource it spawned.

### 6.2 Current #55502: rerank cancellation leak on v0.28.0

Open #55502 was reproduced against the stable `vllm/vllm-openai:v0.28.0` container.

Reporter fired 20 rerank requests × 31 documents, with clients disconnecting after two seconds. Despite the route being decorated with `@with_cancellation`, all **620 query/document pairs** continued executing over ~57 seconds. Similar behavior was reported with explicit socket close and reverse proxy.

This is route-specific evidence for pooling/rerank, not proof that every generative request leaks after disconnect.

Reusable rule:

`client disconnected` → `HTTP handler cancelled` → `all engine child requests aborted` → `GPU/resource work settled`

must be treated as separate states and tested separately.

### 6.3 Request IDs remain correlation/runtime identities

vLLM request IDs help route and abort inference requests. They are not ACL effect IDs, task IDs, durable idempotency keys, or continuation checkpoints.

### 6.4 Streaming success boundary matters

Once output bytes/tokens are delivered, client-visible state exists even if the generation later fails. ACL should preserve the already-established cross-project rule that transport/stream commitment, semantic completion and durable task success are separate states.

---

## 7. Serving surface and API security

### 7.1 Built-in API key has an explicitly limited scope

Current vLLM security docs state `--api-key`/`VLLM_API_KEY` protects OpenAI-like `/v1`, `/v2`, `/inference` path prefixes, but **does not protect the whole HTTP server**.

Current docs list unprotected surfaces even when an API key is configured, including examples such as:

- `/invocations` — inference capability;
- non-`/v1` scoring/pooling/classify/rerank routes;
- `/pause` and `/resume`;
- `/abort_requests`;
- scaling controls;
- weight-transfer/update controls;
- `/tokenize` and `/detokenize`;
- health/version/load endpoints.

The docs explicitly call `/invocations` particularly concerning because it reaches similar inference capability without the `/v1` auth middleware.

Therefore ACL/Vera should never expose vLLM directly to untrusted networks relying only on `--api-key`. If network exposure is ever needed, put vLLM behind a trusted reverse proxy/firewall with an explicit route allowlist and ACL-owned principal authorization.

### 7.2 Development mode is high authority

`VLLM_SERVER_DEV_MODE=1` enables sensitive endpoints such as:

- server configuration inspection;
- prefix/media/encoder-cache reset;
- sleep/wake;
- `collective_rpc`, which upstream labels extremely dangerous.

This mode must be absent from production qualification.

### 7.3 gRPC is private-network-only by design

Optional vLLM gRPC Inference/Control services are unauthenticated, unauthorized and unencrypted by default. If enabled, they can run inference and mutate runtime state. Treat them as an internal trusted-network protocol, not an end-user API.

### 7.4 Remote media is SSRF/resource-consumption surface

Current security docs recommend:

- explicit `--allowed-media-domains`;
- optionally disabling redirects;
- download/decode limits for images/audio/embeddings.

A vLLM inference server that can fetch user-specified URLs carries network authority. ACL's least-authority local worker profile should either disable remote media fetches or confine them behind explicit trusted policy.

### 7.5 Request fanout can be a DoS primitive

The request `n` parameter scales output sequence generation. vLLM has a configurable maximum, but current default is intentionally high for general use. ACL should expose only the request shapes it actually needs and cap fanout at the trusted adapter layer.

---

## 8. Tool server, plugins and executable trust

### 8.1 Tool parsing is not tool execution

Normal vLLM chat tool calling returns structured calls for the **caller** to execute. This is the desirable inference/runtime boundary for ACL: vLLM can nominate/format a tool call while ACL owns authorization and effects.

### 8.2 Optional tool servers cross into effects

vLLM can opt into external tool servers through `--tool-server`. No tool server is enabled by default.

The built-in `demo` path delegates to `gpt-oss` browser/Python tools. Current security docs warn the Python interpreter runs model-generated code in Docker **without network isolation by default**, which can potentially reach:

- host/LAN services;
- cloud metadata;
- internal distributed endpoints.

Prompt injection can therefore influence executable code with network reach.

ACL should **not** enable this path for worker effects. Keep model execution/inference and effect execution in separate processes/trust domains under ACL policy.

### 8.3 Endpoint/general plugins are trusted executable code

Endpoint plugins can add arbitrary FastAPI routes and reach engine RPC. Current docs warn route conflicts are not currently structurally prevented and plugins can shadow core paths. General plugins can execute in worker processes.

Thus plugin set/version is deployment identity and belongs in trusted configuration outside worker mutation authority.

### 8.4 Dynamic LoRA loading is explicitly not secure

Runtime LoRA load/unload is opt-in, and current docs explicitly call dynamic LoRA loading not secure for untrusted clients. If ever used, it is an administrator effect that changes model behavior, not a worker/model-level tool.

---

## 9. Cache-directory and artifact trust

Current vLLM security docs state cache directories are assumed private/trusted and cache content may be loaded without cryptographic integrity verification, including formats capable of arbitrary code execution.

Relevant caches include compilation/Triton/FlashInfer/assets/XLA/media paths.

ACL implications:

- runtime caches are executable/performance artifacts, not untrusted shared scratch;
- do not mount worker-writable directories into trusted vLLM cache roots;
- a compromised worker should not be able to poison inference-engine compile/artifact caches;
- trusted build/cache provenance and worker workspace authority must remain separate.

This is especially important if one physical machine hosts both the local inference service and autonomous coding workers.

---

## 10. Hardware, OS and quantization compatibility

### 10.1 Windows boundary

Current upstream installation docs state vLLM does **not** support Windows natively. Windows use is through WSL or community-maintained forks.

For the user's Windows workstation, a vLLM candidate would therefore likely be a WSL/Linux/container deployment profile rather than a native Windows profile. This is a deployment fact to benchmark later, not a Task 24 adoption recommendation.

### 10.2 NVIDIA support floor

Current CUDA installation docs state NVIDIA GPU compute capability **7.5 or higher** for the primary CUDA path.

### 10.3 Multiple accelerator families

Current project supports materially different accelerator/platform paths including NVIDIA CUDA, AMD ROCm, Intel XPU and CPU profiles; Apple GPU support exists through community-maintained vLLM-Metal/MLX-oriented work rather than the same CUDA runtime path.

These are separate runtime profiles, not interchangeable installation options.

### 10.4 Quantization compatibility is hardware-specific

vLLM supports many weight/cache quantization schemes, but exact support is architecture/backend-specific. Candidate formats include AWQ/GPTQ families, bitsandbytes, FP8, INT4/INT8, ModelOpt/Quark/TorchAO/GGUF-related paths, plus quantized KV cache.

A quantized model file existing is not proof that the exact vLLM build/hardware path supports it correctly or efficiently.

### 10.5 Kernel availability can differ from vLLM routing support

Open #49011 is a useful compatibility example: the reporter demonstrates underlying FlashInfer NVFP4 KV kernels on SM120 while vLLM's current routing does not expose that combination. This shows that “kernel/library supports X” and “current vLLM integration supports X” are separate facts.

### 10.6 Benchmark exact hardware

For ACL's local tower, do not extrapolate H100/DGX benchmark evidence to the user's GPU. Capture exact GPU model/VRAM, compute capability, driver, CUDA/PyTorch/vLLM build and realized memory/offload profile.

---

## 11. Distributed execution and trust

### 11.1 Distributed serving is not one runtime profile

vLLM supports combinations of:

- tensor parallelism;
- pipeline parallelism;
- data parallelism;
- context parallelism;
- multiprocessing/Ray distributed execution;
- KV transfer/offload connectors;
- experimental prefill/decode disaggregation.

Each changes execution topology, failure modes and credential/network surface.

### 11.2 Inter-node communication is insecure by default

Current security docs explicitly state that inter-node communications are insecure by default, including:

- PyTorch Distributed;
- KV-cache transfer;
- tensor/pipeline/data parallel channels.

PyTorch distributed communication has no built-in authorization and is unencrypted. Upstream recommends isolated networks/firewalls.

ACL rule: never treat vLLM's internal distributed port as an authenticated agent/runtime protocol.

### 11.3 Ray cluster is one trust domain

Current vLLM docs explicitly treat the entire Ray cluster as a single trust domain. Any principal able to submit Ray tasks/actors is effectively trusted to execute arbitrary worker-node code.

This is consistent with Ray's security model and means ACL should not place untrusted autonomous workers inside the same Ray cluster merely for convenience.

### 11.4 Driver environment can propagate broadly to workers

Current `RayExecutorV2` uses a **copy-all-except-denylist** strategy for driver environment variables. This may include Hugging Face tokens, cloud keys, registry tokens or internal credentials unless operators exclude them.

Worker-side values use `setdefault`, so existing worker environment values are retained.

ACL consequence: if distributed vLLM is ever used, start the inference service from a deliberately minimal trusted environment and explicitly denylist any driver-only credentials. This is separate from the even stricter rule that autonomous tool workers should get minimal explicit environment projection.

---

## 12. Disaggregated prefill/decode

### 12.1 Experimental feature, explicit goal

Current docs label disaggregated prefilling **experimental and subject to change**.

Its goals are:

- independently tune TTFT and inter-token latency;
- control tail ITL by separating prefill from decode instances.

Upstream explicitly says **P/D disaggregation does not improve throughput**.

### 12.2 Connector identity matters

Current documentation exposes multiple connector implementations (NIXL, LMCache, Mooncake, offloading, multi-connector, etc.). Connector type/version/configuration is therefore deployment identity.

### 12.3 Blocking/async transfer semantics matter

The architecture splits scheduler-side transfer planning from worker-side KV movement. Lookup/transfer paths include blocking and asynchronous operations. These are runtime-data transfer states, not durable task continuation.

### 12.4 Current #49238 / #50047: stale-peer recovery fixture

Open #49238 reports decode instability/segfault after a prefill pod restarts in NIXL P/D disaggregation.

Issue discussion separates at least two failure layers:

1. NIXL-side disconnect handling/crash behavior;
2. vLLM-side cached dead-peer state/rkeys that can survive until TTL.

Still-open PR #50047 proposes invalidating cached peer state when transfer fails or a new engine appears at the same network address, forcing a re-handshake.

Recent issue comments also report stale-endpoint/hang behavior when the **decode** peer is replaced while prefill remains alive, showing restart direction matters and one healthy readiness probe is not proof the distributed KV path is healthy.

Task 24 does not claim current main always reproduces the original segfault. It retains this as an **experimental distributed-recovery fixture** because the vLLM invalidation PR remains open and the issue remains open.

ACL lesson: remote runtime replacement needs generation/lease/endpoint identity and stale-state invalidation. A service health endpoint is insufficient recovery evidence for a connector carrying authoritative runtime state.

---

## 13. Reproducibility and determinism

Current upstream is explicit:

> vLLM does not guarantee reproducibility by default, for performance reasons.

Offline reproducibility options include:

- `VLLM_ENABLE_V1_MULTIPROCESSING=0` for deterministic scheduling;
- batch invariance.

Online mode uses batch invariance rather than disabling multiprocess scheduling.

Even with those controls, upstream only claims reproducibility on the **same hardware and same vLLM version**.

V1 seed defaults to `0` so worker sampling RNGs remain coordinated; the seed cannot simply be “unspecified” in V1 because distributed/speculative workflows need consistent sampling.

### ACL implications

A model benchmark should not assume:

- `temperature=0` implies execution determinism;
- a seed makes results portable across hardware/runtime versions;
- one successful run establishes reliability;
- isolated-request behavior matches concurrent-batch behavior.

For promotion, repeat frozen-profile trials and explicitly compare isolated versus loaded/concurrent runs.

---

## 14. Observability and evidence

### 14.1 Prometheus metrics are strong runtime evidence

V1 exposes a rich `/metrics` surface including examples such as:

- requests running/waiting;
- KV-cache usage;
- prefix-cache queries/hits;
- prompt/generation tokens;
- request success by finish reason;
- TTFT;
- inter-token latency/TPOT;
- end-to-end latency;
- queue/prefill/decode timing;
- request prompt/generation lengths.

The engine records lifecycle events such as QUEUED, SCHEDULED, PREEMPTED and NEW_TOKENS so frontend metrics can reconstruct intervals.

### 14.2 Metrics are not correctness evidence

Prometheus can prove useful facts such as:

- service remained alive;
- requests queued/preempted;
- KV pressure existed;
- generation continued after client disconnect;
- latency/resource use changed.

It does **not** prove:

- generated answer was semantically correct;
- a tool call was the right tool;
- 32K context was faithfully processed;
- ACL verifier accepted artifacts;
- an external effect settled exactly once.

### 14.3 Observability itself has deployment variation

Some process-level metrics disappear under multi-API-server/multiprocess modes. Metric names also have deprecation/version policy. Retain vLLM revision and server topology with performance evidence.

---

## 15. Performance benchmarks versus ACL task benchmarks

vLLM's own benchmark and production metrics are principally inference performance/capacity evidence: throughput, latency, TTFT, TPOT, batch behavior, cache performance, etc.

ACL's later benchmark must add orthogonal correctness dimensions:

- tool-call schema and selection;
- instruction adherence;
- code task correctness;
- long-context evidence recall;
- refusal/authority behavior;
- deterministic harness behavior;
- cancellation/recovery;
- artifact/verifier acceptance.

A fast vLLM profile can therefore lose to a slower profile if the latter preserves required tool/context correctness for the target worker role.

---

## 16. Security architecture implications for ACL/Vera

### 16.1 Recommended trust placement if vLLM is ever used

Pattern-only conclusion from current evidence:

```text
ACL/Vera trusted controller/gateway
    |
    | authenticated, allowlisted inference request
    v
vLLM inference service
    |
    | model computation only
    v
model output / proposed tool call
    |
    v
ACL policy + schema validation + effect ledger + sandbox
```

Do **not** invert this and let vLLM's optional model-facing tool server become ACL's effect authority.

### 16.2 Inference server should not share worker write authority

Protect from worker mutation:

- vLLM binaries/environment;
- model artifacts;
- trusted tokenizer/template/parser files;
- compile/kernel/cache directories;
- server config;
- proxy/firewall config;
- API/admin credentials.

### 16.3 API exposure should be minimal

For a single-machine ACL lab, the lowest-authority profile is likely loopback/private-network inference with only necessary routes exposed through a trusted adapter. Task 24 does not choose this architecture; it records it as the security-minimizing direction if vLLM later survives comparison.

---

## 17. Current/open failure matrix

| Fixture | Status at Task 24 | Scope | ACL/Vera lesson |
| --- | --- | --- | --- |
| #54521 Qwen3.8 Flash Next greedy divergence | Open; updated 2026-09-07 | Specific model/QSA/SM121/TP profile | Advertised context + HTTP 200 + temp=0 do not prove long-context correctness/determinism |
| #52741 `strict` leaks into tool prompt | Open; current main still full-dumps tool object | Tool schema/chat-template projection | Server control metadata and model-visible tool schema are separate representations |
| #55502 rerank survives client disconnect | Open; reproduced on stable v0.28.0 | Rerank/pooling child requests | Handler cancellation does not prove child-engine/resource settlement |
| #49238 NIXL P/D restart failure | Open | Experimental P/D / NIXL | Distributed endpoint generation/stale state needs explicit invalidation/re-handshake |
| #50047 stale peer invalidation | Open PR | vLLM side of NIXL peer cache | TTL alone can fail when activity refreshes stale identity |
| CVE-2025-46570 prefix cache timing | Historical security advisory with current mitigation | Multi-tenant shared prefix cache | Per-tenant secret salt is required when prefix privacy matters |
| API-key endpoint limitation | Current documented behavior | HTTP server | Built-in API key is route-prefix auth, not complete server authorization |
| Ray env propagation | Current documented behavior | Distributed Ray | Driver secrets can flow to workers; cluster is one trust domain |

### Important non-overclaiming rules

- Open issues are not automatically reproduced on pinned main unless current source/issue evidence explicitly supports that statement.
- #54521 is not evidence that all vLLM long-context requests corrupt output.
- #55502 is not evidence that every generation route ignores cancellation.
- #49238/#50047 concerns experimental P/D NIXL recovery, not ordinary single-instance serving.
- historical CVE evidence is used to retain regression/security classes, not to claim current v0.28 is unpatched.

---

## 18. High-value reuse candidates

### 18.1 Pattern: explicit runtime profile

Reuse the idea of treating scheduler/cache/model/parser/backend settings as first-class deployment state. ACL's benchmark manifest should record these fields even if vLLM is not ultimately adopted.

### 18.2 Pattern: resource-state metrics

vLLM's request lifecycle metrics provide a good vocabulary for distinguishing:

- queue delay;
- prefill;
- decode;
- preemption;
- KV utilization;
- first-token/inter-token latency.

ACL can use compatible concepts for inference performance evidence while keeping task lifecycle separate.

### 18.3 Pattern: cache salt / trusted namespace isolation

Per-tenant secret salting is a strong pattern for avoiding cross-principal cache inference/reuse. Similar trusted-domain salting/namespace rules may apply to Vera retrieval caches and ACL inference caches.

### 18.4 Pattern: strict server/tool representation separation

#52741 is a useful negative fixture for future adapters. ACL should maintain:

1. authoritative tool definition/policy metadata;
2. provider/runtime projection;
3. exact model-visible prompt projection;
4. returned parsed call;
5. authoritative schema revalidation.

### 18.5 Pattern: hierarchical cancellation

#55502 motivates a deterministic cancellation tree:

`client/task cancel -> all inference child IDs -> engine abort acknowledged -> queued/running work drains -> resources settled`.

### 18.6 Pattern: distributed endpoint generation and stale-state invalidation

#49238/#50047 maps well to ACL distributed-runtime design: immutable endpoint instance/generation identities, leases and stale-route invalidation are safer than relying on a stable logical ID plus refreshed TTL.

---

## 19. Candidate ACL/Vera invariants derived from vLLM

1. Model capability is qualified against an exact serving-runtime profile, not weights alone.
2. Requested context and measured realized context are separate evidence.
3. `max_model_len` is not proof of long-context correctness.
4. Repeat deterministic long-context probes even at `temperature=0`.
5. Runtime/kernel/hardware transitions inside the context window deserve explicit boundary tests.
6. Model revision, tokenizer revision and chat-template identity are benchmark fields.
7. Tool parser and structured-output backend are benchmark fields.
8. Native/named/required/auto tool-call modes are separately qualified.
9. Schema-valid tool arguments do not prove correct tool selection.
10. Server-only protocol metadata must not silently become model-visible prompt content.
11. Preserve authoritative tool schema outside runtime-specific projections.
12. Revalidate model-produced tool calls against ACL's authoritative schema after parsing.
13. Prefix-cache salt is trusted isolation state, not model-selected metadata.
14. Predictable tenant identifiers are not cache-isolation secrets.
15. Caller-provided cache/media identifiers must not cross tenant boundaries without trusted namespace controls.
16. Cache hashes, KV state and runtime caches are performance state, not ACL task checkpoints.
17. Inference cache directories are trusted executable/performance state and remain worker-unwritable.
18. Client disconnect, handler cancellation, engine abort and resource settlement are separate lifecycle states.
19. Cancellation propagates to every child inference request before task cancellation is considered settled.
20. A successful HTTP response does not prove semantic correctness.
21. vLLM request IDs are correlation/runtime IDs, not ACL task/effect/idempotency IDs.
22. Preemption/recompute is inference scheduling, not task rollback.
23. Scheduler/load profile belongs in benchmark identity when it can affect behavior.
24. Reproducibility claims bind exact vLLM version and hardware.
25. Online/offline batch-invariance settings are explicit benchmark fields.
26. Performance telemetry cannot serve as independent correctness/verifier evidence.
27. Built-in vLLM API-key auth is insufficient as a whole-server security boundary.
28. Expose vLLM through an explicit reverse-proxy/route allowlist if clients beyond the trusted host can reach it.
29. Dev/profiler/collective-RPC surfaces are absent from production qualification.
30. Model effect execution remains outside vLLM; optional tool-server execution is not ACL effect authority.
31. Runtime plugins are trusted executable configuration outside worker write authority.
32. Runtime LoRA/weight mutation is a privileged administrator effect.
33. Remote media fetch is network authority and needs explicit domain/size/redirect policy.
34. Inter-node vLLM transport is an internal trusted-network protocol unless separately secured.
35. A Ray cluster is one trust domain; untrusted workers do not share it.
36. Inference driver environment is intentionally minimized and credential propagation to distributed workers is explicit.
37. Distributed peer identity includes instance generation/lease, not only stable logical name/address.
38. Health/readiness is not proof that distributed KV transfer is healthy after peer replacement.
39. P/D connector/version/topology is a distinct deployment capability profile.
40. Quantization support is exact hardware/runtime/backend compatibility, not a file-format claim.
41. Weight quantization and KV-cache quantization are separately recorded.
42. WSL/native Linux/community Windows forks are separate vLLM runtime profiles.
43. Immutable release/model/package digests are preferred to mutable tags.
44. `trust_remote_code` is an executable trust decision and must be recorded.
45. ACL's later 32K qualification should test correctness, tool use, cancellation and concurrency—not only throughput/OOM.
46. Runtime cache hits should be visible so cached inference is not mistaken for fresh compute where fresh compute matters.
47. Distributed runtime recovery and ACL task recovery remain separate layers.
48. vLLM remains below ACL-owned policy, credentials, sandbox, task/effect ledger and verifier.

---

## 20. Candidate regression fixtures for the later benchmark/harness lab

### Fixture V1 — 32K greedy repeatability
Send identical long-context `temperature=0` requests repeatedly under the exact target profile. Compare byte-level and semantic outputs. Fail promotion on unexplained divergence.

### Fixture V2 — context threshold sweep
Sweep prompt length across model/kernel-specific context or sparse-attention thresholds rather than testing only 1K and 32K endpoints.

### Fixture V3 — concurrency invariance
Repeat the same frozen request alone and under representative concurrent load. Record output/trajectory divergence separately from latency.

### Fixture V4 — cache-on/cache-off equivalence
For deterministic prompts, compare prefix-cache enabled versus disabled output and validate cache isolation.

### Fixture V5 — tenant salt isolation
Two tenants share identical prefixes but different secret cache salts; verify no cross-tenant cache reuse signal is exposed through the intended gateway profile.

### Fixture V6 — media UUID collision
Attempt same media UUID with different contents across isolated tenants. Gateway must prevent collision or derive trusted scoped identity.

### Fixture V7 — named tool call schema
Use named function calling with nested/strict authoritative schema and validate final arguments against the original ACL schema.

### Fixture V8 — auto tool call
Run model-specific parser/template in auto mode. Measure parse validity, correct selection and false tool-call rate separately.

### Fixture V9 — server-only tool field leak
Ensure control metadata such as `strict` does not unexpectedly alter model-visible schema except where deliberately designed and qualified.

### Fixture V10 — tool-none prompt projection
When tool choice is none, verify whether tools remain in model prompt under the selected profile and whether ACL expects that behavior.

### Fixture V11 — client disconnect
Terminate a request and prove handler cancellation plus engine abort/resource drain, not merely closed socket.

### Fixture V12 — child-request cancellation
For fanout/pooling workloads, cancel parent and verify every child request becomes terminal and GPU queue drains.

### Fixture V13 — KV pressure/preemption
Run 32K workload under constrained KV pressure; record preemption/recompute, latency and correctness after recovery.

### Fixture V14 — cold service restart
Restart vLLM and prove cache loss/residency does not masquerade as ACL continuation-state loss.

### Fixture V15 — P/D peer restart
If P/D is ever considered, restart prefill and decode peers independently and validate stale endpoint invalidation/re-handshake.

### Fixture V16 — unauthenticated-route probe
Against the intended deployed reverse-proxy profile, verify all non-allowlisted vLLM inference/control/dev routes are unreachable even if upstream itself leaves them unauthenticated.

### Fixture V17 — worker cache poisoning
Attempt writes from an untrusted worker to model/runtime/cache/template/parser directories. Required result: structurally impossible.

### Fixture V18 — distributed credential projection
If Ray/multi-node is used, inspect realized worker environment and verify only intended inference credentials/config are present.

### Fixture V19 — quantization/KV profile matrix
Run same model/tool/context fixtures across candidate quantization and KV-cache dtype profiles; treat each result independently.

### Fixture V20 — restart health versus correctness
After runtime/connector restart, distinguish `/health` success from successful real generation and, if applicable, KV transfer.

---

## 21. Reuse/adoption questions deferred to synthesis

Task 24 intentionally does not answer:

- whether vLLM should replace Ollama or direct llama.cpp for the user's initial local tower;
- whether LiteLLM should sit in front of vLLM;
- whether 16 GB VRAM is sufficient for any specific planned model at 32K;
- which model/quantization should serve Foreman/worker/verifier roles;
- whether WSL operational complexity outweighs vLLM throughput benefits on the user's Windows host;
- whether P/D or Ray is relevant at single-machine scale;
- whether vLLM's structured-output/tool parsers are more reliable than another runtime for the selected models;
- whether vLLM should be a direct dependency, local service, container, or not adopted.

Those require the later cross-project synthesis and the user's actual hardware benchmark.

---

## 22. Primary source set

### Canonical repository / release / license
- https://github.com/vllm-project/vllm
- https://github.com/vllm-project/vllm/commit/58ad1f3b8973b23943107b51230d594050b42ec3
- https://github.com/vllm-project/vllm/releases/tag/v0.28.0
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/LICENSE

### Runtime/config/cache
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/vllm/v1/core/sched/scheduler.py
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/vllm/config/cache.py
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/vllm/engine/arg_utils.py
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/docs/design/prefix_caching.md

### Serving/tooling/reproducibility
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/docs/features/tool_calling.md
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/vllm/renderers/online_renderer.py
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/vllm/entrypoints/serve/utils/api_utils.py
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/docs/usage/reproducibility.md

### Security/distribution/observability
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/docs/usage/security.md
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/docs/features/disagg_prefill.md
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/docs/design/metrics.md
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/docs/getting_started/installation/gpu.md
- https://github.com/vllm-project/vllm/blob/58ad1f3b8973b23943107b51230d594050b42ec3/docs/getting_started/installation/gpu.cuda.inc.md

### Current/open failure evidence
- https://github.com/vllm-project/vllm/issues/54521
- https://github.com/vllm-project/vllm/issues/52741
- https://github.com/vllm-project/vllm/issues/55502
- https://github.com/vllm-project/vllm/issues/49238
- https://github.com/vllm-project/vllm/pull/50047
- https://github.com/vllm-project/vllm/issues/49011
- https://github.com/vllm-project/vllm/security/advisories/GHSA-4qjh-9fv9-r85r

---

## 23. Task 24 stop boundary

Task 24 ends with vLLM researched as an **inference/runtime candidate and reference**, not selected infrastructure.

No OpenCode research was begun. No vLLM/Ollama/llama.cpp/LiteLLM winner was selected. No model, quantization, structured-output backend, tool parser, cache configuration, WSL/container profile, distributed topology, gateway, dependency, or sandbox was selected. No local benchmark was run. No ACL/Vera runtime/governance code was modified.

The next separately authorized research task is **Task 25 — OpenCode** only.
