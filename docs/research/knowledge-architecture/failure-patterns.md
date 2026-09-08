# Knowledge Architecture Failure / Anti-Pattern Ledger

This ledger records concrete failure patterns that should become design-review questions and later regression/acceptance fixtures.

A pattern is not a claim that every project exhibits the failure. Each entry remains scoped to its cited evidence until later tasks reinforce or qualify it.

## Status meanings

- **observed** — directly supported by current source and/or a concrete issue/reproduction in one campaign task.
- **reinforced** — independently observed across multiple campaign tasks.
- **qualified** — retained with important scope limitations.
- **retired** — no longer useful as an architecture-level pattern.

## Ledger

| ID | Failure / anti-pattern | Evidence/tasks | Architecture risk | Status |
|---|---|---|---|---|
| KA-F-001 | Treating a namespace/group/session/user string as authorization. | KA-1 Graphiti; KA-2 Mem0 | Caller-chosen routing/scope identifiers are confused with authenticated principal authority; Mem0’s fixed scope-metadata bugs show why scope fields require protected ownership. | reinforced |
| KA-F-002 | Mutable shared storage-routing state across concurrent requests. | KA-1 Graphiti #1676/#1840 | Silent cross-domain/cross-tenant data corruption and provenance/privacy failure. Mem0 KA-2 has concurrency failures but not this exact shared-routing pattern. | observed |
| KA-F-003 | LLM contradiction output directly retires current knowledge without structural/relation/trust guardrails. | KA-1 Graphiti #1728/#1666 | False contradictions silently hide true current facts; missed contradictions preserve stale facts. Mem0 Platform contradiction internals were not inspected, so KA-2 does not reinforce this exact mechanism. | observed |
| KA-F-004 | “Newest statement wins” used as a universal truth rule. | KA-1 Graphiti temporal invalidation analysis | Low-trust newer evidence can replace stronger/authoritative older evidence. | observed |
| KA-F-005 | Relationship name + shared endpoint treated as sufficient proof of supersession. | KA-1 Graphiti PR #1729 | Additive many-to-many relationships can be mistaken for replaceable current-state relationships. | observed |
| KA-F-006 | Entity identity is collapsed without a durable merge decision/lineage record. | KA-1 Graphiti current `add_episode`/dedup path | False merge becomes difficult to audit, reverse or propagate correctly. | observed |
| KA-F-007 | Deterministic exact identity evidence is hidden behind a semantic candidate threshold. | KA-1 Graphiti #1734 | Same entity can fragment into multiple canonical records because it never reaches exact-match logic. | observed |
| KA-F-008 | One generic memory search mixes current and retired/superseded facts without an explicit current-only intent. | KA-1 Graphiti #1645; KA-2 Mem0 Dream read modes | Models/callers can treat history as current. Mem0 mitigates this by labeling lifecycle state and exposing `latest_only`, but its default read intentionally remains history-inclusive. | reinforced |
| KA-F-009 | Derived semantic summaries/graph objects become the only practically searchable representation. | KA-1 Graphiti #1427 | Exact source literals/evidence can survive only in raw content that retrieval cannot efficiently reach. Mem0 KA-2 reinforces the need for source evidence generally, but not this exact Graphiti episode-search failure. | observed |
| KA-F-010 | One invalid/mismatched vector can fail a whole semantic query. | KA-1 Graphiti #1328/#1505 | Corrupt derived state makes otherwise valid canonical knowledge unavailable. | observed |
| KA-F-011 | Derived indexes start asynchronously without a tracked readiness/settlement lifecycle. | KA-1 Graphiti #1643 | First use/reset/shutdown races with index creation; errors appear detached from initiating operation. | observed |
| KA-F-012 | Deletion relies on incomplete/best-effort provenance links and silently leaves derived/orphan records. | KA-1 Graphiti #1083; KA-2 Mem0 #4863 | “Delete” can leave semantic/entity derivatives that remain stale or retrievable. | reinforced |
| KA-F-013 | Project/package version is treated as sufficient deployment identity. | KA-1 Graphiti #1656/#1108; KA-2 Mem0 v2→v3 + OSS/Platform profiles | Actual tool schema, storage layout, graph/retrieval/temporal semantics or backend behavior differs from what the project name/version shorthand implies. | reinforced |
| KA-F-014 | Ontology/schema changes are interpreted as if old records were automatically migrated. | KA-1 Graphiti custom-type migration guidance; KA-2 Mem0 v2→v3 migration | Historical records/indexes are read under semantics they were never derived with. | reinforced |
| KA-F-015 | A metadata/filter capability is assumed usable for governance because it exists in an object model or high-level API. | KA-1 Graphiti `episode_metadata`; KA-2 Mem0 #7214 | Policy depends on metadata predicates that may not persist or may be silently weakened by the concrete backend. | reinforced |
| KA-F-016 | Retrieval relevance score is treated as confidence/truth. | KA-1 Graphiti hybrid search; KA-2 Mem0 hybrid scoring/Memory Decay | Highly similar, frequently accessed or graph-proximate records can outrank stronger evidence without being more true. | reinforced |
| KA-F-017 | Persistent/retrieved text is promoted into privileged policy/instruction channels. | KA-1 Graphiti/Zep trust boundary; KA-2 Mem0 agent-config extraction + #4926/#5195 | Prompt injection or ordinary remembered text gains authority through persistence/pinning rather than authenticated policy provenance. | reinforced |
| KA-F-018 | Conceptual temporal correctness is assumed to hold on every backend without qualification. | KA-1 Graphiti #1625 | Point-in-time queries return future data despite correct-looking high-level semantics. Mem0 KA-2 supplies related backend-semantic evidence but not an independent temporal-backend failure. | observed |
| KA-F-019 | Successful storage/API/history operation is treated as proof that deletion or a multi-plane mutation settled. | KA-1 Graphiti deletion/index evidence; KA-2 Mem0 current partial-write path | Partial cleanup/write or pending/best-effort derived maintenance is mistaken for a reconciled final state. | reinforced |
| KA-F-020 | Source provenance is recorded while transformation provenance is discarded or incomplete. | KA-1 Graphiti merge/invalidation/summary analysis; KA-2 Mem0 extraction/history/link analysis | System may know speaker/source-ish metadata but not why a semantic memory, lifecycle decision or derived link took its current form. | reinforced |
| KA-F-021 | “Hybrid retrieval” uses one retriever as the sole candidate-entry gate, so other signals can only rerank what it already found. | KA-2 Mem0 current `_search_vector_store`/`score_and_rank` | Exact lexical/entity evidence can never surface if semantic candidate generation omits it, despite BM25/entity signals being present. | observed |
| KA-F-022 | A hard filter is accepted by the high-level query layer but silently dropped by a backend adapter. | KA-2 Mem0 #7214/current OpenSearch adapter | Eligibility/sensitivity/current-state constraints appear enforced while the query actually runs with weaker predicates. | observed |
| KA-F-023 | A pre-write snapshot or read-modify-write projection is treated as a concurrency-safe integrity guarantee. | KA-2 Mem0 #6515/#6243 | Concurrent writers create duplicate canonical records or lose derived links without an error. | observed |
| KA-F-024 | Partial batch fallback continues with the intended record set instead of the successfully settled subset. | KA-2 Mem0 current Phase 6–8 source | API returns/history/derived indexes can contain phantom success for records whose actual storage insert failed. | observed |
| KA-F-025 | Persistent user/agent/domain scope is reused as transient context-cache episode identity. | KA-2 Mem0 #7195 | Unrelated conversations under the same long-lived scope contaminate extraction context and can leak irrelevant/sensitive prior content. | observed |
| KA-F-026 | “Delete memory” is interpreted as privacy erasure while plaintext mutation history or other planes intentionally remain. | KA-2 Mem0 current delete/history + #6512 | A user/host believes personal data was forgotten while the audit/history plane still retains the prior content. | observed |
| KA-F-027 | A derived synthesis/summary is treated as exhaustive despite explicit enablement, scope, threshold or cadence gaps. | KA-2 Mem0 Dream Synthesis | Missing information in a derivative is mistaken for missing information in source/canonical evidence. | observed |

## How to use this ledger later

These patterns should become hostile scenarios or acceptance tests where applicable. Later project revisits should not merely add duplicates; they should cite an existing ID and record independent evidence. Repeated independent occurrence is stronger architecture evidence than one framework’s design choice.

## KA-2 recurrence update

After Mem0:

- **10 prior failure classes are independently reinforced:** KA-F-001, 008, 012–017, 019 and 020.
- KA-F-021–027 are new Mem0-derived observed patterns.
- Graphiti-specific mechanism failures remain single-task evidence where Mem0 did not independently reproduce the same mechanism.
- No failure pattern has been promoted to a final architecture rule.
