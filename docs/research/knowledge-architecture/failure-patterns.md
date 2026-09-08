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
| KA-F-013 | Project/package/version label is treated as sufficient realized deployment identity even when backend, schema, protocol/extension profile or implementation semantics differ. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph #8653/backend/profile behavior; KA-7 Google ADK; KA-8 Microsoft Agent Framework; KA-9 OpenAI Agents SDK; KA-10 MCP #3348/core-vs-extension profile evidence | reinforced |
| KA-F-014 | Ontology/schema changes are interpreted as if old records were automatically migrated. | KA-1 Graphiti; KA-2 Mem0 | reinforced |
| KA-F-015 | A metadata/filter/query capability is assumed usable for governance because it exists in a high-level object model/API, without qualifying backend semantics. | KA-1 Graphiti; KA-2 Mem0; KA-4 LlamaIndex; KA-6 LangGraph #8829/#8831 | reinforced |
| KA-F-016 | Retrieval relevance/fusion score is treated as confidence/truth. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-6 LangGraph; KA-7 Google ADK; KA-8 Microsoft Agent Framework | reinforced |
| KA-F-017 | Persistent/retrieved/remote text is promoted into privileged policy/instruction channels without independently establishing its authority. | KA-1 Graphiti; KA-2 Mem0; KA-5 Mastra; KA-6 LangGraph adjacent Store/tool-description evidence; KA-10 MCP prompts/resources/tool-metadata evidence | reinforced |
| KA-F-018 | Conceptual temporal correctness is assumed to hold on every backend without qualification. | KA-1 Graphiti #1625 | observed |
| KA-F-019 | Successful storage/API/history/protocol/task operation is treated as proof that a multi-plane mutation, transition or external effect settled. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph #8039/#8833/#8834; KA-7 Google ADK async Memory Bank ingest; KA-8 Microsoft Agent Framework staged/settled workflow state; KA-9 OpenAI Agents SDK #4775; KA-10 MCP Tasks/cancellation and #3350 gap evidence | reinforced |
| KA-F-020 | Source provenance is recorded while transformation provenance is discarded or incomplete. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-6 LangGraph Store/checkpoint vs semantic-derivation gap; KA-7 Google ADK; KA-8 Microsoft Agent Framework memory extraction/consolidation; KA-9 OpenAI Agents SDK compaction/history rewrite | reinforced |
| KA-F-021 | “Hybrid retrieval” uses one retriever as the sole candidate-entry gate, so other signals can only rerank what it already found. | KA-2 Mem0 | observed |
| KA-F-022 | A hard filter is accepted by the high-level query layer but silently dropped by a backend adapter. | KA-2 Mem0 #7214 | observed |
| KA-F-023 | A pre-write snapshot or read-modify-write projection is treated as a concurrency-safe integrity guarantee. | KA-2 Mem0 #6515/#6243; KA-5 Mastra #21041/current legacy-adapter path; KA-8 Microsoft Agent Framework process-local/file-backed merge profile; KA-9 OpenAI Agents SDK #4679 stale compaction snapshot (fixed in current source) | reinforced |
| KA-F-024 | Partial batch fallback continues with the intended record set instead of the successfully settled subset. | KA-2 Mem0 | observed |
| KA-F-025 | Persistent user/agent/domain scope is reused as transient context-cache/task episode identity. | KA-2 Mem0 #7195; KA-5 Mastra resource-scope task-continuity warning | reinforced |
| KA-F-026 | “Delete memory/index data” is interpreted as privacy erasure while plaintext history/docstore/other planes remain. | KA-2 Mem0; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph TTL/checkpoint/store distinction; KA-8 Microsoft Agent Framework topic/transcript/session separation | reinforced |
| KA-F-027 | A derived synthesis/summary/projection is treated as exhaustive despite coverage, type, scope or extraction gaps. | KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-8 Microsoft Agent Framework selected topic/context projection; KA-9 OpenAI Agents SDK compaction | reinforced |
| KA-F-028 | Failed background consolidation retries the same evidence without stable semantic idempotency, producing duplicate/divergent abandoned mutation attempts. | KA-3 Letta Code #4266 | observed |
| KA-F-029 | Restore/replacement deletes the last active good state before the replacement is copied/indexed and validated. | KA-3 Letta Code #4195; KA-4 LlamaIndex `update_ref_doc()`/#22733 | reinforced |
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
| KA-F-045 | A model/runtime that is allowed to retrieve persistent knowledge is also implicitly allowed to append, delete or semantically consolidate that knowledge without an independently evaluated knowledge-mutation authority decision. | KA-8 Microsoft Agent Framework current Harness memory tool definitions/approval modes | observed |
| KA-F-046 | Remote logical-session validity is inferred from transport liveness, so retries reuse a dead server-side continuation/session generation. | KA-7 Google ADK #7060 | observed |
| KA-F-047 | Staged mutation state from a failed/cancelled operation survives its generation and is later committed by an unrelated successful run. | KA-8 Microsoft Agent Framework reproduced #7859 | observed |
| KA-F-048 | Pending approval/tool-continuation state has no complete terminal/expiry/drain lifecycle, so abandoned authority-bearing state remains actionable or accumulates without bound after the interaction that created it. | KA-8 Microsoft Agent Framework #7872/#7890 | observed |

## KA-9 + KA-10 bounded-block recurrence update

- No new failure-pattern ID is added in this block. Both revisits primarily deepen already-observed settlement, replacement, projection, authority-identity and realized-profile families.
- KA-F-019 gains strong OpenAI #4775 evidence: a Session append can commit while acknowledgement is lost, leaving `RunState` unable to distinguish committed from uncommitted pending input and causing duplicate logical input on retry. MCP independently reinforces the same broader boundary: task/protocol completion or cancellation is not domain-effect settlement, while #3350 explicitly proposes filling the missing shared outcome-attestation layer.
- KA-F-023 gains OpenAI #4679 as a concrete stale-snapshot replacement case. Current upstream fixes the specific compaction race by protecting snapshot-through-replacement and tracking mutation generation; the historical failure remains useful as a regression fixture.
- KA-F-013 gains both OpenAI exact source/session/profile evidence and MCP #3348/core-vs-extension compatibility evidence. A project/version label is insufficient when realized semantics depend on SDK, backend, schema/protocol revision, extension set or transport.
- KA-F-032 gains OpenAI's explicit sanitized/persisted presentation behavior after output guardrails and MCP's protocol-result/domain-outcome separation.
- KA-F-043 gains OpenAI provider-cleanup fencing evidence; cancellation is not complete while runner-owned provider cleanup remains active.
- KA-F-044 gains current OpenAI hosted-MCP sticky-approval identity and MCP cross-server identity evidence, reinforcing that a display tool name cannot carry authority by itself.
- No failure ID is created from OpenAI #4896. Current SDK behavior intentionally treats approval as final for that invocation and maintainer guidance places policy-version invalidation at the host boundary. The lesson is captured by new reinforced invariant KA-I-046 rather than mislabeled as an SDK defect.
- No failure ID is created from MCP #3348 because the existing realized-profile failure family KA-F-013 already captures the architecture risk.
- No failure ID is created for the Filesystems Working Group because it is proposed future design, not deployed failure evidence.
- No failure pattern is promoted to a final architecture rule.

## How to use this ledger later

These patterns should become hostile scenarios or acceptance tests where applicable. The next bounded coverage scan should look specifically for missing evidence, counterexamples and untested domains rather than mechanically creating more IDs.