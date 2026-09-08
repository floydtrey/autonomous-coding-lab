# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** KA-5 complete; stopped before next task  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

## Governing plan

Read `CAMPAIGN_PLAN.md` before doing any work in this campaign.

The completed Tasks 1–31 project-by-project campaign remains historical evidence. Do not restart it and do not rewrite its catalogs.

## Completed tasks

### KA-1 — Graphiti Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/graphiti.md`

### KA-2 — Mem0 Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/mem0.md`

### KA-3 — Letta Code Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/letta-code.md`

### KA-4 — LlamaIndex Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/llamaindex.md`

### KA-5 — Mastra Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/mastra.md`

Cumulative ledgers updated:

- `invariants.md`
- `failure-patterns.md`

## KA-5 boundary and verification

- Re-read root research governance, campaign plan/state, cumulative invariant/failure ledgers and the historical Task 31 Mastra report.
- Verified the clean ACL starting branch head at `44a7de7b87ae66fa78431de5085701f9f937f343` before KA-5 writes.
- Reverified `mastra-ai/mastra` current `main` at `d7bd6f7a91daf528f34d628faede4a916421b0dd`, with `@mastra/core` version `1.65.0-alpha.9`.
- Compared current upstream with the Task 31 revision `685616780ea68e55c23c5980c17d5eee9a8f0aa9` rather than assuming yesterday's report was still exact.
- Inspected current memory overview, Observational Memory docs/source, OM record and buffered-chunk schemas, source-message recall ranges, `asOf` observation reconstruction, working memory/extractors, semantic-recall derivation, context construction, storage capability flags, Mongo retention behavior, deletion/vector cleanup, `Memory.settled()`, durable-agent recovery and current/recent issue/PR evidence.
- Rechecked current issue/PR evidence including #22863, #20148, #22188, #19740, #19911, merged #21041, merged #22960, open #22767 and current-head fix #23271.
- Evaluated Mastra against all 26 campaign evidence questions.
- Treated open PR #22767 as current failure evidence, not as a merged fix.
- Treated current recovery leasing as profile-dependent/in transition: source and merged #22960 show lease/fencing machinery, while current docs still retain an older no-distributed-lock warning. No universal backend guarantee was claimed.
- Updated recurrence rather than duplicating existing Graphiti/Mem0/Letta/LlamaIndex concepts.
- Added **no new invariant IDs** because Mastra's strongest lessons fit existing candidate families.
- Moved KA-I-032 and KA-I-036 from single-task candidates to cross-project **reinforced** status.
- Added 2 materially distinct Mastra-derived failure patterns: KA-F-037–038.
- Moved KA-F-023, KA-F-025 and KA-F-032 from single-task observed patterns to cross-project **reinforced** status.
- Added Mastra recurrence to multiple existing identity, deletion, profile, prompt-boundary, settlement and transformation-provenance failure families.
- Did not select Mastra, Observational Memory, a vector store, SQL/NoSQL store, final schema, ontology, retrieval engine or conceptual architecture.
- Did not modify historical `catalog.jsonl`, `catalog-part2.jsonl`, root research state or historical project reports.
- Did not begin LangGraph research.

## Highest-value KA-5 findings

1. **Mastra has multiple distinct memory/knowledge planes.** Raw messages, working memory, semantic vectors, OM active observations, buffered observations, reflection generations, extracted values and model-visible context are not one state.
2. **Raw evidence can remain addressable after compression.** OM retrieval mode stores observation-group ranges back to source message IDs and can recall the underlying raw messages.
3. **Current, historical, buffered and pending memory are explicit lifecycle states.** OM generations/history and buffered chunks provide a useful positive model for derived-state lifecycle.
4. **Background consolidation should activate atomically with source consumption.** `swapBufferedToActive()` is documented to activate derived content and move source message IDs into the observed set together; this independently reinforces KA-I-032.
5. **Source, derivative and presentation identity remain distinct.** OM chunks have their own IDs/source message IDs, while current #23271 shows how reused provider-local block IDs corrupted live presentation even though persisted representation was different; this independently reinforces KA-I-036.
6. **OM provides good coarse provenance but not a complete epistemic claim envelope.** Source ranges, generations, config and timestamps do not encode verified/inferred/disputed/confidence/applicability for every remembered proposition.
7. **OM `asOf` is projection-visibility time, not general world-valid time.** Observation availability and semantic validity must remain distinct.
8. **Reflection replaces the current compact projection while preserving history.** Mutation history does not prove semantic correctness of the model's merge/compression decisions.
9. **Resource and thread are routing/scope identities, not authenticated principals.** FGA, tool approval and A2A pre-execution authorization remain separate authority planes.
10. **Resource-scope memory can legitimately share user-level knowledge while contaminating transient task state.** Current docs explicitly warn that one thread may continue another thread's unfinished work.
11. **Context construction is separate from retrieval.** `Memory.getContext()` combines OM, working memory, recent/unobserved history, other-thread context and continuation reminders with explicit channel placement.
12. **Prompt position does not upgrade provenance.** OM/working memory can enter a system-message channel while remaining user/model-derived content.
13. **Structured extractors improve shape, not truth.** Extracted values are model-derived projections requiring derivation provenance when they matter to automation.
14. **Backend capability flags are semantic.** OM support, partial updates, message deletion, resource memory, clone behavior and retention differ across adapters.
15. **Backward compatibility can preserve weaker consistency.** Current `patchThread()` explicitly notes that legacy adapters can retain the old title-clobbering race; merged #21041 documents the stale read/backfill/write failure.
16. **Thread/OM uniqueness still needs storage-level atomicity.** #20148 and #22188 remain current concurrency evidence; #19740 remains lifecycle-state evidence.
17. **Delete/retention is multi-plane.** Current Mongo pruning excludes OM from age-based retention and cannot reach semantic vectors; vector cleanup can continue after primary deletion returns.
18. **`Memory.settled()` is a quiescence barrier, not a successful-reconciliation certificate.** It waits for tracked background work but documented child failures do not reject it. This becomes KA-F-037.
19. **Historical replay is not current authority.** Open PR #22767 reports stale approval/suspension events becoming actionable after settlement unless current durable suspension state is checked. This becomes KA-F-038.
20. **Live event projections can disagree with persisted evidence.** Current head #23271 fixes a live/persisted transcript-span mismatch and independently reinforces KA-F-032.
21. **Durable recovery remains at-least-once for model/tool execution.** Snapshots support continuation but do not replace effect identity/idempotency/settlement.
22. **Recovery leasing has materially evolved since Task 31.** Current source and merged #22960 show dedicated lease/fencing support, but public docs still include the older multi-replica race warning. Exact source/backend/profile identity is therefore essential.
23. **Mastra is strongest as evidence for memory lifecycle, context and execution boundaries, not as a complete epistemic truth substrate.** Typed world relationships, structured negative/unknown states and general applicability remain outside the ordinary memory model.

## Cumulative ledger changes after KA-5

### Invariants

- KA-I-032 becomes **reinforced** with independent Mastra buffered-activation/source-consumption evidence.
- KA-I-036 becomes **reinforced** with independent Mastra derivative/source identity plus current live-projection identity evidence.
- KA-I-033 and KA-I-034 gain adjacent Mastra evidence but remain candidates because the stronger formulations are not independently established in full.
- No new invariant ID is added.

### Failure patterns

- KA-F-023 becomes **reinforced** with Mastra read-modify-write/concurrency evidence.
- KA-F-025 becomes **reinforced**, narrowly scoped to persistent-domain context contaminating transient episode/task work.
- KA-F-032 becomes **reinforced** by current Mastra #23271 live-versus-persisted projection evidence.
- KA-F-037 is new: a join/quiescence barrier that absorbs child failures is mistaken for successful reconciliation.
- KA-F-038 is new: replayed historical approval/suspension evidence is treated as current actionable authority without validating current durable state.

## Current task

**No task is currently assigned.**

The campaign is stopped after KA-5.

## Planned next candidate

**KA-6 — LangGraph Knowledge-Architecture Revisit**

This is the next planned revisit in `CAMPAIGN_PLAN.md`, but it is **not authorized merely by queue order**.

Do not begin KA-6 until the user explicitly instructs the next bounded task to start.

When authorized, LangGraph must be researched as its own task and then stopped before Google ADK.

## Prohibited work at this state

Do not:

- begin LangGraph or any later revisit without explicit authorization;
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
4. ~~KA-4 LlamaIndex~~ — complete
5. ~~KA-5 Mastra~~ — complete
6. KA-6 LangGraph — not started / not authorized
7. Google ADK
8. Microsoft Agent Framework
9. OpenAI Agents SDK
10. Model Context Protocol

After these, the campaign plan requires a bounded coverage scan before any additional project revisit is promoted.

## Stop point

KA-5 Mastra research is complete and saved. No LangGraph research, cross-project synthesis, gap research, retrieval-requirements task, architecture selection or implementation work has begun.
