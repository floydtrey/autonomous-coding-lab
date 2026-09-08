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
| KA-F-001 | Treating a namespace/group/session/user string as authorization. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-5 Mastra; KA-6 LangGraph; KA-7 Google ADK; KA-8 Microsoft Agent Framework | reinforced |
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
| KA-F-012 | Deletion relies on incomplete/best-effort provenance or dependency traversal and leaves derived/orphan/reconstructability failures. | KA-1 Graphiti #1083; KA-2 Mem0 #4863; KA-4 LlamaIndex current PropertyGraph deletion; KA-6 LangGraph #8531/#7206/current DeltaChannel prune contract | reinforced |
| KA-F-013 | Project/package version is treated as sufficient deployment identity. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph #8653/backend/profile behavior; KA-7 Google ADK; KA-8 Microsoft Agent Framework | reinforced |
| KA-F-014 | Ontology/schema changes are interpreted as if old records were automatically migrated. | KA-1 Graphiti; KA-2 Mem0 | reinforced |
| KA-F-015 | A metadata/filter/query capability is assumed usable for governance because it exists in a high-level object model/API, without qualifying backend semantics. | KA-1 Graphiti; KA-2 Mem0; KA-4 LlamaIndex; KA-6 LangGraph #8829/#8831 | reinforced |
| KA-F-016 | Retrieval relevance/fusion score is treated as confidence/truth. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-6 LangGraph; KA-7 Google ADK; KA-8 Microsoft Agent Framework | reinforced |
| KA-F-017 | Persistent/retrieved text is promoted into privileged policy/instruction channels. | KA-1 Graphiti; KA-2 Mem0; KA-5 Mastra; KA-6 LangGraph adjacent Store/tool-description evidence | reinforced |
| KA-F-018 | Conceptual temporal correctness is assumed to hold on every backend without qualification. | KA-1 Graphiti #1625 | observed |
| KA-F-019 | Successful storage/API/history/commit operation is treated as proof that a multi-plane mutation or transition settled. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph #8039/#8833/#8834; KA-7 Google ADK async Memory Bank ingest; KA-8 Microsoft Agent Framework staged/settled workflow state | reinforced |
| KA-F-020 | Source provenance is recorded while transformation provenance is discarded or incomplete. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-6 LangGraph Store/checkpoint vs semantic-derivation gap; KA-7 Google ADK; KA-8 Microsoft Agent Framework memory extraction/consolidation | reinforced |
| KA-F-021 | “Hybrid retrieval” uses one retriever as the sole candidate-entry gate, so other signals can only rerank what it already found. | KA-2 Mem0 | observed |
| KA-F-022 | A hard filter is accepted by the high-level query layer but silently dropped by a backend adapter. | KA-2 Mem0 #7214 | observed |
| KA-F-023 | A pre-write snapshot or read-modify-write projection is treated as a concurrency-safe integrity guarantee. | KA-2 Mem0 #6515/#6243; KA-5 Mastra #21041/current legacy-adapter path; KA-8 Microsoft Agent Framework process-local/file-backed merge profile | reinforced |
| KA-F-024 | Partial batch fallback continues with the intended record set instead of the successfully settled subset. | KA-2 Mem0 | observed |
| KA-F-025 | Persistent user/agent/domain scope is reused as transient context-cache/task episode identity. | KA-2 Mem0 #7195; KA-5 Mastra resource-scope task-continuity warning | reinforced |
| KA-F-026 | “Delete memory/index data” is interpreted as privacy erasure while plaintext history/docstore/other planes remain. | KA-2 Mem0; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph TTL/checkpoint/store distinction; KA-8 Microsoft Agent Framework topic/transcript/session separation | reinforced |
| KA-F-027 | A derived synthesis/summary/projection is treated as exhaustive despite coverage, type, scope or extraction gaps. | KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-8 Microsoft Agent Framework selected topic/context projection | reinforced |
| KA-F-028 | Failed background consolidation retries the same evidence without stable semantic idempotency, producing duplicate/divergent abandoned mutation attempts. | KA-3 Letta Code #4266 | observed |
| KA-F-029 | Restore/replacement deletes the last active good state before the replacement is copied/indexed and validated. | KA-3 Letta Code #4195; KA-4 LlamaIndex `update_ref_doc()`/#22733 | reinforced |
| KA-F-030 | A derived viewer/count collapses unavailable, legacy-only or filtered representation into false canonical absence. | KA-3 Letta Code #3845/#3894 | observed |
| KA-F-031 | Persistent memory that influences execution is omitted from declared replay/task identity. | KA-3 Letta Code #3807; KA-6 LangGraph checkpointer-vs-Store separation | reinforced |
| KA-F-032 | Runtime transcript/event projection is assumed to be complete/canonical evidence despite profile-dependent record loss/merging. | KA-3 Letta Code #4248; KA-5 Mastra #23271; KA-7 Google ADK #6854/#6721; KA-8 Microsoft Agent Framework #8140 | reinforced |
| KA-F-033 | Source/document identity is reused as derivative uniqueness, collapsing one-to-many derived records. | KA-4 LlamaIndex #22133 (fixed in pinned source) | observed |
| KA-F-034 | A re-chunked/presentation derivative copies its parent identity or stale locators, causing downstream dedup/source-addressing errors. | KA-4 LlamaIndex #22537 (fixed in pinned source) | observed |
| KA-F-035 | A mutable external-resource locator fingerprint is treated as if it were an observed content/version digest. | KA-4 LlamaIndex current `MediaResource.hash` path/URL-only semantics | observed |
| KA-F-036 | Untrusted metadata/resource identifiers are interpolated into backend query syntax rather than safely bound/qualified, changing retrieval/deletion predicate semantics. | KA-4 LlamaIndex #22475/current PGVector source | observed |
| KA-F-037 | A join/quiescence barrier that absorbs child failures is treated as proof that all intended background mutations reconciled successfully. | KA-5 Mastra `Memory.settled()` | observed |
| KA-F-038 | Replayed/historical/consumed approval or suspension evidence is treated as current actionable authority without validating current durable pending state. | KA-5 Mastra #22767; KA-6 LangGraph #8837; KA-8 Microsoft Agent Framework #8140 adjacent durable-reload recurrence | reinforced |
| KA-F-039 | A supposedly read-only retrieval/projection aliases canonical stored memory, so mutating the returned object silently writes knowledge without a mutation event. | KA-6 LangGraph #8835/current `InMemoryStore` | observed |
| KA-F-040 | A serialized value appears equal after restoration but has lost behavior-bearing semantic metadata, so future reasoning or action differs after resume. | KA-6 LangGraph #8826/current `JsonPlusSerializer` | observed |
| KA-F-041 | Live execution and replay/reconstruction use different transition semantics for the same persisted write evidence, producing divergent recovered state. | KA-6 LangGraph #8821/current `DeltaChannel` | observed |
| KA-F-042 | An authority-bearing resume/approval response matches no currently pending target but silently succeeds/no-ops rather than failing closed with an explicit target-mismatch result. | KA-6 LangGraph #8836 | observed |
| KA-F-043 | Background/mutating operation lifecycle is coarsened to a capability name or left unfenced across generation change, so orphan/stale work can mutate state after run teardown or restore. | KA-7 Google ADK #7058; KA-8 Microsoft Agent Framework current orphan-sibling restore race prevention/source commentary | reinforced |
| KA-F-044 | Authority-bearing tool/continuation handling classifies by function/tool name alone, so a colliding implementation or same-named different-origin occurrence inherits or loses approval semantics. | KA-7 Google ADK #6721; KA-8 Microsoft Agent Framework current file-access autoapproval name-collision warning | reinforced |
| KA-F-045 | A model/runtime that is allowed to retrieve persistent knowledge is also implicitly allowed to append, delete or semantically consolidate that knowledge without an independently evaluated knowledge-mutation authority decision. | KA-8 Microsoft Agent Framework current Harness memory tool definitions/approval modes | observed |
| KA-F-046 | Remote logical-session validity is inferred from transport liveness, so retries reuse a dead server-side continuation/session generation. | KA-7 Google ADK #7060 | observed |
| KA-F-047 | Staged mutation state from a failed/cancelled operation survives its generation and is later committed by an unrelated successful run. | KA-8 Microsoft Agent Framework reproduced #7859 | observed |
| KA-F-048 | Pending approval/tool-continuation state has no complete terminal/expiry/drain lifecycle, so abandoned authority-bearing state remains actionable or accumulates without bound after the interaction that created it. | KA-8 Microsoft Agent Framework #7872/#7890 | observed |

## KA-7 + KA-8 bounded-block recurrence update

- KA-F-043 is immediately **reinforced**: Google ADK #7058 loses one same-tool background occurrence under name-keyed tracking, while Microsoft Agent Framework independently documents/fixes orphan sibling work mutating state after restore.
- KA-F-044 is immediately **reinforced**: Google ADK #6721 and MAF's current file-access autoapproval warning independently show that same-name but different-origin/implementation operations can inherit the wrong authority semantics.
- KA-F-045 is new MAF evidence that persistent-knowledge retrieval and mutation/delete/consolidation need independently evaluated authority.
- KA-F-046 is new Google ADK evidence separating transport liveness from logical remote-session validity.
- KA-F-047 is new MAF evidence that failed-generation staged state can later commit under a different successful run.
- KA-F-048 is new MAF evidence that pending authority/continuation state needs explicit terminal/expiry/drain behavior and bounded retention.
- KA-F-032 gains both ADK remote-projection evidence and MAF #8140, where the model-facing message list is clean while the durable snapshot remains corrupted.
- KA-F-038 gains MAF #8140 as adjacent recurrence because durable duplicated historical tool-call evidence can reopen an approval after the original call already executed.
- Existing settlement, transformation-provenance, concurrency, deletion/privacy and non-exhaustive-projection families gain additional recurrence.
- No failure pattern is promoted to a final architecture rule.

## How to use this ledger later

These patterns should become hostile scenarios or acceptance tests where applicable. Later revisits should reuse existing IDs for independent recurrence and create new IDs only for materially distinct failure mechanisms.
