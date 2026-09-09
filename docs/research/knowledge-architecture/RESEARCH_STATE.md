# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** project revisits, coverage scan, promoted Agno revisit, and three bounded standards/domain gap tasks complete; stopped before knowledge-authorization/actionability gap research  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

---

# Scope lock

This campaign is still **research/requirements discovery only**.

The user explicitly asked to prevent scope drift before continuing after KA-G2.

The current documentation already contained the necessary anti-drift boundaries, so no redundant pre-task governance edit was made. This state now makes the remaining pre-build path explicit so later continuation does not broaden implicitly.

Do **not**:

- restart broad agent-framework research;
- reopen completed project revisits without a concrete new evidence gap;
- select a final conceptual schema yet;
- select PostgreSQL, Neo4j, RDF, graph databases, vector stores, or any other storage technology;
- implement a knowledge store;
- implement retrieval/context construction;
- create embeddings;
- migrate historical catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers;
- treat retrieved/provenance content as policy or execution authority;
- skip the retrieval-question, hostile-scenario, synthesis, and small-prototype gates.

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

---

# Detailed reports

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

Gap reports:

- `gaps/epistemic-temporal-conflict.md`
- `gaps/relationships-ontology-evolution.md`
- `gaps/formal-provenance-evidence-lineage.md`

Cumulative ledgers:

- `invariants.md`
- `failure-patterns.md`

---

# KA-G3 verification and boundary

User authorization:

- after KA-G2, user requested a scope check/documentation update if needed and then continuation;
- this authorized the already-named next candidate, KA-G3, while preserving campaign anti-drift rules.

Starting branch/head:

`598fe7cb461bbc10cb3298fdce05a5fcdf421b16`

Starting commit message:

`research: complete relationships and ontology evolution gap`

KA-G3 was bounded to:

- formal provenance/evidence lineage;
- source/derived separation;
- Entity / Activity / Agent distinctions;
- usage/generation/derivation;
- attribution/association/delegation;
- process/plan identity where behavior-bearing;
- revision/quotation/primary-source provenance distinctions;
- provenance-of-provenance;
- multiple provenance providers/perspectives;
- lineage precision;
- backward explanation and forward impact lineage.

Explicitly excluded:

- authorization/actionability model design;
- ABAC/ReBAC policy selection;
- resource/artifact storage design;
- privacy erasure/retention mechanics;
- Home Assistant/Matter operational-domain modeling;
- representative retrieval-question construction;
- hostile/adversarial scenario execution;
- final conceptual synthesis;
- physical storage/database selection;
- implementation.

---

# KA-G3 primary evidence

## W3C PROV family

- PROV Overview: https://www.w3.org/TR/prov-overview/
- PROV-DM: https://www.w3.org/TR/prov-dm/
- PROV-O: https://www.w3.org/TR/prov-o/
- PROV Constraints: https://www.w3.org/TR/prov-constraints/
- PROV-AQ: https://www.w3.org/TR/prov-aq/
- PROV-Links: https://www.w3.org/TR/prov-links/

Used for:

- Entity / Activity / Agent;
- generation/use/derivation;
- revision/quotation/primary source;
- attribution/association/delegation;
- plan/process context;
- provenance bundles/provenance-of-provenance;
- distributed provenance/perspective;
- access/query/completeness limitations;
- provenance consistency versus proposition truth.

## OpenLineage

- https://openlineage.io/docs/spec/object-model/
- https://openlineage.io/docs/spec/facets/
- https://openlineage.io/docs/spec/facets/job-facets/lineage/
- https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.json

Current documentation observed version: `1.53.0`.

Used for contemporary operational corroboration of:

- Job vs Run identity;
- input/output Dataset lineage;
- run events;
- exact lineage edges;
- warning against false all-to-all input/output lineage inferred only from event co-occurrence;
- extensible/versioned lineage metadata.

No W3C PROV, RDF, OpenLineage, graph database, or physical schema adoption decision was made.

---

# Highest-value KA-G3 findings

## 1. Provenance is not truth

Provenance describes origin, transformation, influence, and responsibility.

It can support reliability/trust assessments but does not itself establish proposition truth, epistemic confidence, or verification.

A well-provenanced claim can still be false.

## 2. Source/entity, transformation occurrence, and responsible agent are different

A durable lineage chain must be able to distinguish:

`input/source entity/version -> activity occurrence -> generated entity/version`

from:

- agent attribution;
- agent association with the activity;
- delegation/on-behalf-of relationship;
- plan/procedure/profile used by the activity.

## 3. Derivation has precision levels

A coarse `derivedFrom` edge is useful but is not equivalent to identifying:

- exact input usage;
- transformation/activity occurrence;
- exact output generation;
- behavior-bearing plan/profile.

Low-precision provenance must not be presented as reproducibility-grade lineage.

## 4. Shared run/container co-occurrence is not exact dependency

OpenLineage explicitly supports exact lineage edges to avoid false Cartesian input/output dependencies.

ACL/Vera must not infer that every context item or batch input supported every output merely because they shared one run/event/prompt.

## 5. Attribution, association, and delegation are distinct

- attribution answers who an entity is ascribed to;
- association ties an agent to an activity, optionally with a plan;
- delegation records that one agent acted on behalf of another for an activity.

None is an execution-authorization token.

## 6. Behavior-bearing plans/profiles need lineage identity

Prompt templates, parsers, model profiles, ontology/inference profiles, extraction procedures, and workflow definitions need independent identity/provenance when changing them can change the derived result.

## 7. Revision, quotation, and primary-source provenance should remain distinguishable

A source can be primary for one topic/derivation context and not another.

`primary source` is not a universal trust flag.

## 8. Provenance records themselves need provenance

Provenance bundles/records can be generated, attributed, aggregated, and derived from other provenance.

Model-generated or third-party provenance remains evidence that can itself be wrong or incomplete.

## 9. Multiple provenance providers/perspectives may coexist

Two providers may describe the same entity differently.

The system must preserve which provider/perspective produced which provenance description instead of silently merging provenance into one source-less graph.

## 10. Provenance lookup is not global completeness

Failure to discover provenance does not prove no source/derivation exists unless an explicit completeness contract applies.

## 11. Structural provenance validity is not truth verification

A provenance record can satisfy formal consistency constraints while still containing false, incomplete, or malicious statements.

## 12. Provenance must support backward explanation and forward impact

Backward:

- why/how was this produced?
- what source supports it?

Forward:

- what depends on this source?
- what must be re-derived if it changes or is deleted?

## 13. Provenance does not replace effect settlement

A recorded activity/run/API invocation is not proof that an external effect settled exactly once.

The effect ledger remains a separate architectural component.

---

# Cumulative ledger disposition after KA-G3

## Invariants

Invariant IDs remain **KA-I-001 through KA-I-049**.

No new invariant ID was created.

Reason:

The formal-provenance evidence strongly reinforces existing architecture families and adding narrowly PROV-shaped IDs would duplicate them rather than improve the general ACL/Vera model.

Strong recurrence:

- KA-I-001 — raw/source evidence stays separate from derived knowledge;
- KA-I-017/018 — semantic/behavior-bearing profile/version changes require explicit derivation identity;
- KA-I-023 — transformations need provenance of their own;
- KA-I-025 — provenance/attribution remains separate from epistemic verification;
- KA-I-027 — derived outputs expose source/generation coverage;
- KA-I-036 — source and derivative identities remain distinct;
- KA-I-041 — transformation/run occurrences require stable occurrence identity;
- KA-I-047 — provenance-discovery absence is adjacent evidence for completeness-qualified negative inference;
- KA-I-048 — separately addressable statement/relation occurrences remain useful when provenance differs.

No invariant becomes a final architecture rule yet.

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID/status change was made because this task supplied standards/specification evidence rather than a reproduced implementation incident.

False Cartesian lineage, provenance-as-truth, and provenance-delegation-as-authority are nominated for later hostile/acceptance testing.

---

# Twenty-six-question disposition after KA-G3

## Strong enough for later synthesis without another agent-framework revisit

- 1 Stable identity
- 2 Identity vs namespace/principal
- 3 Provenance — **formal positive semantics materially improved by KA-G3**
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

## Remaining bounded direct gaps

- **8 Permissions/sensitivity** — direct formal authorization study still required
- **9 Actionability/use-purpose semantics**
- **11 Resources/artifacts**
- **22 Privacy deletion/retention**
- **26 Scope of truth/generality** — non-AI operational-domain validation still required

---

# Pre-build scope-locked roadmap

The remaining path before physical implementation remains:

1. **KA-G4 — Knowledge Authorization + Actionability / Use-Purpose**
2. **KA-G5 — Resource / Artifact Identity and Lineage**
3. **KA-G6 — Privacy Deletion / Retention / Erasure Reconciliation**
4. **KA-G7 — Non-AI Operational-Domain Validation (Home Assistant / Matter-style)**
5. **Representative Retrieval Requirements** — approximately 40–60 questions
6. **Hostile / Adversarial Scenario Review**
7. **Conceptual Architecture Synthesis**
8. **Small Hand-Authored Cross-Domain Prototype / Validation**
9. **Only then: physical storage selection and implementation**

This sequence is a scope guard, not automatic authorization to execute all remaining tasks in one run.

Do not skip ahead because the architecture appears obvious.

---

# Current task

**No task is currently assigned.**

KA-G3 is complete.

---

# Planned next candidate

**KA-G4 — Knowledge Authorization + Actionability / Use-Purpose**

Suggested bounded focus:

- principal versus subject/owner;
- resource/knowledge attributes;
- purpose/context/environment attributes;
- ABAC-style authorization semantics;
- ReBAC-style relationship-based authorization where useful;
- read/retrieve versus disclose-to-model versus mutate/delete/consolidate versus use-for-automation;
- actionability classes such as informational/planning/verification-required/automation-input/non-authoritative;
- deny/unknown/conflict/fail-closed behavior;
- policy decision provenance without turning retrieved content into policy.

Explicit exclusions for KA-G4 should include:

- privacy-erasure mechanics beyond authorization relevance;
- resource-storage implementation;
- final policy-engine technology selection;
- final schema synthesis;
- implementation.

Queue position alone is not authorization.

---

# Stop point

KA-G3 is complete and the campaign is stopped before KA-G4.

No authorization research, resource research, privacy research, operational-domain validation, retrieval-requirements construction, hostile review, final synthesis, storage selection, or implementation was started inside KA-G3.