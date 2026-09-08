# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** KA-1 complete; stopped before next task  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

## Governing plan

Read `CAMPAIGN_PLAN.md` before doing any work in this campaign.

The completed Tasks 1–31 project-by-project campaign remains historical evidence. Do not restart it and do not rewrite its catalogs.

## Completed task

### KA-1 — Graphiti Knowledge-Architecture Revisit

**Status:** complete.

Detailed report:

- `projects/graphiti.md`

Cumulative ledgers established/updated:

- `invariants.md`
- `failure-patterns.md`

### KA-1 boundary and verification

- Re-read root research governance, campaign plan/state and the prior Task 20 Graphiti report.
- Reverified `getzep/graphiti` current `main` at `b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d`, the same revision used by the original Task 20 report.
- Revisited current source, official Graphiti documentation, current issue/PR evidence and managed Zep security guidance only where it corroborated an outer trust boundary.
- Evaluated Graphiti against all 26 campaign evidence questions.
- Added 24 candidate invariants and 20 failure/anti-pattern entries; every entry remains single-project campaign evidence and is **not** promoted to a final architectural rule.
- Did not select Graphiti/Zep, a graph database, a storage engine, an ontology, a vector store or a final conceptual model.
- Did not modify historical `catalog.jsonl`, `catalog-part2.jsonl`, root research state or completed project reports.
- Did not begin Mem0 research.

### Highest-value KA-1 findings

1. Raw episodic evidence, resolved entities, semantic relationships and summaries are distinct planes and should not be collapsed.
2. Graphiti’s bitemporal-like `valid_at`/`invalid_at` plus `created_at`/`expired_at` separation is highly reusable, but backend point-in-time behavior must be regression-tested.
3. Graphiti provides provenance from facts to episodes, but merge/invalidation/summary/embedding transformations need stronger first-class lineage for a general knowledge substrate.
4. The core fact model is temporally rich but lacks a general epistemic envelope for source class, trust, confidence, verification, dispute, negative/unknown state and actionability.
5. Invalidation is an authority-bearing semantic transition. #1728/#1666 show both false and missed contradiction failure modes.
6. PR #1729 exposes a deeper requirement: safe supersession depends on relationship semantics/cardinality, not merely a relation name and shared endpoint.
7. Entity resolution is also authority-bearing. Current deterministic dedup can collapse identities while normal `add_episode` discards returned duplicate-pair evidence; #1734 demonstrates the complementary false-split failure.
8. Current, historical, conflict and raw-evidence retrieval should be separate retrieval contracts rather than one generic memory search.
9. Hybrid semantic/BM25/graph ranking is useful discovery but is not truth, confidence or authority.
10. `group_id` is namespace/routing metadata, not authenticated principal identity. #1676/#1840 show mutable shared routing can silently corrupt cross-group data under concurrency.
11. Derived embeddings/indexes/summaries require explicit generation/profile/readiness/reconciliation state; corrupt derived state must not become canonical data loss.
12. Delete/forget is a multi-plane reconciliation process; provenance gaps can leave semantic orphans after source deletion.
13. Custom ontology changes do not retroactively migrate old records; schema/ontology generation must remain interpretable historically.
14. Realized deployment identity requires exact source/build/backend/tool-schema/profile; package/project names are insufficient.
15. Provenance/security metadata cannot be relied on until its write/read/filter/migration path is end-to-end verified.
16. Retrieved/persistent memory remains untrusted content and never grants execution authority.

## Current task

**No task is currently assigned.**

The campaign is stopped after KA-1.

## Planned next candidate

**KA-2 — Mem0 Knowledge-Architecture Revisit**

This is the next planned revisit in `CAMPAIGN_PLAN.md`, but it is **not authorized merely by queue order**.

Do not begin KA-2 until the user explicitly instructs the next bounded task to start.

When authorized, Mem0 must be researched as its own task and then stopped before Letta Code.

## Prohibited work at this state

Do not:

- begin Mem0 or any later revisit without explicit authorization;
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
2. KA-2 Mem0 — not started / not authorized
3. Letta Code
4. LlamaIndex
5. Mastra
6. LangGraph
7. Google ADK
8. Microsoft Agent Framework
9. OpenAI Agents SDK
10. Model Context Protocol

After these, the campaign plan requires a bounded coverage scan before any additional project revisit is promoted.

## Stop point

KA-1 Graphiti research is complete and saved. No subsequent project, cross-project synthesis, gap research, retrieval-requirements task, architecture selection or implementation work has begun.
