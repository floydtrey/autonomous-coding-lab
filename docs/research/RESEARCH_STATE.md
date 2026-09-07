# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 29 — LlamaIndex deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Catalog layout
- `docs/research/catalog.jsonl` remains the original catalog through Task 24 with 257 records and is intentionally left unchanged.
- `docs/research/catalog-part2.jsonl` begins with Task 25 OpenCode records and now contains Task 26 Mem0, Task 27 smolagents, Task 28 Agno and Task 29 LlamaIndex records; it remains the append target for subsequent research tasks unless deliberately consolidated later.
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

## Queue status
- Tasks 5–29 project deep research are complete through **LlamaIndex**.
- **CrewAI (#26 in ranked active-project queue): next task only.** No CrewAI research was begun in Task 29.
- **Mastra** remains after CrewAI.

## Next task

Deep-research **CrewAI** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant agent/crew/flow architecture, model/provider/local-model support, tools/code execution, memory/knowledge, state/persistence, concurrency/writer ownership, retries/cancellation/timeouts, security/credentials/content trust, protocol integrations, observability/evaluation, current failures, reproducibility and reusable mechanisms. Save report/catalog-part2/state/watchlist, make a research-only checkpoint, and stop before Mastra.

## Stop point

Task 29 ended after LlamaIndex's current package/runtime split, agents and multi-agent handoffs, Workflow Context/Memory separation, HITL/replay effects, cancellation settlement, tool/error/effect semantics, MCP workflow instance isolation, memory/session isolation, state projection freshness, CodeAct executor boundary, RAG/index derived-state lifecycle, local/provider integrations, protocol projections, observability/evaluation and current/recent 2026 failures were deeply researched. No CrewAI research, cross-project framework winner selection, 32K benchmark execution or ACL/Vera implementation/governance change was begun.