# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 26 — Mem0 deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Catalog layout
- `docs/research/catalog.jsonl` remains the original catalog through Task 24 with 257 records and is intentionally left unchanged.
- `docs/research/catalog-part2.jsonl` begins with Task 25 OpenCode records and now contains Task 26 Mem0 records; it remains the append target for subsequent research tasks unless deliberately consolidated later.
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

## Task 26 work completed
- Began from finalized Task 25 branch head `48ca4e0e54c1522bff0487b0e51770a484cbfe6c`.
- Re-read research governance/process/state/source boundaries and kept smolagents out of scope.
- Confirmed current Mem0 Python package identity on `main` as **2.0.20** and treated managed Platform, Python OSS, TypeScript OSS and self-hosted server as distinct behavior/security profiles.
- Mapped current memory construction/retrieval architecture across fact/metadata, vector and entity/graph planes; retained raw evidence, extracted facts, summaries, entity relations and policy as distinct Vera trust classes.
- Preserved `user_id`/`agent_id`/`run_id` as useful scope metadata but not authenticated principal identity.
- Retained 2026 P0 identity-scope fixtures #6277/#6342/#6367/#6655 and integration race #4359 as authorization/isolation regression inputs.
- Retained open/current concurrency fixtures #6515/#6531 and #6243 plus fixed #5577 to demonstrate pipeline-level and entity-store TOCTOU classes.
- Derived idempotency + atomic/CAS/transaction/fencing requirements for authoritative multi-writer memory rather than trusting pre-write search dedup.
- Retained delete/erasure fixtures #4863, #3245, #6627, #6512 and #5869, separating canonical deletion, derived-index cleanup, history retention and full erasure settlement.
- Preserved audit/history retention as separate from privacy/user-forget semantics and required read-back/reconciliation for high-value delete effects.
- Retained #4187 as a paper-versus-implementation temporal/supersession fixture and rejected chronological recency as an authority hierarchy.
- Treated persistent memory content as untrusted data; retained #5195/#5331/#5349/#5434 as poisoning-defense evidence and #5127 as a server control-plane authorization fixture.
- Verified official local Ollama pathways but preserved local-memory capability as exact Mem0+LLM+runtime+prompt/schema+embedder+vector-store behavior; retained #6724 as a malformed local-model extraction fixture.
- Retained very recent 2.0.19/main extraction-context fixtures #7195/#7198 for stale cross-session buffer contamination and silent extraction loss.
- Bounded current benchmark claims to managed Platform/proprietary optimizations and fixed retrieval budgets rather than OSS guarantees.
- Wrote detailed findings, candidate Vera/ACL invariants, regression fixtures, reuse candidates, primary sources and explicit non-conclusions to `projects/mem0.md`.
- Appended 12 Task 26 Mem0 records to `catalog-part2.jsonl`; the original 257-record `catalog.jsonl` remains untouched.
- No smolagents research, cross-project winner selection, memory-backend adoption, benchmark execution, model assignment or ACL/Vera implementation/governance change was begun.

## Highest-value Mem0 findings for later comparison
1. **Scope is not principal identity.** `user_id`/`agent_id`/`run_id` are useful memory partitions but must be host-authorized and stamped; recent P0 bugs show why metadata/model input cannot own that boundary.
2. **Stored memory is a claim, not truth.** Evidence, extracted facts, summaries, relations, confidence/trust and supersession state remain separate.
3. **Concurrency is a first-class memory correctness problem.** Current duplicate-add and entity-link TOCTOU issues require idempotency and atomic/CAS/transaction/fencing semantics for authoritative writers.
4. **Delete is multi-plane settlement.** Primary memory, vector/index, entity/graph, history/audit, caches and backups can diverge; SDK success is not proof of erasure.
5. **Audit retention and user forgetting are separate policies.** Current history-retention issues make this explicit.
6. **Temporal recency is not authority.** Supersession should preserve evidence and require risk-appropriate verification rather than automatic newest-wins behavior.
7. **Persistent memory remains untrusted model content.** Retrieval must not elevate stored instructions into system/tool/credential authority.
8. **Memory construction context is its own scope-bearing state.** Recent buffer issues show correct database namespace does not prevent extraction-context contamination.
9. **Managed and OSS are separate profiles.** Current strong benchmark numbers explicitly include managed proprietary optimizations and cannot be assigned to OSS.
10. **Local provider support is profile-specific.** Official Ollama support is real, but #6724 shows local structured-output robustness still needs exact-model testing.
11. **SDK/server generation is security identity.** Python, TypeScript, managed Platform and self-hosted server have had different bugs and guarantees.
12. **Mem0 remains below Vera-owned provenance/truth policy, authenticated authorization, writer fencing, erasure settlement, credential/security authority and independent verification.**

## Queue status
- Tasks 5–26 project deep research are complete through **Mem0**.
- **smolagents (#23 in ranked active-project queue): next task only.** No smolagents research was begun in Task 26.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **smolagents** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL-relevant agent/runtime architecture, tool/code execution boundaries, local-model/provider support, sandboxing and interpreter/executor modes, memory/state, delegation/multi-agent control, retries/cancellation/timeouts, MCP/protocol integration, security/prompt-injection/credential boundaries, observability/evaluation, current failures, reproducibility and reusable mechanisms. Save report/catalog-part2/state/watchlist, make a research-only commit/checkpoint, and stop before Agno.

## Stop point

Task 26 ended after Mem0's current architecture, identity/scope model, write/retrieval and derived storage planes, concurrency/writer risks, delete/erasure lifecycle, temporal/supersession semantics, poisoning/security boundary, local-provider support, extraction-context state, evaluation caveats and current 2026 failures were deeply researched. No smolagents research, memory-system winner selection, 32K benchmark execution or ACL/Vera implementation/governance change was begun.
