# Conceptual Knowledge Architecture Synthesis

**Campaign:** Knowledge Architecture Evidence Campaign  
**Phase:** Conceptual Architecture Synthesis  
**Status:** technology-neutral conceptual model; no physical storage or implementation selection

---

# Purpose

This document synthesizes the completed project evidence, seven standards/domain gap studies, 52 representative retrieval requirements, and 44 hostile/adversarial scenarios into the smallest technology-neutral conceptual architecture that can support ACL and Vera without making either domain the shape of the system.

This is the first phase in which candidate distinctions are deliberately assembled into a coherent model. It is still not a physical schema, database design, API, ontology implementation, graph-store decision, vector-store decision, or execution architecture.

The model must survive the later hand-authored cross-domain prototype before storage technology is selected.

---

# Governing separation

The architecture is organized around three cooperating but non-equivalent systems:

```text
KNOWLEDGE
  what is known, claimed, observed, inferred, remembered or evidenced
        |
        v
REASONING / CONTEXT CONSTRUCTION
        |
        v
AUTHORITY
  whether a principal may read, disclose, mutate, decide or act for a purpose
        |
        v
EXECUTION / EFFECTS
  requested, attempted, accepted, completed, failed, cancelled or reconciled external effects
        |
        v
EXTERNAL WORLD
        |
        v
OBSERVATION / EVIDENCE
        |
        +----> KNOWLEDGE
```

**Knowledge does not grant authority. Authority does not prove execution. Execution acknowledgement does not prove world settlement.**

---

# Minimal canonical knowledge primitives

The synthesis selects six conceptual primitive families.

These are semantic roles, not database tables.

## 1. ENTITY

A persistent semantic thing that can be referred to across time and sources.

Examples:

- a person;
- a physical thermostat;
- a room;
- a project;
- a repository;
- an organization;
- a software package;
- a vehicle;
- an account;
- a conceptual topic.

ENTITY carries stable internal semantic identity. External IDs, names, email addresses, usernames, IP addresses, device registry IDs, Matter node IDs and similar identifiers are identity evidence or source identities, not automatically the entity's universal identity.

Identity ambiguity is representable. Merge, split, replacement and reassignment are explicit transitions with provenance and history; they are never silent destructive rewrites.

## 2. ASSERTION

A provenance-bearing proposition asserted about one or more subjects.

ASSERTION is the common semantic carrier for:

- factual claims;
- preferences;
- configuration claims;
- state claims;
- typed relationships;
- negative assertions;
- inferred conclusions;
- derived findings;
- applicability claims.

Examples:

- `Floyd prefers 32K benchmark context.`
- `Thermostat-17 is located_in Kitchen.`
- `Robert works_for Acme.`
- `Commit abc123 fixes issue 44.`
- `Spare key exists, exact location unknown.`
- `Source X claims package version 3.0.7 is current.`

An assertion occurrence is distinct from the abstract proposition. Two sources may independently assert the same proposition and retain different provenance, validity, confidence, epistemic basis and lifecycle.

### Assertion semantic dimensions

An ASSERTION can carry or reference:

- proposition/type/predicate;
- subject(s) and object/value;
- assertion occurrence identity;
- epistemic basis: stated, observed, imported, configured, inferred, derived, verified, etc.;
- polarity/value state: positive value, explicit negative, known no-value, some-value-unknown, not-established;
- valid/world time;
- record/transaction time;
- applicability scope;
- provenance/evidence links;
- verification/conflict/currentness state;
- supersedes / superseded-by / contradicts relations;
- sensitivity/ownership classification used by external policy;
- vocabulary/profile revision under which the assertion is interpreted.

Confidence or ranking is never a substitute for epistemic basis or truth.

## 3. OCCURRENCE

A bounded event, observation, activity, operation or other happening with occurrence identity and time.

Examples:

- a sensor emitted a reading;
- a user stated a preference;
- a research task ran;
- a model generated a finding;
- a merge decision occurred;
- an ingestion job transformed a PDF;
- a tool call was attempted;
- a deletion reconciliation pass executed.

OCCURRENCE provides the event/activity anchor needed for provenance, concurrency, replay and temporal reasoning.

External effect lifecycle records may reference OCCURRENCE identity, but authoritative execution/effect settlement remains in the separate effect system rather than being reduced to knowledge assertions.

## 4. RESOURCE

An addressable information or artifact object whose logical identity is distinct from its locator and exact observed representation/version.

Examples:

- document;
- file;
- repository;
- commit artifact;
- web resource;
- image;
- PDF;
- email attachment;
- model artifact;
- configuration artifact;
- dataset.

RESOURCE semantics separate:

```text
logical resource
    != mutable locator / alias / path
    != observed representation
    != immutable content/version identity
```

Derived artifacts such as extraction, normalized text, chunk, summary, embedding or index entry have their own identities and lineage to the exact source version consumed.

## 5. EVIDENCE / PROVENANCE LINK

A typed lineage/attribution relationship connecting entities, assertions, resources and occurrences.

Examples:

- assertion `wasAttributedTo` a speaker/source;
- assertion `wasDerivedFrom` a document version;
- occurrence `used` resource version V2;
- derived resource `wasGeneratedBy` extraction occurrence;
- assertion was supported by observations O1 and O2;
- entity-resolution decision used identifiers A and B.

This primitive family may be physically implemented as typed edges/records, but conceptually it is first-class because the system must answer both backward explanation and forward impact questions.

Provenance is not truth, confidence, permission or execution authority.

## 6. SEMANTIC PROFILE / VOCABULARY DEFINITION

Versioned definitions governing the meaning of assertion predicates, entity/resource kinds, relationship semantics, inference rules, applicability vocabulary and domain extensions.

Examples:

- meaning of `located_in`;
- whether a relation has inverse/symmetric/transitive semantics;
- ACL project vocabulary;
- Vera household/device vocabulary;
- research-evidence vocabulary;
- software-version profile;
- domain-specific capability profile.

Changing the meaning of an identifier requires explicit versioning/migration/re-derivation rather than retroactively reinterpreting historical data.

The universal core must allow domain profiles without embedding Home Assistant, Matter, GitHub, mining, coding-agent or household schemas directly into the universal primitives.

---

# Relationships

A relationship is represented as a governed ASSERTION whose predicate is defined by a SEMANTIC PROFILE.

This preserves two separate identities:

1. **relationship semantic identity** — what `works_for`, `located_in`, `owns`, `depends_on`, etc. mean;
2. **relationship assertion occurrence identity** — a particular source's assertion that `A works_for B`.

Direct asserted relationships, inferred relationships and graph connectivity are separate retrieval products.

Derived paths must preserve enough explanation to expose the direct assertions and profile/inference rules that produced them when consequential.

---

# Observation and state model

An observation is modeled as an OCCURRENCE plus one or more ASSERTIONs grounded in that occurrence.

Example:

```text
Occurrence O17
  kind: sensor_observation
  observed_at: 06:31
  source: tracker-9

Assertion A91
  subject: keys
  predicate: located_in
  object: vehicle
  epistemic_basis: observed
  evidence: O17
  valid_time: 06:31...
```

A derived current state is a projection over retained assertions/observations under freshness, conflict, applicability and selection rules.

Therefore:

```text
entity != observation != current-state projection
```

`unknown`, `unavailable`, `stale`, `known false`, `known no-value` and `not established` remain distinct.

Last-known state cannot silently masquerade as current truth.

---

# Temporal model

The architecture requires at least two independent temporal axes conceptually:

1. **world/valid time** — when the assertion/event is believed to apply in the world;
2. **record/transaction time** — when the system recorded, learned or revised that knowledge.

This supports both:

- “What is our best current reconstruction of what was true at 06:30?”
- “What did Vera believe at 06:30?”

Corrections may alter the current reconstruction of historical world truth without rewriting the historical record of what the system knew earlier.

Occurrence time, observation time, source publication time and validity interval may also be retained where semantically relevant; they must not be collapsed merely because a storage system offers one timestamp field.

---

# Epistemic model

The substrate does not use a single Boolean `is_true`.

Minimum semantic distinctions include:

- explicit assertion/claim;
- direct observation;
- imported/configured information;
- inference/derivation;
- verified/validated state;
- disputed/conflicting state;
- positive value;
- explicit negative;
- some value exists but exact value unknown;
- known no-value;
- not established/unknown;
- historically true but no longer current.

A missing record or unsuccessful search becomes `known-negative` only when an explicit completeness/closed-world contract covers the relevant subject set, predicate, scope, time and searched evidence population.

Otherwise absence remains not-established.

---

# Conflict and supersession

The canonical layer retains competing assertion occurrences when they are materially sourced.

“Current truth” is a selection/projection over assertions rather than destructive replacement of all alternatives.

Supersession, invalidation, correction and deprecation are explicit provenance-bearing transitions.

A statement such as “Source X claimed P” can remain historically true even after P itself is judged false.

Context construction must preserve material disagreement rather than letting ranking or summarization silently erase the conflict.

---

# Identity model

ENTITY identity is stable and internal.

External identities are separately typed evidence:

- account/user IDs;
- employee IDs;
- device registry IDs;
- Matter IDs;
- email addresses;
- usernames;
- Git commit/package identifiers;
- source-specific record IDs.

Names, labels, URLs, paths, IPs and room assignments are not intrinsic entity identity.

Identity resolution supports:

- resolved same-entity;
- resolved different-entity;
- candidate match;
- ambiguous/unresolved;
- merge transition;
- split transition;
- replacement/reassignment transition.

Identity transitions preserve history and provenance.

---

# Resource/artifact model

RESOURCE keeps separately representable:

- logical resource identity;
- source/provider/origin;
- current/historical locator(s);
- exact observed version/content identity;
- media/type/profile metadata;
- ownership/sensitivity classifications;
- derivation lineage;
- extracted/derived representations.

Consequential derivations bind to the exact version consumed, not merely a mutable locator such as `main`, `latest`, filename or URL.

Content digest equality proves only the equality supported by that digest/profile; it does not automatically prove same logical resource, provenance, owner, authorization domain or historical object.

---

# Canonical versus derived planes

## Canonical or canonical-adjacent knowledge

The following must remain source-addressable and semantically durable:

- entity identities and identity transitions;
- assertion occurrences and their semantic metadata;
- occurrence/activity records needed for interpretation and provenance;
- logical resources and exact observed versions;
- provenance/evidence links;
- semantic profile/vocabulary revisions;
- deletion/restriction control state required to prevent resurrection.

## Derived/rebuildable projections

The following are normally derived and should carry source revision/generation/profile identity:

- current-state views;
- entity summary pages;
- graph traversal indexes;
- full-text indexes;
- vector embeddings;
- semantic-search indexes;
- reranking features;
- cached relationship closures;
- aggregate summaries;
- context packages;
- dashboards;
- denormalized lookup tables.

Derived data must never silently become stronger truth than its canonical/evidence basis.

---

# Retrieval architecture requirements

Retrieval remains conceptually composite:

```text
1. hard principal/purpose/sensitivity eligibility gates
2. structured deterministic retrieval
3. temporal/applicability filtering
4. relationship/direct-path retrieval
5. full-text candidate discovery
6. semantic candidate discovery
7. provenance/conflict/currentness evaluation
8. reranking
9. context construction
```

The exact order can vary by query class, but hard eligibility is not deferred until after protected content has already been exposed to an unauthorized model/caller.

Semantic similarity introduces candidates; it does not establish truth, identity, authority or currentness.

Context construction is distinct from retrieval. It must consider trust, freshness, revision, conflict, provenance, purpose, sensitivity, actionability and token budget.

---

# Authority interface

The knowledge substrate may expose policy-relevant attributes and relationships, but it does not itself turn them into permission.

An authority request is conceptually scoped to:

```text
authenticated principal
+ target/resource
+ action class
+ purpose/use
+ relevant trusted attributes/authorization relations
+ policy/model revision
+ freshness/expiry context
```

Read, disclose, summarize, export, use-for-reasoning, use-for-automation, append, revise, supersede, consolidate, delete/forget and sensitivity/ownership changes are not automatically the same permission.

A prior authorization decision or approval is not timeless knowledge. Consequential reuse must remain bound to the operation semantics and authority context/version under which it was granted.

Authorization relationships are not automatically canonical world relationships.

---

# Execution/effect interface

Knowledge can inform a proposed action but never proves its settlement.

Conceptually:

```text
knowledge/context
 -> reasoning proposal
 -> policy/authorization decision
 -> operation occurrence
 -> external effect attempt
 -> acknowledgement/result
 -> verification/reconciliation
 -> observation/evidence
 -> knowledge
```

The effect system must separately track requested/attempted/accepted/completed/failed/cancelled/unknown/reconciled states as appropriate.

Dynamic target groups/areas must resolve to a concrete target set bound to the operation when consequential.

Retry/replay requires stable operation occurrence identity and generation fencing so an ambiguous acknowledgement cannot silently become duplicate physical action.

The knowledge layer records observations and conclusions about effects; it does not substitute for the effect ledger.

---

# Deletion, retention and restriction interface

Deletion/forget is a lifecycle spanning multiple planes, not a row-delete Boolean.

Conceptual state may distinguish:

- active;
- restricted/beyond ordinary use;
- soft-deleted/recoverable;
- erasure requested;
- reconciliation pending;
- erased from active canonical plane;
- derived cleanup pending/settled;
- backup-retained but fenced;
- recipient/external reconciliation pending/unknown;
- fully settled within the stated scope;
- exempt/retained for bounded purpose;
- unresolved scope.

Deletion propagation uses lineage to invalidate/remove/rebuild descendants.

Restore must reapply deletion/restriction state newer than the restored snapshot before restored data becomes active.

Audit/control metadata should prove settlement without preserving the erased sensitive payload wholesale.

---

# Domain profiles

The universal model intentionally does not contain domain-specific primitives such as:

- Home Assistant entity;
- Matter endpoint;
- Git branch;
- GitHub issue;
- ACL worker;
- mine portal;
- vehicle remote-start command;
- email thread.

These are represented through domain profiles mapping external/source concepts into the six universal primitive families.

Examples:

```text
Matter endpoint
 -> ENTITY or scoped capability entity under a Matter profile

Git commit
 -> RESOURCE/version + OCCURRENCE/provenance as needed

Home Assistant state event
 -> OCCURRENCE + ASSERTION

Mine portal assignment
 -> relationship ASSERTION with valid time

ACL research finding
 -> ASSERTION derived from RESOURCE/EVIDENCE through OCCURRENCE
```

Domain-profile versions are behavior-bearing. Historical records retain the profile revision under which they were interpreted.

---

# Nine hostile-review seams mapped into the model

## Seam 1 — Identity transition semantics

Handled by ENTITY identity plus explicit merge/split/replacement/reassignment transition OCCURRENCEs and provenance.

## Seam 2 — World-time vs knowledge-time

Handled by distinct valid/world time and record/transaction time on assertion/occurrence interpretation.

## Seam 3 — Negative-knowledge completeness

Handled by epistemic value state plus explicit completeness-contract evidence/applicability.

## Seam 4 — Retrieved content vs policy instruction

Handled by provenance/content typing and the external Authority boundary. Imperative text remains content unless an independently trusted policy/control source establishes authority semantics.

## Seam 5 — Authorization obligations/freshness

Handled outside canonical truth by an authority decision context containing purpose, policy/model revision, freshness/expiry and obligations.

## Seam 6 — Target-set binding and effect settlement

Handled by operation occurrence identity plus external Effect Ledger target-set/effect state, later observed back into knowledge.

## Seam 7 — Conflict-preserving context

Handled by retaining competing assertion occurrences and requiring context construction to expose material conflicts.

## Seam 8 — Derivative sensitivity/erasure propagation

Handled by first-class lineage plus derived-generation identity and deletion/restriction reconciliation.

## Seam 9 — Domain profile semantics

Handled by versioned SEMANTIC PROFILE definitions outside the universal primitive taxonomy.

---

# Mapping to representative retrieval requirements

The 52 retrieval requirements map without adding another universal primitive family:

- RR-01..04 -> ENTITY + identity evidence/transitions
- RR-05..09 -> ASSERTION + OCCURRENCE + temporal axes
- RR-10..15 -> ASSERTION epistemic/polarity state + completeness/conflict metadata
- RR-16..20 -> EVIDENCE/PROVENANCE + RESOURCE + OCCURRENCE
- RR-21..25 -> relationship ASSERTION + SEMANTIC PROFILE + provenance
- RR-26..30 -> RESOURCE + exact version/locator/derivation distinctions
- RR-31..35 -> cross-domain ENTITY/ASSERTION/RESOURCE/OCCURRENCE composition
- RR-36..41 -> Knowledge-to-Authority interface and eligibility/context gates
- RR-42..45 -> OCCURRENCE + Effect Ledger interface + subsequent observations
- RR-46..50 -> deletion/restriction reconciliation + provenance/lineage
- RR-51..52 -> composite retrieval + conflict-aware context construction

This mapping is a synthesis hypothesis to be tested in the hand-authored prototype.

---

# What is deliberately not a universal primitive

The synthesis rejects making the following first-class universal core types unless the prototype proves otherwise:

- `Fact` as separate from ASSERTION;
- `Preference` as separate from ASSERTION;
- `State` as separate from ASSERTION/current projection;
- `Relationship` as a separate storage universe from governed ASSERTION;
- `Observation` as separate from OCCURRENCE + grounded ASSERTION;
- `Memory` as a canonical primitive;
- `Chunk` as canonical truth;
- `Embedding` as canonical truth;
- `Summary` as canonical truth;
- `Permission` as knowledge truth;
- `ToolCall` as knowledge truth;
- `ActionSuccess` as knowledge truth;
- `HomeAssistantEntity`, `MatterEndpoint`, `GitCommit`, `Email`, etc. as universal primitives.

These remain domain kinds, projections, or external-system records mapped onto the universal concepts.

---

# Candidate architecture acceptance rules

The hand-authored prototype must falsify this synthesis if any of the following cannot be represented without semantic loss:

1. same-name people without forced merge;
2. reversible/auditable identity transition;
3. world truth at T versus belief at T;
4. late correction without history rewrite;
5. explicit conflict with separate source provenance;
6. unknown versus known-negative under bounded completeness;
7. direct observation versus inferred current state;
8. direct relationship versus inferred path;
9. relationship assertion occurrence versus relationship semantic identity;
10. exact consumed artifact version despite mutable locator;
11. forward and backward provenance traversal;
12. derived index/summary generation staleness;
13. protected retrieval filtered before unauthorized model exposure;
14. read versus disclose versus automate versus mutate authority;
15. stale approval invalidation;
16. dynamic target-set binding;
17. command acknowledgement versus world settlement;
18. duplicate/retry ambiguity;
19. deletion propagation into derivatives;
20. backup restore without forgotten-data resurrection;
21. domain-profile evolution without reinterpretation of history;
22. cross-domain representation spanning people, research, software, projects and devices with the same universal primitives.

Failure of any of these during the prototype requires revisiting the synthesis before physical storage selection.

---

# Physical-design constraints carried forward

A later storage design must be evaluated against this model rather than driving it.

At minimum it must support or emulate safely:

- stable identifiers;
- typed records/links;
- temporal validity/history;
- immutable or auditable provenance-bearing transitions;
- conflict-preserving assertions;
- efficient structured lookup;
- relationship traversal;
- full-text retrieval;
- semantic/vector retrieval as a derived capability;
- revision/version binding;
- policy-relevant metadata preservation;
- multi-plane deletion reconciliation;
- concurrency controls;
- rebuildable derived projections;
- forward/backward lineage;
- domain-profile/version evolution.

No database or implementation technology is selected here.

---

# Synthesis conclusion

The evidence supports a compact universal knowledge model centered on:

```text
ENTITY
ASSERTION
OCCURRENCE
RESOURCE
EVIDENCE / PROVENANCE LINK
SEMANTIC PROFILE / VOCABULARY
```

with explicit interfaces to:

```text
AUTHORITY / POLICY
EFFECT / EXECUTION LEDGER
DERIVED RETRIEVAL PROJECTIONS
CONTEXT CONSTRUCTION
```

This is intentionally a **knowledge substrate**, not an agent-memory feature and not a smart-home/coding schema.

The final pre-storage gate is the small hand-authored cross-domain prototype. That prototype must exercise the 22 acceptance rules above, representative retrieval requirements, and hostile seams using concrete example records before any physical storage system is selected.