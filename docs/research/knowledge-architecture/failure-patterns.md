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
| KA-F-001 | Treating a namespace/group/session/user string as authorization. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-5 Mastra; KA-6 LangGraph; KA-7 Google ADK; KA-8 Microsoft Agent Framework; KA-11 Agno | reinforced |
| KA-F-002 | Mutable shared knowledge-scope/routing/filter state survives across concurrent or reused requests. | KA-1 Graphiti #1676/#1840; KA-4 LlamaIndex #22701/current `VectorMemoryBlock` | reinforced |
| KA-F-003 | LLM contradiction output directly retires/rewrites current knowledge without structural trust/verification/restraint guardrails. | KA-1 Graphiti #1728/#1666; KA-3 Letta Code #4029; KA-11 Agno adjacent EntityMemory supersession-judge evidence | reinforced |
| KA-F-004 | “Newest statement/evidence wins” used as a universal truth rule. | KA-1 Graphiti; KA-3 Letta Code #4029 | reinforced |
| KA-F-005 | Relationship name + shared endpoint treated as sufficient proof of supersession. | KA-1 Graphiti PR #1729 | observed |
| KA-F-006 | Entity identity is collapsed without a durable merge decision/lineage record. | KA-1 Graphiti; KA-11 Agno negative/current avoidance evidence | observed |
| KA-F-007 | Deterministic exact identity evidence is hidden behind a semantic candidate threshold. | KA-1 Graphiti #1734 | observed |
| KA-F-008 | One generic memory search mixes current and retired/superseded facts without an explicit current-only intent. | KA-1 Graphiti #1645; KA-2 Mem0 | reinforced |
| KA-F-009 | Derived semantic summaries/graph objects become the only practically searchable representation. | KA-1 Graphiti #1427 | observed |
| KA-F-010 | One invalid/mismatched vector can fail a whole semantic query. | KA-1 Graphiti #1328/#1505 | observed |
| KA-F-011 | Derived indexes start asynchronously without a tracked readiness/settlement lifecycle. | KA-1 Graphiti #1643 | observed |
| KA-F-012 | Deletion relies on incomplete/best-effort provenance or dependency traversal and leaves derived/orphan/reconstructability failures. | KA-1 Graphiti #1083; KA-2 Mem0 #4863; KA-4 LlamaIndex current PropertyGraph deletion; KA-6 LangGraph #8531/#7206/current DeltaChannel prune contract; KA-11 Agno adjacent session/tool-result cascade and memory-plane evidence | reinforced |
| KA-F-013 | Project/package/version label is treated as sufficient realized deployment identity even when backend, schema, protocol/extension profile or implementation semantics differ. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph #8653/backend/profile behavior; KA-7 Google ADK; KA-8 Microsoft Agent Framework; KA-9 OpenAI Agents SDK; KA-10 MCP #3348/core-vs-extension profile evidence; KA-11 Agno | reinforced |
| KA-F-014 | Ontology/schema changes are interpreted as if old records were automatically migrated. | KA-1 Graphiti; KA-2 Mem0; KA-11 Agno entity-key migration | reinforced |
| KA-F-015 | A metadata/filter/query capability is assumed usable for governance because it exists in a high-level object model/API, without qualifying backend semantics. | KA-1 Graphiti; KA-2 Mem0; KA-4 LlamaIndex; KA-6 LangGraph #8829/#8831; KA-11 Agno optional backend user-scope evidence | reinforced |
| KA-F-016 | Retrieval relevance/fusion score is treated as confidence/truth. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-6 LangGraph; KA-7 Google ADK; KA-8 Microsoft Agent Framework | reinforced |
| KA-F-017 | Persistent/retrieved/remote text is promoted into privileged policy/instruction channels without independently establishing its authority. | KA-1 Graphiti; KA-2 Mem0; KA-5 Mastra; KA-6 LangGraph adjacent Store/tool-description evidence; KA-10 MCP prompts/resources/tool-metadata evidence; KA-11 Agno UserMemory system-context projection | reinforced |
| KA-F-018 | Conceptual temporal correctness is assumed to hold on every backend without qualification. | KA-1 Graphiti #1625 | observed |
| KA-F-019 | Successful storage/API/history/protocol/task operation is treated as proof that a multi-plane mutation, transition or external effect settled. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph #8039/#8833/#8834; KA-7 Google ADK async Memory Bank ingest; KA-8 Microsoft Agent Framework staged/settled workflow state; KA-9 OpenAI Agents SDK #4775; KA-10 MCP Tasks/cancellation and #3350 gap evidence; KA-11 Agno migration read-back verification | reinforced |
| KA-F-020 | Source provenance is recorded while transformation provenance is discarded or incomplete. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-6 LangGraph Store/checkpoint vs semantic-derivation gap; KA-7 Google ADK; KA-8 Microsoft Agent Framework memory extraction/consolidation; KA-9 OpenAI Agents SDK compaction/history rewrite; KA-11 Agno extraction/supersession evidence | reinforced |
| KA-F-021 | “Hybrid retrieval” uses one retriever as the sole candidate-entry gate, so other signals can only rerank what it already found. | KA-2 Mem0 | observed |
| KA-F-022 | A hard filter is accepted by the high-level query layer but silently dropped by a backend adapter. | KA-2 Mem0 #7214 | observed |
| KA-F-023 | A pre-write snapshot or read-modify-write projection is treated as a concurrency-safe integrity guarantee. | KA-2 Mem0 #6515/#6243; KA-5 Mastra #21041/current legacy-adapter path; KA-8 Microsoft Agent Framework process-local/file-backed merge profile; KA-9 OpenAI Agents SDK #4679 stale compaction snapshot (fixed in current source); KA-11 Agno migration/entity-write concurrency evidence | reinforced |
| KA-F-024 | Partial batch fallback continues with the intended record set instead of the successfully settled subset. | KA-2 Mem0 | observed |
| KA-F-025 | Persistent user/agent/domain scope is reused as transient context-cache/task episode identity. | KA-2 Mem0 #7195; KA-5 Mastra resource-scope task-continuity warning | reinforced |
| KA-F-026 | “Delete memory/index data” is interpreted as privacy erasure while plaintext history/docstore/other planes remain. | KA-2 Mem0; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph TTL/checkpoint/store distinction; KA-8 Microsoft Agent Framework topic/transcript/session separation; KA-11 Agno delete/clear/archive/retire distinction | reinforced |
| KA-F-027 | A derived synthesis/summary/projection is treated as exhaustive despite coverage, type, scope or extraction gaps. | KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-8 Microsoft Agent Framework selected topic/context projection; KA-9 OpenAI Agents SDK compaction; KA-11 Agno visible context truncation | reinforced |
| KA-F-028 | Failed background consolidation retries the same evidence without stable semantic idempotency, producing duplicate/divergent abandoned mutation attempts. | KA-3 Letta Code #4266 | observed |
| KA-F-029 | Restore/replacement deletes the last active good state before the replacement is copied/indexed and validated. | KA-3 Letta Code #4195; KA-4 LlamaIndex `update_ref_doc()`/#22733; KA-11 Agno positive migration counter-pattern | reinforced |
| KA-F-030 | A derived viewer/count collapses unavailable, legacy-only or filtered representation into false canonical absence. | KA-3 Letta Code #3845/#3894 | observed |
| KA-F-031 | Persistent memory that influences execution is omitted from declared replay/task identity. | KA-3 Letta Code #3807; KA-6 LangGraph checkpointer-vs-Store separation | reinforced |
| KA-F-032 | Runtime transcript/event/model-visible/protocol projection is assumed to be complete/canonical evidence despite profile-dependent record loss, merging, sanitization or domain-outcome gaps. | KA-3 Letta Code #4248; KA-5 Mastra #23271; KA-7 Google ADK #6854/#6721; KA-8 Microsoft Agent Framework #8140; KA-9 OpenAI Agents SDK output-guardrail/session projection; KA-10 MCP protocol-result vs domain-outcome distinction | reinforced |
| KA-F-033 | Source/document identity is reused as derivative uniqueness, collapsing one-to-many derived records. | KA-4 LlamaIndex #22133 (fixed in pinned source) | observed |
| KA-F-034 | A re-chunked/presentation derivative copies its parent identity or stale locators, causing downstream dedup/source-addressing errors. | KA-4 LlamaIndex #22537 (fixed in pinned source) | observed |
| KA-F-035 | A mutable external-resource locator fingerprint is treated as if it were an observed content/version digest. | KA-4 LlamaIndex current `MediaResource.hash` path/URL-only semantics | observed |
| KA-F-036 | Untrusted metadata/resource identifiers are interpolated into backend query syntax rather than safely bound/qualified, changing retrieval/deletion predicate semantics. | KA-4 LlamaIndex #22475/current PGVector source | observed |
| KA-F-037 | A join/quiescence barrier that absorbs child failures is treated as proof that all intended background mutations reconciled successfully. | KA-5 Mastra `Memory.settled()` | observed |
| KA-F-038 | Replayed/historical/consumed approval or suspension evidence is treated as current actionable authority without validating current durable pending state. | KA-5 Mastra #22767; KA-6 LangGraph #8837; KA-8 Microsoft Agent Framework #8140 adjacent durable-reload recurrence; KA-10 MCP MRTR single-use warning adjacent evidence | reinforced |
| KA-F-039 | A supposedly read-only retrieval/projection aliases canonical stored memory, so mutating the returned object silently writes knowledge without a mutation event. | KA-6 LangGraph #8835/current `InMemoryStore` | observed |
| KA-F-040 | A serialized value appears equal after restoration but has lost behavior-bearing semantic metadata, so future reasoning or action differs after resume. | KA-6 LangGraph #8826/current `JsonPlusSerializer` | observed |
| KA-F-041 | Live execution and replay/reconstruction use different transition semantics for the same persisted write evidence, producing divergent recovered state. | KA-6 LangGraph #8821/current `DeltaChannel` | observed |
| KA-F-042 | An authority-bearing resume/approval response matches no currently pending target but silently succeeds/no-ops rather than failing closed with an explicit target-mismatch result. | KA-6 LangGraph #8836 | observed |
| KA-F-043 | Background/mutating operation lifecycle is coarsened to a capability name or left unfenced across generation change, so orphan/stale work can mutate state after run teardown or restore. | KA-7 Google ADK #7058; KA-8 Microsoft Agent Framework current orphan-sibling restore race prevention/source commentary; KA-9 OpenAI Agents SDK runner-owned provider lifecycle | reinforced |
| KA-F-044 | Authority-bearing tool/continuation handling classifies by function/tool name alone, so a colliding implementation or same-named different-origin occurrence inherits or loses approval semantics. | KA-7 Google ADK #6721; KA-8 Microsoft Agent Framework current file-access autoapproval name-collision warning; KA-9 OpenAI Agents SDK hosted-MCP identity safeguards; KA-10 MCP multi-server tool identity | reinforced |
| KA-F-045 | A model/runtime that is allowed to retrieve persistent knowledge is also implicitly allowed to append, delete or semantically consolidate that knowledge without an independently evaluated knowledge-mutation authority decision. | KA-8 Microsoft Agent Framework current Harness memory tool definitions/approval modes; KA-11 Agno current MemoryTools/UserMemory agentic mutation surfaces | reinforced |
| KA-F-046 | Remote logical-session validity is inferred from transport liveness, so retries reuse a dead server-side continuation/session generation. | KA-7 Google ADK #7060 | observed |
| KA-F-047 | Staged mutation state from a failed/cancelled operation survives its generation and is later committed by an unrelated successful run. | KA-8 Microsoft Agent Framework reproduced #7859 | observed |
| KA-F-048 | Pending approval/tool-continuation state has no complete terminal/expiry/drain lifecycle, so abandoned authority-bearing state remains actionable or accumulates without bound after the interaction that created it. | KA-8 Microsoft Agent Framework #7872/#7890 | observed |
| KA-F-049 | An owner-scoped knowledge surface resolves update/delete by a globally addressable object ID without reapplying the current caller's owner/domain scope at mutation time. | KA-11 Agno current `MemoryTools.update_memory` / `delete_memory` vs scoped AgentOS REST memory router | observed |

## KA-11 Agno revisit update

- **KA-F-045 moved observed → reinforced.** Microsoft Agent Framework first showed model-facing memory retrieval/mutation bundled without a separate knowledge-mutation authority boundary. Agno independently exposes model-facing memory tool/config surfaces where get/add/update/delete are bundled, while #9983 demonstrates the consequence of wiring a user-facing mutation to an overbroad database-global primitive.
- **KA-F-049 is new, observed.** Current Agno `MemoryTools` scopes get/add by `run_context.user_id`, but update/delete target by bare `memory_id` and omit the caller's user scope. The BaseDb contract makes owner filtering optional, while the current AgentOS REST memory router demonstrates that authenticated owner scope can and should be threaded into the same deletion APIs. KA-11 found no current public issue for this exact path and did not execute a PoC, so the finding is explicitly source-observed rather than independently reproduced.
- #9983 remains open and its proposed #9986 fix remains unmerged at current Agno 3.0.7/main. Current ordinary create/update extraction explicitly disables clear-all, so the failure is scoped to generic paths that expose the clear tool rather than generalized to every memory update.
- Historical #8334 remains open, but current main no longer uses its reported user-less EntityMemory key. Agno now incorporates a user digest into user-private entity keys and includes migration/quarantine logic. The historical failure remains a regression/migration lesson, not a claim of current exploitability.
- KA-F-001 gains Agno recurrence: route-level authenticated scope is distinct from low-level `user_id` storage values.
- KA-F-014/023 gain Agno recurrence from the entity re-key migration: semantic identity changes require explicit migration; source warns the migration lacks a transaction/CAS boundary and should run offline.
- KA-F-019 gains positive Agno counter-pattern evidence: migration success is confirmed with read-back because adapter return values can be insufficient to prove settlement.
- KA-F-026 gains Agno recurrence: delete, clear, retire, archive, quarantine and purge have materially different retention semantics.
- No new failure ID is created for #9983 itself because KA-F-045 plus new KA-F-049 capture the reusable architecture risks without encoding a project-specific global-clear bug as a universal class.
- No failure pattern is promoted to a final architecture rule.

## How to use this ledger later

These patterns should become hostile scenarios or acceptance tests where applicable. The promoted Agno revisit is complete. The next bounded campaign work should target standards/domain gaps rather than mechanically accumulating additional agent-framework failures.
