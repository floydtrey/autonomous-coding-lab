# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 30 — CrewAI deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Catalog layout
- `docs/research/catalog.jsonl` remains the original catalog through Task 24 with 257 records and is intentionally left unchanged.
- `docs/research/catalog-part2.jsonl` begins with Task 25 OpenCode records and now contains Task 26 Mem0, Task 27 smolagents, Task 28 Agno, Task 29 LlamaIndex and Task 30 CrewAI records; it remains the append target for subsequent research tasks unless deliberately consolidated later.
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

## Task 30 work completed
- Began from finalized Task 29 branch head `d21f23b971fe504e6c17ab808da61bbaff229520` and verified the branch had not drifted before Task 30 writes.
- Re-read README, PROCESS, RESEARCH_STATE, sources and watchlist governance and kept Mastra out of scope.
- Confirmed latest observed stable CrewAI release **1.15.20** and current main `1b855b4ff97d3fc8bf6dc0981fed5f0999a7cd81`; current component pins remain 1.15.20, so exact commit remains behavior-bearing identity.
- Mapped Agent, Crew/Process and Flow as distinct orchestration layers; retained sequential versus hierarchical manager topology as benchmark identity.
- Preserved Flow same-ID resume versus `restore_from_state_id` fork as separate continuation transitions.
- Mapped current pre/post tool hook system and retained it as a strong deterministic effect-mediation seam: host code can mutate arguments before execution, block with `False`/`HookAborted`, and redact/transform model-visible output after execution while raw result remains separately available.
- Preserved hook/process registry state as non-durable policy machinery rather than authenticated principal, approval, sandbox or effect-settlement authority.
- Retained open **#5802** as the primary effect-retry fixture: an external effect can succeed, later task handling can fail, and retry can execute the same payment/email/trade-style tool again without a durable idempotency guard.
- Derived stable pre-effect logical IDs, durable claims/idempotency and reconciliation-before-replay requirements.
- Retained closed **#6706** plus current main source as a checkpoint-schema fixture: dict-state restore still clears current state before applying stored state, so older snapshots can erase defaults introduced by newer code.
- Derived explicit checkpoint schema/code/harness revision and migration compatibility requirements.
- Retained closed **#4168** as a concurrency/accounting fixture: threaded async tasks sharing one agent can misattribute sibling token usage when per-task deltas are reconstructed from shared aggregate counters.
- Preserved invocation-local evidence capture rather than post-hoc subtraction from shared mutable totals.
- Retained open **#6439** as a callback/config integration regression family while bounding it to the reported 1.15.2a2 paths unless separately reverified on 1.15.20.
- Inspected current unified `Memory`: LLM-driven scope/category/importance analysis, composite semantic/recency/importance ranking, consolidation, pluggable storage, background single-worker save pool, pending-write tracking, `drain_writes()` and `close()`.
- Preserved memory submission, persistence success/failure and run completion as separate lifecycle states; current source explicitly emits save-failure events without failing the originating task/crew/flow.
- Retained open **#5057** and corroborated current LiteAgent source: recalled memory record content is appended to the system message, providing a persistent lower-trust-content-to-higher-authority prompt-injection fixture.
- Preserved memory scope/importance/consolidation as advisory epistemic metadata rather than authenticated truth/authority.
- Kept Knowledge/RAG, Memory, Flow operational state, run outputs and trusted policy/configuration as separate trust/state planes.
- Verified current documentation deprecates built-in `allow_code_execution`/`code_execution_mode`, notes removal of `CodeInterpreterTool`, and recommends dedicated sandbox services such as E2B/Modal; retained open #6180 as production execution-boundary follow-up evidence.
- Verified direct local Ollama example and preserved exact CrewAI adapter + runtime/model + function-calling model + context/summarization/tool profile as local capability identity.
- Mapped current MCP connection and A2A delegation event surfaces; preserved MCP server/transport/tool request, A2A context/turn/status, Crew task and ACL external effect as separate identities.
- Preserved A2A `completed`/`input_required`/`failed` as remote lifecycle evidence rather than local acceptance authority.
- Reviewed CrewAI observability/evaluation surfaces as useful operational evidence while preserving verifier/effect settlement as ACL-owned.
- Wrote detailed findings, 40 candidate invariants, 18 regression fixtures, reuse candidates, sources and explicit non-conclusions to `projects/crewai.md`.
- Appended 14 Task 30 CrewAI records to `catalog-part2.jsonl`; original 257-record `catalog.jsonl` remains untouched.
- No Mastra research, cross-project framework winner selection, CrewAI adoption, model/runtime assignment, 32K benchmark execution or ACL/Vera implementation/governance change was begun.

## Highest-value CrewAI findings for later comparison
1. **Crew, Flow and Agent are different runtime profiles.** Sequential/hierarchical manager topology is behavior-bearing harness identity.
2. **Flow resume and fork are explicitly different.** This is useful reference material for continuation versus branch semantics.
3. **Pre-tool hooks are a strong deterministic seam.** Arguments can be host-stamped and execution can fail closed before effects.
4. **#5802 is a critical effect-idempotency fixture.** Retry must not imply authority to replay an uncertain external effect.
5. **Checkpoint compatibility requires schema/version identity.** #6706 plus current source shows old dict snapshots can erase newer defaults.
6. **Concurrent shared aggregates are not per-attempt evidence.** #4168 is a clean accounting race fixture.
7. **Unified Memory has explicit asynchronous settlement.** `drain_writes()/close()` separate save submission from durability.
8. **Run success can coexist with memory-save failure.** Continuation-critical persistence must therefore have ACL/Vera-owned required/degraded semantics.
9. **#5057 is a persistent prompt-injection fixture.** Retrieved memory remains untrusted even when a framework places it in a system message.
10. **Memory consolidation is not truth management.** LLM-inferred scope, importance and consolidation remain advisory.
11. **Built-in code execution is being deprecated rather than treated as the security boundary.** Realized sandbox profile remains external deployment identity.
12. **Local Ollama support is real but conditional.** Exact adapter/runtime/model/tool/context profile requires independent qualification.
13. **MCP and A2A add lifecycle evidence, not authority.** Protocol handles/statuses remain separate from ACL task/effect IDs and verifier acceptance.
14. **Observability is evidence, not pass/fail authority.**
15. **CrewAI remains below ACL-owned task/effect identity, idempotency/reconciliation, containment, credentials, writer fencing, checkpoint compatibility and independent verification; Vera retains epistemic memory authority.**

## Queue status
- Tasks 5–30 project deep research are complete through **CrewAI**.
- **Mastra (#27 in ranked active-project queue): next task only.** No Mastra research was begun in Task 30.

## Next task

Deep-research **Mastra** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant agent/workflow architecture, model/provider/local-model support, tools/code execution, memory/RAG/state persistence, concurrency/writer ownership, retries/cancellation/timeouts, security/credentials/content trust, protocol integrations, observability/evaluation, current failures, reproducibility and reusable mechanisms. Save report/catalog-part2/state/watchlist, make a research-only checkpoint, and stop at the next campaign boundary.

## Stop point

Task 30 ended after CrewAI's current Agent/Crew/Process/Flow layering, Flow persistence/resume/fork semantics, retry/effect idempotency, concurrent shared-state accounting, pre/post tool hooks, code-execution/sandbox transition, unified Memory architecture and settlement, persistent prompt-injection risk, provider/local-model support, MCP/A2A surfaces, credentials/content trust, observability/evaluation and current/recent 2026 failures were deeply researched. No Mastra research, cross-project framework winner selection, 32K benchmark execution or ACL/Vera implementation/governance change was begun.
