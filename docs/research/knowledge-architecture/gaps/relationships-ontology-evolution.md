# Relationships and Ontology Evolution Gap Research

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** KA-G2 — Relationships and Ontology Evolution  
**Research date:** 2026-09-08  
**Starting ACL checkpoint:** `18b571c1000fe9b5fcc5ca01556f52fbb372bf17`  
**Boundary:** research/requirements evidence only; no ontology adoption, RDF/OWL adoption, graph database selection, schema synthesis, storage selection, retrieval implementation, or ACL/Vera implementation decision

---

# Executive assessment

KA-G2 closes a major positive-semantics gap left by the agent-framework campaign: how a general ACL/Vera knowledge substrate should represent **relationships**, how relationship semantics should be governed, how direct and inferred relationships should be retrieved, and how a relationship vocabulary can evolve without silently changing the meaning of historical knowledge.

The strongest conclusion is that a relationship cannot safely be represented as merely:

`subject + string label + object`

A durable relationship system needs to keep several distinct things separate:

1. **relationship type / predicate identity** — the stable semantic concept such as `owns`, `located_at`, `part_of`, `depends_on`, `parent_of`;
2. **relationship-type semantic profile** — direction, inverse, symmetry/asymmetry, transitivity, reflexivity, cardinality/functionality, domain/range, subproperty hierarchy, disjointness, property-chain/inference rules and other governed semantics;
3. **relationship assertion occurrence** — one particular claim/observation that the relationship holds, with its own identity where needed;
4. **qualifiers/applicability** — time, method, role, environment, version, location or other context that changes what the assertion means;
5. **references/evidence** — why that assertion exists;
6. **epistemic/currentness state** — whether it is asserted, inferred, disputed, deprecated, superseded, current, historical, etc.;
7. **derived relationship/path** — connectivity inferred from direct assertions, ontology rules or traversal;
8. **validation constraints** — rules about expected/allowed use that are not necessarily logical truth conditions;
9. **vocabulary/ontology version** — which semantic definition profile was used when the assertion or inference was created.

The evidence therefore supports a conceptual pattern closer to:

`RelationDefinition(versioned) ← RelationAssertionOccurrence → Entities`

with qualifiers/evidence/time on the assertion occurrence and derived path/closure records remaining distinguishable from direct assertions.

This task independently reinforces **KA-I-007**: relationship labels alone are insufficient; governed relation semantics are required when consequences depend on them.

KA-G2 adds two new candidate invariants:

- **KA-I-048** — relationship/predicate semantic identity and an individual relationship-assertion occurrence are distinct; identical subject-predicate-object propositions may have multiple occurrence records because source, qualifiers, time, epistemic basis, rank or validity differ.
- **KA-I-049** — direct/asserted relationships, entailed/derived relationships and graph/path connectivity are distinct retrieval intents; consequential relationship answers must be explainable from the asserted edges plus the inference/vocabulary profile that produced them.

No new failure-pattern ID is added. This is standards/domain evidence rather than a newly observed implementation incident. Existing Graphiti failure **KA-F-005** remains the concrete failure fixture for treating a relationship name plus shared endpoint as sufficient supersession proof.

---

# 1. Task boundary

KA-G2 is the second bounded standards/domain gap task after KA-G1.

## Included

- first-class relationship assertion representation;
- relationship type identity;
- direction/inverse semantics;
- symmetry/asymmetry;
- transitivity and direct-vs-closure distinction;
- functional/cardinality/uniqueness implications where relevant;
- domain/range semantics;
- subproperty and property-chain semantics;
- statement qualifiers and references where they affect relationship meaning;
- validation constraints versus logical inference;
- relationship retrieval/path semantics;
- ontology/vocabulary identifiers and versions;
- deprecation, replacement and migration;
- stable meaning across schema evolution;
- relation vocabulary reuse/interoperability.

## Explicitly excluded

- full W3C PROV modeling;
- ABAC/ReBAC authorization design;
- knowledge actionability/use-purpose policy;
- privacy erasure mechanics;
- content-addressed resource/artifact identity;
- Home Assistant/Matter operational-domain validation;
- representative retrieval test set construction;
- hostile/adversarial scenario execution;
- final conceptual schema synthesis;
- graph/relational/vector database selection;
- implementation.

---

# 2. Primary evidence inspected

## W3C RDF 1.2 Concepts and Abstract Data Model

https://www.w3.org/TR/rdf12-concepts/

Status inspected:

- W3C Candidate Recommendation Snapshot dated 2026-04-07.

Used for:

- RDF triple as proposition;
- asserted versus unasserted proposition;
- triple terms and reifiers;
- multiple distinct reifiers for the same proposition;
- relationship changes over time;
- stable intended IRI referent;
- entailment/profile separation.

Important qualification:

RDF 1.2 is still on the Recommendation track; its reification model is useful current standards direction, not a reason to require RDF as ACL/Vera storage technology.

## W3C OWL 2 Primer / Quick Reference / structural versioning material

https://www.w3.org/TR/owl-primer/  
https://www.w3.org/TR/owl2-quick-reference/

Used for:

- inverse properties;
- symmetric/asymmetric properties;
- functional/inverse-functional properties;
- transitive properties;
- subproperties;
- disjoint properties;
- domain/range;
- property chains;
- ontology version IRI;
- `priorVersion`, `backwardCompatibleWith`, `incompatibleWith`, `deprecated` annotations.

## W3C SKOS Reference

https://www.w3.org/TR/skos-reference/

Used for:

- direct `broader`/`narrower` versus transitive closure properties;
- associative `related` versus hierarchy;
- inverse semantics;
- explicit integrity conditions;
- exact/close/broad/narrow/related mapping distinctions;
- warning against overcommitment;
- domain/range axioms as inference, not validation.

## W3C SHACL

https://www.w3.org/TR/shacl/

Used for:

- property shapes;
- property paths;
- inverse/sequence/alternative/zero-or-more paths;
- cardinality/type/value constraints;
- closed shapes;
- separation of validation from OWL/RDF entailment semantics.

## SPARQL 1.2 Query Language

https://www.w3.org/TR/sparql12-query/

Status inspected:

- W3C Working Draft 2026-08-20.

Used for:

- direct graph patterns;
- inverse/sequence/alternative/arbitrary-length property paths;
- relationship connectivity retrieval;
- distinction between endpoint connectivity and an evidence/explanation path.

Important qualification:

SPARQL 1.2 is a current Working Draft, not a final Recommendation.

## Wikibase / Wikidata data model and property constraints

https://www.mediawiki.org/wiki/Wikibase/DataModel  
https://doc.wikimedia.org/Wikibase/master/php/docs_topics_json.html  
https://www.wikidata.org/wiki/Help:Property_constraints_portal  
https://www.wikidata.org/wiki/Help:Statements/en  
https://www.wikidata.org/wiki/Help:Qualifier

Used for:

- stable Property identity independent of labels;
- property direction meaning;
- statement occurrence identity/GUID;
- main claim versus qualifiers versus references versus rank;
- multiple statements for one property;
- contextual/time qualifiers;
- property value/subject type constraints;
- single/multiple/unique constraints;
- symmetric and inverse constraints;
- allowed/required qualifier constraints;
- constraints as guidance with exceptions rather than universal logical truth;
- schema evolution example where property datatype can change before all historical stored values can be migrated.

## OBO Foundry

https://obofoundry.org/principles/fp-007-relations.html  
https://obofoundry.org/principles/fp-019-term-stability.html  
https://obofoundry.org/id-policy.html

Used for:

- relation vocabulary reuse;
- stable relation PURLs/identifiers;
- relation subproperty alignment;
- property-chain governance;
- term/relation meaning stability;
- meaning-changing revisions require a new identifier;
- deprecation rather than identifier reuse;
- exact replacement versus `consider` alternatives;
- removing/replacing logical uses of obsolete terms;
- stable release/version artifacts.

---

# 3. Relationship type identity is not a label

## Observed behavior

Wikibase treats Properties as first-class Entities with stable identifiers. Its own documentation explicitly notes that seemingly similar natural-language concepts may represent different relationships: `parent of` and `has parent` have different meanings and directions.

OBO similarly requires relation reuse by stable relation PURL/IRI rather than re-declaring an equivalent relation under another local label.

SKOS and OWL define relation semantics by property identity plus axioms, not display label.

## Architectural lesson

A relationship type needs stable semantic identity independent of:

- UI label;
- synonym/alias;
- localization;
- storage column name;
- model-generated wording;
- query-time human paraphrase.

For Vera, these may all describe different things:

- `owns`
- `owned_by`
- `has_custody_of`
- `assigned_to`
- `uses`
- `located_at`
- `observed_at`

Natural-language similarity must not collapse them.

## Confidence

High.

## Non-conclusion

This does not require globally standardized public IRIs for every private Vera relation. It requires stable governed identity and explicit mapping/extension rules.

---

# 4. Governed relation semantics are behavior-bearing

OWL provides explicit semantics for properties including:

- inverse;
- symmetric;
- asymmetric;
- reflexive;
- irreflexive;
- functional;
- inverse-functional;
- transitive;
- subproperty;
- disjointness;
- domain;
- range;
- property chains.

These are not cosmetic metadata.

They change what can be inferred.

Examples:

- declaring `hasParent` inverse of `hasChild` means one assertion can entail another directional assertion;
- declaring `hasSpouse` symmetric entails the reverse relation;
- declaring `hasAncestor` transitive entails longer-range ancestry;
- a property chain can derive `hasGrandparent` from two `hasParent` edges;
- functional/inverse-functional semantics can lead to entity-identity consequences;
- domain/range can entail class membership.

## Architectural lesson

Where ACL/Vera uses relation semantics for reasoning, retrieval or consequential decisions, the realized semantic profile must be identifiable.

A relation definition is therefore not only:

`id + label`

but potentially includes governed semantics such as:

- direction;
- inverse relation ID;
- symmetric/asymmetric;
- transitive/non-transitive;
- reflexive/irreflexive;
- direct-only versus closure semantics;
- functional/cardinality expectations;
- domain/range classes;
- parent/subproperty relations;
- chain/inference rules;
- disjoint/conflict relations;
- version/status.

Not every relation needs every field. The requirement is that semantics which affect inference are explicit rather than hidden in code or labels.

## Why this matters to Vera

Suppose Vera stores:

`BatterySensor7 located_in Garage`

If `located_in` is later redefined to mean “physically installed in” rather than “currently detected in,” historical assertions cannot silently inherit that new meaning.

Likewise:

`Laptop connected_to Router`

must not become transitive by default and imply:

`Laptop connected_to InternetService`

unless the governed semantics say that inference is valid.

---

# 5. Domain/range semantics are not ordinary type validation

## Observed behavior

SKOS explicitly explains that OWL domain/range statements give **license to inference**.

If `skos:semanticRelation` has domain and range `skos:Concept`, then asserting:

`A semanticRelation B`

entails that A and B are concepts.

This differs from saying:

“reject the relation unless A and B are already known to be concepts.”

SHACL, by contrast, provides an explicit validation model in which shapes constrain nodes/paths and produce validation results.

Wikidata property constraints similarly describe expected property use, but explicitly say constraints are hints/guidance and can have exceptions.

## Architectural lesson

ACL/Vera must distinguish at least:

1. **semantic/inference rule** — if relationship R holds, infer X;
2. **hard validation rule** — relationship occurrence is invalid unless X;
3. **soft quality expectation** — relationship usually has X, but exceptions are legal;
4. **UI/editor suggestion** — propose a field/qualifier/value;
5. **policy/security eligibility** — outside ontology semantics entirely.

Collapsing all five into “constraint” creates unsafe reasoning.

## Example

A rule:

`head_of_government → value type Human`

may be an editorial expectation with exceptions, not a law of reality.

Vera should not delete or deny a source claim solely because a soft ontology quality rule is violated.

---

# 6. Direct relationships and transitive closure are different knowledge

## Observed behavior

SKOS deliberately separates:

- `skos:broader` — direct/immediate hierarchical link;
- `skos:broaderTransitive` — transitive hierarchy closure.

`broader` is a subproperty of `broaderTransitive`, but direct edges are not themselves defined as universally transitive.

This allows a system to distinguish:

`Dog broader Mammal` directly

from

`Dog broaderTransitive Animal` through a longer chain.

OWL separately supports transitive properties and property chains.

## Architectural lesson

ACL/Vera retrieval must distinguish:

- direct assertion;
- inferred inverse;
- transitive closure;
- property-chain derivation;
- generic path connectivity.

These are different answer types.

A query like:

> “What is this device directly connected to?”

must not return all reachable network nodes.

A query like:

> “What systems depend on this service?”

may intentionally ask for transitive closure.

The intent must be explicit.

---

# 7. Relationship assertion occurrence identity is distinct from the proposition

## RDF 1.2 evidence

RDF 1.2 introduces triple terms and reifiers.

A triple term denotes an abstract proposition.

A reifier can denote a statement, belief, situation or other occurrence related to that proposition.

The specification explicitly allows **multiple distinct reifiers for the same proposition**, such as claims from different sources or situations with different characteristics.

It also allows a proposition to be reified without asserting that the proposition is true.

## Wikibase evidence

A Wikibase Statement has its own statement identifier/GUID and contains:

- main property/value;
- qualifiers;
- references;
- rank.

Multiple Statements for the same property/value can exist in a repository.

## Architectural lesson

The abstract proposition:

`Alice works_for Acme`

is not necessarily the same record as:

- Bob said Alice works for Acme;
- HR system asserted Alice works for Acme;
- badge system inferred Alice works for Acme;
- Vera inferred Alice works for Acme;
- an old source asserted Alice worked for Acme during 2025.

Identical subject/predicate/object should therefore not force occurrence identity collapse.

This produces **KA-I-048**.

---

# 8. Qualifiers can be part of statement meaning

## Observed behavior

Wikibase describes qualifiers as additional property/value pairs that refine a statement.

Examples include:

- start/end time;
- method;
- role/character;
- percentage;
- scope exceptions.

The Wikibase primer explicitly notes that removing a qualifier can change the meaning of a statement.

Wikidata property constraints can specify allowed or required qualifiers.

## Architectural lesson

Relationship applicability must not be relegated to opaque metadata when it materially changes meaning.

For Vera, these are distinct assertions:

`Floyd works_at Portal-A [valid 2026-01..2026-08]`

`Floyd works_at Portal-B [valid 2026-09..]`

Likewise:

`DeviceX connected_to NetworkY [method=wifi]`

and

`DeviceX connected_to NetworkY [method=ethernet]`

may matter differently to diagnostics and automation.

The conceptual model should support structured qualifiers/applicability without forcing every conceivable context field into the core schema.

This reinforces KA-I-022.

---

# 9. References, qualifiers and rank are separate dimensions

Wikibase maintains:

- qualifiers — contextualize the assertion;
- references — source/evidence records;
- rank — preferred/normal/deprecated selection aid.

These dimensions are not interchangeable.

Architecture consequence:

- a source does not define validity interval;
- a validity interval does not define source trust;
- preferred/default rank does not prove truth;
- deprecated/currentness state is not deletion;
- inference status is separate from source reference.

This is consistent with KA-G1's epistemic result and reinforces KA-I-025.

---

# 10. Relationship constraints should themselves be governable/versioned

Wikidata models property constraints as statements on properties.

Constraints include:

- single/multi value;
- distinct value;
- subject/value type;
- allowed values;
- required/allowed qualifiers;
- symmetric relation expectations;
- inverse relationship expectations;
- citation-needed;
- recency/contemporary constraints;
- conflicts-with and other quality rules.

Some constraints can have exceptions and are not hard restrictions.

## Architectural lesson

A relation vocabulary can expose a **constraint profile** separate from semantic inference axioms.

That profile needs:

- constraint identity/type;
- severity or hard/soft status;
- scope;
- exceptions if supported;
- vocabulary version;
- validation result provenance.

ACL/Vera should avoid baking all relationship rules into application code because then changing a rule becomes invisible semantic drift.

---

# 11. Relationship vocabulary reuse improves interoperability

OBO Foundry's relation principle requires reuse of existing governed relation identifiers where appropriate and recommends submitting generally useful new relations to a shared Relations Ontology.

Its purpose is explicitly interoperability and logical inference: different ontologies cannot reliably detect inconsistency or infer across data when each invents a differently identified relation for the same meaning.

## Architectural lesson

Vera does not need to adopt OBO relations, but it should learn the governance principle:

- use one canonical relation identifier for one intended meaning within a governed scope;
- map aliases/paraphrases to that identifier;
- if a local specialization exists, link it to a broader governed relation where useful;
- keep vocabulary extension explicit;
- do not create a new relation merely because an LLM used a new phrase.

This independently reinforces **KA-I-007**.

---

# 12. A controlled vocabulary must still allow extension

SKOS explicitly warns against overcommitment and omits some constraints when general use cases vary.

OBO supports new local relations where existing ones are not appropriate, with alignment to super-properties where possible.

Wikidata permits flexible property use plus constraints/guidance rather than enforcing every semantic expectation in the base data model.

## Architectural lesson

“Governed relationship vocabulary” must not mean a frozen universal ontology.

The likely requirement is:

- small governed core;
- explicit extension mechanism;
- stable identifiers;
- documented definitions;
- optional parent/subproperty alignment;
- version/deprecation lifecycle;
- application/domain scopes.

This is compatible with Vera spanning people, devices, software, work, family, research and future domains.

---

# 13. Mapping relations must not be flattened to one equivalence concept

SKOS distinguishes:

- `exactMatch`;
- `closeMatch`;
- `broadMatch`;
- `narrowMatch`;
- `relatedMatch`.

It also defines integrity conditions: `exactMatch` is disjoint with broader/narrower and associative mapping relations.

## Architectural lesson

Cross-vocabulary mappings need their own semantics.

“Same,” “roughly equivalent,” “broader,” “narrower” and “related” are materially different.

For ACL/Vera schema evolution this matters when importing or aligning:

- external device types;
- third-party tool capabilities;
- project vocabularies;
- people/contact identities;
- research taxonomy terms.

A fuzzy mapping should not be promoted to exact equivalence merely to simplify retrieval.

---

# 14. Functional and inverse-functional semantics can become identity operations

OWL shows that functional/inverse-functional properties can force equality inferences.

For example, two values through a functional property may imply that the two supposedly different individuals are actually the same.

## Architectural lesson

Any relation semantic capable of creating identity merge implications is high risk for Vera.

This reinforces why:

- identity resolution must remain explicit/auditable;
- relational cardinality cannot silently merge entities;
- validation cardinality and logical functionality should be distinguished;
- KA-I-004 remains important.

KA-G2 does **not** promote KA-I-004 to reinforced because the standards show the hazard but do not provide an independently demonstrated reversible merge/split mechanism.

---

# 15. Property-chain inference is derived knowledge

OWL property chains can derive a relationship from an ordered chain of other properties.

Example conceptually:

`hasParent ∘ hasParent → hasGrandparent`

## Architectural lesson

A relationship produced by a property chain is not the same evidence object as the direct edges that support it.

If Vera concludes:

`ServiceA indirectly_depends_on DatabaseC`

from:

`ServiceA depends_on ServiceB`

and

`ServiceB depends_on DatabaseC`

then the derived relation should remain traceable to those asserted edges and to the inference profile/version.

This reinforces KA-I-030 and contributes to new KA-I-049.

---

# 16. Relationship retrieval has at least four intents

Standards evidence supports separating:

## Direct assertion retrieval

“What relationships are explicitly asserted between A and B?”

## Inference-aware retrieval

“What relationships are entailed under semantic profile V?”

## Connectivity/path retrieval

“Can A reach B through allowed relation/path patterns?”

## Explanation/evidence retrieval

“Which asserted relationships, qualifiers and inference rules justify that derived relationship/path?”

These intents cannot safely share one opaque `graph_search()` result.

---

# 17. Property-path result is not derivation provenance

SPARQL property paths provide compact graph traversal including:

- inverse paths;
- sequence paths;
- alternatives;
- zero/one/many repetitions.

They are excellent evidence that graph-shaped retrieval needs path semantics.

But endpoint connectivity does not automatically provide a first-class derivation record explaining:

- which exact direct assertions were chosen;
- which source/evidence supported each assertion;
- which ontology version defined each predicate;
- which inference rules were applied;
- whether alternate paths also existed.

## Architectural lesson

For low-risk discovery, endpoint connectivity may be sufficient.

For consequential reasoning, Vera must be able to reconstruct/expose the actual supporting assertion chain and semantic profile.

This is **KA-I-049**.

---

# 18. Cycles and arbitrary-length traversal are expected

SPARQL property paths explicitly allow arbitrary-length traversal and cycles.

Graph relationship retrieval therefore needs bounded intent and traversal governance.

Possible later retrieval requirements should test:

- max depth;
- allowed relation types;
- direct versus closure;
- cycle handling;
- duplicate path handling;
- current/historical filtering;
- permission filtering;
- provenance/explanation output.

This is a retrieval-requirements concern, not a storage-engine selection decision.

---

# 19. Relation identifiers should preserve intended meaning over time

RDF 1.2 states that an IRI, once minted, should not change its intended referent.

OBO Foundry's term-stability principle makes the same operational requirement stronger:

- if a definition change substantially changes the referents, create a new term with a new IRI;
- mark the old term obsolete/deprecated;
- provide replacement/consider guidance where appropriate.

## Architectural lesson

A relationship identifier such as:

`located_at`

cannot safely change from:

“current physical location”

to:

“assigned/home location”

while reusing the same semantic identifier.

That would silently reinterpret all historical records.

This strongly reinforces KA-I-017.

---

# 20. Deprecation is not deletion

OBO term-stability guidance retains obsolete terms and definitions for history/compatibility while removing their active logical axioms.

It supports:

- exact `replaced_by` replacement;
- inexact `consider` alternatives;
- explicit obsolescence reasons.

OWL provides `owl:deprecated` and ontology-version annotations.

## Architectural lesson

A relationship type lifecycle needs more than `active=true/false`.

Useful states include:

- active/current;
- deprecated but readable;
- exact replacement available;
- inexact alternatives only;
- incompatible semantic revision;
- retired with no replacement.

Historical assertions may still need the deprecated definition to explain old records.

---

# 21. Deprecating a vocabulary term requires data/axiom migration decisions

OBO explicitly requires removing/replacing logical uses of obsolete terms elsewhere in the ontology.

Example:

if `A part_of B` and B is deprecated/replaced, active logical axioms using B must be repaired rather than simply leaving the deprecated term active inside reasoning chains.

## Architectural lesson

Changing the vocabulary is a **semantic migration**, not a documentation edit.

For Vera:

1. mark old relation definition deprecated;
2. determine exact/inexact replacement;
3. identify affected assertions, rules, derived indexes and saved queries;
4. decide whether each historical assertion should remain under old semantics or be migrated;
5. create explicit migration/re-derivation events;
6. rebuild derived projections under the new profile;
7. preserve auditability.

This is existing KA-I-017 applied concretely to relationship vocabularies.

---

# 22. Exact replacement and inexact replacement are different

OBO separates:

- exact `replaced_by`;
- inexact `consider` candidate(s).

## Architectural lesson

A schema migration must not automatically rewrite old relationship types when replacement is only approximate.

Example:

old `member_of`

may be split into:

- `employee_of`;
- `contractor_for`;
- `volunteer_for`.

There is no safe one-to-one automatic rewrite without additional evidence.

The migration state should be able to say:

`deprecated relation; requires reclassification`

rather than forcing a guess.

This mirrors identity ambiguity rules from KA-I-005.

---

# 23. Ontology versions are first-class semantic profile identity

OWL supports ontology version IRIs and annotations for:

- prior version;
- backward compatibility;
- incompatibility;
- version information.

OBO publishes stable current ontology identifiers plus separately addressable dated versions.

## Architectural lesson

The knowledge system should be able to identify which vocabulary/ontology profile an assertion or derived result was interpreted under.

At minimum, behavior-bearing relation definitions need a version/generation identity when semantic evolution is possible.

A historical derived fact should not be assumed reproducible under today's relation profile.

This reinforces KA-I-017, KA-I-018 and KA-I-023.

---

# 24. Backward compatibility must be explicit, not assumed

OWL versioning guidance distinguishes compatible and incompatible ontology versions.

Older OWL guidance explicitly says compatibility should not be assumed merely because no incompatibility is declared.

## Architectural lesson

When Vera upgrades a relationship vocabulary, the migration system should classify the transition, e.g.:

- label/documentation-only compatible;
- additive compatible;
- inference-expanding;
- inference-reducing;
- meaning-changing/incompatible;
- replacement/split/merge requiring migration.

This is a future synthesis requirement, not a decision to use OWL's exact vocabulary.

---

# 25. Property datatype/schema change demonstrates delayed migration reality

Wikibase's data model explicitly notes that a Property datatype may change while previously stored values remain encoded under the earlier datatype because it may be impractical to update all stored data immediately.

## Architectural lesson

Schema version and record interpretation version can temporarily diverge.

Therefore:

- readers must know which historical representation they are decoding;
- migration completeness should be observable;
- old data must not be silently reinterpreted as if written under the new schema;
- validation errors during migration do not necessarily mean the historical record was invalid when written.

This reinforces KA-I-017 and KA-I-039 adjacent concerns.

It does not independently reinforce KA-I-039 enough to change its status because the Wikibase evidence concerns schema migration tolerance rather than behavior-bearing serialization round-trip fidelity.

---

# 26. Same-label relation collisions are an interoperability failure risk

OBO automatically flags a locally minted relation when its label exactly matches an existing shared Relation Ontology relation but uses a different identifier.

The rationale is that identical-looking local relations break cross-ontology inference/interoperability.

## Architectural lesson

For Vera's internal vocabulary:

- relation labels are not identifiers;
- duplicate labels require disambiguation;
- model-generated aliases should map to canonical IDs;
- imported relation types need explicit mapping rather than copy-by-label.

This independently reinforces KA-I-007.

---

# 27. Relation inference profile must be visible to downstream reasoning

RDF 1.2 explicitly describes entailment regimes as specifications that define what additional information follows from a graph, and notes implementations may expose all, some or none of that entailed information.

## Architectural lesson

A query result should not merely say:

`A related_to C`

if that result exists only under a particular inference profile.

Where relevant, context/retrieval should carry:

- asserted versus derived;
- inference profile/version;
- derivation path or derivation identifier;
- validity/applicability;
- source assertion IDs.

Otherwise two backends with different inference support may return semantically different answers under the same high-level query.

This reinforces KA-I-012 and KA-I-018.

---

# 28. Relationship constraints may have exceptions

Wikidata explicitly states that property constraints are guidance and can have exceptions.

This is valuable because real-world data frequently violates neat ontological expectations without making the observation false.

## Example

A constraint may say:

`head_of_government value should be Human`

but an honorary office holder may violate that expectation.

## Architectural lesson

Validation result should support states such as:

- pass;
- warning;
- violation requiring review;
- exception/waiver;
- hard invalid.

The ontology layer should not automatically delete contradictory-but-sourced observations to restore schema cleanliness.

---

# 29. Relationship semantics and authority remain separate

Nothing in RDF, OWL, SKOS, Wikibase, SHACL or OBO turns a relationship into execution authority.

Knowing:

`Floyd owns Highlander`

may help identify a relevant vehicle.

It does not authorize:

`remote_start(Highlander)`.

Likewise:

`DeviceX controls DoorLock`

is knowledge about a capability relationship, not permission to invoke it.

KA-G2 therefore reinforces but does not modify KA-I-020.

---

# 30. Proposed ACL/Vera relationship semantic envelope

This is a **requirements envelope**, not a final schema.

A future relationship definition probably needs to be able to express or reference:

## Relation definition identity

- stable relation ID;
- display label(s)/aliases;
- definition;
- vocabulary/domain owner;
- version/generation;
- active/deprecated status;
- replacement/consider links.

## Semantic characteristics where applicable

- directed/undirected semantics;
- inverse relation;
- symmetric/asymmetric;
- reflexive/irreflexive;
- transitive/direct-only;
- functional/cardinality semantics;
- subject/domain expectations;
- object/range expectations;
- parent/subproperty;
- disjoint relations;
- property-chain/inference rules.

## Validation profile

- hard/soft constraint identity;
- allowed/required qualifiers;
- expected cardinality;
- subject/value type expectations;
- exception mechanism;
- severity.

## Assertion occurrence

- assertion/occurrence ID;
- subject entity ID;
- relation definition ID/version;
- object/value ID;
- qualifiers/applicability;
- valid time;
- epistemic basis/status;
- references/evidence;
- record/system time;
- supersession/deprecation state.

## Derivation

- direct/asserted versus inferred;
- derivation/inference profile;
- supporting assertion IDs/path;
- generation/revision identity.

Not every implementation will store these in one table or object.

The requirement is conceptual separability.

---

# 31. Candidate invariant update

## KA-I-007 — candidate → reinforced

Existing wording:

> Relationship labels alone are insufficient for safe replacement reasoning; governed relationship semantics are required where consequences depend on them.

Independent KA-G2 evidence:

- OWL property characteristics and chains change entailment;
- SKOS separates direct hierarchy, transitive closure, associative and mapping relations;
- Wikidata Property identity/constraints distinguish direction, inverse, symmetry, qualifiers and value types;
- OBO requires relation-IRI reuse for interoperability and monitors relation evolution.

Status becomes **reinforced**.

## KA-I-048 — new candidate

> Relationship/predicate semantic identity is distinct from an individual relationship-assertion occurrence; identical subject-predicate-object propositions may require multiple separately addressable assertion occurrences because evidence source, qualifiers, valid time, epistemic basis, rank/currentness or situation differ.

Evidence:

- RDF 1.2 multiple distinct reifiers for the same proposition;
- Wikibase Statements have individual IDs plus qualifiers/references/rank;
- adjacent recurrence from Graphiti fact edges and Agno relationship IDs.

Status: **candidate** because this is the first bounded task to formulate the invariant explicitly.

## KA-I-049 — new candidate

> Direct/asserted relationships, entailed/derived relationships and path/connectivity results are distinct retrieval intents; when a relationship result may influence consequential reasoning, the system must be able to reconstruct the supporting asserted edges plus the inference/vocabulary profile that produced the derived relationship or path.

Evidence:

- SKOS `broader` vs `broaderTransitive`;
- OWL transitivity/property chains/inverses;
- SPARQL property-path endpoint traversal;
- RDF entailment-profile distinction.

Status: **candidate**.

---

# 32. Existing invariant recurrence

KA-G2 strongly reinforces existing reasoning for:

- **KA-I-002** — semantic entity/relation identity distinct from external labels/locators;
- **KA-I-005** — ambiguous mapping/replacement should remain unresolved when exact replacement cannot be established;
- **KA-I-006** — supersession/deprecation is provenance-bearing and non-destructive;
- **KA-I-008** — relationships can hold at one time and not another;
- **KA-I-009** — direct/current/historical/conflict retrieval differ;
- **KA-I-012** — backend/query inference behavior must be qualified;
- **KA-I-017** — ontology changes require explicit migration/re-derivation;
- **KA-I-018** — realized semantic behavior includes schema/ontology/inference profile;
- **KA-I-022** — relationship applicability requires structured scope/qualifiers;
- **KA-I-023** — derivation/migration/inference decisions need provenance;
- **KA-I-025** — epistemic basis is separate from relationship occurrence/rank/source;
- **KA-I-030** — derived graph relationships are distinct from canonical assertions.

No status change is required for those already reinforced invariants.

---

# 33. Failure-ledger disposition

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID is created.

Reason:

- KA-G2 is standards/domain evidence;
- ontology inconsistencies and validation examples are not implementation incidents;
- the failure ledger intentionally requires observed project failures/reproductions rather than encoding every standards warning as a failure ID.

Existing concrete failure **KA-F-005** remains highly relevant:

> Relationship name + shared endpoint treated as sufficient proof of supersession.

KA-G2 provides independent semantic justification for why that failure class is dangerous, but does not change its `observed` status because it does not add a second concrete implementation incident.

---

# 34. Twenty-six-question impact

KA-G2 primarily improves evidence questions:

## 7. Relationships

Previously under-specified positive semantics.

Now materially stronger:

- first-class relation identity;
- relation semantic profiles;
- individual assertion occurrence identity;
- qualifiers/time/evidence;
- direct versus inferred distinction;
- vocabulary governance/versioning.

## 14. Relationship retrieval

Now materially stronger:

- direct edge retrieval;
- inference-aware retrieval;
- arbitrary path/connectivity retrieval;
- explanation/evidence path retrieval;
- inference-profile identity.

## 23. Schema/version evolution

Now materially stronger:

- ontology version identity;
- stable term meaning;
- deprecation/replacement;
- incompatible/compatible version concepts;
- explicit migration of obsolete logical uses;
- delayed migration tolerance.

## 26. Scope of truth

Improved but still requires non-AI operational-domain validation.

Relationship applicability can carry structured qualifiers/time, but Home Assistant/Matter-style real-world state/capability testing is still necessary.

## Adjacent improvements

- 3 provenance — statement occurrence and derivation identity improved, but formal PROV research still needed;
- 5 temporal truth — relationships explicitly may change over time;
- 6 conflict/supersession — vocabulary deprecation/replacement improved;
- 12 canonical-vs-derived — direct assertion vs inferred closure/path sharpened;
- 17 composite retrieval — relation profile/path/inference filters become clearer;
- 21 derived-state integrity — inference/vocabulary profile must remain traceable.

---

# 35. Requirements that should survive into synthesis

Without choosing implementation technology, KA-G2 supports the following requirements:

1. Relationship types have stable semantic identity independent of labels.
2. Relation definitions may have behavior-bearing semantics; such semantics must be explicit/versioned when used.
3. Relation assertions can have first-class occurrence identity separate from the abstract proposition.
4. Qualifiers/applicability can be part of relationship meaning.
5. References/evidence remain separate from qualifiers/currentness.
6. Direct assertions and inferred relationships remain distinguishable.
7. Derived path answers can be traced back to asserted edges and inference profile when consequential.
8. Validation constraints and logical inference rules remain different layers.
9. Soft constraints can have exceptions and do not automatically negate observations.
10. Vocabulary labels are not canonical IDs.
11. Controlled vocabularies should be extensible rather than frozen.
12. Exact and inexact cross-vocabulary mappings remain different.
13. Meaning-changing vocabulary edits require new identifiers or explicit semantic migration rather than in-place reinterpretation.
14. Deprecated relation definitions remain historically addressable where retention permits.
15. Exact replacement and candidate/approximate replacement remain distinct.
16. Relation-vocabulary version/profile belongs in derivation/reproducibility identity where inference behavior matters.
17. Existing historical assertions do not automatically inherit new ontology semantics.

---

# 36. Non-conclusions

KA-G2 does **not** conclude that ACL/Vera should:

- use RDF as physical storage;
- use OWL as the canonical ontology language;
- use SPARQL as the application query language;
- use Wikibase;
- use OBO Relation Ontology;
- use a graph database;
- make every relation fully formal/logical;
- expose arbitrary ontology inference to an LLM;
- enforce all constraints as hard rules;
- infer permissions from relationships;
- build a universal ontology before prototyping.

The value of these sources is semantic discipline and failure avoidance, not technology adoption.

---

# 37. Hostile scenarios nominated for later review

Do not execute them in this task. Preserve them for the campaign's later hostile-review phase.

1. Two different relation IDs share the same display label.
2. A relation label stays the same while its definition changes materially.
3. A direct `part_of` edge is confused with transitive closure.
4. A property chain produces a derived relationship that is exposed as a direct source fact.
5. Two different sources assert the same subject/relation/object with different validity intervals.
6. Two sources assert the same relation but one is disputed and one verified.
7. A soft validation constraint is treated as a logical impossibility.
8. An OWL-style domain/range inference is treated as an input validation rule.
9. A functional relation silently merges two identities.
10. A deprecated relation has only an inexact replacement but migration rewrites it automatically.
11. An obsolete relation remains in active inference chains after deprecation.
12. Historical assertions are reinterpreted under a new relation definition without migration.
13. A path query returns connectivity but loses which evidence-bearing edges support the path.
14. A cyclic graph causes unbounded relationship traversal.
15. A cross-vocabulary `closeMatch` is treated as exact equivalence.
16. A relation's inverse changes across ontology versions.
17. A derived relationship was generated under ontology V1 but replay uses V2.
18. A historical property value fails today's datatype/constraint profile and is incorrectly treated as historically invalid.

---

# 38. Recommended next gap boundary

The next candidate in the campaign gap map is:

**KA-G3 — Formal Provenance / Evidence Lineage**

Suggested bounded focus:

- W3C PROV entity/activity/agent distinctions;
- derivation/generation/use/attribution relationships;
- source evidence versus transformation provenance;
- collection/bundle/revision applicability where useful;
- mapping provenance semantics into ACL/Vera requirements without adopting PROV wholesale.

This task is **not authorized automatically** by completion of KA-G2.

---

# 39. Stop point

KA-G2 relationship/ontology gap research is complete when this report, cumulative invariants and campaign state are committed atomically.

Stop before:

- formal provenance gap research;
- ABAC/ReBAC/actionability research;
- resources/artifacts research;
- privacy/retention research;
- Home Assistant/Matter validation;
- retrieval-question construction;
- hostile-scenario execution;
- final architecture synthesis;
- storage selection;
- implementation.
