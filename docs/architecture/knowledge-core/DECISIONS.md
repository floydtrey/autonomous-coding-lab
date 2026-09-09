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

Knowledge Core will be designed as its own local/network-capable service rather than as code owned directly by Vera or ACL. Vera, ACL, and future clients interact through a defined interface and do not directly own/manipulate the canonical database. Initial deployment may be on one computer, but the service must be movable later without client redesign.

**Reason:** preserves storage independence, a clean trust/component boundary, reuse, and later physical isolation.

---

## KC-D002 — PostgreSQL is the initial canonical knowledge store

**Status:** Accepted

PostgreSQL is the initial source of canonical semantic state. Embeddings, vector/full-text indexes, summaries, caches, graph projections, and current-state projections are derived/rebuildable where practical and do not become independent truth merely because they optimize retrieval. The six conceptual families do not have to map one-to-one to six tables.

**Reason:** strong structured constraints, transactions, temporal/history support, provenance, concurrency control, and mixed retrieval without premature distributed complexity.

---

## KC-D003 — Large artifact bytes live outside PostgreSQL

**Status:** Accepted

PostgreSQL stores RESOURCE identity, metadata, exact version/digest, lineage, locators, ownership/sensitivity references, and semantics. Large PDFs, images, archives, models, source bundles, video, and similar bytes live in a separately managed artifact store.

**Reason:** preserves `logical resource != locator != representation != exact content/version` and avoids using PostgreSQL as bulk binary storage.

---

## KC-D004 — Authority is a separate deterministic service boundary

**Status:** Accepted

AI reasoning does not grant itself authority. Vera or another client requests an operation; Authority evaluates whether that exact operation is permitted for the authenticated principal, purpose, context, policy version, freshness requirements, and obligations. Retrieval alone never grants execution permission. Authority may initially share a machine but must be separable later.

**Reason:** prevents model reasoning, knowledge, prompt text, or retrieved instructions from becoming authorization.

---

## KC-D005 — Architecture supports a physically read-only Authority Root

**Status:** Accepted

Static/slow-changing root authority material should be capable of living on controller-enforced hardware write-protected media: root policy, trusted-principal/verification roots, capability/confirmation rules, policy-version metadata, and appropriate verification material. Writable requests, approvals, denials, attempts, results, audits, and effect settlement remain elsewhere.

Physical write protection is not assumed to stop a compromised host from bypassing Authority; OS/process isolation and credential separation remain required layers.

**Reason:** low-cost physical barrier against software/AI modifying root rules while retaining an easy path to a separate Authority machine later.

---

## KC-D006 — Canonical knowledge history is non-destructive and supports explicit undo/reversal

**Status:** Accepted

Ordinary learning/correction never destroys prior canonical state. Corrections, contradictions, supersessions, invalidations, and replacements create new assertion/version/transition records while earlier history and provenance remain addressable. Undo/reversal records another transition that restores an earlier or newly corrected state as current without erasing the mistaken intermediate state.

Derived current projections may be rebuilt. Privacy erasure is a separate privileged lifecycle and is not ordinary undo.

**Reason:** preserves fallback, audit, historical truth/belief queries, conflicts, provenance, and reversible mistakes.

---

## KC-D007 — Assertion semantics use typed relational fields with bounded JSON extensibility

**Status:** Accepted

Canonical ASSERTION records are not opaque generic JSON or an untyped EAV bucket. Query/constraint/authorization/history/provenance-critical semantics use explicit typed relational fields or governed relational child records: identity, predicate/profile, subject, typed object/value, epistemic/polarity state, world-valid time, knowledge-record time/revision, applicability, lifecycle, sensitivity/ownership references, and profile revision.

`JSONB` may be a bounded profile-governed extension area, but may not replace typed core fields, hide authority-critical semantics, or become an ungoverned alternate truth store.

**Reason:** preserves both correctness and extensibility.

---

## KC-D008 — Canonical records use a universal internal reference registry for cross-family links

**Status:** Accepted

A small physical reference registry gives each addressable canonical record one stable internal reference across Entity, Assertion, Occurrence, Resource/version, and Semantic Profile/revision. Specialized tables retain their own semantics and constraints. Assertions/provenance can safely reference this address space; scalar values remain typed. The registry is physical addressing, not a seventh conceptual primitive or an untyped graph.

**Reason:** preserves foreign-key integrity without sprawling family-specific nullable foreign keys or weak application-only polymorphic IDs.

---

## KC-D009 — Temporal model uses independent world-valid time and immutable knowledge-record time

**Status:** Accepted

Knowledge Core separates **world-valid time** from **knowledge-record time**. World applicability uses PostgreSQL temporal/range-capable fields where appropriate and preserves uncertainty/precision. Every canonical assertion/occurrence/lifecycle transition receives immutable recorded timestamp plus stable replay/order identity. Late correction appends at the actual record time with whatever earlier world-valid interval is supported; it never pretends the system knew it earlier.

Current state is a derived/rebuildable projection. Absolute instants use timezone-aware timestamps; conflicting overlapping claims remain representable.

**Reason:** supports both current reconstruction of history and historical belief without rewriting the learning timeline.

---

## KC-D010 — Provenance is a typed, traversable lineage model separate from semantic relationships and lifecycle state

**Status:** Accepted

Provenance/evidence is stored as explicit typed directed links among addressable records, pinned to exact resource version and occurrence/activity context where applicable. Relations are governed/versioned rather than free text. Provenance is traversable backward for explanation and forward for impact/rebuild/deletion reconciliation.

Provenance does not replace domain relationships, currentness transitions, confidence/truth, sensitivity clearance, permission, or authority.

**Reason:** avoids an untyped edge model that blurs evidence, domain semantics, correction state, and authority.

---

## KC-D011 — Initial artifact store is a local immutable content-addressed filesystem

**Status:** Accepted

Initial artifact bytes live in a configurable local filesystem store keyed by SHA-256 digest. Blobs are immutable after ingestion; changed bytes create a new digest and resource-version record. Identical bytes may deduplicate physically but do not merge logical resource identity, provenance, ownership, sensitivity, authority, or history.

Ingestion stages bytes, verifies digest/size, atomically commits the blob, then records PostgreSQL metadata; orphan cleanup is separate. The backend remains replaceable later by another drive, NAS, or object store.

**Reason:** immutable exact-version identity and reproducibility with very low operational complexity.

---

## KC-D012 — Semantic profiles and vocabulary are immutable, explicitly versioned, and pinned by assertions

**Status:** Accepted

Knowledge Core distinguishes logical semantic profiles from immutable profile revisions, and stable predicate/kind/role identities from revision-specific definitions. Every assertion whose meaning depends on a vocabulary pins the exact governing profile revision.

A mutable active revision may guide new writes, but old records are never reinterpreted when it changes. Material meaning changes create a new semantic identity or explicit migration/mapping, not a silent redefinition. Profile dependencies are pinned to exact revisions. Activated revisions are immutable; deprecation preserves history. Explicit transformations to new semantics create new provenance-bearing records.

Domain concepts such as Home Assistant entities, Git commits, ACL workers, and email threads remain profile semantics over the universal core rather than new universal primitives.

**Reason:** allows Vera, ACL, research, software, devices, and future domains to evolve without changing historical meaning.

---

## KC-D013 — Knowledge Core API exposes semantic operation classes, not generic CRUD or database access

**Status:** Accepted

Vera, ACL, and other clients will interact with Knowledge Core through semantic operations rather than raw SQL, table CRUD, or arbitrary "update record" endpoints.

The API contract must keep at least these action families distinguishable:

### Read/retrieval

- resolve/identify candidate entities or resources;
- retrieve current knowledge;
- retrieve world-history or historical-belief views;
- structured/full-text/semantic/relationship search;
- retrieve conflicts/uncertainty;
- explain provenance/derivation.

### Ordinary append

- append an assertion/claim;
- record an occurrence/observation;
- register/ingest a logical resource and exact version;
- attach evidence/provenance under governed semantics.

### Revision/lifecycle

- correct/supersede/invalidate an assertion;
- reverse/undo a prior lifecycle transition;
- perform explicit identity transitions such as merge, split, replacement, or reassignment.

### Privileged governance

- restrict or erase knowledge;
- change sensitivity/ownership classifications;
- activate/register semantic-profile revisions;
- perform maintenance operations that can alter canonical interpretation or availability.

These are separate Authority action classes where their risk differs. Permission to read does not imply disclose/export/use-for-automation; permission to append does not imply correct/merge/delete/profile-admin.

Clients never receive PostgreSQL credentials and do not set canonical record time/revision themselves. They may supply claimed/source/world time and source evidence; Knowledge Core assigns trusted record-time/revision identity.

Mutation requests identify the semantic operation and target(s) explicitly rather than expressing arbitrary field patches. The API will reserve support for idempotency/precondition metadata; exact concurrency mechanics are decided separately.

Read/search responses are structured and preserve identifiers, temporal/currentness state, provenance/conflict signals, and relevant uncertainty rather than returning only generated prose. Model-facing natural-language context is a later context-construction product, not the canonical API representation.

The API is network-capable by design, but the exact transport/framework is not fixed by this decision. Initial loopback/local deployment may later move across a VM or machine boundary without semantic API redesign.

**Reason:** semantic operations make authority enforceable, preserve non-destructive history, prevent generic update endpoints from bypassing lifecycle rules, and keep the database implementation hidden from clients.

---

# Open physical-design decisions

These remain deliberately unresolved and should be decided before freezing the deep Knowledge Core folder/package layout:

1. Detailed PostgreSQL table split for canonical/derived structures.
2. Retrieval pipeline ordering and context-construction boundary.
3. Derived-data generation, invalidation, rebuild, and versioning.
4. Identity-resolution workflow and transition mechanics.
5. Deletion/retention/reconciliation workflow.
6. Concurrency, revision/precondition, retry/idempotency, and stale-write protection.
7. Backup, recovery, restore, and deletion-ledger reconciliation.
8. Initial OS process/service identities and permission boundaries.
9. Secret/credential storage and access boundaries.
10. Exact API transport/framework.
11. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

Record accepted decisions here as they are made; supersede rather than silently rewrite. Avoid freezing a deep code/folder skeleton until structural decisions settle. After the major physical-design choices, perform one bounded architecture synthesis covering service boundaries, flows, PostgreSQL schema, artifact storage, security, API, package/folder layout, backup/recovery, build order, and validation gates.

---

# Current next decision

The next design discussion should define retrieval ordering and context construction: authorization/sensitivity filtering, structured and temporal selection, relationship traversal, full-text and semantic candidate generation, provenance/conflict/currentness evaluation, reranking, and the exact point at which safe structured results become model-facing context.
