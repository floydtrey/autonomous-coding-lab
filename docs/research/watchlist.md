# Research Watchlist

Task 3 established the research-priority queues. Task 4 added transition/status evidence. Task 5 completed Pydantic AI deep research. Task 6 completed **Cline** deep research. Rank still means **study/watch sooner because the candidate is expected to reduce ACL/Vera uncertainty**; completed research does not convert the queue into an adoption list.

Detailed historical artifacts remain in:
- `projects/ranked-projects.md`
- `people/ranked-people.md`
- `ranked-sources.md`
- `failures/failed-redesigned-attempts.md`
- `projects/active-projects.md`
- `people/active-people.md`

Completed project deep research:
- `projects/pydantic-ai.md`
- `projects/cline.md`

## Task 6 — Cline research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings to carry into later comparison:

- **Architecture:** current SDK deliberately separates a stateless agent/model loop from stateful core/session ownership, persistence, compaction, telemetry, schedules and hub lifecycle.
- **Plan authority:** Cline added runtime command blocking because prompt instructions alone did not keep weaker models read-only. The current command guard explicitly remains a blacklist rather than a full shell parser, and open issue #13586 demonstrates Python-based write bypass in Plan mode.
- **Approvals:** user approval and model command classification are workflow signals, not a hard execution boundary. SDK extension tools also need explicit policy because unlisted tools can default to enabled/auto-approved.
- **Embedded runtimes:** open Claude Code-provider issue #13146 shows the risk of two tool namespaces/permission systems/cwd assumptions when one agent harness wraps another without one clear authority owner.
- **Edit safety:** `apply_patch` recently fixed an Add File path that could overwrite an existing file because the executor had not loaded target state even though the parser contained an overwrite guard.
- **Context filtering vs access:** `.clineignore` is explicitly not a security boundary. The replacement PreToolUse-hook pattern is stronger but still documents shell-parser, symlink and YOLO limitations.
- **Checkpoint semantics:** recent fixes show checkpoint correctness depends on durable turn identity across retries, compaction and restart; current snapshots capture untracked files and restoration creates recovery protection.
- **Restore safety:** checkpoint restore previously could knock newer user commits off the branch. The current fix refuses if HEAD moved and uses Git compare-and-swap to close the validation/reset race.
- **Local models:** generic OpenAI compatibility was insufficient for Ollama because it lost `num_ctx`; Cline restored a native adapter so runtime context allocation and Cline's budget agree.
- **Capability metadata:** model capabilities are explicit, but unknown/empty capability lists may intentionally fail open for some features for compatibility. ACL should choose unknown semantics explicitly per risk.
- **Context recovery:** overflow is classified, deterministically compacted, checked for actual shrinkage, retried once, and then stopped/escalated rather than blindly replayed.
- **Context durability:** compaction/migration/abort bugs show canonical transcript, provider-facing context and persisted restart state must be distinct but consistent.
- **Loop control:** runtime consecutive-mistake and identical-tool-call loop detection provides a strong alternative to putting many behavioral limits inside small-model prompts.
- **Telemetry:** structured events carry session/agent/parent/run/iteration/tool-call identity and expose tools, provider failures, compaction, mistake limits, sub-agents, timeouts and policy blocks.
- **Long-run storage:** event/checkpoint persistence needs physical retention/GC as well as logical row retention.

See `projects/cline.md` for sources, failure details, candidate invariants, ACL regression-fixture ideas and deliberately deferred comparison questions.

## Task 5 — Pydantic AI research result

**Status:** project deep research complete; no dependency/adoption decision made.

High-value findings retained for later comparison:
- typed agent/tool/output execution with explicit provider/model/profile seams;
- model/runtime capability profiles rather than endpoint compatibility assumptions;
- separate retry categories/budgets;
- validation, approval and authority as separate facts;
- fail-closed authority-bearing configuration composition;
- `StepPersistence` settled/interrupted snapshots plus `unknown_after_crash` effects;
- model-owned Planning is not authoritative project/dependency state;
- persistent memory is bounded but lower-trust on later re-entry;
- filesystem/shell application controls do not replace OS/container isolation;
- trajectory/span evaluation complements final-output checks.

See `projects/pydantic-ai.md` for the complete evidence.

## Task 4 transition/status updates

- **SWE-agent** — upstream-declared maintenance-only and superseded by mini-swe-agent. Its ranked slot is transition-aware.
- **OpenAI Agents SDK** — Swarm is its explicit experimental predecessor.
- **AutoGen** — maintenance mode; Microsoft Agent Framework is the named successor.
- **Aider** — status unresolved, not abandoned; community forks/concerns are discovery evidence only until an authoritative status change.

## Ranked active-project queue — Task 3 snapshot with live research status

### Tier A — immediate deep-research queue
1. **Pydantic AI** — `pydantic/pydantic-ai` — **Task 5 complete**; `projects/pydantic-ai.md`.
2. **Cline** — `cline/cline` — **Task 6 complete**; `projects/cline.md`.
3. **LangGraph** — `langchain-ai/langgraph` — **next task**; checkpoints, retries, interruption/resume, durability and remote lifecycle.
4. **promptfoo** — `promptfoo/promptfoo` — independent agent evaluation, deterministic trace assertions and coding-agent red teaming.
5. **Strands Harness SDK** — `strands-agents/harness-sdk` — explicit harness interfaces, structured-output validation/retry, Ollama support.
6. **Codex** — `openai/codex` — sandbox/approval policies, command authority, child-agent permission inheritance, Ollama integration.
7. **OpenHands** — `OpenHands/OpenHands` — coding-agent runtime/sandbox, evidence policy, telemetry and provider abstraction.
8. **SWE-agent** — `SWE-agent/SWE-agent` — historical/transition-aware; superseded by mini-swe-agent.
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

## Ranked recurring-contributor queue — Task 3 snapshot

This ranks public technical signal, not formal authority, seniority, employment status or outreach priority.

1. **Saoud Rizwan** — `saoudrizwan` — Cline — Task 6 reinforces file/checkpoint/permission/provider safety as a high-signal contribution stream.
2. **Nick Hollon** — `nick-hollon-lc` — LangGraph — durable/remote runtime lifecycle and streaming state.
3. **Jesús Samuel** — `jesussamuel-byte` — Gemini CLI — path/symlink/configuration authorization and command safety.
4. **Graham Neubig** — `neubig` — OpenHands — provider/evidence/repository-boundary and lifecycle decisions.
5. **Johannes Gäßler** — `JohannesGaessler` — llama.cpp — local runtime backends, quantization/KV and multi-device behavior.
6. **Douwe Maan** — `DouweM` — Pydantic AI — cancellation/concurrency/session lifecycle.
7. **Anas Khan** — `anxkhn` — SWE-agent — harness/evaluation correctness and regression discipline.
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

1. AutoGen — ground-up v0.4 rewrite, then maintenance-only with Microsoft Agent Framework named successor.
2. SWE-agent — near-total 1.0 rewrite, then maintenance-only with mini-swe-agent named successor.
3. OpenAI Swarm — experimental predecessor replaced by OpenAI Agents SDK.
4. AutoGPT Classic — unsupported legacy experiment; maintained direction moved to workflow/block Platform architecture.
5. BabyAGI original — archived snapshot; project reconceived around a self-building function framework.
6. GPT-Engineer — owner-archived experimentation CLI / precursor to managed-product direction.
7. GPT Pilot — explicitly unmaintained with an upstream-documented prolonged credential-stealing supply-chain compromise.
8. AgentGPT — owner-archived/read-only; authoritative cause/successor unresolved.

See `failures/failed-redesigned-attempts.md` for evidence and causal boundaries.

## Status unresolved

- **Aider** — `Aider-AI/aider` — not archived; no authoritative abandonment/successor declaration. Recheck only on authoritative status change.

## Explicit non-failure identity controls

- OpenDevin → OpenHands — rename/continuity; active.
- Block Goose → AAIF Goose — governance/org migration with active development.

## Security / governance anchors retained regardless of ordinal source rank

- OWASP AI Agent Security Cheat Sheet
- OWASP Agent Memory Guard
- OWASP GenAI Security Project / Agentic Security Initiative
- MITRE ATLAS
- NIST AI / Agentic AI guidance

## Rules to preserve in later work

- Rank is information value, not adoption preference.
- Deep research extracts mechanisms/invariants first; dependency/fork/build decisions remain later comparative work.
- Model instructions and role labels are not authority boundaries.
- Typed schema validation, approval and execution authority are separate concerns.
- A wrapper around another agent runtime must explicitly unify or isolate tool/permission/cwd/credential ownership.
- Unknown model/runtime capabilities need an explicit risk-based policy; local compatibility must be verified.
- Retry categories should not collapse into one generic retry count; repeated tool loops deserve execution-level detection.
- Conversation history, workspace snapshots and external side-effect evidence are separate recovery dimensions.
- Restore/checkpoint operations are themselves destructive/concurrent operations and need fail-closed preconditions.
- Authority-bearing configuration should compose explicitly and fail closed.
- Current bugs/regression fixes can be more valuable than feature lists because they expose actual failure surfaces.
- Long-running persistence needs both logical retention and physical storage bounds.
- Preserve architecture generations and canonical aliases separately so migrations remain auditable.

## Next research task boundary

Task 6 is complete once the Cline research file, catalog, watchlist and state are committed. The next task is **LangGraph deep research only**. Do not begin it until separately instructed, and when it is begun, stop before promptfoo.
