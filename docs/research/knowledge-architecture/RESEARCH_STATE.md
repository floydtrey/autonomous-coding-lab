# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** project revisits, coverage scan, promoted Agno revisit, all seven bounded standards/domain gap tasks, representative retrieval requirements, hostile/adversarial review, and conceptual architecture synthesis complete; stopped before the hand-authored cross-domain prototype  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

---

# Scope lock

The campaign remains **requirements/architecture validation only** until the prototype gate is complete.

The user explicitly requested scope-drift protection before KA-G3. That remains controlling.

Do **not**:

- restart broad research without a concrete uncovered evidence gap;
- reopen completed project/domain revisits merely because an implementation choice is difficult;
- select PostgreSQL, Neo4j, RDF, a vector store, object store, graph database, policy engine, or other physical storage/implementation technology before the prototype gate;
- implement a knowledge/resource store;
- implement retrieval/context construction;
- create embeddings;
- implement ACL or Vera;
- run autonomous workers;
- weaken the synthesis or acceptance requirements to fit a preferred technology;
- treat the conceptual primitive names as database tables before the prototype validates them.

The campaign remains governed by `CAMPAIGN_PLAN.md`.

---

# Completed campaign work

## Project evidence

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
11. **Bounded post-revisit coverage scan** — complete
12. **KA-11 — Agno Knowledge-Architecture Revisit** — complete

## Standards/domain gaps

13. **KA-G1 — Epistemic, Temporal, Conflict and Negative-Knowledge Semantics** — complete
14. **KA-G2 — Relationships and Ontology Evolution** — complete
15. **KA-G3 — Formal Provenance / Evidence Lineage** — complete
16. **KA-G4 — Knowledge Authorization + Actionability / Use-Purpose** — complete
17. **KA-G5 — Resource / Artifact Identity and Lineage** — complete
18. **KA-G6 — Privacy Deletion / Retention / Erasure Reconciliation** — complete
19. **KA-G7 — Non-AI Operational-Domain Validation (Home Assistant / Matter-style)** — complete

## Pre-build validation/design gates

20. **Representative Retrieval Requirements** — complete
21. **Hostile / Adversarial Scenario Review** — complete
22. **Conceptual Architecture Synthesis** — complete

---

# Detailed artifacts

Project revisits live under `projects/`.

Gap reports live under `gaps/`.

Coverage scan:

- `COVERAGE_SCAN.md`

Cumulative evidence ledgers:

- `invariants.md`
- `failure-patterns.md`

Retrieval acceptance set:

- `REPRESENTATIVE_RETRIEVAL_REQUIREMENTS.md`

Hostile/adversarial review:

- `HOSTILE_ADVERSARIAL_SCENARIOS.md`

Conceptual synthesis:

- `CONCEPTUAL_ARCHITECTURE_SYNTHESIS.md`

Detailed evidence remains in the dedicated reports. This file is the compact current checkpoint.

---

# Conceptual Architecture Synthesis verification and boundary

User authorization:

- after the hostile/adversarial review, the user explicitly instructed `continue`;
- the documented next candidate was Conceptual Architecture Synthesis;
- this authorized synthesis only.

Starting branch/head:

`3c50071fe8b883624b356557be6e2f16783b879d`

Starting commit message:

`research: complete hostile adversarial scenario review`

The synthesis was bounded to:

- converting accumulated evidence into a minimal technology-neutral conceptual model;
- resolving candidate primitive overlap;
- defining canonical-versus-derived boundaries;
- defining temporal, epistemic, identity, relationship, provenance and resource semantics;
- defining interfaces between Knowledge, Authority and Execution;
- preserving domain-profile extensibility;
- mapping the 52 retrieval requirements and nine hostile seams into the model;
- defining prototype acceptance rules.

Explicitly excluded:

- physical schema design;
- SQL/graph/RDF/vector/object-store selection;
- implementation;
- embeddings;
- policy-engine implementation;
- retrieval implementation;
- prototype execution itself.

---

# Synthesis result

The synthesis selects six **conceptual primitive families**:

1. **ENTITY** — persistent semantic thing with stable internal identity.
2. **ASSERTION** — provenance-bearing proposition, including facts, preferences, state claims, relationships, negative assertions and inferred conclusions.
3. **OCCURRENCE** — bounded event/observation/activity/operation with occurrence identity and time.
4. **RESOURCE** — logical information/artifact identity distinct from locator and exact observed representation/version.
5. **EVIDENCE / PROVENANCE LINK** — typed lineage/attribution/support relationships across entities, assertions, resources and occurrences.
6. **SEMANTIC PROFILE / VOCABULARY DEFINITION** — versioned definitions governing predicates, kinds, inference/applicability semantics and domain extensions.

The synthesis keeps the following outside the canonical knowledge core:

- **AUTHORITY / POLICY**
- **EFFECT / EXECUTION LEDGER**
- **DERIVED RETRIEVAL PROJECTIONS**
- **CONTEXT CONSTRUCTION**

Core governing separation:

> **Knowledge does not grant authority. Authority does not prove execution. Execution acknowledgement does not prove world settlement.**

---

# Important synthesis decisions

## Assertion unifies several earlier candidate classes

The model does **not** require separate universal primitives for Fact, Preference, State or Relationship.

Those are represented as typed ASSERTIONs with different semantic/profile metadata.

Relationship semantics remain governed by versioned predicate definitions, while each relationship assertion occurrence retains its own provenance/time/evidence.

## Observation is composition, not a separate universal storage universe

A direct observation is modeled as:

`OCCURRENCE + one or more grounded ASSERTIONs`

Derived current state is a projection over assertions/observations under freshness, conflict and applicability rules.

## Memory is not a canonical primitive

Conversation memory, summaries, vector memory and similar mechanisms are source/derived/projection concepts built on the canonical substrate.

## Domain concepts remain profiles

Home Assistant entities, Matter endpoints, Git commits, GitHub issues, ACL workers, mine portals and other domain objects map into the universal concepts rather than becoming universal core primitives.

## Physical storage remains undecided

The primitive names above are semantic roles, **not database tables**.

---

# Nine hostile seams disposition

All nine hostile-review seams have an explicit place in the synthesized model:

1. identity transitions -> ENTITY + explicit transition OCCURRENCE/provenance;
2. world-time vs knowledge-time -> ASSERTION/OCCURRENCE temporal axes;
3. negative completeness -> ASSERTION epistemic state + completeness evidence;
4. retrieved content vs instruction -> provenance/content typing + Authority boundary;
5. authorization obligations/freshness -> external Authority decision context;
6. target-set/effect settlement -> operation OCCURRENCE + external Effect Ledger;
7. conflict preservation -> retained competing assertion occurrences + context requirements;
8. derivative sensitivity/erasure -> lineage + derived generation + reconciliation;
9. domain profiles -> SEMANTIC PROFILE / VOCABULARY.

No seam requires another broad research pass before the prototype.

---

# Retrieval-requirements disposition

All **52 representative retrieval requirements** map to the six primitive families plus the Authority/Effect/Derived/Context interfaces.

No requirement currently forces a seventh universal primitive family.

This mapping remains a synthesis hypothesis until validated by the hand-authored prototype.

---

# Cumulative ledger disposition

Evidence ledger IDs remain:

- **KA-I-001 through KA-I-049**
- **KA-F-001 through KA-F-049**

The evidence ledgers are intentionally not rewritten into “final” status during synthesis. They remain provenance-bearing records of how the architecture was derived.

The synthesized architecture is the current architecture candidate; the prototype is the falsification gate before physical design.

---

# Final prototype acceptance rules

The hand-authored prototype must demonstrate at least:

1. same-name people without forced merge;
2. auditable/reversible identity transition;
3. world truth at T versus historical belief at T;
4. late correction without rewriting knowledge history;
5. conflict with source provenance preserved;
6. unknown versus known-negative under explicit completeness;
7. direct observation versus inferred current state;
8. direct relationship versus inferred path;
9. relationship semantic identity versus assertion occurrence identity;
10. exact consumed artifact version despite mutable locator;
11. backward explanation and forward impact provenance;
12. derived projection generation/staleness;
13. pre-model permission/sensitivity filtering;
14. read/disclose/automate/mutate authority separation;
15. stale approval invalidation;
16. dynamic target-set binding;
17. command acknowledgement versus physical settlement;
18. retry/duplicate ambiguity;
19. deletion propagation through derivatives;
20. restore without forgotten-data resurrection;
21. domain-profile evolution without historical reinterpretation;
22. people/research/software/projects/devices represented with the same universal core.

Failure of any of these requires revisiting the conceptual synthesis before physical storage selection.

---

# Pre-build scope-locked roadmap

All direct research, retrieval-requirements construction, hostile review and conceptual synthesis are complete.

Remaining path before physical implementation:

1. **Small Hand-Authored Cross-Domain Prototype / Validation**
2. **Only after that passes: physical storage selection and implementation design**

This sequence remains a scope guard, not blanket authorization.

---

# Current task

**No task is currently assigned.**

Conceptual Architecture Synthesis is complete.

---

# Planned next candidate

**Small Hand-Authored Cross-Domain Prototype / Validation**

Suggested bounded focus:

- create a deliberately small technology-neutral example dataset/model, not production code;
- include people/aliases, identity ambiguity and transition;
- preferences and explicit user statements;
- a research source/finding/derivation;
- a repository/resource with mutable locator and exact version;
- a device, observations, stale/unavailable state and derived state;
- temporal relationship history;
- conflicting assertions;
- known-negative completeness example;
- authorization-sensitive knowledge reference without implementing a policy engine;
- command/effect attempt and later observation without implementing an effect engine;
- deleted/restricted source plus derivative reconciliation example;
- profile/version evolution;
- manually exercise the 22 synthesis acceptance rules and representative retrieval patterns;
- record any model failure before storage selection.

Explicit exclusions:

- production code;
- database schema;
- SQL/graph/RDF/vector-store selection;
- embeddings;
- ACL/Vera implementation;
- autonomous workers.

Queue position alone is not authorization.

---

# Stop point

Conceptual Architecture Synthesis is complete and the campaign is stopped before the small hand-authored cross-domain prototype.

No prototype construction, storage selection or implementation was started inside synthesis.