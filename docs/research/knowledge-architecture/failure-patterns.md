# Knowledge Architecture Failure / Anti-Pattern Ledger

This ledger records concrete failure patterns that should become later design-review questions and regression/acceptance fixtures. A pattern is not a claim that every project exhibits the failure.

## Status meanings

- **observed** — directly supported by one task's current source and/or concrete issue/reproduction.
- **reinforced** — independently observed across multiple campaign tasks.
- **qualified** — retained with important scope limitations.
- **retired** — no longer useful as an architecture-level pattern.

## Ledger

| ID | Failure / anti-pattern | Evidence/tasks | Status |
|---|---|---|---|
| KA-F-001 | Treating a namespace/group/session/user string as authorization. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-5 Mastra resource/thread routing vs FGA/A2A authority | reinforced |
| KA-F-002 | Mutable shared knowledge-scope/routing/filter state survives across concurrent or reused requests. | KA-1 Graphiti #1676/#1840; KA-4 LlamaIndex #22701/current `VectorMemoryBlock` | reinforced |
| KA-F-003 | LLM contradiction output directly retires/rewrites current knowledge without structural trust/verification/restraint guardrails. | KA-1 Graphiti #1728/#1666; KA-3 Letta Code #4029 | reinforced |
| KA-F-004 | “Newest statement/evidence wins” used as a universal truth rule. | KA-1 Graphiti; KA-3 Letta Code #4029 | reinforced |
| KA-F-005 | Relationship name + shared endpoint treated as sufficient proof of supersession. | KA-1 Graphiti PR #1729 | observed |
| KA-F-006 | Entity identity is collapsed without a durable merge decision/lineage record. | KA-1 Graphiti | observed |
| KA-F-007 | Deterministic exact identity evidence is hidden behind a semantic candidate threshold. | KA-1 Graphiti #1734 | observed |
| KA-F-008 | One generic memory search mixes current and retired/superseded facts without an explicit current-only intent. | KA-1 Graphiti #1645; KA-2 Mem0 | reinforced |
| KA-F-009 | Derived semantic summaries/graph objects become the only practically searchable representation. | KA-1 Graphiti #1427 | observed |
| KA-F-010 | One invalid/mismatched vector can fail a whole semantic query. | KA-1 Graphiti #1328/#1505 | observed |
| KA-F-011 | Derived indexes start asynchronously without a tracked readiness/settlement lifecycle. | KA-1 Graphiti #1643 | observed |
| KA-F-012 | Deletion relies on incomplete/best-effort provenance traversal and leaves derived/orphan records or planes outside the lifecycle operation. | KA-1 Graphiti #1083; KA-2 Mem0 #4863; KA-4 LlamaIndex PropertyGraph deletion; KA-5 Mastra Mongo prune/semantic-vector cleanup separation | reinforced |
| KA-F-013 | Project/package/version/feature name is treated as sufficient deployment identity. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra local-vs-gateway OM/backend lease capability/docs-source delta | reinforced |
| KA-F-014 | Ontology/schema changes are interpreted as if old records were automatically migrated. | KA-1 Graphiti; KA-2 Mem0 | reinforced |
| KA-F-015 | A metadata/filter capability is assumed usable for governance because it exists in a high-level object model/API. | KA-1 Graphiti; KA-2 Mem0; KA-4 LlamaIndex backend/filter semantics | reinforced |
| KA-F-016 | Retrieval relevance/fusion score is treated as confidence/truth. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex | reinforced |
| KA-F-017 | Persistent/retrieved text is promoted into privileged policy/instruction channels. | KA-1 Graphiti; KA-2 Mem0; KA-5 Mastra OM/working-memory system-message placement | reinforced |
| KA-F-018 | Conceptual temporal correctness is assumed to hold on every backend without qualification. | KA-1 Graphiti #1625 | observed |
| KA-F-019 | Successful storage/API/history/commit/run/barrier operation is treated as proof that a multi-plane mutation settled successfully. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra async memory/vector work + `settled()` caveat | reinforced |
| KA-F-020 | Source provenance is recorded while transformation provenance is discarded or incomplete. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra source ranges without complete per-claim derivation profile | reinforced |
| KA-F-021 | “Hybrid retrieval” uses one retriever as the sole candidate-entry gate, so other signals can only rerank what it already found. | KA-2 Mem0 | observed |
| KA-F-022 | A hard filter is accepted by the high-level query layer but silently dropped by a backend adapter. | KA-2 Mem0 #7214 | observed |
| KA-F-023 | A pre-write snapshot or read-modify-write projection is treated as a concurrency-safe integrity guarantee. | KA-2 Mem0 #6515/#6243; KA-5 Mastra #20148/#22188 and merged title-clobber PR #21041/legacy `patchThread` path | reinforced |
| KA-F-024 | Partial batch fallback continues with the intended record set instead of the successfully settled subset. | KA-2 Mem0 | observed |
| KA-F-025 | Persistent user/agent/domain scope supplies transient episode/task context without a sufficiently explicit episode boundary, contaminating unrelated work. | KA-2 Mem0 #7195; KA-5 Mastra experimental resource-scope warning that one thread may continue another thread's unfinished work | reinforced |
| KA-F-026 | “Delete memory/index data” is interpreted as privacy erasure while plaintext history/docstore/other planes remain. | KA-2 Mem0; KA-4 LlamaIndex `delete_ref_doc`/multi-plane storage; KA-5 Mastra demonstrates separate OM/vector/primary retention planes but does not itself prove a privacy-erasure claim | reinforced |
| KA-F-027 | A derived synthesis/summary/projection is treated as exhaustive despite coverage, type, scope or extraction gaps. | KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex graph extraction/citation projections | reinforced |
| KA-F-028 | Failed background consolidation retries the same evidence without stable semantic idempotency, producing duplicate/divergent abandoned mutation attempts. | KA-3 Letta Code #4266 | observed |
| KA-F-029 | Restore/replacement deletes the last active good state before the replacement is copied/indexed and validated. | KA-3 Letta Code #4195; KA-4 LlamaIndex `update_ref_doc()`/#22733 | reinforced |
| KA-F-030 | A derived viewer/count collapses unavailable, legacy-only or filtered representation into false canonical absence. | KA-3 Letta Code #3845/#3894 | observed |
| KA-F-031 | Persistent memory that influences execution is omitted from declared replay/task identity. | KA-3 Letta Code #3807 | observed |
| KA-F-032 | Runtime/live transcript/event projection is assumed to be complete/canonical evidence despite profile-dependent record loss, merging or lifecycle errors. | KA-3 Letta Code #4248; KA-5 Mastra current #23271 live-vs-persisted span-merging fix | reinforced |
| KA-F-033 | Source/document identity is reused as derivative uniqueness, collapsing one-to-many derived records. | KA-4 LlamaIndex #22133 (fixed in current source) | observed |
| KA-F-034 | A re-chunked/presentation derivative copies its parent identity or stale locators, causing downstream dedup/source-addressing errors. | KA-4 LlamaIndex #22537 (fixed in current source) | observed |
| KA-F-035 | A mutable external-resource locator fingerprint is treated as if it were an observed content/version digest. | KA-4 LlamaIndex current `MediaResource.hash` path/URL-only semantics | observed |
| KA-F-036 | Untrusted metadata/resource identifiers are interpolated into backend query syntax rather than safely bound/qualified, changing retrieval/deletion predicate semantics. | KA-4 LlamaIndex #22475/current PGVector source | observed |
| KA-F-037 | A background-work join/quiescence barrier that intentionally absorbs child failures is treated as proof that all intended knowledge mutations reconciled successfully. | KA-5 Mastra current `Memory.settled()` contract | observed |
| KA-F-038 | A replayed historical approval/suspension event is surfaced as currently actionable without validating current durable authority state. | KA-5 Mastra open PR #22767 regression evidence | observed |

## KA-5 recurrence update

- KA-F-001 gains Mastra evidence that resource/thread/task identifiers route state while authenticated invocation/FGA/approval remain separate authority planes.
- KA-F-012 gains strong current Mastra retention/deletion evidence: Mongo memory pruning excludes observational-memory records from age-based retention and cannot reach semantic-recall vectors; ordinary vector cleanup can continue after primary deletion returns.
- KA-F-013 gains Mastra evidence from local-vs-gateway OM, adapter feature differences and the current source/documentation transition around recovery leasing.
- KA-F-017 gains Mastra recurrence because persistent OM/working-memory content can be placed in system-message context without becoming policy authority.
- KA-F-019 gains Mastra settlement evidence: agent/delete operations can return before background memory/vector work; the drain barrier itself does not propagate child failures.
- KA-F-023 moves from **observed** to **reinforced**. Mastra independently documents/fixes a stale read-backfill-write title race and retains current thread/OM concurrency issue evidence.
- KA-F-025 moves from **observed** to **reinforced**, narrowly scoped to episode/task-context contamination. Mastra's resource-scope docs explicitly warn that one thread may continue unfinished work from another; this is not an argument against legitimate resource-level facts.
- KA-F-032 moves from **observed** to **reinforced** via Mastra #23271, where a live transcript projection merged later-step content under a reused provider-local block ID while the persisted reload shape was correct.
- KA-F-037 is new: quiescence/join completion is distinct from successful reconciliation.
- KA-F-038 is new: historical replayed interactive state must not be promoted to current authority/actionability without checking current durable state.
- Open PR #22767 is recorded as current failure evidence, not as a merged fix.
- Mastra's emerging recovery-lease infrastructure is treated as a profile-dependent positive mechanism and source/docs consistency issue, not a new failure ID.
- No failure pattern is promoted to a final architecture rule.

## How to use this ledger later

These patterns should become hostile scenarios or acceptance tests where applicable. Later revisits should reuse existing IDs for independent recurrence and create new IDs only for materially distinct failure mechanisms.
