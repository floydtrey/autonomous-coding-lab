# Knowledge Core Architecture Decision Log

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Component:** Knowledge Core  
**Status:** active physical-architecture decision log  

---

# Purpose

This file records accepted physical-architecture decisions for Knowledge Core as they are made. Detailed architecture documentation will be synthesized after the major structural decisions are complete. The completed Knowledge Architecture Evidence Campaign remains the evidence base; physical choices must not weaken it.

Conceptual primitive families remain semantic roles rather than mandatory tables: ENTITY, ASSERTION, OCCURRENCE, RESOURCE, EVIDENCE/PROVENANCE LINK, and SEMANTIC PROFILE/VOCABULARY DEFINITION.

> **Knowledge does not grant authority. Authority does not prove execution. Execution acknowledgement does not prove world settlement.**

---

# Decision status

- **Accepted** — current architecture decision; later changes require an explicit superseding decision.
- **Open** — deliberately unresolved.
- **Superseded** — retained for history but replaced by a later decision.

Decisions are not silently rewritten when they change.

---

# Accepted decisions

## KC-D001 — Knowledge Core is a standalone service
**Status:** Accepted

Knowledge Core is its own local/network-capable service. Vera, ACL, and future clients use a defined interface and never directly own/manipulate the canonical database. Initial co-location on one PC must not prevent later process/VM/machine separation.

## KC-D002 — PostgreSQL is the initial canonical knowledge store
**Status:** Accepted

PostgreSQL is the initial source of canonical semantic state. Search indexes, embeddings, summaries, caches, graph projections, and current-state projections are derived/rebuildable where practical. The six conceptual families need not map one-to-one to six tables.

## KC-D003 — Large artifact bytes live outside PostgreSQL
**Status:** Accepted

PostgreSQL stores RESOURCE identity, metadata, exact version/digest, lineage, locators, ownership/sensitivity references, and semantics; large raw bytes live in a separately managed artifact store.

## KC-D004 — Authority is a separate deterministic service boundary
**Status:** Accepted

AI reasoning requests operations but does not grant authority. Authority evaluates the exact operation for authenticated principal, purpose, context, policy revision, freshness, and obligations. Retrieval never itself grants execution permission.

## KC-D005 — Architecture supports a physically read-only Authority Root
**Status:** Accepted

Static/slow-changing root authority policy and verification material can live on controller-enforced write-protected media. Writable operational authority/effect history remains elsewhere. Physical protection supplements, not replaces, process/OS/credential isolation.

## KC-D006 — Canonical knowledge history is non-destructive and supports explicit undo/reversal
**Status:** Accepted

Ordinary learning/correction appends new assertion/version/transition records rather than destroying prior canonical state. Undo/reversal is another explicit transition that can restore an earlier state as current without erasing mistaken intermediate history. Privacy erasure is separate.

## KC-D007 — Assertion semantics use typed relational fields with bounded JSON extensibility
**Status:** Accepted

Canonical ASSERTION semantics that matter for query, history, provenance, constraints, or authority use explicit typed relational fields/children. `JSONB` is only a bounded, profile-governed extension area and may not replace core semantics or hide authority-critical meaning.

## KC-D008 — Canonical records use a universal internal reference registry for cross-family links
**Status:** Accepted

A small physical reference registry provides stable internal addressing across canonical Entity, Assertion, Occurrence, Resource/version, and Semantic Profile/revision records. Specialized tables retain their own semantics/constraints; the registry is not a seventh conceptual primitive or untyped graph.

## KC-D009 — Temporal model uses independent world-valid time and immutable knowledge-record time
**Status:** Accepted

Knowledge Core separately records when a claim applies in the world and when Knowledge Core learned/recorded it. Late corrections append at the real record time with their supported world-valid interval. Current state is derived/rebuildable; historical belief remains reconstructable.

## KC-D010 — Provenance is a typed, traversable lineage model separate from semantic relationships and lifecycle state
**Status:** Accepted

Evidence/provenance uses governed typed directed links, exact source versions, and occurrence/activity context. It supports backward explanation and forward impact. It never substitutes for domain relationships, correction/currentness state, truth/confidence, sensitivity clearance, permission, or authority.

## KC-D011 — Initial artifact store is a local immutable content-addressed filesystem
**Status:** Accepted

Initial artifact bytes live in a configurable local filesystem store keyed by SHA-256. Blobs are immutable; changed bytes create new versions. Identical bytes may deduplicate physically but do not merge logical identity/provenance/ownership/history. Backend may later move to another drive, NAS, or object store.

## KC-D012 — Semantic profiles and vocabulary are immutable, explicitly versioned, and pinned by assertions
**Status:** Accepted

Logical profiles have immutable exact revisions. Assertions pin the governing revision. Material meaning changes create new semantic identity or explicit migration/mapping rather than silently redefining old semantics. Old records never change meaning because a new profile becomes active.

## KC-D013 — Knowledge Core API exposes semantic operation classes, not generic CRUD or database access
**Status:** Accepted

Clients use meaningful operation families: read/search/explain, append assertion/occurrence/resource/evidence, correction/reversal, identity transition, and privileged restriction/erasure/profile administration. Clients receive no DB credentials, cannot set trusted record-time identity, and cannot issue arbitrary field updates. Responses remain structured and provenance/temporal/conflict-aware.

## KC-D014 — Retrieval is an authorization-first composite pipeline; context construction is a final derived step
**Status:** Accepted

Retrieval carries authenticated principal, purpose/use, and explicit query mode. Hard authority/sensitivity eligibility precedes protected model-facing exposure. Structured and temporal filtering, relationship traversal, full-text/semantic candidate generation, provenance/conflict/currentness evaluation, reranking, and final context construction remain distinguishable. Semantic/full-text rank is relevance, not truth/permission/currentness. Context packages retain source/revision and conflict/staleness metadata.

---

## KC-D015 — Derived data is generation-versioned, lineage-bound, explicitly staleable, and rebuildable

**Status:** Accepted

Current-state projections, normalized/extracted text, chunks, summaries, full-text materializations, embeddings, vector indexes, relationship closures, aggregates, caches, and context-supporting projections are **derived data**, not independent canonical truth.

Every derived artifact or derived generation that can affect retrieval must retain enough metadata to identify:

- a stable derived/generation identity;
- exact canonical source reference(s) and source revision/version(s) or a reproducible source-revision cutoff;
- derivation OCCURRENCE/activity identity where applicable;
- semantic-profile revision;
- algorithm/model identity and version/build when applicable;
- prompt/configuration/extraction/chunking/index profile revision when applicable;
- generation timestamp/revision;
- lifecycle state such as building, current, stale, failed, superseded, restricted, or deletion-pending.

A derived item may never become epistemically stronger merely because it is convenient to retrieve. A summary does not outrank its sources; an embedding similarity does not establish truth; an inferred relationship closure does not become a direct assertion.

Source changes can mark dependent derived records stale through forward lineage. Staleness triggers include, as applicable:

- source correction/supersession/invalidation;
- exact RESOURCE-version change;
- identity merge/split/reassignment that changes applicability;
- semantic-profile meaning/version change;
- extraction/chunking/model/configuration revision change;
- sensitivity/restriction change;
- privacy deletion/erasure request.

Derived generations should rebuild under a **generation-fenced** pattern where practical:

```text
old settled generation
        |
        +---- remains serving if allowed
        |
        v
new generation builds separately
        |
     validates
        |
        v
atomic current-generation switch
        |
        v
old generation becomes superseded / later garbage-collected
```

A partial or failed rebuild must not silently replace a known-settled generation.

Some projections, especially current-state lookup tables, may be updated synchronously in the same transaction as canonical appends for fast reads. That does not make them canonical; they must still be independently reconstructable from canonical history.

Stale derived data may be used only when the retrieval/use policy permits it and the stale condition is surfaced. Consequential/authority-sensitive decisions may not rely on stale derived state as if it were current merely because a fresher rebuild has not completed.

Restriction/deletion fences apply immediately to derived exposure even before physical cleanup/rebuild finishes. A derived cache or vector index may never keep restricted content retrievable just because reconciliation is still pending.

Indexes whose internal engine state cannot reasonably carry per-row lineage still require generation-level metadata that proves which canonical revision set/profile/configuration they index and supports safe rebuild/replace.

**Reason:** Knowledge Core depends heavily on derived retrieval helpers. Without explicit generation identity, lineage, staleness, and rebuild semantics, those helpers would eventually become hidden competing truth stores and would undermine correction, deletion, replay, and provenance requirements.

---

# Open physical-design decisions

1. Detailed PostgreSQL table split for canonical and derived structures.
2. Identity-resolution workflow and transition mechanics.
3. Deletion/retention/reconciliation workflow.
4. Concurrency, revision/precondition, retry/idempotency, and stale-write protection.
5. Backup, recovery, restore, and deletion-ledger reconciliation.
6. Initial OS process/service identities and permission boundaries.
7. Secret/credential storage and access boundaries.
8. Exact API transport/framework.
9. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

Record accepted decisions here as they are made; supersede rather than silently rewrite. Avoid freezing a deep code/folder skeleton until structural decisions settle. After the major physical-design choices, perform one bounded architecture synthesis covering service boundaries, flows, PostgreSQL schema, artifact storage, security, API, package/folder layout, backup/recovery, build order, and validation gates.

---

# Current next decision

The next design discussion should define operational identity resolution: how aliases/candidates remain ambiguous, how merges/splits/replacements are performed without destructive identity collapse, and how those transitions can be reversed while preserving provenance and dependent knowledge.
