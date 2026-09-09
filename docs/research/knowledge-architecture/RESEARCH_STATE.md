# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** project revisits, coverage scan, promoted Agno revisit, and five bounded standards/domain gap tasks complete; stopped before privacy deletion/retention gap research  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

---

# Scope lock

This campaign remains **research/requirements discovery only**.

The user explicitly requested scope-drift protection before KA-G3. The remaining pre-build sequence remains mandatory.

Do **not**:

- restart broad agent-framework research;
- reopen completed revisits without a concrete new evidence gap;
- select a final conceptual schema yet;
- select PostgreSQL, Neo4j, RDF, graph databases, vector stores, object stores, content-addressable stores, policy engines, or other implementation technologies;
- implement a knowledge/resource store;
- implement retrieval/context construction;
- create embeddings;
- migrate historical catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers;
- treat locators, hashes, validators, provenance, retrieved content, relationship data, or historical authorization decisions as stronger identity/authority evidence than their semantics support;
- skip retrieval-question, hostile-scenario, synthesis, and small-prototype gates.

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
- `gaps/resource-artifact-identity-lineage.md`

Cumulative ledgers:

- `invariants.md`
- `failure-patterns.md`

This state file is intentionally a compact current checkpoint. Detailed evidence remains in the dedicated reports.

---

# KA-G5 verification and boundary

User authorization:

- after KA-G4, user explicitly instructed `ok, continue`;
- the documented next candidate was KA-G5, so this authorized KA-G5 only.

Starting branch/head:

`3c82cc60189a640020d1c63c1c7516cc40f34534`

Starting commit message:

`research: complete knowledge authorization and actionability gap`

The branch was verified at that exact checkpoint before KA-G5 writes.

KA-G5 was bounded to:

- logical resource identity;
- locator/address/reference identity;
- resource versus representation semantics;
- mutable aliases/references;
- immutable content/version identity;
- validators/revision checks;
- content-addressed object semantics;
- source artifact versus extraction/chunk/derivative identity;
- origin/path/subresource context;
- exact consumed-version lineage;
- derived-index staleness/reconciliation;
- optimistic revision/precondition semantics.

Explicitly excluded:

- privacy erasure/retention mechanics;
- legal records policy;
- final resource schema;
- final URI/identifier scheme;
- final hash algorithm;
- object-store/CAS selection;
- Git/OCI/SWHID adoption;
- database/storage selection;
- retrieval implementation;
- embeddings implementation;
- Home Assistant/Matter domain validation;
- hostile-scenario execution;
- final conceptual synthesis;
- implementation.

---

# KA-G5 primary evidence

## RFC 3986

https://www.rfc-editor.org/rfc/rfc3986.html

Used for:

- resource and identifier semantics;
- identifiers not implying retrieval/access;
- distinction between identification and intrinsic identity;
- fragments/subresources.

## RFC 9110

https://www.rfc-editor.org/rfc/rfc9110.html

Used for:

- resource versus representation;
- multiple representations;
- ETag/validator semantics;
- Content-Location versus target resource identity;
- selected-representation identity;
- If-Match/preconditions and lost-update protection.

## Git object model

https://git-scm.com/book/en/v2/Git-Internals-Git-Objects.html

Used for:

- content-addressable blobs;
- trees and commits as distinct higher-level immutable objects;
- snapshot/history identity versus raw content identity;
- content-object graph semantics.

## OCI Image Specification

https://github.com/opencontainers/image-spec/blob/main/descriptor.md

Used for:

- digest as targeted-content identifier;
- media type and size;
- optional/multiple retrieval URLs;
- digest verification;
- Merkle-DAG artifact composition.

## Software Heritage SWHID

https://docs.softwareheritage.org/devel/swh-model/persistent-identifiers.html  
https://www.softwareheritage.org/2025/06/13/software-hash-identifier-swhid-tutorial/

Used for:

- typed intrinsic identifiers for content/directory/revision/release/snapshot;
- Merkle-DAG structure;
- origin/visit/anchor/path/line qualifiers;
- separation of intrinsic object identity from observation/access context.

No implementation technology was selected.

---

# Highest-value KA-G5 findings

## 1. Logical resource, locator, representation, and immutable observed version are different

The minimum conceptual separation is:

`logical resource -> locator/reference -> observed representation/version`

with locators allowed to move or multiply and representations allowed to vary.

## 2. Content digest equality is narrower than logical-resource identity

A digest can establish content/object equality under its scheme/profile.

It does not by itself prove:

- same logical document/resource;
- same provenance;
- same owner/authorization domain;
- same path/context;
- same higher-level snapshot/history object.

## 3. Mutable alias/reference must not substitute for immutable derivation identity

A branch, `latest` pointer, URL, filename or mutable path may resolve differently later.

Consequential derivation/replay therefore needs the exact observed resource version/content identity consumed at the time.

## 4. Validators are scoped semantics

ETags and similar revision tokens can support change detection and stale-write protection but are not automatically global hashes or logical-resource IDs.

Their producer/scope/semantics must be retained.

## 5. Artifact type/profile is part of identifier meaning

Git and SWHID distinguish raw content from tree/directory, commit/revision, release and snapshot objects.

A naked digest string is not enough.

## 6. Origin/path/subresource context is not intrinsic content identity

The same immutable object may be reached from multiple origins, paths or anchors.

Those contexts remain provenance/addressing data.

## 7. Source and derivative identity must remain separate

Extraction, page image, chunk, normalized text, summary, embedding and index records must not reuse source identity.

Each needs lineage back to the exact source artifact/version.

## 8. Derived projections need source-version/generation identity

A V1 embedding/index should be detectable as stale when the logical source moves to V2.

## 9. Optimistic version preconditions are a general stale-write pattern

If stale overwrite would be harmful, mutation should be able to bind to an expected version/revision and fail when the target changed.

No internal mechanism is selected yet.

## 10. Externally asserted identity/location equivalence is evidence, not self-authenticating truth

A source can claim a Content-Location, canonical URL, alias mapping or equivalence. Such claims may require verification before identity-sensitive use.

---

# Cumulative ledger disposition after KA-G5

## Invariants

Invariant IDs remain **KA-I-001 through KA-I-049**.

Status change:

- **KA-I-037 — candidate -> reinforced**
  - earlier project/adjacent evidence came from LlamaIndex, OpenAI Agents SDK, MCP and Agno;
  - KA-G5 independently supplies direct HTTP/RFC, OCI, Git and Software Heritage evidence that logical resource identity, locator/address and exact content/version identity are separate.

No new invariant ID is created.

Strong recurrence:

- KA-I-001
- KA-I-011
- KA-I-017/018
- KA-I-023
- KA-I-027
- KA-I-036
- KA-I-038/039 adjacent

No invariant is promoted to a final architecture rule.

## Failure patterns

Failure IDs remain **KA-F-001 through KA-F-049**.

No new failure ID/status change is made because KA-G5 supplied standards/system evidence rather than a new reproduced ACL/Vera incident.

Nominated hostile scenarios include:

- same URL -> different content;
- same bytes -> different provenance/authorization;
- mutable branch/latest alias moving after derivation;
- stale validator overwrite;
- chunk citation after parent revision;
- hash equality incorrectly merging logical documents;
- derivative reusing source identity;
- V1 index surviving as current after V2 source;
- digest without scheme/type/profile;
- unverified external identity-equivalence claim.

---

# Twenty-six-question disposition after KA-G5

## Strong enough for later requirements/synthesis without another agent-framework revisit

- 1 Stable identity
- 2 Identity vs namespace/principal
- 3 Provenance
- 4 Epistemic state
- 5 Temporal truth
- 6 Conflict/supersession
- 7 Relationships
- 8 Permissions/sensitivity
- 9 Actionability/use-purpose
- 10 Knowledge vs authority
- 11 Resources/artifacts — **direct positive semantics materially improved by KA-G5**
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

- **22 Privacy deletion/retention**
- **26 Scope of truth/generality — non-AI operational-domain validation**

---

# Pre-build scope-locked roadmap

The remaining path before physical implementation is now:

1. **KA-G6 — Privacy Deletion / Retention / Erasure Reconciliation**
2. **KA-G7 — Non-AI Operational-Domain Validation (Home Assistant / Matter-style)**
3. **Representative Retrieval Requirements** — approximately 40–60 questions
4. **Hostile / Adversarial Scenario Review**
5. **Conceptual Architecture Synthesis**
6. **Small Hand-Authored Cross-Domain Prototype / Validation**
7. **Only then: physical storage selection and implementation**

This sequence is a scope guard, not blanket authorization.

---

# Current task

**No task is currently assigned.**

KA-G5 is complete.

---

# Planned next candidate

**KA-G6 — Privacy Deletion / Retention / Erasure Reconciliation**

Suggested bounded focus:

- delete/forget semantics across canonical and derived planes;
- retention/expiry/tombstone behavior;
- deletion propagation to indexes, caches, embeddings, summaries and replicas;
- audit/history versus erasure tension;
- backup/restore reintroduction hazards;
- source deletion versus derivative deletion;
- scoped erasure versus global deletion;
- proof/reconciliation of erasure without selecting a legal regime or implementation technology.

Queue position alone is not authorization.

---

# Stop point

KA-G5 is complete and the campaign is stopped before KA-G6.

No privacy research, operational-domain validation, retrieval-requirements construction, hostile review, conceptual synthesis, storage selection, or implementation was started inside KA-G5.
