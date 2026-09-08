# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** KA-6 complete; stopped before next task  
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

### KA-6 — LangGraph Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/langgraph.md`

Cumulative ledgers updated:

- `invariants.md`
- `failure-patterns.md`

## KA-6 boundary and verification

- Re-read root research governance, campaign plan/state, cumulative invariant/failure ledgers and the historical Task 7 LangGraph report.
- Verified the clean ACL starting branch head at `c223920e625305fea8a8b7a7f04b2ffaa40088d2` before KA-6 writes.
- Reverified `langchain-ai/langgraph` current `main` at `81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1`, with `langgraph` version `1.2.11`.
- Confirmed that this is the same upstream source revision/package version used by the historical Task 7 report; KA-6 is therefore a deeper knowledge-substrate analysis plus new issue evidence, not an upstream implementation-delta study.
- Inspected current checkpointer and Store separation, checkpoint lineage/pending writes, runtime identity/authenticated-server-user separation, Store record/filter/index/TTL semantics, DeltaChannel reconstruction, serializer behavior and context/replay boundaries.
- Rechecked official current LangGraph Persistence and Memory documentation.
- Rechecked historical high-impact current/open issue evidence including #8039, #8458, #8579, #8653, #8582, #8531 and #7206.
- Added post-historical issue evidence including #8837, #8836, #8835, #8834, #8833, #8831, #8829, #8826, #8822 and #8821.
- Evaluated LangGraph against all 26 campaign evidence questions.
- Treated open issues as scoped failure evidence, not as proof of universal production frequency or maintainer-confirmed behavior for untested backends.
- Retained #8832 only as qualified API/backend evidence because the issue's correction notes the raw `batch()`/`PutOp` validation bypass is intentionally treated as an internal-path behavior in current tests.
- Updated recurrence rather than duplicating existing Graphiti/Mem0/Letta/LlamaIndex/Mastra concepts.
- Moved KA-I-033 from single-task candidate to cross-project **reinforced** status.
- Added 3 materially distinct LangGraph-derived invariant candidates: KA-I-038–040.
- Moved KA-F-031 and KA-F-038 to cross-project **reinforced** status.
- Added 4 materially distinct LangGraph-derived failure patterns: KA-F-039–042.
- Did not select LangGraph, a Store, checkpointer, database, final schema, ontology, retrieval engine or execution framework.
- Did not modify historical `catalog.jsonl`, `catalog-part2.jsonl`, root research state or historical project reports.
- Did not begin Google ADK research.

## Highest-value KA-6 findings

1. **Checkpointers and Stores are explicitly different persistence systems.** Checkpointers persist thread/replay state; Stores persist application-defined long-term cross-thread memory. This is strong evidence against collapsing replayable execution state and semantic knowledge into one object.
2. **Execution identity is rich but not semantic identity.** Thread, run, checkpoint, task, attempt and interrupt IDs are useful recovery identities but do not identify people/devices/assertions/resources.
3. **Namespace/thread IDs are not principals.** Current `Runtime` separately exposes authenticated `ServerInfo.user`, while Store namespaces and runtime `user_id` values remain application routing/scope.
4. **Store is not a complete epistemic truth substrate.** Its ordinary record has namespace/key/value plus record timestamps and optional semantic score, not required verified/inferred/disputed/confidence/world-valid-time/supersession/authority-use fields.
5. **Store record time is not world-valid time.** `created_at`/`updated_at` describe persistence history, not the time interval in which a proposition was true.
6. **Semantic Store search remains derived retrieval.** Embedding profile/field selection/backend and `SearchItem.score` do not encode truth or authority.
7. **Backend semantics alter realized retrieval behavior.** #8831 shows default ordering/pagination divergence; #8829 shows unsupported filter requests can fail loudly on one backend and silently look like no-match on others; #8833 shows pending-write retry conflict behavior can differ by saver.
8. **Read-only retrieval can become an implicit write.** #8835 plus current `InMemoryStore` source show returned nested objects can alias canonical memory, so context-redaction/projection mutations silently alter stored knowledge. This creates KA-I-038 and KA-F-039.
9. **Value equality is not semantic round-trip fidelity.** #8826 plus current serializer source show a timezone-aware datetime can compare equal after checkpoint restoration while losing `ZoneInfo`/`fold`, causing future DST arithmetic to differ. This creates KA-I-039 and KA-F-040.
10. **Live and replay state semantics must agree.** #8821 plus current `DeltaChannel` source show `update()` and `replay_writes()` can produce different states for the same overwrite+write batch. This creates KA-I-040 and KA-F-041.
11. **Derived index identity can be one-to-many.** #8822 shows one deduplicated semantic derivation may need to attach to several distinct record targets, reinforcing source/derived identity separation.
12. **Long-term knowledge revision is not pinned by a checkpoint.** Store is separately injected from checkpoint state, so deterministic replay that reads Store knowledge requires explicit pinned-revision, read-set, fresh-read or non-deterministic semantics. This independently reinforces KA-I-033 and KA-F-031.
13. **Checkpoint, pending writes and external effects are separate settlement planes.** #8039 demonstrates crash recovery can replay or reexecute based on which persistence component settled first; checkpoints are not an exactly-once effect ledger.
14. **Partial control-flow settlement is real.** #8834 shows a state write can settle while a conditional router fails, then resume returns normally with no pending task. This reinforces mutation/transition settlement tracking.
15. **Approval/resume identity must be exact and durable.** #8579 shows scalar ambiguity with multiple interrupts; #8836 shows zero-match ID maps can silently no-op; these require fail-closed target semantics.
16. **Consumed approval state must stop being actionable.** #8837 shows a consumed resume payload can remain in durable pending writes and answer a later interrupt. This independently reinforces KA-F-038.
17. **Untracked input and resumability are separate claims.** #8582 shows a failed task can remain replayable while runtime-only input needed to reproduce it is intentionally absent.
18. **Production wiring profile matters.** #8653 shows config-injected checkpointer hydration can differ from graph-attached local/dev topology and can commit a wrongly empty state.
19. **Hierarchical replay identity must survive forks.** #8458 shows a parent fork can regenerate child task/namespace identity and orphan the explicitly selected subgraph checkpoint.
20. **Retention requires dependency closure.** Current checkpoint contracts warn that DeltaChannel state may depend on ancestor checkpoints/writes; #8531 proposes fail-closed pruning when that closure cannot be preserved.
21. **Deletion requires fencing.** #7206 shows stale pre-delete writers can resurrect a deleted thread unless deletion retires an identity generation/tombstone.
22. **TTL is not semantic expiration or privacy erasure.** Store TTL is backend-dependent and best-effort physical retention behavior.
23. **Checkpoint history is execution history, not epistemic history.** LangGraph still lacks a general current/historical/false/unknown/disputed/superseded truth model for Store records.
24. **Execution graph relationships are not world relationships.** Control-flow edges, checkpoint parent links and namespace hierarchy are distinct from canonical typed world/provenance/authority relations.
25. **Prompt placement does not upgrade provenance.** Retrieved long-term memory and tool descriptions remain content even when included in model-visible privileged-looking prompt channels.
26. **LangGraph is strongest here as evidence for execution/replay lineage and persistence boundaries, not as a complete general knowledge ontology.**

## Cumulative ledger changes after KA-6

### Invariants

- KA-I-033 becomes **reinforced** with independent LangGraph checkpointer-vs-Store replay evidence.
- KA-I-038 is new: canonical reads used for retrieval/projection/context must not mutate canonical state through incidental aliasing.
- KA-I-039 is new: persistence round-trips must preserve behavior-bearing semantic metadata, not only current equality.
- KA-I-040 is new: live transition and replay/reconstruction semantics must be equivalent for the same persisted transition evidence.
- Existing namespace/principal, temporal, retrieval, derived-state, backend, authority, deletion, schema/profile, provenance, context, settlement and identity invariants gain additional LangGraph evidence.

### Failure patterns

- KA-F-031 becomes **reinforced** with LangGraph's separately mutable Store outside checkpoint replay identity.
- KA-F-038 becomes **reinforced** with #8837 consumed-resume replay evidence.
- KA-F-039 is new: read-only retrieval/projection aliases canonical stored memory and silently mutates it.
- KA-F-040 is new: serialization loses behavior-bearing semantics while preserving apparent value equality.
- KA-F-041 is new: live state transition and replay reconstruction disagree for the same persisted writes.
- KA-F-042 is new: authority-bearing resume/approval targets no current request but silently no-ops instead of failing closed.
- Existing deletion, realized-profile, backend-query, settlement and transformation-provenance families gain additional recurrence.

## Current task

**No task is currently assigned.**

The campaign is stopped after KA-6.

## Planned next candidate

**KA-7 — Google ADK Knowledge-Architecture Revisit**

This is the next planned revisit in `CAMPAIGN_PLAN.md`, but it is **not authorized merely by queue order**.

Do not begin KA-7 until the user explicitly instructs the next bounded task to start.

When authorized, Google ADK must be researched as its own task and then stopped before Microsoft Agent Framework.

## Prohibited work at this state

Do not:

- begin Google ADK or any later revisit without explicit authorization;
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
6. ~~KA-6 LangGraph~~ — complete
7. KA-7 Google ADK — not started / not authorized
8. Microsoft Agent Framework
9. OpenAI Agents SDK
10. Model Context Protocol

After these, the campaign plan requires a bounded coverage scan before any additional project revisit is promoted.

## Stop point

KA-6 LangGraph research is complete and saved. No Google ADK research, cross-project synthesis, gap research, retrieval-requirements task, architecture selection or implementation work has begun.
