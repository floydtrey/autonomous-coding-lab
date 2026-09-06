# Research Watchlist

Task 3 established the research-priority queues. Task 4 added transition/status evidence. Task 5 completed Pydantic AI deep research. Task 6 completed Cline deep research. Task 7 completed **LangGraph** deep research. Rank still means **study/watch sooner because the candidate is expected to reduce ACL/Vera uncertainty**; completed research does not convert the queue into an adoption list.

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
- `projects/langgraph.md`

## Task 7 — LangGraph research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings to carry into later comparison:

- **Stateful runtime:** LangGraph models checkpoints, pending task writes, thread/checkpoint lineage, subgraphs, interrupts, retries/timeouts and task/checkpoint/debug streams explicitly.
- **Durability modes:** `sync`, `async` and `exit` make persistence policy explicit, but durability does not establish exactly-once external effects.
- **External effects:** open issue #8039 demonstrates why a process crash between side effect and persistence can lead to node re-execution/duplicate effects; broad proposed ordering fixes #8050/#8055 were closed without merge and current main still warrants caution.
- **Interrupt identity:** concurrent human-input/approval waits need stable IDs. Open #8579 shows a scalar resume can be accepted for multiple child interrupts grouped into one subgraph task.
- **Subgraph replay:** open #8458 shows a parent fork can regenerate task identity/checkpoint namespace and silently rerun an entire subgraph instead of resuming the requested child checkpoint.
- **Authoritative hydration:** open #8653 shows a production-style config-injected checkpointer path can hydrate from the wrong saver and make `update_state` commit an incorrectly empty base state.
- **Replay inputs:** open #8582 shows an `UntrackedValue` can disappear across failure/resume while the task is still considered replayable. Required replay inputs must be persisted, reacquirable or explicitly non-replayable.
- **Runtime recovery policy:** current `RetryPolicy` and `TimeoutPolicy` support bounded retry/backoff, hard timeout, idle timeout and heartbeat semantics; cancellation remains cooperative for blocking synchronous/CPU work.
- **Retention:** open #8531 shows physical Postgres checkpoint pruning is its own lifecycle problem; Delta-style ancestry makes naive keep-latest unsafe.
- **Deletion fencing:** open #7206 shows stale late writers can resurrect deleted threads when deletion has no tombstone/generation fence.
- **Observability:** typed task/checkpoint/debug streams are useful local evidence surfaces; node `TracePolicy` explicitly is not a secret-redaction boundary.
- **Boundary:** LangGraph does not replace workspace/Git snapshots, external-effect ledgers, sandboxing, credential authority, local-model capability verification or task acceptance gates.

See `projects/langgraph.md` for primary sources, failure details, candidate invariants, ACL regression-fixture ideas and deliberately deferred comparison questions.

## Task 6 — Cline research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings retained for later comparison:
- stateless agent/model loop separated from stateful core/session ownership;
- runtime enforcement is stronger than prompt-only Plan-mode restraint but shell blacklists remain defense-in-depth;
- approval UI, model classification and execution authority are separate layers;
- embedded agent runtimes can create a second permission/tool/cwd system;
- file mutation requires authoritative execution-time state;
- checkpoint identity must survive retries/compaction/restart and restore needs fail-closed concurrency/history protection;
- local compatibility must include model + runtime + adapter + backend settings;
- deterministic recovery should prove progress and use bounded retry;
- loop/mistake detection belongs in runtime telemetry;
- long-run storage retention is separate from logical context retention.

See `projects/cline.md` for the complete evidence.

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
3. **LangGraph** — `langchain-ai/langgraph` — **Task 7 complete**; `projects/langgraph.md`.
4. **promptfoo** — `promptfoo/promptfoo` — **next task**; independent agent evaluation, deterministic trace assertions and coding-agent red teaming.
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

1. **Saoud Rizwan** — `saoudrizwan` — Cline — file/checkpoint/permission/provider safety.
2. **Nick Hollon** — `nick-hollon-lc` — LangGraph — Task 7 reinforces durable/remote runtime lifecycle, checkpoint/state and streaming as a high-signal contribution stream.
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
- Conversation/graph state, workspace state and external-effect evidence are separate recovery dimensions.
- A durable checkpoint does not imply exactly-once external side effects.
- Persistent recovery identity should not depend solely on regenerated ephemeral task IDs.
- Human approval/input must bind to stable request IDs; ambiguous concurrent resume should fail closed.
- Replayable tasks require persisted or deterministically reacquirable inputs.
- State mutation must hydrate and commit against one authoritative state source/version.
- Retry, timeout and cancellation policies belong in observable runtime behavior.
- Deletion needs generation/tombstone fencing against stale writers.
- Physical persistence retention is separate from model-context compaction.
- Restore/checkpoint operations are themselves destructive/concurrent operations and need fail-closed preconditions.
- Current bugs/regression fixes can be more valuable than feature lists because they expose actual failure surfaces.
- Preserve architecture generations and canonical aliases separately so migrations remain auditable.

## Next research task boundary

Task 7 is complete once the LangGraph research file, catalog, watchlist and state are committed. The next task is **promptfoo deep research only**. Do not begin it until separately instructed, and when it is begun, stop before Strands Harness SDK.
