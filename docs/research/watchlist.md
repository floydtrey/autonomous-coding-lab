# Research Watchlist

Task 3 established the research-priority queues. Task 4 adds **transition/status evidence** without turning the ranking into an adoption list. Rank still means **study/watch sooner because the candidate is expected to reduce ACL/Vera uncertainty**.

Detailed Task 3 ranking rationale remains in:
- `projects/ranked-projects.md`
- `people/ranked-people.md`
- `ranked-sources.md`

Task 4 transition/failure evidence is in:
- `failures/failed-redesigned-attempts.md`

The original Task 2 activity evidence remains in:
- `projects/active-projects.md`
- `people/active-people.md`

## Task 4 transition/status updates

These findings modify how later research should interpret the Task 3 queue; they do not silently rewrite Task 3's historical ranking artifact.

- **SWE-agent** — now upstream-declared **maintenance-only** and **superseded by mini-swe-agent**. The Task 3 #8 slot becomes a transition-aware historical slot: later research should compare SWE-agent's rewrites with the current mini-swe-agent architecture rather than treat legacy SWE-agent as the current endpoint.
- **OpenAI Agents SDK** — Task 3 #10 gains explicit predecessor context: OpenAI's experimental **Swarm** repository says it was replaced by the production-ready Agents SDK.
- **AutoGen** — prior status ambiguity is resolved. Upstream now explicitly places AutoGen in **maintenance mode**, says no new features/enhancements are planned, and directs new users to **Microsoft Agent Framework** as successor.
- **Aider** — remains **status unresolved**, not abandoned. The canonical repository is not archived and no authoritative maintainer statement establishes an official successor. Community concern and forks remain discovery evidence only.

## Ranked active-project queue — Task 3 snapshot

### Tier A — immediate deep-research queue
1. **Pydantic AI** — `pydantic/pydantic-ai` — typed tool/schema contracts, retry/concurrency, concrete Ollama support.
2. **Cline** — `cline/cline` — coding-agent edit safety, local models, approvals/runtime/provider seams.
3. **LangGraph** — `langchain-ai/langgraph` — checkpoints, retries, interruption/resume, durability and remote lifecycle.
4. **promptfoo** — `promptfoo/promptfoo` — independent agent evaluation, deterministic trace assertions and coding-agent red teaming.
5. **Strands Harness SDK** — `strands-agents/harness-sdk` — explicit harness interfaces, structured-output validation/retry, Ollama support.
6. **Codex** — `openai/codex` — sandbox/approval policies, command authority, child-agent permission inheritance, Ollama integration.
7. **OpenHands** — `OpenHands/OpenHands` — coding-agent runtime/sandbox, evidence policy, telemetry and provider abstraction.
8. **SWE-agent** — `SWE-agent/SWE-agent` — **historical/transition-aware after Task 4; superseded by mini-swe-agent**.
9. **llama.cpp** — `ggml-org/llama.cpp` — local runtime, constrained JSON/tool-call grammars, parsers, backend/KV behavior.
10. **OpenAI Agents SDK** — `openai/openai-agents-python` — serializable run state, approvals, sandbox state, traces and lifecycle tests; predecessor Swarm documented in Task 4.

### Tier B — high-value follow-up
11. **Model Context Protocol** — `modelcontextprotocol/modelcontextprotocol`
12. **Goose** — `aaif-goose/goose`
13. **Ollama** — `ollama/ollama`
14. **Letta Code** — `letta-ai/letta-code`
15. **Gemini CLI** — `google-gemini/gemini-cli`
16. **Graphiti** — `getzep/graphiti`
17. **Microsoft Agent Framework** — `microsoft/agent-framework` — also confirmed AutoGen successor context from Task 4.
18. **Google ADK** — `google/adk-python`
19. **LiteLLM** — `BerriAI/litellm`
20. **vLLM** — `vllm-project/vllm`

### Tier C — comparative / situational watch
21. **OpenCode** — `anomalyco/opencode`
22. **Mem0** — `mem0ai/mem0`
23. **smolagents** — `huggingface/smolagents`
24. **Agno** — `agno-agi/agno`
25. **LlamaIndex** — `run-llama/llama_index`
26. **CrewAI** — `crewAIInc/crewAI`
27. **Mastra** — `mastra-ai/mastra`

## Ranked recurring-contributor queue — Task 3 snapshot

This ranks **public technical signal**, not authority, seniority, employment status, or outreach priority.

1. **Saoud Rizwan** — `saoudrizwan` — Cline — file-operation safety/edit semantics/provider routing.
2. **Nick Hollon** — `nick-hollon-lc` — LangGraph — durable/remote runtime lifecycle and streaming state.
3. **Jesús Samuel** — `jesussamuel-byte` — Gemini CLI — path/symlink/configuration authorization and command safety.
4. **Graham Neubig** — `neubig` — OpenHands — provider/evidence/repository-boundary and lifecycle decisions.
5. **Johannes Gäßler** — `JohannesGaessler` — llama.cpp — local runtime backends, quantization/KV and multi-device behavior.
6. **Douwe Maan** — `DouweM` — Pydantic AI — cancellation/concurrency/session lifecycle.
7. **Anas Khan** — `anxkhn` — SWE-agent — harness/evaluation correctness and regression discipline; later people research should account for the SWE-agent→mini-swe-agent transition.
8. **Kazuhiro Sera** — `seratch` — OpenAI Agents SDK — verification, CI and realtime lifecycle testing.
9. **Jack Amadeo** — `jamadeo` — Goose — MCP/GDK integration and packaging.
10. **Kartik Labhshetwar** — `kartik-mem0` — Mem0 — memory release/integration/configuration signal.

## Ranked recurring source queue — Task 3 snapshot

1. Upstream GitHub repositories
2. OWASP GenAI Security Project / Agentic Security Initiative
3. SWE-bench + Berkeley Function Calling Leaderboard (BFCL)
4. arXiv cs.SE / cs.MA / cs.CR recent feeds
5. Model Context Protocol specification + upstream repository
6. Hugging Face function-calling model filter + Daily Papers
7. GitHub Advisory Database + OSV
8. MITRE ATLAS
9. NIST AI / Agentic AI
10. OpenTelemetry GenAI semantic conventions
11. Agent2Agent (A2A) protocol
12. r/LocalLLaMA
13. Hugging Face Forums
14. Hacker News
15. Public project Discords / chat communities

`sources.md` remains the governing evidence ladder; `ranked-sources.md` only sets review priority.

## Historical failure/redesign set — Task 4

These are research cases, **not a list of failed ideas**. The classification follows upstream evidence.

1. **AutoGen** — ground-up v0.4 rewrite, then maintenance-only with Microsoft Agent Framework named successor.
2. **SWE-agent** — near-total 1.0 rewrite, then maintenance-only with mini-swe-agent named successor.
3. **OpenAI Swarm** — experimental/educational predecessor explicitly replaced by OpenAI Agents SDK.
4. **AutoGPT Classic** — unsupported legacy experiment; maintained AutoGPT direction is block/workflow Platform architecture.
5. **BabyAGI original** — archived snapshot; project materially reconceived around a self-building function framework.
6. **GPT-Engineer** — owner-archived open-source experimentation CLI / precursor to managed Lovable direction.
7. **GPT Pilot** — explicitly unmaintained; upstream documents a credential-stealing supply-chain compromise that remained unnoticed for months because the repository was no longer actively maintained.
8. **AgentGPT** — owner-archived/read-only; no authoritative cause or successor explanation found.

See `failures/failed-redesigned-attempts.md` for facts, causal boundaries, sources and ACL/Vera lessons.

## Status unresolved

- **Aider** — `Aider-AI/aider` — not archived; last canonical activity observed 2026-05-22. Community issue/fork activity indicates maintenance concern but does not establish abandonment or an official successor. Recheck only on authoritative status change.

## Explicit non-failure identity controls

- **OpenDevin → OpenHands** — canonical rename/continuity; current OpenHands is active.
- **Block Goose → AAIF Goose** — organization/governance migration with active development; not abandonment.

These controls prevent repository moves and organization changes from being mislabeled project failures.

## Security / governance anchors retained regardless of ordinal source rank

- OWASP AI Agent Security Cheat Sheet
- OWASP Agent Memory Guard
- OWASP GenAI Security Project / Agentic Security Initiative
- MITRE ATLAS
- NIST AI / Agentic AI guidance

## Rules to preserve in later work

- Rank is **information value**, not adoption preference.
- Project maintenance state is now a first-class trust signal; `archived=false` alone is insufficient.
- A redesign/successor relationship must be backed by primary evidence; do not infer causes from inactivity.
- Local-model support increases relevance but does not prove reliable tool use.
- Current bug fixes and regression tests can be more valuable than feature lists because they expose real failure surfaces.
- Preserve architecture generations and canonical aliases separately so migrations remain auditable.
- When frameworks migrate, compare behavior/evidence before and after rather than assuming semantic compatibility from API migration.

## Next research task boundary

Task 4 is complete once the transition/failure map, live status corrections, catalog and state are committed. The next task is **Pydantic AI deep research only**. Do not begin it until separately instructed, and when it is begun, stop before Cline.
