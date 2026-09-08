# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** project revisits, coverage scan, promoted Agno revisit and first standards/domain gap task complete; stopped before relationship/ontology gap research  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

## Governing plan

Read `CAMPAIGN_PLAN.md` before doing any further work in this campaign.

The completed Tasks 1–31 project-by-project campaign remains historical evidence. Do not restart it and do not rewrite its catalogs merely to fit the future knowledge model.

No completed evidence task authorizes final architecture synthesis, database selection, retrieval implementation, embeddings, model benchmarking or ACL/Vera implementation.

---

## Completed campaign work

### High-yield project revisits

1. **KA-1 — Graphiti Knowledge-Architecture Revisit** — complete
2. **KA-2 — Mem0 Knowledge-Architecture Revisit** — complete
3. **KA-3 — Letta Code Knowledge-Architecture Revisit** — complete
4. **KA-4 — LlamaIndex Knowledge-Architecture Revisit** — complete
5. **KA-5 — Mastra Knowledge-Architecture Revisit** — complete
6. **KA-6 — LangGraph Knowledge-Architecture Revisit** — complete
7. **KA-7 — Google ADK Knowledge-Architecture Revisit** — complete
8. **KA-8 — Microsoft Agent Framework Knowledge-Architecture Revisit** — complete
9. **KA-9 — OpenAI Agents SDK Knowledge-Architecture Revisit** — complete
10. **KA-10 — Model Context Protocol Knowledge-Architecture Revisit** — complete

### Coverage/promotion work

11. **Bounded post-revisit coverage scan** — complete
12. **KA-11 — Agno Knowledge-Architecture Revisit** — complete

### Standards/domain gap research

13. **KA-G1 — Epistemic, Temporal, Conflict and Negative-Knowledge Semantics** — complete

---

## Detailed reports

Project revisits:

- `projects/graphiti.md`
- `projects/mem0.md`
- `projects/letta-code.md`
- `projects/llamaindex.md`
- `projects/mastra.md`
- `projects/langgraph.md`
- `projects/google-adk.md`
- `projects/microsoft-agent-framework.md`
- `projects/openai-agents-sdk.md`
- `projects/model-context-protocol.md`
- `projects/agno.md`

Coverage scan:

- `COVERAGE_SCAN.md`

Gap research:

- `gaps/epistemic-temporal-conflict.md`

Cumulative ledgers:

- `invariants.md`
- `failure-patterns.md`

This state file is intentionally a compact current checkpoint. Detailed prior evidence remains in the dedicated reports rather than being duplicated here.

---

# KA-G1 boundary and verification

The user explicitly authorized continuation into the standards/domain gap phase after KA-11.

KA-G1 was bounded to Priority A semantics only:

- epistemic state;
- unknown/negative knowledge;
- temporal/bitemporal semantics;
- conflict/supersession;
- correction history;
- structured temporal/method applicability where directly relevant.

Explicitly excluded:

- identity/entity-resolution research;
- controlled relationship/ontology research;
- formal provenance standards beyond source/reference distinctions needed for this task;
- ABAC/ReBAC authorization;
- privacy erasure mechanics;
- resource/artifact identity;
- retrieval-requirements construction;
- hostile/adversarial review execution;
- architecture synthesis;
- storage technology selection;
- implementation.

Starting branch verified at:

`efda61ba0fd1146d0da98b85e218f475cad4a42d`

Expected commit message at start:

`research: complete Agno knowledge architecture revisit`

Governance re-read:

- `docs/research/README.md`
- `docs/research/PROCESS.md`
- `docs/research/sources.md`
- `docs/research/watchlist.md`
- `docs/research/knowledge-architecture/CAMPAIGN_PLAN.md`
- this campaign state
- cumulative invariant/failure ledgers

---

# KA-G1 primary evidence

## W3C OWL 2 Primer

https://www.w3.org/TR/owl-primer/

Used for:

- open-world assumption;
- explicit negative property assertions;
- distinction between missing fact and known false relation.

## W3C SHACL

https://www.w3.org/TR/shacl/

Used for:

- validation as a separate bounded operation over data/shapes graphs;
- closed-shape and required-property constraints;
- validation reports;
- evidence that “closed” semantics belong to an explicit validation contract rather than a universal truth default.

## Wikibase/Wikidata

https://www.mediawiki.org/wiki/Wikibase/DataModel  
https://www.wikidata.org/wiki/Help:Statements/en  
https://www.wikidata.org/wiki/Help:Ranking  
https://www.wikidata.org/wiki/Help:Qualifier  
https://www.wikidata.org/wiki/Help:Sources  
https://www.wikidata.org/wiki/Help:Deprecation/en

Used for:

- concrete value vs some-value-unknown vs no-value;
- multiple/conflicting statements;
- references;
- qualifiers;
- preferred/normal/deprecated ranks;
- retaining historically wrong/superseded claims rather than deleting them;
- measurement/time precision as separate from statement rank.

## XTDB

https://docs.xtdb.com/about/time-in-xtdb.html  
https://docs.xtdb.com/concepts/key-concepts.html  
https://docs.xtdb.com/quickstart/sql-overview.html  
https://docs.xtdb.com/tutorials/immutability-walkthrough/part-4

Used for:

- valid time;
- system/transaction time;
- late/backdated/future-effective updates;
- immutable system-time audit;
- corrected historical truth versus history as known at the time.

## Microsoft SQL Server temporal guidance

https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal/overview  
https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-table-usage-scenarios

Used as independent evidence that system/transaction time may be unsuitable as business validity when data arrives late.

## KurrentDB / EventStoreDB

https://docs.kurrent.io/getting-started/introduction  
https://docs.kurrent.io/getting-started/concepts  
https://docs.kurrent.io/getting-started/features  
https://docs.kurrent.io/server/v26.0/http-api/optional-http-headers  
https://docs.kurrent.io/dev-center/use-cases/time-travel/tutorial-summary

Used for:

- append-only immutable event history;
- stream ordering/revision;
- projection reconstruction/time travel;
- optimistic concurrency / expected revision;
- comparison of event history with bitemporal truth semantics.

---

# Highest-value KA-G1 findings

## 1. Absence is not false

OWL's open-world semantics directly supports the rule that a missing fact may simply be unknown.

OWL negative property assertions show that known-negative is an explicit assertion, not inferred from lack of a positive triple.

Wikibase independently distinguishes:

- concrete value;
- some value exists but is unknown;
- no value exists;
- no statement/not established.

Architecture consequence:

> Retrieval/search failure does not create negative knowledge by itself.

## 2. Closed-world negative inference requires a completeness contract

The system may treat absence as meaningful only when the relevant population is explicitly known to be complete for the bounded scope.

The completeness contract needs enough identity to bind:

- subject/entity set;
- predicate/property;
- time/validity interval;
- environment/project/device/version scope where applicable;
- authoritative source/evidence population;
- search/filter profile.

This produces new candidate invariant **KA-I-047**.

## 3. Pairwise negative, no-value and unknown-value are distinct

Examples that must remain distinguishable:

- `Device A is not in Room B`;
- `Person A has no current employer`;
- `Person A's current employer exists but is unknown`;
- no current-employer evidence exists.

A single nullable field cannot safely encode these meanings.

## 4. Epistemic dimensions must not collapse into one status/confidence field

Standards evidence supports separating:

- proposition/value state;
- epistemic basis;
- references/provenance;
- qualifiers/applicability;
- verification/dispute state;
- current/default selection rank;
- uncertainty/precision.

`KA-I-025` and `KA-I-010` gain direct standards/domain recurrence.

## 5. Conflicting assertions can coexist

Wikibase allows multiple values and even multiple preferred statements where disagreement remains.

Default/current selection is therefore not equivalent to deleting alternatives.

Conflict detection/adjudication should be separate from ingestion.

## 6. Wrong/superseded claims can remain useful historical evidence

Wikidata deprecation guidance retains many statements that are now known wrong or superseded.

A key distinction:

- proposition `P` may be false;
- proposition `Source S claimed P` may remain true and historically important.

This sharpens provenance/current-history semantics without selecting Wikibase.

## 7. Valid time and system/record time are different

XTDB provides strong positive semantics:

- system time = when information entered/changed in the database;
- valid time = when it was true/effective in the world.

Microsoft independently warns transaction time may be wrong for delayed business data.

A single timestamp is therefore insufficient for Vera's general knowledge model.

## 8. “What was true then?” and “what did we know then?” are different queries

At minimum future retrieval requirements need:

- current state as best known now;
- historical world state as best known now after later corrections;
- historical knowledge state as it was known at the time;
- conflict/evidence history.

This materially strengthens `KA-I-008` and `KA-I-009`.

## 9. Backdating a correction must not backdate knowledge history

If an event happened at 02:10 but Vera learned it at 03:00:

- valid/event time may be 02:10;
- record/knowledge time remains 03:00.

Later correction of valid time must not rewrite the audit history of when Vera learned/applied it.

## 10. Event sourcing and bitemporality solve different problems

KurrentDB provides strong evidence for:

- append-only history;
- mutation/event ordering;
- projection rebuild;
- concurrency checks.

But an event store does not automatically provide:

- proposition truth;
- epistemic basis;
- source trust;
- conflict semantics;
- valid-time correction.

Likewise bitemporal rows do not automatically provide event intent/provenance.

Future synthesis should test whether Vera needs distinct but linked:

- evidence/observation/event history;
- temporal assertions;
- materialized current projections.

## 11. Event occurrence is not world truth

For Vera, durable evidence should often record:

`Camera-7 emitted match(Alice, .72) at T`

rather than prematurely collapsing it into:

`Alice was in the kitchen at T`.

The latter is a derived proposition requiring source/identity/trust reasoning.

This strengthens `KA-I-001` and `KA-I-025`.

## 12. Significant correction writes need revision/concurrency protection

Kurrent expected-revision semantics provide a mature analogue for preventing stale writers from appending over an unseen concurrent change.

This maps to existing concurrency requirements; no new invariant/failure ID was needed.

## 13. Correction/deprecation is not privacy erasure

Retaining old claims is desirable for ordinary correction/audit.

Privacy/legal erasure may require actual removal across canonical and derived planes.

The later privacy gap remains necessary.

---

# Cumulative ledger state after KA-G1

## Invariants

Invariant IDs now run **KA-I-001 through KA-I-047**.

New:

### KA-I-047 — candidate

A missing value or unsuccessful search may be promoted from `not-established` to `known-negative` only when an explicit, evidence-backed completeness/closed-world contract covers the relevant subject set, predicate, scope, time and source/search population; otherwise absence remains unknown/not-established.

Evidence:

- W3C OWL open-world assumption;
- W3C OWL explicit negative property assertions;
- W3C SHACL bounded validation model;
- Wikibase/Wikidata some-value/no-value semantics.

No status promotions are required because the affected existing invariants were already reinforced.

Strong new recurrence recorded for:

- KA-I-001
- KA-I-006
- KA-I-008
- KA-I-009
- KA-I-010
- KA-I-021
- KA-I-022
- KA-I-025

Candidates remaining:

- KA-I-004 — reversible identity merge/split transition
- KA-I-007 — governed relationship semantics
- KA-I-031 — exact settled knowledge revision for active context
- KA-I-037 — logical resource vs locator vs content/version digest
- KA-I-038 — canonical read isolation/value semantics
- KA-I-039 — semantic persistence round-trip fidelity
- KA-I-040 — live/replay transition equivalence
- KA-I-044 — transport liveness vs logical continuation validity
- KA-I-045 — terminal/expiry lifecycle for pending authority/effects
- KA-I-047 — closed-world negative inference requires completeness contract

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID was created.

Reason:

- this task supplied standards/domain semantic evidence rather than a new concrete implementation incident;
- “absence -> false” is nominated for later hostile/acceptance testing, but adding an observed failure ID from standards doctrine alone would weaken the failure ledger's incident/reproduction discipline.

---

# Twenty-six-question disposition after KA-G1

## Strong enough for later requirements/synthesis without another project revisit

- 1 Stable identity
- 2 Identity vs namespace/principal
- 4 Epistemic state — **positive semantics materially improved by KA-G1**
- 5 Temporal truth — **positive bitemporal semantics materially improved by KA-G1**
- 6 Conflict/supersession — **retention/deprecation/current-selection semantics materially improved by KA-G1**
- 8 Permissions/sensitivity — formal authorization gap still required
- 10 Knowledge vs authority
- 12 Canonical vs derived
- 13 Structured retrieval
- 15 Full-text retrieval
- 16 Semantic retrieval
- 17 Composite retrieval
- 18 Context construction
- 19 Memory poisoning/prompt injection
- 20 Concurrency
- 21 Derived-state integrity
- 24 Recovery semantics
- 25 Unknown/negative knowledge — **positive semantics materially improved by KA-G1**

## Still requires bounded gap research

- 3 Formal provenance
- 7 Governed relationships
- 9 Actionability/use-purpose semantics
- 11 Resources/artifacts
- 14 Relationship retrieval
- 22 Privacy deletion/retention
- 23 Ontology/schema evolution — partial evidence exists
- 26 Scope of truth — temporal/method scope improved; cross-domain applicability still partial

---

# Remaining gap map

These are candidates only; phase order is not authorization.

## Priority B — relationships and ontology evolution

Relevant questions:

- 7 Relationships
- 14 Relationship retrieval
- parts of 23 and 26

Candidate focus:

- controlled relationship vocabulary;
- relationship provenance and validity time;
- inverse/symmetric/transitive/cardinality semantics only where safe;
- relationship identity;
- ontology/vocabulary evolution and migration;
- canonical relationship assertions vs derived association graphs.

## Priority C — formal provenance

Relevant questions:

- 3 Provenance
- parts of 11/21/23

Candidate focus:

- W3C PROV and related lineage models;
- source -> evidence -> assertion -> derivation chains;
- derivation/activity identity;
- responsibility/agent attribution without turning provenance into trust.

## Priority D — knowledge authorization, purpose and sensitivity

Relevant questions:

- 8
- 9
- 10
- 22

Candidate focus:

- ABAC/ReBAC-style access;
- principal/subject/owner/purpose separation;
- read/write/delete/consolidate/use-for-automation authority classes;
- sensitivity/retention.

## Priority E — content-addressed resource/artifact identity

Relevant question:

- 11

Candidate focus:

- logical resource identity;
- locator/replica;
- content digest/version;
- extraction/derivation lineage;
- cache/index/embedding relationships.

## Priority F — privacy deletion and retention

Relevant question:

- 22

Candidate focus:

- canonical/derived/cache/backup erasure;
- audit retention vs user-data retention;
- tombstones/fencing;
- delayed cleanup;
- erasure verification.

## Priority G — non-AI operational-domain validation

Relevant question:

- 26 and generality of the eventual model

Candidate focus:

- Home Assistant / Matter-style devices;
- entities and replacement hardware;
- rooms/locations;
- sensor observations;
- stale/unavailable state;
- capabilities;
- shared-household authority.

This remains necessary to prevent coding-agent vocabulary from becoming Vera's general schema.

---

# Current task

**No task is currently assigned.**

KA-G1 is complete.

## Planned next candidate

**KA-G2 — Relationships and Ontology Evolution**

This is only the next candidate from the gap map. It is **not authorized merely because it is next**.

A future bounded KA-G2 should research current primary standards/domain evidence around:

- relationship identity;
- typed/governed predicates;
- inverse/symmetric/transitive semantics and their hazards;
- cardinality/functional relationships;
- relationship qualifiers/provenance/time;
- ontology/vocabulary versioning and migration;
- canonical relationship truth versus derived association graphs.

It must stop before formal provenance (Priority C).

---

# Prohibited work at this state

Do not:

- begin KA-G2 or another gap task without explicit authorization;
- restart broad agent-framework research;
- build the representative retrieval-question set;
- execute the hostile/adversarial review;
- synthesize the final conceptual schema;
- select a database, graph engine, vector store or event store;
- implement retrieval/context construction;
- create embeddings;
- migrate historical catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers;
- convert candidate/reinforced invariants into final architecture rules.

---

# Stop point

The campaign now has strong direct evidence for the major epistemic/temporal semantics that agent frameworks left underspecified:

- missing != false;
- explicit negative/no-value != unknown;
- unknown != not-established;
- conflicting assertions can coexist;
- source claim != proposition truth;
- current selection != deletion of history;
- valid/world time != system/record time;
- corrected history != history as believed at the time;
- event history != epistemic truth;
- correction != privacy erasure.

New candidate invariant **KA-I-047** captures the critical rule that negative knowledge derived from absence requires an explicit completeness/closed-world contract.

No relationship/ontology research, formal provenance research, authorization/privacy research, resource-identity research, retrieval study, hostile review, synthesis, storage selection or implementation has begun.