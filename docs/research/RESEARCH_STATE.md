# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 17 — Ollama deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Completed campaign checkpoints
- Tasks 1–4: recurring sources, active projects/people, ranked research priority, and failed/abandoned/heavily redesigned attempts.
- Task 5: **Pydantic AI / official Harness** — `projects/pydantic-ai.md`.
- Task 6: **Cline** — `projects/cline.md`.
- Task 7: **LangGraph** — `projects/langgraph.md`.
- Task 8: **promptfoo** — `projects/promptfoo.md`.
- Task 9: **Strands Harness SDK** — `projects/strands-harness-sdk.md`.
- Task 10: **Codex** — `projects/codex.md`.
- Task 11: **OpenHands** — `projects/openhands.md`.
- Task 12: **SWE-agent / SWE-ReX / mini-swe-agent transition** — `projects/swe-agent-mini-swe-agent.md`.
- Task 13: **llama.cpp** — `projects/llama-cpp.md`.
- Task 14: **OpenAI Agents SDK** — `projects/openai-agents-sdk.md`.
- Task 15: **Model Context Protocol** — `projects/model-context-protocol.md`.
- Task 16: **Goose** — `projects/goose.md`.
- Task 17: **Ollama** — `projects/ollama.md`.

## Task 17 work completed
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before research.
- Began from finalized Task 16 checkpoint `f523d8ec1a4a33bc59eee6827f7bb16e6649038b`.
- Verified canonical project identity `ollama/ollama`, active/non-archived, MIT licensed.
- Inspected current upstream revision `83ed7d9965b1ee07e0f0b29fd46e47c31f0fcab8` dated 2026-09-05.
- Verified latest release observed was `v0.33.3`, published 2026-09-02 with refreshed assets on 2026-09-03.
- Verified release artifacts publish SHA-256 digests and include platform/engine-specific packages such as ROCm/MLX variants.
- Verified current Ollama pins llama.cpp via `LLAMA_CPP_VERSION=b10760` and applies Ollama compatibility patches from `llama/compat/` before build.
- Recorded that Ollama's pinned/patched llama.cpp must be treated as behaviorally distinct from a direct pristine llama.cpp deployment unless identical ACL fixtures prove equivalence.
- Verified separate MLX runner identity with pinned `MLX_VERSION=37c26e5755da637255d57ea34b4879196a485301` and materially different implemented surfaces from llama-server.
- Verified current MLX runner lacks the inspected native llama-server Chat/template/embedding/device-info methods and uses its own structural-output representation.
- Verified llama-server and MLX runner launch as loopback subprocesses under Ollama process control and inherit the parent service environment before runtime-specific adjustments.
- Preserved stronger ACL operational rule: run Ollama itself with a deliberate service environment and keep worker/tool-process secret projection separately least-privilege.
- Verified model packaging is content-addressed with SHA-256 layer digests and pull/download digest verification.
- Verified Modelfile behavior-bearing fields include `FROM`, `PARAMETER`, `TEMPLATE`, `SYSTEM`, `ADAPTER`, `LICENSE`, `MESSAGE` and `REQUIRES`.
- Derived benchmark artifact identity as manifest/layer/model digest plus Modelfile/template/system/parameter/adapter state; mutable tags remain aliases.
- Verified current context default is VRAM-tiered: roughly 4K below 24 GiB, 32K from 24–48 GiB and 256K at/above 48 GiB.
- Verified current Ollama documentation recommends at least 64K for agent/coding/web-search workloads, so automatic default is not an adequate coding-agent benchmark policy.
- Verified effective `num_ctx` precedence from current tests/source: request > model/Modelfile > `OLLAMA_CONTEXT_LENGTH` > VRAM-tier default, bounded by model context.
- Derived required ACL benchmark evidence: record both requested and realized context, and treat unintended fallback as non-comparable.
- Verified underlying runner has prompt truncation/context-shift behavior; unexpected runtime truncation must be distinguished from harness compaction/model forgetting.
- Verified behavior-bearing KV/runtime controls include flash attention, KV cache type, GPU overhead, llama fit target, request parallelism, max loaded models, queue size, keep-alive and scheduling spread.
- Recorded KV/cache/fit/parallel settings as deployment-profile fields rather than performance-only notes.
- Deep-researched current scheduler: bounded request queue, runner reuse/refcounts, memory refresh/fit estimation, eviction, keep-alive, configurable loaded-model/parallel limits and finite one-shot load-OOM retry.
- Verified some current model families are forced to single parallel slot because parallel request behavior is not universally safe.
- Recorded open scheduler issue #17408 as current high-value concurrency evidence: eviction state can be overwritten by concurrent runner reuse, leaving a cold-load scheduler path waiting indefinitely while loaded models continue responding.
- Verified proposed explicit-expiring fix PR #17416 remained open/unmerged during Task 17; related PR #17515 was closed unmerged.
- Derived scheduler invariants: explicit lifecycle states, hard deadlines on unload/load waits and health checks that exercise cold-load/scheduling ability rather than only HTTP/already-loaded inference.
- Recorded open #17099 as release-sensitive memory-estimation/offload evidence: a small runtime change moved a documented model from full GPU to partial CPU and produced a large throughput cliff; maintainer acknowledged the regression/workaround.
- Derived benchmark invariant that realized GPU/CPU offload belongs in evidence and a changed placement is a different deployment profile.
- Deep-researched current hardware/backend guidance for CUDA, ROCm/HIP, Metal and Vulkan plus visible-device controls.
- Recorded that scheduler quality depends on free-VRAM observability; nominal GPU detection is weaker evidence than stable device identity plus realized memory telemetry.
- Verified native Ollama API and OpenAI-compatible API are distinct surfaces; upstream explicitly describes compatibility with parts of the OpenAI API rather than universal feature parity.
- Verified current Ollama can use cloud/remote behavior and exposes `OLLAMA_NO_CLOUD` plus remote-host policy, so `runtime=ollama` does not imply local/offline inference.
- Derived strict offline benchmark profile: explicitly disable cloud/remote inference, verify realized local execution and keep local/cloud results separate.
- Deep-researched capability discovery in `server/images.go`: tool/thinking/vision/completion capability is assembled from config, metadata, templates, parser/renderer and family rules; tool discovery can include template-string heuristics.
- Derived explicit distinction `DiscoveredCapability != VerifiedDeploymentCapability`.
- Verified current native tool-schema types preserve only a subset of JSON Schema.
- Recorded open #17142: constraints such as minimum/maximum/default/pattern/length/const are silently dropped because current tool structs do not retain them; current-main structs still substantiate the issue's core claim.
- Recorded open #17597: surviving `enum` can reach the model yet is not enforced in tool-call decoding, while the same constraint can be enforced under structured-output `response_format`.
- Derived mandatory ACL invariant: preserve the authoritative full tool schema outside Ollama and host-validate every generated call before policy/approval/effect dispatch.
- Verified structured output uses a different constrained-generation path from ordinary tool argument presentation.
- Recorded open #17957 as composition evidence: a documented model can support tools and response schema separately yet fail with a grammar-initialization error when both are combined.
- Derived capability-matrix requirement: verify required feature combinations, not independent booleans only.
- Rechecked #17444 and intentionally **did not** classify it as a universal Ollama tool regression; follow-up raw-response evidence supports treating it as client/harness integration-scoped behavior.
- Derived requirement to version the consuming harness/client/parser along with Ollama/model capability state.
- Verified local service default bind is loopback `127.0.0.1:11434` and current route construction applies CORS/allowed-host policy but no general authentication middleware over ordinary local inference/model-management routes.
- Derived network rule: loopback is part of Ollama's default trust boundary; LAN/external binding requires an explicit outer authentication/firewall/TLS policy appropriate to the deployment. CORS is not authorization.
- Verified `OLLAMA_NO_CLOUD` disables remote inference/web-search cloud features and `OLLAMA_REMOTES` constrains allowed remote-model hosts.
- Verified `OLLAMA_DEBUG_LOG_REQUESTS` can save exact inference request bodies and replay commands with restrictive file permissions; classified those captures as sensitive reproducibility evidence.
- Verified response/runtime observability includes load/prompt/cache/generation token-duration metrics and running-model context/VRAM/expiry information.
- Preserved independent-evidence rule: Ollama metrics supplement, but do not replace, host performance telemetry and verifier-owned task success evidence.
- Deep-researched upstream integration-suite structure and realistic `tools_stress_test.go` with large coding-agent prompt/tool catalogs, cache reuse and multi-turn tool-result continuation.
- Derived ACL fixture pattern: realistic coding-agent stress, prompt-cache reuse, continuation and realized GPU-load preconditions rather than toy-only tool tests.
- Wrote detailed evidence, candidate invariants, regression fixtures, source inventory and explicit non-conclusions to `projects/ollama.md`.
- Preserved task boundary: no Letta Code research, cross-project winner selection, benchmark execution, architecture redesign or worker/model execution was begun.

## Highest-value Ollama findings for later comparison
1. Ollama is a behavior-bearing runtime layer above the model; exact Ollama/engine/artifact/config/harness identity matters.
2. Current Ollama uses a pinned **and compatibility-patched** llama.cpp, not pristine upstream source.
3. MLX is a separate engine profile with different implemented capabilities.
4. Immutable manifest/layer/model/template identity is stronger benchmark evidence than a mutable model tag.
5. Current automatic context can be only 4K below 24 GiB VRAM; agent/coding guidance recommends at least 64K.
6. Benchmark context must be explicit and realized context must be observed, not inferred.
7. Runtime truncation/context shifting is separate from harness compaction and model memory failure.
8. KV type, flash attention, parallelism and memory-fit/offload settings are deployment identity fields.
9. Realized full-GPU versus CPU-offloaded execution is a distinct benchmark profile.
10. Scheduler resource transitions require explicit states and hard deadlines; #17408 is a concrete deadlock fixture.
11. Runtime health should prove cold-load/scheduler functionality, not only HTTP or already-loaded inference.
12. Capability metadata/template heuristics are discovery inputs, not verified end-to-end capability.
13. Native Ollama tool schema currently loses parts of JSON Schema; original ACL schemas must remain authoritative.
14. Generated tool arguments require host-side validation even when a schema was supplied to Ollama.
15. Structured-output constraints and ordinary tool-call schemas are different paths with different guarantees.
16. Capability combinations such as tools + structured output need direct tests.
17. Native Ollama, OpenAI-compatible adapter and consuming harness/client are separately versioned capability surfaces.
18. `Ollama` no longer automatically means local/offline; cloud/remote mode must be explicit and policy-controlled.
19. Loopback is part of the default service trust boundary; remote binding needs an outer auth/network boundary.
20. Request-replay logs are valuable but sensitive evidence.
21. Upstream coding-agent-like stress tests provide useful fixture patterns, but ACL still needs independent validators.
22. Runtime/adapter/schema/compiler/scheduler/hardware/harness failures should be classified separately from model failures.
23. Ollama is a candidate inference service, not ACL's scheduler, worker sandbox, effect ledger, checkpoint manager, credential broker or verifier.

## Queue status
- **Pydantic AI (#1): complete.**
- **Cline (#2): complete.**
- **LangGraph (#3): complete.**
- **promptfoo (#4): complete.**
- **Strands Harness SDK (#5): complete.**
- **Codex (#6): complete.**
- **OpenHands (#7): complete.**
- **SWE-agent / mini-swe-agent (#8): complete.**
- **llama.cpp (#9): complete.**
- **OpenAI Agents SDK (#10): complete.**
- **Model Context Protocol (#11): complete.**
- **Goose (#12): complete.**
- **Ollama (#13): complete.** Detailed evidence: `projects/ollama.md`.
- **Letta Code (#14): next task only.** No Letta Code deep research was begun in Task 17.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **Letta Code** only.

Do not begin until separately instructed. When begun, inspect the canonical `letta-ai/letta-code` project and directly relevant upstream lineage only as needed to understand current identity. Focus on its stateful-agent/memory architecture, conversation/project/runtime boundaries, persistence and memory provenance, context management, local/provider compatibility, tools/permissions/execution boundaries, lifecycle/recovery, evaluation/observability, current failure surfaces and reusable ACL/Vera mechanisms. Save report/catalog/state/watchlist, make a research-only commit, and **stop before Gemini CLI**.

## Later tasks
1. Letta Code, then the remaining ranked active-project queue one task at a time.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after individual work is complete.

## Stop point

Task 17 ended after current Ollama engine identity, model packaging, context/KV/resource scheduling, hardware backends, API/local-cloud boundaries, tool/structured-output semantics, process/network lifecycle, reproducibility/evaluation and current failure surfaces were researched. No Letta Code/Gemini CLI research, cross-project winner selection, dependency decision, benchmark execution, ACL/Vera architecture/governance change or worker/model execution was begun.
