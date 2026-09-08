# Knowledge Architecture Candidate Invariants

This ledger accumulates evidence-backed **candidate** invariants during the Knowledge Architecture Evidence Campaign. These are not final architecture rules.

## Status meanings

- **candidate** — supported by one bounded task.
- **reinforced** — independently supported by multiple tasks.
- **qualified** — retained with narrower scope after counterevidence.
- **rejected** — evidence showed the formulation was too strong or wrong.

## Ledger

| ID | Candidate invariant | Evidence/tasks | Status |
|---|---|---|---|
| KA-I-001 | Raw/source evidence must remain separately addressable from derived semantic knowledge. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra | reinforced |
| KA-I-002 | Internal semantic entity identity is distinct from external/source identity. | KA-1 Graphiti; KA-4 LlamaIndex | reinforced |
| KA-I-003 | Namespace/domain identifiers are not authenticated principal identity. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-004 | Identity merge/split is a first-class, auditable and reversible knowledge transition. | KA-1 Graphiti | candidate |
| KA-I-005 | Ambiguous/unresolved identity must be representable; identity resolution must not force a merge. | KA-1 Graphiti | candidate |
| KA-I-006 | Supersession/invalidation is a privileged, reversible, provenance-bearing semantic transition. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex | reinforced |
| KA-I-007 | Relationship labels alone are insufficient for safe replacement reasoning; governed relationship semantics are required where consequences depend on them. | KA-1 Graphiti | candidate |
| KA-I-008 | World/event-valid time and system record/transaction time must remain distinct. | KA-1 Graphiti; KA-2 Mem0; KA-6 LangGraph | reinforced |
| KA-I-009 | Current-state, historical, conflict and evidence retrieval are distinct query intents. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code | reinforced |
| KA-I-010 | Retrieval relevance/rank is not epistemic confidence, truth or authority. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-011 | Derived state such as embeddings, indexes, summaries, projections and graphs must carry generation/profile identity and be rebuildable from more canonical evidence where practical. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-012 | Storage/backend/query implementations must be qualified against semantic invariants; declaring a conceptual model is not sufficient. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-013 | Knowledge-domain routing for a request must be immutable/request-scoped when concurrent or reusable components can occur. | KA-1 Graphiti; KA-4 LlamaIndex | reinforced |
| KA-I-014 | Principal, purpose, sensitivity and hard eligibility constraints should be applied before protected knowledge is exposed to a model. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-015 | Retrieved/persistent memory remains untrusted content unless its source is separately established as trusted; prompt position does not upgrade provenance. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-016 | Delete/forget completion is a multi-plane reconciliation result, not a single successful delete return or current-view removal. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-017 | Schema/ontology/derivation changes do not retroactively reinterpret historical records without an explicit migration or re-derivation event. | KA-1 Graphiti; KA-2 Mem0; KA-4 LlamaIndex; KA-6 LangGraph | reinforced |
| KA-I-018 | Realized capability identity includes exact source/build/backend/schema/model/prompt/profile, not only a project or package name. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-019 | Security/provenance metadata required for policy must be end-to-end verified through persistence, read, filtering, derived projection and migration. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-020 | Knowledge retrieval never grants execution authority. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-021 | The substrate must distinguish unknown, known-false, not-established, conflicting and historically-true-but-no-longer-current states. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-022 | Assertion/relationship applicability must support structured scope such as environment, version, machine, project, person, role, task and time without relying only on arbitrary blobs or storage location. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex | reinforced |
| KA-I-023 | Transformation decisions that can materially alter future reasoning need provenance of their own. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-024 | Context construction is a separate layer from retrieval and must consider trust, freshness, permissions, actionability, relevance, revision and token budget. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-025 | Epistemic basis and verification state are separate from speaker attribution, storage state and retrieval status. | KA-1 Graphiti; KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-6 LangGraph | reinforced |
| KA-I-026 | Composite retrieval must define which retrievers can introduce candidates, which only rerank, and where hard gates/thresholds apply. | KA-2 Mem0; KA-4 LlamaIndex | reinforced |
| KA-I-027 | Derived aggregates, summaries and projections must expose their source revision, coverage/generation window and eligibility/type rules. | KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex | reinforced |
| KA-I-028 | Mutation settlement state must drive success reporting, history/derivation, context refresh and source-input consumption. | KA-2 Mem0; KA-3 Letta Code; KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-029 | Transient episode/conversation identity is distinct from persistent knowledge-domain/agent scope. | KA-2 Mem0; KA-3 Letta Code; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-030 | Derived semantic/association graphs used for retrieval are distinct from canonical typed relationship assertions. | KA-2 Mem0; KA-4 LlamaIndex | reinforced |
| KA-I-031 | Active model context must identify the exact settled knowledge revision it was constructed from; pending knowledge must not silently become active canonical context. | KA-3 Letta Code | candidate |
| KA-I-032 | Background consolidation input should be marked consumed only after canonical integration settles, and retries need stable source/operation identity for idempotency. | KA-3 Letta Code; KA-5 Mastra | reinforced |
| KA-I-033 | Persistent knowledge revision/profile is part of execution/replay identity whenever reproducibility or deterministic retry matters. | KA-3 Letta Code; KA-6 LangGraph | reinforced |
| KA-I-034 | Personal/private and shared/project knowledge domains require distinct ownership plus explicit read/write authority. | KA-3 Letta Code; KA-5 Mastra (adjacent scope evidence) | candidate |
| KA-I-035 | Restore/replacement of active knowledge must stage and validate the replacement before destructive cutover, then reconcile derived projections. | KA-3 Letta Code; KA-4 LlamaIndex | reinforced |
| KA-I-036 | Source/resource identity, derived-record identity and presentation-projection identity are distinct; lineage must not be implemented by identity reuse. | KA-4 LlamaIndex; KA-5 Mastra; KA-6 LangGraph | reinforced |
| KA-I-037 | Logical resource identity, locator/address and observed content/version digest are distinct and must be represented separately. | KA-4 LlamaIndex (`MediaResource.hash`) | candidate |
| KA-I-038 | Canonical knowledge reads exposed to retrieval, projection or context-construction code must have value/snapshot semantics or an explicit mutation contract; incidental object mutation must not alter canonical state. | KA-6 LangGraph #8835/current `InMemoryStore` | candidate |
| KA-I-039 | Persistence/migration round-trips must preserve behavior-bearing semantic metadata required for future interpretation, not merely produce a value that compares equal at the moment of restoration. | KA-6 LangGraph #8826/current serializer | candidate |
| KA-I-040 | For replayable state, live transition semantics and replay/reconstruction semantics must be behaviorally equivalent for the same ordered persisted transition evidence. | KA-6 LangGraph #8821/current `DeltaChannel` | candidate |

## KA-6 recurrence update

- KA-6 independently reinforces the separation of replayable execution state from long-term knowledge, while also showing that a replay can observe an unpinned persistent Store revision.
- KA-I-033 moves from single-task **candidate** to **reinforced** using independent Letta Code and LangGraph evidence.
- KA-I-038–040 are new LangGraph-derived candidates covering read isolation, semantic serialization fidelity and live/replay transition equivalence.
- KA-6 adds independent evidence to existing namespace/principal, temporal, retrieval-rank, derived-state, backend-qualification, authorization, deletion, migration, realized-profile, provenance, context-construction, settlement and identity families.
- KA-I-004, KA-I-005, KA-I-007, KA-I-031, KA-I-034, KA-I-037 and KA-I-038–040 remain single-task candidates.
- No invariant is promoted to a final architecture rule during the evidence campaign.

## Next update rule

Later tasks should reuse an existing invariant ID when independent evidence supports it, add the new evidence/task, record counterexamples or narrower scope, and create a new ID only for a materially distinct concept.
