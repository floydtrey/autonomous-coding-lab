# Active People — Task 2

**Accessed:** 2026-09-05  
**Task:** Identify active people producing recurring signal relevant to ACL and future Vera work.  
**Status:** identification only; **no ranking is implied by inclusion or ordering**.

## Method

A person is included only when a stable public GitHub identity can be tied to **repeated, recent, attributable upstream work** in an active project. One drive-by pull request is not enough. This file deliberately uses the neutral term **recurring contributor** unless a primary source explicitly establishes a formal maintainer role.

Commit recurrence proves current involvement, not authority, employment, endorsement, or architectural ownership. Later tasks may decide which contributors are actually worth following closely or deep-researching.

## Confirmed recurring contributors

### Anas Khan — [`anxkhn`](https://github.com/anxkhn) — SWE-agent
- **Observed evidence:** recurring July 2026 contributor across multimodal SWE-bench evaluation mapping, CLI/docs correctness, image MIME handling, and repository URL parsing, with regression tests.
- **Why the contribution stream matters to ACL/Vera:** harness/evaluation boundary correctness, multimodal inputs, CLI contracts, and regression discipline.
- **Primary evidence:**
  - https://github.com/SWE-agent/SWE-agent/commit/3ea751c087f32b16e039a2233dd6eefecef325d5
  - https://github.com/SWE-agent/SWE-agent/commit/10ab1a978954a117b1b577b8c39fbeb78fedf69f
  - https://github.com/SWE-agent/SWE-agent/commit/5f40e63360d654adcd91e30ed11473389bc4909b
- **Warning:** recurring commits show current involvement; do not infer formal project authority or rank from inclusion here.

### Douwe Maan — [`DouweM`](https://github.com/DouweM) — Pydantic AI
- **Observed evidence:** multiple Sep 4-5 2026 commits on realtime session shutdown, interruption/cancel races, provider behavior, and examples.
- **Why the contribution stream matters to ACL/Vera:** concurrency, cancellation, lifecycle termination, provider abstraction, and tool/session failure handling.
- **Primary evidence:**
  - https://github.com/pydantic/pydantic-ai/commit/26467f6f3002784265709335a9dc5cb636b15d53
  - https://github.com/pydantic/pydantic-ai/commit/c10e8e6d68a40d032b55e60536a514a2bf0cd2cc
- **Warning:** recurring commits show current involvement; do not infer formal project authority or rank from inclusion here.

### Graham Neubig — [`neubig`](https://github.com/neubig) — OpenHands
- **Observed evidence:** recurring current contributor: Sep 5 provider `base_url` fix; Sep 3 review-evidence policy; multiple Aug 2026 model, CI, telemetry, and repository-boundary changes.
- **Why the contribution stream matters to ACL/Vera:** model-provider configuration, evidence/review policy, repository boundaries, and coding-agent lifecycle decisions.
- **Primary evidence:**
  - https://github.com/OpenHands/OpenHands/commit/2ead26e7727146a3a7eaef48640aee70e5f78beb
  - https://github.com/OpenHands/OpenHands/commit/4524a919930d62535a5cdca143c8a54eaf0ede42
  - https://github.com/OpenHands/OpenHands/commit/e9ca71d138a658ea15d930b2be3a5b28c251a7f2
- **Warning:** recurring commits show current involvement; do not infer formal project authority or rank from inclusion here.

### Jack Amadeo — [`jamadeo`](https://github.com/jamadeo) — Goose
- **Observed evidence:** multiple Sep 4 2026 Goose commits, including preferring the latest MCP version and release automation for the Goose Developer Kit.
- **Why the contribution stream matters to ACL/Vera:** MCP integration, developer-kit/harness packaging, release mechanics, and extensibility.
- **Primary evidence:**
  - https://github.com/aaif-goose/goose/commit/6d8152a99adbd149783d9d0cc2b43ce2755cca95
  - https://github.com/aaif-goose/goose/commit/2c4aeb5630ee61edec648309417237bfa2469eea
- **Warning:** recurring commits show current involvement; do not infer formal project authority or rank from inclusion here.

### Jesús Samuel — [`jesussamuel-byte`](https://github.com/jesussamuel-byte) — Gemini CLI
- **Observed evidence:** two consecutive Sep 4 2026 security-focused commits: strict permission/ownership checks for system configuration and stronger workspace/symlink boundary checks.
- **Why the contribution stream matters to ACL/Vera:** directly relevant filesystem authorization, symlink/path escape defense, configuration trust, and command safety.
- **Primary evidence:**
  - https://github.com/google-gemini/gemini-cli/commit/85aca163f6c73ac6ce380b5447359146b8adcae4
  - https://github.com/google-gemini/gemini-cli/commit/567afbbe8fc7927e38bd40733bf09cafc227ede4
- **Warning:** recurring commits show current involvement; do not infer formal project authority or rank from inclusion here.

### Johannes Gäßler — [`JohannesGaessler`](https://github.com/JohannesGaessler) — llama.cpp
- **Observed evidence:** recurring 2026 contributor across CUDA/MMQ, cuBLAS, tensor parallelism, quantized KV cache, model/backend fixes, plus current repository maintenance.
- **Why the contribution stream matters to ACL/Vera:** local runtime performance/compatibility, GPU backends, quantization, KV cache, and multi-device behavior that can materially affect ACL workers.
- **Primary evidence:**
  - https://github.com/ggml-org/llama.cpp/commit/1425386fd996511e1f3295e7366c38289a92a271
  - https://github.com/ggml-org/llama.cpp/commit/6eddde06a4f25d55d538b5d15628dcc2b6882147
  - https://github.com/ggml-org/llama.cpp/commit/8e6fff84de4a31506e0f90bacbf821731e66d237
- **Warning:** recurring commits show current involvement; do not infer formal project authority or rank from inclusion here.

### Kartik Labhshetwar — [`kartik-mem0`](https://github.com/kartik-mem0) — Mem0
- **Observed evidence:** repeated Sep 2-4 2026 Mem0 commits spanning SDK releases, OSS configuration behavior, and documentation maintenance.
- **Why the contribution stream matters to ACL/Vera:** reliable signal for current Mem0 release/integration changes; useful when later evaluating memory lifecycle and operational maturity.
- **Primary evidence:**
  - https://github.com/mem0ai/mem0/commit/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3
  - https://github.com/mem0ai/mem0/commit/9a7924befd7026e41e445ba809370009e5e985a6
  - https://github.com/mem0ai/mem0/commit/3cf41878ea74f92b0ca29a93e690d880cefd0589
- **Warning:** recurring commits show current involvement; do not infer formal project authority or rank from inclusion here.

### Kazuhiro Sera — [`seratch`](https://github.com/seratch) — OpenAI Agents SDK
- **Observed evidence:** several Sep 5 2026 commits covering route verification, repository-skill CI, and realtime test organization.
- **Why the contribution stream matters to ACL/Vera:** agent-framework verification, CI/regression structure, repository skills, and realtime lifecycle tests.
- **Primary evidence:**
  - https://github.com/openai/openai-agents-python/commit/1d471a4775bf2f40179f411824da383deb4c3fca
  - https://github.com/openai/openai-agents-python/commit/36b38b8aec941aae4d4508d7b47a90b1babaac40
  - https://github.com/openai/openai-agents-python/commit/f1ffb3db89d146e11d6aaf5c3d2bfc69908ae2b9
- **Warning:** recurring commits show current involvement; do not infer formal project authority or rank from inclusion here.

### Nick Hollon — [`nick-hollon-lc`](https://github.com/nick-hollon-lc) — LangGraph
- **Observed evidence:** recurring May-Sep 2026 contributions to v3 stream projections, RemoteGraph streaming, stream decoders/interleaving, SDK releases, subagent naming, and lifecycle surfaces.
- **Why the contribution stream matters to ACL/Vera:** long-running runtime semantics—streams, checkpoints/projections, remote execution, subagents, interruptions, and lifecycle observability.
- **Primary evidence:**
  - https://github.com/langchain-ai/langgraph/commit/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1
  - https://github.com/langchain-ai/langgraph/commit/68fa011fc999610b824535058d146dbfd2e814ae
  - https://github.com/langchain-ai/langgraph/commit/1fcb7681825faf0372fc1556910b0337ea10d761
- **Warning:** recurring commits show current involvement; do not infer formal project authority or rank from inclusion here.

### Saoud Rizwan — [`saoudrizwan`](https://github.com/saoudrizwan) — Cline
- **Observed evidence:** multiple Sep 3-4 2026 commits, including preventing `apply_patch` Add File from overwriting existing files and CLI/model-selection fixes.
- **Why the contribution stream matters to ACL/Vera:** file-operation safety, edit semantics, CLI agent behavior, and provider/model routing.
- **Primary evidence:**
  - https://github.com/cline/cline/commit/adbfbd97d352c82f7001273365f6a4bac38b5adb
  - https://github.com/cline/cline/commit/dac3b35ba485dbab3b5a73aca239b0d07ce071cf
- **Warning:** recurring commits show current involvement; do not infer formal project authority or rank from inclusion here.

## Observations from contributor activity

- **Safety work is visible in ordinary engineering commits.** Saoud Rizwan's Cline changes and Jesús Samuel's Gemini CLI changes expose practical failure modes around file replacement, path boundaries, symlinks, permissions, and configuration trust.
- **Runtime reliability work clusters around lifecycle edges.** Nick Hollon's LangGraph work and Douwe Maan's Pydantic AI work repeatedly touch streaming, interruption, cancellation, remote execution, and session termination.
- **Evaluation/harness correctness needs dedicated attention.** Anas Khan's SWE-agent changes show that seemingly small CLI, MIME, repository-URL, or benchmark-subset mismatches can invalidate an agent run before model quality is even relevant.
- **Local-model behavior depends on runtime engineers as much as model authors.** Johannes Gäßler's llama.cpp work spans CUDA, tensor parallelism, quantized KV cache, and backend correctness—the layer that can change ACL worker performance without a model-weight change.
- **Provider abstractions are moving targets.** Graham Neubig's OpenHands work, Jack Amadeo's Goose MCP work, and Kazuhiro Sera's Agents SDK changes are useful streams for watching the seams between models, tools, protocols, and harness behavior.
- **Memory projects require operational as well as conceptual tracking.** Kartik Labhshetwar's Mem0 release/configuration work is a current ecosystem signal, but it should not be mistaken for proof about memory architecture quality or safety.

## People intentionally not added

This task did not add a person solely because they founded a project, are highly visible publicly, appear in historical authorship, or authored one recent pull request. Bot-heavy repositories and repositories whose current work did not expose a repeatable human identity were left for later investigation rather than guessed.

## Stop boundary

This file identifies recurring current contributors only. It does **not** rank people, infer organizational authority, recommend outreach, analyze collaboration prospects, or begin the later person-by-person deep-research task.
