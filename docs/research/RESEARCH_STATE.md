# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 31 — Mastra deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Catalog layout
- `docs/research/catalog.jsonl` remains the original catalog through Task 24 with 257 records and is intentionally left unchanged.
- `docs/research/catalog-part2.jsonl` begins with Task 25 OpenCode records and now contains Task 26 Mem0, Task 27 smolagents, Task 28 Agno, Task 29 LlamaIndex, Task 30 CrewAI and Task 31 Mastra records; it remains the append target for subsequent research tasks unless deliberately consolidated later.
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
- Task 29: **LlamaIndex** — `projects/llamaindex.md`.
- Task 30: **CrewAI** — `projects/crewai.md`.
- Task 31: **Mastra** — `projects/mastra.md`.

## Task 29 work completed
- Began from finalized Task 28 branch head `e7c403311f28753c22f9945c59f2b33ef7004029` and verified no concurrent branch drift before writes.
- Re-read README, PROCESS, RESEARCH_STATE, sources and watchlist governance and kept CrewAI out of scope.
- Confirmed latest observed stable LlamaIndex release **v0.14.24** and current `run-llama/llama_index` main `d2ac544a27c73d2a68e9c57efec4b2ac0ef99892`; current core still reports 0.14.24, so exact source commit remains behavior-bearing identity.
- Identified the current split between `llama-index-core` and the separately versioned `llama-index-workflows` runtime maintained in `run-llama/llama-agents`; preserved both identities in future benchmark/deployment manifests.
- Mapped current `FunctionAgent`, `ReActAgent`, `CodeActAgent` and multi-agent `AgentWorkflow` plus typed agent/workflow events, explicit root/handoff topology and shared Workflow Context state.
- Preserved agent definition, invocation, Workflow run, Context/session, protocol request, tool call and external effect as separate identities.
- Verified Workflow Context is serializable/restorable and is distinct from agent Memory; preserved Context, Memory and RAG/index state as separate persistence/trust planes.
- Preserved JSON Context as continuation evidence rather than ACL checkpoint authority and marked pickle-backed Context restoration as trusted executable deserialization.
- Retained open **#22559** as a high-value at-least-once replay fixture: `wait_for_event` can replay a step and repeat pre-wait external effects; nondeterministic waiter IDs can break response matching across replay.
- Derived stable logical effect/idempotency and waiter/correlation identity requirements before HITL/replay boundaries.
- Inspected the separately versioned Workflows runtime's current `WorkflowHandler`: graceful cancellation delegates to a runtime adapter and waits only for a bounded interval; preserved cancel request, backing-operation termination and effect/resource settlement as separate states.
- Retained current `AgentWorkflow._call_tool()` behavior where ordinary tool exceptions become model-visible `ToolOutput(is_error=True)`; preserved tool error and effect settlement as separate state.
- Retained open **#20386** as design evidence for deterministic host-owned tool I/O mediation: authoritative IDs should be injected before execution and outputs can be deterministically filtered/redacted before model exposure.
- Preserved `can_handoff_to` as orchestration routing rather than a security capability and kept child/peer effect authority independently host-derived.
- Retained open **#22071** and corroborated the current `workflow_as_mcp(workflow: Workflow, ...)` API shape: one mutable Workflow instance can be reused across MCP clients while only Context is per-run, enabling cross-tenant `self.*` state leakage.
- Derived immutable/request-scoped workflow-instance and protocol-lifecycle isolation requirements.
- Retained open current-main **#22701** as a memory isolation fixture: shared `VectorMemoryBlock` state can pin later retrievals to the first session filter and mutate caller-owned filter/message objects.
- Preserved memory/session namespace as scope metadata rather than authenticated principal identity and required per-call host-stamped immutable scope.
- Retained open **#22248** as a state-projection freshness fixture: canonical `ctx.store` state can change while the next LLM call receives a stale model-visible projection.
- Preserved canonical state and model-visible prompt projection as separately versioned/tested representations.
- Retained open **#21666** as memory-poisoning design evidence and preserved persistent/retrieved memory as untrusted content, not verified truth or policy authority.
- Inspected current `CodeActAgent`: model-authored Python is delegated to caller-provided `code_execute_fn`; preserved code execution support and OS/process sandboxing as separate capabilities.
- Required exact CodeAct executor/container/process/network/mount/resource/credential/cleanup profile as benchmark/security identity.
- Mapped RAG/indexing as separate source-document/node/transformation/embedding/index/vector/retrieval/citation planes and retained v0.14.24 fixes such as **#22133** as derived-state integrity fixtures.
- Retained recent chat/memory/AG-UI fixes (#22124, #22179, #22162, #22103, #22109, #22189) as representation/protocol integration fixtures; preserved fail-loud missing tool-call identity rather than fabricated correlation IDs.
- Verified official local Ollama LLM/embedding paths and llama.cpp integration; retained the v0.14.24 effective-context fix as evidence that requested and realized context are separate benchmark fields.
- Preserved exact integration package, model/runtime/template/tool/schema/stream/context profile as provider capability identity rather than nominal provider support.
- Reviewed OpenTelemetry/LlamaTrace and evaluation surfaces as operational/semantic evidence rather than independent ACL verifier authority.
- Wrote detailed findings, 36 candidate invariants, 18 regression fixtures, reuse candidates, primary sources and explicit non-conclusions to `projects/llamaindex.md`.
- Appended 16 Task 29 LlamaIndex records to `catalog-part2.jsonl`; the original 257-record `catalog.jsonl` remains untouched.
- No CrewAI research, framework winner selection, LlamaIndex adoption, model/runtime assignment, 32K benchmark execution or ACL/Vera implementation/governance change was begun.

## Highest-value LlamaIndex findings for later comparison
1. **Core framework and Workflow runtime are separately versioned identities.** Current core delegates Workflow execution to `llama-index-workflows`; one package version is insufficient benchmark identity.
2. **Context, Memory and RAG/index state are distinct planes.** A restorable Context is continuation evidence, not complete checkpoint/effect settlement.
3. **#22559 is a critical effect-replay fixture.** HITL/replay can re-run code before a wait, so external effects require stable IDs/idempotency and reconciliation.
4. **Cancellation return is not settlement.** Current `cancel_run()` can return after a bounded wait without proving backing work/effects ended.
5. **Tool errors are not effect evidence.** AgentWorkflow can convert exceptions into model-visible error results after an ambiguous external effect.
6. **Host-owned deterministic tool I/O matters.** #20386 reinforces authenticated identifier injection and model-visible output filtering outside model control.
7. **Handoffs route work but do not grant authority.** Child/peer capability remains an outer ACL concern.
8. **#22071 is a strong protocol/object-isolation fixture.** Per-run Context does not isolate mutable `self.*` fields on one workflow instance shared by MCP clients.
9. **#22701 is a strong memory-isolation fixture.** Per-session filters must be built per call and must not mutate reusable shared component state.
10. **Canonical state and prompt projection can diverge.** #22248 demonstrates the need to version/test model-visible state freshness independently.
11. **Persistent memory remains untrusted content.** Storage/retrieval does not create truth, instruction authority or authentication.
12. **CodeActAgent does not supply containment.** `code_execute_fn` and its realized sandbox profile own the security boundary.
13. **RAG ingestion is multi-plane derived state.** Source evidence, nodes, embeddings, indexes and citations need explicit generation/reconciliation identity.
14. **Protocol/message projections are separately testable.** Recent AG-UI/chat/memory fixes show canonical execution state can be lost or mutated between representations.
15. **Requested and effective context are separate.** The llama.cpp context metadata fix directly supports ACL's planned measured 32K qualification.
16. **LlamaIndex remains below ACL-owned scheduling, task/effect identity, containment, credentials, writer fencing, reconciliation/checkpoint authority and independent verification; Vera retains epistemic memory authority.**

## Task 31 work completed
- Began from finalized Task 30 branch head `e02e609cc08f4157b593e87df219ab7c92673a0d`.
- Re-read README, PROCESS, RESEARCH_STATE, sources and watchlist governance and did not infer a project after Mastra.
- Confirmed latest stable observed core release **@mastra/core 1.64.0** and current main `685616780ea68e55c23c5980c17d5eee9a8f0aa9`, where core reports **1.65.0-alpha.8**; preserved stable and active-alpha profiles separately.
- Mapped ordinary Agent, durable/evented Agent, workflow, background-task, worker/pubsub and Inngest-style execution as separate runtime profiles.
- Preserved durable snapshot, stream-event cache, run status, observer registry and external effect as separate state/lifecycle planes.
- Retained current durable-agent docs' explicit warning that recovery reissues LLM calls and re-executes tool calls; derived at-least-once recovery and external idempotency/reconciliation requirements.
- Retained current docs' explicit statement that multi-replica durable recovery has no built-in distributed lease/lock; derived external leader/lease/generation/fencing requirements.
- Retained open **#22863** as a critical shutdown/drain fixture and corroborated current main's fixed 5-second BackgroundTaskManager shutdown grace constant.
- Preserved shutdown request, transport teardown, in-flight route completion, workflow snapshot settlement, process/tool termination and external-effect settlement as separate states.
- Mapped suspend/resume/restart workflow snapshots and preserved them as continuation evidence rather than complete ACL checkpoint authority.
- Inspected tool HITL and durable approval context; retained the 1.64.0 **#22841** fix restoring request context/workspace for durable per-tool approval functions.
- Derived the pattern of persisting policy inputs/context and re-evaluating current protected policy after resume rather than serializing policy closures.
- Retained open **#19911** as an A2A invocation-authorization fixture: protocol-level pre-agent authorization is separate from agent/tool approval after invocation.
- Mapped memory into message history, working memory, semantic recall, observational memory and one-call context; preserved each as a separate trust/state plane.
- Preserved resource/thread IDs as memory namespaces rather than authenticated principal identity.
- Retained current docs' model-context projection behavior where working memory, cross-thread semantic recall and observational memory can enter system messages; preserved prompt position as representation rather than source authority.
- Retained open **#20148** as a storage-level thread-creation atomicity fixture; existence-check/upsert is insufficient under concurrency.
- Retained open **#22188** as a PostgreSQL observational-memory generation race; process-local locks are insufficient for multi-instance writers.
- Retained open **#19740** as an observational-memory terminal-turn reuse fixture, bounded to reported package revisions unless separately reverified.
- Mapped subagent delegation memory isolation: fresh thread per delegation, deterministic resource suffixing, inherited/shared Memory options and explicit sharing behavior.
- Mapped Mastra's broad sandbox-provider abstraction and 1.64.0 unified `workingDirectory` plus warm repo templates; preserved provider/template/repo provenance as executable environment identity.
- Preserved workspace and sandbox as separate authority domains.
- Verified Ollama/local/OpenAI-compatible model-routing evidence and retained exact router/provider/runtime/model/context/tool profile as capability identity rather than nominal support.
- Mapped MCP and A2A as protocol interoperability below ACL-owned origin/auth/effect/verifier authority.
- Reviewed broad storage domains, observability and `@mastra/evals/vitest`; retained evaluation/tracing as evidence rather than independent verifier authority.
- Preserved telemetry/outbound behavior as part of offline/restricted deployment identity.
- Wrote detailed findings, 40 candidate invariants, 18 regression fixtures, reuse candidates, primary sources and explicit non-conclusions to `projects/mastra.md`.
- Appended 16 Task 31 Mastra records to `catalog-part2.jsonl`; original 257-record `catalog.jsonl` remains untouched.
- No new project beyond Mastra, framework winner selection, model-role assignment, 32K benchmark execution or ACL/Vera implementation/governance change was begun.

## Highest-value Mastra findings for later comparison
1. **Durable recovery is explicitly at-least-once.** Current docs warn it reissues LLM and tool calls.
2. **Multi-replica recovery is not writer-fenced by Mastra.** External leader election/lease is still required.
3. **#22863 is a critical shutdown/settlement fixture.** Transport teardown can precede full evented-work settlement.
4. **Durable state is multi-plane.** Snapshot, stream cache, run status, observer registry and effects are not interchangeable.
5. **Request-context-aware approval is strong reference material.** The 1.64.0 durable fix restores request context for per-tool approval checks after resume.
6. **Policy should be re-evaluated after resume.** Persist inputs/evidence, not executable policy closures.
7. **A2A invocation authorization is distinct from downstream tool approval.** #19911 preserves that boundary.
8. **Mastra's memory decomposition is valuable for Vera.** Message history, working memory, semantic recall and observational memory should stay distinct.
9. **Prompt placement is not source authority.** Several memory planes can be projected into system messages.
10. **#20148 and #22188 reinforce storage-bound atomicity.** Thread identity and memory-generation uniqueness must be enforced where data is authoritative.
11. **Process-local locks are not distributed fencing.**
12. **#19740 is a lifecycle-state fixture.** A reachable memory turn may already be terminal and invalid for reuse.
13. **Sandbox abstraction is useful but does not normalize security semantics.** Provider/template identity remains explicit.
14. **Warm repo templates are executable/provenance-bearing artifacts.**
15. **Local Ollama/provider support remains exact-profile qualification.**
16. **Mastra remains below ACL-owned effect identity/idempotency, distributed fencing, principal/credential authority, sandbox policy, checkpoint acceptance and independent verification; Vera retains epistemic truth/provenance authority.**

## Queue status
- Tasks 5–31 project deep research are complete through **Mastra**.
- The ranked active-project queue established earlier in the campaign has now been researched through its final listed project.
- **No Task 32 project is inferred or authorized.** Await a separately assigned next research boundary.

## Next task

No next task is currently assigned.

Await explicit instruction before beginning any additional project, cross-project synthesis, benchmark design/execution, architecture selection or implementation work.

## Stop point

Task 31 ended after Mastra's current package/runtime identity, durable/evented agents, workflow state/recovery, shutdown/cancellation settlement, multi-replica recovery fencing, approval context, A2A invocation gating, memory planes/concurrency/lifecycle, subagent memory isolation, sandbox/workspace architecture, local-model routing, protocol surfaces, storage semantics, observability/evaluation and current 2026 failures were deeply researched. No further project or synthesis task was begun.
