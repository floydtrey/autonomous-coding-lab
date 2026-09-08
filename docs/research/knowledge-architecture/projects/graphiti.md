# Graphiti Knowledge-Architecture Revisit — KA-1

**Campaign:** Knowledge Architecture Evidence Campaign  
**Research date:** 2026-09-07  
**Repository:** `getzep/graphiti`  
**Current upstream revision reverified:** `b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d`  
**Observed package version:** `graphiti-core 0.30.1`  
**Prior ACL report:** `docs/research/projects/graphiti.md`  
**Task status:** complete; Graphiti only; no architecture/storage/adoption decision

## 1. Scope and boundary

KA-1 revisits Graphiti under a narrower question than the original Task 20 report:

> What does current Graphiti evidence teach us about the requirements of a durable, general-purpose ACL/Vera knowledge substrate?

The prior report was used only as a discovery map. Current upstream code, docs, issues and PRs were reopened where the knowledge-architecture campaign required stronger evidence.

This task did **not**:

- select Graphiti or Zep;
- select a graph/database/vector store;
- design the final ACL/Vera ontology;
- implement storage or retrieval;
- create embeddings;
- migrate the historical research catalogs;
- research Mem0 or any later campaign target.

## 2. Current-generation verification

The Graphiti `main` branch still resolves to the same revision inspected by Task 20:

`b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d`

Therefore the source-level mechanisms previously studied have not drifted between the original report and this revisit. The incremental value of KA-1 comes from:

- re-reading the code under the new 26-question knowledge-architecture matrix;
- following recent issue/PR discussions more deeply;
- identifying identity-resolution, relationship-semantics, governance and runtime-profile lessons that were secondary in Task 20;
- distinguishing Graphiti OSS behavior from managed Zep documentation and guarantees.

## 3. Executive findings

The highest-value KA-1 conclusions are:

1. **Raw evidence and semantic knowledge are different planes.** Episodic nodes preserve source content/event time; entity nodes and entity edges are derived semantic representations. This separation is worth preserving in ACL/Vera.
2. **Graphiti is temporal, not epistemically authoritative.** `valid_at`/`invalid_at` and `created_at`/`expired_at` are valuable bitemporal-like semantics, but they do not encode source trust, verification, confidence, dispute or action authority.
3. **Supersession is relation-semantic, not merely similarity-semantic.** Current invalidation failures and PR #1729 show that whether one relationship replaces another can depend on cardinality and relation semantics that Graphiti does not currently record.
4. **Entity resolution is an authoritative identity mutation and needs its own ledger.** Current node dedup can deterministically collapse identities, while the normal `add_episode` path discards the returned duplicate-pair record.
5. **Identity errors occur in both directions.** Automatic merge heuristics can over-merge, while issue #1734 shows exact same-name entities can fail to become candidates because exact-name logic sits behind an embedding-similarity gate.
6. **Conflict/invalidation must be bounded before the model and checked after it.** #1728 and #1666 show false and missed contradictions. A model classification cannot directly retire high-value canonical knowledge without structural/trust/relation constraints and an audit trail.
7. **Current, historical, conflict and evidence retrieval are different intents.** Current MCP fact search can express temporal filters but does not default to live facts only; raw episode search by query is also missing from that tool surface.
8. **Search rank is not truth/confidence.** Graphiti’s hybrid vector/BM25/graph ranking is useful for candidate retrieval, but stale/false facts can still rank highly.
9. **Namespace is not principal identity.** `group_id` is a graph partition/routing field. Recent FalkorDB failures show that even data routing can cross group boundaries under concurrency. Authentication and authorization must be external and host-derived.
10. **Request-scoped immutable routing is a knowledge-integrity requirement.** #1676 and #1840 elevate shared mutable driver selection from an isolated bug to a systemic cross-tenant data-corruption class.
11. **Derived-state health must be explicit.** Null/dimension-mismatched embeddings, untracked index creation and backend-specific query behavior can make a valid canonical graph unretrievable or temporally wrong.
12. **Deletion is multi-plane reconciliation, not one delete call.** Episode deletion depends on provenance links and can leave orphaned semantic state. A Vera “forget” operation needs explicit settlement across canonical evidence, derived graph state, indexes, caches and retained audit data.
13. **Schema changes are not retroactive truth changes.** Graphiti’s custom-type guidance explicitly leaves old nodes/edges unchanged; retroactive typing requires re-ingestion into a new graph. Ontology/schema version must therefore be part of interpretation.
14. **Source revision is not realized deployment identity.** Issue #1656 shows packaged MCP schema can differ from tagged source; #1108 shows backend layout changes can make old data disappear after upgrade. Exact build/backend/schema/profile identity matters.
15. **Arbitrary metadata cannot be trusted merely because a model field exists.** Current OSS `EpisodicNode` declares `episode_metadata`, but a repository search found no downstream filtering references, and the single-node save path does not include it in its explicit persistence arguments. Required provenance/security fields need end-to-end persistence/query tests.
16. **Retrieved memory remains untrusted data.** Current Zep security guidance independently recommends keeping retrieved context out of privileged instruction channels and authorizing actions in application code from authenticated state, not from memory.

## 4. Core conceptual planes observed in Graphiti

### 4.1 Episode / raw-evidence plane

Current `EpisodicNode` carries:

- stable UUID;
- name;
- `group_id`;
- source type (`message`, `json`, `text`, `fact_triple`);
- source description;
- raw content;
- `created_at`;
- `valid_at` / episode reference time;
- referenced semantic edge UUIDs;
- an optional `episode_metadata` field in the Pydantic model.

Graphiti documentation describes episodes as ingestion events linked to extracted entities by `MENTIONS` edges and explicitly frames them as provenance and point-in-time-query material.

**Architectural lesson:** raw observations/resources must remain independently addressable after semantic extraction. Derived knowledge should not be the only surviving representation.

**Confidence:** high.

### 4.2 Entity plane

`EntityNode` gives a resolved entity a UUID, name, labels/types, summary, attributes and name embedding.

This is useful for a general substrate, but the stable UUID denotes Graphiti’s resolved record, not necessarily a durable external identity such as a Git repository ID, hardware serial, account ID, biometric identity or person identity.

**Architectural lesson:** internal semantic entity identity and external/source identity should be separate concepts. Aliases/account IDs/face identities/device IDs should attach to an entity rather than replace it.

**Confidence:** high.

### 4.3 Relationship / assertion plane

`EntityEdge` is a first-class record with:

- UUID;
- source and target UUIDs;
- relation name;
- natural-language fact text;
- supporting episode UUID list;
- fact embedding;
- `valid_at`;
- `invalid_at`;
- `created_at`;
- `expired_at`;
- episode `reference_time`;
- custom attributes.

This is strong evidence for treating important relationships as first-class provenance-bearing knowledge, not as unqualified object pointers.

**Architectural lesson:** ACL/Vera should be graph-compatible even if its first physical store is not a graph database.

**Confidence:** high.

### 4.4 Community / summary plane

Graphiti can derive higher-level community summaries from graph structure. Entity summaries are also maintained as derived natural-language projections.

**Architectural lesson:** summaries and communities are useful context views but should be rebuildable derived state, not the sole canonical evidence.

**Confidence:** high.

## 5. Temporal semantics are valuable but must be tested end-to-end

Graphiti separates two time dimensions on semantic facts:

- **world-valid time:** `valid_at`, `invalid_at`;
- **system/transaction-like time:** `created_at`, `expired_at`.

Episodes also carry a reference/event time.

This is directly reusable conceptually for facts such as:

- a device IP valid during one interval;
- a preference that changed;
- a job role that ended;
- a software defect that exists only in specific versions/time periods.

### Failure evidence: #1625

Open issue #1625 reproduces a FalkorDB point-in-time query returning an episode whose `valid_at` is later than the requested reference time. No exception is raised.

**Architectural lesson:** declaring bitemporal semantics in the canonical model is not enough. Each storage/query implementation must pass point-in-time regression fixtures. Backend identity and query semantics are behavior-bearing.

**Non-conclusion:** #1625 does not invalidate Graphiti’s temporal conceptual model or prove the same defect exists in Neo4j.

**Confidence:** high for the reported FalkorDB path; high for the derived requirement.

## 6. Invalidation exposes the difference between temporal state and epistemic truth

### 6.1 Failure evidence: #1728

Issue #1728 reports collateral invalidation where semantically similar but unrelated facts were retired. The current source path still performs a group-wide semantic search for invalidation candidates and presents the judge with fact strings lacking endpoint/relation/provenance/trust context.

A model-selected contradiction can cause:

- an older edge to be retired; or
- a newly extracted edge to be written already invalidated when a selected candidate is later.

### 6.2 Failure evidence: #1666

Issue #1666 reports the opposite failure mode: a non-reasoning small model missed genuine contradictions under the stock response schema. The reported controlled test improved materially when reasoning was elicited before the result arrays.

### 6.3 Structural mitigation remains incomplete

Open PR #1729 proposes bounding invalidation to relationships that could plausibly replace each other. Its stated limitation is particularly important for ACL/Vera:

- `Dana WORKS_AT Northwind` -> `Dana WORKS_AT Contoso` may be a replacement;
- `ServiceA USES Postgres` and `ServiceB USES Postgres` are additive facts.

Both can share the same relation name and an endpoint in the same structural position. Correct supersession depends on relation semantics/cardinality that the graph does not record.

### Derived requirement

Invalidation/supersession should be a first-class, reversible, provenance-bearing state transition constrained by:

- subject/object identity;
- controlled relation identity;
- relation semantics/cardinality/replacement policy;
- source/evidence class;
- trust/verification state;
- temporal compatibility;
- confidence/reason;
- current policy for the domain;
- explicit review for high-risk classes.

The safe failure direction will often be to retain a visible conflict/stale candidate rather than silently retire a true fact.

**Confidence:** high.

## 7. Controlled relationship vocabulary needs more than names and endpoints

Graphiti supports custom edge types through Pydantic models, and `edge_type_map` constrains which configured relationship names may connect ordered source/target entity-type pairs. This is useful domain/range-like control.

Current MCP examples include relationship types such as `WorksFor`, `LocatedAt`, `Owns` and `Requires`.

However, the current type/map surface does not encode the semantic information exposed as necessary by #1729, such as whether a relation is:

- one-to-one, one-to-many or many-to-many;
- functional for a given subject scope;
- symmetric or asymmetric;
- replaceable/current-state versus cumulative/additive;
- expected to have an inverse relation;
- safe for automatic supersession;
- identity-defining versus descriptive.

### Candidate general requirement

A future ACL/Vera controlled relationship vocabulary should be extensible but governed. A relation definition may eventually need a stable semantic ID plus optional metadata for:

- canonical name and aliases;
- source/target type constraints;
- direction/symmetry/inverse;
- cardinality/functional constraints where meaningful;
- temporal semantics;
- supersession/replacement behavior;
- sensitivity/actionability defaults;
- vocabulary version/provenance.

This is a **requirement candidate**, not a final schema decision.

**Confidence:** high that Graphiti lacks these semantics in the examined surface; medium on the exact fields ACL/Vera should ultimately use.

## 8. Entity resolution must be auditable and reversible

### 8.1 Current deterministic behavior

Current node resolution:

1. retrieves at most 15 semantic candidates with cosine floor 0.6;
2. tries exact normalized-name matching among those candidates;
3. for sufficiently specific names, uses MinHash/LSH and 3-gram Jaccard;
4. automatically accepts a fuzzy candidate at Jaccard >= 0.9;
5. sends unresolved cases to an LLM dedupe prompt.

The normal `Graphiti.add_episode` path currently calls:

`nodes, uuid_map, _ = await resolve_extracted_nodes(...)`

The third return value is the computed duplicate-pair list, which is discarded by that path.

The bulk path uses duplicate mappings to compress UUIDs during in-memory processing; it does not establish a general durable entity-merge event ledger.

### 8.2 Failure evidence: #1734

Issue #1734 reports four exact same-name `DGIA` entity records because the semantic candidate gate can exclude an exact-name record before exact string comparison. Open PR #1741 proposes adding a full-text candidate pass.

This demonstrates identity failure in both directions:

- false merge: distinct real-world entities become one;
- false split: the same real-world entity remains multiple records.

### 8.3 External review: #1771

Issue #1771 is a disclosed competitor-authored static review, so it is not treated as neutral benchmark evidence. However, its key source-reading claim that the normal path discards duplicate pairs was independently confirmed against current main during KA-1.

### Derived requirement

Entity consolidation should itself be canonical knowledge/audit state, with enough evidence to answer:

- which records/identities were considered;
- why they were judged the same;
- algorithm/model/version/profile used;
- confidence/verification status;
- who/what approved the merge when required;
- surviving canonical entity;
- reversible mapping to prior identities;
- what downstream facts were re-pointed;
- whether a later correction split the entity again.

People, biometric identities, accounts and devices should have stricter merge policy than low-risk conceptual entities.

**Confidence:** high.

## 9. Provenance is strong for facts but incomplete for transformations

Graphiti’s semantic edges retain supporting episode UUIDs, and episodes retain raw content and source descriptions. This is a strong evidence-lineage pattern.

But provenance gaps remain for transformations such as:

- entity merge decisions;
- contradiction judge decisions;
- summary generations;
- embedding generations;
- ontology/profile changes;
- access/governance decisions.

Provenance answers **why the system believes or derived something**; it does not itself prove truth or authorization.

### Candidate chain

The future substrate should support chains conceptually like:

`Resource/Source -> Evidence Fragment/Observation -> Assertion/Relationship -> Derived Summary/Invariant -> Procedure/Test/Decision`

with each transformation independently identifiable where its result can materially affect future reasoning or action.

## 10. Epistemic state is a major gap in the core fact model

The examined `EntityEdge` core fields provide temporal and provenance linkage but no generic first-class fields for:

- confidence;
- verification status;
- explicit user statement versus model inference;
- authenticated configuration versus third-party claim;
- disputed status;
- source trust class;
- negative/unknown/not-established state;
- permitted use/actionability class.

These concepts can potentially be represented in custom attributes, but that is not the same as a durable cross-domain epistemic contract.

### Derived requirement

ACL/Vera needs an epistemic envelope that is independent of domain-specific content. A confidence score alone is insufficient: an explicit statement, authenticated sensor record and AI inference can all have different usage rules even when numerically “high confidence.”

**Confidence:** high that the examined core does not provide these generic semantics; medium on final ACL/Vera representation.

## 11. Current, historical, conflict and evidence retrieval are separate contracts

### 11.1 Current source capability

`SearchFilters` supports date predicates over:

- `valid_at`;
- `invalid_at`;
- `created_at`;
- `expired_at`;

and filters for node labels, edge types, edge UUIDs and properties.

### 11.2 Current MCP behavior

`search_memory_facts` accepts optional valid/invalid date ranges but does not default to `invalid_at IS NULL`.

Issue #1645 explicitly requests “hide superseded facts by default” with an opt-in historical mode.

### 11.3 Raw episode retrieval gap

Issue #1427 notes that the MCP server searches nodes and facts but does not offer query-based semantic/full-text retrieval of raw episodes; `get_episodes` is pagination/group based. This matters when extraction/summaries drop exact literals such as URLs, numeric anchors or lists.

### Derived retrieval contracts

The future system should make intent explicit, for example conceptually:

- `current_state/current_fact`;
- `historical_state/history`;
- `conflict/dispute`;
- `evidence/source`;
- `semantic discovery`.

A context builder should not ask a model to infer which returned temporal record is current when the retrieval layer can enforce that deterministically.

**Confidence:** high.

## 12. Hybrid retrieval is useful, but ranking is not epistemology

Graphiti combines semantic/vector search, BM25/full-text search and graph proximity/traversal, with RRF, MMR and optional cross-encoder reranking recipes.

This is strong reference material for the campaign’s future composite-retrieval design.

However:

- relevance score is not truth;
- graph distance is not authority;
- vector similarity is not identity;
- a highly relevant superseded fact can still be wrong for a current-state query;
- a lower-ranked authoritative configuration can matter more than a high-ranked forum claim.

### Derived requirement

Eligibility filters for principal/purpose, temporal liveness, source/trust, sensitivity and actionability should be applied before or alongside ranking where those constraints are hard requirements.

## 13. Namespace and authorization must remain separate

Current `group_id` is described in core models as the graph partition. Graphiti documentation presents group IDs as namespacing and gives multi-tenant organization examples.

Neither a group string nor successful group-scoped query is authenticated principal identity.

### Failure evidence: #1676 and #1840

#1676 reproduces concurrent cross-group writes on FalkorDB because `add_episode` mutates shared `self.driver`/`self.clients.driver` state and continues through multiple await points.

The 2026-09-05 FalkorDB triage issue #1840 groups multiple critical bugs under the same shared-driver-mutation architecture and explicitly labels the effect as silent cross-tenant data corruption.

Current `Graphiti.add_episode` and bulk ingestion source still contain the shared driver mutation when `group_id` changes.

### Derived requirement

A general knowledge system should bind every retrieval/mutation to:

- authenticated principal;
- authorized knowledge domain(s);
- purpose/use context;
- request-scoped immutable routing;

before storage access occurs.

Namespace possession must never grant authority.

**Confidence:** high.

## 14. Privacy, sensitivity and governance need an outer policy layer

Graphiti OSS does not provide a general fact-level principal/purpose/sensitivity policy in the examined core model.

Issue #1679 proposes ingestion and retrieval governance hooks for PII, fact-level access control and audit evidence. It is a feature request, not proof of an implemented Graphiti guarantee.

Current managed Zep security guidance is nevertheless useful independent evidence for architecture boundaries. It explicitly recommends:

- deriving user/graph IDs from authenticated application state;
- treating retrieved memory as untrusted data;
- keeping retrieved context out of privileged instruction channels;
- scoping retrieval server-side;
- authorizing consequential actions in application code from current authenticated state rather than memory.

### Derived requirement

Retrieval should occur under a principal and purpose. Sensitivity/read/write/use semantics should be canonical policy inputs, not inferred from graph grouping or prompt text.

## 15. Context construction is a separate security boundary

Graphiti returns records; a separate layer decides what enters a model context.

Persistent memory can contain user messages, documents, web content and other untrusted material. The fact that content has been extracted, embedded, summarized or placed in a graph does not upgrade its trust.

### Candidate context-builder rules

Before model exposure, consider:

- requesting principal;
- query purpose;
- allowed domains/sources;
- temporal liveness;
- provenance/evidence quality;
- epistemic class/confidence;
- sensitivity;
- actionability;
- relevance;
- token budget;
- representation (raw evidence versus summary).

Retrieved data should remain data, not become system/developer policy merely because a framework convenience method places it there.

## 16. Derived-state integrity must be explicit

### 16.1 Embeddings: #1328 and #1505

#1328 reports Neo4j similarity search failing the entire query when stored embeddings are null, invalid or dimension mismatched. #1505 reports NaN/Inf embedding values propagating into dedup/storage.

**Requirement:** vector representations need generation/profile identity, validation, migration/rebuild state and fault isolation. One corrupt vector should not destroy access to otherwise valid canonical knowledge.

### 16.2 Index lifecycle: #1643

#1643 reports FalkorDB index construction launched as an untracked background task from driver construction, creating races with first use/reset/shutdown.

**Requirement:** index/schema readiness is an observable lifecycle state. “Client constructed” is not “derived indexes settled.”

### 16.3 Summaries and semantic projections

Entity/community summaries are generated representations that can drift from their source facts. They should remain traceable and rebuildable.

**Confidence:** high.

## 17. Deletion and retention are reconciliation problems

Graphiti’s `remove_episode` attempts provenance-aware cascading cleanup rather than simply deleting the raw episode.

However issue #1083 reports orphaned entities that lack `MENTIONS` links and therefore evade episode-based cleanup. Earlier MCP shallow-delete behavior was separately corrected toward calling `remove_episode`, showing how tool surface and core semantics can diverge.

### Derived requirement

A forget/erasure operation needs a settlement checklist across all relevant planes, such as:

- raw resource/evidence;
- semantic entities/relationships;
- source associations;
- summaries;
- embeddings/vector indexes;
- graph/search indexes;
- caches/context projections;
- operational histories;
- audit records/backups according to explicit retention policy.

Completion should be established by reconciliation/read-back evidence, not an SDK success return alone.

Audit retention and personal-data erasure are separate policy questions.

**Confidence:** high.

## 18. Schema/ontology evolution must preserve interpretation history

Graphiti’s current custom entity/edge type documentation says:

- new types can be used for future episodes without reclassifying existing records;
- existing nodes continue to work without the new classification;
- retroactively typing prior data requires re-ingestion into a new graph;
- changing custom ontology does not automatically rewrite already-created nodes/edges.

This is a healthy warning against pretending schema changes retroactively alter historical truth.

### Failure evidence: #1108

#1108 reports data appearing missing after a FalkorDB upgrade changed data location and asks for a migration path.

### Derived requirement

Persist or reconstruct:

- canonical schema/ontology version applicable to a record/derivation;
- storage/backend migration version;
- transformation/re-ingestion generation;
- derived-index generation;
- source profile used to interpret old records.

Migration must be explicit and verified; storage layout changes must not silently look like knowledge deletion.

## 19. Realized deployment identity is more than a package version

Issue #1656 reports that an official prebuilt MCP image exposed a tool schema missing temporal inputs present in tagged source.

Therefore behavior-bearing deployment identity may include:

- source commit;
- package version;
- container/artifact digest;
- backend/driver/version;
- database/graph routing mode;
- model + structured-output profile;
- embedding model/dimension;
- reranker;
- MCP/API tool-schema digest;
- ontology/schema version;
- migration history.

### Derived requirement

Claims about “supported capability” should attach to a realized profile, not only a product/project name.

## 20. `episode_metadata` is a cautionary end-to-end verification example

Current OSS `EpisodicNode` declares an optional `episode_metadata` dictionary described as customer-defined metadata for filtering.

During KA-1, a repository-wide search found no other occurrence of `episode_metadata`. The explicit single-node `save()` argument dictionary does not include it. The bulk conversion can carry the field in a Python dict, but no repository search showed query/filter construction referencing the field.

### Architectural lesson

A field important to provenance, sensitivity, principal/purpose or retention is not “supported” until tests verify:

`write -> durable storage -> read -> filter/query -> derived projection -> migration`

The future ACL/Vera architecture should distinguish conceptual schema availability from realized backend capability.

**Non-conclusion:** this source reading does not prove no downstream/custom driver could persist the field generically. It proves the examined OSS repository does not expose a demonstrated end-to-end metadata-filter contract around this field.

**Confidence:** medium-high.

## 21. Unknown, negative and disputed knowledge need explicit representation

Graphiti can store natural-language negative facts and can temporally invalidate facts, but the examined core model has no generic structural distinction among:

- known false;
- unknown;
- searched-for but not established;
- disputed/conflicting;
- inferred with uncertainty;
- historically true but no longer current.

Those states should not be collapsed into absence of an edge or a natural-language sentence if deterministic reasoning will depend on them.

### Derived requirement

The future knowledge substrate should preserve the difference between “no evidence,” “evidence of absence,” “conflicting evidence,” and “superseded historical truth.”

**Confidence:** high as a campaign requirement; medium on the final representation.

## 22. Scope of truth must be structured

Graphiti offers useful scope axes:

- `group_id`;
- temporal intervals;
- entity/edge type;
- custom attributes.

But a general ACL/Vera assertion may be valid only for a specific:

- machine;
- software version;
- project;
- environment;
- person;
- location;
- policy regime;
- runtime profile;
- time interval.

Custom attributes alone are too unconstrained to guarantee deterministic cross-domain interpretation.

### Derived requirement

Assertions/relationships need a structured applicability/scope mechanism while still allowing domain extension. This remains an open design problem for the synthesis phase.

## 23. Recovery and write settlement

The original Task 20 report already established that the primary episode/entity/edge bulk write can settle transactionally in important paths, while saga association, deletion and other maintenance cross additional operations.

KA-1 retains the broader rule:

- canonical write state;
- derived-maintenance state;
- index readiness;
- deletion settlement;
- external action/effect settlement

are different things.

Graphiti is a knowledge/memory layer, not an exactly-once external-effect ledger.

## 24. Knowledge versus authority

Nothing in Graphiti’s semantic graph should be interpreted as automatic permission to act.

Examples:

- knowing a person owns a vehicle does not authorize starting it;
- retrieving a `WorksFor` relationship does not authenticate the person;
- a stored instruction is evidence/content, not policy;
- a `group_id` does not grant access;
- a high search score does not grant actionability.

Current Zep security guidance independently reinforces this boundary by instructing applications to authorize actions outside the model from current authenticated state.

**Candidate invariant:** knowledge retrieval never grants execution authority.

## 25. Evidence-question matrix

| # | Campaign question | Graphiti evidence | KA-1 assessment |
|---|---|---|---|
| 1 | Stable identity | UUIDs for nodes/edges; external identity not first-class | Partial; useful internal identity, external identity layer still required |
| 2 | Identity vs namespace | `group_id` is partition/routing metadata | Strong lesson: namespace != principal |
| 3 | Provenance | Episodes, `MENTIONS`, edge episode UUIDs | Strong for source->fact; weak for merge/maintenance decisions |
| 4 | Epistemic state | No generic trust/confidence/verification/dispute envelope | Major gap |
| 5 | Temporal truth | `valid_at`/`invalid_at` + `created_at`/`expired_at` | Strong concept; backend correctness must be qualified |
| 6 | Conflict/supersession | Soft invalidation; LLM contradiction judge | Useful mechanism, unsafe as sole truth authority |
| 7 | Relationships | First-class typed edges | Strong, but relation cardinality/replacement semantics missing |
| 8 | Permissions/sensitivity | Namespaces; no general core fact ACL/sensitivity model | Outer principal/purpose policy required |
| 9 | Actionability | No generic use/actionability classification | Gap |
| 10 | Knowledge vs authority | Graph stores context, not authorization | Boundary must be enforced above memory |
| 11 | Resources/artifacts | Episodes hold content/source description, not general resource/checksum/version model | Partial |
| 12 | Canonical vs derived | Episodes/facts plus summaries/embeddings/communities | Separation visible but canonical contract not explicit |
| 13 | Structured retrieval | Labels/types/date/property filters | Good building block |
| 14 | Relationship retrieval | Graph traversal/distance | Strong building block |
| 15 | Full-text retrieval | BM25 for graph objects; MCP raw episode query gap | Partial |
| 16 | Semantic retrieval | Embeddings + rerankers | Strong discovery mechanism; not truth |
| 17 | Composite retrieval | Hybrid recipes + graph proximity + filters | Strong retrieval reference, missing principal/policy/epistemic composition |
| 18 | Context construction | Caller/framework responsibility | Requires separate policy-aware context builder |
| 19 | Poisoning/injection | Raw episode text feeds extraction; managed docs warn memory is untrusted | Core trust layer incomplete |
| 20 | Concurrency | Cross-group driver mutation failures | Critical requirement evidence |
| 21 | Derived-state integrity | embedding/index/summary failure classes | Critical requirement evidence |
| 22 | Deletion/retention | provenance-aware cascade plus orphan failures | Multi-plane reconciliation required |
| 23 | Schema/version evolution | old records stay old; re-ingest for retro typing | Strong migration lesson |
| 24 | Recovery semantics | multi-stage writes/maintenance | Knowledge persistence != effect settlement |
| 25 | Unknown/negative knowledge | no generic structural distinction | Gap |
| 26 | Scope of truth | group/time/types/custom attrs | Partial; general applicability model still required |

## 26. Candidate invariants contributed by KA-1

These are campaign candidates, not final architecture decisions:

1. Preserve raw evidence separately from derived semantic knowledge.
2. Internal semantic entity ID is not the same as external/source identity.
3. Namespace/domain ID is not authenticated principal identity.
4. Entity merge/split is a first-class, auditable, reversible identity transition.
5. Unresolved/ambiguous identity must be representable; do not force a merge.
6. Supersession/invalidation is a privileged, reversible semantic transition.
7. Relationship names alone are insufficient for safe supersession; governed relation semantics matter.
8. World-valid time and record/transaction time remain distinct.
9. Current, historical, conflict and evidence retrieval are separate intents.
10. Retrieval relevance/rank is not epistemic confidence or authority.
11. Derived indexes/embeddings/summaries must carry generation/profile identity and be rebuildable.
12. Backend/query implementations must pass temporal and isolation fixtures; conceptual semantics are not enough.
13. Request-scoped immutable routing is required for cross-domain isolation.
14. Principal/purpose/sensitivity eligibility must precede model context exposure for protected knowledge.
15. Retrieved memory remains untrusted content regardless of persistence or prompt position.
16. Delete/forget completion requires multi-plane reconciliation.
17. Schema/ontology changes do not retroactively alter historical records without an explicit migration/re-derivation event.
18. Realized deployment capability is identified by exact source/build/backend/schema/profile, not a project name alone.
19. Security/provenance metadata is not relied upon until persistence, read, filtering and migration are end-to-end verified.
20. Knowledge retrieval never grants execution authority.

## 27. Failure patterns contributed by KA-1

1. **Namespace-as-authorization** — treating a group/session/user string as access authority.
2. **Shared mutable routing state** — concurrent requests silently cross knowledge domains.
3. **Unbounded LLM invalidation** — semantic similarity + model judgment directly retires current truth.
4. **Newest-wins epistemology** — temporal recency silently outranks stronger evidence.
5. **Relation-label-only supersession** — additive many-to-many facts are mistaken for replacements.
6. **Identity merge without merge ledger** — canonical referent changes without durable reversible evidence.
7. **Exact identity evidence hidden behind semantic candidate gate** — obvious duplicates never reach deterministic logic.
8. **Generic memory search mixes live and retired facts** — model must guess which is current.
9. **Derived semantic representation becomes the only searchable representation** — exact literals survive only in raw evidence that is hard to retrieve.
10. **Corrupt derived vector poisons whole retrieval** — one invalid embedding causes query failure.
11. **Untracked background index initialization** — storage appears ready before derived indexes settle.
12. **Delete follows incomplete provenance links** — orphaned semantic data survives a source delete.
13. **Package/version label stands in for realized capability** — deployed tool schema/backend behavior differs from source expectations.
14. **Schema change treated as retroactive migration** — old records silently interpreted under a new ontology.
15. **Metadata field assumed durable because it exists in the model** — no end-to-end persistence/query proof.
16. **Retrieved content promoted to policy** — persistent memory or context placement silently gains instruction authority.

## 28. Representative retrieval tests derived from Graphiti

Save these for the later retrieval-requirements task:

- What is the current employer of Person X, excluding historical employers?
- Show every employer Person X has had, with evidence and validity intervals.
- Why does the system believe Person X works at Company Y?
- Show current facts that contradict or compete with this relationship.
- Find the raw source passage containing an exact URL that was summarized away in semantic extraction.
- Find semantically related facts about duplicate external actions, but exclude superseded findings.
- Return facts about Device X only if they are valid for firmware version Y and current network Z.
- Show all identities/aliases/accounts believed to represent Person X and the merge/split evidence.
- Retrieve facts relevant to a principal while excluding restricted sources before ranking.
- Reconstruct what the system would have believed about Entity X at a historical time using only records valid then.
- Identify derived vectors/indexes whose generation profile no longer matches the active embedding schema.
- Prove that a deleted episode no longer contributes to any retrievable semantic fact while preserving only explicitly required audit evidence.

## 29. Unresolved questions for later campaign phases

Do **not** solve these during KA-1:

- What exact canonical primitive should represent assertions/relationships/state/preferences?
- Should relation semantics/cardinality be intrinsic to a relation vocabulary record or policy layer?
- How should identity merge/split events interact with facts previously attached to each entity?
- What epistemic classes and confidence semantics are sufficiently general without becoming an arbitrary metadata bag?
- How should negative/unknown/not-established knowledge be represented?
- Which provenance standard should shape evidence lineage?
- How should principal/purpose/sensitivity policy compose with graph, structured, full-text and semantic retrieval?
- Which physical store can implement these requirements efficiently?

These belong to later cross-project/gap/synthesis tasks.

## 30. Primary/current sources revisited

Current Graphiti source/docs:

- https://github.com/getzep/graphiti
- https://github.com/getzep/graphiti/blob/main/graphiti_core/nodes.py
- https://github.com/getzep/graphiti/blob/main/graphiti_core/edges.py
- https://github.com/getzep/graphiti/blob/main/graphiti_core/graphiti.py
- https://github.com/getzep/graphiti/blob/main/graphiti_core/search/search_filters.py
- https://github.com/getzep/graphiti/blob/main/graphiti_core/utils/maintenance/node_operations.py
- https://github.com/getzep/graphiti/blob/main/graphiti_core/utils/maintenance/dedup_helpers.py
- https://github.com/getzep/graphiti/blob/main/graphiti_core/utils/bulk_utils.py
- https://github.com/getzep/graphiti/blob/main/mcp_server/src/graphiti_mcp_server.py
- https://github.com/getzep/graphiti/blob/main/mcp_server/src/models/edge_types.py
- https://help.getzep.com/graphiti/getting-started/overview
- https://help.getzep.com/graphiti/core-concepts/adding-episodes
- https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types
- https://help.getzep.com/graphiti/working-with-data/searching

High-value issue/PR evidence:

- https://github.com/getzep/graphiti/issues/1728 — collateral invalidation
- https://github.com/getzep/graphiti/issues/1666 — contradiction judge small-model failures
- https://github.com/getzep/graphiti/pull/1729 — structural invalidation guard and cardinality limitation
- https://github.com/getzep/graphiti/issues/1676 — concurrent cross-group FalkorDB corruption
- https://github.com/getzep/graphiti/issues/1840 — systemic FalkorDB architecture triage
- https://github.com/getzep/graphiti/issues/1625 — point-in-time retrieval temporal violation
- https://github.com/getzep/graphiti/issues/1645 — live versus invalidated search behavior
- https://github.com/getzep/graphiti/issues/1427 — raw episode search gap
- https://github.com/getzep/graphiti/issues/1328 — invalid embeddings can fail search
- https://github.com/getzep/graphiti/issues/1643 — untracked index creation
- https://github.com/getzep/graphiti/issues/1108 — upgrade/data-layout migration gap
- https://github.com/getzep/graphiti/issues/1734 — exact-name duplicate candidate failure
- https://github.com/getzep/graphiti/pull/1741 — proposed full-text dedup candidate pass
- https://github.com/getzep/graphiti/issues/1771 — external merge-accountability source review; independently checked where used
- https://github.com/getzep/graphiti/issues/1083 — orphaned entities after episode deletion
- https://github.com/getzep/graphiti/issues/1679 — governance-hook proposal

Security/context guidance used only as external corroboration, not OSS Graphiti guarantees:

- https://help.getzep.com/memory-security
- https://help.getzep.com/retrieving-context

## 31. Explicit non-conclusions

KA-1 does **not** conclude that:

- Graphiti is unsafe or unsuitable for all memory use;
- Graphiti should or should not be selected for Vera;
- Neo4j, FalkorDB or any graph database should be selected;
- Graphiti’s current open issues apply to every backend/configuration;
- every LLM contradiction/merge judgment is wrong;
- Graphiti’s managed Zep product has the same security/governance surface as OSS Graphiti;
- the candidate ACL/Vera invariants above are final architecture rules;
- a graph-shaped conceptual model requires a graph database;
- relation cardinality fields alone solve epistemic supersession;
- historical Graphiti data should be migrated into a future ACL/Vera store now.

## 32. KA-1 stop point

Graphiti has been revisited against the knowledge-architecture question matrix, current upstream behavior was rechecked, new identity/relationship/governance requirements were recorded, and cumulative ledgers/state are updated in the same task.

**Stop before Mem0.**
