# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** project revisits, coverage scan, promoted Agno revisit, and four bounded standards/domain gap tasks complete; stopped before resource/artifact identity gap research  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

---

# Scope lock

This campaign remains **research/requirements discovery only**.

The user explicitly requested scope-drift protection before KA-G3. The remaining pre-build sequence is preserved below and must not be skipped merely because the architecture appears increasingly clear.

Do **not**:

- restart broad agent-framework research;
- reopen completed revisits without a concrete new evidence gap;
- select a final conceptual schema yet;
- select PostgreSQL, Neo4j, RDF, graph databases, vector stores, policy engines, or other implementation technologies;
- implement a knowledge store or authorization system;
- implement retrieval/context construction;
- create embeddings;
- migrate historical catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers;
- treat retrieved content, provenance, relationship data, or historical authorization decisions as current policy/authority;
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
16. **KA-G4 — Knowledge Authorization + Actionability / Use-Purpose** — complete

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
- `gaps/knowledge-authorization-actionability.md`

Cumulative ledgers:

- `invariants.md`
- `failure-patterns.md`

This state file is intentionally a compact current checkpoint; detailed evidence remains in the dedicated reports.

---

# KA-G4 verification and boundary

User authorization:

- after KA-G3, user explicitly instructed: `ok continue next step`;
- the documented next candidate was KA-G4, so this authorized KA-G4 only.

Starting branch/head:

`b141044032c9d3e9773b5f9d81078576799321bb`

Starting commit message:

`research: complete formal provenance gap`

The branch was reverified at that exact commit before write work.

KA-G4 was bounded to:

- principal/requesting-subject versus owner/storage identifiers;
- target/resource/knowledge scope for policy;
- action/operation identity;
- ABAC-style attribute/context evaluation;
- ReBAC-style relationship authorization;
- purpose/use constraints;
- read/retrieve versus disclosure/model-exposure versus transformation/mutation versus use-for-decision/automation;
- authorization decision versus enforcement separation;
- explicit Permit/Deny/Indeterminate/NotApplicable-style semantics where useful;
- mandatory obligations versus advice;
- policy/model revision identity and authorization-input freshness;
- transient request context;
- decision provenance without converting historical decisions into current authority.

Explicitly excluded:

- privacy erasure/retention mechanics;
- legal/privacy-policy analysis;
- final sensitivity taxonomy;
- resource/artifact identity research beyond target identification;
- policy-engine selection;
- credential-broker implementation;
- Home Assistant/Matter operational modeling;
- retrieval-question construction;
- hostile/adversarial scenario execution;
- conceptual architecture synthesis;
- database/storage selection;
- implementation.

---

# KA-G4 primary evidence

## NIST SP 800-162 — Attribute Based Access Control

https://csrc.nist.gov/pubs/sp/800/162/upd2/final

Used for:

- subject/object/action/environment categories;
- policy evaluation of attributes/relationships;
- operation-specific authorization;
- human and non-person requesting subjects.

## OASIS XACML 3.0

https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-cos01-en.html

Used for:

- Policy Administration / Information / Decision / Enforcement separation;
- Permit, Deny, Indeterminate, NotApplicable;
- rule/policy combining algorithms;
- mandatory obligations versus advice;
- explicit decision/enforcement lifecycle.

## W3C ODRL 2.2

https://www.w3.org/TR/odrl-model/  
https://www.w3.org/TR/odrl-vocab/

Used for:

- permission/prohibition/duty;
- action-specific usage rights;
- purpose as a first-class constraint;
- time, recipient, device, location, version and other contextual constraints;
- distinct actions such as read/use/derive/transform/share/delete/write/secondaryUse.

## Google Zanzibar

https://research.google/pubs/zanzibar-googles-consistent-global-authorization-system/

Used for:

- relationship-based authorization;
- authorization-state consistency;
- evidence that authorization data/model consistency is distinct from ordinary world knowledge.

## OpenFGA current documentation

https://openfga.dev/docs/learn/rebac  
https://openfga.dev/docs/modeling/contextual-time-based-authorization  
https://openfga.dev/docs/interacting/contextual-tuples  
https://openfga.dev/docs/getting-started/tuples-api-best-practices

Current docs inspected on 2026-09-08.

Used for:

- direct and implied authorization relationships;
- ephemeral contextual tuples;
- time/location/network/organization context;
- token-claim staleness until expiry;
- authorization-model ID as behavior/freshness context.

No implementation technology was selected.

---

# Highest-value KA-G4 findings

## 1. Authorization is operation-specific

A generic `can_access` bit is insufficient.

A consequential authorization decision needs enough identity to bind:

- authenticated principal/requestor;
- target/resource/knowledge scope;
- requested action;
- purpose/use context where applicable;
- relevant attributes/authorization relationships;
- policy/model revision;
- transient environment/context;
- decision outcome/obligations;
- appropriate freshness/validity boundary.

## 2. Readability is not universal usability

Permission to retrieve/read does not imply permission to:

- disclose to another person;
- expose to a model;
- transform/derive;
- export/share;
- mutate/supersede;
- delete/clear;
- use for automated decisions;
- use to trigger an external effect.

ODRL supplies direct evidence for action-specific usage semantics.

## 3. Purpose can be first-class policy input

ODRL defines `purpose` as a constraint on exercising an action.

ACL/Vera therefore needs to preserve the ability to distinguish, where policy requires it:

- answering the owner;
- planning/recommendation;
- disclosure to another party;
- model training;
- automated decision;
- automation/effect execution.

KA-G4 does not freeze the final purpose vocabulary.

## 4. Authorization graph and canonical world graph are separate domains

ReBAC tuples may encode authorization relationships such as `editor`, `viewer`, `member`, or `parent` under an authorization model.

Those tuples must not automatically become canonical world assertions.

Authorization relationship semantics are policy/profile dependent.

## 5. Transient request context is not automatically durable knowledge

Network, current organization, token claims, current time and similar request context may affect one authorization decision without being persisted as canonical knowledge.

Durable ingestion requires a separate evidence/knowledge path.

## 6. Decision and enforcement are distinct

Policy evaluation cannot be treated as the effect itself.

A future architecture must preserve:

`policy inputs -> authorization decision -> enforcement gate -> attempted effect -> effect settlement`

The effect ledger remains separate.

## 7. Obligations must not be silently dropped

If a Permit depends on a mandatory condition such as confirmation, redaction, auditing or constrained disclosure, failure to honor that obligation cannot be treated as ordinary successful authorization.

No final obligation vocabulary is selected.

## 8. Deny, Indeterminate and NotApplicable remain distinguishable internally

A missing policy, failed attribute lookup or ambiguous decision must not silently become Permit.

The future top-level fail behavior must be explicit.

KA-G4 does not select a final combining algorithm.

## 9. Policy/model composition is behavior-bearing

Different combining rules can produce different decisions from identical lower-level policies.

Policy/model revision and behavior-bearing combination semantics belong in decision provenance/reproducibility context.

## 10. Authorization inputs can become stale

Token/group membership, ownership, organization membership, device trust, sensitivity and other policy inputs can change.

Cached historical Permit evidence must not masquerade as a fresh decision.

## 11. Authorization decision provenance is evidence, not reusable authority

A decision record can explain why an earlier action was permitted/denied.

It does not authorize a later request automatically.

This reinforces the campaign's operation/context/version-bound authority rule.

## 12. Knowledge may feed policy; knowledge does not self-install policy

Qualified trusted knowledge may be a policy input.

Retrieved text, provenance descriptions, memories or source documents do not become policy merely by being retrieved.

## 13. Delegation authority must be bounded

Provenance that an agent acted on behalf of another is not an authorization grant.

Actual delegation must bind permitted action/scope/context and current policy.

## 14. Actionability is distinct from truth/confidence

A highly credible fact may be prohibited for a particular use.

A bounded automation input may be permitted under policy even if it carries uncertainty, provided verification/confirmation rules are satisfied.

The system must therefore keep separate:

- epistemic state/confidence;
- relevance;
- sensitivity;
- authorization;
- actionability;
- required verification/confirmation.

---

# Cumulative ledger disposition after KA-G4

## Invariants

Invariant IDs remain **KA-I-001 through KA-I-049**.

No new invariant ID was created.

Reason:

KA-G4 materially strengthens an existing cluster rather than revealing a cleanly independent primitive:

- KA-I-003 — namespace/user field != authenticated principal;
- KA-I-014 — principal/purpose/sensitivity gates before model exposure;
- KA-I-019 — policy metadata must survive end-to-end;
- KA-I-020 — retrieval never grants execution authority;
- KA-I-024 — permissions/actionability are context-construction concerns distinct from relevance/truth;
- KA-I-034 — personal/shared ownership/read-write authority;
- KA-I-043 — persistent knowledge mutation actions are separately governable;
- KA-I-046 — durable authority binds exact operation and current authority context/version.

KA-G4 supplies direct standards/domain reinforcement for this combined authorization contract without duplicating the taxonomy.

No invariant becomes a final architecture rule yet.

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID/status change is made because KA-G4 supplied standards/domain semantics rather than a newly reproduced implementation incident.

Later hostile tests should cover:

- read permission reused as automation authority;
- stale group/token claims;
- old Permit replayed after policy change;
- Indeterminate/NotApplicable treated as Permit;
- mandatory obligations dropped;
- transient auth context persisted as knowledge;
- authorization relation treated as world truth;
- retrieved content self-installing policy;
- disclosure-to-model permission confused with effect authority.

---

# Twenty-six-question disposition after KA-G4

## Strong enough for later requirements/synthesis without another agent-framework revisit

- 1 Stable identity
- 2 Identity vs namespace/principal
- 3 Provenance
- 4 Epistemic state
- 5 Temporal truth
- 6 Conflict/supersession
- 7 Relationships
- 8 Permissions/sensitivity — **direct formal authorization semantics materially improved by KA-G4**
- 9 Actionability/use-purpose — **positive semantics materially improved by KA-G4**
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

- **11 Resources/artifacts**
- **22 Privacy deletion/retention**
- **26 Scope of truth/generality — non-AI operational-domain validation**

---

# Pre-build scope-locked roadmap

The remaining path before physical implementation is now:

1. **KA-G5 — Resource / Artifact Identity and Lineage**
2. **KA-G6 — Privacy Deletion / Retention / Erasure Reconciliation**
3. **KA-G7 — Non-AI Operational-Domain Validation (Home Assistant / Matter-style)**
4. **Representative Retrieval Requirements** — approximately 40–60 questions
5. **Hostile / Adversarial Scenario Review**
6. **Conceptual Architecture Synthesis**
7. **Small Hand-Authored Cross-Domain Prototype / Validation**
8. **Only then: physical storage selection and implementation**

This sequence is a scope guard, not blanket authorization to execute all tasks at once.

---

# Current task

**No task is currently assigned.**

KA-G4 is complete.

---

# Planned next candidate

**KA-G5 — Resource / Artifact Identity and Lineage**

Suggested bounded focus:

- logical resource identity;
- locator/address/replica identity;
- content digest/version identity;
- mutable versus immutable artifact semantics;
- source artifact versus extraction/chunk/derivative identity;
- content-addressed objects where useful;
- cache/index/embedding relationships to canonical artifacts;
- resource revision/change detection;
- provenance/lineage interaction;
- no storage-engine selection.

Queue position alone is not authorization.

---

# Stop point

KA-G4 is complete and the campaign is stopped before KA-G5.

No resource/artifact research, privacy research, operational-domain validation, retrieval-requirements construction, hostile review, final synthesis, storage selection, or implementation was started inside KA-G4.
