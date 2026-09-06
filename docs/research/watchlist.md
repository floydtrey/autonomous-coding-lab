# Research Watchlist

Task 3 converts the Task 2 active set into a **research-priority queue**. Rank means **study/watch sooner because the candidate is expected to reduce ACL/Vera uncertainty**. It does not mean best product, safest framework, strongest benchmark result, or recommended dependency.

Detailed rationale and evidence:
- `projects/ranked-projects.md`
- `people/ranked-people.md`
- `ranked-sources.md`

The original Task 2 activity evidence remains in:
- `projects/active-projects.md`
- `people/active-people.md`

## Ranked active-project queue — Task 3

### Tier A — immediate deep-research queue
1. **Pydantic AI** — `pydantic/pydantic-ai` — typed tool/schema contracts, retry/concurrency, concrete Ollama support.
2. **Cline** — `cline/cline` — coding-agent edit safety, local models, approvals/runtime/provider seams.
3. **LangGraph** — `langchain-ai/langgraph` — checkpoints, retries, interruption/resume, durability and remote lifecycle.
4. **promptfoo** — `promptfoo/promptfoo` — independent agent evaluation, deterministic trace assertions and coding-agent red teaming.
5. **Strands Harness SDK** — `strands-agents/harness-sdk` — explicit harness interfaces, structured-output validation/retry, Ollama support.
6. **Codex** — `openai/codex` — sandbox/approval policies, command authority, child-agent permission inheritance, Ollama integration.
7. **OpenHands** — `OpenHands/OpenHands` — coding-agent runtime/sandbox, evidence policy, telemetry and provider abstraction.
8. **SWE-agent** — `SWE-agent/SWE-agent` — minimal coding harness, evaluation correctness, regression discipline and local Ollama path.
9. **llama.cpp** — `ggml-org/llama.cpp` — local runtime, constrained JSON/tool-call grammars, parsers, backend/KV behavior.
10. **OpenAI Agents SDK** — `openai/openai-agents-python` — serializable run state, approvals, sandbox state, traces and lifecycle tests.

### Tier B — high-value follow-up
11. **Model Context Protocol** — `modelcontextprotocol/modelcontextprotocol`
12. **Goose** — `aaif-goose/goose`
13. **Ollama** — `ollama/ollama`
14. **Letta Code** — `letta-ai/letta-code`
15. **Gemini CLI** — `google-gemini/gemini-cli`
16. **Graphiti** — `getzep/graphiti`
17. **Microsoft Agent Framework** — `microsoft/agent-framework`
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

## Ranked recurring-contributor queue — Task 3

This ranks **public technical signal**, not authority, seniority, employment status, or outreach priority.

1. **Saoud Rizwan** — `saoudrizwan` — Cline — file-operation safety/edit semantics/provider routing.
2. **Nick Hollon** — `nick-hollon-lc` — LangGraph — durable/remote runtime lifecycle and streaming state.
3. **Jesús Samuel** — `jesussamuel-byte` — Gemini CLI — path/symlink/configuration authorization and command safety.
4. **Graham Neubig** — `neubig` — OpenHands — provider/evidence/repository-boundary and lifecycle decisions.
5. **Johannes Gäßler** — `JohannesGaessler` — llama.cpp — local runtime backends, quantization/KV and multi-device behavior.
6. **Douwe Maan** — `DouweM` — Pydantic AI — cancellation/concurrency/session lifecycle.
7. **Anas Khan** — `anxkhn` — SWE-agent — harness/evaluation correctness and regression discipline.
8. **Kazuhiro Sera** — `seratch` — OpenAI Agents SDK — verification, CI and realtime lifecycle testing.
9. **Jack Amadeo** — `jamadeo` — Goose — MCP/GDK integration and packaging.
10. **Kartik Labhshetwar** — `kartik-mem0` — Mem0 — memory release/integration/configuration signal.

## Ranked recurring source queue — Task 3

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

## Status-deferred seed projects — excluded from active ranking

These remain relevant but were **not ranked with the confirmed-active set**. No failure/abandonment/replacement conclusion is implied.

- **Aider** — `Aider-AI/aider` — canonical repo not archived, last push observed 2026-05-22.
- **AutoGen** — `microsoft/autogen` — canonical repo not archived, last push observed 2026-04-15; Microsoft metadata reports `activeRepoStatus=false`.

The reasons, transition history, successor relationships and lessons are intentionally reserved for the next task: **find failed, abandoned, or heavily redesigned attempts**.

## Security / governance anchors retained regardless of ordinal source rank

- OWASP AI Agent Security Cheat Sheet
- OWASP Agent Memory Guard
- OWASP GenAI Security Project / Agentic Security Initiative
- MITRE ATLAS
- NIST AI / Agentic AI guidance

These can become controlling sources for a specific security/governance question even when another source has a higher routine-watch rank.

## Ranking rules to preserve in later work

- Rank is **information value**, not adoption preference.
- Local-model support increases relevance but does not prove reliable tool use.
- A broad framework loses priority when a narrower project exposes the same hard problem more clearly.
- Current bug fixes and regression tests can be more valuable than feature lists because they reveal real failure surfaces.
- The queue can change after project-by-project deep research produces stronger evidence.
- Do not infer project health, failure cause, maintainer authority, collaboration fit, or architectural superiority from ordinal position alone.

## Stop boundary

Task 3 is complete once the active projects, recurring contributors, and recurring source channels are ranked and documented. It does **not** begin the next failure/redesign investigation, recommend dependencies, change ACL governance/code, run workers/models, or start individual deep research.
