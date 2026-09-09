# Formal Provenance / Evidence Lineage Gap Research

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** KA-G3 — Formal Provenance / Evidence Lineage  
**Research date:** 2026-09-08  
**Starting ACL checkpoint:** `598fe7cb461bbc10cb3298fdce05a5fcdf421b16`  
**Boundary:** provenance/evidence-lineage requirements only; no authorization/actionability design, resource-storage design, privacy-erasure design, operational-domain modeling, retrieval-question construction, hostile-scenario execution, architecture synthesis, database selection, or ACL/Vera implementation

---

# Executive assessment

KA-G3 closes the campaign's formal-provenance gap without changing the project's core architectural direction.

The main result is that ACL/Vera provenance should not be modeled as a few metadata fields such as `source`, `created_by`, or `confidence` attached to a fact. Formal provenance evidence strongly supports a separate lineage structure that can answer, at different levels of precision:

- what entity/resource/version was used;
- what transformation/activity occurred;
- what entity/resource/version was generated;
- which activity occurrence generated it;
- which inputs were actually used by that occurrence;
- which agent was associated with the activity;
- which plan/profile/procedure was intended or applied where relevant;
- which agent an output is attributed to;
- whether an agent acted on behalf of another for a specific activity;
- whether the lineage relation is derivation, revision, quotation, or domain-qualified primary-source use;
- which provenance provider/bundle supplied the lineage statement itself;
- how the provenance record was generated, transformed, aggregated, or attributed.

The strongest architecture boundary is:

> **Provenance is evidence about origin, transformation, influence and responsibility. It can support an assessment of reliability or trustworthiness, but it is not itself truth, epistemic confidence, policy authority, or proof that an external effect settled.**

This is consistent with the campaign's established separation:

`Knowledge ≠ Authority ≠ Execution`

and adds a more precise provenance layer:

`Source / input entity -> usage -> activity occurrence -> generation -> derived entity`

with responsibility and process context alongside, not collapsed into, that chain:

`agent -> association -> activity`

`plan/profile -> association/activity context`

`delegate -> acted-on-behalf-of -> responsible agent`

This task does **not** adopt W3C PROV or OpenLineage wholesale. Their models are used as requirements evidence.

No new invariant ID is necessary. KA-G3 substantially reinforces existing invariants, especially:

- **KA-I-001** — raw/source evidence remains separately addressable from derived knowledge;
- **KA-I-023** — transformation decisions that alter future reasoning need provenance of their own;
- **KA-I-025** — epistemic/verification state remains separate from attribution/storage/retrieval state;
- **KA-I-027** — derived outputs need coverage/generation identity;
- **KA-I-036** — source/resource identity, derived-record identity and presentation identity remain distinct;
- **KA-I-041** — mutating/background operations need stable occurrence identity;
- **KA-I-048** — separately addressable assertion occurrences remain useful where provenance differs.

The failure ledger also remains unchanged. This was standards/domain research, not a new reproduced implementation incident.

---

# 1. Scope lock and anti-drift decision

Before research began, the current campaign state was checked.

The documentation already explicitly named KA-G3 and excluded:

- authorization/actionability work;
- resources/artifacts work;
- privacy/retention work;
- Home Assistant/Matter operational modeling;
- retrieval-requirements construction;
- hostile-scenario execution;
- final conceptual synthesis;
- storage/database selection;
- implementation.

Therefore no redundant pre-task governance edit was made.

This report preserves that boundary.

---

# 2. Primary evidence inspected

## 2.1 W3C PROV Overview

Current published entry:

https://www.w3.org/TR/prov-overview/

Used for:

- provenance as information about entities, activities and people involved in producing data/things;
- provenance as input to assessments of quality, reliability and trustworthiness rather than an automatic truth judgment;
- provenance-of-provenance;
- reproducibility/versioning/derivation goals;
- the structure of the W3C PROV family.

The W3C PROV family remains the primary formal reference used here. The main Recommendation-track documents are from 2013; this task uses them as mature conceptual evidence, not as a technology-selection signal.

## 2.2 W3C PROV-DM

https://www.w3.org/TR/prov-dm/

Used for:

- Entity;
- Activity;
- Agent;
- Generation;
- Usage;
- Derivation;
- Revision;
- Quotation;
- Primary Source;
- Attribution;
- Association;
- Plan;
- Delegation;
- Influence;
- Bundle;
- Alternate;
- Specialization;
- Collection/Membership.

Particularly important for ACL/Vera:

- derivation may be described at varying precision;
- exact usage/activity/generation links can make a derivation path explicit;
- association distinguishes an agent's role in an activity from mere attribution of an entity;
- plans can themselves be entities with provenance;
- delegation records responsibility/on-behalf-of context but does not assign a precise degree of responsibility;
- bundles make provenance descriptions themselves addressable entities with their own provenance.

## 2.3 W3C PROV-O

https://www.w3.org/TR/prov-o/

Used for:

- evidence that the conceptual PROV model can be represented independently of one physical storage or serialization;
- qualified provenance relations;
- distinction between compact binary provenance relations and richer relation instances with attributes/context.

No RDF/OWL adoption decision is made.

## 2.4 W3C PROV Constraints

https://www.w3.org/TR/prov-constraints/

Used for:

- provenance validation as internal consistency/normalization of a provenance history;
- bundles as independently valid provenance instances;
- specialization/alternate constraints;
- distinction between a valid provenance description and broader claims of world truth.

## 2.5 W3C PROV-AQ

https://www.w3.org/TR/prov-aq/

Used for:

- provenance records as separately discoverable/queryable resources;
- target resource identity versus provenance-record identity;
- multiple provenance providers;
- third-party provenance about a resource;
- provenance query services;
- downstream/late-discovered provenance via pingback concepts.

Architecture lesson:

> the provenance known by one publisher or store need not be exhaustive.

Therefore an unsuccessful provenance lookup is not proof that no derivation/source exists.

## 2.6 W3C PROV-Links

https://www.w3.org/TR/prov-links/

Used for:

- distributed provenance produced by multiple parties;
- bundles as independent provenance perspectives;
- the need to identify not just an entity but the description/perspective in which that entity was described;
- provenance aggregation/stitching without mutating another party's original bundle.

The `Mention` construct is experimental/Note-level evidence and is not adopted as an ACL/Vera primitive.

## 2.7 OpenLineage

Current documentation inspected:

https://openlineage.io/docs/spec/object-model/  
https://openlineage.io/docs/spec/facets/  
https://openlineage.io/docs/spec/facets/job-facets/lineage/  
https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.json

Current documentation observed version: `1.53.0`.

Used as contemporary operational corroboration for:

- Job versus Run identity;
- Dataset inputs/outputs;
- run lifecycle events;
- source/version facets;
- exact lineage edges;
- explicit warning that inferring every event input as a source of every event output creates false lineage edges;
- versioned/extensible lineage metadata.

OpenLineage is not selected as ACL/Vera's provenance implementation.

---

# 3. Provenance is not a truth value

## Observed behavior

The W3C overview defines provenance as information about entities, activities and people involved in producing data or things, and says it can be used to form assessments about quality, reliability or trustworthiness.

It does not define provenance presence as proof that a proposition is true.

## Architecture lesson

ACL/Vera must be able to hold:

- a well-provenanced false claim;
- a poorly provenanced true observation;
- conflicting claims with independently valid provenance;
- a derived claim whose transformation history is known but whose epistemic verification remains pending.

Therefore:

`provenance quality != truth`

and:

`source authority != proposition truth`

## Example

A signed maintenance report may reliably prove:

> Technician X recorded “bearing temperature normal” at 09:00.

That provenance does not automatically prove:

> the bearing temperature was actually normal.

The proposition's epistemic state still depends on evidence quality, sensor corroboration, calibration, later corrections, etc.

## Campaign impact

Strong recurrence for KA-I-025.

---

# 4. Entity, activity occurrence and agent must remain distinct

## Observed behavior

PROV separates:

- **Entity** — a thing/state/resource/aspect being described;
- **Activity** — something that occurs over time and acts on/with entities;
- **Agent** — something bearing responsibility for an activity or entity's existence.

OpenLineage independently separates:

- Job definition;
- Run occurrence;
- input/output Dataset.

## Architecture lesson

ACL/Vera should not encode provenance merely as:

`derived_item.created_by = model-X`

That loses at least:

- the actual transformation occurrence;
- exact inputs;
- generated output identity;
- runtime/profile/version;
- who/what invoked the transformation;
- which plan/prompt/procedure was applied;
- retry/run identity.

A more faithful requirement is:

`input entity/version`
`↓ used by`
`transformation/activity occurrence`
`↓ generated`
`output entity/version`

with agent/process responsibility linked separately.

## ACL example

A research summary should be able to distinguish:

- source web page/PDF version;
- extraction activity occurrence;
- extracted evidence record;
- synthesis activity occurrence;
- derived finding;
- model/runtime/prompt profile involved;
- human/agent responsible for initiating or approving the transformation.

## Campaign impact

Strong recurrence for KA-I-001, KA-I-023, KA-I-036 and KA-I-041.

---

# 5. Derivation has levels of precision

## Observed behavior

PROV-DM explicitly permits a derivation to be described simply as one entity derived from another.

When the activity is known, derivation can include it.

For higher precision, the derivation can identify:

- the usage event for the input entity;
- the activity occurrence;
- the generation event for the output entity.

PROV states that this additional information supports provenance analysis and reproducibility.

## Architecture lesson

ACL/Vera should support more than one provenance precision tier, but must know which tier is present.

Suggested conceptual levels for later synthesis:

### P0 — source attribution only

`output <- source`

Useful for simple citation.

### P1 — coarse derivation

`output wasDerivedFrom input`

Useful when the specific process occurrence is unavailable.

### P2 — activity-qualified derivation

`input -> activity occurrence -> output`

Useful for normal derived knowledge.

### P3 — reproducibility-grade derivation

Includes exact:

- input identity/version/digest where applicable;
- activity/run occurrence identity;
- output identity/version;
- transformation profile/plan/model/prompt/schema/ontology version where behavior-bearing;
- responsible agent/provider;
- generation/use timestamps and/or transaction revision where required.

This is requirements guidance only. The final architecture may use different names.

## Critical rule

Low-precision provenance must not be silently presented as high-precision provenance.

“Derived from document X” is not equivalent to:

“Produced by activity A from bytes/version V of document X using parser/model/profile P.”

---

# 6. Exact lineage must not be inferred from co-occurrence

## Observed behavior

OpenLineage's explicit Lineage Job Facet exists specifically to express exact source-to-target edges rather than treating every input observed in an event as a source for every output.

Its documentation gives the example of one job reading `customers` and `orders` while independently writing `customer_summary` and `order_summary`; event-level co-occurrence would incorrectly imply a Cartesian set of dependencies.

## Architecture lesson

A shared run, prompt, conversation, batch, document, or activity container is not itself proof that every contained input influenced every output.

ACL/Vera must avoid provenance such as:

`all retrieved context -> every generated assertion`

unless the transformation actually supports that dependency.

This matters especially for LLM use, where a context window may contain many items that did not materially support a particular extracted/derived claim.

## Future acceptance fixture

A transformation has three inputs and two independently produced outputs.

Expected:

- exact per-output source dependencies where known;
- unknown/coarse dependency status where not known;
- never fabricate complete all-to-all edges merely because items shared one run.

## Campaign impact

This strengthens the precision interpretation of KA-I-023 and KA-I-027 without requiring a new invariant ID.

---

# 7. Attribution, association and delegation are different

## Attribution

PROV attribution ascribes an entity to an agent.

It is useful when the exact generating activity is unknown or irrelevant.

Example architecture question:

> Who is responsible for the existence/publication of this report?

## Association

PROV association links an activity with an agent and can identify the plan on which the agent relied.

Example architecture question:

> Which agent participated in this specific transformation run, and under what intended procedure/profile?

## Delegation

PROV delegation records that one agent acted on behalf of another in an activity context.

The specification notes that the responsible party retains some responsibility but does not determine who bears what degree.

## Architecture lesson

ACL/Vera must not collapse:

- creator/author;
- operator/invoker;
- transforming software/model;
- approving principal;
- service account;
- organization;
- delegated worker;
- policy authority.

These may all participate in one lineage chain but have different meanings.

## Security boundary

A provenance relation saying:

`WorkerAgent acted on behalf of ForemanAgent`

must **not** grant runtime tool permissions.

That is historical/lineage information, not an authorization token or policy rule.

The later authorization task remains responsible for executable authority semantics.

---

# 8. Plan/procedure identity belongs in transformation provenance when behavior-bearing

## Observed behavior

PROV association may include a Plan, defined as an entity representing intended actions/steps used to achieve goals in the activity context.

Plans themselves can have provenance.

## Architecture lesson

For ACL/Vera, behavior-bearing process descriptions may need independent identity and provenance, including examples such as:

- prompt template;
- extraction procedure;
- transformation rule set;
- parser configuration;
- model/system-prompt profile;
- ontology/inference profile;
- research protocol;
- workflow definition;
- test procedure.

This does **not** mean every tiny runtime setting becomes canonical knowledge.

It means that when a plan/profile materially changes the interpretation or reproducibility of an output, lineage must be able to identify it.

## Campaign recurrence

Reinforces KA-I-017, KA-I-018, KA-I-023 and KA-I-033.

---

# 9. Revision, quotation and primary-source relations should not be collapsed

## Revision

PROV treats revision as a subtype of derivation in which the resulting entity is a revised version of the preceding entity.

## Quotation

Quotation is a derivation in which some or all of the preceding entity is copied/quoted.

## Primary source

PROV models primary source as a relation, not an intrinsic entity type, because something may be primary for one derived artifact/topic and not another.

Its determination is domain-conventional and may be interpretive.

## Architecture lesson

ACL/Vera provenance should support meaningfully distinct derivation kinds rather than one generic `source_of` relation when the distinction affects interpretation.

Examples:

- copied verbatim from;
- summarized from;
- translated from;
- revised from;
- extracted from;
- computed from;
- inferred from;
- imported from;
- primary-source-for in this domain/context.

The final controlled vocabulary is not selected here.

## Important caution

“Primary source” is context-dependent.

A GitHub issue is a primary source for:

> the reporter claimed this behavior.

It is not automatically a primary source proving:

> the behavior actually occurs in all affected versions.

---

# 10. Provenance descriptions themselves need provenance

## Observed behavior

PROV bundles are named sets of provenance descriptions and are themselves Entities.

This allows provenance-of-provenance:

- who produced the bundle;
- when it was produced;
- whether it was derived from/aggregated from other bundles.

PROV examples explicitly show separate observers producing separate bundles and an aggregator producing a third bundle derived from them.

## Architecture lesson

ACL/Vera cannot safely treat provenance metadata as magical trustworthy metadata.

The system needs to be able to ask:

- who asserted this provenance edge?
- which extractor/provider supplied it?
- when?
- under what profile?
- was it imported from an external system?
- was it generated automatically?
- was it manually corrected?
- was it aggregated from other provenance records?

## Example

A model-generated citation map is provenance **data**, but the map itself has provenance and can be wrong.

That derived provenance graph must not overwrite raw source linkage merely because it is formatted as provenance.

## Campaign impact

Strong recurrence for KA-I-001, KA-I-023 and KA-I-025.

---

# 11. Multiple parties may hold different provenance descriptions of the same thing

## Observed behavior

PROV-Links describes distributed settings in which separate parties create independent provenance bundles concerning the same entity.

It emphasizes that a resource/entity URI alone may not identify the particular description/perspective being referenced.

## Architecture lesson

ACL/Vera needs to distinguish:

- the entity/resource being discussed;
- a provenance description about it;
- the provider/perspective/bundle that supplied that description.

Two providers can disagree about provenance without requiring one provenance record to overwrite the other.

This is analogous to KA-G1's conflict retention for propositions and KA-G2's separately addressable statement occurrences.

## Non-conclusion

KA-G3 does not require W3C Bundles as the physical implementation.

The architectural requirement is source-addressable provenance assertions/perspectives.

---

# 12. Provenance access is not provenance completeness

## Observed behavior

PROV-AQ supports multiple ways to locate provenance and explicitly considers third-party provenance providers and provenance discovered after original publication.

## Architecture lesson

A provenance query can return:

- some known provenance;
- provenance from one provider;
- provenance filtered by a service;
- no provenance currently discoverable.

None of these by itself proves global completeness.

Therefore:

`no provenance record found != no provenance exists`

This mirrors KA-G1's closed-world rule.

A claim such as:

> “this assertion has no source”

requires an explicit completeness contract if it is stronger than:

> “no source is currently recorded/discoverable in the searched provenance population.”

## Campaign impact

Adjacent independent reinforcement for KA-I-047; not enough by itself to promote the invariant because this is provenance-discovery completeness rather than the full negative-knowledge contract.

---

# 13. Provenance validation is not truth validation

## Observed behavior

PROV Constraints defines a notion of valid provenance based on internal constraints, ordering, typing, normalization and consistency of a provenance history.

## Architecture lesson

ACL/Vera must distinguish at least:

- structurally valid provenance;
- provenance authenticity/integrity;
- provenance completeness;
- source trust;
- epistemic verification of the derived proposition;
- policy authorization to act on the proposition.

A provenance graph can be structurally valid while containing false or maliciously supplied statements.

## Security consequence

“Valid PROV” or “complete lineage object” must never become a bypass around content trust/prompt-injection policy.

---

# 14. Resource/entity versions must be lineage-addressable

## Observed behavior

PROV specialization provides a way to describe a more specific aspect/version/context of an underlying changing thing.

OpenLineage distinguishes datasets and supports dataset version facets when the underlying store provides version identity.

## Architecture lesson

Provenance for a changing resource should not normally point only to a mutable logical name when exact content/version affects derivation.

Example:

`RiskCardOCR roster.xlsx`

is insufficient if the relevant input was specifically the roster as of revision V at 10:03.

The later resource/artifact task still needs to determine the exact logical-resource/locator/digest/version requirements.

## Boundary

KA-G3 does not solve resource identity; it only establishes that provenance needs to address the relevant version/aspect where reproducibility depends on it.

---

# 15. Collections/batches do not remove item-level provenance needs

## Observed behavior

PROV supports collections/membership and dictionary-like provenance extensions.

OpenLineage supports run-level datasets while also adding more precise facets, including column and explicit lineage structures.

## Architecture lesson

ACL/Vera may need both:

- batch-level provenance;
- item/claim-level provenance.

Example:

A PDF ingestion activity may produce 100 extracted assertions.

It is useful to know all 100 came from the same ingestion run, but a consequential assertion should still identify the exact page/span/evidence and transformation where practical.

Batch membership is not a substitute for claim-level source support.

---

# 16. LLM provenance needs transformation-event identity

LLMs make provenance especially easy to flatten incorrectly.

An output may depend on:

- retrieved records;
- prompt/system instructions;
- model build;
- model/provider/runtime profile;
- tool results;
- prior conversation/context;
- transformation/extraction prompt;
- ontology/rules profile;
- human edits/approvals.

KA-G3 does not require every token's causal ancestry.

Instead it supports a practical rule:

> Record the inputs and behavior-bearing transformation profile at the finest reliable granularity required by the consequence/reproducibility class, while explicitly representing when dependency precision is coarse or unknown.

Do not manufacture false precision.

---

# 17. Provenance should be queryable in both directions

Useful ACL/Vera provenance queries include:

Backward:

- What source evidence supports this assertion?
- What transformation produced this summary?
- Which model/profile created this extraction?
- What prior revision was this derived from?

Forward/impact:

- Which assertions depend on this source?
- Which summaries/indexes were built from the deleted resource?
- What should be re-derived after an ontology/parser/model change?
- Which decisions were informed by a now-superseded finding?

PROV-AQ's discussion of downstream provenance and OpenLineage's explicit lineage both support these needs.

## Boundary

KA-G3 specifies the retrieval requirement conceptually but does not design the query engine or storage indexes.

---

# 18. Provenance and effect settlement remain separate

An activity/run record can say that a transformation or tool invocation was attempted or that an output artifact was generated.

It does not automatically prove that a real-world external effect settled exactly once.

Examples:

- API call emitted versus remote transaction committed;
- email send attempted versus accepted/delivered;
- file write requested versus durably settled;
- vehicle-start request sent versus vehicle started.

The existing ACL/Vera effect-ledger boundary remains necessary.

KA-G3 does not merge provenance with the effect ledger.

Provenance may reference effect-ledger evidence, but it cannot replace settlement semantics.

---

# 19. Provenance and authority remain separate

PROV attribution/association/delegation describe responsibility/history.

They are not authorization credentials.

Examples:

- `worker acted on behalf of foreman` in historical provenance;
- `report was attributed to manager`;
- `activity was associated with service account`.

None grants present permission to:

- read protected data;
- mutate knowledge;
- execute a tool;
- approve a high-risk action;
- impersonate another principal.

The later authorization/actionability task remains necessary.

---

# 20. Requirements carried forward from KA-G3

1. Provenance is separate from proposition truth/confidence/verification.
2. Provenance is separate from authorization and effect settlement.
3. Source/Entity, transformation/Activity occurrence and responsible Agent remain distinct concepts.
4. Derivation may exist at different precision levels; provenance must expose the precision actually known.
5. Consequential/reproducibility-grade derivation should identify exact used inputs, activity occurrence and generated outputs where available.
6. Shared event/run/container membership is not proof of all-to-all dependency.
7. Exact lineage edges should be retained where known; unknown/coarse dependency should remain explicitly unknown/coarse rather than fabricated.
8. Attribution, activity association and delegation are different responsibility relations.
9. Plans/procedures/profiles that materially change outputs should be independently identifiable/provenance-bearing.
10. Revision, quotation, primary-source use and other derivation subtypes should remain distinguishable when interpretation depends on them.
11. Primary-source status is contextual, not an intrinsic universal trust flag.
12. Provenance records themselves need source/provenance where trust or aggregation matters.
13. Multiple providers/perspectives may provide different provenance descriptions of the same entity.
14. Provenance lookup failure is not proof of provenance absence without an explicit completeness contract.
15. Structural provenance validity is not truth verification or provenance authenticity.
16. Changing resources should be linked at the version/aspect required for reproducibility.
17. Batch/run provenance does not eliminate claim/item-level evidence needs.
18. Provenance precision should be proportional to consequence/reproducibility requirements; do not manufacture token-level or claim-level precision that was not observed.
19. Provenance must support backward explanation and forward impact/re-derivation analysis.
20. Transformation provenance should identify behavior-bearing model/parser/prompt/schema/ontology/profile versions when those change semantics.
21. Historical provenance should remain retained through ordinary corrections where retention policy permits; privacy erasure is a separate later requirement.
22. Derived provenance graphs/summaries remain derived evidence and must not overwrite raw source lineage merely because they are formatted as provenance.

---

# 21. Candidate conceptual pattern for later synthesis

Not a final schema.

A later conceptual model should be able to express something equivalent to:

```text
Source/Entity Version
    |
    | used
    v
Transformation Activity Occurrence
    |-- associated-with --> Agent
    |-- followed/profile --> Plan/Profile Entity
    |
    | generated
    v
Derived Entity / Evidence / Assertion Occurrence
```

and optionally:

```text
Derived Entity
    wasDerivedFrom
Source Entity
```

when only coarse provenance is available.

For provenance-of-provenance:

```text
Provenance Record/Bundle
    generated-by Activity
    attributed-to Agent/Provider
    derived-from Prior Provenance Records
```

This is a conceptual acceptance requirement only.

---

# 22. Nominated later hostile/acceptance scenarios

Do not execute them in this state.

- a citation exists but points to a source that does not support the claim;
- a correct source is attached to the wrong assertion occurrence;
- several context documents share one run but only one actually supports the output;
- event-level lineage creates false Cartesian input/output dependencies;
- source file changes after ingestion while provenance keeps only mutable path;
- derived summary loses exact source revision;
- a model-generated provenance map is treated as authoritative provenance;
- two provenance providers disagree about the same derivation;
- provenance bundle is valid but supplied by an untrusted/malicious provider;
- primary-source flag is interpreted as automatic truth/high trust;
- activity is attributed to an agent but exact transformation occurrence is missing;
- delegation provenance is misused as current execution authority;
- plan/profile changes but derived outputs are not marked under a new derivation profile;
- coarse derivation is displayed as exact evidence lineage;
- deletion impact analysis misses derived outputs because provenance only points backward;
- a run records success but the real-world effect was not settled;
- privacy erasure removes source but leaves provenance containing sensitive copied values;
- provenance query returns nothing and the system incorrectly concludes “no source exists.”

---

# 23. Twenty-six-question disposition after KA-G3

## Materially improved by this task

**3. Provenance**

Now has strong positive semantics for:

- source/derived separation;
- transformation activity occurrences;
- usage/generation/derivation;
- agent attribution/association/delegation;
- plans/profiles;
- provenance-of-provenance;
- multiple provider perspectives;
- queryability/impact lineage;
- lineage precision.

## Strong project/gap evidence already adequate for later synthesis

- 1 Stable identity
- 2 Identity vs namespace/principal
- 4 Epistemic state
- 5 Temporal truth
- 6 Conflict/supersession
- 7 Relationships
- 10 Knowledge vs authority
- 12 Canonical vs derived
- 13 Structured retrieval
- 14 Relationship retrieval
- 15 Full-text retrieval
- 16 Semantic retrieval
- 17 Composite retrieval
- 18 Context construction
- 19 Memory poisoning/prompt injection
- 20 Concurrency
- 21 Derived-state integrity
- 23 Schema/version evolution
- 24 Recovery semantics
- 25 Unknown/negative knowledge

## Remaining bounded direct gaps before synthesis

- 8 Permissions/sensitivity — direct formal authorization study still needed
- 9 Actionability/use-purpose semantics
- 11 Resources/artifacts
- 22 Privacy deletion/retention
- 26 Scope of truth/generality — non-AI operational validation

---

# 24. Cumulative ledger decision

## Invariants

Invariant IDs remain **KA-I-001 through KA-I-049**.

No new ID is created.

Reason:

The strongest provenance requirements are already captured by existing invariant families. Creating new IDs for every W3C PROV distinction would duplicate rather than clarify the architecture evidence.

Strong KA-G3 recurrence:

- **KA-I-001** — raw/source evidence remains separate from derived semantic knowledge;
- **KA-I-017/018** — behavior-bearing process/profile/version changes require explicit derivation identity;
- **KA-I-023** — transformations need provenance of their own;
- **KA-I-025** — provenance/attribution remains separate from epistemic verification;
- **KA-I-027** — derived projections require source/generation coverage identity;
- **KA-I-036** — source and derived identities remain distinct;
- **KA-I-041** — transformation/run occurrences need stable occurrence identity;
- **KA-I-047** — provenance discovery absence is adjacent recurrence for completeness-qualified negative inference;
- **KA-I-048** — provenance relation/statement occurrences may require separate addressability where sources/context differ.

No invariant is promoted to a final architecture rule.

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID is created because KA-G3 supplied standards/specification evidence rather than a new concrete implementation failure or reproduced incident.

Potential failures such as false Cartesian lineage and provenance-as-truth are nominated for the later hostile/acceptance review rather than being mislabeled as observed incidents.

---

# 25. Scope conclusion

KA-G3 answers the provenance question deeply enough to proceed without another broad provenance survey.

The evidence supports a provenance substrate that is:

- source-addressable;
- transformation-aware;
- occurrence-aware;
- version/profile-aware;
- responsibility-aware;
- capable of provenance-of-provenance;
- able to preserve multiple perspectives;
- queryable backward for explanation and forward for impact;
- explicit about lineage precision;
- separate from truth, authority and effect settlement.

It does **not** justify:

- choosing W3C PROV as the physical schema;
- choosing RDF/graph storage;
- choosing OpenLineage as the runtime implementation;
- selecting a database;
- designing authorization;
- implementing Vera/ACL memory.

The remaining pre-synthesis research should now stay on the already-defined path rather than widening back into agent frameworks or general semantic-web research.

---

# Stop point

KA-G3 is complete.

Do not begin KA-G4 or any later phase inside this task.

The next candidate is a bounded **knowledge authorization + actionability/use-purpose** study, but it requires separate authorization/continuation.