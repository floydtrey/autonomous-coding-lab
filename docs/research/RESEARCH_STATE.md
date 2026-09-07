# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 22 — Google ADK deep research complete
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

## Task 22 work completed
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, and `watchlist.md` before beginning Task 22.
- Began from finalized Task 21 checkpoint `a5376589aa278089abfbdeb9415690053355394e`.
- Confirmed Task 22 scope as Google ADK only and preserved LiteLLM as next-task-only.
- Pinned canonical `google/adk-python` research to revision `b0180620f4c2f4f4467a89c37a30f75bf849700b` and stable release `v2.8.0` (2026-08-26).
- Deep-researched deterministic Workflow graph validation, dependency-ready concurrency, nested/dynamic execution and history-derived replay.
- Verified ADK resumability is explicitly experimental/best-effort and provides at-least-once resumed tool execution; side-effecting tools therefore require idempotency/reconciliation.
- Deep-researched Session/event/state persistence and current DatabaseSessionService stale-writer protection using locks, storage revision markers and transaction boundaries.
- Preserved partial streamed events and `temp:` state as non-durable state distinct from durable semantic events.
- Preserved session history, scoped key-value state and opt-in long-term MemoryService as separate state/trust planes.
- Deep-researched current HITL confirmation binding to historical function-call ID/name/arguments.
- Cross-checked open/reopened #6461 and retained `event.author == "user"` as a current authenticated-principal weakness across remote/A2A/HTTP boundaries.
- Retained fixed #6977 as a control-plane regression fixture showing confirmation pauses must not be reinterpreted as ordinary model/tool-result content.
- Deep-researched code-executor tiers from explicitly unsafe local subprocess through Docker and stronger GKE/gVisor/managed sandbox paths.
- Deep-researched LiteLLM-backed provider portability only as an ADK adapter surface; LiteLLM itself was not independently researched.
- Cross-checked current open #6482 and retained model-name/provider rewrite behavior as a current local/OpenAI-compatible adapter failure fixture.
- Preserved tool/schema composition as deployment-specific through fixed #5130 and current open #6984.
- Deep-researched MCP integration and retained its effect-aware retry boundary: automatically retry only while no remote tool effect could yet have occurred.
- Deep-researched A2A remote-agent state and HITL semantics; retained open #6854 and #6721 as current remote-boundary fixtures.
- Verified self-hosted FastAPI authentication/authorization is application-owned and local helper storage can fall back to in-memory services when durable paths are unavailable.
- Deep-researched Runner-global plugin authority and Model Armor boundaries; content screening does not replace tool-output provenance, authorization or sandboxing.
- Deep-researched AgentEvaluator/OpenTelemetry and preserved response quality, tool trajectory, semantic grading and runtime telemetry as separate evidence classes.
- Retained open #6099 as a useful decision-ledger gap: traces/tool events do not by themselves connect effect, authenticated principal, policy/refusal, approval and settlement.
- Wrote detailed evidence, primary sources, current/fixed failure surfaces, candidate invariants, reuse candidates and explicit non-conclusions to `projects/google-adk.md`.
- Appended exactly 18 Task 22 records after the 197 Task 21 catalog records, producing 215 total records.
- Preserved task boundary: no LiteLLM deep research, dependency/provider/model/sandbox/workflow/memory selection, benchmark execution, ACL/Vera redesign or worker/model execution was begun.

## Highest-value Google ADK findings for later comparison
1. Deterministic Workflow dependency/concurrency/replay belongs outside model prompt reasoning.
2. ADK explicitly confirms replayable workflow state is not exactly-once effects: resumability is best-effort and at-least-once.
3. Session history, scoped state and cross-session memory are separate systems and should remain separate Vera trust/state planes.
4. Database stale-writer fencing is useful, but generic shared-state replacement is not sufficient for concurrency-sensitive CAS/increment semantics.
5. Partial stream delivery and temporary state are not durable continuation evidence.
6. HITL exact-call binding is strong; authenticated principal binding remains a separate required authority dimension.
7. Confirmation/control events must remain typed control-plane state rather than normal model-visible task results.
8. Executor choice is a realized security/deployment profile, not a boolean sandbox label.
9. Provider/model/backend adapters contain behavior-bearing rewrites; `OpenAI-compatible` and model name do not establish equivalent behavior.
10. Automatic retry is safe only while the runtime can prove no remote effect may yet have begun.
11. In-process state semantics do not automatically survive an A2A remote boundary.
12. Remote HITL must preserve typed control response, principal, occurrence and paused destination across transport.
13. Self-hosted API principal auth and required durability are host-owned deployment gates.
14. Plugins/guardrails are privileged control-plane code and must remain outside worker mutation authority.
15. Model Armor/content screening is defense-in-depth, not authorization, provenance or containment.
16. Tool trajectory and response quality are separate evaluation dimensions; repeated frozen-profile trials are useful for ACL's later 32K benchmark.
17. A unified effect/decision ledger remains above ordinary runtime trace/session evidence.
18. ADK does not replace ACL/Vera effect settlement, credential brokering, protected verifier/policy, epistemic memory policy or independent acceptance evidence.

## Queue status
- Tasks 5–22 through **Google ADK (#18): complete**.
- **LiteLLM (#19): next task only.** No LiteLLM deep research was begun in Task 22.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **LiteLLM** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant provider normalization, local/OpenAI-compatible routing, retries/fallbacks, structured output/tool schemas, streaming/cancellation, credential/network boundaries, observability/evaluation, security/current failures, reproducibility and reusable mechanisms. Save report/catalog/state/watchlist, make a research-only commit, and stop before vLLM.

## Later tasks
1. LiteLLM, then the remaining ranked active-project queue one task at a time.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after individual work is complete.

## Stop point

Task 22 ended after Google ADK's current identity/maturity, Workflow orchestration/replay, explicit at-least-once resumability, session/state/memory separation, database stale-writer handling, HITL/principal boundary, executor tiers, provider/local compatibility, schema composition, MCP retry semantics, A2A state/HITL, FastAPI deployment trust, plugin/Model Armor boundaries and evaluation/observability were researched. No LiteLLM research, cross-project winner selection, dependency decision, benchmark execution, ACL/Vera architecture/governance change or worker/model execution was begun.
