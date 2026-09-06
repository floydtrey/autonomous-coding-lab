# Research Watchlist

This watchlist now contains:
1. **confirmed-active project candidates** identified in Task 2;
2. **confirmed recurring contributors** identified in Task 2;
3. **status-deferred seed projects** that remain relevant but did not meet the Task 2 recent-activity threshold; and
4. the recurring **source channels** established by Task 1.

Everything remains deliberately **unranked**. Ordering is by category/name, not priority.

## Confirmed-active coding agents / harnesses — Task 2
- Cline — `cline/cline`
- Codex — `openai/codex`
- Gemini CLI — `google-gemini/gemini-cli`
- Goose — `aaif-goose/goose`
- OpenCode — `anomalyco/opencode`
- OpenHands — `OpenHands/OpenHands`
- SWE-agent — `SWE-agent/SWE-agent`

## Confirmed-active agent runtimes / orchestration / harnesses — Task 2
- Agno — `agno-agi/agno`
- CrewAI — `crewAIInc/crewAI`
- Google ADK — `google/adk-python`
- LangGraph — `langchain-ai/langgraph`
- LlamaIndex — `run-llama/llama_index`
- Mastra — `mastra-ai/mastra`
- Microsoft Agent Framework — `microsoft/agent-framework`
- OpenAI Agents SDK — `openai/openai-agents-python`
- Pydantic AI — `pydantic/pydantic-ai`
- smolagents — `huggingface/smolagents`
- Strands Harness SDK — `strands-agents/harness-sdk`

## Confirmed-active memory / persistent-state candidates — Task 2
- Graphiti — `getzep/graphiti`
- Letta Code — `letta-ai/letta-code`
- Mem0 — `mem0ai/mem0`

## Confirmed-active local-model runtime / serving / routing candidates — Task 2
- LiteLLM — `BerriAI/litellm`
- llama.cpp — `ggml-org/llama.cpp`
- Ollama — `ollama/ollama`
- vLLM — `vllm-project/vllm`

## Confirmed-active evaluation / security / protocol candidates — Task 2
- Model Context Protocol — `modelcontextprotocol/modelcontextprotocol`
- promptfoo — `promptfoo/promptfoo`

## Confirmed recurring contributors — Task 2
- Anas Khan — `anxkhn` — SWE-agent
- Douwe Maan — `DouweM` — Pydantic AI
- Graham Neubig — `neubig` — OpenHands
- Jack Amadeo — `jamadeo` — Goose
- Jesús Samuel — `jesussamuel-byte` — Gemini CLI
- Johannes Gäßler — `JohannesGaessler` — llama.cpp
- Kartik Labhshetwar — `kartik-mem0` — Mem0
- Kazuhiro Sera — `seratch` — OpenAI Agents SDK
- Nick Hollon — `nick-hollon-lc` — LangGraph
- Saoud Rizwan — `saoudrizwan` — Cline

See `projects/active-projects.md` and `people/active-people.md` for the activity evidence and ACL/Vera relevance.

## Status-deferred seed projects

These remain on the broad watchlist but were **not** classified as confirmed active in Task 2. No failure/abandonment conclusion is implied.

- Aider — `Aider-AI/aider` — canonical repo not archived, but last push observed 2026-05-22.
- AutoGen — `microsoft/autogen` — canonical repo not archived, but last push observed 2026-04-15; Microsoft metadata reports `activeRepoStatus=false`.

The reasons, transition history, or successor relationships are intentionally **not** investigated here. That belongs to the later failed/abandoned/redesigned-attempts task.

## Security / governance sources already established
- OWASP AI Agent Security Cheat Sheet
- OWASP Agent Memory Guard
- OWASP GenAI Security Project / Agentic Security Initiative
- MITRE ATLAS
- NIST AI / Agentic AI guidance

## Recurring source watch stack — mapped in Task 1

### Core / primary
- Upstream GitHub releases, changelogs, advisories, issues, discussions, and selected PRs for watched projects.
- arXiv recent feeds: cs.SE, cs.MA, cs.CR; cs.AI as a cross-list/search overflow.
- Hugging Face function-calling model filter and Daily Papers.
- SWE-bench official leaderboards/news.
- Berkeley Function Calling Leaderboard (BFCL) and changelog.
- OWASP GenAI Security Project and Agentic Security Initiative.
- MITRE ATLAS machine-readable data releases.
- GitHub Advisory Database and OSV.
- NIST AI and Agentic AI pages.
- Model Context Protocol specification/upstream repository.
- Agent2Agent protocol specification/upstream repository.
- OpenTelemetry GenAI semantic-conventions repository.

### Discovery only; verify upstream
- r/LocalLLaMA
- Hacker News
- Hugging Face Forums
- publicly searchable project Discord/forum discussions

### Low priority
- generic AI news aggregation
- GitHub Trending/Topics without follow-up verification
- vendor marketing without primary technical evidence
- social accounts without an attributable current contribution stream

See `sources.md` for cadence, evidence, caveats, and the evidence ladder.

## Questions reserved for the next task: ranking

Do **not** answer these until the ranking task is separately started:
- Which confirmed-active projects deserve the highest watch priority for ACL?
- Which people produce the highest-value recurring technical signal?
- Does a project support local/open models in practice, not merely in documentation?
- How does it handle tool contracts and malformed model output?
- Who owns workflow control: model or harness?
- How are state, checkpoints, retries, cancellation, and recovery handled?
- How are sandboxes, filesystem/network boundaries, and secrets handled?
- How is success independently validated?
- What failures recur in issues/discussions?
- Is there a reusable component that would save ACL work?
- Is the project healthy enough to watch, contribute to, fork, or collaborate with?

## Stop boundary

Task 2 identified active projects and recurring contributors. It did not rank any candidate, analyze failed attempts, recommend adoption, or begin deep research on an individual project/person.
