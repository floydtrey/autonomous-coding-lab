# Research Watchlist

Task 3 established the research-priority queues. Task 4 added transition/status evidence. Tasks 5–9 completed deep research on Pydantic AI, Cline, LangGraph, promptfoo, and **Strands Harness SDK**. Rank still means **study/watch sooner because the candidate is expected to reduce ACL/Vera uncertainty**; completed research does not convert the queue into an adoption list.

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
- `projects/promptfoo.md`
- `projects/strands-harness-sdk.md`

## Task 9 — Strands Harness SDK research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings to carry into later comparison:

- **Composable control planes:** Strands keeps a model-driven loop while lifecycle limits, retries, interventions, authorization, interrupts, sandbox routing, persistence, context management and telemetry live in separable runtime layers.
- **Runtime lifecycle:** turn/token limits and explicit stop reasons are runtime state rather than prompt instructions; cancellation remains cooperative at some model/tool/process boundaries and needs explicit settlement evidence.
- **Invocation identity:** safe default invocation ownership prevents one agent from mutating one conversation concurrently; Python idempotency tokens show a useful duplicate-request pattern, but process-local ownership does not solve distributed session writers.
- **Retry taxonomy:** provider throttling retry, structured-output correction and intervention/Guide retry are different mechanisms. Guide-triggered retry has no framework-imposed cap, so convergence and retry budgets remain application responsibilities.
- **Tool contracts:** schema publication and runtime validation strength differ by path (for example TypeScript Zod versus plain JSON Schema). Schema, validation, authorization and execution must remain separate facts.
- **Structured output:** schema failures are returned as concrete tool feedback so the model can self-correct in the normal agent loop rather than through an opaque parser/guesser.
- **Typed interventions:** `Proceed`, `Deny`, `Guide`, `Confirm` and `Transform` provide explicit composable decisions; handler failure mode can be fail-open or fail-closed and therefore belongs in the trust model.
- **Deterministic authorization:** shipped Python Cedar authorization runs before tool calls, resolves the principal, can inspect tool arguments/runtime context, maintains call-count state and denies on missing identity, policy evaluation error, no-decision or explicit refusal.
- **Objective integrity remains separate:** open goal-fencing issue #3877 highlights that individually authorized actions do not prove the run still serves the principal-approved objective.
- **Sandbox boundary:** with a sandbox, shell/file operations route to Docker, SSH or a custom backend while the agent core stays trusted; without a sandbox those operations run on the host with the agent process's full authority.
- **Environment lifecycle is external:** Strands does not create Docker containers for `DockerSandbox`; mounts, network, credentials, user, resource quotas, cleanup and verification remain application-owned.
- **SSH hardening:** built-in SSH option allowlisting blocks unsafe host-command directives unless an explicit unsafe bypass is enabled.
- **File/process correctness:** recent file-editor fix #4014 preserves untouched bytes/line endings/tabs, while open #4156 reports split UTF-8 stream corruption. Exact byte/stream semantics belong in coding-worker fixtures.
- **Snapshot/session ownership:** snapshot managers persist SDK-owned state and immutable history, while multi-agent orchestration has its own persistence owner; child agents must not independently persist competing orchestrator state.
- **Single-live-writer limitation:** built-in sessions document no distributed lock. Two processes sharing session/agent identity can overwrite/merge history without necessarily raising an error.
- **Trusted-state boundary:** session storage is trusted and symlink-sensitive; restored Python history ending in `toolUse` can execute that stored tool request on the next invocation before another model call. Valid state serialization is not authorization to resume.
- **Handle validation:** open #4198 reports snapshot IDs that listing can expose but restore rejects. Enumeration and consume APIs must share identity validation.
- **Multiple durable state planes:** open #4102 and stateful-provider design evidence show local messages may not be the only durable model-visible state when a provider stores conversation chains.
- **Representation consistency:** open #4004 shows streamed UI content can differ from durable replay history; live stream, persisted history, model-visible context and audit/effect truth must be tested separately.
- **Interrupt identity:** human responses bind to unique interrupt IDs. Open #4171 reports stale/repeated interrupt response acceptance, reinforcing exactly-once active-request validation.
- **Interrupt replay:** a per-tool interrupt can split one logical batch across cycles, making lifecycle hooks such as `AfterToolsEvent` execute more than once; side-effecting hooks require idempotency identity.
- **Context is mutable model state:** sliding-window trimming, summarization, tool-result truncation/pinning and proactive compression change model-visible context and must not replace authoritative project/effect state.
- **Local models:** native Ollama support is currently a real Python path with tools/streaming/configuration, but capability still belongs to exact model + Ollama/runtime + adapter + settings.
- **OpenTelemetry:** agent/cycle/model/tool spans provide useful GUI/eval evidence but can contain raw system prompts, messages, tool arguments/results and other sensitive fields.
- **Framework-native evals:** Strands Evaluation includes deterministic, trajectory/state and LLM-based evaluators; its trace quickstart warns that missing session identity can mix spans between test cases.
- **Boundary:** Strands does not replace ACL's distributed project/task scheduler, effect ledger, workspace recovery, dependency governance, environment provisioning, acceptance policy or independent hostile verifier.

See `projects/strands-harness-sdk.md` for primary sources, current failure surfaces, shipped-vs-proposed distinctions, candidate invariants and ACL regression-fixture ideas.

## Task 8 — promptfoo research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings retained for later comparison:
- independent evaluation/red-team role rather than authoritative agent runtime ownership;
- deterministic tool/trace/trajectory assertions before semantic grading;
- required evidence channels should fail/invalid when unavailable rather than silently degrade;
- coding-agent failure taxonomy separates model behavior, harness boundary, verifier integrity and eval-design failures;
- host-side canaries, hashes, sidecars and traces can provide worker-independent evidence;
- mutable coding-agent rows need isolated/resettable workspaces;
- unsafe willingness, attempted action and verified effect are distinct labels;
- target and grader model/runtime identity both belong in reproducibility evidence;
- evaluator scripts/plugins are privileged executable dependencies;
- serializable evaluator descriptors should remain separate from live provider/client/session/credential objects.

See `projects/promptfoo.md` for the complete evidence.

## Task 7 — LangGraph research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings retained for later comparison:
- checkpoints, pending task writes, thread/checkpoint lineage, subgraphs, interrupts, retries/timeouts and typed task/checkpoint/debug streams;
- explicit durability modes without an implied exactly-once external-effect guarantee;
- external-effect settlement needs separate evidence/idempotency handling;
- concurrent approvals need stable interrupt IDs and ambiguous resume should fail closed;
- subgraph replay identity must survive parent forks/retries;
- state mutation must hydrate from one authoritative persistence source/version;
- replayable tasks need persisted or deterministically reacquirable inputs;
- physical checkpoint retention/deletion fencing is separate from model-context compaction.

See `projects/langgraph.md` for the complete evidence.

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
- loop/mistake detection belongs in runtime telemetry.

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
4. **promptfoo** — `promptfoo/promptfoo` — **Task 8 complete**; `projects/promptfoo.md`.
5. **Strands Harness SDK** — `strands-agents/harness-sdk` — **Task 9 complete**; `projects/strands-harness-sdk.md`.
6. **Codex** — `openai/codex` — **next task**; sandbox/approval policies, command authority, child-agent permission inheritance, Ollama integration.
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
2. **Nick Hollon** — `nick-hollon-lc` — LangGraph — durable/remote runtime lifecycle, checkpoint/state and streaming.
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
- Strands `sdk-python` → consolidated `harness-sdk` monorepo — canonical repository consolidation/continuity; not evidence of abandonment.

## Security / governance anchors retained regardless of ordinal source rank

- OWASP AI Agent Security Cheat Sheet
- OWASP Agent Memory Guard
- OWASP GenAI Security Project / Agentic Security Initiative
- MITRE ATLAS
- NIST AI / Agentic AI guidance

## Rules to preserve in later work

- Rank is information value, not adoption preference.
- Deep research extracts mechanisms/invariants first; dependency/fork/build decisions remain later comparative work.
- Model proposals and role labels are not authority boundaries.
- Runtime limits, cancellation and retry policy belong in observable harness state rather than prompt prose.
- Retry classes need separate reasons/budgets/progress tests.
- Tool schema, runtime validation, authorization, execution and evaluation are distinct contracts.
- Typed policy decisions should have explicit fail-open/fail-closed error semantics; authority-bearing controls should fail closed on ambiguity.
- Action authorization does not replace principal-approved objective/task-scope provenance.
- Logical request/idempotency identity, run/attempt identity, agent/process identity and durable session identity must remain separate.
- Sandboxed vs host execution must be explicit, and sandbox provisioning/network/mount/credential/user/resource/cleanup policy remains a separate lifecycle concern.
- Destructive file editing must preserve untouched bytes; process stream decoding must preserve multibyte character boundaries.
- Each durable state domain needs one authoritative owner; nested components must not persist competing versions.
- Persistent state requires distributed writer/fencing/lease semantics when multiple processes are possible.
- Restored history/checkpoints are trusted execution input; valid serialization does not prove provenance or permission to resume.
- Enumerated handles must satisfy the same identity contract as consume/restore APIs.
- Provider/server-side conversation state is a separate durable/model-visible state plane from local history.
- UI stream, persisted replay history, model-visible context and audit/effect evidence are distinct representations with explicit consistency contracts.
- Human approval/input binds to stable active request IDs; stale/duplicate responses fail closed.
- Interrupt/retry lifecycle callbacks can replay; side-effecting callbacks require idempotency/effect identity.
- Context trimming/summarization/offloading is model-state mutation, not authoritative project/effect truth.
- Local-model capability means exact model + runtime + adapter + configuration + SDK-language behavior.
- Telemetry may contain secrets/system prompts/tool data; evidence audience/redaction is separate policy.
- Evaluation evidence must bind to stable project/task/run/test identity; wrong correlation invalidates otherwise valid spans.
- The system under test should not own the authoritative definition of whether it passed.
- Deterministic evidence should precede semantic model grading when the property is machine-observable.
- Missing required evidence should produce an explicit invalid/failure state rather than an implicit pass.
- Verifier-owned tests/hashes/sidecars should remain outside worker mutation authority.
- Conversation/graph state, workspace state and external-effect evidence are separate recovery dimensions.
- A durable checkpoint does not imply exactly-once external side effects.
- State mutation must hydrate and commit against one authoritative state source/version.
- Physical persistence retention is separate from model-context compaction.
- Current bugs/regression fixes can be more valuable than feature lists because they expose actual failure surfaces.
- Preserve design proposals, shipped behavior, architectural generations and canonical aliases separately so migrations remain auditable.

## Next research task boundary

Task 9 is complete once the Strands Harness SDK research file, catalog, watchlist and state are committed. The next task is **Codex deep research only**. Do not begin it until separately instructed, and when it is begun, stop before OpenHands.
