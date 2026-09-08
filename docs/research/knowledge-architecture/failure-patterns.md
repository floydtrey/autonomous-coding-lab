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
| KA-F-001 | Treating a namespace/group/session/user string as authorization. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code | Caller-chosen routing/scope IDs are confused with authenticated authority. Letta's separate harness auth/cross-agent guards reinforce that agent/conversation/repo identity is not sufficient permission. | reinforced |
| KA-F-002 | Mutable shared storage-routing state across concurrent requests. | KA-1 Graphiti #1676/#1840 | Silent cross-domain/cross-tenant data corruption and provenance/privacy failure. Mem0/Letta have concurrency evidence in other layers but not this exact shared-routing mechanism. | observed |
| KA-F-003 | LLM contradiction output directly retires/rewrites current knowledge without structural trust/verification/restraint guardrails. | KA-1 Graphiti #1728/#1666; KA-3 Letta Code #4029 | A model can hide/weaken stronger truth or fabricate a merge while trying to reconcile contradictions. | reinforced |
| KA-F-004 | “Newest statement/evidence wins” used as a universal truth rule. | KA-1 Graphiti temporal invalidation analysis; KA-3 Letta Code #4029/current reflection prompt | Low-trust newer evidence can replace stronger/confirmed older evidence; Letta's controlled prompt eval shows safety-critical downgrade and confabulated merge failures. | reinforced |
| KA-F-005 | Relationship name + shared endpoint treated as sufficient proof of supersession. | KA-1 Graphiti PR #1729 | Additive many-to-many relationships can be mistaken for replaceable current-state relationships. | observed |
| KA-F-006 | Entity identity is collapsed without a durable merge decision/lineage record. | KA-1 Graphiti current `add_episode`/dedup path | False merge becomes difficult to audit, reverse or propagate correctly. | observed |
| KA-F-007 | Deterministic exact identity evidence is hidden behind a semantic candidate threshold. | KA-1 Graphiti #1734 | Same entity can fragment into multiple canonical records because it never reaches exact-match logic. | observed |
| KA-F-008 | One generic memory search mixes current and retired/superseded facts without an explicit current-only intent. | KA-1 Graphiti #1645; KA-2 Mem0 Dream read modes | Models/callers can treat history as current. Letta instead separates current MemFS from recall/Git history, so KA-3 is supporting contrast rather than another occurrence. | reinforced |
| KA-F-009 | Derived semantic summaries/graph objects become the only practically searchable representation. | KA-1 Graphiti #1427 | Exact source literals/evidence can survive only in raw content that retrieval cannot efficiently reach. Letta provides a positive counter-shape by retaining searchable recall separately. | observed |
| KA-F-010 | One invalid/mismatched vector can fail a whole semantic query. | KA-1 Graphiti #1328/#1505 | Corrupt derived state makes otherwise valid canonical knowledge unavailable. | observed |
| KA-F-011 | Derived indexes start asynchronously without a tracked readiness/settlement lifecycle. | KA-1 Graphiti #1643 | First use/reset/shutdown races with index creation; errors appear detached from initiating operation. | observed |
| KA-F-012 | Deletion relies on incomplete/best-effort provenance links and silently leaves derived/orphan records. | KA-1 Graphiti #1083; KA-2 Mem0 #4863 | “Delete” can leave semantic/entity derivatives stale or retrievable. Letta contributes retention/history evidence but not this exact orphan-link mechanism. | reinforced |
| KA-F-013 | Project/package version is treated as sufficient deployment identity. | KA-1 Graphiti #1656/#1108; KA-2 Mem0 v2→v3/OSS-Platform; KA-3 Letta Code backend/model/runtime differences | Actual tool schema, storage, retrieval, transcript or reflection behavior differs from the project/version shorthand. | reinforced |
| KA-F-014 | Ontology/schema changes are interpreted as if old records were automatically migrated. | KA-1 Graphiti custom-type migration; KA-2 Mem0 v2→v3 migration | Historical records/indexes are read under semantics they were never derived with. Letta adds adjacent configuration-migration evidence but not a third exact ontology occurrence. | reinforced |
| KA-F-015 | A metadata/filter capability is assumed usable for governance because it exists in an object model or high-level API. | KA-1 Graphiti `episode_metadata`; KA-2 Mem0 #7214 | Policy depends on predicates that may not persist or may be weakened by a backend. Letta KA-3 instead highlights coarse repository attachment versus fine-grained policy. | reinforced |
| KA-F-016 | Retrieval relevance score is treated as confidence/truth. | KA-1 Graphiti hybrid search; KA-2 Mem0 hybrid scoring/decay; KA-3 Letta Code recall search | Semantic/lexical/hybrid relevance can locate evidence but cannot establish whether it is true, verified, current or authorized. | reinforced |
| KA-F-017 | Persistent/retrieved text is promoted into privileged policy/instruction channels. | KA-1 Graphiti/Zep boundary; KA-2 Mem0 #4926/#5195 | Prompt injection or remembered text gains authority through persistence/pinning. Letta provides strong mitigating separation by placing security/credentials in the harness, rather than an independent exploit instance. | reinforced |
| KA-F-018 | Conceptual temporal correctness is assumed to hold on every backend without qualification. | KA-1 Graphiti #1625 | Point-in-time queries return future data despite correct-looking high-level semantics. | observed |
| KA-F-019 | Successful storage/API/history/commit operation is treated as proof that a multi-plane mutation settled. | KA-1 Graphiti deletion/index evidence; KA-2 Mem0 partial-write path; KA-3 Letta Code #4266/#4249/reflection finalization | Local persistence or a success-like intermediate event is mistaken for canonical integration/synchronization/context settlement. | reinforced |
| KA-F-020 | Source provenance is recorded while transformation provenance is discarded or incomplete. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code reflection/#4040 | System can identify source/commit-ish history but not fully explain why a merge, conflict resolution, summary or replacement took its current semantic form. | reinforced |
| KA-F-021 | “Hybrid retrieval” uses one retriever as the sole candidate-entry gate, so other signals can only rerank what it already found. | KA-2 Mem0 current `_search_vector_store`/`score_and_rank` | Exact lexical/entity evidence can never surface if semantic candidate generation omits it. Letta exposes hybrid modes but KA-3 did not inspect enough ranking internals to reproduce this exact pattern. | observed |
| KA-F-022 | A hard filter is accepted by the high-level query layer but silently dropped by a backend adapter. | KA-2 Mem0 #7214/current OpenSearch adapter | Eligibility/sensitivity/current-state constraints appear enforced while the concrete query runs with weaker predicates. | observed |
| KA-F-023 | A pre-write snapshot or read-modify-write projection is treated as a concurrency-safe integrity guarantee. | KA-2 Mem0 #6515/#6243 | Concurrent writers create duplicate canonical records or lose derived links without an error. | observed |
| KA-F-024 | Partial batch fallback continues with the intended record set instead of the successfully settled subset. | KA-2 Mem0 current Phase 6–8 source | API returns/history/derived indexes can contain phantom success for records whose actual storage insert failed. | observed |
| KA-F-025 | Persistent user/agent/domain scope is reused as transient context-cache episode identity. | KA-2 Mem0 #7195 | Unrelated conversations under the same long-lived scope contaminate extraction context. Letta's separate `agent_id`/`conversation_id` is an independent positive counterexample. | observed |
| KA-F-026 | “Delete memory” is interpreted as privacy erasure while plaintext history or other planes intentionally remain. | KA-2 Mem0 current delete/history + #6512 | A user/host believes data was forgotten while an audit/history plane still contains it. Letta's Git history independently reinforces the semantic distinction but KA-3 did not verify an erasure API failure. | observed |
| KA-F-027 | A derived synthesis/summary/projection is treated as exhaustive despite explicit coverage, type, scope or cadence gaps. | KA-2 Mem0 Dream; KA-3 Letta Code #3845/#3894 | Missing information in a derivative/view is mistaken for missing information in canonical evidence. | reinforced |
| KA-F-028 | Failed background consolidation retries the same evidence without stable semantic idempotency, producing duplicate/divergent abandoned mutation attempts. | KA-3 Letta Code #4266 | Reprocessing the same source slice can create repeated commits or differing learned state even though the original mutation never settled. | observed |
| KA-F-029 | Restore deletes/replaces the active canonical store before the replacement is copied and validated. | KA-3 Letta Code #4195/current restore source | A recovery operation destroys the last good state and can leave canonical knowledge missing/partial when the replacement fails. | observed |
| KA-F-030 | A derived viewer/count collapses unavailable, legacy-only or filtered representation into false canonical absence. | KA-3 Letta Code #3845/#3894 | Users/agents make decisions from `0`/missing resources even though committed canonical MemFS content exists. | observed |
| KA-F-031 | Persistent memory that influences execution is omitted from declared replay/task identity. | KA-3 Letta Code #3807 | Same declared task inputs or a retry can behave differently because inherited hidden memory changed between runs. | observed |
| KA-F-032 | Runtime transcript/event projection is assumed to be complete evidence despite profile-dependent record loss/merging. | KA-3 Letta Code #4248 | Downstream recall/reflection may reason over a transformed source projection without a completeness signal. Scope is limited: the cited issue demonstrates reasoning-record projection differences, not general loss of all user facts. | observed |

## How to use this ledger later

These patterns should become hostile scenarios or acceptance tests where applicable. Later project revisits should not merely add duplicates; they should cite an existing ID and record independent evidence. Repeated independent occurrence is stronger architecture evidence than one framework's design choice.

## KA-3 recurrence update

After Letta Code:

- KA-F-003 and KA-F-004 are newly **reinforced** by Letta's current reflection prompt and #4029 conflict evaluation.
- KA-F-013, KA-F-016, KA-F-019, KA-F-020 and KA-F-027 gain additional independent Letta evidence.
- KA-F-028–032 are new Letta-derived observed patterns.
- Letta supplies positive counterexamples/mitigations for some earlier patterns, especially explicit agent-versus-conversation identity, separate recall history, committed-revision context construction and harness-owned authority.
- No failure pattern is promoted to a final architecture rule.
