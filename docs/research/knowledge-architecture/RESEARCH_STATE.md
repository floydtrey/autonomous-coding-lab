# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** KA-2 complete; stopped before next task  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

## Governing plan

Read `CAMPAIGN_PLAN.md` before doing any work in this campaign.

The completed Tasks 1–31 project-by-project campaign remains historical evidence. Do not restart it and do not rewrite its catalogs.

## Completed tasks

### KA-1 — Graphiti Knowledge-Architecture Revisit

**Status:** complete.

Detailed report:

- `projects/graphiti.md`

KA-1 established the initial candidate-invariant and failure-pattern ledgers and stopped before Mem0.

### KA-2 — Mem0 Knowledge-Architecture Revisit

**Status:** complete.

Detailed report:

- `projects/mem0.md`

Cumulative ledgers updated:

- `invariants.md`
- `failure-patterns.md`

### KA-2 boundary and verification

- Re-read root research governance, campaign plan/state and the prior historical Mem0 report.
- Reverified current `mem0ai/mem0` `main` at `dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3`, package version `2.0.20`.
- Revisited current Python OSS source, current first-party migration/Platform documentation, and current/recent issues/PRs only where they affected the knowledge-architecture evidence matrix.
- Evaluated Mem0 against all 26 campaign evidence questions.
- Updated recurrence status in the invariant/failure ledgers rather than duplicating Graphiti-derived concepts.
- Added 6 materially distinct invariant candidates/concepts (KA-I-025–030), with KA-I-025 immediately marked reinforced because the epistemic-basis gap was independently observed in KA-1 and KA-2.
- Added 7 materially distinct Mem0 failure/anti-pattern entries (KA-F-021–027).
- Reinforced 19 existing candidate invariants with independent Mem0 evidence.
- Reinforced 10 existing failure/anti-pattern classes with independent Mem0 evidence.
- Did not select Mem0, a vector database, a graph database, a storage engine, a final ontology, a retrieval engine, or a final conceptual model.
- Did not modify historical `catalog.jsonl`, `catalog-part2.jsonl`, root research state or completed historical project reports.
- Did not begin Letta Code research.

### Highest-value KA-2 findings

1. **Current OSS v3 is ADD-only on the inferred write path.** Semantic capture is now intentionally separated from later update/delete/current-state lifecycle decisions.
2. **Mem0 OSS is primarily a derived semantic-memory plane, not a durable raw-evidence corpus.** The SQLite message buffer retains only recent source messages per scope, and mutation history does not provide general source/evidence/derivation provenance.
3. **Attribution is not epistemic state.** User/assistant attribution is useful, but explicit statements, recommendations, researched claims, inferences, verified facts and disputed facts still require a separate epistemic envelope.
4. **Scope IDs are not principals.** Current code fixes historical scope-metadata mutation/injection bugs; Platform docs also explicitly distinguish user/agent/run/app scopes from graph entities.
5. **Persistent scope and conversational episode identity differ.** #7195 shows a last-k context cache keyed only by user/agent/run can mix unrelated sessions.
6. **Managed Dream provides useful non-destructive lifecycle semantics.** Supersede, Merge and Synthesis preserve prior records, while `latest_only` makes current-state retrieval an explicit intent.
7. **Derived synthesis needs coverage metadata.** Dream Synthesis is forward-only, scope-restricted, threshold-gated and scheduled; derivative absence cannot mean source absence.
8. **Graph Memory is a retrieval association graph, not a typed relationship truth model.** It links entity mentions/memories and contributes ranking; it explicitly does not create typed entity relationships.
9. **“Hybrid retrieval” must define candidate semantics.** OSS calculates semantic, BM25 and entity signals, but only semantic results enter the candidate set and semantic thresholding happens before combination.
10. **Backend filter semantics are correctness/security behavior.** Current OpenSearch source/#7214 show high-level advanced predicates can be silently dropped while a narrower filter still runs.
11. **Retrieval score is not truth.** Mem0’s combined semantic/BM25/entity score and Platform Memory Decay can encode topical relevance and access recency/frequency in the same public ranking.
12. **Concurrency still breaks integrity above the backend.** #6515 demonstrates hash-dedup TOCTOU duplicates; #6243 demonstrates lost entity links from read-modify-write races.
13. **Current source exposes a direct settlement mismatch.** Individual fallback vector inserts may fail, yet history, entity maintenance and returned ADD results are still built from the intended record list.
14. **Derived entity state is best-effort.** Failures are intentionally non-fatal, but #4863 shows stale derived links can survive update/delete; readiness/reconciliation must therefore be explicit.
15. **Delete, privacy erasure and audit retention are separate operations.** Vector memories can be removed while plaintext old memory remains in SQLite history; #6512 documents the resulting retention concern.
16. **v2→v3 is a semantic migration.** Extraction, graph behavior, retrieval defaults, API contracts and backend/language behavior changed materially; a project/package label is not sufficient derivation identity.
17. **Remembered policy/configuration text cannot own authority.** #4926’s deterministic-policy retrieval request is evidence that critical policy must not depend on similarity, but the ACL/Vera answer remains protected policy/configuration outside ordinary semantic-memory authority.
18. **Model/prompt/parser profile is part of memory provenance.** #5901/#6724 show malformed but plausible model output shapes can alter ingestion correctness, especially in local/open-compatible deployments.

## Current task

**No task is currently assigned.**

The campaign is stopped after KA-2.

## Planned next candidate

**KA-3 — Letta Code Knowledge-Architecture Revisit**

This is the next planned revisit in `CAMPAIGN_PLAN.md`, but it is **not authorized merely by queue order**.

Do not begin KA-3 until the user explicitly instructs the next bounded task to start.

When authorized, Letta Code must be researched as its own task and then stopped before LlamaIndex.

## Prohibited work at this state

Do not:

- begin Letta Code or any later revisit without explicit authorization;
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
3. KA-3 Letta Code — not started / not authorized
4. LlamaIndex
5. Mastra
6. LangGraph
7. Google ADK
8. Microsoft Agent Framework
9. OpenAI Agents SDK
10. Model Context Protocol

After these, the campaign plan requires a bounded coverage scan before any additional project revisit is promoted.

## Stop point

KA-2 Mem0 research is complete and saved. No subsequent project, cross-project synthesis, gap research, retrieval-requirements task, architecture selection or implementation work has begun.
