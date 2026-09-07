# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 28 — Agno deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Catalog layout
- `docs/research/catalog.jsonl` remains the original catalog through Task 24 with 257 records and is intentionally left unchanged.
- `docs/research/catalog-part2.jsonl` begins with Task 25 OpenCode records and now contains Task 26 Mem0, Task 27 smolagents and Task 28 Agno records; it remains the append target for subsequent research tasks unless deliberately consolidated later.
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
- Task 28: **Agno** — `projects/agno.md`.

## Task 28 work completed
- Began from finalized Task 27 branch head `4ec0f41a45bf6fa8c02ab94ca8284dee21cb50be`.
- Re-read research governance/process/state/source boundaries and kept LlamaIndex out of scope.
- Confirmed latest observed stable Agno release **v3.0.6** and current `main` `d703c34f3abf3c41275d3fb2da6e0518a8881f24`; current main still reports package version 3.0.6, so exact commit remains required identity.
- Mapped Agent, Team, Workflow and AgentOS as distinct layers and retained TeamMode `coordinate`, `route`, `broadcast` and `tasks` plus workflow Step/Loop/Parallel/Condition/Router structures as behavior-bearing orchestration profiles.
- Preserved component definition, invocation, session, workflow step, protocol request and ACL effect as distinct identities.
- Retained #9348's root-only nested-team DB ownership as a useful single-writer principle while preserving its history-propagation failure as evidence that writer ownership and child read visibility are separate.
- Retained open #7479 as a same-session storage regression fixture: concurrent runs can silently lose history through stale-snapshot full-JSONB last-writer-wins updates.
- Derived atomic append/CAS/row-lock/lease/fencing requirements for authoritative shared session state rather than whole-document LWW persistence.
- Retained open #10015 as a mixed sync/async cancellation race: separate locks over the same dictionaries can overwrite cancellation intent and member-run mappings.
- Retained #7294 as a child/delegation/stream lifecycle fixture showing member completion can precede parent delegation completion by a timeout-scale interval.
- Retained #8910/#9278 as HITL continuation fixtures where workflow `PAUSED` and executor child `CANCELLED` become contradictory durable state and make resume impossible.
- Derived explicit cross-level parent/child lifecycle invariants and reconciliation-before-resume requirements.
- Mapped current `MemoryManager`, including LLM-driven memory maintenance, database UserMemory storage, default memory-management model behavior and user-scope semantics.
- Retained open #9983 and corroborated current source: when the model-facing `clear_memory` tool is enabled, its closure calls unscoped `db.clear_memories()`, providing a cross-principal destructive-memory fixture.
- Preserved memory `user_id` as storage scope rather than authenticated principal and rejected generic/default user fallbacks for authoritative multi-user domains.
- Inspected current CodeMode: persistent per-session IPython Python/shell execution, explicit non-sandbox status, executable dill snapshots, session-keyed kernels, snapshot limits/eviction and team namespace sharing.
- Preserved CodeMode/persistent interpreter state as runtime state rather than ACL continuation authority and required ACL-owned containment, process custody, credentials and snapshot provenance.
- Retained DB-backed FileSystem `expected_version` CAS/atomic semantics and local-backend explicit CAS rejection as strong capability-honesty patterns; retained Studio immutable revisions plus guarded current-version updates as a reuse candidate.
- Retained open #8620 as a credential/audience fixture: configured Authorization/Cookie headers can accompany a model-selected URL; treated #8847 as related external-send authority design evidence rather than a proven framework escape.
- Retained #8494 as indirect-prompt-injection/content-trust evidence while rejecting text sanitization alone as an authorization boundary.
- Verified broad provider/local support including distinct native Ollama chat and Ollama Responses paths while keeping exact adapter/runtime/API/tool/context profile qualification mandatory.
- Retained #9034/current #10031 provider-adapter signature-drift behavior as a critical harness fixture: adapter exceptions can become normal assistant text instead of typed run failure.
- Preserved tool-result compression/offloading/history policy as behavior-bearing benchmark identity and current fail-loud incompatibility as preferable to silent reference corruption.
- Retained maintainer-tracked #9680/#9829 as cleanup/settlement evidence: run deletion can leave detached result payloads and async run return can precede final CodeMode snapshot flush.
- Mapped v3.0.6 MCP legacy/auto/stateless profiles, server-card/auth/Host-Origin controls and direct-tool publication semantics.
- Preserved Agno's fail-closed MCP rule: tools requiring confirmation/user-input/external-execution are refused when the direct MCP surface would bypass normal FunctionCall controls.
- Preserved same logical tool over Agent/REST/MCP/A2A as separate security/lifecycle profiles whenever hook/approval/auth behavior differs.
- Reviewed A2A task/card/send/stream surfaces and retained current documentation caveat that remote content and lifecycle status can diverge.
- Reviewed AgentOS JWT/RBAC and opt-in user isolation; retained #9741 as a narrower REST/WebSocket auth-path consistency fixture.
- Reviewed OpenInference/OpenTelemetry tracing plus accuracy/performance/reliability eval surfaces as useful evidence mechanisms rather than independent ACL acceptance authority.
- Wrote detailed findings, 32 candidate invariants, regression fixtures, reuse candidates, sources and explicit non-conclusions to `projects/agno.md`.
- Appended 14 Task 28 Agno records to `catalog-part2.jsonl`; the original 257-record `catalog.jsonl` remains untouched.
- No LlamaIndex research, cross-project framework winner selection, Agno adoption, model/runtime assignment, 32K benchmark execution or ACL/Vera implementation/governance change was begun.

## Highest-value Agno findings for later comparison
1. **Agno is a platform/runtime reference, not just a loop.** Agent, Team, Workflow and AgentOS are distinct architecture layers worth comparing independently.
2. **Exact commit remains identity even when package version does not change.** Current main contains post-v3.0.6 fixes while still reporting 3.0.6.
3. **Single writer and readable child state are separate problems.** #9348 preserves root-owned persistence intent while exposing nested history loss.
4. **#7479 is a strong shared-session fixture.** Whole-JSONB last-writer-wins persistence can silently discard concurrent runs.
5. **#10015 is a strong cancellation fixture.** Separate sync/async locks cannot safely govern one shared state domain.
6. **Composite lifecycle invariants matter.** #8910/#9278 show a durable PAUSED parent with CANCELLED continuation child can become unrecoverable.
7. **Memory deletion scope is effect authority.** #9983 shows an enabled model-facing clear path can reach every user's memories through a global DB clear.
8. **CodeMode is explicitly not containment.** Persistent Python/shell plus executable dill snapshots require outer ACL isolation and trusted snapshot provenance.
9. **DB FileSystem CAS is a positive reusable pattern.** Unsupported local CAS fails explicitly; Studio combines immutable revisions and guarded head movement.
10. **Credentials bind to destinations.** #8620 demonstrates why a toolkit credential cannot safely follow a model-selected arbitrary URL.
11. **Provider exceptions must remain typed failures.** #9034/#10031 show adapter failure can otherwise masquerade as assistant output.
12. **Async completion requires cleanup settlement.** #9680/#9829 separate run return from snapshot/result-payload cleanup.
13. **Agno's MCP fail-closed publication is high-value reference material.** If required approval semantics cannot survive direct MCP invocation, current AgentOS refuses the tool instead of silently downgrading it.
14. **Authentication, RBAC, user isolation, content trust and effect authorization remain separate.** AgentOS has all of these concerns, but one does not imply the others.
15. **Agno remains below ACL-owned scheduling, task/effect identity, containment, writer fencing, credentials, reconciliation/checkpoint authority and independent verification; Vera retains epistemic memory authority.**

## Queue status
- Tasks 5–28 project deep research are complete through **Agno**.
- **LlamaIndex (#25 in ranked active-project queue): next task only.** No LlamaIndex research was begun in Task 28.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **LlamaIndex** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant agent/workflow architecture, provider/local-model support, tools/protocol integration, storage/indexing/retrieval/memory, state/session persistence, concurrency/writer ownership, retries/cancellation/timeouts, security/credential/content-trust boundaries, observability/evaluation, current failures, reproducibility and reusable mechanisms. Save report/catalog-part2/state/watchlist, make a research-only commit/checkpoint, and stop before CrewAI.

## Stop point

Task 28 ended after Agno's current architecture, Agent/Team/Workflow/AgentOS layering, team/delegation modes, session persistence and writer races, cancellation/HITL lifecycle, memory authority, CodeMode execution/snapshots, FileSystem CAS/versioning, tool/credential boundaries, provider/local-model adapters, MCP/A2A surfaces, AgentOS auth/isolation, cleanup settlement, observability/evaluation and current 2026 failures were deeply researched. No LlamaIndex research, cross-project framework winner selection, 32K benchmark execution or ACL/Vera implementation/governance change was begun.