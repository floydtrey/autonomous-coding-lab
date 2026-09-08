# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** project revisits, coverage scan, promoted Agno revisit and two standards/domain gap tasks complete; stopped before formal-provenance gap research  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

## Governing plan

Read `CAMPAIGN_PLAN.md` before doing any further work in this campaign.

The completed Tasks 1–31 project campaign remains historical evidence. Do not restart it or rewrite historical catalogs merely to fit the future knowledge model.

No completed evidence task authorizes final architecture synthesis, storage/database selection, retrieval implementation, embeddings, model benchmarking, ACL/Vera implementation or autonomous worker execution.

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
14. **KA-G2 — Relationships and Ontology Evolution** — complete

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
- `gaps/relationships-ontology-evolution.md`

Cumulative ledgers:

- `invariants.md`
- `failure-patterns.md`

This state is intentionally a compact checkpoint. Detailed evidence remains in the dedicated reports.

---

# KA-G2 boundary and verification

The user explicitly authorized KA-G2 after KA-G1.

Starting branch/head for the task:

`18b571c1000fe9b5fcc5ca01556f52fbb372bf17`

Starting message:

`research: complete epistemic and temporal semantics gap`

KA-G2 was bounded to:

- first-class relationship assertions;
- relationship/predicate semantic identity;
- direction/inverse semantics;
- symmetry/asymmetry/transitivity and related property characteristics;
- direct relationship versus transitive closure/inference;
- qualifiers/applicability and statement occurrence identity;
- relationship retrieval/path semantics;
- validation constraints versus logical entailment;
- controlled vocabulary reuse/extension;
- ontology/vocabulary versioning;
- deprecation/replacement;
- semantic migration and historical interpretation.

Explicitly excluded:

- full formal provenance/W3C PROV study;
- ABAC/ReBAC/actionability policy;
- resource/artifact identity;
- privacy erasure/retention mechanics;
- Home Assistant/Matter operational-domain validation;
- representative retrieval-question construction;
- hostile/adversarial scenario execution;
- final conceptual schema synthesis;
- storage/graph/database selection;
- implementation.

## Primary evidence inspected

### W3C RDF 1.2 Concepts and Abstract Data Model

https://www.w3.org/TR/rdf12-concepts/

Used for:

- proposition versus asserted triple;
- triple terms/reifiers;
- multiple reifiers for one proposition;
- reification without asserting truth;
- change over time;
- stable intended IRI referent;
- entailment profile separation.

Qualification: RDF 1.2 was inspected as a 2026 Candidate Recommendation Snapshot; it is standards-direction evidence, not a technology-selection decision.

### W3C OWL 2

https://www.w3.org/TR/owl-primer/  
https://www.w3.org/TR/owl2-quick-reference/

Used for:

- inverse/symmetric/asymmetric/reflexive/irreflexive properties;
- functional/inverse-functional properties;
- transitive properties;
- subproperties/disjoint properties;
- domain/range;
- property chains;
- ontology version IRI;
- prior/backward-compatible/incompatible/deprecated version annotations.

### W3C SKOS Reference

https://www.w3.org/TR/skos-reference/

Used for:

- direct hierarchy versus transitive closure;
- associative versus hierarchical relations;
- inverse relation semantics;
- mapping relations such as exact/close/broad/narrow/related match;
- integrity conditions;
- domain/range as inference rather than validation.

### W3C SHACL

https://www.w3.org/TR/shacl/

Used for:

- validation as a separate layer from ontology entailment;
- node/property shapes;
- property paths;
- cardinality/type/value constraints;
- closed shapes.

### SPARQL 1.2 Query

https://www.w3.org/TR/sparql12-query/

Used for:

- inverse/sequence/alternative/arbitrary-length property paths;
- graph connectivity/path retrieval;
- evidence that connectivity retrieval is distinct from derivation/explanation provenance.

Qualification: SPARQL 1.2 was a 2026 Working Draft; the task used its path model directionally and did not make adoption decisions.

### Wikibase / Wikidata

https://www.mediawiki.org/wiki/Wikibase/DataModel  
https://doc.wikimedia.org/Wikibase/master/php/docs_topics_json.html  
https://www.wikidata.org/wiki/Help:Property_constraints_portal  
https://www.wikidata.org/wiki/Help:Statements/en  
https://www.wikidata.org/wiki/Help:Qualifier

Used for:

- stable Property identity independent of labels;
- direction-specific relationship meaning;
- statement occurrence IDs;
- main claim versus qualifiers/references/rank;
- multiple statements for one property/value;
- contextual/time qualifiers;
- property constraints and exceptions;
- symmetric/inverse/type/cardinality/qualifier constraints;
- schema/datatype evolution where historical records may lag migration.

### OBO Foundry

https://obofoundry.org/principles/fp-007-relations.html  
https://obofoundry.org/principles/fp-019-term-stability.html  
https://obofoundry.org/id-policy.html

Used for:

- reuse of governed relation identifiers;
- relation interoperability;
- subproperty alignment and property-chain governance;
- stable meaning/identifier policy;
- meaning-changing revision requires a new identifier;
- deprecation rather than identifier reuse;
- exact `replaced_by` versus inexact `consider` guidance;
- removal/replacement of obsolete logical uses;
- stable current and dated version artifacts.

---

# Highest-value KA-G2 findings

## 1. Relationship type identity is not its label

A stable relationship/predicate identity must be independent of display labels, aliases, localization and model-generated phrasing.

Natural-language similarity cannot safely collapse distinct relations such as:

- owns;
- assigned_to;
- uses;
- located_at;
- observed_at;
- parent_of / has_parent.

## 2. Governed relation semantics are behavior-bearing

Direction, inverse, symmetry/asymmetry, transitivity, functionality/cardinality, domain/range, subproperty, disjointness and property-chain rules can change inference.

When ACL/Vera relies on them, they must be explicit/versioned rather than hidden in application code or inferred from labels.

## 3. Logical inference and validation are different layers

OWL/SKOS semantics can entail new facts.

SHACL/Wikidata-style constraints can instead validate or flag expected usage and may permit exceptions.

ACL/Vera must distinguish:

- semantic entailment rule;
- hard validation rule;
- soft quality expectation;
- UI/editor suggestion;
- security/policy eligibility.

## 4. Direct relation and transitive closure are different knowledge

SKOS's direct hierarchy versus transitive hierarchy, plus OWL transitivity/property chains, establish that direct asserted edges must remain distinguishable from inferred closure.

## 5. Assertion occurrence identity is distinct from the abstract proposition

RDF 1.2 permits multiple reifiers for the same proposition.

Wikibase gives statements their own IDs plus qualifiers/references/rank.

Therefore identical subject-predicate-object propositions may require multiple separately addressable occurrences because source, time, epistemic basis or applicability differs.

This produces new **KA-I-048**.

## 6. Qualifiers/applicability can change relationship meaning

Time, role, method, environment, version and other qualifiers may be intrinsic to interpretation of one relationship occurrence.

This strongly reinforces structured applicability under **KA-I-022**.

## 7. Relationship retrieval has different intents

At least:

- direct assertion retrieval;
- inference-aware retrieval;
- path/connectivity retrieval;
- explanation/evidence-chain retrieval.

A path endpoint result is not the same thing as a direct source assertion.

Consequential reasoning needs reconstructable support from asserted edges plus inference/vocabulary profile.

This produces new **KA-I-049**.

## 8. Controlled vocabulary does not mean frozen universal ontology

Evidence supports:

- small governed core;
- stable IDs;
- definitions;
- explicit extension;
- aliases/mappings;
- optional subproperty alignment;
- version/deprecation lifecycle.

## 9. Exact and approximate mappings are different

SKOS exact/close/broad/narrow/related mappings and OBO `replaced_by` versus `consider` demonstrate that approximate mappings must not be upgraded to exact equivalence for convenience.

## 10. Meaning-changing vocabulary updates must not reuse semantic identity

OBO requires a new identifier when a term's intended referents change materially.

Historical relationship assertions therefore must not silently inherit a new meaning because a label remained unchanged.

This strongly reinforces **KA-I-017**.

## 11. Deprecation is not deletion

Deprecated relation definitions may remain historically addressable, with exact or inexact replacement guidance.

Active logical uses of obsolete vocabulary require explicit repair/migration.

## 12. Ontology/vocabulary profile is part of semantic reproducibility

Derived relationships may differ when ontology/inference rules differ.

A consequential derived relationship should therefore be able to identify the semantic/inference profile under which it was produced.

---

# Cumulative ledger state after KA-G2

## Invariants

Invariant IDs now run **KA-I-001 through KA-I-049**.

Status change:

- **KA-I-007 — candidate → reinforced**
  - Graphiti/Agno provided prior project evidence;
  - KA-G2 independently supplies OWL/SKOS/Wikibase/OBO governed-relation semantics.

New candidates:

- **KA-I-048 — candidate**
  - relationship semantic identity is distinct from individual relationship-assertion occurrence identity.
- **KA-I-049 — candidate**
  - direct assertions, derived/entailed relationships and path connectivity are distinct retrieval intents; consequential derived relationships require explainable supporting assertion chains plus inference/vocabulary profile.

Candidates remaining after KA-G2:

- KA-I-004 — reversible identity merge/split transition
- KA-I-031 — exact settled knowledge revision for active context
- KA-I-037 — logical resource vs locator vs content/version digest
- KA-I-038 — canonical read isolation/value semantics
- KA-I-039 — semantic persistence round-trip fidelity
- KA-I-040 — live/replay transition equivalence
- KA-I-044 — transport liveness vs logical continuation validity
- KA-I-045 — terminal/expiry lifecycle for pending authority/effects
- KA-I-047 — closed-world negative inference requires completeness contract
- KA-I-048 — relation semantic identity vs assertion occurrence identity
- KA-I-049 — direct vs inferred/path relationship retrieval and explanation

Strong recurrence without status changes:

- KA-I-002
- KA-I-005/006
- KA-I-008/009
- KA-I-012
- KA-I-017/018
- KA-I-022/023
- KA-I-025
- KA-I-030

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID or status change is made.

Reason:

- KA-G2 is standards/domain evidence rather than a new implementation incident/reproduction;
- existing **KA-F-005** remains the concrete fixture for treating relationship name + shared endpoint as sufficient supersession proof.

---

# Twenty-six-question disposition after KA-G2

## Strong enough for later requirements/synthesis without another agent-framework revisit

- 1 Stable identity
- 2 Identity vs namespace/principal
- 4 Epistemic state
- 5 Temporal truth
- 6 Conflict/supersession
- 7 Relationships — **positive semantics materially improved by KA-G2**
- 8 Permissions/sensitivity — formal authorization gap still remains
- 10 Knowledge vs authority
- 12 Canonical vs derived
- 13 Structured retrieval
- 14 Relationship retrieval — **positive semantics materially improved by KA-G2**
- 15 Full-text retrieval
- 16 Semantic retrieval
- 17 Composite retrieval
- 18 Context construction
- 19 Memory poisoning/prompt injection
- 20 Concurrency
- 21 Derived-state integrity
- 23 Schema/version evolution — **ontology evolution materially improved by KA-G2**
- 24 Recovery semantics
- 25 Unknown/negative knowledge

## Still requires bounded direct gap/domain research

- 3 Formal provenance/evidence lineage
- 9 Actionability/use-purpose semantics
- 11 Resources/artifacts
- 22 Privacy deletion/retention
- 26 Scope of truth / generality — non-AI operational validation still needed

Question 8 also still benefits from direct ABAC/ReBAC-style authorization study despite strong project evidence.

---

# Requirements carried forward from KA-G2

1. Relationship types have stable semantic IDs independent of labels.
2. Behavior-bearing relation semantics are explicit/versioned when relied upon.
3. Relationship assertion occurrences may have first-class identity separate from the abstract proposition.
4. Qualifiers/applicability can be part of statement meaning.
5. References/evidence remain separate from qualifiers and currentness/rank.
6. Direct and inferred relationships remain distinguishable.
7. Consequential path/derived answers can be traced to supporting direct assertions and inference profile.
8. Validation constraints and logical inference rules remain separate layers.
9. Soft constraints may have exceptions and do not automatically negate sourced observations.
10. Controlled vocabularies remain extensible.
11. Exact and approximate mappings remain distinct.
12. Meaning-changing vocabulary edits require new semantic identity or explicit migration rather than silent reinterpretation.
13. Deprecated relation definitions remain historically addressable where retention policy permits.
14. Exact replacement and candidate/inexact replacement remain distinct.
15. Vocabulary/inference profile belongs in derivation/reproducibility identity when it changes semantics.
16. Existing historical assertions do not automatically inherit new ontology semantics.

---

# Nominated later hostile scenarios

Do not execute them in this state.

- two different relation IDs share one label;
- label unchanged while relation meaning changes;
- direct edge confused with transitive closure;
- property-chain result shown as direct source fact;
- same subject/relation/object asserted by different sources with different validity;
- soft constraint treated as logical impossibility;
- domain/range inference treated as input validation;
- functional relation silently merges identities;
- inexact replacement auto-migrated as exact;
- deprecated relation remains active in inference chains;
- old assertions reinterpreted under new relation definition without migration;
- path result loses evidence-bearing supporting edges;
- cyclic traversal runs unbounded;
- close-match mapping treated as exact equivalence;
- derived relation built under ontology V1 replayed under V2 without qualification.

---

## Current task

**No task is currently assigned.**

KA-G2 is complete.

## Planned next candidate

**KA-G3 — Formal Provenance / Evidence Lineage**

Suggested bounded focus:

- W3C PROV Entity/Activity/Agent distinctions;
- generation/use/derivation/attribution/association relationships;
- source evidence versus transformation provenance;
- revision/bundle/collection applicability where useful;
- requirements for ACL/Vera without adopting PROV wholesale.

This candidate is **not authorized merely because it is next**.

## Prohibited work at this state

Do not:

- begin KA-G3 without explicit authorization;
- begin authorization/actionability gap research automatically;
- begin resource/artifact gap research;
- begin privacy/retention gap research;
- begin Home Assistant/Matter operational validation;
- construct the representative retrieval-requirements suite;
- execute hostile/adversarial scenario review;
- synthesize the final conceptual schema;
- select a graph/database/storage engine;
- implement retrieval/context construction;
- create embeddings;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers;
- promote evidence-campaign invariants into final architecture rules.

## Stop point

KA-G1 and KA-G2 are complete. Epistemic/temporal/negative semantics and relationship/ontology semantics now have direct standards evidence. The remaining major gaps are formal provenance, authorization/actionability, resources/artifacts, privacy/retention and non-AI operational-domain validation. No later gap task, retrieval study, hostile review, synthesis, storage selection or implementation has begun.
