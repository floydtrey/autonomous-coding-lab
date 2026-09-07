# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 27 — smolagents deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Catalog layout
- `docs/research/catalog.jsonl` remains the original catalog through Task 24 with 257 records and is intentionally left unchanged.
- `docs/research/catalog-part2.jsonl` begins with Task 25 OpenCode records and now contains Task 26 Mem0 and Task 27 smolagents records; it remains the append target for subsequent research tasks unless deliberately consolidated later.
- Treat both files together as the research catalog; do not rebuild or rewrite Part 1 merely to add new records.

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
- Task 25: **OpenCode** — `projects/opencode.md`.
- Task 26: **Mem0** — `projects/mem0.md`.
- Task 27: **smolagents** — `projects/smolagents.md`.

## Task 27 work completed
- Began from finalized Task 26 branch head `1dd0e6da3a9b1bb9225693d551a3cf5c88aeba3a`.
- Re-read the Task 26 state boundary and kept Agno out of scope.
- Confirmed latest observed stable smolagents release **v1.26.0** and current `main` at `30bb1161095dbae2271e6bc3cc4c219cc3897a57` reporting **1.27.0.dev0**; preserved stable and development profiles separately.
- Mapped the thin `MultiStepAgent` ReAct loop, `CodeAgent` Python-action profile, `ToolCallingAgent` structured-call profile, planning, callbacks, mutable state, managed-agent delegation and `AgentMemory` step history.
- Verified current upstream security policy explicitly states `LocalPythonExecutor` is **not a security boundary** and retained Docker/E2B/Modal/Blaxel as separate stronger sandbox profiles rather than equivalent executor labels.
- Preserved interpreter restrictions/authorized imports as non-containment and required ACL-owned filesystem/network/process/resource/credential policy for any future model-generated code execution.
- Retained accepted priority-P1 issue **#2722** as evidence that executor extensibility is itself under redesign and current executor identities are hardcoded core profiles.
- Retained open **#2197** as a timeout/control-return fixture: a configured local execution timeout can still return only after the worker finishes.
- Preserved cancellation/interrupt, loop termination, backing process/provider termination and effect settlement as distinct states.
- Retained **#1781** as a parallel-delegation state-isolation fixture: concurrent calls to one managed-agent instance can share/overwrite mutable run state.
- Retained open **#2166** as a typed-child-status fixture: failed/max-step sub-agents can collapse into empty/None parent-visible output.
- Retained open **#2424** as an information-flow fixture: `provide_run_summary=True` can expose raw inner tool calls/results, including secrets or PII, into parent context.
- Preserved child invocation identity, capability ceiling, mutable state and redacted child-to-parent evidence export as distinct control-plane concerns.
- Retained open **#2456** and corroborated current main source: `final_answer_checks` uses `assert`, so optimized Python can silently remove truth enforcement.
- Derived a fail-closed verifier invariant: production authorization/acceptance must use explicit control flow in protected code, never assertions inside the harness under test.
- Retained **#2566** as a long-horizon/context fixture: full accumulated step memory is replayed on every action step, creating approximately quadratic cumulative input-token growth.
- Preserved context compaction/truncation/history policy as behavior-bearing benchmark identity and kept AgentMemory separate from durable ACL continuation checkpoints.
- Verified broad local/provider support through Transformers, vLLM, MLX, LiteLLM and OpenAI-compatible adapters while keeping exact model+runtime+adapter+action-style+executor profile qualification mandatory.
- Mapped MCP/Hub tool loading and explicit `trust_remote_code`; retained open **#2305** as evidence that remote-server/tool trust remains an application/control-plane responsibility.
- Preserved OpenTelemetry, step timing/token usage and benchmark traces as operational evidence rather than independent verifier authority.
- Inspected the upstream benchmark runner comparing code/tool-calling/vanilla modes and derived additional ACL manifest requirements for exact harness, runtime, sandbox, cache, hardware and tool identity.
- Wrote detailed findings, candidate invariants, regression fixtures, reuse candidates, sources and explicit non-conclusions to `projects/smolagents.md`.
- Appended 12 Task 27 smolagents records to `catalog-part2.jsonl`; the original 257-record `catalog.jsonl` remains untouched.
- No Agno research, harness adoption/fork, model/runtime assignment, 32K benchmark execution or ACL implementation/governance change was begun.

## Highest-value smolagents findings for later comparison
1. **Stable versus development is a qualification boundary.** v1.26.0 and current 1.27.0.dev0/main are separate harness profiles.
2. **The thin loop is useful reference material.** `MultiStepAgent` demonstrates how little model-facing orchestration is necessary when other responsibilities stay explicit.
3. **CodeAgent and ToolCallingAgent are different benchmark profiles.** Python-action and native/JSON tool-call behavior must be scored separately.
4. **LocalPythonExecutor is explicitly not a sandbox.** Interpreter restrictions cannot replace ACL-owned OS/process/filesystem/network/credential containment.
5. **Executor identity is security and benchmark identity.** Local, Docker, E2B, Modal, Blaxel and future plugins have different trust/lifecycle properties.
6. **#2197 is a strong deadline fixture.** Timeout declaration does not necessarily mean prompt caller control return or worker termination.
7. **Managed-agent invocation state needs fencing.** #1781 shows one child definition cannot safely stand in for multiple concurrent mutable invocations.
8. **Delegation completion/export must be typed and redacted.** #2166 and #2424 expose silent failure and raw-inner-tool-data leakage classes.
9. **`final_answer_checks` is a useful seam but not current verifier authority.** #2456 plus current source show `assert` can be optimized away.
10. **Agent memory is runtime context, not a checkpoint.** #2566 also shows full-history replay creates long-horizon context pressure.
11. **MCP/Hub tool compatibility is not trust.** Remote tool origin, schema, credentials, network and effect authorization remain outside smolagents.
12. **smolagents remains below ACL-owned scheduling, task/effect identity, containment, durable recovery, delegation fencing, credentials and independent verification.**

## Queue status
- Tasks 5–27 project deep research are complete through **smolagents**.
- **Agno (#24 in ranked active-project queue): next task only.** No Agno research was begun in Task 27.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **Agno** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant agent/runtime architecture, model/provider/local-model support, teams/multi-agent delegation, workflows/state/session persistence, memory/knowledge, tools/MCP/protocol integration, sandbox/code-execution and credential boundaries, concurrency/writer ownership, retries/cancellation/timeouts, observability/evaluation, current failures, reproducibility and reusable mechanisms. Save report/catalog-part2/state/watchlist, make a research-only commit/checkpoint, and stop before LlamaIndex.

## Stop point

Task 27 ended after smolagents' stable/dev identity, thin ReAct architecture, CodeAgent/ToolCallingAgent split, executor/sandbox boundary, timeout/cancellation behavior, managed-agent isolation and information flow, final-answer validation seam, runtime memory/context growth, provider/local-model portability, MCP/tool trust, observability/evaluation and current 2026 failures were deeply researched. No Agno research, cross-project harness winner selection, 32K benchmark execution or ACL implementation/governance change was begun.
