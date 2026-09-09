# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** project revisits, coverage scan, promoted Agno revisit, all seven bounded standards/domain gap tasks, and representative retrieval requirements complete; stopped before hostile/adversarial scenario review  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

---

# Scope lock

This campaign remains **research/requirements discovery and validation only**.

The user explicitly requested scope-drift protection before KA-G3. That remains controlling.

Do **not**:

- restart broad agent-framework or domain research without a concrete new evidence gap;
- reopen completed revisits merely because an implementation choice is difficult;
- select a final conceptual schema yet;
- select PostgreSQL, Neo4j, RDF, graph databases, vector stores, object stores, content-addressable stores, policy engines, Home Assistant/Matter implementation stacks, or other implementation technologies;
- implement a knowledge/resource store;
- implement authorization, deletion, retention, retrieval or context-construction services;
- create embeddings;
- migrate historical catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers;
- begin hostile scenario execution, conceptual synthesis, prototype construction, storage selection, or implementation inside the retrieval-requirements task;
- weaken requirements merely to fit a preferred storage technology.

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

## Pre-build validation gates

20. **Representative Retrieval Requirements** — complete

---

# Detailed artifacts

Project revisits live under `projects/`.

Gap reports:

- `gaps/epistemic-temporal-conflict.md`
- `gaps/relationships-ontology-evolution.md`
- `gaps/formal-provenance-evidence-lineage.md`
- `gaps/knowledge-authorization-actionability.md`
- `gaps/resource-artifact-identity-lineage.md`
- `gaps/privacy-deletion-retention-erasure.md`
- `gaps/non-ai-operational-domain-validation.md`

Coverage scan:

- `COVERAGE_SCAN.md`

Cumulative ledgers:

- `invariants.md`
- `failure-patterns.md`

Retrieval acceptance set:

- `REPRESENTATIVE_RETRIEVAL_REQUIREMENTS.md`

Detailed evidence remains in the dedicated reports. This file is the compact current checkpoint.

---

# Representative Retrieval Requirements verification and boundary

User authorization:

- after KA-G7, the user explicitly instructed `ok continue`;
- the documented next candidate was Representative Retrieval Requirements;
- this authorized this requirements phase only.

Starting branch/head:

`bf61ca42d4e2affd9898f868bb32de39fb98c0eb`

Starting commit message:

`research: complete non-ai operational validation gap`

The phase was bounded to:

- converting completed evidence into concrete cross-domain acceptance requirements;
- approximately 40–60 representative retrieval questions/tasks;
- ACL, Vera, research, people, devices, projects, software versions, resources, permissions, history, conflicts, provenance, effects and deletion;
- current-state versus historical-world versus historical-belief retrieval;
- unknown/negative/conflict semantics;
- direct versus inferred relationships;
- resource/version identity;
- provenance backward and forward traversal;
- semantic/full-text discovery without conflating relevance with truth;
- authorization-sensitive retrieval and model exposure;
- effect/deletion reconciliation;
- composite retrieval and context construction.

Explicitly excluded:

- hostile/adversarial scenario execution;
- final conceptual primitive/schema selection;
- storage/database selection;
- retrieval implementation;
- embeddings;
- policy-engine implementation;
- effect/deletion implementation;
- prototype construction;
- ACL/Vera implementation.

---

# Retrieval requirements result

`REPRESENTATIVE_RETRIEVAL_REQUIREMENTS.md` defines **52 representative acceptance requirements**.

Coverage groups:

1. Identity, people, aliases and ambiguity — RR-01 through RR-04
2. Current truth, historical truth and historical belief — RR-05 through RR-09
3. Epistemic state, conflicts and negative knowledge — RR-10 through RR-15
4. Provenance, evidence and derivation — RR-16 through RR-20
5. Relationships and graph/path semantics — RR-21 through RR-25
6. Resources, files, documents, repositories and versions — RR-26 through RR-30
7. Projects, ACL, research and software knowledge — RR-31 through RR-35
8. Authorization, sensitivity, purpose and actionability — RR-36 through RR-41
9. Commands, effects, observations and operational state — RR-42 through RR-45
10. Deletion, restriction, retention and reconciliation — RR-46 through RR-50
11. Composite retrieval and context construction — RR-51 through RR-52

The requirements exercise:

- deterministic structured lookup;
- temporal/bitemporal retrieval;
- direct and inferred relationship retrieval;
- provenance backward explanation;
- forward impact lineage;
- full-text/semantic candidate discovery;
- composite retrieval/reranking;
- authorization gates;
- context construction;
- effect/deletion reconciliation.

The requirements are acceptance criteria, not a query-language or storage design.

---

# Cumulative ledger disposition

Invariant IDs remain **KA-I-001 through KA-I-049**.

Failure IDs remain **KA-F-001 through KA-F-049**.

No new invariant or failure ID was created during this phase because the task translated existing evidence into testable retrieval requirements rather than adding new evidence.

No invariant becomes a final architecture rule yet.

---

# Pre-build scope-locked roadmap

Direct gap research and representative retrieval-requirements construction are complete.

Remaining path before physical implementation:

1. **Hostile / Adversarial Scenario Review**
2. **Conceptual Architecture Synthesis**
3. **Small Hand-Authored Cross-Domain Prototype / Validation**
4. **Only then: physical storage selection and implementation**

This sequence remains a scope guard, not blanket authorization.

---

# Current task

**No task is currently assigned.**

Representative Retrieval Requirements are complete.

---

# Planned next candidate

**Hostile / Adversarial Scenario Review**

Suggested bounded focus:

- attack the requirements/invariants with concrete cross-domain scenarios rather than doing more broad research;
- test same-name identity collisions and mistaken merges/splits;
- stale and unavailable operational state;
- conflicting/late evidence;
- retrieved-instruction/prompt-injection attempts;
- authorization relation/world-relation confusion;
- stale policy/approval reuse;
- mutable locator/version drift;
- wrong derived relationship/path explanation;
- deleted/restricted data surviving derivatives or restore;
- concurrent writers/background generation races;
- command acknowledgement mistaken for physical/effect settlement;
- schema/ontology/profile evolution;
- cross-domain edge cases from ACL and Vera;
- identify which existing invariants/requirements catch each scenario and record any genuine uncovered gap.

Explicit exclusions:

- final architecture synthesis;
- storage selection;
- implementation;
- prototype construction.

Queue position alone is not authorization.

---

# Stop point

The retrieval-requirements phase is complete and the campaign is stopped before Hostile / Adversarial Scenario Review.

No hostile review, conceptual synthesis, prototype construction, storage selection or implementation was started inside this phase.
