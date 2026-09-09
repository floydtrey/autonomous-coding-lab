# Knowledge Core Architecture Decision Log

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Component:** Knowledge Core  
**Status:** active physical-architecture decision log  

---

# Purpose

This file records accepted physical-architecture decisions for Knowledge Core as they are made.

It is intentionally concise. Detailed architecture documentation will be synthesized after the major structural decisions are complete.

The completed Knowledge Architecture Evidence Campaign under `docs/research/knowledge-architecture/` remains the evidence base. Decisions here must not weaken those requirements merely to fit a preferred implementation technology.

The conceptual primitive families remain semantic roles rather than mandatory database tables:

- ENTITY
- ASSERTION
- OCCURRENCE
- RESOURCE
- EVIDENCE / PROVENANCE LINK
- SEMANTIC PROFILE / VOCABULARY DEFINITION

The governing separation remains:

> **Knowledge does not grant authority. Authority does not prove execution. Execution acknowledgement does not prove world settlement.**

---

# Decision status

- **Accepted** — current architecture decision; later changes require an explicit superseding decision.
- **Open** — deliberately unresolved and still to be designed.
- **Superseded** — retained for history but replaced by a later decision.

Architecture decisions are not silently rewritten when they change. A later decision should explicitly supersede the earlier one so the reasoning remains recoverable.

---

# Accepted decisions

## KC-D001 — Knowledge Core is a standalone service
**Status:** Accepted

Knowledge Core is its own local/network-capable service. Vera, ACL, and future clients use a defined interface and never directly own/manipulate the canonical database. Initial co-location on one PC must not prevent later process/VM/machine separation.

---

## KC-D002 — PostgreSQL is the initial canonical knowledge store
**Status:** Accepted

PostgreSQL is the initial source of canonical semantic state. Search indexes, embeddings, summaries, caches, graph projections, and current-state projections are derived/rebuildable where practical. The six conceptual families need not map one-to-one to six tables.

---

## KC-D003 — Large artifact bytes live outside PostgreSQL
**Status:** Accepted

PostgreSQL stores RESOURCE identity, metadata, exact version/digest, lineage, locators, ownership/sensitivity references, and semantics; large raw bytes live in a separately managed artifact store.

---

## KC-D004 — Authority is a separate deterministic service boundary
**Status:** Accepted

AI reasoning requests operations but does not grant authority. Authority evaluates the exact operation for authenticated principal, purpose, context, policy revision, freshness, and obligations. Retrieval never itself grants execution permission.

---

## KC-D005 — Architecture supports a physically read-only Authority Root
**Status:** Accepted

Static/slow-changing root authority policy and verification material can live on controller-enforced write-protected media. Writable operational authority/effect history remains elsewhere. Physical protection supplements, not replaces, process/OS/credential isolation.

---

## KC-D006 — Canonical knowledge history is non-destructive and supports explicit undo/reversal
**Status:** Accepted

Ordinary learning and correction append new assertion/version/transition records rather than destroying previous canonical state. Undo/reversal is another explicit transition that can restore an earlier state as current without erasing the mistaken intermediate history. Privacy erasure is a separate privileged lifecycle.

---

## KC-D007 — Assertion semantics use typed relational fields with bounded JSON extensibility
**Status:** Accepted

Canonical ASSERTION semantics that matter for query, history, provenance, constraints, or authority use explicit typed relational fields/children. `JSONB` is only a bounded, profile-governed extension area and may not replace core semantics or hide authority-critical meaning.

---

## KC-D008 — Canonical records use a universal internal reference registry for cross-family links
**Status:** Accepted

A small physical reference registry provides stable internal addressing across canonical Entity, Assertion, Occurrence, Resource/version, and Semantic Profile/revision records. Specialized tables retain their own semantics/constraints; the registry is not a seventh conceptual primitive or untyped graph.

---

## KC-D009 — Temporal model uses independent world-valid time and immutable knowledge-record time
**Status:** Accepted

Knowledge Core separately records when a claim applies in the world and when Knowledge Core learned/recorded it. Late corrections append at the real record time with their supported world-valid interval. Current state is derived/rebuildable; historical belief remains reconstructable.

---

## KC-D010 — Provenance is a typed, traversable lineage model separate from semantic relationships and lifecycle state
**Status:** Accepted

Evidence/provenance uses governed typed directed links, exact source versions, and occurrence/activity context. It supports backward explanation and forward impact. It never substitutes for domain relationships, correction/currentness state, truth/confidence, sensitivity clearance, permission, or authority.

---

## KC-D011 — Initial artifact store is a local immutable content-addressed filesystem
**Status:** Accepted

Initial artifact bytes live in a configurable local filesystem store keyed by SHA-256. Blobs are immutable; changed bytes create new versions. Identical bytes may deduplicate physically but do not merge logical identity/provenance/ownership/history. Backend may later move to another drive, NAS, or object store.

---

## KC-D012 — Semantic profiles and vocabulary are immutable, explicitly versioned, and pinned by assertions
**Status:** Accepted

Logical profiles have immutable exact revisions. Assertions pin the governing revision. Material meaning changes create new semantic identity or explicit migration/mapping rather than silently redefining old semantics. Old records never change meaning because a new profile becomes active.

---

## KC-D013 — Knowledge Core API exposes semantic operation classes, not generic CRUD or database access
**Status:** Accepted

Clients use meaningful operation families: read/search/explain, append assertion/occurrence/resource/evidence, correction/reversal, identity transition, and privileged restriction/erasure/profile administration. Clients receive no DB credentials, cannot set trusted record-time identity, and cannot issue arbitrary field updates. Responses remain structured and provenance/temporal/conflict-aware.

---

## KC-D014 — Retrieval is an authorization-first composite pipeline; context construction is a final derived step

**Status:** Accepted

Knowledge Core retrieval will be an explicit multi-stage pipeline rather than a single search score or a model with direct database/vector access.

A retrieval request carries authenticated principal, purpose/use, requested query mode, and any required target/scope information. Query modes explicitly distinguish at least:

- current knowledge;
- current reconstruction of world history at a requested world time;
- historical belief as of a requested knowledge-record time;
- direct evidence/provenance explanation;
- direct relationship versus inferred/path relationship requests.

The default conceptual ordering is:

1. **Authority/sensitivity eligibility** — determine which records the principal may read/disclose/use for the stated purpose before protected content becomes model-facing context or an unrestricted semantic candidate set.
2. **Structured constraints** — entity/resource/profile/domain/applicability filters and exact identifiers.
3. **Temporal selection** — current/world-valid/historical-belief constraints.
4. **Relationship selection/traversal** — direct edges and inferred/path results remain distinguishable.
5. **Candidate generation** — PostgreSQL structured/full-text retrieval and derived semantic/vector retrieval over the eligible corpus.
6. **Provenance/conflict/currentness evaluation** — preserve competing assertions, source basis, staleness, uncertainty, and direct-versus-derived distinctions.
7. **Reranking** — combine relevance signals without converting ranking into truth, authority, confidence, or currentness.
8. **Context construction** — build the bounded model-facing package from authorized structured results.

The exact implementation may reorder compatible internal steps for performance so long as protected content is not exposed before its hard eligibility gate and the semantic distinctions above remain intact.

Semantic similarity is **candidate generation**, not identity, truth, permission, or currentness. Full-text rank is likewise relevance, not truth. No single scalar score may silently collapse relevance, confidence, authority, provenance quality, freshness, and epistemic basis into one meaning.

Context packages are derived/ephemeral artifacts. They retain source references/revisions, temporal mode, relevant provenance/conflict indicators, profile/generation identity, and enough metadata for the reasoning layer to know when information is stale, conflicting, inferred, incomplete, or restricted.

Retrieved imperative text remains content; context construction never upgrades a document's instructions into Authority semantics.

**Reason:** this preserves the research campaign's security and epistemic requirements while still allowing hybrid structured, relationship, full-text, and semantic retrieval.

---

# Open physical-design decisions

1. Detailed PostgreSQL table split for canonical and derived structures.
2. Derived-data generation, invalidation, rebuild, and versioning.
3. Identity-resolution workflow and transition mechanics.
4. Deletion/retention/reconciliation workflow.
5. Concurrency, revision/precondition, retry/idempotency, and stale-write protection.
6. Backup, recovery, restore, and deletion-ledger reconciliation.
7. Initial OS process/service identities and permission boundaries.
8. Secret/credential storage and access boundaries.
9. Exact API transport/framework.
10. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

Record accepted decisions here as they are made; supersede rather than silently rewrite. Avoid freezing a deep code/folder skeleton until structural decisions settle. After the major physical-design choices, perform one bounded architecture synthesis covering service boundaries, flows, PostgreSQL schema, artifact storage, security, API, package/folder layout, backup/recovery, build order, and validation gates.

---

# Current next decision

The next design discussion should define the lifecycle of derived data such as current-state projections, full-text materializations, summaries, chunks, embeddings, vector indexes, relationship closures, and context-supporting caches: how each records its source/generation/model/profile revision, becomes stale, rebuilds, and is prevented from becoming stronger truth than its canonical sources.
