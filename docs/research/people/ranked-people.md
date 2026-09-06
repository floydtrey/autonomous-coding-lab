# Ranked People — Task 3

**Accessed:** 2026-09-05  
**Task:** Rank the Task 2 recurring-contributor watchlist for ACL/Vera research.  
**Interpretation:** this ranks **technical-signal watch priority**, not seniority, organizational authority, employment status, public reputation, or outreach priority.

## Method

Only the 10 contributors already verified in Task 2 are ranked. The heuristic favors:

1. **Direct relevance to unresolved ACL/Vera hard problems — 35%**
2. **Recurrence and recency of attributable work — 20%**
3. **Depth/breadth of the relevant implementation surface — 20%**
4. **Distinctive signal not already duplicated by other watch streams — 15%**
5. **Evidence clarity / auditability — 10%**

The ranking is intentionally about whose public contribution stream is most likely to reveal useful engineering decisions and failure modes. It does not infer that the contributor owns the relevant subsystem or speaks for the project.

## Tier A — highest-priority contributor streams

### 1. Saoud Rizwan — `saoudrizwan` — Cline
- **Why #1:** current work is extremely close to ACL's highest-risk execution boundary: preventing destructive file replacement and refining coding-agent CLI/model behavior.
- **Evidence:** the Sep 4 `apply_patch` fix makes Add File refuse to overwrite existing files; other current commits touch model selection and CLI behavior.
- **Signal to watch:** edit semantics, filesystem safeguards, model/provider routing, and coding-agent runtime decisions.
- **Warning:** repeated commits do not establish formal subsystem ownership.
- **Primary evidence:**
  - https://github.com/cline/cline/commit/adbfbd97d352c82f7001273365f6a4bac38b5adb
  - https://github.com/cline/cline/commit/dac3b35ba485dbab3b5a73aca239b0d07ce071cf

### 2. Nick Hollon — `nick-hollon-lc` — LangGraph
- **Why #2:** unusually dense recurring signal on long-running lifecycle mechanics—stream projections, RemoteGraph execution, decoders/interleaving, releases, subagents, interruptions, and checkpoint-adjacent runtime behavior.
- **Signal to watch:** checkpoint/resume semantics, remote execution, streaming state, interruption, subagent lifecycle, and observable run state.
- **Warning:** LangGraph's architecture is broader than ACL's; the value is in the hard runtime lessons, not an assumption ACL needs a graph framework.
- **Primary evidence:**
  - https://github.com/langchain-ai/langgraph/commit/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1
  - https://github.com/langchain-ai/langgraph/commit/68fa011fc999610b824535058d146dbfd2e814ae
  - https://github.com/langchain-ai/langgraph/commit/1fcb7681825faf0372fc1556910b0337ea10d761

### 3. Jesús Samuel — `jesussamuel-byte` — Gemini CLI
- **Why #3:** two consecutive current security fixes directly address workspace path boundaries, symlink resolution, configuration ownership, and permission checks—the exact class of authority escapes ACL must prevent independently of model quality.
- **Signal to watch:** filesystem authorization, command safety, configuration trust, symlink/path traversal defense, and extension/environment boundaries.
- **Warning:** the implementation sits in a Gemini product, but the threat mechanics are provider-neutral.
- **Primary evidence:**
  - https://github.com/google-gemini/gemini-cli/commit/85aca163f6c73ac6ce380b5447359146b8adcae4
  - https://github.com/google-gemini/gemini-cli/commit/567afbbe8fc7927e38bd40733bf09cafc227ede4

### 4. Graham Neubig — `neubig` — OpenHands
- **Why #4:** recurring work spans provider configuration, review-evidence policy, CI readiness, repository boundaries, telemetry, and model/profile behavior, providing both technical and process-level agent reliability signal.
- **Signal to watch:** provider seams, evidence/review requirements, repository trust boundaries, coding-agent lifecycle and telemetry.
- **Warning:** contribution recurrence is not equivalent to sole architectural ownership.
- **Primary evidence:**
  - https://github.com/OpenHands/OpenHands/commit/2ead26e7727146a3a7eaef48640aee70e5f78beb
  - https://github.com/OpenHands/OpenHands/commit/4524a919930d62535a5cdca143c8a54eaf0ede42
  - https://github.com/OpenHands/OpenHands/commit/e9ca71d138a658ea15d930b2be3a5b28c251a7f2

### 5. Johannes Gäßler — `JohannesGaessler` — llama.cpp
- **Why #5:** local-model workers depend on runtime engineers as much as model weights. His recurring work spans CUDA/MMQ, cuBLAS, tensor parallelism, quantized KV cache, model/backend fixes, and current maintenance.
- **Signal to watch:** runtime regressions, quantization/backend behavior, KV-cache constraints, multi-device behavior, and local-inference performance changes.
- **Warning:** runtime expertise does not answer harness policy, authorization, or task-validation questions.
- **Primary evidence:**
  - https://github.com/ggml-org/llama.cpp/commit/1425386fd996511e1f3295e7366c38289a92a271
  - https://github.com/ggml-org/llama.cpp/commit/6eddde06a4f25d55d538b5d15628dcc2b6882147
  - https://github.com/ggml-org/llama.cpp/commit/8e6fff84de4a31506e0f90bacbf821731e66d237

## Tier B — strong targeted watch streams

### 6. Douwe Maan — `DouweM` — Pydantic AI
- **Priority reason:** current work on session shutdown, cancellation races, realtime tools and provider behavior exposes concurrency/lifecycle edges that are easy for long-running agents to mishandle.
- **Signal to watch:** cancellation, async lifecycle, session termination, provider abstraction and race conditions.
- **Primary evidence:**
  - https://github.com/pydantic/pydantic-ai/commit/26467f6f3002784265709335a9dc5cb636b15d53
  - https://github.com/pydantic/pydantic-ai/commit/c10e8e6d68a40d032b55e60536a514a2bf0cd2cc

### 7. Anas Khan — `anxkhn` — SWE-agent
- **Priority reason:** recurring fixes show how seemingly small harness mismatches—benchmark subset mapping, MIME headers, URL parsing and CLI hierarchy—can invalidate an agent run before model capability matters.
- **Signal to watch:** evaluation validity, harness regression discipline, multimodal handling and CLI/config contracts.
- **Primary evidence:**
  - https://github.com/SWE-agent/SWE-agent/commit/3ea751c087f32b16e039a2233dd6eefecef325d5
  - https://github.com/SWE-agent/SWE-agent/commit/10ab1a978954a117b1b577b8c39fbeb78fedf69f
  - https://github.com/SWE-agent/SWE-agent/commit/5f40e63360d654adcd91e30ed11473389bc4909b

### 8. Kazuhiro Sera — `seratch` — OpenAI Agents SDK
- **Priority reason:** repeated current work on route verification, repository-skill CI and realtime test organization provides useful signal on framework verification and regression structure.
- **Signal to watch:** run-state verification, test responsibility boundaries, skills/tooling CI and realtime lifecycle tests.
- **Primary evidence:**
  - https://github.com/openai/openai-agents-python/commit/1d471a4775bf2f40179f411824da383deb4c3fca
  - https://github.com/openai/openai-agents-python/commit/36b38b8aec941aae4d4508d7b47a90b1babaac40
  - https://github.com/openai/openai-agents-python/commit/f1ffb3db89d146e11d6aaf5c3d2bfc69908ae2b9

### 9. Jack Amadeo — `jamadeo` — Goose
- **Priority reason:** current MCP-version handling and Goose Developer Kit release work give a useful stream for protocol integration and agent-harness packaging.
- **Signal to watch:** MCP compatibility, extension/developer-kit boundaries, release/version behavior and provider integration.
- **Primary evidence:**
  - https://github.com/aaif-goose/goose/commit/6d8152a99adbd149783d9d0cc2b43ce2755cca95
  - https://github.com/aaif-goose/goose/commit/2c4aeb5630ee61edec648309417237bfa2469eea

### 10. Kartik Labhshetwar — `kartik-mem0` — Mem0
- **Priority reason:** repeated SDK-release, OSS-configuration and documentation work makes this a reliable operational stream for a major memory project.
- **Signal to watch:** memory API releases, integration/config changes and operational maturity.
- **Why #10:** Task 2 evidence is stronger on release/integration operations than on the memory-integrity/provenance problems that are most distinctive for future Vera.
- **Primary evidence:**
  - https://github.com/mem0ai/mem0/commit/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3
  - https://github.com/mem0ai/mem0/commit/9a7924befd7026e41e445ba809370009e5e985a6
  - https://github.com/mem0ai/mem0/commit/3cf41878ea74f92b0ca29a93e690d880cefd0589

## Ranking observations

- The top five deliberately span **file safety, lifecycle/recovery, authorization boundaries, coding-agent evidence policy, and local inference**. Watching five people doing the same kind of orchestration work would produce less information.
- People can move rapidly in this ranking because contribution focus changes. The project ranking is the more stable queue; the people ranking should be refreshed from attributable work before any person-by-person deep research.
- High rank does not imply the user should contact, follow socially, or collaborate with the person. Collaboration/outreach is a later assigned task.

## Stop boundary

This file ranks already-verified recurring contributors only. It does not infer formal maintainership, employment, organizational authority, collaboration fit, or begin person-by-person deep research.
