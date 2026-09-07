# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 24 — vLLM deep research complete
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
- Task 18: **Letta Code** — `projects/letta-code.md`.
- Task 19: **Gemini CLI** — `projects/gemini-cli.md`.
- Task 20: **Graphiti** — `projects/graphiti.md`.
- Task 21: **Microsoft Agent Framework** — `projects/microsoft-agent-framework.md`.
- Task 22: **Google ADK** — `projects/google-adk.md`.
- Task 23: **LiteLLM** — `projects/litellm.md`.
- Task 24: **vLLM** — `projects/vllm.md`.

## Task 24 work completed
- Began from finalized Task 23 checkpoint `7ce3afc1bd2ed8c061b27c6cc9ec95f147c1f186`.
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `watchlist.md`, and `sources.md` before research.
- Confirmed Task 24 scope as vLLM only and preserved OpenCode as Task 25 next-only.
- Pinned canonical `vllm-project/vllm` current main to `58ad1f3b8973b23943107b51230d594050b42ec3` and stable release `v0.28.0`.
- Verified Apache-2.0 license and release asset digest/provenance evidence.
- Deep-researched V1 scheduler/request/token budgets, preemption, KV manager/connectors and overlapping-batch resource-lifetime safeguards.
- Deep-researched KV capacity, GPU-memory utilization, explicit KV memory, KV dtype/offload, prefix caching and realized-context state.
- Deep-researched prefix-cache hash reproducibility, CVE-2025-46570 cache timing isolation, secret `cache_salt`, and multimodal UUID cache-integrity boundaries.
- Derived that requested `max_model_len=32768` is not measured 32K correctness/capacity.
- Retained open #54521 as a model/hardware/kernel-specific long-context determinism/corruption fixture without generalizing it to all vLLM.
- Deep-researched named/required/auto/none tool-calling modes, structured-output constraints, strict structural tags, model-specific parser/template identity and schema revalidation.
- Cross-checked open #52741 against pinned current source and retained server-only `strict` leakage into model-visible tool projection as a current-source-correlated fixture.
- Deep-researched HTTP route cancellation and retained open #55502 on stable v0.28.0 as a rerank child-engine work-after-disconnect fixture.
- Deep-researched current HTTP API-key limitations, dev/control/gRPC/media/DoS surfaces, dynamic LoRA, endpoint plugins and optional model-executed tool-server security.
- Deep-researched trusted cache-directory/artifact boundary for compile/kernel/assets/runtime caches.
- Deep-researched Windows/WSL, NVIDIA compute-capability and hardware/quantization/backend compatibility boundaries; retained #49011 as an integration-versus-underlying-kernel example.
- Deep-researched insecure-by-default distributed communications, Ray one-trust-domain semantics and driver environment propagation.
- Deep-researched experimental P/D disaggregation and retained open #49238 plus still-open #50047 as NIXL stale-peer/restart recovery fixtures.
- Deep-researched vLLM reproducibility controls and the same-hardware/same-version guarantee boundary.
- Deep-researched Prometheus scheduler/KV/token/TTFT/TPOT/prefill/decode/e2e metrics as runtime evidence separate from semantic/verifier acceptance.
- Wrote detailed findings, current/open failure matrix, 48 candidate invariants, 20 regression fixtures, reuse candidates, primary sources and explicit non-conclusions to `projects/vllm.md`.
- Prepared exactly 22 Task 24 catalog records after the 235 Task 23 records, producing 257 total records.
- No OpenCode project research, runtime/model/quantization/parser/cache/distributed choice, benchmark execution or ACL/Vera implementation was begun.

## Highest-value vLLM findings for later comparison
1. Model capability is exact model + vLLM build/profile + hardware/kernel/parser/cache/scheduler state, not weights alone.
2. `max_model_len` is requested configuration; realized KV capacity and 32K correctness must be measured.
3. #54521 shows why repeated greedy long-context threshold tests belong in the future 32K lab.
4. Named/required/auto tool modes have different constraint paths; parser/template/strict/backend identity is required.
5. #52741 shows server-control metadata and model-visible tool projection must be separately testable representations.
6. Prefix cache is both performance state and a tenant confidentiality boundary; trusted secret salts isolate sharing.
7. Caller-controlled media/cache identities can create confidentiality/integrity cross-talk in shared runtimes.
8. HTTP disconnect, handler cancellation, engine child abort and resource settlement are separate; #55502 is a concrete fixture.
9. Built-in `--api-key` is not whole-server authorization; outer route allowlisting/auth is required for exposure beyond trusted host/network.
10. Optional tool servers/plugins/LoRA/runtime controls are privileged executable/behavior authority and remain outside worker mutation authority.
11. vLLM cache roots are trusted runtime artifacts and must remain worker-unwritable.
12. Windows uses WSL/community paths rather than native vLLM; platform/backend is benchmark identity.
13. Weight quantization and KV-cache quantization are separate hardware/runtime compatibility profiles.
14. Distributed vLLM transport is insecure by default; Ray is one trust domain and driver secrets can propagate to workers.
15. P/D disaggregation is experimental, connector-specific and not throughput improvement; restart recovery requires stale-peer invalidation/re-handshake.
16. vLLM is not reproducible by default; even enabled reproducibility is scoped to same hardware and same vLLM version.
17. Prometheus runtime metrics explain performance/resource behavior but do not prove semantic correctness or ACL acceptance.
18. vLLM remains below ACL-owned task/effect identity, policy, credential, sandbox and verifier authority.

## Queue status
- Tasks 5–24 project deep research are complete through **vLLM**.
- **OpenCode (#21 in ranked active-project queue): next task only.** No OpenCode research was begun in Task 24.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **OpenCode** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant agent/harness architecture, task/session state, tool/policy/approval model, provider/local-model integration, subprocess/workspace/credential isolation, MCP/LSP/IDE surfaces, cancellation/retry/recovery, observability/evals, security/current failures, reproducibility and reusable mechanisms. Save report/catalog/state/watchlist, make a research-only commit, and stop before Mem0.

## Stop point

Task 24 ended after vLLM's current identity/release, V1 scheduler, KV/cache/context, structured output/tool parsing, cancellation, platform/quantization, distributed/P-D, security, reproducibility and observability were deeply researched. No OpenCode research, cross-project winner selection, model/runtime assignment, 32K benchmark execution or ACL/Vera implementation/governance change was begun.
