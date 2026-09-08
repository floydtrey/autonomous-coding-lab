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
| KA-F-001 | Treating a namespace/group/session/user string as authorization. | KA-1 Graphiti | Data can be accessed or routed under a caller-chosen scope without authenticated principal/purpose enforcement. | observed |
| KA-F-002 | Mutable shared storage-routing state across concurrent requests. | KA-1 Graphiti #1676/#1840 | Silent cross-domain/cross-tenant data corruption and provenance/privacy failure. | observed |
| KA-F-003 | LLM contradiction output directly retires current knowledge without structural/relation/trust guardrails. | KA-1 Graphiti #1728/#1666 | False contradictions silently hide true current facts; missed contradictions preserve stale facts. | observed |
| KA-F-004 | “Newest statement wins” used as a universal truth rule. | KA-1 Graphiti temporal invalidation analysis | Low-trust newer evidence can replace stronger/authoritative older evidence. | observed |
| KA-F-005 | Relationship name + shared endpoint treated as sufficient proof of supersession. | KA-1 Graphiti PR #1729 | Additive many-to-many relationships can be mistaken for replaceable current-state relationships. | observed |
| KA-F-006 | Entity identity is collapsed without a durable merge decision/lineage record. | KA-1 Graphiti current `add_episode`/dedup path | False merge becomes difficult to audit, reverse or propagate correctly. | observed |
| KA-F-007 | Deterministic exact identity evidence is hidden behind a semantic candidate threshold. | KA-1 Graphiti #1734 | Same entity can fragment into multiple canonical records because it never reaches exact-match logic. | observed |
| KA-F-008 | One generic memory search mixes current and retired facts. | KA-1 Graphiti #1645/current MCP search | Model must infer liveness and may act on historical data as if current. | observed |
| KA-F-009 | Derived semantic summaries/graph objects become the only practically searchable representation. | KA-1 Graphiti #1427 | Exact source literals/evidence can survive only in raw content that retrieval cannot efficiently reach. | observed |
| KA-F-010 | One invalid/mismatched vector can fail a whole semantic query. | KA-1 Graphiti #1328/#1505 | Corrupt derived state makes otherwise valid canonical knowledge unavailable. | observed |
| KA-F-011 | Derived indexes start asynchronously without a tracked readiness/settlement lifecycle. | KA-1 Graphiti #1643 | First use/reset/shutdown races with index creation; errors appear detached from initiating operation. | observed |
| KA-F-012 | Deletion relies on incomplete provenance links and silently leaves derived/orphan records. | KA-1 Graphiti #1083 | “Forget” appears successful while retrievable or sensitive derivatives survive. | observed |
| KA-F-013 | Project/package version is treated as sufficient deployment identity. | KA-1 Graphiti #1656/#1108 | Actual tool schema, routing, storage layout or capability differs from expected source behavior. | observed |
| KA-F-014 | Ontology/schema changes are interpreted as if old records were automatically migrated. | KA-1 Graphiti custom-type migration guidance | Historical records are read under semantics they were never derived with. | observed |
| KA-F-015 | A metadata field is assumed usable for governance because it exists in an object model. | KA-1 Graphiti `episode_metadata` source inspection | Policy depends on metadata that may not persist, query or project end-to-end. | observed |
| KA-F-016 | Retrieval relevance score is treated as confidence/truth. | KA-1 Graphiti hybrid search | Highly similar stale/false/untrusted records outrank authoritative but less similar records. | observed |
| KA-F-017 | Persistent/retrieved text is promoted into privileged policy/instruction channels. | KA-1 Graphiti/Zep security guidance | Prompt injection or memory poisoning gains authority through placement rather than provenance. | observed |
| KA-F-018 | Conceptual temporal correctness is assumed to hold on every backend without qualification. | KA-1 Graphiti #1625 | Point-in-time queries return future data despite correct-looking high-level semantics. | observed |
| KA-F-019 | Successful storage/API operation is treated as deletion/derived-state settlement proof. | KA-1 Graphiti deletion/index evidence | Partial cleanup or pending maintenance is mistaken for a reconciled final state. | observed |
| KA-F-020 | Source provenance is recorded while transformation provenance is discarded. | KA-1 Graphiti merge/invalidation/summary analysis | System can explain where input came from but not why canonical identity/truth changed. | observed |

## How to use this ledger later

These patterns should become hostile scenarios or acceptance tests where applicable. Later project revisits should not merely add duplicates; they should cite an existing ID and record independent evidence. Repeated independent occurrence is stronger architecture evidence than one framework’s design choice.

## KA-1 boundary

All entries above are Graphiti-derived or Graphiti-corroborated and therefore remain single-source campaign evidence. No cross-project reinforcement has been claimed yet.
