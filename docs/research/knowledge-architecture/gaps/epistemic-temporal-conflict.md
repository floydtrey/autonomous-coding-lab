# Gap A — Epistemic, Temporal, Conflict and Negative-Knowledge Semantics

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** KA-G1 — Priority A standards/domain gap research  
**Research date:** 2026-09-08  
**Starting ACL checkpoint:** `efda61ba0fd1146d0da98b85e218f475cad4a42d`  
**Boundary:** research only; no final schema, database, graph engine, event store, ontology language, RDF stack, XTDB/Kurrent/Wikibase adoption, retrieval implementation, model assignment, or ACL/Vera implementation decision

## Purpose

The agent-framework revisits repeatedly showed what is missing from typical agent memory systems:

- explicit epistemic state;
- a principled distinction between unknown and false;
- world-valid time distinct from record/transaction time;
- correction and supersession without destroying history;
- multiple conflicting claims with source/context preserved;
- query semantics for current truth versus historical belief;
- structured applicability rather than arbitrary prose.

This bounded task asks only:

> What do current standards and mature domain models tell us about representing uncertainty, negative knowledge, temporal truth, conflict, correction and historical belief for a general ACL/Vera knowledge substrate?

Relevant campaign questions:

- Q4 Epistemic state
- Q5 Temporal truth
- Q6 Conflict and supersession
- Q25 Unknown/negative knowledge
- Q26 Scope of truth

Identity/entity-resolution techniques are deliberately excluded from this task even though they appeared in the Priority A candidate list. Relationship vocabulary/ontology evolution is the next separate candidate gap and is not researched here.

---

# Executive assessment

The strongest result is that ACL/Vera should not represent “truth status” with one scalar confidence field or one mutable current-value slot.

The evidence supports a multi-dimensional assertion model in which at least the following concerns remain distinct:

1. **Proposition/value state** — concrete value, explicit negative assertion, explicitly no value, some value exists but is unknown, or no assertion established.
2. **Epistemic basis** — observation, direct user statement, third-party claim, imported configuration, inference, derived summary, etc.
3. **Verification/dispute status** — unverified, corroborated, verified, disputed, contradicted, deprecated/known erroneous, etc.
4. **Provenance/reference** — which source/evidence supports the claim.
5. **Applicability/qualifiers** — time, method, environment, version, location, role or other context in which the claim applies.
6. **World-valid time** — when the proposition was true/effective in the domain.
7. **System/record time** — when Vera/ACL recorded or changed its belief about that proposition.
8. **Selection/rank** — which retained assertions a particular projection should prefer by default.
9. **Uncertainty** — measurement precision/probability/confidence where appropriate, without conflating it with rank or provenance.

No single inspected standard provides all of these dimensions.

The standards/domain evidence is most useful when combined:

- OWL demonstrates open-world semantics and explicit negative property assertions.
- Wikibase/Wikidata demonstrates explicit unknown/no-value states, retained conflicting statements, references, qualifiers and coarse ranks/deprecation.
- SHACL demonstrates that validation/closed constraints are a separate operation over an explicitly supplied graph rather than a universal truth inference rule.
- XTDB demonstrates valid-time plus system-time and directly exposes the query distinction between corrected historical truth and “what we believed then.”
- SQL Server system-versioned temporal guidance independently demonstrates why transaction time can be insufficient when data arrives late.
- KurrentDB/EventStore-style event sourcing demonstrates immutable ordered mutation/event history, projection rebuild and optimistic concurrency, but does not itself supply epistemic truth or valid-time semantics.

The central architectural conclusion is:

> **Absence, assertion polarity, source claim, current selection, world validity and record history are different semantics. Vera must preserve them separately rather than compressing them into “memory text + timestamp + confidence.”**

---

# Primary sources inspected

## W3C OWL 2 Primer (Second Edition)

Stable W3C recommendation material:

- https://www.w3.org/TR/owl-primer/

Relevant mechanisms:

- open-world assumption;
- no unique-name assumption;
- explicit negative object/data property assertions.

## W3C SHACL Recommendation

- https://www.w3.org/TR/shacl/

Relevant mechanisms:

- validation as a separate process over a data graph and shapes graph;
- `sh:closed` constraints;
- required/min/max constraints;
- validation reports;
- immutable validation inputs.

## Wikibase conceptual data model

Living current documentation inspected 2026-09-08:

- https://www.mediawiki.org/wiki/Wikibase/DataModel

Relevant mechanisms:

- Statements as claims plus references;
- `PropertyValueSnak`;
- `PropertySomeValueSnak` (“some value exists, but unknown”);
- `PropertyNoValueSnak` (“no value exists”);
- multiple possibly conflicting statements;
- preferred/normal/deprecated ranks;
- quantity uncertainty intervals;
- time precision.

## Wikidata help guidance

- https://www.wikidata.org/wiki/Help:Statements/en
- https://www.wikidata.org/wiki/Help:Ranking
- https://www.wikidata.org/wiki/Help:Qualifier
- https://www.wikidata.org/wiki/Help:Sources
- https://www.wikidata.org/wiki/Help:Deprecation/en

Relevant mechanisms:

- references/sources;
- qualifiers including point-in-time, start/end time and method/context;
- retained historical/wrong statements;
- multiple preferred values where disagreement remains;
- unknown and no-value statements.

## XTDB current temporal documentation

Current documentation inspected 2026-09-08:

- https://docs.xtdb.com/about/time-in-xtdb.html
- https://docs.xtdb.com/concepts/key-concepts.html
- https://docs.xtdb.com/quickstart/sql-overview.html
- https://docs.xtdb.com/tutorials/immutability-walkthrough/part-4

Relevant mechanisms:

- system time;
- valid time;
- bitemporal history;
- out-of-order/backdated/future-effective updates;
- “as best known now” versus “as known at the time” historical queries;
- immutable system-time history with mutable/correctable valid-time interpretation.

## Microsoft SQL Server system-versioned temporal documentation

Current documentation inspected 2026-09-08:

- https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal/overview
- https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-table-usage-scenarios

Relevant evidence:

- system-versioned tables preserve row versions using transaction/system time;
- Microsoft explicitly warns transaction time may be unsuitable for business validity when data is loaded with significant delay.

## KurrentDB / EventStoreDB current documentation

Current documentation inspected 2026-09-08:

- https://docs.kurrent.io/getting-started/introduction
- https://docs.kurrent.io/getting-started/concepts
- https://docs.kurrent.io/getting-started/features
- https://docs.kurrent.io/server/v26.0/http-api/optional-http-headers
- https://docs.kurrent.io/dev-center/use-cases/time-travel/tutorial-summary

Relevant mechanisms:

- immutable append-only event log;
- streams and per-stream ordering/revision;
- projections and time-travel reconstruction;
- expected revision / optimistic concurrency;
- event IDs / idempotency mechanisms in client APIs.

---

# Finding 1 — Missing information is not automatically false

## Observed upstream behavior

OWL explicitly uses an **open-world assumption**: a fact missing from an OWL document may simply be unknown rather than false.

OWL also provides **negative property assertions** when a relationship is explicitly known not to hold. That is a different semantic object from simply lacking a positive assertion.

Wikibase independently distinguishes:

- a concrete property value;
- `PropertySomeValueSnak`: some value exists, but the value is unknown;
- `PropertyNoValueSnak`: the property is known to have no value;
- no statement at all.

Wikidata help examples make the distinction concrete:

- unknown date of birth/death can be represented positively as “some value exists but is unknown”;
- a person known to have no children can be represented as “no value”; this differs from merely having no child statement.

## Architectural lesson

ACL/Vera needs at least the following distinguishable outcomes for a proposition/property:

- known positive/value;
- known negative / explicit negation;
- known no-value / known absence where the predicate semantics warrant it;
- value exists but is unknown;
- not established / no evidence yet;
- conflicting evidence.

An unsuccessful retrieval/search is not sufficient to promote `not-established` to `known-false`.

## Requirement refinement

A missing value or negative search result may be converted into known-negative only when there is an explicit **completeness/closed-world contract** for the relevant scope.

That contract must identify enough context to make the absence meaningful, such as:

- subject/entity set;
- property/predicate;
- time or validity interval;
- source or evidence population;
- environment/project/device/version scope;
- completeness statement or authoritative enumerator;
- search/filter profile.

Example:

- “Vera has no record of a spare key” → not established.
- “The authoritative key inventory for House A was fully enumerated at 09:00 and contains no spare key” → scoped known-negative may be justified.

## Confidence

High.

## Non-conclusion

This does not require OWL/RDF or Wikibase. The lesson is semantic, not a technology choice.

---

# Finding 2 — Explicit negative relations and predicate-level “no value” are different shapes

## Observed upstream behavior

OWL negative property assertions can say a specific pairwise relationship is false, e.g. A does not have relationship R to B.

Wikibase `PropertyNoValueSnak` says an entity has no value for a property at all.

These are not identical semantics.

## Architectural lesson

Vera should eventually be able to distinguish, for example:

- `Vehicle A is NOT located_at Garage` — pairwise negative relation;
- `Person A has NO current_employer` — predicate-level no value;
- `Person A current_employer is UNKNOWN` — value exists/expected but unknown;
- no `current_employer` evidence — not established.

Trying to encode all four as `value = null` destroys useful meaning.

## Confidence

High.

## Non-conclusion

This task does not define final assertion classes or null/value encoding.

---

# Finding 3 — Open-world inference and closed validation are separate concerns

## Observed upstream behavior

OWL provides open-world semantic inference.

SHACL defines a separate validation process over:

- an explicitly supplied data graph;
- an explicitly supplied shapes graph;
- constraint evaluation producing a validation report.

SHACL supports closed shapes and required/count constraints, but these validate a graph against declared conditions. They do not globally convert the Semantic Web into a closed-world truth system.

The SHACL specification also requires the data and shapes graphs used for validation to remain unchanged during validation.

## Architectural lesson

Vera should separate:

- **what the knowledge substrate means**;
- **what completeness/shape contract a bounded dataset is expected to satisfy**;
- **what a particular validation run established**.

A closed-world assertion should therefore be explicit and scoped, not an implicit global default.

A validator may establish something like:

> “For authoritative inventory snapshot X, every device must have exactly one serial number and all inventory rows are included.”

Only within that bounded contract can absence carry stronger negative meaning.

## Confidence

High.

## Non-conclusion

SHACL itself is not selected as Vera's validator or schema language.

---

# Finding 4 — A statement is not just a property-value pair

## Observed upstream behavior

Wikibase conceptualizes a Statement as a **claim plus zero or more references**.

Wikidata then adds independently useful dimensions:

- main value;
- qualifiers;
- references;
- rank.

Qualifiers can express:

- point-in-time;
- start/end time;
- method of determination;
- role/context;
- percentage or other statement-specific detail.

References identify the source supporting the claim.

Ranks select preferred/normal/deprecated statements for default treatment.

## Architectural lesson

A Vera assertion should not collapse these into one metadata blob or one confidence number.

At minimum, future synthesis should test whether the representation keeps distinct:

- proposition content;
- applicability qualifiers;
- provenance/evidence;
- epistemic basis;
- verification/dispute status;
- selection/currentness;
- uncertainty.

## Confidence

High.

## Non-conclusion

Wikidata's specific three-rank system is not sufficient as Vera's epistemic model and is not being adopted.

---

# Finding 5 — Rank/current selection is not truth or confidence

## Observed upstream behavior

Wikibase ranks are intentionally coarse:

- preferred;
- normal;
- deprecated.

Current Wikibase documentation says multiple preferred statements may exist, including when different sources disagree.

Deprecated statements may represent information known to be wrong or unreliable while still preserving the historically meaningful fact that a source made that claim.

## Architectural lesson

The “best/current” projection can legitimately contain:

- one preferred assertion;
- several compatible preferred assertions;
- several conflicting but still live assertions;
- no selected assertion because evidence is insufficient.

Therefore:

- rank is not confidence;
- rank is not source trust;
- rank is not verification state;
- rank is not authorization;
- “preferred” does not imply unique truth.

This independently strengthens `KA-I-010` and `KA-I-009`.

## Confidence

High.

## Non-conclusion

This task does not define the algorithm by which Vera selects a current/default assertion.

---

# Finding 6 — False proposition versus true attribution-of-claim must remain distinguishable

## Observed upstream behavior

Wikibase documentation gives a subtle but important example for deprecated statements: a historic source can have published an erroneous value. The proposition may be false, but the statement documenting **that the historical source asserted the value** remains meaningful and can be retained with its reference.

## Architectural lesson

ACL/Vera needs to distinguish:

- `P is true`;
- `Source S claims P`;
- `Vera inferred P from E`;
- `P was formerly believed true`;
- `P is now considered false`;
- `Source S's claim P remains historically documented`.

This prevents correction from destroying evidence.

Example:

- old OCR research report: “Model X supports feature Y”;
- later current source proves feature Y was removed;
- the historical research finding remains true **as a record of what was observed/reported then**, while the current product assertion is false/outdated.

## Confidence

High.

## Non-conclusion

This task does not define final claim/evidence nesting or provenance schema; formal provenance is a later gap.

---

# Finding 7 — Conflict can be represented without immediate forced resolution

## Observed upstream behavior

Wikibase permits multiple statements for one property, including conflicting values from different sources.

Qualifiers and references preserve context.

Ranks can influence default display/retrieval without deleting alternatives.

## Architectural lesson

Conflicting assertions should be able to coexist as first-class knowledge.

Conflict resolution should be a separate process from evidence ingestion.

A useful conceptual sequence is:

`Evidence/claim ingestion -> retained assertions -> conflict detection -> optional adjudication/selection -> current projection`

not:

`new value -> overwrite old value`.

## Confidence

High.

## Non-conclusion

Wikibase ranks do not supply the trust, verification or automated-action policy Vera will need.

---

# Finding 8 — Deprecation/supersession should normally preserve history

## Observed upstream behavior

Wikidata guidance explicitly recommends deprecating rather than removing many statements that are superseded or now known wrong but historically informative.

Agno/Graphiti/Letta already supplied project evidence for non-destructive retirement; the standards/domain evidence now provides a mature public-data analogue.

## Architectural lesson

A correction should generally change current eligibility/selection without erasing:

- the previous assertion;
- when it was recorded;
- its source/evidence;
- why/when it was retired;
- the replacement/correction linkage where known.

Deletion remains a separate operation for privacy, legal, security or invalid-ingestion reasons.

## Confidence

High.

## Non-conclusion

“Never delete anything” is not supported. Privacy erasure is a later separate gap.

---

# Finding 9 — World-valid time and record/system time answer different questions

## Observed upstream behavior

XTDB maintains two temporal dimensions:

- **system time**: when a version entered/changed in the database;
- **valid time**: when the row/fact is considered true/effective in the application/domain.

XTDB documentation explicitly motivates valid time for:

- late-arriving data;
- retrospective corrections;
- future-effective changes.

Current SQL Server documentation independently warns that system/transaction time may not match business validity when data is loaded late.

## Architectural lesson

Vera needs to preserve at least:

- observation/event time where applicable;
- world-valid-from / valid-to;
- record/knowledge time — when Vera recorded/accepted the assertion;
- possibly source publication/retrieval time as provenance, which is separate again.

A single `timestamp` field is insufficient.

## Example

02:10 — equipment actually fails.  
02:12 — local sensor goes offline before reporting it.  
03:00 — maintenance system syncs and Vera learns the failure occurred at 02:10.

Correct representation must support:

- valid/event time ≈ 02:10;
- Vera record/knowledge time ≈ 03:00.

## Confidence

High.

## Non-conclusion

This does not require XTDB or SQL:2011 temporal tables as the physical store.

---

# Finding 10 — Historical query intent has at least two distinct meanings

## Observed upstream behavior

XTDB documentation explicitly distinguishes:

1. “What was the state at time T, **as best known now**, including later corrections?”
2. “What did the system believe/record at time T, **without later corrections**?”

The first is largely a valid-time question under current system knowledge.

The second uses historical system time to reconstruct the knowledge state as it existed then.

## Architectural lesson

The phrase “what did we know last Tuesday?” is not equivalent to “what was actually true last Tuesday?”

Vera retrieval requirements must eventually contain both.

Examples:

- “Where did we believe the keys were at 09:00 yesterday?”
- “Where were the keys actually located at 09:00, based on all evidence now available?”
- “What did our research report say about API behavior on September 1?”
- “What do we now know the API behavior was on September 1 after correcting that report?”

This directly sharpens `KA-I-008` and `KA-I-009`.

## Confidence

High.

## Non-conclusion

The exact query syntax and storage mechanism remain undecided.

---

# Finding 11 — Backdating a correction must not rewrite the audit timeline

## Observed upstream behavior

XTDB's system-time history is append-only while valid-time interpretation can be corrected retrospectively.

Its documentation demonstrates that the system can show both the corrected valid-time timeline and the prior uncorrected system-time view.

## Architectural lesson

When Vera receives a late correction:

- world-valid interpretation may change retroactively;
- record/system history must still preserve when the correction was learned/applied.

Backdating `valid_from` must not backdate `recorded_at` or erase the earlier belief state.

## Confidence

High.

## Non-conclusion

This does not imply that every observation should receive a full bitemporal interval immediately; synthesis may define simpler defaults for point events and static resources.

---

# Finding 12 — Event sourcing and bitemporality are complementary, not substitutes

## Observed upstream behavior

Current KurrentDB documentation describes:

- an immutable append-only event log;
- immutable event positions/order;
- streams;
- projections/read models;
- reconstruction/time travel;
- optimistic concurrency via expected stream revision.

XTDB bitemporality instead explicitly models valid and system time.

## Architectural lesson

Event sourcing is strong evidence for preserving **mutation/observation history** and rebuilding derived state.

Bitemporality is strong evidence for separating **world validity** from **record history**.

An append-only event log alone does not tell Vera:

- whether an event payload is an observation, claim, inference or verified fact;
- whether the content was true in the world;
- what valid interval the claim applies to;
- whether a later event is a correction versus an unrelated new fact;
- whether two sources conflict.

Conversely, a bitemporal current-state table does not automatically provide rich event intent, source evidence or action/effect semantics.

## Practical architecture lesson

Do not choose between “event history” and “temporal assertions” as if they solve the same problem.

Future synthesis should test whether Vera needs:

- immutable evidence/transition history;
- canonical temporal assertions;
- derived current projections;

as separate but linked planes.

## Confidence

High.

## Non-conclusion

KurrentDB/EventStoreDB is not selected as Vera's event store.

---

# Finding 13 — Concurrency protection belongs at the correction/append boundary

## Observed upstream behavior

KurrentDB supports expected-revision checks when appending to a stream. A write can require that the stream remain at the revision the writer observed; mismatches fail rather than silently applying over unseen concurrent changes.

This is a mature analogue for the campaign's recurring “stale read-modify-write” failure class.

## Architectural lesson

Assertion correction/supersession cannot rely only on:

1. read current assertion;
2. reason about it;
3. write replacement.

If another writer changes the assertion set during that interval, the supersession decision may be stale.

Future mutation contracts need an expected revision/generation/CAS-style check or equivalent transactional rule around semantically significant replacements.

## Confidence

High.

## Non-conclusion

This is recurrence for existing concurrency invariants/failures; no new ledger ID is required in this task.

---

# Finding 14 — Event occurrence is not epistemic truth

## Observed upstream behavior

KurrentDB documentation describes events as factual occurrences in the application's event model.

For Vera, however, many durable inputs are better modeled as factual **occurrences of evidence production**, not automatically factual world propositions.

## Architectural lesson

Examples:

Safe event/evidence form:

- `Camera-7 emitted face-match(person=Alice, confidence=.72) at T`.

Unsafe collapsed world-truth form:

- `Alice was in the kitchen at T`.

The first can be a durable observation occurrence.

The second is a derived assertion that may require sensor trust, corroboration, identity resolution and temporal reasoning.

Likewise:

- `User U said “I sold the truck”` is an observed communication event.
- `User U no longer owns truck` is a proposition that may be accepted with a particular epistemic basis but is not the same record.

This independently sharpens `KA-I-001` and `KA-I-025`.

## Confidence

High as an architecture inference from combined project + event-model evidence.

## Non-conclusion

KurrentDB itself does not make this Vera-specific epistemic distinction; that is precisely why event-store semantics alone are insufficient.

---

# Finding 15 — Measurement uncertainty is not epistemic confidence

## Observed upstream behavior

The Wikibase data model supports:

- quantity lower/upper bounds;
- time precision;
- coarse statement ranks.

These are different constructs.

A numeric uncertainty interval describes uncertainty/precision in a measured value.

A statement rank is a selection/display concept.

Neither is a general source-trust or epistemic-confidence model.

## Architectural lesson

Vera should not overload one `confidence` field to mean all of:

- classifier probability;
- sensor measurement uncertainty;
- source reliability;
- inference confidence;
- identity-match confidence;
- verification status;
- current-selection rank.

These quantities may need different types and aggregation rules.

## Confidence

High.

## Non-conclusion

This task does not define confidence calculus or Bayesian fusion.

---

# Finding 16 — Scope/applicability is partly demonstrated, but still a gap

## Observed upstream behavior

Wikidata qualifiers can contextualize statements with time, method and other property-specific qualifiers.

XTDB valid time provides a strong temporal applicability dimension.

The agent-project campaign already showed user/project/version/environment scopes.

## Architectural lesson

`KA-I-022` remains appropriate: applicability should be structured.

However, this gap task does not find one mature general-purpose model that cleanly governs all Vera scope axes such as:

- device/model/version;
- physical location;
- environment;
- project/repository/branch;
- user/household/role;
- task/run;
- jurisdiction;
- temporal interval;
- operational mode.

Relationship/ontology and later retrieval-requirements work still need to test how these qualifiers compose.

## Confidence

High on the gap; medium on eventual representation.

## Non-conclusion

A generic free-form qualifier bag is not endorsed as the final design.

---

# Finding 17 — Current truth should be a projection over retained assertions

## Evidence synthesis

Across Wikibase, XTDB and event-sourced history, current/default state is produced from retained historical material rather than requiring destructive overwrite.

## Architectural lesson

A useful conceptual model is:

`Evidence / observations / claims`

`-> canonical retained assertions with provenance + validity`

`-> conflict/supersession/verification transitions`

`-> current/default projection`

This projection may depend on:

- valid time;
- current record revision;
- rank/selection;
- verification/dispute state;
- source trust;
- principal/purpose eligibility;
- domain-specific cardinality.

Therefore “current” is generally derived state, even when optimized for fast deterministic lookup.

## Confidence

High.

## Non-conclusion

This does not mean current state must be recomputed from raw history on every query; materialized current projections may be appropriate if lineage/reconciliation is preserved.

---

# Finding 18 — Corrections and privacy erasure are different operations

## Evidence synthesis

Wikidata deprecation retains historically wrong/superseded statements.

XTDB/Kurrent preserve historical changes/events.

The existing campaign deletion evidence shows privacy erasure may require removal across canonical and derived planes.

## Architectural lesson

The knowledge lifecycle must distinguish at least:

- supersede/correct;
- deprecate/do-not-use-currently;
- dispute;
- archive;
- redact;
- delete/erase.

A correction should usually preserve the old evidence.

A privacy/legal erasure request may require destroying it.

Do not implement erasure by merely marking an assertion deprecated, and do not implement ordinary correction by destructive erasure.

## Confidence

High.

## Non-conclusion

The privacy deletion mechanics are a separate future gap task.

---

# Evidence-question disposition

## Q4 — Epistemic state

**Before:** strong evidence that agent memory systems lack positive semantics.

**After this task:** substantially improved requirement clarity.

Evidence supports separating:

- value/polarity state;
- epistemic basis;
- references/provenance;
- verification/dispute;
- current-selection rank;
- uncertainty.

Still open:

- exact controlled vocabulary for Vera's epistemic basis/status;
- confidence semantics;
- automatic verification policy.

## Q5 — Temporal truth

**After this task:** strong positive semantics.

Required conceptual distinction:

- world/valid time;
- record/system/transaction time.

Historical queries must distinguish corrected history from historical belief.

Still open:

- exact interval/event encoding;
- default treatment for timeless facts;
- physical storage.

## Q6 — Conflict and supersession

**After this task:** strong positive semantics.

Requirements:

- retain alternatives;
- preserve source/context;
- select/deprecate separately from deletion;
- preserve correction history;
- mutation concurrency guard.

Still open:

- adjudication policy;
- trust comparison;
- domain-specific cardinality/relationship replacement semantics.

## Q25 — Unknown/negative knowledge

**After this task:** strong positive semantics.

At least four distinct states are justified:

- concrete value/positive assertion;
- explicit negative/no-value;
- some value exists but unknown;
- not established.

Conflict remains separate.

Critical rule:

- absence becomes known-negative only under an explicit completeness/closed-world contract.

## Q26 — Scope of truth

**After this task:** temporal/method applicability is much clearer, but the broader cross-domain scope problem remains partial.

Later relationship/ontology and operational-domain research still needed.

---

# Cumulative invariant impact

No existing invariant is rejected or narrowed.

This task provides direct standards/domain recurrence for:

- **KA-I-001** — source/evidence occurrence separate from derived semantic truth;
- **KA-I-006** — supersession/correction is non-destructive/provenance-bearing;
- **KA-I-008** — valid/world time distinct from record/system time;
- **KA-I-009** — current, historical-as-corrected and historical-as-known are distinct query intents;
- **KA-I-010** — rank/selection is not epistemic confidence/truth;
- **KA-I-021** — unknown, false, not-established, conflict and historical truth are distinct;
- **KA-I-022** — applicability requires structured qualifiers;
- **KA-I-025** — epistemic basis/verification are separate from attribution/retrieval state.

### New candidate invariant

**KA-I-047 — Closed-world negative derivation requires an explicit completeness contract.**

Proposed wording:

> A missing value or unsuccessful search may be promoted from `not-established` to `known-negative` only when an explicit, evidence-backed completeness/closed-world contract covers the relevant subject set, predicate, scope, time and source/search population; otherwise absence remains unknown/not-established.

Status: **candidate** — supported by this one bounded gap task using W3C OWL/SHACL and Wikibase/Wikidata evidence.

---

# Failure-ledger impact

No new KA-F ID is created in this task.

Reason:

- the standards evidence clarifies semantic requirements but does not itself provide a current implementation incident/reproduction comparable to the existing failure ledger;
- “absence -> false” should become a hostile scenario/acceptance test later, but creating a failure ID from a standards warning alone would weaken the ledger's evidence discipline;
- transaction-time-as-valid-time and stale correction races map cleanly to existing temporal/concurrency families.

Failure IDs therefore remain **KA-F-001 through KA-F-049**.

---

# Hostile scenarios nominated for later review

These are nominations only; the hostile-review phase has not begun.

1. **Missing fact mistaken for false**
   - no record of Alice owning a truck;
   - system answers “Alice does not own a truck.”

2. **Search-index incompleteness mistaken for negative knowledge**
   - one index shard unavailable;
   - semantic search returns no match;
   - system records `known_false`.

3. **Unknown value collapsed to null/no-value**
   - user's spouse name is unknown;
   - system records “user has no spouse.”

4. **No-value collapsed to unknown**
   - authoritative inventory establishes no spare key exists;
   - system keeps asking where the spare key is because it cannot represent known absence.

5. **Pairwise negative collapsed to predicate-level no-value**
   - device is known not to be in room A;
   - system concludes device has no location.

6. **Late correction overwrites knowledge time**
   - event occurred 02:10, learned 03:00;
   - system rewrites record timestamp to 02:10 and can no longer answer when it learned the fact.

7. **Transaction time mistaken for valid time**
   - imported maintenance record arrives two days late;
   - state history incorrectly shows the maintenance starting only when imported.

8. **Correction destroys source history**
   - source A claimed value X;
   - source B proves Y;
   - X is deleted and later the system cannot explain why it previously acted on X.

9. **Deprecated source claim returned as current truth**
   - historic wrong software capability ranks semantically high;
   - current answer reports it without current-state filtering.

10. **Conflicting preferred assertions forced into arbitrary winner**
    - two authoritative sources disagree;
    - ingestion order silently determines current truth.

11. **Event log confused with world truth**
    - camera emits low-confidence face detection;
    - durable event is interpreted as proof the person was present.

12. **Measurement uncertainty confused with source confidence**
    - sensor reading ±5 units from highly trusted calibrated instrument;
    - system lowers source trust because numeric uncertainty is large.

13. **Closed-world assumption leaks across scope**
    - inventory A is complete for House A;
    - no spare key found there;
    - system generalizes “no spare key exists anywhere.”

14. **Corrected history versus as-known history conflated**
    - audit asks “what did Vera know when it made the decision?”;
    - query returns later-corrected world state instead.

---

# Requirements carried forward

Without selecting storage technology, future conceptual synthesis should be able to represent/test:

1. explicit assertion identity;
2. positive/value assertion;
3. explicit negative assertion;
4. known no-value;
5. some-value-but-unknown;
6. no assertion/not established;
7. conflicting assertions;
8. retained deprecated/historical assertions;
9. source/reference links;
10. qualifier/applicability fields;
11. epistemic basis;
12. verification/dispute status;
13. world-valid interval or event time;
14. record/system time;
15. correction/supersession lineage;
16. current/default selection as a projection;
17. expected revision/generation for significant correction writes;
18. explicit completeness contracts for any negative inference from absence;
19. distinct retrieval intents for:
    - current as best known now;
    - history as best known now;
    - history as known then;
    - conflict/evidence view;
20. explicit difference between ordinary correction/deprecation and privacy erasure.

---

# What this task does not establish

This research does **not** establish that ACL/Vera should use:

- RDF;
- OWL;
- SHACL;
- Wikibase/Wikidata;
- XTDB;
- SQL Server temporal tables;
- KurrentDB/EventStoreDB;
- event sourcing as the primary persistence model;
- a graph database;
- one universal Assertion table;
- one universal bitemporal table;
- a specific confidence scale;
- a specific ontology.

It also does not solve:

- entity resolution;
- controlled relationship semantics;
- formal provenance schema;
- ABAC/ReBAC authorization;
- privacy erasure;
- resource/artifact identity;
- cross-domain operational modeling.

Those remain later bounded tasks.

---

# Stop point

KA-G1 Priority A semantics research is complete.

The evidence materially closes the positive-semantics gap for:

- unknown versus false versus no-value;
- conflict retention;
- correction/deprecation without history destruction;
- valid time versus record/system time;
- corrected historical truth versus historical belief;
- the limits of event sourcing as an epistemic model.

One new candidate invariant is warranted: **KA-I-047**, requiring an explicit completeness/closed-world contract before absence may become known-negative.

No new failure ID is warranted from standards evidence alone.

No relationship/ontology research, formal provenance research, authorization/privacy research, resource identity research, retrieval-requirements work, hostile review, architecture synthesis, storage selection or implementation has begun.