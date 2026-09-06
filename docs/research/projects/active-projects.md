# Active Projects — Task 2

**Accessed:** 2026-09-05  
**Task:** Find active people and projects relevant to ACL and future Vera work.  
**Status:** identification only; **no ranking is implied by inclusion or ordering**.

## Method

This task uses a conservative activity test. A project is listed as **confirmed active** when its canonical upstream repository is not archived/disabled and shows substantive upstream activity within roughly the last 90 days, with preference for projects active in the last 30 days. Repository `updated_at`, stars, forks, and general popularity are not sufficient by themselves; the primary signal is recent code/documentation/release activity in the canonical upstream.

The task intentionally does **not** answer whether a project is good, safe, locally compatible, reusable, healthy enough to depend on, or superior to another project. Those are ranking/deep-research questions reserved for later tasks.

Repository moves and renames are treated as identity changes, not as evidence of failure. Where an older seed project did not meet the recent-activity threshold, it is recorded separately as **status deferred** without investigating why.

## Confirmed active projects

### Coding agents / coding harnesses

#### Cline — `cline/cline`
- **Observed activity:** pushed 2026-09-05; current commits include apply-patch overwrite protection and CLI fixes.
- **Observed scope:** autonomous coding agent available as IDE/CLI/SDK.
- **ACL/Vera relevance:** file-operation safety, approval UX, model routing, MCP/tool use, and agent edit semantics.
- **Warning / later question:** end-user product scope differs from ACL's bounded worker-lab architecture.
- **Primary source:** https://github.com/cline/cline

#### Codex — `openai/codex`
- **Observed activity:** pushed 2026-09-05/06 UTC.
- **Observed scope:** terminal coding agent implemented primarily in Rust.
- **ACL/Vera relevance:** sandbox/approval/tooling architecture, terminal workflow, and coding-agent reliability patterns.
- **Warning / later question:** provider/product assumptions may differ from ACL's local-first worker requirements.
- **Primary source:** https://github.com/openai/codex

#### Gemini CLI — `google-gemini/gemini-cli`
- **Observed activity:** pushed 2026-09-05/06 UTC; current commits include workspace-boundary, symlink, permission, and environment-safety fixes.
- **Observed scope:** open-source terminal AI agent.
- **ACL/Vera relevance:** filesystem boundaries, command safety, extension permissions, ownership checks, and MCP integration.
- **Warning / later question:** Google-specific provider/product choices may not transfer to local-model workers.
- **Primary source:** https://github.com/google-gemini/gemini-cli

#### Goose — `aaif-goose/goose`
- **Observed activity:** pushed 2026-09-05; current commits include MCP-version and model-provider support.
- **Observed scope:** extensible agent that can install, execute, edit, and test with multiple LLMs.
- **ACL/Vera relevance:** extensibility, MCP integration, provider abstraction, developer-kit boundaries, and tool execution.
- **Warning / later question:** canonical repository moved from `block/goose` to `aaif-goose/goose`; stale paths should not be treated as a separate current project.
- **Primary source:** https://github.com/aaif-goose/goose

#### OpenCode — `anomalyco/opencode`
- **Observed activity:** pushed 2026-09-05/06 UTC; multiple current commits across agent/provider/console surfaces.
- **Observed scope:** open-source coding agent.
- **ACL/Vera relevance:** terminal-agent UX, provider abstraction, permissions, and high-velocity integration behavior.
- **Warning / later question:** the older `opencode-ai/opencode` repository is not the current canonical project.
- **Primary source:** https://github.com/anomalyco/opencode

#### OpenHands — `OpenHands/OpenHands`
- **Observed activity:** pushed 2026-09-05; current work includes model-provider configuration, CI/evidence policy, telemetry, and repository-boundary changes.
- **Observed scope:** AI-driven software-development agent/harness.
- **ACL/Vera relevance:** task lifecycle, model-provider abstraction, validation/evidence, and sandbox/runtime boundaries.
- **Warning / later question:** high activity does not establish local-model reliability or safe autonomy.
- **Primary source:** https://github.com/OpenHands/OpenHands

#### SWE-agent — `SWE-agent/SWE-agent`
- **Observed activity:** pushed 2026-08-31; recurring 2026 fixes cover evaluation mappings, multimodal handling, CLI parsing, and regression tests.
- **Observed scope:** software-engineering agent that attempts repository issue resolution.
- **ACL/Vera relevance:** minimal harness design, SWE-bench integration, model/tool interfaces, and deterministic regression behavior.
- **Warning / later question:** recent activity is lower-volume than some peers; activity alone does not imply benchmark leadership.
- **Primary source:** https://github.com/SWE-agent/SWE-agent

### Agent frameworks / orchestration / harnesses

#### Agno — `agno-agi/agno`
- **Observed activity:** pushed 2026-09-05.
- **Observed scope:** framework/platform for building and operating agent systems.
- **ACL/Vera relevance:** agent/team/workflow organization, runtime operations, and model/provider abstraction.
- **Warning / later question:** broad platform scope may exceed ACL's desired bounded-worker architecture.
- **Primary source:** https://github.com/agno-agi/agno

#### CrewAI — `crewAIInc/crewAI`
- **Observed activity:** pushed 2026-09-04; current fixes include streaming tool-call argument handling.
- **Observed scope:** multi-agent orchestration framework.
- **ACL/Vera relevance:** role/task decomposition, tool argument handling, crews/flows, and multi-agent coordination failure modes.
- **Warning / later question:** feature breadth is not evidence that multi-agent decomposition improves ACL outcomes.
- **Primary source:** https://github.com/crewAIInc/crewAI

#### Google ADK — `google/adk-python`
- **Observed activity:** pushed 2026-09-05; current commits cover state serialization, multiple-candidate handling, tool callbacks, and tool-list failures.
- **Observed scope:** code-first Python agent development kit.
- **ACL/Vera relevance:** session/state handling, callbacks, tool contracts, evaluation/deployment interfaces, and provider behavior.
- **Warning / later question:** some development flows through Google's internal mirror/Copybara, so GitHub attribution can be indirect.
- **Primary source:** https://github.com/google/adk-python

#### LangGraph — `langchain-ai/langgraph`
- **Observed activity:** pushed 2026-09-05/06 UTC; current 2026 work includes v3 streaming, remote graph lifecycle, checkpoints/projections, and releases.
- **Observed scope:** resilient agent runtime / graph orchestration framework.
- **ACL/Vera relevance:** durable state, checkpoints, interruptions, streaming, subgraphs, remote execution, and recovery semantics.
- **Warning / later question:** broad framework surface can add complexity ACL may not need.
- **Primary source:** https://github.com/langchain-ai/langgraph

#### LlamaIndex — `run-llama/llama_index`
- **Observed activity:** pushed 2026-09-05.
- **Observed scope:** agent/data framework with document, RAG, and multi-agent components.
- **ACL/Vera relevance:** future Vera retrieval/memory/data interfaces and agent tool/data orchestration.
- **Warning / later question:** large data/RAG surface is adjacent to, not identical with, ACL coding-worker needs.
- **Primary source:** https://github.com/run-llama/llama_index

#### Mastra — `mastra-ai/mastra`
- **Observed activity:** pushed 2026-09-05/06 UTC.
- **Observed scope:** TypeScript agent/application framework with workflows, evals, and MCP support.
- **ACL/Vera relevance:** workflow/eval integration and developer observability.
- **Warning / later question:** TypeScript-first ecosystem differs from ACL's current Python-centric experimentation.
- **Primary source:** https://github.com/mastra-ai/mastra

#### Microsoft Agent Framework — `microsoft/agent-framework`
- **Observed activity:** pushed 2026-09-05; Microsoft repository metadata marks `activeRepoStatus=true`.
- **Observed scope:** Python/.NET framework for building, orchestrating, and deploying agents and multi-agent workflows.
- **ACL/Vera relevance:** orchestration contracts, enterprise lifecycle, multi-agent routing, and deployment boundaries.
- **Warning / later question:** enterprise-framework constraints differ from a small local lab.
- **Primary source:** https://github.com/microsoft/agent-framework

#### OpenAI Agents SDK — `openai/openai-agents-python`
- **Observed activity:** pushed 2026-09-05; current commits cover route verification, CI, realtime tests, and repository skills.
- **Observed scope:** lightweight Python framework for multi-agent workflows.
- **ACL/Vera relevance:** handoffs, tool contracts, tracing, guardrails, realtime lifecycle, and test discipline.
- **Warning / later question:** provider-specific features may not map directly to ACL's local models.
- **Primary source:** https://github.com/openai/openai-agents-python

#### Pydantic AI — `pydantic/pydantic-ai`
- **Observed activity:** pushed 2026-09-05; current commits include concurrency guidance and realtime interruption/cancellation fixes.
- **Observed scope:** typed Python agent framework/harness.
- **ACL/Vera relevance:** strict tool schemas, typed structured output, dependency injection, retries, async/concurrency, and lifecycle handling.
- **Warning / later question:** strong typing does not substitute for permission or semantic validation.
- **Primary source:** https://github.com/pydantic/pydantic-ai

#### smolagents — `huggingface/smolagents`
- **Observed activity:** pushed 2026-08-25.
- **Observed scope:** minimal agent library centered on agents acting through code/tools.
- **ACL/Vera relevance:** small-framework counterpoint for deciding how much harness ACL actually needs.
- **Warning / later question:** minimalism can shift safety/reliability responsibility onto prompts/models.
- **Primary source:** https://github.com/huggingface/smolagents

#### Strands Harness SDK — `strands-agents/harness-sdk`
- **Observed activity:** pushed 2026-09-04; canonical repository resolves from the former `sdk-python` path.
- **Observed scope:** agent harness SDK for Python/TypeScript with model/provider flexibility.
- **ACL/Vera relevance:** directly relevant to custom-harness-versus-framework decisions and explicit harness control.
- **Warning / later question:** track the canonical move so stale `sdk-python` links are not treated as a separate project.
- **Primary source:** https://github.com/strands-agents/harness-sdk

### Persistent state / memory

#### Graphiti — `getzep/graphiti`
- **Observed activity:** pushed 2026-09-04.
- **Observed scope:** real-time knowledge graph framework for agent memory/context.
- **ACL/Vera relevance:** temporal/graph memory, fact evolution, provenance, and retrieval for future Vera.
- **Warning / later question:** knowledge-graph complexity may be unnecessary unless Vera's requirements justify it.
- **Primary source:** https://github.com/getzep/graphiti

#### Letta Code — `letta-ai/letta-code`
- **Observed activity:** pushed 2026-09-05/06 UTC; active repository discovered alongside the older Letta server repository.
- **Observed scope:** stateful agents emphasizing memory, identity, learning, and adaptation.
- **ACL/Vera relevance:** high-value future Vera comparison for persistent identity/memory plus coding-agent behavior.
- **Warning / later question:** do not infer migration history or architectural superiority from repository movement; transition analysis belongs to a later task.
- **Primary source:** https://github.com/letta-ai/letta-code

#### Mem0 — `mem0ai/mem0`
- **Observed activity:** pushed 2026-09-04; recurring current release/documentation/core-configuration work.
- **Observed scope:** memory layer for AI agents and assistants.
- **ACL/Vera relevance:** memory CRUD, persistence, retrieval, scoping, user/session identity, and integrations.
- **Warning / later question:** memory usefulness does not establish memory integrity; poisoning, provenance, rollback, and policy are separate concerns.
- **Primary source:** https://github.com/mem0ai/mem0

### Local-model runtime / serving / routing

#### LiteLLM — `BerriAI/litellm`
- **Observed activity:** pushed 2026-09-05/06 UTC.
- **Observed scope:** multi-provider LLM gateway/SDK with routing, logging, guardrails, cost tracking, and runtime/protocol integrations.
- **ACL/Vera relevance:** provider abstraction, fallback/routing, observability, cost accounting, and uniform API contracts.
- **Warning / later question:** gateway abstraction can mask provider-specific failure semantics; licensing/deployment terms need later verification before reuse.
- **Primary source:** https://github.com/BerriAI/litellm

#### llama.cpp — `ggml-org/llama.cpp`
- **Observed activity:** pushed 2026-09-05/06 UTC; multiple same-day backend fixes.
- **Observed scope:** C/C++ local LLM inference runtime.
- **ACL/Vera relevance:** quantization, backend support, context/KV-cache behavior, structured/tool-output plumbing, and local performance constraints.
- **Warning / later question:** fast-moving backend changes can create regressions; ACL benchmarks should pin versions.
- **Primary source:** https://github.com/ggml-org/llama.cpp

#### Ollama — `ollama/ollama`
- **Observed activity:** pushed 2026-09-05.
- **Observed scope:** local model runner/server ecosystem.
- **ACL/Vera relevance:** local-worker model loading, tool-call support, model packaging, API behavior, and regression risk.
- **Warning / later question:** convenience abstractions can hide lower-level runtime behavior; verify important issues against lower layers when applicable.
- **Primary source:** https://github.com/ollama/ollama

#### vLLM — `vllm-project/vllm`
- **Observed activity:** pushed 2026-09-05.
- **Observed scope:** high-throughput, memory-efficient LLM inference and serving engine.
- **ACL/Vera relevance:** future concurrent/server-style workers, structured output, tool support, batching, and serving semantics.
- **Warning / later question:** optimized serving architecture may be unnecessary on small single-GPU hardware.
- **Primary source:** https://github.com/vllm-project/vllm

### Evaluation / security tooling

#### promptfoo — `promptfoo/promptfoo`
- **Observed activity:** pushed 2026-09-05/06 UTC.
- **Observed scope:** LLM/agent evaluation, regression testing, red teaming, and vulnerability scanning.
- **ACL/Vera relevance:** potential reusable evaluation/red-team infrastructure for prompt/tool/security regression suites.
- **Warning / later question:** generic tests still need ACL-specific deterministic fixtures and threat models.
- **Primary source:** https://github.com/promptfoo/promptfoo

### Tool / context protocols

#### Model Context Protocol — `modelcontextprotocol/modelcontextprotocol`
- **Observed activity:** pushed 2026-09-04; active issues/discussions/specification repository.
- **Observed scope:** specification and documentation for MCP.
- **ACL/Vera relevance:** tool contracts, context/resource exposure, long-running tasks, cancellation, progress, and trust boundaries.
- **Warning / later question:** protocol compatibility is not authorization; third-party servers/tools remain untrusted boundaries.
- **Primary source:** https://github.com/modelcontextprotocol/modelcontextprotocol

## Status-deferred seed projects

These projects remain relevant enough to retain on the broader watchlist, but they did not meet this task's recent-activity threshold. This task does **not** classify them as failed, abandoned, replaced, or unhealthy; those explanations belong to the later failure/redesign task.

### Aider — `Aider-AI/aider`
- **Observed fact:** repository is not archived/disabled, but the canonical repository's last push was 2026-05-22, outside this task's recent-activity window.
- **Decision for this task:** retain as **status deferred**, not confirmed active.
- **Primary source:** https://github.com/Aider-AI/aider

### AutoGen — `microsoft/autogen`
- **Observed fact:** repository is not archived/disabled, but the canonical repository's last push was 2026-04-15; Microsoft repository metadata currently reports `activeRepoStatus=false`.
- **Decision for this task:** retain as **status deferred**, not confirmed active.
- **Primary source:** https://github.com/microsoft/autogen

## Cross-cutting observations

1. **The coding-agent field is broader than the original seed list.** Current upstream activity confirms OpenHands, SWE-agent, Cline, Goose, OpenCode, Gemini CLI, and Codex as distinct active coding-agent/harness implementations.
2. **Harness engineering is becoming an explicit category.** Pydantic AI and Strands use harness-oriented language, while other frameworks expose equivalent lifecycle/tool/state concerns through different terminology.
3. **Filesystem and tool safety are active engineering problems, not theoretical concerns.** Current Cline and Gemini CLI commits directly address destructive file overwrite, path/symlink boundaries, configuration ownership, and environment trust.
4. **Long-running lifecycle mechanics are visible in active runtime work.** LangGraph's current work on streaming, projections, remote runs, interruptions, and checkpoints is directly adjacent to ACL's long-running worker/recovery questions.
5. **Persistent memory is an active implementation lane.** Letta Code, Mem0, and Graphiti represent materially different state/memory approaches worth later comparison for Vera.
6. **Local runtime churn is high.** llama.cpp, Ollama, and vLLM continue to change rapidly; ACL benchmarks should record exact runtime/model versions rather than treating a model name as a stable result.
7. **Protocol adoption is entering concrete agent implementations.** MCP appears both as an active specification project and in active coding agents such as Goose and Gemini CLI; compatibility should still be separated from trust/authorization.

## Stop boundary

This file identifies active candidates and preserves evidence for later work. It does **not** rank them, score them, recommend adoption, analyze failures, or begin deep research on any individual project.
