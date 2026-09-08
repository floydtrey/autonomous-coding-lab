# Knowledge Architecture Candidate Invariants

This ledger accumulates evidence-backed **candidate** invariants during the Knowledge Architecture Evidence Campaign.

These are not final architecture rules. A candidate gains weight when independent projects/standards support it, and may be narrowed, split or rejected when counterevidence appears.

## Status meanings

- **candidate** — supported by at least one bounded research task; not yet cross-project validated.
- **reinforced** — supported independently by multiple campaign tasks.
- **qualified** — retained but narrowed by counterexamples/scope.
- **rejected** — evidence showed the proposed invariant was too strong or wrong.
- **promoted later** — reserved for the eventual synthesis phase; not used merely because a candidate feels persuasive.

## Ledger

| ID | Candidate invariant | Evidence/tasks | Current scope / rationale | Status |
|---|---|---|---|---|
| KA-I-001 | Raw/source evidence must remain separately addressable from derived semantic knowledge. | KA-1 Graphiti; KA-2 Mem0 | Graphiti episodes and Mem0 semantic-memory/history separation independently show that compact derived knowledge is lossy and needs a traceable lower evidence plane. Mem0’s last-10 source-message cache makes the need especially concrete. | reinforced |
| KA-I-002 | Internal semantic entity identity is distinct from external/source identity. | KA-1 Graphiti | A graph UUID identifies a resolved record, not necessarily a person/account/device/repository identity in the outside world. Mem0 provides adjacent evidence by separating graph entities from scope IDs, but KA-2 does not independently establish the full external-identity rule. | candidate |
| KA-I-003 | Namespace/domain identifiers are not authenticated principal identity. | KA-1 Graphiti; KA-2 Mem0 | Graphiti `group_id` and Mem0 user/agent/run/app scopes are routing/query dimensions. Both projects require an outer authentication/authorization boundary. | reinforced |
| KA-I-004 | Identity merge/split is a first-class, auditable and reversible knowledge transition. | KA-1 Graphiti | Current Graphiti dedup can change the surviving UUID while the ordinary ingest path discards duplicate-pair evidence. | candidate |
| KA-I-005 | Ambiguous/unresolved identity must be representable; identity resolution must not force a merge. | KA-1 Graphiti | False merges and false splits are both observed Graphiti failure classes; semantic/string heuristics are not universally decisive. Mem0’s retrieval-oriented entity matching is not treated as independent canonical identity evidence. | candidate |
| KA-I-006 | Supersession/invalidation is a privileged, reversible, provenance-bearing semantic transition. | KA-1 Graphiti; KA-2 Mem0 | Graphiti exposes unsafe invalidation failure modes; Mem0 Dream independently documents non-destructive supersede/merge states and replacement links. | reinforced |
| KA-I-007 | Relationship labels alone are insufficient for safe reasoning about replacement; governed relationship semantics are required where consequences depend on them. | KA-1 Graphiti | Graphiti PR #1729 exposes cardinality/replacement ambiguity (`WORKS_AT` versus `USES`) not represented by the current edge-type map. Mem0’s graph is deliberately untyped retrieval association, so it does not independently validate replacement semantics. | candidate |
| KA-I-008 | World/event-valid time and system record/transaction time must remain distinct. | KA-1 Graphiti; KA-2 Mem0 | Graphiti exposes separate validity/transaction fields; Mem0 Platform distinguishes imported/event timestamps from system storage time while OSS expiration remains a separate lifecycle concept. | reinforced |
| KA-I-009 | Current-state, historical, conflict and evidence retrieval are distinct query intents. | KA-1 Graphiti; KA-2 Mem0 | Graphiti generic fact search can mix current/history; Mem0 Dream explicitly provides default history-inclusive reads versus `latest_only` current reads. | reinforced |
| KA-I-010 | Retrieval relevance/rank is not epistemic confidence, truth or authority. | KA-1 Graphiti; KA-2 Mem0 | Both systems combine semantic/text/graph signals. Mem0 further adds access-based decay, showing a public relevance score may include usage recency that has no truth meaning. | reinforced |
| KA-I-011 | Derived state such as embeddings, indexes, summaries and association graphs must carry generation/profile identity and be rebuildable from more canonical evidence where practical. | KA-1 Graphiti; KA-2 Mem0 | Graphiti vector/index failures and Mem0 best-effort entity/Dream layers independently show derived state can drift or fail without changing the underlying knowledge record. | reinforced |
| KA-I-012 | Storage/backend/query implementations must be qualified against semantic invariants; declaring a conceptual model is not sufficient. | KA-1 Graphiti; KA-2 Mem0 | Graphiti backend temporal/routing differences and Mem0 OpenSearch filter/operator mismatch independently show concrete backends can violate high-level semantics. | reinforced |
| KA-I-013 | Knowledge-domain routing for a request must be immutable/request-scoped when concurrent access can occur. | KA-1 Graphiti | Shared mutable Graphiti driver routing caused silent cross-group writes. Mem0 KA-2 adds concurrency evidence in other layers but not this exact routing pattern. | candidate |
| KA-I-014 | Principal, purpose, sensitivity and hard eligibility constraints should be applied before protected knowledge is exposed to a model. | KA-1 Graphiti; KA-2 Mem0 | Graphiti group filters are not governance; Mem0’s backend-specific filter behavior shows a hard predicate must be enforced before candidate/context exposure and fail closed if unsupported. | reinforced |
| KA-I-015 | Retrieved/persistent memory remains untrusted content unless its source is separately established as trusted; prompt position does not upgrade provenance. | KA-1 Graphiti; KA-2 Mem0 | Both systems place persistent/source text into later model contexts; neither persistence nor privileged prompt placement makes that text policy. | reinforced |
| KA-I-016 | Delete/forget completion is a multi-plane reconciliation result, not a single successful delete return. | KA-1 Graphiti; KA-2 Mem0 | Graphiti can leave semantic orphans; Mem0 separates vector deletion, best-effort entity cleanup, retained plaintext history and short-term message cache. | reinforced |
| KA-I-017 | Schema/ontology/derivation changes do not retroactively reinterpret historical records without an explicit migration or re-derivation event. | KA-1 Graphiti; KA-2 Mem0 | Graphiti custom-type evolution and Mem0’s v2→v3 semantic migration independently demonstrate that old records/indexes retain the semantics under which they were derived unless explicitly migrated. | reinforced |
| KA-I-018 | Realized capability identity includes exact source/build/backend/schema/profile, not only a project or package name. | KA-1 Graphiti; KA-2 Mem0 | Graphiti backend/tool surfaces and Mem0 OSS/Platform/language/backend v3 profiles materially alter behavior under the same project name. | reinforced |
| KA-I-019 | Security/provenance metadata required for policy must be end-to-end verified through persistence, read, filtering, derived projection and migration. | KA-1 Graphiti; KA-2 Mem0 | Graphiti `episode_metadata` and Mem0’s high-level filter grammar/backend mismatch independently show declared metadata capability is not enough. | reinforced |
| KA-I-020 | Knowledge retrieval never grants execution authority. | KA-1 Graphiti; KA-2 Mem0 | Graphiti relationships/context and Mem0 remembered policy/configuration text are descriptive. Protected policy/approval/credential state must authorize actions separately. | reinforced |
| KA-I-021 | The substrate must distinguish unknown, known-false, not-established, conflicting and historically-true-but-no-longer-current states. | KA-1 Graphiti; KA-2 Mem0 | Both systems provide some history/lifecycle semantics but neither supplies this full epistemic absence/conflict taxonomy. | reinforced |
| KA-I-022 | Assertion/relationship applicability must support structured scope such as environment, version, machine, project, person and time without relying only on arbitrary key/value blobs. | KA-1 Graphiti; KA-2 Mem0 | Graphiti group/time/custom attributes and Mem0 entity IDs/metadata provide useful partial scope, but not a general storage-independent applicability contract. | reinforced |
| KA-I-023 | Transformation decisions that can materially alter future reasoning need provenance of their own. | KA-1 Graphiti; KA-2 Mem0 | Graphiti merge/invalidation/summary transformations and Mem0 extraction/Dream/entity derivations show source provenance alone cannot explain why canonical or retrieved knowledge changed. | reinforced |
| KA-I-024 | Context construction is a separate layer from retrieval and must consider trust, freshness, permissions, actionability, relevance and token budget. | KA-1 Graphiti; KA-2 Mem0 | Graphiti search returns candidates; Mem0 independently demonstrates stateful construction from memories + last-k messages + instructions, including stale-context failures. | reinforced |
| KA-I-025 | Epistemic basis and verification state are separate from speaker attribution, storage state and retrieval status. | KA-1 Graphiti; KA-2 Mem0 | Graphiti lacks a general trust/confidence envelope; Mem0 adds user/assistant attribution but still stores explicit statements, recommendations, inferred/derived memories and managed synthesis without a common verified/disputed basis field. | reinforced |
| KA-I-026 | Composite retrieval must define which retrievers can introduce candidates, which only rerank, and where hard gates/thresholds apply. | KA-2 Mem0 | Mem0 OSS computes semantic, BM25 and entity signals but only semantic hits enter the candidate pool and the semantic threshold runs before combination. | candidate |
| KA-I-027 | Derived aggregates and summaries must expose their coverage/generation window and eligibility rules. | KA-2 Mem0 | Dream Synthesis is forward-only, scope-restricted, threshold-gated and scheduled; a pattern set is therefore not an exhaustive statement about all source evidence. | candidate |
| KA-I-028 | Per-record settlement state must drive API success, mutation history and downstream derived maintenance. | KA-2 Mem0 | Current fallback inserts can fail individually while history, entity linking and returned ADD results are still built from the intended record list. | candidate |
| KA-I-029 | Transient episode/conversation/context-cache identity is distinct from persistent knowledge-domain scope. | KA-2 Mem0 | Last-k messages are keyed only by user/agent/run scope; #7195 shows reused scopes can mix unrelated conversational episodes. | candidate |
| KA-I-030 | Derived association graphs used for retrieval are distinct from canonical typed relationship assertions. | KA-2 Mem0 | Platform Graph Memory explicitly uses entity↔memory co-occurrence and does not assign typed entity relationships; that graph is a retrieval structure, not a general relationship truth model. | candidate |

## Recurrence tracking

After KA-2:

- **19 existing candidates are now independently reinforced by Graphiti + Mem0:** KA-I-001, 003, 006, 008–012, 014–024.
- **KA-I-025 is introduced as reinforced immediately** because the same epistemic-basis gap was independently observed in both KA-1 and KA-2.
- KA-I-026–030 are new Mem0-derived candidates and remain single-task evidence.
- KA-I-002, 004, 005, 007 and 013 remain Graphiti-only candidates; Mem0 supplied adjacent but not sufficiently independent evidence to promote them.

## Next update rule

Later tasks should:

1. cite the existing invariant ID when independent evidence supports it;
2. add the new project/task to the evidence column;
3. note meaningful counterexamples or narrower scope;
4. create a new ID only when the concept is materially distinct.
