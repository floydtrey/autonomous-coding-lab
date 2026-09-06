# Research Watchlist

Task 3 established the research-priority queues. Task 4 added transition/status evidence. Tasks 5–8 completed deep research on Pydantic AI, Cline, LangGraph, and **promptfoo**. Rank still means **study/watch sooner because the candidate is expected to reduce ACL/Vera uncertainty**; completed research does not convert the queue into an adoption list.

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

## Task 8 — promptfoo research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings to carry into later comparison:

- **Independent evaluator role:** promptfoo is strongest as an evaluation/red-team layer around a worker/runtime, not as an owner of authoritative agent session/checkpoint state.
- **Deterministic first:** tool use, exact/partial tool arguments, sequences, counts, trace errors/durations and other observable properties can be checked mechanically before semantic model grading.
- **Trajectory evidence:** OpenTelemetry traces tie target calls, tools, agent turns and grading to each test execution; cache and subagent semantics must be accounted for when assertions depend on turn/trajectory structure.
- **Evidence availability:** trace-dependent high-confidence evals can fail on receiver startup failure rather than silently continuing without traces; ACL should generalize this to every required evidence channel.
- **Coding-agent threat model:** dedicated plugins cover repository/terminal prompt injection, secret reads, sandbox escape, verifier sabotage, network/procfs access, delayed CI exfiltration, automation poisoning, generated vulnerabilities and hidden exfiltration.
- **Failure taxonomy:** coding-agent guidance separates model behavior, harness boundary, verifier integrity and eval-design failures instead of collapsing every result into one score.
- **Workspace isolation:** mutable agent rows should use disposable/resettable workspaces and unique synthetic canaries so one test cannot contaminate later tests.
- **Verifier integrity:** host-side hashes, canaries, command/trace evidence, trap logs and sidecar reports can outrank model rubrics; a configured missing sidecar report fails closed.
- **Action evidence:** unsafe willingness, attempted action and verified effect are distinct labels; training/security signoff should prefer action-observable evidence.
- **Telemetry audience:** `includeInAttack` and `includeInGrading` demonstrate that attacker-visible telemetry and validator-visible telemetry are separate information-flow choices.
- **Local models:** native Ollama targets, tools, embeddings and local grading providers make an offline/local benchmark path practical; grader identity/settings still belong in the benchmark definition.
- **Reproducibility:** cache policy, concurrency, repeats, fixture commit/workspace/reset identity, target runtime and grader runtime all need pinning; evaluator controls help but do not make runs automatically reproducible.
- **CI gates:** deterministic/security/verifier failures should remain distinguishable from infrastructure errors and semantic scores; severe failures should not be averaged away by a global pass rate.
- **Executable eval code:** JavaScript/Python assertions are privileged executable code, so third-party eval packs require provenance and containment.
- **Live-object boundary:** open #10501 shows why serializable test/grader descriptors must remain separate from live SDK/provider/session objects and credentials.
- **Bounded grader evidence:** open #10166 reinforces the need for explicitly selected, size-bounded, provenance-preserving structured evidence when semantic graders need more than final text.
- **Boundary:** promptfoo does not replace ACL task/runtime state, workspace/effect recovery, sandboxing, credentials, scheduling, local-model capability profiles or final project acceptance policy.

See `projects/promptfoo.md` for primary sources, current failure surfaces, candidate invariants, ACL regression-fixture ideas and deliberately deferred comparison questions.

## Task 7 — LangGraph research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings retained for later comparison:
- checkpoints, pending task writes, thread/checkpoint lineage, subgraphs, interrupts, retries/timeouts and typed task/checkpoint/debug streams;
- explicit `sync`, `async` and `exit` durability modes without an implied exactly-once external-effect guarantee;
- external-effect settlement needs separate evidence/idempotency handling;
- concurrent approvals need stable interrupt IDs and ambiguous resume should fail closed;
- subgraph replay identity must survive parent forks/retries;
- state mutation must hydrate from one authoritative persistence source/version;
- replayable tasks need persisted or deterministically reacquirable inputs;
- physical checkpoint retention/deletion fencing is separate from model-context compaction;
- retry, hard/idle timeout and cancellation belong in observable runtime policy.

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
4. **promptfoo** — `promptfoo/promptfoo` — **Task 8 complete**; `projects/promptfoo.md`.
5. **Strands Harness SDK** — `strands-agents/harness-sdk` — **next task**; explicit harness interfaces, structured-output validation/retry, Ollama support.
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

## Security / governance anchors retained regardless of ordinal source rank

- OWASP AI Agent Security Cheat Sheet
- OWASP Agent Memory Guard
- OWASP GenAI Security Project / Agentic Security Initiative
- MITRE ATLAS
- NIST AI / Agentic AI guidance

## Rules to preserve in later work

- Rank is information value, not adoption preference.
- Deep research extracts mechanisms/invariants first; dependency/fork/build decisions remain later comparative work.
- The system under test should not own the authoritative definition of whether it passed.
- Deterministic evidence should precede semantic model grading when the property is machine-observable.
- Missing required evidence should produce an explicit invalid/failure state rather than an implicit pass.
- Verifier-owned tests/hashes/sidecars should remain outside worker mutation authority.
- Coding-agent failures should distinguish model behavior, harness boundary, verifier integrity and eval-design defects.
- Security results should distinguish unsafe willingness, attempted action and verified effect.
- Mutable eval rows need isolated/resettable workspaces and unique synthetic canaries.
- Attacker-visible and validator-visible telemetry are separate policy choices.
- Evaluator target and grader model/runtime identities both belong in reproducibility evidence.
- Cache/concurrency/repeat/workspace/reset settings are part of benchmark identity.
- Evaluator scripts/plugins are privileged executable dependencies, not passive test data.
- Serializable configuration/descriptors should remain separate from live provider/session/credential objects.
- Conversation/graph state, workspace state and external-effect evidence are separate recovery dimensions.
- A durable checkpoint does not imply exactly-once external side effects.
- Persistent recovery identity should not depend solely on regenerated ephemeral task IDs.
- Human approval/input must bind to stable request IDs; ambiguous concurrent resume should fail closed.
- Replayable tasks require persisted or deterministically reacquirable inputs.
- State mutation must hydrate and commit against one authoritative state source/version.
- Retry, timeout and cancellation policies belong in observable runtime behavior.
- Deletion needs generation/tombstone fencing against stale writers.
- Physical persistence retention is separate from model-context compaction.
- Current bugs/regression fixes can be more valuable than feature lists because they expose actual failure surfaces.
- Preserve architecture generations and canonical aliases separately so migrations remain auditable.

## Next research task boundary

Task 8 is complete once the promptfoo research file, catalog, watchlist and state are committed. The next task is **Strands Harness SDK deep research only**. Do not begin it until separately instructed, and when it is begun, stop before Codex.
