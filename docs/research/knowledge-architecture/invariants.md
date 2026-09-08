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
| KA-I-001 | Raw/source evidence must remain separately addressable from derived semantic knowledge. | KA-1 Graphiti | Episodes preserve source material while entities/edges/summaries are lossy derivations; raw episode search gaps show why source access matters. | candidate |
| KA-I-002 | Internal semantic entity identity is distinct from external/source identity. | KA-1 Graphiti | A graph UUID identifies a resolved record, not necessarily a person/account/device/repository identity in the outside world. | candidate |
| KA-I-003 | Namespace/domain identifiers are not authenticated principal identity. | KA-1 Graphiti | `group_id` scopes/routs data; FalkorDB races show even routing isolation can fail. Authentication/authorization must be host-derived. | candidate |
| KA-I-004 | Identity merge/split is a first-class, auditable and reversible knowledge transition. | KA-1 Graphiti | Current dedup can change the surviving UUID while the ordinary ingest path discards duplicate-pair evidence. | candidate |
| KA-I-005 | Ambiguous/unresolved identity must be representable; identity resolution must not force a merge. | KA-1 Graphiti | False merges and false splits are both observed failure classes; semantic/string heuristics are not universally decisive. | candidate |
| KA-I-006 | Supersession/invalidation is a privileged, reversible, provenance-bearing semantic transition. | KA-1 Graphiti | Current contradiction selection can retire true facts; historical fact retention is valuable but the transition needs stronger constraints. | candidate |
| KA-I-007 | Relationship labels alone are insufficient for safe reasoning about replacement; governed relationship semantics are required where consequences depend on them. | KA-1 Graphiti | PR #1729 exposes cardinality/replacement ambiguity (`WORKS_AT` versus `USES`) not represented by the current edge-type map. | candidate |
| KA-I-008 | World-valid time and system record/transaction time must remain distinct. | KA-1 Graphiti | `valid_at`/`invalid_at` versus `created_at`/`expired_at` is a strong reusable temporal pattern. | candidate |
| KA-I-009 | Current-state, historical, conflict and evidence retrieval are distinct query intents. | KA-1 Graphiti | Generic fact search can mix invalidated/current facts; raw episodes require a different evidence retrieval path. | candidate |
| KA-I-010 | Retrieval relevance/rank is not epistemic confidence, truth or authority. | KA-1 Graphiti | Vector/BM25/graph ranking optimizes relevance; it can still surface stale/false/untrusted facts. | candidate |
| KA-I-011 | Derived state such as embeddings, indexes and summaries must carry generation/profile identity and be rebuildable from more canonical evidence where practical. | KA-1 Graphiti | Invalid vectors and index lifecycle failures can break retrieval without changing underlying facts. | candidate |
| KA-I-012 | Storage/backend/query implementations must be qualified against semantic invariants; declaring a conceptual model is not sufficient. | KA-1 Graphiti | FalkorDB point-in-time and routing failures violate intended semantics without changing the high-level API. | candidate |
| KA-I-013 | Knowledge-domain routing for a request must be immutable/request-scoped when concurrent access can occur. | KA-1 Graphiti | Shared mutable driver routing caused silent cross-group writes. | candidate |
| KA-I-014 | Principal, purpose, sensitivity and hard eligibility constraints should be applied before protected knowledge is exposed to a model. | KA-1 Graphiti | Group filtering alone is not governance; current Zep security guidance independently recommends authenticated scope and server-side filtering. | candidate |
| KA-I-015 | Retrieved/persistent memory remains untrusted content unless its source is separately established as trusted; prompt position does not upgrade provenance. | KA-1 Graphiti | Raw episodes can contain arbitrary user/document text; managed Zep security guidance explicitly warns against privileged-context promotion. | candidate |
| KA-I-016 | Delete/forget completion is a multi-plane reconciliation result, not a single successful delete return. | KA-1 Graphiti | Episode deletion can leave orphaned semantic objects; vectors/indexes/history may have separate lifecycle. | candidate |
| KA-I-017 | Schema/ontology changes do not retroactively reinterpret historical records without an explicit migration/re-derivation event. | KA-1 Graphiti | Graphiti custom-type guidance leaves old records unchanged; retroactive typing requires re-ingestion. | candidate |
| KA-I-018 | Realized capability identity includes exact source/build/backend/schema/profile, not only a project or package name. | KA-1 Graphiti | Prebuilt MCP schema and source can differ; backend upgrades can move/obscure data. | candidate |
| KA-I-019 | Security/provenance metadata required for policy must be end-to-end verified through persistence, read, filtering, derived projection and migration. | KA-1 Graphiti | `episode_metadata` exists as a model field without a demonstrated OSS end-to-end filtering contract in the inspected repository. | candidate |
| KA-I-020 | Knowledge retrieval never grants execution authority. | KA-1 Graphiti | Ownership/relationship/context knowledge is descriptive; current application policy/principal state must separately authorize actions. | candidate |
| KA-I-021 | The substrate must distinguish unknown, known-false, not-established, conflicting and historically-true-but-no-longer-current states. | KA-1 Graphiti | Temporal invalidation covers history but the core fact model does not structurally distinguish the other epistemic absence/conflict states. | candidate |
| KA-I-022 | Assertion/relationship applicability must support structured scope such as environment, version, machine, project, person and time without relying only on arbitrary key/value blobs. | KA-1 Graphiti | Group/time/type/custom attributes provide partial scope but not a cross-domain applicability contract. | candidate |
| KA-I-023 | Transformation decisions that can materially alter future reasoning need provenance of their own. | KA-1 Graphiti | Source-to-fact lineage is strong, while merge, contradiction, summary and embedding transformations have weaker first-class audit identity. | candidate |
| KA-I-024 | Context construction is a separate layer from retrieval and must consider trust, freshness, permissions, actionability, relevance and token budget. | KA-1 Graphiti | Search returns candidate records; safe model exposure requires additional filtering/representation decisions. | candidate |

## Recurrence tracking

At the end of KA-1 all entries have recurrence count **1** because only Graphiti has been revisited in this campaign. Do not mark them reinforced until a later bounded task provides independent evidence.

## Next update rule

Later tasks should:

1. cite the existing invariant ID when independent evidence supports it;
2. add the new project/task to the evidence column;
3. note meaningful counterexamples or narrower scope;
4. create a new ID only when the concept is materially distinct.
