# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** KA-3 complete; stopped before next task  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

## Governing plan

Read `CAMPAIGN_PLAN.md` before doing any work in this campaign.

The completed Tasks 1–31 project-by-project campaign remains historical evidence. Do not restart it and do not rewrite its catalogs.

## Completed tasks

### KA-1 — Graphiti Knowledge-Architecture Revisit

**Status:** complete.

Detailed report:

- `projects/graphiti.md`

### KA-2 — Mem0 Knowledge-Architecture Revisit

**Status:** complete.

Detailed report:

- `projects/mem0.md`

### KA-3 — Letta Code Knowledge-Architecture Revisit

**Status:** complete.

Detailed report:

- `projects/letta-code.md`

Cumulative ledgers updated:

- `invariants.md`
- `failure-patterns.md`

### KA-3 boundary and verification

- Re-read root research governance, campaign plan/state and the historical Task 18 Letta Code report.
- Verified ACL starting branch head at `4aece181bab2720bba77db5a256c7a4ae068d7d4` before KA-3 writes.
- Reverified current `letta-ai/letta-code` `main` at `2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8`, package version `0.31.13`.
- Compared the current upstream revision to the historical Letta research revision `701f2a5367828847313876c735ade27b9df97689`; current main was eight commits ahead and the core memory architecture remained materially recognizable.
- Revisited current MemFS prompts, memory filesystem/worktree/Git and local prompt-compilation source, recall prompts, shared-memory guidance, and current/recent issue evidence relevant to the campaign matrix.
- Evaluated Letta Code against all 26 campaign evidence questions.
- Updated recurrence in the cumulative invariant/failure ledgers rather than duplicating existing Graphiti/Mem0 concepts.
- Added 5 materially distinct Letta-derived invariant candidates (KA-I-031–035).
- Added 5 materially distinct Letta-derived failure patterns (KA-F-028–032).
- Independently reinforced 21 existing invariant families with Letta evidence.
- Newly reinforced KA-I-027, KA-I-028 and KA-I-029 from single-task candidates to cross-project evidence.
- Newly reinforced KA-F-003 and KA-F-004 with Letta conflict-resolution evidence and added further recurrence to KA-F-013, KA-F-016, KA-F-019, KA-F-020 and KA-F-027.
- Did not select Letta Code, Git, a filesystem schema, a graph database, vector database, storage engine, final ontology, retrieval engine or final conceptual model.
- Did not modify historical `catalog.jsonl`, `catalog-part2.jsonl`, root research state or historical project reports.
- Did not begin LlamaIndex research.

### Highest-value KA-3 findings

1. **Persistent agent identity and conversation identity are separate.** Letta models a long-lived `agent_id` with multiple `conversation_id`s and per-agent durable memory.
2. **Recall evidence and curated memory are distinct planes.** Conversation history remains separately searchable from editable future-facing MemFS knowledge.
3. **Active context is revisioned.** Local compilation reads committed Git `HEAD`, excludes pending uncommitted files and records `memfsRevision` in the compiled-prompt result.
4. **Git mutation provenance is not epistemic provenance.** Commits/diffs explain repository change, not truth, confidence, verification, world-valid time or authority.
5. **Background reflection is an integration state machine.** Explicit finalize statuses determine whether transcript input is consumed and whether context is recompiled.
6. **Committed is not the same as integrated or synchronized.** #4266 shows valid reflection commits discarded at finalize; #4249 shows local memory commits can fail subsequent sync/refresh.
7. **Reflection retries require semantic idempotency.** #4266 documents duplicate/triplicate dangling commits from repeated attempts over the same transcript evidence.
8. **The current latest-evidence conflict heuristic is unsafe as a universal truth rule.** #4029 reports a 120-run prompt evaluation with 50% failure on restraint cases, including safety-critical downgrade and confabulated merge examples.
9. **Memory, skills and harness authority are different state classes.** Security/compliance rules and secrets that must not depend on model recall belong outside editable memory.
10. **Shared memory is a separate organization-owned domain.** Multiple agents can attach independent shared Git repositories, but #4267 identifies missing fine-grained user/role/task projection and governed write semantics.
11. **Context construction is not retrieval.** Committed MemFS, recall search, external resources, shared repositories and skills enter context through different mechanisms.
12. **Derived views can disagree with canonical state.** #3845/#3894 show false zero/incomplete file views while committed MemFS remains intact.
13. **Restore must be transactional.** #4195 and current source show active memory is removed before the replacement backup is copied/validated.
14. **Persistent memory is part of execution/replay identity.** #3807 documents deterministic-orchestration problems when inherited memory is not a declared task input.
15. **Record history is not bitemporal truth.** Git/message timestamps are strong transaction history but do not encode a general world-valid interval model.
16. **Structured epistemic states remain necessary.** Plain text cannot reliably distinguish explicit, inferred, verified, disputed, unknown or historically true knowledge.
17. **Letta is a strong mechanism reference rather than a complete general knowledge substrate.** The observed gaps remain evidence for later synthesis, not a framework-selection decision.

## Current task

**No task is currently assigned.**

The campaign is stopped after KA-3.

## Planned next candidate

**KA-4 — LlamaIndex Knowledge-Architecture Revisit**

This is the next planned revisit in `CAMPAIGN_PLAN.md`, but it is **not authorized merely by queue order**.

Do not begin KA-4 until the user explicitly instructs the next bounded task to start.

When authorized, LlamaIndex must be researched as its own task and then stopped before Mastra.

## Prohibited work at this state

Do not:

- begin LlamaIndex or any later revisit without explicit authorization;
- synthesize the final conceptual schema;
- select a database/storage engine;
- implement retrieval;
- create embeddings;
- migrate the old catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers.

## Planned revisit queue

For orientation only; queue order is not authorization:

1. ~~KA-1 Graphiti~~ — complete
2. ~~KA-2 Mem0~~ — complete
3. ~~KA-3 Letta Code~~ — complete
4. KA-4 LlamaIndex — not started / not authorized
5. Mastra
6. LangGraph
7. Google ADK
8. Microsoft Agent Framework
9. OpenAI Agents SDK
10. Model Context Protocol

After these, the campaign plan requires a bounded coverage scan before any additional project revisit is promoted.

## Stop point

KA-3 Letta Code research is complete and saved. No subsequent project, cross-project synthesis, gap research, retrieval-requirements task, architecture selection or implementation work has begun.
