# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 25 — OpenCode deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Catalog layout
- `docs/research/catalog.jsonl` remains the original catalog through Task 24 with 257 records and is intentionally left unchanged.
- `docs/research/catalog-part2.jsonl` begins with Task 25 OpenCode records and is the append target for subsequent research tasks unless the catalogs are deliberately consolidated later.
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

## Task 25 work completed
- Began from finalized Task 24 checkpoint `12dd335f0c3b98d187dd55ef877c9ea922caa282`.
- Re-read the research governance/process/state boundary before completing the task and preserved Mem0 as Task 26 next-only.
- Confirmed Task 25 scope as canonical `anomalyco/opencode` only.
- Identified stable observed release **v1.18.29** and kept stable V1 evidence separate from the active V2 redesign on the default `dev` branch.
- Classified OpenCode as a substantial coding-agent harness/runtime rather than a thin CLI, with session, tool, permission, provider, MCP and server/client responsibilities.
- Verified the upstream security boundary that the OpenCode agent is **not sandboxed**; permission/approval remains awareness/control UX rather than OS/process/filesystem/network/credential containment.
- Derived that any later ACL OpenCode worker must execute inside ACL-owned containment with protected governance/verifier/checkpoint roots and a minimal explicit child environment.
- Retained current stable issue **#47605** as a timeout/transport lifecycle fixture: malformed or absent response `Content-Type` can bypass a body watchdog and leave a session indefinitely busy.
- Derived an unconditional deadline invariant: response metadata/parser selection may choose how to consume a response but must never choose whether the request has hard/idle timeout ownership.
- Retained current stable issue **#47727** as a server/resource lifecycle fixture: per-directory instances and MCP child processes can accumulate under `serve` until memory/process exhaustion.
- Derived explicit workspace/server/MCP child ownership, bounded retention, teardown and cleanup-settlement invariants.
- Preserved separate identities for provider request, OpenCode session, tool call, MCP server/process, ACL task/run and external effect.
- Preserved provider/local-model qualification as an exact model + runtime + adapter + OpenCode generation/profile + configuration property.
- Preserved durable session/event state as evidence rather than an ACL continuation checkpoint; workspace, processes, effects, current authority and verifier state still require outer validation.
- Separated runtime/session telemetry from verifier-owned acceptance evidence and classified current defects as harness lifecycle failures rather than model failures.
- Wrote detailed findings, candidate invariants, regression fixtures, reuse candidates, sources and explicit non-conclusions to `projects/opencode.md`.
- Wrote the Task 25 OpenCode catalog records to new `catalog-part2.jsonl`, leaving the original 257-record `catalog.jsonl` untouched.
- No Mem0 research, benchmark execution, OpenCode adoption/fork, model assignment or ACL/Vera implementation/governance change was begun.

## Highest-value OpenCode findings for later comparison
1. **Stable versus V2/dev is a hard qualification boundary.** Stable v1.18.29 behavior and the active default-branch V2 redesign are separate profiles; dev mechanisms are not stable guarantees.
2. **Harness identity is benchmark identity.** Exact OpenCode release/commit/profile belongs beside exact model/runtime/adapter identity.
3. **OpenCode is not a sandbox.** Upstream permission/approval controls do not provide OS/process/filesystem/network/credential isolation.
4. **ACL must retain external containment.** Any later OpenCode worker runs inside ACL-owned sandbox/capability ceilings with protected control-plane roots.
5. **#47605 is a strong deadline fixture.** Content-Type/parser branching must not bypass hard/idle request/body/stream deadlines or leave sessions permanently busy.
6. **#47727 is a strong resource-ownership fixture.** Workspace/server instances and MCP child processes need explicit ownership, bounded retention, teardown and settlement evidence.
7. **Session/event durability is not safe continuation authority.** ACL still validates workspace, processes, external effects, current credentials/policy and verifier state before resume.
8. **MCP is both tool-origin and process-lifecycle state.** Tool names alone are insufficient identity and spawned servers need separately managed environments/lifecycles.
9. **Provider/local support remains deployment-specific.** OpenAI-compatible or provider labels do not establish tool/stream/context/schema/retry parity.
10. **Cancellation and cleanup are multi-stage.** Cancel intent, session/coroutine termination, backing provider/process termination and resource/effect settlement remain separate.
11. **Operational telemetry is not independent verification.** Runtime defects must be classified separately from model capability failures.
12. **OpenCode remains below ACL-owned project/task/effect identity, policy, sandbox, credential, writer-fencing and verifier authority.**

## Queue status
- Tasks 5–25 project deep research are complete through **OpenCode**.
- **Mem0 (#22 in ranked active-project queue): next task only.** No Mem0 research was begun in Task 25.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **Mem0** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant persistent-memory architecture, provenance/identity, memory write/read/delete lifecycle, conflict/supersession and truth boundaries, provider/local-model integration, storage/vector/database backends, concurrency/writer ownership, security/prompt-injection/credential boundaries, MCP/API surfaces, observability/evaluation, current failures, reproducibility and reusable mechanisms. Save report/catalog/state/watchlist, make a research-only commit, and stop before smolagents.

## Stop point

Task 25 ended after OpenCode's stable-versus-V2 identity boundary, agent/harness runtime responsibilities, non-sandbox permission boundary, provider/MCP/session state, timeout/cancellation/resource lifecycle, observability/reproducibility and current stable issues #47605/#47727 were deeply researched. No Mem0 research, cross-project winner selection, model/runtime assignment, 32K benchmark execution or ACL/Vera implementation/governance change was begun.
